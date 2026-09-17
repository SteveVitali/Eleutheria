# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The `agency_registry` connector — the FBI CDE ORI9 agency substrate (P26.2 / SOURCES.2).

A source adapter on the P04.1 eight-stage framework (:mod:`connectors.stages`) for
the FBI Crime Data Explorer **agency registry** (§14.2 identity substrate). It is
NOT a records or procurement connector: the CDE ``/agency/byStateAbbr/{ST}``
endpoint answers the question "which law-enforcement agencies exist, under which
ORI9?" — an **identity** surface the rest of the pipeline keys agency resolution
on. Each returned agency object is an ``agency_registry_entry`` carrying its ORI,
name, state, county set, agency type, NIBRS participation and registry
coordinates — and nothing more. The connector never asserts a deployment, a
device, or a headcount: the registry says an agency *exists*, not what it runs
(the predicate allowlist in ``data/agency_registry_vocab.toml`` enforces that,
SIG-INGEST-033).

Conduct rules this adapter upholds:

* **Targeted lookups only** (SIG-INGEST-036/037): a target names one state
  (``byStateAbbr/OK``) — a documented bounded read of one registry slice. The
  connector never enumerates states it was not configured for.
* **The api.data.gov key is auth, never stored** (HG-09): the fetch resolves
  ``$SIG_DATA_GOV_KEY`` at call time, falling back to api.data.gov's documented
  public ``DEMO_KEY`` (published upstream for exploration, heavily rate-limited).
  A keyless/invalid-key 403 is a recorded disappearance — never defeated.
* **Raw preserved, never coerced** (P2, SIG-INGEST-017): a payload whose shape
  drifts (no county map, agencies without ``ori``) raises :class:`ContentDrift`,
  recorded loud — the connector reads exactly what the capture holds.
* **Candidate identifiers, never resolution** (SIG-INGEST-034): the ORI and the
  agency name are emitted as ``(scheme, value)`` candidates for the identity
  layer (P03.2/P05.1); the connector resolves nothing.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
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
    """The versioned `agency_registry` vocabulary (``data/agency_registry_vocab.toml``)."""
    return load_table("agency_registry_vocab")


def vocab_version() -> str:
    """The connector vocabulary version stamped onto every run (§20)."""
    return str(vocab()["vocab_version"])


def source_ids() -> Mapping[str, str]:
    """The registry source ids the connector runs against, by role key (§22.6)."""
    return dict(vocab()["sources"])


def cde_config() -> Mapping[str, Any]:
    """The FBI CDE API facts (``[cde]`` in the vocab)."""
    return vocab()["cde"]


def field_map() -> Mapping[str, str]:
    """The CDE agency-object field → predicate map (``[field_map]`` in the vocab)."""
    return dict(vocab()["field_map"])


# --- the predicate allowlist (SIG-INGEST-033) ---------------------------------


class PredicateNotAllowed(Exception):
    """A schema error: the connector tried to write outside its predicate allowlist."""


def predicate_allowlist() -> frozenset[str]:
    """The predicates this connector may write (SIG-INGEST-033)."""
    return frozenset(vocab()["predicate_allowlist"])


def assert_predicate_allowed(predicate: str) -> str:
    """Return ``predicate`` if allowed, else raise :class:`PredicateNotAllowed`.

    The registry is an identity substrate: an ``agency_registry_entry`` and its
    ORI/name/state/county/type/NIBRS/coordinate predicates are the whole
    write-set — a deployment, a device count, or a personnel claim is refused
    here, at the ingestion boundary (SIG-INGEST-033, §10.5 D6).
    """
    if not is_predicate_allowed(predicate):
        raise PredicateNotAllowed(
            f"the agency_registry connector may write only "
            f"{sorted(predicate_allowlist())} (§14.2, SIG-INGEST-033); {predicate!r} is "
            "outside the allowlist — deployments, devices, and personnel are refused."
        )
    return predicate


def is_predicate_allowed(predicate: str) -> bool:
    """Whether ``predicate`` is in the connector's allowlist (SIG-INGEST-033)."""
    return predicate in predicate_allowlist()


# --- the agency-registry entry -------------------------------------------------


@dataclass(frozen=True)
class AgencyRegistryEntry:
    """One ORI-keyed agency row from the CDE registry (§14.2).

    The whole point of the entity is identity: an agency exists under an ORI9,
    in a state/county, of an agency type, with NIBRS participation as recorded.
    ``ori`` is required — it is the join key the identity layer resolves on.
    """

    ori: str
    source_id: str
    agency_name: str | None = None
    state_abbr: str | None = None
    state_name: str | None = None
    counties: str | None = None
    agency_type: str | None = None
    is_nibrs: bool | None = None
    nibrs_start_date: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    raw: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        if not str(self.ori).strip():
            raise ValueError("an AgencyRegistryEntry requires an ori (the ORI9 join key)")

    @property
    def subject_id(self) -> str:
        """The claim subject id for this agency entry (source + ORI scoped)."""
        return f"agency_registry_entry:{self.source_id}:{self.ori}"

    def predicate_values(self) -> dict[str, Any]:
        """The predicate → value map for the set predicates (allowlisted keys only)."""
        candidates: dict[str, Any] = {
            "agency_ori9": self.ori,
            "agency_name": self.agency_name,
            "agency_state": self.state_abbr,
            "agency_county": self.counties,
            "agency_type": self.agency_type,
            "nibrs_participant": (
                str(self.is_nibrs).lower() if self.is_nibrs is not None else None
            ),
            "nibrs_start_date": self.nibrs_start_date,
            "agency_latitude": (str(self.latitude) if self.latitude is not None else None),
            "agency_longitude": (str(self.longitude) if self.longitude is not None else None),
            "external_id": self.ori,
        }
        return {k: v for k, v in candidates.items() if v is not None}

    def claim_rows(self) -> list[dict[str, Any]]:
        """The append-only claim rows for this entry, confined to the allowlist (P2).

        One ``agency_registry_entry`` entity row (carrying the whole predicate
        surface for provenance) plus one row per set predicate. The ORI is a
        ``us.fbi.ori`` candidate identifier, the name a name candidate, the state
        a ``us.state_abbr`` jurisdiction candidate — never resolutions
        (SIG-INGEST-034). ``raw_value`` is preserved beside every typed value.
        """
        rows: list[dict[str, Any]] = [
            _stamp(
                {
                    "record_kind": "agency_registry_entry",
                    "subject_id": self.subject_id,
                    "predicate_id": assert_predicate_allowed("agency_registry_entry"),
                    "external_id": self.ori,
                    "raw_value": self.ori,
                    "predicate_surface": self.predicate_values(),
                    "raw": dict(self.raw or {}),
                },
                source_id=self.source_id,
            )
        ]
        for predicate, value in self.predicate_values().items():
            row: dict[str, Any] = {
                "record_kind": "claim",
                "subject_id": self.subject_id,
                "predicate_id": assert_predicate_allowed(predicate),
                "raw_value": str(value),
                "value": value,
            }
            if predicate == "agency_ori9":
                row["candidate_identifier"] = {
                    "scheme": "us.fbi.ori",
                    "value": self.ori,
                }
            elif predicate == "agency_name":
                row["candidate_identifier"] = {
                    "scheme": "agency_registry.org_name",
                    "value": str(value),
                }
            elif predicate == "agency_state":
                row["candidate_identifier"] = {
                    "scheme": "us.state_abbr",
                    "value": str(value),
                }
            rows.append(_stamp(row, source_id=self.source_id))
        return rows


# --- the connector ------------------------------------------------------------


@register
class AgencyRegistryConnector(Connector):
    """The `agency_registry` connector: the FBI CDE ORI9 identity substrate (P26.2).

    Runs on the P04.1 eight-stage framework as a **targeted-lookup** client:
    ``discover`` returns the supplied per-state targets; ``fetch`` egresses
    through the shared politeness layer with the data.gov key resolved from the
    environment (HG-09); ``parse``/``extract``/``normalize`` are pure functions
    of the capture that flatten the ``{county: [agency]}`` shape into
    :class:`AgencyRegistryEntry` rows. Shape drift is :class:`ContentDrift`,
    recorded loud — never a silent empty set.
    """

    name = "agency_registry"
    version = "1.0.0"

    # -- acquisition --
    def discover(self, ctx: RunContext) -> list[Mapping[str, Any]]:
        """Enumerate fetch targets — explicitly supplied per-state lookups only."""
        return list(ctx.parameters.get("targets", []))

    def fetch(self, ctx: RunContext, target: Mapping[str, Any]) -> FetchResult:
        """Obtain bytes for one target through the shared politeness layer only.

        The data.gov API key is resolved from ``$SIG_DATA_GOV_KEY`` at call time
        (HG-09 — auth, never the rights basis and never stored in a file),
        falling back to api.data.gov's documented ``DEMO_KEY``; an invalid-key
        403 rides to the disappearance layer unmodified (SIG-INGEST-013).
        """
        assert ctx.fetcher is not None, "connectors fetch only through the shared layer"
        cfg = cde_config()
        key = os.environ.get(str(cfg["api_key_env"]), "").strip() or str(cfg.get("demo_key", ""))
        url = str(target["url"])
        # The api.data.gov credential rides the reviewed X-Api-Key request header
        # (P26.4), never the URL — a keyed query would land in the capture's
        # recorded source_uri and run records (HG-09).
        if key:
            return ctx.fetcher.fetch(url, headers={str(cfg["api_key_header"]): key})
        return ctx.fetcher.fetch(url)

    # -- interpretation (pure functions of the capture) --
    def parse(self, ctx: RunContext, capture: CaptureRef) -> dict[str, Any]:
        """Structure the captured JSON registry slice (pure, network-isolated)."""
        data = ctx.captures.get(capture.digest)
        return {"kind": "agency_registry_payload", "payload": json.loads(data), "capture": capture}

    def extract(self, ctx: RunContext, parsed: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        """Raw agency records with locators, preserving raw values (P2).

        The CDE response is ``{<COUNTY>: [ {agency}, … ]}``; a metadata-only
        envelope (``{"cde_agencies_query": {…}}`` — the shape the API answers for
        an odd parameter fold) yields zero agency rows and a
        ``registry_query_meta`` record so the response is retained honestly,
        never mistaken for an empty registry.
        """
        payload = parsed["payload"]
        if not isinstance(payload, Mapping):
            raise ContentDrift(
                ctx.source.id,
                "agency-registry payload is not an object",
                details=f"got {type(payload).__name__}; expected a county→agencies map",
            )
        if "cde_agencies_query" in payload and not _has_agency_rows(payload):
            return [
                {
                    "record_kind": "registry_query_meta",
                    "raw": dict(payload.get("cde_agencies_query") or payload),
                }
            ]
        out: list[Mapping[str, Any]] = []
        for county, agencies in payload.items():
            if not isinstance(agencies, list):
                continue
            for agency in agencies:
                if not isinstance(agency, Mapping) or not str(agency.get("ori") or "").strip():
                    keys = sorted(agency) if isinstance(agency, Mapping) else type(agency).__name__
                    raise ContentDrift(
                        ctx.source.id,
                        "an agency row has no ori",
                        details=f"county {county!r} row keys: {keys}",
                    )
                record = dict(agency)
                record.setdefault("counties", county)
                out.append({"record_kind": "agency_registry_entry", "raw": record})
        return out

    def normalize(
        self, ctx: RunContext, raw_claims: list[Mapping[str, Any]]
    ) -> list[dict[str, Any]]:
        """Typed rows beside preserved raw values (P2), confined to the allowlist."""
        out: list[dict[str, Any]] = []
        for raw in raw_claims:
            if raw["record_kind"] == "registry_query_meta":
                out.append(
                    _stamp(
                        {
                            "record_kind": "registry_query_meta",
                            "subject_id": f"agency_registry:{ctx.source.id}",
                            "predicate_id": assert_predicate_allowed("agency_registry_entry"),
                            "raw_value": "cde_agencies_query metadata envelope",
                            "raw": dict(raw["raw"]),
                        },
                        source_id=ctx.source.id,
                    )
                )
                continue
            out.extend(_entry_from_raw(ctx.source.id, raw["raw"]).claim_rows())
        return out

    # -- link + load --
    # link() is inherited (identity): SIG-INGEST-034 — candidate identifiers only.

    def load(self, ctx: RunContext, linked: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Produce the L1 rows; the driver asserts them (live only, SIG-INGEST-003)."""
        return load_claims_for_l1(linked)


# --- module-private helpers ---------------------------------------------------


def _entry_from_raw(source_id: str, raw: Mapping[str, Any]) -> AgencyRegistryEntry:
    """Map a raw CDE agency object onto :class:`AgencyRegistryEntry` (field_map)."""

    def _s(key: str) -> str | None:
        value = raw.get(key)
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _f(key: str) -> float | None:
        value = raw.get(key)
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    is_nibrs = raw.get("is_nibrs")
    return AgencyRegistryEntry(
        ori=str(raw.get("ori") or ""),
        source_id=source_id,
        agency_name=_s("agency_name"),
        state_abbr=_s("state_abbr"),
        state_name=_s("state_name"),
        counties=_s("counties"),
        agency_type=_s("agency_type_name"),
        is_nibrs=(bool(is_nibrs) if is_nibrs is not None else None),
        nibrs_start_date=_s("nibrs_start_date"),
        latitude=_f("latitude"),
        longitude=_f("longitude"),
        raw=dict(raw),
    )


def _has_agency_rows(payload: Mapping[str, Any]) -> bool:
    """Whether the payload carries any county→agency rows."""
    return any(isinstance(v, list) and v for k, v in payload.items() if k != "cde_agencies_query")


def _stamp(row: dict[str, Any], *, source_id: str) -> dict[str, Any]:
    """Stamp a row with its source id and the connector vocabulary version (§20)."""
    row.setdefault("source_id", source_id)
    row.setdefault("vocab_version", vocab_version())
    return row


def load_claims_for_l1(claims: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Add the generated ``claim_id`` + transaction time each L1 claim/entity row needs.

    ``claim_id`` and ``sys_period`` are the two non-deterministic columns the
    reproducibility fingerprint excludes (SIG-INGEST-003). Only claim/entity rows
    get an identity + transaction time; metadata rows keep their own keys.
    """
    stamped_kinds = {"agency_registry_entry", "claim"}
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
    "AgencyRegistryConnector",
    "AgencyRegistryEntry",
    "PredicateNotAllowed",
    "assert_predicate_allowed",
    "cde_config",
    "field_map",
    "is_predicate_allowed",
    "load_claims_for_l1",
    "predicate_allowlist",
    "source_ids",
    "vocab",
    "vocab_version",
]
