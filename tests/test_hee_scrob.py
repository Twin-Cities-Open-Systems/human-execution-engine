#!/usr/bin/env python3
"""test_hee_scrob: HEE#670 path-map coverage, and which player scrob reports
(operator, 2026-09-20: flippy was playing and scrob showed another player's
show). Pure functions only, no Plex, no network."""
import contextlib
import importlib.machinery
import importlib.util
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(ROOT, "tooling", "bin", "hee-scrob")


def _load():
    loader = importlib.machinery.SourceFileLoader("hee_scrob", TOOL)
    spec = importlib.util.spec_from_loader("hee_scrob", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


d = _load()


class TestMapLocalPath(unittest.TestCase):
    def test_mapping_resolves_a_container_path_that_does_not_exist_locally(self):
        with tempfile.TemporaryDirectory() as t:
            local_root = os.path.join(t, "media")
            os.makedirs(local_root)
            video = os.path.join(local_root, "show.mkv")
            open(video, "w").close()
            mappings = d.parse_path_map(f"/data={local_root}")
            self.assertFalse(os.path.exists("/data/show.mkv"))
            local_file, exists = d.resolve_media_file("/data/show.mkv", mappings)
            self.assertEqual(local_file, video)
            self.assertTrue(exists)

    def test_longest_prefix_wins(self):
        mappings = d.parse_path_map("/data=/a,/data/tv=/b")
        self.assertEqual(d.map_local_path("/data/tv/show.mkv", mappings), "/b/show.mkv")
        self.assertEqual(d.map_local_path("/data/movie.mkv", mappings), "/a/movie.mkv")

    def test_prefix_matches_only_on_a_path_component_boundary(self):
        mappings = d.parse_path_map("/data=/mapped")
        self.assertEqual(d.map_local_path("/database/x.mkv", mappings), "/database/x.mkv")
        self.assertEqual(d.map_local_path("/data/x.mkv", mappings), "/mapped/x.mkv")
        self.assertEqual(d.map_local_path("/data", mappings), "/mapped")

    def test_no_mapping_matches_returns_the_path_unchanged(self):
        mappings = d.parse_path_map("/data=/mapped")
        self.assertEqual(d.map_local_path("/other/x.mkv", mappings), "/other/x.mkv")


class TestParsePathMap(unittest.TestCase):
    def test_several_pairs_parse_longest_container_first(self):
        mappings = d.parse_path_map("/data=/a,/data/tv=/b,/movies=/c")
        self.assertEqual(
            mappings,
            [("/data/tv", "/b"), ("/movies", "/c"), ("/data", "/a")],
        )

    def test_malformed_pairs_are_skipped_missing_equals_or_empty_side(self):
        # "nofoo" has no '=', "/data=" and "=/mapped" have an empty side --
        # all three are dropped. "/data=/a=/b" is NOT malformed: only the
        # first '=' separates container from local, so its local side is
        # "/a=/b" and it survives, ordered by container length like any pair.
        mappings = d.parse_path_map("nofoo, /data=, =/mapped, /ok=/there, ,/data=/a=/b")
        self.assertEqual(mappings, [("/data", "/a=/b"), ("/ok", "/there")])

    def test_empty_or_unset_variable_yields_no_mappings(self):
        self.assertEqual(d.parse_path_map(""), [])
        self.assertEqual(d.parse_path_map(None), [])


class TestResolveOutcomes(unittest.TestCase):
    def test_unresolvable_path_warns_on_stderr_naming_path_and_mappings_and_returns_no_srt(self):
        mappings = d.parse_path_map("/data=/nowhere-real")
        media_file = "/data/show.mkv"
        local_file, exists = d.resolve_media_file(media_file, mappings)
        self.assertFalse(exists)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            d.warn_unresolved(media_file, mappings)
        out = err.getvalue()
        self.assertIn(media_file, out)
        self.assertIn("/data=/nowhere-real", out)
        self.assertIn(d.PATH_MAP_VAR, out)

    def test_resolvable_path_with_no_sidecar_srt_stays_quiet(self):
        with tempfile.TemporaryDirectory() as t:
            video = os.path.join(t, "show.mkv")
            open(video, "w").close()
            local_file, exists = d.resolve_media_file(video, [])
            self.assertTrue(exists)
            self.assertIsNone(d.find_srt(local_file))

    def test_resolvable_path_with_sidecar_srt_returns_it(self):
        with tempfile.TemporaryDirectory() as t:
            video = os.path.join(t, "show.mkv")
            srt = os.path.join(t, "show.srt")
            open(video, "w").close()
            open(srt, "w").close()
            local_file, exists = d.resolve_media_file(video, [])
            self.assertTrue(exists)
            self.assertEqual(str(d.find_srt(local_file)), srt)

    def test_unset_variable_leaves_a_resolvable_local_path_working_as_before(self):
        with tempfile.TemporaryDirectory() as t:
            video = os.path.join(t, "show.mkv")
            srt = os.path.join(t, "show.srt")
            open(video, "w").close()
            open(srt, "w").close()
            env = dict(os.environ)
            env.pop(d.PATH_MAP_VAR, None)
            with mock.patch.dict(os.environ, env, clear=True):
                mappings = d.parse_path_map(os.environ.get(d.PATH_MAP_VAR, ""))
            self.assertEqual(mappings, [])
            local_file, exists = d.resolve_media_file(video, mappings)
            self.assertEqual(local_file, video)
            self.assertTrue(exists)
            self.assertEqual(str(d.find_srt(local_file)), srt)


if __name__ == "__main__":
    unittest.main()


class ToMeme(unittest.TestCase):
    """-to meme hands the file and the moment to hee meme quote --file --at;
    it does not search, and it refuses what it cannot hand over."""

    def test_builds_the_hee_meme_command_with_file_moment_job_and_caption(self):
        m = _load()
        calls = []
        with mock.patch.object(m.subprocess, "call", side_effect=lambda cmd: calls.append(cmd) or 0):
            rc = m.to_meme({"kind": "video", "title": "Show s01e01 - Pilot", "ts": "0:01:30", "file": "/data/media/TV/x.mkv",
                            "offset_ms": 90500, "line": "rum ham"}, "np", hee="/bin/hee")
        self.assertEqual(rc, 0)
        self.assertEqual(calls, [["/bin/hee", "meme", "quote", "--file", "/data/media/TV/x.mkv", "--at", "00:01:30.500",
                                  "--job", "np", "--caption", "rum ham"]])

    def test_a_track_or_a_file_not_here_is_refused_without_calling_anything(self):
        m = _load()
        with mock.patch.object(m.subprocess, "call") as call:
            self.assertEqual(m.to_meme({"kind": "track"}, "np", hee="/bin/hee"), 1)
            self.assertEqual(m.to_meme({"kind": "video", "title": "x", "ts": "0", "file": None, "offset_ms": 0}, "np", hee="/bin/hee"), 1)
        call.assert_not_called()


SESSIONS = """<MediaContainer size="3">
  <Video type="episode" grandparentTitle="Rick and Morty" parentIndex="1" index="2" title="Lawnmower Dog" viewOffset="60000">
    <User title="arewnarb"/>
    <Player address="10.0.0.9" machineIdentifier="win-1" product="Plex for Windows" state="paused" title="DESKTOP-C96DMGM"/>
  </Video>
  <Video type="episode" grandparentTitle="South Park" parentIndex="7" index="6" title="Lil' Crime Stoppers" viewOffset="510000">
    <User title="CrookedMedia"/>
    <Player address="10.0.0.5" machineIdentifier="lin-1" product="Plex for Linux" state="playing" title="flippy"/>
  </Video>
  <Track grandparentTitle="GBH" title="Sick Boy" parentTitle="Perfume and Piss" viewOffset="1000">
    <User title="CrookedMedia"/>
    <Player address="127.0.0.1" machineIdentifier="amp-1" product="Plexamp" state="playing" title="flippy"/>
  </Track>
</MediaContainer>"""

DEVICES = """<MediaContainer size="2">
  <Device name="Arewna's TV" platform="Android" clientIdentifier="tv-1" createdAt="20"/>
  <Device name="flippy" platform="Linux" clientIdentifier="lin-1" createdAt="10"/>
</MediaContainer>"""


def _sessions():
    import xml.etree.ElementTree as ET
    root = ET.fromstring(SESSIONS)
    els = list(root.findall("Video")) + list(root.findall("Track"))
    return [(el, d.player_of(el, {})) for el in els]


class TestChooseSession(unittest.TestCase):
    """The reported bug: Plex lists every session on the server and the tool
    took the first one, so the operator watching on flippy was told about a
    paused Rick and Morty on someone else's desktop."""

    def test_no_claims_prefers_a_player_that_is_actually_playing(self):
        el, player, note = d.choose_session(_sessions(), [])
        self.assertEqual(player["title"], "flippy")
        self.assertEqual(el.get("grandparentTitle"), "South Park")
        self.assertIn("none is claimed", note)

    def test_a_claim_by_title_wins_over_order_and_takes_both_players_of_that_name(self):
        _el, player, note = d.choose_session(_sessions(), ["flippy"])
        self.assertEqual(player["id"], "lin-1")
        self.assertIsNone(note)
        self.assertTrue(all(d.claimed(p, ["flippy"]) for _, p in _sessions() if p["title"] == "flippy"))

    def test_a_claim_by_id_takes_exactly_one_of_two_players_sharing_a_title(self):
        el, player, _ = d.choose_session(_sessions(), ["amp-1"])
        self.assertEqual(player["product"], "Plexamp")
        self.assertEqual(el.tag, "Track")

    def test_a_claim_matches_the_friendly_name_from_device_names(self):
        import xml.etree.ElementTree as ET
        root = ET.fromstring(SESSIONS)
        pairs = [(el, d.player_of(el, {"DESKTOP-C96DMGM": "arewna's desktop"})) for el in root.findall("Video")]
        _, player, _ = d.choose_session(pairs, ["arewna's desktop"])
        self.assertEqual(player["id"], "win-1")

    def test_claims_set_and_none_of_them_playing_reports_nothing_and_says_which_players_are(self):
        el, player, note = d.choose_session(_sessions(), ["living-room"])
        self.assertIsNone(el)
        self.assertIsNone(player)
        self.assertIn("none on a claimed player", note)
        self.assertIn("flippy", note)

    def test_player_argument_overrides_the_claims_for_one_run(self):
        _, player, _ = d.choose_session(_sessions(), ["win-1"], want="lin-1")
        self.assertEqual(player["id"], "lin-1")

    def test_player_argument_that_matches_nothing_is_a_message_not_a_wrong_show(self):
        el, _, note = d.choose_session(_sessions(), [], want="nosuch")
        self.assertIsNone(el)
        self.assertIn("nosuch", note)

    def test_no_sessions_at_all_is_simply_nothing(self):
        self.assertEqual(d.choose_session([], ["flippy"]), (None, None, None))

    def test_claimed_ignores_case_and_surrounding_space(self):
        self.assertTrue(d.claimed({"id": "lin-1", "title": "flippy", "name": "flippy"}, ["  FLIPPY "]))
        self.assertFalse(d.claimed({"id": "lin-1", "title": "flippy", "name": "flippy"}, []))
        self.assertFalse(d.claimed({"id": "", "title": "", "name": ""}, [""]))


class TestRcFile(unittest.TestCase):
    def test_reads_claims_and_server_and_ignores_comments(self):
        with tempfile.TemporaryDirectory() as t:
            rc = os.path.join(t, "scrob.rc")
            with open(rc, "w") as f:
                f.write("# mine\nclaim = flippy\nclaim = lin-1   # the linux one\nserver = https://plex.example\n\nnonsense\nclaim =\n")
            got = d.read_rc(rc)
            self.assertEqual(got["claims"], ["flippy", "lin-1"])
            self.assertEqual(got["server"], "https://plex.example")

    def test_a_missing_rc_is_no_claims_not_an_error(self):
        self.assertEqual(d.read_rc(os.path.join(tempfile.gettempdir(), "no-such-scrob.rc")), {"claims": [], "server": None})

    def test_claim_creates_the_file_with_its_header_and_unclaim_removes_only_that_line(self):
        with tempfile.TemporaryDirectory() as t:
            rc = os.path.join(t, "scrob.rc")
            d.write_claim("flippy", path=rc)
            d.write_claim("lin-1", path=rc)
            body = Path(rc).read_text()
            self.assertIn("claim = flippy", body)
            self.assertIn("claim = lin-1", body)
            self.assertTrue(body.startswith("# hee-scrob rc"))
            self.assertIn("already claimed", d.write_claim("flippy", path=rc))
            d.write_claim("flippy", remove=True, path=rc)
            body = Path(rc).read_text()
            self.assertNotIn("claim = flippy", body)
            self.assertIn("claim = lin-1", body)
            self.assertIn("was not claimed", d.write_claim("nope", remove=True, path=rc))


class TestListPlayers(unittest.TestCase):
    def test_lists_live_sessions_then_known_devices_without_repeating_one(self):
        import xml.etree.ElementTree as ET
        pages = {"/status/sessions": ET.fromstring(SESSIONS), "/devices": ET.fromstring(DEVICES)}
        playing, known = d.list_players("s", "t", {}, ["flippy"], fetch=lambda path: pages[path])
        self.assertEqual([r["id"] for r in playing], ["win-1", "lin-1", "amp-1"])
        self.assertEqual([r["claimed"] for r in playing], [False, True, True])
        self.assertEqual([r["id"] for r in known], ["tv-1"])   # lin-1 is already listed as playing
        text = d.format_players(playing, known, ["flippy"])
        self.assertIn("* flippy", text)
        self.assertIn("  DESKTOP-C96DMGM", text)
        self.assertIn("claimed in", text)

    def test_a_device_list_that_cannot_be_read_still_lists_the_live_sessions(self):
        import xml.etree.ElementTree as ET
        def fetch(path):
            if path == "/devices":
                raise OSError("no route")
            return ET.fromstring(SESSIONS)
        playing, known = d.list_players("s", "t", {}, [], fetch=fetch)
        self.assertEqual(len(playing), 3)
        self.assertEqual(known, [])
        self.assertIn("nothing claimed yet", d.format_players(playing, known, []))
