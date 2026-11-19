"""Regression checks for Lucent Home two-stage touch tab navigation."""
from pathlib import Path
import xml.etree.ElementTree as ET
root = Path(__file__).resolve().parent.parent
home = ET.parse(root / "xml/Home.xml").getroot()
inc = ET.parse(root / "xml/Includes.xml").getroot()
original = ET.parse(root / "xml/Includes_Home.xml").getroot()
touch = ET.parse(root / "xml/Includes_HomeMenu_Touch.xml").getroot()
assert any(x.get("file") == "Includes_HomeMenu_Touch.xml" for x in inc.findall("include"))
oldmenu = original.find("./include[@name='HomeMenuItems']")
newmenu = touch.find("./include[@name='HomeMenuItemsTouch']")
assert oldmenu is not None and newmenu is not None
olds, news = oldmenu.findall("item"), newmenu.findall("item")
assert len(olds) == len(news) == 13
for old, new in zip(olds, news):
    assert [(x.tag, x.attrib, x.text) for x in old if x.tag != "onclick"] == [(x.tag, x.attrib, x.text) for x in new if x.tag != "onclick"]
    clicks = new.findall("onclick")
    assert len(clicks) == 5
    assert clicks[0].get("condition") == "!Skin.HasSetting(lucent.touch)"
    assert "lucent.touch.menu.open" in clicks[1].get("condition", "")
    assert clicks[2].text == "SetProperty(lucent.touch.menu.open,1,home)"
    assert clicks[3].text == "SetFocus(9088)"
    assert "lucent.touch.menu.last" in clicks[4].text
assert home.find(".//control[@id='9000']/onunfocus") is not None
assert home.find(".//control[@id='9000']/content/include").text == "HomeMenuItemsTouch"
assert len(home.findall(".//control[@id='9088']/onclick")) == 2
assert "Skin.HasSetting(lucent.touch)" in home.find(".//control[@id='9000']/onunfocus").get("condition","")
print("Lucent Home touch: 12 tabs + kids; select, expand, activate; remote unaffected")
