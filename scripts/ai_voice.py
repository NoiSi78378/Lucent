# -*- coding: utf-8 -*-
"""Global Lucent input using Kodi's own keyboard and Android speech service.

No Android permissions, key injection, external app, playback focus or audio
changes. A request is sent only when the user confirms native keyboard input.
"""
import sys
import time
import xbmc
import xbmcgui

BUSY = "lucent.voice.busy"
ARM = "lucent.voice.arm"
KEYBOARD = 10103

def listen(home):
    """One shot, scoped to the keyboard opened by this invocation."""
    ticket=home.getProperty(ARM)
    if not ticket or ticket!=home.getProperty(BUSY):
        return
    mon=xbmc.Monitor()
    # Dialog's XML onload may run before the keyboard is the active modal.
    for _ in range(20):
        if mon.abortRequested() or home.getProperty(ARM)!=ticket or home.getProperty(BUSY)!=ticket:
            return
        if xbmcgui.getCurrentWindowDialogId()==KEYBOARD:
            if mon.waitForAbort(0.25):
                return
            if xbmcgui.getCurrentWindowDialogId()==KEYBOARD and home.getProperty(ARM)==ticket:
                home.clearProperty(ARM)
                # Kodi's action is handled by GUIDialogKeyboardGeneric::OnAction.
                xbmc.executebuiltin("Action(VoiceRecognizer)")
            return
        if mon.waitForAbort(0.1):
            return

def playback_context():
    """Only public title/episode/channel metadata, never file paths or tokens."""
    if not xbmc.getCondVisibility("Player.HasVideo | Pvr.IsPlayingTV"):
        return None
    def info(label):
        return (xbmc.getInfoLabel(label) or "").strip()[:180]
    if xbmc.getCondVisibility("Pvr.IsPlayingTV"):
        return {"channel":info("VideoPlayer.ChannelName"),"programme":info("VideoPlayer.Title"),
                "kind":"tv_live"}
    show=info("VideoPlayer.TVShowTitle")
    title=info("VideoPlayer.Title")
    if not (title or show):
        return None
    return {"title":show or title,"kind":"serie" if show else "film",
            "episode_title":title if show else "",
            "season":info("VideoPlayer.Season"),"episode":info("VideoPlayer.Episode"),
            "year":info("VideoPlayer.Year"),"context":"currently_playing"}

def allowed_window(dialog):
    # Only playback-related modal windows; don't stack another keyboard over
    # text entry, PIN, confirmations, add-on settings or a running query.
    return dialog in (0, 9999, -1) or xbmc.getCondVisibility(
        "Window.IsActive(videoosd) | Window.IsActive(fullscreeninfo) | "
        "Window.IsActive(seekbar) | Window.IsActive(pvrosdchannels) | Window.IsActive(pvrchannelguide)")

def run(home):
    if not allowed_window(xbmcgui.getCurrentWindowDialogId()):
        return
    current=home.getProperty(BUSY)
    if current:
        try:
            if 0 <= time.monotonic()-float(current) < 180:
                return
        except ValueError:
            pass
    ticket=str(time.monotonic())
    home.setProperty(BUSY,ticket)
    try:
        context=playback_context()
        android=xbmc.getCondVisibility("System.Platform.Android")
        auto=android and xbmc.getInfoLabel("Skin.String(lucent.voice.auto)")!="off"
        heading="Lucent AI"
        if context:
            heading+=" · "+(context.get("title") or context.get("channel") or "Riproduzione")
        if android:
            heading+=" · OK prolungato per parlare"
        keyboard=xbmc.Keyboard("",heading[:145])
        if auto:
            home.setProperty(ARM,ticket)
        try:
            keyboard.doModal()
        finally:
            if home.getProperty(ARM)==ticket:
                home.clearProperty(ARM)
        if not keyboard.isConfirmed():
            return
        text=keyboard.getText().strip()[:500]
        if not text:
            return
        from ai_home import _run_query
        _run_query(text,context,global_mode=True)
    except Exception as exc:
        xbmc.log("[skin.lucent] voice: "+type(exc).__name__,xbmc.LOGWARNING)
        xbmcgui.Dialog().notification("Lucent AI","Assistente non disponibile. Riprova.",
                                       xbmcgui.NOTIFICATION_WARNING,3500)
    finally:
        if home.getProperty(BUSY)==ticket:
            home.clearProperty(BUSY)

def main():
    home=xbmcgui.Window(10000)
    if len(sys.argv)>1 and sys.argv[1]=="listen":
        listen(home)
    else:
        run(home)

if __name__=="__main__":
    main()
