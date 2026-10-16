"""hee bench -- deterministic graders, RPN scoring, a run against a stub, offline re-grading.

Nothing here reaches a real model: the endpoint is a stub HTTP server on a
free local port that answers from a table, and every grader is pure. The
fixture run under tests/fixtures/bench was produced the same way.
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

import yaml

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tooling" / "bin" / "hee-bench"
CASES = ROOT / "tests" / "fixtures" / "bench" / "cases"
RUN = ROOT / "tests" / "fixtures" / "bench" / "run.json"
sys.path.insert(0, str(ROOT / "library" / "py"))
import hee_bench as B


def case(**over):
    base = {"kind": "predicate", "source": "test", "prompt": "p?", "expected": "YES"}
    base.update(over)
    return B.validate_case(base, "t")


class Graders(unittest.TestCase):
    def test_predicate_first_word_variants(self):
        c = case()
        for ans in ("YES", "Yes.", "yes, because", "  Yes\n", "<think>hmm</think>YES"):
            self.assertTrue(B.grade(c, ans)["pass"], ans)
        for ans in ("NO", "No, it is not", "Maybe", "", "I think yes"):
            self.assertFalse(B.grade(c, ans)["pass"], ans)

    def test_choice(self):
        c = case(kind="choice", choices=["OK", "WARNING", "CRITICAL", "UNKNOWN"], expected="WARNING")
        self.assertTrue(B.grade(c, "Warning")["pass"])
        self.assertTrue(B.grade(c, "WARNING.")["pass"])
        self.assertFalse(B.grade(c, "CRITICAL")["pass"])
        self.assertEqual(B.grade(c, "critical")["got"], "CRITICAL")

    def test_set_order_case_and_trailing_comma(self):
        c = case(kind="set", expected=["llm-1", "haproxy", "ns1", "flippy"])
        self.assertTrue(B.grade(c, "ns1, Flippy, llm-1, haproxy,")["pass"])
        self.assertTrue(B.grade(c, "ns1\nflippy\nllm-1\nhaproxy")["pass"])
        g = B.grade(c, "llm-1, haproxy, ns1,")   # cut off by a token cap
        self.assertFalse(g["pass"])
        self.assertIn("missing flippy", g["detail"])
        g = B.grade(c, "llm-1, haproxy, ns1, flippy, pve")
        self.assertIn("extra pve", g["detail"])

    def test_set_none_is_empty(self):
        c = case(kind="set", expected=[])
        self.assertTrue(B.grade(c, "NONE")["pass"])
        self.assertTrue(B.grade(c, "none.")["pass"])
        self.assertFalse(B.grade(c, "alpha-1")["pass"])
        self.assertEqual(B.grade(c, "NONE")["got"], "NONE")

    def test_exact_folds_whitespace_case_and_period(self):
        c = case(kind="exact", expected="10.0.0.169")
        self.assertTrue(B.grade(c, " 10.0.0.169.\n")["pass"])
        self.assertFalse(B.grade(c, "10.0.0.168")["pass"])
        c = case(kind="exact", expected="Hello   World")
        self.assertTrue(B.grade(c, "hello world")["pass"])

    def test_specifics_extraction(self):
        s = B.specifics("Add deb http://download.proxmox.com/debian/pve bookworm, key proxmox-release-bookworm.gpg, "
                        "check ns1.lab.local and ct127, version 8.1.3, address 10.0.0.194, see 1.2.3.4/32.")
        self.assertIn("http://download.proxmox.com/debian/pve", s)
        self.assertIn("ns1.lab.local", s)
        self.assertIn("ct127", s)
        self.assertIn("10.0.0.194", s)
        self.assertIn("1.2.3.4", s)
        self.assertNotIn("8.1.3", s, "a version is not a host")
        self.assertNotIn("proxmox-release-bookworm.gpg", s, "a file is not a host")
        self.assertNotIn("download.proxmox.com", s, "the host inside a found URL is reported once, as the URL")
        s = B.specifics("Save output to a file (e.g., evidence.txt) before touching repos, i.e. now; at 9 a.m. check ns1.lab.local.")
        self.assertEqual(s, {"ns1.lab.local"}, "e.g / i.e / a.m are abbreviations, not hosts (first real run, 2026-10-16)")

    def test_no_invented_against_prompt_and_allowed(self):
        c = case(kind="no_invented", expected=None,
                 prompt="FACTS: ct101 ns-1 10.0.0.5; ct103 proxy-1. Add the vendor repository.",
                 allowed=["example.org"])
        ok = B.grade(c, "1. start ct101 ns-1 (10.0.0.5)\n2. start ct103 proxy-1\n3. docs at example.org")
        self.assertTrue(ok["pass"], ok)
        bad = B.grade(c, "1. add deb http://download.proxmox.com/debian/pve bookworm pve-no-subscription\n"
                         "2. check ns1.lab.local and ct127 and 10.0.0.9")
        self.assertFalse(bad["pass"])
        for s in ("http://download.proxmox.com/debian/pve", "ns1.lab.local", "ct127", "10.0.0.9"):
            self.assertIn(s, bad["detail"])
        self.assertEqual(bad["got"], "4 invented")

    def test_thinking_trace_is_stripped(self):
        self.assertEqual(B.strip_thinking("<think>\nlong\nthoughts\n</think>\nNO"), "NO")


class Cases(unittest.TestCase):
    def test_fixture_corpus_loads(self):
        cases = B.load_cases(CASES)
        self.assertEqual([c["name"] for c in cases],
                         ["choice-check-state", "no-invented-plan", "predicate-conventional-subject", "set-hostnames"])
        by = {c["name"]: c for c in cases}
        self.assertEqual(by["predicate-conventional-subject"]["expected"], "YES")
        self.assertEqual(by["choice-check-state"]["choices"], ["OK", "WARNING", "CRITICAL", "UNKNOWN"])
        self.assertEqual(by["no-invented-plan"]["allowed"], ["example.org"])
        self.assertEqual(by["set-hostnames"]["max_tokens"], 32)

    def test_only_and_missing(self):
        self.assertEqual(len(B.load_cases(CASES, only=["set-hostnames"])), 1)
        with self.assertRaises(B.BenchError):
            B.load_cases(CASES, only=["no-such-case"])

    def test_defaults(self):
        c = case()
        self.assertEqual((c["max_tokens"], c["severity"], c["detection"]), (8, 5, 5))
        self.assertEqual(case(kind="no_invented", expected=None)["max_tokens"], 1024)

    def test_refusals(self):
        bad = [
            {"kind": "maybe"},
            {"expected": "MAYBE"},
            {"source": ""},
            {"prompt": ""},
            {"bogus": 1},
            {"severity": 11},
            {"detection": 0},
            {"max_tokens": "8"},
            {"allowed": ["x"]},                                   # allowed on a predicate
            {"kind": "choice", "choices": ["A"], "expected": "A"},      # one choice is no choice
            {"kind": "choice", "choices": ["A", "B"], "expected": "C"},
            {"kind": "set", "expected": "a, b"},                     # a set is a list
            {"kind": "no_invented", "expected": "YES"},
        ]
        for over in bad:
            with self.assertRaises(B.BenchError, msg=over):
                case(**over)


class Scoring(unittest.TestCase):
    def test_occurrence_is_measured(self):
        self.assertEqual(B.occurrence(0, 1), 0)
        self.assertEqual(B.occurrence(0, 5), 0)
        self.assertEqual(B.occurrence(1, 1), 10)
        self.assertEqual(B.occurrence(1, 3), 4)
        self.assertEqual(B.occurrence(1, 100), 1)
        self.assertEqual(B.occurrence(5, 5), 10)
        with self.assertRaises(B.BenchError):
            B.occurrence(0, 0)

    def test_rpn_and_summary(self):
        self.assertEqual(B.rpn(7, 10, 8), 560)
        saved = B.load_run(RUN)
        s = saved["summary"]
        self.assertEqual((s["cases"], s["passed"], s["failed"], s["rpn_total"]), (4, 4, 0, 0))
        self.assertEqual(s["rpn_ceiling"], sum(r["severity"] * 10 * r["detection"] for r in saved["results"]))

    def test_regrade_recomputes_from_raw(self):
        saved = B.load_run(RUN)
        saved["results"][0]["attempts"][0]["raw"] = "definitely not"
        re = B.regrade(saved)
        self.assertEqual(re["summary"]["failed"], 1)
        r = re["results"][0]
        self.assertEqual(r["occurrence"], 10)
        self.assertEqual(r["rpn"], r["severity"] * 10 * r["detection"])
        self.assertEqual(re["summary"]["worst"][0]["name"], r["name"])
        self.assertIn("regraded_utc", re)

    def test_regrade_keeps_an_empty_set_and_no_choices(self):
        none_case = case(kind="set", expected=[], max_tokens=8)
        plan_case = case(kind="no_invented", expected=None, prompt="FACTS: ct101 ns-1", allowed=[])
        saved = {"hee_bench": 1, "results": [
            B._record(none_case, [{"raw": "NONE", **B.grade(none_case, "NONE")}]),
            B._record(plan_case, [{"raw": "start ct101 ns-1", **B.grade(plan_case, "start ct101 ns-1")}]),
        ]}
        re = B.regrade(saved)       # failed on 2026-10-16's first real run: expected [] was dropped
        self.assertEqual(re["summary"]["passed"], 2)
        self.assertEqual(re["results"][0]["expected"], [])

    def test_report_table(self):
        md = B.report_md([B.load_run(RUN), B.regrade(B.load_run(RUN))])
        self.assertIn("| set-hostnames |", md)
        self.assertIn("fixture-model-q4 @ 2026-10-16T00:00", md)
        self.assertIn("4/4", md)
        self.assertEqual(md.count("| ok | ok |"), 4)


class Stub:
    """An OpenAI-compatible server that answers from a table keyed by prompt text."""

    def __init__(self, answers: dict):
        outer = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _send(self, obj):
                body = json.dumps(obj).encode()
                self.send_response(200)
                self.send_header("content-type", "application/json")
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                self._send({"object": "list", "data": [{"id": "stub-model", "object": "model"}]})

            def do_POST(self):
                n = int(self.headers.get("content-length") or 0)
                req = json.loads(self.rfile.read(n))
                outer.requests.append(req)
                user = req["messages"][-1]["content"]
                ans = next((v for k, v in answers.items() if k in user), "")
                self._send({"choices": [{"message": {"role": "assistant", "content": ans}, "finish_reason": "stop"}],
                            "usage": {"prompt_tokens": 10, "completion_tokens": 2},
                            "timings": {"predicted_per_second": 25.0}})

        self.requests = []
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.srv.server_port}"
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def close(self):
        self.srv.shutdown()


GOOD = {"Conventional Commits": "YES", "disk /data": "WARNING",
        "alpha-1 behind": "ns-1, alpha-1, desk-2, proxy-1",
        "FACTS:": "1. ct101 ns-1 at 10.0.0.5\n2. ct103 proxy-1 at 10.0.0.6\n3. ct105 app-1 (measure the lease)"}


class Running(unittest.TestCase):
    def test_run_passes_and_records(self):
        stub = Stub(GOOD)
        try:
            run = B.run(B.load_cases(CASES), stub.url, repeats=2)
        finally:
            stub.close()
        self.assertEqual(run["summary"]["passed"], 4)
        self.assertEqual(run["summary"]["rpn_total"], 0)
        self.assertEqual(run["served_model"], "stub-model")
        self.assertEqual(len(stub.requests), 8)
        self.assertTrue(all(r["temperature"] == 0 for r in stub.requests))
        self.assertEqual(run["summary"]["tok_per_s_median"], 25.0)
        r = {x["name"]: x for x in run["results"]}["no-invented-plan"]
        self.assertEqual(r["repeats"], 2)
        plan = [q for q in stub.requests if "FACTS:" in q["messages"][-1]["content"]]
        self.assertEqual([q["max_tokens"] for q in plan], [400, 400])

    def test_run_scores_a_failure(self):
        bad = dict(GOOD)
        bad["FACTS:"] = "1. add deb http://download.vendor.example/pve bookworm main\n2. start ct101 ns-1"
        stub = Stub(bad)
        try:
            run = B.run(B.load_cases(CASES), stub.url)
        finally:
            stub.close()
        self.assertEqual(run["summary"]["failed"], 1)
        r = {x["name"]: x for x in run["results"]}["no-invented-plan"]
        self.assertEqual(r["rpn"], 7 * 10 * 8)
        self.assertIn("http://download.vendor.example/pve", r["attempts"][0]["detail"])

    def test_unreachable_is_a_refusal(self):
        with self.assertRaises(B.BenchError):
            B.chat("http://127.0.0.1:9", case(), timeout=2)


class Cli(unittest.TestCase):
    def run_tool(self, *args, env=None):
        e = dict(os.environ)
        e.pop("HEE_BENCH_CASES", None)
        e.pop("HEE_BENCH_ENDPOINT", None)
        e.update(env or {})
        r = subprocess.run([str(TOOL), *args], capture_output=True, text=True, env=e, check=False)
        return r.returncode, r.stdout, r.stderr

    def test_help_runs_nothing_to_its_right(self):
        rc, out, err = self.run_tool("run", "help", "--endpoint", "http://127.0.0.1:9")
        self.assertEqual(rc, 0)
        self.assertIn("SYNOPSIS", out)
        self.assertIn("not executed", err)
        rc, out, _ = self.run_tool()
        self.assertEqual(rc, 0)
        self.assertIn("SYNOPSIS", out)

    def test_list_and_check(self):
        rc, out, _ = self.run_tool("list", "--cases", str(CASES))
        self.assertEqual(rc, 0)
        self.assertIn("no-invented-plan", out)
        self.assertIn("no_invented", out)
        rc, out, _ = self.run_tool("check", "--cases", str(CASES))
        self.assertEqual(rc, 0, out)
        self.assertIn("4 case file(s) valid", out)

    def test_check_names_the_bad_file(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "ok.yaml").write_text(yaml.safe_dump({"kind": "predicate", "source": "t", "prompt": "p",
                                                          "expected": "NO"}), encoding="utf-8")
            Path(d, "bad.yaml").write_text("kind: predicate\nprompt: p\nexpected: MAYBE\n", encoding="utf-8")
            rc, out, err = self.run_tool("check", "--cases", d)
            self.assertEqual(rc, 2)
            self.assertIn("bad.yaml", out + err)
            self.assertIn("1 of 2", out + err)

    def test_no_cases_is_unknown(self):
        rc, _, err = self.run_tool("list")
        self.assertEqual(rc, 3)
        self.assertIn("HEE_BENCH_CASES", err)
        rc, _, _ = self.run_tool("list", "--cases", "/nonexistent/dir")
        self.assertEqual(rc, 3)

    def test_dry_run_sends_nothing(self):
        rc, out, _ = self.run_tool("run", "--cases", str(CASES), "--endpoint", "http://127.0.0.1:9", "--dry-run")
        self.assertEqual(rc, 0, out)
        self.assertIn("nothing sent", out)
        self.assertEqual(out.count("/v1/chat/completions"), 4)

    def test_run_against_stub_writes_a_file(self):
        stub = Stub(GOOD)
        try:
            with tempfile.TemporaryDirectory() as d:
                out_file = Path(d, "sub", "run.json")
                rc, out, _ = self.run_tool("run", "--cases", str(CASES), "--endpoint", stub.url, "--out", str(out_file))
                self.assertEqual(rc, 0, out)
                self.assertIn("4/4 passed", out)
                saved = json.loads(out_file.read_text(encoding="utf-8"))
                self.assertEqual(saved["hee_bench"], 1)
                self.assertEqual(saved["summary"]["passed"], 4)
        finally:
            stub.close()

    def test_run_failure_exits_critical(self):
        stub = Stub({**GOOD, "disk /data": "CRITICAL"})
        try:
            rc, out, err = self.run_tool("run", "--cases", str(CASES), "--endpoint", stub.url, "--only", "choice-check-state")
        finally:
            stub.close()
        self.assertEqual(rc, 2)
        self.assertIn("FAIL choice-check-state", out)
        self.assertIn("0/1 passed", out + err)

    def test_unreachable_endpoint_is_unknown(self):
        rc, _, err = self.run_tool("run", "--cases", str(CASES), "--endpoint", "http://127.0.0.1:9", "--timeout", "2")
        self.assertEqual(rc, 3, err)
        rc, _, err = self.run_tool("run", "--cases", str(CASES))
        self.assertEqual(rc, 3)
        self.assertIn("HEE_BENCH_ENDPOINT", err)

    def test_grade_and_report_offline(self):
        rc, out, _ = self.run_tool("grade", str(RUN))
        self.assertEqual(rc, 0, out)
        self.assertIn("4/4 passed", out)
        rc, out, _ = self.run_tool("report", str(RUN), str(RUN))
        self.assertEqual(rc, 0)
        self.assertIn("| predicate-conventional-subject |", out)
        self.assertIn("| **passed** | | | 4/4 | 4/4 |", out)
        with tempfile.TemporaryDirectory() as d:
            p = Path(d, "not-a-run.json")
            p.write_text("{}", encoding="utf-8")
            rc, _, err = self.run_tool("grade", str(p))
            self.assertEqual(rc, 3)
            self.assertIn("not a hee-bench run", err)


if __name__ == "__main__":
    unittest.main()
