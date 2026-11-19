#!/usr/bin/env python3
"""Regression tests for Lucent ITA's Netflix-style Continue, without Kodi.

Covers starting from zero, resume, next episode, next season, and the exact
bug where the screen contains TV-show tiles ("Squid Game" E22, "FROM" E40)
rather than playable episodes. No dependency on Lucent Video.
"""
import json
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import continue_native as target


def ep(season, episode, watched=0, position=0, total=1800,
       aired="2025-01-01", **extra):
    return dict(season=season, episode=episode, playcount=watched,
                resume={"position": position, "total": total},
                firstaired=aired, **extra)


class SelectionTests(unittest.TestCase):
    def test_series_from_zero(self):
        item = target.next_unwatched([ep(2, 1), ep(1, 2), ep(1, 1)])
        self.assertEqual(target._episode_order(item), (1, 1))

    def test_one_watched_next_episode(self):
        item = target.next_unwatched([ep(1, 1, watched=1), ep(1, 2)])
        self.assertEqual(target._episode_order(item), (1, 2))

    def test_resume_unfinished_even_with_playcount_one(self):
        item = target.next_unwatched([ep(1, 1, watched=1, position=420),
                                      ep(1, 2)])
        self.assertEqual(target._episode_order(item), (1, 1))

    def test_next_season(self):
        item = target.next_unwatched([ep(1, 1, watched=1),
                                      ep(1, 2, watched=1), ep(2, 1)])
        self.assertEqual(target._episode_order(item), (2, 1))

    def test_fully_watched_does_not_randomly_restart(self):
        self.assertIsNone(target.next_unwatched([
            ep(1, 1, watched=1), ep(1, 2, watched=1)]))

    def test_no_unreleased_episodes(self):
        self.assertIsNone(target.next_unwatched([ep(1, 1, aired="2036-01-01")],
                                                 today="2026-11-19"))

    def test_specials_are_lower_priority_than_season_one(self):
        item = target.next_unwatched([ep(0, 1), ep(1, 1)])
        self.assertEqual(target._episode_order(item), (1, 1))

    def test_localized_first_air_date(self):
        self.assertTrue(target._valid_today({"firstaired": "17.09.2021"}, "2026-11-19"))


class FakeKodi:
    LOGINFO = 1

    def __init__(self, labels=None, shows=None, direct=None, episodes=None,
                 tabs=None, season_episodes=None, directory_files=None):
        self.labels = labels or {}
        self.shows = shows or []
        self.direct = direct or {}
        self.episodes = episodes or []
        self.tabs = tabs or []
        self.season_episodes = season_episodes or {}
        self.directory_files = directory_files or {}
        self.selected_season = None
        self.builtins = []
        self.calls = []

    def getInfoLabel(self, name):
        m = re.fullmatch(r"Container\(56\).ListItemAbsolute\((\d+)\)\.(.*)", name)
        if m:
            i = int(m.group(1))
            row = self.tabs[i] if i < len(self.tabs) else {}
            return str(row.get(m.group(2), self.labels.get(name, "")))
        m = re.fullmatch(r"Container\(5601\).ListItemAbsolute\((\d+)\)\.(.*)", name)
        if m:
            i = int(m.group(1))
            season = self.season_episodes.get(self.selected_season, [])
            row = season[i] if i < len(season) else {}
            return str(row.get(m.group(2), self.labels.get(name, "")))
        if name == "Container(56).NumItems":
            return str(len(self.tabs))
        if name == "Container(5601).NumItems" and self.tabs:
            return str(len(self.season_episodes.get(self.selected_season, [])))
        return str(self.labels.get(name, ""))

    def getCondVisibility(self, name):
        return False

    def executebuiltin(self, cmd):
        self.builtins.append(cmd)
        m = re.match(r"Control.SetFocus\(56,(\d+),absolute\)", cmd)
        if m:
            self.selected_season = int(m.group(1))

    def sleep(self, _ms):
        pass

    def log(self, _message, _level):
        pass

    def executeJSONRPC(self, raw):
        request = json.loads(raw)
        method, params = request["method"], request.get("params") or {}
        self.calls.append((method, params))
        if method == "VideoLibrary.GetTVShows":
            result = {"tvshows": self.shows}
        elif method == "VideoLibrary.GetTVShowDetails":
            result = {"tvshowdetails": self.direct.get(params["tvshowid"], {})}
        elif method == "VideoLibrary.GetEpisodes":
            result = {"episodes": self.episodes}
        elif method == "Files.GetDirectory":
            result = {"files": self.directory_files.get(params["directory"], [])}
        elif method == "Player.Open":
            result = "OK"
        else:
            return json.dumps({"jsonrpc": "2.0", "id": 1,
                               "error": {"code": -32601, "message": "Unknown"}})
        return json.dumps({"jsonrpc": "2.0", "id": 1, "result": result})


class ContinueIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.old = sys.modules.get("xbmc")

    def tearDown(self):
        if self.old is None:
            sys.modules.pop("xbmc", None)
        else:
            sys.modules["xbmc"] = self.old

    def use(self, kodi):
        sys.modules["xbmc"] = kodi
        return kodi

    def test_library_from_zero_no_tmdb_id(self):
        kodi = self.use(FakeKodi(
            labels={"Container.ShowTitle": "FROM"},
            shows=[{"tvshowid": 50, "title": "FROM"}],
            episodes=[dict(ep(1, 1), episodeid=100),
                      dict(ep(1, 2), episodeid=101)]))
        self.assertTrue(target.run())
        self.assertIn(("Player.Open", {"item": {"episodeid": 100},
                          "options": {"resume": False}}), kodi.calls)

    def test_library_next_day_next_episode(self):
        kodi = self.use(FakeKodi(
            labels={"Container.ShowTitle": "FROM",
                    "ListItem.TvShowDBID": "50"},
            direct={50: {"title": "FROM"}},
            episodes=[dict(ep(1, 1, watched=1), episodeid=100),
                      dict(ep(1, 2), episodeid=101)]))
        self.assertTrue(target.run())
        self.assertIn(("Player.Open", {"item": {"episodeid": 101},
                          "options": {"resume": False}}), kodi.calls)

    def test_library_partial_resume(self):
        kodi = self.use(FakeKodi(
            labels={"Container.ShowTitle": "FROM"},
            shows=[{"tvshowid": 50, "title": "FROM"}],
            episodes=[dict(ep(1, 1, position=650), episodeid=100),
                      dict(ep(1, 2), episodeid=101)]))
        self.assertTrue(target.run())
        self.assertIn(("Player.Open", {"item": {"episodeid": 100},
                          "options": {"resume": True}}), kodi.calls)

    def test_addon_seasons_from_zero_with_grouped_show_tiles(self):
        tabs = [{"Label": "* Tutte le stagioni"},
                {"Label": "Stagione 1"}, {"Label": "Stagione 2"}]
        season_rows = {
            0: [{"Label": "Squid Game", "DBType": "tvshow",
                 "Episode": "22", "Season": "1"},
                {"Label": "FROM", "DBType": "tvshow",
                 "Episode": "40", "Season": "1"}],
            1: [{"Label": "Episodio uno", "DBType": "episode",
                 "Episode": "1", "Season": "1", "PlayCount": "0"},
                {"Label": "Episodio due", "DBType": "episode",
                 "Episode": "2", "Season": "1", "PlayCount": "0"}],
            2: [{"Label": "Episodio uno", "DBType": "episode",
                 "Episode": "1", "Season": "2", "PlayCount": "0"}],
        }
        kodi = self.use(FakeKodi(tabs=tabs, season_episodes=season_rows))
        self.assertTrue(target.run())
        self.assertEqual(kodi.builtins[-2:],
                         ["Control.SetFocus(5601,0,absolute)", "Action(Select)"])
        self.assertFalse(any("plugin.video.lucent" in x for x in kodi.builtins))

    def test_addon_next_season(self):
        tabs = [{"Label": "Stagione 1"}, {"Label": "Stagione 2"}]
        rows = {
            0: [{"Label": "Episodio uno", "DBType": "episode", "Episode": "1",
                 "Season": "1", "PlayCount": "1"}],
            1: [{"Label": "Episodio uno", "DBType": "episode", "Episode": "1",
                 "Season": "2", "PlayCount": "0"}]}
        kodi = self.use(FakeKodi(tabs=tabs, season_episodes=rows))
        self.assertTrue(target.run())
        self.assertEqual(kodi.selected_season, 1)
        self.assertEqual(kodi.builtins[-2:],
                         ["Control.SetFocus(5601,0,absolute)", "Action(Select)"])

    def test_show_tiles_do_not_count_as_episodes(self):
        kodi = self.use(FakeKodi(labels={"Container(5601).NumItems": "2",
                                         "Container(56).ListItem.Season": "1",
            "Container(5601).ListItemAbsolute(0).Label": "Squid Game",
            "Container(5601).ListItemAbsolute(0).Episode": "22",
            "Container(5601).ListItemAbsolute(0).DBType": "tvshow",
            "Container(5601).ListItemAbsolute(1).Label": "FROM",
            "Container(5601).ListItemAbsolute(1).Episode": "40",
            "Container(5601).ListItemAbsolute(1).DBType": "tvshow"}))
        self.assertFalse(target.run())
        self.assertNotIn("Action(Select)", kodi.builtins)


    def test_explicit_context_from_skin_finds_mobland_without_gui_labels(self):
        """Exact user report: MobLand S1 E1 watched, E2 needs playing."""
        kodi = self.use(FakeKodi(
            direct={50: {"title": "MobLand", "uniqueid": {}}},
            episodes=[
                dict(ep(1, 1, watched=1), episodeid=201),
                dict(ep(1, 2), episodeid=202)]))
        context = ["MobLand", "videodb://tvshows/titles/50/",
                   "videodb://tvshows/titles/50/1/", "50", "MobLand", "1"]
        self.assertTrue(target.run(context))
        self.assertIn(("Player.Open", {"item": {"episodeid": 202},
                          "options": {"resume": False}}), kodi.calls)

    def test_directory_fallback_uses_stream4me_season_files(self):
        folder = "plugin://plugin.video.stream4me/?action=season"
        kodi = self.use(FakeKodi(directory_files={folder: [
            {"filetype": "file", "type": "episode", "title": "E1",
             "file": "plugin://plugin.video.stream4me/?play=1",
             "season": 1, "episode": 1, "playcount": 1},
            {"filetype": "file", "type": "episode", "title": "E2",
             "file": "plugin://plugin.video.stream4me/?play=2",
             "season": 1, "episode": 2, "playcount": 0}
        ]}))
        self.assertTrue(target.run(["MobLand", "", folder, "", "MobLand", "1"]))
        opened = [p for method, p in kodi.calls if method == "Player.Open"]
        self.assertEqual(opened, [{"item": {"file": "plugin://plugin.video.stream4me/?play=2"},
                                   "options": {"resume": False}}])
        self.assertTrue(any(method == "Files.GetDirectory" for method, p in kodi.calls))

    def test_season_view_with_missing_file_metadata_can_still_select_e2(self):
        kodi = self.use(FakeKodi(labels={
            "Container(56).ListItem.Season": "1",
            "Container(5601).NumItems": "2",
            "Container(5601).ListItemAbsolute(0).Label": "Stick or Twist",
            "Container(5601).ListItemAbsolute(0).Episode": "1",
            "Container(5601).ListItemAbsolute(0).Season": "1",
            "Container(5601).ListItemAbsolute(0).PlayCount": "1",
            "Container(5601).ListItemAbsolute(1).Label": "Jigsaw Puzzle",
            "Container(5601).ListItemAbsolute(1).Episode": "2",
            "Container(5601).ListItemAbsolute(1).Season": "1",
            "Container(5601).ListItemAbsolute(1).PlayCount": "0",
        }))
        self.assertTrue(target.run(["MobLand"]))
        self.assertEqual(kodi.builtins[-2:],
                         ["Control.SetFocus(5601,1,absolute)", "Action(Select)"])

    def test_skin_passes_context_to_script_instead_of_reading_button_focus(self):
        xml = (ROOT / "xml/Includes_Views.xml").read_text(encoding="utf-8")
        self.assertIn("info.py,resumeshow,$ESCINFO[Container(56).ListItem.TVShowTitle]", xml)
        self.assertIn("$ESCINFO[Container(56).ListItem.FolderPath]", xml)

    def test_ambiguous_same_name_does_not_pick_random_show(self):
        kodi = FakeKodi(labels={"Container.ShowTitle": "Same Name"},
                         shows=[{"title": "Same Name", "tvshowid": 1},
                                {"title": "Same Name", "tvshowid": 2}])
        self.assertIsNone(target._find_library_show(kodi))


if __name__ == "__main__":
    unittest.main(verbosity=2)
