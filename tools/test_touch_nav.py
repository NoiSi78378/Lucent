"""Static UI regression: logo touch target and contextual Back controls."""
from pathlib import Path
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parent.parent
read = lambda name: ET.parse(root / "xml" / name).getroot()
home, includes, touch = read("Home.xml"), read("Includes.xml"), read("Includes_Touch.xml")
assert any(x.get("file") == "Includes_Touch.xml" for x in includes.findall("include"))
logo = home.find(".//control[@id='9088']")
assert logo is not None
assert logo.findtext("texturefocus", "missing") == ""
assert logo.findtext("texturenofocus", "missing") == ""
assert [a.text for a in logo.findall("onclick")] == ["SetProperty(lucent.touch.menu.open,1,home)", "SetFocus(9000)"]
assert "Skin.HasSetting(lucent.touch)" in logo.findtext("visible", "")
assert "icons/list.png" not in (ET.tostring(home, encoding="unicode").split('id="9088"')[-1].split('<include>ClockWeather</include>')[0])
nav = touch.find("./include[@name='LucentTouchNavigation']")
assert nav is not None
button = nav.find(".//control[@id='9087']")
assert button is not None and button.findtext("onclick") == "Action(Back)"
assert int(button.findtext("width")) >= 72 and int(button.findtext("height")) >= 72
assert "Skin.HasSetting(lucent.touch)" in nav.find(".//control[@type='group']").findtext("visible","")
standard = ["Settings.xml", "SkinSettings.xml", "SettingsCategory.xml", "SettingsSystemInfo.xml", "SettingsProfile.xml",
    "DialogVideoInfo.xml", "DialogAddonInfo.xml", "DialogAddonSettings.xml", "MyPVRChannels.xml", "MyPVRGuide.xml",
    "MyPVRProviders.xml", "MyPVRRecordings.xml", "MyPVRSearch.xml", "MyPVRTimers.xml", "FileManager.xml", "EventLog.xml",
    "Lucent_Agenda.xml", "Lucent_Sport.xml"]
modal = ["DialogSelect.xml", "DialogButtonMenu.xml", "DialogTextViewer.xml"]
for name in standard + modal:
    rootwindow = read(name)
    assert any(x.get("content") == "LucentTouchNavigation" for x in rootwindow.iter("include")), name
    ids = [i.get("id") for i in rootwindow.iter("control") if i.get("id")]
    assert "9087" not in ids, "id collision: " + name
print(f"Touch navigation: logo transparent; {len(standard)} screens + {len(modal)} dialogs audited")
