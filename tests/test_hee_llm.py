"""hee llm -- a checkout in, a guarded tool loop, a patch out; no node and no model needed here.

The transport is a recorded runner; the model server is a stub on a free
local port that scripts its replies. Nothing reaches a real container.
"""
import datetime as dt
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import yaml

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


class Ledger(unittest.TestCase):
    """The dispatch record: start writes it, ask and collect rewrite it.
    Everything here is a temp directory, never a real ledger."""

    def test_two_starts_in_one_second_get_two_records(self):
        # CORRECTNESS-2 (2026-10-23): same name, same second, no overwrite.
        import datetime as _dt
        with tempfile.TemporaryDirectory() as tmp:
            when = _dt.datetime(2026, 10, 23, 12, 0, 0, tzinfo=_dt.timezone.utc)
            a = L.write_started_record(tmp, "demo", model="m", vmid="1", ticket=None, tools=("read_file",), source={"repo": "r", "ref": "HEAD"}, when=when)
            b = L.write_started_record(tmp, "demo", model="m", vmid="1", ticket=None, tools=("read_file",), source={"repo": "r", "ref": "HEAD"}, when=when)
            self.assertNotEqual(a, b)
            self.assertTrue(os.path.exists(a) and os.path.exists(b))
            import yaml as _yaml
            with open(b) as fh:
                self.assertEqual(_yaml.safe_load(fh)["job"], "demo-20261023T120000Z-2")

    def test_record_writes_leave_no_temp_file_behind(self):
        # CORRECTNESS-1 (2026-10-23): written beside, then renamed into place.
        with tempfile.TemporaryDirectory() as tmp:
            path = L.write_started_record(tmp, "demo", model="m", vmid="1", ticket=None, tools=("read_file",), source={"repo": "r", "ref": "HEAD"})
            self.assertEqual(sorted(os.listdir(tmp)), [os.path.basename(path)])

    def test_ledger_dir_uses_the_given_root(self):
        self.assertEqual(L.ledger_dir("/tmp/x"), "/tmp/x/.hee/dispatch")

    def test_write_started_record_has_the_pve_shaped_keys(self):
        with tempfile.TemporaryDirectory() as d:
            dispatch = os.path.join(d, ".hee", "dispatch")
            when = dt.datetime(2026, 10, 23, 20, 36, 37, tzinfo=dt.timezone.utc)
            path = L.write_started_record(dispatch, "demo", vmid="7", model="default", ticket="0183",
                                           tools=L.READ_TOOLS, source={"repo": ".", "ref": "HEAD"}, when=when)
            self.assertEqual(path, os.path.join(dispatch, "demo-20261023T203637Z.yaml"))
            with open(path, encoding="utf-8") as fh:
                rec = yaml.safe_load(fh)
            self.assertEqual(list(rec.keys()), [
                "job", "name", "agent", "runner", "model", "hostname", "vmid", "endpoint", "ticket", "auth",
                "started_at", "ended_at", "budget_usd", "timeout_s", "tools", "mode", "exit", "cost_usd",
                "num_turns", "is_error", "subtype", "source", "usage", "asks", "review",
            ])
            self.assertEqual(rec["job"], "demo-20261023T203637Z")
            self.assertEqual(rec["name"], "demo")
            self.assertEqual(rec["agent"], "llm")
            self.assertEqual(rec["runner"], "llm")
            self.assertEqual(rec["model"], "default")
            self.assertIsNone(rec["hostname"])
            self.assertEqual(rec["vmid"], "7")
            self.assertIsNone(rec["endpoint"])
            self.assertEqual(rec["ticket"], "0183")
            self.assertEqual(rec["auth"], "none")
            self.assertEqual(rec["started_at"], "2026-10-23T20:36:37+00:00")
            self.assertIsNone(rec["ended_at"])
            self.assertEqual(rec["budget_usd"], 0.0)
            self.assertIsNone(rec["timeout_s"])
            self.assertEqual(rec["tools"], list(L.READ_TOOLS))
            self.assertIsNone(rec["mode"])
            self.assertIsNone(rec["exit"])
            self.assertIsNone(rec["cost_usd"])
            self.assertEqual(rec["num_turns"], 0)
            self.assertIsNone(rec["is_error"])
            self.assertEqual(rec["subtype"], "started")
            self.assertEqual(rec["source"], {"repo": ".", "ref": "HEAD"})
            self.assertEqual(rec["usage"], {"prompt_tokens": 0, "completion_tokens": 0, "steps": 0})
            self.assertEqual(rec["asks"], [])
            self.assertEqual(rec["review"], {"accepted": None, "corrections": None, "mistakes": [],
                                              "merged_pr": None, "reviewer": None, "method": None})

    def test_find_llm_record_picks_the_newest_matching_name_and_runner(self):
        with tempfile.TemporaryDirectory() as d:
            dispatch = os.path.join(d, ".hee", "dispatch")
            os.makedirs(dispatch)
            L.write_started_record(dispatch, "demo", vmid="1", model="default", ticket=None,
                                    tools=L.READ_TOOLS, source={"repo": ".", "ref": "HEAD"},
                                    when=dt.datetime(2026, 10, 23, 10, 0, 0, tzinfo=dt.timezone.utc))
            newest = L.write_started_record(dispatch, "demo", vmid="1", model="default", ticket=None,
                                             tools=L.READ_TOOLS, source={"repo": ".", "ref": "HEAD"},
                                             when=dt.datetime(2026, 10, 23, 11, 0, 0, tzinfo=dt.timezone.utc))
            with open(os.path.join(dispatch, "other-20261023T120000Z.yaml"), "w", encoding="utf-8") as fh:
                yaml.safe_dump({"name": "demo", "runner": "pve"}, fh)
            self.assertEqual(L.find_llm_record(dispatch, "demo"), newest)
            self.assertIsNone(L.find_llm_record(dispatch, "nope"))
            self.assertIsNone(L.find_llm_record(os.path.join(d, "missing"), "demo"))

    def test_append_ask_record_sums_usage_and_appends(self):
        with tempfile.TemporaryDirectory() as d:
            dispatch = os.path.join(d, ".hee", "dispatch")
            path = L.write_started_record(dispatch, "demo", vmid="1", model="default", ticket=None,
                                           tools=L.READ_TOOLS, source={"repo": ".", "ref": "HEAD"})
            long_prompt = "x" * 200
            L.append_ask_record(path, prompt=long_prompt, steps=[{"tool": "read_file"}], stopped=False,
                                 tools=L.READ_TOOLS, usage={"prompt_tokens": 10, "completion_tokens": 4}, endpoint="http://e")
            L.append_ask_record(path, prompt="second", steps=[{"tool": "a"}, {"tool": "b"}], stopped=True,
                                 tools=L.allowed_tools(allow_write=True), usage={"prompt_tokens": 1, "completion_tokens": 1},
                                 endpoint="http://e2")
            with open(path, encoding="utf-8") as fh:
                rec = yaml.safe_load(fh)
            self.assertEqual(rec["num_turns"], 2)
            self.assertEqual(rec["usage"], {"prompt_tokens": 11, "completion_tokens": 5, "steps": 3})
            self.assertEqual(rec["endpoint"], "http://e2")
            self.assertEqual(len(rec["asks"]), 2)
            self.assertEqual(rec["asks"][0]["prompt"], long_prompt[:120])
            self.assertEqual(rec["asks"][0]["steps"], 1)
            self.assertFalse(rec["asks"][0]["stopped"])
            self.assertEqual(rec["asks"][1]["tools"], list(L.allowed_tools(allow_write=True)))
            self.assertTrue(rec["asks"][1]["stopped"])

    def test_finish_collect_record_success_and_empty(self):
        with tempfile.TemporaryDirectory() as d:
            dispatch = os.path.join(d, ".hee", "dispatch")
            path = L.write_started_record(dispatch, "demo", vmid="1", model="default", ticket=None,
                                           tools=L.READ_TOOLS, source={"repo": ".", "ref": "HEAD"})
            L.finish_collect_record(path, results_dir="/tmp/out", patch_path="/tmp/out/demo.patch",
                                     patch_bytes=123, commits=2)
            with open(path, encoding="utf-8") as fh:
                rec = yaml.safe_load(fh)
            self.assertIsNotNone(rec["ended_at"])
            self.assertEqual(rec["exit"], 0)
            self.assertEqual(rec["subtype"], "success")
            self.assertEqual(rec["cost_usd"], 0.0)
            self.assertIn("marginal cost", rec["cost_note"])
            self.assertEqual(rec["results_dir"], "/tmp/out")
            self.assertEqual(rec["patch"], {"path": "/tmp/out/demo.patch", "bytes": 123, "commits": 2})

            path2 = L.write_started_record(dispatch, "demo2", vmid="1", model="default", ticket=None,
                                            tools=L.READ_TOOLS, source={"repo": ".", "ref": "HEAD"})
            L.finish_collect_record(path2, results_dir="/tmp/out2", patch_path="/tmp/out2/demo2.patch",
                                     patch_bytes=0, commits=0)
            with open(path2, encoding="utf-8") as fh:
                rec2 = yaml.safe_load(fh)
            self.assertEqual(rec2["exit"], 2)
            self.assertEqual(rec2["subtype"], "empty")


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
                body = {"choices": [{"finish_reason": "tool_calls" if reply.get("tool_calls") else "stop",
                                      "message": {"role": "assistant", "content": reply.get("content", ""),
                                                  "tool_calls": reply.get("tool_calls")}}]}
                if "usage" in reply:
                    body["usage"] = reply["usage"]
                self._send(body)

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

    def test_context_budget_compacts_oldest_results(self):
        msgs = [{"role": "system", "content": "s"}, {"role": "user", "content": "q"},
                {"role": "assistant", "content": "", "tool_calls": []},
                {"role": "tool", "tool_call_id": "a", "content": "x" * 4000},
                {"role": "tool", "tool_call_id": "b", "content": "y" * 4000}]
        before = L.est_tokens(msgs)
        n = L.compact(msgs, budget=before - 1000)
        self.assertEqual(n, 1, "only the oldest result is cut when that is enough")
        self.assertTrue(msgs[3]["content"].startswith("x" * 300))
        self.assertIn("compacted", msgs[3]["content"])
        self.assertEqual(msgs[4]["content"], "y" * 4000)
        self.assertEqual(L.compact(msgs, budget=10**9), 0)

    def test_web_tools_run_locally_and_only_when_allowed(self):
        # a stub "search engine" and "web page" on a free port; the model asks for both
        class Web(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                if self.path.startswith("/search"):
                    body = (b'<a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.org%2Fa">Alpha <b>page</b></a>'
                            b'<a class="result__snippet" href="x">About alpha &amp; beta</a>')
                else:
                    body = b"<html><head><style>p{}</style><title>T</title></head><body><h1>Hello</h1><p>World &amp; co</p><script>x()</script></body></html>"
                self.send_response(200)
                self.send_header("content-type", "text/html")
                self.end_headers()
                self.wfile.write(body)
        web = ThreadingHTTPServer(("127.0.0.1", 0), Web)
        threading.Thread(target=web.serve_forever, daemon=True).start()
        wurl = f"http://127.0.0.1:{web.server_port}"
        old = os.environ.get("HEE_LLM_SEARCH_URL")
        os.environ["HEE_LLM_SEARCH_URL"] = wurl + "/search?q={q}"
        stub = Stub([{"tool_calls": [tc("web_search", {"query": "alpha"}, "s"), tc("fetch_url", {"url": wurl + "/page"}, "f")]},
                     {"content": "done"}])
        try:
            res = L.ask(stub.url, self.ROOT, "look it up", web=True)
            self.assertEqual(stub.tool_calls, [], "web tools never reach the server's /tools")
            self.assertIn("https://example.org/a", res["steps"][0]["result"])
            self.assertIn("Alpha page", res["steps"][0]["result"])
            self.assertIn("About alpha & beta", res["steps"][0]["result"])
            self.assertIn("Hello", res["steps"][1]["result"])
            self.assertIn("World & co", res["steps"][1]["result"])
            self.assertNotIn("x()", res["steps"][1]["result"])
            names = [d["function"]["name"] for d in stub.chats[0]["tools"]]
            self.assertIn("web_search", names)
            # without --allow-web the same call is refused and nothing is fetched
            stub2 = Stub([{"tool_calls": [tc("fetch_url", {"url": wurl + "/page"})]}, {"content": "ok"}])
            try:
                res2 = L.ask(stub2.url, self.ROOT, "fetch")
            finally:
                stub2.close()
            self.assertIn("not allowed", res2["steps"][0]["result"])
            self.assertNotIn("fetch_url", [d["function"]["name"] for d in stub2.chats[0]["tools"]])
        finally:
            stub.close()
            web.shutdown()
            if old is None:
                os.environ.pop("HEE_LLM_SEARCH_URL", None)
            else:
                os.environ["HEE_LLM_SEARCH_URL"] = old

    def test_html_text(self):
        self.assertEqual(L.html_text("<p>a &lt; b</p>\n\n\n\n<p>c</p>"), "a < b\n\nc")

    def test_step_budget_ends_with_a_forced_answer(self):
        # distinct calls each time, so the repeat rule does not fire; the budget does
        script = [{"tool_calls": [tc("read_file", {"path": f"f{i}"})]} for i in range(3)] + [{"content": "from what I read: X"}]
        stub = Stub(script)
        try:
            res = L.ask(stub.url, self.ROOT, "loop", max_steps=3)
        finally:
            stub.close()
        self.assertEqual(res["answer"], "from what I read: X")
        self.assertFalse(res["stopped"])
        self.assertEqual(res["ended_by"], "the 3-step budget")
        self.assertEqual(len(res["steps"]), 2, "the last step's call is not executed")
        self.assertEqual(stub.chats[-1].get("tools", []), [], "the final request carries no tools")
        self.assertIn("tool phase is over", stub.chats[-1]["messages"][-1]["content"])

    def test_repeated_call_ends_the_tool_phase(self):
        stub = Stub([{"tool_calls": [tc("read_file", {"path": "same"})]}] * 3 + [{"content": "I could not read past line 60."}])
        try:
            res = L.ask(stub.url, self.ROOT, "loop", max_steps=10)
        finally:
            stub.close()
        self.assertEqual(res["ended_by"], "a call repeated three times")
        self.assertEqual(len(res["steps"]), 2)
        self.assertIn("could not read", res["answer"])

    def test_unreachable(self):
        with self.assertRaises(L.LlmError):
            L.fetch_tools("http://127.0.0.1:9", L.READ_TOOLS, timeout=2)

    def test_chat_returns_usage_when_the_server_sends_it(self):
        stub = Stub([{"content": "hi", "usage": {"prompt_tokens": 7, "completion_tokens": 3}}])
        try:
            choice, usage = L.chat(stub.url, [{"role": "user", "content": "hi"}], [])
        finally:
            stub.close()
        self.assertEqual(usage, {"prompt_tokens": 7, "completion_tokens": 3})
        self.assertEqual(choice["message"]["content"], "hi")

    def test_chat_usage_is_empty_when_the_server_sends_none(self):
        stub = Stub([{"content": "hi"}])
        try:
            _, usage = L.chat(stub.url, [{"role": "user", "content": "hi"}], [])
        finally:
            stub.close()
        self.assertEqual(usage, {})

    def test_ask_sums_usage_across_every_chat_call(self):
        stub = Stub([
            {"tool_calls": [tc("read_file", {"path": "f"})], "usage": {"prompt_tokens": 10, "completion_tokens": 2}},
            {"content": "done", "usage": {"prompt_tokens": 5, "completion_tokens": 8}},
        ])
        try:
            res = L.ask(stub.url, self.ROOT, "q")
        finally:
            stub.close()
        self.assertEqual(res["usage"], {"prompt_tokens": 15, "completion_tokens": 10})


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


class Records(unittest.TestCase):
    """The ledger through the real binary: --repo-name sidesteps the ssh
    lookup inside cmd_ask, so --endpoint can point straight at the stub and
    `job ask` runs for real, record included."""

    def run_tool(self, *args, env=None):
        e = {k: v for k, v in os.environ.items() if not k.startswith("HEE_LLM_")}
        e.update(env or {})
        r = subprocess.run([str(TOOL), *args], capture_output=True, text=True, env=e, check=False)
        return r.returncode, r.stdout, r.stderr

    def test_start_dry_run_writes_no_record(self):
        with tempfile.TemporaryDirectory() as d:
            rc, out, _ = self.run_tool("job", "start", "demo", "--repo", str(ROOT), "--dry-run",
                                        "--host", "h", "--vmid", "1", "--ledger", d, "--ticket", "0183")
            self.assertEqual(rc, 0, out)
            self.assertFalse(os.path.exists(os.path.join(d, ".hee", "dispatch")))

    def test_ask_updates_the_record_under_ledger(self):
        stub = Stub([{"tool_calls": [tc("read_file", {"path": "f"})], "usage": {"prompt_tokens": 9, "completion_tokens": 2}},
                     {"content": "the answer", "usage": {"prompt_tokens": 3, "completion_tokens": 4}}])
        try:
            with tempfile.TemporaryDirectory() as d:
                dispatch = os.path.join(d, ".hee", "dispatch")
                path = L.write_started_record(dispatch, "demo", vmid="1", model="default", ticket=None,
                                               tools=L.READ_TOOLS, source={"repo": ".", "ref": "HEAD"})
                rc, out, err = self.run_tool("job", "ask", "demo", "what does it say?", "--repo-name", "repo",
                                              "--endpoint", stub.url, "--ledger", d)
                self.assertEqual(rc, 0, err)
                self.assertIn("the answer", out)
                with open(path, encoding="utf-8") as fh:
                    rec = yaml.safe_load(fh)
                self.assertEqual(rec["num_turns"], 1)
                self.assertEqual(rec["usage"], {"prompt_tokens": 12, "completion_tokens": 6, "steps": 1})
                self.assertEqual(rec["endpoint"], stub.url)
                self.assertEqual(len(rec["asks"]), 1)
                self.assertEqual(rec["asks"][0]["prompt"], "what does it say?")
                self.assertFalse(rec["asks"][0]["stopped"])
        finally:
            stub.close()

    def test_ask_without_a_record_warns_and_still_answers(self):
        stub = Stub([{"content": "ok"}])
        try:
            with tempfile.TemporaryDirectory() as d:
                rc, out, err = self.run_tool("job", "ask", "nosuchjob", "hi", "--repo-name", "repo",
                                              "--endpoint", stub.url, "--ledger", d)
                self.assertEqual(rc, 0, err)
                self.assertIn("ok", out)
                self.assertIn("no dispatch record", err)
                self.assertIn(d, err)
        finally:
            stub.close()


if __name__ == "__main__":
    unittest.main()
