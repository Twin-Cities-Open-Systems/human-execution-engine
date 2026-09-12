"""hee-release requires: a card's declared requirements are checked before any
build or deploy, and every missing one is reported at once (human-execution-engine#729).

Run: python3 -m unittest tests/test_hee_release_requires.py
"""
import base64, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "tooling" / "bin" / "hee-release"
HEADER = "apiVersion: hee/v1\nkind: Card\nmetadata: { name: t-release, labels: { domain: release } }\n"


def pkesk(keyid_hex: str, new_format=True) -> bytes:
    body = bytes([3]) + bytes.fromhex(keyid_hex) + bytes([18]) + b"\x00\x08\xff"
    return (bytes([0xC1, len(body)]) if new_format else bytes([0x84, len(body)])) + body


def lift(name, until):
    src = TOOL.read_text(); ns = {"base64": base64}
    exec(src[src.index(f"def {name}("):src.index(f"def {until}(")], ns)
    return ns[name]


class Repo:
    def __init__(self, d, spec):
        self.root = Path(d) / "repo"; self.root.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=self.root, check=True)
        (self.root / "release.card.v1.yaml").write_text(HEADER + "spec:\n" + spec)
        subprocess.run(["git", "add", "-A"], cwd=self.root, check=True)
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init"], cwd=self.root, check=True)
        self.env = dict(os.environ, HOME=d, GNUPGHOME=str(Path(d) / "gnupg"))
        (Path(d) / "gnupg").mkdir(mode=0o700)

    def run(self, *args):
        return subprocess.run([sys.executable, str(TOOL), *args], cwd=self.root, capture_output=True, text=True, env=self.env)


class MissingAllAtOnce(unittest.TestCase):
    def test_every_missing_item_reported_together_and_nothing_builds(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Repo(d, "  build: \"touch built.txt\"\n  outputs: [\"built.txt\"]\n"
                           "  requires:\n"
                           "    commands: [hee-no-such-command-729]\n"
                           "    python: [hee_no_such_module_729, PIL_no_such_729]\n"
                           "    files: [missing-729.txt]\n"
                           "    versions: { git: \">=999\" }\n"
                           "    decrypt: [sealed.gpg]\n"
                           "  surfaces:\n    - { name: web, lab: \"touch lab.txt\", promote: \"true\" }\n")
            (repo.root / "sealed.gpg").write_bytes(pkesk("0123456789ABCDEF"))
            r = repo.run("-lab")
            self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
            for word in ("command hee-no-such-command-729", "python module hee_no_such_module_729", "file missing-729.txt",
                         "git is", "needs >=999", "no secret key on this machine is a recipient (0123456789ABCDEF)",
                         "6 of 6 requirement(s) missing for lab"):
                self.assertIn(word, r.stderr)
            self.assertIn("UNKNOWN", r.stderr)
            self.assertFalse((repo.root / "built.txt").exists(), "the build ran despite missing requirements")
            self.assertFalse((repo.root / "lab.txt").exists(), "a surface ran despite missing requirements")

    def test_steps_and_surfaces_are_named_and_credential_is_implied_for_promote(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Repo(d, "  credential: { account: acct, dir: ../secrets }\n"
                           "  requires:\n    commands: [git]\n    promote: { commands: [hee-promote-only-729] }\n"
                           "  surfaces:\n    - { name: web, requires: { lab: { files: [lab-only-729.txt] } }, lab: \"true\", promote: \"true\" }\n")
            r = repo.run("-requires")
            self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
            self.assertIn("command hee-promote-only-729 is not on PATH -- needed by promote", r.stderr)
            self.assertIn("file lab-only-729.txt does not exist -- needed by lab (web)", r.stderr)
            self.assertIn("file ../secrets/acct.gpg does not exist -- needed by promote (credential)", r.stderr)
            self.assertIn("sealed file ../secrets/acct.gpg does not exist", r.stderr)
            self.assertNotIn("hee-promote-only-729", repo.run("-lab").stderr, "a promote-only requirement blocked lab")


class Satisfied(unittest.TestCase):
    def test_met_requirements_pass_and_the_step_runs(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Repo(d, "  build: \"touch built.txt\"\n  outputs: [\"built.txt\"]\n"
                           "  requires:\n    commands: [git]\n    python: [json]\n    files: [release.card.v1.yaml]\n"
                           "    versions: { git: \">=1\" }\n"
                           "  surfaces:\n    - { name: web, lab: \"true\", promote: \"true\" }\n")
            r = repo.run("-requires")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("all 4 requirement(s) met for lab, cut, promote", r.stdout)
            r = repo.run("-lab")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertTrue((repo.root / "built.txt").exists())

    @unittest.skipUnless(shutil.which("gpg"), "gpg not installed")
    def test_decrypt_met_by_a_real_recipient_key_without_decrypting(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as d:   # a short GNUPGHOME: gpg-agent's socket path has a length limit
            repo = Repo(d, "  requires:\n    decrypt: [sealed.gpg]\n  surfaces:\n    - { name: web, lab: \"true\", promote: \"true\" }\n")
            gpg = ["gpg", "--batch", "--pinentry-mode", "loopback", "--passphrase", ""]
            try:
                subprocess.run(gpg + ["--quick-gen-key", "req-test <req-test@example.invalid>", "future-default", "default", "never"],
                               env=repo.env, check=True, capture_output=True)
                subprocess.run(["gpg", "--batch", "--trust-model", "always", "-r", "req-test@example.invalid", "-o",
                                str(repo.root / "sealed.gpg"), "-e", str(repo.root / "release.card.v1.yaml")],
                               env=repo.env, check=True, capture_output=True)
                r = repo.run("-requires")
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            finally:
                subprocess.run(["gpgconf", "--kill", "gpg-agent"], env=repo.env, capture_output=True)


class NoRequiresField(unittest.TestCase):
    def test_a_card_without_requires_runs_as_before(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Repo(d, "  surfaces:\n    - { name: web, lab: \"touch lab.txt\", promote: \"true\" }\n")
            r = repo.run("-lab")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertNotIn("requires", r.stdout + r.stderr)
            self.assertTrue((repo.root / "lab.txt").exists())
            self.assertEqual(repo.run("-requires").returncode, 1)


class Recipients(unittest.TestCase):
    def test_binary_old_new_and_armored(self):
        f = lift("pgp_recipients", "secret_keyids")
        two = pkesk("7F2480F15809ACD8") + pkesk("01C9F82A7582A4DC", new_format=False) + bytes([0xD2, 0x05]) + b"xxxxx"
        self.assertEqual(f(two), ["7F2480F15809ACD8", "01C9F82A7582A4DC"])
        armored = (b"-----BEGIN PGP MESSAGE-----\nVersion: t\n\n" + base64.b64encode(two) + b"\n=abcd\n-----END PGP MESSAGE-----\n")
        self.assertEqual(f(armored), ["7F2480F15809ACD8", "01C9F82A7582A4DC"])
        self.assertEqual(f(b"not openpgp"), [])


if __name__ == "__main__":
    unittest.main()
