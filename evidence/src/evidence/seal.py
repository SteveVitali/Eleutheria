# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The protective-seal deny set (P34.49 / ADR-185, ADR-189).

``sig.seal-deny/1`` is the **serving/export deny set** the L2 leg persists on
the restricted bucket — an append-only VERSIONED object (a new version per
update under the bucket's versioning, never an in-place rewrite). Its entries
are ids + digests + rule ids only: a flagged object is named so the serving
surface can refuse exactly it, never so it can be inspected on a public path.

Two carriers, one rule — the same discipline as ADR-124's dispositions:

* **The spine side** is ``capture_seal`` (sqitch ``seal_register``): an
  append-only registry of protective seals keyed by ``capture_id`` — insert
  only, no UPDATE/DELETE. The serving paths (``store_pg.capture``,
  ``spine_export`` bindings) consult it the same way they consult
  ``publication_disposition``.
* **The object side** is this document — the durable record surviving a
  rebuild, carrying the rule ids the seal fired under and a ``supersedes``
  pointer so a superseding unseal is a NEW version, never an edit.

A seal **suppresses, never deletes**: bytes stay content-addressed in the OCFL
store under Object Lock (SIG-EVID-006); the deny set + the artifact-level
``withhold``/``restrict`` disposition keep them off every publishable path.
True deletion/purge stays the operator's in-ticket action (WV-06/WV-11,
ADR-181) — nothing here mutates a byte.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

SCHEMA = "sig.seal-deny/1"

#: Entry kinds the deny set can name — the sealed unit is always a capture
#: (digest-keyed OCFL object); artifact/digest aliases cover the consult paths.
ENTRY_KINDS = ("capture", "artifact", "digest")

#: Seal actions — ``seal`` is the protective suppress; ``unseal`` is the
#: superseding record a later authorized review writes (a NEW row, never an
#: edit). No ``delete``/``purge`` action exists here by design.
SEAL_ACTIONS = ("seal", "unseal")

_ACTION_RE = re.compile(r"^[a-z]+$")
_SHA512_RE = re.compile(r"^[0-9a-f]{128}$")


class SealDocError(ValueError):
    """A malformed ``sig.seal-deny/1`` document — fail closed."""


@dataclass(frozen=True)
class DenyEntry:
    """One deny-set entry — ``id`` is the capture/artifact/digest the path
    must refuse; ``rules`` are the F-406/I7/PUB-002 class ids that fired."""

    kind: str
    id: str
    rules: tuple[str, ...]


@dataclass(frozen=True)
class SealRecord:
    """One ``capture_seal`` row (spine side) — append-only."""

    capture_id: str
    content_digest: str
    action: str  # "seal" | "unseal"
    rules: tuple[str, ...]
    author: str
    audit_report: str  # the sig.at-rest-audit/1 report object that flagged it


def build_deny_set(
    entries: list[DenyEntry] | tuple[DenyEntry, ...],
    *,
    generated_at: str,
    prior: dict[str, Any] | None = None,
    audit_report: str = "",
    notes: str = "",
) -> dict[str, Any]:
    """Render the ``sig.seal-deny/1`` document. A new version supersedes the
    recorded prior (the object is versioned — this is a pointer, not an edit).
    """
    version = 1
    history: list[dict[str, Any]] = []
    if prior:
        prior_v = prior.get("version")
        if not isinstance(prior_v, int) or prior_v < 1:
            raise SealDocError("prior deny set carries no integer version")
        version = prior_v + 1
        old_entries = prior.get("entries")
        if not isinstance(old_entries, list):
            raise SealDocError("prior deny set carries no entries list")
        # The FULL prior entry set is retained verbatim under "history" so the
        # record stays self-contained counts+ids only.
        history = list(old_entries)
    doc: dict[str, Any] = {
        "schema": SCHEMA,
        "version": version,
        "generated_at": generated_at,
        "audit_report": audit_report,
        "entries": [{"kind": e.kind, "id": e.id, "rules": sorted(e.rules)} for e in entries],
        "supersedes": history,
        "notes": notes,
    }
    validate_deny_set(doc)
    return doc


def validate_deny_set(doc: dict[str, Any]) -> None:
    """Fail-closed shape check — ids/digests/class-ids only; any free-text
    field or value-looking payload is a breach of the counts-only contract."""
    if doc.get("schema") != SCHEMA:
        raise SealDocError(f"deny set schema must be {SCHEMA!r}")
    if not isinstance(doc.get("version"), int) or doc["version"] < 1:
        raise SealDocError("deny set version must be a positive integer")
    entries = doc.get("entries")
    if not isinstance(entries, list):
        raise SealDocError("deny set entries must be a list")
    seen: set[tuple[str, str]] = set()
    for e in entries:
        if not isinstance(e, dict) or set(e.keys()) != {"kind", "id", "rules"}:
            raise SealDocError("deny entry keys must be exactly kind/id/rules")
        if e["kind"] not in ENTRY_KINDS:
            raise SealDocError(f"deny entry kind {e['kind']!r} is not one of {ENTRY_KINDS}")
        if not isinstance(e["id"], str) or not e["id"] or len(e["id"]) > 512:
            raise SealDocError("deny entry id must be a bounded string")
        if not isinstance(e["rules"], list) or not all(
            isinstance(r, str) and _ACTION_RE.match(r) is None and r == r.upper()
            for r in e["rules"]
        ):
            raise SealDocError("deny entry rules must be class ids (upper-case tokens)")
        key = (e["kind"], e["id"])
        if key in seen:
            raise SealDocError(f"duplicate deny entry {key!r}")
        seen.add(key)


def load_deny_set(raw: bytes | str) -> dict[str, Any]:
    """Parse + validate a recorded deny set."""
    doc = json.loads(raw)
    validate_deny_set(doc)
    return doc


def denied_ids(doc: dict[str, Any], kind: str) -> set[str]:
    """The ids a path must refuse for ``kind`` (capture/artifact/digest)."""
    return {e["id"] for e in doc["entries"] if e["kind"] == kind}


def denied_digests(doc: dict[str, Any]) -> set[str]:
    """Every content digest a serving/export path must refuse — capture entries
    name the OCFL object (``sig:capture:<digest>``), digest entries name the
    digest directly."""
    out: set[str] = set()
    for e in doc["entries"]:
        if e["kind"] == "digest":
            out.add(e["id"])
        elif e["kind"] == "capture" and e["id"].startswith("sig:capture:"):
            out.add(e["id"].split("sig:capture:", 1)[1])
    return out


def seal_action(
    capture_id: str,
    digest: str,
    rules: tuple[str, ...] | list[str],
    *,
    author: str,
    audit_report: str,
    action: str = "seal",
) -> SealRecord:
    """Build a validated append-only seal record for ``capture_seal``."""
    if action not in SEAL_ACTIONS:
        raise SealDocError(f"seal action {action!r} must be one of {SEAL_ACTIONS}")
    if not capture_id or len(capture_id) != 36:
        raise SealDocError("capture_id must be a uuid")
    if not digest:
        raise SealDocError("content_digest is required (the sealed object id)")
    if not author or len(author) > 120:
        raise SealDocError("author must be a bounded operator id")
    return SealRecord(
        capture_id=capture_id,
        content_digest=digest,
        action=action,
        rules=tuple(sorted(set(rules))),
        author=author,
        audit_report=audit_report,
    )


__all__ = [
    "ENTRY_KINDS",
    "SCHEMA",
    "SEAL_ACTIONS",
    "DenyEntry",
    "SealDocError",
    "SealRecord",
    "build_deny_set",
    "denied_digests",
    "denied_ids",
    "load_deny_set",
    "seal_action",
    "validate_deny_set",
]
