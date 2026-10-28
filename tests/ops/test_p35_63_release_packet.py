# SPDX-License-Identifier: Apache-2.0
"""P35.63 (R11-ACT-24) — the committed first-model-release publish packet.

The packet under ``docs/build/reports/p35.63-first-model-release/`` is the
prepared, never-executed form of the ``D-R10-PUBLISH-1`` release-exposure
return pass: L1 (dispatch) stages the cut over the hosted registry, runs
the full V1–V15 suite on the private staging origins, classifies the
candidate and emits the agent-drafted HG-11 readout; L2 (operator)
promotes after the verbatim signature and runs the reversed-and-receipted
rollback rehearsal. These tests pin the committed artifact's contract
surface: the never-authorised authority block, the two queued leg
dispositions, the per-precondition verdicts, the verbatim re-run prompt,
the G2 step-7 command order, the contract pins, and the rule that no
project id, bucket URI, or secret is ever literal in the packet (HG-09).

Nothing here is a hosted leg — the file reads committed bytes only.
"""

from __future__ import annotations

import json
import re

from support import REPO_ROOT

PACKET_DIR = REPO_ROOT / "docs" / "build" / "reports" / "p35.63-first-model-release"
PACKET_JSON = PACKET_DIR / "RELEASE_PACKET.json"
PACKET_MD = PACKET_DIR / "RELEASE_PACKET.md"

RERUN_PROMPT = (
    "implement-spec "
    "spec=docs/tickets/341_P35.63__first-model-release-to-production.md "
    "live_verification=true"
)

CLOSING_REDISPATCH = (
    "implement-spec "
    "spec=docs/tickets/191_P32.25__accepted-release-public-verification.md "
    "live_verification=true"
)


def _packet() -> dict:
    return json.loads(PACKET_JSON.read_text(encoding="utf-8"))


def test_packet_exists_and_status() -> None:
    p = _packet()
    assert p["packet_version"] == "first-model-release-return-pass/1"
    assert p["status"] == "prepared_not_executed"
    assert p["row"].startswith("341")
    assert PACKET_MD.exists()


def test_authority_never_preauthorised() -> None:
    """Publication is in the GATE-G4 never-listed set — the authority block
    quotes the never-list verbatim, names P35.63 inside it, and records the
    Class-S promotion as the operator's act."""
    auth = _packet()["authority"]
    assert "never" in auth["listing"].lower()
    assert "P35.63" in auth["listing"]
    assert "GATE-G4" in auth["listing"]
    rule = auth["rule"]
    assert "operator" in rule.lower()
    assert "never promote Class S" in rule
    assert "never sign" in rule
    assert "p-17b713" in rule
    sig = auth["signature_state"]
    assert "absent" in sig
    assert "D-P35.60-1" in sig
    assert "OPEN" in sig


def test_leg_dispositions_both_queued() -> None:
    """L1 is the queued dispatch leg; L2 is queued and blocked on the
    signature — an agent never promotes Class S."""
    legs = _packet()["legs"]
    l1 = legs["L1_dispatch"]
    assert l1["disposition"] == "queued"
    assert "V1-V15" in l1["scope"]
    assert "class_s" in l1["scope"]
    assert "readout" in l1["scope"]
    assert "if-generation-match=0" in l1["exactly_once"]
    l2 = legs["L2_operator"]
    assert "queued" in l2["disposition"]
    assert "signature" in l2["disposition"]
    assert "never promote Class S" in l2["note"]
    # the rehearsal records all three legs incl. the not-rehearsable one
    rehearsal = l2["rehearsal_shape"]
    assert "clear_latest_pointer" in rehearsal
    assert "record_withdrawal" in rehearsal
    assert "NOT rehearsable" in rehearsal
    assert "reversed and receipted" in rehearsal


def test_precondition_verdicts_cover_the_contract() -> None:
    """Every precondition the ticket names gets an explicit verdict — the
    signature, the staged candidate, the infra home, the cutover, the
    upstream chain, the P35.57 dep input, the env, AR-2 and the window."""
    verdicts = _packet()["precondition_verdicts"]
    text = "\n".join(v["precondition"] for v in verdicts)
    for phrase in (
        "HG-11",
        "live:P35.62",
        "live:P35.53",
        "live:P35.59",
        "live:P35.61",
        "live:P34.46",
        "live:P34.43",
        "P35.57",
        "SIG_GCP_PROJECT",
        "AR-2",
        "14:00-20:00Z",
    ):
        assert phrase in text
    assert sum(1 for v in verdicts if v["verdict"].startswith("unmet")) >= 6
    assert all(v.get("evidence") for v in verdicts)
    # the P35.57 dep is recorded as an unlanded precondition input — never
    # silently satisfied
    (p57,) = [v for v in verdicts if v["precondition"].startswith("P35.57")]
    assert "unmet" in p57["verdict"]
    assert "never silently" in p57["verdict"]
    assert "returnPass" in p57["evidence"]


def test_rerun_prompt_verbatim() -> None:
    p = _packet()
    assert p["rerun_prompt"] == RERUN_PROMPT
    assert RERUN_PROMPT in PACKET_MD.read_text(encoding="utf-8")
    assert "resumes at the promote leg" in p["rerun_note"]


def test_command_sequence_g2_step7() -> None:
    """L1 order: pre-state → release-publish staged → verify --mode S →
    classify → drafted readout → regenerated P32.25 packet. L2 order:
    signature → promote → post-promote checks → rehearsal → allow-list →
    ratchet → closing P32.25 re-dispatch."""
    p = _packet()
    l1 = "\n".join(p["l1_commands"])
    i_pre = l1.index("pre-state")
    i_cut = l1.index("sig-ops release-publish --candidate")
    i_ver = l1.index("release verify --mode S")
    i_cls = l1.index("release classify")
    i_ro = l1.index("sig.release-readout/1")
    i_pkt = l1.index("P32.25 packet regenerated")
    assert i_pre < i_cut < i_ver < i_cls < i_ro < i_pkt
    # V1-V15 named verbatim on the verify step
    verify_step = next(c for c in p["l1_commands"] if "release verify" in c)
    for check in ("V1", "V5", "V10", "V12", "V14", "V15"):
        assert check in verify_step
    assert "fail closed" in verify_step or "fail-closed" in verify_step
    readout_step = next(c for c in p["l1_commands"] if "sig.release-readout/1" in c)
    assert "single maintainer, no second reviewer" in readout_step
    assert "no human check performed" in readout_step
    assert "signature slot empty" in readout_step
    l2 = "\n".join(p["l2_commands"])
    i_sig = l2.index("verbatim signature")
    i_pro = l2.index("release promote")
    i_chk = l2.index("post-promote checks")
    i_reh = l2.index("rollback rehearsal")
    i_allow = l2.index("allow-list expansion")
    i_ratchet = l2.index("ratchet read")
    i_close = l2.index("spec=docs/tickets/191_P32.25__accepted-release-public-verification.md")
    assert i_sig < i_pro < i_chk < i_reh < i_allow < i_ratchet < i_close
    promote_step = next(c for c in p["l2_commands"] if "release promote" in c)
    assert "--approval" in promote_step
    assert "conf/<gen+1>" in promote_step
    assert "min-instances=1" in promote_step
    assert "post-signature only" in promote_step
    allow_step = next(c for c in p["l2_commands"] if "allow-list expansion" in c)
    assert "archive + pinned citations + release search first" in allow_step
    assert "stay dark" in allow_step


def test_pins_record_contract_surfaces() -> None:
    pins = _packet()["pins"]
    assert pins["readout_version"].startswith("sig.release-readout/1")
    assert "signature slot empty" in pins["readout_version"]
    assert pins["approval_version"].startswith("sig.promotion-approval/1")
    assert pins["pointer_version"].startswith("sig.latest-pointer/2")
    assert pins["verify_version"].startswith("sig.release-verify/1")
    assert "V12 never waivable" in pins["verify_version"]
    assert pins["publish_class"].startswith("class_s")
    assert pins["expected_class"] == "class_s"
    assert "archive + pinned citations + release search first" in pins["allow_list"]
    assert "superseded" in pins["superseded_candidate"]
    assert "p-17b713" in pins["superseded_candidate"]
    assert "P37.67" in pins["ratchet"]
    assert "C13" in pins["split_decision"]
    assert "≤ 24 h" in pins["merge_sentence"]
    assert pins["closing_redispatch"] == CLOSING_REDISPATCH


def test_no_literals_or_secrets() -> None:
    """HG-09: the project id, real bucket URIs and any secret never sit
    literal in the packet — both files stay env-parameterised."""
    blob = PACKET_JSON.read_text(encoding="utf-8") + PACKET_MD.read_text(encoding="utf-8")
    assert "gs://" not in blob, "no gs:// URI — the bucket stays env-derived"
    assert not re.search(r"[a-z]+-[a-z]+-\d{6}", blob), (
        "a GCP-project-shaped literal is committed — the project id stays environment-derived"
    )
    for env in ("SIG_GCP_PROJECT", "SIG_EXEC_IMAGE", "SIG_HOSTED_DSN", "SIG_RELEASE_REGISTRY"):
        assert env in blob, f"{env} must be named as the env surface"


def test_reservations_cover_the_never_list() -> None:
    res = "\n".join(_packet()["explicit_reservations"])
    for phrase in (
        "NEVER pre-authorised",
        "never promote Class S",
        "never sign",
        "RETURN PASS",
        "never transfers",
        "stays OPEN",
        "environment-only",
        "AR-3",
        "P35.57",
        "stay dark",
        "never deleted",
        "C13",
        "never commits",
        "queued leg ran",
    ):
        assert phrase in res


def test_verification_checklist_covers_invariants() -> None:
    check = "\n".join(_packet()["verification_checklist"])
    for phrase in (
        "V1-V15",
        "fail-closed",
        "single maintainer, no second reviewer",
        "no human check performed",
        "signature empty",
        "date -u",
        "digest match on every manifest route",
        "/v1/releases/",
        "+0",
        "reversed and receipted",
        "not-rehearsable",
        "ratchet",
        "release-exposure half",
        "receiver half stays owed",
    ):
        assert phrase in check


def test_deferral_dispositions_keep_rows_open() -> None:
    disp = {d["id"]: d for d in _packet()["deferral_dispositions"]}
    for owed in (
        "D-R10-PUBLISH-1",
        "D-P32.23a-1",
        "D-R10-LIVE-1",
        "D-P35.53-1",
        "D-P35.60-1",
        "D-P35.57-1",
        "D-P35.56-1",
    ):
        assert disp[owed]["disposition"] == "open", owed
    # the publish deferral records the split closure rule — release-exposure
    # half only, the receiver half never silently marked
    note = disp["D-R10-PUBLISH-1"]["note"]
    assert "release-exposure half" in note
    assert "receiver half stays owed" in note
    assert "no lead-token change" in note


def test_machinery_checks_recorded() -> None:
    mc = _packet()["machinery_checks"]
    assert "classify" in mc["verbs_present"]
    assert "promote" in mc["verbs_present"]
    proof = mc["readout_path_proof"]
    assert "class_s" in proof
    assert "signature" in proof and "null" in proof
    assert "single maintainer, no second reviewer" in proof
    assert "no human check performed" in proof
    assert "release.readout-pending" in proof


def test_true_date_pin() -> None:
    """The prepared stamp is a real build-clock date (2026-10-25 run), never
    a future-dated literal."""
    p = _packet()
    assert p["prepared_at"].startswith("2026-10-25T")
    assert p["prepared_at"].endswith("Z")
    assert re.fullmatch(r"[0-9a-f]{40}", p["prepared_at_commit"])
