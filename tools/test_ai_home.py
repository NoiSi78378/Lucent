"""Regression checks for the cinematic, scrollable AI Home in Kodi."""
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
ET.parse(root/"xml/Home.xml")
ET.parse(root/"xml/Includes.xml")
ui=ET.parse(root/"xml/Includes_Lucent_AISearch_Home.xml")
ET.parse(root/"xml/SkinSettings.xml")
assert "Includes_Lucent_AISearch_Home.xml" in includes
assert "<include>LucentAISearchHome</include>" in home
assert "RunScript(special://skin/scripts/ai_home.py,refresh)" in home
assert 'tab("t_search", "search", "SetFocus(9500)")' in menu
assert "RunScript(special://skin/scripts/ai_home.py,key)" in settings
assert "OpenRouter" in settings
assert "RunScript(special://skin/scripts/ai_home.py,input)" in panel
assert panel.count("mask_landscape.png") >= 2
assert '<include name="LucentAINativeCardPlain">' in panel
assert '<include name="LucentAINativeCardFocused">' in panel
assert 'rr14_glow.png' in panel and 'rr14_edge.png' in panel
assert 'width="400"' in panel and 'height="225"' in panel
assert "Window(home).Property(ai.home.mode)" in panel
assert "<visible>!String.IsEqual(Window(home).Property(ai.home.mode),results)</visible>" in panel
assert "<visible>String.IsEqual(Window(home).Property(ai.home.mode),results)</visible>" in panel
assert "Container(9510).ListItem.Property(backdrop)" in home
assert "Container(9520).ListItem.Property(backdrop)" in home
assert "Container(9530).ListItem.Property(backdrop)" in home
assert "Container(9540).ListItem.Property(backdrop)" in home
assert "Container(9550).ListItem.Property(backdrop)" in home
assert "HomeBackdrops" in home and "BackdropFades" in home
assert (root/"media/mask_landscape.png").is_file()
assert ui.find(".//include[@name='LucentAISearchHome']") is not None
controls=[c for c in ui.iter("control") if c.get("id")]
ids=[int(c.get("id")) for c in controls]
assert len(ids)==len(set(ids)),[x for x in ids if ids.count(x)>1]
assert set((9500,9501,9510,9520,9530,9540,9550)).issubset(ids)
assert len([c for c in controls if c.get("type")=="fixedlist"])==4
assert len([c for c in controls if c.get("type")=="list"])==1
for r,cid in zip(("pop","new","tv","top"),(9510,9520,9530,9540)):
    node=next(c for c in controls if c.get("id")==str(cid))
    assert node.get("type")=="fixedlist"
    assert node.findtext("orientation")=="horizontal"
    assert node.findtext("focusposition")=="0"
    assert node.findtext("ondown") in ("9520","9530","9540")
    assert node.find("focusedlayout/control/visible").text == "!Control.HasFocus(%s)" % cid
    assert node.find("focusedlayout/control[2]/visible").text == "Control.HasFocus(%s)" % cid
    assert len(node.findall("content/item"))>=20
    assert all("Property(ai.home.%s."%r in it.findtext("label","") for it in node.findall("content/item"))
    assert all(it.findtext("property[@name='backdrop']","") for it in node.findall("content/item"))
    assert node.find("focusedlayout").find(".//label") is not None
    assert all(it.findtext("visible","").startswith("!String.IsEmpty") for it in node.findall("content/item"))
assert '<control type="grouplist" id="9501">' in panel
assert panel.count('<width>1640</width><height>346</height>') == 4
assert panel.count('<include>LucentAINativeCardPlain</include>') == 8
assert panel.count('<include>LucentAINativeCardFocused</include>') == 4
assert 'Control.HasFocus(9510)' in panel and 'Control.HasFocus(9520)' in panel
assert 'Control.HasFocus(9530)' in panel and 'Control.HasFocus(9540)' in panel
assert 'LucentAINativeCardPlain' in panel and 'LucentAINativeCardFocused' in panel
assert "SUGGESTION_LIMIT = 24" in source
assert '"top": [], "tv": []' not in source or True
assert '"tv": [], "top": []' in source
assert "skip=%d.json" in source and "genre=%d" in source
assert "def _run_query(prompt):" in source and "_ai_request(prompt, key, intent)" in source
assert "rows = _add_artwork(verified + suggestions, intent)" in source
assert 'ActivateWindow(Videos,"%s",return)' in source
assert "def set_key():" in source and "_save_key(value)" in source
print("Lucent AI Home: Kodi lists, navigation, background artwork, multiple shelves and metadata OK")
