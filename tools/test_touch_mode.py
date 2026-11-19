# -*- coding: utf-8 -*-
"""Regression tests for Lucent Auto / Touch / Remote (run without Kodi)."""
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

state = {"mode": "auto", "touch": False}
writes = []

def cond(name):
    return state["touch"] if name == "Skin.HasSetting(lucent.touch)" else False

def execute(command, wait=False):
    writes.append(command)
    if command == "Skin.SetBool(lucent.touch)":
        state["touch"] = True
    if command == "Skin.Reset(lucent.touch)":
        state["touch"] = False

sys.modules["xbmc"] = SimpleNamespace(
    getCondVisibility=cond,
    getInfoLabel=lambda name: state["mode"] if name == "Skin.String(lucent.touch.mode)" else "",
    getLanguage=lambda *args: "it",
    ISO_639_1=1,
    executebuiltin=execute,
    log=lambda *args: None,
    LOGINFO=0,
)
sys.modules["xbmcgui"] = SimpleNamespace(Dialog=lambda: None)
path = Path(__file__).resolve().parents[1] / "scripts" / "touchmode.py"
spec = importlib.util.spec_from_file_location("touchmode", path)
touchmode = importlib.util.module_from_spec(spec)
spec.loader.exec_module(touchmode)

assert touchmode.android_classify("phone", set())
assert touchmode.android_classify("tablet", set())
assert touchmode.android_classify("", {"handheld_core_hardware.xml"})
assert touchmode.android_classify("", {"android.hardware.touchscreen.xml"})
assert not touchmode.android_classify("tv", set())
assert not touchmode.android_classify("phone,tv", set())
assert not touchmode.android_classify("", {"android.software.leanback.xml", "android.hardware.touchscreen.xml"})
assert not touchmode.android_classify("", set())
assert touchmode.windows_touch(0x81)
assert touchmode.windows_touch(0x82)
assert not touchmode.windows_touch(0x01)
assert not touchmode.windows_touch(0x80)

touchmode.detect = lambda: (True, "touchscreen simulated")
assert touchmode.apply()
assert state["touch"]
assert writes[-1] == "Skin.SetBool(lucent.touch)"
state["mode"] = "remote"
assert not touchmode.apply()
assert not state["touch"]
state["mode"] = "touch"
assert touchmode.apply()
assert state["touch"]
touchmode.detect = lambda: (False, "TV simulated")
state["mode"] = "auto"
assert not touchmode.apply()
assert not state["touch"]
assert "Automatico" in touchmode.label()
print("Touch-mode regressions OK: Android TV priority, PC touch capability, persistent override")
