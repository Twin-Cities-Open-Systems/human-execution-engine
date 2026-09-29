"""hee-git-tag: with several signing keys in the keyring, $HEE_SIGN_KEY picks one (this is how `hee release
-promote`, which calls the tool itself, is told), --key beats it, and with neither the tool refuses to guess."""
import os, subprocess, sys, tempfile, unittest
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "tooling" / "bin" / "hee-git-tag"


def fpr(env, uid):
    out = subprocess.run(["gpg", "--list-keys", "--with-colons", uid], env=env, capture_output=True, text=True).stdout
    return out.split("fpr:::::::::")[1].split(":")[0]


class SignKeyEnv(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.home = cls.tmp.name
        cls.env = {k: v for k, v in os.environ.items() if k != "HEE_SIGN_KEY"}
        cls.env.update(GNUPGHOME=cls.home, HOME=cls.home)
        for uid in ("a@test", "b@test"):
            subprocess.run(["gpg", "--batch", "--quick-gen-key", "--passphrase", "", uid, "ed25519", "cert,sign", "0"],
                           env=cls.env, check=True, capture_output=True)
        cls.a, cls.b = fpr(cls.env, "a@test"), fpr(cls.env, "b@test")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_tool(self, *args, **extra):
        env = dict(self.env, **extra)
        return subprocess.run([sys.executable, str(TOOL), *args], env=env, capture_output=True, text=True, cwd=self.home)

    def test_two_keys_and_nothing_chosen_refuses(self):
        r = self.run_tool("--show-key")
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("no single key", r.stderr)
        self.assertIn("HEE_SIGN_KEY", r.stderr)

    def test_env_picks_the_key(self):
        r = self.run_tool("--show-key", HEE_SIGN_KEY=self.b)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(r.stdout.splitlines()[0], self.b)
        self.assertIn("HEE_SIGN_KEY", r.stdout)

    def test_flag_beats_env(self):
        r = self.run_tool("--show-key", "--key", self.a, HEE_SIGN_KEY=self.b)
        self.assertEqual(r.stdout.splitlines()[0], self.a)

    def test_env_key_signs_a_real_tag(self):
        repo = Path(self.home) / "repo"
        repo.mkdir()
        git = dict(self.env, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@test", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@test")
        subprocess.run(["git", "init", "-q"], cwd=repo, env=git, check=True)
        subprocess.run(["git", "commit", "-q", "--allow-empty", "-m", "c"], cwd=repo, env=git, check=True)
        r = subprocess.run([sys.executable, str(TOOL), "v1", "-m", "release v1", "HEAD", "--yes"],
                           cwd=repo, env=dict(git, HEE_SIGN_KEY=self.b), capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        v = subprocess.run(["git", "verify-tag", "-v", "v1"], cwd=repo, env=git, capture_output=True, text=True)
        self.assertIn(self.b[-16:], v.stderr)


if __name__ == "__main__":
    unittest.main()
