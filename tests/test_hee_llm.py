"""hee llm -- a checkout in, a guarded tool loop, a patch out; no node and no model needed here.

The transport is a recorded runner; the model server is a stub on a free
local port that scripts its replies. Nothing reaches a real container.
"""
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tooling" / "bin" / "hee-llm"
sys.path.insert(0, str(ROOT / "library" / "py"))
import hee_llm as L


class Recorder:
    """A runner that records argv + stdin and answers from a script keyed by a substring of the shell."""

    def __init__(self, answers=None, fail_on=None):
        self.calls = []
        self.answers = answers or {}
        self.fail_on = fail_on

    def __call__(self, cmd, stdin):
        self.calls.append((cmd, stdin))
        shell = L.remote_shell(cmd) if cmd[0] == "ssh" else cmd[-1]
        rc = 1 if self.fail_on and self.fail_on in shell else 0
        out = b""
        for k, v in self.answers.items():
            if k in shell:
                out = v if isinstance(v, bytes) else v.encode()
        return subprocess.CompletedProcess(cmd, rc, stdout=out, stderr=b"boom" if rc else b"")


class Names(unittest.TestCase):
    def test_valid_and_invalid(self):
        for ok in ("fix-readme", "job.1", "A_b"):
            self.assertEqual(L.valid_name(ok), ok)
        for bad in ("", ".hidden", "a/b", "x" * 65, "sp ace"):
            with self.assertRaises(L.LlmError):
                L.valid_name(bad)

    def test_root_and_transport_argv(self):
        self.assertEqual(L.job_root("j", "repo"), "/var/lib/llm/work/j/repo")
        argv = L.pct_shell("pve.example", 120, "echo 'it''s' \"ok\"")
        self.assertEqual(argv[:4], ["ssh", "-o", "BatchMode=yes", "root@pve.example"])
        self.assertEqual(len(argv), 5, "one remote string, so ssh cannot re-split it")
        self.assertTrue(argv[4].startswith("pct exec 120 -- su -s /bin/sh llm -c "))
        self.assertEqual(L.remote_shell(argv), "echo 'it''s' \"ok\"")
        with self.assertRaises(L.LlmError):
            L.pct_shell("", 120, "true")
        with self.assertRaises(L.LlmError):
            L.pct_shell("h", "abc", "true")


class Transport(unittest.TestCase):
    def test_start_ships_the_archive_and_tags_baseline(self):
        rec = Recorder()
        res = L.start("demo", str(ROOT), host="h", vmid=1, ref="HEAD", runner=rec)
        self.assertEqual(res["repo"], ROOT.name)
        self.assertGreater(res["bytes"], 10000)
        cmd, stdin = rec.calls[0]
        self.assertEqual(len(stdin), res["bytes"])
        shell = L.remote_shell(cmd)
        for part in ("mkdir -p", "tar -x", "git init -q", "git add -A", "commit -q --allow-empty -m baseline", "git tag -f baseline", ".repo"):
            self.assertIn(part, shell)
        self.assertIn(f"/var/lib/llm/work/demo/{ROOT.name}", shell)

    def test_start_from_a_path_inside_the_container(self):
        rec = Recorder()
        res = L.start("demo", host="h", vmid=1, from_path="/data/storage/git/fleet-ops", runner=rec)
        self.assertEqual(res["repo"], "fleet-ops")
        self.assertEqual(res["bytes"], 0)
        cmd, stdin = rec.calls[0]
        self.assertIsNone(stdin, "nothing crosses the wire")
        shell = L.remote_shell(cmd)
        self.assertIn("cp -r /data/storage/git/fleet-ops /var/lib/llm/work/demo/fleet-ops", shell)
        self.assertNotIn("git clone", shell, "a clone of root's tree is refused as dubious ownership; the copy is the job user's own")
        self.assertIn("git tag -f baseline", shell)
        self.assertIn(".repo", shell)
        with self.assertRaises(L.LlmError):
            L.start("demo", str(ROOT), host="h", vmid=1, from_path="/x", runner=rec)     # both sources
        with self.assertRaises(L.LlmError):
            L.start("demo", host="h", vmid=1, runner=rec)                                 # neither
        with self.assertRaises(L.LlmError):
            L.start("demo", host="h", vmid=1, from_path="relative/path", runner=rec)

    def test_start_dry_run_touches_nothing(self):
        rec = Recorder()
        res = L.start("demo", str(ROOT), host="", vmid="", dry_run=True, runner=rec)
        self.assertTrue(res["dry_run"])
        self.assertEqual(rec.calls, [])

    def test_archive_refuses_a_bad_ref(self):
        with self.assertRaises(L.LlmError):
            L.archive(str(ROOT), "no-such-ref-zzz")

    def test_collect_commits_leftovers_and_writes_the_patch(self):
        patch = b"From 0123456789abcdef0123456789abcdef01234567 Mon Sep 17 00:00:00 2001\nSubject: [PATCH] x\n\n---\n a | 1 +\n"
        rec = Recorder({"cat /var/lib/llm/work/demo/.repo": "repo\n", "format-patch": patch})
        with tempfile.TemporaryDirectory() as d:
            res = L.collect("demo", d, host="h", vmid=1, runner=rec)
            self.assertEqual(res["commits"], 1)
            self.assertEqual(Path(res["path"]).read_bytes(), patch)
        shell = L.remote_shell(rec.calls[-1][0])
        for part in ("git add -A", "git diff --cached --quiet ||", "commit -q -m 'hee llm job demo'", "git format-patch baseline --stdout"):
            self.assertIn(part, shell)

    def test_list_and_remove(self):
        rec = Recorder({"ls -1": "demo\n.hidden\nother\n"})
        self.assertEqual(L.list_jobs(host="h", vmid=1, runner=rec), ["demo", "other"])
        L.remove("demo", host="h", vmid=1, runner=rec)
        self.assertIn("rm -rf /var/lib/llm/work/demo /var/lib/llm/out/demo", L.remote_shell(rec.calls[-1][0]))
        with self.assertRaises(L.LlmError):
            L.remove("../etc", host="h", vmid=1, runner=rec)

    def test_a_failing_node_is_a_refusal(self):
        rec = Recorder(fail_on="ls -1")
        with self.assertRaises(L.LlmError):
            L.list_jobs(host="h", vmid=1, runner=rec)


class Guard(unittest.TestCase):
    ROOT = "/var/lib/llm/work/j/repo"

    def test_relative_paths_are_rooted(self):
        args, refusal = L.guard("read_file", {"path": "README.md"}, self.ROOT)
        self.assertIsNone(refusal)
        self.assertEqual(args["path"], self.ROOT + "/README.md")

    def test_inside_absolute_is_fine_outside_is_refused(self):
        _, refusal = L.guard("read_file", {"path": self.ROOT + "/pve/x.yaml"}, self.ROOT)
        self.assertIsNone(refusal)
        for bad in ("/etc/passwd", "../../../etc/passwd", self.ROOT + "/../other", "/var/lib/llm/work/j/repo2/x"):
            _, refusal = L.guard("read_file", {"path": bad}, self.ROOT)
            self.assertIsNotNone(refusal, bad)
            self.assertIn("outside the job root", refusal)

    def test_read_roots_open_reads_only(self):
        mirror = "/data/storage/git"
        args, refusal = L.guard("read_file", {"path": mirror + "/inventory/README.md"}, self.ROOT, (mirror,))
        self.assertIsNone(refusal)
        self.assertEqual(args["path"], mirror + "/inventory/README.md")
        _, refusal = L.guard("write_file", {"path": mirror + "/inventory/README.md"}, self.ROOT, (mirror,))
        self.assertIsNotNone(refusal, "a write tool is still held to the job root")
        _, refusal = L.guard("read_file", {"path": "/data/storage/llm/models/x.gguf"}, self.ROOT, (mirror,))
        self.assertIsNotNone(refusal, "a read outside both the root and the read roots is refused")
        _, refusal = L.guard("read_file", {"path": mirror + "/../llm/x"}, self.ROOT, (mirror,))
        self.assertIsNotNone(refusal, "dot-dot does not escape a read root")

    def test_shell_is_cd_into_root(self):
        args, refusal = L.guard("exec_shell_command", {"command": "ls; cat x"}, self.ROOT)
        self.assertIsNone(refusal)
        self.assertEqual(args["command"], f"cd {self.ROOT} && (ls; cat x)")

    def test_allowed_sets(self):
        self.assertEqual(L.allowed_tools(), L.READ_TOOLS)
        self.assertIn("write_file", L.allowed_tools(allow_write=True))
        self.assertNotIn("exec_shell_command", L.allowed_tools(allow_write=True))
        self.assertIn("exec_shell_command", L.allowed_tools(allow_shell=True))


def _defs():
    return [{"display_name": n, "tool": n, "type": "server", "permissions": {"write": n in L.WRITE_TOOLS + L.SHELL_TOOLS},
             "definition": {"type": "function", "function": {"name": n, "description": n, "parameters": {"type": "object", "properties": {}}}}}
            for n in L.READ_TOOLS + L.WRITE_TOOLS + L.SHELL_TOOLS]


class Stub:
    """llama-server's agent surface: GET /tools, POST /tools, POST /v1/chat/completions (scripted)."""

    def __init__(self, script):
        outer = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _send(self, obj, code=200):
                b = json.dumps(obj).encode()
                self.send_response(code)
                self.send_header("content-type", "application/json")
                self.end_headers()
                self.wfile.write(b)

            def do_GET(self):
                if self.path == "/tools":
                    return self._send(_defs())
                self._send({"error": {"message": "nope"}}, 404)

            def do_POST(self):
                n = int(self.headers.get("content-length") or 0)
                req = json.loads(self.rfile.read(n))
                if self.path == "/tools":
                    outer.tool_calls.append(req)
                    return self._send({"plain_text_response": f"content of {req['params'].get('path', '?')}"})
                outer.chats.append(req)
                reply = outer.script[min(len(outer.chats) - 1, len(outer.script) - 1)]
                self._send({"choices": [{"finish_reason": "tool_calls" if reply.get("tool_calls") else "stop",
                                         "message": {"role": "assistant", "content": reply.get("content", ""),
                                                     "tool_calls": reply.get("tool_calls")}}]})

        self.script, self.chats, self.tool_calls = script, [], []
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.srv.server_port}"
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def close(self):
        self.srv.shutdown()


def tc(name, args, cid="c1"):
    return {"id": cid, "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}


class Loop(unittest.TestCase):
    ROOT = "/var/lib/llm/work/j/repo"

    def test_fetch_tools_filters_to_allowed(self):
        stub = Stub([])
        try:
            names = [d["function"]["name"] for d in L.fetch_tools(stub.url, L.READ_TOOLS)]
        finally:
            stub.close()
        self.assertEqual(names, list(L.READ_TOOLS))

    def test_loop_reads_then_answers(self):
        stub = Stub([{"tool_calls": [tc("read_file", {"path": "README.md"})]}, {"content": "It says hello."}])
        try:
            res = L.ask(stub.url, self.ROOT, "What does the README say?")
        finally:
            stub.close()
        self.assertEqual(res["answer"], "It says hello.")
        self.assertFalse(res["stopped"])
        self.assertEqual(len(res["steps"]), 1)
        self.assertEqual(stub.tool_calls[0], {"tool": "read_file", "params": {"path": self.ROOT + "/README.md"}})
        self.assertEqual(len(stub.chats), 2)
        self.assertEqual(stub.chats[1]["messages"][-1]["role"], "tool")
        self.assertIn("content of", stub.chats[1]["messages"][-1]["content"])
        self.assertEqual([t["function"]["name"] for t in stub.chats[0]["tools"]], list(L.READ_TOOLS))

    def test_guard_and_disallowed_tools_are_told_to_the_model_not_executed(self):
        stub = Stub([{"tool_calls": [tc("read_file", {"path": "/etc/passwd"}, "a"), tc("exec_shell_command", {"command": "rm -rf /"}, "b")]},
                     {"content": "ok"}])
        try:
            res = L.ask(stub.url, self.ROOT, "do bad things")
        finally:
            stub.close()
        self.assertEqual(stub.tool_calls, [], "nothing was executed")
        self.assertIn("outside the job root", res["steps"][0]["result"])
        self.assertIn("not allowed", res["steps"][1]["result"])
        self.assertEqual(res["answer"], "ok")

    def test_shell_allowed_is_cd_into_root(self):
        stub = Stub([{"tool_calls": [tc("exec_shell_command", {"command": "git status"})]}, {"content": "clean"}])
        try:
            L.ask(stub.url, self.ROOT, "status?", allow=L.allowed_tools(allow_shell=True))
        finally:
            stub.close()
        self.assertEqual(stub.tool_calls[0]["params"]["command"], f"cd {self.ROOT} && (git status)")

    def test_tool_results_are_clipped(self):
        self.assertEqual(L.clip("short", 10), "short")
        out = L.clip("x" * 100, 10)
        self.assertTrue(out.startswith("x" * 10))
        self.assertIn("90 more characters not shown", out)
        stub = Stub([{"tool_calls": [tc("read_file", {"path": "big"})]}, {"content": "ok"}])
        try:
            res = L.ask(stub.url, self.ROOT, "read big", max_result_chars=8)
        finally:
            stub.close()
        self.assertIn("more characters not shown", res["steps"][0]["result"])
        self.assertIn("more characters not shown", stub.chats[1]["messages"][-1]["content"])

    def test_step_budget(self):
        stub = Stub([{"tool_calls": [tc("read_file", {"path": "a"})]}])   # never answers
        try:
            res = L.ask(stub.url, self.ROOT, "loop", max_steps=3)
        finally:
            stub.close()
        self.assertTrue(res["stopped"])
        self.assertEqual(len(res["steps"]), 3)

    def test_unreachable(self):
        with self.assertRaises(L.LlmError):
            L.fetch_tools("http://127.0.0.1:9", L.READ_TOOLS, timeout=2)


class Cli(unittest.TestCase):
    def run_tool(self, *args, env=None):
        e = {k: v for k, v in os.environ.items() if not k.startswith("HEE_LLM_")}
        e.update(env or {})
        r = subprocess.run([str(TOOL), *args], capture_output=True, text=True, env=e, check=False)
        return r.returncode, r.stdout, r.stderr

    def test_help_runs_nothing(self):
        rc, out, err = self.run_tool("job", "rm", "help", "demo", "--host", "h", "--vmid", "1")
        self.assertEqual(rc, 0)
        self.assertIn("SYNOPSIS", out)
        self.assertIn("not executed", err)

    def test_tools_lists(self):
        rc, out, _ = self.run_tool("tools")
        self.assertEqual(rc, 0)
        self.assertEqual(out.split(), list(L.READ_TOOLS))
        rc, out, _ = self.run_tool("tools", "--allow-write", "--allow-shell")
        self.assertIn("exec_shell_command", out)

    def test_start_from_dry_run(self):
        rc, out, _ = self.run_tool("job", "start", "ci-demo", "--from", "/data/storage/git/repo", "--dry-run", "--host", "pve.example", "--vmid", "1")
        self.assertEqual(rc, 0, out)
        self.assertIn("would copy /data/storage/git/repo", out)

    def test_start_dry_run_needs_no_node(self):
        rc, out, _ = self.run_tool("job", "start", "ci-demo", "--repo", str(ROOT), "--dry-run", "--host", "pve.example", "--vmid", "1")
        self.assertEqual(rc, 0, out)
        self.assertIn("would ship", out)
        self.assertIn("nothing shipped", out)

    def test_missing_node_is_unknown(self):
        rc, _, err = self.run_tool("job", "list")
        self.assertEqual(rc, 3)
        self.assertIn("HEE_LLM_HOST", err)
        rc, _, err = self.run_tool("job", "ask", "demo", "hi", "--host", "h", "--vmid", "1")
        self.assertEqual(rc, 3)
        self.assertIn("HEE_LLM_ENDPOINT", err)


if __name__ == "__main__":
    unittest.main()
