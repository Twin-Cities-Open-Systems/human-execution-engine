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
import json
import os
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

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

    def test_features_render_in_manifest_order(self):
        self.assertIsNone(deploy._features({}))
        self.assertEqual(deploy._features({"features": {"nesting": True, "keyctl": True}}), "nesting=1,keyctl=1")
        self.assertEqual(deploy._features({"features": {"fuse": False}}), "fuse=0")

    def test_features_refuse_what_they_do_not_know(self):
        for bad in ({"features": {"mount": True}}, {"features": {"nesting": 1}}, {"features": []},
                    {"features": {}}, {"features": {"keyctl": True}, "unprivileged": False}):
            with self.subTest(bad=bad), self.assertRaises(SystemExit):
                deploy._features(bad)

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
        self.assertIn("DRY RUN, would run pve/x/p.sh via: pct exec 999 -- env PATH="
                      "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin sh -s", text)


class TestDirectoryFiles(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        (self.root / "svc" / "sub").mkdir(parents=True)
        (self.root / "svc" / "app.py").write_text("print(1)\n")
        (self.root / "svc" / "sub" / "x.txt").write_text("x\n")
        (self.root / "svc" / "untracked.tmp").write_text("no\n")
        subprocess.run(["git", "-C", str(self.root), "add", "svc/app.py", "svc/sub/x.txt"], check=True)
        subprocess.run(["git", "-C", str(self.root), "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "x"], check=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_directory_ships_tracked_files_only_as_one_tar(self):
        files = deploy.plan_files({"files": [{"src": "svc", "dst": "/opt/svc"}]}, self.root)
        self.assertEqual(len(files), 1)
        f = files[0]
        self.assertTrue(f["dir"]); self.assertEqual(f["data"]["files"], 2); self.assertEqual(f["data"]["strip"], 1)
        import tarfile
        names = sorted(m.name for m in tarfile.open(fileobj=io.BytesIO(f["data"]["tar"])).getmembers() if m.isfile())
        self.assertEqual(names, ["svc/app.py", "svc/sub/x.txt"])   # untracked.tmp is not there

    def test_directory_refuses_mode_and_untracked(self):
        with self.assertRaises(SystemExit):
            deploy.plan_files({"files": [{"src": "svc", "dst": "/opt/svc", "mode": "0755"}]}, self.root)
        (self.root / "loose").mkdir(); (self.root / "loose" / "a").write_text("a")
        with self.assertRaises(SystemExit):
            deploy.plan_files({"files": [{"src": "loose", "dst": "/opt/loose"}]}, self.root)

    def test_dry_run_prints_the_unpack_and_never_connects(self):
        files = deploy.plan_files({"files": [{"src": "svc", "dst": "/opt/svc"}]}, self.root)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            deploy.apply_files("invalid.", "999", files, dry_run=True)
        self.assertIn("would unpack svc/ (2 tracked files", out.getvalue())
        self.assertIn("tar -xf - -C /opt/svc --strip-components=1", out.getvalue())


class TestMounts(unittest.TestCase):

    def test_renders_mpN_in_manifest_order(self):
        self.assertEqual(deploy._mounts({}), [])
        self.assertEqual(
            deploy._mounts({"mounts": [{"host": "/srv/storage", "ct": "/data/storage"},
                                       {"host": "/srv/media", "ct": "/data/media", "ro": True}]}),
            ["-mp0", "/srv/storage,mp=/data/storage", "-mp1", "/srv/media,mp=/data/media,ro=1"])

    def test_refusals(self):
        bad = [
            {"mounts": {}},                                            # not a list
            {"mounts": []},                                            # empty
            {"mounts": [{"host": "/srv/x"}]},                          # no ct
            {"mounts": [{"host": "srv/x", "ct": "/data/x"}]},          # relative host
            {"mounts": [{"host": "/srv/x/", "ct": "/data/x"}]},        # trailing slash
            {"mounts": [{"host": "/srv/../x", "ct": "/data/x"}]},      # not normalized
            {"mounts": [{"host": "/srv/x", "ct": "/"}]},               # rootfs
            {"mounts": [{"host": "/srv/x", "ct": "/data/x"},
                        {"host": "/srv/y", "ct": "/data/x"}]},         # duplicate ct
            {"mounts": [{"host": "/srv/x", "ct": "/data/x", "ro": "yes"}]},   # ro not bool
            {"mounts": [{"host": "/srv/x", "ct": "/data/x", "size": "8G"}]},  # unknown key
            {"mounts": [{"host": "/srv/a,b", "ct": "/data/x"}]},       # pve option syntax
        ]
        for spec in bad:
            with self.subTest(spec=spec), self.assertRaises(SystemExit):
                deploy._mounts(spec)

    def test_dry_run_prints_the_mount_and_never_connects(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "svc.yaml"
            manifest.write_text(
                "hostname: mf-test\ntemplate: alpine.tar.xz\nstorage: ssd1\n"
                "mounts:\n  - {host: /srv/storage, ct: /data/storage}\n")
            out = io.StringIO()
            with mock.patch.object(deploy, "existing_hostnames", return_value={}), \
                 mock.patch.object(deploy, "ensure_template", return_value=None), \
                 mock.patch.object(deploy, "pvesh", return_value="999\n"), \
                 mock.patch.object(sys, "argv", ["hee-pve-deploy", str(manifest), "--dry-run"]), \
                 contextlib.redirect_stdout(out):
                deploy.main()
        self.assertIn("-mp0 /srv/storage,mp=/data/storage", out.getvalue())
        self.assertIn("DRY RUN complete", out.getvalue())


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
            self.assertEqual([c.args[0] for c in run.call_args_list if c.args and c.args[0] and c.args[0][0] == 'pct'], [])  # git rev-parse (manifest resolution) is a read; nothing reaches pct

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


class TestResolver(unittest.TestCase):

    BLOCK = {"nameservers": ["10.0.0.194", "10.0.0.72"], "search": ["lab.tcos.us", "tcos.us"], "ndots": 2}

    def _data(self, plan, dst):
        return next(f["data"] for f in plan if f["dst"] == dst).decode()

    def test_no_block_no_files(self):
        self.assertEqual(deploy.plan_resolver({}), [])

    def test_renders_search_nameservers_in_order_and_ndots(self):
        plan = deploy.plan_resolver({"resolver": self.BLOCK})
        body = [l for l in self._data(plan, "/etc/resolv.conf").splitlines() if not l.startswith("#")]
        self.assertEqual(body, ["search lab.tcos.us tcos.us", "nameserver 10.0.0.194",
                                "nameserver 10.0.0.72", "options ndots:2"])

    def test_dhcp_container_stops_udhcpc_and_pve_rewriting(self):
        dsts = [f["dst"] for f in deploy.plan_resolver({"resolver": self.BLOCK})]
        self.assertEqual(dsts, ["/etc/.pve-ignore.resolv.conf", "/etc/udhcpc/udhcpc.conf", "/etc/resolv.conf"])
        plan = deploy.plan_resolver({"resolver": self.BLOCK})
        self.assertIn('RESOLV_CONF="no"', self._data(plan, "/etc/udhcpc/udhcpc.conf"))

    def test_static_container_has_no_udhcpc_file(self):
        dsts = [f["dst"] for f in deploy.plan_resolver({"resolver": self.BLOCK, "address": "172.16.0.10/24"})]
        self.assertNotIn("/etc/udhcpc/udhcpc.conf", dsts)
        self.assertIn("/etc/.pve-ignore.resolv.conf", dsts)

    def test_ndots_defaults_to_one(self):
        plan = deploy.plan_resolver({"resolver": {"nameservers": ["10.0.0.194"]}})
        self.assertIn("options ndots:1", self._data(plan, "/etc/resolv.conf"))

    def test_refusals(self):
        bad = [
            "not a mapping",
            {"nameservers": []},
            {"nameservers": ["1.1.1.1", "1.0.0.1", "8.8.8.8", "8.8.4.4"]},
            {"nameservers": ["ns1.lab.tcos.us"]},
            {"nameservers": ["10.0.0.194"], "search": ["not a domain"]},
            {"nameservers": ["10.0.0.194"], "search": "lab.tcos.us"},
            {"nameservers": ["10.0.0.194"], "ndots": 0},
            {"nameservers": ["10.0.0.194"], "ndots": 16},
            {"nameservers": ["10.0.0.194"], "ndots": "2"},
            {"nameservers": ["10.0.0.194"], "ndots": True},
            {"nameservers": ["10.0.0.194"], "options": ["rotate"]},
        ]
        for b in bad:
            with self.subTest(block=b), self.assertRaises(SystemExit):
                deploy.plan_resolver({"resolver": b})

    def test_dry_run_prints_the_rendered_resolv_conf(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            deploy.apply_files("invalid.", "999", deploy.plan_resolver({"resolver": self.BLOCK}), dry_run=True)
        self.assertIn("resolver: /etc/resolv.conf -> /etc/resolv.conf (mode 0644)", out.getvalue())


class TestContainerPath(unittest.TestCase):
    """pct exec hands containers PVE's PATH, which has no /usr/local/bin."""

    PATH = "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

    def test_pct_argv_sets_the_login_path(self):
        self.assertEqual(deploy._pct(114, ["hee", "list"]),
                         ["pct", "exec", "114", "--", "env", self.PATH, "hee", "list"])

    def test_addon_dry_run_sets_path_and_is_paste_safe(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "r.yaml")
            with open(p, "w") as fh:
                fh.write("apiVersion: hee/v1\nkind: Registry\nspec:\n  addons:\n"
                         "    demo:\n      packages: [curl, git]\n")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                deploy.apply_addons("invalid.", "999", ["demo"], True, p)
        text = out.getvalue()
        self.assertIn("env " + self.PATH, text)
        self.assertIn("sh -c 'apk add --no-cache curl git'", text)

    def test_files_dry_run_sets_path(self):
        files = [{"rel": "x", "src": None, "data": b"y", "dst": "/etc/x", "mode": None}]
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            deploy.apply_files("invalid.", "999", files, dry_run=True)
        self.assertIn("pct exec 999 -- env " + self.PATH + " sh -c", out.getvalue())

    def test_plan_addons_refuses_unknown_and_reads_nothing_for_no_sets(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "r.yaml")
            with open(p, "w") as fh:
                fh.write("apiVersion: hee/v1\nkind: Registry\nspec:\n  addons:\n"
                         "    demo:\n      packages: [curl]\n")
            with self.assertRaises(SystemExit):
                deploy.plan_addons(["demo", "nope"], p)
            self.assertIn("demo", deploy.plan_addons(["demo"], p))
        self.assertEqual(deploy.plan_addons([], "/nonexistent/registry.yaml"), {})


class TestBusyboxRealpath(unittest.TestCase):
    """BusyBox realpath takes no options: `realpath -- X` resolves X, then fails
    on `--`, and the `|| echo` fallback appends the unresolved path. hee's
    TOOL_ROOT became / on every Alpine container."""

    def test_no_tool_passes_double_dash_to_realpath(self):
        import re
        offenders = []
        for f in sorted((ROOT / "tooling" / "bin").iterdir()):
            if not f.is_file():
                continue
            try:
                text = f.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for n, line in enumerate(text.splitlines(), 1):
                if re.search(r"\brealpath\s+--(\s|$)", line) and not line.lstrip().startswith("#"):
                    offenders.append(f"{f.name}:{n}")
        self.assertEqual(offenders, [], "realpath -- breaks under BusyBox")


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


# ---------------------------------------------------------------------------
# --reprovision -- human-execution-engine#760.
#
# Nothing here opens a real ssh connection either: subprocess.run itself is
# mocked wherever a helper would call out to `pct`/`pvesh`, the same fake
# shape the rest of this file uses for `gpg` (TestAgentRosterModel) and pve
# create (TestMounts.test_dry_run_prints_the_mount_and_never_connects).
# ---------------------------------------------------------------------------

class TestReprovisionHelp(unittest.TestCase):

    def test_help_documents_reprovision_and_its_missing_container_no_op(self):
        out = io.StringIO()
        with mock.patch.object(sys, "argv", ["hee-pve-deploy", "--help"]), \
             contextlib.redirect_stdout(out):
            deploy.main()
        text = out.getvalue()
        self.assertIn("--reprovision", text)
        self.assertIn("no-op", text)


class TestLiveSha256(unittest.TestCase):

    def test_present_file_returns_its_hash(self):
        r = types.SimpleNamespace(returncode=0, stdout="deadbeef  /etc/x\n", stderr="")
        with mock.patch.object(deploy.subprocess, "run", return_value=r):
            self.assertEqual(deploy._live_sha256("h", 1, "/etc/x"), "deadbeef")

    def test_absent_file_is_none_not_an_error(self):
        r = types.SimpleNamespace(returncode=1, stdout="",
                                  stderr="sha256sum: /etc/x: No such file or directory\n")
        with mock.patch.object(deploy.subprocess, "run", return_value=r):
            self.assertIsNone(deploy._live_sha256("h", 1, "/etc/x"))


class TestTarAndLiveDirSha256(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        (self.root / "svc" / "sub").mkdir(parents=True)
        (self.root / "svc" / "app.py").write_text("print(1)\n")
        (self.root / "svc" / "sub" / "x.txt").write_text("x\n")
        subprocess.run(["git", "-C", str(self.root), "add", "svc/app.py", "svc/sub/x.txt"], check=True)
        subprocess.run(["git", "-C", str(self.root), "-c", "user.email=t@t", "-c", "user.name=t",
                        "commit", "-q", "-m", "x"], check=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_tar_entry_sha256s_keys_match_paths_relative_to_dst(self):
        files = deploy.plan_files({"files": [{"src": "svc", "dst": "/opt/svc"}]}, self.root)
        entries = deploy._tar_entry_sha256s(files[0]["data"])
        self.assertEqual(set(entries), {"app.py", "sub/x.txt"})
        self.assertEqual(entries["app.py"], deploy._sha256_hex(b"print(1)\n"))

    def test_live_dir_sha256s_parses_find_sha256sum_output(self):
        r = types.SimpleNamespace(returncode=0, stdout="aaa  ./app.py\nbbb  ./sub/x.txt\n", stderr="")
        with mock.patch.object(deploy.subprocess, "run", return_value=r):
            live = deploy._live_dir_sha256s("h", 1, "/opt/svc")
        self.assertEqual(live, {"app.py": "aaa", "sub/x.txt": "bbb"})

    def test_live_dir_sha256s_missing_dst_is_empty_not_an_error(self):
        r = types.SimpleNamespace(returncode=1, stdout="", stderr="")
        with mock.patch.object(deploy.subprocess, "run", return_value=r):
            self.assertEqual(deploy._live_dir_sha256s("h", 1, "/opt/nope"), {})


class TestDiffFiles(unittest.TestCase):

    def test_regular_files_report_unchanged_changed_new(self):
        files = [
            {"rel": "a", "src": None, "data": b"AAAA", "dst": "/etc/a", "mode": None},
            {"rel": "b", "src": None, "data": b"BBBB", "dst": "/etc/b", "mode": None},
            {"rel": "c", "src": None, "data": b"CCCC", "dst": "/etc/c", "mode": None},
        ]
        hash_a = deploy._sha256_hex(b"AAAA")
        hash_b_old = deploy._sha256_hex(b"old-b")
        with mock.patch.object(deploy, "_live_sha256", side_effect=[hash_a, hash_b_old, None]):
            report = deploy.diff_files("h", 1, files)
        self.assertEqual([label for label, _ in report], ["a -> /etc/a", "b -> /etc/b", "c -> /etc/c"])
        self.assertEqual([status for _, status in report], ["unchanged", "changed", "new"])

    def test_directory_entry_new_changed_unchanged(self):
        entry = {"rel": "svc/", "src": None, "data": {"tar": b"", "files": 2, "strip": 1},
                 "dst": "/opt/svc", "mode": None, "dir": True}
        wanted = {"a": "h1", "b": "h2"}
        with mock.patch.object(deploy, "_tar_entry_sha256s", return_value=wanted), \
             mock.patch.object(deploy, "_live_dir_sha256s", return_value={}):
            self.assertEqual(deploy.diff_files("h", 1, [entry])[0], ("svc/ -> /opt/svc/", "new"))
        with mock.patch.object(deploy, "_tar_entry_sha256s", return_value=wanted), \
             mock.patch.object(deploy, "_live_dir_sha256s", return_value=dict(wanted)):
            self.assertEqual(deploy.diff_files("h", 1, [entry])[0], ("svc/ -> /opt/svc/", "unchanged"))
        with mock.patch.object(deploy, "_tar_entry_sha256s", return_value=wanted), \
             mock.patch.object(deploy, "_live_dir_sha256s", return_value={"a": "h1", "b": "OLD"}):
            self.assertEqual(deploy.diff_files("h", 1, [entry])[0], ("svc/ -> /opt/svc/", "changed"))


class TestLiveConfig(unittest.TestCase):

    def test_parses_pct_config_colon_lines(self):
        r = types.SimpleNamespace(
            returncode=0,
            stdout="arch: amd64\nfeatures: nesting=1,keyctl=1\nmp0: /srv/storage,mp=/data/storage\n",
            stderr="")
        with mock.patch.object(deploy.subprocess, "run", return_value=r):
            live = deploy.live_config("h", 123)
        self.assertEqual(live["features"], "nesting=1,keyctl=1")
        self.assertEqual(live["mp0"], "/srv/storage,mp=/data/storage")

    def test_unreadable_config_refuses(self):
        r = types.SimpleNamespace(returncode=1, stdout="", stderr="no such container")
        with mock.patch.object(deploy.subprocess, "run", return_value=r):
            with self.assertRaises(SystemExit):
                deploy.live_config("h", 123)


class TestDiffConfig(unittest.TestCase):

    def test_no_diff_when_live_matches_the_manifest(self):
        spec = {"features": {"nesting": True},
                "mounts": [{"host": "/srv/storage", "ct": "/data/storage"}]}
        live = {"features": "nesting=1", "mp0": "/srv/storage,mp=/data/storage"}
        self.assertEqual(deploy.diff_config(spec, live, 123), [])

    def test_reports_mismatched_missing_and_extra_mounts_and_features(self):
        spec = {"features": {"nesting": True, "keyctl": True},
                "mounts": [{"host": "/srv/storage", "ct": "/data/storage"}]}
        live = {"features": "nesting=1", "mp0": "/srv/OLD,mp=/data/storage", "mp1": "/srv/x,mp=/data/x"}
        pct_sets = [pct_set for _, pct_set in deploy.diff_config(spec, live, 123)]
        self.assertIn("pct set 123 -features nesting=1,keyctl=1", pct_sets)
        self.assertIn("pct set 123 -mp0 /srv/storage,mp=/data/storage", pct_sets)
        self.assertIn("pct set 123 -delete mp1", pct_sets)

    def test_manifest_with_no_features_but_live_has_some_reports_a_delete(self):
        diffs = deploy.diff_config({}, {"features": "nesting=1"}, 5)
        self.assertEqual(diffs, [("features: manifest wants none, live is 'nesting=1'",
                                  "pct set 5 -delete features")])


class TestPctExecStdinExitCode(unittest.TestCase):

    def test_provision_failure_exits_with_the_scripts_own_code(self):
        r = types.SimpleNamespace(returncode=3, stderr=b"boom")
        with mock.patch.object(deploy.subprocess, "run", return_value=r):
            with self.assertRaises(SystemExit) as cm:
                deploy._pct_exec_stdin("h", 1, ["sh", "-s"], b"", "provision: x.sh",
                                       capture=False, propagate_exit_code=True)
        self.assertEqual(cm.exception.code, 3)

    def test_files_push_failure_still_exits_on_a_message_not_a_bare_code(self):
        r = types.SimpleNamespace(returncode=3, stderr=b"boom")
        with mock.patch.object(deploy.subprocess, "run", return_value=r):
            with self.assertRaises(SystemExit) as cm:
                deploy._pct_exec_stdin("h", 1, ["sh", "-c", "x"], b"", "files: x")
        self.assertIsInstance(cm.exception.code, str)


class TestReprovisionIntegration(unittest.TestCase):
    """main() with --reprovision, mocking existing_hostnames/live_config the
    same way TestMounts mocks pvesh/existing_hostnames for a create."""

    def _manifest(self, tmp, extra=""):
        manifest = Path(tmp) / "svc.yaml"
        manifest.write_text(
            "hostname: mf-test\ntemplate: alpine.tar.xz\nstorage: ssd1\n"
            "provision:\n  - prov.sh\n" + extra)
        (Path(tmp) / "prov.sh").write_text("echo hi\n")
        return manifest

    def test_missing_container_reprovision_is_a_plain_create(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = self._manifest(tmp)
            out = io.StringIO()
            with mock.patch.object(deploy, "existing_hostnames", return_value={}), \
                 mock.patch.object(deploy, "ensure_template", return_value=None), \
                 mock.patch.object(deploy, "pvesh", return_value="999\n"), \
                 mock.patch.object(sys, "argv",
                                    ["hee-pve-deploy", str(manifest), "--reprovision", "--dry-run"]), \
                 contextlib.redirect_stdout(out):
                deploy.main()
            text = out.getvalue()
            self.assertIn("does not exist yet -- '--reprovision' is a no-op", text)
            self.assertIn("DRY RUN, would run: pvesh create", text)
            self.assertIn("DRY RUN, would run prov.sh via:", text)

    def test_dry_run_reprovision_touches_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = self._manifest(tmp)
            out = io.StringIO()
            with mock.patch.object(deploy, "existing_hostnames", return_value={"mf-test": 7}), \
                 mock.patch.object(deploy, "live_config", return_value={}), \
                 mock.patch.object(deploy.subprocess, "run") as run, \
                 mock.patch.object(sys, "argv",
                                    ["hee-pve-deploy", str(manifest), "--reprovision", "--dry-run"]), \
                 contextlib.redirect_stdout(out):
                deploy.main()
            text = out.getvalue()
            self.assertIn("already exists (vmid 7) -- reprovisioning", text)
            self.assertIn("DRY RUN, would run prov.sh via:", text)
            self.assertIn("DRY RUN complete", text)
            self.assertEqual([c.args[0] for c in run.call_args_list if c.args and c.args[0] and c.args[0][0] == 'pct'], [])  # git rev-parse (manifest resolution) is a read; nothing reaches pct   # no files: entries here, so no sha256sum reads either;
                                      # apply_files/apply_provision print-only under dry_run

    def test_existing_container_reships_reports_diff_and_runs_provision(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = self._manifest(tmp, extra="files:\n  - {src: prov.sh, dst: /opt/prov.sh}\n")
            out = io.StringIO()
            with mock.patch.object(deploy, "existing_hostnames", return_value={"mf-test": 123}), \
                 mock.patch.object(deploy, "live_config", return_value={}), \
                 mock.patch.object(deploy, "_live_sha256", return_value=None), \
                 mock.patch.object(deploy, "apply_files") as af, \
                 mock.patch.object(deploy, "apply_provision") as ap, \
                 mock.patch.object(sys, "argv", ["hee-pve-deploy", str(manifest), "--reprovision"]), \
                 contextlib.redirect_stdout(out):
                deploy.main()
            text = out.getvalue()
            self.assertIn("'mf-test' already exists (vmid 123) -- reprovisioning", text)
            self.assertIn("files: prov.sh -> /opt/prov.sh: new", text)
            self.assertNotIn("WARNING", text)   # nothing in mounts:/features: to warn about
            af.assert_called_once()
            ap.assert_called_once()

    def test_exit_code_follows_the_provision(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = self._manifest(tmp)
            with mock.patch.object(deploy, "existing_hostnames", return_value={"mf-test": 123}), \
                 mock.patch.object(deploy, "live_config", return_value={}), \
                 mock.patch.object(deploy, "apply_files", return_value=None), \
                 mock.patch.object(deploy, "apply_provision", side_effect=SystemExit(7)), \
                 mock.patch.object(sys, "argv", ["hee-pve-deploy", str(manifest), "--reprovision"]):
                with self.assertRaises(SystemExit) as cm:
                    deploy.main()
            self.assertEqual(cm.exception.code, 7)

    def test_mounts_mismatch_warns_with_the_pct_set_and_applies_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "svc.yaml"
            manifest.write_text(
                "hostname: mf-test\ntemplate: alpine.tar.xz\nstorage: ssd1\n"
                "mounts:\n  - {host: /srv/storage, ct: /data/storage}\n")
            out = io.StringIO()
            with mock.patch.object(deploy, "existing_hostnames", return_value={"mf-test": 42}), \
                 mock.patch.object(deploy, "live_config",
                                    return_value={"mp0": "/srv/OLD,mp=/data/storage"}), \
                 mock.patch.object(deploy, "apply_files", return_value=None), \
                 mock.patch.object(deploy, "apply_provision", return_value=None), \
                 mock.patch.object(deploy.subprocess, "run") as run, \
                 mock.patch.object(sys, "argv", ["hee-pve-deploy", str(manifest), "--reprovision"]), \
                 contextlib.redirect_stdout(out):
                deploy.main()
            text = out.getvalue()
            self.assertIn("WARNING", text)
            self.assertIn("pct set 42 -mp0 /srv/storage,mp=/data/storage", text)
            self.assertIn("not applied", text)
            self.assertEqual([c.args[0] for c in run.call_args_list if c.args and c.args[0] and c.args[0][0] == 'pct'], [])  # git rev-parse (manifest resolution) is a read; nothing reaches pct   # never runs `pct set` -- nothing reached subprocess at all


if __name__ == "__main__":
    sys.exit(unittest.main())
