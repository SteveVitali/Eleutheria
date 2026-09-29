# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""A repeatable, **read-only** public-surface data & rights audit over the spine (P27.1, LAUNCH.1).

The public web renders the OKC fixture demo while the hosted spine holds ~1.06M claims. Before
P27 builds the national export/web, this verb measures exactly what a public surface can honestly
show — publishable fraction, geolocated inventory, jurisdiction spread, and the modeling gap —
deterministically over **any** spine. It is the durable deliverable; the *numbers* it emits are an
as-of snapshot.

Design constraints (the invariants this module never relaxes):

* **Read-only (append-only spine, §16).** Every statement is a ``SELECT``; :func:`run_audit` puts
  the session in read-only mode so the connection *cannot* write even by accident. No
  INSERT/UPDATE/DELETE, no source flip, no publication.
* **Never a bare total (§32 / SIG-METRIC-008).** Every count is reported with its **named
  denominator** (a :class:`Fraction`) — the coverage-honesty rule. "75,479 geolocated" is
  meaningless without "of 92,169 entities".
* **Part VIII §0.7 / §19.4 / §43.3.** The audit reports coordinates **only in aggregate** (a
  distinct geolocated-entity count + jurisdiction spread) and never emits a per-person, per-plate,
  or raw-coordinate field. Jurisdiction granularity only.
* **Deterministic.** Given a spine state the output bytes are stable: SQL orders every result and
  the Python assembler re-sorts, so a diff of two runs is a diff of the *spine*, never of the verb.

The pure assembler :func:`build_spine_audit` builds a :class:`SpineAudit` from already-fetched query
rows (unit-tested with no database); :func:`run_audit` is the thin executor that fetches those rows
from a live connection. Both feed :meth:`SpineAudit.to_json` / :meth:`SpineAudit.to_markdown` — the
latter is the body of ``docs/build/reports/PUBLIC_SURFACE_AUDIT.md``.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol

#: The audit output schema version — bumped when the emitted shape changes.
AUDIT_SCHEMA_VERSION = "p27.1/1.0.0"

#: The geolocation predicates coordinates live under (as text) on the claim spine.
GEO_PREDICATES = ("camera_latitude", "camera_longitude")

#: The jurisdiction predicate whose value_text carries the (coarse) jurisdiction label.
JURISDICTION_PREDICATE = "camera_jurisdiction"

#: The modeling tables the shaping work (P27.3) populates; the audit reports their population so the
#: "everything is a bare claim, nothing is assembled" gap is a measured fact, not an assumption.
MODELING_TABLES = (
    "resolution",
    "jurisdiction",
    "coverage_record",
    "relationship",
    "organization_relation",
    "physical_asset",
    "deployment",
    "contradiction",
    "legal_instrument",
    "policy",
)


class _Cursor(Protocol):
    """The minimal cursor surface :func:`run_audit` uses (psycopg-compatible)."""

    def execute(self, query: str, params: Sequence[Any] | None = ...) -> Any: ...
    def fetchone(self) -> Any: ...
    def fetchall(self) -> list[Any]: ...


class _Connection(Protocol):
    def cursor(self) -> _Cursor: ...
    def execute(self, query: str, params: Sequence[Any] | None = ...) -> Any: ...


# --------------------------------------------------------------------------- #
# The read-only query set. Every query is a SELECT; ordering is deterministic. #
# The keys here are the keys :func:`build_spine_audit` reads from the raw map. #
# --------------------------------------------------------------------------- #

QUERIES: dict[str, str] = {
    "claim_total": "SELECT count(*) FROM claim",
    "claim_current_total": "SELECT count(*) FROM claim WHERE upper_inf(sys_period)",
    "entity_total": "SELECT count(*) FROM entity",
    "source_total": "SELECT count(*) FROM source_registry",
    "source_permitted": "SELECT count(*) FROM source_registry WHERE ingestion_permitted",
    "entity_by_type": (
        "SELECT entity_type, count(*) AS n FROM entity "
        "GROUP BY entity_type ORDER BY n DESC, entity_type ASC"
    ),
    "sensitivity_by_tier": (
        "SELECT sensitivity_tier, count(*) AS n FROM claim "
        "GROUP BY sensitivity_tier ORDER BY sensitivity_tier ASC"
    ),
    # Licence mix: claims joined to their rights record, grouped by SPDX expression.
    "licence_mix": (
        "SELECT r.spdx_expression, r.redistributable, r.derivative_permitted, count(*) AS n "
        "FROM claim c JOIN rights_record r ON c.rights_id = r.rights_id "
        "GROUP BY r.spdx_expression, r.redistributable, r.derivative_permitted "
        "ORDER BY n DESC, r.spdx_expression ASC"
    ),
    # The redistributability split (the compartment posture at claim granularity).
    "redistributable_split": (
        "SELECT r.redistributable, count(*) AS n "
        "FROM claim c JOIN rights_record r ON c.rights_id = r.rights_id "
        "GROUP BY r.redistributable ORDER BY n DESC, r.redistributable ASC"
    ),
    # UNDETERMINED claims attributed to the connector that ingested them (the P27.2 worklist).
    "undetermined_by_connector": (
        "SELECT ir.connector_name, count(*) AS n "
        "FROM claim c JOIN rights_record r ON c.rights_id = r.rights_id "
        "JOIN ingest_run ir ON c.ingest_run_id = ir.run_id "
        "WHERE r.redistributable = 'UNDETERMINED' "
        "GROUP BY ir.connector_name ORDER BY n DESC, ir.connector_name ASC"
    ),
    # Claims by connector (top of the whole spine, for context / denominators).
    "claims_by_connector": (
        "SELECT ir.connector_name, count(*) AS n "
        "FROM claim c JOIN ingest_run ir ON c.ingest_run_id = ir.run_id "
        "GROUP BY ir.connector_name ORDER BY n DESC, ir.connector_name ASC"
    ),
    # Geolocation — AGGREGATE ONLY (§0.7): a distinct-subject count, never a coordinate row.
    "geolocated_entities": (
        "SELECT count(DISTINCT subject_id) FROM claim "
        "WHERE predicate_id IN ('camera_latitude','camera_longitude')"
    ),
    "geo_claims": (
        "SELECT predicate_id, count(*) AS n FROM claim "
        "WHERE predicate_id IN ('camera_latitude','camera_longitude') "
        "GROUP BY predicate_id ORDER BY predicate_id ASC"
    ),
    "value_geom_populated": "SELECT count(*) FROM claim WHERE value_geom IS NOT NULL",
    # Jurisdiction spread — coarse label only (§19.4/§43.3), never a coordinate.
    "jurisdiction_spread": (
        "SELECT value_text AS jurisdiction, count(DISTINCT subject_id) AS n FROM claim "
        "WHERE predicate_id = 'camera_jurisdiction' AND value_text IS NOT NULL "
        "GROUP BY value_text ORDER BY n DESC, value_text ASC"
    ),
    # Freshness (§32.4): observation-time coverage + span. observed_at is nullable (§16.2).
    "observed_at_coverage": (
        "SELECT count(*) FILTER (WHERE observed_at IS NOT NULL) AS observed, "
        "min(observed_at) AS earliest, max(observed_at) AS latest FROM claim"
    ),
}


@dataclass(frozen=True)
class Fraction:
    """A count reported with its named denominator — never a bare total (§32/SIG-METRIC-008)."""

    numerator: int
    denominator: int
    label: str

    @property
    def pct(self) -> float:
        if self.denominator == 0:
            return 0.0
        return round(100.0 * self.numerator / self.denominator, 2)

    def render(self) -> str:
        return f"{self.numerator:,} of {self.denominator:,} {self.label} ({self.pct}%)"

    def to_json(self) -> dict[str, Any]:
        return {
            "numerator": self.numerator,
            "denominator": self.denominator,
            "label": self.label,
            "pct": self.pct,
        }


@dataclass(frozen=True)
class LicenceRow:
    spdx: str
    redistributable: str
    derivative_permitted: str
    claims: int


@dataclass(frozen=True)
class NamedCount:
    name: str
    count: int


@dataclass(frozen=True)
class ModelingTableRow:
    table: str
    rows: int

    @property
    def empty(self) -> bool:
        return self.rows == 0


@dataclass(frozen=True)
class SpineAudit:
    """A deterministic, read-only public-surface audit — a point-in-time snapshot of the spine."""

    # Snapshot metadata (honesty: an as-of snapshot, never a settled launch total).
    as_of: str
    generated_at: str
    spine_label: str
    note: str
    schema_version: str

    # Totals (each rendered with a denominator where one is meaningful).
    total_claims: int
    total_current_claims: int
    total_entities: int
    total_sources: int
    permitted_sources: int

    entity_by_type: list[NamedCount]
    sensitivity_by_tier: list[NamedCount]

    licence_mix: list[LicenceRow]
    redistributable_split: list[NamedCount]
    undetermined_by_connector: list[NamedCount]
    claims_by_connector: list[NamedCount]

    geolocated_entities: int
    geo_claims: list[NamedCount]
    value_geom_populated: int
    jurisdiction_spread: list[NamedCount]

    observed_claims: int
    earliest_observed: str | None
    latest_observed: str | None

    modeling_tables: list[ModelingTableRow]

    # Derived, denominator-bearing headline figures.
    publishable: Fraction = field(init=False)
    undetermined: Fraction = field(init=False)
    geolocated: Fraction = field(init=False)

    def __post_init__(self) -> None:
        publishable_claims = sum(
            row.claims for row in self.licence_mix if row.redistributable == "yes"
        )
        undetermined_claims = sum(
            row.claims for row in self.licence_mix if row.redistributable == "UNDETERMINED"
        )
        object.__setattr__(
            self,
            "publishable",
            Fraction(publishable_claims, self.total_claims, "claims (redistributable=yes)"),
        )
        object.__setattr__(
            self,
            "undetermined",
            Fraction(undetermined_claims, self.total_claims, "claims (rights UNDETERMINED)"),
        )
        object.__setattr__(
            self,
            "geolocated",
            Fraction(self.geolocated_entities, self.total_entities, "entities"),
        )

    # ------------------------------------------------------------------ #
    # Serialisation                                                       #
    # ------------------------------------------------------------------ #
    def to_json(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "as_of": self.as_of,
            "generated_at": self.generated_at,
            "spine_label": self.spine_label,
            "note": self.note,
            "totals": {
                "claims": self.total_claims,
                "current_claims": self.total_current_claims,
                "entities": self.total_entities,
                "sources": self.total_sources,
                "permitted_sources": self.permitted_sources,
            },
            "publishable": self.publishable.to_json(),
            "undetermined": self.undetermined.to_json(),
            "geolocated": self.geolocated.to_json(),
            "entity_by_type": [{"name": n.name, "count": n.count} for n in self.entity_by_type],
            "sensitivity_by_tier": [
                {"name": n.name, "count": n.count} for n in self.sensitivity_by_tier
            ],
            "licence_mix": [
                {
                    "spdx": r.spdx,
                    "redistributable": r.redistributable,
                    "derivative_permitted": r.derivative_permitted,
                    "claims": r.claims,
                }
                for r in self.licence_mix
            ],
            "redistributable_split": [
                {"name": n.name, "count": n.count} for n in self.redistributable_split
            ],
            "undetermined_by_connector": [
                {"name": n.name, "count": n.count} for n in self.undetermined_by_connector
            ],
            "claims_by_connector": [
                {"name": n.name, "count": n.count} for n in self.claims_by_connector
            ],
            "geolocation": {
                "geolocated_entities": self.geolocated_entities,
                "value_geom_populated": self.value_geom_populated,
                "geo_claims": [{"name": n.name, "count": n.count} for n in self.geo_claims],
                "jurisdiction_spread": [
                    {"name": n.name, "count": n.count} for n in self.jurisdiction_spread
                ],
            },
            "freshness": {
                "observed_claims": self.observed_claims,
                "earliest_observed": self.earliest_observed,
                "latest_observed": self.latest_observed,
            },
            "modeling_tables": [{"table": m.table, "rows": m.rows} for m in self.modeling_tables],
        }

    def to_json_str(self) -> str:
        return json.dumps(self.to_json(), indent=2, sort_keys=True) + "\n"

    def to_markdown(self) -> str:
        lines: list[str] = []
        w = lines.append
        w("# Public-surface data & rights audit — as-of snapshot (P27.1, LAUNCH.1)")
        w("")
        w("> **PROVISIONAL pre/mid-OSM snapshot.** These are as-of numbers, **not** a settled")
        w("> launch total. A hosted OSM land (`camreg_osm_surveillance`, ~1.37M claims via the")
        w("> P26.18 chunked-commit path) may be in flight while this ran, growing the spine")
        w("> toward ~2.43M claims. **A re-audit (re-run of `sig-exports audit`) after the OSM")
        w("> land completes is REQUIRED before any export/launch is frozen** (D-P27.1-1).")
        w("")
        w(f"- **as_of:** `{self.as_of}` · **generated_at (UTC):** `{self.generated_at}`")
        w(f"- **spine:** `{self.spine_label}`")
        w(f"- **note:** {self.note or '(none)'}")
        w(f"- **schema:** `{self.schema_version}`")
        w("")
        w("## Headline (denominator-bearing — never a bare total, §32/SIG-METRIC-008)")
        w("")
        w("| metric | value |")
        w("|---|---|")
        w(f"| total claims | {self.total_claims:,} ({self.total_current_claims:,} current) |")
        w(f"| total entities | {self.total_entities:,} |")
        w(f"| sources | {self.total_sources:,} ({self.permitted_sources:,} ingestion_permitted) |")
        w(f"| publishable | {self.publishable.render()} |")
        w(f"| UNDETERMINED rights | {self.undetermined.render()} |")
        w(f"| geolocated | {self.geolocated.render()} |")
        w("")
        w("## Licence mix (claims by `rights_record.spdx_expression`)")
        w("")
        w("| claims | spdx | redistributable | derivative |")
        w("|---:|---|---|---|")
        for r in self.licence_mix:
            w(f"| {r.claims:,} | {r.spdx} | {r.redistributable} | {r.derivative_permitted} |")
        w("")
        w("Redistributability split (compartment posture at claim granularity):")
        w("")
        w("| redistributable | claims |")
        w("|---|---:|")
        for n in self.redistributable_split:
            w(f"| {n.name} | {n.count:,} |")
        w("")
        w("## UNDETERMINED rights by connector (`ingest_run.connector_name`) — the P27.2 worklist")
        w("")
        w("| connector | UNDETERMINED claims |")
        w("|---|---:|")
        for n in self.undetermined_by_connector:
            w(f"| {n.name} | {n.count:,} |")
        w("")
        w("## Claims by connector (top of the spine — context/denominators)")
        w("")
        w("| connector | claims |")
        w("|---|---:|")
        for n in self.claims_by_connector:
            w(f"| {n.name} | {n.count:,} |")
        w("")
        w("## Geolocation (aggregate only — Part VIII §0.7 / §19.4 / §43.3)")
        w("")
        w(f"- distinct geolocated entities: **{self.geolocated.render()}**")
        w(
            f"- `value_geom` populated on **{self.value_geom_populated:,}** of "
            f"{self.total_claims:,} claims (the assembly gap P27.3 fills)"
        )
        w("- geolocation claims by predicate:")
        w("")
        w("| predicate | claims |")
        w("|---|---:|")
        for n in self.geo_claims:
            w(f"| {n.name} | {n.count:,} |")
        w("")
        w("Jurisdiction spread (`camera_jurisdiction`, coarse label; distinct subjects):")
        w("")
        w("| jurisdiction | distinct subjects |")
        w("|---|---:|")
        for n in self.jurisdiction_spread:
            w(f"| {n.name} | {n.count:,} |")
        w("")
        w("## Freshness (§32.4)")
        w("")
        obs = Fraction(self.observed_claims, self.total_claims, "claims carry `observed_at`")
        w(f"- {obs.render()}")
        w(f"- observed span: `{self.earliest_observed}` … `{self.latest_observed}`")
        w("")
        w("## Modeling-table population (the shaping gap P27.3 fills)")
        w("")
        w("| table | rows | state |")
        w("|---|---:|---|")
        for m in self.modeling_tables:
            w(f"| `{m.table}` | {m.rows:,} | {'EMPTY' if m.empty else 'populated'} |")
        w(
            f"| `claim.value_geom` | {self.value_geom_populated:,} | "
            f"{'EMPTY' if self.value_geom_populated == 0 else 'populated'} |"
        )
        w("")
        w("## Exact queries")
        w("")
        w("All read-only SELECTs, run inside a `READ ONLY` transaction (no INSERT/UPDATE/DELETE):")
        w("")
        w("```sql")
        for key in sorted(QUERIES):
            w(f"-- {key}")
            w(QUERIES[key] + ";")
        w("```")
        w("")
        w("## Caveats (observation-level, pre-resolution)")
        w("")
        w("- Counts are **raw claims, pre-resolution** — cross-source duplicate cameras")
        w("  (`dot_511` vs `osm` vs `atlas` vs `flock_portal`) are **not** deduped; the")
        w("  geolocated-entity count is **observation-level**, not a resolved device inventory.")
        w("- Rights → source attribution via `rights_id` alone fans out (many sources share one")
        w("  record); UNDETERMINED is attributed via `ingest_run.connector_name` (per-run).")
        w("- Coordinates are reported **only in aggregate** (a distinct-subject count + coarse")
        w("  jurisdiction spread); no per-person, per-plate, or raw-coordinate field is emitted.")
        w("- **PROVISIONAL** per the OSM land in flight — re-run this verb after it completes.")
        w("")
        return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Pure assembler + live executor                                              #
# --------------------------------------------------------------------------- #


def _scalar(raw: Mapping[str, Any], key: str) -> int:
    value = raw.get(key)
    if value is None:
        return 0
    return int(value)


def _named_counts(rows: Sequence[Sequence[Any]] | None) -> list[NamedCount]:
    out: list[NamedCount] = []
    for row in rows or []:
        name = "(null)" if row[0] is None else str(row[0])
        out.append(NamedCount(name=name, count=int(row[1])))
    # Deterministic: primary count desc, then name asc (mirrors the SQL ORDER BY).
    out.sort(key=lambda n: (-n.count, n.name))
    return out


def build_spine_audit(
    raw: Mapping[str, Any],
    *,
    as_of: str,
    generated_at: str,
    spine_label: str,
    note: str = "",
) -> SpineAudit:
    """Assemble a :class:`SpineAudit` from already-fetched query rows (pure — no database).

    ``raw`` maps each :data:`QUERIES` key to its fetched result: scalar queries to their scalar,
    grouped queries to a list of ``(key, count)`` rows. This is the unit-testable core.
    """
    licence_rows_raw = raw.get("licence_mix") or []
    licence_mix = [
        LicenceRow(
            spdx="(null)" if r[0] is None else str(r[0]),
            redistributable=str(r[1]),
            derivative_permitted=str(r[2]),
            claims=int(r[3]),
        )
        for r in licence_rows_raw
    ]
    licence_mix.sort(key=lambda r: (-r.claims, r.spdx))

    geo_obs = raw.get("observed_at_coverage")
    if geo_obs:
        observed_claims = int(geo_obs[0] or 0)
        earliest = None if geo_obs[1] is None else str(geo_obs[1])
        latest = None if geo_obs[2] is None else str(geo_obs[2])
    else:
        observed_claims, earliest, latest = 0, None, None

    modeling_raw = raw.get("modeling_tables") or {}
    modeling_tables = [
        ModelingTableRow(table=t, rows=int(modeling_raw.get(t, 0))) for t in MODELING_TABLES
    ]

    return SpineAudit(
        as_of=as_of,
        generated_at=generated_at,
        spine_label=spine_label,
        note=note,
        schema_version=AUDIT_SCHEMA_VERSION,
        total_claims=_scalar(raw, "claim_total"),
        total_current_claims=_scalar(raw, "claim_current_total"),
        total_entities=_scalar(raw, "entity_total"),
        total_sources=_scalar(raw, "source_total"),
        permitted_sources=_scalar(raw, "source_permitted"),
        entity_by_type=_named_counts(raw.get("entity_by_type")),
        sensitivity_by_tier=_named_counts(raw.get("sensitivity_by_tier")),
        licence_mix=licence_mix,
        redistributable_split=_named_counts(raw.get("redistributable_split")),
        undetermined_by_connector=_named_counts(raw.get("undetermined_by_connector")),
        claims_by_connector=_named_counts(raw.get("claims_by_connector")),
        geolocated_entities=_scalar(raw, "geolocated_entities"),
        geo_claims=_named_counts(raw.get("geo_claims")),
        value_geom_populated=_scalar(raw, "value_geom_populated"),
        jurisdiction_spread=_named_counts(raw.get("jurisdiction_spread")),
        observed_claims=observed_claims,
        earliest_observed=earliest,
        latest_observed=latest,
        modeling_tables=modeling_tables,
    )


def run_audit(
    conn: _Connection,
    *,
    as_of: str | None = None,
    note: str = "",
    spine_label: str = "(unlabelled spine)",
) -> SpineAudit:
    """Execute the read-only query set against ``conn`` and assemble the audit.

    The session is put in read-only mode first (``default_transaction_read_only = on``), so every
    subsequent transaction the verb opens *cannot* mutate the spine even if a query were
    mis-written. Works in both autocommit (the CLI) and an open transaction. Only ``SELECT``s run.
    """
    generated_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    as_of = as_of or generated_at

    cur = conn.cursor()
    # Fail-closed read-only for the whole session (append-only spine held trivially, §16).
    cur.execute("SET default_transaction_read_only = on")

    raw: dict[str, Any] = {}
    scalar_keys = {
        "claim_total",
        "claim_current_total",
        "entity_total",
        "source_total",
        "source_permitted",
        "geolocated_entities",
        "value_geom_populated",
    }
    for key, query in QUERIES.items():
        cur.execute(query)
        if key in scalar_keys:
            row = cur.fetchone()
            raw[key] = None if row is None else row[0]
        elif key == "observed_at_coverage":
            raw[key] = cur.fetchone()
        else:
            raw[key] = cur.fetchall()

    # Modeling-table population: one COUNT(*) per table (all read-only).
    modeling: dict[str, int] = {}
    for table in MODELING_TABLES:
        cur.execute(f"SELECT count(*) FROM {table}")  # table names are a fixed module constant
        row = cur.fetchone()
        modeling[table] = 0 if row is None else int(row[0])
    raw["modeling_tables"] = modeling

    return build_spine_audit(
        raw,
        as_of=as_of,
        generated_at=generated_at,
        spine_label=spine_label,
        note=note,
    )


def redact_dsn(dsn: str) -> str:
    """Return a DSN with any password removed — the audit records host/db only, never a secret."""
    try:
        # postgresql://user[:pw]@host:port/db?...
        if "://" not in dsn:
            return dsn
        scheme, _, rest = dsn.partition("://")
        authority, _, tail = rest.partition("/")
        if "@" in authority:
            userinfo, _, hostport = authority.rpartition("@")
            user = userinfo.split(":", 1)[0]
            authority = f"{user}@{hostport}" if user else hostport
        return f"{scheme}://{authority}/{tail}".split("?", 1)[0]
    except Exception:  # noqa: BLE001 - redaction must never raise
        return "(dsn redacted)"
