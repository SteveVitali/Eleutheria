# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The raw-ok archive lane (P37.36 / R11-K13-TX-12 / J3 §6.9, SIG-TRANSP-020).

`D-J3-1 [B-19] = yes` decides the lane's whole scope, verbatim: **raw bytes
for raw-ok sources only, after the Part VIII byte screen**. The lane never
serves a broader set and never bypasses the screen:

* a capture publishes only when its source's recorded ``[redistribution]``
  lane is ``raw-ok`` and the source's Part VIII class is publishable —
  P8-1/P8-2/P8-4 and every ``restricted``/``derived-only``/``link-only``/
  ``unknown`` lane is ``never``, fail closed;
* served bytes pass :func:`evidence.screen.screen_blob` (the committed
  ``sig.at-rest-audit-decl/1`` rules) — **any** screen hit refuses the object,
  recorded as its class ids, never the flagged material;
* a P8-5/P8-6/P8-8 capture (the field-screen classes) is served only as a
  **field-allowlist re-serialisation recorded as a new capture**
  (SIG-PUB-015/016): new content-addressed bytes with a
  ``sig.raw-reserialisation/1`` record naming the parent digest, the method
  and version — the original bytes are **never** served, never mutated
  (append-only; the derivative is re-screened and a residual hit refuses);
* objects are content-addressed ``raw/<multihash>`` (the connectors' sha2-256
  multihash, SIG-EVID-004) with a per-object size cap — an oversized capture
  links out, never truncates;
* a withdrawal deletes the object from the mirror AND the origin, purges the
  CDN cache by URL, and leaves a tombstone record — rehearsed by
  ``ops.raw_withdrawal`` (D-J3-1's "delete, purge and tombstone", J3 §9.2).

The index ``raw/index.json`` is ``sig.raw-archive-index/1``: every served
object with digest, sha256, bytes, media type, capture/artifact/source ids,
the upstream licence, and (for a redacted object) the parent digest +
method/version. Skipped captures list only digests + reason classes — never
the withheld content, never a lane the rights record did not evidence.

The live leg — the hosted append-only archive write over the real capture
store plus the mirror/origin push — is **never pre-authorised** (OM-20:
archive write touching Part VIII-screened families): it runs only on the
operator's explicit verbatim go. The engineering here is exercised over
committed fixtures only; ``ops/gcp/raw-archive.sh`` is the staged runner and
``D-P37.36-1`` holds the queued leg ``prepared_not_executed``.
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from evidence.digest import multihash
from evidence.screen import ScreenDeclaration, screen_blob
from policy.transparency import (
    LANE_RAW_OK,
    PART_VIII_SEALED_CLASSES,
    find_secrets,
)

#: The index document schema.
INDEX_SCHEMA = "sig.raw-archive-index/1"
#: The re-serialisation record schema (one per redacted derivative).
RESERIALISATION_SCHEMA = "sig.raw-reserialisation/1"
#: The object path prefix on the distribution host.
RAW_PREFIX = "raw"
#: The per-object cap (J3 §6.9: ≤50 MB/object; larger → link-out).
MAX_OBJECT_BYTES = 50 * 1024 * 1024
#: The Part VIII classes whose originals are served only as redacted
#: re-serialisations (J3 §5.3/§6.9; D-J3-1).
FIELD_SCREEN_CLASSES: frozenset[str] = frozenset({"P8-5", "P8-6", "P8-8"})
#: The reserialisation method + version recorded on every derivative
#: (SIG-PUB-015 — a redaction names its method and version).
RESERIALISATION_METHOD = "field-allowlist"
RESERIALISATION_VERSION = "p37.36/1"

#: The verdict vocabulary — a capture's archive disposition is always a
#: member of this closed set (fail closed, never a guessed verdict).
VERDICT_SERVE = "serve"
VERDICT_RESERIALISE = "reserialise"
VERDICT_LINK_OUT = "link_out"
VERDICT_NEVER = "never"

#: The closed reason-class vocabulary a ``never``/``link_out`` verdict or a
#: skipped index row carries (digests + classes only — never content).
REASON_LANE = "lane_not_raw_ok"
REASON_SEALED = "part_viii_sealed_class"
REASON_SYNTHETIC = "synthetic_capture"
REASON_NO_BYTES = "bytes_not_stored"
REASON_BYTES_MISSING = "bytes_unavailable"
REASON_SCREEN = "part_viii_screen_hit"
REASON_SECRET = "secret_shaped_value"
REASON_UNPARSEABLE = "reserialisation_unparseable"
REASON_OVERSIZE = "over_object_cap"
REASON_CLASSES: frozenset[str] = frozenset(
    {
        REASON_LANE,
        REASON_SEALED,
        REASON_SYNTHETIC,
        REASON_NO_BYTES,
        REASON_BYTES_MISSING,
        REASON_SCREEN,
        REASON_SECRET,
        REASON_UNPARSEABLE,
        REASON_OVERSIZE,
    }
)


class RawArchiveError(RuntimeError):
    """A raw-archive contract violation — always loud, never partial."""


@dataclass(frozen=True)
class RawDecision:
    """The archive verdict for one capture row (lane × Part VIII × bytes)."""

    verdict: str  # VERDICT_* member
    reason_class: str | None = None  # REASON_* member when not ``serve``


@dataclass(frozen=True)
class ArchiveEntry:
    """One served ``raw/<multihash>`` object — an index row."""

    digest: str  # the content multihash (object name)
    path: str  # ``raw/<digest>``
    sha256: str
    byte_size: int
    media_type: str
    capture_id: str
    artifact_id: str
    source_id: str
    license: str
    retrieved_at: str | None
    kind: str  # ``original`` | ``redacted``
    parent_digest: str | None = None
    redaction_method: str | None = None
    redaction_version: str | None = None
    dropped_fields: tuple[str, ...] = ()

    def as_json(self) -> dict[str, Any]:
        row: dict[str, Any] = {
            "path": self.path,
            "digest": self.digest,
            "sha256": self.sha256,
            "byte_size": self.byte_size,
            "media_type": self.media_type,
            "capture_id": self.capture_id,
            "artifact_id": self.artifact_id,
            "source_id": self.source_id,
            "license": self.license,
            "retrieved_at": self.retrieved_at,
            "kind": self.kind,
        }
        if self.kind == "redacted":
            row["parent_digest"] = self.parent_digest
            row["redaction_method"] = self.redaction_method
            row["redaction_version"] = self.redaction_version
            row["dropped_fields"] = list(self.dropped_fields)
        return row


@dataclass(frozen=True)
class SkippedRow:
    """A ``never``/``link_out`` capture — digest + reason class only."""

    capture_id: str
    source_id: str
    digest: str | None
    reason_class: str
    screen_classes: tuple[str, ...] = ()

    def as_json(self) -> dict[str, Any]:
        row: dict[str, Any] = {
            "capture_id": self.capture_id,
            "source_id": self.source_id,
            "digest": self.digest,
            "reason_class": self.reason_class,
        }
        if self.screen_classes:
            row["screen_classes"] = list(self.screen_classes)
        return row


@dataclass
class ArchiveResult:
    """The build outcome: served entries, skipped rows, reserialisation
    records (the ``sig.raw-reserialisation/1`` set the live leg persists as
    new capture rows — append-only)."""

    entries: list[ArchiveEntry] = field(default_factory=list)
    skipped: list[SkippedRow] = field(default_factory=list)
    reserialisations: list[dict[str, Any]] = field(default_factory=list)


def decide_capture(
    capture: Mapping[str, Any],
    *,
    lane: str | None,
    part_viii_class: str | None,
    byte_cap: int = MAX_OBJECT_BYTES,
) -> RawDecision:
    """The J3 §5.3/§6.9 verdict for one recorded capture — fail closed.

    ``raw-ok`` is the only lane that may serve bytes (D-J3-1 verbatim); the
    P8-1/P8-2/P8-4 classes are never publishable; the P8-5/6/8 field-screen
    classes serve only the re-serialised derivative; an oversized capture
    links out. Anything else — a synthetic run record, a capture whose bytes
    were never stored, an unevidenced lane — is ``never``.
    """
    lane_v = str(lane or "").strip()
    p8 = str(part_viii_class or "").strip()
    if lane_v != LANE_RAW_OK:
        return RawDecision(VERDICT_NEVER, REASON_LANE)
    if p8 in PART_VIII_SEALED_CLASSES:
        return RawDecision(VERDICT_NEVER, REASON_SEALED)
    if str(capture.get("capture_classification") or "") == "synthetic":
        return RawDecision(VERDICT_NEVER, REASON_SYNTHETIC)
    # An already-recorded redaction derivative is itself a servable object
    # when the lane allows — it screens like any other candidate and serves
    # as ``kind: redacted`` off its own digest.
    stored = bool(
        int(capture.get("byte_size") or 0) > 0
        or capture.get("bytes_retained")
        or str(capture.get("storage_tier") or "") == "public"
        or capture.get("redaction_applied")
    )
    if not stored:
        return RawDecision(VERDICT_NEVER, REASON_NO_BYTES)
    if int(capture.get("byte_size") or 0) > byte_cap:
        return RawDecision(VERDICT_LINK_OUT, REASON_OVERSIZE)
    if p8 in FIELD_SCREEN_CLASSES:
        if capture.get("redaction_applied") or capture.get("parent_capture_id"):
            return RawDecision(VERDICT_SERVE)
        return RawDecision(VERDICT_RESERIALISE)
    return RawDecision(VERDICT_SERVE)


def _field_vocab(decl: ScreenDeclaration, class_ids: Sequence[str]) -> frozenset[str]:
    """The union of field vocabularies the hit classes declared — the drop
    set the re-serialisation applies (committed ``sig.at-rest-audit-decl/1``
    vocabulary, never a guessed field)."""
    out: set[str] = set()
    for cid in class_ids:
        rule_set = decl.rule_for(cid)
        if rule_set is None:
            continue
        for r in rule_set.rules:
            out.update(str(f).lower() for f in r.fields)
    return frozenset(out)


def _drop_fields(node: Any, vocab: frozenset[str], dropped: set[str]) -> Any:
    """Recursively drop dict keys matching ``vocab`` (exact or glob) —
    case-insensitive. Records each matched name in ``dropped`` (the field
    NAME only — a value never travels)."""
    if isinstance(node, dict):
        out: dict[str, Any] = {}
        for k, v in node.items():
            kl = str(k).lower()
            if kl in vocab or any("*" in f and fnmatch.fnmatch(kl, f) for f in vocab):
                dropped.add(kl)
                continue
            out[k] = _drop_fields(v, vocab, dropped)
        return out
    if isinstance(node, list):
        return [_drop_fields(v, vocab, dropped) for v in node]
    return node


def reserialise_fields(
    blob: bytes,
    *,
    media_type: str,
    drop_fields: frozenset[str],
) -> tuple[bytes, tuple[str, ...]]:
    """The P8-5/6/8 transform: drop the declared field names from a JSON
    document and re-serialise deterministically (sorted keys, minimal
    separators — byte-stable, SIG-EXPORT-003).

    The output is **new bytes** — the parent's are never touched
    (SIG-EPIS-006; the derivative persists as a NEW capture, SIG-PUB-015).
    A non-JSON payload refuses: a field-screen class on an unparseable
    document can never produce a reliable derivative, so the lane fails
    closed rather than serving raw bytes it cannot vouch for.
    """
    if not drop_fields:
        raise RawArchiveError("reserialise_fields requires a non-empty drop set")
    try:
        doc = json.loads(blob.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise RawArchiveError(
            f"capture is not a parseable JSON document — no reliable "
            f"field-allowlist derivative exists ({exc})"
        ) from exc
    dropped: set[str] = set()
    out = _drop_fields(doc, drop_fields, dropped)
    if not dropped:
        raise RawArchiveError(
            "the declared drop set matched no field — the derivative would be "
            "the parent's bytes re-labelled (refused; record the screen basis)"
        )
    data = json.dumps(out, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )
    return data, tuple(sorted(dropped))


def reserialisation_record(
    *,
    parent_digest: str,
    parent_capture_id: str,
    derivative_digest: str,
    dropped_fields: Sequence[str],
    screen_classes: Sequence[str],
    source_id: str,
) -> dict[str, Any]:
    """The ``sig.raw-reserialisation/1`` record — the append-only provenance
    the live leg persists as the new capture's redaction record
    (SIG-PUB-015/016): parent binding, method + version, the dropped field
    NAMES (committed vocabulary — never a value), and the screen classes that
    motivated the derivative."""
    return {
        "schema": RESERIALISATION_SCHEMA,
        "parent_digest": parent_digest,
        "parent_capture_id": parent_capture_id,
        "derivative_digest": derivative_digest,
        "redaction_method": RESERIALISATION_METHOD,
        "redaction_version": RESERIALISATION_VERSION,
        "dropped_fields": sorted(set(str(f) for f in dropped_fields)),
        "screen_classes": sorted(set(str(c) for c in screen_classes)),
        "source_id": str(source_id),
    }


def _screen_or_none(
    blob: bytes, *, source_id: str, media_type: str, decl: ScreenDeclaration | None
) -> dict[str, int]:
    """The Part VIII byte screen — fail closed. No declaration means the
    screen cannot run, which is a REFUSAL, not a pass: an unscreened raw
    object is never served (D-J3-1's "after the Part VIII byte screen")."""
    if decl is None:
        raise RawArchiveError(
            "no screen declaration — the Part VIII byte screen cannot run; "
            "an unscreened raw object is never served"
        )
    return screen_blob(blob, source_id=source_id, media_type=media_type, decl=decl)


def _secret_scan(blob: bytes, media_type: str) -> bool:
    """The S-1 block clause over decodable text — a secret-shaped value in a
    served object refuses it (SIG-TRANSP-022). Binary payloads skip the
    text scan (the byte screen still ran)."""
    mt = media_type.split(";", 1)[0].strip().lower()
    if mt.startswith(("image/", "audio/", "video/")) or mt in {
        "application/zip",
        "application/pdf",
        "application/octet-stream",
    }:
        return False
    try:
        text = blob.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return bool(find_secrets(text))


def build_archive(
    captures: Sequence[Mapping[str, Any]],
    *,
    lanes: Mapping[str, Mapping[str, Any]],
    read_bytes: Callable[[str], bytes | None],
    decl: ScreenDeclaration | None,
    out_dir: Path | str,
    byte_cap: int = MAX_OBJECT_BYTES,
) -> ArchiveResult:
    """Build the raw-ok archive tree under ``out_dir``.

    ``captures`` are the recorded capture rows (``capture_id``,
    ``artifact_id``, ``source_id``, ``content_digest``, ``byte_size``,
    ``media_type``, ``retrieved_at``, ``storage_tier``,
    ``capture_classification``, ``license`` …). ``lanes`` maps ``source_id``
    → ``{"lane": …, "part_viii_class": …}`` — the recorded redistribution
    verdicts (never derived here). ``read_bytes`` resolves a content digest
    to bytes (``None`` = unavailable).

    Writes ``raw/<multihash>`` per served object and ``raw/index.json`` —
    deterministic order (digest sort), canonical JSON.
    """
    out = Path(out_dir)
    raw_dir = out / RAW_PREFIX
    raw_dir.mkdir(parents=True, exist_ok=True)
    result = ArchiveResult()
    for cap in captures:
        source_id = str(cap.get("source_id") or "")
        lane_row = dict(lanes.get(source_id) or {})
        decision = decide_capture(
            cap,
            lane=lane_row.get("lane"),
            part_viii_class=lane_row.get("part_viii_class"),
            byte_cap=byte_cap,
        )
        capture_id = str(cap.get("capture_id") or "")
        digest = str(cap.get("content_digest") or "")
        if decision.verdict == VERDICT_NEVER:
            result.skipped.append(
                SkippedRow(capture_id, source_id, digest or None, str(decision.reason_class))
            )
            continue
        if decision.verdict == VERDICT_LINK_OUT:
            result.skipped.append(
                SkippedRow(capture_id, source_id, digest or None, REASON_OVERSIZE)
            )
            continue
        blob = read_bytes(digest)
        if blob is None:
            result.skipped.append(
                SkippedRow(capture_id, source_id, digest or None, REASON_BYTES_MISSING)
            )
            continue
        media_type = str(cap.get("media_type") or "application/octet-stream")
        hits = _screen_or_none(blob, source_id=source_id, media_type=media_type, decl=decl)
        parent_digest: str | None = None
        method: str | None = None
        version: str | None = None
        dropped: tuple[str, ...] = ()
        served_bytes = blob
        kind = "original"
        if decision.verdict == VERDICT_RESERIALISE:
            assert decl is not None  # _screen_or_none raised on None above
            drop = _field_vocab(decl, sorted(hits))
            if not drop:
                # The recorded class demands a derivative but the screen
                # found no field vocabulary to remove — fail closed, never
                # serve raw bytes on a guessed field list.
                result.skipped.append(
                    SkippedRow(
                        capture_id,
                        source_id,
                        digest or None,
                        REASON_UNPARSEABLE,
                        tuple(sorted(hits)),
                    )
                )
                continue
            try:
                served_bytes, dropped = reserialise_fields(
                    blob, media_type=media_type, drop_fields=drop
                )
            except RawArchiveError:
                result.skipped.append(
                    SkippedRow(
                        capture_id,
                        source_id,
                        digest or None,
                        REASON_UNPARSEABLE,
                        tuple(sorted(hits)),
                    )
                )
                continue
            # The derivative re-screens — a residual hit refuses (the parent
            # is never served either way).
            dhits = _screen_or_none(
                served_bytes, source_id=source_id, media_type=media_type, decl=decl
            )
            if dhits:
                result.skipped.append(
                    SkippedRow(
                        capture_id,
                        source_id,
                        digest or None,
                        REASON_SCREEN,
                        tuple(sorted(dhits)),
                    )
                )
                continue
            kind = "redacted"
            parent_digest = digest
            method = RESERIALISATION_METHOD
            version = RESERIALISATION_VERSION
        elif hits:
            result.skipped.append(
                SkippedRow(
                    capture_id, source_id, digest or None, REASON_SCREEN, tuple(sorted(hits))
                )
            )
            continue
        if len(served_bytes) > byte_cap:
            result.skipped.append(
                SkippedRow(capture_id, source_id, digest or None, REASON_OVERSIZE)
            )
            continue
        if _secret_scan(served_bytes, media_type):
            result.skipped.append(SkippedRow(capture_id, source_id, digest or None, REASON_SECRET))
            continue
        obj_digest = multihash(served_bytes)
        target = raw_dir / obj_digest
        target.write_bytes(served_bytes)
        entry = ArchiveEntry(
            digest=obj_digest,
            path=f"{RAW_PREFIX}/{obj_digest}",
            sha256=hashlib.sha256(served_bytes).hexdigest(),
            byte_size=len(served_bytes),
            media_type=media_type,
            capture_id=capture_id,
            artifact_id=str(cap.get("artifact_id") or ""),
            source_id=source_id,
            license=str(cap.get("license") or cap.get("spdx_expression") or ""),
            retrieved_at=cap.get("retrieved_at") or None,
            kind=kind,
            parent_digest=parent_digest,
            redaction_method=method,
            redaction_version=version,
            dropped_fields=dropped,
        )
        result.entries.append(entry)
        if kind == "redacted":
            result.reserialisations.append(
                reserialisation_record(
                    parent_digest=str(parent_digest),
                    parent_capture_id=capture_id,
                    derivative_digest=obj_digest,
                    dropped_fields=dropped,
                    screen_classes=sorted(hits),
                    source_id=source_id,
                )
            )
    result.entries.sort(key=lambda e: e.digest)
    result.skipped.sort(key=lambda s: (s.source_id, s.capture_id))
    index = index_document(result.entries, result.skipped)
    (raw_dir / "index.json").write_bytes(index)
    return result


def index_document(entries: Sequence[ArchiveEntry], skipped: Sequence[SkippedRow]) -> bytes:
    """``raw/index.json`` — the ``sig.raw-archive-index/1`` document.

    Served objects carry the full row; skipped captures carry digest +
    reason class (never withheld content). ``counts`` reconciles: every
    input capture is exactly one entry or one skip."""
    reason_counts: dict[str, int] = {}
    for s in skipped:
        reason_counts[s.reason_class] = reason_counts.get(s.reason_class, 0) + 1
    doc = {
        "schema": INDEX_SCHEMA,
        "objects": [e.as_json() for e in entries],
        "skipped": [s.as_json() for s in skipped],
        "counts": {
            "objects": len(entries),
            "skipped": len(skipped),
            "by_reason": dict(sorted(reason_counts.items())),
            "reserialisations": sum(1 for e in entries if e.kind == "redacted"),
        },
    }
    return (
        json.dumps(doc, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        + b"\n"
    )


def public_href(digest: str, *, base_url: str) -> str:
    """The distribution-host URL of a raw object — ``{base}/raw/<multihash>``
    (J3 §5.3's "from `raw/<multihash>`"; the mirror row's committed base)."""
    return f"{base_url.rstrip('/')}/{RAW_PREFIX}/{digest}"


def served_href_map(entries: Sequence[ArchiveEntry], *, base_url: str) -> dict[str, str]:
    """``content_digest → public href`` for the view-original wiring
    (SIG-TRANSP-012): an ``original`` entry maps its own digest; a
    ``redacted`` entry maps its PARENT's digest to the derivative object —
    the parent's bytes are never served, so a view-original link for the
    parent row resolves the redacted copy (the label already says
    "Download redacted copy")."""
    out: dict[str, str] = {}
    for e in entries:
        out[e.digest] = public_href(e.digest, base_url=base_url)
        if e.kind == "redacted" and e.parent_digest:
            out[e.parent_digest] = public_href(e.digest, base_url=base_url)
    return out


def index_entries_from_bytes(index_bytes: bytes) -> list[dict[str, Any]]:
    """Parse ``raw/index.json`` back to its object rows (the withdrawal
    rehearsal + the view-original resolver read it — never a second
    vocabulary)."""
    doc = json.loads(index_bytes.decode("utf-8"))
    if doc.get("schema") != INDEX_SCHEMA:
        raise RawArchiveError(f"raw index schema is not {INDEX_SCHEMA!r}")
    return [dict(e) for e in doc.get("objects") or []]


__all__ = [
    "ArchiveEntry",
    "ArchiveResult",
    "FIELD_SCREEN_CLASSES",
    "INDEX_SCHEMA",
    "MAX_OBJECT_BYTES",
    "RAW_PREFIX",
    "REASON_CLASSES",
    "RESERIALISATION_METHOD",
    "RESERIALISATION_SCHEMA",
    "RESERIALISATION_VERSION",
    "RawArchiveError",
    "RawDecision",
    "SkippedRow",
    "VERDICT_LINK_OUT",
    "VERDICT_NEVER",
    "VERDICT_RESERIALISE",
    "VERDICT_SERVE",
    "build_archive",
    "decide_capture",
    "index_document",
    "index_entries_from_bytes",
    "public_href",
    "reserialisation_record",
    "reserialise_fields",
    "served_href_map",
]
