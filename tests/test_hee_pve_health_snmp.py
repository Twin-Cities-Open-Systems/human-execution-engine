#!/usr/bin/env python3
"""hee-pve-health snmp: the fleetTable join and its OID encoding, with no node.

Nothing here talks to pve. The join is a pure function over three declared
sources and one measured dict, which is the whole reason it is shaped that way.
"""
import importlib.machinery
import importlib.util
import os
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

ENTRY = ".1.3.6.1.4.1.66550.1.1.1"


def _m(vmid, name, status="running", template=False, address=""):
    return {name: {"vmid": vmid, "name": name, "status": status,
                   "template": template, "address": address}}


class TestOidSortkey(unittest.TestCase):
    def test_numeric_order_not_string_order(self):
        """The reason this function exists.

        Plain string compare puts ".10" before ".9", so a GETNEXT built on it
        walks the table in the wrong order and can revisit a row forever.
        """
        self.assertLess(h.oid_sortkey(f"{ENTRY}.2.9"), h.oid_sortkey(f"{ENTRY}.2.10"))
        self.assertGreater(f"{ENTRY}.2.9", f"{ENTRY}.2.10")  # the naive compare, wrong

    def test_sorts_a_whole_table_correctly(self):
        oids = [f"{ENTRY}.{c}.{i}" for c in (2, 6) for i in (1, 2, 9, 10, 21)]
        got = sorted(oids, key=h.oid_sortkey)
        want = [f"{ENTRY}.{c}.{i}" for c in (2, 6) for i in (1, 2, 9, 10, 21)]
        self.assertEqual(got, want)

    def test_padding_survives_a_full_32_bit_arc(self):
        """10 digits covers 4294967295, so no arc can overflow the padding and
        re-order the file."""
        a = h.oid_sortkey(".1.4294967295")
        b = h.oid_sortkey(".1.4294967294")
        self.assertGreater(a, b)
        self.assertEqual(len(a.split(".")[1]), 10)

    def test_leading_dot_is_optional(self):
        self.assertEqual(h.oid_sortkey(".1.2.3"), h.oid_sortkey("1.2.3"))

    def test_shared_literal_with_the_agent_side(self):
        """THE CROSS-REPO CONTRACT.

        This key is written here and read by the awk in fleet-ops'
        pve/snmp/tcos-fleet-pass.sh. The two must agree byte-for-byte or
        GETNEXT compares against a padding scheme the file was not written
        with -- a walk that silently skips rows rather than an error.

        This exact literal is asserted in that repo's
        pve/snmp/test/test_tcos_fleet_pass.py as SORTKEY_1_3_6, so changing
        either padding scheme fails a test on one side or the other.
        """
        self.assertEqual(h.oid_sortkey(".1.3.6"),
                         "0000000001.0000000003.0000000006")


class TestAnchors(unittest.TestCase):
    """The registry pins its four anchors three different ways."""

    ANCHORS = {
        "lab-gateway": {"pinned": "role"},
        "resolver": {"pinned": "mac", "current_role_holder": "ns1"},
        "lab-dhcp": {"pinned": "address", "current_role_holder": "tcos-dhcp-bonnie"},
        "hypervisor-api": {"pinned": "mac", "current_role_holder": "pve"},
    }

    def test_key_equals_role(self):
        self.assertTrue(h.is_anchor("lab-dhcp", "tcos-dhcp-bonnie", self.ANCHORS))

    def test_holder_equals_role(self):
        """Key-only matching left the resolver false(2). Measured 2026-09-21."""
        self.assertTrue(h.is_anchor("ns1", "tcos-ns1-lois", self.ANCHORS))

    def test_holder_equals_declared_hostname(self):
        self.assertTrue(h.is_anchor("whatever", "tcos-dhcp-bonnie", self.ANCHORS))

    def test_ordinary_role_is_not_an_anchor(self):
        for role in ("haproxy", "view-dashboard", "store"):
            self.assertFalse(h.is_anchor(role, "tcos-x", self.ANCHORS), role)

    def test_empty_hostname_does_not_match_a_holder(self):
        self.assertFalse(h.is_anchor("store", "", self.ANCHORS))


class TestFleetRows(unittest.TestCase):
    def one(self, roles, measured, anchors=None, templates=None):
        return h.fleet_rows(roles, anchors or {}, templates or {}, measured)[0]

    def test_declared_but_not_built_is_unknown_with_vmid_zero(self):
        """The MIB's load-bearing case: 'a role declared but not yet built
        appears with fleetState unknown(3)', and zero is not a legal Proxmox
        VMID so it can carry 'no container'."""
        r = self.one({"ghost": "tcos-ghost"}, {})
        self.assertEqual(r["vmid"], 0)
        self.assertEqual(r["state"], h.Status.UNKNOWN.value)
        self.assertEqual(r["address"], "")
        self.assertIsNone(r["matched_by"])

    def test_matched_on_declared_hostname_is_clean(self):
        r = self.one({"store": "tcos-store-bart"}, _m(124, "tcos-store-bart"))
        self.assertEqual((r["vmid"], r["state"], r["matched_by"]),
                         (124, h.Status.OK.value, "hostname"))

    def test_matched_on_role_name_reports_the_real_vmid(self):
        """Eight containers predate `hee name`. Joining on the declared
        hostname alone reported every one of them as vmid 0 / unknown(3) --
        a walk claiming eight running services did not exist."""
        r = self.one({"haproxy": "tcos-hap-chris"}, _m(103, "haproxy"))
        self.assertEqual(r["vmid"], 103)

    def test_matched_on_role_name_warns_about_the_drift(self):
        r = self.one({"haproxy": "tcos-hap-chris"}, _m(103, "haproxy"))
        self.assertEqual(r["state"], h.Status.WARNING.value)
        self.assertEqual(r["matched_by"], "role")

    def test_no_drift_warning_when_declared_name_equals_role(self):
        """soju declares hostname `soju`, so a role-name match is not drift."""
        r = self.one({"soju": "soju"}, _m(111, "soju"))
        self.assertEqual(r["state"], h.Status.OK.value)

    def test_stopped_container_warns(self):
        r = self.one({"store": "tcos-store-bart"},
                     _m(124, "tcos-store-bart", status="stopped"))
        self.assertEqual(r["state"], h.Status.WARNING.value)

    def test_declared_template_is_ok_not_stopped(self):
        r = self.one({"golden-tiny": "tcos-golden-tiny"},
                     _m(112, "tcos-golden-tiny", status="stopped", template=True),
                     templates={"tcos-golden-tiny": {"vmid": 112}})
        self.assertEqual(r["state"], h.Status.OK.value)

    def test_undeclared_template_warns(self):
        """Same rule `templates` and `warn` apply, so the three cannot
        disagree about one container."""
        r = self.one({"golden-tiny": "tcos-golden-tiny"},
                     _m(112, "tcos-golden-tiny", status="stopped", template=True),
                     templates={})
        self.assertEqual(r["state"], h.Status.WARNING.value)

    def test_rows_are_ordered_and_indexed_by_role(self):
        rows = h.fleet_rows({"zulu": "z", "alpha": "a", "mike": "m"}, {}, {}, {})
        self.assertEqual([r["role"] for r in rows], ["alpha", "mike", "zulu"])
        self.assertEqual([r["index"] for r in rows], [1, 2, 3])

    def test_address_is_carried_through(self):
        r = self.one({"ns1": "tcos-ns1-lois"}, _m(101, "ns1", address="10.0.0.194"))
        self.assertEqual(r["address"], "10.0.0.194")


class TestUndeclaredContainers(unittest.TestCase):
    def test_container_with_no_manifest_is_reported(self):
        """fleetTable is keyed on declared role, so these can have no row.
        Measured 2026-09-21: mx1 and tcos-gopher-gateway have no manifest."""
        measured = {}
        measured.update(_m(103, "haproxy"))
        measured.update(_m(108, "mx1"))
        got = h.undeclared_containers({"haproxy": "tcos-hap-chris"}, measured)
        self.assertEqual(got, ["mx1"])

    def test_role_matched_container_is_not_reported_as_undeclared(self):
        got = h.undeclared_containers({"haproxy": "tcos-hap-chris"}, _m(103, "haproxy"))
        self.assertEqual(got, [])

    def test_hostname_matched_container_is_not_reported(self):
        got = h.undeclared_containers({"store": "tcos-store-bart"},
                                      _m(124, "tcos-store-bart"))
        self.assertEqual(got, [])


class TestTableLines(unittest.TestCase):
    def rows(self):
        return h.fleet_rows({"store": "tcos-store-bart"},
                            {}, {"tcos-store-bart": {}},
                            _m(124, "tcos-store-bart", address="10.0.0.167"))

    def test_fleet_index_is_never_emitted(self):
        """fleetIndex is MAX-ACCESS not-accessible. An index column that
        answers a GET is a walk that returns the index twice."""
        for line in h.fleet_table_lines(self.rows()):
            self.assertNotIn(f"\t{ENTRY}.1.", line)

    def test_every_accessible_column_is_emitted_once(self):
        lines = h.fleet_table_lines(self.rows())
        cols = sorted(int(ln.split("\t")[1].split(".")[-2]) for ln in lines)
        self.assertEqual(cols, [2, 3, 4, 5, 6, 7])

    def test_output_is_sorted_by_oid(self):
        rows = h.fleet_rows({f"r{i:02d}": f"h{i:02d}" for i in range(1, 13)},
                            {}, {}, {})
        lines = h.fleet_table_lines(rows)
        self.assertEqual([ln.split("\t")[0] for ln in lines],
                         sorted(ln.split("\t")[0] for ln in lines))

    def test_line_shape_is_sortkey_oid_type_value(self):
        for line in h.fleet_table_lines(self.rows()):
            parts = line.split("\t")
            self.assertEqual(len(parts), 4)
            self.assertIn(parts[2], ("string", "integer"))

    def test_types_match_the_mib(self):
        want = {2: "string", 3: "string", 4: "integer",
                5: "string", 6: "integer", 7: "integer"}
        for line in h.fleet_table_lines(self.rows()):
            _k, oid, typ, _v = line.split("\t")
            self.assertEqual(typ, want[int(oid.split(".")[-2])], oid)

    def test_an_empty_string_value_still_produces_a_line(self):
        """An unbuilt role has empty hostname/address. Dropping the cell would
        make the walk skip columns rather than report them empty."""
        lines = h.fleet_table_lines(h.fleet_rows({"ghost": ""}, {}, {}, {}))
        self.assertEqual(len(lines), 6)


if __name__ == "__main__":
    unittest.main()
