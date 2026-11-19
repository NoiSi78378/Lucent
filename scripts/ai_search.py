# -*- coding: utf-8 -*-
"""Lucent AI Search: OpenRouter free model, verified S4Me global search and optional Kodi PVR EPG.

RunScript(special://skin/scripts/ai_search.py) opens the dialog.
RunScript(special://skin/scripts/ai_search.py,setupmenu) migrates only standard Search tabs.
No API key is embedded in the public skin or logged. Does not modify Stream4Me.
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import time

import xbmc
import xbmcgui
import xbmcvfs

sys.path.insert(0, os.path.dirname(__file__))
from ai_search_core import is_default_search, matches_live, parse_ai, stream4me_url
from ai_art_core import choose_record, catalogue_art, tmdb_art, normalize, metadata_label

API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "openrouter/free"
UI = "Lucent_AISearch.xml"
SKIN = xbmcvfs.translatePath("special://skin/")
KEY_DIR = xbmcvfs.translatePath("special://profile/addon_data/skin.lucent.ai/")
KEY_FILE = os.path.join(KEY_DIR, "settings.json")
MENU_ACTION = "RunScript(special://skin/scripts/ai_search.py)"
CLOSE = (9, 10, 13, 92, 216, 247)

def _rpc(method, params):
    raw = xbmc.executeJSONRPC(json.dumps({"jsonrpc": "2.0", "method": method, "params": params, "id": 1}))
    response = json.loads(raw)
    if response.get("error"):
        raise RuntimeError("Kodi JSON-RPC: " + str(response["error"].get("message", "error")))
    return response.get("result") or {}

def _settings():
    try:
        with open(KEY_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except (OSError, ValueError):
        return {}

def _save_key(key):
    os.makedirs(KEY_DIR, exist_ok=True)
    tmp = KEY_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as file:
        json.dump({"openrouter_key": key.strip()}, file)
    try:
        os.chmod(tmp, 0o600)
    except OSError:
        pass
    os.replace(tmp, KEY_FILE)

def _ai_request(prompt, key):
    system_prompt = (
        "Sei Lucent, esperto di film e serie TV. Rispondi in italiano con SOLO "
        "un oggetto JSON valido con chiavi message (breve testo) e titles (array "
        "di massimo 5 elementi). Ogni elemento ha title (nome esatto di un'opera "
        "reale), year (anno, se noto), type (movie o tvshow), reason (breve motivo). "
        "Per un titolo preciso restituisci quello. Per consigli proponi opere "
        "reali e pertinenti. Non inventare disponibilità su Stream4Me o in TV. "
        "Non includere link, comandi o altri campi."
    )
    last_reason = "empty"
    for attempt in range(2):
        # First use JSON-constrained routing; fall back to a simpler prompt if
        # the free provider does not support JSON mode or emits empty text.
        messages = [
            {"role": "system", "content": system_prompt if attempt == 0 else (
                "Consiglia fino a cinque film o serie reali in italiano. "
                "Rispondi SOLO con una lista numerata di titoli, uno per riga. "
                "Esempio: 1. Severance\n2. Dark\n3. Fallout. Non aggiungere link."
            )},
            {"role": "user", "content": prompt},
        ]
        data = {
            "model": MODEL, "messages": messages,
            "max_tokens": 1600 if attempt == 0 else 1100,
            "temperature": 0.25,
        }
        if attempt == 0:
            data["response_format"] = {"type": "json_object"}
            data["provider"] = {"require_parameters": True}
        request = urllib.request.Request(
            API_URL, data=json.dumps(data, ensure_ascii=False).encode("utf-8"),
            headers={"Authorization": "Bearer " + key, "Content-Type": "application/json",
                     "HTTP-Referer": "https://github.com/NoiSi78378/Lucent-ITA",
                     "X-Title": "Lucent AI Search"},
            method="POST")
        try:
            with urllib.request.urlopen(request, timeout=22) as reply:
                output = json.loads(reply.read(300000).decode("utf-8"))
        except urllib.error.HTTPError as error:
            if attempt == 0 and error.code in (400, 422):
                # A free provider may reject the structured-output parameter.
                last_reason = "format"
                continue
            if error.code == 429:
                raise RuntimeError("Modello gratuito occupato o limite OpenRouter raggiunto.") from None
            if error.code in (401, 403):
                raise RuntimeError("Chiave OpenRouter non valida o senza accesso.") from None
            if error.code == 402:
                raise RuntimeError("OpenRouter richiede credito o non consente questa richiesta.") from None
            raise RuntimeError("OpenRouter HTTP " + str(error.code)) from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise RuntimeError("OpenRouter non raggiungibile. Riprova o cerca direttamente.") from None

        if not isinstance(output, dict):
            last_reason = "invalid-response"
            continue
        if output.get("error"):
            # Do not expose remote error payloads, prompt, or API key in Kodi logs.
            raise RuntimeError("OpenRouter ha restituito un errore del servizio.")
        choices = output.get("choices") or []
        choice = choices[0] if isinstance(choices, list) and choices else {}
        if not isinstance(choice, dict):
            choice = {}
        message = choice.get("message") or {}
        if not isinstance(message, dict):
            message = {}
        try:
            rows, summary = parse_ai(message.get("content"))
            if rows:
                return rows, summary
            last_reason = "no-titles"
        except (ValueError, TypeError):
            last_reason = "unreadable"
        # Log metadata only: never include the response, user query or API key.
        xbmc.log("[skin.lucent] AI response attempt=%d result=%s finish=%s model=%s" % (
            attempt + 1, last_reason, str(choice.get("finish_reason") or "?")[:25],
            str(output.get("model") or "?")[:75]), xbmc.LOGWARNING)

    raise RuntimeError(
        "OpenRouter ha risposto senza titoli utilizzabili dopo due tentativi. "
        "Prova un'altra richiesta o un modello diverso."
    )



# Catalogue endpoints provide artwork only, never streaming availability.
# Kodi and TMDb are preferred; Cinemeta and TVmaze work without extra keys.
ART_CACHE = os.path.join(KEY_DIR, "art_cache.json")
ART_TTL = 14 * 86400
NO_ART_TTL = 24 * 3600


def _read_art_cache():
    try:
        with open(ART_CACHE, "r", encoding="utf-8") as handle:
            result = json.load(handle)
            return result if isinstance(result, dict) else {}
    except (OSError, ValueError):
        return {}


def _save_art_cache(cache):
    try:
        os.makedirs(KEY_DIR, exist_ok=True)
        now = time.time()
        fresh = {k: v for k, v in cache.items()
                 if isinstance(v, dict) and now - v.get("t", 0) < ART_TTL}
        fresh = dict(sorted(fresh.items(), key=lambda pair: pair[1].get("t", 0))[-350:])
        tmp = ART_CACHE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(fresh, handle, ensure_ascii=False)
        os.replace(tmp, ART_CACHE)
    except (OSError, ValueError, TypeError):
        xbmc.log("[skin.lucent] AI artwork cache unavailable", xbmc.LOGDEBUG)


def _json_art(url, timeout=3):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Lucent-ITA/AI-Search"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read(200000).decode("utf-8"))
    except (urllib.error.HTTPError, urllib.error.URLError, OSError, ValueError, TimeoutError):
        return {}


def _art_key():
    """Reuse the TMDb key of this skin; the OpenRouter key is unrelated."""
    for path in ("special://profile/addon_data/skin.lucent/tmdb_key.txt",
                 "special://profile/addon_data/skin.lucent.ita/tmdb_key.txt"):
        try:
            with xbmcvfs.File(path) as handle:
                value = (handle.read() or "").strip()
            if value:
                return value
        except (OSError, RuntimeError):
            pass
    return ""


def _local_art(row):
    """Use real Kodi library posters first, including Stream4Me library imports."""
    media_type = "TVShows" if row.get("kind") == "serie" else "Movies"
    method = "VideoLibrary.Get" + media_type
    result_key = "tvshows" if media_type == "TVShows" else "movies"
    try:
        entries = _rpc(method, {
            "filter": {"field": "title", "operator": "contains", "value": row["title"]},
            "properties": ["title", "year", "art"],
            "limits": {"start": 0, "end": 30}
        }).get(result_key) or []
        match = choose_record(entries, row["title"], row.get("year") or "")
        if match:
            art = match.get("art") or {}
            return {"poster": art.get("poster") or art.get("thumb") or "",
                    "backdrop": art.get("fanart") or "",
                    "year": str(match.get("year") or ""), "rating": ""}
    except (RuntimeError, ValueError, KeyError, TypeError):
        pass
    return {}


def _remote_art(row, tmdb_key):
    title = row["title"]
    types = ("tv", "movie") if row.get("kind") == "serie" else ("movie", "tv")
    for media in types:
        if tmdb_key:
            params = urllib.parse.urlencode(
                {"api_key": tmdb_key, "query": title, "language": "it-IT", "page": 1})
            data = _json_art("https://api.themoviedb.org/3/search/%s?%s" % (media, params))
            match = choose_record(data.get("results") or [], title, row.get("year"))
            if match:
                art = tmdb_art(match)
                if art.get("poster"):
                    return art
        kind = "series" if media == "tv" else "movie"
        encoded = urllib.parse.quote(title, safe="")
        data = _json_art("https://v3-cinemeta.strem.io/catalog/%s/top/search=%s.json" %
                         (kind, encoded))
        match = choose_record(data.get("metas") or [], title, row.get("year"))
        if match:
            art = catalogue_art(match, "cinemeta")
            if art.get("poster"):
                return art
        if media == "tv":
            data = _json_art("https://api.tvmaze.com/search/shows?q=" + encoded)
            match = choose_record(data if isinstance(data, list) else [],
                                  title, row.get("year"))
            if match:
                art = catalogue_art(match, "tvmaze")
                if art.get("poster"):
                    return art
    return {}


def _add_artwork(rows):
    """Enrich at most five recommendations, with negative cache and time budget."""
    if not rows:
        return rows
    cache = _read_art_cache()
    now = time.time()
    deadline = time.monotonic() + 21
    key = _art_key()
    changed = False
    for row in rows[:5]:
        if row.get("kind") == "live":
            continue
        lookup = row.get("kind", "") + "|" + normalize(row.get("title"))
        if not lookup.strip("|"):
            continue
        art = _local_art(row)
        if not art.get("poster"):
            cached = cache.get(lookup) or {}
            cached_art = cached.get("art") or {}
            ttl = ART_TTL if cached_art.get("poster") else NO_ART_TTL
            if now - cached.get("t", 0) < ttl:
                art = cached_art
            elif time.monotonic() < deadline:
                art = _remote_art(row, key)
                cache[lookup] = {"t": now, "art": art}
                changed = True
        if art.get("poster"):
            row["poster"] = art["poster"]
        if art.get("backdrop"):
            row["backdrop"] = art["backdrop"]
        if art.get("year"):
            row["year"] = art["year"]
        if art.get("rating"):
            row["rating"] = art["rating"]
    if changed:
        _save_art_cache(cache)
    return rows


def _live_epg(titles):
    """Read ONLY current Kodi PVR EPG, never infer live schedules from a model."""
    if not xbmc.getCondVisibility("Pvr.HasTVChannels"):
        return [], "Nessun canale PVR con EPG registrato in Kodi."
    try:
        groups = _rpc("PVR.GetChannelGroups", {"channeltype": "tv"}).get("channelgroups") or []
        if not groups:
            return [], "Nessun gruppo di canali PVR disponibile."
        group = next((x for x in groups if "tutti" in str(x.get("label","")).lower()
                      or "all channels" in str(x.get("label","")).lower()), groups[0])
        channels = _rpc("PVR.GetChannels", {
            "channelgroupid": int(group["channelgroupid"]),
            "properties": ["channel", "broadcastnow"],
            "limits": {"start": 0, "end": 300}
        }).get("channels") or []
        found = []
        for channel in channels:
            broadcast = channel.get("broadcastnow")
            if not isinstance(broadcast, dict):
                continue
            title = str(broadcast.get("title") or "").strip()
            for target in titles[:6]:
                if matches_live(target, title):
                    found.append({
                        "kind": "live", "title": title, "year": "",
                        "reason": "IN ONDA su " + str(channel.get("label") or channel.get("channel") or "TV"),
                        "channelid": int(channel["channelid"])})
                    break
        return found[:12], "" if found else "Nessuna corrispondenza nei programmi attualmente in onda dell'EPG Kodi."
    except (RuntimeError, TypeError, KeyError, ValueError) as error:
        xbmc.log("[skin.lucent] AI PVR metadata unavailable: " + type(error).__name__, xbmc.LOGINFO)
        return [], "EPG PVR non disponibile o non compatibile con questi canali."

def install_menu():
    """Migrate standard existing Search tabs once; never override custom menu actions."""
    if xbmc.getInfoLabel("Skin.String(lucent.ai.search.migrated)") == "1":
        return
    if not xbmc.getInfoLabel("Skin.String(nuvio.menu.version)"):
        return
    count = 0
    for index in range(1, 13):
        icon = xbmc.getInfoLabel("Skin.String(nuvio.tab%d.icon)" % index)
        action = xbmc.getInfoLabel("Skin.String(nuvio.tab%d.action)" % index)
        if is_default_search(icon, action):
            xbmc.executebuiltin('Skin.SetString(nuvio.tab%d.action,"%s")' % (index, MENU_ACTION), True)
            count += 1
    xbmc.executebuiltin("Skin.SetString(lucent.ai.search.migrated,1)", True)
    xbmc.log("[skin.lucent] AI search: migrated %d default search tabs" % count, xbmc.LOGINFO)

class SearchDialog(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self.prompt = ""
        self.rows = []
        self.pending = None

    def onInit(self):
        self.setProperty("ai.prompt", "Tocca per scrivere un titolo o una richiesta...")
        self.setProperty("ai.status", "Ricerca titoli gratuita, senza AI. Per i consigli configura OpenRouter.")
        self.getControl(50).reset()
        self.setFocusId(10)

    def _text(self):
        result = xbmcgui.Dialog().input("Cosa vuoi guardare?", defaultt=self.prompt,
                                        type=xbmcgui.INPUT_ALPHANUM).strip()
        if result:
            self.prompt = result[:250]
            self.setProperty("ai.prompt", self.prompt)
        return bool(self.prompt)

    def _key(self):
        key = xbmcgui.Dialog().input("Chiave API OpenRouter (salvata solo qui)",
                                     type=xbmcgui.INPUT_ALPHANUM,
                                     option=getattr(xbmcgui, "ALPHANUM_HIDE_INPUT", 0)).strip()
        if key:
            if not key.startswith("sk-or-"):
                xbmcgui.Dialog().ok("Lucent AI", "La chiave OpenRouter deve iniziare con sk-or-.")
                return
            try:
                _save_key(key)
            except OSError:
                xbmcgui.Dialog().ok("Lucent AI", "Non posso salvare la chiave nel profilo Kodi.")
                return
            self.setProperty("ai.status", "Chiave OpenRouter salvata sul dispositivo. Puoi chiedere consigli all'AI.")

    def _list(self, rows, status):
        self.rows = rows
        items = []
        for row in rows:
            live = row.get("kind") == "live"
            title = ("IN ONDA  ·  " if live else "") + row["title"]
            meta = metadata_label(row)
            detail = row.get("reason") or ("Cerca questo titolo in Stream4Me" if not live
                                           else "Trasmissione in diretta")
            item = xbmcgui.ListItem(title, meta, offscreen=True)
            icon = "special://skin/media/icons/tv.png" if live else "special://skin/media/icons/movies.png"
            poster = row.get("poster") or ""
            artwork = {"icon": icon}
            if poster:
                artwork.update({"poster": poster, "thumb": poster})
            if row.get("backdrop"):
                artwork["fanart"] = row["backdrop"]
            item.setArt(artwork)
            item.setProperty("reason", detail)
            item.setProperty("meta", meta)
            items.append(item)
        control = self.getControl(50)
        control.reset()
        if items:
            control.addItems(items)
            self.setFocusId(50)
        self.setProperty("ai.status", status)

    def _to_stream4me(self, title):
        if not xbmc.getCondVisibility("System.HasAddon(plugin.video.s4me)"):
            xbmcgui.Dialog().ok("Lucent AI", "Stream4Me non è installato o non è abilitato in Kodi.")
            return
        try:
            url = stream4me_url(title)
        except ValueError:
            return
        self.pending = ("search", url)
        self.close()

    def _search(self):
        if not self.prompt and not self._text():
            return
        self._to_stream4me(self.prompt)

    def _recommend(self):
        if not self.prompt and not self._text():
            return
        key = (_settings().get("openrouter_key") or "").strip()
        if not key:
            xbmcgui.Dialog().ok("Lucent AI", "Inserisci prima la chiave OpenRouter con il pulsante 'Chiave OpenRouter'.")
            return
        progress = xbmcgui.DialogProgressBG()
        progress.create("Lucent AI", "Sto preparando i suggerimenti...")
        try:
            rows, message = _ai_request(self.prompt, key)
            if not rows:
                self.setProperty("ai.status", "Nessun suggerimento. Riprova con un titolo o un genere più preciso.")
                return
            progress.update(65, "Lucent AI", "Recupero le locandine...")
            rows = _add_artwork(rows)
            live, _ = _live_epg([row["title"] for row in rows])
            self._list(live + rows, (message or "Suggerimenti AI") +
                       " · Seleziona un titolo per cercarlo davvero in Stream4Me.")
        except RuntimeError as error:
            self.setProperty("ai.status", str(error) + " Ricerca diretta sempre disponibile.")
        finally:
            progress.close()

    def _live(self):
        if not self.prompt and not self._text():
            return
        results, status = _live_epg([self.prompt])
        self._list(results, "TV in diretta: " + (status or "titoli verificati nell'EPG attuale."))

    def onClick(self, control_id):
        if control_id == 90:
            self.close()
        elif control_id == 10:
            self._text()
        elif control_id == 11:
            self._search()
        elif control_id == 12:
            self._recommend()
        elif control_id == 13:
            self._live()
        elif control_id == 14:
            self._key()
        elif control_id == 50:
            pos = self.getControl(50).getSelectedPosition()
            if 0 <= pos < len(self.rows):
                row = self.rows[pos]
                if row.get("kind") == "live":
                    self.pending = ("live", int(row["channelid"]))
                    self.close()
                else:
                    self._to_stream4me(row["title"])

    def onAction(self, action):
        if action.getId() in CLOSE:
            self.close()

def run():
    dialog = SearchDialog(UI, SKIN, "Default", "1080i")
    dialog.doModal()
    pending = dialog.pending
    del dialog
    if not pending:
        return
    kind, value = pending
    if kind == "search":
        # Close our dialog BEFORE calling S4Me; S4Me runs its own progress dialogs.
        xbmc.executebuiltin('ActivateWindow(Videos,"%s",return)' % value)
    elif kind == "live":
        try:
            _rpc("Player.Open", {"item": {"channelid": int(value)}})
        except (RuntimeError, ValueError) as error:
            xbmcgui.Dialog().ok("Lucent AI", "Impossibile aprire il canale TV: " + str(error))

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "setupmenu":
        install_menu()
    else:
        run()
