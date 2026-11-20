# -*- coding: utf-8 -*-
"""Lucent ITA: native Kodi Home search, direct Enter-to-AI and landscape suggestions.

The sidebar selects this panel by focus; this script updates Window(home)
properties without opening a modal result window. OpenRouter stays in the
existing private profile file and is never logged or bundled with the skin.
"""
import datetime
import json
import os
import re
import sys
import time
import urllib.parse

import xbmc
import xbmcgui

sys.path.insert(0, os.path.dirname(__file__))
from ai_art_core import catalogue_art, normalize, tmdb_art, backdrop_full
from ai_intent_core import understand, GENRE_IT
from ai_exact_core import candidate, merge_candidates
from ai_cast_core import person_intent, find_person, credit_rows
import ai_assistant as assistant
from ai_search import (_ai_request, _discover, _add_artwork, _live_epg, _art_key,
                       _json_art, _settings, _save_key, stream4me_url, KEY_DIR, _rpc)

HOME = xbmcgui.Window(10000)
CACHE_FILE = os.path.join(KEY_DIR, "home_suggestions.json")
CACHE_SECONDS = 6 * 3600
NOW = datetime.date.today
SOURCES = ("pop", "new", "tv", "top", "result")
SLOTS = 16
SUGGESTION_LIMIT = 24
PLACEHOLDER = "Cerca un film, una serie o chiedi un consiglio..."
CLOSE_SEARCH = "Tocca la barra e premi Invio per cercare con Lucent AI."


def _put(name, value):
    value = "" if value is None else str(value)
    if HOME.getProperty(name) != value:
        HOME.setProperty(name, value)
    if name == "ai.home.query":
        HOME.setProperty("ai.home.hasquery", "1" if value and value != PLACEHOLDER else "")


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
    return {"title": title, "image": image, "backdrop": backdrop_full(image),
            "kind": kind, "sub": sub}


def _read_cache():
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as fp:
            obj = json.load(fp)
        if (isinstance(obj, dict) and
                time.time() - obj.get("time", 0) < CACHE_SECONDS and
                obj.get("pop") and obj.get("new") and obj.get("tv") and obj.get("top")):
            # Upgrade the existing 2.1.45.22 thumbnail-only cache automatically.
            # Keep the titles already loaded: no extra requests or manual clearing.
            changed = False
            for group in ("pop", "new", "tv", "top"):
                for row in obj.get(group) or []:
                    if not isinstance(row, dict):
                        continue
                    hd = backdrop_full(row.get("backdrop") or row.get("image"))
                    if row.get("backdrop") != hd:
                        row["backdrop"] = hd
                        changed = True
            if changed:
                _write_cache(obj)
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
    """Four 16:9 discovery rows with pagination and an upper network deadline.

    No OpenRouter calls. Cinemeta catalog/skip extras follow its public manifest.
    No availability claims are made for any suggestion.
    """
    today = NOW()
    key = _art_key()
    deadline = time.monotonic() + 24
    groups = {"pop": [], "new": [], "tv": [], "top": []}
    seen = {name: set() for name in groups}

    def add(group, item, source, media=None):
        row = _metadata(item, source, media)
        if not row:
            return
        fingerprint = normalize(row["title"]) + "|" + row["kind"]
        if fingerprint in seen[group] or len(groups[group]) >= SUGGESTION_LIMIT:
            return
        if group == "new":
            date = str(item.get("released") or item.get("release_date") or "")
            if date[:10] and date[:10] > today.isoformat():
                return
            if row["sub"].find(str(today.year)) < 0 and row["sub"].find(str(today.year - 1)) < 0:
                return
        seen[group].add(fingerprint)
        groups[group].append(row)

    if key:
        first = (today - datetime.timedelta(days=290)).isoformat()
        requests = (
            ("pop", "https://api.themoviedb.org/3/trending/all/week", {}, None),
            ("tv", "https://api.themoviedb.org/3/trending/tv/week", {}, "tv"),
            ("top", "https://api.themoviedb.org/3/movie/top_rated", {}, "movie"),
            ("new", "https://api.themoviedb.org/3/discover/movie",
             {"sort_by": "primary_release_date.desc", "primary_release_date.gte": first,
              "primary_release_date.lte": today.isoformat(), "vote_count.gte": 3}, "movie"),
        )
        for group, endpoint, extra, media in requests:
            for page in (1, 2):
                if time.monotonic() > deadline or len(groups[group]) >= SUGGESTION_LIMIT:
                    break
                params = dict(extra, api_key=key, language="it-IT", page=page)
                answer = _json_art(endpoint + "?" + urllib.parse.urlencode(params), timeout=4)
                for item in answer.get("results") or []:
                    if not isinstance(item, dict) or item.get("media_type") == "person":
                        continue
                    add(group, item, "tmdb", media)

    # Public fallback or additional suggestions. Each catalogue has a real
    # cursor (skip), so right-scrolling shows genuinely different titles.
    catalogues = {
        "pop": [("movie", "top"), ("series", "top")],
        "new": [("movie", "year/genre=%d" % today.year),
                ("movie", "year/genre=%d" % (today.year - 1))],
        "tv": [("series", "top")],
        "top": [("movie", "imdbRating")],
    }
    for group, queries in catalogues.items():
        for media, category in queries:
            for skip in (0, 20, 40):
                if time.monotonic() > deadline or len(groups[group]) >= SUGGESTION_LIMIT:
                    break
                base = "https://v3-cinemeta.strem.io/catalog/%s/%s" % (media, category)
                path = base + ("/skip=%d.json" % skip if skip and "/" not in category
                               else "&skip=%d.json" % skip if skip else ".json")
                data = _json_art(path, timeout=4)
                if not isinstance(data, dict):
                    continue
                for item in data.get("metas") or []:
                    if isinstance(item, dict):
                        add(group, item, "cinemeta", media)
            if len(groups[group]) >= SUGGESTION_LIMIT:
                break
    groups["time"] = time.time()
    return groups


def _fill(name, rows):
    limit = SLOTS if name == "result" else SUGGESTION_LIMIT
    for i in range(1, limit + 1):
        row = rows[i - 1] if i <= len(rows) else {}
        prefix = "ai.home.%s.%d." % (name, i)
        for field in ("title", "sub", "image", "backdrop", "poster", "kind", "reason", "year", "tmdb_id"):
            _put(prefix + field, row.get(field, ""))


def refresh():
    if not HOME.getProperty("ai.home.query"):
        _put("ai.home.query", PLACEHOLDER)
    if not HOME.getProperty("ai.home.mode"):
        _put("ai.home.mode", "suggestions")
    cache = _read_cache()
    if cache:
        for group in ("pop", "new", "tv", "top"):
            _fill(group, cache.get(group) or [])
        if not HOME.getProperty("ai.home.status"):
            _status(CLOSE_SEARCH)
        return
    _status("Carico i suggerimenti del momento...")
    data = _fetch_suggestions()
    for group in ("pop", "new", "tv", "top"):
        _fill(group, data.get(group) or [])
    if data["pop"] or data["new"] or data["tv"] or data["top"]:
        _write_cache(data)
    if HOME.getProperty("ai.home.mode") != "results":
        _status(CLOSE_SEARCH if any(data.get(group) for group in ("pop","new","tv","top")) else
                "Suggerimenti non disponibili, ma puoi comunque cercare con Lucent AI.")


def _focus_search():
    """Never hide a focused result/clear control before Home has another focus.

    The button's XML also runs SetFocus synchronously before RunScript, while
    the clear button remains visible if Kodi has not yet transferred focus.
    """
    try:
        xbmc.executebuiltin("SetFocus(9500)", True)
    except (RuntimeError, TypeError):
        pass


def reset_search():
    """Return to discovery without losing remote/keyboard navigation."""
    _focus_search()
    _fill("result", [])
    _put("ai.home.query", PLACEHOLDER)
    _put("ai.home.mode", "suggestions")
    _status(CLOSE_SEARCH)
    _focus_search()


def input_search():
    default = HOME.getProperty("ai.home.query")
    if default == PLACEHOLDER:
        default = ""
    keyboard = xbmc.Keyboard(default, "Lucent AI · Cosa vuoi guardare?")
    keyboard.doModal()
    if not keyboard.isConfirmed():
        return
    query = keyboard.getText().strip()[:500]
    if not query:
        reset_search()
        return
    _put("ai.home.query", query)
    _run_query(query)


def _exact_titles(prompt):
    """Search BOTH movie and TV indexes, independently of OpenRouter.

    Keep differently dated or typed titles separate; 'Silo' must not become
    only the 2015 movie because that happened to be the first lookup.
    """
    rows = []
    deadline = time.monotonic() + 17
    searches = (("serie", "series", "tv", "TVShows", "tvshows"),
                ("film", "movie", "movie", "Movies", "movies"))
    for kind, catalog_kind, tmdb_kind, library_kind, result_key in searches:
        try:
            results = _rpc("VideoLibrary.Get" + library_kind, {
                "filter": {"field": "title", "operator": "contains", "value": prompt},
                "properties": ["title", "year", "art", "rating"],
                "limits": {"start": 0, "end": 40}
            }).get(result_key) or []
            for item in results:
                match = candidate(prompt, item, kind, "kodi")
                if match:
                    rows.append(match)
        except (RuntimeError, ValueError, TypeError):
            pass
        # Cinemeta is available without an API key.
        if time.monotonic() < deadline:
            url = "https://v3-cinemeta.strem.io/catalog/%s/top/search=%s.json" % (
                catalog_kind, urllib.parse.quote(prompt, safe=""))
            data = _json_art(url, timeout=4)
            for item in (data.get("metas") or []) if isinstance(data, dict) else []:
                match = candidate(prompt, item, kind, "cinemeta")
                if match:
                    rows.append(match)
        tmdb_key = _art_key()
        if tmdb_key and time.monotonic() < deadline:
            params = urllib.parse.urlencode({
                "api_key": tmdb_key, "query": prompt, "language": "it-IT",
                "include_adult": "false", "page": 1})
            data = _json_art("https://api.themoviedb.org/3/search/%s?%s" %
                             (tmdb_kind, params), timeout=4)
            for item in (data.get("results") or []) if isinstance(data, dict) else []:
                match = candidate(prompt, item, kind, "tmdb")
                if match:
                    rows.append(match)
    # TVmaze can find shows omitted by Cinemeta, without an API key.
    if not any(x["kind"] == "serie" for x in rows) and time.monotonic() < deadline:
        data = _json_art("https://api.tvmaze.com/search/shows?q=" +
                         urllib.parse.quote(prompt, safe=""), timeout=4)
        for item in data if isinstance(data, list) else []:
            match = candidate(prompt, item, "serie", "tvmaze")
            if match:
                rows.append(match)
    found = merge_candidates(rows, SLOTS)
    if found:
        return found
    # Even an unindexed exact title still has a working Stream4Me route.
    return [{"title": prompt, "kind": "titolo", "year": "", "rating": "",
             "poster": "", "backdrop": "",
             "reason": "Non presente nei cataloghi: cerca il titolo in Stream4Me."}]


def _verified_person_search(person, intent):
    """Find credited actor/director titles, never substituting guessed year matches.

    TMDb credentials are configured through Lucent skin's existing
    Integrations setting and remain exclusively inside the Kodi profile.
    """
    key = _art_key()
    if not key:
        return [], ("Per cercare film con un attore o regista, configura la Key "
                    "TMDb nelle Impostazioni skin > Integrazioni. "
                    "La Key OpenRouter da sola non verifica i cast.")
    args = urllib.parse.urlencode({
        "api_key": key, "query": person["name"], "language": "it-IT",
        "include_adult": "false", "page": 1})
    results = _json_art("https://api.themoviedb.org/3/search/person?" + args, timeout=6)
    matched = find_person(results.get("results") or [], person["name"], person["role"])
    if not matched or not matched.get("id"):
        return [], "Impossibile verificare l'identità di %s su TMDb." % person["name"]
    pid = str(int(matched["id"]))
    kinds = ("film", "serie") if not intent.get("kind") else (intent["kind"],)
    rows = []
    for kind in kinds:
        resource = "movie_credits" if kind == "film" else "tv_credits"
        url = "https://api.themoviedb.org/3/person/%s/%s?%s" % (
            pid, resource, urllib.parse.urlencode({"api_key": key, "language": "it-IT"}))
        credits = _json_art(url, timeout=6)
        rows.extend(credit_rows(credits, kind, person["role"], intent))
    rows.sort(key=lambda row: (row["kind"] != "film", -(float(row.get("rating") or 0))))
    if rows:
        return rows[:SLOTS], ("Titoli con %s verificati nei crediti TMDb" %
                             person["name"])
    period = " del %s" % intent["year"] if intent.get("year") else ""
    return [], ("Nessun titolo%s con %s verificato nei crediti TMDb." %
                (period, person["name"]))


def _run_query(prompt, context=None):
    """One validated plan then a bounded, allowlisted executor."""
    _focus_search()
    progress = xbmcgui.DialogProgressBG()
    progress.create("Lucent AI", "Comprendo la richiesta...")
    _status("Ricerca in corso...")
    try:
        # Simple titles remain available without any AI credentials. Requests for
        # actions or people must go through the planner (even just two words).
        direct = understand(prompt)["direct"] and not context and not re.search(
            r"\b(riprendi|continua|avvia|apri|aggiungi|aggiungimi|cancella|elimina|"
            r"aggiorna|guarda|chi|quando|quanto|perche|perché|spiega|dammi|dal|senza)\b",
            prompt, re.I)
        if direct:
            rows = _exact_titles(prompt)
            message = "Titoli corrispondenti: %d" % len(rows)
            assistant.remember(prompt, {"operation":"search","title":prompt})
        else:
            p = assistant.plan_query(prompt,context)
            op = p["operation"]
            progress.update(35,"Lucent AI","Consulto le fonti disponibili...")
            if op in ("resume","play"):
                target,message = assistant.resume_target(p)
                progress.close()
                if target:
                    if _rpc("Player.Open",target)=="OK":
                        _status("Riproduzione richiesta · "+message)
                    else:
                        _status("Kodi non ha confermato la riproduzione.")
                else: xbmcgui.Dialog().ok("Lucent AI",message)
                return
            if op=="scan":
                progress.close()
                if xbmcgui.Dialog().yesno("Lucent AI","Aggiornare la videoteca Kodi?"):
                    _rpc("VideoLibrary.Scan",{})
                    _status("Aggiornamento videoteca richiesto a Kodi.")
                return
            if op=="add":
                progress.close()
                if not p["title"]:
                    xbmcgui.Dialog().ok("Lucent AI","Indica quale titolo vuoi aggiungere.")
                    return
                kind=p["kind"]
                found=[x for k in ([kind] if kind else ["serie","film"]) for x in assistant.library_items(k)
                       if normalize(x.get("title"))==normalize(p["title"])]
                if found:
                    xbmcgui.Dialog().ok("Lucent AI","Un titolo omonimo è già nella videoteca. Controlla la scheda prima di aggiungerne un altro.")
                    return
                xbmcgui.Dialog().ok("Lucent AI","L'importazione da una sorgente specifica va confermata nell'add-on. Apro la ricerca del titolo; non posso confermare l'aggiunta automatica.")
                if xbmc.getCondVisibility("System.HasAddon(plugin.video.s4me)"):
                    xbmc.executebuiltin('ActivateWindow(Videos,"%s",return)' % stream4me_url(p["title"]))
                return
            if op=="answer":
                response=assistant.answer(prompt,p,context)
                progress.close()
                xbmcgui.Dialog().textviewer("Lucent AI",response)
                return
            if op=="epg":
                progress.close()
                if p["title"]:
                    live,msg=_live_epg([p["title"]])
                    xbmcgui.Dialog().ok("Lucent AI","\n".join(x["title"]+" · "+x["reason"] for x in live) or msg)
                else:
                    xbmc.executebuiltin("ActivateWindow(TVGuide)")
                return
            if op=="unsupported":
                progress.close()
                xbmcgui.Dialog().ok("Lucent AI","Questa azione non è ancora supportata da Kodi/Lucent.")
                return
            if op=="library":
                rows=[]
                for kind in ([p["kind"]] if p["kind"] else ["film","serie"]):
                    for obj in assistant.library_items(kind):
                        if p["title"] and normalize(p["title"])!=normalize(obj.get("title")): continue
                        if p["unwatched"] and (obj.get("playcount") or obj.get("watchedepisodes")): continue
                        art=obj.get("art") or {}
                        rows.append({"title":obj.get("title"),"kind":kind,"year":obj.get("year"),
                                     "poster":art.get("poster"),"backdrop":art.get("fanart")})
                message="Videoteca Kodi · filtri titolo, tipo e visione"
                if assistant.hard_filters(dict(p,unwatched=False)):
                    message+=" · altri criteri non verificati"
            else:
                rows,message=assistant.catalogue(p,_exact_titles)
        _focus_search()
        if not rows:
            _put("ai.home.mode", "suggestions")
            _fill("result", [])
            _status(message+" · Nessuna corrispondenza trovata.")
            return
        result=[]
        for row in rows[:SLOTS]:
            kind=row.get("kind") or "film"
            year=str(row.get("year") or "")
            rating=str(row.get("rating") or "")
            sub="SERIE TV" if kind=="serie" else "FILM" if kind=="film" else "RICERCA TITOLO"
            if year: sub+="  ·  "+year
            if rating: sub+="  ·  ★ "+rating
            result.append({"title":row["title"],"sub":sub,
                           "poster":row.get("poster") or "",
                           "image":row.get("backdrop") or "",
                           "backdrop": backdrop_full(row.get("backdrop") or ""),
                           "kind":kind,"reason":row.get("reason") or "",
                           "year":year,"tmdb_id":row.get("tmdb_id") or ""})
        _fill("result",result)
        _put("ai.home.mode","results")
        _status(message+" · Seleziona un titolo per aprirlo.")
    except (RuntimeError,ValueError) as exc:
        _focus_search()
        _put("ai.home.mode","suggestions")
        _fill("result",[])
        _status(str(exc))
    except Exception as exc:
        xbmc.log("[skin.lucent] assistant: "+type(exc).__name__,xbmc.LOGWARNING)
        _focus_search()
        _put("ai.home.mode","suggestions")
        _fill("result",[])
        _status("Ricerca non disponibile. Verifica connessione e impostazioni.")
    finally:
        progress.close()


def history_menu():
    rows=assistant.history()
    if not rows:
        xbmcgui.Dialog().ok("Lucent AI","Nessuna ricerca recente.")
        return
    rows=list(reversed(rows))
    choice=xbmcgui.Dialog().select("Cronologia Lucent AI",[r["query"] for r in rows])
    if choice>=0:
        _put("ai.home.query",rows[choice]["query"])
        _run_query(rows[choice]["query"])


def ask_selected(container=0):
    if container not in (9510,9520,9530,9540,9550):
        # Explicit fallback: choose the active item from the visible shelves.
        ids=(9550,) if HOME.getProperty("ai.home.mode")=="results" else (9510,9520,9530,9540)
        choices=[(i,xbmc.getInfoLabel("Container(%d).ListItem.Label"%i)) for i in ids]
        choices=[x for x in choices if x[1]]
        if not choices: return
        selected=xbmcgui.Dialog().select("Chiedi all'AI · titolo",[x[1] for x in choices])
        if selected<0: return
        container=choices[selected][0]
    title=xbmc.getInfoLabel("Container(%d).ListItem.Label"%container)
    meta=xbmc.getInfoLabel("Container(%d).ListItem.Label2"%container)
    if not title: return
    keyboard=xbmc.Keyboard("","Chiedi all'AI · "+title)
    keyboard.doModal()
    if keyboard.isConfirmed() and keyboard.getText().strip():
        text=keyboard.getText().strip()[:500]
        _put("ai.home.query",text)
        _run_query(text,{"title":title,"metadata":meta})


def assistant_settings():
    d=xbmcgui.Dialog()
    cfg=_settings()
    choice=d.select("Lucent AI",["Chiave OpenRouter","Modello AI · "+cfg.get("model",assistant.MODEL),
        "Ragionamento · "+cfg.get("reasoning","medium"),
        "Memoria · "+("Attiva" if cfg.get("memory",True) else "Disattivata"),"Cancella cronologia"])
    if choice==0: set_key()
    elif choice==1:
        i=d.select("Modello OpenRouter",list(assistant.MODELS)+["Altro modello..."])
        if i==len(assistant.MODELS):
            model=d.input("ID modello OpenRouter",defaultt=cfg.get("model",assistant.MODEL))
            if re.fullmatch(r"[A-Za-z0-9_.:/-]{3,100}",model or ""): assistant.configure(model=model)
        elif i>=0: assistant.configure(model=assistant.MODELS[i])
    elif choice==2:
        i=d.select("Ragionamento",["Rapido","Bilanciato","Approfondito"])
        if i>=0: assistant.configure(reasoning=("low","medium","high")[i])
    elif choice==3: assistant.configure(memory=not cfg.get("memory",True))
    elif choice==4 and d.yesno("Lucent AI","Cancellare le quattro ricerche recenti?"): assistant.clear_history()


def open_title(source, index):
    if source not in SOURCES or not 1 <= index <= (SLOTS if source == "result" else SUGGESTION_LIMIT):
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
    elif action == "reset":
        reset_search()
    elif action == "open" and len(sys.argv) > 3:
        try:
            open_title(sys.argv[2], int(sys.argv[3]))
        except (ValueError, TypeError):
            pass
    elif action == "key":
        set_key()
    elif action == "settings":
        assistant_settings()
    elif action == "history":
        history_menu()
    elif action == "ask":
        ask_selected(int(sys.argv[2]) if len(sys.argv)>2 and sys.argv[2].isdigit() else 0)


if __name__ == "__main__":
    main()
