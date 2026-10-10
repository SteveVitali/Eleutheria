# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The committed state-statute-inventory seed connectors (P25.7, SIG-INGEST-049f;
v2 refresh P35.10 / I8 §4.4 / ACQ-06, F-374).

``state_alpr_statute_inventory`` is the one national ALPR-statute inventory that
exists — the NCSL state-by-state table, HTML-only and FROZEN since
``2022-02-03``. It is a **one-time committed seed, never a feed** (F3.28): this
connector loads the packaged ``state_alpr_statute_seed.toml`` through the same
eight-stage pipeline, the same loader gate, and the same append-only claim sink
as every source — via ``sig-connectors load-seed`` / ``runner.run_seed`` (the
in-memory permit flip the fixture path documents; the registry row stays
``ingestion_permitted=false`` and no network is ever opened for a seed).

**The 2026 refresh is a second asset, not a rewrite.** Under I7-C9 answer `a`
the stale 2022 inventory is refreshed *from origins*: every ``statute_seed/2``
``[[statutes]]`` entry is verified at its own legislature/governor page in the
committed I7 packets and carries ``origin_url``, ``instrument_type``,
``effective_date``, ``verified_on`` and ``confidence``; NCSL/LAPPA/GHSA/
MultiState were enumeration aids only — an enumeration-aid host in
``origin_url`` is :class:`ContentDrift` (I7 NEW-7). The asset's
``supersedes_asset`` names the 2022 seed; both stay registered and loadable
(append-only, P7). Its ``[[duty_rows]]`` 50-state table is the coverage/duty
surface (SIG-INGEST-050): ``origin_verified`` rows name this seed's entries,
``recorded`` rows name the superseded asset's, and ``none_recorded`` is
absence of evidence — never a "no statute" claim (§3.1).

**The ``as_of`` label is first-class data.** A frozen inventory's claims are
only meaningful beside the date the upstream froze at, so the load stamps the
seed's ``as_of`` on every claim's evidence and emits a dedicated ``as_of`` claim
carrying the recorded label (P2); for v2 that label is the packet verification
day, honestly labelled — not an upstream page label.

**Shape, not guesses.** ``parse_statute_seed`` is STRICT: a TOML document whose
``statutes``/``as_of``/frozen flags no longer match the reviewed shape is
:class:`ContentDrift` — the adapter fails loud rather than asserting drifted
data. The declared ``state_count`` / ``ncsl_table_rows`` / ``duty_row_count``
totals are re-derived and must agree, so a truncated or duplicated table
cannot load silently.

Each ``[[statutes]]`` entry becomes §11.14 ``LegalInstrument`` claims — one per
enactment year for v1 (the NCSL table's row granularity); for v2 the entry's
declared ``instrument_type`` (``statute`` or ``executive_order``) and
``effective_date`` drive the instrument's typing and ``effective_from``.
``jurisdiction`` is a ``us.state`` **candidate** identifier, never a resolution
(SIG-INGEST-034).
"""

from __future__ import annotations

import re
import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

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
#: An effective_date is ISO, year-precision allowed (KY/CT signing dates carry
#: full ISO; nothing yet needs year-only, but the shape permits it).
_EFFECTIVE_DATE = re.compile(r"^\d{4}(-\d{2}-\d{2})?$")
_DUTY_ID = re.compile(r"^future_statutory_disclosure_[a-z0-9_]+$")

#: The statute-entry keys the reviewed v1 seed shape carries; anything else is drift.
_ENTRY_KEYS = frozenset({"state", "years_enacted", "citations"})

#: The v2 (statute_seed/2) entry keys — v1 keys plus the origin-provenance
#: fields I8 §4.4 prescribes (origin_url, instrument_type, effective_date,
#: verified_on) plus `date_basis` (what the date actually records — signed vs
#: effective), `confidence`, the committed `evidence` ids, and `notes`.
_ENTRY_KEYS_V2 = frozenset(
    {
        "state",
        "years_enacted",
        "citations",
        "instrument_type",
        "origin_url",
        "effective_date",
        "date_basis",
        "verified_on",
        "confidence",
        "evidence",
        "notes",
    }
)

#: The [[duty_rows]] keys — the 50-state coverage/duty table (SIG-INGEST-050).
_DUTY_KEYS = frozenset(
    {
        "state",
        "statute_posture",
        "statute_ref",
        "origin_url",
        "instruments",
        "duties",
        "duty_notes",
        "evidence",
        "verified_on",
    }
)

#: The v2 instrument_type permissible values (§11.14 names more; the seed
#: refresh recorded only these two in the I7 packets).
_INSTRUMENT_TYPES_V2 = frozenset({"statute", "executive_order"})

#: What an entry's effective_date actually records (honesty about basis).
_DATE_BASES = frozenset({"effective", "signed", "issued", "reported"})

_CONFIDENCES = frozenset({"high", "medium", "low"})

#: The duty-row postures. `none_recorded` is absence of evidence — never a
#: "no statute exists" claim (§3.1).
_POSTURES = frozenset({"origin_verified", "recorded", "none_recorded"})

#: Enumeration-aid hosts — I7 NEW-7 / C9 `a`: NCSL, LAPPA, GHSA and MultiState
#: enumerated statutes for the packet's origin reads but no claim cites them;
#: an origin_url on one of these hosts is drift, not a reviewed seed.
_ENUMERATION_AID_HOSTS = frozenset(
    {"ncsl.org", "legislativeanalysis.org", "ghsa.org", "multistate.us"}
)

#: The 2026 refresh's declared supersedes target — the frozen committed asset.
_SUPERSEDES_V2 = "state_alpr_statute_seed.toml"


@dataclass(frozen=True)
class StatuteSeedEntry:
    """One ``[[statutes]]`` row: a state's ALPR instrument(s), years, citations."""

    state: str
    years: tuple[int, ...]
    citations: tuple[str, ...] = ()
    #: v2 fields — unset on v1 rows (defaults keep the 2022 shape intact).
    instrument_type: str = "statute"
    origin_url: str = ""
    effective_date: str = ""
    date_basis: str = ""
    verified_on: str = ""
    confidence: str = ""
    evidence_ids: tuple[str, ...] = ()
    notes: str = ""


@dataclass(frozen=True)
class StatuteDutyRow:
    """One ``[[duty_rows]]`` row: a state's coverage/duty posture (SIG-INGEST-050)."""

    state: str
    statute_posture: str
    statute_ref: str = ""
    origin_url: str = ""
    instruments: tuple[str, ...] = ()
    duties: tuple[str, ...] = ()
    duty_notes: str = ""
    evidence_ids: tuple[str, ...] = ()
    verified_on: str = ""


@dataclass(frozen=True)
class StatuteSeed:
    """The parsed seed document: the frozen label + its statute + duty rows."""

    as_of: str
    as_of_label: str
    retrieved: str
    inventory_url: str
    state_count: int
    ncsl_table_rows: int
    statutes: tuple[StatuteSeedEntry, ...]
    schema: str = "statute_seed/1"
    supersedes_asset: str = ""
    duty_rows: tuple[StatuteDutyRow, ...] = ()
    duty_row_count: int = 0


def _drift(source_id: str, reason: str, *, details: str = "") -> ContentDrift:
    return ContentDrift(source_id, reason, details=details)


def _host_is_enumeration_aid(url: str) -> bool:
    netloc = urlsplit(url).netloc.lower()
    return any(netloc == h or netloc.endswith("." + h) for h in _ENUMERATION_AID_HOSTS)


def _parse_entries_v1(source_id: str, raw_entries: Any) -> list[StatuteSeedEntry]:
    if not isinstance(raw_entries, list):
        raise _drift(source_id, "the statute-seed asset carries no `[[statutes]]` table")
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
    return entries


def _str_list(source_id: str, what: str, value: Any, *, allow_empty: bool) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or any(not str(v).strip() for v in value):
        raise _drift(source_id, f"{what} is not a list of non-empty strings")
    out = tuple(str(v).strip() for v in value)
    if not out and not allow_empty:
        raise _drift(source_id, f"{what} must be a non-empty list")
    return out


def _parse_entries_v2(source_id: str, raw_entries: Any) -> list[StatuteSeedEntry]:
    if not isinstance(raw_entries, list):
        raise _drift(source_id, "the v2 statute-seed asset carries no `[[statutes]]` table")
    entries: list[StatuteSeedEntry] = []
    for i, entry in enumerate(raw_entries):
        where = f"statute-seed v2 entry #{i}"
        if not isinstance(entry, Mapping):
            raise _drift(source_id, f"{where} is not a TOML table")
        unknown = set(entry) - _ENTRY_KEYS_V2
        if unknown:
            raise _drift(source_id, f"{where} carries unreviewed keys {sorted(unknown)}")
        state = str(entry.get("state") or "").strip()
        if not state:
            raise _drift(source_id, f"{where} lacks a `state`")
        where = f"{where} ({state})"

        instrument_type = str(entry.get("instrument_type") or "")
        if instrument_type not in _INSTRUMENT_TYPES_V2:
            raise _drift(
                source_id,
                f"{where} `instrument_type` {instrument_type!r} not in "
                f"{sorted(_INSTRUMENT_TYPES_V2)} — the v2 seed records statutes "
                "and executive orders only (I8 §4.4)",
            )
        years = entry.get("years_enacted")
        if (
            not isinstance(years, list)
            or not years
            or any(not isinstance(y, int) or isinstance(y, bool) for y in years)
        ):
            raise _drift(source_id, f"{where} lacks a non-empty `years_enacted` int list")
        origin_url = str(entry.get("origin_url") or "")
        if not origin_url.startswith(("http://", "https://")):
            raise _drift(
                source_id,
                f"{where} lacks a fetch-shaped `origin_url` — a v2 row cites its "
                "legislature/governor origin, never an enumeration aid",
            )
        if _host_is_enumeration_aid(origin_url):
            raise _drift(
                source_id,
                f"{where} `origin_url` is an enumeration-aid host "
                f"({urlsplit(origin_url).netloc}) — NCSL/LAPPA/GHSA/MultiState "
                "enumerate; they are never cited (I7 NEW-7; C9 `a`)",
            )
        effective_date = str(entry.get("effective_date") or "")
        if not _EFFECTIVE_DATE.match(effective_date):
            raise _drift(
                source_id,
                f"{where} `effective_date` {effective_date!r} is not an ISO "
                "date (year precision allowed)",
            )
        date_basis = str(entry.get("date_basis") or "")
        if date_basis not in _DATE_BASES:
            raise _drift(
                source_id,
                f"{where} `date_basis` {date_basis!r} not in {sorted(_DATE_BASES)} "
                "— the seed records what the date actually is",
            )
        verified_on = str(entry.get("verified_on") or "")
        if not _SEED_DATE.match(verified_on):
            raise _drift(
                source_id,
                f"{where} `verified_on` {verified_on!r} is not an ISO date — "
                "the packet's origin-read day is required data",
            )
        confidence = str(entry.get("confidence") or "")
        if confidence not in _CONFIDENCES:
            raise _drift(
                source_id,
                f"{where} `confidence` {confidence!r} not in {sorted(_CONFIDENCES)}",
            )
        evidence_ids = _str_list(
            source_id, f"{where} `evidence`", entry.get("evidence"), allow_empty=False
        )
        entries.append(
            StatuteSeedEntry(
                state=state,
                years=tuple(int(y) for y in years),
                citations=_str_list(
                    source_id,
                    f"{where} `citations`",
                    entry.get("citations"),
                    allow_empty=True,
                ),
                instrument_type=instrument_type,
                origin_url=origin_url,
                effective_date=effective_date,
                date_basis=date_basis,
                verified_on=verified_on,
                confidence=confidence,
                evidence_ids=evidence_ids,
                notes=str(entry.get("notes") or "").strip(),
            )
        )
    return entries


def _parse_duty_rows(source_id: str, raw_rows: Any) -> list[StatuteDutyRow]:
    if not isinstance(raw_rows, list) or not raw_rows:
        raise _drift(
            source_id,
            "the v2 statute-seed asset carries no `[[duty_rows]]` — the "
            "50-state coverage/duty table is required data (SIG-INGEST-050)",
        )
    rows: list[StatuteDutyRow] = []
    seen: set[str] = set()
    for i, row in enumerate(raw_rows):
        where = f"statute-seed duty row #{i}"
        if not isinstance(row, Mapping):
            raise _drift(source_id, f"{where} is not a TOML table")
        unknown = set(row) - _DUTY_KEYS
        if unknown:
            raise _drift(source_id, f"{where} carries unreviewed keys {sorted(unknown)}")
        state = str(row.get("state") or "").strip()
        if not state:
            raise _drift(source_id, f"{where} lacks a `state`")
        if state in seen:
            raise _drift(
                source_id,
                f"{where} ({state}) duplicates a state — the coverage table "
                "carries exactly one row per state",
            )
        seen.add(state)
        where = f"{where} ({state})"
        posture = str(row.get("statute_posture") or "")
        if posture not in _POSTURES:
            raise _drift(
                source_id,
                f"{where} `statute_posture` {posture!r} not in {sorted(_POSTURES)}",
            )
        origin_url = str(row.get("origin_url") or "")
        instruments = _str_list(
            source_id, f"{where} `instruments`", row.get("instruments"), allow_empty=True
        )
        statute_ref = str(row.get("statute_ref") or "").strip()
        if posture == "origin_verified":
            if not origin_url.startswith(("http://", "https://")):
                raise _drift(
                    source_id,
                    f"{where} is origin_verified but lacks a fetch-shaped `origin_url`",
                )
            if not statute_ref or not instruments:
                raise _drift(
                    source_id,
                    f"{where} is origin_verified but lacks `statute_ref`/`instruments`",
                )
        if posture == "recorded" and not statute_ref:
            raise _drift(
                source_id,
                f"{where} is recorded but names no `statute_ref` — the row "
                "must say which committed asset carries the record",
            )
        if posture == "none_recorded" and (instruments or origin_url or statute_ref):
            raise _drift(
                source_id,
                f"{where} is none_recorded but carries instruments/origin/ref — "
                "none_recorded is absence of evidence, it asserts no instrument",
            )
        verified_on = str(row.get("verified_on") or "")
        if not _SEED_DATE.match(verified_on):
            raise _drift(source_id, f"{where} `verified_on` {verified_on!r} is not an ISO date")
        duties = _str_list(source_id, f"{where} `duties`", row.get("duties"), allow_empty=True)
        bad_duties = [d for d in duties if not _DUTY_ID.match(d)]
        if bad_duties:
            raise _drift(
                source_id,
                f"{where} `duties` ids {bad_duties} are not "
                "`future_statutory_disclosure_*` registry ids (SIG-INGEST-050)",
            )
        rows.append(
            StatuteDutyRow(
                state=state,
                statute_posture=posture,
                statute_ref=statute_ref,
                origin_url=origin_url,
                instruments=instruments,
                duties=duties,
                duty_notes=str(row.get("duty_notes") or "").strip(),
                evidence_ids=_str_list(
                    source_id,
                    f"{where} `evidence`",
                    row.get("evidence"),
                    allow_empty=True,
                ),
                verified_on=verified_on,
            )
        )
    return rows


def parse_statute_seed(data: bytes, *, source_id: str) -> StatuteSeed:
    """Parse the committed statute-seed TOML — STRICT shape (fail closed).

    v1 (``statute_seed/1``, the frozen 2022 asset): ``as_of``/``frozen``/
    ``never_a_feed``/``inventory_url`` plus ``[[statutes]]`` rows of
    ``{state, years_enacted, citations?}``.

    v2 (``statute_seed/2``, the 2026 origin refresh, I8 §4.4): declares
    ``schema``/``supersedes_asset``; every entry carries ``origin_url`` (a
    legislature/governor page — never an enumeration-aid host),
    ``instrument_type``, ``effective_date``, ``verified_on`` and
    ``confidence``; ``[[duty_rows]]`` is the per-state coverage table whose
    ``origin_verified`` states must equal the entry set.

    A document that is not TOML, drops the frozen flags, carries a malformed
    row, or disagrees with its declared totals is :class:`ContentDrift`: a
    seed's value is that it is reviewed data — an unreviewed shape never
    loads.
    """
    try:
        payload = tomllib.loads(data.decode("utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as exc:
        raise _drift(source_id, "the statute-seed asset is not TOML", details=str(exc)) from exc
    if not isinstance(payload, Mapping):
        raise _drift(source_id, "the statute-seed asset is not a TOML document")

    schema = str(payload.get("schema") or "statute_seed/1")
    if schema not in {"statute_seed/1", "statute_seed/2"}:
        raise _drift(
            source_id,
            f"statute-seed `schema` {schema!r} is not a reviewed shape "
            "(statute_seed/1 | statute_seed/2)",
        )

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
    if schema == "statute_seed/1":
        if not inventory_url.startswith(("http://", "https://")):
            raise _drift(source_id, "the statute-seed asset lacks its `inventory_url`")
    elif not (
        inventory_url.startswith(("http://", "https://")) or inventory_url.startswith("urn:sig:")
    ):
        # A compiled multi-origin asset has no single upstream URL; the
        # committed-asset URN is its honest provenance (P2).
        raise _drift(
            source_id,
            "the v2 statute-seed asset lacks its `inventory_url` (http(s) "
            "origin or the committed-asset `urn:sig:` id)",
        )

    supersedes_asset = ""
    duty_rows: tuple[StatuteDutyRow, ...] = ()
    if schema == "statute_seed/2":
        supersedes_asset = str(payload.get("supersedes_asset") or "")
        if supersedes_asset != _SUPERSEDES_V2:
            raise _drift(
                source_id,
                f"the v2 statute-seed `supersedes_asset` {supersedes_asset!r} is not "
                f"{_SUPERSEDES_V2!r} — the refresh names the committed asset it "
                "supersedes, append-only (P7)",
            )
        entries = _parse_entries_v2(source_id, payload.get("statutes"))
        duty_rows = tuple(_parse_duty_rows(source_id, payload.get("duty_rows")))
        verified_states = {e.state for e in entries}
        posture_states = {r.state for r in duty_rows if r.statute_posture == "origin_verified"}
        if posture_states != verified_states:
            raise _drift(
                source_id,
                f"the duty table's origin_verified states {sorted(posture_states)} "
                f"!= the [[statutes]] entry states {sorted(verified_states)} — "
                "the coverage table must name exactly the seeded instruments",
            )
    else:
        entries = _parse_entries_v1(source_id, payload.get("statutes"))

    if not entries:
        raise _drift(source_id, "the statute-seed asset carries no `[[statutes]]` rows")

    # The declared totals are part of the reviewed shape: ``state_count`` is
    # re-derived exactly; ``duty_row_count`` (v2) likewise; ``ncsl_table_rows``
    # must at least cover every state (a state occupies no fewer than one
    # NCSL table row — California occupies two).
    if "state_count" in payload and int(payload["state_count"]) != len(entries):
        raise _drift(
            source_id,
            f"statute-seed `state_count` {payload['state_count']} != parsed "
            f"{len(entries)} entries — the asset changed shape",
        )
    if "duty_row_count" in payload and int(payload["duty_row_count"]) != len(duty_rows):
        raise _drift(
            source_id,
            f"statute-seed `duty_row_count` {payload['duty_row_count']} != parsed "
            f"{len(duty_rows)} duty rows — the asset changed shape",
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
        schema=schema,
        supersedes_asset=supersedes_asset,
        duty_rows=duty_rows,
        duty_row_count=len(duty_rows),
    )


def _citation_for(entry: StatuteSeedEntry, index: int) -> str | None:
    """The citation for one enactment year, when the mapping is unambiguous.

    The reviewed tables are row-per-statute: a ``citations`` list the same
    length as ``years_enacted`` pairs positionally (California's two rows); a
    single-year state's citations all describe that one statute. Anything else
    is left off the typed claim — the raw value is preserved on the record
    regardless (P2), and a guess is never emitted.
    """
    if not entry.citations:
        return None
    if len(entry.years) == 1:
        return "; ".join(entry.citations)
    if len(entry.citations) == len(entry.years):
        return entry.citations[index]
    return None


def _duty_summary(duty_rows: tuple[StatuteDutyRow, ...]) -> dict[str, Any]:
    """The coverage/duty totals for the label record and quality report."""
    return {
        "duty_row_count": len(duty_rows),
        "states_origin_verified": sorted(
            r.state for r in duty_rows if r.statute_posture == "origin_verified"
        ),
        "states_recorded": sorted(r.state for r in duty_rows if r.statute_posture == "recorded"),
        "states_none_recorded": sorted(
            r.state for r in duty_rows if r.statute_posture == "none_recorded"
        ),
        "duty_sources": sorted({d for r in duty_rows for d in r.duties}),
    }


@register
class StateStatuteSeedConnector(Connector):
    """Loads a committed statute-inventory seed into the claim spine (P25.7).

    ``fetch`` is protocol conformance only: the seed path serves the packaged
    asset over the static transport, so this connector never egresses.
    """

    name = "state_statute_seed"
    version = "1.1.0"  # P35.10: the statute_seed/2 origin-verified refresh

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
            "seed_schema": parsed.schema,
        }
        label_raw: dict[str, Any] = {
            "as_of": parsed.as_of,
            "as_of_label": parsed.as_of_label,
            "retrieved": parsed.retrieved,
            "inventory_url": parsed.inventory_url,
            "state_count": parsed.state_count,
            "ncsl_table_rows": parsed.ncsl_table_rows,
            "frozen": True,
            "never_a_feed": True,
            "schema": parsed.schema,
            "supersedes_asset": parsed.supersedes_asset,
            "duty_rows": [
                {
                    "state": r.state,
                    "statute_posture": r.statute_posture,
                    "statute_ref": r.statute_ref,
                    "origin_url": r.origin_url,
                    "instruments": list(r.instruments),
                    "duties": list(r.duties),
                    "duty_notes": r.duty_notes,
                    "evidence": list(r.evidence_ids),
                    "verified_on": r.verified_on,
                }
                for r in parsed.duty_rows
            ],
            **_duty_summary(parsed.duty_rows),
        }
        records: list[Mapping[str, Any]] = [
            {
                "record_kind": "statute_seed_label",
                "raw": label_raw,
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
                        "instrument_type": entry.instrument_type,
                        "origin_url": entry.origin_url,
                        "effective_date": entry.effective_date,
                        "date_basis": entry.date_basis,
                        "verified_on": entry.verified_on,
                        "confidence": entry.confidence,
                        "evidence": list(entry.evidence_ids),
                        "notes": entry.notes,
                    },
                    # Per-entry provenance for v2: the legislature/governor
                    # origin + its verification day ride the record's own
                    # evidence; the label's inventory-level evidence stays for
                    # v1 rows (which carry no per-entry origin).
                    "_evidence": (
                        {
                            "source_url": entry.origin_url,
                            "retrieved_date": entry.verified_on,
                            "as_of": parsed.as_of,
                            "extraction_method": "statute_seed_toml",
                            "seed_schema": parsed.schema,
                            "evidence_ids": list(entry.evidence_ids),
                        }
                        if entry.origin_url
                        else evidence
                    ),
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
                # dedicated `as_of` claim carries the recorded label as its
                # raw value (P2), beside a quality report for the run.
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
                            "schema": str(raw.get("schema") or "statute_seed/1"),
                            "supersedes_asset": str(raw.get("supersedes_asset") or ""),
                            "duty_row_count": int(raw.get("duty_row_count") or 0),
                            "states_origin_verified": int(
                                len(raw.get("states_origin_verified") or ())
                            ),
                            "states_recorded": int(len(raw.get("states_recorded") or ())),
                            "states_none_recorded": int(len(raw.get("states_none_recorded") or ())),
                            "duty_source_count": int(len(raw.get("duty_sources") or ())),
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
                instrument_type=str(raw.get("instrument_type") or "statute"),
                origin_url=str(raw.get("origin_url") or ""),
                effective_date=str(raw.get("effective_date") or ""),
                date_basis=str(raw.get("date_basis") or ""),
                verified_on=str(raw.get("verified_on") or ""),
            )
            for i, year in enumerate(entry.years):
                instrument = LegalInstrument(
                    external_id=f"ncsl:{entry.state}:{year}"
                    if not entry.origin_url
                    else f"state-seed-2026:{entry.state}:{year}",
                    source_id=ctx.source.id,
                    instrument_type=entry.instrument_type,
                    jurisdiction=entry.state,
                    jurisdiction_scheme="us.state",
                    citation=_citation_for(entry, i),
                    # v2 rows carry a real ISO effective date; v1 rows carry
                    # the enactment year the NCSL table recorded.
                    effective_from=entry.effective_date or str(year),
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
    "StatuteDutyRow",
    "StatuteSeed",
    "StatuteSeedEntry",
    "parse_statute_seed",
]
