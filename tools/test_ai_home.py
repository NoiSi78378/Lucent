"""Offline source and XML regression checks for the native Lucent Home search."""
import ast
import xml.etree.ElementTree as ET
from pathlib import Path

root=Path(__file__).resolve().parent.parent
source=(root/"scripts/ai_home.py").read_text(encoding="utf-8")
ast.parse(source)
home=(root/"xml/Home.xml").read_text(encoding="utf-8")
panel=(root/"xml/Includes_Lucent_AISearch_Home.xml").read_text(encoding="utf-8")
includes=(root/"xml/Includes.xml").read_text(encoding="utf-8")
settings=(root/"xml/SkinSettings.xml").read_text(encoding="utf-8")
menu=(root/"scripts/menu.py").read_text(encoding="utf-8")
migrator=(root/"scripts/ai_search.py").read_text(encoding="utf-8")
ET.parse(root/"xml/Home.xml")
ET.parse(root/"xml/Includes.xml")
ui=ET.parse(root/"xml/Includes_Lucent_AISearch_Home.xml")
ET.parse(root/"xml/SkinSettings.xml")
assert "Includes_Lucent_AISearch_Home.xml" in includes
assert "<include>LucentAISearchHome</include>" in home
assert "String.IsEqual(Container(9000).ListItem.Icon,icons/search.png)" in home
assert "RunScript(special://skin/scripts/ai_home.py,refresh)" in home
assert 'tab("t_search", "search", "SetFocus(9500)")' in menu
assert "lucent.ai.inline.migrated" in migrator and "SetFocus(9500)" in migrator
assert "RunScript(special://skin/scripts/ai_home.py,key)" in settings
assert "OpenRouter" in settings
assert "RunScript(special://skin/scripts/ai_home.py,input)" in panel
assert "mask_landscape.png" in panel
assert "mask_poster.png" in panel
assert "Window(home).Property(ai.home.mode)" in panel
assert "<visible>!String.IsEqual(Window(home).Property(ai.home.mode),results)</visible>" in panel
assert "<visible>String.IsEqual(Window(home).Property(ai.home.mode),results)</visible>" in panel
controls=[c for c in ui.iter("control") if c.get("id")]
ids=[int(c.get("id")) for c in controls]
assert len(ids)==len(set(ids)),[x for x in ids if ids.count(x)>1]
assert set(range(9511,9516)).issubset(ids)
assert set(range(9521,9526)).issubset(ids)
assert set(range(9531,9536)).issubset(ids)
assert 9500 in ids
assert all("open,%s,%s" % (src,i) in panel for src in ("pop","new","result") for i in range(1,6))
assert "def _run_query(prompt):" in source and "_ai_request(prompt, key, intent)" in source
assert "rows = _add_artwork(verified + suggestions, intent)" in source
assert 'ActivateWindow(Videos,"%s",return)' in source
assert "https://v3-cinemeta.strem.io/catalog/movie/year/genre=%d.json" in source
assert "https://api.themoviedb.org/3/trending/all/week?" in source
assert "def set_key():" in source and "_save_key(value)" in source
assert source.count("SLOTS = 5")==1
print("Lucent AI Home: XML, menu focus, Enter-to-AI, artwork rows, key settings verified")
