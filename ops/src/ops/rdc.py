# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.23 / SIG-CONF-008 (+D08): the real-data regression corpus.

One licence-aware captured slice per recorded failure archetype, or a filed
deferral when no licensed slice exists. Two lanes:

* ``committed`` — slices whose upstream licence lane is ``raw-ok`` and whose
  bytes are not ODbL-compartment material live under ``tests/rdc/data/`` with
  per-slice ``sig.rdc-slice/1`` metadata + attribution (SOURCES.md). They run
  in the PR lane.
* ``restricted`` — ODbL compartment material and sources whose recorded lane
  is not ``raw-ok`` keep their bytes in the screened compartment bucket's
  OCFL capture store (``evidence/captures/…``); only SHA-256 digests + the
  capture locators are committed. The scheduled ``sig-rdc-probe`` job
  (SIG-CONF-013 posture) fetches, digest-verifies and evaluates them on an
  overlay corpus; a dev clone never needs them.

Expected facts come from ``ops.rdc_oracles`` — pipeline-INDEPENDENT code over
the raw bytes. ``sig.rdc-snapshot/1`` files pin the computed oracle+pipeline
digests; a drift outside an appended approval entry refuses (snapshot changes
are explicit commits, reviewed like ruleset changes). Every ``sig.rdc-report/1``
header names its estimand verbatim and states that the numbers are mechanical
censuses, never real-world precision or recall (SIG-CONF-012 / D12). An empty
corpus run fails — SIG-ENG-042.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tempfile
import tomllib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from . import rdc_oracles

SCHEMA = "sig.rdc-corpus/1"
SLICE_SCHEMA = "sig.rdc-slice/1"
SNAPSHOT_SCHEMA = "sig.rdc-snapshot/1"
REPORT_SCHEMA = "sig.rdc-report/1"

LANES = ("committed", "restricted")
COVERAGE = ("served", "partial", "analog")
ARCHETYPE_STATUS = ("served", "partial", "deferred")
LEGS = ("oracle", "pipeline", "records", "m4", "m5", "m6")

#: SPDX expressions whose captured bytes stay out of the committed tree even
#: when the recorded redistribution lane is ``raw-ok`` — the ODbL compartment
#: (§42.3) is a separate licence space, never merged into committed fixtures.
ODBL_FAMILY = ("ODbL", "odbl")

#: The estimand header every M-4/M-5/M-6 report section must carry verbatim
#: (SIG-CONF-012). Mechanical censuses over the declared corpus — never a
#: real-world precision/recall estimate.
ESTIMAND_DISCLAIMER = "never an estimate of real-world precision or recall"
ESTIMANDS = {
    "m4": (
        "per-class join/no-join outcomes over modelled perturbations of corpus "
        "records — a mechanical census against the declared ruleset contract, "
        + ESTIMAND_DISCLAIMER
    ),
    "m5": (
        "share of mechanically-declared known-distinct pairs the matcher "
        "merges — a census over the declared negative classes only, " + ESTIMAND_DISCLAIMER
    ),
    "m6": (
        "metamorphic invariants over the corpus record set — cluster-set "
        "equality under input-order permutation and blocking-page changes, "
        "unchanged distinct-record count under declared-mirror edits, and "
        "idempotent re-run — " + ESTIMAND_DISCLAIMER
    ),
}

SHA256_RE_LEN = 64


@dataclass(frozen=True)
class Member:
    path: str
    sha256: str
    source_uri: str = ""
    capture: str = ""  # restricted lane: the sig:capture:<id> the bytes derive from


@dataclass(frozen=True)
class Slice:
    slice_id: str
    lane: str
    source_id: str
    archetype: str
    coverage: str
    spdx: str
    attribution: str
    terms_url: str
    captured: str
    oracle: str
    oracle_params: dict[str, Any]
    legs: tuple[str, ...]
    pipeline: dict[str, Any]
    records: dict[str, Any]
    members: tuple[Member, ...]
    notes: str
    directory: Path


@dataclass(frozen=True)
class Archetype:
    archetype_id: str
    summary: str
    status: str
    deferral: str


@dataclass
class Corpus:
    root: Path
    corpus_id: str
    version: int
    estimands: dict[str, str]
    archetypes: list[Archetype]
    slices: list[Slice]


class CorpusError(ValueError):
    """A corpus validation/integrity failure — always fatal, never skipped."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _digest_doc(doc: Any) -> str:
    """Deterministic content digest of a JSON doc (sorted keys, compact)."""
    return (
        "sha256:"
        + hashlib.sha256(
            json.dumps(doc, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        ).hexdigest()
    )


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def _slice_dir(root: Path, lane: str, slice_id: str) -> Path:
    return root / "restricted" / slice_id if lane == "restricted" else root / slice_id


def load_slice(directory: Path) -> Slice:
    doc = tomllib.loads((directory / "slice.toml").read_text())
    if doc.get("schema") != SLICE_SCHEMA:
        raise CorpusError(f"{directory}: slice.toml schema {doc.get('schema')!r} != {SLICE_SCHEMA}")
    members = tuple(
        Member(
            path=str(m["path"]),
            sha256=str(m["sha256"]),
            source_uri=str(m.get("source_uri", "")),
            capture=str(m.get("capture", "")),
        )
        for m in doc.get("members", [])
    )
    return Slice(
        slice_id=str(doc["slice_id"]),
        lane=str(doc["lane"]),
        source_id=str(doc["source_id"]),
        archetype=str(doc["archetype"]),
        coverage=str(doc.get("coverage", "served")),
        spdx=str(doc.get("spdx", "")),
        attribution=str(doc.get("attribution", "")),
        terms_url=str(doc.get("terms_url", "")),
        captured=str(doc.get("captured", "")),
        oracle=str(doc.get("oracle", "")),
        oracle_params=dict(doc.get("oracle_params", {})),
        legs=tuple(str(x) for x in doc.get("legs", [])),
        pipeline=dict(doc.get("pipeline", {})),
        records=dict(doc.get("records", {})),
        members=members,
        notes=str(doc.get("notes", "")),
        directory=directory,
    )


def load_corpus(root: Path) -> Corpus:
    """Load corpus.toml + every slice.toml under ``root`` (committed dirs and
    ``restricted/``). Structural errors raise CorpusError."""
    corpus_file = root / "corpus.toml"
    if not corpus_file.exists():
        raise CorpusError(f"{root}: no corpus.toml")
    doc = tomllib.loads(corpus_file.read_text())
    if doc.get("schema") != SCHEMA:
        raise CorpusError(f"{root}: corpus.toml schema {doc.get('schema')!r} != {SCHEMA}")
    archetypes = [
        Archetype(
            archetype_id=str(a["id"]),
            summary=str(a.get("summary", "")),
            status=str(a.get("status", "deferred")),
            deferral=str(a.get("deferral", "")),
        )
        for a in doc.get("archetypes", [])
    ]
    slices: list[Slice] = []
    for lane_dir in (root, root / "restricted"):
        if not lane_dir.is_dir():
            continue
        for child in sorted(lane_dir.iterdir()):
            if child.is_dir() and (child / "slice.toml").exists():
                slices.append(load_slice(child))
    return Corpus(
        root=root,
        corpus_id=str(doc.get("corpus_id", "rdc")),
        version=int(doc.get("version", 0)),
        estimands={str(k): str(v) for k, v in dict(doc.get("estimands", {})).items()},
        archetypes=archetypes,
        slices=slices,
    )


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_corpus(corpus: Corpus, *, require_materialized: bool = False) -> list[str]:
    """Every structural + licence + integrity violation. Empty list ⇒ valid.

    Licence rule (fail closed): a ``committed`` slice requires the source
    registry's recorded redistribution lane ``raw-ok`` AND a non-ODbL SPDX;
    anything else belongs in ``restricted``. A lane/source-registry mismatch
    or an unresolved rights record is a violation, never a warning.
    """
    errors: list[str] = []
    if not corpus.slices:
        errors.append("corpus declares zero slices — an empty corpus cannot run (SIG-ENG-042)")
    if not corpus.archetypes:
        errors.append("corpus declares zero archetypes")
    for leg in ("m4", "m5", "m6"):
        est = corpus.estimands.get(leg, "")
        if not est:
            errors.append(
                f"estimands.{leg} missing — report headers name the estimand (SIG-CONF-012)"
            )
        elif ESTIMAND_DISCLAIMER not in est:
            errors.append(
                f"estimands.{leg} does not carry the disclaimer "
                f"{ESTIMAND_DISCLAIMER!r} (SIG-CONF-012)"
            )
    arch_ids = set()
    for a in corpus.archetypes:
        if a.archetype_id in arch_ids:
            errors.append(f"duplicate archetype id {a.archetype_id!r}")
        arch_ids.add(a.archetype_id)
        if a.status not in ARCHETYPE_STATUS:
            errors.append(
                f"archetype {a.archetype_id}: status {a.status!r} not in {ARCHETYPE_STATUS}"
            )
        if a.status == "deferred" and not a.deferral.startswith("D-"):
            errors.append(f"archetype {a.archetype_id}: deferred without a D-… deferral id")

    try:
        from connectors.registry import get as source_get
    except Exception:  # pragma: no cover - workspace always has connectors
        source_get = None  # type: ignore[assignment]

    slice_ids = set()
    materialized = 0
    for s in corpus.slices:
        where = f"slice {s.slice_id}"
        if s.slice_id in slice_ids:
            errors.append(f"{where}: duplicate slice id")
        slice_ids.add(s.slice_id)
        if s.lane not in LANES:
            errors.append(f"{where}: lane {s.lane!r} not in {LANES}")
        if s.coverage not in COVERAGE:
            errors.append(f"{where}: coverage {s.coverage!r} not in {COVERAGE}")
        if s.archetype not in arch_ids:
            errors.append(f"{where}: archetype {s.archetype!r} not declared in corpus.toml")
        if s.oracle not in rdc_oracles.ORACLES:
            errors.append(f"{where}: oracle {s.oracle!r} not registered in ops.rdc_oracles")
        if not s.members:
            errors.append(f"{where}: zero members — an empty slice cannot evaluate (SIG-ENG-042)")
        for m in s.members:
            if len(m.sha256) != SHA256_RE_LEN or any(c not in "0123456789abcdef" for c in m.sha256):
                errors.append(f"{where}: member {m.path} sha256 {m.sha256!r} is not a hex sha256")
            f = s.directory / m.path
            if f.exists():
                actual = _sha256(f.read_bytes())
                if actual != m.sha256:
                    errors.append(
                        f"{where}: member {m.path} digest mismatch — declared "
                        f"{m.sha256[:16]}… actual {actual[:16]}… (corrupt or replaced bytes)"
                    )
                else:
                    materialized += 1
            elif s.lane == "committed":
                errors.append(
                    f"{where}: committed member {m.path} absent — committed slices carry bytes"
                )
            elif require_materialized:
                errors.append(f"{where}: restricted member {m.path} not materialized")

        # licence lane vs the source registry — fail closed on unresolved rights
        if source_get is not None:
            try:
                src = source_get(s.source_id)
            except Exception as exc:
                errors.append(f"{where}: source {s.source_id!r} not in the registry ({exc})")
            else:
                lane = src.redistribution.lane
                spdx = src.rights.spdx or ""
                odbl = any(tok in spdx for tok in ODBL_FAMILY)
                if s.lane == "committed":
                    if lane != "raw-ok":
                        errors.append(
                            f"{where}: committed lane requires registry redistribution lane "
                            f"'raw-ok'; {s.source_id} records {lane!r} — licence violation "
                            "(unresolved rights fail closed)"
                        )
                    if odbl:
                        errors.append(
                            f"{where}: {spdx} is ODbL-compartment material — never committed"
                        )
                    if s.spdx and s.spdx != spdx:
                        errors.append(f"{where}: declared spdx {s.spdx!r} != registry {spdx!r}")
                else:  # restricted
                    if lane == "raw-ok" and not odbl:
                        errors.append(
                            f"{where}: {s.source_id} records lane 'raw-ok' non-ODbL — "
                            "it belongs in the committed lane, not restricted"
                        )
                    for m in s.members:
                        if not m.capture:
                            errors.append(
                                f"{where}: restricted member {m.path} names no sig:capture: locator"
                            )

    if require_materialized and materialized == 0:
        errors.append("zero materialized members — an empty run cannot evaluate (SIG-ENG-042)")
    return errors


# ---------------------------------------------------------------------------
# Member access + oracle
# ---------------------------------------------------------------------------


def member_bytes(s: Slice) -> dict[str, bytes]:
    """Materialized member bytes, digest-verified. A digest mismatch is a
    corrupt slice and raises CorpusError — never skipped."""
    out: dict[str, bytes] = {}
    for m in s.members:
        f = s.directory / m.path
        if not f.exists():
            if s.lane == "committed":
                raise CorpusError(f"{s.slice_id}: committed member {m.path} absent")
            continue
        data = f.read_bytes()
        if _sha256(data) != m.sha256:
            raise CorpusError(
                f"{s.slice_id}: member {m.path} corrupt — declared sha256 "
                f"{m.sha256[:16]}… actual {_sha256(data)[:16]}…"
            )
        out[m.path] = data
    return out


def materialized(s: Slice) -> bool:
    return all((s.directory / m.path).exists() for m in s.members)


def run_oracle(s: Slice) -> dict[str, Any]:
    """The pipeline-independent expected facts for a slice."""
    fn = rdc_oracles.ORACLES[s.oracle]
    members = member_bytes(s)
    if s.oracle == "arcgis_camera_facts":
        pages = [members[m.path] for m in s.members if m.path in members]
        params = dict(s.oracle_params)
        if "extent" in params and params["extent"] is not None:
            params["extent"] = tuple(params["extent"])
        return fn(pages, **params)
    if s.oracle == "legistar_tenant_facts":
        return fn(members)
    data = next(iter(members.values()))
    return fn(data, **s.oracle_params)


# ---------------------------------------------------------------------------
# The pipeline leg — the real connector over the captured bytes
# ---------------------------------------------------------------------------


def run_pipeline_leg(s: Slice) -> dict[str, Any]:
    """Run the slice's declared connector over its member bytes and return a
    snapshot doc: run outcome + per-predicate claim census + the oracle-
    checked assertions the pipeline must satisfy.

    The member ``source_uri`` keys the transport: the connector requests the
    exact URL it composed at capture time; a member whose URL the connector
    no longer requests fails loudly (the slice drifted, or the connector's
    URL composition changed — either is a recorded drift, never a silent
    skip).
    """
    if not s.pipeline:
        return {"pipeline": None, "note": "no pipeline leg declared"}
    import dataclasses as _dc

    from connectors.live_targets import live_targets
    from connectors.net import PoliteFetcher, RobotsResult
    from connectors.pipeline import run as connector_run
    from connectors.registry import get as source_get
    from connectors.runner import CONNECTOR_FOR_SOURCE, registered_connectors
    from connectors.stages import (
        FetchResult,
        InMemoryCaptureStore,
        InMemoryClaimSink,
        RunContext,
    )
    from evidence.ingest_run import IngestRun

    members = member_bytes(s)
    uri_to_member = {m.source_uri: m.path for m in s.members if m.source_uri}
    connector_name = s.pipeline.get("connector") or CONNECTOR_FOR_SOURCE.get(s.source_id)
    if not connector_name:
        raise CorpusError(f"{s.slice_id}: no connector resolved for source {s.source_id}")
    connector = registered_connectors()[connector_name]()
    targets = live_targets(s.source_id)
    want_ids = tuple(s.pipeline.get("target_ids", ()))
    if want_ids:
        targets = [t for t in targets if t.get("id") in want_ids]

    requested: list[str] = []

    class _Members:
        def robots(self, _u: str) -> RobotsResult:
            return RobotsResult(text="User-agent: *\nAllow: /\n")

        def request(
            self,
            url: str,
            *,
            user_agent: str,
            headers: Any = None,
            body: Any = None,
        ) -> FetchResult:
            requested.append(url)
            if url not in uri_to_member:
                raise CorpusError(
                    f"{s.slice_id}: connector requested {url} — no corpus member "
                    f"serves it (slice drift or connector URL-composition change)"
                )
            return FetchResult(
                url=url,
                status=200,
                body=members[uri_to_member[url]],
                media_type=s.pipeline.get("media_type", "application/json"),
                retrieved_at=datetime(2026, 9, 18, tzinfo=UTC),
            )

    source = _dc.replace(source_get(s.source_id), ingestion_permitted=True)
    params: dict[str, Any] = {"targets": targets}
    params.update(s.pipeline.get("parameters", {}))
    ctx = RunContext(
        source=source,
        run=IngestRun(
            connector.name, getattr(connector, "version", "1.0.0"), "rdc", "r1", "v1", ()
        ),
        fetcher=PoliteFetcher(
            connector_name=connector.name,
            connector_version=getattr(connector, "version", "1.0.0"),
            transport=_Members(),
        ),
        captures=InMemoryCaptureStore(),
        claim_sink=InMemoryClaimSink(),
        parameters=params,
    )
    outcome: dict[str, Any] = {"pipeline": connector_name, "requested": requested}
    try:
        report = connector_run(connector, ctx)
    except Exception as exc:  # the recorded fail-closed outcome is a first-class result
        outcome.update(
            {
                "run": "failed",
                "error_class": type(exc).__name__,
                "error": str(exc)[:300],
            }
        )
        return outcome
    preds: dict[str, int] = {}
    subjects: set[str] = set()
    for c in report.claims:
        key = str(c.get("predicate_id") or c.get("record_kind") or "?")
        preds[key] = preds.get(key, 0) + 1
        if c.get("subject_id"):
            subjects.add(str(c["subject_id"]))
    outcome.update(
        {
            "run": "completed",
            "asserted": report.asserted,
            "claim_count": len(report.claims),
            "predicate_counts": dict(sorted(preds.items())),
            "distinct_subjects": len(subjects),
            "subject_ids": sorted(subjects),
        }
    )
    return outcome


# ---------------------------------------------------------------------------
# Snapshots — the committed pin + the explicit-approval mechanism
# ---------------------------------------------------------------------------


def _members_digest(s: Slice) -> str:
    return _digest_doc({m.path: m.sha256 for m in s.members})


def compute_snapshot(s: Slice, *, with_pipeline: bool = True) -> dict[str, Any]:
    """The computed snapshot doc for one materialized slice."""
    facts = run_oracle(s)
    pipe = run_pipeline_leg(s) if with_pipeline and s.pipeline else {"pipeline": None}
    return {
        "schema": SNAPSHOT_SCHEMA,
        "slice_id": s.slice_id,
        "lane": s.lane,
        "members_digest": _members_digest(s),
        "oracle_digest": _digest_doc(facts),
        "pipeline_digest": _digest_doc(pipe),
        "facts": facts,
        "pipeline": pipe,
        "approvals": [],
    }


def snapshot_path(corpus: Corpus, s: Slice) -> Path:
    return corpus.root / "snapshots" / f"{s.slice_id}.snapshot.json"


def verify_snapshots(corpus: Corpus) -> list[str]:
    """Compare computed snapshots to the committed pins.

    A drift is legal only when the committed snapshot's append-only
    ``approvals`` list carries an entry covering ``from`` (the pinned digest
    pair) → ``to`` (the recomputed pair). Anything else refuses — an
    uncommitted snapshot change is never silently absorbed.
    """
    violations: list[str] = []
    for s in corpus.slices:
        if s.lane == "restricted" and not materialized(s):
            continue  # the scheduled lane verifies restricted snapshots
        committed_file = snapshot_path(corpus, s)
        if not committed_file.exists():
            violations.append(
                f"{s.slice_id}: no committed snapshot — a new slice lands its "
                f"initial snapshot in the same explicit commit"
            )
            continue
        committed = None
        try:
            committed = json.loads(committed_file.read_text())
        except Exception as exc:
            violations.append(f"{s.slice_id}: committed snapshot unreadable ({exc})")
            continue
        if committed.get("schema") != SNAPSHOT_SCHEMA:
            violations.append(f"{s.slice_id}: snapshot schema {committed.get('schema')!r}")
            continue
        try:
            computed = compute_snapshot(s)
        except CorpusError as exc:
            violations.append(f"{s.slice_id}: {exc}")
            continue
        want = (
            committed.get("members_digest"),
            committed.get("oracle_digest"),
            committed.get("pipeline_digest"),
        )
        got = (
            computed["members_digest"],
            computed["oracle_digest"],
            computed["pipeline_digest"],
        )
        if want == got:
            continue
        approvals = committed.get("approvals") or []
        covered = any(
            a.get("from") == list(want) and a.get("to") == list(got) and a.get("rationale")
            for a in approvals
        )
        if not covered:
            violations.append(
                f"{s.slice_id}: snapshot drift without approval — "
                f"pinned {tuple(x[:18] if isinstance(x, str) else x for x in want)} "
                f"computed {tuple(x[:18] for x in got)}; approve explicitly via "
                f"`sig-ops rdc snapshot --approve` in a dedicated commit with "
                f"rationale + diff summary (corpus snapshots change only by "
                f"explicit commit)"
            )
    return violations


def approve_snapshot(
    corpus: Corpus,
    s: Slice,
    *,
    landed_in: str,
    rationale: str,
    rationale_ref: str,
    out: Path | None = None,
) -> dict[str, Any]:
    """Recompute the snapshot and write it with the appended approval entry.

    The approval records the digest pair it covers plus the rationale and its
    build-memory reference — the explicit-commit mechanism. The file change
    itself IS the commit under review.
    """
    committed_file = snapshot_path(corpus, s)
    computed = compute_snapshot(s)
    prior_approvals: list[dict[str, Any]] = []
    prior_pair: tuple[Any, Any, Any] = ("", "", "")
    if committed_file.exists():
        committed = json.loads(committed_file.read_text())
        prior_approvals = list(committed.get("approvals") or [])
        prior_pair = (
            committed.get("members_digest"),
            committed.get("oracle_digest"),
            committed.get("pipeline_digest"),
        )
    to_pair = [
        computed["members_digest"],
        computed["oracle_digest"],
        computed["pipeline_digest"],
    ]
    computed["approvals"] = prior_approvals + [
        {
            "landed_in": landed_in,
            "from": list(prior_pair) if committed_file.exists() else None,
            "to": to_pair,
            "rationale": rationale,
            "rationale_ref": rationale_ref,
        }
    ]
    target = out or committed_file
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(computed, indent=2, sort_keys=True, default=str) + "\n")
    return computed


# ---------------------------------------------------------------------------
# The sig.rdc-report/1 document + estimand lint (SIG-CONF-012)
# ---------------------------------------------------------------------------


def build_report(
    corpus: Corpus,
    *,
    sections: dict[str, Any],
    generated_at: str,
    verdict: str,
    slices_evaluated: int,
    slices_deferred: list[str],
) -> dict[str, Any]:
    """The corpus harness report. The ``estimand`` header names every leg's
    estimand verbatim and carries the disclaimer — the lint below refuses a
    report that drops or re-frames it."""
    return {
        "schema": REPORT_SCHEMA,
        "corpus_id": corpus.corpus_id,
        "corpus_version": corpus.version,
        "generated_at": generated_at,
        "slices_evaluated": slices_evaluated,
        "slices_deferred_unmaterialized": slices_deferred,
        "estimand": {leg: corpus.estimands.get(leg, "") for leg in ("m4", "m5", "m6")},
        "verdict": verdict,
        "sections": sections,
    }


def report_lint_errors(report: dict[str, Any]) -> list[str]:
    """SIG-CONF-012 lint: every estimand header must carry the disclaimer
    verbatim; a report section missing its estimand, or asserting real-world
    precision/recall framing, fails."""
    errors: list[str] = []
    if report.get("schema") != REPORT_SCHEMA:
        errors.append(f"report schema {report.get('schema')!r} != {REPORT_SCHEMA}")
    est = report.get("estimand") or {}
    for leg in ("m4", "m5", "m6"):
        text = str(est.get(leg) or "")
        if not text:
            errors.append(f"report estimand.{leg} missing — unlabelled estimands fail")
        elif ESTIMAND_DISCLAIMER not in text:
            errors.append(f"report estimand.{leg} drops the required disclaimer")
    for leg, section in (report.get("sections") or {}).items():
        if leg in ("m4", "m5", "m6") and not isinstance(section, dict):
            errors.append(f"section {leg} malformed")
    if report.get("slices_evaluated", 0) < 1:
        errors.append("report evaluated zero slices — vacuous pass refused (SIG-ENG-042)")
    return errors


# ---------------------------------------------------------------------------
# Restricted-lane derivation — content-addressed, digest-verified
# ---------------------------------------------------------------------------


def derive_restricted(corpus: Corpus, capture_root: Path, out_dir: Path) -> dict[str, Any]:
    """Materialize restricted members from the OCFL capture root.

    Each member's ``capture`` names the ``sig:capture:<id>`` object; the
    object's manifest locates the raw bytes (``v*/content/capture``). Every
    derived byte stream is re-hashed and compared against the committed
    digest BEFORE it is written — a mismatch aborts (content-addressed;
    a re-run re-derives, it never re-uploads or trusts bytes).
    """
    derived: dict[str, Any] = {"derived": [], "errors": []}
    for s in corpus.slices:
        if s.lane != "restricted":
            continue
        for m in s.members:
            found = list(capture_root.glob(f"*/*/*/sig%3acapture%3a{m.capture.split(':')[-1]}"))
            if not found:
                derived["errors"].append(
                    f"{s.slice_id}/{m.path}: capture {m.capture} not under {capture_root}"
                )
                continue
            obj = found[0]
            inv = json.loads((obj / "inventory.json").read_text())
            cap_path = None
            for _sha, paths in (inv.get("manifest") or {}).items():
                for p in paths:
                    if p.endswith("/capture"):
                        cap_path = obj / p
            if cap_path is None or not cap_path.exists():
                derived["errors"].append(f"{s.slice_id}/{m.path}: no capture member in {obj}")
                continue
            data = cap_path.read_bytes()
            if _sha256(data) != m.sha256:
                derived["errors"].append(
                    f"{s.slice_id}/{m.path}: derived bytes sha256 mismatch — "
                    f"committed {m.sha256[:16]}… derived {_sha256(data)[:16]}…"
                )
                continue
            target = out_dir / "restricted" / s.slice_id / m.path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            derived["derived"].append(
                {"slice": s.slice_id, "member": m.path, "sha256": m.sha256, "from": str(cap_path)}
            )
    return derived


def derive_restricted_from_bucket(
    corpus: Corpus, bucket: Any, capture_prefix: str, staging_root: Path
) -> dict[str, Any]:
    """Fetch restricted member bytes from the screened compartment bucket.

    Each member's ``capture`` id resolves to a deterministic OCFL storage
    path (extension 0003 — three 2-char sha256 tuples + the percent-encoded
    id), so the read is one bounded object fetch per member, never a bucket
    listing. The object's head version's ``capture`` logical path is the raw
    byte stream; every fetched stream is sha256-checked against the
    committed digest BEFORE it is staged — a mismatch is an error entry,
    never trusted bytes. ``bucket`` is a ``GcsBucket``-shaped object
    (injectable in tests).
    """
    from evidence.ocfl import object_path

    out: dict[str, Any] = {"derived": [], "errors": []}
    for s in corpus.slices:
        if s.lane != "restricted":
            continue
        for m in s.members:
            base = f"{capture_prefix.strip('/')}/{object_path(m.capture)}"
            try:
                inv = json.loads(bucket.get_object(f"{base}/inventory.json"))
            except Exception as exc:  # noqa: BLE001 — a missing object is an error entry
                out["errors"].append(f"{s.slice_id}/{m.path}: inventory {m.capture}: {exc}")
                continue
            head = inv.get("head") or ""
            cap_content = None
            manifest = inv.get("manifest") or {}
            state = (inv.get("versions") or {}).get(head, {}).get("state") or {}
            for digest, logicals in state.items():
                if "capture" in logicals:
                    paths = manifest.get(digest) or []
                    cap_content = paths[0] if paths else None
                    break
            if cap_content is None:
                # manifest-only fallback (the on-disk derive uses the same scan)
                for paths in manifest.values():
                    for p in paths:
                        if p.endswith("/capture"):
                            cap_content = p
                            break
            if cap_content is None:
                out["errors"].append(
                    f"{s.slice_id}/{m.path}: no capture content in {m.capture} {head}"
                )
                continue
            try:
                data = bucket.get_object(f"{base}/{cap_content}")
            except Exception as exc:  # noqa: BLE001
                out["errors"].append(f"{s.slice_id}/{m.path}: fetch {cap_content}: {exc}")
                continue
            if _sha256(data) != m.sha256:
                out["errors"].append(
                    f"{s.slice_id}/{m.path}: fetched bytes sha256 mismatch — "
                    f"committed {m.sha256[:16]}… fetched {_sha256(data)[:16]}…"
                )
                continue
            target = staging_root / "restricted" / s.slice_id / m.path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            out["derived"].append(
                {
                    "slice": s.slice_id,
                    "member": m.path,
                    "sha256": m.sha256,
                    "from": f"{base}/{cap_content}",
                }
            )
    return out


def overlay_corpus(root: Path, staging: Path, work: Path) -> Path:
    """Copy the corpus to ``work`` and overlay staged restricted member bytes.

    The committed corpus tree is never mutated: the scheduled leg works on
    this overlay so a half-fetched staging leaves the pinned tree untouched.
    """
    shutil.copytree(root, work)
    for staged in sorted(staging.glob("restricted/*/*")):
        if not staged.is_file():
            continue
        rel = staged.relative_to(staging)
        target = work / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(staged, target)
    return work


# ---------------------------------------------------------------------------
# The scheduled probe leg — window guard, records, upload
# ---------------------------------------------------------------------------

#: The restricted-bucket prefix the probe's two records land under — inside
#: the conditioned ``ops/probes/`` objectCreator scope the job's runtime
#: identity already carries (ops/iam_identities.toml, SIG-CONF-013).
RDC_PROBE_PREFIX = "ops/probes/rdc/"

#: The capture-store prefix the restricted member bytes are fetched from —
#: inside the conditioned ``evidence/captures/`` objectViewer scope.
RDC_CAPTURE_PREFIX = "evidence/captures/"


def _window_suppression(now: str) -> str | None:
    """The OM-19 guard the job re-checks at run time (defence in depth for a
    manually invoked or drifted trigger — the declared cron can never land
    inside either window). Returns the suppression reason or ``None``."""
    hhmm = now[11:16]
    dom = now[8:10]
    if "03:00" <= hhmm < "06:30":
        return f"{now} is inside 03:00–06:30Z — never run then"
    if "06" <= dom <= "13" and (dom < "13" or hhmm < "12:00"):
        return f"{now} is inside the monthly batch window (day 6 00:00Z → day 13 12:00Z)"
    return None


def _stamp(now: str) -> str:
    return now.replace(":", "").replace("-", "")


def _object_name(prefix: str, kind: str, now: str) -> str:
    day = now[:10]
    return f"{prefix}{day}/{_stamp(now)}-{kind}.json"


def _upload(bucket: Any, name: str, doc: dict[str, Any]) -> None:
    bucket.put_object(
        name,
        (json.dumps(doc, indent=2, sort_keys=True, default=str) + "\n").encode("utf-8"),
        content_type="application/json",
    )


def run_scheduled(
    corpus: Corpus,
    *,
    slices_dir: Path | None,
    bucket: Any,
    capture_prefix: str,
    records_prefix: str,
    out_dir: Path | None,
    job_name: str,
    now: str | None = None,
) -> int:
    """The ``sig-rdc-probe`` job's in-container leg.

    Order: window guard → derive the restricted members (from the screened
    bucket, or a pre-staged ``slices_dir`` in tests) → overlay corpus →
    validate (every restricted member materialized) → full harness →
    write ``rdc-report.json`` + a ``sig.probe-run/1`` envelope → upload
    both as new timestamped objects under ``records_prefix`` (WORM-shaped,
    never rewritten). A suppressed or refused run still writes a
    probe-run record — an empty slot is never mistaken for a pass.
    """
    from . import probe_run, rdc_harness

    generated_at = now or probe_run.utcnow()

    def _emit(record: dict[str, Any], report: dict[str, Any] | None) -> int:
        if out_dir is not None:
            out_dir.mkdir(parents=True, exist_ok=True)
            if report is not None:
                (out_dir / "rdc-report.json").write_text(
                    json.dumps(report, indent=2, sort_keys=True, default=str) + "\n"
                )
            probe_run.write_record(record, out_dir / "probe-run.json")
        if bucket is not None:
            _upload(bucket, _object_name(records_prefix, "probe-run", generated_at), record)
            if report is not None:
                _upload(
                    bucket,
                    _object_name(records_prefix, "rdc-report", generated_at),
                    report,
                )
        return 0

    suppressed = _window_suppression(generated_at)
    if suppressed:
        record = probe_run.build_record(
            job_name,
            {"window": probe_run.CheckResult("skipped", {"reason": suppressed})},
            subject={"corpus": corpus.corpus_id, "slices": len(corpus.slices)},
            now=generated_at,
        )
        _emit(record, None)
        print(f"suppressed: {suppressed} — probe-run record written")
        return 0

    def _fail_leg(name: str, detail: dict[str, Any]) -> int:
        for e in detail.get("errors", []):
            print(f"FAIL {e}", file=sys.stderr)
        record = probe_run.build_record(
            job_name,
            {name: probe_run.CheckResult("fail", detail)},
            subject={"corpus": corpus.corpus_id},
            now=generated_at,
        )
        _emit(record, None)
        return 1

    with tempfile.TemporaryDirectory(prefix="rdc-sched-") as tmp:
        # the overlay lives for the whole run — member bytes are read lazily
        staging = Path(tmp) / "staging"
        if slices_dir is not None:
            staging = slices_dir
        else:
            staging.mkdir(parents=True, exist_ok=True)
            if bucket is None:
                return _fail_leg(
                    "derive",
                    {"errors": ["no --slices-dir and no bucket — restricted bytes unfetchable"]},
                )
            derived = derive_restricted_from_bucket(corpus, bucket, capture_prefix, staging)
            if derived["errors"]:
                return _fail_leg("derive", {"errors": derived["errors"]})
        corpus2 = load_corpus(overlay_corpus(corpus.root, staging, Path(tmp) / "corpus"))

        errors = validate_corpus(corpus2, require_materialized=True)
        if errors:
            return _fail_leg("corpus", {"errors": errors})

        report = rdc_harness.run_harness(corpus2)
        sections = report["sections"]
        checks = {
            "corpus": probe_run.CheckResult(
                "pass" if report["verdict"] == "pass" else "fail",
                {
                    "slices_evaluated": report["slices_evaluated"],
                    "deferred": report["slices_deferred_unmaterialized"],
                    "failures": report.get("failures", []),
                },
            ),
        }
        for leg in ("m4", "m5", "m6"):
            sec = sections[leg]
            checks[leg] = probe_run.CheckResult(
                "pass" if sec.get("violations") == 0 else "fail",
                {
                    "sample_size": sec.get("sample_size"),
                    "violations": sec.get("violations"),
                },
            )
        record = probe_run.build_record(
            job_name,
            checks,
            subject={
                "corpus": corpus.corpus_id,
                "slices": [s.slice_id for s in corpus2.slices],
            },
            now=generated_at,
        )
        _emit(record, report)
        print(f"scheduled rdc run complete — verdict {report['verdict']}")
        return 0 if report["verdict"] == "pass" else 1


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _repo_root() -> Path:
    # ops/src/ops/rdc.py -> ops/src/ops -> ops/src -> ops -> repo root
    return Path(__file__).resolve().parents[3]


def _default_root() -> Path:
    return _repo_root() / "tests" / "rdc" / "data"


def main(argv: list[str] | None = None) -> int:
    """``sig-ops rdc`` — the corpus surface (offline/digest-verified)."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        prog="sig-ops rdc",
        description=(
            "P35.23 (SIG-CONF-008/012/013): the real-data regression corpus. "
            "`check` validates the corpus (licence lanes, digests, empty-fail); "
            "`harness` runs the M-4/M-5/M-6 mechanical legs + oracle + pipeline "
            "legs and emits sig.rdc-report/1; `snapshot` verifies/approves the "
            "committed pins; `derive` materializes restricted members from the "
            "OCFL capture root (digest-verified); `scheduled` is the "
            "sig-rdc-probe job's in-container command over fetched restricted "
            "slices; `job` renders the ops/rdc_probe.toml declaration."
        ),
    )
    sub = parser.add_subparsers(dest="rdc_command", required=True)

    def _root_arg(p: argparse.ArgumentParser) -> None:
        p.add_argument("--corpus", default=None, help="corpus root (default tests/rdc/data)")

    p_check = sub.add_parser("check", help="validate the corpus (offline)")
    _root_arg(p_check)
    p_check.add_argument(
        "--materialized",
        action="store_true",
        help="require every restricted member materialized too (the job's posture)",
    )

    p_harness = sub.add_parser("harness", help="run the corpus harness (offline)")
    _root_arg(p_harness)
    p_harness.add_argument("--out", default=None, help="write rdc-report.json under this dir")
    p_harness.add_argument("--emit", action="store_true", help="print the report JSON")
    p_harness.add_argument(
        "--skip-pipeline",
        action="store_true",
        help="skip the connector legs (oracle + harness only)",
    )

    p_snap = sub.add_parser("snapshot", help="verify or approve the committed snapshots")
    _root_arg(p_snap)
    snap_sub = p_snap.add_subparsers(dest="snapshot_command", required=True)
    snap_sub.add_parser("verify", help="fail on unapproved drift")
    p_app = snap_sub.add_parser("approve", help="recompute + append the approval entry")
    p_app.add_argument("--landed-in", required=True, help="the manifest row landing the change")
    p_app.add_argument("--rationale", required=True, help="why the snapshot legitimately changed")
    p_app.add_argument(
        "--rationale-ref", required=True, help="build-memory ref carrying the diff summary"
    )
    p_app.add_argument("--slice", default=None, help="approve one slice only")

    p_der = sub.add_parser("derive", help="materialize restricted members from the capture root")
    _root_arg(p_der)
    p_der.add_argument("--capture-root", required=True)
    p_der.add_argument("--out", required=True, help="staging dir for the derived members")

    p_sched = sub.add_parser(
        "scheduled",
        help="the sig-rdc-probe job command (P35.23, SIG-CONF-013): window "
        "guard, derive restricted members from the screened bucket, run the "
        "full harness over the overlay corpus, emit rdc-report + probe-run "
        "records under the restricted prefix",
    )
    _root_arg(p_sched)
    p_sched.add_argument(
        "--slices-dir",
        default=None,
        help="pre-staged restricted members root (test/local leg; else the "
        "members are fetched from --bucket under --capture-prefix)",
    )
    p_sched.add_argument(
        "--bucket",
        default=os.environ.get("SIG_OPS_GCS_BUCKET", ""),
        help="restricted bucket (default: SIG_OPS_GCS_BUCKET; empty = local only)",
    )
    p_sched.add_argument(
        "--capture-prefix",
        default=os.environ.get("SIG_RDC_CAPTURE_PREFIX", RDC_CAPTURE_PREFIX),
        help="bucket-relative OCFL capture-root prefix",
    )
    p_sched.add_argument(
        "--records-prefix",
        default=os.environ.get("SIG_RDC_PROBE_PREFIX", RDC_PROBE_PREFIX),
        help="bucket-relative record prefix (inside the ops/probes/ grant)",
    )
    p_sched.add_argument(
        "--job-name",
        default=os.environ.get("SIG_RDC_JOB_NAME", "sig-rdc-probe"),
        help="the job name stamped on the probe-run record",
    )
    p_sched.add_argument("--out", default=None, help="local dir for the two records")
    p_sched.add_argument(
        "--now",
        default=None,
        help="ISO-UTC for the window guard (test hook — a live run reads the clock)",
    )

    p_job = sub.add_parser(
        "job",
        help="the sig-rdc-probe declaration surface: plan, render, "
        "verify-describe, verify-trigger — offline verbs ops/gcp/rdc-slices.sh "
        "drives",
    )
    job_sub = p_job.add_subparsers(dest="job_command", required=True)
    p_jp = job_sub.add_parser("plan", help="print the validated declaration (offline)")
    p_jp.add_argument("--declaration", default=None)
    p_jr = job_sub.add_parser("render", help="render the whole mutation set as argv JSON")
    p_jr.add_argument("--declaration", default=None)
    p_jr.add_argument("--image", required=True, help="digest-pinned image ref")
    p_jr.add_argument("--project", default=os.environ.get("SIG_GCP_PROJECT", "<SIG_GCP_PROJECT>"))
    p_jr.add_argument("--region", default=os.environ.get("SIG_GCP_REGION", "us-central1"))
    p_jr.add_argument(
        "--env",
        dest="env_pairs",
        action="append",
        default=[],
        help="NAME=value for a declared plain env var (repeatable)",
    )
    p_jd = job_sub.add_parser(
        "verify-describe", help="judge a recorded `run jobs describe --format=json`"
    )
    p_jd.add_argument("--declaration", default=None)
    p_jd.add_argument("--describe", required=True)
    p_jd.add_argument("--project", default=os.environ.get("SIG_GCP_PROJECT", ""))
    p_jt = job_sub.add_parser(
        "verify-trigger", help="judge a recorded `scheduler jobs describe --format=json`"
    )
    p_jt.add_argument("--declaration", default=None)
    p_jt.add_argument("--describe", required=True)
    p_jt.add_argument("--project", default=os.environ.get("SIG_GCP_PROJECT", ""))
    p_jt.add_argument("--region", default=os.environ.get("SIG_GCP_REGION", "us-central1"))

    args = parser.parse_args(argv)
    root = Path(args.corpus).resolve() if getattr(args, "corpus", None) else _default_root()

    if args.rdc_command == "check":
        corpus = load_corpus(root)
        errors = validate_corpus(corpus, require_materialized=args.materialized)
        for s in corpus.slices:
            print(
                f"  {s.slice_id:34s} {s.lane:10s} {s.archetype:28s} "
                f"{s.coverage:8s} members={len(s.members)}"
            )
        for a in corpus.archetypes:
            print(f"  archetype {a.archetype_id:32s} {a.status:9s} {a.deferral}")
        if errors:
            for e in errors:
                print(f"FAIL {e}", file=sys.stderr)
            return 1
        print(f"check OK — {len(corpus.slices)} slices, {len(corpus.archetypes)} archetypes")
        return 0

    if args.rdc_command == "harness":
        from . import rdc_harness

        corpus = load_corpus(root)
        errors = validate_corpus(corpus)
        if errors:
            for e in errors:
                print(f"FAIL {e}", file=sys.stderr)
            return 1
        report = rdc_harness.run_harness(corpus, with_pipeline=not args.skip_pipeline)
        lint = report_lint_errors(report)
        if lint:
            for e in lint:
                print(f"FAIL {e}", file=sys.stderr)
            return 1
        if args.out:
            out_dir = Path(args.out)
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "rdc-report.json").write_text(
                json.dumps(report, indent=2, sort_keys=True, default=str) + "\n"
            )
        if args.emit or not args.out:
            print(json.dumps(report, indent=2, sort_keys=True, default=str))
        else:
            print(f"rdc-report.json written under {args.out} — verdict {report['verdict']}")
        return 0 if report["verdict"] == "pass" else 1

    if args.rdc_command == "snapshot":
        corpus = load_corpus(root)
        if args.snapshot_command == "verify":
            violations = verify_snapshots(corpus)
            for v in violations:
                print(f"FAIL {v}", file=sys.stderr)
            if violations:
                return 1
            print("snapshot verify OK — every committed pin matches (or is approved)")
            return 0
        # approve
        slices = (
            corpus.slices
            if args.slice is None
            else [s for s in corpus.slices if s.slice_id == args.slice]
        )
        for s in slices:
            if s.lane == "restricted" and not materialized(s):
                print(f"skip {s.slice_id} — restricted member bytes not materialized")
                continue
            approve_snapshot(
                corpus,
                s,
                landed_in=args.landed_in,
                rationale=args.rationale,
                rationale_ref=args.rationale_ref,
            )
            print(f"approved {s.slice_id} → {snapshot_path(corpus, s)}")
        return 0

    if args.rdc_command == "derive":
        corpus = load_corpus(root)
        result = derive_restricted(corpus, Path(args.capture_root), Path(args.out))
        for d in result["derived"]:
            print(f"derived {d['slice']}/{d['member']} {d['sha256'][:16]}…")
        for e in result["errors"]:
            print(f"FAIL {e}", file=sys.stderr)
        return 1 if result["errors"] else 0

    if args.rdc_command == "scheduled":
        bucket = None
        if args.bucket:
            from .gcs import GcsBucket

            bucket = GcsBucket(args.bucket)
        return run_scheduled(
            load_corpus(root),
            slices_dir=Path(args.slices_dir) if args.slices_dir else None,
            bucket=bucket,
            capture_prefix=args.capture_prefix,
            records_prefix=args.records_prefix,
            out_dir=Path(args.out) if args.out else None,
            job_name=args.job_name,
            now=args.now,
        )

    if args.rdc_command == "job":
        from . import rdc_job

        try:
            decl = rdc_job.load_declaration(args.declaration)
        except ValueError as e:
            print(f"sig-ops rdc job: refused — {e}", file=sys.stderr)
            return 4
        if args.job_command == "plan":
            print(
                json.dumps(
                    {
                        "schema": rdc_job.SCHEMA,
                        "job": decl.job,
                        "service_account": decl.service_account,
                        "image_repo": decl.image_repo,
                        "command": decl.command,
                        "container_args": list(decl.container_args),
                        "tasks": decl.tasks,
                        "max_retries": decl.max_retries,
                        "task_timeout": decl.task_timeout,
                        "cpu": decl.cpu,
                        "memory": decl.memory,
                        "corpus_root": decl.corpus_root,
                        "capture_prefix": decl.capture_prefix,
                        "probe_prefix": decl.probe_prefix,
                        "scheduler": vars(decl.scheduler),
                        "plain_env": list(decl.plain_env),
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        if args.job_command == "render":
            env_values = {}
            for pair in args.env_pairs:
                name, _, value = pair.partition("=")
                env_values[name] = value
            try:
                rendered = rdc_job.render(
                    decl,
                    project=args.project,
                    region=args.region,
                    image=args.image,
                    env_values=env_values,
                )
            except ValueError as e:
                print(f"sig-ops rdc job render: refused — {e}", file=sys.stderr)
                return 4
            print(json.dumps(rendered, indent=2, sort_keys=True))
            return 0
        if args.job_command == "verify-describe":
            describe = json.loads(Path(args.describe).read_text(encoding="utf-8"))
            diffs = rdc_job.verify_describe(decl, describe, project=args.project)
            for d in diffs:
                print(f"DRIFT {d}", file=sys.stderr)
            return 1 if diffs else 0
        if args.job_command == "verify-trigger":
            describe = json.loads(Path(args.describe).read_text(encoding="utf-8"))
            diffs = rdc_job.verify_trigger(decl, describe, project=args.project, region=args.region)
            for d in diffs:
                print(f"DRIFT {d}", file=sys.stderr)
            return 1 if diffs else 0

    return 2  # pragma: no cover
