#!/usr/bin/env python3
"""
Unit tests for hee_hostmap.

Real known example hostnames/paths from this session live here, as
data proving the generic pattern classifies them correctly -- not as
a constraint baked into the matching regex itself (see __init__.py's
module docstring for why that distinction matters).
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from hee_hostmap import classify_host, is_clean_path


class TestClassifyHost(unittest.TestCase):

    def test_apex(self):
        self.assertEqual(classify_host("tcos.us"), {"person": None, "service": None, "env": None})
        self.assertEqual(classify_host("lab.tcos.us"), {"person": None, "service": None, "env": "lab"})

    def test_known_real_service_no_person(self):
        # foo.tcos.us -- the shared dogfood slot, no person prefix
        self.assertEqual(classify_host("foo.tcos.us"), {"person": None, "service": "foo", "env": None})
        # man.tcos.us -- external infra, kept as-is, matches the shape
        self.assertEqual(classify_host("man.tcos.us"), {"person": None, "service": "man", "env": None})

    def test_known_real_service_with_person(self):
        self.assertEqual(
            classify_host("spencer.media.tcos.us"),
            {"person": "spencer", "service": "media", "env": None},
        )
        self.assertEqual(
            classify_host("spencer.media.lab.tcos.us"),
            {"person": "spencer", "service": "media", "env": "lab"},
        )
        self.assertEqual(
            classify_host("spencer.blog.tcos.us"),
            {"person": "spencer", "service": "blog", "env": None},
        )

    def test_agent_person(self):
        self.assertEqual(
            classify_host("touchy-claude.blog.tcos.us"),
            {"person": "touchy-claude", "service": "blog", "env": None},
        )

    def test_unknown_service_still_matches_shape(self):
        # the whole point: a service name never seen before still
        # classifies correctly, no code change required
        self.assertEqual(
            classify_host("spencer.podcast.tcos.us"),
            {"person": "spencer", "service": "podcast", "env": None},
        )
        self.assertEqual(
            classify_host("wiki.lab.tcos.us"),
            {"person": None, "service": "wiki", "env": "lab"},
        )

    def test_wrong_tld_does_not_match(self):
        self.assertIsNone(classify_host("tcos.com"))
        self.assertIsNone(classify_host("spencer.media.tcos.org"))

    def test_case_insensitive(self):
        self.assertEqual(
            classify_host("Spencer.Media.TCOS.US"),
            {"person": "spencer", "service": "media", "env": None},
        )

    def test_real_lab_tcos_us_zone_entries(self):
        # every real name in /etc/bind/zones/db.lab.tcos.us as of
        # 2026-08-28 -- lab-internal tooling, no person prefix. All
        # classify as a service under env=lab; whether each is
        # *expected* to have a tcos.us mirror is SITEMAP-PROPOSED.yaml's
        # call (lab_only_no_mirror_expected), not this module's.
        for name in [
            "ns1", "bastion", "haproxy", "view", "thesis-engine",
            "owner-dogfood", "container-factory", "lab-to-prod-deploy",
            "mx1",
        ]:
            with self.subTest(name=name):
                self.assertEqual(
                    classify_host(f"{name}.lab.tcos.us"),
                    {"person": None, "service": name, "env": "lab"},
                )

    def test_real_external_non_pve_hosts(self):
        # rtfm/man on the DigitalOcean box (159.65.46.8), outside the
        # pve/haproxy stack entirely -- still classify as a plain
        # shape match. rtfm is being killed (real DNS record removed,
        # 2026-08-28); a shape match here is about syntax, not
        # whether the record still exists afterward.
        self.assertEqual(classify_host("rtfm.tcos.us"), {"person": None, "service": "rtfm", "env": None})
        self.assertEqual(classify_host("man.tcos.us"), {"person": None, "service": "man", "env": None})

    def test_dead_or_never_real_names_still_match_shape(self):
        # confirmed this session to not resolve / not be provisioned
        # (www, resume, people, bofh) -- shape-matching them anyway is
        # correct: this module classifies syntax, not realness.
        for host, expected in [
            ("www.tcos.us", {"person": None, "service": "www", "env": None}),
            ("resume.tcos.us", {"person": None, "service": "resume", "env": None}),
            ("people.tcos.us", {"person": None, "service": "people", "env": None}),
            ("bofh.tcos.us", {"person": None, "service": "bofh", "env": None}),
            ("nuc1-claude.media.tcos.us", {"person": "nuc1-claude", "service": "media", "env": None}),
        ]:
            with self.subTest(host=host):
                self.assertEqual(classify_host(host), expected)

    def test_malformed_hosts_do_not_match(self):
        for host in ["", "tcos.us.", ".tcos.us", "a..b.tcos.us", "-leadinghyphen.tcos.us", "tcos.us/path"]:
            with self.subTest(host=host):
                self.assertIsNone(classify_host(host))


class TestIsCleanPath(unittest.TestCase):

    def test_clean_paths_pass(self):
        for path in ["/", "/contracts", "/people/spencer"]:
            self.assertTrue(is_clean_path(path), path)

    def test_ugly_paths_fail(self):
        for path in ["/contracts.html", "/index.html", "/tux-tattoo/", "/a//b"]:
            self.assertFalse(is_clean_path(path), path)

    def test_more_malformed_paths_fail(self):
        for path in ["", "contracts", "/contracts?q=1", "/-leadinghyphen", "//"]:
            self.assertFalse(is_clean_path(path), path)

    def test_real_page_slugs_pass(self):
        for path in ["/roadmap", "/review", "/follow-up", "/todo", "/plan"]:
            self.assertTrue(is_clean_path(path), path)


if __name__ == "__main__":
    unittest.main()
