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
        if not isinstance(resume, dict):
            resume = {}
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


def _show_context(xbmc, context=None):
    """Look at the *series*, never confuse a season's database ID with it."""
    label = lambda key: _label(xbmc, key)
    context = list(context or [])
    context += [""] * max(0, 5 - len(context))
    explicit_title, root_path, season_path, explicit_id, explicit_show_title = context[:5]
    titles = []
    for direct in (explicit_title, explicit_show_title):
        if direct and direct not in titles:
            titles.append(direct)
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
    if str(explicit_id).isdigit() and int(explicit_id) > 0:
        candidates.append(int(explicit_id))
    for expr in ("Container(56).ListItem.TvShowDBID",
                 "ListItem.TvShowDBID", "ListItem.DBID"):
        if expr == "ListItem.DBID" and label("ListItem.DBType") != "tvshow":
            continue
        val = label(expr)
        if val.isdigit() and int(val) not in candidates:
            candidates.append(int(val))
    # Season folders in Kodi's library carry the original series DB ID.
    for path in (root_path, season_path,
                 label("Container.FolderPath"),
                 label("Container(56).ListItem.FolderPath")):
        match = re.search(r"videodb://tvshows/[^/]+/(\d+)/", str(path or ""))
        if match and int(match.group(1)) not in candidates:
            candidates.insert(0, int(match.group(1)))
    return titles, identifiers, candidates


def _matches_show(show, titles, identifiers):
    ids = show.get("uniqueid") or {}
    name = _normalized(show.get("title"))
    title_matches = bool(name and any(name == _normalized(t) for t in titles))
    # The season list can expose identifiers belonging to a *season*, not
    # the parent TV show. An exact series-title match is more reliable here.
    if title_matches:
        return True
    if titles:
        return False
    # With no usable title, require a unique matching external ID.
    for key, incoming in identifiers.items():
        actual = str(ids.get(key) or (show.get("imdbnumber") if key == "imdb" else "") or "")
        if actual and actual == incoming:
            return True
    return False


def _find_library_show(xbmc, context=None):
    titles, identifiers, candidates = _show_context(xbmc, context)
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
        if is_folder:
            return None
        scoped_season_card = season_hint > 0 and episode > 0
        if not scoped_season_card and (not (file_path or playable) or not (showname or pattern)):
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


def _choose_on_screen(xbmc, context=None):
    """Scan the real season folders, not an all-series/all-seasons grouping."""
    tabs = _season_tabs(xbmc)
    context = list(context or []) + [""] * 9
    if not tabs:
        season = (_integer(context[5]) or _integer(_label(xbmc, "Container(56).ListItem.Season")))
        if not season:
            name = context[6] or _label(xbmc, "Container(56).ListItem.Label")
            match = re.search(r"(?:stagione|season)\\s*(\\d+)", name, re.IGNORECASE)
            season = int(match.group(1)) if match else 0
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



# Safe diagnostics are kept in memory for the calling UI, never transmitted.
LAST_DIAGNOSTIC = {"step": "init", "library_id": 0, "folder_items": 0, "view_items": 0, "error": "", "file_type": "", "episode_meta": 0}


def diagnosis():
    """Short non-sensitive detail for debugging a failed Continue press."""
    d = LAST_DIAGNOSTIC
    return ("C5 %s / serie %s / cartella %s / righe %s / tipo %s / episodi %s / errore %s" %
            (d.get("step", "?"), d.get("library_id", 0),
             d.get("folder_items", 0), d.get("view_items", 0),
             d.get("file_type", "-"), d.get("episode_meta", 0), d.get("error", "-")))


def _files_for(xbmc, folder):
    """Ask Kodi for video metadata, keeping the error category for diagnostics."""
    props = ["title", "season", "episode", "playcount", "resume",
             "firstaired", "lastplayed", "showtitle", "watchedepisodes"]
    try:
        result = _rpc(xbmc, "Files.GetDirectory", directory=folder,
                      media="video", properties=props)
    except Exception as error:
        LAST_DIAGNOSTIC["error"] = type(error).__name__ + "-filesprops"
        _log(xbmc, "Files.GetDirectory with properties: " + str(error)[:130])
        try:
            result = _rpc(xbmc, "Files.GetDirectory", directory=folder, media="video")
        except Exception as fallback_error:
            LAST_DIAGNOSTIC["error"] = type(fallback_error).__name__ + "-files"
            return []
    return result.get("files") or []


def _extract_season(item, fallback=0):
    number = _integer(item.get("season"))
    if number:
        return number
    text = str(item.get("label") or item.get("title") or "")
    match = re.search(r"(?:stagione|season)\s*(\d+)\b", text, re.IGNORECASE)
    return int(match.group(1)) if match else fallback


def _episode_tiles(items, season, watched_hint=0):
    """Extract episodes from the selected season, including add-on folders.

    Stream4Me often exposes playable episode *directories* rather than
    JSON-RPC files, and may omit the episode field even though Kodi renders E1,
    E2, etc. Ordinal recovery is allowed only in a known season directory,
    never in a mixed list of shows or seasons.
    """
    if not season:
        return []
    possible = []
    for ix, item in enumerate(items):
        if not isinstance(item, dict) or not item.get("file"):
            continue
        kind = str(item.get("type") or "").lower()
        filetype = str(item.get("filetype") or "").lower()
        label = str(item.get("label") or item.get("title") or "")
        if kind in ("tvshow", "season", "movie") or not label or label == "..":
            continue
        if re.search(r"^(?:\*\s*)?(?:tutte le stagioni|all seasons|stagione\s+\d+|season\s+\d+)$",
                     label.strip(), re.IGNORECASE):
            continue
        if filetype and filetype not in ("file", "directory"):
            continue
        number = _integer(item.get("episode"))
        if not number:
            match = re.search(r"\bS\d{1,2}\s*E(\d{1,3})\b|\bE(\d{1,3})\b", label, re.IGNORECASE)
            if match:
                number = _integer(match.group(1) or match.group(2))
        possible.append((ix, item, number, filetype))
    if not possible:
        return []
    # If Kodi provided no episode numbers at all, the directory itself is an
    # explicit SEASON and must only contain episode entries. Use its listing
    # order and number rows E1..En. Never infer from the all-seasons root.
    known = [n for _, _, n, _ in possible if n > 0]
    if known and len(known) != len(possible):
        # Mixed metadata is ambiguous: don't auto-play an incorrect episode.
        return []
    if len(known) != len(set(known)):
        return []
    raw_watched = [_integer(row.get("playcount")) for _, row, _, _ in possible]
    contiguous_watch_hint = (not any(raw_watched)) and watched_hint > 0
    out = []
    for ordinal, (ix, row, number, filetype) in enumerate(possible, start=1):
        epnumber = number or ordinal
        ep = dict(row)
        ep.update(season=season, episode=epnumber, index=ix, filetype=filetype)
        if contiguous_watch_hint and ordinal <= watched_hint:
            ep["playcount"] = 1
        resume = ep.get("resume")
        if not isinstance(resume, dict):
            ep["resume"] = {}
        out.append(ep)
    LAST_DIAGNOSTIC["episode_meta"] += sum(1 for _, _, number, _ in possible if number)
    return out


def _safe_season_root(path, showid):
    """Only visit Kodi's directory for this *one* series."""
    match = re.fullmatch(r"videodb://tvshows/[^/]+/(\d+)/?", str(path or ""))
    return bool(match and showid and int(match.group(1)) == showid)


def _play_directory_entry(xbmc, chosen, selected_season, selected_path):
    """Use native library playback or the same add-on entry as manual OK."""
    target = str(chosen.get("file") or "")
    if not target:
        return False
    resume = chosen.get("resume") or {}
    if not isinstance(resume, dict):
        resume = {}
    continuing = _number(resume.get("position")) > 0

    # On the season currently shown, let Kodi click the *same* plugin entry
    # the user clicks by hand. This also handles source-picker subfolders.
    if (selected_season == chosen["season"]
            and str(chosen.get("folder") or "") == selected_path):
        xbmc.executebuiltin("Control.SetFocus(5601,%d,absolute)" % chosen["index"])
        xbmc.sleep(180)
        xbmc.executebuiltin("Action(Select)")
        LAST_DIAGNOSTIC["step"] = "selected-episode"
        return True

    if str(chosen.get("filetype") or "") == "directory":
        # A plugin may expose the *episode itself* as a directory (for source
        # selection). Prefer selecting the original row, not treating the URL
        # as a movie file.
        if target.startswith(("plugin://", "videodb://", "library://")):
            for season, tab_index in _season_tabs(xbmc):
                if season == chosen["season"]:
                    xbmc.executebuiltin("Control.SetFocus(56,%d,absolute)" % tab_index)
                    xbmc.sleep(350)
                    for _ in range(7):
                        try:
                            if xbmc.getCondVisibility("Container(5601).IsUpdating"):
                                xbmc.sleep(200)
                                continue
                        except Exception:
                            pass
                        break
                    count = _integer(_label(xbmc, "Container(5601).NumItems"))
                    if count > chosen["index"]:
                        xbmc.executebuiltin(
                            "Control.SetFocus(5601,%d,absolute)" % chosen["index"])
                        xbmc.sleep(150)
                        xbmc.executebuiltin("Action(Select)")
                        LAST_DIAGNOSTIC["step"] = "selected-other-season"
                        return True
            # When a remote script cannot see GUI list metadata, use the
            # *actual episode folder* as a safe navigation target.
            xbmc.executebuiltin('ActivateWindow(Videos,"%s",return)' % target.replace('"', '%22'))
            LAST_DIAGNOSTIC["step"] = "episode-folder"
            return True
        return False

    _rpc(xbmc, "Player.Open",
         item={"file": target}, options={"resume": continuing})
    LAST_DIAGNOSTIC["step"] = "episode-file"
    return True


def _directory_fallback(xbmc, context):
    """Use Kodi's real series/season folder instead of guessing URLs."""
    context = list(context or []) + [""] * 10
    root, selected_path, season_string, seen_string = (
        context[1], context[2], context[5], context[7])
    selected_season = _integer(season_string)
    seen = _integer(seen_string)
    showid = _integer(LAST_DIAGNOSTIC.get("library_id"))

    # Prefer scanning all seasons via the original Kodi TV-show folder.
    # This is necessary when the user is currently on season 2 but has not
    # watched any episode of season 1 (as in the supplied Silo screenshot).
    season_folders = []
    if _safe_season_root(root, showid):
        folder_entries = _files_for(xbmc, root)
        for item in folder_entries:
            if not isinstance(item, dict):
                continue
            season = _extract_season(item)
            path = str(item.get("file") or "")
            if season > 0 and path and str(item.get("filetype") or "") == "directory":
                season_folders.append((season, path, _integer(item.get("watchedepisodes"))))
        season_folders = sorted(set(season_folders))
    if selected_path and selected_season > 0 and not any(
            path == selected_path for _, path, _ in season_folders):
        season_folders.append((selected_season, selected_path, seen))

    if not season_folders and selected_path and selected_season:
        season_folders = [(selected_season, selected_path, seen)]
    all_rows = []
    # Never follow unrestricted plugin directory roots: only individual
    # seasons explicitly present in this series' Kodi folder.
    for season, folder, watched in sorted(season_folders)[:20]:
        if not folder.startswith(("videodb://", "plugin://", "library://")):
            continue
        items = _files_for(xbmc, folder)
        LAST_DIAGNOSTIC["folder_items"] += len(items)
        if items and not LAST_DIAGNOSTIC["file_type"]:
            first = items[0]
            if isinstance(first, dict):
                LAST_DIAGNOSTIC["file_type"] = (
                    str(first.get("filetype") or "?")[:12] + ":"
                    + str(first.get("type") or "?")[:12])
        # For selected season trust the label shown in Lucent, which reports
        # watched episodes even when Files.GetDirectory omits playcount.
        if folder == selected_path and not watched:
            watched = seen
        for item in _episode_tiles(items, season, watched):
            item["folder"] = folder
            all_rows.append(item)
    chosen = next_unwatched(all_rows)
    if chosen:
        _log(xbmc, "directory selected S%02dE%02d of %d" %
             (chosen["season"], chosen["episode"], len(all_rows)))
        return _play_directory_entry(xbmc, chosen, selected_season, selected_path)
    return False



def _log(xbmc, message):
    xbmc.log("[Lucent ITA] native Continue: " + str(message), xbmc.LOGINFO)


def run(context=None):
    """True if playback was requested; False if none can safely be selected."""
    import xbmc
    LAST_DIAGNOSTIC.update(step="library-lookup", library_id=0,
                           folder_items=0, view_items=0, error="", file_type="", episode_meta=0)
    showid = _find_library_show(xbmc, context)
    LAST_DIAGNOSTIC["library_id"] = int(showid or 0)
    if showid:
        try:
            episodes = _library_episodes(xbmc, showid)
            chosen = next_unwatched(episodes)
            if chosen and _integer(chosen.get("episodeid")):
                resume = chosen.get("resume") or {}
                continuing = _number(resume.get("position")) > 0
                _log(xbmc, f"library show={showid}, S{chosen['season']}E{chosen['episode']}, resume={continuing}")
                LAST_DIAGNOSTIC["step"] = "library-play"
                _rpc(xbmc, "Player.Open",
                     item={"episodeid": _integer(chosen["episodeid"])},
                     options={"resume": continuing})
                return True
            if episodes:
                _log(xbmc, f"no remaining unwatched episodes for library show {showid}")
                return False
        except Exception as error:
            LAST_DIAGNOSTIC["error"] = type(error).__name__ + "-library"
            _log(xbmc, f"library playback fallback: {error}")
    # Read the selected season's actual Kodi directory even if the script
    # cannot see its on-screen GUI control or the show was not in the library.
    LAST_DIAGNOSTIC["step"] = "directory-lookup"
    if _directory_fallback(xbmc, context):
        return True
    # For an add-on-only show, select the *real* episode provided by the
    # existing addon, never a synthetic Lucent Video or TMDb Helper URL.
    LAST_DIAGNOSTIC["step"] = "view-lookup"
    LAST_DIAGNOSTIC["view_items"] = _integer(_label(xbmc, "Container(5601).NumItems"))
    result = _choose_on_screen(xbmc, context)
    if not result:
        _log(xbmc, "no identifiable playable episodes; refusing to launch a different title")
    return result
