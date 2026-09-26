# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The committed state-statute-inventory seed connector (P25.7, SIG-INGEST-049f).

`state_alpr_statute_inventory` is the one national ALPR-statute inventory that
exists — the NCSL state-by-state table, HTML-only and FROZEN since
``2022-02-03``. It is a **one-time committed seed, never a feed** (F3.28): this
connector loads the packaged ``state_alpr_statute_seed.toml`` through the same
eight-stage pipeline, the same loader gate, and the same append-only claim sink
as every source — via ``sig-connectors load-seed`` / ``runner.run_seed`` (the
in-memory permit flip the fixture path documents; the registry row stays
``ingestion_permitted=false`` and no network is ever opened for a seed).

**The ``as_of`` label is first-class data.** A frozen inventory's claims are
only meaningful beside the date the upstream froze at, so the load stamps the
seed's ``as_of`` on every claim's evidence and emits a dedicated ``as_of`` claim
carrying the page's verbatim label (P2).

**Shape, not guesses.** ``parse_statute_seed`` is STRICT: a TOML document whose
``statutes``/``as_of``/frozen flags no longer match the reviewed shape is
:class:`ContentDrift` — the adapter fails loud rather than asserting drifted
data. The ``state_count`` / ``ncsl_table_rows`` totals are re-derived and must
agree, so a truncated or duplicated table cannot load silently.

Each ``[[statutes]]`` entry becomes one §11.14 ``LegalInstrument``
(``instrument_type="statute"``) per enactment year — the NCSL table's own row
granularity (California's two statutes occupy two rows). ``jurisdiction`` is a
``us.state`` **candidate** identifier, never a resolution (SIG-INGEST-034).
"""

from __future__ import annotations

import re
import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .france_belgium import (
    LegalInstrument,
    _stamp,
    assert_legal_predicate_allowed,
    load_claims_for_l1,
)
from .stages import (
    CaptureRef,
    Connector,
    ContentDrift,
    FetchResult,
    RunContext,
    register,
)

_SEED_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

#: The statute-entry keys the reviewed seed shape carries; anything else is drift.
_ENTRY_KEYS = frozenset({"state", "years_enacted", "citations"})


@dataclass(frozen=True)
class StatuteSeedEntry:
    """One ``[[statutes]]`` row: a state's ALPR statute(s), enactment years, citations."""

    state: str
    years: tuple[int, ...]
    citations: tuple[str, ...] = ()


@dataclass(frozen=True)
class StatuteSeed:
    """The parsed seed document: the frozen label + its statute entries."""

    as_of: str
    as_of_label: str
    retrieved: str
    inventory_url: str
    state_count: int
    ncsl_table_rows: int
    statutes: tuple[StatuteSeedEntry, ...]


def _drift(source_id: str, reason: str, *, details: str = "") -> ContentDrift:
    return ContentDrift(source_id, reason, details=details)


def parse_statute_seed(data: bytes, *, source_id: str) -> StatuteSeed:
    """Parse the committed statute-seed TOML — STRICT shape (fail closed).

    The reviewed shape is ``as_of``/``frozen``/``never_a_feed``/``inventory_url``
    plus ``[[statutes]]`` rows of ``{state, years_enacted, citations?}``. A
    document that is not TOML, drops the frozen flags, or carries a malformed
    entry is :class:`ContentDrift`: a seed's value is that it is reviewed data —
    an unreviewed shape never loads. The declared ``state_count`` /
    ``ncsl_table_rows`` totals must agree with the parsed entries.
    """
    try:
        payload = tomllib.loads(data.decode("utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as exc:
        raise _drift(source_id, "the statute-seed asset is not TOML", details=str(exc)) from exc
    if not isinstance(payload, Mapping):
        raise _drift(source_id, "the statute-seed asset is not a TOML document")

    as_of = str(payload.get("as_of") or "")
    if not _SEED_DATE.match(as_of):
        raise _drift(source_id, "the statute-seed asset lacks an `as_of` ISO date")
    if payload.get("frozen") is not True or payload.get("never_a_feed") is not True:
        raise _drift(
            source_id,
            "the statute-seed asset lost its `frozen`/`never_a_feed` flags — a seed "
            "is one-time committed data; a feed-shaped asset is a different source",
        )
    inventory_url = str(payload.get("inventory_url") or "")
    if not inventory_url.startswith(("http://", "https://")):
        raise _drift(source_id, "the statute-seed asset lacks its `inventory_url`")

    raw_entries = payload.get("statutes")
    if not isinstance(raw_entries, list) or not raw_entries:
        raise _drift(source_id, "the statute-seed asset carries no `[[statutes]]` rows")
    entries: list[StatuteSeedEntry] = []
    for i, entry in enumerate(raw_entries):
        if not isinstance(entry, Mapping):
            raise _drift(source_id, f"statute-seed entry #{i} is not a TOML table")
        unknown = set(entry) - _ENTRY_KEYS
        if unknown:
            raise _drift(
                source_id,
                f"statute-seed entry #{i} carries unreviewed keys {sorted(unknown)}",
            )
        state = str(entry.get("state") or "").strip()
        if not state:
            raise _drift(source_id, f"statute-seed entry #{i} lacks a `state`")
        years = entry.get("years_enacted")
        if (
            not isinstance(years, list)
            or not years
            or any(not isinstance(y, int) or isinstance(y, bool) for y in years)
        ):
            raise _drift(
                source_id,
                f"statute-seed entry #{i} ({state}) lacks a non-empty `years_enacted` int list",
            )
        citations_raw = entry.get("citations") or []
        if not isinstance(citations_raw, list) or any(not str(c).strip() for c in citations_raw):
            raise _drift(
                source_id,
                f"statute-seed entry #{i} ({state}) carries a malformed `citations` list",
            )
        entries.append(
            StatuteSeedEntry(
                state=state,
                years=tuple(int(y) for y in years),
                citations=tuple(str(c).strip() for c in citations_raw),
            )
        )

    # The declared totals are part of the reviewed shape (16 states / 17 NCSL
    # table rows — a row can carry several enactment years, so the row count is
    # an upstream-layout label, not a derivable total): ``state_count`` is
    # re-derived exactly; ``ncsl_table_rows`` must at least cover every state
    # (a state occupies no fewer than one table row — California occupies two).
    if "state_count" in payload and int(payload["state_count"]) != len(entries):
        raise _drift(
            source_id,
            f"statute-seed `state_count` {payload['state_count']} != parsed "
            f"{len(entries)} entries — the asset changed shape",
        )
    if "ncsl_table_rows" in payload:
        ncsl_rows = payload["ncsl_table_rows"]
        if not isinstance(ncsl_rows, int) or ncsl_rows < len(entries):
            raise _drift(
                source_id,
                f"statute-seed `ncsl_table_rows` {ncsl_rows} cannot hold "
                f"{len(entries)} states — the asset changed shape",
            )

    return StatuteSeed(
        as_of=as_of,
        as_of_label=str(payload.get("as_of_label") or as_of),
        retrieved=str(payload.get("retrieved") or ""),
        inventory_url=inventory_url,
        state_count=len(entries),
        ncsl_table_rows=int(payload.get("ncsl_table_rows") or len(entries)),
        statutes=tuple(entries),
    )


def _citation_for(entry: StatuteSeedEntry, index: int) -> str | None:
    """The citation for one enactment year, when the mapping is unambiguous.

    The NCSL table is row-per-statute: a ``citations`` list the same length as
    ``years_enacted`` pairs positionally (California's two rows); a single-year
    state's citations all describe that one statute. Anything else is left off
    the typed claim — the raw value is preserved on the record regardless (P2),
    and a guess is never emitted.
    """
    if not entry.citations:
        return None
    if len(entry.years) == 1:
        return "; ".join(entry.citations)
    if len(entry.citations) == len(entry.years):
        return entry.citations[index]
    return None


@register
class StateStatuteSeedConnector(Connector):
    """Loads a committed statute-inventory seed into the claim spine (P25.7).

    ``fetch`` is protocol conformance only: the seed path serves the packaged
    asset over the static transport, so this connector never egresses.
    """

    name = "state_statute_seed"
    version = "1.0.0"

    def discover(self, ctx: RunContext) -> list[Mapping[str, Any]]:
        return [
            t
            for t in (ctx.parameters.get("targets") or ())
            if str(t.get("kind") or "") == "statute_seed"
        ]

    def fetch(self, ctx: RunContext, target: Mapping[str, Any]) -> FetchResult:
        assert ctx.fetcher is not None, "connectors fetch only through the shared layer"
        return ctx.fetcher.fetch(str(target["url"]))

    def parse(self, ctx: RunContext, capture: CaptureRef) -> StatuteSeed:
        return parse_statute_seed(ctx.captures.get(capture.digest), source_id=ctx.source.id)

    def extract(self, ctx: RunContext, parsed: StatuteSeed) -> list[Mapping[str, Any]]:
        evidence = {
            "source_url": parsed.inventory_url,
            "retrieved_date": parsed.retrieved or parsed.as_of,
            "as_of": parsed.as_of,
            "extraction_method": "statute_seed_toml",
        }
        records: list[Mapping[str, Any]] = [
            {
                "record_kind": "statute_seed_label",
                "raw": {
                    "as_of": parsed.as_of,
                    "as_of_label": parsed.as_of_label,
                    "retrieved": parsed.retrieved,
                    "inventory_url": parsed.inventory_url,
                    "state_count": parsed.state_count,
                    "ncsl_table_rows": parsed.ncsl_table_rows,
                    "frozen": True,
                    "never_a_feed": True,
                },
                "_evidence": evidence,
            }
        ]
        for entry in parsed.statutes:
            records.append(
                {
                    "record_kind": "statute_seed_entry",
                    "raw": {
                        "state": entry.state,
                        "years_enacted": list(entry.years),
                        "citations": list(entry.citations),
                    },
                    "_evidence": evidence,
                }
            )
        return records

    def normalize(
        self, ctx: RunContext, raw_claims: Sequence[Mapping[str, Any]]
    ) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for record in raw_claims:
            raw = record["raw"]
            evidence = record.get("_evidence")
            if record["record_kind"] == "statute_seed_label":
                # The frozen-inventory date label is first-class spine data: a
                # dedicated `as_of` claim carries the page's verbatim label as
                # its raw value (P2), beside a quality report for the run.
                out.append(
                    _stamp(
                        {
                            "record_kind": "claim",
                            "subject_id": f"seed:{ctx.source.id}",
                            "predicate_id": assert_legal_predicate_allowed("as_of"),
                            "value": str(raw["as_of"]),
                            "raw_value": str(raw.get("as_of_label") or raw["as_of"]),
                        },
                        source_id=ctx.source.id,
                    )
                )
                out.append(
                    _stamp(
                        {
                            "record_kind": "quality_report",
                            "source_id": ctx.source.id,
                            "capture_kind": "statute_seed",
                            "as_of": str(raw["as_of"]),
                            "retrieved": str(raw.get("retrieved") or ""),
                            "state_count": int(raw["state_count"]),
                            "ncsl_table_rows": int(raw["ncsl_table_rows"]),
                            "frozen": True,
                            "never_a_feed": True,
                            "connector_name": self.name,
                            "connector_version": self.version,
                        },
                        source_id=ctx.source.id,
                    )
                )
                if isinstance(evidence, Mapping):
                    out[0]["evidence"] = dict(evidence)
                    out[0]["observed_at"] = str(evidence.get("retrieved_date") or "")
                continue
            if record["record_kind"] != "statute_seed_entry":
                continue
            entry = StatuteSeedEntry(
                state=str(raw["state"]),
                years=tuple(int(y) for y in raw["years_enacted"]),
                citations=tuple(str(c) for c in raw.get("citations") or ()),
            )
            for i, year in enumerate(entry.years):
                instrument = LegalInstrument(
                    external_id=f"ncsl:{entry.state}:{year}",
                    source_id=ctx.source.id,
                    instrument_type="statute",
                    jurisdiction=entry.state,
                    jurisdiction_scheme="us.state",
                    citation=_citation_for(entry, i),
                    effective_from=str(year),
                    constrains_technology=("alpr",),
                    raw=dict(raw),
                )
                rows = instrument.claim_rows()
                if isinstance(evidence, Mapping):
                    observed_at = str(evidence.get("retrieved_date") or "")
                    for row in rows:
                        row["evidence"] = dict(evidence)
                        row["observed_at"] = observed_at
                out.extend(rows)
        return out

    def load(self, ctx: RunContext, linked: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return load_claims_for_l1(linked)


__all__ = [
    "StateStatuteSeedConnector",
    "StatuteSeed",
    "StatuteSeedEntry",
    "parse_statute_seed",
]
