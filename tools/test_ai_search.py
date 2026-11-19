"""Offline contract/regression tests for Lucent AI Search (no Kodi installation required)."""
import os
import sys
import json
import xml.etree.ElementTree as ET
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from ai_search_core import stream4me_url, parse_ai, matches_live, is_default_search
r = Path(__file__).resolve().parent.parent
u = stream4me_url("Silo & MobLand, 2025")
assert u == "plugin://plugin.video.s4me/?channel=search&action=new_search&mode=all&search_text=Silo%20%26%20MobLand%2C%202025"
assert "search_text=" in u and "channel=search&action=new_search&mode=all" in u
for q in ("", "   ", "x"*300):
    try: stream4me_url(q); raise AssertionError("invalid title accepted")
    except ValueError: pass
rows, message = parse_ai('z ```json\n{"message":"Ecco","titles":[{"title":"John Wick","year":2014,"type":"movie","reason":"Azione"},{"title":"Silo","type":"tvshow"},{"title":"Silo"}]}\n``` z')
assert len(rows) == 2 and rows[1]["kind"] == "serie" and rows[0]["year"] == "2014"
assert message == "Ecco"
assert rows[0]["title"] == "John Wick" and rows[1]["title"] == "Silo"
assert matches_live("Il padrino", "Il Padrino (film)") and not matches_live("azione", "Film d'azione")
assert is_default_search("icons/search.png","VideoLibrary.Search")
assert not is_default_search("icons/search.png","ActivateWindow(Settings)")
ui = ET.parse(r / "xml/Lucent_AISearch.xml").getroot()
ids = {int(c.get("id")):c for c in ui.iter("control") if c.get("id")}
assert {10,11,12,13,14,50,90}.issubset(ids)
assert int(ids[10].findtext("height")) >= 72
menu = (r / "scripts/menu.py").read_text(encoding="utf-8")
assert menu.count("RunScript(special://skin/scripts/ai_search.py)") >= 2
startup = (r / "scripts/startup.py").read_text(encoding="utf-8")
assert 'ai_search.install_menu' in startup
home_source = (r / "xml/Home.xml").read_text(encoding="utf-8")
assert "ai_search.py,setupmenu" in home_source
print("Lucent AI: verified Stream4Me route, URL encoding, JSON parsing, EPG title matching, UI and menu")
