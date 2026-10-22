"""hee gen-skills -- the repo is where you run it, and an ephemeral skill
renders into its job, never into the ratified tree.

Before 2026-10-22 the tool read hee/skills/ and wrote .claude/skills/
relative to its own install path, so a fleet could never render its own
skills (the hee-name install-path bug, fleet-ops#882, in a second tool).
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tooling" / "bin" / "hee-gen-skills"
FIX = ROOT / "tests" / "fixtures" / "skills"
RATIFIED = ROOT / "hee" / "skills" / "ratify-contract-v1.skill.yaml"


def run(*args, cwd=None):
    env = dict(os.environ, HEE_STATUS_STYLE="plain")
    return subprocess.run([sys.executable, str(TOOL), *args], capture_output=True,
                          text=True, env=env, cwd=cwd or ROOT, check=False)


def git_repo(tmp):
    """A throwaway repository carrying one ratified Skill object."""
    repo = Path(tmp) / "fleet"
    (repo / "hee" / "skills").mkdir(parents=True)
    shutil.copy(RATIFIED, repo / "hee" / "skills" / RATIFIED.name)
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    return repo


class RepoResolution(unittest.TestCase):
    def test_repo_flag_renders_that_repo_not_the_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = git_repo(tmp)
            dry = run("--repo", str(repo))
            self.assertEqual(dry.returncode, 1, dry.stdout + dry.stderr)
            self.assertIn("would create", dry.stdout)
            self.assertFalse((repo / ".claude").exists(), "dry run wrote")
            wet = run("--repo", str(repo), "--write")
            self.assertEqual(wet.returncode, 0, wet.stdout + wet.stderr)
            dest = repo / ".claude" / "skills" / "ratify-contract" / "SKILL.md"
            self.assertTrue(dest.is_file())
            self.assertTrue(dest.read_text().startswith("---\nname: ratify-contract\n"))
            again = run("--repo", str(repo))
            self.assertEqual(again.returncode, 0)
            self.assertIn("unchanged", again.stdout)

    def test_cwd_inside_a_repo_resolves_that_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = git_repo(tmp)
            sub = repo / "hee" / "skills"
            wet = run("--write", cwd=sub)
            self.assertEqual(wet.returncode, 0, wet.stdout + wet.stderr)
            self.assertTrue((repo / ".claude" / "skills" / "ratify-contract" / "SKILL.md").is_file())
            # and nothing landed in the engine checkout from this run
            self.assertNotIn(str(ROOT), wet.stdout)

    def test_no_skills_tree_is_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["git", "init", "-q", tmp], check=True)
            r = run(cwd=tmp)
            self.assertEqual(r.returncode, 3)
            self.assertIn("no ", r.stderr)


class Ephemeral(unittest.TestCase):
    def test_ephemeral_object_in_the_ratified_tree_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = git_repo(tmp)
            shutil.copy(FIX / "job-skill.skill.yaml", repo / "hee" / "skills" / "job.skill.yaml")
            r = run("--repo", str(repo), "--write")
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
            self.assertIn("ephemeral", r.stderr)
            self.assertFalse((repo / ".claude" / "skills" / "rename-targets-conf").exists())

    def test_skill_renders_into_the_job(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "in" / ".claude" / "skills"
            r = run("--skill", str(FIX / "job-skill.skill.yaml"), "--out", str(out), "--write")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            body = (out / "rename-targets-conf" / "SKILL.md").read_text()
            head = body.split("---")[1]
            self.assertIn("\ndisable-model-invocation: true\n", head)
            self.assertIn("\ncontext: fork\n", head)
            self.assertIn("\nallowed-tools: [Read, Grep, Edit]\n", head)
            self.assertNotIn("{", head, "a scalar key rendered as a flow map")
            self.assertIn("**EPHEMERAL.** Written for fleet-ops/0151", body)

    def test_skill_needs_out(self):
        r = run("--skill", str(FIX / "job-skill.skill.yaml"))
        self.assertEqual(r.returncode, 3)
        self.assertIn("--out", r.stderr)

    def test_committed_rendering_is_current(self):
        # The # ci example: the fixture's rendered form is committed, and a
        # dry run against it must find nothing to change.
        r = run("--skill", str(FIX / "job-skill.skill.yaml"), "--out", str(FIX / "rendered"))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("unchanged", r.stdout)


class Frontmatter(unittest.TestCase):
    def test_derived_keys_cannot_be_overridden(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "bad.skill.yaml"
            src.write_text((FIX / "job-skill.skill.yaml").read_text().replace(
                "      context: fork", "      context: fork\n      name: other"))
            r = run("--skill", str(src), "--out", tmp)
            self.assertEqual(r.returncode, 2)
            self.assertIn("frontmatter.name", r.stderr)

    def test_unknown_key_is_emitted_with_a_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "odd.skill.yaml"
            src.write_text((FIX / "job-skill.skill.yaml").read_text().replace(
                "      context: fork", "      context: fork\n      colour: blue"))
            r = run("--skill", str(src), "--out", tmp, "--write")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("colour", r.stderr)
            self.assertIn("\ncolour: blue\n", (Path(tmp) / "rename-targets-conf" / "SKILL.md").read_text())


if __name__ == "__main__":
    unittest.main()
