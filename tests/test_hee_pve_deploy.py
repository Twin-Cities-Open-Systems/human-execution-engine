#!/usr/bin/env python3
"""
Unit tests for hee-pve-deploy's manifest planning: the parts that decide
what a deploy WOULD do without talking to a node. Nothing here opens an
ssh connection -- every case is either a pure function or a --dry-run
path, which is the contract those paths exist to keep.

Run: python3 -m unittest tests/test_hee_pve_deploy.py
"""
import contextlib
import importlib.machinery
import importlib.util
import io
import os
import sys
import json
import tempfile
import types
import unittest
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "tooling" / "bin" / "hee-pve-deploy"


def _load():
    # The tool has no .py suffix, so it is loaded by path as a module.
    loader = importlib.machinery.SourceFileLoader("hee_pve_deploy", str(TOOL))
    spec = importlib.util.spec_from_loader("hee_pve_deploy", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


deploy = _load()

ANCHORS = """\
apiVersion: hee/v1
kind: Registry
spec:
  anchors:
    lab-gateway: {pinned: role}
    resolver: {pinned: mac}
"""


class TestNet0(unittest.TestCase):

    def test_default_is_dhcp_on_vmbr0(self):
        self.assertEqual(deploy._net0({}), "name=eth0,bridge=vmbr0,ip=dhcp")

    def test_bridge_is_configurable_and_still_dhcp(self):
        self.assertEqual(deploy._net0({"bridge": "vmbr1"}),
                         "name=eth0,bridge=vmbr1,ip=dhcp")

    def test_static_needs_cidr(self):
        with self.assertRaises(SystemExit):
            deploy._net0({"address": "172.16.0.10", "role": "resolver"})

    def test_gateway_without_address_is_refused(self):
        with self.assertRaises(SystemExit):
            deploy._net0({"gateway": "172.16.0.1"})

    def test_static_pin_is_refused_for_a_non_anchor_role(self):
        with tempfile.TemporaryDirectory() as d:
            anchors = os.path.join(d, "anchors.yaml")
            with open(anchors, "w") as fh:
                fh.write(ANCHORS)
            with self.assertRaises(SystemExit):
                deploy._net0({"address": "172.16.0.10/24", "role": "ci-triage"}, anchors)
            with self.assertRaises(SystemExit):
                deploy._net0({"address": "172.16.0.10/24"}, anchors)

    def test_static_pin_is_allowed_for_an_anchor_role(self):
        with tempfile.TemporaryDirectory() as d:
            anchors = os.path.join(d, "anchors.yaml")
            with open(anchors, "w") as fh:
                fh.write(ANCHORS)
            net = deploy._net0({"bridge": "vmbr1", "address": "172.16.0.10/24",
                                "gateway": "172.16.0.1", "role": "resolver"}, anchors)
        self.assertEqual(net, "name=eth0,bridge=vmbr1,ip=172.16.0.10/24,gw=172.16.0.1")

    def test_unreadable_registry_refuses_rather_than_allows(self):
        with self.assertRaises(SystemExit):
            deploy._net0({"address": "172.16.0.10/24", "role": "resolver"},
                         "/nonexistent/anchors.yaml")


class TestFilesAndProvision(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        os.makedirs(os.path.join(self.root, "pve", "x"))
        with open(os.path.join(self.root, "pve", "x", "a.conf"), "w") as fh:
            fh.write("k=v\n")
        with open(os.path.join(self.root, "pve", "x", "p.sh"), "w") as fh:
            fh.write("echo hi\n")

    def tearDown(self):
        self.tmp.cleanup()

    def test_files_resolve_against_root_with_mode(self):
        plan = deploy.plan_files(
            {"files": [{"src": "pve/x/a.conf", "dst": "/etc/a.conf", "mode": "0644"}]},
            self.root)
        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0]["dst"], "/etc/a.conf")
        self.assertEqual(plan[0]["mode"], "0644")
        self.assertTrue(plan[0]["src"].endswith(os.path.join("pve", "x", "a.conf")))

    def test_no_files_key_is_an_empty_plan(self):
        self.assertEqual(deploy.plan_files({}, self.root), [])
        self.assertEqual(deploy.plan_provision({}, self.root), [])

    def test_absolute_src_is_refused(self):
        with self.assertRaises(SystemExit):
            deploy.plan_files({"files": [{"src": "/etc/passwd", "dst": "/x"}]}, self.root)

    def test_escaping_src_is_refused(self):
        with self.assertRaises(SystemExit):
            deploy.plan_files({"files": [{"src": "../../etc/passwd", "dst": "/x"}]},
                              self.root)

    def test_missing_src_is_refused(self):
        with self.assertRaises(SystemExit):
            deploy.plan_files({"files": [{"src": "pve/x/nope.conf", "dst": "/x"}]},
                              self.root)

    def test_relative_dst_is_refused(self):
        with self.assertRaises(SystemExit):
            deploy.plan_files({"files": [{"src": "pve/x/a.conf", "dst": "etc/a.conf"}]},
                              self.root)

    def test_bad_mode_is_refused(self):
        with self.assertRaises(SystemExit):
            deploy.plan_files({"files": [{"src": "pve/x/a.conf", "dst": "/a",
                                          "mode": "rw-r--r--"}]}, self.root)

    def test_provision_resolves_and_refuses_missing(self):
        plan = deploy.plan_provision({"provision": ["pve/x/p.sh"]}, self.root)
        self.assertEqual(plan[0]["rel"], "pve/x/p.sh")
        with self.assertRaises(SystemExit):
            deploy.plan_provision({"provision": ["pve/x/missing.sh"]}, self.root)

    def test_dry_run_prints_and_never_connects(self):
        files = deploy.plan_files(
            {"files": [{"src": "pve/x/a.conf", "dst": "/etc/a.conf", "mode": "0644"}]},
            self.root)
        scripts = deploy.plan_provision({"provision": ["pve/x/p.sh"]}, self.root)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            # host "invalid." would fail immediately if anything tried ssh.
            deploy.apply_files("invalid.", "999", files, dry_run=True)
            deploy.apply_provision("invalid.", "999", scripts, dry_run=True)
        text = out.getvalue()
        self.assertIn("DRY RUN, would push pve/x/a.conf -> /etc/a.conf (mode 0644)", text)
        self.assertIn("chmod 0644", text)
        self.assertIn("DRY RUN, would run pve/x/p.sh via: pct exec 999 -- sh -s", text)


class TestAddonRegistry(unittest.TestCase):

    def test_missing_registry_refuses_rather_than_skips(self):
        with self.assertRaises(SystemExit):
            deploy.load_addon_registry("/nonexistent/container-addons.registry.v1.yaml")

    def test_registry_without_addons_refuses(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "r.yaml")
            with open(p, "w") as fh:
                fh.write("apiVersion: hee/v1\nkind: Registry\nspec: {}\n")
            with self.assertRaises(SystemExit):
                deploy.load_addon_registry(p)

    def test_dry_run_resolves_sets_from_the_given_registry(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "r.yaml")
            with open(p, "w") as fh:
                fh.write("apiVersion: hee/v1\nkind: Registry\nspec:\n  addons:\n"
                         "    demo:\n      packages: [curl, git]\n")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                deploy.apply_addons("invalid.", "999", ["demo"], True, p)
            self.assertIn("apk add --no-cache curl git", out.getvalue())
            with self.assertRaises(SystemExit):
                deploy.apply_addons("invalid.", "999", ["not-a-set"], True, p)


AGENT_ROSTER = """\
apiVersion: hee/v1
kind: Registry
spec:
  status: {status}
  ratification_evidence: "detached GPG signature, key 73B1462A91E844FD96607C157CE485B26654FDA0"
  agents:
    groomer:
      model: claude-haiku-4-5-20251001
    silent:
      role: "names no model"
"""
FPR = "73B1462A91E844FD96607C157CE485B26654FDA0"


def _gpg(returncode=0, fpr=FPR):
    # A stand-in for `gpg --status-fd 1 --verify`: VALIDSIG carries the signing
    # key first and the primary key last.
    line = f"[GNUPG:] VALIDSIG {fpr} 2026-09-09 1789000000 0 4 0 22 10 00 {fpr}\n"
    return types.SimpleNamespace(returncode=returncode, stdout=line if returncode == 0 else "",
                                 stderr="" if returncode == 0 else "BAD signature")


class TestAgentRosterModel(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.agent_roster = os.path.join(self.tmp.name, "agent-roster.registry.v1.yaml")
        self._write("ratified")
        open(self.agent_roster + ".asc", "w").close()

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, status):
        with open(self.agent_roster, "w") as fh:
            fh.write(AGENT_ROSTER.format(status=status))

    def test_renders_the_three_key_pin_from_the_agent_roster(self):
        with mock.patch.object(deploy.subprocess, "run", return_value=_gpg()):
            data = deploy.render_agent_roster_model({"agent": "groomer"}, self.agent_roster)
        self.assertEqual(json.loads(data), {
            "model": "claude-haiku-4-5-20251001",
            "availableModels": ["claude-haiku-4-5-20251001"],
            "enforceAvailableModels": True,
            "env": {"ANTHROPIC_MODEL": "claude-haiku-4-5-20251001"},
        })

    def test_manifest_without_agent_refuses(self):
        with self.assertRaises(SystemExit):
            deploy.render_agent_roster_model({}, self.agent_roster)

    def test_unknown_agent_and_modelless_agent_refuse(self):
        with mock.patch.object(deploy.subprocess, "run", return_value=_gpg()):
            with self.assertRaises(SystemExit):
                deploy.render_agent_roster_model({"agent": "nobody"}, self.agent_roster)
            with self.assertRaises(SystemExit):
                deploy.render_agent_roster_model({"agent": "silent"}, self.agent_roster)

    def test_unratified_agent_roster_refuses_before_any_signature_check(self):
        self._write("proposed")
        with mock.patch.object(deploy.subprocess, "run") as run:
            with self.assertRaises(SystemExit):
                deploy.render_agent_roster_model({"agent": "groomer"}, self.agent_roster)
            run.assert_not_called()

    def test_missing_agent_roster_or_signature_refuses(self):
        with self.assertRaises(SystemExit):
            deploy.load_agent_roster(os.path.join(self.tmp.name, "absent.yaml"))
        os.remove(self.agent_roster + ".asc")
        with self.assertRaises(SystemExit):
            deploy.load_agent_roster(self.agent_roster)

    def test_bad_signature_refuses(self):
        with mock.patch.object(deploy.subprocess, "run", return_value=_gpg(returncode=1)):
            with self.assertRaises(SystemExit):
                deploy.load_agent_roster(self.agent_roster)

    def test_good_signature_from_a_key_the_evidence_does_not_name_refuses(self):
        other = "0" * 40
        with mock.patch.object(deploy.subprocess, "run", return_value=_gpg(fpr=other)):
            with self.assertRaises(SystemExit):
                deploy.load_agent_roster(self.agent_roster)

    def test_files_entry_needs_exactly_one_of_src_or_generate(self):
        with self.assertRaises(SystemExit):
            deploy.plan_files({"files": [{"dst": "/x"}]}, self.tmp.name, self.agent_roster)
        with self.assertRaises(SystemExit):
            deploy.plan_files({"files": [{"src": "a", "generate": "agent-roster-model", "dst": "/x"}]},
                              self.tmp.name, self.agent_roster)

    def test_unknown_generator_refuses(self):
        with self.assertRaises(SystemExit):
            deploy.plan_files({"files": [{"generate": "nope", "dst": "/x"}]},
                              self.tmp.name, self.agent_roster)

    def test_dry_run_prints_the_rendered_file_and_never_connects(self):
        spec = {"agent": "groomer", "files": [
            {"generate": "agent-roster-model", "dst": "/etc/claude-code/managed-settings.d/50-model.json",
             "mode": "0644"}]}
        with mock.patch.object(deploy.subprocess, "run", return_value=_gpg()):
            plan = deploy.plan_files(spec, self.tmp.name, self.agent_roster)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            deploy.apply_files("invalid.", "999", plan, dry_run=True)
        text = out.getvalue()
        self.assertIn("generated agent-roster-model for agent 'groomer' -> "
                      "/etc/claude-code/managed-settings.d/50-model.json (mode 0644)", text)
        self.assertIn('"model": "claude-haiku-4-5-20251001"', text)


class TestManifestRoot(unittest.TestCase):

    def test_root_is_the_git_toplevel_when_inside_a_repo(self):
        # This test file lives in the tool's own repo.
        self.assertEqual(deploy._manifest_root(str(TOOL)), str(ROOT))

    def test_root_falls_back_to_the_manifest_dir_outside_git(self):
        with tempfile.TemporaryDirectory() as d:
            m = os.path.join(d, "m.yaml")
            open(m, "w").close()
            self.assertEqual(deploy._manifest_root(m), os.path.realpath(d)
                             if os.path.realpath(d) == d else d)


if __name__ == "__main__":
    sys.exit(unittest.main())
