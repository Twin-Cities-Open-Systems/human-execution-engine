"""hee gen-manpages --gopher writes index.json: the rendered tree as data.

A web page that lists the man pages reads this instead of parsing gophermaps.
It must be derived from the rendered text alone and carry no timestamp, so
the same tree always gives the same bytes.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "library" / "py"))
import hee_manpage as M

PAGE = """HEE-CRED(1)                 HEE Tools                 HEE-CRED(1)

NAME
       hee-cred  -  sealed  credential store (GPG, or age for TPM-
       bound secrets), kept in the repo with‐
       out a server

SYNOPSIS
       hee cred -run NAME
"""


class Summary(unittest.TestCase):
    def test_name_section_is_unwrapped(self):
        self.assertEqual(M.page_summary(PAGE),
                         "sealed credential store (GPG, or age for TPM-bound secrets), kept in the repo without a server")

    def test_page_without_name_uses_its_tagline(self):
        self.assertEqual(M.page_summary("()   ()\n\nscan.py(1)\n       scan.py -- tolerant inventory of cards.\n\n   More.\n"),
                         "tolerant inventory of cards")

    def test_no_summary_is_empty_not_an_error(self):
        self.assertEqual(M.page_summary("just text\n"), "")


class Index(unittest.TestCase):
    def tree(self, d):
        for sec, names in ((1, ("hee-zed", "hee", "hee-alpha")), (8, ("hee-admin",))):
            p = Path(d, "man", f"man{sec}")
            p.mkdir(parents=True)
            for n in names:
                (p / f"{n}.txt").write_text(f"X\n\nNAME\n       {n} - does {n}\n\nSYNOPSIS\n")
        Path(d, "man", "man3").mkdir()          # an empty section is not listed

    def test_sections_and_order(self):
        with tempfile.TemporaryDirectory() as d:
            self.tree(d)
            idx = M.tree_index(d)
        self.assertEqual([(s["section"], s["title"]) for s in idx["sections"]],
                         [(1, "User Commands"), (8, "System Administration")])
        # hee leads its section, as in the gopher menu; the rest by name
        self.assertEqual([p["name"] for p in idx["sections"][0]["pages"]], ["hee", "hee-alpha", "hee-zed"])
        self.assertEqual(idx["sections"][1]["pages"][0],
                         {"name": "hee-admin", "section": 8, "path": "man/man8/hee-admin.txt", "summary": "does hee-admin"})

    def test_written_index_is_stable(self):
        with tempfile.TemporaryDirectory() as d:
            self.tree(d)
            self.assertEqual(M.write_index(d), 4)
            first = Path(d, "index.json").read_bytes()
            M.write_index(d)
            self.assertEqual(first, Path(d, "index.json").read_bytes())
            self.assertEqual(json.loads(first)["sections"][0]["pages"][0]["name"], "hee")

    def test_committed_tree_carries_a_current_index(self):
        tree = ROOT / "man" / "gopher"
        self.assertEqual(json.loads((tree / "index.json").read_text()), M.tree_index(tree))


if __name__ == "__main__":
    unittest.main()
