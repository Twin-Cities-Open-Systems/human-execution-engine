"""hee-check: two false-positive classes that turned other repos red.

1. refs -- a reference is resolved file-relative as well as root-relative.
   tick-task's frontend/package.json names "src/main.tsx" (i.e.
   frontend/src/main.tsx, present) -- root-only resolution called it broken.
2. signatures -- a .asc holding a PGP PUBLIC KEY BLOCK is a committed key,
   not a detached signature. fleet-ops keeps two host keys that way; they
   were reported as "orphan signature, signs nothing".

Both fixes may only turn a false failure into a pass: a genuinely broken ref,
and a real orphan detached signature, must still be reported.
"""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECK = ROOT / "tooling" / "bin" / "hee-check"
sys.path.insert(0, str(ROOT / "library" / "py"))
from hee_refs import scan  # noqa: E402


def _mk(d):
    r = Path(d)
    (r / "frontend").mkdir()
    (r / "frontend" / "src").mkdir()
    (r / "frontend" / "src" / "main.tsx").write_text("export {}\n")
    # package.json's "main" is file-relative (npm resolves it against the
    # package dir): src/main.tsx == frontend/src/main.tsx here.
    (r / "frontend" / "package.json").write_text('{\n  "main": "src/main.tsx"\n}\n')
    # A root-level src/ so "src" IS a top-level dir and the token counts.
    (r / "src").mkdir()
    (r / "src" / "keep.txt").write_text("x\n")
    # A genuinely broken ref: src/gone.tsx exists nowhere.
    (r / "frontend" / "note.md").write_text("see `src/gone.tsx`\n")
    subprocess.run(["git", "init", "-q", str(r)], check=True)
    subprocess.run(["git", "-C", str(r), "add", "-A"], check=True)
    return r


class FileRelativeRefs(unittest.TestCase):
    def test_file_relative_ref_resolves_but_missing_one_still_breaks(self):
        with tempfile.TemporaryDirectory() as d:
            r = _mk(d)
            _checked, broken = scan(str(r))
            refs = {b.ref for b in broken}
            self.assertNotIn("src/main.tsx", refs, "file-relative ref wrongly broken")
            self.assertIn("src/gone.tsx", refs, "a genuinely missing ref must still break")


class TicketProseIsNotChecked(unittest.TestCase):
    """.hee/tickets/ is skipped wholesale -- operator decision 2026-09-26.

    Ticket descriptions are a record of intent, so they routinely name a path
    in another repo, one that has since been renamed, and one that does not
    exist yet because the ticket proposes building it. The same reasoning
    already exempts CHANGELOG.md.
    """

    def _mk(self, d):
        r = Path(d)
        (r / "src").mkdir()
        (r / "src" / "keep.txt").write_text("x\n")
        (r / ".hee" / "tickets").mkdir(parents=True)
        # The SAME broken reference in both places.
        (r / ".hee" / "tickets" / "0001.yaml").write_text(
            "description: rewrite src/gone.tsx, which lives elsewhere\n")
        (r / "note.md").write_text("see `src/gone.tsx`\n")
        subprocess.run(["git", "init", "-q", str(r)], check=True)
        subprocess.run(["git", "-C", str(r), "add", "-A"], check=True)
        return r

    def test_same_broken_ref_breaks_in_a_doc_and_is_ignored_in_a_ticket(self):
        with tempfile.TemporaryDirectory() as d:
            r = self._mk(d)
            _checked, broken = scan(str(r))
            sources = {b.source for b in broken}
            self.assertIn("note.md", sources,
                          "a broken ref in ordinary prose must still break")
            self.assertNotIn(".hee/tickets/0001.yaml", sources,
                             "ticket prose must not be checked for file refs")


class SignatureVsKey(unittest.TestCase):
    def _sig(self, root):
        env = dict(os.environ, HEE_STATUS_STYLE="plain")
        return subprocess.run([str(CHECK), "signatures", str(root)],
                              capture_output=True, text=True, env=env)

    def test_public_key_asc_is_not_an_orphan_signature(self):
        with tempfile.TemporaryDirectory() as d:
            r = Path(d)
            (r / "host.gpg.asc").write_text(
                "-----BEGIN PGP PUBLIC KEY BLOCK-----\n\nmDMEZ...\n"
                "-----END PGP PUBLIC KEY BLOCK-----\n")
            subprocess.run(["git", "init", "-q", str(r)], check=True)
            subprocess.run(["git", "-C", str(r), "add", "-A"], check=True)
            out = self._sig(r)
            self.assertNotIn("orphan", out.stdout.lower(), out.stdout)
            self.assertNotIn("CRITICAL", out.stdout, out.stdout)

    def test_real_orphan_detached_signature_still_warns(self):
        with tempfile.TemporaryDirectory() as d:
            r = Path(d)
            # A detached signature block whose signed file is absent.
            (r / "gone.txt.asc").write_text(
                "-----BEGIN PGP SIGNATURE-----\n\niHUEA...\n"
                "-----END PGP SIGNATURE-----\n")
            subprocess.run(["git", "init", "-q", str(r)], check=True)
            subprocess.run(["git", "-C", str(r), "add", "-A"], check=True)
            out = self._sig(r)
            self.assertIn("orphan", out.stdout.lower(), out.stdout)


if __name__ == "__main__":
    unittest.main()
