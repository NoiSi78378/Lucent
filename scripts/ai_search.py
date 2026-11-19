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
import urllib.request

import xbmc
import xbmcgui
import xbmcvfs

sys.path.insert(0, os.path.dirname(__file__))
from ai_search_core import is_default_search, matches_live, parse_ai, stream4me_url

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
    data = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": (
                "Sei Lucent, consulente di film e serie TV. Rispondi SEMPRE in italiano e SOLO "
                "con JSON valido: {\"message\":\"breve spiegazione\","
                "\"titles\":[{\"title\":\"titolo reale\",\"year\":2024,"
                "\"type\":\"movie o tvshow\",\"reason\":\"perché consigliarlo\"}]}. "
                "Se la persona chiede un titolo preciso, restituisci quel titolo. Se chiede "
                "consigli, suggerisci al massimo 5 titoli di opere realmente esistenti, senza "
                "inventare date o disponibilità. NON affermare mai di aver verificato "
                "Stream4Me, siti streaming o programmi TV. NON includere URL o comandi."
            )},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 700, "temperature": 0.35
    }
    request = urllib.request.Request(
        API_URL, data=json.dumps(data, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json",
                 "HTTP-Referer": "https://github.com/NoiSi78378/Lucent-ITA",
                 "X-Title": "Lucent AI Search"},
        method="POST")
    try:
        with urllib.request.urlopen(request, timeout=19) as reply:
            output = json.loads(reply.read(300000).decode("utf-8"))
    except urllib.error.HTTPError as error:
        if error.code == 429:
            raise RuntimeError("Modello gratuito occupato o limite OpenRouter raggiunto.") from None
        if error.code in (401, 403):
            raise RuntimeError("Chiave OpenRouter non valida o senza accesso.") from None
        raise RuntimeError("OpenRouter HTTP " + str(error.code)) from None
    except (urllib.error.URLError, TimeoutError):
        raise RuntimeError("OpenRouter non raggiungibile. Riprova o cerca direttamente.") from None
    try:
        content = output["choices"][0]["message"]["content"]
        return parse_ai(content)
    except (KeyError, IndexError, TypeError, ValueError):
        raise RuntimeError("Il modello non ha restituito titoli leggibili. Riprova.") from None

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
            label2 = row.get("reason") or ("Da cercare in Stream4Me · " + row.get("kind","film"))
            if not live and row.get("year"):
                label2 = str(row["year"]) + "  ·  " + label2
            item = xbmcgui.ListItem(title, label2, offscreen=True)
            item.setArt({"icon": "special://skin/media/icons/tv.png" if live else "special://skin/media/icons/movies.png"})
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
