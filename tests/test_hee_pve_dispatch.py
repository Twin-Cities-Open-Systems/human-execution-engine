#!/usr/bin/env python3
"""hee-pve-dispatch: the parts that decide what a dispatch WOULD do, with no
node and no key. Nothing here opens ssh."""
import contextlib
import importlib.machinery
import importlib.util
import io
import os
import sys
import tarfile
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(ROOT, "tooling", "bin", "hee-pve-dispatch")


def _load():
    loader = importlib.machinery.SourceFileLoader("hee_pve_dispatch", TOOL)
    spec = importlib.util.spec_from_loader("hee_pve_dispatch", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


d = _load()

ALLOC = """\
apiVersion: hee/v1
kind: Registry
spec:
  allocations:
    ci-triage: {hostname: tcos-triage-herbert, vmid: 115, kind: agent}
    lab-dhcp: {hostname: tcos-dhcp-bonnie, vmid: 114, kind: service}
"""


class TestResolve(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.alloc = os.path.join(self.tmp.name, "a.yaml")
        open(self.alloc, "w").write(ALLOC)

    def tearDown(self):
        self.tmp.cleanup()

    def test_role_and_hostname_resolve_to_the_agent(self):
        a = d.load_allocations(self.alloc)
        self.assertEqual(d.resolve_agent("ci-triage", a), ("ci-triage", "tcos-triage-herbert", 115))
        self.assertEqual(d.resolve_agent("tcos-triage-herbert", a), ("ci-triage", "tcos-triage-herbert", 115))

    def test_non_agent_and_unknown_are_refused(self):
        a = d.load_allocations(self.alloc)
        with self.assertRaises(SystemExit):
            d.resolve_agent("lab-dhcp", a)
        with self.assertRaises(SystemExit):
            d.resolve_agent("nobody", a)


class TestJob(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.job = os.path.join(self.tmp.name, "job")
        os.makedirs(os.path.join(self.job, "in"))
        open(os.path.join(self.job, "prompt.md"), "w").write("Do the thing with `quotes' and $vars.\n")
        open(os.path.join(self.job, "in", "a.html"), "w").write("<p>x</p>")
        self.spec = os.path.join(self.job, "job.yaml")

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, text):
        open(self.spec, "w").write(text)

    def test_budget_is_required_and_bounded(self):
        self._write("name: convert\nprompt: prompt.md\n")
        with self.assertRaises(SystemExit):
            d.plan_job(self.job)
        self._write("name: convert\nprompt: prompt.md\nbudget_usd: 500\n")
        with self.assertRaises(SystemExit):
            d.plan_job(self.job)

    def test_bypass_permissions_and_escaping_inputs_are_refused(self):
        self._write("name: convert\nbudget_usd: 1\npermission_mode: bypassPermissions\n")
        with self.assertRaises(SystemExit):
            d.plan_job(self.job)
        self._write("name: convert\nbudget_usd: 1\ninputs: ['../secret']\n")
        with self.assertRaises(SystemExit):
            d.plan_job(self.job)

    def test_defaults_and_run_sh(self):
        self._write("name: convert\nbudget_usd: 1.5\n")
        job = d.plan_job(self.job)
        self.assertEqual(job["tools"], d.DEFAULT_TOOLS)
        self.assertEqual(job["mode"], "acceptEdits")
        self.assertIn("in", job["inputs"])
        sh = d.render_run_sh(job, "convert-20260910T120000Z")
        self.assertIn("IFS= read -r ANTHROPIC_API_KEY", sh)
        self.assertIn("su -p agent -c", sh)
        self.assertIn("--max-budget-usd 1.50", sh)
        self.assertIn("--permission-mode acceptEdits", sh)
        self.assertIn("--allowedTools Read Write Edit Glob Grep", sh)
        self.assertIn("timeout 1800", sh)
        self.assertIn('"$(cat prompt.md; printf %s ', sh)      # the prompt text itself is never in the script; the out/ note is appended at run time
        self.assertIn("Files the dispatcher itself writes into out/", sh)
        self.assertNotIn("quotes", sh)
        self.assertNotIn("bypassPermissions", sh)

    def test_tar_carries_inputs_prompt_and_run_sh_only(self):
        self._write("name: convert\nbudget_usd: 1\ninputs: [in]\n")
        job = d.plan_job(self.job)
        os.makedirs(os.path.join(self.job, "results", "old"))
        open(os.path.join(self.job, "results", "old", "x"), "w").write("old")
        data = d.make_tar(job, d.render_run_sh(job, "convert-x"))
        names = sorted(m.name for m in tarfile.open(fileobj=io.BytesIO(data)).getmembers())
        self.assertEqual(names, ["in", "in/a.html", "job.yaml", "prompt.md", "run.sh"])

    def test_extract_results_refuses_escaping_members(self):
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w") as t:
            for name, body in (("out/result.json", b'{"type":"result","total_cost_usd":0.12,"num_turns":3,"result":"done"}'),
                               ("out/exit", b"0\n"), ("../evil", b"x")):
                info = tarfile.TarInfo(name); info.size = len(body); t.addfile(info, io.BytesIO(body))
        dest = os.path.join(self.tmp.name, "res")
        d.extract_results(buf.getvalue(), dest)
        self.assertTrue(os.path.isfile(os.path.join(dest, "out", "result.json")))
        self.assertFalse(os.path.exists(os.path.join(self.tmp.name, "evil")))
        res = d.read_result(dest)
        self.assertEqual((res["exit"], res["cost_usd"], res["num_turns"], res["result"]), (0, 0.12, 3, "done"))

    def test_dry_run_never_ships_and_needs_no_key(self):
        self._write("name: convert\nbudget_usd: 1\n")
        alloc = os.path.join(self.tmp.name, "a.yaml"); open(alloc, "w").write(ALLOC)
        pct_list = "VMID       Status     Lock         Name\n115        running                 tcos-triage-herbert\n"
        fake = mock.Mock(returncode=0, stdout=pct_list.encode(), stderr=b"")
        out = io.StringIO()
        with mock.patch.object(d.subprocess, "run", return_value=fake) as run, \
             mock.patch.object(sys, "argv", ["hee-pve-dispatch", "ci-triage", self.job, "--dry-run", "--allocations", alloc]), \
             contextlib.redirect_stdout(out):
            rc = d.main()
        self.assertEqual(rc, 0)
        self.assertEqual(run.call_count, 1)                      # only pct list
        self.assertIn("DRY RUN complete", out.getvalue())
        self.assertIn("run.sh (runs inside the container", out.getvalue())

    def test_real_run_without_credential_is_refused_before_shipping(self):
        self._write("name: convert\nbudget_usd: 1\n")
        alloc = os.path.join(self.tmp.name, "a.yaml"); open(alloc, "w").write(ALLOC)
        pct_list = "VMID       Status     Lock         Name\n115        running                 tcos-triage-herbert\n"
        fake = mock.Mock(returncode=0, stdout=pct_list.encode(), stderr=b"")
        with mock.patch.object(d.subprocess, "run", return_value=fake) as run, \
             mock.patch.object(sys, "argv", ["hee-pve-dispatch", "ci-triage", self.job, "--allocations", alloc]), \
             contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit):
                d.main()
        self.assertEqual(run.call_count, 1)



class Wif(unittest.TestCase):
    CON = {"organization_id": "org-1", "workspace_id": "wrkspc_1", "service_account_id": "svac_1",
           "federation_rule_id": "fdrl_1", "issuer": "https://issuer.lab.tcos.us", "subject": "pve:ci-triage"}

    def test_mint_jwt_signs_es256_with_the_jwks_kid(self):
        import base64, hashlib, json, subprocess
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
        key = ec.generate_private_key(ec.SECP256R1())
        pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL, serialization.NoEncryption()).decode()
        tok, claims = d.mint_jwt(pem, self.CON, 600)
        h, c, sig = tok.split(".")
        pad = lambda x: x + "=" * (-len(x) % 4)
        header = json.loads(base64.urlsafe_b64decode(pad(h)))
        self.assertEqual(header["alg"], "ES256")
        pub = key.public_key().public_numbers(); raw = b"\x04" + pub.x.to_bytes(32, "big") + pub.y.to_bytes(32, "big")
        self.assertEqual(header["kid"], hashlib.sha256(raw).hexdigest()[:16])
        self.assertEqual(claims["aud"], "https://api.anthropic.com"); self.assertEqual(claims["sub"], "pve:ci-triage")
        self.assertEqual(claims["exp"] - claims["iat"], 600)
        r = base64.urlsafe_b64decode(pad(sig)); der = encode_dss_signature(int.from_bytes(r[:32], "big"), int.from_bytes(r[32:], "big"))
        key.public_key().verify(der, f"{h}.{c}".encode(), ec.ECDSA(hashes.SHA256()))   # raises if wrong

    def test_run_sh_wif_exchanges_and_never_exports_an_api_key(self):
        job = {"name": "j", "prompt": "prompt.md", "budget_usd": 1.0, "timeout_s": 60, "tools": ["Read"], "mode": "default",
               "inputs": [], "outputs": ["out/"], "dir": "/tmp/j"}
        sh = d.render_run_sh(job, "j-1", self.CON)
        self.assertIn("read -r HEE_WIF_JWT", sh); self.assertIn("v1/oauth/token", sh)
        self.assertIn("export ANTHROPIC_AUTH_TOKEN", sh); self.assertIn("unset ANTHROPIC_API_KEY", sh)
        self.assertNotIn("export ANTHROPIC_API_KEY", sh); self.assertIn("fdrl_1", sh)
        self.assertIn("unset HEE_WIF_JWT HEE_WIF_BODY", sh)

    def test_console_block_must_be_complete(self):
        with self.assertRaises(SystemExit):
            d.console_block({"console": {"workspace_id": "w"}}, "ci-triage")
        self.assertEqual(d.console_block({"console": self.CON}, "ci-triage")["federation_rule_id"], "fdrl_1")

if __name__ == "__main__":
    sys.exit(unittest.main())
