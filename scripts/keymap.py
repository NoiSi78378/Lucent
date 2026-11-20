# -*- coding: utf-8 -*-
"""Lucent: the Back button stops the video while you are watching.

Kodi skins cannot change what Back does in the full screen player, so this writes a small keymap
(special://profile/keymaps/lucent-back-stop.xml) and asks Kodi to reload its keymaps. It only
changes the full screen video; menus, the OSD and the pause screen keep their normal Back.
(Until 1.31.27 this file also made the Enter key finish the on-screen keyboard. Many remotes - CoreELEC especially -
send their OK button as the Enter key, so OK on a letter closed the keyboard. That part is gone; the file is rewritten.)
Set Skin.String(nuvio.backstop) to "off" (or delete the file) to get the old behaviour back.
Runs from the Home screen; it does nothing when the file is already right.
"""
import xbmc
import xbmcvfs

DIR = "special://profile/keymaps/"
PATH = DIR + "lucent-back-stop.xml"
KEYMAP = """<keymap>
    <FullscreenVideo>
        <keyboard>
            <backspace>RunScript(special://skin/scripts/fsback.py)</backspace>
            <escape>RunScript(special://skin/scripts/fsback.py)</escape>
            <browser_back>RunScript(special://skin/scripts/fsback.py)</browser_back>
        </keyboard>
        <remote>
            <back>RunScript(special://skin/scripts/fsback.py)</back>
        </remote>
    </FullscreenVideo>
</keymap>
"""


def log(text):
    xbmc.log(f"[skin.lucent] keymap: {text}", xbmc.LOGINFO)


def current():
    if not xbmcvfs.exists(PATH):
        return None
    with xbmcvfs.File(PATH) as fh:
        return fh.read()


OK_PATH = DIR + "lucent-ok-page.xml"
OK_KEYMAP = """<keymap>
    <videos>   <!-- Kodi's keymap name for MyVideoNav.xml (the video lists); "MyVideoNav" itself is not recognised -->
        <!-- holding OK still opens the context menu: once a key is mapped here, Kodi ignores the global long press -->
        <keyboard>
            <return>RunScript(special://skin/scripts/openitem.py)</return>
            <return mod="longpress">ContextMenu</return>
            <enter>RunScript(special://skin/scripts/openitem.py)</enter>
            <enter mod="longpress">ContextMenu</enter>
        </keyboard>
        <remote>
            <select>RunScript(special://skin/scripts/openitem.py)</select>
            <select mod="longpress">ContextMenu</select>
        </remote>
    </videos>
</keymap>
"""


HOME_PATH = DIR + "lucent-home.xml"
BTN = "ActivateWindow(Home)"
def _home_keymap():
    body = (
        "        <keyboard>\n"
        "            <browser_home>%(b)s</browser_home>\n"
        "            <home>%(b)s</home>\n"
        "            <homepage>%(b)s</homepage>\n"
        "        </keyboard>\n"
        "        <remote>\n"
        "            <start>%(b)s</start>\n"
        "            <rootmenu>%(b)s</rootmenu>\n"
        "        </remote>\n"
    ) % {"b": BTN}
    out = "<keymap>\n"
    # the info page (movieinformation) and the players have their own sections in Kodi's keymaps, so they are named too
    # (not in <global>: there the Home key of a keyboard stays "first item of the list")
    for win in ("MovieInformation", "FullscreenVideo", "VideoOSD", "SeekBar", "VideoMenu"):
        out += "    <%s>\n%s    </%s>\n" % (win, body, win)
    out += "    <global>\n%s    </global>\n" % body.replace("            <home>%s</home>\n" % BTN, "")
    return out + "</keymap>\n"


HOME_KEYMAP = _home_keymap()

# Touch screens (phones, tablets): Kodi only passes a touch to a Home row that is completely on screen, so rows that peek
# in at the bottom cannot be touched. A quick swipe up / down moves to the next / previous row instead; that row then
# scrolls fully into view and can be touched. Switch off: Skin.String(lucent.touchswipe) = off.
TOUCH_PATH = DIR + "lucent-touch.xml"
TOUCH_KEYMAP = """<keymap>
    <Home>
        <touch>
            <swipe direction="up">Down</swipe>
            <swipe direction="down">Up</swipe>
        </touch>
    </Home>
</keymap>
"""


# FullscreenLiveTV is a separate input context. Preserve film mappings.
PVR_PATH = DIR + "lucent-pvr-navigation.xml"

def pvr_keymap(backstop=True):
    back = "RunScript(special://skin/scripts/fsback.py)" if backstop else "Back"
    return """<keymap>
    <FullscreenLiveTV>
        <keyboard>
            <backspace>{back}</backspace>
            <escape>{back}</escape>
            <browser_back>{back}</browser_back>
            <up>ChannelUp</up>
            <down>ChannelDown</down>
            <pageup>ChannelUp</pageup>
            <pagedown>ChannelDown</pagedown>
            <return>OSD</return>
            <enter>OSD</enter>
        </keyboard>
        <remote>
            <back>{back}</back>
            <up>ChannelUp</up>
            <down>ChannelDown</down>
            <pageplus>ChannelUp</pageplus>
            <pageminus>ChannelDown</pageminus>
            <select>OSD</select>
        </remote>
    </FullscreenLiveTV>
</keymap>
""".format(back=back)


# Separate, reversible overlay. No ordinary Back, OK or channel mappings are
# rewritten. Android BACK is translated to backspace; other remotes may send
# browser_back or a remote back event. Kodi tries a window's short action
# before a global long action, so list the relevant native windows explicitly.
VOICE_PATH = DIR + "lucent-voice.xml"
VOICE_ACTION = "RunScript(special://skin/scripts/ai_voice.py)"
VOICE_WINDOWS = (
    "global","Home","Videos","VideoPlaylist","MovieInformation","Music",
    "MusicPlaylist","MusicPlaylistEditor","MusicInformation","Pictures",
    "PictureInfo","FavouritesBrowser","Programs","Addon","AddonInformation",
    "Settings","PlayerSettings","MediaSettings","SystemSettings",
    "ServiceSettings","InterfaceSettings","Profiles","SystemInfo","Weather",
    "FileManager","TVChannels","TVGuide","TVRecordings","TVTimers","TVSearch",
    "RadioChannels","RadioGuide","RadioRecordings","RadioTimers",
    "FullscreenVideo","FullscreenLiveTV","FullscreenRadio","VideoOSD",
    "FullscreenInfo","SeekBar","PVROSDChannels","PVRChannelGuide","VideoMenu",
)

def voice_keymap(mode="back"):
    if mode not in ("back","keyboard"):
        return "<keymap/>"
    lines=["<keymap>"]
    for win in VOICE_WINDOWS:
        lines.append("    <"+win+">")
        if mode=="back":
            lines.append("        <keyboard>")
            for key in ("backspace","browser_back"):
                lines.append('            <'+key+' mod="longpress">'+VOICE_ACTION+'</'+key+'>')
            if win in ("FullscreenVideo","FullscreenLiveTV","FullscreenRadio","VideoOSD","FullscreenInfo","SeekBar","VideoMenu"):
                lines.append('            <escape mod="longpress">'+VOICE_ACTION+'</escape>')
            lines.extend(["        </keyboard>","        <remote>",
                          '            <back mod="longpress">'+VOICE_ACTION+'</back>',
                          "        </remote>"])
        else:
            lines.extend(["        <keyboard>",'            <f12 mod="ctrl,alt">'+VOICE_ACTION+'</f12>',"        </keyboard>"])
        lines.append("    </"+win+">")
    # Never intercept Back or OK inside a text field / password / numeric input.
    # Explicit noop disables global long-press detection for those keys;
    # browser_back retains Kodi's stock keyboard escape on long press.
    if mode=="back":
        lines.extend(['    <VirtualKeyboard><keyboard>',
            '        <backspace mod="longpress">noop</backspace>',
            '        <browser_back mod="longpress">PreviousMenu</browser_back>',
            '        <escape mod="longpress">Back</escape>',
            '    </keyboard><remote><back mod="longpress">noop</back></remote></VirtualKeyboard>',
            '    <NumericInput><keyboard>',
            '        <backspace mod="longpress">noop</backspace>',
            '        <browser_back mod="longpress">noop</browser_back>',
            '    </keyboard><remote><back mod="longpress">noop</back></remote></NumericInput>'])
    return "\n".join(lines+["</keymap>",""])


def read(path):
    if not xbmcvfs.exists(path):
        return None
    with xbmcvfs.File(path) as fh:
        return fh.read()


def sync(path, text, wanted):
    """Make the keymap file exist with this text (wanted) or not exist. True when something changed."""
    have = read(path)
    if wanted and have != text:
        xbmcvfs.mkdirs(DIR)
        with xbmcvfs.File(path, "w") as fh:
            fh.write(text)
        return True
    if not wanted and have is not None:
        xbmcvfs.delete(path)
        return True
    return False


def main():
    backstop = xbmc.getInfoLabel("Skin.String(nuvio.backstop)") != "off"
    changed = sync(PATH, KEYMAP, backstop)
    changed = sync(PVR_PATH, pvr_keymap(backstop), True) or changed
    voice_mode = xbmc.getInfoLabel("Skin.String(lucent.voice.key)") or "back"
    changed = sync(VOICE_PATH, voice_keymap(voice_mode), voice_mode in ("back","keyboard")) or changed
    # OK opens the page first for films / episodes in the Kodi video lists (add-on folders): only when chosen in Skin settings
    ok_wanted = xbmc.getCondVisibility("Skin.HasSetting(nuvio.ok.movie.page) | Skin.HasSetting(nuvio.ok.episode.page)")
    changed = sync(OK_PATH, OK_KEYMAP, ok_wanted) or changed
    # the Home button of the remote goes to the Home screen from every window (switch off: Skin.String(nuvio.homekey) = off)
    changed = sync(HOME_PATH, HOME_KEYMAP, xbmc.getInfoLabel("Skin.String(nuvio.homekey)") != "off") or changed
    changed = sync(TOUCH_PATH, TOUCH_KEYMAP, xbmc.getInfoLabel("Skin.String(lucent.touchswipe)") != "off") or changed
    if changed:
        xbmc.executebuiltin("Action(reloadkeymaps)")
        log("keymaps updated")
    xbmc.executebuiltin("SetProperty(lucent.pvr.keys.v1,1,home)")
    xbmc.executebuiltin("SetProperty(lucent.voice.keys.v1,1,home)")


if __name__ == "__main__":
    main()
