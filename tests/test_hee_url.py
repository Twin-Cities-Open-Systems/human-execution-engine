"""hee url -- slugs are derived, records are HEE objects, the tree redirects.

Everything here runs with no network: the store is a temporary directory and
the config is an explicit file, so ~/.config/hee/url.yaml on the test host
cannot leak in.
"""
import hashlib
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tooling" / "bin" / "hee-url"
sys.path.insert(0, str(ROOT / "library" / "py"))
import hee_url as U

EXAMPLE = "https://example.com/some/other-url.html"


def cfg(**over):
    return U.load_config(Path("/dev/null"), over)


class Slugs(unittest.TestCase):
    def test_default_is_eight_chars_with_goose(self):
        c = cfg()
        for url in (EXAMPLE, "https://tcos.us/", "https://tcos.us/people"):
            s = U.derive_slug(url, c)
            self.assertEqual(len(s), 8, s)
            self.assertIn("goose", s)
            self.assertRegex(s, r"^[a-z0-9]+$")

    def test_same_url_same_slug(self):
        self.assertEqual(U.derive_slug(EXAMPLE, cfg()), U.derive_slug(EXAMPLE, cfg()))
        self.assertNotEqual(U.derive_slug(EXAMPLE, cfg()), U.derive_slug(EXAMPLE + "?x", cfg()))

    def test_infix_position_varies(self):
        c = cfg()
        positions = {U.derive_slug(f"https://tcos.us/{i}", c).index("goose") for i in range(60)}
        self.assertGreater(len(positions), 1, "goose always at the same offset")

    def test_no_infix_and_four_chars(self):
        c = cfg(infix="", length=4)
        s = U.derive_slug(EXAMPLE, c)
        self.assertEqual(len(s), 4)
        self.assertNotIn("goose", s)

    def test_length_must_leave_room(self):
        with self.assertRaises(U.UrlError):
            cfg(length=5)
        with self.assertRaises(U.UrlError):
            cfg(length=4, infix="goose")

    def test_salt_steps_to_a_different_slug(self):
        c = cfg()
        self.assertNotEqual(U.derive_slug(EXAMPLE, c, 0), U.derive_slug(EXAMPLE, c, 1))

    def test_hand_slug_rules(self):
        c = cfg()
        self.assertEqual(U.check_slug("axgoose8", c), "axgoose8")
        for bad in ("AxGoose8", "ax_goose", "nogeese", "-goose", "index", "_redirects"):
            with self.assertRaises(U.UrlError, msg=bad):
                U.check_slug(bad, c)
        self.assertEqual(U.check_slug("nogeese", cfg(infix="")), "nogeese")


class Config(unittest.TestCase):
    def test_unknown_key_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "url.yaml"
            p.write_text("lenght: 4\n")
            with self.assertRaises(U.UrlError) as ctx:
                U.load_config(p)
            self.assertIn("lenght", str(ctx.exception))

    def test_file_then_flags(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "url.yaml"
            p.write_text("length: 6\ninfix: ''\nbase: https://s.example\n")
            c = U.load_config(p)
            self.assertEqual((c["length"], c["infix"], c["base"]), (6, "", "https://s.example"))
            c = U.load_config(p, {"length": 9})
            self.assertEqual(c["length"], 9)

    def test_init_text_round_trips(self):
        text = U.default_config_text()
        self.assertEqual(yaml.safe_load(text), None)  # every key commented out
        live = yaml.safe_load("\n".join(ln[1:] for ln in text.splitlines() if ln.startswith("#") and ":" in ln[1:].split(" ")[0]))
        self.assertEqual(set(live), set(U.DEFAULTS))


class Store(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.c = cfg(store=self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_add_is_idempotent_and_lint_shaped(self):
        rec, created = U.add(EXAMPLE, self.c)
        self.assertTrue(created)
        again, created2 = U.add(EXAMPLE, self.c)
        self.assertFalse(created2)
        self.assertEqual(rec["spec"]["slug"], again["spec"]["slug"])
        self.assertEqual(len(list(Path(self.tmp.name).glob("*.yaml"))), 1)
        ann = rec["metadata"]["annotations"]
        self.assertEqual(ann["inuid"], hashlib.sha256(ann["inuid_seed"].encode()).hexdigest())
        self.assertEqual(ann["inuid_seed"], rec["spec"]["short"])
        self.assertEqual(rec["apiVersion"], "hee/v1")
        self.assertEqual(rec["spec"]["short"], f"https://u.tcos.us/{rec['spec']['slug']}/")
        on_disk = yaml.safe_load(U.record_path(rec["spec"]["slug"], self.c).read_text())
        self.assertEqual(on_disk, rec)

    def test_hand_slug_taken(self):
        U.add(EXAMPLE, self.c, slug="axgoose8")
        with self.assertRaises(U.UrlError):
            U.add("https://tcos.us/", self.c, slug="axgoose8")
        rec, _ = U.add("https://tcos.us/", self.c, slug="axgoose8", force=True)
        self.assertEqual(rec["spec"]["url"], "https://tcos.us/")

    def test_collision_steps_past(self):
        s = U.derive_slug(EXAMPLE, self.c)
        U.add("https://tcos.us/", self.c, slug=s)  # occupy the derived slug
        rec, _ = U.add(EXAMPLE, self.c)
        self.assertNotEqual(rec["spec"]["slug"], s)
        self.assertIn("goose", rec["spec"]["slug"])

    def test_bad_url(self):
        for bad in ("example.com", "ftp://x/y", "https://", "https://a b"):
            with self.assertRaises(U.UrlError, msg=bad):
                U.add(bad, self.c)

    def test_search_and_remove(self):
        U.add(EXAMPLE, self.c, tags=["demo", "docs"], note="the example")
        U.add("https://tcos.us/people", self.c)
        recs = U.load_all(self.c)
        self.assertEqual(len(U.search(["example"], recs)), 1)
        self.assertEqual(len(U.search(["demo", "tcos"], recs)), 0)
        self.assertEqual(len(U.search(["demo", "tcos"], recs, use_or=True)), 2)
        slug = U.search(["people"], recs)[0]
        U.remove(slug, self.c)
        self.assertIsNone(U.load(slug, self.c))
        with self.assertRaises(U.UrlError):
            U.remove(slug, self.c)


class Build(unittest.TestCase):
    def test_tree(self):
        with tempfile.TemporaryDirectory() as store, tempfile.TemporaryDirectory() as out:
            c = cfg(store=store)
            U.add(EXAMPLE, c, slug="axgoose8")
            slugs = U.build(c, Path(out))
            self.assertEqual(slugs, ["axgoose8"])
            redirects = (Path(out) / "_redirects").read_text().splitlines()
            self.assertIn(f"/axgoose8 {EXAMPLE} 302", redirects)
            self.assertIn(f"/axgoose8/ {EXAMPLE} 302", redirects)
            page = (Path(out) / "axgoose8" / "index.html").read_text()
            self.assertIn(f'url={EXAMPLE}"', page)
            self.assertTrue((Path(out) / "index.html").is_file())
            self.assertTrue((Path(out) / "404.html").is_file())

    def test_html_is_escaped(self):
        with tempfile.TemporaryDirectory() as store, tempfile.TemporaryDirectory() as out:
            c = cfg(store=store)
            U.add('https://example.com/?q="><script>', c)
            U.build(c, Path(out))
            page = next(Path(out).glob("*/index.html")).read_text()
            self.assertNotIn("<script>", page)


class Cli(unittest.TestCase):
    def run_tool(self, *args, env=None):
        e = dict(os.environ, HEE_URL_CONFIG="/dev/null")
        e.update(env or {})
        r = subprocess.run([str(TOOL), *args], capture_output=True, text=True, env=e, check=False)
        return r.returncode, r.stdout, r.stderr

    def test_help_runs_nothing_to_its_right(self):
        with tempfile.TemporaryDirectory() as store:
            rc, out, _ = self.run_tool("--store", store, "add", "help", EXAMPLE)
            self.assertEqual(rc, 0)
            self.assertIn("SYNOPSIS", out)
            self.assertEqual(list(Path(store).glob("*.yaml")), [])

    def test_add_get_list(self):
        with tempfile.TemporaryDirectory() as store:
            rc, out, err = self.run_tool("--store", store, "add", EXAMPLE, "--slug", "axgoose8")
            self.assertEqual(rc, 0, err)
            self.assertEqual(out.strip(), "https://u.tcos.us/axgoose8/")
            rc, out, _ = self.run_tool("--store", store, "get", "axgoose8")
            self.assertEqual((rc, out.strip()), (0, EXAMPLE))
            rc, out, _ = self.run_tool("--store", store, "list")
            self.assertEqual(rc, 0)
            self.assertIn("axgoose8", out)
            rc, _, err = self.run_tool("--store", store, "get", "nope")
            self.assertEqual(rc, 1)
            self.assertIn("CRITICAL", err)

    def test_verify_unreachable_is_unknown(self):
        # A base nothing listens on: every probe fails, the worst level is
        # UNKNOWN, and the exit code says so. No network is touched.
        with tempfile.TemporaryDirectory() as store:
            rc, _, err = self.run_tool("--store", store, "--base", "http://127.0.0.1:9", "add", EXAMPLE)
            self.assertEqual(rc, 0, err)
            rc, _, err = self.run_tool("--store", store, "verify")
            self.assertEqual(rc, 3, err)
            self.assertIn("UNKNOWN", err)
            self.assertIn("1 UNKNOWN", err)

    def test_fixture_store(self):
        rc, out, _ = self.run_tool("--store", str(ROOT / "tests/fixtures/urls"), "get", "axgoose8")
        self.assertEqual((rc, out.strip()), (0, EXAMPLE))


if __name__ == "__main__":
    unittest.main()
