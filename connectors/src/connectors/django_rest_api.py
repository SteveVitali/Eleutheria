# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P37.53 — the ``django_rest_api`` screened-count connector (ACQ-26, I7-S1 `a`).

One seat: ``camreg_la_new_orleans_eye_on`` — Eye on Surveillance's New
Orleans surveillance map API (I3-C070), a Django REST Framework list
endpoint whose every row is a private-registrant / crowdsourced camera
location (the candidate record's Part VIII flags: residential-intersection,
private-registrant-location). The S1 screen reads **programme facts only**:
the committed target fetches the single minimal page the declared contract
allows (``?page=1&page_size=1`` — one bounded JSON envelope), and the lane
materialises the published ``count`` ONLY — the ``results`` row bytes are
dropped in transit, their field NAMES screened against the Part VIII
denylist (F-330): a denied name — or more rows than the declared page —
is :class:`ContentDrift`, never a warning and never a captured location.

The emit mirrors the ``dot_511`` ``arcgis_s1`` count lane: one
``programme_area:`` aggregate subject per committed programme label plus a
``programme_count`` claim carrying the published total, the committed
period label and the declared measure — never a device, geometry,
registrant, name or below-programme count. The source row stays
``ingestion_permitted=false``; leg B, the first real wire, is the
operator's act (OP-26) — nothing here flips it.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime
from functools import cache
from typing import Any
from urllib.parse import urlencode

from parsing.locator import Locator

from ._data import load_table
from .field_denylist import denied_match
from .stages import CaptureRef, Connector, ContentDrift, FetchResult, RunContext, register

CONNECTOR_NAME = "django_rest_api"
_VOCAB_TABLE = "django_rest_api_vocab"
_TARGETS_TABLE = "django_rest_api_targets"
_SCHEMA = "sig.django-rest-api-vocab/1"
_TARGETS_SCHEMA = "sig.django-rest-api-targets/1"


@cache
def vocab() -> dict[str, Any]:
    table = load_table(_VOCAB_TABLE)
    if str(table.get("schema") or "") != _SCHEMA:
        raise ValueError(f"django_rest_api vocabulary must be {_SCHEMA!r}")
    return table


def vocab_version() -> str:
    return str(vocab()["vocab_version"])


@cache
def predicate_allowlist() -> frozenset[str]:
    return frozenset(str(p) for p in vocab()["predicate_allowlist"])


def assert_predicate_allowed(predicate: str) -> str:
    if predicate not in predicate_allowlist():
        raise ValueError(
            f"predicate {predicate!r} is not in the django_rest_api allowlist "
            f"{sorted(predicate_allowlist())} (SIG-INGEST-033)"
        )
    return predicate


@cache
def target_table() -> list[dict[str, Any]]:
    table = load_table(_TARGETS_TABLE)
    if str(table.get("schema") or "") != _TARGETS_SCHEMA:
        raise ValueError(f"django_rest_api inventory must be {_TARGETS_SCHEMA!r}")
    return [dict(t) for t in table.get("targets", ())]


def targets_for(source_id: str) -> list[dict[str, Any]]:
    return [t for t in target_table() if str(t.get("source_id")) == source_id]


def drf_targets(source_id: str) -> list[dict[str, Any]]:
    """The expanded live targets for ``source_id`` — the bounded count pages.

    Each inventory row expands to its single declared page
    (``?page=1&page_size=1``): the minimal envelope the S1 contract reads.
    """
    out: list[dict[str, Any]] = []
    for row in targets_for(source_id):
        endpoint = str(row["endpoint_url"])
        params = {
            str(row.get("page_param") or "page"): "1",
            str(row.get("page_size_param") or "page_size"): "1",
        }
        out.append(
            {
                "id": str(row["id"]),
                "url": f"{endpoint}?{urlencode(params)}",
                "kind": "drf_count_page",
                "target": dict(row),
            }
        )
    return out


def _stamp(row: dict[str, Any], *, source_id: str) -> dict[str, Any]:
    row.setdefault("source_id", source_id)
    row.setdefault("vocab_version", vocab_version())
    row.setdefault("sensitivity_class", str(vocab()["default_sensitivity_class"]))
    row.setdefault("source_attribution", source_id)
    return row


@register
class DjangoRestApiConnector(Connector):
    """DRF list-endpoint screened-count lane (S1; programme facts only)."""

    name = CONNECTOR_NAME
    version = "1.0.0"
    ingestion_mode = "rest_api"
    incrementality = "re-issue detection via content-addressed capture digests"

    def discover(self, ctx: RunContext) -> list[Mapping[str, Any]]:
        """The committed inventory rows for this source — identifiers only."""
        targets = list(ctx.parameters.get("targets", []))
        if targets:
            return targets
        out: list[Mapping[str, Any]] = [dict(t) for t in drf_targets(ctx.source.id)]
        return out

    def fetch(self, ctx: RunContext, target: Mapping[str, Any]) -> FetchResult:
        """ONE polite GET through the shared layer — the only egress."""
        assert ctx.fetcher is not None, "connectors fetch only through the shared layer"
        return ctx.fetcher.fetch(str(target["url"]))

    def parse(self, ctx: RunContext, capture: CaptureRef) -> dict[str, Any]:
        """Structure the DRF envelope; screen + drop the results rows (S1).

        The declared contract is a Django REST Framework paginated envelope —
        ``{"count": <int>, "results": [ … ]}`` — fetched with ``page_size=1``
        so at most ONE result row crosses the wire. The lane keeps the
        published ``count`` and the result field NAMES only; any denied
        field name (F-330), a second result row, an error envelope, or a
        non-integer count fails closed as :class:`ContentDrift`.
        """
        data = ctx.captures.get(capture.digest)
        try:
            doc = json.loads(data)
        except (ValueError, TypeError) as exc:
            head = data[:64] if isinstance(data, (bytes, bytearray)) else str(data)[:64]
            raise ContentDrift(
                ctx.source.id,
                f"DRF list endpoint returned non-JSON content ({len(data)} bytes; starts {head!r})",
            ) from exc
        if not isinstance(doc, Mapping):
            raise ContentDrift(
                ctx.source.id, f"DRF list payload is not an object (got {type(doc).__name__})"
            )
        if isinstance(doc.get("detail"), str) and "count" not in doc:
            raise ContentDrift(
                ctx.source.id, f"DRF list endpoint returned an error envelope: {doc['detail']!r}"
            )
        try:
            count = int(str(doc["count"]))
        except (KeyError, TypeError, ValueError):
            raise ContentDrift(
                ctx.source.id, f"DRF list payload lacks an integer 'count' (keys: {sorted(doc)})"
            ) from None
        results = doc.get("results")
        if not isinstance(results, list):
            raise ContentDrift(
                ctx.source.id,
                f"DRF list payload lacks the declared 'results' array (keys: {sorted(doc)})",
            )
        if len(results) > 1:
            raise ContentDrift(
                ctx.source.id,
                f"DRF page carries {len(results)} result rows under the declared "
                "page_size=1 contract — the lane never reads a row set",
            )
        # S1: the result row's field NAMES are screened and recorded, its
        # VALUES dropped in transit — a denied name is a whole refusal.
        field_names: list[str] = []
        if results:
            row = results[0]
            if not isinstance(row, Mapping):
                raise ContentDrift(ctx.source.id, "the DRF result row is not an object")
            field_names = sorted(str(k) for k in row)
            for name in field_names:
                term = denied_match(name)
                if term is not None:
                    raise ContentDrift(
                        ctx.source.id,
                        f"the DRF result row publishes denied field {name!r} "
                        f"(denied {term!r}) — a Part VIII registrant field the "
                        "S1 screen refuses by name (F-330)",
                    )
        return {
            "kind": "drf_count_page",
            "payload": {"count": count, "result_field_names": field_names},
            "capture": capture,
        }

    def extract(self, ctx: RunContext, parsed: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        """One raw screened-count record — the count plus the field names."""
        target = _resolve(ctx, parsed["capture"].source_uri)
        row = target.get("target") or {}
        return [
            {
                "record_kind": "drf_count",
                "count": int(parsed["payload"]["count"]),
                "result_field_names": list(parsed["payload"]["result_field_names"]),
                "source_uri": parsed["capture"].source_uri,
                "retrieved_at": (
                    parsed["capture"].retrieved_at.isoformat()
                    if parsed["capture"].retrieved_at is not None
                    else datetime.now(UTC).isoformat()
                ),
                "target": dict(row),
            }
        ]

    def normalize(
        self, ctx: RunContext, raw_claims: list[Mapping[str, Any]]
    ) -> list[dict[str, Any]]:
        """The ``programme_area`` subject + ``programme_count`` claim rows."""
        out: list[dict[str, Any]] = []
        for raw in raw_claims:
            target = raw.get("target") or {}
            target_id = str(target.get("id") or "unknown_target")
            programme = str(target.get("programme_label") or "").strip()
            period = str(target.get("period_label") or "").strip()
            measure = str(target.get("measure") or "").strip()
            if not programme or not period or not measure:
                out.append(
                    _stamp(
                        {
                            "record_kind": "drf_count_rejected",
                            "subject_id": f"programme_area:{ctx.source.id}:{target_id}:rejected",
                            "predicate_id": assert_predicate_allowed("external_id"),
                            "raw_value": "missing declaration",
                            "rejection_reason": "missing_s1_declaration",
                            "rejection_detail": "programme_label/period_label/measure required",
                            "target_id": target_id,
                        },
                        source_id=ctx.source.id,
                    )
                )
                continue
            subject_id = f"programme_area:{ctx.source.id}:{target_id}:{programme}"
            evidence = {
                "source_url": str(raw["source_uri"]),
                "extraction_method": "drf_count_page",
                "locator": Locator.row(0).to_row(),
            }
            state = str(target.get("state") or "")
            agency = str(target.get("agency") or "")

            def _claim(
                predicate: str,
                value: Any,
                raw_value: str,
                *,
                _subject_id: str = subject_id,
                _evidence: dict[str, Any] = evidence,
            ) -> dict[str, Any]:
                row: dict[str, Any] = {
                    "record_kind": "claim",
                    "subject_id": _subject_id,
                    "predicate_id": assert_predicate_allowed(predicate),
                    "raw_value": raw_value,
                    "value": value,
                    "evidence_genre": "camera_registry",
                    "evidence": dict(_evidence),
                }
                return _stamp(row, source_id=ctx.source.id)

            out.append(
                _stamp(
                    {
                        "record_kind": "programme_area",
                        "subject_id": subject_id,
                        "predicate_id": assert_predicate_allowed("programme_area"),
                        "external_id": programme,
                        "raw_value": programme,
                        "state": state,
                        "agency": agency,
                        "target_id": target_id,
                        "technology": str(target.get("technology") or ""),
                        "aggregate_measure": measure,
                        "excluded_fields": list(raw.get("result_field_names") or ()),
                        "evidence_genre": "camera_registry",
                        "evidence": dict(evidence),
                    },
                    source_id=ctx.source.id,
                )
            )
            out.append(_claim("external_id", programme, programme))
            technology = str(target.get("technology") or "").strip()
            if technology:
                out.append(_claim("technology", technology, technology))
            if agency:
                out.append(_claim("camera_registry_publisher", agency, agency))
            count_claim = _claim("programme_count", int(raw["count"]), str(int(raw["count"])))
            count_claim["period"] = period
            count_claim["measure"] = measure
            out.append(count_claim)
        return out


def _resolve(ctx: RunContext, source_uri: str) -> dict[str, Any]:
    """The run-time target a capture was fetched from (exact-URL match)."""
    for t in ctx.parameters.get("targets", []):
        if str(t.get("url")) == source_uri:
            return dict(t)
    # Fixture replay supplies a synthetic single target — resolve by prefix.
    for t in ctx.parameters.get("targets", []):
        if source_uri.startswith(str(t.get("target", {}).get("endpoint_url") or "\x00")):
            return dict(t)
    # Fall back to the committed inventory row (single-target source).
    rows = targets_for(ctx.source.id)
    return {"id": str(rows[0]["id"]), "target": dict(rows[0])} if rows else {}


__all__ = [
    "CONNECTOR_NAME",
    "DjangoRestApiConnector",
    "assert_predicate_allowed",
    "drf_targets",
    "predicate_allowlist",
    "targets_for",
    "vocab",
    "vocab_version",
]
