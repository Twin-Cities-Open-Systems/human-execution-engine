#!/usr/bin/env python3
"""hee-pve-health: the local-pvesh transport, with no node and no network.

The dangerous case is not "local pvesh fails to run" -- it is local pvesh
answering for a host that is somewhere else. A plausible table about the wrong
machine is worse than an error, so most of these tests are about refusing.
"""
import importlib.machinery
import importlib.util
import json
import os
import subprocess
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(ROOT, "tooling", "bin", "hee-pve-health")


def _load():
    loader = importlib.machinery.SourceFileLoader("hee_pve_health", TOOL)
    spec = importlib.util.spec_from_loader("hee_pve_health", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


h = _load()

IP_OUT = (
    "1: lo    inet 127.0.0.1/8 scope host lo\\       valid_lft forever\n"
    "2: vmbr0 inet 10.0.0.153/24 brd 10.0.0.255 scope global vmbr0\\  valid_lft forever\n"
    "3: vmbr1 inet 172.16.0.1/24 brd 172.16.0.255 scope global vmbr1\\ valid_lft forever\n"
    "2: vmbr0 inet6 fe80::1/64 scope link \\       valid_lft forever\n"
)


def _run(stdout="", rc=0):
    return subprocess.CompletedProcess(args=[], returncode=rc, stdout=stdout, stderr="")


class TestOwnAddresses(unittest.TestCase):
    def test_parses_ip_output(self):
        with mock.patch.object(h.subprocess, "run", return_value=_run(IP_OUT)):
            got = h._own_addresses()
        for a in ("10.0.0.153", "172.16.0.1", "fe80::1", "127.0.0.1", "::1", "localhost"):
            self.assertIn(a, got, a)

    def test_loopback_survives_a_missing_ip_command(self):
        """No `ip` is not a reason to think we have no addresses at all."""
        with mock.patch.object(h.subprocess, "run", side_effect=OSError("no ip")):
            got = h._own_addresses()
        self.assertIn("127.0.0.1", got)
        self.assertNotIn("10.0.0.153", got)


class TestLocalPvesh(unittest.TestCase):
    def _call(self, host, which="/usr/bin/pvesh", pvesh=None):
        pvesh = pvesh if pvesh is not None else _run(json.dumps({"ok": 1}))

        def fake_run(argv, *a, **kw):
            if argv and argv[0] == "ip":
                return _run(IP_OUT)
            return pvesh

        with mock.patch.object(h.shutil, "which", return_value=which), \
             mock.patch.object(h.subprocess, "run", side_effect=fake_run):
            return h._local_pvesh_json(host, "/nodes/pve/status")

    def test_answers_for_an_address_this_machine_has(self):
        self.assertEqual(self._call("10.0.0.153"), {"ok": 1})

    def test_answers_for_loopback(self):
        self.assertEqual(self._call("127.0.0.1"), {"ok": 1})

    def test_refuses_for_a_different_node(self):
        """The whole point. Querying another pve node from a pve node is a
        real thing to want, and answering with local state would be a
        plausible table about the wrong machine."""
        self.assertIsNone(self._call("10.0.0.99"))

    def test_refuses_when_pvesh_is_not_installed(self):
        self.assertIsNone(self._call("10.0.0.153", which=None))

    def test_falls_through_when_pvesh_exits_non_zero(self):
        self.assertIsNone(self._call("10.0.0.153", pvesh=_run("", rc=2)))

    def test_falls_through_on_empty_output(self):
        """rc 0 with no body is not an answer."""
        self.assertIsNone(self._call("10.0.0.153", pvesh=_run("   ")))

    def test_falls_through_on_unparseable_output(self):
        self.assertIsNone(self._call("10.0.0.153", pvesh=_run("not json")))

    def test_falls_through_when_pvesh_cannot_be_executed(self):
        def boom(argv, *a, **kw):
            if argv and argv[0] == "ip":
                return _run(IP_OUT)
            raise OSError("exec failed")

        with mock.patch.object(h.shutil, "which", return_value="/usr/bin/pvesh"), \
             mock.patch.object(h.subprocess, "run", side_effect=boom):
            self.assertIsNone(h._local_pvesh_json("10.0.0.153", "/nodes/pve/status"))


class TestTransportOrder(unittest.TestCase):
    def test_local_pvesh_wins_over_the_api_token(self):
        """Off the node nothing changes, but on it the credential-free path
        must not be skipped in favour of one that needs a sealed token."""
        with mock.patch.object(h, "_local_pvesh_json", return_value={"from": "local"}), \
             mock.patch.object(h, "_token_api_json", return_value={"from": "token"}):
            self.assertEqual(h.pvesh_json("10.0.0.153", "/x"), {"from": "local"})

    def test_api_token_still_used_when_local_declines(self):
        with mock.patch.object(h, "_local_pvesh_json", return_value=None), \
             mock.patch.object(h, "_token_api_json", return_value={"from": "token"}):
            self.assertEqual(h.pvesh_json("10.0.0.153", "/x"), {"from": "token"})

    def test_falsy_but_real_local_answer_is_not_discarded(self):
        """An empty list is a real API answer -- a node with no containers.
        Testing `is not None` rather than truthiness is what keeps that from
        silently falling through to a transport that cannot work."""
        with mock.patch.object(h, "_local_pvesh_json", return_value=[]), \
             mock.patch.object(h, "_token_api_json", return_value={"from": "token"}):
            self.assertEqual(h.pvesh_json("10.0.0.153", "/x"), [])


if __name__ == "__main__":
    unittest.main()
