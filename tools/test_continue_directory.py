#!/usr/bin/env python3
"""Regression checks reproducing the two real Kodi screenshots.

MobLand: 10 episode entries in the active season, two episodes watched.
Silo: currently viewing Season 2, but the series has never been started.
Kodi and Stream4Me can expose each episode as a navigable plugin folder
with no season/episode fields in the JSON-RPC directory response.
"""
import pathlib
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from test_continue_native import FakeKodi, target


def folder(label, path, **metadata):
    return dict(label=label, file=path, filetype="directory", **metadata)


def season_path(show, season):
    return f"videodb://tvshows/titles/{show}/{season}/"


def episode_folders(show, season, total):
    return [folder(f"Episode tile {i}",
                   f"plugin://plugin.video.stream4me/?show={show}&s={season}&e={i}")
            for i in range(1, total + 1)]


class DirectoryFallbackTests(unittest.TestCase):
    def setUp(self):
        self.original = sys.modules.get("xbmc")

    def tearDown(self):
        if self.original is None:
            sys.modules.pop("xbmc", None)
        else:
            sys.modules["xbmc"] = self.original

    def use(self, kodi):
        sys.modules["xbmc"] = kodi
        return kodi

    def test_mobland_two_watched_no_episode_fields(self):
        """C4: 10 directory items; use observed '2 watched' to pick E3."""
        root = "videodb://tvshows/titles/3/"
        first = season_path(3, 1)
        rows = episode_folders(3, 1, 10)
        kodi = self.use(FakeKodi(
            direct={3: {"title": "MobLand"}},
            directory_files={
                root: [folder("Stagione 1", first, season=1, watchedepisodes=2)],
                first: rows
            },
            tabs=[{"Label": "Stagione 1", "Season": "1"}],
            season_episodes={0: [
                {"Label": f"Episode tile {i}", "Episode": str(i),
                 "Season": "1", "DBType": "episode"}
                for i in range(1, 11)
            ]},
        ))
        context = ["MobLand", root, first, "3", "MobLand",
                   "1", "Stagione 1", "2"]
        self.assertTrue(target.run(context))
        self.assertEqual(kodi.builtins[-2:], [
            "Control.SetFocus(5601,2,absolute)", "Action(Select)"
        ])
        self.assertEqual(target.LAST_DIAGNOSTIC["folder_items"], 10)
        self.assertEqual(target.LAST_DIAGNOSTIC["step"], "selected-episode")

    def test_silo_from_zero_while_season_two_selected(self):
        """C4: Silo has 4 seasons, S2 selected; start S1E1 instead."""
        root = "videodb://tvshows/titles/4/"
        seasons = [season_path(4, i) for i in range(1, 5)]
        season_folders = [
            folder(f"Stagione {i}", seasons[i - 1], season=i,
                   watchedepisodes=0) for i in range(1, 5)
        ]
        data = {root: season_folders}
        for i, path in enumerate(seasons, start=1):
            data[path] = episode_folders(4, i, 10)
        tabs = [{"Label": ".."}, {"Label": "* Tutte le stagioni"}] + [
            {"Label": f"Stagione {i}", "Season": str(i)} for i in range(1, 5)
        ]
        gui = {i + 1: [
            {"Label": f"Episode tile {n}", "Episode": str(n), "Season": str(i)}
            for n in range(1, 11)
        ] for i in range(1, 5)}
        kodi = self.use(FakeKodi(
            direct={4: {"title": "Silo"}},
            directory_files=data, tabs=tabs, season_episodes=gui))
        context = ["Silo", root, seasons[1], "4", "Silo",
                   "2", "Stagione 2", "0"]
        self.assertTrue(target.run(context))
        self.assertEqual(kodi.builtins[-3:], [
            "Control.SetFocus(56,2,absolute)",
            "Control.SetFocus(5601,0,absolute)", "Action(Select)"
        ])
        self.assertEqual(target.LAST_DIAGNOSTIC["step"], "selected-other-season")

    def test_actual_kodi_file_with_no_resume_object_is_handled(self):
        root = "videodb://tvshows/titles/3/"
        first = season_path(3, 1)
        items = [
            {"filetype": "file", "file": "plugin://stream4me/1",
             "label": "First", "season": 1, "episode": 1,
             "playcount": 1, "resume": "unknown"},
            {"filetype": "file", "file": "plugin://stream4me/2",
             "label": "Second", "season": 1, "episode": 2,
             "playcount": 0, "resume": "unknown"}
        ]
        kodi = self.use(FakeKodi(
            direct={3: {"title": "MobLand"}},
            directory_files={root: [folder("Stagione 1", first, season=1)],
                             first: items}))
        self.assertTrue(target.run(
            ["MobLand", root, first, "3", "MobLand", "1", "Stagione 1", "1"]))
        self.assertIn(("Player.Open", {
            "item": {"file": "plugin://stream4me/2"},
            "options": {"resume": False}
        }), kodi.calls)

    def test_do_not_browse_generic_tvshows_root(self):
        self.assertFalse(target._safe_season_root("videodb://tvshows/titles/", 3))
        self.assertFalse(target._safe_season_root(
            "videodb://tvshows/titles/300/", 3))
        self.assertTrue(target._safe_season_root(
            "videodb://tvshows/titles/3/", 3))

    def test_never_play_other_series_tile(self):
        rows = [
            folder("Squid Game", "plugin://anything/a", type="tvshow", episode=22),
            folder("FROM", "plugin://anything/b", type="tvshow", episode=40),
        ]
        self.assertEqual(target._episode_tiles(rows, 1, 0), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
