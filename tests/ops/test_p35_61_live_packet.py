# SPDX-License-Identifier: Apache-2.0
"""P35.61 (R11-ACT-14) — the committed live-pass return packet.

The packet under ``docs/build/reports/p35.61-live-pass/`` is the
prepared, never-executed form of the owed hosted audit → plan →
operator-pause → bounded-apply → freeze pass (``prepared_not_executed``
— the same shape ``write_apply_return_pass`` emits and P32.6 recorded).
These tests pin the committed artifact's contract surface: leg
dispositions, the verbatim re-run prompt, the G2 §4 step-2 command
sequence, the byte-figure ceilings (AR-9), and the rule that no project
id, bucket URI, or secret is ever literal in the packet (HG-09).

Nothing here is a hosted leg — the file reads committed bytes only.
"""

from __future__ import annotations

import json
import re

from support import REPO_ROOT

PACKET_DIR = REPO_ROOT / "docs" / "build" / "reports" / "p35.61-live-pass"
PACKET_JSON = PACKET_DIR / "LIVE_PASS_PACKET.json"
PACKET_MD = PACKET_DIR / "LIVE_PASS_PACKET.md"

RERUN_PROMPT = (
    "implement-spec "
    "spec=docs/tickets/338_P35.61__round10-live-pass-audit-apply-freeze.md "
    "live_verification=true"
)

GB = 10**9
MIB = 2**20


def _packet() -> dict:
    return json.loads(PACKET_JSON.read_text(encoding="utf-8"))


def test_packet_exists_and_status() -> None:
    p = _packet()
    assert p["packet_version"] == "live-pass-return-pass/1"
    assert p["status"] == "prepared_not_executed"
    assert PACKET_MD.exists()


def test_rerun_prompt_verbatim() -> None:
    p = _packet()
    assert p["rerun_prompt"] == RERUN_PROMPT
    assert RERUN_PROMPT in PACKET_MD.read_text(encoding="utf-8")


def test_leg_dispositions() -> None:
    legs = _packet()["legs"]
    assert legs["L1"]["disposition"] == "queued"
    assert legs["L1"]["read_only"] is True
    assert legs["L2"]["disposition"] == "pause_reached"
    assert legs["L3"]["disposition"] == "queued"
    # The apply is never pre-authorised — the recorded authority is the
    # operator's verbatim in-ticket go plus a recorded --authority scope.
    auth = legs["L3"]["authority"]
    assert "verbatim in-ticket go" in auth
    assert "--authority" in auth
    assert "never" in auth


def test_command_sequence_g2_step2() -> None:
    cmds = _packet()["commands"]
    joined = "\n".join(cmds)
    # the seven-step sequence, in order
    idx_audit = joined.index("sig-ops evidence-audit")
    idx_plan = joined.index("sig-ops recovery-plan")
    idx_pause = joined.index("operator review")
    idx_apply = joined.index("sig-ops recovery-apply")
    idx_freeze = joined.index("sig-ops recovery-freeze")
    idx_close = joined.index("spec=docs/tickets/183_P32.22__bounded-recovery-and-activation.md")
    assert idx_audit < idx_plan < idx_pause < idx_apply < idx_freeze < idx_close
    # the apply command carries the bounded-apply contract flags
    apply_step = next(c for c in cmds if "sig-ops recovery-apply" in c)
    for flag in (
        "--apply",
        "--execution-id",
        "--authority",
        "--verify-rerun",
        "--rematerialize",
        "--max-actions",
    ):
        assert flag in apply_step
    # the audit writes nothing — read-only
    assert "--apply" not in next(c for c in cmds if "evidence-audit" in c)


def test_ceilings_byte_figures() -> None:
    ceilings = _packet()["ceilings"]
    assert ceilings["pilot"]["claims"] == 500
    assert ceilings["pilot"]["bytes"] == 50 * MIB
    assert ceilings["batch"]["assertions"] == 10_000
    assert ceilings["batch"]["distinct_bytes"] == 250 * MIB
    assert ceilings["batch"]["workers"] == 1
    head = ceilings["storage_headroom"]
    alloc = head["disk_allocated_bytes"]
    assert alloc == 15 * GB
    # fractions restated in bytes: warn 0.7, disposition 0.85, free floor 0.2
    assert head["warn_at_used_bytes"] == int(0.7 * alloc)
    assert head["disposition_at_used_bytes"] == int(0.85 * alloc)
    assert head["min_batch_free_bytes"] == int(0.2 * alloc)


def test_pins_record_contract_surfaces() -> None:
    pins = _packet()["pins"]
    assert pins["audit_version"] == "evidence-audit/1"
    assert pins["plan_version"] == "recovery-plan/1"
    assert pins["freeze_record"].endswith("frozen_unpublished")
    assert pins["policy_version"] == "publication-eligibility/1"
    assert pins["role"] == "sig_recovery"


def test_no_literals_or_secrets() -> None:
    """HG-09: the project id, bucket URIs and any secret never sit literal
    in the packet — both files stay env-parameterised."""
    blob = PACKET_JSON.read_text(encoding="utf-8") + PACKET_MD.read_text(encoding="utf-8")
    assert "gs://" not in blob
    assert not re.search(r"[a-z]+-[a-z]+-\d{6}", blob), (
        "a GCP-project-shaped literal is committed — the project id stays environment-derived"
    )
    for env in ("SIG_GCP_PROJECT", "SIG_HOSTED_DSN", "SIG_EXEC_IMAGE"):
        assert env in blob, f"{env} must be named as the env surface"


def test_reservations_cover_the_never_list() -> None:
    res = "\n".join(_packet()["explicit_reservations"])
    for phrase in (
        "frozen_unpublished",
        "never pre-authorised",
        "digest-for-digest",
        "no publication",
        "split flag stays with C13",
    ):
        assert phrase in res


def test_verification_checklist_covers_invariants() -> None:
    check = "\n".join(_packet()["verification_checklist"])
    for phrase in (
        "digest for digest",
        "exactly-once",
        "+0 re-run applies nothing",
        "no fetch path",
        "frozen_unpublished",
        "bytesUsed/bytesAllocated",
    ):
        assert phrase in check
