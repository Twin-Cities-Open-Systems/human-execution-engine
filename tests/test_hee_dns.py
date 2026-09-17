#!/usr/bin/env python3
# section: 1
"""test_hee_dns.py -- tooling/bin/hee-dns: the host-file parser and zones.

Run from the repo root: python3 -m unittest tests/test_hee_dns.py
Addresses are TEST-NET-1 (192.0.2.0/24).
"""
import importlib.machinery
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "tooling" / "bin" / "hee-dns"
_l = importlib.machinery.SourceFileLoader("hee_dns", str(SRC))
_s = importlib.util.spec_from_loader("hee_dns", _l)
hd = importlib.util.module_from_spec(_s)
_l.exec_module(hd)

HOSTS = """# sample
=ns1.lab.tcos.us:192.0.2.53:300
+www.lab.tcos.us:192.0.2.80
^80.2.0.192.in-addr.arpa:box.other.example:600
@lab.tcos.us::mx1.lab.tcos.us:10:300
"""


def write(tmp, text):
    p = Path(tmp) / "hosts"
    p.write_text(text)
    return p


class TestParse(unittest.TestCase):
    def test_kinds(self):
        with tempfile.TemporaryDirectory() as t:
            hosts, vhosts, ptr_only, mx, errors = hd.parse(write(t, HOSTS))
        self.assertEqual(errors, [])
        self.assertEqual(hosts, [("ns1.lab.tcos.us", "192.0.2.53", "300")])
        self.assertEqual(vhosts, [("www.lab.tcos.us", "192.0.2.80", "300")])
        self.assertEqual(ptr_only, [("box.other.example", "192.0.2.80", "600")])
        self.assertEqual(len(mx), 1)

    def test_bad_ptr_only(self):
        bad = "^192.0.2.80:box.example\n^1.2.3.in-addr.arpa:box.example\n^80.2.0.192.in-addr.arpa:box\n?x\n"
        with tempfile.TemporaryDirectory() as t:
            *_, errors = hd.parse(write(t, bad))
        self.assertEqual(len(errors), 4)
        self.assertIn("not an in-addr.arpa name", errors[0])
        self.assertIn("does not name one IPv4 address", errors[1])
        self.assertIn("not a fully qualified name", errors[2])
        self.assertIn("unknown record type", errors[3])

    def test_rev_to_ip(self):
        self.assertEqual(hd.rev_to_ip("72.0.0.10.in-addr.arpa"), "10.0.0.72")
        with self.assertRaises(ValueError):
            hd.rev_to_ip("300.0.0.10.in-addr.arpa")


class TestZones(unittest.TestCase):
    def test_ptr_only_is_reverse_only(self):
        with tempfile.TemporaryDirectory() as t:
            p = write(t, HOSTS)
            out = Path(t) / "out"
            r = subprocess.run([sys.executable, str(SRC), "generate", str(p), "--out", str(out)],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("1 PTR-only", r.stdout)
            fwd = (out / "db.lab.tcos.us").read_text()
            rev = (out / "db.2.0.192.in-addr.arpa").read_text()
        self.assertNotIn("box.other.example", fwd)
        self.assertIn("www\t300\tIN A\t192.0.2.80", fwd)
        self.assertIn("80\t600\tIN PTR\tbox.other.example.", rev)
        self.assertIn("53\t300\tIN PTR\tns1.lab.tcos.us.", rev)
        self.assertNotIn("www.lab.tcos.us", rev)

    def test_collision_counts_ptr_only(self):
        with tempfile.TemporaryDirectory() as t:
            p = write(t, "=a.lab.tcos.us:192.0.2.9\n^9.2.0.192.in-addr.arpa:b.other.example\n")
            r = subprocess.run([sys.executable, str(SRC), "check", str(p)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0)
        self.assertIn("192.0.2.9 has two PTR records", r.stderr)

    def test_malformed_writes_nothing(self):
        with tempfile.TemporaryDirectory() as t:
            p = write(t, "^nope:x.y\n")
            out = Path(t) / "out"
            r = subprocess.run([sys.executable, str(SRC), "generate", str(p), "--out", str(out)],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 2)
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
