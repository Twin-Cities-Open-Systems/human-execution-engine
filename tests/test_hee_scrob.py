#!/usr/bin/env python3
"""test_hee_scrob: HEE#670 path-map coverage. Pure functions only, no
Plex, no network."""
import contextlib
import importlib.machinery
import importlib.util
import io
import os
import tempfile
import unittest
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
