# SPDX-License-Identifier: Apache-2.0
"""P35.62 (R11-ACT-15) — the committed production-candidate staging packet.

The packet under ``docs/build/reports/p35.62-production-candidate/`` is the
prepared, never-executed form of the ``D-P32.23a-1`` return pass: the real
production release candidate over the hosted frozen snapshot, staged into
private namespaces (``staged/`` objects + IAM-only staging origins) — the
same shape ``write_candidate_return_pass`` emits in
``ops/src/ops/release_candidate.py``. These tests pin the committed
artifact's contract surface: the OM-20 authority line, the
``prepared_not_executed`` staging disposition, the per-precondition
verdicts, the verbatim re-run prompt, the G2 §4 step-3 command sequence,
the exactly-once staging rule, and the rule that no project id, bucket
URI, or secret is ever literal in the packet (HG-09).

Nothing here is a hosted leg — the file reads committed bytes only.
"""

from __future__ import annotations

import json
import re

from support import REPO_ROOT

PACKET_DIR = REPO_ROOT / "docs" / "build" / "reports" / "p35.62-production-candidate"
PACKET_JSON = PACKET_DIR / "CANDIDATE_PACKET.json"
PACKET_MD = PACKET_DIR / "CANDIDATE_PACKET.md"

RERUN_PROMPT = (
    "implement-spec "
    "spec=docs/tickets/339_P35.62__round10-production-candidate.md "
    "live_verification=true"
)

CLOSING_REDISPATCH = (
    "implement-spec "
    "spec=docs/tickets/188_P32.23a__post-evaluation-release-candidate.md "
    "live_verification=true"
)


def _packet() -> dict:
    return json.loads(PACKET_JSON.read_text(encoding="utf-8"))


def test_packet_exists_and_status() -> None:
    p = _packet()
    assert p["packet_version"] == "candidate-staging-return-pass/1"
    assert p["status"] == "prepared_not_executed"
    assert p["row"].startswith("339")
    assert PACKET_MD.exists()


def test_om20_authority_named_and_bounded() -> None:
    """The GATE-G4 listing is the authority half — named verbatim, expiry
    recorded, and the mutation set is exactly the staged-candidate writes."""
    om = _packet()["om20_authority"]
    assert om["row_named"] is True
    assert "P35.62" in om["listing"]
    assert "expiry" in om
    mutation = om["mutation_set_verbatim"]
    assert "staged/" in mutation
    assert "latest.json" in mutation  # quoted as the never-write
    never = " ".join(om["never"])
    for phrase in (
        "no publication",
        "latest.json",
        "publicly reachable",
        "if-generation-match=0",
        "no gate tick",
    ):
        assert phrase in never


def test_staging_leg_queued_exactly_once() -> None:
    leg = _packet()["staging_leg"]
    assert leg["disposition"] == "queued"
    assert "if-generation-match=0" in leg["exactly_once"]
    assert "no-op" in leg["exactly_once"]
    assert "ever overwritten" in leg["exactly_once"]


def test_precondition_verdicts_cover_the_contract() -> None:
    """Every precondition the ticket names gets an explicit verdict — the
    listing is the only met row, the rest are honestly unmet/noted."""
    verdicts = _packet()["precondition_verdicts"]
    text = "\n".join(v["precondition"] for v in verdicts)
    for phrase in (
        "OM-20",
        "REPAIRED_SNAPSHOT.json",
        "live:P34.46",
        "live:P35.53",
        "SIG_GCP_PROJECT",
        "AR-2",
        "AR-3",
    ):
        assert phrase in text
    by_pre = {v["precondition"]: v["verdict"] for v in verdicts}
    (listing_pre,) = [k for k in by_pre if "OM-20" in k]
    assert by_pre[listing_pre] == "met"
    # the input snapshot, upstream live rows, the staged home and the
    # runtime env are all unmet — nothing ran
    assert sum(1 for v in verdicts if v["verdict"].startswith("unmet")) >= 4
    assert all(v.get("evidence") for v in verdicts)


def test_rerun_prompt_verbatim() -> None:
    p = _packet()
    assert p["rerun_prompt"] == RERUN_PROMPT
    assert RERUN_PROMPT in PACKET_MD.read_text(encoding="utf-8")


def test_command_sequence_g2_step3() -> None:
    cmds = _packet()["commands"]
    joined = "\n".join(cmds)
    # the contract order: pre-state → build → stage → web build → verify →
    # post-state → closing re-dispatch
    idx_pre = joined.index("pre-state")
    idx_build = joined.index("sig-ops release-candidate")
    idx_stage = joined.index("sig-ops release stage")
    idx_web = joined.index("SIG_DATA_SOURCE=export")
    idx_post = joined.index("post-state")
    idx_close = joined.index("spec=docs/tickets/188_P32.23a__post-evaluation-release-candidate.md")
    assert idx_pre < idx_build < idx_stage < idx_web < idx_post < idx_close
    # the build command carries the contract's flag surface
    build_step = next(c for c in cmds if "sig-ops release-candidate" in c)
    for flag in (
        "--dsn",
        "--snapshot",
        "--plan",
        "--audit",
        "--apply-report",
        "--registry",
        "--out",
    ):
        assert flag in build_step
    assert "$SIG_HOSTED_DSN" in build_step
    # the stage is create-only staged-namespace writes — never a promote
    stage_step = next(c for c in cmds if "sig-ops release stage" in c)
    assert "--apply" in stage_step
    assert "staged/" in stage_step
    assert "promote" not in stage_step
    # the verification legs are IAM-only — never public
    verify_step = next(c for c in cmds if "DR-C4-01" in c)
    assert "refused" in verify_step


def test_pins_record_contract_surfaces() -> None:
    pins = _packet()["pins"]
    assert pins["snapshot_version"] == "sig.repaired-snapshot/1"
    assert "frozen_unpublished" in pins["freeze_state"]
    assert "provisional-ruleset/1" in pins["ruleset"]
    assert pins["candidate_version"] == "sig.release-candidate/1"
    assert pins["identity_version"] == "sig.candidate-identity/1"
    assert pins["manifest_version"] == "sig.candidate-manifest/1"
    assert "shadow" in pins["eval_policy"]
    assert "applied=[]" in pins["eval_policy"]
    assert pins["policy_version"] == "publication-eligibility/1"
    assert "staged/{r,v,s,releases}/<pub>/" in pins["staged_namespaces"]
    assert "superseded" in pins["superseded_candidate"]
    assert pins["closing_redispatch"] == CLOSING_REDISPATCH


def test_no_literals_or_secrets() -> None:
    """HG-09: the project id, real bucket URIs and any secret never sit
    literal in the packet — both files stay env-parameterised. The OM-20
    line quotes the ticket's own elided ``…-sig-release`` form only."""
    blob = PACKET_JSON.read_text(encoding="utf-8") + PACKET_MD.read_text(encoding="utf-8")
    for m in re.finditer(r"gs://\S*", blob):
        assert m.group(0) == "gs://…-sig-release", (
            "only the ticket's elided bucket form may appear — a real gs:// URI never commits"
        )
    assert not re.search(r"[a-z]+-[a-z]+-\d{6}", blob), (
        "a GCP-project-shaped literal is committed — the project id stays environment-derived"
    )
    for env in ("SIG_GCP_PROJECT", "SIG_HOSTED_DSN", "SIG_EXEC_IMAGE", "SIG_RELEASE_REGISTRY_URI"):
        assert env in blob, f"{env} must be named as the env surface"


def test_reservations_cover_the_never_list() -> None:
    res = "\n".join(_packet()["explicit_reservations"])
    for phrase in (
        "stays OPEN",
        "no publication",
        "activate()/rollback()",
        "environment-only",
        "AR-3",
        "AR-2",
        "never re-signed",
        "NEW candidate",
        "never commits",
        "SIG-CHART-034",
    ):
        assert phrase in res


def test_verification_checklist_covers_invariants() -> None:
    check = "\n".join(_packet()["verification_checklist"])
    for phrase in (
        "+0",
        "applied=[]",
        "pointer_unchanged: true",
        "published: false",
        "provisional/review-only",
        "web/leverage.json",
        "web/tiles/*-sites.pmtiles",
        "web/releases.json",
        "date later than the build clock",
        "unauthenticated probe",
    ):
        assert phrase in check


def test_deferral_dispositions_keep_rows_open() -> None:
    disp = {d["id"]: d for d in _packet()["deferral_dispositions"]}
    for owed in ("D-P32.23a-1", "D-R10-LIVE-1", "D-R10-PUBLISH-1", "D-P35.53-1"):
        assert disp[owed]["disposition"] == "open", owed


def test_true_date_pin() -> None:
    """The prepared stamp is a real build-clock date (2026-10-24 run), never
    a future-dated literal."""
    p = _packet()
    assert p["prepared_at"].startswith("2026-10-24T")
    assert p["prepared_at"].endswith("Z")
    assert re.fullmatch(r"[0-9a-f]{40}", p["prepared_at_commit"])
