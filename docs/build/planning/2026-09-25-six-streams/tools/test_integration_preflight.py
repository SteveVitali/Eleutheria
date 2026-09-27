#!/usr/bin/env python3
"""Exercise boundary safety against disposable repositories, never the live checkout."""

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "preflight", Path(__file__).with_name("integration_preflight.py")
)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


def state(last="P31.12"):
    return {
        "projectStatus": "IN-PROGRESS",
        "nextTicket": MOD.NEXT[last],
        "lastCompleted": last,
        "blockedOn": "(nothing)",
        "pauseRequested": "false",
        "round": "9",
    }


class BoundaryTests(unittest.TestCase):
    def test_all_six_actual_boundaries(self):
        for last, nxt in MOD.NEXT.items():
            with self.subTest(last=last):
                values = state(last)
                if last == "P31.19":
                    values.update(projectStatus="DONE", nextTicket="(none — capstone complete)")
                proposed, errors = MOD.transition(values, last)
                self.assertEqual(errors, [])
                self.assertEqual(proposed["nextTicket"], nxt)
                self.assertEqual(proposed["round"], "10" if last == "P31.19" else "9")
                self.assertEqual(proposed["lastCompleted"], last)

    def test_historical_state_and_pr_number_not_parsed_as_control(self):
        parsed = MOD.parse_current(
            "## CURRENT STATE\n```\nnextTicket: P31.13 # row 154\n"
            "returnPass: PR #147 remains owed\n```\n## HISTORY\n```\nnextTicket: SETUP\n```\n"
        )
        self.assertEqual(parsed, {"nextTicket": "P31.13", "returnPass": "PR #147 remains owed"})

    def test_duplicate_control_key_rejected(self):
        with self.assertRaises(ValueError):
            MOD.parse_current("## CURRENT STATE\n```\nnextTicket: A\nnextTicket: B\n```\n")

    def test_stale_boundary_and_real_block_rejected(self):
        values = state()
        values.update(blockedOn="failed live closeout", nextTicket="P32.1")
        _, errors = MOD.transition(values, "P31.13")
        self.assertGreaterEqual(len(errors), 3)

    def test_changed_snapshot_cannot_pass_final_guard(self):
        self.assertTrue(MOD.compare_fingerprint({"head": "old"}, {"head": "new"}))
        self.assertEqual(MOD.compare_fingerprint({"head": "old"}, {"head": "old"}), [])

    def test_real_git_preflight_is_read_only_and_requires_pause(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)

            def git(*args):
                return subprocess.run(
                    ["git", "-C", tmp, *args], check=True, text=True, capture_output=True
                ).stdout.strip()

            git("init", "-b", "devin/p31-12")
            git("config", "user.name", "Preflight fixture")
            git("config", "user.email", "fixture@example.invalid")
            values = state()
            values.update(buildWorktree=tmp, chainTip="devin/p31-12")
            ledger = repo / MOD.CONTROL[0]
            ledger.parent.mkdir(parents=True)
            ledger.write_text(
                "## CURRENT STATE\n```\n"
                + "\n".join(f"{k}: {v}" for k, v in values.items())
                + "\n```\n"
            )
            (repo / MOD.CONTROL[1]).write_text("| 153 | P31.12 | ticket | branch | #1 |\n")
            (repo / MOD.CONTROL[2]).parent.mkdir(parents=True)
            (repo / MOD.CONTROL[2]).write_text(
                "\n".join(
                    f"| {153 + i} | `{last}__fixture.md` |" for i, last in enumerate(MOD.NEXT)
                )
            )
            (repo / MOD.CONTROL[3]).write_text("# Deferrals\n")
            (repo / "docs/build/runs").mkdir()
            (repo / "docs/build/runs/P31.12.md").write_text(
                "Fixture closeout — not real acceptance\n"
            )
            git("add", "docs")
            git("commit", "-m", "fixture boundary")
            base = git("rev-parse", "HEAD")
            git("switch", "-c", "codex/planning-fixture")
            (repo / "docs/plan.md").write_text("fixture foundation\n")
            git("add", "docs/plan.md")
            git("commit", "-m", "fixture foundation")
            foundation = git("rev-parse", "HEAD")
            (repo / "docs/runbook.md").write_text("fixture follow-up\n")
            (repo / MOD.CONTROL[3]).write_text("# Deferrals\nNew planned obligation\n")
            git("add", "docs/runbook.md", MOD.CONTROL[3])
            git("commit", "-m", "fixture follow-up")
            git("switch", "devin/p31-12")
            before = MOD.fingerprint(repo)
            report = MOD.inspect(repo, "codex/planning-fixture", "P31.12", True, base, foundation)
            self.assertTrue(report["ready_local"], json.dumps(report["errors"]))
            self.assertEqual(len(report["source"]["commits_in_order"]), 2)
            self.assertEqual(before, MOD.fingerprint(repo))
            waiting = MOD.inspect(repo, "codex/planning-fixture", "P31.12", False, base, foundation)
            self.assertFalse(waiting["ready_local"])
            (repo / "unfinished.txt").write_text("owned by other worker\n")
            dirty = MOD.inspect(repo, "codex/planning-fixture", "P31.12", True, base, foundation)
            self.assertTrue(any("dirty" in e for e in dirty["errors"]))
            self.assertTrue((repo / "unfinished.txt").exists())


if __name__ == "__main__":
    unittest.main()
