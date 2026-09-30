#!/usr/bin/env python3
"""Stdlib tests for the A3 universe extractor: parsers, the exactly-once checker, and the
reconciliation of the repository universe against the frozen A1 baseline.

Not collected by `make check` (pytest `testpaths = ["tests"]`); run explicitly:
    uv run python -m pytest docs/build/planning/2026-09-30-next-phase/tools/test_extract_universe.py
"""

import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("extract_universe", HERE / "extract_universe.py")
MOD = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MOD  # dataclasses resolve annotations via sys.modules
SPEC.loader.exec_module(MOD)


class ParserTests(unittest.TestCase):
    def test_split_row_keeps_escaped_pipes_literal(self):
        cells = MOD.split_row(r"| RISK-X-1 | a \| b | c |")
        self.assertEqual(cells, ["RISK-X-1", "a | b", "c"])

    def test_row_layout_names_legacy_and_overflow_rows(self):
        seven = "| D-A.1-1 | P | item | why | by | verify | OPEN |"
        self.assertEqual(MOD.row_layout(seven, MOD.split_row(seven)), "legacy-7-col")
        eight = "| D-A.1-1 | P | item | why | by | verify | proxy | OPEN |"
        self.assertEqual(MOD.row_layout(eight, MOD.split_row(eight)), "8-col")
        code = "| D-A.1-1 | P | item | why | by | `t[a|b|c]` | OPEN |"
        self.assertEqual(
            MOD.row_layout(code, MOD.split_row(code)),
            "legacy-7-col (+2 literal pipe(s) inside code spans)",
        )
        # Known limit (README): one code-span pipe in a 7-col row reads as 8 cells; the status
        # (last cell) and item (third cell) are still right unless the pipe sits in the item.
        one = "| D-A.1-1 | P | item | why | by | `t[a|b]` | OPEN |"
        self.assertEqual(MOD.row_layout(one, MOD.split_row(one)), "8-col")
        self.assertEqual(MOD.split_row(one)[2], "item")
        bare = "| D-A.1-1 | P | item | why | a|b | verify | proxy | OPEN |"
        self.assertTrue(MOD.row_layout(bare, MOD.split_row(bare)).startswith("overflow-9-cells"))

    def test_deferral_shorthand_expands(self):
        got = MOD.expand_d("flip D-P30.3-1/-2/-3 + D-P21.4-1/2 and D-R6.1-EVAL/D-P32.23a-1.")
        self.assertEqual(
            got,
            {
                "D-P30.3-1",
                "D-P30.3-2",
                "D-P30.3-3",
                "D-P21.4-1",
                "D-P21.4-2",
                "D-R6.1-EVAL",
                "D-P32.23a-1",
            },
        )
        self.assertEqual(MOD.expand_d("LD-F01 and D-rows"), set())

    def test_requirement_shorthand_and_ranges_expand(self):
        self.assertEqual(MOD.expand_sig("SIG-IDENT-020/025"), {"SIG-IDENT-020", "SIG-IDENT-025"})
        self.assertEqual(MOD.expand_sig("SIG-TASK-016a/b"), {"SIG-TASK-016a", "SIG-TASK-016b"})
        self.assertEqual(
            MOD.expand_sig("SIG-DOS-002…005"),
            {"SIG-DOS-002", "SIG-DOS-003", "SIG-DOS-004", "SIG-DOS-005"},
        )

    def test_blocker_mapping_from_f3_domains(self):
        cases = {
            "human (credentials)": "operator",
            "human (rights)": "rights",
            "human (rights) → hosted": "rights",
            "external + rights": "external",
            "hosted (date-bound)": "scheduled",
            "hosted": "live-execution",
            "decision (maintainer)": "engineering",
            "human → engineering": "human",
            "public": "operator",
        }
        for domain, expected in cases.items():
            self.assertEqual(MOD.blocker_from_domain(domain), expected, domain)

    def test_return_pass_key_split_respects_parentheses(self):
        body = "P31.1(**DONE — a, b (c, d)**), P21.3, P23.6(Go-public)"
        self.assertEqual(
            MOD.split_top_level(body),
            ["P31.1(**DONE — a, b (c, d)**)", "P21.3", "P23.6(Go-public)"],
        )

    def test_natural_sort(self):
        refs = ["D-P21.10-1", "D-P21.9-1", "D-P21.1-2", "D-P21.1-1"]
        self.assertEqual(
            sorted(refs, key=MOD.natural_key), ["D-P21.1-1", "D-P21.1-2", "D-P21.9-1", "D-P21.10-1"]
        )


class UniverseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.items, cls.infos = MOD.build(MOD.ROOT)
        cls.rows = MOD.to_rows(cls.items)
        cls.baseline = json.loads(MOD.BASELINE.read_text())

    def errors(self, rows):
        return MOD.check_rows(rows, self.items, self.infos, MOD.ROOT)

    def test_repository_universe_is_clean(self):
        self.assertEqual(self.errors(self.rows), [])
        _, recon_errors = MOD.reconciliation(self.rows, self.infos, self.baseline)
        self.assertEqual(recon_errors, [])

    def test_committed_csv_is_current_and_deterministic(self):
        again = MOD.render(MOD.to_rows(MOD.build(MOD.ROOT)[0]))
        self.assertEqual(again, MOD.render(self.rows))
        self.assertEqual(MOD.OUT.read_text(encoding="utf-8"), again)

    def test_counts_reconcile_to_the_a1_baseline(self):
        b = self.baseline
        kinds = {k: [r for r in self.rows if r["source_kind"] == k] for k in MOD.KIND_ORDER}
        self.assertEqual(len(kinds["deferral"]), b["mem.deferrals.rows"])
        owed = [r for r in kinds["deferral"] if r["effective_status"] in MOD.OWED]
        self.assertEqual(len(owed), b["mem.current.owed"])
        status = [r["source_status"] for r in kinds["requirement"]]
        not_met = sum(status.count(v) for v in ("PARTIAL", "MISSING", "AT-RISK-INTEGRATION"))
        self.assertEqual(not_met, b["mem.coverage.not_met"])
        self.assertEqual(
            status.count("MET-DIFFERENTLY"), b["mem.coverage.verdicts"]["MET-DIFFERENTLY"]
        )
        self.assertEqual(status.count("N/A-RATIONALE"), b["mem.coverage.verdicts"]["N/A-RATIONALE"])
        reduced = {
            r["source_ref"]
            for r in kinds["requirement"]
            if r["source_status"] == "MET(reduced-scope?)"
        }
        self.assertEqual(reduced, set(MOD.REDUCED_SCOPE_MET))
        bl = b["mem.backlog.status"]
        self.assertEqual(len(kinds["backlog"]), bl["open"] + bl["accepted"])
        self.assertEqual(len(kinds["adr_trigger"]), b["mem.adr.files"])
        self.assertEqual({r["source_ref"] for r in kinds["readout"]}, {"HUMAN-H4", "HUMAN-H5"})
        self.assertEqual(
            {r["source_ref"] for r in kinds["manifest_row"]},
            {f"MANIFEST-{n}" for n in (158, 159, 184, 185, 186, 187)},
        )
        self.assertTrue(all(r["links"] for r in kinds["risk"]), "every risk row links its BL home")

    def test_duplicate_row_is_rejected(self):
        rows = self.rows + [dict(self.rows[0])]
        self.assertTrue(any("appears 2 times" in e for e in self.errors(rows)))

    def test_missing_source_item_is_rejected(self):
        rows = [r for r in self.rows if r["source_ref"] != "D-P31.4-1"]
        self.assertTrue(any("D-P31.4-1: source item missing" in e for e in self.errors(rows)))

    def test_asymmetric_or_dangling_link_is_rejected(self):
        rows = copy.deepcopy(self.rows)
        target = next(r for r in rows if r["source_ref"] == "D-P31.4-1")
        target["links"] += " BL-999"
        errs = self.errors(rows)
        self.assertTrue(any("BL-999 does not resolve" in e for e in errs))
        rows = copy.deepcopy(self.rows)
        other = next(r for r in rows if r["source_ref"] == "RETURN-PASS:P31.4")
        other["links"] = ""
        self.assertTrue(any("is not symmetric" in e for e in self.errors(rows)))

    def test_dispositions_stay_empty_until_s1(self):
        rows = copy.deepcopy(self.rows)
        rows[0]["disposition"] = "ticket(201)"
        self.assertTrue(any("disposition must stay empty" in e for e in self.errors(rows)))

    def test_owed_set_must_match_operational_readiness_f3(self):
        rows = copy.deepcopy(self.rows)
        row = next(r for r in rows if r["source_ref"] == "D-P31.4-1")
        row["effective_status"] = "DONE"
        self.assertTrue(any("§(f3)" in e for e in self.errors(rows)))

    def test_unexplained_count_difference_is_rejected(self):
        baseline = dict(self.baseline, **{"mem.deferrals.rows": 98})
        _, errs = MOD.reconciliation(self.rows, self.infos, baseline)
        self.assertTrue(any("deferral: expected 98" in e for e in errs))


if __name__ == "__main__":
    unittest.main()
