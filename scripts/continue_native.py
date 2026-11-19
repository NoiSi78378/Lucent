# -*- coding: utf-8 -*-
"""Netflix-like Continue for Lucent ITA, using Kodi's native playback.

On a TV series page:
- resume a partially watched library episode,
- otherwise play the next unseen episode (across seasons),
- otherwise play the first episode of a series not yet started.
Works with Kodi's library, including entries supplied by Stream4Me, without
requiring Lucent Video, TMDb Helper or a Trakt login.

For series absent from the library, only use real playable episode rows.
Never mistake a TV-show tile (for example "Squid Game", "E22" = 22 episodes)
for episode 22, and never launch an unrelated series.
"""
import json
import re
from datetime import date, datetime


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


def _normalized(text):
    return re.sub(r"\s+", " ", str(text or "").strip()).casefold()


def _valid_today(episode, today=None):
    """Exclude clearly future episodes; accept unparseable dates as unknown."""
    raw = str(episode.get("firstaired") or episode.get("premiered") or "").strip()
    if not raw:
        return True
    day = None
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
        try:
            day = datetime.strptime(raw[:10], fmt).date()
            break
        except ValueError:
            continue
    if day is None:
        return True
    return day <= (date.fromisoformat(today) if today else date.today())


def _episode_order(ep):
    return (_integer(ep.get("season")), _integer(ep.get("episode")))


def next_unwatched(episodes, today=None):
    """Choose partially watched, then next after last watched, else first.

    Recognize progress even when Kodi reports playcount=1. Exclude specials
    when normal seasons are available. Do not silently restart a completed
    series or select not-yet-aired episodes.
    """
    rows = [e for e in episodes
            if _integer(e.get("episode")) > 0
            and _integer(e.get("season")) >= 0
            and _valid_today(e, today)]
    if any(_integer(e.get("season")) > 0 for e in rows):
        rows = [e for e in rows if _integer(e.get("season")) > 0]
    rows.sort(key=_episode_order)
    if not rows:
        return None
    partial = []
    for ep in rows:
        resume = ep.get("resume") or {}
        position = _number(resume.get("position"))
        total = _number(resume.get("total"))
        pct = _number(ep.get("percent"))
        if ((position > 0 and (total <= 0 or position / total < .95))
                or 2 < pct < 95):
            partial.append(ep)
    if partial:
        return max(partial, key=lambda e: (str(e.get("lastplayed") or ""), _episode_order(e)))
    last_watched = max((i for i, e in enumerate(rows) if _integer(e.get("playcount"))), default=-1)
    if last_watched >= 0:
        return next((e for e in rows[last_watched + 1:]
                     if not _integer(e.get("playcount"))), None)
    return next((e for e in rows if not _integer(e.get("playcount"))), None)


def _rpc(xbmc, method, **params):
    result = json.loads(xbmc.executeJSONRPC(json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": method, "params": params})))
    if result.get("error"):
        raise RuntimeError("%s: %s" % (method, result["error"]))
    return result.get("result") or {}


def _label(xbmc, name):
    return str(xbmc.getInfoLabel(name) or "").strip()


def _show_context(xbmc):
    """Look at the *series*, never confuse a season's database ID with it."""
    label = lambda key: _label(xbmc, key)
    titles = []
    for expression in ("Container.ShowTitle", "ListItem.TVShowTitle",
                       "Container(56).ListItem.TVShowTitle",
                       "Container.FolderName", "ListItem.Title"):
        val = label(expression)
        if val and val not in titles:
            titles.append(val)
    identifiers = {}
    for kind, suffix in (("tmdb", "tmdb"), ("imdb", "imdb"), ("tvdb", "tvdb")):
        for expr in (f"Container(56).ListItem.UniqueID({suffix})",
                     f"ListItem.UniqueID({suffix})",
                     f"Container(56).ListItem.Property({suffix}_id)",
                     f"ListItem.Property({suffix}_id)"):
            val = label(expr)
            if val:
                identifiers[kind] = val
                break
    candidates = []
    for expr in ("Container(56).ListItem.TvShowDBID",
                 "ListItem.TvShowDBID", "ListItem.DBID"):
        if expr == "ListItem.DBID" and label("ListItem.DBType") != "tvshow":
            continue
        val = label(expr)
        if val.isdigit() and int(val) not in candidates:
            candidates.append(int(val))
    # Season folders in Kodi's library carry the original series DB ID.
    for expr in ("Container.FolderPath", "Container(56).ListItem.FolderPath"):
        match = re.search(r"videodb://tvshows/[^/]+/(\d+)/", label(expr))
        if match and int(match.group(1)) not in candidates:
            candidates.insert(0, int(match.group(1)))
    return titles, identifiers, candidates


def _matches_show(show, titles, identifiers):
    ids = show.get("uniqueid") or {}
    for key, incoming in identifiers.items():
        actual = str(ids.get(key) or (show.get("imdbnumber") if key == "imdb" else "") or "")
        if actual and incoming and actual != incoming:
            return False
    # An explicit matching ID is stronger than localized display names.
    for key, incoming in identifiers.items():
        actual = str(ids.get(key) or "")
        if actual and actual == incoming:
            return True
    name = _normalized(show.get("title"))
    return bool(name and any(name == _normalized(t) for t in titles))


def _find_library_show(xbmc):
    titles, identifiers, candidates = _show_context(xbmc)
    for sid in candidates:
        try:
            details = _rpc(xbmc, "VideoLibrary.GetTVShowDetails",
                           tvshowid=sid, properties=["title", "uniqueid", "imdbnumber"])
            item = details.get("tvshowdetails") or {}
            if item and _matches_show(item, titles, identifiers):
                return sid
        except Exception:
            continue
    if not titles and not identifiers:
        return None
    try:
        result = _rpc(xbmc, "VideoLibrary.GetTVShows",
                      properties=["title", "uniqueid", "imdbnumber"],
                      limits={"start": 0, "end": 2000})
    except Exception:
        return None
    matched = [s for s in result.get("tvshows") or []
               if _matches_show(s, titles, identifiers)]
    # A common series title can identify different shows. Do not pick at random.
    return _integer(matched[0].get("tvshowid")) if len(matched) == 1 else None


def _library_episodes(xbmc, showid):
    result = _rpc(xbmc, "VideoLibrary.GetEpisodes",
                  tvshowid=showid, limits={"start": 0, "end": 3000},
                  properties=["season", "episode", "firstaired", "resume",
                              "playcount", "lastplayed", "file"])
    return result.get("episodes") or []


def _gui_listitem(control_id, index):
    try:
        import xbmcgui
        window = xbmcgui.Window(xbmcgui.getCurrentWindowId())
        return window.getControl(control_id).getListItem(index)
    except Exception:
        return None


def _tag_value(item, method, default=""):
    if item is None:
        return default
    try:
        return getattr(item.getVideoInfoTag(), method)()
    except Exception:
        return default


def _row(xbmc, control_id, index, season_hint=0):
    """Only return real episode tiles; TV-show and season folders are unsafe."""
    stem = f"Container({control_id}).ListItemAbsolute({index})."
    li = _gui_listitem(control_id, index)
    def get(key):
        value = _label(xbmc, stem + key)
        if value:
            return value
        if li:
            try:
                if key == "Label":
                    return li.getLabel() or ""
                if key == "Property(WatchedProgress)":
                    return li.getProperty("WatchedProgress") or ""
            except Exception:
                pass
        return ""
    title = get("Label")
    media = get("DBType") or str(_tag_value(li, "getMediaType"))
    if media in ("tvshow", "season", "movie"):
        return None
    season = _integer(get("Season") or _tag_value(li, "getSeason"))
    episode = _integer(get("Episode") or _tag_value(li, "getEpisode"))
    showname = get("TVShowTitle") or str(_tag_value(li, "getTvShowTitle"))
    explicit_episode = (media == "episode")
    if episode <= 0:
        m = re.search(r"(?:s(\d{1,2})e(\d{1,3})|\b\d{1,2}x(\d{1,3})\b)",
                      title, re.IGNORECASE)
        if m:
            season = season or _integer(m.group(1))
            episode = _integer(m.group(2) or m.group(3))
    if episode <= 0:
        return None
    if season <= 0:
        season = season_hint
    if season <= 0:
        return None
    # Add-on show tiles may display "E22" as their total episode count; do not
    # treat that as a season episode. Require either episode mediatype or a
    # series name carried with an actual non-folder video tile.
    if not explicit_episode:
        file_path = get("FileNameAndPath")
        playable = get("Property(IsPlayable)").lower() in ("1", "true")
        is_folder = _label(xbmc, stem + "IsFolder").lower() in ("1", "true")
        pattern = re.search(r"(?:s\d{1,2}e\d{1,3}|\b\d{1,2}x\d{1,3}\b)", title, re.IGNORECASE)
        if is_folder or not (file_path or playable) or not (showname or pattern):
            return None
    return {"index": index, "title": title,
            "season": season, "episode": episode,
            "playcount": get("PlayCount") or _tag_value(li, "getPlaycount", 0),
            "percent": get("PercentPlayed") or get("Property(WatchedProgress)"),
            "firstaired": get("Premiered") or get("Date"),
            "lastplayed": get("LastPlayed")}


def _onscreen_episodes(xbmc, season_hint=0):
    total = min(max(0, _integer(_label(xbmc, "Container(5601).NumItems"))), 350)
    return [ep for i in range(total)
            if (ep := _row(xbmc, 5601, i, season_hint)) is not None]


def _season_tabs(xbmc):
    total = min(max(0, _integer(_label(xbmc, "Container(56).NumItems"))), 35)
    tabs = []
    for i in range(total):
        stem = f"Container(56).ListItemAbsolute({i})."
        item = _gui_listitem(56, i)
        name = _label(xbmc, stem + "Label")
        if not name and item:
            try:
                name = item.getLabel() or ""
            except Exception:
                pass
        season = _integer(_label(xbmc, stem + "Season") or _tag_value(item, "getSeason"))
        if not season:
            match = re.search(r"(?:stagione|season)\s*(\d+)", name, re.IGNORECASE)
            season = int(match.group(1)) if match else 0
        if season > 0:
            tabs.append((season, i))
    return sorted(set(tabs))


def _focus(xbmc, ctrl, index):
    xbmc.executebuiltin(f"Control.SetFocus({ctrl},{index},absolute)")


def _choose_on_screen(xbmc):
    """Scan the real season folders, not an all-series/all-seasons grouping."""
    tabs = _season_tabs(xbmc)
    if not tabs:
        season = _integer(_label(xbmc, "Container(56).ListItem.Season"))
        rows = _onscreen_episodes(xbmc, season)
        chosen = next_unwatched(rows)
        if chosen:
            _focus(xbmc, 5601, chosen["index"])
            xbmc.sleep(170)
            xbmc.executebuiltin("Action(Select)")
            return True
        return False

    # Kodi changes Container(5601).FolderPath when the selected season changes.
    # Keep the UI responsive by scanning at most 12 seasons per button press.
    rows = []
    for season, tab_index in tabs[:12]:
        _focus(xbmc, 56, tab_index)
        xbmc.sleep(260)
        for _ in range(7):
            try:
                if xbmc.getCondVisibility("Container(5601).IsUpdating"):
                    xbmc.sleep(180)
                    continue
            except Exception:
                pass
            break
        entries = _onscreen_episodes(xbmc, season)
        for ep in entries:
            if ep["season"] == season:
                rows.append(dict(ep, tab_index=tab_index))

    chosen = next_unwatched(rows)
    if chosen is None:
        return False
    _focus(xbmc, 56, chosen["tab_index"])
    xbmc.sleep(340)
    # Match by S/E number again after the view is reloaded. Do not rely on
    # stale absolute indices when a plugin reorders its episode directory.
    for ep in _onscreen_episodes(xbmc, chosen["season"]):
        if _episode_order(ep) == _episode_order(chosen):
            _focus(xbmc, 5601, ep["index"])
            xbmc.sleep(170)
            xbmc.executebuiltin("Action(Select)")
            return True
    return False


def _log(xbmc, message):
    xbmc.log("[Lucent ITA] native Continue: " + str(message), xbmc.LOGINFO)


def run():
    """True if playback was requested; False if none can safely be selected."""
    import xbmc
    showid = _find_library_show(xbmc)
    if showid:
        try:
            episodes = _library_episodes(xbmc, showid)
            chosen = next_unwatched(episodes)
            if chosen and _integer(chosen.get("episodeid")):
                resume = chosen.get("resume") or {}
                continuing = _number(resume.get("position")) > 0
                _log(xbmc, f"library show={showid}, S{chosen['season']}E{chosen['episode']}, resume={continuing}")
                _rpc(xbmc, "Player.Open",
                     item={"episodeid": _integer(chosen["episodeid"])},
                     options={"resume": continuing})
                return True
            if episodes:
                _log(xbmc, f"no remaining unwatched episodes for library show {showid}")
                return False
        except Exception as error:
            _log(xbmc, f"library playback fallback: {error}")
    # For an add-on-only show, select the *real* episode provided by the
    # existing addon, never a synthetic Lucent Video or TMDb Helper URL.
    result = _choose_on_screen(xbmc)
    if not result:
        _log(xbmc, "no identifiable playable episodes; refusing to launch a different title")
    return result
