#!/usr/bin/env python3
"""hee-pve-health templates: the registry reader and the comparison, with no
node and no network. Nothing here talks to pve.

The comparison is the whole point of the subcommand, so the cases that matter
most are the ones where it must REFUSE to say "clean": an unreadable registry,
and a registry that parses but declares nothing.
"""
import importlib.machinery
import importlib.util
import os
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(ROOT, "tooling", "bin", "hee-pve-health")


def _load():
    loader = importlib.machinery.SourceFileLoader("hee_pve_health", TOOL)
    spec = importlib.util.spec_from_loader("hee_pve_health", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


h = _load()

GOOD = """\
apiVersion: hee/v1
kind: Registry
spec:
  templates:
    tcos-golden-tiny:
      vmid: 112
      role: golden-base
"""


def _lxc(vmid, name, status="running", template=0):
    return {"vmid": vmid, "name": name, "status": status, "template": template}


def _write(text):
    fd, path = tempfile.mkstemp(suffix=".yaml")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


class TestLoad(unittest.TestCase):
    def tearDown(self):
        for p in getattr(self, "_paths", []):
            os.unlink(p)

    def _mk(self, text):
        p = _write(text)
        self._paths = getattr(self, "_paths", []) + [p]
        return p

    def test_good_registry_parses(self):
        declared, err = h._load_templates(self._mk(GOOD))
        self.assertIsNone(err)
        self.assertEqual(list(declared), ["tcos-golden-tiny"])
        self.assertEqual(declared["tcos-golden-tiny"]["vmid"], 112)

    def test_missing_file_is_an_error_not_an_empty_registry(self):
        declared, err = h._load_templates("/nonexistent/templates.yaml")
        self.assertIsNone(declared)
        self.assertIn("no template registry", err)

    def test_unparseable_file_is_an_error(self):
        declared, err = h._load_templates(self._mk("spec:\n  templates:\n   - [unclosed\n"))
        self.assertIsNone(declared)
        self.assertIn("did not parse", err)

    def test_parses_but_declares_nothing_is_an_error(self):
        """The fail-closed case, and the one that actually bites.

        A registry that parses cleanly and declares no templates must not read
        as "no templates are sanctioned, so everything on the node is cruft",
        and must not read as "nothing to check, all clear" either. Both are a
        control reporting on something it never looked at -- the shape of the
        namespace-audit failure, which said "OK across 17 repo(s)" every day
        while its token was empty.
        """
        for text in ("spec:\n  status: proposed\n", "spec:\n  templates:\n", "{}\n"):
            declared, err = h._load_templates(self._mk(text))
            self.assertIsNone(declared, text)
            self.assertIn("declares no", err, text)


class TestFindings(unittest.TestCase):
    def _by_status(self, findings):
        return {t: s for s, t in findings}

    def test_declared_and_present_is_ok(self):
        f = h._template_findings([_lxc(112, "tcos-golden-tiny", "stopped", 1)],
                                 {"tcos-golden-tiny": {"vmid": 112}})
        self.assertEqual([s for s, _ in f], [h.Status.OK])
        self.assertEqual(h._worst(f), h.Status.OK)

    def test_vmid_compared_as_string(self):
        """pvesh returns vmid as int over HTTPS and as str over SSH.

        An int-vs-int comparison reported a mismatch between 112 and "112"
        depending only on which path the tool took to reach the node.
        Measured 2026-09-21 against the live node.
        """
        for node_vmid in (112, "112"):
            for want in (112, "112"):
                f = h._template_findings([_lxc(node_vmid, "tcos-golden-tiny", "stopped", 1)],
                                         {"tcos-golden-tiny": {"vmid": want}})
                self.assertEqual([s for s, _ in f], [h.Status.OK],
                                 f"node={node_vmid!r} registry={want!r}")

    def test_real_vmid_mismatch_still_warns(self):
        f = h._template_findings([_lxc(112, "tcos-golden-tiny", "stopped", 1)],
                                 {"tcos-golden-tiny": {"vmid": 199}})
        self.assertEqual(h._worst(f), h.Status.WARNING)
        self.assertIn("registry declares vmid 199", f[0][1])
        self.assertIn("node says 112", f[0][1])

    def test_undeclared_template_warns(self):
        f = h._template_findings([_lxc(150, "tcos-rogue", "stopped", 1)], {})
        self.assertEqual(h._worst(f), h.Status.WARNING)
        self.assertIn("undeclared template", f[0][1])

    def test_declared_template_absent_from_node_warns(self):
        """The other direction. A registry read one way cannot tell a template
        that was never built from one that was deleted by accident."""
        f = h._template_findings([], {"tcos-ghost": {"vmid": 199}})
        self.assertEqual(h._worst(f), h.Status.WARNING)
        self.assertIn("not present on the node", f[0][1])

    def test_stopped_non_template_is_cruft(self):
        f = h._template_findings([_lxc(120, "tcos-test-tos-rocky", "stopped", 0)], {})
        self.assertEqual(h._worst(f), h.Status.WARNING)
        self.assertIn("cruft", f[0][1])

    def test_running_non_template_produces_no_finding(self):
        """Steady state is quiet. A running service is not news."""
        self.assertEqual(h._template_findings([_lxc(107, "view", "running", 0)], {}), [])

    def test_a_template_is_never_reported_as_cruft(self):
        """A template is stopped BY DEFINITION. Reporting it as a stopped
        container is the permanently-red line rule 16 names."""
        f = h._template_findings([_lxc(112, "tcos-golden-tiny", "stopped", 1)],
                                 {"tcos-golden-tiny": {"vmid": 112}})
        self.assertNotIn("cruft", " ".join(t for _, t in f))

    def test_worst_wins_across_findings(self):
        f = h._template_findings(
            [_lxc(112, "tcos-golden-tiny", "stopped", 1),
             _lxc(120, "tcos-test-tos-rocky", "stopped", 0),
             _lxc(107, "view", "running", 0)],
            {"tcos-golden-tiny": {"vmid": 112}})
        self.assertEqual(h._worst(f), h.Status.WARNING)
        self.assertEqual(len(f), 2)  # the running container contributes nothing

    def test_worst_of_nothing_is_ok(self):
        self.assertEqual(h._worst([]), h.Status.OK)


if __name__ == "__main__":
    unittest.main()
