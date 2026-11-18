# -*- coding: utf-8 -*-
"""Independent Continue button for the seasons-as-tabs TV show screen.

Uses Kodi's own video library if possible. If the show is supplied only by
another add-on, selects the correct episode in the *existing* 5601 list and
presses Select: this is exactly the path that already works when a user clicks
that episode manually. Never requires plugin.video.lucent, TMDb Helper or Trakt.

Nothing is scanned, changed or played unless Continue is pressed.
"""
import json
from datetime import date


def _integer(value, default=0):
    try:
        return int(float(value or 0))
    except (TypeError, ValueError):
        return default


def _number(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _valid_today(episode, today=None):
    """Do not start an episode before its first air date."""
    first = str(episode.get("firstaired") or episode.get("premiered") or "")[:10]
    if not first:
        return True
    today = today or date.today().isoformat()
    return first <= today


def _episode_order(ep):
    return (_integer(ep.get("season")), _integer(ep.get("episode")))


def next_unwatched(episodes, today=None):
    """Select an unfinished episode, or the next unseen *after* the last watched.

    With no watched history, start at the first unwatched episode. Season zero
    (specials) is excluded if any ordinary episode exists. Never restart the
    first episode after a series has been completely watched.
    """
    rows = [ep for ep in episodes if _valid_today(ep, today)
            and _integer(ep.get("season")) >= 0]
    if any(_integer(ep.get("season")) > 0 for ep in rows):
        rows = [ep for ep in rows if _integer(ep.get("season")) > 0]
    if not rows:
        return None
    rows.sort(key=_episode_order)
    started = []
    for ep in rows:
        resume = ep.get("resume") or {}
        progress = _number(resume.get("position"))
        total = _number(resume.get("total"))
        # The UI exposes a percentage for add-ons without an exact resume point.
        percent = _number(ep.get("percent"))
        if ((progress > 0 and (total <= 0 or progress / total < .95))
                or (2 < percent < 95)) and not _integer(ep.get("playcount")):
            started.append(ep)
    if started:
        return max(started, key=lambda e: (str(e.get("lastplayed") or ""), _episode_order(e)))
    watched = [i for i, ep in enumerate(rows) if _integer(ep.get("playcount"))]
    if watched:
        return next((ep for ep in rows[max(watched) + 1:] if not _integer(ep.get("playcount"))), None)
    return next((ep for ep in rows if not _integer(ep.get("playcount"))), None)


def _rpc(xbmc, method, **params):
    result = json.loads(xbmc.executeJSONRPC(json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": method, "params": params})))
    if result.get("error"):
        raise RuntimeError("%s: %s" % (method, result["error"]))
    return result.get("result") or {}


def _label(xbmc, expression):
    return xbmc.getInfoLabel(expression) or ""


def _show_context(xbmc):
    """Identify a series, not a selected season's own DBID."""
    label = lambda key: _label(xbmc, key)
    title = next((label(x) for x in (
        "Container.ShowTitle", "Container(5698).ListItem.Title",
        "ListItem.TVShowTitle", "Container(56).ListItem.TVShowTitle",
        "ListItem.Title") if label(x)), "")
    tmdb = next((label(x) for x in (
        "Container(5698).ListItem.UniqueID(tmdb)",
        "Container(56).ListItem.Property(tmdb_id)",
        "Container(56).ListItem.UniqueID(tmdb)",
        "ListItem.UniqueID(tmdb)", "ListItem.Property(tmdb_id)"
    ) if label(x).isdigit()), "")
    # Never pass Container(56).ListItem.DBID as tvshowid: it identifies a season.
    show_ids = []
    for expr in ("Container(5698).ListItem.DBID", "ListItem.DBID"):
        if expr == "ListItem.DBID" and label("ListItem.DBType") != "tvshow":
            continue
        val = label(expr)
        if val.isdigit() and int(val) > 0:
            show_ids.append(int(val))
    return title.strip(), tmdb, show_ids


def _find_library_show(xbmc):
    title, tmdb, candidates = _show_context(xbmc)
    for sid in candidates:
        try:
            result = _rpc(xbmc, "VideoLibrary.GetTVShowDetails",
                          tvshowid=sid, properties=["title", "uniqueid"])
            item = result.get("tvshowdetails") or {}
            if not item:
                continue
            ids = item.get("uniqueid") or {}
            if tmdb and str(ids.get("tmdb") or "") != tmdb:
                continue
            if not tmdb and title and item.get("title", "").strip().casefold() != title.casefold():
                continue
            return sid
        except Exception:
            continue
    if not title and not tmdb:
        return None
    try:
        data = _rpc(xbmc, "VideoLibrary.GetTVShows", properties=["title", "uniqueid"])
    except Exception:
        return None
    shows = data.get("tvshows") or []
    if tmdb:
        matches = [s for s in shows if str((s.get("uniqueid") or {}).get("tmdb") or "") == tmdb]
    else:
        matches = [s for s in shows if str(s.get("title") or "").strip().casefold() == title.casefold()]
    # Avoid guessing when several shows share a title.
    return _integer(matches[0].get("tvshowid")) if len(matches) == 1 else None


def _library_episodes(xbmc, showid):
    result = _rpc(xbmc, "VideoLibrary.GetEpisodes", tvshowid=showid,
                  properties=["season", "episode", "firstaired",
                              "resume", "playcount", "lastplayed", "file"])
    return result.get("episodes") or []


def _onscreen_episodes(xbmc):
    """Read the actual visible episodes (Stream4Me or any other add-on)."""
    size = min(max(0, _integer(_label(xbmc, "Container(5601).NumItems"))), 300)
    rows = []
    for index in range(size):
        stem = "Container(5601).ListItemAbsolute(%d)." % index
        get = lambda key: _label(xbmc, stem + key)
        title = get("Label")
        if not title or title == "..":
            continue
        rows.append({
            "index": index, "title": title,
            "season": get("Season") or _label(xbmc, "Container(56).ListItem.Season"),
            "episode": get("Episode") or (index + 1),
            "playcount": get("PlayCount"),
            "percent": get("PercentPlayed") or get("Property(WatchedProgress)"),
            "firstaired": get("Premiered") or get("Date"),
            "lastplayed": get("LastPlayed"),
        })
    return rows


def _focus_episode(xbmc, index):
    """Click the existing episode with Kodi's native selection action."""
    xbmc.executebuiltin("Control.SetFocus(5601,%d,absolute)" % index)
    xbmc.sleep(160)
    xbmc.executebuiltin("Action(Select)")


def _log(xbmc, message):
    xbmc.log("[Lucent ITA] native Continue: " + message, xbmc.LOGINFO)


def run():
    """True if playback was started; False if no valid episode was identified."""
    import xbmc
    showid = _find_library_show(xbmc)
    if showid:
        try:
            episodes = _library_episodes(xbmc, showid)
            chosen = next_unwatched(episodes)
            if chosen and _integer(chosen.get("episodeid")):
                # Kodi owns the library entry, including its plugin:// or strm
                # path and resume position. No special Lucent player is needed.
                resume = chosen.get("resume") or {}
                continuing = _number(resume.get("position")) > 0
                _log(xbmc, "library show=%d S%sE%s (resume=%s)" % (
                    showid, chosen.get("season"), chosen.get("episode"), continuing))
                _rpc(xbmc, "Player.Open", item={"episodeid": _integer(chosen["episodeid"])},
                     options={"resume": continuing})
                return True
            _log(xbmc, "no unplayed episode found for library show %d" % showid)
            return False
        except Exception as error:
            _log(xbmc, "library fallback: " + str(error))

    # Add-on-only series: do *not* synthesize a Lucent Video or TMDb Helper URL.
    # Selecting the existing row delegates to the same add-on that already plays
    # correctly when the user presses OK on the episode.
    rows = _onscreen_episodes(xbmc)
    selected = next_unwatched(rows)
    if selected is not None:
        _log(xbmc, "screen row %s S%sE%s" %
             (selected["index"], selected["season"], selected["episode"]))
        _focus_episode(xbmc, selected["index"])
        return True
    _log(xbmc, "no suitable episode in library or currently loaded season")
    return False
