# -*- coding: utf-8 -*-
"""Lucent ITA: native Kodi Home search, direct Enter-to-AI and landscape suggestions.

The sidebar selects this panel by focus; this script updates Window(home)
properties without opening a modal result window. OpenRouter stays in the
existing private profile file and is never logged or bundled with the skin.
"""
import datetime
import json
import os
import sys
import time
import urllib.parse

import xbmc
import xbmcgui

sys.path.insert(0, os.path.dirname(__file__))
from ai_art_core import catalogue_art, normalize, tmdb_art
from ai_intent_core import understand, GENRE_IT
from ai_search import (_ai_request, _discover, _add_artwork, _live_epg, _art_key,
                       _json_art, _settings, _save_key, stream4me_url, KEY_DIR)

HOME = xbmcgui.Window(10000)
CACHE_FILE = os.path.join(KEY_DIR, "home_suggestions.json")
CACHE_SECONDS = 6 * 3600
NOW = datetime.date.today
SOURCES = ("pop", "new", "result")
SLOTS = 5
PLACEHOLDER = "Cerca un film, una serie o chiedi un consiglio..."
CLOSE_SEARCH = "Tocca la barra e premi Invio per cercare con Lucent AI."


def _put(name, value):
    value = "" if value is None else str(value)
    if HOME.getProperty(name) != value:
        HOME.setProperty(name, value)


def _status(value):
    _put("ai.home.status", value)


def _metadata(obj, source="cinemeta", media=None):
    """Return a verified landscape card; never use portrait artwork for a wide row."""
    if not isinstance(obj, dict):
        return None
    if source == "tmdb":
        art = tmdb_art(obj)
        title = obj.get("title") or obj.get("name") or ""
        kind = "serie" if (media or obj.get("media_type")) in ("tv", "series") else "film"
    else:
        art = catalogue_art(obj, "cinemeta")
        title = obj.get("name") or obj.get("title") or ""
        kind = "serie" if (media or obj.get("type")) in ("series", "tv") else "film"
    title = str(title).strip()
    image = art.get("backdrop") or ""
    if not title or not image:
        return None
    year = str(art.get("year") or "")
    rating = str(art.get("rating") or "")
    sub = ("SERIE TV" if kind == "serie" else "FILM")
    if year:
        sub += "  ·  " + year
    if rating:
        sub += "  ·  ★ " + rating
    return {"title": title, "image": image, "kind": kind, "sub": sub}


def _read_cache():
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as fp:
            obj = json.load(fp)
        if (isinstance(obj, dict) and
                time.time() - obj.get("time", 0) < CACHE_SECONDS and
                obj.get("pop") and obj.get("new")):
            return obj
    except (OSError, ValueError, TypeError):
        pass
    return {}


def _write_cache(data):
    try:
        os.makedirs(KEY_DIR, exist_ok=True)
        temp = CACHE_FILE + ".tmp"
        with open(temp, "w", encoding="utf-8") as fp:
            json.dump(data, fp, ensure_ascii=False)
        os.replace(temp, CACHE_FILE)
    except (OSError, ValueError, TypeError):
        xbmc.log("[skin.lucent] AI Home: suggestions cache unavailable", xbmc.LOGDEBUG)


def _fetch_suggestions():
    """Fetch curated metadata only. Popularity is NOT Stream4Me availability."""
    today = NOW()
    year = today.year
    key = _art_key()
    pop, recent = [], []

    if key:
        trending = _json_art(
            "https://api.themoviedb.org/3/trending/all/week?" +
            urllib.parse.urlencode({"api_key": key, "language": "it-IT"}),
            timeout=5)
        for obj in trending.get("results") or []:
            if obj.get("media_type") not in ("movie", "tv"):
                continue
            row = _metadata(obj, "tmdb")
            if row:
                pop.append(row)
            if len(pop) >= SLOTS:
                break
        first = (today - datetime.timedelta(days=270)).isoformat()
        params = {"api_key": key, "language": "it-IT", "sort_by": "primary_release_date.desc",
                  "primary_release_date.gte": first,
                  "primary_release_date.lte": today.isoformat(), "vote_count.gte": 3,
                  "page": 1}
        latest = _json_art(
            "https://api.themoviedb.org/3/discover/movie?" +
            urllib.parse.urlencode(params), timeout=5)
        for obj in latest.get("results") or []:
            row = _metadata(obj, "tmdb", "movie")
            if row:
                recent.append(row)
            if len(recent) >= SLOTS:
                break

    # Official Cinemeta movie/series/top and movie/year catalogs are public
    # and require no extra API key. Keep names as "popular", not "live now".
    for media in ("movie", "series"):
        if len(pop) >= SLOTS:
            break
        catalog = _json_art(
            "https://v3-cinemeta.strem.io/catalog/%s/top.json" % media, timeout=5)
        for obj in (catalog.get("metas") or []) if isinstance(catalog, dict) else []:
            row = _metadata(obj, "cinemeta", media)
            if row and normalize(row["title"]) not in {normalize(x["title"]) for x in pop}:
                pop.append(row)
            if len(pop) >= SLOTS:
                break

    for selected_year in (year, year - 1):
        if len(recent) >= SLOTS:
            break
        catalog = _json_art(
            "https://v3-cinemeta.strem.io/catalog/movie/year/genre=%d.json" % selected_year,
            timeout=5)
        for obj in (catalog.get("metas") or []) if isinstance(catalog, dict) else []:
            released = str(obj.get("released") or obj.get("release_date") or "")
            if released and released[:10] > today.isoformat():
                continue
            row = _metadata(obj, "cinemeta", "movie")
            if row and row["sub"].find(str(selected_year)) >= 0 \
                    and normalize(row["title"]) not in {normalize(x["title"]) for x in recent}:
                recent.append(row)
            if len(recent) >= SLOTS:
                break
    return {"time": time.time(), "pop": pop[:SLOTS], "new": recent[:SLOTS]}


def _fill(name, rows):
    for i in range(1, SLOTS + 1):
        row = rows[i - 1] if i <= len(rows) else {}
        prefix = "ai.home.%s.%d." % (name, i)
        for field in ("title", "sub", "image", "poster", "kind", "reason"):
            _put(prefix + field, row.get(field, ""))


def refresh():
    if not HOME.getProperty("ai.home.query"):
        _put("ai.home.query", PLACEHOLDER)
    if not HOME.getProperty("ai.home.mode"):
        _put("ai.home.mode", "suggestions")
    cache = _read_cache()
    if cache:
        _fill("pop", cache["pop"])
        _fill("new", cache["new"])
        if not HOME.getProperty("ai.home.status"):
            _status(CLOSE_SEARCH)
        return
    _status("Carico i suggerimenti più popolari...")
    data = _fetch_suggestions()
    _fill("pop", data["pop"])
    _fill("new", data["new"])
    if data["pop"] and data["new"]:
        _write_cache(data)
    if HOME.getProperty("ai.home.mode") != "results":
        _status(CLOSE_SEARCH if (data["pop"] or data["new"]) else
                "Suggerimenti temporaneamente non disponibili. La ricerca rimane utilizzabile.")


def input_search():
    default = HOME.getProperty("ai.home.query")
    if default == PLACEHOLDER:
        default = ""
    query = xbmcgui.Dialog().input(
        "Lucent AI · Cosa vuoi guardare?", defaultt=default,
        type=xbmcgui.INPUT_ALPHANUM)
    if not query or not query.strip():
        return
    query = query.strip()[:250]
    _put("ai.home.query", query)
    _run_query(query)


def _run_query(prompt):
    from ai_search import _art_key
    intent = understand(prompt)
    progress = xbmcgui.DialogProgressBG()
    progress.create("Lucent AI", "Cerco titoli e verifico i metadati...")
    _status("Ricerca in corso...")
    try:
        if intent["direct"]:
            rows = _add_artwork([{"title": prompt, "kind": "film",
                                  "reason": "Cerca il titolo esatto in Stream4Me."}], intent)
            message = "Ricerca per titolo esatto."
        else:
            verified = _discover(intent, _art_key()) if intent.get("year") else []
            key = (_settings().get("openrouter_key") or "").strip()
            suggestions, message = [], ""
            if key and len(verified) < 4:
                try:
                    suggestions, message = _ai_request(prompt, key, intent)
                except RuntimeError as err:
                    if not verified:
                        raise
                    message = "Catalogo verificato."
            elif not key and not verified:
                _status("Imposta la chiave OpenRouter nelle impostazioni della skin.")
                return
            progress.update(65, "Lucent AI", "Verifico genere, anno e copertine...")
            rows = _add_artwork(verified + suggestions, intent)
            if intent.get("year"):
                label = GENRE_IT.get(intent.get("genre"), "qualsiasi genere")
                message = "Risultati verificati · %s · %s" % (label, intent["year"])
            else:
                message = message or "Risultati AI verificati."
        if not rows:
            _fill("result", [])
            _put("ai.home.mode", "suggestions")
            _status("Nessun titolo verificato per questa richiesta. Prova un'altra ricerca.")
            return
        # No full-screen dialog; populate visible native Home controls directly.
        result = []
        for row in rows[:SLOTS]:
            kind = row.get("kind") or "film"
            year = str(row.get("year") or "")
            rating = str(row.get("rating") or "")
            sub = ("SERIE TV" if kind == "serie" else "FILM")
            if year:
                sub += "  ·  " + year
            if rating:
                sub += "  ·  ★ " + rating
            result.append({"title": row["title"], "sub": sub,
                           "poster": row.get("poster") or "", "kind": kind,
                           "reason": row.get("reason") or ""})
        _fill("result", result)
        _put("ai.home.mode", "results")
        _status(message + " · Seleziona un titolo per aprire Stream4Me.")
    except RuntimeError as err:
        _fill("result", [])
        _put("ai.home.mode", "suggestions")
        _status(str(err) + " · La ricerca per titolo resta disponibile.")
    except Exception as err:
        # No model messages, queries or private keys in Kodi logs.
        xbmc.log("[skin.lucent] AI Home query: " + type(err).__name__, xbmc.LOGWARNING)
        _fill("result", [])
        _put("ai.home.mode", "suggestions")
        _status("Ricerca non disponibile. Riprova o verifica la connessione.")
    finally:
        progress.close()


def open_title(source, index):
    if source not in SOURCES or not 1 <= index <= SLOTS:
        return
    title = HOME.getProperty("ai.home.%s.%d.title" % (source, index)).strip()
    if not title:
        return
    if not xbmc.getCondVisibility("System.HasAddon(plugin.video.s4me)"):
        xbmcgui.Dialog().ok("Lucent AI", "Installa o abilita Stream4Me per cercare il titolo.")
        return
    try:
        uri = stream4me_url(title)
    except ValueError:
        return
    xbmc.executebuiltin('ActivateWindow(Videos,"%s",return)' % uri)


def set_key():
    value = xbmcgui.Dialog().input(
        "Chiave OpenRouter per Lucent AI (salvata solo in Kodi)",
        type=xbmcgui.INPUT_ALPHANUM,
        option=getattr(xbmcgui, "ALPHANUM_HIDE_INPUT", 0))
    value = (value or "").strip()
    if not value:
        return
    if not value.startswith("sk-or-"):
        xbmcgui.Dialog().ok("Lucent AI", "Una chiave OpenRouter valida deve iniziare con sk-or-.")
        return
    try:
        _save_key(value)
    except OSError:
        xbmcgui.Dialog().ok("Lucent AI", "Impossibile salvare la chiave nel profilo Kodi.")
        return
    xbmcgui.Dialog().notification("Lucent AI", "Chiave OpenRouter salvata.",
                                  xbmcgui.NOTIFICATION_INFO, 3000)


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else "refresh"
    if action == "refresh":
        refresh()
    elif action == "input":
        input_search()
    elif action == "open" and len(sys.argv) > 3:
        try:
            open_title(sys.argv[2], int(sys.argv[3]))
        except (ValueError, TypeError):
            pass
    elif action == "key":
        set_key()


if __name__ == "__main__":
    main()
