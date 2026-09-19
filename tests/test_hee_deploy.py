"""hee-deploy blog -- gate order, dry-run assembly, and the -to prod procedure.

Every case drives the tool through subprocess with -dry-run and -resume
pointing at a temp directory this file builds, so no test needs a real
git checkout, network, or a real resume repo (SPEC.md's own test contract).
"""
import importlib.machinery
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tooling" / "bin" / "hee-deploy"


def run(*args, cwd=None):
    return subprocess.run(
        [sys.executable, str(TOOL), *args],
        cwd=cwd,
        capture_output=True,
        check=False,
        text=True,
    )


def make_resume(root: Path, opers=("alice",)):
    """A resume checkout shaped just enough for the gates: one profile.json
    per oper, carrying meta.media_routing (SPEC's own fixture shape)."""
    for oper in opers:
        profile_dir = root / "profiles" / oper
        profile_dir.mkdir(parents=True, exist_ok=True)
        (profile_dir / "profile.json").write_text(
            json.dumps({"meta": {"media_routing": f"{oper}.media.tcos.us"}})
        )
    return root


def make_post(root: Path, name="my-new-blog", body=None, images=None):
    """images: dict of filename -> note text or None (no note)."""
    post_dir = root / name
    post_dir.mkdir(parents=True, exist_ok=True)
    (post_dir / "blog.md").write_text(body if body is not None else "# Title of new blog\n")
    for filename, note in (images or {}).items():
        (post_dir / filename).write_bytes(b"\x89PNG\r\n\x1a\n")
        if note is not None:
            (post_dir / f"{filename}.md").write_text(note)
    return post_dir


class HelpTests(unittest.TestCase):
    def test_help_executes_nothing_from_any_position(self):
        with tempfile.TemporaryDirectory() as tmp:
            # A directory that would fail every gate if the tool actually
            # ran past help -- proof that help really executed nothing.
            missing_dir = Path(tmp) / "does-not-exist"
            cases = [
                ["help"],
                ["--help"],
                ["-h"],
                ["blog", "help"],
                ["blog", str(missing_dir), "help", "-to", "prod"],
                ["blog", str(missing_dir), "-dry-run", "help"],
            ]
            for argv in cases:
                with self.subTest(argv=argv):
                    r = run(*argv)
                    self.assertEqual(r.returncode, 0, r.stderr)
                    self.assertIn("SYNOPSIS", r.stdout)
                    self.assertFalse(missing_dir.exists())

    def test_help_notes_ignored_tail_on_stderr(self):
        r = run("blog", "help", "-to", "prod")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("not executed", r.stderr)
        self.assertIn("-to", r.stderr)


class GateTests(unittest.TestCase):
    def test_title_only_warns_and_deploys_on_lab(self):
        with tempfile.TemporaryDirectory() as tmp:
            resume = make_resume(Path(tmp) / "resume")
            post_dir = make_post(Path(tmp) / "posts", body="# Title of new blog\n")
            r = run("blog", str(post_dir), "-oper", "alice", "-resume", str(resume), "-dry-run")
            self.assertEqual(r.returncode, 1, r.stderr)
            self.assertIn("⚠️ WARNING", r.stderr)
            self.assertIn("title-only", r.stderr)

    def test_title_only_is_critical_on_prod(self):
        with tempfile.TemporaryDirectory() as tmp:
            resume = make_resume(Path(tmp) / "resume")
            post_dir = make_post(Path(tmp) / "posts", body="# Title of new blog\n")
            r = run(
                "blog", str(post_dir), "-oper", "alice", "-resume", str(resume),
                "-dry-run", "-to", "prod",
            )
            self.assertEqual(r.returncode, 2, r.stderr)
            self.assertIn("❌ CRITICAL", r.stderr)
            self.assertIn("title-only", r.stderr)

    def test_note_without_image_is_critical(self):
        with tempfile.TemporaryDirectory() as tmp:
            resume = make_resume(Path(tmp) / "resume")
            post_dir = make_post(
                Path(tmp) / "posts",
                body="# Title of new blog\n\nSome real prose.\n",
            )
            # A note for an image that was never written.
            (post_dir / "b.png.md").write_text("a note with nothing to caption\n")
            r = run("blog", str(post_dir), "-oper", "alice", "-resume", str(resume), "-dry-run")
            self.assertEqual(r.returncode, 2, r.stderr)
            self.assertIn("❌ CRITICAL", r.stderr)
            self.assertIn("b.png.md", r.stderr)

    def test_unknown_oper_lists_profiles(self):
        with tempfile.TemporaryDirectory() as tmp:
            resume = make_resume(Path(tmp) / "resume", opers=("alice", "bob"))
            post_dir = make_post(
                Path(tmp) / "posts",
                body="# Title of new blog\n\nSome real prose.\n",
            )
            r = run("blog", str(post_dir), "-oper", "nobody", "-resume", str(resume), "-dry-run")
            self.assertEqual(r.returncode, 2, r.stderr)
            self.assertIn("❌ CRITICAL", r.stderr)
            self.assertIn("alice", r.stderr)
            self.assertIn("bob", r.stderr)


class AssemblyTests(unittest.TestCase):
    def _full_post(self, tmp):
        resume = make_resume(Path(tmp) / "resume")
        post_dir = make_post(
            Path(tmp) / "posts",
            body="# Title of new blog\n\nSome real prose about the trip.\n",
            images={
                "a.png": "first image, the cabin\n\nA longer caption paragraph about the cabin.\n",
                "b.png": "second image, the lake\n",
            },
        )
        return resume, post_dir

    def test_full_directory_deploys_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            resume, post_dir = self._full_post(tmp)
            r = run("blog", str(post_dir), "-oper", "alice", "-resume", str(resume), "-dry-run")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(r.stderr.strip(), "")

            self.assertIn("----- post -----", r.stdout)
            # The markers are printed on their own print() calls, so the
            # captured section carries a leading/trailing newline from
            # those -- strip it before treating this as the post body.
            post = r.stdout.split("----- post -----")[1].strip("\n")
            post_lines = post.splitlines()

            self.assertEqual(post_lines[0], "# Title of new blog")
            self.assertTrue(post_lines[1].startswith("**Date:**"))
            self.assertRegex(post_lines[1], r"\*\*Date:\*\* \d{4}-\d{2}-\d{2}")

            first_img = post.find("![first image, the cabin](a.png)")
            second_img = post.find("![second image, the lake](b.png)")
            self.assertGreater(first_img, -1)
            self.assertGreater(second_img, -1)
            self.assertLess(first_img, second_img, "images must appear in sort order")
            self.assertIn("A longer caption paragraph about the cabin.", post)

            self.assertIn("would write:", r.stdout)
            self.assertIn("profiles/alice/blog/my-new-blog.md", r.stdout)
            self.assertIn("profiles/alice/blog/my-new-blog/a.png", r.stdout)
            self.assertIn("profiles/alice/blog/my-new-blog/b.png", r.stdout)

    def test_to_prod_prints_release_procedure(self):
        with tempfile.TemporaryDirectory() as tmp:
            resume, post_dir = self._full_post(tmp)
            r = run(
                "blog", str(post_dir), "-oper", "alice", "-resume", str(resume),
                "-dry-run", "-to", "prod",
            )
            self.assertEqual(r.returncode, 3, r.stderr)
            self.assertIn(
                "hee release -lab -repos resume            # already done by this tool",
                r.stdout,
            )
            self.assertIn(
                "hee release -cut -repos resume -yes       # release commit + PR; "
                "merging it is the sign-off",
                r.stdout,
            )
            self.assertIn(
                "hee release -promote -repos resume -yes   # prod; the operator's act",
                r.stdout,
            )


class ReviewFindings(unittest.TestCase):
    """The failing inputs pr-reviewer named (fleet-ops job deploy-blog-review,
    2026-09-19), each kept as a test."""

    FIX = ROOT / "tests" / "fixtures" / "deploy-blog"

    def test_ci_example_exits_0_with_both_figures(self):
        r = run("blog", str(self.FIX / "my-new-blog"), "-oper", "alice",
                "-resume", str(self.FIX / "resume"), "-dry-run", cwd=ROOT)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("![a red square](a.png)", r.stdout)
        self.assertIn("![a blue square](b.png)", r.stdout)
        self.assertLess(r.stdout.index("a.png"), r.stdout.index("b.png"))

    def test_non_ascii_title_under_c_locale_is_not_a_crash(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td) / "cafe"
            d.mkdir()
            (d / "blog.md").write_text("# Caf\u00e9\n\nProse.\n", encoding="utf-8")
            env = dict(os.environ, LC_ALL="C", LANG="C", PYTHONUTF8="0")
            r = subprocess.run([sys.executable, str(TOOL), "blog", str(d), "-oper", "alice",
                                "-resume", str(self.FIX / "resume"), "-dry-run"],
                               capture_output=True, text=True, check=False, env=env)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("Caf\u00e9", r.stdout)
            self.assertNotIn("Traceback", r.stderr)

    def test_oper_that_is_not_a_slug_is_refused(self):
        r = run("blog", str(self.FIX / "my-new-blog"), "-oper", "../spencer",
                "-resume", str(self.FIX / "resume"), "-dry-run", cwd=ROOT)
        self.assertEqual(r.returncode, 2)
        self.assertIn("CRITICAL", r.stderr)
        self.assertIn("not a slug", r.stderr)

    def test_credentials_in_a_remote_url_are_redacted(self):
        loader = importlib.machinery.SourceFileLoader("hee_deploy", str(TOOL))
        spec = importlib.util.spec_from_loader("hee_deploy", loader)
        mod = importlib.util.module_from_spec(spec)
        loader.exec_module(mod)
        out = mod._safe("fatal: Authentication failed for 'https://x-access-token:ghp_AbC123@github.com/o/r.git/'")
        self.assertNotIn("ghp_AbC123", out)
        self.assertIn("https://***@github.com/o/r.git/", out)


if __name__ == "__main__":
    unittest.main()
