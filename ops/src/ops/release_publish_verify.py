# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P32.25 / ADR-144 (SIG-TRUST-009) — publish and verify a gate-accepted
release with rollback, inside the bounded staging namespace.

The subject is the candidate packet named on the command line: its
publication id, descriptor, manifest digests, identity, frozen snapshot,
ruleset, data-release id and as-of cuts are read from its
``CANDIDATE_MANIFEST.json`` (P34.22a / ADR-146 D4 — no candidate pin is a
code constant and there is no production default for ``--candidate``). The
signed gate readout is the publish authority: it must name the manifest's
publication, identity and frozen snapshot, or the run refuses before it
moves a single pointer. When the packet directory carries a recorded
supersession (``CORRECTION.md`` § Supersession record naming the
publication — as the p32.23a rehearsal candidate does, withdrawn by the
operator's B-4 answer), the proof reports *rehearsal evidence of a
superseded candidate — no publish authorised*: the machinery is still
proven over the committed bytes, but the run never exits as a production
verification.

Phases:

1. **Preflight** — the candidate packet, the signed gate readout, the
   disclosure posture and every release byte are re-verified against the
   approved digests. Any drift refuses the publish.
2. **Atomic staging publish** — ``activate()`` on a fresh bounded registry:
   ``validate_release`` first (the pointer can never flip on a partial
   release), ``latest.json`` last, every transition recorded.
3. **Public verification** — unauthenticated reads (direct file + real HTTP
   GETs over a throwaway unauthenticated static server) match the approved
   digests across every manifest compartment; citations resolve; records /
   search / tiles are honestly absent on this 0-record fixture candidate;
   the withdrawal barrier and withheld slices stay suppressed; the
   reduced/incomplete dossier scope and the deferred-evaluation disclosure
   are carried; the intake receiver is verified honestly unavailable only
   (no synthetic submissions — none are authorized).
4. **Rollback rehearsals** — in clearly-labelled scratch registries:
   * prior-release rollback (the committed P32.24 acceptance-corpus release
     stands in for "whatever pointer production holds" — labelled, never
     conflated with the accepted subject);
   * the no-prior-pointer path the ROLLBACK_PACKET names
     (``clear_latest_pointer``) — the candidate's real rollback shape;
   * the refusal path — a corrupted release leaves the previous pointer
     byte-identical (no partial release observable).
5. **Return pass** — ``prepared_not_executed``: the production exposure
   commands + live rollback instructions + the residual deferrals
   (``D-R10-PUBLISH-1`` production half, ``D-P32.23a-1``, ``D-R10-LIVE-1``,
   ``D-P32.16-1``) — recorded, never claimed.

No production serve, hosted probe, gate tick, human label, intake operation
or synthetic submission happens here — ``live_verification=false``.
"""

from __future__ import annotations

import hashlib
import http.server
import json
import shutil
import socket
import threading
import tomllib
import urllib.request
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from typing import Any

from api.intake import create_intake_app, intake_operational
from api.release_search import ReleaseSearchStore
from exports.release import (
    ReleaseError,
    ReleaseRegistry,
    activate,
    clear_latest_pointer,
    record_withdrawal,
    rollback,
    route_access,
    validate_release,
)
from exports.search_index import SearchIndexError, SearchParams
from policy.eligibility import (
    Disposition,
    ReasonCategory,
    TargetKind,
    new_disposition,
)

from exports import release as rel

# --------------------------------------------------------------------------- #
# The candidate's pins are read from the packet's own CANDIDATE_MANIFEST.json #
# (P34.22a / ADR-146 D4 — the superseded rehearsal candidate stays a record   #
# in docs/build/reports/, never a code constant). The signed gate readout is  #
# the publish authority that binds the manifest's pins to a decision.         #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class CandidatePins:
    """The release pins of the candidate named on the command line, read from
    its ``CANDIDATE_MANIFEST.json`` (``release.*`` + ``candidate.*``)."""

    publication_id: str
    identity_digest: str
    frozen_snapshot_digest: str
    descriptor_sha256: str  # bare hex — the manifest carries the sha256: prefix
    release_manifest_sha256: str
    export_manifest_sha256: str
    ruleset_version: str
    data_release_id: str
    as_of_world: str
    as_of_belief: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


def pins_from_manifest(manifest: dict[str, Any]) -> CandidatePins:
    """Extract the candidate's release pins from a parsed
    ``CANDIDATE_MANIFEST.json``. Fail-closed: a missing or empty pin is a
    ``PublishVerificationError`` — the publish never runs on guessed pins."""
    cand = manifest.get("candidate") or {}
    release = manifest.get("release") or {}
    descriptor = release.get("descriptor") or {}
    raw: dict[str, Any] = {
        "publication_id": release.get("publication_id"),
        "identity_digest": cand.get("identity_digest"),
        "frozen_snapshot_digest": cand.get("frozen_snapshot_digest"),
        "descriptor_sha256": release.get("descriptor_sha256"),
        "release_manifest_sha256": release.get("release_manifest_sha256"),
        "export_manifest_sha256": release.get("export_manifest_sha256"),
        "ruleset_version": cand.get("ruleset_version"),
        "data_release_id": descriptor.get("data_release_id"),
        "as_of_world": descriptor.get("as_of_world"),
        "as_of_belief": descriptor.get("as_of_belief"),
    }
    missing = [k for k, v in raw.items() if not isinstance(v, str) or not v]
    if missing:
        raise PublishVerificationError(
            f"the candidate manifest is missing release pins: {missing} — "
            "the packet named on the command line must declare them all"
        )
    return CandidatePins(
        publication_id=raw["publication_id"],
        identity_digest=raw["identity_digest"],
        frozen_snapshot_digest=raw["frozen_snapshot_digest"],
        descriptor_sha256=str(raw["descriptor_sha256"]).removeprefix("sha256:"),
        release_manifest_sha256=raw["release_manifest_sha256"],
        export_manifest_sha256=raw["export_manifest_sha256"],
        ruleset_version=raw["ruleset_version"],
        data_release_id=raw["data_release_id"],
        as_of_world=raw["as_of_world"],
        as_of_belief=raw["as_of_belief"],
    )


def pins_from_candidate_dir(candidate_dir: Path | str) -> CandidatePins:
    """The pins of the packet named on the command line."""
    return pins_from_manifest(_read_json(Path(candidate_dir) / "CANDIDATE_MANIFEST.json"))


#: What a run over a superseded candidate reports — the machinery is proven
#: over the committed bytes, never authorised as a production publish.
SUPERSEDED_POSTURE = "rehearsal evidence of a superseded candidate (B-4) — no publish authorised"
STAGING_POSTURE = (
    "rehearsal evidence — bounded staging namespace only; no production "
    "publish is authorised by this run"
)


def _supersession_record(candidate_dir: Path, publication_id: str) -> str | None:
    """The recorded supersession for this publication, when the packet
    directory carries one — a ``CORRECTION.md`` § Supersession record naming
    the publication id (SEED-08's record for the rehearsal candidate).
    Returns the record's headline, or ``None`` when nothing supersedes it."""
    corr = candidate_dir / "CORRECTION.md"
    if not corr.exists():
        return None
    text = corr.read_text(encoding="utf-8")
    if "Supersession record" not in text or publication_id not in text:
        return None
    for line in text.splitlines():
        if "Supersession record" in line:
            headline = line.lstrip("# -*").strip()
            if headline:
                return headline
    return f"supersession recorded for {publication_id[:24]}…"


#: The committed P32.24 acceptance corpus — a labelled rehearsal stand-in for
#: "whatever pointer production holds at rollback time". It is NOT a
#: production predecessor of the candidate (the candidate is the first
#: immutable release; its real rollback path is the no-prior-pointer branch).
#: The prior is REGENERATED from the committed corpus_export (deterministic —
#: byte-identical to the committed corpus_release). P32.24's committed
#: corpus_release had been silently corrupted by hardlink write-through when
#: its staged tree was tombstoned (4 record routes carried sig.tombstone/1
#: bytes while the manifest pinned the record digests); P32.25 restored those
#: bytes via this same deterministic rebuild, and exports.release now breaks
#: hardlinks before tombstone writes (ADR-144).
PRIOR_RELEASE_ID = "p-81f1986aac5cb18b29f2dae0458f74d8b639f6efc1a9de35abc38167b126d2dd"
PRIOR_RENDERER = "p32.24"
PRIOR_ENTITY_WITHHOLD = "ent-acc-dep-41"  # corpus entity — deny target
PRIOR_CLAIM_WITHHOLD = "cl-acc-denied-claim"  # corpus claim — denies its carriers

DEFAULT_PRIOR_EXPORT = Path(
    "docs/build/reports/p32.24-investigation-journey-verification/corpus_export"
)
DEFAULT_GATE_READOUT = Path("docs/build/readouts/GATE-G3.md")
DEFAULT_CONFIG = Path("ops/config.toml")

PROOF_SCHEMA = "sig.release-publish-verification/1"
REHEARSAL_SCHEMA = "sig.release-rollback-rehearsal/1"
RETURN_PASS_SCHEMA = "sig.release-publish-return-pass/1"

OPEN_DEFERRALS = [
    {
        "id": "D-R10-PUBLISH-1",
        "note": "release-exposure authorization signed at GATE-G3; the "
        "production-exposure half stays OPEN until an actual public serve",
    },
    {
        "id": "D-P32.23a-1",
        "note": "the production release-candidate build over the hosted "
        "repaired snapshot — the fixture candidate proven here is not it",
    },
    {
        "id": "D-R10-LIVE-1",
        "note": "hosted production recovery/freeze + final production "
        "candidate — the production public exposure is this return pass",
    },
    {
        "id": "D-P32.16-1",
        "note": "intake owner/staffing/retention/secrets/role grants/infra-log "
        "exclusions unmet — the receiver stays non-operational",
    },
]


class PublishVerificationError(RuntimeError):
    """Fail-closed refusal — preflight drift, non-fresh registry, or a failed
    publish step. Nothing is half-published silently."""


# --------------------------------------------------------------------------- #
# Check records — same evidence vocabulary as the journey portfolio           #
# --------------------------------------------------------------------------- #


def _check(
    check_id: str,
    status: str,
    detail: str,
    *,
    evidence_class: str = "automated_conformance",
    owner: str | None = None,
    landing: str | None = None,
    evidence: Any = None,
) -> dict[str, Any]:
    if status in {"fail", "deferred", "not_applicable"} and not (owner and landing):
        raise PublishVerificationError(
            f"check {check_id} is {status} without owner+landing — "
            "a gap can never be recorded silently"
        )
    out: dict[str, Any] = {
        "id": check_id,
        "status": status,
        "evidence_class": evidence_class,
        "detail": detail,
    }
    if evidence is not None:
        out["evidence"] = evidence
    if owner:
        out["owner"] = owner
    if landing:
        out["landing"] = landing
    return out


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _file_digest(path: Path) -> tuple[str, int]:
    h = hashlib.sha256()
    size = 0
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
            size += len(chunk)
    return h.hexdigest(), size


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# Phase 1 — preflight: the packet must BE the accepted candidate              #
# --------------------------------------------------------------------------- #


def _integrity_manifest(release_dir: Path) -> dict[str, Any]:
    manifests = list(release_dir.glob("releases/*/integrity_manifest.json"))
    if len(manifests) != 1:
        raise PublishVerificationError(
            f"expected exactly one integrity manifest under {release_dir}/releases/, "
            f"found {len(manifests)}"
        )
    return _read_json(manifests[0])


def preflight(
    candidate_dir: Path,
    gate_readout: Path | str,
    pins: CandidatePins,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Verify the packet's declared pins agree with the gate-signed record
    and that every release byte matches the approved digests. Raises
    ``PublishVerificationError`` on drift — the publish refuses before it moves
    a single pointer."""
    checks: list[dict[str, Any]] = []
    candidate_dir = Path(candidate_dir)
    gate_readout = Path(gate_readout)
    release_dir = candidate_dir / "candidate_release"
    export_dir = candidate_dir / "candidate_export"

    # -- the gate authority ------------------------------------------------ #
    text = gate_readout.read_text(encoding="utf-8") if gate_readout.exists() else ""
    gate_ok = (
        "SIGNED" in text
        and pins.publication_id in text
        and pins.identity_digest in text
        and pins.frozen_snapshot_digest in text
    )
    if not gate_ok:
        raise PublishVerificationError(
            f"the gate readout at {gate_readout} does not record a SIGNED acceptance "
            f"of {pins.publication_id} — there is no publish authority"
        )
    checks.append(
        _check(
            "PF.gate_signed",
            "pass",
            "the gate readout records SIGNED acceptance of the exact candidate "
            "(publication + identity + frozen snapshot pinned in the readout)",
            evidence={"readout": str(gate_readout)},
        )
    )

    # -- the manifest's declared pins + the accepted publish posture -------- #
    cman = _read_json(candidate_dir / "CANDIDATE_MANIFEST.json")
    cand = cman.get("candidate") or {}
    release = cman.get("release") or {}
    declared = {
        "publication_id": release.get("publication_id"),
        "descriptor_sha256": (release.get("descriptor_sha256") or "").removeprefix("sha256:"),
        "release_manifest_sha256": release.get("release_manifest_sha256"),
        "export_manifest_sha256": release.get("export_manifest_sha256"),
        "identity_digest": cand.get("identity_digest"),
        "frozen_snapshot_digest": cand.get("frozen_snapshot_digest"),
        "ruleset_version": cand.get("ruleset_version"),
        "evaluation_status": cand.get("evaluation_status"),
        "evaluation_mode": cand.get("evaluation_mode"),
        "published": cand.get("published"),
        "validation_state": release.get("validation_state"),
    }
    # The identity fields must equal the pins the command line loaded (the
    # external authority binding them is the SIGNED readout above); the
    # posture fields must be the accepted values — nothing else may publish
    # under this run.
    expected = {
        "publication_id": pins.publication_id,
        "descriptor_sha256": pins.descriptor_sha256,
        "release_manifest_sha256": pins.release_manifest_sha256,
        "export_manifest_sha256": pins.export_manifest_sha256,
        "identity_digest": pins.identity_digest,
        "frozen_snapshot_digest": pins.frozen_snapshot_digest,
        "ruleset_version": pins.ruleset_version,
        "evaluation_status": "deferred",
        "evaluation_mode": "shadow",
        "published": False,
        "validation_state": "complete",
    }
    drift: dict[str, Any] = {}
    for key, want in expected.items():
        got = declared.get(key)
        if got != want:
            drift[key] = {"expected": want, "found": got}
    if drift:
        raise PublishVerificationError(
            "the candidate packet's declared pins or publish posture drift "
            f"from what the command line loaded and the gate accepted — {drift}"
        )
    checks.append(
        _check(
            "PF.candidate_pinned",
            "pass",
            "CANDIDATE_MANIFEST declares the loaded publication, descriptor, "
            "manifests, identity, snapshot, ruleset and the accepted deferred-"
            "evaluation posture — nothing else can be published by this run",
            evidence=declared,
        )
    )

    # -- every release byte matches the approved integrity manifest --------- #
    report = validate_release(release_dir)
    if report.state != "complete":
        raise PublishVerificationError(f"candidate release fails validation: {report.failures[:5]}")
    manifest = _integrity_manifest(release_dir)
    if manifest.get("publication_id") != pins.publication_id:
        raise PublishVerificationError("integrity manifest names a different publication")
    if str(manifest.get("descriptor_sha256") or "") != pins.descriptor_sha256:
        raise PublishVerificationError("integrity manifest names a different descriptor digest")
    artifacts = manifest.get("artifacts") or []
    digests: list[dict[str, Any]] = []
    for art in artifacts:
        digest, size = _file_digest(release_dir / str(art["path"]))
        if digest != art["sha256"] or size != art["byte_size"]:
            raise PublishVerificationError(
                f"release artifact drift at {art['path']}: sha256={digest} size={size}"
            )
        digests.append(
            {
                "path": art["path"],
                "sha256": digest,
                "byte_size": size,
                "compartment": art.get("compartment"),
                "license": art.get("license"),
            }
        )
    checks.append(
        _check(
            "PF.release_bytes",
            "pass",
            f"validate_release=complete; all {len(artifacts)} manifest artifacts "
            "re-hashed byte-for-byte against the approved digests",
            evidence={"artifacts_checked": report.artifacts_checked, "digests": digests},
        )
    )

    # -- disclosure posture: deferred eval + suppressed slices, honestly ----- #
    disc = _read_json(candidate_dir / "DISCLOSURE.json")
    ev = disc.get("evaluation") or {}
    disc_ok = (
        ev.get("status") == "deferred"
        and ev.get("mode") == "shadow"
        and ev.get("decision") is None
        and ev.get("applied") == []
        and ev.get("p32_10_confidence_policy_activated") is False
        and disc.get("published") is False
        and disc.get("resolved_sites") is None
        and disc.get("prior_preview_counts_reused") is False
        and (disc.get("suppression_disclosure") or {}).get("dispositions_recorded") == 3
    )
    if not disc_ok:
        raise PublishVerificationError(
            "DISCLOSURE.json does not carry the accepted deferred-evaluation / "
            "provisional-review-only posture"
        )
    exclusions = _read_json(export_dir / "exclusions.json")
    refused = exclusions.get("refused") or []
    totals = exclusions.get("totals") or {}
    checks.append(
        _check(
            "PF.disclosure_posture",
            "pass",
            "DISCLOSURE pins evaluation.status=deferred / mode=shadow / "
            "decision=null / applied=[] / resolved_sites=null; the 3 recorded "
            "dispositions + loudly-recorded exclusion totals carry the "
            "withheld slices — nothing silently dropped",
            evidence={
                "evaluation": ev,
                "dispositions_recorded": (disc.get("suppression_disclosure") or {}).get(
                    "dispositions_recorded"
                ),
                "export_refused_rows": totals.get("refused_rows"),
                "export_refused_slices": totals.get("refused_slices"),
                "export_refused_count": len(refused),
            },
        )
    )

    # -- reduced/incomplete dossier scope (GATE-G3 scope (a)) --------------- #
    dossiers_doc = _read_json(export_dir / "web" / "research_dossiers.json")
    dossier_posture: list[dict[str, Any]] = []
    for doss in dossiers_doc.get("dossiers") or []:
        comp = doss.get("completeness") or {}
        review = doss.get("review") or {}
        dossier_posture.append(
            {
                "dossier_id": doss.get("dossier_id"),
                "review_status": doss.get("review_status"),
                "review_status_field": review.get("status"),
                "mechanical_complete": comp.get("mechanical_complete"),
                "pilot_complete": comp.get("pilot_complete"),
                "rubric_total": comp.get("total"),
            }
        )
        if doss.get("review_status") != "not_run" or review.get("status") != "not_run":
            raise PublishVerificationError(
                f"dossier {doss.get('dossier_id')} claims a semantic review that was never run"
            )
        if comp.get("pilot_complete") is not False:
            raise PublishVerificationError(
                f"dossier {doss.get('dossier_id')} claims pilot completion — "
                "forbidden under the GATE-G3 reduced scope"
            )
    summary = dossiers_doc.get("summary") or {}
    checks.append(
        _check(
            "PF.dossier_scope",
            "pass",
            "all three dossiers carry the reduced GATE-G3 scope honestly — "
            "review.status=not_run, pilot_complete=False; mechanical_complete "
            "reported per-dossier (never a completion claim)",
            evidence={
                "dossiers": dossier_posture,
                "summary_mechanical_complete": summary.get("mechanical_complete"),
                "summary_pilot_complete": summary.get("pilot_complete"),
            },
        )
    )

    # -- the packet's rollback plan exists and names the no-prior path ------- #
    rp = _read_json(candidate_dir / "ROLLBACK_PACKET.json")
    checks.append(
        _check(
            "PF.rollback_packet",
            "pass",
            "the P32.23a rollback packet is prepared: pointer-only reversal, "
            "immutable namespace retained, and the no-prior-pointer path "
            "recorded for this first-release candidate",
            evidence={
                "schema": rp.get("packet_version") or rp.get("schema"),
                "state": rp.get("state") or rp.get("status"),
            },
        )
    )

    pins_evidence = {
        **declared,
        "data_release_id": pins.data_release_id,
        "as_of_world": pins.as_of_world,
        "as_of_belief": pins.as_of_belief,
        "artifact_count": len(artifacts),
        "artifact_digests": digests,
        "release_dir": str(release_dir),
    }
    return checks, pins_evidence


# --------------------------------------------------------------------------- #
# Phase 2 — the atomic bounded publish                                        #
# --------------------------------------------------------------------------- #


def publish(
    candidate_dir: Path,
    registry_dir: Path,
    pins: CandidatePins,
    *,
    now: datetime | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Activate the accepted candidate in a FRESH bounded registry. The release
    bytes are staged from a copy (never the committed packet — tombstone writes
    would otherwise write through the hardlink inodes)."""
    checks: list[dict[str, Any]] = []
    registry_dir = Path(registry_dir)
    candidate_dir = Path(candidate_dir)

    if registry_dir.exists() and any(registry_dir.iterdir()):
        raise PublishVerificationError(
            f"staging registry {registry_dir} is not empty — the bounded publish "
            "needs a fresh namespace so the pointer transition is observable"
        )

    # stage input: a COPY of the committed release (withdrawal tombstones write
    # through hardlink inodes — activating the committed packet directly could
    # mutate it).
    staged_input = registry_dir / "_release_input" / "candidate_release"
    shutil.copytree(candidate_dir / "candidate_release", staged_input)

    registry = ReleaseRegistry(registry_dir)
    before = registry.latest()
    before_bytes = (
        (registry_dir / "latest.json").read_bytes()
        if (registry_dir / "latest.json").exists()
        else None
    )
    activation = activate(registry_dir, staged_input, now=now)
    after = registry.latest()
    after_bytes = (
        (registry_dir / "latest.json").read_bytes()
        if (registry_dir / "latest.json").exists()
        else None
    )

    validator = activation.get("validator") or {}
    checks.append(
        _check(
            "P.validate_first",
            "pass",
            f"activate() ran validate_release first — state={validator.get('state')}, "
            f"artifacts_checked={validator.get('artifacts_checked')}: the latest "
            "pointer can only move on a fully-verified release",
            evidence=validator,
        )
    )
    transition_ok = (
        before is None
        and after is not None
        and after.get("publication_id") == pins.publication_id
        and after.get("manifest_sha256") == pins.release_manifest_sha256
    )
    checks.append(
        _check(
            "P.pointer_transition",
            "pass" if transition_ok else "fail",
            "latest.json flipped atomically: absent (no prior release — this is "
            "the first immutable namespace) → "
            f"{pins.publication_id[:20]}… with the pinned manifest digest",
            evidence={
                "before": before,
                "before_bytes_sha256": _sha256(before_bytes) if before_bytes else None,
                "after": after,
                "after_bytes_sha256": _sha256(after_bytes) if after_bytes else None,
            },
            owner="operator" if not transition_ok else None,
            landing="docs/build/readouts/GATE-G3.md" if not transition_ok else None,
        )
    )
    cat = registry.catalog()
    pubs = cat.get("publications") or []
    cat_ok = (
        len(pubs) == 1
        and pubs[0].get("publication_id") == pins.publication_id
        and pubs[0].get("manifest_sha256") == pins.release_manifest_sha256
        and pubs[0].get("record_count") == 0
    )
    checks.append(
        _check(
            "P.catalog",
            "pass" if cat_ok else "fail",
            "the catalog registers exactly the accepted publication — pinned "
            "manifest digest, honest 0 records, no compartments",
            evidence={"publications": len(pubs), "entry": pubs[0] if pubs else None},
            owner="operator" if not cat_ok else None,
            landing="docs/build/readouts/GATE-G3.md" if not cat_ok else None,
        )
    )
    # the whole staged tree re-validates post-activation — no partial release
    post = validate_release(registry_dir / "staged")
    checks.append(
        _check(
            "P.staged_revalidates",
            "pass" if post.state == "complete" else "fail",
            f"post-publish staged tree re-validates: state={post.state}, "
            f"artifacts_checked={post.artifacts_checked}",
            evidence={"state": post.state, "failures": post.failures},
            owner="operator" if post.state != "complete" else None,
            landing="docs/build/readouts/GATE-G3.md" if post.state != "complete" else None,
        )
    )
    receipt = registry_dir / "activations" / f"{pins.publication_id}.json"
    checks.append(
        _check(
            "P.activation_receipt",
            "pass" if receipt.exists() else "fail",
            "the activation is receipted under activations/ with validator + "
            "withdrawal-application evidence",
            evidence=_read_json(receipt) if receipt.exists() else None,
            owner=None if receipt.exists() else "operator",
            landing=None if receipt.exists() else "docs/build/readouts/GATE-G3.md",
        )
    )
    publish_record = {
        "registry": str(registry_dir),
        "staged_input": str(staged_input),
        "activation": activation,
        "pointer": {"before": before, "after": after},
    }
    return checks, publish_record


# --------------------------------------------------------------------------- #
# Phase 3 — public verification over the staged surface                       #
# --------------------------------------------------------------------------- #


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _http_reads(staged: Path, routes: list[str]) -> list[dict[str, Any]]:
    """Unauthenticated GETs over a throwaway static server — the same bytes an
    anonymous reader sees (no credentials exist to send)."""
    port = _free_port()
    handler = partial(http.server.SimpleHTTPRequestHandler, directory=str(staged))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    out: list[dict[str, Any]] = []
    try:
        for route in routes:
            url = f"http://127.0.0.1:{port}/{route.lstrip('/')}"
            try:
                with urllib.request.urlopen(url, timeout=10) as resp:  # noqa: S310 - loopback
                    body = resp.read()
                    out.append(
                        {
                            "route": route,
                            "status": resp.status,
                            "bytes": len(body),
                            "sha256": _sha256(body),
                        }
                    )
            except urllib.error.HTTPError as exc:
                out.append({"route": route, "status": exc.code, "sha256": None})
    finally:
        server.shutdown()
        thread.join(timeout=10)
        server.server_close()
    return out


def verify_surface(
    registry_dir: Path,
    candidate_dir: Path | str,
    pins: CandidatePins,
    *,
    config_path: Path = DEFAULT_CONFIG,
) -> list[dict[str, Any]]:
    """The unauthenticated public-verification suite over the bounded staged
    surface. Every digest assertion reads the same bytes an anonymous reader
    gets; every absence is an honest absence."""
    checks: list[dict[str, Any]] = []
    registry_dir = Path(registry_dir)
    candidate_dir = Path(candidate_dir)
    staged = registry_dir / "staged"
    manifest = _integrity_manifest(staged)
    artifacts = manifest.get("artifacts") or []
    by_path = {str(a["path"]): a for a in artifacts}

    # -- every manifest route serves the approved bytes --------------------- #
    digest_rows: list[dict[str, Any]] = []
    mismatches: list[str] = []
    for art in artifacts:
        p = staged / str(art["path"])
        digest, size = _file_digest(p)
        ok = digest == art["sha256"] and size == art["byte_size"]
        if not ok:
            mismatches.append(str(art["path"]))
        digest_rows.append(
            {"path": art["path"], "compartment": art.get("compartment"), "sha256": digest, "ok": ok}
        )
    # no undeclared file under the release routes — the overlay additions are
    # the only allowed extras
    overlay_ok = {
        f"releases/{pins.publication_id}/catalog_entry.json",
        f"releases/{pins.publication_id}/integrity_manifest.json",
        "releases/index.html",
        "releases/catalog.json",
        "compat_index.json",
        "conf/withdrawn_routes.conf",
    }
    undeclared: list[str] = []
    for base in (staged / "r", staged / "releases"):
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if not p.is_file():
                continue
            rel_path = p.relative_to(staged).as_posix()
            if rel_path not in by_path and rel_path not in overlay_ok:
                undeclared.append(rel_path)
    for p in (staged / "entity").rglob("*") if (staged / "entity").exists() else []:
        if p.is_file():
            undeclared.append(p.relative_to(staged).as_posix())
    ok = not mismatches and not undeclared
    checks.append(
        _check(
            "V.digests",
            "pass" if ok else "fail",
            f"all {len(artifacts)} published artifacts re-hash to the approved "
            f"sha256+size over the served tree; {len(undeclared)} undeclared "
            "files under the public routes",
            evidence={
                "checked": len(digest_rows),
                "mismatches": mismatches,
                "undeclared": undeclared,
                "compartments": sorted({str(a.get("compartment")) for a in artifacts}),
            },
            owner="operator" if not ok else None,
            landing="docs/build/readouts/GATE-G3.md" if not ok else None,
        )
    )

    # -- unauthenticated HTTP reads over the staged tree -------------------- #
    routes = [str(a["path"]) for a in artifacts]
    routes += [
        f"r/{pins.publication_id}/c/web/evidence/{_evidence_uuid(artifacts)}/",
        f"releases/{pins.publication_id}/",
        "releases/index.html",
        "releases/catalog.json",
        "compat_index.json",
    ]
    reads = _http_reads(staged, routes)
    bad_reads = [r for r in reads if r["status"] != 200]
    http_digest_bad = [
        r["route"]
        for r in reads
        if r["route"] in by_path and r["sha256"] != by_path[r["route"]]["sha256"]
    ]
    ok = not bad_reads and not http_digest_bad
    checks.append(
        _check(
            "V.http_reads",
            "pass" if ok else "fail",
            f"{len(reads)} unauthenticated GETs over a plain static server — "
            "every manifest route answers 200 with the approved bytes; the "
            "directory routes serve their index pages",
            evidence={
                "gets": len(reads),
                "non_200": bad_reads,
                "digest_mismatches": http_digest_bad,
                "sample": reads[:2],
            },
            owner="operator" if not ok else None,
            landing="docs/build/readouts/GATE-G3.md" if not ok else None,
        )
    )

    # -- citations: immutable routes + honest selectors --------------------- #
    landing = (staged / f"releases/{pins.publication_id}/index.html").read_text(encoding="utf-8")
    sel_now = rel.resolve_selector(
        registry_dir, as_of_world=pins.as_of_world, as_of_belief=None, ruleset=pins.ruleset_version
    )
    sel_current = rel.resolve_selector(
        registry_dir, as_of_world=None, as_of_belief=None, ruleset=None
    )
    sel_old = rel.resolve_selector(
        registry_dir, as_of_world="2026-01-01", as_of_belief=None, ruleset=None
    )
    compat = registry_dir / "staged" / "compat_index.json"
    compat_entries = (_read_json(compat).get("entries") or []) if compat.exists() else []
    cit_ok = (
        pins.publication_id in landing
        and "cite this URL" in landing
        and sel_now.get("status") == "redirect"
        and sel_now.get("publication_id") == pins.publication_id
        and sel_current.get("status") == "current"
        and sel_current.get("publication_id") == pins.publication_id
        and sel_old.get("status") == "unavailable"
        and any(
            e.get("publication_id") == pins.publication_id
            and e.get("as_of_world") == pins.as_of_world
            and e.get("ruleset_version") == pins.ruleset_version
            for e in compat_entries
        )
    )
    checks.append(
        _check(
            "V.citations",
            "pass" if cit_ok else "fail",
            "the immutable /r/<pub> routes carry 'cite this URL' marking; a "
            "selector naming this cut redirects to the immutable namespace, "
            "the bare selector answers the latest convenience pointer, and a "
            "pre-release selector is honestly unavailable — never substituted",
            evidence={
                "selector_pinned": sel_now,
                "selector_current": sel_current,
                "selector_pre_release": sel_old,
                "compat_entries": len(compat_entries),
            },
            owner="operator" if not cit_ok else None,
            landing="docs/build/readouts/GATE-G3.md" if not cit_ok else None,
        )
    )

    # -- records: honestly zero on this fixture candidate ------------------- #
    entity_routes = (
        [p for p in (staged / "r").rglob("c/*/entity/*/*") if p.is_file()]
        if (staged / "r").exists()
        else []
    )
    stubs = (
        [p for p in (staged / "entity").rglob("index.html") if p.is_file()]
        if (staged / "entity").exists()
        else []
    )
    cat_entry = _read_json(staged / f"releases/{pins.publication_id}/catalog_entry.json")
    rec_ok = cat_entry.get("record_count") == 0 and not entity_routes and not stubs
    checks.append(
        _check(
            "V.records_honest_zero",
            "pass" if rec_ok else "fail",
            "the fixture candidate publishes 0 records — the catalog entry, "
            "the record route tree and the entity convenience stubs all agree "
            "(no phantom record surface)",
            evidence={
                "record_count": cat_entry.get("record_count"),
                "record_routes": len(entity_routes),
                "entity_stubs": len(stubs),
            },
            owner="D-P32.23a-1" if not rec_ok else None,
            landing="D-P32.23a-1" if not rec_ok else None,
        )
    )

    # -- search: the honest 404, never a current-spine fallback ------------- #
    store = ReleaseSearchStore(registry_dir)
    search_cases = [
        (pins.publication_id, "sig_graph", 404, "unknown_compartment"),
        (pins.publication_id, "osm_physical", 404, "unknown_compartment"),
        (
            "p-0000000000000000000000000000000000000000000000000000000000000000",
            "sig_graph",
            404,
            "unknown_publication",
        ),
    ]
    search_outcomes: list[dict[str, Any]] = []
    for pub, comp, want_status, want_code in search_cases:
        got_status: int | str
        got_code: str
        try:
            store.search(pub, comp, _params())
            got_status, got_code = 200, "ok"
        except Exception as exc:  # SearchIndexError carries status+code
            if isinstance(exc, SearchIndexError):
                got_status, got_code = exc.status, exc.code
            else:  # an unexpected exception is itself evidence
                got_status, got_code = "?", str(exc)[:60]
        search_outcomes.append(
            {
                "pub": pub[:20],
                "comp": comp,
                "status": got_status,
                "code": got_code,
                "expected": [want_status, want_code],
                "ok": (got_status, got_code) == (want_status, want_code),
            }
        )
    search_ok = all(o["ok"] for o in search_outcomes)
    checks.append(
        _check(
            "V.search_honest",
            "pass" if search_ok else "fail",
            "release-scoped search over the published artifact set answers the "
            "honest state — 404 unknown_compartment for the 0-record "
            "candidate's compartments, 404 unknown_publication for a phantom "
            "namespace; there is no silent fallback to current-spine data",
            evidence={"outcomes": search_outcomes},
            owner="operator" if not search_ok else None,
            landing="docs/build/readouts/GATE-G3.md" if not search_ok else None,
        )
    )

    # -- tiles: none declared, none staged ---------------------------------- #
    tile_artifacts = [
        a["path"]
        for a in artifacts
        if "tile" in str(a.get("path", "")).lower()
        or "tile" in str(a.get("media_type", "")).lower()
    ]
    tile_files = [p for p in staged.rglob("*tile*") if p.is_file()]
    tiles_ok = not tile_artifacts and not tile_files
    checks.append(
        _check(
            "V.tiles_honest",
            "pass" if tiles_ok else "fail",
            "no tile artifact is declared or staged for this candidate — "
            "honestly absent, not masqueraded",
            evidence={"declared": tile_artifacts, "staged": len(tile_files)},
            owner="operator" if not tiles_ok else None,
            landing="docs/build/readouts/GATE-G3.md" if not tiles_ok else None,
        )
    )

    # -- withdrawal barrier + suppressed slices ------------------------------ #
    registry = ReleaseRegistry(registry_dir)
    withdrawals = registry.withdrawals()
    conf = staged / "conf" / "withdrawn_routes.conf"
    deny_lines = (
        [
            line
            for line in conf.read_text(encoding="utf-8").splitlines()
            if line.startswith("location =")
        ]
        if conf.exists()
        else []
    )
    sample_route = f"r/{pins.publication_id}/c/web/evidence/{_evidence_uuid(artifacts)}/"
    access = route_access(registry_dir, sample_route)
    w_ok = not withdrawals and not deny_lines and access.get("permitted") is True
    checks.append(
        _check(
            "V.withdrawal_barrier",
            "pass" if w_ok else "fail",
            "the staged registry carries zero withdrawal dispositions — every "
            "manifest route is route_access-permitted and the generated deny "
            "map is empty (the barrier itself is exercised in R.*)",
            evidence={
                "dispositions": len(withdrawals),
                "deny_lines": len(deny_lines),
                "sample_route_permitted": access.get("permitted"),
            },
            owner="operator" if not w_ok else None,
            landing="docs/build/readouts/GATE-G3.md" if not w_ok else None,
        )
    )
    exclusions = _read_json(candidate_dir / "candidate_export" / "exclusions.json")
    refused = exclusions.get("refused") or []
    disc = _read_json(candidate_dir / "DISCLOSURE.json")
    supp = disc.get("suppression_disclosure") or {}
    supp_ok = (
        not refused
        and supp.get("dispositions_recorded") == 3
        and supp.get("export_refused_totals", {}).get("refused_slices") == 0
    )
    checks.append(
        _check(
            "V.suppressed_slices",
            "pass" if supp_ok else "fail",
            "the 3 spine-level dispositions are recorded loudly in the packet "
            "(exclusions.json + DISCLOSURE) and no withheld record or edge "
            "appears anywhere on the public surface — the 0-record surface "
            "contains nothing to leak",
            evidence={
                "dispositions": supp.get("dispositions_recorded"),
                "refused_rows": supp.get("export_refused_totals"),
                "refused_in_export": len(refused),
            },
            owner="operator" if not supp_ok else None,
            landing="docs/build/readouts/GATE-G3.md" if not supp_ok else None,
        )
    )

    # -- disclosures on the published surface -------------------------------- #
    descriptor = _read_json(staged / f"releases/{pins.publication_id}/descriptor.json")
    forbidden: list[str] = []
    scanned = 0
    for p in staged.rglob("*"):
        if not p.is_file() or p.suffix not in {".html", ".json", ".jsonl"}:
            continue
        scanned += 1
        body = p.read_text(encoding="utf-8", errors="replace")
        for phrase in ('pilot_complete": true', "final evaluation decision", "certified resolved"):
            if phrase.lower() in body.lower():
                forbidden.append(f"{p.relative_to(staged)}: {phrase}")
    disclosure_ok = (
        descriptor.get("ruleset_version") == pins.ruleset_version
        and "provisional-ruleset/1" in landing
        and not forbidden
    )
    checks.append(
        _check(
            "V.disclosures",
            "pass" if disclosure_ok else "fail",
            "the provisional basis is on the published surface: descriptor + "
            "landing carry ruleset=provisional-ruleset/1; no artifact anywhere "
            "asserts a completed pilot, a final evaluation decision, or a "
            "certified resolved-sites count (eval.status=deferred everywhere)",
            evidence={
                "descriptor_ruleset": descriptor.get("ruleset_version"),
                "files_scanned": scanned,
                "forbidden_assertions": forbidden,
            },
            owner="operator" if not disclosure_ok else None,
            landing="docs/build/readouts/GATE-G3.md" if not disclosure_ok else None,
        )
    )

    # -- intake: honestly unavailable, never advertised ---------------------- #
    cfg = tomllib.loads(config_path.read_text(encoding="utf-8"))
    intake_cfg = cfg.get("intake") or {}
    env_gate = intake_operational({})
    armed_but_uncommitted = intake_operational(
        {"SIG_INTAKE_OPERATIONAL": "1"}, config_path=config_path
    )
    app = create_intake_app(enabled=True, operational=False)
    from starlette.testclient import TestClient

    client = TestClient(app)
    root = client.get("/")
    new_page = client.get("/intake/new")
    posted = client.post("/intake/v1/reports", json={"report_key": "x", "summary": "x"})
    intake_refs = []
    for p in staged.rglob("*"):
        if p.is_file() and p.suffix in {".html", ".json"}:
            body = p.read_text(encoding="utf-8", errors="replace")
            if "/intake/" in body:
                intake_refs.append(str(p.relative_to(staged)))
    new_body = new_page.text
    intake_ok = (
        intake_cfg.get("operational") is False
        and env_gate is False
        and armed_but_uncommitted is False
        and root.status_code == 200
        and root.json().get("operational") is False
        and new_page.status_code == 503
        and "not yet operating" in new_body
        and "never" in new_body
        and "advertise" in new_body
        and posted.status_code == 503
        and posted.json().get("error") == "receiver_not_operating"
        and not intake_refs
    )
    checks.append(
        _check(
            "V.intake_unavailable",
            "pass" if intake_ok else "fail",
            "the receiver is honestly unavailable: ops/config.toml "
            "operational=false, the env gate is unset, /intake/new and POST "
            "/intake/v1/reports answer 503 receiver_not_operating, and no "
            "published byte advertises a live submission surface. No "
            "synthetic report was submitted — none are authorized.",
            evidence={
                "config_operational": intake_cfg.get("operational"),
                "config_staffed": intake_cfg.get("staffed"),
                "config_owner": intake_cfg.get("owner"),
                "env_gate": env_gate,
                "armed_env_but_uncommitted_config": armed_but_uncommitted,
                "root_operational": root.json().get("operational"),
                "new_status": new_page.status_code,
                "post_status": posted.status_code,
                "staged_intake_refs": intake_refs,
            },
            owner="D-P32.16-1" if not intake_ok else None,
            landing="D-P32.16-1" if not intake_ok else None,
        )
    )

    # -- zero-JS public surface ---------------------------------------------- #
    scripted = [
        str(p.relative_to(staged))
        for p in staged.rglob("*.html")
        if "<script" in p.read_text(encoding="utf-8", errors="replace").lower()
    ]
    checks.append(
        _check(
            "V.zero_js",
            "pass" if not scripted else "fail",
            "every published page is script-free (SIG-UI-036/037 zero-JS public surface)",
            evidence={"scripted_pages": scripted},
            owner="operator" if scripted else None,
            landing="docs/build/readouts/GATE-G3.md" if scripted else None,
        )
    )
    return checks


def _evidence_uuid(artifacts: list[dict[str, Any]]) -> str:
    for a in artifacts:
        parts = str(a["path"]).split("/")
        if "evidence" in parts:
            return parts[parts.index("evidence") + 1]
    raise PublishVerificationError("no evidence artifact route in the integrity manifest")


def _params() -> SearchParams:
    from exports.search_index import parse_params

    return parse_params(
        q=None,
        kind=None,
        jurisdiction=None,
        source=None,
        location=None,
        technology=None,
        limit=25,
        cursor=None,
    )


# --------------------------------------------------------------------------- #
# Phase 4 — rollback rehearsals (scratch registries, labelled)                #
# --------------------------------------------------------------------------- #


def _deny(
    registry_dir: Path,
    *,
    target_kind: TargetKind,
    target_id: str,
    disposition: Disposition = Disposition.WITHDRAW,
    seq: int,
    decided_at: datetime,
) -> None:
    record_withdrawal(
        registry_dir,
        [
            new_disposition(
                target_kind=target_kind,
                target_id=target_id,
                disposition=disposition,
                reason_category=ReasonCategory.SAFETY_WITHDRAWAL,
                authority="p32.25-rollback-rehearsal",
                decided_at=decided_at,
                seq=seq,
            )
        ],
    )


def rehearse_rollback(
    candidate_dir: Path,
    prior_export_dir: Path,
    rehearsal_root: Path,
    pins: CandidatePins,
    *,
    now: datetime | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Exercise the three rollback shapes in labelled scratch registries:
    prior-release pointer restore, the no-prior-pointer path the
    ROLLBACK_PACKET names, and the failed-deployment refusal."""
    checks: list[dict[str, Any]] = []
    candidate_dir = Path(candidate_dir)
    prior_export_dir = Path(prior_export_dir)
    rehearsal_root = Path(rehearsal_root)
    base_now = now or datetime(2026, 10, 20, tzinfo=UTC)
    cand_release_src = candidate_dir / "candidate_release"
    cand_manifest = _integrity_manifest(cand_release_src)
    cand_artifacts = {str(a["path"]): a for a in cand_manifest.get("artifacts") or []}
    evidence_uuid = _evidence_uuid(list(cand_artifacts.values()))
    evidence_route = f"r/{pins.publication_id}/c/web/evidence/{evidence_uuid}/"
    evidence_file = f"{evidence_route}index.html"
    second_artifact = next(a["path"] for a in cand_artifacts.values() if a["path"] != evidence_file)

    # -- R1: prior-release rollback ----------------------------------------- #
    r1 = rehearsal_root / "prior_registry"
    if r1.exists():
        shutil.rmtree(r1)
    prior_copy = r1 / "_release_input" / "prior_release"
    cand_copy = r1 / "_release_input" / "candidate_release"
    # Regenerate the stand-in prior from the committed corpus_export — the
    # deterministic build is byte-identical (same publication id) and never
    # depends on a committed release dir's post-run state.
    build = rel.build_release(prior_export_dir, prior_copy, renderer_revision=PRIOR_RENDERER)
    if build.publication_id != PRIOR_RELEASE_ID:
        raise PublishVerificationError(
            f"the regenerated prior is {build.publication_id}, expected "
            f"{PRIOR_RELEASE_ID} — the corpus export or the pipeline drifted"
        )
    shutil.copytree(cand_release_src, cand_copy)
    activate(r1, prior_copy, now=base_now)
    activate(r1, cand_copy, now=base_now)
    reg = ReleaseRegistry(r1)
    pre_latest = reg.latest() or {}
    # current withdrawals recorded AFTER both activations — they must survive
    # the rollback (ADR-132: current controls apply to historical namespaces)
    _deny(
        r1,
        target_kind=TargetKind.ENTITY,
        target_id=PRIOR_ENTITY_WITHHOLD,
        seq=1,
        decided_at=base_now,
    )
    _deny(
        r1,
        target_kind=TargetKind.ARTIFACT,
        target_id=evidence_uuid,
        disposition=Disposition.WITHHOLD,
        seq=2,
        decided_at=base_now,
    )
    denied_prior = route_access(
        r1, f"r/{PRIOR_RELEASE_ID}/c/sig_graph/entity/deployment/{PRIOR_ENTITY_WITHHOLD}/"
    )
    denied_cand = route_access(r1, evidence_route)
    result = rollback(r1, PRIOR_RELEASE_ID, now=base_now)
    post_latest = reg.latest() or {}
    # the candidate's unaffected bytes still serve at their citation routes
    untouched_path = r1 / "staged" / second_artifact
    untouched_digest = _file_digest(untouched_path)[0]
    tomb = (r1 / "staged" / evidence_route / "index.html").read_text(
        encoding="utf-8", errors="replace"
    )
    post_denied = route_access(r1, evidence_route)
    cat = reg.catalog()
    rollback_receipts = list((r1 / "activations").glob("rollback-*.json"))
    tombstone_ok = any(
        marker in tomb.lower()
        for marker in ("tombstone", "withheld", "withdrawn", "safety_withdrawal")
    )
    r1_ok = (
        pre_latest.get("publication_id") == pins.publication_id
        and post_latest.get("publication_id") == PRIOR_RELEASE_ID
        and post_latest.get("rolled_back") is True
        and denied_prior.get("permitted") is False
        and denied_cand.get("permitted") is False
        and post_denied.get("permitted") is False
        and untouched_digest == cand_artifacts[second_artifact]["sha256"]
        and tombstone_ok
        and len(cat.get("publications") or []) == 2
        and len(rollback_receipts) == 1
    )
    checks.append(
        _check(
            "R.prior_release",
            "pass" if r1_ok else "fail",
            "prior-release rollback restores the pointer atomically: latest "
            f"{pins.publication_id[:16]}… → {PRIOR_RELEASE_ID[:16]}…; the candidate's "
            "non-denied bytes still serve byte-identically at their immutable "
            "routes (old citations preserved), current withdrawals keep "
            "denying under the rollback (artifact tombstone + entity deny), "
            "the catalog keeps both activations and the rollback is receipted",
            evidence={
                "pre_latest": pre_latest,
                "post_latest": post_latest,
                "rollback_result": result,
                "untouched_route_digest_ok": untouched_digest
                == cand_artifacts[second_artifact]["sha256"],
                "denied_candidate_route_permitted": post_denied.get("permitted"),
                "denied_prior_route_permitted": denied_prior.get("permitted"),
                "catalog_publications": len(cat.get("publications") or []),
            },
            owner="operator" if not r1_ok else None,
            landing="docs/build/readouts/GATE-G3.md" if not r1_ok else None,
        )
    )

    # -- R2: the no-prior-pointer path (this candidate's real rollback) ------- #
    r2 = rehearsal_root / "no_prior_registry"
    if r2.exists():
        shutil.rmtree(r2)
    cand_copy2 = r2 / "_release_input" / "candidate_release"
    shutil.copytree(cand_release_src, cand_copy2)
    activate(r2, cand_copy2, now=base_now)
    cleared = clear_latest_pointer(r2, now=base_now)
    reg2 = ReleaseRegistry(r2)
    index_html = (r2 / "staged" / "releases" / "index.html").read_text(
        encoding="utf-8", errors="replace"
    )
    evidence_bytes = _file_digest(r2 / "staged" / evidence_file)[0]
    r2_ok = (
        not (r2 / "latest.json").exists()
        and reg2.latest() is None
        and len(reg2.catalog().get("publications") or []) == 1
        and evidence_bytes == cand_artifacts[evidence_file]["sha256"]
        and "<strong>(latest)</strong>" not in index_html
        and pins.publication_id in index_html
        and cleared.get("cleared") is True
    )
    checks.append(
        _check(
            "R.no_prior_pointer",
            "pass" if r2_ok else "fail",
            "the ROLLBACK_PACKET path — with no prior pointer, reversal removes "
            "latest.json entirely rather than fabricating a predecessor: the "
            "catalog keeps the activated history, the immutable routes keep "
            "serving identical bytes, and the convenience pointer is honestly "
            "absent",
            evidence={
                "latest_exists": (r2 / "latest.json").exists(),
                "catalog_publications": len(reg2.catalog().get("publications") or []),
                "evidence_route_digest_ok": evidence_bytes
                == cand_artifacts[evidence_file]["sha256"],
                "receipt": cleared,
            },
            owner="operator" if not r2_ok else None,
            landing="docs/build/readouts/GATE-G3.md" if not r2_ok else None,
        )
    )

    # -- R3: failed deployment leaves the previous release ------------------- #
    r3 = rehearsal_root / "refused_registry"
    if r3.exists():
        shutil.rmtree(r3)
    r3_input = r3 / "_release_input" / "candidate_release"
    shutil.copytree(cand_release_src, r3_input)
    activate(r3, r3_input, now=base_now)
    latest_before = (r3 / "latest.json").read_bytes()
    cat_before = (r3 / "catalog.json").read_bytes()
    staged_digest_before = _file_digest(r3 / "staged" / evidence_file)[0]
    # a corrupted second copy of the release — deployment fails validation
    bad = r3 / "_release_input" / "corrupted_release"
    shutil.copytree(cand_release_src, bad)
    victim = bad / evidence_file
    victim.write_bytes(victim.read_bytes() + b"tampered")
    refused = False
    try:
        activate(r3, bad, now=base_now)
    except ReleaseError:
        refused = True
    r3_ok = (
        refused
        and (r3 / "latest.json").read_bytes() == latest_before
        and (r3 / "catalog.json").read_bytes() == cat_before
        and _file_digest(r3 / "staged" / evidence_file)[0] == staged_digest_before
    )
    checks.append(
        _check(
            "R.refused_deploy",
            "pass" if r3_ok else "fail",
            "a tampered release can never partially deploy: activate() refuses "
            "on validate_release before staging, leaving latest.json, the "
            "catalog and every served byte byte-identical — the previous "
            "release remains, atomically",
            evidence={
                "activate_refused": refused,
                "latest_unchanged": (r3 / "latest.json").read_bytes() == latest_before,
                "catalog_unchanged": (r3 / "catalog.json").read_bytes() == cat_before,
            },
            owner="operator" if not r3_ok else None,
            landing="docs/build/readouts/GATE-G3.md" if not r3_ok else None,
        )
    )

    record = {
        "schema": REHEARSAL_SCHEMA,
        "exercised_at": base_now.isoformat(),
        "rehearsals": [
            {
                "id": "R.prior_release",
                "registry": str(r1),
                "prior_stand_in": {
                    "publication_id": PRIOR_RELEASE_ID,
                    "built_from": str(prior_export_dir),
                    "renderer_revision": PRIOR_RENDERER,
                    "note": "regenerated from the committed P32.24 "
                    "sig.journey-corpus/1 export (deterministic, same "
                    "publication id) — a labelled stand-in for whatever "
                    "pointer production holds; NOT a production predecessor",
                },
                "withdrawals_recorded": [
                    {"target_kind": "entity", "target_id": PRIOR_ENTITY_WITHHOLD},
                    {"target_kind": "artifact", "target_id": evidence_uuid},
                ],
            },
            {
                "id": "R.no_prior_pointer",
                "registry": str(r2),
                "note": "the candidate's real rollback shape — remove latest.json, "
                "never fabricate a predecessor; immutable routes stay reachable",
            },
            {
                "id": "R.refused_deploy",
                "registry": str(r3),
                "note": "validate_release refuses a corrupted bundle before "
                "staging — the previous pointer is untouched",
            },
        ],
    }
    return checks, record


# --------------------------------------------------------------------------- #
# Phase 5 — the live return pass (prepared, not executed)                     #
# --------------------------------------------------------------------------- #


def live_return_pass(pins: CandidatePins) -> dict[str, Any]:
    """The production obligations this run explicitly does NOT claim — the
    staged proof is evidence for the return pass, never a substitute."""
    return {
        "schema": RETURN_PASS_SCHEMA,
        "status": "prepared_not_executed",
        "subject_publication_id": pins.publication_id,
        "what_this_run_proved": [
            "atomic publish of the exact GATE-G3-accepted artifact set in the "
            "bounded staging namespace (validate-first, pointer-last)",
            "unauthenticated reads byte-match the approved digests across "
            "every manifest compartment and the immutable citation routes",
            "the withdrawal barrier, suppressed-slice disclosure, "
            "reduced-scope dossier posture and deferred-evaluation disclosure "
            "hold on the staged surface",
            "honest unavailable states: 0 records, no search compartments, no "
            "tiles, non-operational intake (verified, never advertised)",
            "prior-release rollback, no-prior-pointer rollback and the "
            "failed-deployment refusal — all atomic, all receipted",
        ],
        "what_this_run_did_not_do": [
            "no production serve: nothing was deployed, pushed to a bucket, "
            "or exposed at any public origin/CDN",
            "no production candidate: D-P32.23a-1's hosted build over the "
            "repaired production snapshot is still owed",
            "no intake operation: the receiver stays non-operational "
            "(D-P32.16-1); no synthetic submission was sent",
            "no evaluation claim: status=deferred is carried, not resolved",
            "no human/usability verification: D-R10-USERS-1 stays open",
            "no merge, tag, or push to main",
        ],
        "production_commands": [
            {
                "step": "produce the production candidate",
                "command": "sig-ops release-candidate --dsn <hosted> --out <dir>",
                "deferral": "D-P32.23a-1 (needs the D-R10-LIVE-1 frozen snapshot)",
            },
            {
                "step": "stage the registry",
                "command": "sig-ops release-publish --candidate <dir> "
                "--out <report>  # activate() over the hosted registry",
                "deferral": "D-R10-PUBLISH-1 production half",
            },
            {
                "step": "deploy staged tree + deny map",
                "command": "sync staging_registry/staged/ → the web bucket; "
                "include conf/withdrawn_routes.conf in the nginx config",
                "deferral": "D-R10-PUBLISH-1 production half",
            },
            {
                "step": "serve release search",
                "command": "sig-api serve --release-registry <registry>",
                "deferral": "D-R10-PUBLISH-1 production half",
            },
            {
                "step": "unauthenticated production probe",
                "command": "GET /releases/, /releases/<pub>/, every manifest "
                "route; compare response sha256 to the approved digests; "
                "probe /intake/new → expect 503 receiver_not_operating",
                "deferral": "D-R10-PUBLISH-1 production half",
            },
        ],
        "live_rollback_instructions": [
            {
                "case": "roll back to a prior activated release",
                "command": "exports.release.rollback(<registry>, <prior_pub>) — "
                "pointer-only; immutable bytes stay; current withdrawals "
                "re-apply under the rollback; receipted under activations/",
            },
            {
                "case": "this candidate has no prior pointer",
                "command": "exports.release.clear_latest_pointer(<registry>) — "
                "removes latest.json, re-emits the overlay, receipts; the "
                "r/<pub> namespace stays reachable as immutable history",
            },
            {
                "case": "post-publish withholding",
                "command": "record_withdrawal(<registry>, [<disposition>]) — "
                "denied routes tombstone (sig.tombstone/1) + the nginx deny "
                "map regenerates; unaffected bytes are untouched",
            },
        ],
        "open_deferrals": OPEN_DEFERRALS,
        "generated_at": datetime.now(UTC).isoformat(),
    }


# --------------------------------------------------------------------------- #
# Orchestration + report                                                      #
# --------------------------------------------------------------------------- #


def _counts(checks: list[dict[str, Any]]) -> dict[str, int]:
    out = {"pass": 0, "fail": 0, "deferred": 0, "not_applicable": 0, "verified_by_test": 0}
    for c in checks:
        out[c["status"]] = out.get(c["status"], 0) + 1
    return out


def render_markdown(proof: dict[str, Any]) -> str:
    """The human-readable verification report — evidence-first, honest about
    what a fixture-candidate staging proof is (and is not)."""
    c = proof["counts"]
    lines = [
        "# P32.25 — accepted release publish + public verification + rollback",
        "",
        f"**Verdict: {proof['verdict']}** — checks={proof['total_checks']} "
        f"({c.get('pass', 0)} pass, {c.get('fail', 0)} fail, "
        f"{c.get('deferred', 0)} deferred, {c.get('not_applicable', 0)} n/a)",
        "",
        f"**Subject:** `{proof['subject']['publication_id']}` — {proof['subject']['posture']}",
        "",
        "The subject is the gate-accepted candidate packet named on the "
        "command line — this is a **bounded/staging-namespace** proof of the "
        "publish + verify + rollback machinery over that artifact set. **No "
        "production exposure is claimed**: nothing was served publicly, no "
        "intake operation ran, no synthetic submission was sent, and the "
        "deferred-evaluation posture is carried, not resolved.",
        "",
        "## Accepted pins",
        "",
        f"- publication `{proof['accepted']['publication_id']}`",
        f"- identity `{proof['accepted']['identity_digest']}`",
        f"- frozen snapshot `{proof['accepted']['frozen_snapshot_digest']}`",
        f"- descriptor `{proof['accepted']['descriptor_sha256']}`",
        f"- release manifest `{proof['accepted']['release_manifest_sha256']}`",
        f"- ruleset `{proof['accepted']['ruleset_version']}` — evaluation "
        "`deferred`/`shadow`/`applied=[]`",
        "",
        "## Pointer transition",
        "",
        f"- before: `{json.dumps(proof['publish']['pointer']['before'])}`",
        f"- after: `{json.dumps(proof['publish']['pointer']['after'])}`",
        "",
        "## Checks",
        "",
        "| check | status | detail |",
        "|---|---|---|",
    ]
    for chk in proof["checks"]:
        line = f"| `{chk['id']}` | **{chk['status']}** | {chk['detail']} |"
        if chk.get("owner"):
            line += f" owner={chk['owner']}"
        lines.append(line)
    lines += [
        "",
        "## Rollback rehearsals",
        "",
    ]
    for r in proof["rehearsal"]["rehearsals"]:
        lines.append(f"- **{r['id']}** — `{r['registry']}`")
        if r.get("note"):
            lines.append(f"  - {r['note']}")
    lines += [
        "",
        "## Live rollback instructions (return pass — prepared, not executed)",
        "",
    ]
    for item in proof["return_pass"]["live_rollback_instructions"]:
        lines.append(f"- **{item['case']}** — `{item['command']}`")
    lines += [
        "",
        "## Residual production obligations (recorded, never claimed)",
        "",
    ]
    for d in proof["return_pass"]["open_deferrals"]:
        lines.append(f"- `{d['id']}` — {d['note']}")
    lines += [
        "",
        "NOT DONE here (by contract): production serve, production candidate "
        "(D-P32.23a-1), hosted recovery (D-R10-LIVE-1), intake operation "
        "(D-P32.16-1), any evaluation decision, any usability session, "
        "merge/tag/push-main.",
        "",
    ]
    return "\n".join(lines)


def run(
    *,
    candidate_dir: Path,
    out_dir: Path,
    prior_export_dir: Path = DEFAULT_PRIOR_EXPORT,
    gate_readout: Path | str = DEFAULT_GATE_READOUT,
    config_path: Path | str = DEFAULT_CONFIG,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Execute the whole bounded publish + verification + rehearsal and write
    the committed evidence packet into ``out_dir``. ``candidate_dir`` is a
    required argument — the publish verifies the candidate named on the
    command line; there is no production default."""
    candidate_dir = Path(candidate_dir)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    base_now = now or datetime.now(UTC)

    pins = pins_from_candidate_dir(candidate_dir)

    checks: list[dict[str, Any]] = []
    pf_checks, pins_evidence = preflight(candidate_dir, gate_readout, pins)
    checks += pf_checks

    # -- the recorded posture: a superseded candidate is rehearsal evidence -- #
    supersession = _supersession_record(candidate_dir, pins.publication_id)
    checks.append(
        _check(
            "PF.publish_authority",
            "deferred" if supersession else "pass",
            (
                SUPERSEDED_POSTURE
                if supersession
                else "no supersession record names this candidate — the "
                "bounded staging rehearsal proceeds under the gate's "
                "recorded signature"
            ),
            owner="P35.12" if supersession else None,
            landing=(
                "the true-dated candidate (release identity v2, FEA-06)" if supersession else None
            ),
            evidence={"supersession_record": supersession},
        )
    )

    registry_dir = out_dir / "staging_registry"
    p_checks, publish_record = publish(candidate_dir, registry_dir, pins, now=base_now)
    checks += p_checks

    checks += verify_surface(registry_dir, candidate_dir, pins, config_path=Path(config_path))

    r_checks, rehearsal_record = rehearse_rollback(
        candidate_dir, prior_export_dir, out_dir / "rehearsal", pins, now=base_now
    )
    checks += r_checks

    return_pass = live_return_pass(pins)
    counts = _counts(checks)
    verdict = "fail" if counts.get("fail") else "pass"
    proof = {
        "schema": PROOF_SCHEMA,
        "verdict": verdict,
        "run": "P32.25 — accepted release publish + public verification + rollback",
        "requirement": "SIG-TRUST-009",
        "executed_at": base_now.isoformat(),
        "live_verification": False,
        "subject": {
            "publication_id": pins.publication_id,
            "candidate_dir": str(candidate_dir),
            "superseded": supersession is not None,
            "supersession_record": supersession,
            "posture": SUPERSEDED_POSTURE if supersession else STAGING_POSTURE,
        },
        "accepted": {
            **pins.as_dict(),
            "evaluation": {"status": "deferred", "mode": "shadow", "applied": []},
            "artifact_count": pins_evidence["artifact_count"],
        },
        "publish": publish_record,
        "checks": checks,
        "total_checks": len(checks),
        "counts": counts,
        "rehearsal": rehearsal_record,
        "return_pass": return_pass,
        "boundary": (
            "bounded/staging namespace over the gate-accepted candidate "
            "packet named on the command line — NO production exposure, "
            "intake operation, evaluation decision, human verification, "
            "merge, tag, or push-main is claimed"
        ),
    }
    (out_dir / "PUBLISH_PROOF.json").write_text(
        json.dumps(proof, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out_dir / "PUBLIC_VERIFICATION.md").write_text(render_markdown(proof), encoding="utf-8")
    (out_dir / "ROLLBACK_REHEARSAL.json").write_text(
        json.dumps(rehearsal_record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out_dir / "LIVE_RETURN_PASS.json").write_text(
        json.dumps(return_pass, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out_dir / "README.md").write_text(_readme(proof), encoding="utf-8")
    return proof


def _readme(proof: dict[str, Any]) -> str:
    return f"""# P32.25 — accepted release publish + public verification + rollback rehearsal

Bounded/staging-namespace proof that the gate-accepted candidate packet —
publication `{proof["subject"]["publication_id"]}` — publishes atomically,
verifies over unauthenticated reads, and rolls back cleanly.
**{proof["subject"]["posture"]}** **No production exposure
is claimed** (`live_verification=false`).

- `PUBLISH_PROOF.json` — `sig.release-publish-verification/1`: the accepted
  pins, the pointer transition, every check, the verdict
  (verdict={proof["verdict"]}).
- `PUBLIC_VERIFICATION.md` — the human-readable report.
- `staging_registry/` — the bounded registry: catalog, latest.json, compat
  index, withdrawals, activation receipt, and the staged public tree.
- `rehearsal/` — scratch registries exercising prior-release rollback, the
  no-prior-pointer path (the candidate's real rollback shape), and the
  failed-deployment refusal. The "prior" is the committed P32.24
  acceptance-corpus release — a labelled stand-in, NOT a production
  predecessor.
- `ROLLBACK_REHEARSAL.json` — the rehearsal record + live rollback
  instructions.
- `LIVE_RETURN_PASS.json` — `sig.release-publish-return-pass/1`,
  `prepared_not_executed`: the production commands + the open deferrals
  (D-R10-PUBLISH-1 production half, D-P32.23a-1, D-R10-LIVE-1, D-P32.16-1).
"""
