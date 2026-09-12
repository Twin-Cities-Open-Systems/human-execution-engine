#!/usr/bin/env python3
"""hee-board outsiders: who counts as us, what is a finding, and how bad.
Fixture API rows are invented; no network, no gh."""
import importlib.machinery
import importlib.util
import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(ROOT, "tooling", "bin", "hee-board")


def _load():
    loader = importlib.machinery.SourceFileLoader("hee_board", TOOL)
    spec = importlib.util.spec_from_loader("hee_board", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


b = _load()
CUTOFF = datetime(2026, 9, 4, tzinfo=timezone.utc)
ROSTER = {"tiers": [
    {"name": "Executive", "people": [{"github": "oper-one", "status": "verified"}]},
    {"name": "Team", "people": [{"github": "agent-two", "status": "ratified"},
                                {"github": "gone-three", "status": "departed"},
                                {"github": None, "status": "proposed"}]},
]}


def row(number, login, created="2026-09-10T12:00:00Z", state="open", user_type="User", is_pr=False, assoc="NONE"):
    return {"number": number, "title": f"t{number}", "html_url": f"https://example.invalid/{number}",
            "state": state, "created_at": created, "author_association": assoc,
            "login": login, "user_type": user_type, "is_pr": is_pr}


class TestRoster(unittest.TestCase):
    def test_logins_and_statuses_from_every_tier_skipping_null(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            json.dump(ROSTER, fh)
        try:
            self.assertEqual(b.load_roster(fh.name),
                             {"oper-one": "verified", "agent-two": "ratified", "gone-three": "departed"})
        finally:
            os.unlink(fh.name)


class TestClassify(unittest.TestCase):
    roster = {"oper-one": "verified", "gone-three": "departed"}

    def test_kinds(self):
        allowed = set(b.EXPECTED_BOTS)
        self.assertEqual(b.classify("oper-one", "User", self.roster, allowed), ("us", False))
        self.assertEqual(b.classify("gone-three", "User", self.roster, allowed), ("roster-inactive", True))
        self.assertEqual(b.classify("dependabot[bot]", "Bot", self.roster, allowed), ("bot", False))
        self.assertEqual(b.classify("mystery[bot]", "Bot", self.roster, allowed), ("bot-unexpected", True))
        self.assertEqual(b.classify("stranger", "User", self.roster, allowed), ("outsider", True))

    def test_severity_private_outsider_is_critical(self):
        self.assertIs(b.severity("outsider", True), b.Status.CRITICAL)
        self.assertIs(b.severity("outsider", False), b.Status.WARNING)
        self.assertIs(b.severity("bot-unexpected", True), b.Status.WARNING)
        self.assertIs(b.severity("roster-inactive", True), b.Status.WARNING)


class TestSelect(unittest.TestCase):
    def test_open_any_age_recent_any_state_old_closed_dropped_deduped(self):
        items = [row(1, "x", created="2026-01-01T00:00:00Z", state="open"),
                 row(2, "x", created="2026-09-05T00:00:00Z", state="closed"),
                 row(3, "x", created="2026-08-01T00:00:00Z", state="closed"),
                 row(1, "x", created="2026-01-01T00:00:00Z", state="open")]
        self.assertEqual([i["number"] for i in b.select_items(items, CUTOFF)], [1, 2])


class TestReview(unittest.TestCase):
    roster = {"oper-one": "verified", "gone-three": "departed"}
    allowed = set(b.EXPECTED_BOTS)

    def run_review(self, repos, fetched):
        return b.review(repos, fetched, self.roster, self.allowed, CUTOFF)

    def test_all_ours_is_ok(self):
        worst, findings, unreadable, counts = self.run_review(
            [{"name": "pub", "private": False}],
            {"pub": ([row(1, "oper-one"), row(2, "dependabot[bot]", user_type="Bot", is_pr=True)], "")})
        self.assertIs(worst, b.Status.OK)
        self.assertEqual(findings, [])
        self.assertEqual(counts, {("pub", "us"): 1, ("pub", "bot"): 1})

    def test_outsider_on_public_warns_on_private_is_critical(self):
        repos = [{"name": "pub", "private": False}, {"name": "priv", "private": True}]
        worst, findings, _, _ = self.run_review(repos, {"pub": ([row(1, "stranger")], ""), "priv": ([], "")})
        self.assertIs(worst, b.Status.WARNING)
        worst, findings, _, _ = self.run_review(repos, {"pub": ([row(1, "stranger")], ""),
                                                        "priv": ([row(9, "stranger")], "")})
        self.assertIs(worst, b.Status.CRITICAL)
        self.assertEqual(sorted((f["repo"], f["severity"].name) for f in findings),
                         [("priv", "CRITICAL"), ("pub", "WARNING")])

    def test_unreadable_repo_is_unknown_never_ok_but_warning_outranks_it(self):
        repos = [{"name": "pub", "private": False}, {"name": "priv", "private": True}]
        worst, _, unreadable, _ = self.run_review(repos, {"pub": ([], ""), "priv": (None, "HTTP 403")})
        self.assertIs(worst, b.Status.UNKNOWN)
        self.assertEqual(unreadable, [("priv", "HTTP 403")])
        worst, _, _, _ = self.run_review(repos, {"pub": ([row(1, "gone-three")], ""), "priv": (None, "HTTP 403")})
        self.assertIs(worst, b.Status.WARNING)

    def test_markdown_names_severity_label_and_counts(self):
        repos = [{"name": "pub", "private": False}]
        worst, findings, unreadable, counts = self.run_review(
            repos, {"pub": ([row(4, "stranger", is_pr=True), row(5, "oper-one")], "")})
        md = b.outsiders_markdown(worst, findings, unreadable, counts, 7)
        self.assertIn("WARNING", md)
        self.assertIn("[PR #4](https://example.invalid/4)", md)
        self.assertIn("1 item(s) from roster accounts, 0 from expected bots", md)


class TestFetch(unittest.TestCase):
    def test_parses_jq_lines_from_both_queries_and_reports_failure(self):
        calls = []

        def fake_run(argv, capture_output, text):
            calls.append(argv[3])
            out = json.dumps(row(7, "stranger")) + "\n" if "state=open" in argv[3] else ""
            return SimpleNamespace(returncode=0, stdout=out, stderr="")
        items, err = b.fetch_repo_items("org", "repo", CUTOFF, run=fake_run)
        self.assertEqual([i["number"] for i in items], [7])
        self.assertEqual(err, "")
        self.assertIn("since=2026-09-04T00:00:00Z", calls[1])

        def failing(argv, capture_output, text):
            return SimpleNamespace(returncode=1, stdout="", stderr="HTTP 404: Not Found\nmore")
        self.assertEqual(b.fetch_repo_items("org", "repo", CUTOFF, run=failing), (None, "HTTP 404: Not Found"))


if __name__ == "__main__":
    unittest.main()
