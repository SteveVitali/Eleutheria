# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Emitter-side claim identity + the claim-minting-diff harness (P35.22 / F-504).

The emitted record and the stored claim MUST mint under one identity function
(SIG-INGEST-003/004): ``db.claim_sink.content_digest`` and this module both
delegate to :func:`evidence.claim_identity.claim_digest`, and this module adds
the two emitter-side surfaces that need it:

* **Registry-read predicate classes** — :func:`predicate_temporal_classes`
  projects the committed predicate registry (``ontology/vocab/predicates.yaml``,
  the same registry ``vocab_predicate`` is seeded from) to each predicate's
  ``obs``/``ref`` identity class. The class is registry-declared
  (``is_windowed``/the interval ``resolution_strategy`` family), never inferred
  from a record's shape.
* **The claim-minting-diff harness** — :func:`diff_minting` compares the emitted
  digest stream with the stored digest stream over the
  ``ingest_claim_reconcile.csv`` schema (P34.44b's comparison surface): every
  emitted claim's digest must appear on the stored side (a re-observation
  re-binds, never re-mints), and every digest the stored side reports for the
  compared row set must be emitted under the same identity. ``write_rows`` /
  ``read_rows`` are the CSV codec the probe and the fixture tests share.

Nothing here fetches, asserts or mutates — it is a pure comparison over records
and rows, runnable in tests, in shadow replay, and in the nightly probe.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from evidence.claim_identity import (
    PAYLOAD_VERSION,
    PredicateClass,
    claim_digest,
    temporal_class,
)
from ontology.generate import load_vocab

#: The ``ingest_claim_reconcile.csv`` column order — the emitted-vs-stored
#: comparison the dedup-parity check consumes (P35.22; the P34.44b probe writes
#: ``stored`` rows, replay/emission writes ``emitted`` rows). ``row_key`` is the
#: logical source-row identity the two sides join on; ``content_digest`` is the
#: minted identity under this row's digest scheme; ``payload_version`` records
#: which normalisation produced it.
RECONCILE_FIELDS = (
    "side",
    "row_key",
    "source_id",
    "predicate_id",
    "subject_key",
    "object_key",
    "value_repr",
    "content_digest",
    "payload_version",
)

#: Record kinds the claim sink mints — the same filter ``PgClaimSink`` applies
#: (``record_kind`` absent or ``"claim"``; every other kind is a non-claim record
#: the emit stage may carry beside claims).
_CLAIM_RECORD_KINDS = frozenset({"claim"})


def is_claim_record(record: Mapping[str, Any]) -> bool:
    """Whether the sink mints a claim for this record (its claim filter)."""
    kind = record.get("record_kind")
    return kind is None or kind in _CLAIM_RECORD_KINDS


def predicate_temporal_classes() -> dict[str, PredicateClass]:
    """The registry's predicate → ``obs``/``ref`` map (emitter side).

    Reads ``vocab/predicates.yaml`` — the committed source ``vocab_predicate``
    is seeded from — so an emitter-side digest resolves the SAME class the
    sink's ``vocab_predicate`` lookup resolves. A registry row declares the
    class via ``is_windowed`` or an interval ``resolution_strategy``; a missing
    field reads as ``ref``.
    """
    vocab = load_vocab("predicates")
    classes: dict[str, PredicateClass] = {}
    for row in vocab.get("predicates", []):
        pid = str(row.get("predicate_id") or "")
        if not pid:
            continue
        classes[pid] = temporal_class(
            resolution_strategy=row.get("resolution_strategy"),
            is_windowed=bool(row.get("is_windowed")),
        )
    return classes


def emitted_claim_digest(
    record: Mapping[str, Any],
    *,
    classes: Mapping[str, PredicateClass] | None = None,
) -> str:
    """The emitter-side claim digest — the same function the sink runs.

    ``classes`` is :func:`predicate_temporal_classes`'s map; ``None`` loads the
    registry fresh. A record whose predicate the registry does not declare mints
    under ``ref`` — identical to the sink, which quarantines unregistered
    predicates before they could mint anyway.
    """
    if classes is None:
        classes = predicate_temporal_classes()
    predicate = _first_key(record, "predicate_id", "predicate")
    return claim_digest(record, temporal_class=classes.get(predicate, "ref"))


def _first_key(record: Mapping[str, Any], *keys: str) -> str:
    for key in keys:
        value = record.get(key)
        if value is not None and str(value) != "":
            return str(value)
    return ""


def emitted_row_key(record: Mapping[str, Any], *, ordinal: int | None = None) -> str:
    """A stable logical key for an emitted claim row (the CSV join key).

    ``source`` × ``subject`` × ``predicate`` × ``object`` × ``value`` is what a
    claim IS once the volatile acquisition fields leave identity; ``ordinal``
    disambiguates two identical claims emitted in one pass (still one claim —
    the diff counts them as one re-binding group).
    """
    parts = [
        _first_key(record, "source_id", "source"),
        _first_key(record, "subject_id", "subject", "subject_ref"),
        _first_key(record, "predicate_id", "predicate"),
        _first_key(record, "object_ref", "object_id", "object", "value", "value_text"),
        _first_key(record, "value", "value_text", "raw_value"),
    ]
    if ordinal is not None:
        parts.append(f"#{ordinal}")
    return "|".join(parts)


def reconcile_rows(
    records: Iterable[Mapping[str, Any]],
    *,
    source_id: str,
    classes: Mapping[str, PredicateClass] | None = None,
    side: str = "emitted",
) -> list[dict[str, str]]:
    """Project emitted claim records to ``ingest_claim_reconcile.csv`` rows.

    Only claim records enter the comparison — the sink's own claim filter, so a
    side-by-side entity/outcome record never reports as a phantom mint. The row
    digest is the emitter-side mint (:func:`emitted_claim_digest`).
    """
    if classes is None:
        classes = predicate_temporal_classes()
    rows: list[dict[str, str]] = []
    for ordinal, record in enumerate(records):
        if not is_claim_record(record):
            continue
        predicate = _first_key(record, "predicate_id", "predicate")
        subject = _first_key(record, "subject_id", "subject", "subject_ref")
        obj = _first_key(record, "object_ref", "object_id", "object")
        value_repr = _first_key(record, "value", "value_text", "raw_value")
        rows.append(
            {
                "side": side,
                "row_key": emitted_row_key(record, ordinal=ordinal),
                "source_id": source_id,
                "predicate_id": predicate,
                "subject_key": subject,
                "object_key": obj,
                "value_repr": value_repr,
                "content_digest": emitted_claim_digest(record, classes=classes),
                "payload_version": PAYLOAD_VERSION,
            }
        )
    return rows


def write_rows(rows: Iterable[Mapping[str, str]]) -> str:
    """Serialise reconcile rows to the CSV text form (sorted for determinism)."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(RECONCILE_FIELDS), lineterminator="\n")
    writer.writeheader()
    for row in sorted(
        rows,
        key=lambda r: (
            str(r.get("side", "")),
            str(r.get("row_key", "")),
            str(r.get("content_digest", "")),
        ),
    ):
        writer.writerow({name: str(row.get(name, "") or "") for name in RECONCILE_FIELDS})
    return buf.getvalue()


def read_rows(text: str) -> list[dict[str, str]]:
    """Parse ``ingest_claim_reconcile.csv`` text back to reconcile rows."""
    out: list[dict[str, str]] = []
    for row in csv.DictReader(io.StringIO(text)):
        out.append({name: (row.get(name) or "") for name in RECONCILE_FIELDS})
    return out


@dataclass(frozen=True)
class MintingDiff:
    """The dedup-parity verdict over one emitted-vs-stored comparison."""

    #: Emitted claim rows compared.
    emitted: int = 0
    #: Stored claim rows compared.
    stored: int = 0
    #: Logical row keys whose emitted digests all re-bound (in stored digests).
    rebound: int = 0
    #: Logical row keys whose emitted digest has no stored counterpart — these
    #: would mint new claims on ingest.
    minted: int = 0
    #: Logical row keys where emitted and stored digests BOTH exist but differ —
    #: an identity divergence between emitter and sink (a bug class F-504 names).
    divergent: int = 0
    #: Per-key detail for minted/divergent keys (bounded for reports).
    detail: dict[str, dict[str, Any]] = field(default_factory=dict)

    @property
    def converged(self) -> bool:
        """Parity holds when nothing mints and nothing diverges."""
        return self.minted == 0 and self.divergent == 0

    def summary(self) -> dict[str, int | bool]:
        return {
            "emitted": self.emitted,
            "stored": self.stored,
            "rebound": self.rebound,
            "minted": self.minted,
            "divergent": self.divergent,
            "converged": self.converged,
        }


def diff_minting(rows: Iterable[Mapping[str, str]], *, max_detail: int = 50) -> MintingDiff:
    """Compare emitted vs stored digests over reconcile rows (SIG-INGEST-004).

    Joins on ``row_key`` (the logical claim identity): a row key whose emitted
    digests are a subset of its stored digests re-bound; any emitted digest
    absent from the stored side is a would-be mint; a stored digest absent from
    the emitted side flags a stored row the emitter no longer produces (logged,
    not a parity failure — sources legitimately shrink).
    """
    emitted_rows = [r for r in rows if str(r.get("side")) == "emitted"]
    stored_rows = [r for r in rows if str(r.get("side")) == "stored"]
    stored_digests_by_key: dict[str, set[str]] = {}
    for row in stored_rows:
        stored_digests_by_key.setdefault(str(row.get("row_key", "")), set()).add(
            str(row.get("content_digest", ""))
        )
    rebound = 0
    minted = 0
    divergent = 0
    detail: dict[str, dict[str, Any]] = {}
    emitted_by_key: dict[str, set[str]] = {}
    for row in emitted_rows:
        emitted_by_key.setdefault(str(row.get("row_key", "")), set()).add(
            str(row.get("content_digest", ""))
        )
    for key, digests in emitted_by_key.items():
        stored = stored_digests_by_key.get(key, set())
        missing = digests - stored
        if not missing:
            rebound += 1
        elif not stored:
            minted += 1
            if len(detail) < max_detail:
                detail[key] = {"emitted": sorted(digests), "stored": []}
        else:
            divergent += 1
            if len(detail) < max_detail:
                detail[key] = {"emitted": sorted(digests), "stored": sorted(stored)}
    return MintingDiff(
        emitted=len(emitted_rows),
        stored=len(stored_rows),
        rebound=rebound,
        minted=minted,
        divergent=divergent,
        detail=detail,
    )


__all__ = [
    "MintingDiff",
    "RECONCILE_FIELDS",
    "diff_minting",
    "emitted_claim_digest",
    "emitted_row_key",
    "is_claim_record",
    "predicate_temporal_classes",
    "read_rows",
    "reconcile_rows",
    "write_rows",
]
