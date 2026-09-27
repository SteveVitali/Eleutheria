#!/usr/bin/env python3
"""Stdlib regression tests for worktree isolation and strict ownership checks."""
import copy
import importlib.util
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
SPEC = importlib.util.spec_from_file_location("check_plan", HERE / "check_plan.py")
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


class PlanningTests(unittest.TestCase):
    def setUp(self):
        self.plan = json.loads((HERE.parent / "PLAN.json").read_text())
        self.prior = {"P31.19": 160, "P31.10": 151, "P31.11": 152, "P31.14": 155, "P31.15": 156}

    def test_current_structure(self):
        self.assertEqual(MOD.structural_errors(self.plan, self.prior), [])

    def test_forward_dependency_rejected(self):
        self.plan["tickets"][0]["depends"] = ["P32.2"]
        self.assertTrue(any("forward dependency" in e for e in MOD.structural_errors(self.plan, self.prior)))

    def test_duplicate_owner_rejected(self):
        self.plan["tickets"][1]["requirements"] += self.plan["tickets"][0]["requirements"]
        self.assertTrue(any("expected one owner" in e for e in MOD.structural_errors(self.plan, self.prior)))

    def test_missing_owner_and_tail_rejected(self):
        changed = copy.deepcopy(self.plan)
        changed["tickets"][0]["requirements"] = []
        changed["tickets"][-1]["kind"] = "ticket"
        errors = MOD.structural_errors(changed, self.prior)
        self.assertTrue(any("expected one owner" in e for e in errors))
        self.assertTrue(any("tail" in e for e in errors))

    def test_relocated_block_requires_consistent_bounds_and_filenames(self):
        self.plan["first_sequence"] = 211
        self.plan["last_sequence"] = 250
        for ticket in self.plan["tickets"]:
            ticket["sequence"] += 50
            ticket["filename"] = f'{ticket["sequence"]}_{ticket["id"]}__{ticket["slug"]}.md'
        self.assertEqual(MOD.structural_errors(self.plan, self.prior), [])
        self.plan["last_sequence"] = 200
        self.assertTrue(any("last_sequence" in e for e in MOD.structural_errors(self.plan, self.prior)))

    def test_sequence_collision_with_another_extension_rejected(self):
        self.prior["EXTRA.1"] = 161
        self.assertTrue(any("already occupied" in e for e in MOD.structural_errors(self.plan, self.prior)))

    def test_builder_uses_its_checkout_not_cwd(self):
        builder = ROOT / "docs/research/_meta/spec_src/BUILD.sh"
        # Guard before execution: never run a reintroduced absolute developer path.
        source = builder.read_text()
        self.assertNotIn("ROOT=/", source)
        self.assertNotIn("/Users/", source)
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "a", Path(tmp) / "b"
            src = a / "docs/research/_meta/spec_src"
            src.mkdir(parents=True)
            (b / "docs").mkdir(parents=True)
            sentinel = b / "docs/2_canonical_design_spec.md"
            sentinel.write_text("other checkout remains unchanged\n")
            shutil.copyfile(builder, src / "BUILD.sh")
            (src / "00_first.md").write_text("first\n")
            (src / "10_second.md").write_text("second\n")
            subprocess.run(["sh", str(src / "BUILD.sh")], cwd=b, check=True, capture_output=True)
            self.assertEqual((a / "docs/2_canonical_design_spec.md").read_text(), "first\n\nsecond\n\n")
            self.assertEqual(sentinel.read_text(), "other checkout remains unchanged\n")


if __name__ == "__main__":
    unittest.main()
