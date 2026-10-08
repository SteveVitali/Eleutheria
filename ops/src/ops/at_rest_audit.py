# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""at_rest_audit — the P34.49 Part VIII at-rest audit (F-406, ADR-185,
SIG-PUB-002/003/011–014a, SIG-STORE-025, SIG-GOV-007/017, ADR-189).

The scan/seal machinery for the at-rest question: *does the evidence store
hold material SIG may not hold?* Legs:

* **L1 — read-only scan** (``sig-ops at-rest scan``): walks the OCFL capture
  root (the exec host's read-only mount, or a local root for offline runs),
  applies every declared ``sig.at-rest-audit-decl/1`` rule
  (:mod:`evidence.screen`) to each capture's bytes, and emits

  - ``sig.at-rest-audit/1`` — the counts-only report: objects scanned, hits
    per class per source, SIG-PUB-002 category counts. A field name, value,
    or captured string NEVER appears in it.
  - ``sig.at-rest-flagged/1`` — the restricted-side companion: the flagged
    objects keyed by object id + digest + (when a spine join is available)
    capture/artifact ids + the classes that fired. Restricted only — the
    seal leg's input.

* **L2 — protective seal** (``sig-ops at-rest seal-plan`` renders,
  ``seal-apply`` writes): gated on an L1 report. Produces

  - append-only ``capture_seal`` rows (spine) + artifact-level
    ``withhold``/``restrict`` ``publication_disposition`` rows
    (insert-only — the registry's own write path, never an UPDATE),
  - the ``sig.seal-deny/1`` serving/export deny set (a new object VERSION on
    the restricted bucket — never an in-place rewrite),
  - the counts-only ``sig.pub002-listing/1`` for the operator's purge
    decision (WV-11, ADR-181 control 2, ADR-189).

**Nothing here deletes or overwrites a byte.** Seal = suppress on every
publishable path; true purge stays the operator's in-ticket action.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tomllib
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NoReturn

from evidence.seal import DenyEntry, build_deny_set
from evidence.storage import BlobStore, LocalFileStore

from evidence import screen

SCHEMA = screen.SCHEMA_DECL
REPORT_SCHEMA = screen.SCHEMA_REPORT
FLAGGED_SCHEMA = screen.SCHEMA_FLAGGED
SEAL_PLAN_SCHEMA = screen.SCHEMA_SEAL_PLAN
PUB002_LISTING_SCHEMA = "sig.pub002-listing/1"

DEFAULT_DECLARATION = Path(__file__).resolve().parents[3] / "ops" / "at_rest_audit.toml"

#: The OCFL object-id prefix the capture store uses (connectors.capture_ocfl).
CAPTURE_ID_PREFIX = "sig:capture:"

#: Disposition mapping for a seal: F-406/I7 classes → policy_restriction;
#: a PUB-002-only flag → suppressed. Disposition is always ``withhold`` —
#: the strongest non-deleting suppress the registry carries.
F406_I7_REASON = "policy_restriction"
PUB002_REASON = "suppressed"


def _fail(msg: str) -> NoReturn:
    raise ValueError(msg)


def _utcnow() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _object_key_root(store_key: str) -> str | None:
    """``aa/bb/cc/<encid>/inventory.json`` → the object root key, else None."""
    parts = store_key.split("/")
    if len(parts) >= 2 and parts[-1] == "inventory.json" and len(parts[-2]) > 0:
        return "/".join(parts[:-1])
    return None


def _decode_object_id(encid: str) -> str:
    return urllib.parse.unquote(encid)


def load_declaration(path: str | Path | None = None) -> screen.ScreenDeclaration:
    """Parse ``sig.at-rest-audit-decl/1`` into a validated ScreenDeclaration."""
    p = Path(path) if path else DEFAULT_DECLARATION
    try:
        raw = tomllib.loads(p.read_text(encoding="utf-8"))
    except OSError as e:
        _fail(f"at-rest declaration unreadable: {e}")
    if raw.get("schema") != SCHEMA:
        _fail(f"{p}: schema must be {SCHEMA!r}")

    classes: list[screen.ClassRule] = []
    for i, c in enumerate(raw.get("class") or []):
        if not isinstance(c, dict):
            _fail(f"{p}: class {i} must be a table")
        cid = str(c.get("id") or _fail(f"{p}: class {i} missing id"))
        members = tuple(str(m) for m in (c.get("members") or []))
        rules: list[screen.Rule] = []
        for j, r in enumerate(c.get("rules") or []):
            rules.append(
                screen.Rule(
                    kind=str(r.get("kind") or _fail(f"{p}: class {i} rule {j} missing kind")),
                    fields=tuple(str(f) for f in (r.get("fields") or [])),
                    patterns=tuple(str(x) for x in (r.get("patterns") or [])),
                    shapes=tuple(str(s) for s in (r.get("shapes") or [])),
                    applies=tuple(str(a) for a in (r.get("applies") or [])),
                )
            )
        classes.append(screen.ClassRule(class_id=cid, rules=tuple(rules), members=members))
    outputs = raw.get("outputs") or {}
    decl = screen.ScreenDeclaration(
        classes=tuple(classes),
        report_prefix=str(outputs.get("report_prefix") or "ops/probes/at-rest/"),
        deny_set_object=str(outputs.get("deny_set_object") or "ops/seal/deny-set.json"),
        pub002_object=str(outputs.get("pub002_object") or "ops/seal/pub002-listing.json"),
    )
    screen.validate_declaration(decl)
    return decl


# --- the L1 scan ----------------------------------------------------------------


@dataclass
class CaptureRow:
    """The spine-side join row for one stored capture (from ``evidence_capture``
    × ``evidence_artifact`` — read-only)."""

    capture_id: str
    artifact_id: str
    source_id: str
    storage_tier: str


def fetch_capture_rows(dsn: str) -> dict[str, list[CaptureRow]]:
    """content_digest → capture rows (one OCFL object can back N capture rows —
    dedup by content). Read-only; ``sig_audit``'s §37 surface covers it."""
    import psycopg

    rows: dict[str, list[CaptureRow]] = {}
    with psycopg.connect(dsn, autocommit=True) as conn:
        cur = conn.execute(
            "SELECT ec.content_digest, ec.capture_id::text, ec.artifact_id::text,"
            "       ea.source_id, ec.storage_tier::text"
            "  FROM evidence_capture ec"
            "  JOIN evidence_artifact ea ON ea.artifact_id = ec.artifact_id"
        )
        for digest, cid, aid, sid, tier in cur.fetchall():
            rows.setdefault(str(digest), []).append(
                CaptureRow(
                    capture_id=str(cid),
                    artifact_id=str(aid),
                    source_id=str(sid or ""),
                    storage_tier=str(tier),
                )
            )
    return rows


def fetch_sealed_captures(dsn: str) -> set[str]:
    """capture_ids already protectively sealed (``capture_seal``, insert-only
    registry). A spine without the change yields the empty set — the seal
    leg reports it not_evaluable, never fabricates."""
    import psycopg

    with psycopg.connect(dsn, autocommit=True) as conn:
        has = conn.execute("SELECT to_regclass('capture_seal') IS NOT NULL").fetchone()
        if not (has and has[0]):
            return set()
        cur = conn.execute(
            "SELECT DISTINCT capture_id::text FROM capture_seal"
            " WHERE capture_currently_sealed(capture_id)"
        )
        return {str(r[0]) for r in cur.fetchall()}


def _capture_payload(store: BlobStore, root: str, inventory: dict) -> tuple[bytes, str] | None:
    """The head version's ``capture`` + ``metadata.json`` pair, if present."""
    head = inventory.get("head")
    versions = inventory.get("versions") or {}
    state = (versions.get(head) or {}).get("state") or {}
    manifest = inventory.get("manifest") or {}

    def _resolve(logical: str) -> bytes | None:
        for digest, paths in state.items():
            if logical in paths:
                content = (manifest.get(digest) or [None])[0]
                if content is None:
                    return None
                key = f"{root}/{content}" if root else content
                try:
                    return store.get(key)
                except Exception:
                    return None
        return None

    payload = _resolve("capture")
    if payload is None:
        return None
    meta_raw = _resolve("metadata.json")
    media_type = "application/octet-stream"
    if meta_raw:
        try:
            meta = json.loads(meta_raw)
            media_type = str(meta.get("media_type") or media_type)
        except Exception:
            pass
    return payload, media_type


def scan_store(
    store: BlobStore,
    decl: screen.ScreenDeclaration,
    *,
    capture_rows: dict[str, list[CaptureRow]] | None = None,
    sealed: set[str] | None = None,
    generated_at: str | None = None,
    store_label: str = "",
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Scan every OCFL capture object under the root. Returns
    (``sig.at-rest-audit/1`` report, ``sig.at-rest-flagged/1`` sidecar) —
    counts + ids only."""
    capture_rows = capture_rows or {}
    sealed = sealed or set()
    objects_listed = 0
    scanned = 0
    unreadable = 0
    non_capture = 0
    per_class: dict[str, dict[str, Any]] = {
        c: {"objects": 0, "hits": 0, "by_source": {}} for c in screen.ALL_CLASSES
    }
    flagged_entries: list[dict[str, Any]] = []

    inv_keys = sorted(
        k for k in store.list("") if _object_key_root(k) and k.endswith("inventory.json")
    )
    # Object roots are <a>/<b>/<c>/<encid>/inventory.json — keep only those.
    inv_keys = [k for k in inv_keys if len(k.split("/")) == 5]
    for key in inv_keys:
        root = _object_key_root(key)
        assert root is not None
        objects_listed += 1
        try:
            inventory = json.loads(store.get(key))
        except Exception:
            unreadable += 1
            continue
        object_id = str(inventory.get("id") or _decode_object_id(root.rsplit("/", 1)[-1]))
        if not object_id.startswith(CAPTURE_ID_PREFIX):
            non_capture += 1
            continue
        digest = object_id[len(CAPTURE_ID_PREFIX) :]
        got = _capture_payload(store, root, inventory)
        if got is None:
            unreadable += 1
            continue
        payload, media_type = got
        scanned += 1
        rows = capture_rows.get(digest) or []
        source_ids = sorted({r.source_id for r in rows if r.source_id}) or ["<unregistered>"]
        # Screen once per declared member-source the object backs — the
        # union of hits over the source set (the same bytes attributed to
        # several captures screen identically).
        union_hits: dict[str, int] = {}
        for sid in source_ids:
            hits = screen.screen_blob(payload, source_id=sid, media_type=media_type, decl=decl)
            for cid, n in hits.items():
                union_hits[cid] = max(union_hits.get(cid, 0), n)
        for cid, n in union_hits.items():
            c = per_class[cid]
            c["objects"] += 1
            c["hits"] += n
            for sid in source_ids:
                bs = c["by_source"].setdefault(sid, {"objects": 0, "hits": 0})
                bs["objects"] += 1
                bs["hits"] += n
        if union_hits:
            pub002 = sorted(c for c in union_hits if screen.is_pub002(c))
            flagged_entries.append(
                {
                    "object_id": object_id,
                    "digest": digest,
                    "source_ids": source_ids,
                    "classes": sorted(union_hits),
                    "pub002_categories": pub002,
                    "captures": [
                        {
                            "capture_id": r.capture_id,
                            "artifact_id": r.artifact_id,
                            "source_id": r.source_id,
                            "storage_tier": r.storage_tier,
                            "already_sealed": r.capture_id in sealed or r.storage_tier == "sealed",
                        }
                        for r in rows
                    ],
                }
            )

    report = {
        "schema": REPORT_SCHEMA,
        "generated_at": generated_at or _utcnow(),
        "store": store_label,
        "declaration": str(DEFAULT_DECLARATION.name),
        "objects": {
            "listed": objects_listed,
            "capture_objects": scanned + unreadable,
            "non_capture_objects": non_capture,
            "scanned": scanned,
            "unreadable": unreadable,
        },
        "classes": {
            cid: {
                "objects_flagged": v["objects"],
                "hits": v["hits"],
                "by_source": {
                    sid: {"objects": bs["objects"], "hits": bs["hits"]}
                    for sid, bs in sorted(v["by_source"].items())
                },
            }
            for cid, v in per_class.items()
            if v["objects"] or v["hits"]
        },
        "pub002_categories": {
            cid: {
                "objects_flagged": per_class[cid]["objects"],
                "hits": per_class[cid]["hits"],
            }
            for cid in screen.PUB002_CLASSES
        },
        "note": (
            "counts only — a field name, value, or captured string never "
            "appears in this report (the counts-only contract, ADR-185)"
        ),
    }
    flagged = {
        "schema": FLAGGED_SCHEMA,
        "generated_at": report["generated_at"],
        "entries": flagged_entries,
        "note": "restricted — object/digest ids + class ids only; never field names or values",
    }
    return report, flagged


# --- the L2 seal --------------------------------------------------------------------


def build_seal_plan(
    flagged: dict[str, Any],
    *,
    report: dict[str, Any],
    generated_at: str | None = None,
) -> dict[str, Any]:
    """``sig.at-rest-seal-plan/1`` — the protective-seal plan over an L1
    flagged sidecar. Append-only artifacts only: capture_seal rows, artifact
    ``withhold`` dispositions, the deny set, the PUB-002 listing."""
    if flagged.get("schema") != FLAGGED_SCHEMA:
        _fail(f"flagged sidecar schema must be {FLAGGED_SCHEMA!r}")
    if report.get("schema") != REPORT_SCHEMA:
        _fail(f"audit report schema must be {REPORT_SCHEMA!r}")
    entries: list[dict[str, Any]] = []
    deny_captures: list[dict[str, Any]] = []
    pub002_cat_objects: dict[str, int] = {c: 0 for c in screen.PUB002_CLASSES}
    skipped_sealed = 0
    for e in flagged["entries"]:
        classes = [str(c) for c in e["classes"]]
        pub002 = [str(c) for c in e.get("pub002_categories") or []]
        for c in pub002:
            pub002_cat_objects[c] = pub002_cat_objects.get(c, 0) + 1
        caps = [c for c in e.get("captures") or [] if not c.get("already_sealed")]
        skipped_sealed += len(e.get("captures") or []) - len(caps)
        if not caps and not e.get("captures"):
            # An object with no spine row (pre-spine or store-only): the deny
            # set still refuses it by digest.
            caps = []
        captures_out = [
            {"capture_id": c["capture_id"], "artifact_id": c["artifact_id"]} for c in caps
        ]
        reason = PUB002_REASON if all(screen.is_pub002(c) for c in classes) else F406_I7_REASON
        entries.append(
            {
                "object_id": e["object_id"],
                "digest": e["digest"],
                "rules": classes,
                "reason_category": reason,
                "disposition": "withhold",
                "captures": captures_out,
            }
        )
        for c in caps:
            deny_captures.append({"kind": "capture", "id": c["capture_id"], "rules": classes})
        deny_captures.append({"kind": "digest", "id": e["digest"], "rules": classes})

    plan = {
        "schema": SEAL_PLAN_SCHEMA,
        "generated_at": generated_at or _utcnow(),
        "audit_report_generated_at": report.get("generated_at"),
        "entries": entries,
        "deny_entries": deny_captures,
        "counts": {
            "flagged_objects": len(flagged["entries"]),
            "captures_to_seal": sum(len(e["captures"]) for e in entries),
            "already_sealed_skipped": skipped_sealed,
            "artifacts_to_withhold": len(
                {c["artifact_id"] for e in entries for c in e["captures"]}
            ),
            "pub002_category_objects": pub002_cat_objects,
        },
        "note": (
            "protective suppression only — seal records + withhold dispositions "
            "+ the deny set. No byte is deleted or overwritten; true purge is "
            "the operator's WV-11 action (ADR-181/189), never this leg."
        ),
    }
    return plan


def build_pub002_listing(
    plan: dict[str, Any], *, generated_at: str | None = None
) -> dict[str, Any]:
    """``sig.pub002-listing/1`` — the counts-only categorical listing for the
    operator's purge decision. Categories × object/capture counts; digests of
    the flagged objects are listed (existence proof), never field material."""
    cat_counts = plan["counts"]["pub002_category_objects"]
    objects: dict[str, list[str]] = {c: [] for c in screen.PUB002_CLASSES}
    # Per-category object digests — the operator's existence checklist.
    for e in plan["entries"]:
        for c in e["rules"]:
            if screen.is_pub002(c):
                objects[c].append(e["digest"])
    return {
        "schema": PUB002_LISTING_SCHEMA,
        "generated_at": generated_at or _utcnow(),
        "audit_report_generated_at": plan.get("audit_report_generated_at"),
        "categories": {
            c: {"objects": cat_counts.get(c, 0), "digests": sorted(set(objects[c]))}
            for c in screen.PUB002_CLASSES
        },
        "note": (
            "counts + digests only — the operator's WV-11 purge checklist. "
            "The sealed material itself is never listed."
        ),
    }


def build_deny_doc(
    plan: dict[str, Any],
    *,
    generated_at: str,
    prior: dict[str, Any] | None = None,
    audit_report_object: str = "",
) -> dict[str, Any]:
    """The ``sig.seal-deny/1`` object body from a seal plan."""
    entries = [
        DenyEntry(kind=str(e["kind"]), id=str(e["id"]), rules=tuple(e["rules"]))
        for e in plan["deny_entries"]
    ]
    return build_deny_set(
        entries,
        generated_at=generated_at,
        prior=prior,
        audit_report=audit_report_object,
        notes="P34.49 Part VIII at-rest audit — protective seal (ADR-185)",
    )


def apply_seal(
    dsn: str,
    plan: dict[str, Any],
    *,
    author: str,
    audit_report_object: str,
) -> dict[str, int]:
    """Write the plan's append-only records: ``capture_seal`` rows +
    artifact ``withhold`` dispositions. One transaction, insert-only.

    Pre-deploy (no ``capture_seal`` table) → fails loudly: the seal leg is
    gated on the hosted deploy, never partial."""
    import psycopg
    from db.dispositions import record_disposition
    from policy.eligibility import Disposition, ReasonCategory, TargetKind, new_disposition

    counts = {"seal_rows": 0, "dispositions": 0, "skipped_sealed": 0}
    with psycopg.connect(dsn) as conn, conn.transaction():
        has = conn.execute("SELECT to_regclass('capture_seal') IS NOT NULL").fetchone()
        if not (has and has[0]):
            _fail(
                "capture_seal is absent — the hosted seal_register deploy has "
                "not landed; the seal leg is not_evaluable, never partial"
            )
        already = {
            str(r[0])
            for r in conn.execute(
                "SELECT DISTINCT capture_id::text FROM capture_seal"
                " WHERE capture_currently_sealed(capture_id)"
            ).fetchall()
        }
        artifact_ids: set[str] = set()
        for e in plan["entries"]:
            for c in e["captures"]:
                cid = str(c["capture_id"])
                if cid in already:
                    counts["skipped_sealed"] += 1
                    continue
                conn.execute(
                    "INSERT INTO capture_seal"
                    "  (capture_id, content_digest, action, rules, author, audit_report)"
                    " VALUES (%s::uuid, %s, 'seal', %s::text[], %s, %s)",
                    (cid, e["digest"], list(e["rules"]), author, audit_report_object),
                )
                already.add(cid)
                counts["seal_rows"] += 1
                artifact_ids.add(str(c["artifact_id"]))
        for aid in sorted(artifact_ids):
            reason = (
                PUB002_REASON
                if all(
                    screen.is_pub002(r)
                    for e in plan["entries"]
                    for c in e["captures"]
                    if c["artifact_id"] == aid
                    for r in e["rules"]
                )
                else F406_I7_REASON
            )
            record_disposition(
                conn,
                new_disposition(
                    target_kind=TargetKind.ARTIFACT,
                    target_id=aid,
                    disposition=Disposition.WITHHOLD,
                    reason_category=ReasonCategory(reason),
                    authority="P34.49-at-rest-audit",
                    decided_by=author,
                    rationale=(
                        "protective seal — at-rest audit flagged this artifact's "
                        "capture (ADR-185; ids in the restricted deny set)"
                    ),
                ),
            )
            counts["dispositions"] += 1
    return counts


# --- CLI ----------------------------------------------------------------------


def _write_json(path: str | None, doc: dict[str, Any]) -> None:
    body = json.dumps(doc, indent=2, sort_keys=True) + "\n"
    if path:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(body, encoding="utf-8")
        print(f"wrote {path}")
    else:
        sys.stdout.write(body)


def _read_json(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _store_from_args(args: argparse.Namespace) -> tuple[BlobStore, str]:
    """A read-only store over the scan root: a local OCFL root dir, or a
    ``gs://bucket/prefix`` listing via :class:`ops.gcs.GcsBucket` (ADC)."""
    root = str(args.root or "")
    if root.startswith("gs://"):
        bucket, _, prefix = root[len("gs://") :].partition("/")
        store = _GcsBlobStore(bucket, prefix.strip("/"))
        return store, root
    if not root:
        _fail("at-rest scan needs --root <ocfl-root-dir | gs://bucket/prefix>")
    return LocalFileStore(root), root


class _GcsBlobStore:
    """A BlobStore over a GCS prefix — read-only (list/get)."""

    def __init__(self, bucket: str, prefix: str) -> None:
        from .gcs import GcsBucket

        self._bucket = GcsBucket(bucket)
        self._prefix = prefix

    def _strip(self, key: str) -> str:
        return key[len(self._prefix) :].lstrip("/") if self._prefix else key

    def get(self, key: str) -> bytes:
        full = f"{self._prefix}/{key}" if self._prefix else key
        return self._bucket.get_object(full)

    def exists(self, key: str) -> bool:
        try:
            self.get(key)
            return True
        except Exception:
            return False

    def list(self, prefix: str = "") -> list[str]:
        full = f"{self._prefix}/{prefix}" if self._prefix else prefix
        return sorted(self._strip(k) for k in self._bucket.list_objects(full))

    def put(self, key: str, data: bytes) -> None:
        raise NotImplementedError("the at-rest scan store is read-only")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="sig-ops at-rest",
        description=(
            "P34.49 Part VIII at-rest audit (F-406, ADR-185): the read-only "
            "capture-store scan (L1) + the protective seal plan/apply (L2) — "
            "counts-only records, no byte is ever deleted or overwritten."
        ),
    )
    sub = parser.add_subparsers(dest="at_rest_command", required=True)

    p_scan = sub.add_parser("scan", help="the L1 read-only scan → counts report + flagged sidecar")
    p_scan.add_argument("--declaration", default=None)
    p_scan.add_argument(
        "--root",
        default=os.environ.get("SIG_ATREST_ROOT", ""),
        help="the OCFL capture root — a local dir or gs://bucket/prefix",
    )
    p_scan.add_argument("--dsn", default=os.environ.get("SIG_DB_DSN", ""))
    p_scan.add_argument("--report", default=None, help="sig.at-rest-audit/1 out path")
    p_scan.add_argument("--flagged", default=None, help="sig.at-rest-flagged/1 out path")
    p_scan.add_argument(
        "--bucket",
        default=os.environ.get("SIG_EXEC_BUCKET", ""),
        help="also write the outputs under <report_prefix> on this bucket",
    )
    p_scan.add_argument("--at", default=None, help="ISO-UTC stamp (default: now)")

    p_plan = sub.add_parser("seal-plan", help="render the L2 seal plan over a flagged sidecar")
    p_plan.add_argument("--declaration", default=None)
    p_plan.add_argument("--flagged", required=True)
    p_plan.add_argument("--report", required=True, help="the L1 sig.at-rest-audit/1 report")
    p_plan.add_argument("--prior-deny", default=None, help="the recorded deny set (for version++)")
    p_plan.add_argument("--out", default=None)
    p_plan.add_argument("--deny-out", default=None, help="write the sig.seal-deny/1 body here")
    p_plan.add_argument("--pub002-out", default=None, help="write the sig.pub002-listing/1 here")
    p_plan.add_argument("--at", default=None)

    p_apply = sub.add_parser(
        "seal-apply",
        help="write the plan's append-only records (capture_seal + dispositions) over --dsn",
    )
    p_apply.add_argument("--plan", required=True)
    p_apply.add_argument("--dsn", default=os.environ.get("SIG_DB_DSN", ""))
    p_apply.add_argument("--author", required=True, help="the recorded operator id")
    p_apply.add_argument("--audit-report-object", default="", help="the L1 report's gs:// name")
    p_apply.add_argument(
        "--apply", action="store_true", help="actually write (default: dry-run counts)"
    )

    args = parser.parse_args(argv)
    try:
        decl = load_declaration(getattr(args, "declaration", None))
        if args.at_rest_command == "scan":
            store, label = _store_from_args(args)
            rows: dict[str, list[CaptureRow]] = {}
            sealed: set[str] = set()
            if args.dsn:
                rows = fetch_capture_rows(args.dsn)
                sealed = fetch_sealed_captures(args.dsn)
            report, flagged = scan_store(
                store,
                decl,
                capture_rows=rows,
                sealed=sealed,
                generated_at=args.at,
                store_label=label,
            )
            _write_json(args.report, report)
            _write_json(args.flagged, flagged)
            if args.bucket:
                from .gcs import GcsBucket

                b = GcsBucket(args.bucket)
                ts = str(report["generated_at"]).replace(":", "-")
                base = decl.report_prefix.rstrip("/")
                b.put_object(
                    f"{base}/{ts}/report.json",
                    (json.dumps(report, indent=2, sort_keys=True) + "\n").encode(),
                    content_type="application/json",
                )
                b.put_object(
                    f"{base}/{ts}/flagged.json",
                    (json.dumps(flagged, indent=2, sort_keys=True) + "\n").encode(),
                    content_type="application/json",
                )
                print(f"scan objects landed under gs://{args.bucket}/{base}/{ts}/")
            return 0
        if args.at_rest_command == "seal-plan":
            flagged = _read_json(args.flagged)
            report = _read_json(args.report)
            plan = build_seal_plan(flagged, report=report, generated_at=args.at)
            _write_json(args.out, plan)
            if args.deny_out:
                prior = _read_json(args.prior_deny) if args.prior_deny else None
                deny = build_deny_doc(plan, generated_at=plan["generated_at"], prior=prior)
                _write_json(args.deny_out, deny)
            if args.pub002_out:
                _write_json(
                    args.pub002_out,
                    build_pub002_listing(plan, generated_at=plan["generated_at"]),
                )
            return 0
        if args.at_rest_command == "seal-apply":
            if not args.dsn:
                _fail("seal-apply needs --dsn (SIG_DB_DSN)")
            plan = _read_json(args.plan)
            if not args.apply:
                print(json.dumps({"dry_run": True, "counts": plan["counts"]}))
                return 0
            counts = apply_seal(
                args.dsn,
                plan,
                author=args.author,
                audit_report_object=args.audit_report_object,
            )
            print(json.dumps({"applied": True, "counts": counts}))
            return 0
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
