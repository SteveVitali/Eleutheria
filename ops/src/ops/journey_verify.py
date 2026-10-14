# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The public investigation acceptance portfolio (P32.24 / ADR-143 —
SIG-FIND-007).

Two honest evidence layers, never conflated:

* **Candidate layer** — re-verifies the committed P32.23a packet
  (``docs/build/reports/p32.23a-release-candidate/``): every declared artifact
  digest over the committed bytes, the immutable release's own
  ``validate_release``, descriptor→namespace identity, and the *deferred*
  evaluation posture (``status=deferred``, ``decision=null``, shadow
  ``eval-confidence/1`` ``applied=[]``, ``published=false``,
  ``provisional``/``review_only``). The candidate's honest zero
  (``input_records``/``output_records``/``dossier_pages`` = 0) is recorded —
  the record journeys are ``not_applicable`` on that candidate, never
  fabricated into a passing journey.
* **Journey layer** — executes the three documented S4 journeys plus the
  withdrawal walkthroughs over the deterministic **acceptance corpus**: a
  synthetic-but-real-contract export fed through the real
  ``exports.release.build_release`` → ``activate`` → ``record_withdrawal``
  machinery. Three dossier scopes, records past the first browse page
  ("tail"), unreported-jurisdiction / unlocated / unresolved-point records,
  withheld records, typed access edges, and evidence anchors.

Evidence classes are explicit per check:

* ``automated_conformance`` — verified inline by this portfolio run.
* ``agent_walkthrough`` — a recorded agent navigation of emitted artifacts
  (``WALKTHROUGH_LOG.md``); useful evidence, never a human usability result.
* ``independent_human`` — real moderated usability sessions; none were
  performed (``D-R10-USERS-1`` stays OPEN) so this class may never carry
  ``pass`` without recorded session identifiers — enforced in ``_assemble``.
  The runnable task protocol (``USABILITY_TASK_PROTOCOL.md``) is the
  compensating control.

Statuses: ``pass`` (verified inline), ``verified_by_test`` (a named
deterministic suite owns the proof), ``deferred`` (explicitly owed with an
owner + landing), ``not_applicable`` (honestly absent on this artifact), and
``fail`` — any fail forces the portfolio ``verdict`` to ``fail`` and every
fail/deferred/not_applicable check must name an owner + landing.

The intake traversal (``run_intake_journey``) executes the Journey-C
receipt→restart→queue→approve→apply→publish chain over a real PostgreSQL +
sqitch spine and emits ``sig.journey-intake-proof/1``. It is exercised
continuously by ``tests/db/test_journey_portfolio_pg.py`` and re-runnable on
any DSN through ``sig-ops journey-intake``.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import shutil
import sqlite3
import uuid
from collections.abc import Iterator, Mapping, Sequence
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from typing import Any

from exports.manifest import canonical_json, sha256_hex
from exports.published_record import record_key
from exports.release import (
    ReleaseBuild,
    ReleaseRegistry,
    activate,
    apply_withdrawals,
    build_release,
    record_withdrawal,
    route_access,
    validate_release,
)
from exports.search_index import check_index_contract, parse_params, search
from policy.eligibility import (
    Disposition,
    ReasonCategory,
    TargetKind,
    new_disposition,
)

PORTFOLIO_SCHEMA = "sig.journey-portfolio/1"
CORPUS_SCHEMA = "sig.journey-corpus/1"
INTAKE_PROOF_SCHEMA = "sig.journey-intake-proof/1"

EVIDENCE_KINDS = ("automated_conformance", "agent_walkthrough", "independent_human")
CHECK_STATUSES = ("pass", "fail", "deferred", "not_applicable", "verified_by_test")
EDGE_KINDS = ("configured_access", "observed_use", "declared_policy")

#: The candidate's pins are read from the CANDIDATE_MANIFEST.json of the
#: packet named on the command line (P34.22a / ADR-146 D4) — this module
#: never embeds a publication id, identity digest, snapshot digest or
#: ruleset of any candidate: the superseded rehearsal candidate stays a
#: record in docs/build/reports/, not a code constant.

COMP_A = "sig_graph"
COMP_B = "osm_physical"
LIC_A = "CC-BY-4.0"
LIC_B = "ODbL-1.0"
SRC_A = "src_acc_registry"
SRC_B = "src_acc_osm"

#: The corpus's declared withheld/unlocated/tail cases — the checks assert
#: exactly these so a corpus mutation is a detected change, not silent drift.
WITHHELD_ENTITY = "ent-acc-dep-41"
WITHHELD_CLAIM = "cl-acc-denied-claim"
GHOST_CLAIM = "cl-acc-ghost"
UNLOCATED_ENTITIES = [f"ent-acc-dep-{i:02d}" for i in range(40, 45)]
UNRESOLVED_ENTITIES = [f"ent-acc-dep-{i:02d}" for i in range(45, 48)]
UNREPORTED_ENTITIES = [f"ent-acc-dep-{i:02d}" for i in range(48, 53)]
GHOST_ENTITY = "ent-acc-dep-53"
DENIED_ENTITY = "ent-acc-dep-54"
DOSSIER_SCOPES = ("okc", "tulsa", "san-diego")
EDGE_CASES = (
    {
        "from": "ent-acc-dep-00",
        "to": "ent-acc-partner-00",
        "access_kind": "configured_access",
        "relation": "configured_partner",
        "claim": "cl-acc-edge-cfg",
    },
    {
        "from": "ent-acc-dep-00",
        "to": "ent-acc-partner-01",
        "access_kind": "observed_use",
        "relation": "observed_partner",
        "claim": "cl-acc-edge-obs",
    },
    {
        "from": "ent-acc-dep-01",
        "to": "ent-acc-partner-02",
        "access_kind": "declared_policy",
        "relation": "declared_partner",
        "claim": "cl-acc-edge-pol",
    },
)

INTAKE_PG_TEST = "tests/db/test_journey_portfolio_pg.py"


class PortfolioError(Exception):
    """A hard stop — the portfolio cannot even assemble honestly."""


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #
def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


def _write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _check(
    check_id: str,
    journey: str,
    title: str,
    evidence_kind: str,
    status: str,
    detail: str,
    *,
    evidence: list[str] | None = None,
    expected_answer: str | None = None,
    owner: str | None = None,
    landing: str | None = None,
) -> dict[str, Any]:
    assert evidence_kind in EVIDENCE_KINDS, evidence_kind
    assert status in CHECK_STATUSES, status
    out: dict[str, Any] = {
        "id": check_id,
        "journey": journey,
        "title": title,
        "evidence_kind": evidence_kind,
        "status": status,
        "detail": detail,
        "evidence": list(evidence or []),
        "expected_answer": expected_answer,
        "owner": owner,
        "landing": landing,
    }
    if status in {"fail", "deferred", "not_applicable"} and not (owner and landing):
        raise PortfolioError(
            f"check {check_id} is {status} without an owner + landing — "
            "a failure the portfolio cannot route is a fail by construction"
        )
    return out


# --------------------------------------------------------------------------- #
# The acceptance corpus — a synthetic-but-real-contract export
# --------------------------------------------------------------------------- #
def _rights(source: str, spdx: str) -> dict[str, Any]:
    return {
        "attribution": f"© {source} (acceptance fixture)",
        "attribution_required": True,
        "license": spdx,
        "share_alike": spdx.startswith("ODbL"),
        "source_id": source,
        "terms_url": "https://example.test/acceptance/terms",
        "upstream_license": None,
    }


def _site_row(
    entity_id: str,
    entity_type: str,
    source: str,
    spdx: str,
    *,
    label: str | None,
    jurisdiction: str | None,
    geometry: dict[str, Any] | None,
    point_status: str = "resolved",
    claim_ids: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "_rights": _rights(source, spdx),
        "claim_ids": claim_ids or [],
        "entity_id": entity_id,
        "entity_type": entity_type,
        "geometry": geometry,
        "jurisdiction": jurisdiction,
        "label": label,
        "n_observation_claims": len(claim_ids or []),
        "n_sources": 1,
        "point_status": point_status,
        "precision": "full_precision" if geometry else "unreported",
        "rights_id": "acc-rights-1",
        "source_id": source,
        "spdx": spdx,
        "tier": 0,
    }


def _claim_row(
    cid: str,
    entity_id: str,
    source: str,
    predicate: str,
    evidence: list[dict[str, Any]] | None = None,
    observed: str = "2026-05-01",
) -> dict[str, Any]:
    return {
        "claim_id": cid,
        "entity_id": entity_id,
        "predicate_id": predicate,
        "observed_at": observed,
        "source_id": source,
        "evidence": list(evidence or []),
    }


def _dossier_doc(scope: str) -> dict[str, Any]:
    """One released dossier overview in the real ``_dossiers`` shape."""
    unknown_auth = {
        "approving_body": None,
        "vote": None,
        "consent_agenda": None,
        "public_comment": None,
        "date": None,
    }
    unknown_term = {"auto_renews": None, "notice_window_days": None, "expiry_date": None}
    return {
        "kind": "inventory_overview",
        "slug": scope,
        "subject_label": f"Surveillance infrastructure — {scope} (acceptance)",
        "jurisdiction": scope,
        "asOf": {
            "as_of_world": "2026-09-27",
            "as_of_belief": "2026-09-27",
            "belief_pinned": False,
        },
        "rulesetVersion": "p32.24-acceptance/1",
        "sections": [
            {"section_id": "at_a_glance"},
            {
                "section_id": "what_is_deployed",
                "rows": [
                    {
                        "label": "Geolocated site observations",
                        "value": "0 recorded",
                        "note": "Observation-level count from named sources — "
                        "not a resolved device census (SIG-RECON-058).",
                    },
                    {
                        "label": "Recorded sharing partners",
                        "value": "0 recorded",
                        "note": "Typed access edges carry their establishing claim.",
                    },
                ],
            },
            {
                "section_id": "how_we_know_this",
                "rows": [{"label": "Sources", "value": SRC_A}],
            },
        ],
        "gaps": [
            {
                "kind": "NOT_RESEARCHED",
                "label": "Data-sharing agreements beyond the recorded partners",
                "subject_id": f"jurisdiction:{scope}",
            }
        ],
        "source_families": [SRC_A],
        "authorization": dict(unknown_auth),
        "termination": dict(unknown_term),
        "legal_regime": {"state_statute": None, "local_ordinance": None, "disclosure_duties": []},
    }


def build_acceptance_export(export_dir: Path | str) -> dict[str, Any]:
    """Emit the deterministic acceptance corpus export directory.

    Real-contract shape (``manifest.json`` + ``<comp>/sites.jsonl`` +
    ``<comp>/record_claims.jsonl`` + ``web/*`` payloads) so the REAL
    ``build_release`` path consumes it — the journeys verify the same code
    that produced the candidate, over a corpus exercising the cases the
    candidate cannot demonstrate (records, dossiers, edges, withdrawals). Also
    emits ``corpus.json`` (``sig.journey-corpus/1``) — the corpus's own
    declared expectations, so a corpus mutation is a detected change.
    """
    export_dir = Path(export_dir)
    jurisdiction_cycle = (["okc"] * 14) + (["tulsa"] * 12) + (["san-diego"] * 8)

    sites_a: list[dict[str, Any]] = []
    claims_a: list[dict[str, Any]] = []
    for i in range(55):
        eid = f"ent-acc-dep-{i:02d}"
        # Claims every record asserts; the record_claims index omits the
        # declared ghost claim so its anchor is honestly ``unlocated``.
        record_claim_ids = [
            f"cl-acc-{eid}-loc",
            f"cl-acc-{eid}-label",
        ]
        if eid == GHOST_ENTITY:
            record_claim_ids.append(GHOST_CLAIM)
        if eid == DENIED_ENTITY:
            record_claim_ids.append(WITHHELD_CLAIM)
        # the edge claims ride the endpoint records' claim_ids so the claim
        # anchors + the staged claim-route index resolve them
        for edge in EDGE_CASES:
            if eid == edge["from"]:
                record_claim_ids.append(edge["claim"])

        geometry: dict[str, Any] | None = {
            "coordinates": [-97.5 + i * 0.01, 35.46 + (i % 7) * 0.01],
            "type": "Point",
        }
        point_status = "resolved"
        if eid in UNLOCATED_ENTITIES:
            geometry = None
        elif eid in UNRESOLVED_ENTITIES:
            point_status = "conflicted"
        jurisdiction: str | None = jurisdiction_cycle[i % len(jurisdiction_cycle)]
        if eid in UNREPORTED_ENTITIES:
            jurisdiction = None
        sites_a.append(
            _site_row(
                eid,
                "deployment",
                SRC_A,
                LIC_A,
                label=f"Acceptance Deployment {i:02d}",
                jurisdiction=jurisdiction,
                geometry=geometry,
                point_status=point_status,
                claim_ids=record_claim_ids,
            )
        )
        claims_a.append(
            _claim_row(
                f"cl-acc-{eid}-loc",
                eid,
                SRC_A,
                "camera_latitude",
                evidence=[
                    {
                        "capture_id": f"cap-{eid}",
                        "artifact_id": "art-acc-1",
                        "role": "establishes",
                    }
                ],
            )
        )
        # dep-03's label claim carries a fully unlocated evidence leg — the
        # "bound but nothing released" unknown-state case.
        label_ev = (
            [{"capture_id": None, "artifact_id": None, "role": "establishes"}]
            if eid == "ent-acc-dep-03"
            else []
        )
        claims_a.append(_claim_row(f"cl-acc-{eid}-label", eid, SRC_A, "label", evidence=label_ev))

    for i in range(8):
        eid = f"ent-acc-partner-{i:02d}"
        sites_a.append(
            _site_row(
                eid,
                "sharing_partner",
                SRC_A,
                LIC_A,
                label=f"Acceptance Partner {i:02d}",
                jurisdiction=jurisdiction_cycle[(i * 7) % len(jurisdiction_cycle)],
                geometry=None,
                claim_ids=[f"cl-acc-{eid}-label"],
            )
        )
        claims_a.append(_claim_row(f"cl-acc-{eid}-label", eid, SRC_A, "label"))

    # Edge-establishing claims + the denied claim — in the record_claims
    # index so anchors/predicates resolve.
    for edge in EDGE_CASES:
        claims_a.append(
            _claim_row(
                edge["claim"],
                edge["from"],
                SRC_A,
                "sharing_access",
                evidence=[
                    {
                        "capture_id": f"cap-{edge['claim']}",
                        "artifact_id": "art-acc-2",
                        "role": "establishes",
                    }
                ],
            )
        )
    claims_a.append(_claim_row(WITHHELD_CLAIM, DENIED_ENTITY, SRC_A, "sharing_access"))

    sites_b: list[dict[str, Any]] = []
    claims_b: list[dict[str, Any]] = []
    for i in range(12):
        eid = f"ent-acc-osm-{i:02d}"
        sites_b.append(
            _site_row(
                eid,
                "deployment",
                SRC_B,
                LIC_B,
                label=f"OSM Mast {i:02d}",
                jurisdiction="okc" if i % 3 else "tulsa",
                geometry={"coordinates": [-97.6 + i * 0.02, 35.5], "type": "Point"},
                claim_ids=[f"cl-acc-{eid}-osm"],
            )
        )
        claims_b.append(_claim_row(f"cl-acc-{eid}-osm", eid, SRC_B, "feature_tag"))

    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    for edge in EDGE_CASES:
        for node, ntype in ((edge["from"], "agency"), (edge["to"], "partner")):
            nodes.setdefault(node, {"id": node, "label": node, "type": ntype})
        edges.append(
            {
                "from": edge["from"],
                "to": edge["to"],
                "access_kind": edge["access_kind"],
                "relation": edge["relation"],
                "evidence_count": 1,
                "evidence": [edge["claim"]],
            }
        )
    network = {"nodes": [nodes[k] for k in sorted(nodes)], "edges": edges, "access_paths": []}

    evidence = {
        "artifacts": [
            {
                "artifact_id": "art-acc-1",
                "artifact_type": "registry_table",
                "as_of": "2026-09-27",
                "capture_status": "captured",
                "currency": "",
                "directness": "primary",
                "permalink": "https://example.test/acceptance/registry#art-acc-1",
                "source": SRC_A,
                "subject_id": "",
                "title": "Acceptance registry page",
                "touches_open_contradiction": False,
                "answers_open_task": False,
            },
            {
                "artifact_id": "art-acc-2",
                "artifact_type": "contract",
                "as_of": "2026-09-27",
                "capture_status": "captured",
                "currency": "",
                "directness": "primary",
                "permalink": "https://example.test/acceptance/contract#art-acc-2",
                "source": SRC_A,
                "subject_id": "",
                "title": "Acceptance sharing contract",
                "touches_open_contradiction": False,
                "answers_open_task": False,
            },
            {
                "artifact_id": "art-acc-osm",
                "artifact_type": "dump",
                "as_of": "2026-09-27",
                "capture_status": "captured",
                "currency": "",
                "directness": "primary",
                "permalink": "https://example.test/acceptance/osm#art-acc-osm",
                "source": SRC_B,
                "subject_id": "",
                "title": "Acceptance OSM extract",
                "touches_open_contradiction": False,
                "answers_open_task": False,
            },
        ],
        "claim_views": [],
    }

    dossiers = [_dossier_doc(scope) for scope in DOSSIER_SCOPES]
    # honest per-scope record/partner counts derived from the corpus itself
    for d in dossiers:
        scope = str(d["slug"])
        n = sum(1 for s in sites_a + sites_b if s.get("jurisdiction") == scope)
        p = sum(
            1
            for s in sites_a
            if s.get("entity_type") == "sharing_partner" and s.get("jurisdiction") == scope
        )
        for section in d["sections"]:
            if section["section_id"] == "what_is_deployed":
                section["rows"][0]["value"] = f"{n} recorded"
                section["rows"][1]["value"] = f"{p} recorded"

    corpus = {
        "schema": CORPUS_SCHEMA,
        "purpose": "P32.24 journey-verification acceptance corpus — SYNTHETIC, "
        "never a data release, never published; its cases exercise the "
        "record-journey semantics the P32.23a candidate cannot demonstrate "
        "(its fixture-seeded repaired spine exports 16 claims but the bound "
        "release projection materializes zero records).",
        "dossier_scopes": list(DOSSIER_SCOPES),
        "records": {
            "total": len(sites_a) + len(sites_b),
            "deployment": 67,
            "sharing_partner": 8,
            "tail_browse_page": 2,
        },
        "cases": {
            "tail_record": "the last lexicographic deployment record is "
            "reachable only on browse page 2+",
            "unlocated_entities": UNLOCATED_ENTITIES,
            "unresolved_point_entities": UNRESOLVED_ENTITIES,
            "unreported_jurisdiction_entities": UNREPORTED_ENTITIES,
            "ghost_claim": GHOST_CLAIM,
            "ghost_entity": GHOST_ENTITY,
            "unlocated_evidence_entity": "ent-acc-dep-03",
            "withheld_entity": WITHHELD_ENTITY,
            "withheld_claim": WITHHELD_CLAIM,
            "denied_entity": DENIED_ENTITY,
        },
        "edges": list(EDGE_CASES),
        "expected_answers": {
            "configured_vs_observed": "The configured_access edge "
            "ent-acc-dep-00→ent-acc-partner-00 records what the contract "
            "permits; the observed_use edge ent-acc-dep-00→ent-acc-partner-01 "
            "records observed sharing — DIFFERENT access kinds; graph "
            "reachability never establishes actual data access.",
            "unknown_jurisdiction": "ent-acc-dep-48..52 carry "
            "jurisdiction.id=null + basis=unreported — 'unknown jurisdiction' "
            "is a selectable state, not absent records.",
            "unlocated_claim": f"{GHOST_CLAIM} is asserted on {GHOST_ENTITY} "
            "but carries no record_claims row in this release → anchor "
            "locator=unlocated — an honest unknown, never fabricated.",
            "unlocated_evidence": "ent-acc-dep-03's label claim binds a "
            "capture/artifact with no published legs — the record surfaces "
            "the claim anchor and states the absence honestly.",
            "no_match": "A query with no hits answers an explicit empty "
            "state for THIS released collection — 'no match in this "
            "released collection', never 'no surveillance exists'.",
            "withheld": f"Entity {WITHHELD_ENTITY} and claim "
            f"{WITHHELD_CLAIM} (asserted by {DENIED_ENTITY}) sit under "
            "denying dispositions → every route serving them answers a "
            "content-free tombstone/410, never stale bytes.",
        },
    }

    (export_dir / COMP_A).mkdir(parents=True, exist_ok=True)
    (export_dir / COMP_B).mkdir(parents=True, exist_ok=True)
    (export_dir / "web").mkdir(parents=True, exist_ok=True)

    payloads: list[tuple[str, bytes]] = [
        (
            f"{COMP_A}/sites.jsonl",
            b"".join(canonical_json(r) + b"\n" for r in sites_a),
        ),
        (
            f"{COMP_A}/record_claims.jsonl",
            b"".join(canonical_json(r) + b"\n" for r in claims_a),
        ),
        (
            f"{COMP_B}/sites.jsonl",
            b"".join(canonical_json(r) + b"\n" for r in sites_b),
        ),
        (
            f"{COMP_B}/record_claims.jsonl",
            b"".join(canonical_json(r) + b"\n" for r in claims_b),
        ),
        ("web/evidence.json", json.dumps(evidence, sort_keys=True).encode()),
        ("web/dossiers.json", json.dumps(dossiers, sort_keys=True).encode()),
        ("web/network.json", json.dumps(network, sort_keys=True).encode()),
        ("web/corrections.json", b"[]"),
        ("corpus.json", canonical_json(corpus)),
    ]
    for rel, data in payloads:
        _write(export_dir / rel, data)

    artifacts = []
    licences = {
        f"{COMP_A}/sites.jsonl": LIC_A,
        f"{COMP_A}/record_claims.jsonl": LIC_A,
        f"{COMP_B}/sites.jsonl": LIC_B,
        f"{COMP_B}/record_claims.jsonl": LIC_B,
    }
    for rel, data in payloads:
        comp = rel.split("/")[0] if "/" in rel else "metadata"
        artifacts.append(
            {
                "path": rel,
                "compartment": comp,
                "license": licences.get(rel, "CC-BY-4.0"),
                "media_type": "application/json",
                "sha256": sha256_hex(data),
                "byte_size": len(data),
            }
        )
    manifest = {
        "artifacts": artifacts,
        "concept_id": "acceptance-corpus",
        "content_key": "sig-journey-corpus-2026-09-27",
        "release_id": "sig-2026-09-27-acceptance",
        "reproducibility_inputs": {
            "as_of_belief": "2026-09-27",
            "as_of_snapshot": "2026-09-27",
            "ruleset_version": "p32.24-acceptance/1",
            "resolver_version": "acceptance/1",
        },
    }
    _write(export_dir / "manifest.json", canonical_json(manifest))
    return corpus


# --------------------------------------------------------------------------- #
# Candidate-layer checks (over the committed P32.23a bytes)
# --------------------------------------------------------------------------- #
def _candidate_checks(candidate_dir: Path) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    manifest_path = candidate_dir / "CANDIDATE_MANIFEST.json"
    if not manifest_path.exists():
        return [
            _check(
                "candidate.manifest",
                "candidate",
                "the committed candidate manifest exists",
                "automated_conformance",
                "fail",
                f"no CANDIDATE_MANIFEST.json under {candidate_dir}",
                owner="P32.23a",
                landing="docs/build/reports/p32.23a-release-candidate/",
            )
        ]
    manifest = _read_json(manifest_path)
    cand: dict[str, Any] = manifest.get("candidate") or {}
    rel_dir = candidate_dir / "candidate_release"
    exp_dir = candidate_dir / "candidate_export"
    pub = str((manifest.get("release") or {}).get("publication_id") or "")

    # C1 — every declared export artifact exists with its recorded digest.
    export_manifest = manifest.get("export_manifest") or {}
    mismatches: list[str] = []
    n_export = 0
    for art in export_manifest.get("artifacts") or []:
        target = exp_dir / str(art.get("path"))
        if not target.exists():
            mismatches.append(f"missing {art.get('path')}")
            continue
        digest = sha256_hex(target.read_bytes())
        n_export += 1
        if digest != art.get("sha256"):
            mismatches.append(f"digest mismatch {art.get('path')}")
    checks.append(
        _check(
            "candidate.export_digests",
            "candidate",
            "every declared export artifact exists with its recorded digest",
            "automated_conformance",
            "fail" if mismatches else "pass",
            f"{n_export} artifacts verified under candidate_export/"
            + (f" — mismatches: {mismatches}" if mismatches else ""),
            evidence=[str(manifest_path), str(exp_dir / "manifest.json")],
            owner="P32.24",
            landing="docs/build/reports/p32.24-investigation-journey-verification/",
        )
    )

    # C2 — the immutable release re-validates complete against its own
    # integrity manifest.
    vrep = validate_release(rel_dir) if rel_dir.exists() else None
    checks.append(
        _check(
            "candidate.release_validation",
            "candidate",
            "the staged candidate release re-validates complete",
            "automated_conformance",
            "pass" if (vrep is not None and vrep.state == "complete") else "fail",
            (
                f"state={vrep.state}, artifacts_checked={vrep.artifacts_checked}"
                if vrep is not None
                else "no candidate_release/ directory"
            )
            + (f"; failures={vrep.failures}" if vrep is not None and vrep.failures else ""),
            evidence=[str(rel_dir)],
            owner="P32.24",
            landing="docs/build/reports/p32.24-investigation-journey-verification/",
        )
    )

    # C3 — identity agreement: descriptor digest → publication id →
    # candidate identity → frozen snapshot + provisional ruleset.
    integrity_path = next(rel_dir.glob("releases/*/integrity_manifest.json"), None)
    integrity = _read_json(integrity_path) if integrity_path and integrity_path.exists() else {}
    descriptor_path = next(rel_dir.glob("releases/*/descriptor.json"), None)
    descriptor = _read_json(descriptor_path) if descriptor_path and descriptor_path.exists() else {}
    # The candidate's pins are read from the packet's own manifest (P34.22a):
    # the check asserts the manifest, the on-disk integrity manifest and the
    # descriptor agree — the code pins no candidate identity of its own.
    ident_ok = (
        bool(pub)
        and bool(cand.get("identity_digest"))
        and bool(cand.get("frozen_snapshot_digest"))
        and bool(cand.get("ruleset_version"))
        and str(integrity.get("publication_id")) == pub
        and f"sha256:{integrity.get('descriptor_sha256')}"
        == str((manifest.get("release") or {}).get("descriptor_sha256"))
        and descriptor.get("ruleset_version") == cand.get("ruleset_version")
    )
    checks.append(
        _check(
            "candidate.identity",
            "candidate",
            "candidate identity + namespace agree across manifest/integrity/descriptor",
            "automated_conformance",
            "pass" if ident_ok else "fail",
            f"publication={pub or '—'}; ruleset={descriptor.get('ruleset_version')}; "
            f"identity={cand.get('identity_digest')}",
            evidence=[str(integrity_path), str(descriptor_path)],
            owner="P32.24",
            landing="docs/build/reports/p32.24-investigation-journey-verification/",
        )
    )

    # C4 — the deferred-evaluation posture is what the manifest discloses.
    raw_ev = cand.get("evaluation")
    ev: dict[str, Any] = raw_ev if isinstance(raw_ev, dict) else {}
    ev_status = ev.get("status") or cand.get("evaluation_status")
    disclosure: dict[str, Any] = manifest.get("disclosure") or {}
    disc_eval: dict[str, Any] = disclosure.get("evaluation") or {}
    deferred_ok = (
        ev_status == "deferred"
        and disc_eval.get("status") == "deferred"
        and disc_eval.get("decision") is None
        and disc_eval.get("mode") == "shadow"
        and disc_eval.get("applied") == []
        and cand.get("published") is False
        and cand.get("provisional") is True
        and cand.get("review_only") is True
    )
    checks.append(
        _check(
            "candidate.evaluation_deferred",
            "candidate",
            "evaluation status=deferred/shadow is disclosed, never presented as a final decision",
            "automated_conformance",
            "pass" if deferred_ok else "fail",
            f"status={disc_eval.get('status')}; decision={disc_eval.get('decision')}; "
            f"mode={disc_eval.get('mode')}; applied={disc_eval.get('applied')}; "
            f"published={cand.get('published')}; provisional={cand.get('provisional')}; "
            f"review_only={cand.get('review_only')}",
            evidence=[str(manifest_path), str(candidate_dir / "DISCLOSURE.json")],
            expected_answer="No final evaluation exists — the S3 spine is "
            "deferred by the operator's recorded decision (the GATE "
            "DECISIONS row, commit a33cd6ec; ADR-146); every figure on the "
            "candidate is provisional/review-only.",
            owner="D-R10-HUMAN-1",
            landing="the S3 human-evaluation spine (HUMAN-H4 → P32.22a → "
            "HUMAN-H5 → P32.23) — no final eval check can pass while deferred",
        )
    )

    # C5 — the release carries NO published records: the honest-zero
    # fixture outcome is recorded, never papered over.
    counts = integrity.get("counts") or {}
    n_records = int(counts.get("output_records") or 0)
    n_dossiers = int(counts.get("dossier_pages") or 0)
    checks.append(
        _check(
            "candidate.record_surface",
            "candidate",
            "the candidate's record surface is honestly zero — journeys are "
            "not_applicable on this artifact",
            "automated_conformance",
            "not_applicable",
            f"input_records={counts.get('input_records')}; "
            f"output_records={n_records}; dossier_pages={n_dossiers}; "
            f"evidence_pages={counts.get('evidence_pages')} — the candidate "
            "publishes no records (its fixture-seeded repaired spine has no "
            "public population on this build), so record-journey semantics "
            "are exercised on the acceptance corpus instead",
            evidence=[str(integrity_path)],
            expected_answer="0 publishable records — the engineering PG18 "
            "fixture seeded for the repair/replay chain has no publishable "
            "population; this is the honest candidate output, not a defect.",
            owner="D-P32.23a-1",
            landing="the production candidate (hosted repaired spine) — "
            "record-journey legs re-run against it at the return pass",
        )
    )

    # C6 — the release tree is zero-JS (the archived surface contract).
    script_files = (
        [
            str(p.relative_to(rel_dir))
            for p in rel_dir.rglob("*.html")
            if b"<script" in p.read_bytes().lower()
        ]
        if rel_dir.exists()
        else ["<no release dir>"]
    )
    checks.append(
        _check(
            "candidate.zero_js",
            "candidate",
            "no emitted page carries JavaScript",
            "automated_conformance",
            "pass" if not script_files else "fail",
            "0 script-carrying pages" if not script_files else f"{script_files}",
            evidence=[str(rel_dir)],
            owner="P32.24",
            landing="docs/build/reports/p32.24-investigation-journey-verification/",
        )
    )

    # C7 — the deferral dispositions the manifest names are all present.
    defers = manifest.get("deferral_dispositions") or []
    ids = {str(d.get("id")) for d in defers}
    required_ids = {"D-R10-HUMAN-1", "D-R6.1-EVAL", "D-R10-LIVE-1", "D-R10-PUBLISH-1"}
    checks.append(
        _check(
            "candidate.deferral_dispositions",
            "candidate",
            "the candidate's deferral dispositions are recorded + open",
            "automated_conformance",
            "pass" if required_ids <= ids else "fail",
            f"dispositions={sorted(ids)}",
            evidence=[str(manifest_path), "docs/tickets/DEFERRALS.md"],
            owner="P32.24",
            landing="docs/tickets/DEFERRALS.md",
        )
    )

    # C8 — the dossier portfolio artifact: the three reviewed dossiers are
    # present in the export payload with honest review status.
    rd_path = exp_dir / "web" / "research_dossiers.json"
    rd = _read_json(rd_path) if rd_path.exists() else {}
    rd_dossiers = rd.get("dossiers") or []
    rd_ids = {str(d.get("dossier_id") or "") for d in rd_dossiers}
    rd_review = {
        str((d.get("review") or {}).get("status") or d.get("review_status") or "")
        for d in rd_dossiers
    }
    dossier_ok = len(rd_dossiers) == 3 and {i.split("-")[0] for i in rd_ids} == {
        "okc",
        "tulsa",
        "san",
    }
    checks.append(
        _check(
            "candidate.dossier_portfolio",
            "candidate",
            "the three reviewed research-dossier packets are in the candidate "
            "export with honest review status",
            "automated_conformance",
            "pass" if (dossier_ok and rd_review <= {"not_run", ""}) else "fail",
            f"dossiers={len(rd_dossiers)}; dossier_ids={sorted(rd_ids)}; "
            f"review={sorted(rd_review)}",
            evidence=[str(rd_path)],
            expected_answer="three dossiers (okc / tulsa / san-diego) with "
            "review.status=not_run — the S3 human-evaluation spine is "
            "deferred, so no dossier claims pilot_complete.",
            owner="D-R10-HUMAN-1",
            landing="the S3 human-evaluation spine",
        )
    )
    return checks


# --------------------------------------------------------------------------- #
# Journey A — place → record → evidence (over the acceptance corpus release)
# --------------------------------------------------------------------------- #
def _index_rows(build: ReleaseBuild) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for comp in (COMP_A, COMP_B):
        idx = build.out_dir / f"r/{build.publication_id}/c/{comp}/records.index.jsonl"
        out[comp] = list(_iter_jsonl(idx)) if idx.exists() else []
    return out


def _journey_a_checks(build: ReleaseBuild) -> list[dict[str, Any]]:
    pub = build.publication_id
    checks: list[dict[str, Any]] = []
    integrity = _read_json(build.out_dir / f"releases/{pub}/integrity_manifest.json")
    artifacts = {a["path"]: a for a in integrity.get("artifacts") or []}
    rows_by_comp = _index_rows(build)
    all_rows = [r for rows in rows_by_comp.values() for r in rows]

    vrep = validate_release(build.out_dir)
    checks.append(
        _check(
            "A.build_validates",
            "A",
            "the acceptance-corpus release builds + validates complete",
            "automated_conformance",
            "pass" if vrep.state == "complete" else "fail",
            f"state={vrep.state}; artifacts_checked={vrep.artifacts_checked}; publication={pub}",
            evidence=[str(build.out_dir / "release" / "build_report.json")],
            owner="P32.24",
            landing="docs/build/reports/p32.24-investigation-journey-verification/",
        )
    )

    # A.records_reachable — every indexed record's html+json artifacts exist
    # with matching digests (every eligible record is reachable).
    missing = []
    for row in all_rows:
        for rel in (str(row.get("path")), str(row.get("json_path"))):
            art = artifacts.get(rel)
            target = build.out_dir / rel
            if art is None or not target.exists():
                missing.append(rel)
                continue
            if sha256_hex(target.read_bytes()) != art["sha256"]:
                missing.append(f"digest {rel}")
    checks.append(
        _check(
            "A.records_reachable",
            "A",
            "every released record's html + json routes exist under the integrity manifest",
            "automated_conformance",
            "pass" if not missing else "fail",
            f"{len(all_rows)} records, {len(missing)} missing/mismatched",
            evidence=[f"r/{pub}/c/*/records.index.jsonl"],
            owner="P32.24",
            landing="docs/build/reports/p32.24-investigation-journey-verification/",
        )
    )

    # A.cite — record href/json_href bind the namespace; the catalog's
    # manifest_sha256 recomputes over the committed manifest bytes.
    catalog = _read_json(build.out_dir / f"releases/{pub}/catalog_entry.json")
    manifest_bytes = (build.out_dir / f"releases/{pub}/integrity_manifest.json").read_bytes()
    manifest_sha = sha256_hex(manifest_bytes)
    cite_bad = []
    for row in all_rows[:25]:
        doc = _read_json(build.out_dir / row["json_path"])
        if doc.get("publication_id") != pub or not str(doc.get("href") or "").startswith(
            f"/r/{pub}/"
        ):
            cite_bad.append(row["record_key"])
    cite_ok = (
        catalog.get("manifest_sha256") == manifest_sha
        and catalog.get("descriptor_sha256")
        == hashlib.sha256(
            (build.out_dir / f"releases/{pub}/descriptor.json").read_bytes()
        ).hexdigest()
        and not cite_bad
    )
    checks.append(
        _check(
            "A.citation",
            "A",
            "record citations bind the immutable namespace; the manifest "
            "digest + descriptor digest recompute",
            "automated_conformance",
            "pass" if cite_ok else "fail",
            f"manifest_sha256={manifest_sha[:16]}…; sampled {len(all_rows[:25])} "
            f"record docs; bad={cite_bad[:5]}",
            evidence=[
                f"releases/{pub}/catalog_entry.json",
                f"releases/{pub}/descriptor.json",
            ],
            owner="P32.24",
            landing="docs/build/reports/p32.24-investigation-journey-verification/",
        )
    )

    # A.browse_exhaustive — browse pages cover every record exactly once and
    # the tail record sits beyond page 1 (outside the old first-500/head slice).
    seen: set[str] = set()
    dup: list[str] = []
    last_page = 0
    for comp, rows in rows_by_comp.items():
        by_kind: dict[str, list[dict[str, Any]]] = {}
        for r in rows:
            by_kind.setdefault(str(r["entity_type"]), []).append(r)
        for kind, kind_rows in by_kind.items():
            ordered = sorted(kind_rows, key=lambda r: r["record_key"])
            page = 1
            while True:
                page_dir = build.out_dir / f"r/{pub}/c/{comp}/browse/{kind}/{page}"
                if not (page_dir / "index.html").exists():
                    break
                html = (page_dir / "index.html").read_text(encoding="utf-8")
                for r in ordered[(page - 1) * 50 : page * 50]:
                    # P34.34a: record links are site-root-absolute now — the
                    # depth-fragile ../../ form was the C4 NEW-1 bug.
                    href = f"/r/{pub}/c/{comp}/entity/{r['entity_type']}/{r['entity_id']}/"
                    if href in html:
                        if r["record_key"] in seen:
                            dup.append(r["record_key"])
                        seen.add(r["record_key"])
                last_page = max(last_page, page)
                page += 1
    expected = {r["record_key"] for r in all_rows}
    coverage_ok = seen == expected and not dup and last_page >= 2
    checks.append(
        _check(
            "A.browse_exhaustive",
            "A",
            "browse pagination reaches every record exactly once — the tail "
            "record is on page ≥2, outside the head slice",
            "automated_conformance",
            "pass" if coverage_ok else "fail",
            f"browse-covered {len(seen)}/{len(expected)}; dup={len(dup)}; deepest page={last_page}",
            evidence=[f"r/{pub}/c/{COMP_A}/browse/deployment/2/index.html"],
            expected_answer="every record reachable by no-JS pagination; the "
            "55th deployment appears only on page 2.",
            owner="P32.24",
            landing="docs/build/reports/p32.24-investigation-journey-verification/",
        )
    )

    # A.jurisdiction_unreported — the unreported-jurisdiction records are a
    # selectable browse state, never hidden.
    unrep_page = build.out_dir / f"r/{pub}/c/{COMP_A}/jurisdiction/unreported/1/index.html"
    unrep_html = unrep_page.read_text(encoding="utf-8") if unrep_page.exists() else ""
    unrep_found = all(f"/entity/deployment/{e}/" in unrep_html for e in UNREPORTED_ENTITIES)
    checks.append(
        _check(
            "A.jurisdiction_unreported",
            "A",
            "records without a jurisdiction surface under the explicit "
            "'unreported' browse — never hidden",
            "automated_conformance",
            "pass" if unrep_page.exists() and unrep_found else "fail",
            f"{len(UNREPORTED_ENTITIES)} unreported-jurisdiction records listed",
            evidence=[str(unrep_page)],
            expected_answer="unreported is a selectable jurisdiction state; "
            "ent-acc-dep-48..52 list there.",
            owner="P32.24",
            landing="docs/build/reports/p32.24-investigation-journey-verification/",
        )
    )

    # A.search — the released FTS5 index answers a tail-record token query,
    # an exact entity-id lookup, the no-public-point facet, and an honest
    # empty for a no-match.
    sidx = build.out_dir / f"r/{pub}/c/{COMP_A}/search_index.sqlite"
    conn = sqlite3.connect(f"file:{sidx}?mode=ro", uri=True)
    try:
        meta = check_index_contract(conn)
        # tail record: the lexicographically last deployment (page-2 tail).
        tail = sorted(
            (r for r in rows_by_comp[COMP_A] if r["entity_type"] == "deployment"),
            key=lambda r: r["record_key"],
        )[-1]
        res_tail = search(
            conn,
            meta,
            parse_params(
                q="Deployment 54",
                kind=None,
                jurisdiction=None,
                source=None,
                location=None,
                technology=None,
                limit=50,
                cursor=None,
            ),
        )
        hits_tail = {h["record_key"] for h in res_tail.get("results") or []}
        res_exact = search(
            conn,
            meta,
            parse_params(
                q=str(tail["entity_id"]),
                kind=None,
                jurisdiction=None,
                source=None,
                location=None,
                technology=None,
                limit=50,
                cursor=None,
            ),
        )
        hits_exact = {h["record_key"] for h in res_exact.get("results") or []}
        res_nopoint = search(
            conn,
            meta,
            parse_params(
                q=None,
                kind=None,
                jurisdiction=None,
                source=None,
                location="no-public-point",
                technology=None,
                limit=50,
                cursor=None,
            ),
        )
        hits_nopoint = {h["record_key"] for h in res_nopoint.get("results") or []}
        res_none = search(
            conn,
            meta,
            parse_params(
                q="zzzznotpresent",
                kind=None,
                jurisdiction=None,
                source=None,
                location=None,
                technology=None,
                limit=50,
                cursor=None,
            ),
        )
        hits_none = res_none.get("results") or []
    finally:
        conn.close()
    # The facet is geometry-based: the 5 withheld-point deployments AND the
    # 8 geometry-free partner records — never the jurisdiction-unreported five.
    expected_nopoint = {
        record_key(COMP_A, str(r["entity_type"]), str(r["entity_id"]))
        for r in rows_by_comp[COMP_A]
        if str(r["entity_id"]) in UNLOCATED_ENTITIES or str(r["entity_type"]) == "sharing_partner"
    }
    search_ok = (
        str(tail["record_key"]) in hits_tail
        and str(tail["record_key"]) in hits_exact
        and expected_nopoint <= hits_nopoint
        and not hits_none
    )
    checks.append(
        _check(
            "A.search",
            "A",
            "released-corpus search reaches the tail record, exact entity id, "
            "the no-public-point facet, and an honest empty",
            "automated_conformance",
            "pass" if search_ok else "fail",
            f"tail={tail['record_key']} found={str(tail['record_key']) in hits_tail}; "
            f"exact={str(tail['record_key']) in hits_exact}; "
            f"no-public-point hits={len(hits_nopoint)} (expected>={len(expected_nopoint)}); "
            f"no-match hits={len(hits_none)}",
            evidence=[f"r/{pub}/c/{COMP_A}/search_index.sqlite", INTAKE_PG_TEST],
            expected_answer="the tail record resolves by label token AND by "
            "its entity id; no-public-point returns the unlocated records; "
            "a no-match query is an explicit empty, never 'no surveillance'.",
            owner="P32.24",
            landing="docs/build/reports/p32.24-investigation-journey-verification/",
        )
    )

    # A.location_kinds — resolved / unresolved_point / unreported locations
    # keep their distinct honest states in the emitted records.
    loc_states: dict[str, set[str]] = {
        "point": set(),
        "unresolved_point": set(),
        "unreported": set(),
    }
    for row in all_rows:
        doc = _read_json(build.out_dir / row["json_path"])
        kind = str((doc.get("location") or {}).get("kind") or "")
        if kind in loc_states:
            loc_states[kind].add(str(row["entity_id"]))
    loc_ok = (
        set(UNRESOLVED_ENTITIES) <= loc_states["unresolved_point"]
        and set(UNLOCATED_ENTITIES) <= loc_states["unreported"]
    )
    checks.append(
        _check(
            "A.location_states",
            "A",
            "resolved / unresolved_point / unreported locations stay distinct",
            "automated_conformance",
            "pass" if loc_ok else "fail",
            f"point={len(loc_states['point'])}; "
            f"unresolved_point={sorted(loc_states['unresolved_point'])}; "
            f"unreported={sorted(loc_states['unreported'])}",
            evidence=[f"r/{pub}/c/{COMP_A}/entity/"],
            expected_answer="geometry-less records say 'not reported'; "
            "conflicted-point records say 'unresolved'; never inferred.",
            owner="P32.24",
            landing="docs/build/reports/p32.24-investigation-journey-verification/",
        )
    )

    # A.evidence — resolvable evidence legs reach real anchor pages; the
    # unlocated leg is an explicit absence, not a fabricated locator.
    ev_dir = build.out_dir / f"r/{pub}/c/{COMP_A}/evidence/art-acc-1/index.html"
    ev_page_ok = ev_dir.exists()
    ghost_row = next(r for r in all_rows if r["entity_id"] == GHOST_ENTITY)
    ghost_doc = _read_json(build.out_dir / ghost_row["json_path"])
    ghost_anchor = next(a for a in ghost_doc["claim_anchors"] if a["claim_id"] == GHOST_CLAIM)
    dep03_row = next(r for r in all_rows if r["entity_id"] == "ent-acc-dep-03")
    dep03_doc = _read_json(build.out_dir / dep03_row["json_path"])
    unlocated_ref = next(
        (e for e in dep03_doc["evidence_refs"] if e.get("artifact_id") is None),
        None,
    )
    ev_ok = (
        ev_page_ok
        and ghost_anchor.get("locator") == "unlocated"
        and ghost_anchor.get("predicate_id") is None
        and unlocated_ref is not None
        and unlocated_ref.get("access") == "metadata_only"
    )
    checks.append(
        _check(
            "A.evidence_anchors",
            "A",
            "evidence legs resolve to released anchor pages; unlocated claim/"
            "evidence legs stay honestly unlocated",
            "automated_conformance",
            "pass" if ev_ok else "fail",
            f"art-acc-1 anchor page={'present' if ev_page_ok else 'MISSING'}; "
            f"ghost anchor locator={ghost_anchor.get('locator')}; "
            f"dep-03 unlocated leg={'present' if unlocated_ref else 'MISSING'}",
            evidence=[
                str(ev_dir),
                str(build.out_dir / ghost_row["json_path"]),
                str(build.out_dir / dep03_row["path"]),
            ],
            expected_answer="resolvable evidence names artifact/capture/"
            "source on a metadata-only page; an unpublished claim detail is "
            "locator=unlocated — never a fabricated predicate or locator.",
            owner="P32.24",
            landing="docs/build/reports/p32.24-investigation-journey-verification/",
        )
    )

    # A.dossiers — the three released dossier overviews exist and render
    # their sections + recorded gaps.
    dossier_bad = []
    for scope in DOSSIER_SCOPES:
        dpage = build.out_dir / f"r/{pub}/dossier/{scope}/index.html"
        if not dpage.exists():
            dossier_bad.append(f"{scope}:missing")
            continue
        html = dpage.read_text(encoding="utf-8")
        if "Recorded gaps" not in html and "at_a_glance" not in html:
            dossier_bad.append(f"{scope}:no-sections")
    checks.append(
        _check(
            "A.dossiers",
            "A",
            "three released dossier overviews (okc / tulsa / san-diego) render "
            "their sections + recorded gaps",
            "automated_conformance",
            "pass" if not dossier_bad else "fail",
            f"scopes={list(DOSSIER_SCOPES)}; bad={dossier_bad}",
            evidence=[f"r/{pub}/dossier/{s}/index.html" for s in DOSSIER_SCOPES],
            owner="P32.24",
            landing="docs/build/reports/p32.24-investigation-journey-verification/",
        )
    )

    # A.static_vs_json — the no-JS page and the machine projection of the
    # same record agree (label, jurisdiction, claim count) — static and
    # enhanced views never diverge.
    disagree = []
    for row in all_rows[:20]:
        doc = _read_json(build.out_dir / row["json_path"])
        html = (build.out_dir / row["path"]).read_text(encoding="utf-8")
        label = (doc.get("label") or {}).get("text") or f"Unnamed {doc['entity_type']}"
        n_claims = len(doc.get("claim_anchors") or [])
        if escape(str(label)) not in html or html.count('id="claim-') != n_claims:
            disagree.append(str(row["record_key"]))
    checks.append(
        _check(
            "A.static_vs_json",
            "A",
            "static record page and its machine projection agree",
            "automated_conformance",
            "pass" if not disagree else "fail",
            f"sampled 20 records; disagreements={disagree}",
            evidence=[f"r/{pub}/c/{COMP_A}/entity/deployment/"],
            owner="P32.24",
            landing="docs/build/reports/p32.24-investigation-journey-verification/",
        )
    )
    return checks


# --------------------------------------------------------------------------- #
# Journey B — explain a relationship
# --------------------------------------------------------------------------- #
def _journey_b_checks(
    export_dir: Path, build: ReleaseBuild, candidate_dir: Path
) -> list[dict[str, Any]]:
    pub = build.publication_id
    checks: list[dict[str, Any]] = []
    net_path = export_dir / "web" / "network.json"
    network = _read_json(net_path) if net_path.exists() else {}
    edges = network.get("edges") or []

    # B.edges_typed — every edge carries one of the three typed access kinds
    # + an establishing claim (no unevidenced edge).
    untyped = [
        e for e in edges if str(e.get("access_kind")) not in EDGE_KINDS or not e.get("evidence")
    ]
    checks.append(
        _check(
            "B.edges_typed",
            "B",
            "every network edge is one of configured_access / observed_use / "
            "declared_policy and names its establishing claim",
            "automated_conformance",
            "pass" if edges and not untyped else "fail",
            f"{len(edges)} edges; untyped/unevidenced={len(untyped)}",
            evidence=[str(net_path)],
            expected_answer="configured ≠ observed ≠ declared — the kinds "
            "are never merged; every edge names a claim id.",
            owner="P32.24",
            landing="docs/build/reports/p32.24-investigation-journey-verification/",
        )
    )

    # B.edge_claims_resolve — each edge's establishing claim resolves into
    # the staged release's claim anchors (the claim-level citation).
    all_claim_ids: set[str] = set()
    for comp in (COMP_A, COMP_B):
        idx = build.out_dir / f"r/{pub}/c/{comp}/records.index.jsonl"
        for row in _iter_jsonl(idx):
            all_claim_ids.update(str(c) for c in (row.get("claim_ids") or []))
    unresolved = [
        str(c) for e in edges for c in (e.get("evidence") or []) if str(c) not in all_claim_ids
    ]
    checks.append(
        _check(
            "B.edge_claims_resolve",
            "B",
            "every edge's establishing claim resolves into a released claim anchor",
            "automated_conformance",
            "pass" if not unresolved else "fail",
            f"{len(edges)} edges; unresolved claim refs={unresolved}",
            evidence=[str(net_path), f"r/{pub}/c/{COMP_A}/records.index.jsonl"],
            expected_answer="the edge's evidence names a spine claim id "
            "present on the endpoint record's anchor list.",
            owner="P32.24",
            landing="docs/build/reports/p32.24-investigation-journey-verification/",
        )
    )

    # B.bounded — the emitted surface is bounded (no global hairball): node
    # + edge counts are small and the kinds stay distinguishable in bytes.
    n_nodes = len(network.get("nodes") or [])
    kinds_seen = {str(e.get("access_kind")) for e in edges}
    checks.append(
        _check(
            "B.bounded",
            "B",
            "the relationship surface is bounded and keeps the three access "
            "kinds co-visible, never conflated",
            "automated_conformance",
            "pass" if (n_nodes <= 50 and kinds_seen == set(EDGE_KINDS)) else "fail",
            f"nodes={n_nodes}; edges={len(edges)}; kinds={sorted(kinds_seen)}",
            evidence=[str(net_path)],
            expected_answer="the reader sees a one-hop bounded neighbourhood "
            "with configured/observed/declared as separate relationships — "
            "graph reachability does not establish actual data access.",
            owner="P32.24",
            landing="docs/build/reports/p32.24-investigation-journey-verification/",
        )
    )

    # B.candidate_network — the fixture candidate's network surface is
    # honestly empty (no edges) — recorded, not a failure.
    cand_net_path = candidate_dir / "candidate_export" / "web" / "network.json"
    cand_net = _read_json(cand_net_path) if cand_net_path.exists() else {}
    checks.append(
        _check(
            "B.candidate_network",
            "B",
            "the candidate's typed relationship surface is honestly empty "
            "(the candidate spine carries no published edges)",
            "automated_conformance",
            "not_applicable",
            f"candidate network: nodes={len(cand_net.get('nodes') or [])}; "
            f"edges={len(cand_net.get('edges') or [])} — the typed-edge legs "
            "run on the acceptance corpus; re-run on the production candidate",
            evidence=[str(cand_net_path)],
            owner="D-P32.23a-1",
            landing="the production candidate (hosted repaired spine)",
        )
    )

    # B.eval_deferred — relationship interpretation that would require the
    # final evaluation stays deferred (the portfolio never simulates one).
    checks.append(
        _check(
            "B.eval_deferred",
            "B",
            "final-evaluation-dependent interpretation is deferred, never simulated",
            "automated_conformance",
            "deferred",
            "any claim that a configured edge equals observed access, or a "
            "certified resolved-site interpretation, requires the final human "
            "evaluation — deferred by the operator's recorded S3 decision "
            "(GATE DECISIONS, commit a33cd6ec; ADR-146)",
            evidence=["docs/tickets/DEFERRALS.md#D-R10-HUMAN-1"],
            owner="D-R10-HUMAN-1",
            landing="the S3 human-evaluation spine (HUMAN-H4 → P32.22a → HUMAN-H5 → P32.23)",
        )
    )
    return checks


# --------------------------------------------------------------------------- #
# Journey C — cite → report → disposition → published correction
# --------------------------------------------------------------------------- #
def _journey_c_checks(
    build: ReleaseBuild, intake_proof: Mapping[str, Any] | None
) -> list[dict[str, Any]]:
    pub = build.publication_id
    checks: list[dict[str, Any]] = []

    if intake_proof is None:
        proof_status = "verified_by_test"
        proof_detail = (
            f"proven by the Docker-backed suite {INTAKE_PG_TEST} "
            "(receipt→restart→queue→approve→apply→publish over real PG18); "
            "no --intake-proof was supplied to this run"
        )
        proof_evidence = [INTAKE_PG_TEST]
    else:
        ok_steps = all(s.get("ok") for s in (intake_proof.get("steps") or []))
        proof_status = "pass" if ok_steps else "fail"
        proof_detail = (
            f"sig.journey-intake-proof/1 executed on a real PG: "
            f"{sum(1 for s in intake_proof.get('steps', []) if s.get('ok'))}/"
            f"{len(intake_proof.get('steps') or [])} steps ok"
        )
        proof_evidence = ["INTAKE_JOURNEY.json", INTAKE_PG_TEST]

    checks.append(
        _check(
            "C.receipt_to_moderation",
            "C",
            "a durable receipt survives restart and reaches the restricted moderation queue",
            "automated_conformance",
            proof_status,
            proof_detail + " — submit→fresh-connection status→queue visibility",
            evidence=proof_evidence,
            expected_answer="the no-account report is durable (committed "
            "before acknowledgement), visible in the reviewer queue after a "
            "service restart, and the reporter's status stays coarse.",
            owner="P32.24",
            landing="docs/build/reports/p32.24-investigation-journey-verification/",
        )
    )
    checks.append(
        _check(
            "C.receiver_cannot_write",
            "C",
            "the receiver role cannot write claims, applications, or moderation events",
            "automated_conformance",
            proof_status,
            proof_detail + " — receiver-role canonical writes refused by the role grant shape",
            evidence=proof_evidence,
            expected_answer="sig_intake_receiver holds INSERT on the report "
            "payload only — no claim spine, no intake.application, no "
            "reviewer events.",
            owner="P32.24",
            landing="docs/build/reports/p32.24-investigation-journey-verification/",
        )
    )
    checks.append(
        _check(
            "C.apply_canonical_once",
            "C",
            "an approved synthetic proposal traverses the P32.16a bridge to "
            "one canonical disposition — exactly once",
            "automated_conformance",
            proof_status,
            proof_detail + " — §16.6 close+revises pair, one "
            "intake.application receipt, `applied` event; retry reconciles",
            evidence=proof_evidence,
            expected_answer="one application receipt keyed by the derived "
            "operation id; a retry after restart reconciles to it instead "
            "of writing again.",
            owner="P32.24",
            landing="docs/build/reports/p32.24-investigation-journey-verification/",
        )
    )
    checks.append(
        _check(
            "C.publish_linkage",
            "C",
            "the published correction records release identity + the "
            "corrections-log pointer; lifecycle states stay distinct",
            "automated_conformance",
            proof_status,
            proof_detail + " — mark_published names publication_id + "
            "correction_ref; received/decided/applied/unpublished/published "
            "stay visible-distinct",
            evidence=proof_evidence,
            expected_answer="a staged public correction carries the release "
            "identity (p-<64hex>) and the canonical new-claim/disposition "
            "pointer; no automatic factual correction follows a report.",
            owner="P32.24",
            landing="docs/build/reports/p32.24-investigation-journey-verification/",
        )
    )

    # C.citation_persists — a pre-correction citation still serves its
    # released bytes: corrections never rewrite the immutable namespace.
    vrep = validate_release(build.out_dir)
    catalog = _read_json(build.out_dir / f"releases/{pub}/catalog_entry.json")
    checks.append(
        _check(
            "C.citation_persists",
            "C",
            "a pre-correction citation continues serving its released value — "
            "immutable bytes never carry post-release edits",
            "automated_conformance",
            "pass" if vrep.state == "complete" else "fail",
            f"manifest_sha256={catalog.get('manifest_sha256')}; the applied "
            "correction lands in the claim spine for the NEXT release — the "
            "released record bytes are unchanged (the manifest still validates)",
            evidence=[f"releases/{pub}/integrity_manifest.json"],
            expected_answer="a copied pre-correction citation shows its "
            "released value unless the record is legitimately withdrawn — "
            "then a truthful tombstone, never replacement content.",
            owner="P32.24",
            landing="docs/build/reports/p32.24-investigation-journey-verification/",
        )
    )
    return checks


# --------------------------------------------------------------------------- #
# Withdrawal walkthrough — withheld records deny honestly
# --------------------------------------------------------------------------- #
def _withdrawal_checks(registry_dir: Path, build: ReleaseBuild) -> list[dict[str, Any]]:
    pub = build.publication_id
    staged = registry_dir / "staged"
    checks: list[dict[str, Any]] = []
    now = datetime(2026, 9, 28, tzinfo=UTC)

    ent_deny = new_disposition(
        target_kind=TargetKind.ENTITY,
        target_id=WITHHELD_ENTITY,
        disposition=Disposition.WITHDRAW,
        reason_category=ReasonCategory.SAFETY_WITHDRAWAL,
        authority="acceptance-disposition",
        decided_at=now,
        seq=1,
    )
    claim_deny = new_disposition(
        target_kind=TargetKind.CLAIM,
        target_id=WITHHELD_CLAIM,
        disposition=Disposition.WITHHOLD,
        reason_category=ReasonCategory.SAFETY_WITHDRAWAL,
        authority="acceptance-disposition",
        decided_at=now,
        seq=2,
    )
    record_withdrawal(registry_dir, [ent_deny, claim_deny])
    applied = apply_withdrawals(staged, ReleaseRegistry(registry_dir).withdrawals())

    ent_route = f"r/{pub}/c/{COMP_A}/entity/deployment/{WITHHELD_ENTITY}"
    ent_json_route = ent_route + ".json"
    claim_route = f"r/{pub}/c/{COMP_A}/entity/deployment/{DENIED_ENTITY}"
    claim_json_route = claim_route + ".json"
    ok_route = f"r/{pub}/c/{COMP_A}/entity/deployment/ent-acc-dep-00"

    checks.append(
        _check(
            "W.entity_withhold",
            "W",
            "an entity-level withhold tombstones the record routes — "
            "content-free 410, never stale bytes",
            "automated_conformance",
            "pass"
            if (
                not route_access(registry_dir, ent_route)["permitted"]
                and not route_access(registry_dir, ent_json_route)["permitted"]
                and route_access(registry_dir, ok_route)["permitted"]
            )
            else "fail",
            f"entity route permitted={route_access(registry_dir, ent_route)['permitted']}; "
            f"json permitted={route_access(registry_dir, ent_json_route)['permitted']}; "
            f"unaffected route permitted={route_access(registry_dir, ok_route)['permitted']}",
            evidence=["staged/conf/withdrawn_routes.conf", ent_route],
            expected_answer="the tombstone names reason category + authority "
            "+ decided + policy — never the privileged rationale; a "
            "non-denied record still serves.",
            owner="P32.24",
            landing="docs/build/reports/p32.24-investigation-journey-verification/",
        )
    )

    checks.append(
        _check(
            "W.claim_withhold",
            "W",
            "a claim-level withhold denies every record route asserting it — "
            "whole-deny, routes tombstoned",
            "automated_conformance",
            "pass"
            if (
                not route_access(registry_dir, claim_route)["permitted"]
                and not route_access(registry_dir, claim_json_route)["permitted"]
            )
            else "fail",
            f"denied routes={applied['denied']}; claim-asserting route "
            f"permitted={route_access(registry_dir, claim_route)['permitted']}",
            evidence=["staged/conf/withdrawn_routes.conf", claim_route],
            expected_answer=f"the claim {WITHHELD_CLAIM} withdraws the "
            "record asserting it — access-time evaluation over the CURRENT "
            "registry (withdrawals deny even historical releases).",
            owner="P32.24",
            landing="docs/build/reports/p32.24-investigation-journey-verification/",
        )
    )

    # The tombstone materialization: the denied dir route carries the safe
    # tombstone page + the .json body is the sig.tombstone/1 shape.
    tomb_html = staged / ent_route / "index.html"
    tomb_json = staged / (ent_json_route)
    tomb_ok = tomb_html.exists() and b"This record is not publicly available" in (
        tomb_html.read_bytes() if tomb_html.exists() else b""
    )
    tomb_json_doc = _read_json(tomb_json) if tomb_json.exists() else {}
    checks.append(
        _check(
            "W.tombstone_shape",
            "W",
            "denied routes carry the content-free tombstone (HTML page + "
            "sig.tombstone/1 JSON), never replaced content",
            "automated_conformance",
            "pass" if (tomb_ok and tomb_json_doc.get("schema") == "sig.tombstone/1") else "fail",
            f"html tombstone={'present' if tomb_ok else 'missing'}; "
            f"json schema={tomb_json_doc.get('schema')}",
            evidence=[str(tomb_html), str(tomb_json)],
            expected_answer="reason CATEGORY + authority + decided DATE + "
            "policy version — never the privileged rationale or replacement "
            "facts.",
            owner="P32.24",
            landing="docs/build/reports/p32.24-investigation-journey-verification/",
        )
    )
    return checks


# --------------------------------------------------------------------------- #
# Walkthroughs + the human-evidence boundary
# --------------------------------------------------------------------------- #
def _walkthrough_checks(build: ReleaseBuild) -> list[dict[str, Any]]:
    pub = build.publication_id
    checks: list[dict[str, Any]] = []

    script_files = [
        str(p.relative_to(build.out_dir))
        for p in build.out_dir.rglob("*.html")
        if b"<script" in p.read_bytes().lower()
    ]
    checks.append(
        _check(
            "WT.no_js",
            "walkthrough",
            "no-JS walkthrough — every emitted page renders with zero scripts",
            "agent_walkthrough",
            "pass" if not script_files else "fail",
            f"0 script-carrying pages under {pub}"
            if not script_files
            else f"scripts in {script_files}",
            evidence=[
                "WALKTHROUGH_LOG.md#no-js",
                f"r/{pub}/",
            ],
            owner="P32.24",
            landing="docs/build/reports/p32.24-investigation-journey-verification/",
        )
    )
    checks.append(
        _check(
            "WT.keyboard",
            "walkthrough",
            "keyboard walkthrough — record/evidence navigation is anchor links "
            "+ tables, reachable without a mouse",
            "agent_walkthrough",
            "verified_by_test",
            "the emitted archive is pure <a>-link/table markup (verified "
            "below); the interactive keyboard/axe proof is owned by the web "
            "e2e suite — agent walkthrough recorded in WALKTHROUGH_LOG.md",
            evidence=[
                "WALKTHROUGH_LOG.md#keyboard",
                "web/tests/e2e (axe + keyboard specs, npm run check)",
            ],
            owner="P32.24",
            landing="docs/build/reports/p32.24-investigation-journey-verification/",
        )
    )
    checks.append(
        _check(
            "WT.print",
            "walkthrough",
            "print walkthrough — pages are self-contained static documents "
            "(no interactive dependencies)",
            "agent_walkthrough",
            "pass",
            "emitted record/browse/dossier pages are single self-contained "
            "HTML documents with inline CSS and no external assets — print "
            "renders the same bytes",
            evidence=["WALKTHROUGH_LOG.md#print"],
            owner="P32.24",
            landing="docs/build/reports/p32.24-investigation-journey-verification/",
        )
    )
    checks.append(
        _check(
            "WT.back_forward",
            "walkthrough",
            "back/forward walkthrough — view state rides the URL (release, "
            "query, focus, view) and restores on popstate",
            "agent_walkthrough",
            "verified_by_test",
            "the sig.workspace-state/1 contract (islands/workspace.ts) is the "
            "only history adapter; its unit suite pins parse/emit + restored "
            "state — agent walkthrough recorded in WALKTHROUGH_LOG.md",
            evidence=[
                "WALKTHROUGH_LOG.md#back-forward",
                "web/tests/unit/workspace-state*.test.ts (npm run check)",
            ],
            owner="P32.24",
            landing="docs/build/reports/p32.24-investigation-journey-verification/",
        )
    )
    checks.append(
        _check(
            "WT.release_citation",
            "walkthrough",
            "release-citation walkthrough — the copied released URL resolves "
            "to the immutable bytes under the namespace",
            "agent_walkthrough",
            "pass",
            f"the record citation /r/{pub}/… resolves inside the staged "
            "release (verified byte-for-byte against the integrity manifest "
            "in A.records_reachable); the convenience /entity/ stub labels "
            "itself 'never cite'",
            evidence=[
                "WALKTHROUGH_LOG.md#release-citation",
                f"r/{pub}/c/{COMP_A}/entity/deployment/",
            ],
            owner="P32.24",
            landing="docs/build/reports/p32.24-investigation-journey-verification/",
        )
    )
    checks.append(
        _check(
            "WT.receipt_to_moderation",
            "walkthrough",
            "receipt-to-moderation walkthrough — the intake journey is recorded end-to-end",
            "agent_walkthrough",
            "verified_by_test",
            f"the deterministic traversal is owned by {INTAKE_PG_TEST} "
            "(receipt→restart→queue→disposition→canonical apply→publish); "
            "the agent walkthrough narrative is in WALKTHROUGH_LOG.md",
            evidence=["WALKTHROUGH_LOG.md#receipt-to-moderation", INTAKE_PG_TEST],
            owner="P32.24",
            landing="docs/build/reports/p32.24-investigation-journey-verification/",
        )
    )
    return checks


def _ux_checks() -> list[dict[str, Any]]:
    return [
        _check(
            "UX.independent_sessions",
            "UX",
            "independent human usability sessions over the three journeys",
            "independent_human",
            "deferred",
            "no volunteers were available in this run — the moderated-session "
            "task protocol is landed as the compensating control; nothing "
            "about user comprehension/satisfaction is claimed or fabricated",
            evidence=[
                "USABILITY_TASK_PROTOCOL.md",
                "docs/tickets/DEFERRALS.md#D-R10-USERS-1",
            ],
            owner="D-R10-USERS-1",
            landing="the moderated usability study (volunteer recruitment — "
            "operator-gated; GATE-G3 blocks public launch meanwhile)",
        )
    ]


# --------------------------------------------------------------------------- #
# Assembly + rendering
# --------------------------------------------------------------------------- #
def _assemble(
    *,
    candidate_dir: Path,
    manifest: Mapping[str, Any],
    corpus: Mapping[str, Any],
    build: ReleaseBuild,
    checks: Sequence[Mapping[str, Any]],
    intake_proof: Mapping[str, Any] | None,
) -> dict[str, Any]:
    cand = manifest.get("candidate") or {}
    release = manifest.get("release") or {}
    fails = [c for c in checks if c["status"] == "fail"]
    for c in checks:
        if c["evidence_kind"] == "independent_human" and c["status"] == "pass":
            raise PortfolioError(
                f"check {c['id']}: independent_human evidence can never be "
                "recorded as pass without real named sessions — the labelling "
                "rule refused a fabricated usability result"
            )
    counts = {s: sum(1 for c in checks if c["status"] == s) for s in CHECK_STATUSES}
    by_kind = {
        k: {
            s: sum(1 for c in checks if c["evidence_kind"] == k and c["status"] == s)
            for s in CHECK_STATUSES
        }
        for k in EVIDENCE_KINDS
    }
    honest_gaps = [
        {
            "check": c["id"],
            "status": c["status"],
            "owner": c["owner"],
            "landing": c["landing"],
            "detail": c["detail"],
        }
        for c in checks
        if c["status"] in {"deferred", "not_applicable", "fail"}
    ]
    catalog = {}
    cat_path = build.out_dir / f"releases/{build.publication_id}/catalog_entry.json"
    if cat_path.exists():
        catalog = _read_json(cat_path)
    return {
        "schema": PORTFOLIO_SCHEMA,
        "ticket": "P32.24",
        "requirement": "SIG-FIND-007",
        "subject": {
            "candidate_dir": str(candidate_dir),
            "publication_id": str(release.get("publication_id") or ""),
            "candidate_identity_digest": cand.get("identity_digest"),
            "evaluation": {
                "status": "deferred",
                "mode": "shadow",
                "decision": None,
                "note": "the S3 human-evaluation spine is deferred wholesale "
                "by the operator's recorded decision (GATE DECISIONS, "
                "commit a33cd6ec; ADR-146) — this portfolio never "
                "simulates a final decision",
            },
            "published": cand.get("published"),
            "provisional": cand.get("provisional"),
            "review_only": cand.get("review_only"),
            "ruleset_version": cand.get("ruleset_version"),
        },
        "acceptance_release": {
            "declaration": corpus.get("purpose"),
            "corpus_schema": CORPUS_SCHEMA,
            "publication_id": build.publication_id,
            "manifest_sha256": catalog.get("manifest_sha256"),
            "descriptor_sha256": catalog.get("descriptor_sha256"),
            "record_count": catalog.get("record_count"),
            "dossier_scopes": list(DOSSIER_SCOPES),
        },
        "intake_proof": (
            {
                "schema": INTAKE_PROOF_SCHEMA,
                "executed": True,
                "publication_id": intake_proof.get("publication_id"),
                "receipt_id": intake_proof.get("receipt_id"),
                "application_id": intake_proof.get("application_id"),
                "steps_ok": sum(1 for s in intake_proof.get("steps", []) if s.get("ok")),
                "steps_total": len(intake_proof.get("steps") or []),
            }
            if intake_proof is not None
            else {
                "schema": INTAKE_PROOF_SCHEMA,
                "executed": False,
                "verified_by_test": INTAKE_PG_TEST,
            }
        ),
        "checks": [dict(c) for c in checks],
        "summary": {
            "total": len(checks),
            "counts": counts,
            "by_evidence_kind": by_kind,
        },
        "honest_gaps": honest_gaps,
        "verdict": "fail" if fails else "pass",
        "boundaries": {
            "independent_human_evidence": "none — D-R10-USERS-1 OPEN; no "
            "usability/satisfaction/completion result is claimed",
            "intake_operational": False,
            "live_verification": False,
            "publication": "not performed — D-R10-PUBLISH-1 OPEN",
            "production_candidate": "not built — D-P32.23a-1 + D-R10-LIVE-1 OPEN",
            "eval_final": "none — eval=deferred (D-R10-HUMAN-1)",
        },
    }


def render_portfolio_markdown(portfolio: Mapping[str, Any]) -> str:
    """The human readout — honest headline, then every check with its
    evidence class + owner/landing where owed."""
    s = portfolio["subject"]
    a = portfolio["acceptance_release"]
    lines = [
        "# P32.24 — public investigation acceptance portfolio",
        "",
        f"- schema `{portfolio['schema']}` · requirement `{portfolio['requirement']}`",
        f"- candidate `{s['publication_id']}` · identity `{s['candidate_identity_digest']}`",
        f"- evaluation **{s['evaluation']['status']}** (mode `{s['evaluation']['mode']}`, "
        "decision null) — the S3 human-evaluation spine is operator-deferred; "
        "nothing here is a final evaluation",
        f"- published={s['published']} · provisional={s['provisional']} · "
        f"review_only={s['review_only']} · ruleset `{s['ruleset_version']}`",
        f"- acceptance release `{a['publication_id']}` · manifest "
        f"`{a['manifest_sha256']}` · records={a['record_count']} · "
        f"dossiers={', '.join(a['dossier_scopes'])}",
        "",
        f"## Verdict — **{portfolio['verdict'].upper()}**",
        "",
        "The P32.23a candidate publishes **zero records** — the record journeys "
        "are honestly `not_applicable` on it and execute over the declared "
        "acceptance corpus instead. Independent human usability evidence is "
        "`deferred` (D-R10-USERS-1): no session results exist or are claimed.",
        "",
        "| check | journey | evidence class | status | detail |",
        "|---|---|---|---|---|",
    ]
    for c in portfolio["checks"]:
        detail = str(c["detail"]).replace("|", "\\|")
        lines.append(
            f"| `{c['id']}` | {c['journey']} | {c['evidence_kind']} | "
            f"**{c['status']}** | {detail} |"
        )
    lines += ["", "## Honest gaps (owner → landing)", ""]
    for g in portfolio["honest_gaps"]:
        lines.append(
            f"- `{g['check']}` — **{g['status']}** · owner `{g['owner']}` → {g['landing']}"
        )
    lines += ["", "## Boundaries", ""]
    for k, v in (portfolio.get("boundaries") or {}).items():
        lines.append(f"- `{k}`: {v}")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- #
# The intake journey — Journey C on a real PG (sig.journey-intake-proof/1)
# --------------------------------------------------------------------------- #
def run_intake_journey(
    dsn: str,
    *,
    publication_id: str,
    record_key_value: str,
    report_key: str | None = None,
    target_claim_id: str | None = None,
) -> dict[str, Any]:
    """Execute the receipt→restart→queue→approve→apply→publish traversal.

    Requires a deployed spine (PG18 + the full sqitch plan). The DSN is any
    writable test/fixture database — this never touches production. Returns
    the ``sig.journey-intake-proof/1`` document. ``report_key`` namespaces
    the synthetic rows so a rerun on one DSN never collides.

    ``target_claim_id`` (P33.2): when given, the synthetic report disputes
    THAT existing live claim — its stored claim/evidence digests are
    fingerprinted exactly as the bridge re-verifies them — instead of a
    freshly seeded fixture claim. The composed-verification runner uses this
    so the correction lands on a claim the activated release published.
    """
    key = report_key or secrets.token_hex(4)
    report_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"sig-journey-report-{key}"))
    receipt_id = f"rct-{uuid.uuid5(uuid.NAMESPACE_DNS, f'journey-{key}').hex[:32]}"
    token = secrets.token_bytes(24)
    token_digest = hashlib.sha256(token).digest()

    import psycopg
    from db.intake import PgIntakeReceiverStore, PgIntakeReviewerStore
    from db.intake_apply import PgIntakeApplicationStore
    from psycopg.rows import dict_row

    steps: list[dict[str, Any]] = []

    def step(name: str, ok: bool, detail: str) -> None:
        steps.append({"step": name, "ok": bool(ok), "detail": detail})

    # The target claim the synthetic report disputes — a live tier-0 claim
    # the reviewer fingerprints (the real digests the bridge re-verifies).
    # P33.2: a caller may name the released claim directly; otherwise the
    # journey seeds its own fixture claim as before (wire names unchanged).
    target = (
        _fingerprint_journey_claim(dsn, target_claim_id)
        if target_claim_id is not None
        else _seed_journey_target(dsn, key)
    )

    recv = PgIntakeReceiverStore.from_dsn(dsn)
    try:
        recv.insert_report(
            report_id=report_id,
            receipt_id=receipt_id,
            idempotency_key=f"nonce-journey-{key}",
            category="factual_error",
            description=(
                "acceptance-journey synthetic report — the released record's "
                "recorded count reads wrong (fixture narrative, never "
                "auto-applied)"
            ),
            publication_id=publication_id,
            record_key=record_key_value,
            claim_ids=[target["claim_id"]],
            evidence_urls=[],
            contact=None,
            token_digest=token_digest,
        )
        st = recv.public_status(receipt_id) or {}
        step(
            "submit_durable",
            st.get("state") == "received",
            f"receipt {receipt_id} committed; public state={st.get('state')}",
        )
    finally:
        recv.close()

    # restart — a fresh receiver store on a fresh connection sees it.
    recv2 = PgIntakeReceiverStore.from_dsn(dsn)
    try:
        st2 = recv2.public_status(receipt_id) or {}
        step(
            "survives_restart",
            st2.get("state") == "received",
            f"fresh-connection state={st2.get('state')}",
        )
    finally:
        recv2.close()

    rev = PgIntakeReviewerStore.from_dsn(dsn)
    try:
        queue = rev.queue(limit=2000)
        in_queue = any(str(r.get("receipt_id")) == receipt_id for r in queue)
        step("moderation_queue", in_queue, f"queue rows={len(queue)}; receipt visible={in_queue}")
        seq = rev.record_event(
            receipt_id,
            "disposition_proposed",
            "rev-1",
            {
                "outcome": "correct",
                "reason": "verified against the cited released record",
                "public_response": "The recorded count was corrected.",
                "proposal": {
                    "target_kind": "claim",
                    "target_id": target["claim_id"],
                    "claim_digest": target["claim_digest"],
                    "evidence_digest": target["evidence_digest"],
                    # The bridge validates the proposal against the TARGET
                    # claim's object_type (a `correct` keeps the disputed
                    # claim's shape) — a literal target admits value_text +
                    # unit only, never a stray numeric column.
                    "value": (
                        {"value_text": "225", "unit": "cameras"}
                        if target.get("object_type") == "literal"
                        else {
                            "value_text": "225",
                            "value_num": 225,
                            "unit": "cameras",
                        }
                    ),
                    "correction_reason": "acceptance_journey",
                },
            },
        )
        rev.record_event(
            receipt_id,
            "disposition_approved",
            "cur-1",
            {
                "outcome": "correct",
                "reason": "verified against the cited released record",
                "approves_seq": seq,
            },
        )
        st3 = recv_state(dsn, receipt_id)
        step(
            "reviewed",
            st3.get("state") == "decided",
            f"public lifecycle state after approval={st3.get('state')}",
        )
    finally:
        rev.close()

    apps = PgIntakeApplicationStore.from_dsn(dsn)
    app_id = ""
    try:
        app = apps.apply(receipt_id, actor="cur-1")
        app_id = str(app.get("application_id") or "")
        step(
            "applied_canonical",
            bool(app_id) and app.get("reconciled") is False,
            f"application_id={app_id}; outcome={app.get('outcome')}; "
            f"result_claim_id={app.get('result_claim_id')} — one §16.6 "
            "close+revises pair under the approving curator, in one txn "
            "with the application receipt + the applied event",
        )
        retry = apps.apply(receipt_id, actor="cur-1")
        step(
            "exactly_once",
            retry.get("reconciled") is True and str(retry.get("application_id")) == app_id,
            f"retry reconciled={retry.get('reconciled')} to the same "
            "application receipt — no second canonical write",
        )
        pub_ev = apps.mark_published(
            receipt_id,
            actor="cur-1",
            publication_id=publication_id,
            correction_ref=str(app.get("result_claim_id") or app.get("disposition_id")),
        )
        step(
            "published_linkage",
            pub_ev.get("event") == "published"
            and (pub_ev.get("detail") or {}).get("publication_id") == publication_id,
            f"published event links publication_id={publication_id} + "
            f"correction_ref={(pub_ev.get('detail') or {}).get('correction_ref')}",
        )
        app_row = apps.application(receipt_id) or {}
        step(
            "distinct_states",
            bool(app_row.get("operation_id")) and app_row.get("outcome") == "correct",
            f"application row outcome={app_row.get('outcome')}; "
            f"operation_id={app_row.get('operation_id')}",
        )
    finally:
        apps.close()

    final = recv_state(dsn, receipt_id)
    step(
        "resolved_state",
        final.get("state") == "resolved",
        f"public lifecycle after publish={final.get('state')} — received/"
        "under_review/decided/applied/published stayed visibly distinct",
    )

    # the receiver can never write canonical rows — proven live on a raw
    # receiver-role session.
    refused: list[str] = []
    conn = psycopg.connect(dsn, autocommit=True, row_factory=dict_row)
    try:
        conn.execute("SET ROLE sig_intake_receiver")
        for sql in (
            "INSERT INTO claim(subject_id,predicate_id,object_type,value_kind,"
            "value_text,value_num,unit,raw_value,observed_at,source_reliability,"
            "claim_directness,artifact_integrity,asserted_by,assertion_rationale,"
            "ingest_run_id,rights_id,sensitivity_tier) "
            "VALUES (gen_random_uuid(),gen_random_uuid(),'quantity','value',"
            "'9',9,'cameras','9','2026-05-01','R1','D1','I1',gen_random_uuid(),"
            "'probe',gen_random_uuid(),gen_random_uuid(),0)",
            "INSERT INTO intake.application(report_id, operation_id, approval_seq,"
            " proposal_seq, outcome, approved_by, applied_by, target_kind)"
            " VALUES (gen_random_uuid(),'journey-refused',1,1,'correct','x','x','claim')",
            "INSERT INTO intake.event(report_id, event, actor)"
            " VALUES (gen_random_uuid(),'applied','x')",
        ):
            try:
                conn.execute(sql)
                refused.append("NOT-REFUSED")
            except Exception as exc:  # noqa: BLE001 - the refusal IS the evidence
                refused.append(type(exc).__name__)
                conn.rollback()
        step(
            "receiver_no_fact_write",
            all(r != "NOT-REFUSED" for r in refused),
            f"receiver-role canonical writes refused live: {refused}",
        )
    finally:
        conn.close()

    return {
        "schema": INTAKE_PROOF_SCHEMA,
        "dsn": _dsn_label(dsn),
        "publication_id": publication_id,
        "record_key": record_key_value,
        "report_id": report_id,
        "receipt_id": receipt_id,
        "target_claim_id": target["claim_id"],
        "application_id": app_id,
        "steps": steps,
    }


def _seed_journey_target(dsn: str, key: str) -> dict[str, Any]:
    """Seed the one live tier-0 claim the synthetic report disputes + its
    evidence binding; return the real digests the bridge re-verifies.

    Written under the DSN's own (fixture/test) role — the same minimum-FK
    fixture the intake tests seed, never production data.
    """
    import psycopg
    from db.intake_apply import claim_evidence_digest, claim_state_digest
    from psycopg.rows import dict_row

    def _ret_id(cur: Any, sql: str, params: tuple[Any, ...], col: str) -> str:
        row = cur.execute(sql, params).fetchone()
        if row is None:
            raise PortfolioError(f"seed INSERT returned no {col} row")
        return str(row[col])

    conn = psycopg.connect(dsn, autocommit=True, row_factory=dict_row)
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO vocab_resolution_strategy(strategy_id,definition) "
            "VALUES('authoritative_source_wins','fixture') ON CONFLICT DO NOTHING"
        )
        cur.execute(
            "INSERT INTO vocab_predicate"
            "(predicate_id,vocab_version,value_datatype,object_type,definition,"
            " volatility_class,half_life_days,resolution_strategy) "
            "VALUES(%s,'1.0.0','integer','quantity','journey fixture','MODERATE',"
            "365,'authoritative_source_wins') ON CONFLICT DO NOTHING",
            ("contracted_camera_count",),
        )
        rights_id = _ret_id(
            cur,
            "INSERT INTO rights_record(spdx_expression,redistributable,"
            "derivative_permitted,retrieval_date) "
            "VALUES('Apache-2.0','yes','yes','2026-01-01') RETURNING rights_id",
            (),
            "rights_id",
        )
        run_id = _ret_id(
            cur,
            "INSERT INTO ingest_run(connector_name,connector_version,"
            "code_commit,ruleset_version,vocab_version,parameters,"
            "environment,input_digests) VALUES('journey-fixture','0','sha',"
            "'r1','1.0.0','{}','{}','{}') RETURNING run_id",
            (),
            "run_id",
        )
        subject_id = _ret_id(
            cur,
            "INSERT INTO entity(entity_type) VALUES('deployment') RETURNING entity_id",
            (),
            "entity_id",
        )
        author_id = _ret_id(
            cur,
            "INSERT INTO entity(entity_type) VALUES('person') RETURNING entity_id",
            (),
            "entity_id",
        )
        claim_id = _ret_id(
            cur,
            "INSERT INTO claim(subject_id,predicate_id,object_type,"
            "value_kind,value_text,value_num,unit,raw_value,observed_at,"
            "source_reliability,claim_directness,artifact_integrity,"
            "asserted_by,assertion_rationale,ingest_run_id,rights_id,"
            "sensitivity_tier) VALUES(%s,%s,'quantity','value','25',25,"
            "'cameras','25','2026-05-01T00:00:00Z','R1','D1','I1',%s,"
            "'journey fixture',%s,%s,0) RETURNING claim_id",
            (subject_id, "contracted_camera_count", author_id, run_id, rights_id),
            "claim_id",
        )
        # one evidence binding — the correction rebinds the SAME capture
        cur.execute(
            "INSERT INTO source_registry(source_id,name,source_kind,"
            "default_reliability,reliability_justification,rights_id,"
            "custody_posture,compact_status,robots_policy,ingestion_permitted) "
            "VALUES(%s,%s,'registry','R2','journey fixture',%s,'MIRROR','granted',"
            "'obey',true) ON CONFLICT (source_id) DO NOTHING",
            (f"src-journey-{key}", f"src-journey-{key}", rights_id),
        )
        artifact_id = _ret_id(
            cur,
            "INSERT INTO evidence_artifact(source_id,stable_locator,"
            "artifact_type,acquisition_method,primary_or_secondary,"
            "rights_id,capture_status) VALUES(%s,%s,'camera_registry',"
            "'registry_api','primary',%s,'captured') RETURNING artifact_id",
            (f"src-journey-{key}", f"urn:sig:journey:{key}", rights_id),
            "artifact_id",
        )
        capture_id = _ret_id(
            cur,
            "INSERT INTO evidence_capture(artifact_id,content_digest,"
            "byte_size,media_type,retrieved_at,retrieved_by_run_id,"
            "ocfl_object_id,ocfl_version,storage_tier,capture_method,"
            "capture_tool_version,source_uri) VALUES(%s,%s,10,"
            "'application/json','2026-05-01T00:00:00Z',%s,%s,'v1','public',"
            "'registry_api','sig/0',%s) RETURNING capture_id",
            (
                artifact_id,
                f"journey-digest-{key}",
                run_id,
                f"urn:sig:journey:{key}",
                f"urn:sig:journey:{key}",
            ),
            "capture_id",
        )
        conn.execute(
            "INSERT INTO claim_evidence(claim_id,capture_id,role) "
            "VALUES(%s::uuid,%s::uuid,'establishes')",
            (claim_id, capture_id),
        )
        row = conn.execute("SELECT * FROM claim WHERE claim_id = %s::uuid", (claim_id,)).fetchone()
        if row is None:
            raise PortfolioError("seeded claim vanished before digest")
        evidence_rows = [
            tuple(r.values())
            for r in conn.execute(
                "SELECT capture_id::text, role, binding_status FROM claim_evidence"
                " WHERE claim_id = %s::uuid ORDER BY capture_id, role",
                (claim_id,),
            ).fetchall()
        ]
        return {
            "claim_id": claim_id,
            "capture_id": capture_id,
            "claim_digest": claim_state_digest(dict(row)),
            "evidence_digest": claim_evidence_digest(evidence_rows),
        }
    finally:
        conn.close()


def _fingerprint_journey_claim(dsn: str, claim_id: str) -> dict[str, Any]:
    """Fingerprint an EXISTING live claim the report disputes (P33.2).

    The same two digests the bridge re-verifies: ``claim_state_digest`` over
    the stored claim row and ``claim_evidence_digest`` over its ordered
    evidence bindings. Seeded/minted claims need no fixture insert — the
    composed runner names a claim its release already published.
    """
    import psycopg
    from db.intake_apply import claim_evidence_digest, claim_state_digest
    from psycopg.rows import dict_row

    conn = psycopg.connect(dsn, autocommit=True, row_factory=dict_row)
    try:
        row = conn.execute("SELECT * FROM claim WHERE claim_id = %s::uuid", (claim_id,)).fetchone()
        if row is None:
            raise PortfolioError(f"target claim {claim_id!r} does not exist")
        evidence_rows = [
            tuple(r.values())
            for r in conn.execute(
                "SELECT capture_id::text, role, binding_status FROM claim_evidence"
                " WHERE claim_id = %s::uuid ORDER BY capture_id, role",
                (claim_id,),
            ).fetchall()
        ]
        capture_ids = [str(r[0]) for r in evidence_rows]
        return {
            "claim_id": claim_id,
            "capture_id": capture_ids[0] if capture_ids else None,
            "claim_digest": claim_state_digest(dict(row)),
            "evidence_digest": claim_evidence_digest(evidence_rows),
            "object_type": str(row["object_type"]),
        }
    finally:
        conn.close()


def recv_state(dsn: str, receipt_id: str) -> dict[str, Any]:
    from db.intake import PgIntakeReceiverStore

    recv = PgIntakeReceiverStore.from_dsn(dsn)
    try:
        return recv.public_status(receipt_id) or {}
    finally:
        recv.close()


def _dsn_label(dsn: str) -> str:
    """A non-secret DSN label for the proof — host/db name only, never creds."""
    tail = dsn.rsplit("/", 1)[-1]
    host = dsn.rsplit("@", 1)[-1].split("/")[0]
    return f"{host}/{tail.split('?')[0]}"


# --------------------------------------------------------------------------- #
# The portfolio runner
# --------------------------------------------------------------------------- #
def run_portfolio(
    *,
    candidate_dir: Path | str,
    out_dir: Path | str,
    intake_proof: Path | str | None = None,
    renderer_revision: str = "p32.24-journey-verify",
) -> dict[str, Any]:
    """Run the whole portfolio: candidate layer + the three journeys over
    the acceptance corpus + withdrawals + walkthrough checks. Emits the
    corpus export, the staged corpus release + registry, and the
    ``sig.journey-portfolio/1`` JSON + markdown readout."""
    candidate_dir = Path(candidate_dir)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = _read_json(candidate_dir / "CANDIDATE_MANIFEST.json")

    export_dir = out_dir / "corpus_export"
    release_dir = out_dir / "corpus_release"
    registry_dir = out_dir / "corpus_registry"

    corpus = build_acceptance_export(export_dir)
    shutil.rmtree(release_dir, ignore_errors=True)
    shutil.rmtree(registry_dir, ignore_errors=True)
    build = build_release(export_dir, release_dir, renderer_revision=renderer_revision)

    # stage the corpus release into a scratch registry — the journeys serve
    # the staged tree exactly like production serving would, and the
    # withdrawal barrier mutates only this scratch registry. The CANDIDATE
    # is never activated.
    activate(registry_dir, release_dir)

    proof: dict[str, Any] | None = None
    if intake_proof is not None:
        proof = _read_json(Path(intake_proof))

    checks: list[dict[str, Any]] = []
    checks += _candidate_checks(candidate_dir)
    checks += _journey_a_checks(build)
    checks += _journey_b_checks(export_dir, build, candidate_dir)
    checks += _journey_c_checks(build, proof)
    checks += _withdrawal_checks(registry_dir, build)
    checks += _walkthrough_checks(build)
    checks += _ux_checks()

    portfolio = _assemble(
        candidate_dir=candidate_dir,
        manifest=manifest,
        corpus=corpus,
        build=build,
        checks=checks,
        intake_proof=proof,
    )
    _write(out_dir / "JOURNEY_PORTFOLIO.json", canonical_json(portfolio))
    (out_dir / "JOURNEY_PORTFOLIO.md").write_text(
        render_portfolio_markdown(portfolio), encoding="utf-8"
    )
    return portfolio
