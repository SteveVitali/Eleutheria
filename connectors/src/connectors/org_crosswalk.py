# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The `org_crosswalk` connector — organisation-identity crosswalk intake (P37.46a).

The four crosswalk lanes of R11-CONF-13 13a (design CP-10): SAM UEI
(``us.sam.uei``), Census-of-Governments GEOID (``us.census.geoid``), Wikidata
QID (``wikidata.qid``) and the LEAIC ORI↔FIPS crosswalk (``us.fbi.ori`` +
established GEOID). The FBI-CDE ORI lane lands through the separate
``agency_registry`` connector; this one serves the registry sources named in
``data/org_crosswalk_vocab.toml`` (§22.6 — one connector, a closed lane set).

Each lane row is an upstream registry's own assertion that an organisation
exists under external identifiers. The connector emits **candidate
identifiers, never resolutions** (SIG-INGEST-034): one ``org_crosswalk_entry``
subject per upstream row, ``external_id`` claims carrying the
``candidate_identifier`` pair, plus the name/jurisdiction/type surface the
cascade reads. Where a single upstream row carries several schemes (a
Wikidata entity's ORI statement, a LEAIC ORI↔FIPS row), every identifier is
asserted on the same subject — that is the *established upstream crosswalk*
the deterministic cascade's tier 1 consumes (§14.6). The tier-0/1 id lanes
themselves run only under their source's own ``ingestion_permitted`` posture
(HG-03): an un-flipped lane replays committed fixtures and is refused live by
the loader gate, never bypassed.

Conduct rules this adapter upholds:

* **Identity surface only** (SIG-INGEST-033): the predicate allowlist refuses
  a deployment, device or personnel claim — the registry says an organisation
  *exists under these ids*, not what it runs.
* **Aggregate/organisation rows only** (Part VIII): a row naming a natural
  person is refused by the same person-shape rules the partner-identity layer
  enforces; a registry row with no key-field id raises :class:`ContentDrift`,
  recorded loud — never a silent empty set.
* **Targeted, bounded reads** (SIG-INGEST-036/037): targets name the reviewed
  extract/endpoint URLs; the connector never enumerates beyond them.
"""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import cache
from typing import Any
from uuid import uuid4

from ._data import load_table
from .stages import (
    CaptureRef,
    Connector,
    ContentDrift,
    FetchResult,
    RunContext,
    register,
)

# --- the versioned vocabulary (data, not code — §20, SIG-ENG-001) -------------


@cache
def vocab() -> dict[str, Any]:
    """The versioned `org_crosswalk` vocabulary (``data/org_crosswalk_vocab.toml``)."""
    return load_table("org_crosswalk_vocab")


def vocab_version() -> str:
    """The connector vocabulary version stamped onto every run (§20)."""
    return str(vocab()["vocab_version"])


def lanes() -> Mapping[str, Mapping[str, Any]]:
    """The per-lane intake declarations (``[lanes.*]``)."""
    return dict(vocab()["lanes"])


def source_ids() -> Mapping[str, str]:
    """The registry source ids the connector serves, by lane role."""
    return dict(vocab()["sources"])


def lane_for_source(source_id: str) -> str | None:
    """The lane a registry source id feeds, or ``None``."""
    for role, sid in source_ids().items():
        if sid == source_id:
            return role
    return None


# --- the predicate allowlist (SIG-INGEST-033) ---------------------------------


class PredicateNotAllowed(Exception):
    """A schema error: the connector tried to write outside its predicate allowlist."""


def predicate_allowlist() -> frozenset[str]:
    """The predicates this connector may write (SIG-INGEST-033)."""
    return frozenset(vocab()["predicate_allowlist"])


def is_predicate_allowed(predicate: str) -> bool:
    """Whether ``predicate`` is in the connector's allowlist."""
    return predicate in predicate_allowlist()


def assert_predicate_allowed(predicate: str) -> str:
    """Return ``predicate`` if allowed, else raise :class:`PredicateNotAllowed`.

    The crosswalk intake is an identity substrate: the registry-entry record and
    its name/jurisdiction/type/external-id predicates are the whole write-set —
    a deployment, device or personnel claim is refused at this boundary.
    """
    if not is_predicate_allowed(predicate):
        raise PredicateNotAllowed(
            f"the org_crosswalk connector may write only "
            f"{sorted(predicate_allowlist())} (§14.2, SIG-INGEST-033); {predicate!r} is "
            "outside the allowlist — deployments, devices, and personnel are refused."
        )
    return predicate


# --- the crosswalk org record -------------------------------------------------


def _field(row: Mapping[str, Any], names: Iterable[str]) -> str | None:
    """The first non-empty string among candidate field names, else ``None``."""
    for name in names:
        value = row.get(name)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


@dataclass(frozen=True)
class CrosswalkOrg:
    """One upstream registry's assertion of an organisation (§14.2 identity row).

    ``key`` is the lane's upstream id (a UEI, GEOID, QID or ORI); ``identifiers``
    is the full ``{scheme: value}`` set the row carries — the lane's own key id
    plus any upstream-declared crosswalk ids. A row with no key id is
    :class:`ContentDrift` upstream, never minted.
    """

    lane: str
    key: str
    scheme: str
    source_id: str
    name: str | None = None
    state: str | None = None
    organization_class: str = "us.org"
    identifiers: Mapping[str, str] = field(default_factory=dict)
    raw: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        if not str(self.key).strip():
            raise ValueError("a CrosswalkOrg requires a key (the lane's upstream id)")

    @property
    def subject_id(self) -> str:
        """The claim subject id — lane + upstream-key scoped (§22.6)."""
        return f"org_crosswalk_entry:{self.lane}:{self.key}"

    def claim_rows(self) -> list[dict[str, Any]]:
        """The append-only claim rows, confined to the allowlist (P2).

        One ``agency_registry_entry`` surface row (the registry record itself)
        plus one ``external_id`` claim per carried identifier — each bearing the
        ``candidate_identifier`` pair the intake apply asserts onto the
        organisation's ``entity_identifier`` row — and the name/jurisdiction/
        type claims the cascade reads. Person-shaped names mint no org claim
        (Part VIII — the never-a-person rule, checked here the same way the
        partner-identity layer checks it).
        """
        from resolution.partner_identity import PartnerIdentity, partner_identity

        surface: dict[str, Any] = {
            "lane": self.lane,
            "scheme": self.scheme,
            "key": self.key,
            "identifiers": dict(self.identifiers),
        }
        rows: list[dict[str, Any]] = [
            _stamp(
                {
                    "record_kind": "org_crosswalk_entry",
                    "subject_id": self.subject_id,
                    "predicate_id": assert_predicate_allowed("agency_registry_entry"),
                    "external_id": self.key,
                    "raw_value": self.key,
                    "predicate_surface": surface,
                    "raw": dict(self.raw or {}),
                },
                source_id=self.source_id,
            )
        ]
        if self.name:
            # A natural-person-shaped name is refused by the identity rules —
            # sole traders hold UEIs too; such a row keeps its surface record
            # but asserts no organisation name (Part VIII, ADR-163).
            ident = partner_identity(self.name)
            if isinstance(ident, PartnerIdentity):
                rows.append(
                    _stamp(
                        {
                            "record_kind": "claim",
                            "subject_id": self.subject_id,
                            "predicate_id": assert_predicate_allowed("organization_legal_name"),
                            "raw_value": self.name,
                            "value": self.name,
                            "candidate_identifier": {
                                "scheme": "sig.org.name",
                                "value": self.name,
                            },
                        },
                        source_id=self.source_id,
                    )
                )
            else:
                rows.append(
                    _stamp(
                        {
                            "record_kind": "claim",
                            "subject_id": self.subject_id,
                            "predicate_id": assert_predicate_allowed("organization_legal_name"),
                            "raw_value": "[suppressed: person-shaped]",
                            "value": None,
                            "part_viii_suppressed": True,
                        },
                        source_id=self.source_id,
                    )
                )
        if self.state:
            rows.append(
                _stamp(
                    {
                        "record_kind": "claim",
                        "subject_id": self.subject_id,
                        "predicate_id": assert_predicate_allowed("organization_jurisdiction"),
                        "raw_value": self.state,
                        "value": self.state,
                        "candidate_identifier": {
                            "scheme": "us.state_abbr",
                            "value": self.state,
                        },
                    },
                    source_id=self.source_id,
                )
            )
        rows.append(
            _stamp(
                {
                    "record_kind": "claim",
                    "subject_id": self.subject_id,
                    "predicate_id": assert_predicate_allowed("organization_type"),
                    "raw_value": self.organization_class,
                    "value": self.organization_class,
                },
                source_id=self.source_id,
            )
        )
        for scheme, value in sorted(self.identifiers.items()):
            predicate = "organization_ori" if scheme == "us.fbi.ori" else "external_id"
            rows.append(
                _stamp(
                    {
                        "record_kind": "claim",
                        "subject_id": self.subject_id,
                        "predicate_id": assert_predicate_allowed(predicate),
                        "raw_value": str(value),
                        "value": str(value),
                        "candidate_identifier": {"scheme": scheme, "value": str(value)},
                    },
                    source_id=self.source_id,
                )
            )
        return rows


# --- per-lane payload parsing --------------------------------------------------


def _sparql_rows(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Flatten a ``sparql-results+json`` body into plain field→value rows."""
    results = payload.get("results")
    bindings = (results or {}).get("bindings")
    if not isinstance(bindings, list):
        raise ContentDrift(
            "wikidata_sparql",
            "SPARQL payload has no results.bindings list",
            details=f"got keys {sorted(payload)}",
        )
    rows: list[dict[str, Any]] = []
    for b in bindings:
        if not isinstance(b, Mapping):
            continue
        row: dict[str, Any] = {}
        for key, cell in b.items():
            if isinstance(cell, Mapping) and "value" in cell:
                row[str(key)] = str(cell["value"])
        rows.append(row)
    return rows


def _csv_rows(text: str) -> list[dict[str, Any]]:
    reader = csv.DictReader(io.StringIO(text))
    return [dict(r) for r in reader]


def _payload_rows(data: bytes, *, lane: str, source_id: str) -> list[dict[str, Any]]:
    """Structure a lane capture into raw row dicts (pure, network-isolated)."""
    text = data.decode("utf-8", errors="replace").lstrip("\ufeff").strip()
    if not text:
        raise ContentDrift(source_id, f"{lane} capture is empty")
    if text.startswith("{") or text.startswith("["):
        payload = json.loads(text)
        if lane == "wikidata_qid" or (isinstance(payload, Mapping) and "results" in payload):
            return _sparql_rows(payload)
        if isinstance(payload, list):
            return [dict(r) for r in payload if isinstance(r, Mapping)]
        for key in ("rows", "entities", "records", "agency", "agencies"):
            rows = payload.get(key)
            if isinstance(rows, list):
                return [dict(r) for r in rows if isinstance(r, Mapping)]
        raise ContentDrift(
            source_id,
            f"{lane} payload has no row list",
            details=f"got keys {sorted(payload)}",
        )
    return _csv_rows(text)


def _org_from_row(
    lane: str, lane_cfg: Mapping[str, Any], raw: Mapping[str, Any], *, source_id: str
) -> CrosswalkOrg:
    """Map one upstream row onto a :class:`CrosswalkOrg` (the lane's field map)."""
    key = _field(raw, (str(lane_cfg["key_field"]),))
    if not key:
        raise ContentDrift(
            source_id,
            f"a {lane} row has no {lane_cfg['key_field']} key",
            details=f"row keys: {sorted(raw)}",
        )
    identifiers: dict[str, str] = {str(lane_cfg["scheme"]): key}
    for field_name, scheme in dict(lane_cfg.get("established") or {}).items():
        value = _field(raw, (field_name,))
        if value:
            identifiers[str(scheme)] = value
    class_hint = lane_cfg.get("class_hint", "us.org")
    org_class = (
        _field(raw, (str(class_hint),)) if not str(class_hint).startswith("us.") else None
    ) or str(class_hint)
    return CrosswalkOrg(
        lane=lane,
        key=key,
        scheme=str(lane_cfg["scheme"]),
        source_id=source_id,
        name=_field(raw, lane_cfg.get("name_fields") or ()),
        state=_field(raw, lane_cfg.get("state_fields") or ()),
        organization_class=org_class,
        identifiers=identifiers,
        raw=dict(raw),
    )


# --- the connector ------------------------------------------------------------


@register
class OrgCrosswalkConnector(Connector):
    """The `org_crosswalk` connector: organisation-identity crosswalk lanes (P37.46a).

    Runs on the P04.1 eight-stage framework as a **targeted-lookup** client:
    ``discover`` returns the supplied lane targets; ``fetch`` egresses through
    the shared politeness layer only; ``parse``/``extract``/``normalize`` are
    pure functions of the capture that flatten the lane payload into
    :class:`CrosswalkOrg` rows. The lane is chosen by the running source's
    registry id (the vocab's ``[sources]`` map) — a source the map does not
    know drifts loud rather than guessing a lane.
    """

    name = "org_crosswalk"
    version = "1.0.0"
    ingestion_mode = "bulk_file_download"
    incrementality = "versioned extract re-run (append-only claims)"

    # -- acquisition --
    def discover(self, ctx: RunContext) -> list[Mapping[str, Any]]:
        """Enumerate fetch targets — explicitly supplied lane extracts only."""
        return list(ctx.parameters.get("targets", []))

    def fetch(self, ctx: RunContext, target: Mapping[str, Any]) -> FetchResult:
        """Obtain bytes for one target through the shared politeness layer only."""
        assert ctx.fetcher is not None, "connectors fetch only through the shared layer"
        return ctx.fetcher.fetch(str(target["url"]))

    # -- interpretation (pure functions of the capture) --
    def parse(self, ctx: RunContext, capture: CaptureRef) -> dict[str, Any]:
        """Structure the captured lane payload (pure, network-isolated)."""
        data = ctx.captures.get(capture.digest)
        lane = lane_for_source(ctx.source.id)
        if lane is None:
            raise ContentDrift(
                ctx.source.id,
                f"source {ctx.source.id!r} is not a declared org_crosswalk lane",
                details=f"declared: {sorted(source_ids().values())}",
            )
        rows = _payload_rows(data, lane=lane, source_id=ctx.source.id)
        return {"kind": "org_crosswalk_payload", "lane": lane, "rows": rows}

    def extract(self, ctx: RunContext, parsed: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        """Raw org records, preserving raw values (P2)."""
        return [
            {"record_kind": "org_crosswalk_row", "lane": parsed["lane"], "raw": dict(r)}
            for r in parsed["rows"]
        ]

    def normalize(
        self, ctx: RunContext, raw_claims: list[Mapping[str, Any]]
    ) -> list[dict[str, Any]]:
        """Typed rows beside preserved raw values (P2), confined to the allowlist."""
        lane = lane_for_source(ctx.source.id)
        assert lane is not None
        lane_cfg = lanes()[lane]
        out: list[dict[str, Any]] = []
        for raw in raw_claims:
            org = _org_from_row(str(raw["lane"]), lane_cfg, raw["raw"], source_id=ctx.source.id)
            out.extend(org.claim_rows())
        return out

    # -- link + load --
    # link() is inherited (identity): SIG-INGEST-034 — candidate identifiers only.

    def load(self, ctx: RunContext, linked: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Produce the L1 rows; the driver asserts them (live only, SIG-INGEST-003)."""
        return load_claims_for_l1(linked)


# --- module-private helpers ---------------------------------------------------


def _stamp(row: dict[str, Any], *, source_id: str) -> dict[str, Any]:
    """Stamp a row with its source id and the connector vocabulary version (§20)."""
    row.setdefault("source_id", source_id)
    row.setdefault("vocab_version", vocab_version())
    return row


def load_claims_for_l1(claims: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Add the generated ``claim_id`` + transaction time each L1 claim row needs."""
    stamped_kinds = {"org_crosswalk_entry", "claim"}
    out: list[dict[str, Any]] = []
    for claim in claims:
        if claim.get("record_kind") in stamped_kinds:
            out.append(
                {
                    **claim,
                    "claim_id": str(uuid4()),
                    "sys_period": f"[{datetime.now(UTC).isoformat()},)",
                }
            )
        else:
            out.append(dict(claim))
    return out


__all__ = [
    "CrosswalkOrg",
    "OrgCrosswalkConnector",
    "PredicateNotAllowed",
    "assert_predicate_allowed",
    "is_predicate_allowed",
    "lane_for_source",
    "lanes",
    "load_claims_for_l1",
    "predicate_allowlist",
    "source_ids",
    "vocab",
    "vocab_version",
]
