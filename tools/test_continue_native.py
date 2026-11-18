#!/usr/bin/env python3
"""Offline regression tests for the season-page Continue button.

Never needs installed Kodi, internet, Lucent Video or Stream4Me.
"""
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import continue_native as target  # noqa: E402


def ep(season, episode, watched=0, position=0, total=1800, aired="2025-01-01", **extra):
    return dict(season=season, episode=episode, playcount=watched,
                resume={"position": position, "total": total},
                firstaired=aired, **extra)


class ContinueSelectionTests(unittest.TestCase):
    def test_start_first_episode_when_never_watched(self):
        self.assertEqual(target.next_unwatched([
            ep(2, 1), ep(1, 2), ep(1, 1)])["episode"], 1)

    def test_resume_unfinished_before_new_episodes(self):
        result = target.next_unwatched([
            ep(1, 1, watched=1), ep(1, 2, position=640),
            ep(1, 3), ep(2, 1)])
        self.assertEqual(target._episode_order(result), (1, 2))

    def test_next_episode_after_last_watched(self):
        result = target.next_unwatched([
            ep(1, 1, watched=1), ep(1, 2, watched=1), ep(1, 3)])
        self.assertEqual(target._episode_order(result), (1, 3))

    def test_next_season_not_first_episode_again(self):
        result = target.next_unwatched([
            ep(1, 1, watched=1), ep(1, 2, watched=1), ep(2, 1)])
        self.assertEqual(target._episode_order(result), (2, 1))

    def test_all_watched_never_auto_restarts(self):
        self.assertIsNone(target.next_unwatched([
            ep(1, 1, watched=1), ep(1, 2, watched=1)]))

    def test_future_episodes_are_ignored(self):
        self.assertIsNone(target.next_unwatched([ep(1, 1, aired="2035-01-01")],
                                                 today="2026-11-18"))

    def test_specials_excluded_when_season_one_exists(self):
        result = target.next_unwatched([ep(0, 1), ep(1, 1)])
        self.assertEqual(target._episode_order(result), (1, 1))

    def test_dont_restart_watched_when_only_unwatched_are_earlier(self):
        self.assertIsNone(target.next_unwatched([
            ep(1, 1), ep(1, 2, watched=1)]))


class FakeKodi:
    LOGINFO = 1
    def __init__(self, labels=None, episodes=None, shows=None, direct=None):
        self.labels = labels or {}
        self.episodes = episodes or []
        self.shows = shows or []
        self.direct = direct or {}
        self.builtins = []
        self.calls = []
        self.notifications = []
    def getInfoLabel(self, name):
        return str(self.labels.get(name, ""))
    def sleep(self, ms):
        pass
    def executebuiltin(self, action):
        self.builtins.append(action)
    def log(self, msg, level):
        pass
    def executeJSONRPC(self, raw):
        req = json.loads(raw)
        method = req["method"]
        self.calls.append((method, req["params"]))
        if method == "VideoLibrary.GetTVShowDetails":
            sid = req["params"]["tvshowid"]
            ret = self.direct.get(sid, {})
            return json.dumps({"jsonrpc":"2.0","id":1,"result":{"tvshowdetails":ret}})
        if method == "VideoLibrary.GetTVShows":
            return json.dumps({"jsonrpc":"2.0","id":1,"result":{"tvshows":self.shows}})
        if method == "VideoLibrary.GetEpisodes":
            return json.dumps({"jsonrpc":"2.0","id":1,"result":{"episodes":self.episodes}})
        if method == "Player.Open":
            return json.dumps({"jsonrpc":"2.0","id":1,"result":"OK"})
        return json.dumps({"jsonrpc":"2.0","id":1,"error":{"code":-32601,"message":"Unknown method"}})


class ContinueIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.old = sys.modules.get("xbmc")
    def tearDown(self):
        if self.old is None:
            sys.modules.pop("xbmc", None)
        else:
            sys.modules["xbmc"] = self.old

    def test_library_episode_uses_native_player(self):
        kodi = FakeKodi(
            labels={"Container(5698).ListItem.DBID":"12",
                    "Container(5698).ListItem.UniqueID(tmdb)":"9988",
                    "Container.ShowTitle":"Serie di prova"},
            direct={12: {"title":"Serie di prova","uniqueid":{"tmdb":"9988"}}},
            episodes=[
                dict(ep(1, 1, watched=1), episodeid=301),
                dict(ep(1, 2, position=100), episodeid=302)])
        sys.modules["xbmc"] = kodi
        self.assertTrue(target.run())
        opened = [params for name, params in kodi.calls if name == "Player.Open"]
        self.assertEqual(opened, [{"item":{"episodeid":302},"options":{"resume":True}}])
        self.assertFalse(any("lucent" in str(x).lower() for x in kodi.builtins))

    def test_addon_only_episodes_use_actual_visible_kodi_list(self):
        # No library match. A season supplied by Stream4Me has playable rows
        # loaded in container 5601. Select its next unwatched row normally.
        props = {"Container(5601).NumItems":"3",
                 "Container(56).ListItem.Season":"1"}
        for i, seen in enumerate([1, 1, 0]):
            stem=f"Container(5601).ListItemAbsolute({i})."
            props[stem+"Label"]=f"Episodio {i+1}"
            props[stem+"Episode"]=str(i+1)
            props[stem+"PlayCount"]=str(seen)
        kodi=FakeKodi(labels=props)
        sys.modules["xbmc"]=kodi
        self.assertTrue(target.run())
        self.assertEqual(kodi.builtins, ["Control.SetFocus(5601,2,absolute)", "Action(Select)"])

    def test_nothing_to_play_does_not_invoke_lucent_video(self):
        kodi = FakeKodi(labels={"Container(5601).NumItems":"0"})
        sys.modules["xbmc"]=kodi
        self.assertFalse(target.run())
        self.assertFalse(any("plugin.video.lucent" in str(x) for x in kodi.builtins))

    def test_ambiguous_title_does_not_guess_library_show(self):
        kodi = FakeKodi(
            labels={"Container.ShowTitle":"Same Name"},
            shows=[{"tvshowid":1,"title":"Same Name"}, {"tvshowid":2,"title":"Same Name"}])
        self.assertIsNone(target._find_library_show(kodi))


if __name__ == "__main__":
    unittest.main(verbosity=2)
