# -*- coding: utf-8 -*-
"""Lucent navigation: automatic touch detection and manual override.

Skin.String(lucent.touch.mode) is auto, touch or remote.
Skin.HasSetting(lucent.touch) is the effective UI state for existing XML.
"""
import glob
import os
import subprocess

import xbmc
import xbmcgui

MODES = ("auto", "touch", "remote")
LABELS = {
    "it": ("Automatico", "Touch (telefono, tablet o PC)", "Telecomando / tastiera"),
    "nl": ("Automatisch", "Touch (telefoon, tablet of pc)", "Afstandsbediening / toetsenbord"),
    "en": ("Automatic", "Touch (phone, tablet or PC)", "Remote / keyboard"),
}
HEADINGS = {"it": "Modalità di navigazione", "nl": "Navigatiemodus", "en": "Navigation mode"}
DETECTED = {
    "it": ("touch rilevato", "telecomando rilevato"),
    "nl": ("touch gedetecteerd", "afstandsbediening gedetecteerd"),
    "en": ("touch detected", "remote detected"),
}


def lang():
    value = xbmc.getLanguage(xbmc.ISO_639_1).lower()
    return value if value in LABELS else "en"


def mode():
    value = xbmc.getInfoLabel("Skin.String(lucent.touch.mode)").lower().strip()
    return value if value in MODES else "auto"


def android_classify(kind, files):
    """Android TV / Leanback always wins over touch-capable hardware flags."""
    parts = set(kind.lower().replace(" ", "").split(","))
    tv = bool(parts & {"tv", "leanback"}) or bool(files & {
        "tv_core_hardware.xml", "android.software.leanback.xml", "android.software.leanback_only.xml"})
    handheld = bool(parts & {"phone", "tablet", "handheld"}) or bool(files & {
        "handheld_core_hardware.xml", "tablet_core_hardware.xml",
        "android.hardware.touchscreen.xml", "android.hardware.touchscreen.multitouch.xml"})
    return handheld and not tv


def windows_touch(flags):
    """Windows SM_DIGITIZER: READY plus integrated/external touch hardware."""
    return bool(flags & 0x80 and flags & 0x03)


def detect():
    cond = xbmc.getCondVisibility
    if cond("System.Platform.IOS"):
        return True, "iOS"
    if cond("System.Platform.TVOS"):
        return False, "tvOS"
    if cond("System.Platform.Android"):
        kind = ""
        for exe in ("/system/bin/getprop", "getprop"):
            try:
                result = subprocess.run([exe, "ro.build.characteristics"],
                                        capture_output=True, text=True, timeout=2)
                kind = result.stdout.strip().lower()
                if kind:
                    break
            except (OSError, subprocess.TimeoutExpired):
                continue
        files = set()
        for partition in ("/system", "/vendor", "/product", "/odm", "/system_ext"):
            try:
                files.update(os.listdir(partition + "/etc/permissions"))
            except OSError:
                pass
        return android_classify(kind, files), "Android kind=%s files=%s" % (kind or "-", len(files))
    if cond("System.Platform.Windows") or cond("System.Platform.UWP"):
        try:
            import ctypes
            flags = ctypes.windll.user32.GetSystemMetrics(94)
            return windows_touch(flags), "Windows digitizer=%s" % flags
        except (AttributeError, OSError, ValueError):
            return False, "Windows digitizer unavailable"
    if cond("System.Platform.Linux"):
        for path in glob.glob("/sys/class/input/event*/device/name"):
            try:
                with open(path, encoding="utf-8", errors="ignore") as file:
                    name = file.read().lower()
                if "touchscreen" in name or "touch screen" in name:
                    return True, "Linux touchscreen"
            except OSError:
                continue
        return False, "Linux no touchscreen"
    return False, "desktop/unknown"


def apply():
    chosen = mode()
    active, reason = detect() if chosen == "auto" else (chosen == "touch", "manual override")
    current = bool(xbmc.getCondVisibility("Skin.HasSetting(lucent.touch)"))
    if current != active:
        xbmc.executebuiltin("Skin.SetBool(lucent.touch)" if active else "Skin.Reset(lucent.touch)", True)
    xbmc.log("[skin.lucent] touch mode=%s active=%s (%s)" % (chosen, active, reason), xbmc.LOGINFO)
    return active


def label():
    chosen = mode()
    language = lang()
    result = LABELS[language][MODES.index(chosen)]
    if chosen == "auto":
        detected = bool(xbmc.getCondVisibility("Skin.HasSetting(lucent.touch)"))
        result += " · " + DETECTED[language][0 if detected else 1]
    return result


def pick():
    language = lang()
    choice = xbmcgui.Dialog().select(HEADINGS[language], list(LABELS[language]),
                                    preselect=MODES.index(mode()))
    if choice < 0:
        return
    chosen = MODES[choice]
    if mode() != chosen:
        xbmc.executebuiltin('Skin.SetString(lucent.touch.mode,"%s")' % chosen, True)
    apply()
    value = label()
    if xbmc.getInfoLabel("Skin.String(lucent.touch.mode.label)") != value:
        xbmc.executebuiltin('Skin.SetString(lucent.touch.mode.label,"%s")' % value, True)
