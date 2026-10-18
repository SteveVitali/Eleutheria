# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Plain-CLI entry point for the `connectors` stage (SIG-ENG-013, SIG-INGEST-021).

Every stage of the connector framework stays runnable as a plain CLI so the
orchestration choice is reversible (SIG-INGEST-021, ADR-014). The sub-commands:

* ``validate`` — the registry self-checks that must hold at every phase gate
  (SIG-INGEST-023..040).
* ``stages`` — list the eight stages in order (§21.1, SIG-INGEST-001).
* ``list-connectors`` — list the registered source connectors (the `osm`
  connector lands in P04.2; the plug-in seam they register through, SIG-INGEST-021).
* ``gate --source ID`` — report the connector-loader gate verdict for a source
  (SIG-INGEST-014/028): ingestion_permitted + compact_status + custody_posture.
* ``export-check`` — compute the export licence per compartment across the
  registry and exit non-zero on any incompatibility (SIG-LIC-010).
* ``review-status`` — per-source rights-review gate breakdown (P21.1).
* ``run --source ID --mode live|replay|shadow`` — drive a source connector
  (P21.3, ADR-065). ``live`` **refuses** (exit 3, with the gate reasons) unless the
  source's review-status is fully green — a live fetch is impossible without a
  green review-status (LD-X08); ``replay``/``shadow`` run over a committed fixture
  under network isolation and never fetch. The run orchestration itself lives in
  :mod:`connectors.runner`; the CLI only parses args and maps a refusal to exit 3.
"""

from __future__ import annotations

import argparse
from typing import TYPE_CHECKING

from policy.licensing import LicenseIncompatibilityError, compartments

from . import __version__
from .ecosystem import GroupStatus, local_groups, partners
from .loader import assert_export_compatible, is_loadable, source_export_license
from .registry import get, sources
from .review import flip_ready, gate_breakdown, is_flip_ready, review_metadata_violations
from .stages import registered_connectors, stage_names

if TYPE_CHECKING:
    from pathlib import Path

    from resolution.review_pg import PgReviewQueue
    from resolution.review_queue import ReviewQueue

    from .capture_ocfl import OcflCaptureStore


def build_parser() -> argparse.ArgumentParser:
    """Return the argument parser for the `connectors` stage."""
    parser = argparse.ArgumentParser(
        prog="sig-connectors",
        description="SIG connectors: connector framework, source registry, gate (§21/§22).",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("validate", help="run the source-registry data-layer self-checks")
    sub.add_parser("stages", help="list the eight connector stages in order (§21.1)")
    sub.add_parser("list-connectors", help="list the registered source connectors")
    gate = sub.add_parser("gate", help="report the connector-loader gate verdict for a source")
    gate.add_argument("--source", required=True, help="source id to check")
    sub.add_parser("export-check", help="compute the export licence per compartment (SIG-LIC-010)")
    rekeyp = sub.add_parser(
        "rekey-personal-ids",
        help=(
            "P34.18 / ADR-178: dry-run-by-default re-key of the handle-bearing "
            "source ids (S0 RI-01); --apply writes, counts only, never prints a handle"
        ),
    )
    rekeyp.add_argument("--apply", action="store_true", help="write changes (default: dry-run)")
    rekeyp.add_argument("--handles", default=None, help="gitignored handle-list path")
    rekeyp.add_argument("--report", default=None, help="report output path (gitignored)")
    rekeyp.add_argument("--restricted-out", default=None, help="restricted map path (gitignored)")
    acl = sub.add_parser(
        "attribution-correction-list",
        help=(
            "P34.21a / ADR-194: emit the committed source-attribution corrections "
            "artifact `sig-db attribution-corrections` consumes — one row per "
            "rights-reviewed registry source; --out writes the committed file, "
            "else the document prints to stdout"
        ),
    )
    acl.add_argument("--out", default=None, help="output path (default: print to stdout)")
    sll = sub.add_parser(
        "source-lineage-list",
        help=(
            "P35.25 / SIG-CONF-014: emit the committed source-lineage "
            "declarations artifact `sig-db lineage-rematerialize` consumes — "
            "one row per registry source (kind, upstream refs, resolved "
            "independence_class, id_namespace); --out writes the committed "
            "file, else the document prints to stdout"
        ),
    )
    sll.add_argument("--out", default=None, help="output path (default: print to stdout)")
    tb = sub.add_parser(
        "technology-backfill",
        help=(
            "P35.15b / PKG-07 (F-329/F-523): dry-run-by-default, INSERT-only "
            "backfill of each target's declared `technology` claim onto the "
            "pre-PKG-07 traffic_camera:* subjects, chunked commits + "
            "claim_evidence links to existing captures; --apply writes"
        ),
    )
    tb.add_argument("--dsn", required=True, help="PostgreSQL DSN for the claim spine")
    tb.add_argument("--apply", action="store_true", help="write claims (default: dry-run)")
    tb.add_argument(
        "--commit-chunk-size",
        type=int,
        default=None,
        help="claims committed per transaction (default: $SIG_COMMIT_CHUNK_SIZE "
        "else the sink default) — P26.18",
    )
    tb.add_argument(
        "--code-commit",
        default="unknown",
        help="code commit recorded on the ingest_run (default: 'unknown')",
    )
    gc = sub.add_parser(
        "geometry-corrections",
        help=(
            "P35.16 / R11-DATA-01 (F-322): dry-run-by-default, INSERT-only "
            "correction pass over the declared sig.geometry-corrections/1 "
            "groups — marks each flagged subject with a `geometry_defect` "
            "claim and revises provable axis-swapped coordinate claims; "
            "--apply writes"
        ),
    )
    gc.add_argument("--dsn", required=True, help="PostgreSQL DSN for the claim spine")
    gc.add_argument("--apply", action="store_true", help="write claims (default: dry-run)")
    gc.add_argument(
        "--commit-chunk-size",
        type=int,
        default=None,
        help="claims committed per transaction (default: $SIG_COMMIT_CHUNK_SIZE "
        "else the sink default) — P26.18",
    )
    gc.add_argument(
        "--code-commit",
        default="unknown",
        help="code commit recorded on the ingest_run (default: 'unknown')",
    )
    rp = sub.add_parser(
        "redact-propose",
        help=(
            "P36.15 (SIG-PUB-015): enqueue a redaction proposal as a "
            "'redaction' review_item on the curation mechanism — scope (spans or "
            "literal strings, resolved + digest-bound), method, version. The "
            "proposal carries digests of the removed text, never the text."
        ),
    )
    rp.add_argument("--capture-dir", required=True, help="OCFL capture root")
    rp.add_argument("--parent-capture-id", required=True, help="evidence_capture row id")
    rp.add_argument("--parent-digest", required=True, help="parent's content multihash")
    rp.add_argument("--media-type", required=True, help="parent capture media type")
    rp.add_argument(
        "--method", required=True, help="redaction method (e.g. text-layer-substitution)"
    )
    rp.add_argument("--version", required=True, help="redaction method version")
    rp.add_argument(
        "--span",
        action="append",
        default=None,
        help="code-point span 'start:end' over the decoded document (repeatable)",
    )
    rp.add_argument(
        "--text",
        action="append",
        default=None,
        help="literal string to remove — every occurrence is spanned (repeatable)",
    )
    rp.add_argument("--note", default="", help="bounded human-readable scope note")
    rp.add_argument("--queue-json", default=None, help="a JSON-serialised ReviewQueue file")
    rp.add_argument("--dsn", default=None, help="PostgreSQL DSN for the review queue")
    ra = sub.add_parser(
        "redact-apply",
        help=(
            "P36.15 (SIG-PUB-015/016): apply a *reviewed* redaction — the latest "
            "recorded decision on the review item must be a human accept; the "
            "derivative is written as a NEW OCFL object carrying the "
            "sig.redaction-review/1 record. Exit 3 when no accept is recorded."
        ),
    )
    ra.add_argument("--capture-dir", required=True, help="OCFL capture root")
    ra.add_argument("--item", required=True, help="the redaction review_item id")
    ra.add_argument("--queue-json", default=None, help="a JSON-serialised ReviewQueue file")
    ra.add_argument("--dsn", default=None, help="PostgreSQL DSN for the review queue")
    rev = sub.add_parser(
        "review-status",
        help="per-source rights-review gate breakdown + flip-ready count (P21.1)",
    )
    rev.add_argument("--source", default=None, help="show one source's five-field gate breakdown")
    runp = sub.add_parser(
        "run",
        help=(
            "run a source connector in live|replay|shadow mode (P21.3); live refuses "
            "(exit 3) unless the source's review-status is fully green"
        ),
    )
    seedp = sub.add_parser(
        "load-seed",
        help=(
            "load a committed one-time seed asset (seeds.toml) into the claim spine "
            "through the same pipeline + loader gate as every source (P25.7); "
            "packaged bytes over the static transport — never a network fetch"
        ),
    )
    seedp.add_argument("--source", required=True, help="seed source id (seeds.toml row)")
    seedp.add_argument(
        "--connector", default=None, help="registered connector name (else inferred)"
    )
    seedp.add_argument(
        "--sink",
        default="memory",
        choices=("memory", "pg"),
        help="claim sink: 'memory' (default) or 'pg' (requires --dsn)",
    )
    seedp.add_argument("--dsn", default=None, help="PG DSN for --sink pg")
    runp.add_argument("--source", required=True, help="source id for the run (SourceRecord)")
    runp.add_argument(
        "--mode",
        default="shadow",
        choices=("live", "replay", "shadow"),
        help="live (gated), replay, or shadow (default) over a committed fixture",
    )
    runp.add_argument(
        "--connector", default=None, help="registered connector name (else inferred from --source)"
    )
    runp.add_argument(
        "--fixture", default=None, help="committed fixture path (required for replay/shadow)"
    )
    runp.add_argument("--kind", default="overpass", help="target kind (e.g. bulk_csv, overpass)")
    runp.add_argument("--media-type", default="application/json", help="fixture media type")
    runp.add_argument(
        "--sink",
        default="memory",
        choices=("memory", "pg"),
        help="claim sink: 'memory' (default) or 'pg' (requires --dsn)",
    )
    runp.add_argument("--dsn", default=None, help="PostgreSQL DSN when --sink pg")
    runp.add_argument(
        "--capture-dir",
        default=None,
        help="OCFL capture root for a live run (default .sig/captures)",
    )
    runp.add_argument(
        "--wacz", action="store_true", help="also capture HTML pages as WACZ (live, P02.2 path)"
    )
    runp.add_argument(
        "--commit-chunk-size",
        type=int,
        default=None,
        help="PG sink: claims committed per transaction (default: $SIG_COMMIT_CHUNK_SIZE "
        "else the sink default; small sources commit in one chunk) — P26.18",
    )
    return parser


def _validate() -> int:
    srcs = sources()
    groups = local_groups()
    orgs = partners()
    undetermined = [s for s in srcs if s.rights.spdx.strip().upper() == "UNDETERMINED"]
    permitted = [s for s in srcs if s.ingestion_permitted]
    loadable = [s for s in srcs if is_loadable(s)]
    disappeared = [g for g in groups.values() if g.status is GroupStatus.DISAPPEARED]
    unlocated = [g for g in groups.values() if g.status is GroupStatus.UNLOCATED]
    print(f"registered sources: {len(srcs)}")
    print(f"  rights UNDETERMINED (export gate fails closed): {len(undetermined)}")
    print(f"  ingestion_permitted=true: {len(permitted)}")
    print(f"  loadable now (permitted + compact + custody): {len(loadable)}")
    print(
        f"local groups: {len(groups)} (unlocated {len(unlocated)}, disappeared {len(disappeared)})"
    )
    print(f"national partners: {len(orgs)}")
    # The flip-metadata rule (P21.1, SIG-INGEST-028/038, SIG-LIC-001/009): a row
    # flipped to ingestion_permitted=true is invalid without its review metadata.
    violations = review_metadata_violations(srcs)
    if violations:
        for msg in violations:
            print(f"VALIDATION FAILED: {msg}")
        return 1
    # F-330 (P35.6, S1): the Part VIII layer-field denylist is a registration
    # refusal enforced over every committed ArcGIS/Socrata target row — a
    # target whose `observed_fields`/`out_fields` name a denied field fails
    # validation (it was registered before the denylist, or written around it).
    from .dot_511 import target_table
    from .field_denylist import target_field_violations

    field_violations: list[str] = []
    for row in target_table().get("targets", []):
        for hit in target_field_violations(row):
            field_violations.append(
                f"target {row.get('id')!r} (source {row.get('source_id')!r}): {hit}"
            )
    if field_violations:
        for msg in field_violations:
            print(f"VALIDATION FAILED: F-330 field denylist: {msg}")
        return 1
    # PKG-07 (P35.15a, F-329/F-523): every camera-registry target row must
    # declare a `technology` slug that is an ACTIVE member of
    # ontology/vocab/technology.yaml — a missing or out-of-registry slug fails
    # closed here and at target expansion/emit; the default is never silently
    # `traffic_camera`.
    from .dot_511 import target_technology_violations

    tech_violations = target_technology_violations()
    if tech_violations:
        for msg in tech_violations:
            print(f"VALIDATION FAILED: PKG-07 technology slug: {msg}")
        return 1
    # SIG-GEO-003 (P36.4 / ACQ-08): a target's declared `geometry_kind` must be
    # a member of the ontology's GeometryKind enum (point|line|area, P36.3) —
    # a row naming a shape the vocabulary does not know fails closed here and
    # at target expansion/emit, never silently point-flattened.
    from .dot_511 import target_geometry_violations

    geometry_violations = target_geometry_violations()
    if geometry_violations:
        for msg in geometry_violations:
            print(f"VALIDATION FAILED: SIG-GEO-003 geometry kind: {msg}")
        return 1
    # P36.5 / ACQ-09 (I9a NEW-2, P4): a target's declared status disposition
    # must be a member of the closed set and a removal ledger must carry its
    # declared removal-value vocabulary; the declared coordinate precision
    # must be a member too — a broken declaration fails closed here and at
    # expansion/emit, never a silently un-bounded or falsely bounded emit.
    from .dot_511 import target_status_violations

    status_violations = target_status_violations()
    if status_violations:
        for msg in status_violations:
            print(f"VALIDATION FAILED: P36.5 status/coordinate semantics: {msg}")
        return 1
    # P36.6 / ACQ-10 (I8 NEW-7): an aggregate target's declaration must be a
    # complete member of the closed vocabulary — subject/period/count columns
    # as bare identifiers, a declared period kind and count function, and a
    # measure — never an expression smuggled into the committed query text or
    # a guessed grouping surface.
    from .dot_511 import target_aggregate_violations

    aggregate_violations = target_aggregate_violations()
    if aggregate_violations:
        for msg in aggregate_violations:
            print(f"VALIDATION FAILED: P36.6 aggregate declaration: {msg}")
        return 1
    # §26 rule 7 (P36.1a): the committed host-level opt-out register must parse
    # under the fail-closed rules — a malformed row is a validation failure,
    # never a silent "no opt-outs".
    from .opt_out import OptOutRegisterError, load_register

    try:
        opt_out = load_register()
    except OptOutRegisterError as exc:
        print(f"VALIDATION FAILED: opt-out register malformed: {exc}")
        return 1
    print(f"  host-level opt-out register: {len(opt_out.entries)} entr(ies)")
    # P35.66 (SIG-PUB-005/013): the declared residential-parcel signal must
    # parse under the fail-closed integrity rules — a malformed ring, an
    # out-of-range position, or a parcel outside every declared coverage
    # region is a config defect, never a "clean" screening outcome. The signal
    # lives in `policy/data` (the package that owns the emit-path screen), so
    # the load goes through its own loader; a malformed file raises
    # ParcelSignalError — recorded as a validation failure, never a crash.
    from policy.parcel_screen import ParcelSignalError, declared_parcel_signal

    try:
        parcel_signal = declared_parcel_signal()
    except ParcelSignalError as exc:
        print(f"VALIDATION FAILED: P35.66 parcel signal: {exc}")
        return 1
    print(
        f"  declared residential-parcel signal: OK ({parcel_signal.stamp}; "
        f"{len(parcel_signal.coverage)} coverage region(s), "
        f"{len(parcel_signal.parcels)} parcel(s) — coverage boundary recorded)"
    )
    # P32.12 (SIG-ACQ-003): the frozen dossier field crosswalk must resolve
    # every configured field to an existing ontology predicate, or carry a
    # recorded scoped amendment — never an ad-hoc term.
    from .dossier_documents import check_crosswalk

    crosswalk_violations = check_crosswalk()
    if crosswalk_violations:
        for msg in crosswalk_violations:
            print(f"VALIDATION FAILED: {msg}")
        return 1
    # P36.8 / ACQ-12 (SIG-ONTO-021): the mandated-disclosure vocab's
    # [technology_map] values and every adapter-declared slug
    # (default_technology / entries[].technology) must be ACTIVE members of
    # ontology/vocab/technology.yaml; entry kinds and use_fields predicates
    # must be members of their closed sets — a broken declaration fails
    # closed here and at emit, never a guessed or silently un-typed slug.
    from .government_mandated_disclosure import technology_map_violations

    map_violations = technology_map_violations()
    if map_violations:
        for msg in map_violations:
            print(f"VALIDATION FAILED: P36.8 technology map: {msg}")
        return 1
    print("connectors registry self-checks OK")
    return 0


def _stages() -> int:
    for i, name in enumerate(stage_names(), start=1):
        print(f"{i}. {name}")
    return 0


def _list_connectors() -> int:
    names = sorted(registered_connectors())
    if not names:
        print("no source connectors registered yet (P04.1 is framework-only; see P04.2/P04.3)")
        return 0
    for name in names:
        print(name)
    return 0


def _gate(source_id: str) -> int:
    try:
        get(source_id)
    except KeyError:
        print(f"unknown source id: {source_id!r}")
        return 2
    ok = is_loadable(source_id)
    print(f"source {source_id!r}: {'LOADABLE' if ok else 'REFUSED'} (SIG-INGEST-014/028)")
    return 0 if ok else 1


def _export_check() -> int:
    # SIG-LIC-010: compute the export licence for each compartment's sources; any
    # incompatibility inside a compartment fails the build (non-zero exit).
    by_compartment: dict[str, list[str]] = {name: [] for name in compartments()}
    licence_to_compartment = {c["license"]: name for name, c in compartments().items()}
    for src in sources():
        if src.rights.spdx.strip().upper() == "UNDETERMINED":
            continue
        compartment = licence_to_compartment.get(source_export_license(src))
        if compartment is not None:
            by_compartment[compartment].append(src.id)
    failures = 0
    for compartment, ids in by_compartment.items():
        if not ids:
            continue
        try:
            licence = assert_export_compatible(ids)
            print(f"compartment {compartment!r}: {len(ids)} source(s) -> {licence}")
        except LicenseIncompatibilityError as exc:
            failures += 1
            print(f"compartment {compartment!r}: INCOMPATIBLE — {exc}")
    if failures:
        print(f"export-check FAILED: {failures} incompatible compartment(s) (SIG-LIC-010)")
        return 1
    print("export-check OK: every compartment exports under a single licence (SIG-LIC-010)")
    return 0


def _review_status(source_id: str | None) -> int:
    # Per-source gate breakdown (SIG-INGEST-014/028, §22.4, §8.4). With --source,
    # print the five gate fields; with no arg, print the same counts as `validate`
    # plus flip-ready and loadable-now.
    if source_id is not None:
        try:
            record = get(source_id)
        except KeyError:
            print(f"unknown source id: {source_id!r}")
            return 2
        bd = gate_breakdown(record)
        print(f"source {source_id!r}:")
        print(
            f"  ingestion_permitted={bd.ingestion_permitted} compact={bd.compact_ok} "
            f"custody={bd.custody_ok} rights={bd.rights_present} reviewed-by={bd.reviewed_by} "
            f"reserved={bd.rights_reserved}"
        )
        print(f"  flip-ready: {is_flip_ready(record)}")
        print(f"  loadable now: {bd.loadable}")
        return 0

    srcs = sources()
    permitted = [s for s in srcs if s.ingestion_permitted]
    loadable = [s for s in srcs if is_loadable(s)]
    ready = flip_ready(srcs)
    print(f"registered sources: {len(srcs)}")
    print(f"  ingestion_permitted=true: {len(permitted)}")
    print(f"  flip-ready: {len(ready)}")
    print(f"  loadable now: {len(loadable)}")
    for s in ready:
        print(f"    flip-ready: {s.id}")
    return 0


def _load_seed(args: argparse.Namespace) -> int:
    """Drive ``runner.run_seed`` — the packaged seed through the same pipeline+gate."""
    from .runner import run_seed
    from .seeds import SeedNotRegistered
    from .stages import ContentDrift

    if args.sink == "pg" and not args.dsn:
        print("--sink pg requires --dsn")
        return 2
    try:
        report = run_seed(
            args.source,
            connector_name=args.connector,
            sink_kind=args.sink,
            dsn=args.dsn,
        )
    except SeedNotRegistered as missing:
        print(f"NO SEED (exit 4): {missing}")
        return 4
    except ContentDrift as drift:
        # The committed asset's shape drifted from the reviewed contract: fail
        # loud — a seed's value is that it is reviewed data (SIG-INGEST-049f).
        print(f"CONTENT DRIFT (exit 5): {drift}")
        return 5
    claims = [r for r in report.claims if r.get("record_kind") == "claim"]
    print(
        f"seed {args.source!r}: {len(claims)} claim row(s) asserted "
        f"(asserted={report.asserted}) via the packaged asset — the same gate + "
        "pipeline as every source; the registry row stays ingestion_permitted=false."
    )
    return 0


def _technology_backfill(args: argparse.Namespace) -> int:
    """Drive ``db.technology_backfill`` — the P35.15b append-only backfill.

    The declared slug map is read from the SAME committed target registry the
    emit path reads (``dot_511.target_table`` → ``declared_technologies``), so
    the backfill and the emitter can never disagree; a registry that fails the
    PKG-07 self-check refuses before any DSN is touched (fail closed —
    ``sig-connectors validate`` carries the same rule).
    """
    import json as _json

    from .dot_511 import declared_technologies, target_table, target_technology_violations
    from .sinks import resolve_commit_chunk_size

    violations = target_technology_violations()
    if violations:
        for msg in violations:
            print(f"VALIDATION FAILED: PKG-07 technology slug: {msg}")
        return 1
    try:
        commit_chunk_size = resolve_commit_chunk_size(args.commit_chunk_size)
    except ValueError as bad:
        print(f"invalid commit chunk size: {bad}")
        return 2
    licenses = {
        (str(row.get("source_id") or ""), str(row.get("id") or "")): str(
            row.get("license_spdx") or ""
        )
        for row in target_table().get("targets", [])
    }
    from db.technology_backfill import run_backfill

    from .sinks import _registry_rights

    report = run_backfill(
        args.dsn,
        declared=declared_technologies(),
        licenses=licenses,
        apply=args.apply,
        code_commit=args.code_commit,
        commit_chunk_size=commit_chunk_size,
        rights_resolver=_registry_rights,
    )
    print(_json.dumps(report, indent=2, sort_keys=True, default=str))
    return 1 if report.get("refused") else 0


def _geometry_corrections(args: argparse.Namespace) -> int:
    """Drive ``db.geometry_corrections`` — the P35.16 append-only pass.

    The declared scopes resolve from the SAME committed
    ``sig.geometry-corrections/1`` artifact + registry/extent tables the
    emit detectors read (``dot_511.geometry_correction_scopes`` /
    ``scan_extents``), so the correction pass and the ingest detectors can
    never disagree on a bound; a registry that fails the P35.16 self-check
    refuses before any DSN is touched (fail closed).
    """
    import json as _json

    from .dot_511 import (
        geometry_correction_scopes,
        scan_extents,
        target_geometry_violations,
    )
    from .sinks import resolve_commit_chunk_size

    violations = target_geometry_violations()
    if violations:
        for msg in violations:
            print(f"VALIDATION FAILED: P35.16 geometry declarations: {msg}")
        return 1
    try:
        commit_chunk_size = resolve_commit_chunk_size(args.commit_chunk_size)
    except ValueError as bad:
        print(f"invalid commit chunk size: {bad}")
        return 2
    from db.geometry_corrections import run_corrections

    from .sinks import _registry_rights

    report = run_corrections(
        args.dsn,
        scopes=geometry_correction_scopes(),
        scan_extents=scan_extents(),
        apply=args.apply,
        code_commit=args.code_commit,
        commit_chunk_size=commit_chunk_size,
        rights_resolver=_registry_rights,
    )
    print(_json.dumps(report, indent=2, sort_keys=True, default=str))
    return 1 if report.get("refused") else 0


def _redact_queue(
    args: argparse.Namespace,
) -> tuple[ReviewQueue | PgReviewQueue | None, Path | None]:
    """The review mechanism for the redact verbs: a JSON-file queue, or the PG
    ``review_item``/``review_decision`` tables behind ``--dsn``. Returns
    ``(queue, path)`` — ``path`` is where a JSON queue serialises back."""
    import json as _json
    from pathlib import Path as _Path

    from resolution.review_queue import ReviewQueue

    if args.dsn:
        from resolution.review_pg import PgReviewQueue

        return PgReviewQueue.from_dsn(args.dsn), None
    if not args.queue_json:
        return None, None
    path = _Path(args.queue_json)
    queue = ReviewQueue.from_dict(_json.loads(path.read_text())) if path.exists() else ReviewQueue()
    return queue, path


def _redact_store(capture_dir: str) -> OcflCaptureStore:
    from evidence.ocfl import OcflStore
    from evidence.storage import LocalFileStore

    from .capture_ocfl import OcflCaptureStore

    return OcflCaptureStore(OcflStore(LocalFileStore(capture_dir)))


def _redact_propose(args: argparse.Namespace) -> int:
    """Enqueue a redaction proposal for human review (P36.15, step 1)."""
    import json as _json
    import sys

    from evidence.redaction import RedactionError, RedactionSpan

    from .redaction_pipeline import enqueue_proposal, propose_redaction

    queue, path = _redact_queue(args)
    if queue is None:
        print("a review queue is required: --queue-json FILE or --dsn DSN")
        return 2
    spans = None
    if args.span:
        try:
            spans = tuple(
                RedactionSpan(start=int(s.split(":")[0]), end=int(s.split(":")[1]))
                for s in args.span
            )
        except (ValueError, IndexError):
            print("--span takes 'start:end' code-point offsets")
            return 2
    store = _redact_store(args.capture_dir)
    if not store.has(args.parent_digest):
        print(f"no capture with digest {args.parent_digest} in {args.capture_dir}")
        return 4
    try:
        item = propose_redaction(
            parent_capture_id=args.parent_capture_id,
            parent_digest=args.parent_digest,
            parent_bytes=store.get(args.parent_digest),
            media_type=args.media_type,
            spans=spans,
            literals=args.text,
            method=args.method,
            version=args.version,
            scope_note=args.note,
        )
        inserted = enqueue_proposal(queue, item)
    except RedactionError as err:
        print(f"REDACTION REFUSED: {err}", file=sys.stderr)
        return 3
    if path is not None:
        import json as _json2

        from resolution.review_queue import ReviewQueue as _ReviewQueue

        assert isinstance(queue, _ReviewQueue)  # a file path means the JSON queue
        path.write_text(_json2.dumps(queue.to_dict(), indent=2, sort_keys=True))
    print(
        _json.dumps(
            {"item_id": item.item_id, "inserted": inserted, "item": item.to_row()},
            indent=2,
            sort_keys=True,
            default=str,
        )
    )
    print("next: a human records accept/reject on the queue item; then redact-apply.")
    return 0


def _redact_apply(args: argparse.Namespace) -> int:
    """Apply a reviewed redaction — derivative OCFL object + record (P36.15)."""
    import json as _json
    import sys

    from evidence.redaction import RedactionError, RedactionReviewRequired

    from .redaction_pipeline import run_redaction

    queue, _path = _redact_queue(args)
    if queue is None:
        print("a review queue is required: --queue-json FILE or --dsn DSN")
        return 2
    store = _redact_store(args.capture_dir)
    try:
        result = run_redaction(store, queue, item_id=args.item)
    except RedactionReviewRequired as missing:
        # The gate-style refusal: no recorded human accept → exit 3 (like
        # `run --mode live` on a non-green source) — a redaction attempted
        # without its review fails loudly, never silently.
        print(f"REDACTION REFUSED (exit 3): {missing}", file=sys.stderr)
        return 3
    except RedactionError as err:
        print(f"REDACTION FAILED (exit 4): {err}", file=sys.stderr)
        return 4
    print(_json.dumps(result.to_row(), indent=2, sort_keys=True, default=str))
    return 0


def _run(args: argparse.Namespace) -> int:
    # Importing the package registers every source connector (SIG-INGEST-021).
    from pathlib import Path

    from .live_targets import NoLiveTargets
    from .net import RobotsDisallowed, RobotsUnretrievable
    from .runner import LiveGateRefused, RunMode, run_source
    from .sinks import resolve_commit_chunk_size
    from .stages import ContentDrift

    if args.sink == "pg" and not args.dsn:
        print("--sink pg requires --dsn")
        return 2
    try:
        commit_chunk_size = resolve_commit_chunk_size(args.commit_chunk_size)
    except ValueError as bad:
        print(f"invalid commit chunk size: {bad}")
        return 2
    try:
        report = run_source(
            args.source,
            mode=RunMode(args.mode),
            connector_name=args.connector,
            fixture=Path(args.fixture) if args.fixture else None,
            media_type=args.media_type,
            kind=args.kind,
            sink_kind=args.sink,
            dsn=args.dsn,
            capture_dir=Path(args.capture_dir) if args.capture_dir else None,
            wacz=args.wacz,
            commit_chunk_size=commit_chunk_size,
        )
    except LiveGateRefused as refused:
        # A live fetch on a non-green source is refused before any egress
        # (SIG-INGEST-028); exit 3 with the gate reasons (LD-X08 can never recur).
        print(f"REFUSED: live fetch for source {refused.source_id!r} is gated (exit 3):")
        for reason in refused.reasons:
            print(f"  - {reason}")
        return 3
    except NoLiveTargets as missing:
        # A green source with no configured live target: config gap, not a fetch.
        print(f"NO LIVE TARGETS (exit 4): {missing}")
        return 4
    except ContentDrift as drift:
        # The fetch succeeded but the content no longer matches the parser's shape
        # (P25.1 / ADR-082): fail loud + recorded (a content_drift fetch record),
        # never garbage or a silent zero.
        print(f"CONTENT DRIFT (exit 5): {drift}")
        print("  recorded in the fetch record; no garbage emitted (pages before the drift may")
        print("  have committed — the fetch record and the run's completion count them).")
        return 5
    except (RobotsUnretrievable, RobotsDisallowed) as refused:
        # A politeness refusal (SIG-INGEST-012): under GL-GATE-08 / ADR-088 the
        # shared PoliteFetcher never raises these (robots verdicts are recorded
        # as robots_disregarded, never enforced); this path remains for
        # non-standard fetcher implementations that still refuse.
        print(f"POLITENESS REFUSAL (exit 6): {refused}")
        print("  recorded in the fetch record; the refusal is never bypassed.")
        return 6
    summary = (
        f"source {args.source!r} [{args.mode}] via connector {report.connector!r}: "
        f"{report.emitted} claim(s), {len(report.captures)} capture(s)"
    )
    if report.refusals:
        summary += f", {len(report.refusals)} politeness refusal(s) recorded"
    if report.diff is not None:
        summary += f", shadow diff changed={report.diff.changed_count}"
    if report.replay_reproducible is not None:
        summary += f", replay_reproducible={report.replay_reproducible}"
    print(summary)
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the `connectors` CLI. Returns a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "run":
        return _run(args)
    if args.command == "load-seed":
        return _load_seed(args)
    if args.command == "validate":
        return _validate()
    if args.command == "stages":
        return _stages()
    if args.command == "list-connectors":
        return _list_connectors()
    if args.command == "gate":
        return _gate(args.source)
    if args.command == "export-check":
        return _export_check()
    if args.command == "review-status":
        return _review_status(args.source)
    if args.command == "attribution-correction-list":
        import json as _json
        from pathlib import Path as _Path

        from .corrections import corrections_list, write_corrections_list

        if args.out:
            path = write_corrections_list(_Path(args.out))
            print(f"wrote {path}")
        else:
            print(_json.dumps(corrections_list(), indent=2, sort_keys=True))
        return 0
    if args.command == "source-lineage-list":
        import json as _json
        from pathlib import Path as _Path

        from .lineage_declarations import declarations_list, write_declarations_list

        if args.out:
            path = write_declarations_list(_Path(args.out))
            print(f"wrote {path}")
        else:
            print(_json.dumps(declarations_list(), indent=2, sort_keys=True))
        return 0
    if args.command == "rekey-personal-ids":
        from . import personal_id_rekey

        argv_tail = []
        if args.apply:
            argv_tail.append("--apply")
        for opt in ("handles", "report", "restricted_out"):
            val = getattr(args, opt)
            if val:
                argv_tail += [f"--{opt.replace('_', '-')}", val]
        return personal_id_rekey.main(argv_tail)
    if args.command == "technology-backfill":
        return _technology_backfill(args)
    if args.command == "geometry-corrections":
        return _geometry_corrections(args)
    if args.command == "redact-propose":
        return _redact_propose(args)
    if args.command == "redact-apply":
        return _redact_apply(args)
    parser.print_help()
    return 0
