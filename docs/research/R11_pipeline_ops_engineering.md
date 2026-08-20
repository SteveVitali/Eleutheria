# R11 — Pipeline & Ops Engineering: ingestion, orchestration, quality, delivery, economics

**Workstream:** R11
**Researched:** 2026-08-20
**Researcher:** R11 (pipeline/ops)
**Outline sections covered:** §10 (all of 1A–1G), §14.3, §17 (Stages 0–6), §19 (19.1–19.12), §20 (Q23, Q24, Q25, Q26; partial Q27/Q28 where they touch the pipeline), §2 Layer B (portal disappearance as data), §2 ALPR Watch (inspectable/reversible normalization)
**Outline questions answered:** Q23, Q24, Q25, Q26 (fully); Q28 (pipeline-side scaffolding only — R7 owns the matching algorithms)
**Confidence in this file overall:** high

---

## 0. Executive summary of recommendations

| Decision | Recommendation | Confidence |
|---|---|---|
| Orchestrator | **Dagster OSS** (1.13.18, Apache-2.0), self-hosted, Postgres-backed | high |
| Escape hatch | Every asset must be runnable as `uv run sig-ingest <connector> --since ...` with **zero orchestrator** — Dagster is a scheduler over a CLI, never a dependency of the logic | high |
| Primary language | **Python 3.13** (3.14 tolerated, not required); TypeScript for `web/`; Rust/Go only via prebuilt binaries (pyosmium, tippecanoe, pmtiles) | high |
| Repo layout | **Monorepo**, uv workspace, one package per bounded context | high |
| Dep management | **uv** + `uv.lock` committed; `uv export --format pylock.toml` for PEP 751 archival copy | high |
| Data quality | **Pandera (schema/frame) + custom SQL invariant suite run by pytest + Pointblank for the public quality report**. NOT Soda Core (relicensed to Elastic License 2.0). NOT Great Expectations as the primary gate. | high |
| API | **FastAPI** for the dynamic read API; **static-first** bulk artifacts on R2 are the primary distribution channel | high |
| Object storage | **Cloudflare R2** ($0.015/GB-mo, **zero egress**) as primary; Backblaze B2 as mirror | high |
| Postgres | Neon (bootstrap) → Crunchy Bridge or self-hosted Hetzner/Postgres+PostGIS (steady state) | medium |
| Bootstrap cost | **≈ $32–48/month** all-in (see §6.3) | high |
| Degraded ($0) mode | GitHub Actions cron + R2 free tier + static exports + Datasette Lite. Fully specified in §6.6. | high |
| LLM in pipeline | Extraction **candidate generator only**, never a publisher. Every LLM-derived field carries a source span, a prompt hash, and a `review_status`. | high |

**The five things the outline does not say that this workstream insists on:**

1. **Re-extraction is a first-class write path, not a migration.** A better parser run over an old snapshot produces *new claims with new ids*, not edits. §2.6.
2. **A source disappearing is an ingestion success, not a failure.** `SourceUnavailableEvent` is a row, and it must survive the retry logic that would otherwise swallow it. §1.5.
3. **Structural diff on extracted JSON, never on HTML.** Boilerplate churn will otherwise generate thousands of false state transitions on Flock portals. §1.6.
4. **Geospatial jurisdiction sanity is the single highest-value automated check SIG can run** and it is not in the outline at all. §3.2 T-GEO-1.
5. **Egress, not storage or compute, is the cost that kills a public-interest bulk-data project.** R2's zero-egress is worth more than every other infrastructure decision combined. §6.2.

---

## PART A — CONNECTOR ARCHITECTURE

## 1. The uniform connector interface

### 1.1 Design premise

The outline's §19.1–19.3 ("provenance over convenience", "raw before normalized", "time before overwrite") are not properties you bolt onto a pipeline. They are properties of the *shape* of the pipeline. If any connector is allowed to go straight from `fetch()` to `load()`, the guarantee is gone project-wide, because the weakest connector defines what a claim means.

So: **one interface, eight stages, no exceptions, including for hand-uploaded FOIA PDFs.** The manual-upload path is a connector whose `discover()` reads a review queue instead of an HTTP endpoint.

The stage boundaries are chosen so that each boundary is a *persistence point* with a stable content address. That is what makes replay possible (§2.6) and what makes Q25 answerable (§1.4).

### 1.2 The stages, and the contract of each

| Stage | Input | Output | Idempotent? | Content-addressed? | Persisted? |
|---|---|---|---|---|---|
| `discover()` | connector config + watermark | `Iterable[DiscoveryRef]` | yes (pure over cursor) | no (refs are URLs/ids) | yes — `discovery_ref` table |
| `fetch()` | `DiscoveryRef` | `FetchResult` (bytes + headers + timing) or `Unavailable` | no (network) | n/a | no (transient) |
| `capture()` | `FetchResult` | `Snapshot` (immutable blob + `sha256`) | **yes** (keyed on sha256) | **yes** | yes — object store + `snapshot` table |
| `parse()` | `Snapshot` | `ParsedDoc` (structured, still source-shaped) | **yes** (pure fn of snapshot+parser version) | **yes** (sha256 of canonical JSON) | yes — `parsed_doc` table |
| `extract()` | `ParsedDoc` | `list[RawClaim]` (+ source spans) | **yes** (pure, except LLM path — see §7) | **yes** | yes — `raw_claim` table |
| `normalize()` | `RawClaim` | `NormalizedClaim` (vocab-mapped, units, dates) | **yes** (pure fn of raw + vocab version) | yes | yes — `normalized_claim` table |
| `link()` | `NormalizedClaim` | `LinkedClaim` or `ReviewTask` | **no** (depends on entity state at time T) | no | yes — `claim_link` + `review_task` |
| `load()` | `LinkedClaim` | claim rows in the bitemporal store | **yes** (keyed on claim identity, §2.7) | n/a | yes — `claim` |

Rules that fall out of this table and must be enforced in code review:

- **`capture()` is the only stage allowed to touch the network's output.** `parse()` and everything downstream take a `Snapshot` handle, never a URL. This is what makes replay (§2.6) possible at all: if a parser can re-fetch, replay is not reproducible.
- **`parse()` through `normalize()` must be pure functions.** Given the same snapshot bytes and the same code version, the same output. A parser that calls `datetime.now()` breaks reproducibility (§14.3) and will be caught by the determinism test in §3.6.
- **`link()` is the only impure downstream stage,** because entity resolution depends on the state of the entity registry at the moment it runs. That is why `link()` is where the human-review queue is injected, and why relinking is a separate replayable job (§2.6.3).
- **`load()` never updates in place.** It appends. §19.3.

### 1.3 Python protocol / ABC pseudocode

```python
# sig/connectors/base.py
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Protocol, runtime_checkable
import hashlib

# ---------------------------------------------------------------- value types

class IngestMode(StrEnum):
    BULK_FILE      = "bulk_file"        # Atlas CSV, OSM extracts
    REST_API       = "rest_api"         # MuckRock, DocumentCloud, USAspending, Overpass, Legistar
    REPLICATION    = "replication"      # OSM minutely/daily .osc.gz diffs
    HTML_SCRAPE    = "html_scrape"      # Flock portals, agency sites
    BROWSER_SCRAPE = "browser_scrape"   # SPA portals requiring JS
    MANUAL_UPLOAD  = "manual_upload"    # FOIA responses, contributor photos
    PARTNER_FEED   = "partner_feed"     # Eyes on Flock, HIBF (if collaboration lands)
    ALERT_FEED     = "alert_feed"       # RSS / email agenda + news alerts


class Incrementality(StrEnum):
    ETAG           = "etag"             # conditional GET, If-None-Match / If-Modified-Since
    CURSOR         = "cursor"           # opaque server cursor / next_page token
    WATERMARK      = "watermark"        # monotone field (updated_at, sequenceNumber)
    CONTENT_HASH   = "content_hash"     # no server hint; hash the normalized body
    FULL_DIFF      = "full_refresh_diff" # re-pull everything, diff against last snapshot
    PUSH           = "push"             # webhook / human submission; no polling


@dataclass(frozen=True, slots=True)
class DiscoveryRef:
    """A pointer to one fetchable unit. Stable across runs where possible."""
    connector_id: str
    external_id: str            # portal slug, OSM sequence no, MuckRock request id, file path
    url: str | None
    hint: dict[str, str] = field(default_factory=dict)   # etag, last_modified, cursor
    priority: int = 100         # lower = fetched sooner; used by the politeness scheduler

    @property
    def ref_key(self) -> str:
        return f"{self.connector_id}:{self.external_id}"


@dataclass(frozen=True, slots=True)
class FetchResult:
    ref: DiscoveryRef
    body: bytes
    media_type: str
    status: int
    headers: dict[str, str]
    fetched_at: datetime
    request_trace: dict          # final URL after redirects, TLS cert fingerprint, UA sent, elapsed_ms


class UnavailableReason(StrEnum):
    HTTP_404          = "http_404"
    HTTP_403          = "http_403"
    HTTP_410          = "http_410"
    DNS_FAILURE       = "dns_failure"
    TLS_FAILURE       = "tls_failure"
    TIMEOUT           = "timeout"
    ROBOTS_DISALLOW   = "robots_disallow"
    RATE_LIMITED_OUT  = "rate_limited_exhausted"
    CONTENT_GONE      = "content_gone"       # 200 but the resource says "not found"
    PARTNER_REVOKED   = "partner_revoked"


@dataclass(frozen=True, slots=True)
class Unavailable:
    """NOT an exception. A first-class observation. See §1.5."""
    ref: DiscoveryRef
    reason: UnavailableReason
    observed_at: datetime
    detail: str
    consecutive_count: int      # filled by the runner from prior state
    prior_success_at: datetime | None


@dataclass(frozen=True, slots=True)
class Snapshot:
    sha256: str                 # of the raw bytes, lowercase hex — THE content address
    size_bytes: int
    media_type: str
    storage_uri: str            # r2://sig-snapshots/sha256/<aa>/<bb>/<sha256>
    captured_at: datetime
    ref_key: str
    fetch_headers: dict[str, str]
    request_trace: dict

    @staticmethod
    def address(body: bytes) -> str:
        return hashlib.sha256(body).hexdigest()


@dataclass(frozen=True, slots=True)
class ParsedDoc:
    snapshot_sha256: str
    parser_id: str
    parser_version: str         # semver of the parser module, bumped on ANY behavior change
    canonical_json: dict        # source-shaped; NOT ontology-shaped
    canonical_sha256: str       # sha256 of json.dumps(canonical_json, sort_keys=True, separators=(",",":"))
    parse_warnings: list[str]


@dataclass(frozen=True, slots=True)
class SourceSpan:
    """Where in the snapshot this value came from. MANDATORY for every extracted field."""
    kind: str                   # "json_pointer" | "css_path" | "char_range" | "pdf_bbox" | "csv_cell"
    locator: str                # "/organizations/3/name" | "table.stats tr:nth-child(2) td" | "1204:1231"
    page: int | None = None
    excerpt: str | None = None  # verbatim source text, <= 500 chars, for the review UI


@dataclass(frozen=True, slots=True)
class RawClaim:
    """Source-shaped assertion. Values are VERBATIM. No vocabulary mapping yet. §19.2"""
    parsed_doc_sha: str
    predicate: str              # "camera_count" | "retention_days" | "shares_data_with" | ...
    subject_hint: dict          # raw identifying strings: {"agency_name": "Hagerstown MD PD", "slug": "..."}
    object_raw: str             # verbatim: "30 days", "1,247", "Yes"
    spans: Sequence[SourceSpan]
    observed_at: datetime       # when the source asserted it (portal "last updated"), NOT when we fetched
    extractor_id: str
    extractor_version: str
    extraction_method: str      # "deterministic" | "llm" | "human"
    llm_meta: dict | None = None  # see §7.3


@dataclass(frozen=True, slots=True)
class NormalizedClaim:
    raw_claim_id: str
    predicate: str
    object_value: object        # typed: int, Decimal, date, timedelta, enum member, geometry
    object_unit: str | None
    vocabulary_id: str | None   # ontology term IRI for coded values
    normalization_method: str   # "regex:duration_v3" | "lookup:reason_codes_v7" | "llm:classify_v2"
    normalization_version: str
    confidence: float | None    # NEVER model-generated. See §7.2.
    review_status: str          # "auto_accepted" | "pending" | "human_confirmed" | "human_corrected" | "rejected"


@dataclass(frozen=True, slots=True)
class LinkedClaim:
    normalized_claim_id: str
    subject_entity_id: str | None
    object_entity_id: str | None
    link_method: str            # "deterministic:ori" | "deterministic:osm_id" | "review:human"
    link_confidence: float | None
    review_task_id: str | None  # set when the link could not be made deterministically


@dataclass
class RunContext:
    run_id: str
    connector_version: str
    started_at: datetime
    watermark_in: dict          # opaque per-connector state read at run start
    watermark_out: dict         # written back on success ONLY
    dry_run: bool = False
    replay_of_run_id: str | None = None   # set for backfill/replay runs, §2.6


# ---------------------------------------------------------------- the interface

class Connector(ABC):
    """Every SIG source adapter implements exactly this. No exceptions."""

    connector_id: str
    ingest_mode: IngestMode
    incrementality: Incrementality
    source_license_id: str        # FK into the license registry; blocks export if incompatible
    politeness_host: str          # the host key for the shared rate limiter, §1.7
    version: str                  # semver; bump on ANY behavior change; recorded on every run

    # ---- stage 1
    @abstractmethod
    def discover(self, ctx: RunContext) -> Iterable[DiscoveryRef]:
        """Enumerate fetchable units. MUST be resumable: yield lazily, and never
        materialize the full set for a large source. MUST respect ctx.watermark_in.
        For MANUAL_UPLOAD this reads the pending-upload queue."""

    # ---- stage 2
    @abstractmethod
    def fetch(self, ref: DiscoveryRef, ctx: RunContext) -> FetchResult | Unavailable:
        """Perform exactly one network (or filesystem) read, THROUGH the shared
        politeness gateway. MUST return Unavailable rather than raise for any
        condition in UnavailableReason. May raise only on programmer error."""

    # ---- stage 3 (provided by the framework; connectors do not override)
    def capture(self, fetched: FetchResult, ctx: RunContext) -> Snapshot:
        """Content-address and store immutably. Idempotent on sha256: if the blob
        already exists, this is a no-op write plus a new observation row.
        NEVER overwritten. NEVER deleted by the pipeline (only by takedown, §6.5)."""
        raise NotImplementedError  # framework-provided

    # ---- stage 4
    @abstractmethod
    def parse(self, snap: Snapshot, blob: bytes) -> ParsedDoc:
        """Pure. Same bytes + same parser_version => same canonical_sha256.
        Forbidden: network I/O, clock reads, randomness, locale-dependent parsing."""

    # ---- stage 5
    @abstractmethod
    def extract(self, doc: ParsedDoc) -> Iterable[RawClaim]:
        """Emit verbatim assertions with source spans. MUST NOT map vocabularies,
        convert units, or resolve entities. Every RawClaim MUST carry >=1 SourceSpan."""

    # ---- stage 6 (usually the shared default implementation)
    def normalize(self, raw: RawClaim) -> NormalizedClaim:
        """Vocabulary + unit + date normalization. Reversible: raw is retained,
        method+version recorded. §2 ALPR Watch."""
        raise NotImplementedError  # framework-provided default

    # ---- stage 7 (framework-provided; connectors supply identity hints only)
    def link(self, norm: NormalizedClaim) -> LinkedClaim:
        """Deterministic first. On ambiguity, emit a ReviewTask and return a
        LinkedClaim with subject_entity_id=None. NEVER guess-and-write. Q28."""
        raise NotImplementedError  # framework-provided

    # ---- stage 8 (framework-provided)
    def load(self, linked: LinkedClaim, ctx: RunContext) -> None:
        """Append-only insert into the bitemporal claim store. Idempotent on
        claim identity (§2.7)."""
        raise NotImplementedError  # framework-provided

    # ---- optional hooks
    def on_unavailable(self, u: Unavailable, ctx: RunContext) -> None:
        """Default: record a SourceUnavailableEvent. Override to add semantics,
        e.g. FlockPortalConnector escalates 3 consecutive 404s to a
        PortalDisappearedEvent, which is DATA (§2 Layer B), not an error."""

    def health(self) -> "ConnectorHealth":
        """Cheap liveness probe used by the freshness dashboard (§6.4)."""


@runtime_checkable
class SupportsBackfill(Protocol):
    """Connectors that can be pointed at an arbitrary historical window."""
    def discover_range(self, start: datetime, end: datetime) -> Iterable[DiscoveryRef]: ...
```

### 1.4 Content addressing — the answer to Q25

**Q25: "How should source snapshots be content-addressed?"**

Answer, concretely:

- **Address = lowercase hex `sha256` of the exact response body bytes**, before any decompression, transcoding, or normalization. Not of the decoded text. Not of a normalized form. The raw octets.
- **Storage layout:** `r2://sig-snapshots/sha256/<first2>/<next2>/<full-hex>` with no extension. Media type lives in object metadata and in the `snapshot` row. Two-level fanout keeps any single prefix listing tractable.
- **Deduplication is automatic and desirable.** A Flock portal that is byte-identical today and tomorrow produces one blob and two `snapshot_observation` rows. This is the correct model: *the snapshot is the content; the observation is the event of seeing it.* Splitting these two is what makes the storage cost of daily portal snapshotting negligible (§6.2).
- **Second address for the parsed layer:** `canonical_sha256` = sha256 of `json.dumps(canonical_json, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")`. This is what change detection compares (§1.6), and what proves a re-parse was a no-op.
- **Do not use sha1 or md5** — collision resistance matters here because the hash is the evidence identifier a downstream researcher will cite.
- **Do not use a "logical" content address** (e.g. hash of the extracted fields) as the snapshot address. That destroys the ability to prove what the source actually said.

Two addresses, two purposes: `sha256` proves *what the source served*; `canonical_sha256` proves *what our parser understood*. §2 Layer B's four-line distinction ("what portal says now / what portal said on date T / what our parser extracted on date T / what later evidence says") maps exactly onto `snapshot_observation` / `snapshot` / `parsed_doc` / `claim`.

### 1.5 Source disappearance as a first-class event

The outline says (§2 Layer B) "a portal may disappear" and lists it as a property of the source. R11's position: **that sentence is a schema requirement, and almost every pipeline gets it wrong** because the natural implementation puts 404 in the exception path, where retry logic, dead-letter queues, and alert fatigue conspire to make it invisible.

Design:

```python
# emitted by the runner, not by the connector
@dataclass(frozen=True, slots=True)
class SourceUnavailableEvent:
    event_id: str
    ref_key: str
    connector_id: str
    reason: UnavailableReason
    observed_at: datetime
    run_id: str
    consecutive_count: int
    prior_success_at: datetime | None
    prior_snapshot_sha256: str | None   # what we last successfully saw
    escalated_to: str | None            # "portal_disappeared" once threshold met
```

Rules:

1. `fetch()` **returns** `Unavailable`; it does not raise. The type system enforces that the caller handles it (`FetchResult | Unavailable` forces a match).
2. Every `Unavailable` writes a `SourceUnavailableEvent`. Always. Even the first transient timeout. Storage cost is trivial; the time series is the value.
3. **Escalation is a connector-specific policy**, evaluated on `consecutive_count`:
   - Flock portal: 3 consecutive daily 404/410 → `PortalDisappearedEvent`, which becomes a **negative claim** (§9.4 of the outline) with `valid_from = first 404 observation`, and materially changes the org's dossier ("this agency had a public transparency portal from 2025-03 to 2026-04; it is gone").
   - MuckRock: 404 on a request id → likely embargoed or deleted; escalate at 2, and record it as an access-change event, not a disappearance of the underlying record.
   - OSM replication: a gap in sequence numbers is **never** an unavailability — it is a fatal correctness error and must halt the connector (see §1.8, and the explicit upstream warning at planet.openstreetmap.org).
4. **A run in which every fetch returned `Unavailable` is a SUCCESSFUL run** that produced N observations. It must not be marked failed, because marking it failed will cause an operator to "fix" it by disabling the connector, destroying the time series. Instead the *freshness dashboard* (§6.4) shows the source as red while the *run* shows as green.
5. The negative claim generated from disappearance is `evidence`-backed like anything else: its evidence is the `SourceUnavailableEvent` chain plus the last successful snapshot.

**This is the highest-value cheap thing in the whole ingestion layer.** "Which agencies quietly took their transparency portal down, and when" is a headline that no existing project in the outline's ecosystem map can currently produce, and it falls out of correct error modelling.

### 1.6 Change detection on scraped pages

**Recommendation: structural diff on the extracted canonical JSON. Never diff HTML. Never diff rendered text.**

Rationale, in order of how badly each alternative fails on a Flock transparency portal:

| Approach | Failure mode |
|---|---|
| Raw HTML byte diff | Every build hash, CSRF token, ad slot, session id, and `<!-- rendered in 42ms -->` comment produces a "change". Signal-to-noise ~0. |
| Rendered-text diff | Better, but relative dates ("updated 2 hours ago"), rotating footers, and cookie banners still churn. Also loses structure: a swapped table column reads as a huge diff. |
| Normalized-content hash of the whole page | Fixes churn only if the normalizer is perfect; one missed dynamic element and you are back to case 1. Also all-or-nothing: you know *that* it changed, not *what*. |
| **Structural diff on extracted JSON** | **Recommended.** Churn is impossible by construction because boilerplate never enters the extracted representation. Produces per-field deltas, which is exactly what the temporal model wants. |

Concrete mechanism:

```python
def detect_changes(prev: ParsedDoc | None, curr: ParsedDoc) -> list[FieldChange]:
    """Emit one FieldChange per differing leaf in the canonical JSON."""
    if prev is None:
        return [FieldChange(path=p, before=None, after=v, kind="first_seen")
                for p, v in leaves(curr.canonical_json)]
    if prev.canonical_sha256 == curr.canonical_sha256:
        return []                      # fast path: provably no semantic change
    return [
        FieldChange(path=p, before=prev_v, after=curr_v,
                    kind=classify(p, prev_v, curr_v))
        for p, prev_v, curr_v in diff_leaves(prev.canonical_json, curr.canonical_json)
    ]
```

`FieldChange.kind` is drawn from a fixed vocabulary so that downstream automation can be selective:

- `first_seen`, `value_changed`, `value_appeared`, `value_disappeared`
- `collection_member_added` / `collection_member_removed` (sharing-partner lists — this is where the network-topology signal lives, §6.6 of the outline)
- `structure_changed` — **a shape change, not a value change. This is the canary.** A `structure_changed` on a source that has been stable is the strongest available signal of an upstream redesign, and it fires the parser-drift alert (§3.5) *before* the parser starts silently producing garbage.

**Per-field change events are the write unit**, not whole-document diffs. Each `FieldChange` becomes at most one `RawClaim` with `observed_at` from the source's own "last updated" field where one exists, falling back to `captured_at`. §9.2 of the outline ("never collapse observation time and validity time") is honoured because these are two distinct columns populated from two distinct places.

**Count-plausibility guard rides on this path** (§3.2 T-PLAUS-1): a `value_changed` on `camera_count` from 300 → 0 does not silently write. It writes the claim (because §19.3 says append, and because a portal genuinely reporting 0 is data) *and* raises a review task *and* holds the derived "current camera count" projection at its prior value until reviewed. Three separate behaviors, deliberately.

### 1.7 The politeness layer

R8 writes the policy; R11 builds the enforcement. The enforcement mechanism must make impolite crawling *impossible*, not merely discouraged — a single misconfigured connector can get SIG's whole IP range blocked and burn ecosystem goodwill the project depends on (§17 Stage 0).

**Architecture: a single in-process `PolitenessGateway` that every `fetch()` must pass through. Connectors have no direct HTTP client.**

```python
class PolitenessGateway:
    """The ONLY egress path. Connectors receive this; they never import httpx."""

    def __init__(self, budgets: dict[str, HostBudget], ua: str, contact: str): ...

    async def get(self, ref: DiscoveryRef, *, connector_id: str,
                  conditional: bool = True) -> FetchResult | Unavailable:
        host = urlsplit(ref.url).netloc
        # 1. robots.txt — cached per host, refetched every 24h, Protego-parsed
        robots = await self._robots(host)
        if not robots.can_fetch(self.ua, ref.url):
            return Unavailable(ref, UnavailableReason.ROBOTS_DISALLOW, now(), "robots.txt", ...)
        # 2. crawl-delay: max(robots crawl_delay, host_budget.min_interval)
        delay = max(robots.crawl_delay(self.ua) or 0.0, self.budgets[host].min_interval)
        # 3. per-host token bucket + single-flight lock => strictly serial per host
        async with self._host_lock(host):
            await self._bucket(host).acquire(delay)
            # 4. conditional request from the stored etag/last-modified
            headers = {"User-Agent": self.ua, "From": self.contact}
            if conditional:
                headers |= self._conditional_headers(ref)
            resp = await self._client.get(ref.url, headers=headers)
        # 5. 429/503 => exponential backoff with jitter, honour Retry-After, and
        #    HALVE the host budget for the rest of the run (adaptive politeness)
        ...
```

Non-negotiable properties:

1. **Per-host serialization.** Never more than one in-flight request per host, ever, regardless of how many connectors or workers are running. Implemented as a distributed lock keyed on host when running >1 worker.
2. **Per-host budget** (`requests/hour`, `bytes/hour`, `min_interval`) declared in `ops/politeness.toml`, version-controlled, reviewed by R8. Default for an undeclared host: 1 request / 10 s, 500 requests/day. A connector cannot raise its own budget in code.
3. **robots.txt honoured by default**, parsed with **Protego 0.6.2 (BSD-3-Clause, requires Python >=3.10)** — verified F11.14 — which implements Google's modern spec including wildcards and length-based precedence, unlike stdlib `urllib.robotparser`. Crawl-delay is read from robots and used as a *floor*, never as a ceiling.
   - Overrides require an explicit, per-host, human-signed entry with a written justification field. The audit trail is the point.
4. **Documented UA with contact**, e.g.
   `SIG-Bot/0.4 (+https://<project>/bot; contact@<project>)`
   plus a `From:` header. MuckRock explicitly requires an identifiable UA with valid contact information and blocks generic `curl`/`python-requests` UAs and browser-spoofing UAs (verified F11.12) — so this is not merely etiquette, it is an access requirement on a Tier-A source.
5. **Adaptive de-escalation.** Any 429/503 halves that host's budget for the remainder of the run and writes a `PolitenessIncident` row. Three incidents in 24h auto-pauses the connector and pages a human.
6. **Global cap on browser-scrape concurrency** (§6.2 — headless browsers are the single most expensive compute line item).
7. **Dry-run mode** in which the gateway logs the request it *would* make and returns a stored snapshot. Every connector must pass its golden-fixture test suite in dry-run with zero network calls (enforced by a pytest fixture that monkeypatches the socket module to raise).

---

## 2. Per-source-class ingestion matrix (Q23, Q24)

### 2.1 The matrix

**Q23 ("which connectors can be incremental?") and Q24 ("which sources require scraping?") answered in one table.**

| # | Class | SIG sources (§10, §21) | Incrementality | Can be truly incremental? | Failure/retry | Backoff | Disappearance semantics |
|---|---|---|---|---|---|---|---|
| 1 | **Bulk file download** | EFF Atlas CSV; Geofabrik/planet OSM extracts; EFF Data Driven CSVs; ALPR Watch published tables | `ETAG` then `FULL_DIFF` | **Partially.** Conditional GET avoids the *download*; you still must diff the whole file to find changes. | 3 retries; partial download = discard, never resume into the hash | exp, base 30 s, cap 30 min | Missing file for 3 consecutive runs → `SourceUnavailableEvent`; do NOT delete prior claims |
| 2 | **REST API (cursored)** | MuckRock `api_v2`; DocumentCloud; USAspending v2 | `CURSOR` + `WATERMARK` | **Yes.** Best-case class. | per-page retry, resume from last good cursor | exp + jitter, honour `Retry-After` | 404 on a known id = access-change event, not deletion |
| 3 | **REST API (query, uncursored)** | Overpass API | `FULL_DIFF` per bbox tile | **No** — Overpass is a query engine, not a feed. Tile the world, diff per tile. | per-tile; a failed tile does not fail the run | exp; HTTP 429 → long sleep; 504 → reduce query cost | tile failure ≠ data absence; never write negatives from a failed tile |
| 4 | **Replication diff** | OSM minutely/hourly/daily `.osc.gz` | `WATERMARK` (sequenceNumber) | **Yes — the gold standard.** | **Gap = halt.** Never skip a sequence number. | linear retry; alert after 3 | a missing sequence file is a fatal error, not unavailability |
| 5 | **HTML scrape** | Flock transparency portals; agency websites; policy pages | `ETAG` → `CONTENT_HASH` → structural diff | **Effectively yes** via conditional GET + canonical-JSON hash, though the server usually gives no hint. | 2 retries then `Unavailable` | exp, base 60 s, cap 6 h; per-host budget dominates | **3 consecutive 404/410 → `PortalDisappearedEvent` → negative claim.** §1.5 |
| 6 | **Headless-browser scrape** | SPA portals; JS-gated dashboards | `CONTENT_HASH` on extracted JSON only | Yes, but expensive. Capture **both** the DOM-after-settle HTML *and* the intercepted XHR JSON. | 1 retry (expensive); then `Unavailable` | exp, base 5 min | same as class 5 |
| 7 | **Manual / human-in-the-loop** | FOIA response bundles; contributor photos; hand-transcribed contracts | `PUSH` | n/a — event-driven | upload is atomic; parse failures queue for human | n/a | n/a — but *staleness* of a manually maintained source is tracked |
| 8 | **Partner feed** | Eyes on Flock; HIBF; ALPR Accountability Atlas (if collaboration lands, §17 Stage 0) | `WATERMARK` or `ETAG`, per agreement | Yes if the partner exposes one | never retry aggressively against a partner; 1 retry | exp, base 5 min | `PARTNER_REVOKED` is a distinct reason and pages a human immediately |
| 9 | **RSS / email alert** | Legistar & agenda systems; Google Alerts–style news; council calendars | `WATERMARK` on item guid/pubDate | Yes | 3 retries | exp, base 5 min | feed 404 → `SourceUnavailableEvent`; do not infer "no meetings" |

### 2.2 Per-class notes with verified evidence

Findings F11.1–F11.16 below carry the evidence for the matrix rows.

### F11.1 — OSM replication diffs give SIG a true incremental feed with sequence-number watermarks

**Claim:** OpenStreetMap publishes minutely, hourly, and daily `.osc.gz` change files under `planet.openstreetmap.org/replication/{minute,hour,day}/`, each addressed by a nine-digit sequence number split `AAA/BBB/CCC.osc.gz` and accompanied by a `state.txt` carrying `sequenceNumber` and `timestamp`; the upstream docs explicitly warn against incrementing sequence numbers blindly.
**Status:** VERIFIED
**Evidence:** https://wiki.openstreetmap.org/wiki/Planet.osm/diffs — documents the three feeds and their schedules (minutely; hourly at :02; daily at 00:05 UTC), the `AAA/BBB/CCC` layout where N = AAA×1,000,000 + BBB×1,000 + CCC, the `state.txt` contents, and the warning: "Under no circumstances should you attempt to just fetch diffs by incrementing the sequence number as incomplete diffs may be present." Also documents Geofabrik regional daily diffs and download.openstreetmap.fr minutely regional diffs as lower-load alternatives.
**Retrieved:** 2026-08-20
**Implication for the spec:** The OSM connector is `IngestMode.REPLICATION` with `Incrementality.WATERMARK` keyed on `sequenceNumber`. It must (a) always read the feed's `state.txt` rather than incrementing, (b) treat a gap as a **halt-and-alert**, not a retry, and (c) default to **Geofabrik/OSM-FR regional daily diffs** rather than the global minutely feed — SIG needs surveillance-tagged nodes, not sub-minute latency, and regional diffs are the explicitly-blessed way to reduce upstream load.
**Outline delta:** EXTENDS §10 Phase 1B and answers Q19 partially — SIG does *not* need to replicate OSM history; it needs the daily diff stream filtered to `man_made=surveillance` and friends, plus the OSM element `version` field the outline already asks to retain.

### F11.2 — pyosmium is the right OSM processing library and is permissively licensed

**Claim:** `osmium` (PyOsmium) 4.3.1, BSD-2-Clause, requires Python >= 3.8, provides Python bindings to libosmium and bundles matching libosmium/protozero/pybind11.
**Status:** VERIFIED
**Evidence:** https://pypi.org/pypi/osmium/json — version 4.3.1, license BSD-2-Clause, `requires_python` >=3.8, "Python bindings for libosmium, the data processing library for OSM data"; system deps expat/libz/libbz2.
**Retrieved:** 2026-08-20
**Implication for the spec:** Use `osmium` for both PBF extract reading and `.osc.gz` diff application. This is the one place where a C++ (not Rust/Go) dependency is unavoidable and justified — writing a PBF parser in pure Python is a non-starter at planet scale. The BSD-2 license imposes no obligations on SIG's output.
**Outline delta:** CONFIRMS §10 Phase 1B is technically cheap.

### F11.3 — Overpass API cannot be a bulk source and has an explicit fair-use ceiling

**Claim:** The public Overpass instances target ~30,000 daily users with a fair-use guideline of roughly 10,000 requests/day and under 1 GB/day download per user; scraping the world by stitching bounding boxes and relying on public instances for a non-mapper app are both explicitly discouraged; rate limiting is per-IP with request slots, 15 s queueing, HTTP 429 on limit and HTTP 504 on resource denial; defaults are 180 s timeout and 512 MiB memory with a 12 GiB cap.
**Status:** VERIFIED
**Evidence:** https://dev.overpass-api.de/overpass-doc/en/preface/commons.html — "a maximum of about 10000 requests per day and keep their download volume below about 1 GB per day"; prohibited patterns include "Stitching bounding boxes to scrape the full data of the complete world" and "Setting up an app for more than just OSM mappers and relying on the public instances"; "only running your own instance sustainably serves your mission."
**Retrieved:** 2026-08-20
**Implication for the spec:** Overpass is a **lead-generation / spot-check** connector only, hard-capped in `ops/politeness.toml` at ≤2,000 requests/day and ≤200 MB/day, with a documented `From:` contact. Bulk physical-asset ingestion goes through **PBF extracts + replication diffs (F11.1/F11.2)**, not Overpass. If SIG later needs Overpass at volume, the answer is self-hosting an instance, not raising the budget.
**Outline delta:** CORRECTS §10 Phase 1B / §21 by implication — the outline lists OSM/Overpass without distinguishing them; treating Overpass as the OSM connector would violate the commons policy of a project SIG explicitly wants to be a good citizen of (§19.5 "federation before duplication").

### F11.4 — MuckRock's API is cursored, authenticated, rate-limited, and requires an identifying UA

**Claim:** MuckRock's current API is `https://www.muckrock.com/api_v2/`; most endpoints now require authentication via 5-minute access tokens from `https://accounts.muckrock.com/api/token/` sent as bearer tokens; most endpoints allow 15 requests/minute with bursts to 100; users and organizations endpoints allow 5/minute with no burst; responses default to 50 items/page and to HTML unless `format=json` or an Accept header is used; requests require an identifiable user agent with valid contact information, and generic (`curl`, `python-requests`) or browser-spoofing UAs are subject to blocking.
**Status:** VERIFIED
**Evidence:** https://www.muckrock.com/api/ — documents base URL `api_v2`, token endpoint and 5-minute token lifetime, the 15/min + burst-100 limit and the stricter 5/min users/organizations limit, the 50-item default page size, the JSON opt-in, the UA requirement and blocking policy, endpoints for requests/communications/files/agencies/jurisdictions/users/organizations/projects, and recommends the `python-muckrock` library.
**Retrieved:** 2026-08-20
**Implication for the spec:** (a) The MuckRock connector is `REST_API` + `CURSOR`, genuinely incremental — Q23's best case. (b) **Token refresh must be built into the gateway**, not the connector: a 5-minute token means a long backfill will expire mid-run, so the gateway holds the token and refreshes at T-60s. (c) The politeness budget for `muckrock.com` is set at **12 req/min sustained** (below the 15 limit, no burst) with the `users`/`organizations` paths pinned to **4 req/min** as a separate sub-budget — the gateway therefore needs *path-scoped* budgets, not just host-scoped. (d) The UA requirement is an access requirement, confirming §1.7 rule 4.
**Outline delta:** EXTENDS §10 Phase 1F and answers Q7's API-constraints half. The path-scoped budget requirement is a design detail the outline could not have anticipated and that a host-only rate limiter would get wrong.

### F11.5 — USAspending exposes a public v2 API; v1 is deprecated

**Claim:** USAspending offers a public API at `https://api.usaspending.gov` with a documentation index at `/docs/` and an endpoints list at `/docs/endpoints`; V1 endpoints are deprecated and V2 is current; the codebase is open source, maintained by the U.S. Department of the Treasury.
**Status:** PARTIALLY VERIFIED
**Evidence:** https://api.usaspending.gov/ — confirms the base URL, the public-access framing, the V1-deprecated/V2-current status, and the docs index. **The root page does not state authentication requirements, rate limits, or bulk-download endpoint details** — those were not visible in the fetched content.
**Retrieved:** 2026-08-20
**Implication for the spec:** Build the USAspending connector against **v2 only**. Because rate limits are undocumented at the entry point, the connector must adopt the conservative default budget (§1.7 rule 2: 1 req/10 s) until R8/R4 confirms a published limit, and must implement adaptive de-escalation on any 429. Bulk download endpoints exist in the v2 docs but were not confirmed here — the spec should hedge by making the connector work in cursored mode and treat bulk download as an optimization.
**Outline delta:** EXTENDS §10 Phase 1F. Flag: the outline names "procurement systems" generically; USAspending covers *federal* awards, which is the minority of ALPR procurement (mostly municipal). Legistar/agenda systems and state portals matter more for SIG's actual subject matter.

### F11.6 — The Legistar Web API exists but its surface is not publicly documented at the entry point

**Claim:** Granicus operates a Legistar Web API that "exposes Legistar data to the web directly over HTTPS" at `webapi.legistar.com` (version 26.4.2.0 at time of retrieval); base URL patterns, authentication, endpoint list, and rate limits are not stated on the landing page and require the `/Help` and `/Home/Examples` pages.
**Status:** PARTIALLY VERIFIED — landing page reached, technical surface INACCESSIBLE from it
**Evidence:** https://webapi.legistar.com/ — confirms existence and the one-line description; explicitly lacks base URL pattern, auth, endpoints, and rate limits. Follow-up would require `webapi.legistar.com/Help`.
**Retrieved:** 2026-08-20
**Implication for the spec:** Legistar is a **Stage 4+ connector**, not Stage 1. Build it as `REST_API` + `WATERMARK` per client (`webapi.legistar.com/v1/<client>/...` is the widely-observed shape but is **not verified here** — the spec must not hard-code it without confirming against `/Help`). Because Legistar is multi-tenant with one path segment per municipality, the politeness budget must be **per-tenant-path**, reinforcing F11.4's path-scoped-budget requirement. Until verified, the agenda-system connector should be built against **RSS/iCal feeds** (class 9), which most Legistar deployments expose and which need no auth.
**Outline delta:** EXTENDS §10 Phase 1F ("city agenda systems"). CORRECTS an implicit assumption that agenda systems are a single connector — they are a *family* (Legistar, CivicClerk, PrimeGov, Granicus, Municode, plus hand-rolled), which argues for one generic RSS/iCal connector plus per-vendor parsers behind the same interface.

### F11.7 — EFF Atlas of Surveillance publishes a single ~8.6 MB CSV at a stable URL with a weak validator

**Claim:** `https://atlasofsurveillance.org/download.csv` returns HTTP 200, `content-type: text/csv`, `content-length: 8,579,798` bytes, a weak `ETag` (`W/"ee42384d..."`), and a `content-disposition` filename that **embeds the current date** (`Atlas of Surveillance-20260820.csv`); the header row is `AOSNUMBER, NEWAOSNUMBER (ORI9), City, County, State, Agency, Type of LEA, Summary, Type of Juris, Technology, TECH ABV, Vendor, Link 1..Link 3 (+Snapshot/Source/Type/Date each), Other Links`. There is a separate Data Library page at `/data-library` linking ~20 external datasets including EFF's ALPR dataset, Data Driven 2, campus police, and BWC grant data.
**Status:** VERIFIED
**Evidence:** `curl -sIL https://atlasofsurveillance.org/download.csv` → 301 then 200 with the headers above; `curl -sL ... | head -c 400` → the header row and first record `"AOS000001","VA0850300BWC",...`. `curl -sL https://atlasofsurveillance.org/data-library` → `<title>Data Library | Atlas of Surveillance</title>` with hrefs to `download.csv`, `eff.org/files/2020/01/10/aos-bordercounties...csv`, `whohasyourface.org/...csv`, a Google Sheets `gviz/tq?tqx=out:csv` export, Mendeley dataset `386s7f9d25`, and several `eff.org/document/...` pages.
**Retrieved:** 2026-08-20
**Implication for the spec:** (1) The Atlas connector is class 1 (`BULK_FILE`) with `ETAG`-then-`FULL_DIFF`. (2) **The date-stamped `content-disposition` filename must be ignored for content addressing** — the snapshot address is the sha256 of the bytes; using the filename would create a false new-version-every-day signal. (3) The **weak** ETag means it validates semantic equivalence, not byte equality, so SIG must still hash the body — do not trust `304`-absence as proof of change. (4) The `NEWAOSNUMBER (ORI9)` column is *directly* the identity aid the outline asks for in §10 Phase 1A: it embeds a 9-char ORI plus a technology suffix (`VA0850300` + `BWC`), which is the single best deterministic join key SIG will get for free. (5) The `Link N Snapshot` columns mean Atlas already carries archival URLs — SIG should ingest them as `EvidenceArtifact` references rather than re-archiving.
**Outline delta:** EXTENDS §10 Phase 1C substantially and materially helps Q9/Q10 — the ORI9 column is a stronger identity anchor than the outline's "ORI identifiers where available" implies, because it is *already joined to Atlas rows*. **Also a correction:** the outline's §21 and §10 treat Atlas as one CSV; there is a whole Data Library of ~20 heterogeneous datasets behind `/data-library`, each with its own format and license, which is a multi-connector problem, not a one-connector problem.

### F11.8 — Atlas licensing terms are NOT stated on the pages SIG would naturally check

**Claim:** Neither `atlasofsurveillance.org/about` nor `eff.org/pages/atlas-surveillance` states an explicit license or reuse terms for the Atlas dataset. EFF's site-wide footer references a CC BY copyright policy for website content, which is not the same as a dataset license.
**Status:** VERIFIED (as a negative finding)
**Evidence:** `curl -sL https://atlasofsurveillance.org/about | sed 's/<[^>]*>/ /g' | grep -iE "licen|creative commons|attribut|cite|reuse"` returned only prose about scope and the `aos@eff.org` inquiry address — no license string. https://www.eff.org/pages/atlas-surveillance — no explicit CC license or reuse terms for the dataset; site-wide CC BY applies to EFF website materials broadly, not specifically to the dataset. `atlasofsurveillance.org/library` returns HTTP 404 (the correct path is `/data-library`).
**Retrieved:** 2026-08-20
**Implication for the spec:** **The Atlas connector must be built with `source_license_id = "UNDETERMINED"`, and `UNDETERMINED` must block bulk redistribution by default** in the export license gate (§3.2 T-LIC-1). SIG can *link* and *reconcile* against Atlas immediately; it cannot *redistribute* Atlas-derived rows until R2/R8 gets written confirmation to `aos@eff.org`. This is exactly the §17 Stage 0 "determine data licenses" task, and it has a concrete blocking consequence in the pipeline rather than being advisory.
**Outline delta:** CORRECTS the implicit optimism of §10 Phase 1C ("Import surveillance deployments and their source references") and sharpens Q15. The license question is not a research nicety; it is a boolean in the export path.

### F11.9 — Zenodo provides a scriptable DOI-minting path with concept-vs-version DOIs and generous file limits

**Claim:** Zenodo's REST API is at `https://zenodo.org/api/`, uses OAuth 2.0 personal access tokens as `Authorization: Bearer`, with `deposit:write` and `deposit:actions` scopes; publishing a deposition mints a DOI automatically; the system distinguishes concept DOIs (versioned collection) from version DOIs; the newer files API supports up to 50 GB total per record and per file with up to 100 files; rate limits are 60 req/min and 2,000/hour for guests, 100 req/min and 5,000/hour authenticated; a sandbox exists at `sandbox.zenodo.org` issuing 10.5072-prefix test DOIs.
**Status:** VERIFIED
**Evidence:** https://developers.zenodo.org/ — base URL, token scopes and Bearer header, deposit/records/files operations, the 50 GB / 100 file limits vs the older 100 MB per-file limit, concept vs version DOI distinction, the four rate-limit numbers, and the sandbox with its DOI prefix.
**Retrieved:** 2026-08-20
**Implication for the spec:** The release pipeline mints a **version DOI per snapshot release** and cites the **concept DOI** as the citable identity of the dataset as a whole. `ops/release.py` must (a) develop against sandbox in CI, (b) upload the release manifest + artifacts under the 50 GB ceiling (SIG's projected bulk export is single-digit GB, §6.2, so this is not binding), and (c) store the returned version DOI back into `MANIFEST.json` and the `release` table — the DOI is provenance, so it belongs in the lineage record. The 100-file limit means artifacts must be bundled per format, not per table-shard.
**Outline delta:** EXTENDS §14.3 ("versioned snapshots", "reproducible ingestion") with a concrete, free, permanent-identifier mechanism the outline does not name.

### F11.10 — Data Package (`datapackage.json`) is the right manifest standard and already models licenses and resources

**Claim:** The Data Package standard requires a `resources` array of at least one Data Resource, strongly recommends `name`, `id` (UUID or DOI), `licenses`, and `profile`, and permits `title`, `description`, `version`, `created`, `keywords`, `contributors`, `sources`, `homepage`, `image`; licenses are an array of objects each carrying `name` (Open Definition id) or `path` (URL) plus optional `title`; the spec explicitly disclaims that the license property is legally binding.
**Status:** VERIFIED
**Evidence:** https://datapackage.org/standard/data-package/ — required `resources`; strongly recommended `name`, `id`, `licenses`, `profile`; the license array shape and the caveat "This property is not legally binding and does not guarantee the package is licensed under the terms defined in this property."
**Retrieved:** 2026-08-20
**Implication for the spec:** SIG's release manifest is a **Data Package descriptor with a `sig` profile extension** (§5.4), not a bespoke JSON blob. `id` carries the Zenodo version DOI (F11.9). Per-resource `licenses` is where the ODbL-vs-other split lives (§14.1 of the outline): the OSM-derived physical-asset resource carries ODbL in its own resource-level `licenses` array while the rest of the package carries SIG's chosen license — **this is the mechanism by which "Strategy A: keep OSM as a separable external layer" becomes machine-checkable rather than aspirational.**
**Outline delta:** EXTENDS §14.1/§14.2 with a concrete encoding. The outline says "source licenses should be first-class metadata"; Data Package makes them first-class *at the artifact level*, which is where a downstream consumer actually needs them.

### F11.11 — PMTiles + tippecanoe give SIG a zero-backend map tile pipeline

**Claim:** PMTiles is a single-file archive format for tiled data, currently spec version 3, with reference implementations under BSD-3-Clause and the specification itself public domain / CC0; it serves tiles from commodity object storage via HTTP range requests with no tile server; tooling includes `go-pmtiles`, JS libraries for MapLibre/Leaflet/OpenLayers, and serverless deployments. Tippecanoe (Felt fork) is at version 2.0.0, BSD-2-Clause, actively maintained by Erica Fischer at Felt, and can write `.pmtiles` directly via `-o file.pmtiles`.
**Status:** VERIFIED
**Evidence:** https://github.com/protomaps/PMTiles — "a single-file archive format for tiled data", spec v3, BSD-3-Clause reference implementations, CC0/public-domain spec, range-request architecture, "low-cost, zero-maintenance map applications", tooling list. https://github.com/felt/tippecanoe — v2.0.0 (equivalent to 1.36.0 of the original), BSD-2-Clause, `-o file.mbtiles, file.pmtiles or --output=...`.
**Retrieved:** 2026-08-20
**Implication for the spec:** The map surface (§15.2 of the outline) needs **no tile server at any scale**: `exports/` builds `.pmtiles` with tippecanoe and pushes to R2, where zero egress (F11.19) makes map traffic free. This removes an entire class of infrastructure from the cost model and is a large part of why bootstrap comes in under $50/month (§6.3).
**Outline delta:** EXTENDS §15.2 and §14.3 — a versioned `.pmtiles` per release is itself a reproducible, checksummed artifact, so the map is part of the citable snapshot rather than a separate live service that can silently drift from the data.

### F11.12 — Datasette (0.65.3, Apache-2.0) and Datasette Lite make a SQLite bundle a genuinely serverless product surface

**Claim:** Datasette 0.65.3 is Apache-2.0, requires Python >=3.9, and is "an open source multi-tool for exploring and publishing data" that turns datasets into interactive websites with APIs. Datasette Lite runs the full Datasette application in the browser via Pyodide/WebAssembly with no server, at the cost of a ~10 MB initial download, no SQL threading (`num_sql_threads: 0`), non-functional JS/plugin features, a CORS requirement on remotely-hosted databases, and wheel-only dependency installation.
**Status:** VERIFIED
**Evidence:** https://pypi.org/pypi/datasette/json — 0.65.3, Apache-2.0, requires_python >=3.9. https://simonwillison.net/2022/May/4/datasette-lite/ — "a server-side Python web application running in a browser", Pyodide + Web Worker architecture, the ~10 MB download, `num_sql_threads: 0`, JS-feature and plugin limitations, CORS requirement, micropip wheel-only constraint.
**Retrieved:** 2026-08-20
**Implication for the spec:** Ship a **SQLite bundle** as a first-class export artifact (§5.4). In steady state it powers a hosted Datasette instance; in **degraded $0 mode (§6.6) the same artifact plus Datasette Lite gives a fully interactive query UI with literally zero running infrastructure** — the user's browser is the server. The CORS requirement means R2 must be configured with permissive CORS on the exports bucket, which is a one-line config but must be in `ops/`.
**Outline delta:** EXTENDS §15.7 and §14.3. This is the single most important finding for the sustainability question (§6.6): SIG's core product can survive total funding loss without becoming a dead link.

### F11.13 — GitHub Actions gives a real free scheduler, with two footguns that determine the degraded-mode design

**Claim:** GitHub Actions provides 2,000 free minutes/month on Free plans (3,000 Pro/Team, 50,000 Enterprise Cloud), 500 MB–50 GB artifact storage by plan, 10 GB cache per repo, and **standard GitHub-hosted runners are free for public repositories**; paid overage is $0.006/min Linux 2-core, $0.010/min Windows, $0.062/min macOS; artifact storage overage $0.25/GB-month and cache $0.07/GB-month. Scheduled workflows run at minimum every 5 minutes, **are automatically disabled in public repositories after 60 days with no repository activity**, and `schedule` events can be delayed or dropped during high load, especially at the top of the hour.
**Status:** VERIFIED
**Evidence:** https://docs.github.com/en/billing/.../about-billing-for-github-actions — the free-minute tiers, storage allowances, per-minute rates, and "The use of standard GitHub-hosted runners is free" in public repositories. https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows — 5-minute minimum interval; "In a public repository, scheduled workflows are automatically disabled when no repository activity has occurred in 60 days"; "The `schedule` event can be delayed during periods of high loads"; recommendation to avoid the top of the hour.
**Retrieved:** 2026-08-20
**Implication for the spec:** (1) **If SIG's repo is public, Actions minutes are free and unlimited in practice** — this is the backbone of degraded mode (§6.6). (2) The 60-day auto-disable is fatal to an abandoned-but-alive project, so degraded mode **must** include a trivial keepalive (a weekly workflow that commits a freshness-log line), turning "repository activity" into a self-sustaining property. (3) Never schedule at `:00`; SIG's crons run at `:17`, `:23`, `:41` etc. (4) Delays and drops mean Actions is **acceptable for daily/weekly cadence and unacceptable for anything claiming "hourly guaranteed"** — the freshness dashboard must therefore report *observed* last-success, never *scheduled* cadence.
**Outline delta:** EXTENDS §14.3 and adds an operational-risk item the outline does not contemplate at all. "The project's data silently stopped updating 61 days after the last human touched the repo" is a realistic death mode for a volunteer public-interest project.

### F11.14 — Protego is the correct robots.txt parser

**Claim:** Protego 0.6.2, BSD-3-Clause, requires Python >=3.10; a pure-Python robots.txt parser implementing modern conventions (wildcards, length-based precedence) following Google's specification rather than the 1996 draft; exposes fetch permission, crawl delay, request rate, sitemaps, and preferred host.
**Status:** VERIFIED
**Evidence:** https://pypi.org/pypi/protego/json — version 0.6.2, BSD-3-Clause, requires_python >=3.10, the Google-spec framing, wildcard and length-precedence support, and the crawl-delay/request-rate/sitemap/host API surface.
**Retrieved:** 2026-08-20
**Implication for the spec:** `PolitenessGateway` uses Protego, not `urllib.robotparser` (which follows the 1996 draft and mishandles wildcards — a real correctness gap when a portal disallows `/*.pdf$`). Protego's `sitemaps` accessor is a bonus: `discover()` for HTML-scrape connectors should prefer a declared sitemap over link-crawling.
**Outline delta:** Purely additive to §13.5 ("no operational interference") — correct robots handling is the mechanical expression of that principle.

### F11.15 — DocumentCloud's public API documentation is not reachable at the URLs SIG would try

**Claim:** `https://www.documentcloud.org/help/api/` 301-redirects to a Notion-hosted page (`help.muckrock.com/API-19ef889269638147bbb7d8cc8af8e0fc`) whose content did not render usable API details through fetch; `https://www.documentcloud.org/api/` returns HTTP 404; the `MuckRock/documentcloud` repository README covers local Docker development against a Squarelet auth service and does not document the public API surface, license, or self-hosting.
**Status:** INACCESSIBLE
**Evidence:** https://www.documentcloud.org/help/api/ → 301 to `help.muckrock.com/API-19ef889269638147bbb7d8cc8af8e0fc`; that page returned essentially only "Notion" plus a topic list with no substantive API content. https://www.documentcloud.org/api/ → HTTP 404. https://raw.githubusercontent.com/MuckRock/documentcloud/master/README.md → local dev setup only; explicitly no API docs, no license info, no production self-hosting guidance.
**Retrieved:** 2026-08-20
**Implication for the spec:** **Do not design the DocumentCloud connector from memory.** The fallback is: (a) treat DocumentCloud as reachable via the *MuckRock* account/token system (the Squarelet linkage in the repo README plus the shared help domain strongly suggest a common auth plane, but this is inference, not verification); (b) build it as a class-2 cursored REST connector with the conservative default budget; (c) file a spec open question (§8, OQ-3) requiring a human to read the Notion API page in a browser before implementation. Q8 of the outline is **not answered** by this workstream.
**Outline delta:** CONTRADICTS the outline's assumption in Q8 that DocumentCloud programmatic access is straightforwardly documented. It may well be — but it is not discoverable at the canonical URLs, which is itself a finding: any SIG contributor will hit the same 404.

### F11.16 — Playwright is the right headless-browser tool and is Apache-2.0

**Claim:** Playwright for Python is at 1.62.0, Apache-2.0, requires Python >=3.10, bundling Chromium 151, Firefox 153, and WebKit 26.5 across Linux/macOS/Windows, with sync and async APIs.
**Status:** VERIFIED
**Evidence:** https://pypi.org/pypi/playwright/json — version 1.62.0, Apache-2.0, requires_python >=3.10, the three bundled engines and their versions, sync+async APIs, maintained by Microsoft.
**Retrieved:** 2026-08-20
**Implication for the spec:** Class-6 connectors use Playwright with a **hard global concurrency cap of 2** and a required `route`-level request interceptor that (a) blocks images/fonts/analytics to cut bandwidth and cost, and (b) **captures the underlying XHR/JSON responses**, which are usually the real data and are far more stable to parse than the rendered DOM. Capture both: the DOM-after-settle HTML *and* each intercepted JSON payload, each as its own content-addressed snapshot with a `derived_from` link.
**Outline delta:** EXTENDS §2 Layer B — the "independent transparency-portal archival projects" described taking "PDF snapshots; raw HTML snapshots; normalized JSON". SIG should capture the *intercepted API responses* too, which none of the described projects mention and which is strictly better evidence than scraped HTML.


---

## PART B — ORCHESTRATION

## 3. Orchestrator evaluation and recommendation

### 3.1 Version and license findings

Every candidate was checked for current version and — critically — for **license drift**, because BSL/Elastic-style relicensing is the standard failure mode for VC-backed data infrastructure and would poison a public-interest project's dependency tree.

### F11.17 — Dagster OSS is at 1.13.18 and remains Apache-2.0

**Claim:** `dagster` 1.13.18 on PyPI, license classifier Apache-2.0, requires Python `>=3.10,<3.15` (i.e. 3.10–3.14), Production/Stable, described as "an orchestration platform for the development, production, and observation of data assets." The GitHub repo `dagster-io/dagster` reports license "Apache License 2.0", ~16,033 stars, 2,594 open issues, last pushed 2026-08-19. `dagster-webserver` 1.13.18 is separately published and also Apache-2.0.
**Status:** VERIFIED
**Evidence:** https://pypi.org/pypi/dagster/json; https://api.github.com/repos/dagster-io/dagster; https://pypi.org/pypi/dagster-webserver/json.
**Retrieved:** 2026-08-20
**Implication for the spec:** Dagster OSS can be adopted without license risk to SIG's own licensing (§14). The commercial product (Dagster+) is a separate hosted offering; nothing in the OSS packages requires it. Pin `dagster>=1.13,<1.14` and treat minor upgrades as a scheduled chore.
**Outline delta:** N/A (tooling choice, not in outline).

### F11.18 — Prefect, Airflow, Kestra, Temporal, and Argo licenses and versions

**Claim:** `prefect` 3.8.3, Apache-2.0, Python `>=3.10,<3.15`. `apache-airflow` 3.3.1, Apache-2.0, Python `!=3.15,>=3.10`. `kestra-io/kestra` — Apache License 2.0, ~27,866 stars, pushed 2026-08-20, "Event Driven Orchestration & Scheduling Platform". `temporalio/temporal` — MIT, ~22,421 stars, pushed 2026-08-20. `argoproj/argo-workflows` — Apache-2.0, ~16,922 stars, pushed 2026-08-20, "Workflow Engine for Kubernetes".
**Status:** VERIFIED
**Evidence:** https://pypi.org/pypi/prefect/json; https://pypi.org/pypi/apache-airflow/json; https://api.github.com/repos/kestra-io/kestra; https://api.github.com/repos/temporalio/temporal; https://api.github.com/repos/argoproj/argo-workflows.
**Retrieved:** 2026-08-20
**Implication for the spec:** None of the five carries a viral or source-available license at the core. Kestra's *core* is Apache-2.0 but its Enterprise Edition gates RBAC, audit logs, worker groups, and storage isolation behind custom pricing (F11.22) — relevant only if SIG ever needs multi-tenant access control.
**Outline delta:** N/A.

### F11.19 — Windmill's core is AGPLv3 with a proprietary enterprise layer and a no-resale Community Edition clause

**Claim:** `windmill-labs/windmill` reports GitHub license "Other (NOASSERTION)". Its LICENSE file shows a split: backend and frontend **without** the `enterprise` compile flag are **AGPL v3**; client libraries (python/deno/go/powershell) and the OpenAPI/OpenFlow specs are **Apache 2.0**; code behind the `enterprise` flag or requiring a positive license check is **proprietary**; and the Community Edition docker images carry the right "to distribute...but not to sell, resell, serve as a managed service, modify or wrap under any form without an explicit agreement."
**Status:** VERIFIED
**Evidence:** https://api.github.com/repos/windmill-labs/windmill (license: Other/NOASSERTION); https://raw.githubusercontent.com/windmill-labs/windmill/main/LICENSE (the AGPL/Apache/proprietary split and the CE distribution restriction).
**Retrieved:** 2026-08-20
**Implication for the spec:** **Disqualifying for SIG's orchestrator slot.** AGPLv3 on a component that would sit in the middle of SIG's stack raises exactly the "does this reach my code?" question SIG cannot afford to litigate, and the CE image restriction is incompatible with a public-interest project that may want to let local groups run their own instance. This is not a judgment on Windmill's quality — it is a fit judgment for a project whose entire value proposition is reusability.
**Outline delta:** EXTENDS §14.3 ("open source code is not enough") — the *dependency* licenses matter as much as SIG's own.

### F11.20 — Soda Core has been relicensed to Elastic License 2.0

**Claim:** `soda-core` 4.21.1 on PyPI declares its license as **"Proprietary"**; the repository `sodadata/soda-core` reports GitHub license "Other (NOASSERTION)", is not archived, was pushed 2026-08-20, and describes itself as "Data Contracts engine for the modern data stack"; its `LICENSE` file at `main` is the **Elastic License 2.0**, which prohibits providing the software to third parties as a hosted or managed service exposing a substantial set of its features, prohibits circumventing license-key functionality, requires notice preservation, and terminates on patent assertion.
**Status:** VERIFIED — and this is a **correction to the common assumption** that Soda Core is open source
**Evidence:** https://pypi.org/pypi/soda-core/json (license: "Proprietary", requires_python >=3.10, version 4.21.1); https://api.github.com/repos/sodadata/soda-core (license "Other (NOASSERTION)"); https://raw.githubusercontent.com/sodadata/soda-core/main/LICENSE (Elastic License 2.0, with the hosted/managed-service restriction and license-key clause quoted above).
**Retrieved:** 2026-08-20
**Implication for the spec:** **Soda Core is eliminated from consideration.** SIG plans to publish its full pipeline as reusable open code (§14.3) and may well end up running a hosted quality dashboard — the ELv2 managed-service clause is a direct conflict, and the license-key clause is incompatible with a fully self-hostable stack for local groups. Any pre-existing SIG design note recommending Soda must be revised.
**Outline delta:** This does not correct the outline (which does not name a DQ tool) but it **corrects the field**: Soda Core appears on essentially every 2024-era "open source data quality tools" list, and a downstream design agent working from memory would very likely have picked it.

### F11.21 — Great Expectations, Pandera, dbt-core, and Pointblank licenses and versions

**Claim:** `great-expectations` 1.21.0, Apache-2.0, Python `>=3.10,<3.14`; repo `great-expectations/great_expectations` is Apache-2.0, ~11,725 stars, 25 open issues, pushed 2026-08-20. `pandera` 0.32.1, **MIT**, Python >=3.10, "The Open-source Framework for Dataset Validation", maintained by Union.ai, supporting pandas/polars/pyspark. `dbt-labs/dbt-core` is Apache-2.0, ~13,672 stars, pushed 2026-08-20. `pointblank` 0.27.0, MIT, Python >=3.10, validating against Polars/Pandas/DuckDB/MySQL/PostgreSQL/SQLite/Parquet/PySpark/Snowflake, with YAML-configurable validation, a CLI, threshold management, and HTML report output.
**Status:** VERIFIED
**Evidence:** https://pypi.org/pypi/great-expectations/json; https://api.github.com/repos/great-expectations/great_expectations; https://pypi.org/pypi/pandera/json; https://api.github.com/repos/dbt-labs/dbt-core; https://pypi.org/pypi/pointblank/json.
**Retrieved:** 2026-08-20
**Implication for the spec:** All four are license-safe. Note GX's Python ceiling (`<3.14`) is *tighter* than Dagster's (`<3.15`) — this constrains SIG's Python version choice if GX is adopted, which is one more reason to prefer Pandera (§4.1).
**Outline delta:** N/A.

### F11.22 — Kestra's free edition is genuinely capable but the enterprise wall sits exactly where a growing project hits it

**Claim:** Kestra ships Open Source (free, unlimited flows/executions, 1,900+ plugins, declarative workflows, event-driven scheduling, multi-cloud/air-gapped), Kestra Cloud (managed, pay-as-you-scale), and Enterprise Edition (custom pricing, contact sales) which gates LDAP/SCIM/custom RBAC, audit logs, storage isolation, worker groups, high concurrency, enterprise plugins, AI copilot, and SLA support.
**Status:** VERIFIED
**Evidence:** https://kestra.io/pricing — the three editions and the specific feature split above.
**Retrieved:** 2026-08-20
**Implication for the spec:** Kestra is a legitimate runner-up, especially for its YAML-first ergonomics and plugin breadth. Its disqualifier for SIG is not license but **impedance mismatch**: SIG's pipeline logic is Python with rich typed dataclasses (§1.3), and a YAML orchestration DSL forces that logic into subprocess boundaries where the type system stops helping. Audit logs behind Enterprise is a mild concern for a project that cares about provenance of its own operations.
**Outline delta:** N/A.

### F11.23 — Argo Workflows requires Kubernetes; Temporal requires a substantial self-hosted footprint

**Claim:** Argo Workflows' quick start states "Before installing Argo, you need a Kubernetes cluster and `kubectl` configured to access it", suggests minikube/kind/k3s/k3d/Docker Desktop for local testing, and explicitly says the quick-start manifests are "not suitable for production." Temporal's self-hosted guide frames Temporal as "open source infrastructure software that orchestrates your durable applications", points to Docker/Kubernetes/manual deployment paths, a production checklist covering "scale, reliability, operations, and long-term maintainability", monitoring, TLS/mTLS, namespace management and upgrades, and offers the single-binary Temporal CLI dev server only as a **development** alternative.
**Status:** VERIFIED
**Evidence:** https://argo-workflows.readthedocs.io/en/latest/quick-start/; https://docs.temporal.io/self-hosted-guide.
**Retrieved:** 2026-08-20
**Implication for the spec:** Both are disqualified on **ops burden for a small volunteer team** (the explicit constraint). Argo mandates a Kubernetes cluster SIG has no other reason to run. Temporal's own documentation frames production self-hosting as a checklist-driven undertaking with TLS/mTLS, namespace, and upgrade management — appropriate for durable-execution-critical systems, disproportionate for a nightly scraping pipeline.
**Outline delta:** N/A.

### F11.24 — Self-hosted Dagster and Prefect both reduce to "a Python process plus Postgres"

**Claim:** A self-hosted Dagster OSS deployment consists of a webserver (UI), a daemon (schedules/sensors/background), and code locations, all sharing a single `dagster.yaml` instance config; storage defaults to SQLite on the local filesystem, with PostgreSQL (`dagster-postgres`, UTC-configured) or MySQL (`dagster-mysql`) for production, plus compute-log storage (local/S3/GCS/Azure) and artifact storage. Prefect self-hosting starts with `prefect server start` (default http://127.0.0.1:4200), defaults to SQLite at `~/.prefect/prefect.db`, and requires **PostgreSQL and Redis** for multi-worker mode because "SQLite is not supported due to database locking issues."
**Status:** VERIFIED
**Evidence:** https://docs.dagster.io/deployment/oss/oss-instance-configuration; https://docs.prefect.io/v3/how-to-guides/self-hosted/server-cli.
**Retrieved:** 2026-08-20
**Implication for the spec:** Both fit SIG's budget. Dagster needs **Postgres only**; Prefect needs **Postgres + Redis** once you go multi-worker. That is one more managed service, one more thing to back up, and one more thing to break at 3am — a real, if small, point for Dagster given the volunteer-team constraint. Because SIG already runs Postgres+PostGIS for the graph itself, Dagster's storage requirement is nearly free (a separate schema or a small separate database on the same instance).
**Outline delta:** N/A.

### F11.25 — Dagster's asset model and declarative automation map onto SIG's evidence→claim lineage

**Claim:** In Dagster, "An asset is an object in persistent storage, such as a table, file, or persisted machine learning model"; asset definitions are code-based descriptions of data objects and how to compute them; running an asset's function and storing the result is called **materialization**; asset definitions intrinsically know their dependencies (unlike ops, which are dependency-agnostic until placed in a graph). Declarative Automation "uses information about the status of your assets and their dependencies to launch executions", with recommended conditions `on_cron` (run on a schedule after upstreams update within the tick), `eager` (run whenever dependencies update, waiting for all upstream partitions and skipping while upstreams are in progress), and `on_missing` (fill missing partitions once upstreams are available). Asset freshness policies exist as a separate observability feature.
**Status:** VERIFIED
**Evidence:** https://docs.dagster.io/guides/build/assets; https://docs.dagster.io/guides/automate/declarative-automation/.
**Retrieved:** 2026-08-20
**Implication for the spec:** See the argument in §3.3 — this is the substantive reason for the recommendation, not a preference.
**Outline delta:** EXTENDS §19.1/§19.3 with a concrete execution model.

### 3.2 Scorecard

Weights reflect the stated constraint: *small, possibly volunteer team; low ops burden; cheap hosting; reproducibility and lineage are the product.*

| Criterion (weight) | Dagster 1.13.18 | Prefect 3.8.3 | Airflow 3.3.1 | Temporal | Argo WF | Kestra | Windmill | cron + job table |
|---|---|---|---|---|---|---|---|---|
| **License safety (×3)** | 5 — Apache-2.0 (F11.17) | 5 — Apache-2.0 | 5 — Apache-2.0 | 5 — MIT | 5 — Apache-2.0 | 4 — Apache core, EE gates audit logs | **1 — AGPL core + CE resale ban (F11.19)** | 5 |
| **Lineage / provenance fit (×3)** | **5 — assets are first-class, materializations carry metadata (F11.25)** | 3 — task-centric; assets bolted on | 2 — task-centric | 1 — workflow-centric, no data model | 1 | 3 | 3 | 1 |
| **Ops burden for 1–3 people (×3)** | 4 — webserver + daemon + Postgres (F11.24) | 4 — server + Postgres **+ Redis** multi-worker (F11.24) | 2 — scheduler + webserver + workers + DB | **1 — production checklist, TLS/mTLS, namespaces (F11.23)** | **1 — requires Kubernetes (F11.23)** | 3 — JVM service + DB | 3 | **5 — nothing to run** |
| **Backfill / replay ergonomics (×3)** | **5 — partitions + `on_missing` + per-partition backfill UI** | 3 | 3 | 2 | 2 | 3 | 2 | 1 |
| **Python-native typed pipeline (×2)** | 5 | 5 | 4 | 3 (SDK-based) | 2 (container-per-step) | 2 (YAML DSL) | 3 | 5 |
| **Cheap hosting (×2)** | 4 — one small VM + existing PG | 4 | 2 | 2 | 1 | 3 | 3 | **5** |
| **Local dev / testability (×2)** | 5 — `dg dev`, assets unit-testable as plain fns | 4 | 3 | 3 | 2 | 3 | 3 | 5 |
| **Observability out of the box (×2)** | 5 — asset catalog, run timeline, materialization metadata | 4 | 4 | 4 | 3 | 4 | 4 | 1 |
| **Ecosystem / hireability (×1)** | 4 | 4 | 5 | 4 | 3 | 3 | 2 | 5 |
| **Weighted total (max 105)** | **93** | 79 | 66 | 51 | 44 | 66 | 51 | 65 |

### 3.3 Recommendation: Dagster OSS — and the argument for why assets fit SIG specifically

**Recommend Dagster OSS, self-hosted, Postgres-backed.**

The outline hints that "software-defined assets map unusually well onto SIG's evidence→claim lineage." That is correct, and the reason is sharper than "both involve data":

**1. SIG's pipeline is not a sequence of tasks; it is a set of persistent objects with declared derivations.** The eight stages in §1.2 each *persist* something with a content address. That is the literal definition Dagster uses for an asset — "an object in persistent storage" (F11.25). A task-centric orchestrator models "run the Flock scraper"; an asset-centric one models "`flock_portal_snapshot`, `flock_portal_parsed`, `flock_portal_raw_claims`, `flock_portal_normalized` exist, and here is how each is derived from the one before." The second model is the one SIG's *data* model already assumes. Using a task orchestrator would mean maintaining the lineage graph twice: once in Dagster and once in PROV.

**2. Materialization metadata is a natural home for the content addresses.** Every Dagster materialization can carry structured metadata. SIG attaches `snapshot_sha256`, `canonical_sha256`, `parser_version`, `row_count`, `claims_emitted`, `review_tasks_created`, and `unavailable_count`. The asset catalog then *is* a browsable operational view of the evidence chain, for free — which is a meaningful fraction of the "freshness dashboard" (§6.4) at zero build cost.

**3. Partitions are the backfill primitive SIG needs.** SIG's natural partition keys are (a) date, for snapshot-per-day sources, and (b) source/portal-slug, for the fan-out over ~thousands of Flock portals. Dagster's partition model plus `on_missing` (F11.25) means "re-extract every 2025-Q4 partition of `flock_portal_raw_claims` with parser v7" is a first-class UI/CLI operation rather than a bespoke script. Every other candidate makes this a script.

**4. `on_cron` semantics match "snapshot cadence" reasoning.** F11.25: `on_cron` runs an asset on a schedule *after all upstreams have updated within that tick*. SIG's derived assets (e.g. the reconciliation views in §11 of the outline) should not recompute against a half-updated evidence layer, and this is exactly that constraint expressed declaratively rather than as `sleep 300` in a bash script.

**5. Freshness policies are the trust affordance.** F11.25 notes freshness policies as a separate observability feature. SIG's public freshness page (§6.4) is a *trust* artifact — "we last successfully read this portal 3 days ago" is a claim about SIG's own reliability, and it should be generated from the same source of truth the operators use.

**The decisive counter-argument, and why it does not win:** plain cron + a job table scores 65 and is genuinely defensible for a 1-person project. It wins on ops burden and cost. It loses on the two things that *are the product*: backfill/replay ergonomics (§2.6) and lineage. SIG's differentiator is reproducibility; the orchestrator is where reproducibility is either mechanized or left to discipline. Discipline does not survive a volunteer team.

**Mandatory hedge — the escape hatch requirement.** Because a volunteer project must survive its own tooling choices, **Dagster must never be a dependency of the pipeline logic.** Concretely:

- Every asset body is a thin wrapper over a plain function in `sig-ingest` that is fully callable as `uv run sig-ingest run <connector> --since <ts> --to <ts>`.
- No connector imports `dagster`. The `dagster` imports live only in `orchestration/`.
- CI runs the entire nightly pipeline via the CLI, without Dagster, on a small fixture set. If that job ever breaks, the escape hatch has rotted.
- Degraded mode (§6.6) runs the CLI from GitHub Actions with no orchestrator at all.

This makes the Dagster decision **reversible at any time for the cost of a cron file**, which is the correct risk posture for a 10-year public-interest project choosing infrastructure in 2026.

### 3.4 Runner-up guidance

- **If the team turns out to be one person who hates services:** cron + job table, with the *same* CLI, the same run/lineage tables (§3.5), and the same content addressing. SIG loses the catalog and the backfill UI, nothing else. This is a legitimate Stage-1 posture.
- **If SIG later needs multi-tenant, per-local-group execution:** re-evaluate Kestra (F11.22), whose YAML flows are the most plausible thing to hand to a non-Python local partner.
- **Never Airflow** for this project: the highest ops burden of the Apache-licensed options with the weakest data model. Its ecosystem advantage is irrelevant to a team of three.

### 3.5 Lineage: the operational records

R6 owns the PROV model. R11 owns the **operational** records that PROV projects from. The rule: *every claim must be traceable to the run, the connector version, the parser version, and the source snapshot hash.* That is four foreign keys, and they must be **NOT NULL on the claim row**, not reconstructible-by-join, because a join across a mutable table is not provenance.

```sql
-- ops lineage schema (sig_ops). Deliberately separate from the graph schema.

CREATE TABLE ingest_run (
    run_id              text PRIMARY KEY,         -- ULID
    connector_id        text NOT NULL,
    connector_version   text NOT NULL,            -- semver of the connector module
    code_commit         text NOT NULL,            -- git sha of the whole repo, from CI
    image_digest        text,                     -- sha256 of the container image, if containerized
    ontology_version    text NOT NULL,            -- LinkML schema version in force
    started_at          timestamptz NOT NULL,
    ended_at            timestamptz,
    status              text NOT NULL,            -- running|succeeded|failed|cancelled
    trigger             text NOT NULL,            -- schedule|manual|sensor|backfill|replay
    replay_of_run_id    text REFERENCES ingest_run(run_id),
    watermark_in        jsonb NOT NULL,
    watermark_out       jsonb,
    partition_key       text,                     -- Dagster partition, if any
    counts              jsonb NOT NULL DEFAULT '{}'::jsonb,  -- fetched/captured/parsed/claims/unavailable/review_tasks
    env                 jsonb NOT NULL            -- python version, key dep versions, region
);

CREATE TABLE snapshot (                            -- the immutable blob (content)
    sha256              text PRIMARY KEY,
    size_bytes          bigint NOT NULL,
    media_type          text NOT NULL,
    storage_uri         text NOT NULL,
    first_captured_at   timestamptz NOT NULL
);

CREATE TABLE snapshot_observation (                -- the EVENT of seeing it
    observation_id      text PRIMARY KEY,
    snapshot_sha256     text NOT NULL REFERENCES snapshot(sha256),
    ref_key             text NOT NULL,
    run_id              text NOT NULL REFERENCES ingest_run(run_id),
    captured_at         timestamptz NOT NULL,
    source_url          text,
    final_url           text,                      -- after redirects
    http_status         int,
    response_headers    jsonb,
    request_trace       jsonb NOT NULL             -- UA sent, elapsed_ms, TLS fingerprint, proxy
);
CREATE INDEX ON snapshot_observation (ref_key, captured_at DESC);

CREATE TABLE source_unavailable_event (            -- §1.5 — disappearance is DATA
    event_id            text PRIMARY KEY,
    ref_key             text NOT NULL,
    connector_id        text NOT NULL,
    run_id              text NOT NULL REFERENCES ingest_run(run_id),
    reason              text NOT NULL,
    observed_at         timestamptz NOT NULL,
    detail              text,
    consecutive_count   int NOT NULL,
    prior_success_at    timestamptz,
    prior_snapshot_sha  text,
    escalated_to        text                        -- 'portal_disappeared' | 'access_revoked' | NULL
);
CREATE INDEX ON source_unavailable_event (ref_key, observed_at DESC);

CREATE TABLE parsed_doc (
    canonical_sha256    text PRIMARY KEY,
    snapshot_sha256     text NOT NULL REFERENCES snapshot(sha256),
    parser_id           text NOT NULL,
    parser_version      text NOT NULL,
    run_id              text NOT NULL REFERENCES ingest_run(run_id),
    parsed_at           timestamptz NOT NULL,
    canonical_json      jsonb NOT NULL,
    warnings            jsonb NOT NULL DEFAULT '[]'::jsonb,
    UNIQUE (snapshot_sha256, parser_id, parser_version)   -- re-parse with same version is a no-op
);

CREATE TABLE extraction (
    extraction_id       text PRIMARY KEY,
    parsed_doc_sha      text NOT NULL REFERENCES parsed_doc(canonical_sha256),
    extractor_id        text NOT NULL,
    extractor_version   text NOT NULL,
    method              text NOT NULL,             -- deterministic|llm|human
    run_id              text NOT NULL REFERENCES ingest_run(run_id),
    extracted_at        timestamptz NOT NULL,
    -- LLM columns are NULL for deterministic extraction; NOT NULL enforced by CHECK when method='llm'
    model_id            text,                      -- e.g. 'claude-opus-5'
    model_params_hash   text,                      -- sha256 of the exact request params
    prompt_id           text,
    prompt_version      text,
    prompt_sha256       text,
    token_usage         jsonb,
    CONSTRAINT llm_provenance_complete CHECK (
        method <> 'llm' OR (model_id IS NOT NULL AND prompt_sha256 IS NOT NULL
                            AND model_params_hash IS NOT NULL)
    )
);

CREATE TABLE claim_lineage (                       -- the four mandatory FKs, denormalized on purpose
    claim_id            text PRIMARY KEY,          -- FK to the graph's claim table
    run_id              text NOT NULL REFERENCES ingest_run(run_id),
    connector_id        text NOT NULL,
    connector_version   text NOT NULL,
    parser_id           text NOT NULL,
    parser_version      text NOT NULL,
    extractor_id        text NOT NULL,
    extractor_version   text NOT NULL,
    normalizer_version  text NOT NULL,
    snapshot_sha256     text NOT NULL REFERENCES snapshot(sha256),
    parsed_doc_sha      text NOT NULL REFERENCES parsed_doc(canonical_sha256),
    extraction_id       text NOT NULL REFERENCES extraction(extraction_id),
    source_spans        jsonb NOT NULL             -- >= 1 span, enforced by CHECK
);
```

**Mapping to PROV (R6 owns the RDF; this is the projection contract):**

| Operational record | PROV term |
|---|---|
| `ingest_run` | `prov:Activity` |
| `connector_version` / `parser_version` / `extractor_version` | `prov:SoftwareAgent` + `prov:wasAssociatedWith` |
| `snapshot` | `prov:Entity` (the primary evidence) |
| `snapshot_observation` | `prov:Activity` (`prov:generated` the entity) with `prov:atTime` |
| `parsed_doc` | `prov:Entity`, `prov:wasDerivedFrom` snapshot |
| `extraction` | `prov:Activity` |
| `claim` | `prov:Entity`, `prov:wasDerivedFrom` parsed_doc, `prov:wasGeneratedBy` extraction |
| `source_unavailable_event` | `prov:Activity` with a SIG-specific `sig:observedAbsence` role |

**OpenLineage is available but is not recommended as the primary lineage store.**

### F11.26 — OpenLineage exists as an Apache-2.0 standard with Airflow/Spark/dbt/Flink integrations

**Claim:** OpenLineage is "an Open standard for metadata and lineage collection designed to instrument jobs as they are running", Apache-2.0, a graduate project of the LF AI & Data Foundation, with a generic run/job/dataset model extensible via custom facets, an OpenAPI-defined spec at `/spec/OpenLineage.md`, integrations including Apache Spark, Apache Airflow, dbt, and Apache Flink, and Marquez as the reference implementation.
**Status:** PARTIALLY VERIFIED — spec version number not stated in the fetched content
**Evidence:** https://github.com/OpenLineage/OpenLineage — the quoted definition, Apache-2.0, the facet-extensible run/job/dataset model, the listed integrations, and Marquez.
**Retrieved:** 2026-08-20
**Implication for the spec:** SIG should **emit** OpenLineage events as a secondary, optional output (a Dagster sensor that POSTs to a configured OL endpoint), because it costs almost nothing and makes SIG legible to any partner already running Marquez. It should **not** be the system of record: OpenLineage models job-level lineage, not *claim-level* provenance with source spans, and SIG's requirement (§9.4, §19.1) is the latter. Custom facets could carry the extra fields, but that means owning a bespoke facet schema anyway — at which point the Postgres tables above are simpler and queryable.
**Outline delta:** EXTENDS §18 (interoperation) — OpenLineage emission is a cheap "we play well with others" gesture.

### 3.6 Backfill and replay — the core requirement

This is, in R11's view, the single most under-specified requirement in the outline, and the one most likely to be got wrong. §19.2 ("raw before normalized") and §14.3 ("reproducible ingestion") *imply* it; nothing states it.

**Requirement (restated precisely):** SIG must be able to run an improved parser/extractor over archived snapshots and produce a **new** set of claims, **without destroying the old ones**, **without fabricating new observation times**, and **without silently changing what SIG is recorded as having believed in the past.**

#### 3.6.1 Why the naive approaches fail

| Naive approach | Why it fails |
|---|---|
| Re-run the pipeline and `UPDATE` the claims | Destroys history; violates §19.3; makes "what did SIG believe on 2026-03-01?" unanswerable |
| Re-run and `DELETE` + `INSERT` | Same, plus breaks every external stable ID (§20 Q37) |
| Version the parser and keep only the newest claim per (source, predicate) | Silently discards the old interpretation; a downstream researcher who cited the old value cannot reproduce their citation |
| Re-fetch from the source and re-parse | **Not a replay at all** — the source may have changed or vanished; you've conflated a parser improvement with a source change |

#### 3.6.2 The design

**Replay operates on snapshots, never on the network.** This is enforced by the interface: `parse()` takes a `Snapshot` + bytes, not a URL (§1.2). A replay run therefore *cannot* hit the network, by construction.

Claim identity (see §3.7) is:

```
claim_id = ULID   -- opaque, never reused
claim_key = hash(
    subject_entity_id_or_hint,
    predicate,
    object_value_normalized,
    observation_time,          -- from the SOURCE, not from the run
    snapshot_sha256,           -- WHICH evidence
    extractor_id, extractor_version,
    normalizer_version
)
```

Because `extractor_version` and `normalizer_version` are inside `claim_key`, **a replay with an improved parser produces a different `claim_key`, and therefore a genuinely new claim row.** A replay with the *same* versions produces an identical `claim_key` and is a no-op insert — which is the idempotency guarantee, and also the determinism test (§3.6 of Part C).

**The bitemporal interaction — the part that is easy to get wrong:**

SIG's claim carries (at minimum, per the outline's §9.2 and §8.16):

- `valid_from` / `valid_to` — **validity time**: when the asserted fact was true in the world.
- `observation_time` — when the *source* asserted it.
- `recorded_at` / `superseded_at` — **transaction time**: when SIG came to hold this record.

The rule for replay:

> **A replay MUST preserve `observation_time` and `valid_from`/`valid_to` from the source, and MUST set `recorded_at = now()` for the new claims. It must never backdate `recorded_at`.**

This is the whole trick. The new claims say "the portal asserted X as of 2025-06-14 (unchanged), and SIG came to understand that on 2026-08-20 (new)." A query with `as_of=2026-01-01` still returns the *old* interpretation, because the new claim's `recorded_at` is in that query's future. A query with `as_of=now` returns the new one. **The as-of API (§5.5) is therefore correct by construction over replays** — SIG's answer to "what did you believe then" survives every parser improvement, which is exactly the reproducibility promise.

**Supersession, not deletion.** When a replay produces a claim that the *same extractor lineage* now considers a correction of a prior claim, the prior claim gets `superseded_by = new_claim_id` and `superseded_at = now()`. It is never deleted and never edited. Three supersession reasons, recorded explicitly:

- `parser_improved` — the new extractor reads the same bytes better.
- `normalization_revised` — the vocabulary mapping changed (e.g. reason-code taxonomy v7 → v8).
- `human_correction` — a reviewer overrode it.

A fourth case is **not** supersession: `source_changed`. If the source itself changed, that is a new observation of a new snapshot, and both claims stand as true statements about different moments. Conflating these two is the most common modelling error and would silently erase the "portal changed its retention period" signal that is a core SIG deliverable.

#### 3.6.3 Replay job types

```bash
# 1. Re-parse: new parser over archived snapshots, no re-fetch, no network
uv run sig-replay parse \
    --connector flock_portal --parser-version 7.0.0 \
    --snapshots-from 2025-01-01 --snapshots-to 2026-08-01 \
    --dry-run                    # prints claim delta counts, writes nothing

# 2. Re-normalize: new vocabulary mapping over existing raw claims (cheap; no re-parse)
uv run sig-replay normalize \
    --predicate search_reason --normalizer-version reason_codes_v8

# 3. Re-link: entity resolution improved; relink existing normalized claims
uv run sig-replay link --since 2025-01-01 --emit-review-tasks

# 4. Backfill: fetch a historical window from a source that supports it
uv run sig-backfill fetch --connector osm_replication --from-seq 6120000 --to-seq 6180000
```

Each writes an `ingest_run` row with `trigger='replay'|'backfill'` and `replay_of_run_id` pointing at the original where meaningful. Each is a Dagster partitioned backfill in normal operation and a plain CLI invocation in degraded mode.

**`--dry-run` is mandatory on every replay.** A replay that changes 400,000 claims is a fact an operator must see *before* it happens. The dry-run report shows: claims created, claims superseded (by reason), review tasks created, and — most importantly — a **sample of 20 diffs** rendered side by side with source spans. This is a review gate, not a progress bar.

#### 3.6.4 Storage cost of never deleting

Because replays append rather than overwrite, claim volume grows with (sources × time × parser generations). This is affordable and the arithmetic should be in the spec so nobody panics later: a claim row with lineage is ~1 KB in Postgres including indexes. Ten million claims across all parser generations is ~10 GB. At Neon's $0.35/GB-month (F11.30) that is $3.50/month; on self-hosted Postgres it is free. **The cost of full replay history is negligible; the cost of not having it is the project's credibility.**

### 3.7 Claim identity and idempotency of `load()`

```python
def claim_key(c: LinkedClaim, lineage: ClaimLineage) -> str:
    payload = canonical_json({
        "subject": c.subject_entity_id or stable_hint_hash(c.subject_hint),
        "predicate": c.predicate,
        "object": canonical_value(c.object_value, c.object_unit, c.vocabulary_id),
        "observation_time": c.observation_time.astimezone(timezone.utc).isoformat(),
        "evidence": lineage.snapshot_sha256,
        "extractor": f"{lineage.extractor_id}@{lineage.extractor_version}",
        "normalizer": lineage.normalizer_version,
    })
    return hashlib.sha256(payload.encode()).hexdigest()
```

`load()` is `INSERT ... ON CONFLICT (claim_key) DO NOTHING`, returning whether a row was created. That single line gives: idempotent re-runs, safe retries after a partial failure, and a free determinism check (re-running yesterday's job must create zero claims).

**Deliberate exclusion:** `run_id` is *not* in the key. Two runs that legitimately produce the same claim from the same evidence must collapse to one claim with two observations, not two claims. The `run_id` lives in `claim_lineage` for the *first* run that produced it, plus a `claim_reobservation` table if SIG wants the full "we saw this again" series (recommended, cheap).


---

## PART C — DATA QUALITY AND TESTING

## 4. Data-quality framework

### 4.1 Recommendation

**Recommend a three-part stack, not a single framework:**

1. **Pandera (0.32.1, MIT)** for in-pipeline schema and dataframe validation — typed `DataFrameModel` classes that live next to the connector, run on every batch, and fail the asset. Chosen over Great Expectations because it is (a) MIT vs Apache (irrelevant) but critically (b) *code-first with no separate metadata store to operate*, (c) not bound by GX's `<3.14` Python ceiling (F11.21) which would constrain the whole repo, and (d) trivially unit-testable — a Pandera schema is a class, so it is tested by the same pytest run as everything else.
2. **A custom SQL invariant suite executed by pytest** for everything that is a *relational or temporal* invariant. This is the majority of SIG's real checks (§4.2), and none of the frameworks express them well: "no two mutually-exclusive `ConfigurationState` claims overlap in validity time for the same deployment" is a SQL window query, not a column expectation. Writing these as `.sql` files with expected-zero-rows semantics — the dbt singular-test pattern (F11.27) — without adopting dbt is the minimum-machinery answer.
3. **Pointblank (0.27.0, MIT)** for the **public-facing** data-quality report. Pointblank's differentiator is that it renders interactive HTML validation reports and supports YAML-configured, version-controlled validation plans across DuckDB/Parquet/Postgres (F11.21). SIG's quality report is a *trust affordance* aimed at outside researchers, not an internal dashboard — an attractive, linkable, per-release quality report published alongside the data is worth real credibility. Run it against the released Parquet/DuckDB artifacts, not against the live database.

**Explicitly rejected:**

- **Soda Core — eliminated on license (F11.20, Elastic License 2.0).** This is the single most important negative finding in Part C.
- **Great Expectations as the primary gate** — viable and Apache-2.0 (F11.21), but the operational surface (Data Context, stores, checkpoints) is disproportionate for a 3-person team, and its `<3.14` Python bound is a real constraint. Reconsider only if SIG grows a dedicated data-quality owner.
- **dbt tests as the framework** — dbt-core is Apache-2.0 and its test model is genuinely good (F11.27), but adopting dbt means adopting dbt's whole transformation paradigm for a pipeline that is not SQL-transformation-shaped. **Borrow the pattern, not the tool.**

### F11.27 — dbt's data-test model is the right *pattern* to imitate

**Claim:** dbt supports singular data tests (one-off `.sql` files in `tests/`, each a `select` returning failing records, passing when zero rows return) and generic data tests (parameterized Jinja macros applied via YAML), ships four built-in generic tests — `unique`, `not_null`, `accepted_values`, `relationships` — and configures thresholds via `severity` (`warn`/`error`) and `error_if`/`warn_if` expressions such as `">10"`.
**Status:** VERIFIED
**Evidence:** https://docs.getdbt.com/docs/build/data-tests — singular vs generic tests, the `tests/` directory convention, the zero-rows-pass semantics, the four built-ins with YAML examples, and the `severity` / `error_if` / `warn_if` configuration.
**Retrieved:** 2026-08-20
**Implication for the spec:** SIG adopts (a) the **zero-rows-pass** convention for every SQL invariant, (b) the **severity/threshold** split so that a check can warn at >0 and fail at >N — essential, because SIG will always have some legitimately-contradictory claims and a check that fails on the first contradiction would be disabled within a week, and (c) the **four built-in categories** as the floor of the taxonomy in §4.2.
**Outline delta:** EXTENDS §6.5 ("contradiction as a first-class state") with the operational consequence: **a contradiction must not be a test failure.** Contradictions are the product. The test asserts on *unexplained* contradictions and on *rate of change* of contradictions, never on their existence.

### 4.2 The test taxonomy — the concrete list

Each entry: id, what it asserts, severity, cadence, and where it runs. `PR` = every pull request against fixtures; `RUN` = every ingest run against the batch; `NIGHTLY` = full-database sweep; `RELEASE` = blocks artifact publication.

**Schema tests (Pandera + LinkML)**

| Id | Assertion | Sev | When |
|---|---|---|---|
| T-SCH-1 | Every ingested row conforms to its connector's Pandera `DataFrameModel` (types, nullability, ranges) | error | RUN |
| T-SCH-2 | Every emitted claim validates against the LinkML-generated Pydantic model for its predicate | error | RUN |
| T-SCH-3 | The LinkML source schema compiles and its generated artifacts are byte-identical to the committed ones (no drift) | error | PR |
| T-SCH-4 | Every `RawClaim` carries ≥1 `SourceSpan` with a non-empty locator | error | RUN |
| T-SCH-5 | Every claim row has non-null `run_id`, `connector_version`, `parser_version`, `snapshot_sha256` | error | RUN |
| T-SCH-6 | No claim's `source_spans` locator fails to resolve against its `parsed_doc.canonical_json` (spans are checkable, not decorative) | warn>0, error>1% | NIGHTLY |

**Referential integrity**

| Id | Assertion | Sev | When |
|---|---|---|---|
| T-REF-1 | Every `claim.snapshot_sha256` exists in `snapshot` and the blob is retrievable from object storage (HEAD 200) | error | NIGHTLY |
| T-REF-2 | Every `claim_lineage.extraction_id` resolves; every `extraction.parsed_doc_sha` resolves | error | RUN |
| T-REF-3 | Every claim with a non-null `subject_entity_id` points at a live (non-merged-away) entity, or at a merge target | error | NIGHTLY |
| T-REF-4 | Every `EvidenceArtifact` referenced by a claim has either a stored snapshot or an explicit `link_only` flag with a reason | error | NIGHTLY |
| T-REF-5 | No orphan claims: every claim is reachable from at least one entity **or** is explicitly flagged `unlinked_pending_review` | warn | NIGHTLY |
| T-REF-6 | Every `review_task` in `open` state older than 90 days is surfaced (queue rot detector) | warn | NIGHTLY |

**Temporal-consistency invariants** — the ones the outline's §9.2/§19.3 make mandatory

| Id | Assertion | Sev | When |
|---|---|---|---|
| T-TIME-1 | No claim has `valid_to < valid_from` | error | RUN |
| T-TIME-2 | No claim has `observation_time > recorded_at + 1 day` (a source cannot have asserted something meaningfully after we recorded it) | error | RUN |
| T-TIME-3 | No claim has `observation_time` before the earliest plausible epoch for its source (e.g. a Flock portal observation dated 1999) | error | RUN |
| T-TIME-4 | No claim has `observation_time` in the future beyond clock skew (>1 h) | error | RUN |
| T-TIME-5 | For any (deployment, mutually-exclusive-state-predicate), no two non-superseded claims have overlapping `[valid_from, valid_to)` with different values | warn>0, error>threshold | NIGHTLY |
| T-TIME-6 | No claim has `recorded_at < superseded_at` violated (supersession is monotone) | error | RUN |
| T-TIME-7 | Bitemporal round-trip: for a random sample of 1,000 claims, `as_of(recorded_at + ε)` returns the claim and `as_of(recorded_at - ε)` does not | error | NIGHTLY |
| T-TIME-8 | A replay run did not change any `observation_time` or `valid_from` for any pre-existing claim (§3.6.2's central rule, mechanized) | error | RUN (replay only) |

**Vocabulary conformance**

| Id | Assertion | Sev | When |
|---|---|---|---|
| T-VOC-1 | Every `vocabulary_id` on a normalized claim exists in the ontology at the claim's `ontology_version` | error | RUN |
| T-VOC-2 | No normalized claim uses a vocabulary term marked `deprecated` without a `superseded_by` mapping | warn | NIGHTLY |
| T-VOC-3 | Free-text reason codes: the share mapped to `other`/`unmapped` does not exceed its historical baseline by >5 pp (catches a taxonomy drifting out from under us) | warn | NIGHTLY |
| T-VOC-4 | Every Atlas `Technology` value maps to a SIG technology term, or is explicitly listed in `unmapped_atlas_technologies.yaml` with a note | error | RUN |

**Geospatial sanity — the highest-value novel check**

| Id | Assertion | Sev | When |
|---|---|---|---|
| **T-GEO-1** | **Every asset with a point geometry and a claimed jurisdiction falls inside (or within a configured buffer of) that jurisdiction's boundary polygon** | **warn>0, error>1%** | **NIGHTLY** |
| T-GEO-2 | No point at (0,0) or with lat/lon transposed (|lat|>90) | error | RUN |
| T-GEO-3 | No point outside the connector's declared geographic scope (a US-only source emitting a point in Belgium is a parse bug) | error | RUN |
| T-GEO-4 | Coordinate precision does not exceed the source's plausible precision (a portal that reports city-level location must not yield 7-decimal coordinates — false precision, §19.4) | warn | RUN |
| T-GEO-5 | Cluster-density anomaly: >N assets within a 10 m radius attributed to different agencies (usually a geocoding fallback to a centroid) | warn | NIGHTLY |
| T-GEO-6 | Geometry validity (`ST_IsValid`) on every polygon; SRID is 4326 everywhere at the boundary, projected CRS only inside analysis | error | RUN |

T-GEO-1 deserves its emphasis. The outline nowhere proposes it, and it is (a) cheap — one PostGIS `ST_Contains` per asset, (b) catches the two most common real-world errors in this domain simultaneously (bad geocoding, and a device attributed to the wrong agency), and (c) produces *research leads* rather than just failures: a camera physically inside City A operated by City B's police department is not necessarily an error — it may be the most interesting fact in the dataset (§6.6 of the outline, "network topology across vendors", and the mutual-aid/shared-infrastructure pattern). So T-GEO-1's failure output is a **review queue of jurisdictional anomalies**, not a build break.

**Count-plausibility**

| Id | Assertion | Sev | When |
|---|---|---|---|
| T-PLAUS-1 | A numeric metric (camera count, search count) changing by >X% or crossing to/from zero raises a review task and **holds the derived projection** at its prior value pending review | warn (never error) | RUN |
| T-PLAUS-2 | Batch row count within ±3σ of the trailing 30-run mean for that connector | warn | RUN |
| T-PLAUS-3 | Zero-row batch from a source that has never previously returned zero → error (distinguishes "source is empty" from "our parser broke") | error | RUN |
| T-PLAUS-4 | Claim-emission rate per snapshot within ±3σ of trailing baseline (catches a parser that silently started emitting 1 claim instead of 40) | error | RUN |
| T-PLAUS-5 | Aggregate: total distinct organizations does not *decrease* between releases without an explicit merge event to explain it | error | RELEASE |

T-PLAUS-1 is the outline's explicit example ("a portal reporting 0 cameras after reporting 300 is an alert, not a silent overwrite"). Note the deliberate design: **the claim is still written** (§19.3 forbids dropping it) and the *projection* is held. Refusing to write the claim would be the wrong fix, because if the portal really does now say 0, that is the fact.

**Duplicate detection**

| Id | Assertion | Sev | When |
|---|---|---|---|
| T-DUP-1 | No two claims share a `claim_key` (enforced by the unique index; the test asserts the index exists) | error | PR |
| T-DUP-2 | No two entities share a deterministic identifier (ORI, OSM id, portal slug, FIPS) | error | NIGHTLY |
| T-DUP-3 | Near-duplicate entities: pairs above the blocking threshold that are neither merged nor explicitly marked `distinct_confirmed` | warn | NIGHTLY |
| T-DUP-4 | No two `snapshot` rows share a `storage_uri` with different `sha256` (storage corruption detector) | error | NIGHTLY |

**License compatibility on export** — a gate, not a report

| Id | Assertion | Sev | When |
|---|---|---|---|
| **T-LIC-1** | Every row in every export artifact traces to ≥1 source whose `source_license_id` permits redistribution under that artifact's declared license; `UNDETERMINED` fails closed | **error — blocks release** | RELEASE |
| T-LIC-2 | OSM-derived rows appear **only** in resources whose Data Package `licenses` array declares ODbL (F11.10); no OSM-derived column appears in a non-ODbL resource | error | RELEASE |
| T-LIC-3 | Every source in the license registry has a `license_evidence_url` and a `terms_verified_at` date; anything unverified for >365 days warns | warn | RELEASE |
| T-LIC-4 | Every artifact carries per-resource attribution strings required by its sources | error | RELEASE |

T-LIC-1's fail-closed behavior is what turns F11.8 (Atlas license undetermined) from a footnote into an enforced constraint.

**Privacy/safety gates** (R8 owns policy; R11 owns the mechanism)

| Id | Assertion | Sev | When |
|---|---|---|---|
| T-PRIV-1 | No export artifact contains a value matching the plate-number detector, the SSN/DL detector, or the personal-email detector | error — blocks release | RELEASE |
| T-PRIV-2 | No claim marked `sensitive_private` appears in a public artifact; only its metadata does (§20 Q31) | error | RELEASE |
| T-PRIV-3 | Coordinate fuzzing applied to any asset class flagged for it (§13.3) before export | error | RELEASE |
| T-PRIV-4 | Every takedown-flagged item is absent from all artifacts built after the flag timestamp | error | RELEASE |

### 4.3 Golden / fixture testing for parsers

**Every parser has committed fixtures. No exceptions. A parser without fixtures cannot be merged.**

Layout:

```
tests/fixtures/
  flock_portal/
    green-brook-twp-nj-pd/
      2025-11-03T12-00Z/
        snapshot.html                 # real captured bytes, verbatim
        snapshot.meta.json            # sha256, media_type, captured_at, source_url, http headers
        expected.parsed.json          # canonical_json for parser_version 6.2.0
        expected.claims.json          # extracted RawClaims incl. source spans
        NOTES.md                      # why this fixture exists; what edge case it pins
      2026-02-17T12-00Z/              # a redesign; pins the migration
        ...
    _schema/
      portal.pandera.py               # the DataFrameModel this connector must satisfy
  muckrock/
    request_9182/
      response.json
      ...
  atlas_csv/
    2026-08-20/
      head-5000.csv                   # truncated for repo size; full file hash recorded
      expected.claims.json
  pdf_contracts/
    city_of_x_flock_2024/
      contract.pdf
      expected.parsed.json
      expected.claims.json
```

Rules:

1. **Fixtures are real captured bytes**, never hand-written. A hand-written fixture tests the developer's imagination.
2. **Fixture files are redacted before commit** by the same privacy gate as exports (T-PRIV-1). A FOIA PDF fixture containing plate numbers gets a redacted variant committed and the original stored privately, referenced by hash. `NOTES.md` records that this happened.
3. **Repo size discipline:** binary fixtures >1 MB go to a `fixtures` bucket in R2 addressed by sha256 and are pulled by `uv run sig-fixtures sync`; only the hash and metadata are committed. HTML/JSON/CSV under 1 MB commits directly (git handles text well).
4. **Expected outputs are generated, then reviewed.** `uv run sig-fixtures bless <path>` regenerates `expected.*` and shows a diff; a human approves it in the PR. This makes an intentional parser change a *visible, reviewable diff of the extracted meaning*, which is the whole point.
5. **A site redesign fails a test.** When Flock changes its portal markup, the old fixture still parses (bytes are immutable), so the *old* test keeps passing — which is correct, and is why fixtures alone are insufficient. Hence:

**The canary test — detecting upstream drift.**

Fixtures pin *known* inputs. Drift detection catches *unknown* ones. Both are needed.

```python
# tests/canary/test_upstream_drift.py — runs NIGHTLY, never in PR CI (it uses the network)

CANARY_TARGETS = [                    # small, stable, deliberately chosen
    ("flock_portal", "green-brook-twp-nj-pd"),
    ("flock_portal", "hagerstown-md-pd"),
    ("atlas_csv",    "download.csv"),
    ("muckrock",     "agencies?page_size=1"),
]

@pytest.mark.canary
@pytest.mark.parametrize("connector_id,ref", CANARY_TARGETS)
def test_live_source_still_parses(connector_id, ref):
    conn = registry.get(connector_id)
    fetched = gateway.get_sync(make_ref(conn, ref), connector_id=connector_id)
    assert not isinstance(fetched, Unavailable), f"canary unreachable: {fetched}"

    snap = conn.capture(fetched, ctx=canary_ctx())
    doc  = conn.parse(snap, fetched.body)
    claims = list(conn.extract(doc))

    # 1. STRUCTURAL: the shape we depend on is still present
    assert_shape_matches(doc.canonical_json, expected_shape(connector_id))

    # 2. YIELD: we still get roughly the number of claims we used to
    baseline = load_baseline(connector_id, ref)          # trailing 30-day median
    assert 0.5 * baseline.claim_count <= len(claims) <= 2.0 * baseline.claim_count

    # 3. NON-EMPTY REQUIRED FIELDS: the fields we actually publish are populated
    for predicate in REQUIRED_PREDICATES[connector_id]:
        assert any(c.predicate == predicate for c in claims), \
            f"required predicate {predicate} vanished — likely upstream redesign"

    # 4. WARNING FLOOR: parser warnings did not spike
    assert len(doc.parse_warnings) <= baseline.warn_count + 3

    # 5. On any failure: auto-capture the snapshot as a CANDIDATE FIXTURE and open an issue
```

Failure of a canary opens a GitHub issue with the newly-captured snapshot attached as a candidate fixture — so the response to "Flock redesigned their portal" is a PR with the new fixture already in it, rather than a week of silent garbage. **Silent garbage is the specific failure mode the outline's §19 principles exist to prevent, and the canary is the only mechanism that catches it early.**

Canaries must be *few* (4–8 targets), *small*, and *politely fetched* through the same gateway — they are a nightly, not a monitor.

### 4.4 Entity-resolution regression testing

R7 owns matching. R11 owns the **gate**.

```
tests/gold/entity_resolution/
  agencies_gold_v3.jsonl        # {"left": {...}, "right": {...}, "label": "match"|"non_match"|"ambiguous"}
  agencies_gold_v3.meta.yaml    # who labeled, when, inter-annotator agreement, sampling method
  orgs_private_gold_v1.jsonl    # private orgs in Flock networks (Q12) — the hard case
  osm_to_deployment_gold_v2.jsonl
```

CI gate on every PR touching `resolution/`:

```python
def test_er_precision_recall_gates():
    gold = load_gold("agencies_gold_v3.jsonl")
    pred = [resolver.decide(p.left, p.right) for p in gold]
    m = score(gold, pred, ignore_labels={"ambiguous"})

    # Precision is the hard gate: a bad merge corrupts every downstream statistic (§19.6)
    assert m.precision >= 0.98, f"ER precision regressed to {m.precision:.4f}"
    # Recall is a softer gate: a missed match becomes a review task, which is recoverable
    assert m.recall    >= 0.85, f"ER recall regressed to {m.recall:.4f}"
    # Auto-merge rate: how much is decided without a human
    assert m.auto_rate <= 0.80, "auto-merge rate too high — review queue is being bypassed"

    write_metrics_artifact(m)     # posted as a PR comment for reviewers to see the delta
```

Design notes that matter:

- **Asymmetric thresholds are deliberate.** §19.6: "Bad entity resolution makes every network statistic misleading." A false merge is far more damaging than a missed one, because a missed match surfaces as a review task while a false merge silently invents a relationship. Precision 0.98 / recall 0.85 encodes that asymmetry.
- **The `ambiguous` label is required in the gold set** and excluded from scoring. A gold set that forces binary labels on genuinely ambiguous pairs teaches the resolver to be overconfident — and "ambiguous" is exactly the class that must route to review (Q28).
- **Gold set versioning:** `_v3` in the filename, never edited in place. Adding examples creates `_v4` and the thresholds are re-baselined in the same PR, with the baseline change called out in the description. Silently editing a gold set to make CI pass is the most common way ER quality dies.
- **Nightly extended run** over a 10× larger unlabeled sample computes *stability* metrics (how many decisions flipped vs. yesterday), which catches non-determinism in the matcher.

### 4.5 Python testing stack and CI

| Tool | Version verified | License | Role |
|---|---|---|---|
| pytest | 9.1.1 (F11.28) | MIT | test runner |
| Hypothesis | 6.165.10 (F11.28) | MPL-2.0 | property tests on temporal logic |
| Pandera | 0.32.1 (F11.21) | MIT | dataframe/schema validation |
| Pointblank | 0.27.0 (F11.21) | MIT | published quality report |
| Ruff | 0.16.3 (F11.29) | MIT | lint + format |
| Playwright | 1.62.0 (F11.16) | Apache-2.0 | browser connectors + their tests |
| GitHub Actions | — (F11.13) | — | CI + degraded-mode scheduler |

### F11.28 — pytest and Hypothesis current versions and licenses

**Claim:** `pytest` 9.1.1, MIT, requires Python >=3.10, with a 1300+ plugin ecosystem. `hypothesis` 6.165.10, **MPL-2.0**, requires Python >=3.10, "The property-based testing library for Python."
**Status:** VERIFIED
**Evidence:** https://pypi.org/pypi/pytest/json; https://pypi.org/pypi/hypothesis/json.
**Retrieved:** 2026-08-20
**Implication for the spec:** Both adopted. **Note the MPL-2.0 on Hypothesis** — it is a file-level copyleft, which is fine for a test-only dependency but should be recorded in the dependency-license inventory so nobody vendors Hypothesis source into shipped code.
**Outline delta:** N/A.

### F11.29 — Ruff replaces the flake8/black/isort stack

**Claim:** `ruff` 0.16.3, MIT, "An extremely fast Python linter and code formatter, written in Rust", 900+ built-in lint rules with native reimplementations of popular flake8 plugins, drop-in compatible with flake8/isort/Black, supports Python 3.7–3.14, monorepo-friendly configuration, by Astral.
**Status:** VERIFIED
**Evidence:** https://pypi.org/pypi/ruff/json.
**Retrieved:** 2026-08-20
**Implication for the spec:** One tool, one config block in the root `pyproject.toml`, monorepo-aware — which matters given §5.2's workspace layout. Enable at minimum: `E,F,W,I` (pycodestyle/pyflakes/isort), `B` (bugbear), `DTZ` (**flake8-datetimez — bans naive `datetime.now()`, which is a correctness rule for SIG, not a style rule**), `ASYNC`, `S` (bandit subset), `PTH`, `RUF`.
**Outline delta:** N/A.

**Property tests with Hypothesis — where they earn their keep.** The temporal logic is the only part of SIG where property testing is clearly worth the cost, because the invariants are algebraic and the bug class (interval edge cases) is exactly what example-based tests miss:

```python
@given(claims=st.lists(bitemporal_claims(), min_size=1, max_size=50),
       t=st.datetimes(timezones=st.just(timezone.utc)))
def test_as_of_is_a_consistent_snapshot(claims, t):
    view = as_of(claims, t)
    # 1. every returned claim was recorded at or before t and not yet superseded at t
    assert all(c.recorded_at <= t and (c.superseded_at is None or c.superseded_at > t) for c in view)
    # 2. no two claims in the view assert conflicting values for the same
    #    (subject, mutually-exclusive predicate) over overlapping validity
    assert no_overlapping_conflicts(view)
    # 3. monotonicity: as_of is stable under replay — adding a claim with
    #    recorded_at > t does not change the view at t
    later = claims + [make_claim(recorded_at=t + timedelta(days=1))]
    assert as_of(later, t) == view
```

Property 3 is the mechanized form of §3.6.2's central replay rule and is worth writing first.

**CI split — what runs when:**

| Job | Trigger | Contents | Budget |
|---|---|---|---|
| `pr-fast` | every PR | ruff check+format, mypy/pyright on changed packages, unit tests, **all parser golden-fixture tests**, schema-drift check (T-SCH-3), ER gate (T-ER), migration up/down against ephemeral PG+PostGIS, Hypothesis at default examples | target <6 min |
| `pr-full` | PR label `full-ci`, and on merge to `main` | everything above + full Hypothesis profile (1000 examples) + integration tests against a seeded PG + Playwright fixture-replay tests | <25 min |
| `nightly-canary` | cron `17 6 * * *` | canary tests against live sources (§4.3), politeness-budget audit, dependency `uv lock --check` | <10 min |
| `nightly-quality` | cron `41 7 * * *` | full-database invariant sweep (all NIGHTLY-tagged tests), Pointblank report generation, freshness dashboard rebuild | <30 min |
| `release` | tag `v*` | RELEASE-tagged gates (T-LIC-*, T-PRIV-*, T-PLAUS-5), artifact build, checksum + manifest, R2 upload, Zenodo deposition | <45 min |

**Never in `pr-fast`: anything that touches the network.** Enforced by a `conftest.py` autouse fixture that patches `socket.socket` to raise unless the test is marked `@pytest.mark.network`, and by a CI check that fails if a non-canary test carries that mark.

---

## PART D — RUNTIME, LANGUAGE, AND REPO ARCHITECTURE

## 5. Language, dependencies, repo layout, reproducibility

### 5.1 Language recommendation

**Python is the primary language.** The argument is not "Python is the data language" — it is four specific things:

1. **The dependency graph SIG needs is Python's.** pyosmium (F11.2), Pandera, LinkML (F11.31), the Anthropic SDK, Playwright's Python bindings, psycopg/SQLAlchemy/Alembic, PyArrow, DuckDB, Datasette. Reimplementing any one of these elsewhere costs more than the entire orchestration decision.
2. **The contributor pool is Python's.** SIG's §3 thesis is that local research groups are infrastructure. The realistic contributor writing a parser for their city's agenda system knows Python or nothing.
3. **Typed Python is now adequate for the claim model.** `dataclass(frozen=True, slots=True)` + Pydantic v2 (2.13.4, F11.32) + LinkML-generated models gives SIG a checked ontology-to-code path.
4. **The escape hatch works in Python.** §3.3's requirement that everything be runnable as a CLI is cheap in Python and awkward in a compiled orchestrated system.

**Where other languages earn a place — and only these places:**

| Language | Where | Justification |
|---|---|---|
| **TypeScript** | `web/` — the entire frontend | Map/graph/dossier UIs. Non-negotiable; there is no Python frontend story worth having. |
| **Go/Rust — as prebuilt binaries, not as SIG source** | `tippecanoe` (C++, F11.11), `go-pmtiles` (Go), `osmium-tool` (C++) | Invoked as subprocesses from `exports/`. SIG writes no Go or Rust. |
| **Rust — conditional, future** | OSM PBF processing *if* pyosmium becomes a bottleneck | **Do not pre-emptively write this.** pyosmium wraps libosmium (C++); it is already fast. Revisit only with a profile showing PBF processing is >30% of pipeline wall-clock. Adding a second compiled language to a volunteer project is a real tax. |
| **SQL** | `db/` migrations, all invariant tests (§4.2), analytical views | First-class, not an implementation detail. The temporal invariants are more readable and faster in SQL than in Python. |

### F11.30 — Python 3.13 is the right target; 3.14 is available but not required

**Claim:** Python 3.10 (security-only until Oct 2026), 3.11 (security-only until Oct 2027), 3.12 (bugfix until Oct 2028), 3.13 (bugfix until Oct 2029), 3.14 (bugfix until Oct 2030) are supported; 3.14 is the most recent stable branch, in bugfix mode; 3.9 reached EOL 2025-10-31.
**Status:** VERIFIED
**Evidence:** https://devguide.python.org/versions/ — the support table and EOL dates above.
**Retrieved:** 2026-08-20
**Implication for the spec:** **Target Python 3.13.** Rationale: (a) 3.10 goes security-only in ~2 months, so it is not a viable floor for a project starting now; (b) Dagster supports `<3.15` i.e. through 3.14 (F11.17), Pandera/Pointblank/Protego/pytest/Hypothesis all require ≥3.10, and Great Expectations caps at `<3.14` (F11.21) — so 3.13 is the highest version compatible with *everything* including GX, keeping that option open; (c) 3.13 has bugfix support until Oct 2029, comfortably longer than the project's first planning horizon. Declare `requires-python = ">=3.13,<3.15"` and test on 3.13 and 3.14 in CI.
**Outline delta:** N/A.

### 5.2 Repo layout: monorepo

**Monorepo, uv workspace.** Polyrepo is wrong here for one decisive reason: **the ontology changes together with the connectors, the migrations, the exports, and the API.** A LinkML term rename touches `ontology/`, `db/`, `connectors/`, `api/`, and `exports/` in one logical change. In a polyrepo that is a five-PR coordinated release with a version-skew window; in a monorepo it is one PR that CI validates atomically (T-SCH-3). For a small team, the coordination cost of polyrepo is not affordable.

```
sig/
├── pyproject.toml                # uv workspace root; ruff/pytest/mypy config; requires-python
├── uv.lock                       # COMMITTED. the reproducibility anchor.
├── pylock.toml                   # PEP 751 export, regenerated on release (F11.33)
├── README.md
├── LICENSE                       # code license (see §14 — R2 owns; likely Apache-2.0 or AGPL)
├── DATA-LICENSE.md               # data license(s) and the ODbL separation statement
├── CONTRIBUTING.md
├── AGENTS.md                     # conventions for AI-assisted contributions (see §7.6)
│
├── ontology/                     # SCHEMA IS THE SOURCE OF TRUTH
│   ├── src/sig/                  # LinkML YAML: entities, predicates, vocabularies, enums
│   │   ├── core.yaml             # Organization, Vendor, Product, Technology, Deployment...
│   │   ├── evidence.yaml         # EvidenceArtifact, Claim, SourceSpan, Confidence
│   │   ├── temporal.yaml         # bitemporal mixins
│   │   ├── vocab/                # controlled vocabularies incl. Atlas mappings, reason codes
│   │   └── profiles/             # per-source shape profiles (Atlas, Flock portal, OSM)
│   ├── generated/                # CHECKED IN, never hand-edited; drift is a CI failure
│   │   ├── pydantic/             # runtime validation models
│   │   ├── sqlddl/               # reference DDL (informational; db/ owns real migrations)
│   │   ├── jsonschema/           # for export validation + external consumers
│   │   ├── shacl/                # for the RDF export
│   │   └── docs/                 # generated ontology docs published on the site
│   └── tests/
│
├── db/
│   ├── migrations/               # Alembic; every migration reversible or explicitly marked one-way
│   ├── sql/                      # views, functions, the as-of query implementation
│   ├── invariants/               # the SQL test suite (§4.2) — one .sql per check, zero-rows-pass
│   └── seeds/                    # jurisdictions, FIPS, ORI reference, vocab bootstrap
│
├── packages/
│   ├── sig-core/                 # value types, claim identity, bitemporal algebra, IDs (ULID)
│   ├── sig-store/                # repository layer over PG/PostGIS; the ONLY module with SQL for writes
│   ├── sig-capture/              # PolitenessGateway, snapshot store, content addressing
│   ├── sig-parse/                # parser framework + shared PDF/HTML/CSV/XLSX/ZIP handling (R4 owns internals)
│   ├── sig-extract/              # extraction framework incl. the LLM adapter and its guardrails (§7)
│   ├── sig-resolution/           # entity resolution (R7 owns algorithms; this is the package)
│   ├── sig-reconcile/            # cross-source reconciliation + contradiction detection (§11 of outline)
│   ├── sig-review/               # review queue: task model, assignment, sampling, adjudication
│   ├── sig-export/               # Parquet/CSV/JSONL/GeoJSON/PMTiles/RDF/SQLite builders + manifest
│   └── sig-quality/              # Pandera schemas, invariant runner, Pointblank report builder
│
├── connectors/                   # ONE PACKAGE PER SOURCE. all implement Connector (§1.3)
│   ├── _registry.py
│   ├── atlas_csv/
│   ├── osm_replication/
│   ├── osm_extract/
│   ├── overpass_probe/
│   ├── flock_portal/
│   ├── flock_portal_browser/
│   ├── muckrock/
│   ├── documentcloud/
│   ├── usaspending/
│   ├── legistar_rss/
│   ├── agenda_generic_rss/
│   ├── manual_upload/
│   └── partner_eyesonflock/      # stub until §17 Stage 0 collaboration lands
│
├── api/                          # FastAPI app; read-only; as-of semantics (§5.5)
│   ├── routers/
│   ├── schemas/                  # response models generated from ontology/generated/pydantic
│   └── openapi/                  # committed OpenAPI snapshot; diff is reviewed in PRs
│
├── web/                          # TypeScript frontend (separate toolchain, same repo)
│
├── exports/                      # artifact builders + release orchestration + Zenodo deposition
│
├── orchestration/                # THE ONLY PLACE `import dagster` APPEARS
│   ├── definitions.py
│   ├── assets/
│   ├── partitions.py
│   ├── sensors/
│   └── schedules.py
│
├── ops/
│   ├── politeness.toml           # per-host + per-path budgets (§1.7) — reviewed by R8
│   ├── licenses.yaml             # source license registry; drives T-LIC-*
│   ├── privacy_rules.yaml        # detectors and redaction rules; drives T-PRIV-*
│   ├── freshness.yaml            # expected cadence per source; drives the public dashboard
│   ├── terraform/ | pulumi/      # R2 buckets, DNS, CDN rules
│   ├── docker/
│   └── runbooks/
│
├── docs/                         # this research cache, the spec, ADRs, methodology
│   ├── research/
│   ├── adr/
│   └── methodology/              # PUBLIC: how SIG decides things. a trust artifact.
│
├── tests/
│   ├── unit/ integration/ property/ canary/ gold/
│   └── conftest.py               # network-blocking autouse fixture
│
└── fixtures/                     # small fixtures inline; large ones by sha256 pointer
```

Boundary rules enforced by an import-linter check in `pr-fast`:

- `connectors/*` may import `sig-core`, `sig-capture`, `sig-parse`, `sig-extract` — **never** `sig-store`, `api`, `orchestration`, or another connector.
- Only `sig-store` writes SQL that mutates. Everything else goes through its repository interface.
- Only `orchestration/` imports `dagster`.
- Only `sig-extract`'s LLM adapter imports `anthropic`. One chokepoint means one place to enforce §7.

### F11.31 — LinkML is production-ready as the schema source of truth

**Claim:** `linkml` 1.11.1, Apache-2.0, requires Python >=3.10, "a linked data modeling language following object-oriented and ontological principles"; models are authored in YAML and converted to other schema formats including JSON and RDF.
**Status:** VERIFIED
**Evidence:** https://pypi.org/pypi/linkml/json.
**Retrieved:** 2026-08-20
**Implication for the spec:** LinkML is the right pick for `ontology/` because SIG needs *one* schema to generate (a) Pydantic runtime models, (b) JSON Schema for export validation, (c) SHACL/RDF for the JSON-LD dump, and (d) human-readable docs. Hand-maintaining four representations is how ontologies rot. The generated artifacts are **committed** and drift-checked (T-SCH-3) so that a contributor can read the repo without running the generator.
**Outline delta:** EXTENDS §8 and §14.3 ("open schemas") with a concrete mechanism.

### F11.32 — Core Python data dependencies verified

**Claim:** `pydantic` 2.13.4 (released 2026-05-06), open-source classifiers, requires Python >=3.9 supporting through 3.14. `sqlalchemy` 2.0.52, MIT, requires >=3.7. `alembic` 1.17.1, MIT, requires >=3.10, by the SQLAlchemy author, supporting autogeneration, transactional DDL, and SQL-script output for DBA-gated environments. `psycopg` 3.3.4, **LGPL-3.0-only**, requires >=3.10. `pyarrow` 25.0.1, Apache-2.0, requires >=3.10. `duckdb` 1.5.5, MIT, requires >=3.10.0. `httpx` 0.28.1, BSD-3-Clause, requires >=3.8. `scrapy` 2.18.0, BSD-3-Clause, requires >=3.10.
**Status:** VERIFIED
**Evidence:** PyPI JSON endpoints for each: pydantic, sqlalchemy, alembic, psycopg, pyarrow, duckdb, httpx, scrapy.
**Retrieved:** 2026-08-20
**Implication for the spec:** All adopted except Scrapy — SIG does **not** adopt Scrapy, because Scrapy brings its own scheduler, its own concurrency model, and its own middleware stack, all of which duplicate and fight the `PolitenessGateway` (§1.7). SIG uses `httpx` behind the gateway. **Note psycopg's LGPL-3.0-only license:** dynamically linking an LGPL library from a non-copyleft application is standard and fine, but it must appear in the dependency-license inventory and SIG must not statically vendor it. Alembic's SQL-script output mode is worth adopting for production migrations regardless of team size — a reviewable `.sql` diff is better than a trusted autogenerated `op.alter_column`.
**Outline delta:** N/A.

### 5.3 Dependency management: uv

### F11.33 — uv is the current best practice, PEP 751 is Final, and uv can export to it

**Claim:** `uv` 0.12.5, dual-licensed MIT OR Apache-2.0, "An extremely fast Python package and project manager, written in Rust" by Astral, providing lockfile-backed project management, script execution with inline dependency declarations, tool install/run, Python version management, and a pip-compatible interface. PEP 751 is **Final** (as of 2025-03-31) and standardizes `pylock.toml` (or `pylock.<name>.toml`); PDM, Poetry, and uv are noted as implementing semantically similar approaches. uv's lockfile is `uv.lock`; uv will not consider a lockfile outdated merely because new versions were released — updates must be explicit; `uv export --format pylock.toml` produces a PEP 751 file, and `requirements.txt` and CycloneDX SBOM exports are also supported. Poetry is at 2.4.1, MIT, requires `>=3.10,<4.0`.
**Status:** VERIFIED
**Evidence:** https://pypi.org/pypi/uv/json; https://peps.python.org/pep-0751/ (Status: Final, 2025-03-31; `pylock.toml` naming; TOML format; PDM/Poetry/uv noted); https://docs.astral.sh/uv/concepts/projects/sync/ (lock/sync semantics, explicit-update behavior, `uv export --format pylock.toml`, `uv lock --upgrade`); https://pypi.org/pypi/poetry/json.
**Retrieved:** 2026-08-20
**Implication for the spec:** **Adopt uv.** Commit `uv.lock` as the operative lockfile. Additionally generate and commit `pylock.toml` **on each release** as the standards-based archival record — this matters because in 10 years a researcher reproducing a SIG release should not need uv specifically to know what was installed. Also export a **CycloneDX SBOM per release** into the release manifest; it costs one command and makes the dependency provenance auditable. Do not adopt Poetry: it is fine, but uv's speed materially changes CI cost (a real line item for a project running many CI jobs on free minutes, F11.13) and its workspace support fits §5.2.
**Outline delta:** EXTENDS §14.3 ("reproducible ingestion") — the lockfile plus SBOM is half of what "reproducible" means.

### 5.4 What "reproducible ingestion" concretely means (§14.3)

The outline lists "reproducible ingestion" among the ideals without defining it. R11 defines it as **four separately-testable properties**, each with a mechanized proof:

**RP-1 — Deterministic transformation.** Given the same snapshot bytes and the same code version, `parse → extract → normalize` produces byte-identical output.
*Proof:* `test_determinism` runs every golden fixture twice in the same process and once in a fresh subprocess with `PYTHONHASHSEED` varied, and asserts identical `canonical_sha256` and identical claim keys. Ruff's `DTZ` rules (F11.29) statically ban `datetime.now()` in the pure stages; a runtime guard patches `time.time` during fixture tests.

**RP-2 — Reconstructible artifacts.** Given a release tag, any third party can rebuild the published artifacts and get matching checksums.
*Proof:* the release job builds artifacts twice — once in the normal job, once in a clean container from the tag — and compares SHA-256. Requires: sorted output ordering everywhere, fixed Parquet writer options (compression, row-group size, no writer-version string in metadata), `SOURCE_DATE_EPOCH` for any archive, and no wall-clock timestamps inside artifact bodies (they go in the manifest, which is signed separately).

**RP-3 — Auditable environment.** Every artifact records exactly what produced it.
*Proof:* every `ingest_run` row carries `code_commit`, `image_digest`, `ontology_version`, and an `env` blob (Python version, key dependency versions, region). The release manifest embeds the same plus the SBOM.

**RP-4 — Replayable history.** Any past claim can be regenerated from its archived snapshot with its recorded parser version.
*Proof:* a nightly job samples 50 claims, checks out the recorded `parser_version` of the extractor, re-runs it against the archived snapshot, and asserts the resulting `claim_key` matches. **This is the strongest single reproducibility test SIG can run** and it will find real bugs, because it exercises the interaction of code versioning, content addressing, and claim identity simultaneously. Failures here mean either a parser version wasn't bumped when behavior changed, or a snapshot was mutated — both critical.

**Containerization.** Build one image per release, `sig/pipeline:<git-sha>`, from a pinned base digest (never `:latest`), installing from `uv.lock` with `--frozen`. Record the image digest on every run. The image is what makes RP-2 and RP-4 achievable across years; without it, "the same code version" is a fiction the moment a transitive C library changes.


---

## PART E — API AND EXPORT DELIVERY

## 6. Delivery architecture

### 6.1 The governing decision: static-first

**The primary distribution channel is versioned static artifacts on object storage. The dynamic API is a convenience layer over the same data, not the source of truth.**

Three reasons, in order of weight:

1. **Cost.** R2's zero egress (F11.34) makes unlimited bulk download free. A dynamic API serving the same bytes costs compute *and* egress and scales with popularity — the worst possible cost curve for a public-interest project whose success metric is being downloaded.
2. **Reproducibility.** A citable, checksummed, DOI-minted artifact (F11.9) is what makes a SIG claim usable in a paper or a filing. An API response is not citable.
3. **Survivability.** Static artifacts on object storage keep working when SIG has no funded compute (§6.6). An API does not.

The API therefore exists to serve the three things static files serve badly: (a) point lookups by entity id, (b) as-of temporal queries, (c) the review-queue and contribution write paths.

### 6.2 API framework recommendation: FastAPI

### F11.34 — API framework versions and licenses

**Claim:** `fastapi` 0.141.1, MIT, requires Python >=3.10. `litestar` 2.24.0, MIT, released 2026-06-11, requires `>=3.8,<4.0`, "a production-ready, highly performant, extensible ASGI API Framework". `django-ninja` 1.6.3, MIT, requires >=3.7, Django + type hints + Pydantic.
**Status:** VERIFIED
**Evidence:** https://pypi.org/pypi/fastapi/json; https://pypi.org/pypi/litestar/json; https://pypi.org/pypi/django-ninja/json.
**Retrieved:** 2026-08-20
**Implication for the spec:** All three are MIT and viable. **Recommend FastAPI** because (a) it shares Pydantic v2 with the ontology-generated models (F11.31/F11.32), so response schemas are the ontology rather than a hand-written mirror; (b) its OpenAPI generation is the most widely-consumed, which matters for §20 Q37 (other projects linking back); (c) contributor familiarity is highest, which is the same argument as §5.1. **Litestar is the credible alternative** and would be preferred if SIG wanted built-in DI and a stricter layered structure; it is not enough better to outweigh (c). **Django Ninja is rejected** — it implies Django, and SIG has no need for Django's ORM/admin given that `sig-store` owns persistence and the review UI is a purpose-built surface.
**Outline delta:** N/A.

### 6.3 API specification

**REST, not GraphQL — plus a SPARQL-ish escape hatch via the published RDF dump, and a DuckDB/Datasette path for arbitrary queries.**

GraphQL is rejected for a public read API on three grounds: (a) unbounded query cost is an availability risk for an unfunded project, (b) it defeats CDN caching, which is the mechanism making the API nearly free, and (c) SIG's arbitrary-query use case is better served by "download the 200 MB DuckDB file and query it locally," which is strictly more powerful and costs SIG nothing.

```
GET  /v1/entities/{id}                        # canonical entity, current view
GET  /v1/entities/{id}?as_of=2026-03-01T00:00:00Z
GET  /v1/entities/{id}/claims                 # paginated, filterable by predicate
GET  /v1/entities/{id}/evidence               # evidence artifacts + snapshot links
GET  /v1/entities/{id}/timeline               # state transitions, bitemporal
GET  /v1/entities/{id}/contradictions         # §6.5 — contradictions as a resource
GET  /v1/claims/{claim_id}                    # a single claim with full lineage + source spans
GET  /v1/search?q=&type=&state=&technology=   # bounded search
GET  /v1/deployments?bbox=&technology=&as_of= # geospatial query, bbox-bounded
GET  /v1/organizations/{id}/dossier           # the §15.1 product surface, composed server-side
GET  /v1/sources                              # source registry incl. licenses + freshness
GET  /v1/sources/{id}/freshness               # machine-readable form of the §6.4 dashboard
GET  /v1/releases                             # release manifests, checksums, DOIs
GET  /v1/coverage                             # §7.2 Goal 6: quantified incompleteness
POST /v1/reports                              # authenticated: corrections, new leads → review queue
GET  /v1/review/tasks                         # partner tier: claimable research tasks (§12, Q36)
```

| Concern | Decision |
|---|---|
| **Versioning** | URL-prefix major version (`/v1/`). Additive changes only within a major. A breaking change ships `/v2/` with `/v1/` maintained ≥12 months and a `Sunset` header. Response bodies carry `"schema_version"` (the ontology version) independently — an ontology minor bump is not an API break. |
| **Pagination** | Cursor-based (opaque, encodes sort key + tiebreaker id). No offset pagination anywhere — offsets over a bitemporal table with concurrent appends produce duplicates and gaps. `limit` default 50, max 1000. Every list response returns `next_cursor` and `has_more`. |
| **Conditional requests** | Every GET returns a strong `ETag` derived from `(entity_id, max(recorded_at) over included claims, ontology_version, as_of)`. `If-None-Match` → 304. `Last-Modified` also emitted. As-of responses for a **past** `as_of` are immutable and get `Cache-Control: public, max-age=31536000, immutable`. |
| **Caching / CDN** | Cloudflare in front of everything. Current-view responses: `s-maxage=300, stale-while-revalidate=86400`. Past-as-of responses: immutable, one year. Static artifacts: immutable, one year. Cache purge on release only. |
| **Rate limiting** | Enforced at the CDN edge, not in the app. Anonymous: 60 req/min, 10,000/day per IP. Registered (free API key): 300 req/min, 200,000/day. Partner: negotiated, plus review-queue write access. Bulk downloads are **never rate limited** — the whole point is to push people toward them. |
| **Auth tiers** | Anonymous (read, no key). Registered (key in `Authorization: Bearer`; used for quota and for contacting heavy users, not for gating data). Partner (scoped: review tasks, unredacted metadata where R8's policy permits, write-back). |
| **OpenAPI** | Generated by FastAPI, **committed to `api/openapi/openapi.json`**, and diffed in CI — an unintended breaking change shows as a reviewable diff. Published at `/v1/openapi.json`. |
| **Errors** | RFC 9457 `application/problem+json` with a stable `type` URI per error class. |
| **CORS** | Permissive on all read endpoints (`*`) — required for Datasette Lite and browser-based PMTiles (F11.11/F11.12) and appropriate for public data. |

### 6.4 As-of semantics

**Every read endpoint accepts `as_of` (RFC 3339 UTC). Its absence means "now".** Two distinct axes exist and both must be addressable (§9.2 of the outline):

- `as_of` — **transaction time**: what SIG believed at that instant. Default: now.
- `valid_at` — **validity time**: what was true in the world at that instant. Default: now.

They are orthogonal and the combination is meaningful: `?as_of=2026-01-01&valid_at=2024-06-01` = "on 2026-01-01, what did SIG believe was true in June 2024?" This is the query that makes SIG's temporal claims defensible, and it must be in `/v1` from the start — retrofitting bitemporality is not feasible.

```sql
-- the single as-of predicate, in db/sql/as_of.sql, used by EVERY read path
WHERE c.recorded_at <= :as_of
  AND (c.superseded_at IS NULL OR c.superseded_at > :as_of)
  AND c.valid_from <= :valid_at
  AND (c.valid_to IS NULL OR c.valid_to > :valid_at)
```

**Caching implications, which are the reason to design this carefully:**

1. A response for a **past** `as_of` can never change — it is a function of an append-only table's prefix. Mark it `immutable`, cache for a year, and the expensive queries become free after first request.
2. A response for `as_of=now` changes constantly. Cache 300 s with `stale-while-revalidate`.
3. **Therefore: normalize `as_of` at the edge.** An omitted `as_of` is *not* rewritten to a timestamp (that would fragment the cache into one entry per request); it stays the canonical "current" key. An explicitly-supplied `as_of` is snapped to the nearest second and becomes part of the cache key.
4. **Reject future `as_of`** with 400. A future as-of is either a bug or an attempt to cache-poison.
5. **`as_of` before the project's genesis** returns an empty result set with an explanatory `Warning` header, not a 404 — "SIG did not exist then" is a true and useful answer.
6. Every response echoes the effective `as_of` and `valid_at` in the body and in `X-SIG-As-Of` / `X-SIG-Valid-At` headers, so a cached response is self-describing.

### 6.5 Static-first exports: artifacts, manifest, versioning

**Artifact set, per release:**

| Artifact | Format | Purpose | Est. size (steady state) |
|---|---|---|---|
| `entities.parquet`, `claims.parquet`, `evidence.parquet`, `sources.parquet` | Parquet (zstd) | analysis; the primary bulk format | 200 MB–1.5 GB |
| `*.csv.gz` | CSV | lowest-common-denominator; spreadsheet users | 300 MB–2 GB |
| `claims.jsonl.gz` | JSONL | streaming consumers | similar |
| `deployments.geojson.gz`, `assets.geojson.gz` | GeoJSON | GIS tools | 50–300 MB |
| `map.pmtiles` | PMTiles v3 (F11.11) | the map surface; served by range request | 100–500 MB |
| `sig.jsonld` / `sig.nt.gz` | JSON-LD + N-Triples | RDF consumers; SHACL-validated against `ontology/generated/shacl` | 500 MB–3 GB |
| `sig.db` | SQLite | Datasette + Datasette Lite (F11.12) | 300 MB–2 GB |
| `sig.duckdb` | DuckDB (F11.32) | local analytical queries | similar |
| `osm_derived/*.parquet` | Parquet | **ODbL-licensed layer, physically separate** (§14.1 Strategy A) | 100–800 MB |
| `MANIFEST.json` | Data Package (F11.10) | the index; checksums; licenses; DOI | <1 MB |
| `CHECKSUMS.txt` + `.sig` | text + signature | integrity + authenticity | tiny |
| `quality-report.html` | Pointblank (F11.21) | the trust artifact | few MB |
| `sbom.cdx.json` | CycloneDX | dependency provenance | small |

**Snapshot versioning scheme: calendar version + content hash, both.**

```
sig-2026.08.20+a3f9c1e2
└── calver: YYYY.0M.0D    (what a human cites; what the DOI is minted against)
    └── +hash: first 8 hex of sha256(sorted CHECKSUMS.txt)   (what a machine verifies)
```

Rationale: calver alone cannot distinguish two releases on the same day and does not prove content identity. Content hash alone is unusable in prose ("as of SIG release a3f9c1e2" is unreadable). Semver is actively wrong for a dataset — there is no meaningful "minor" vs "patch" for a snapshot of the world, and pretending otherwise invites arguments. Ontology changes are versioned **separately** with semver (`ontology_version: 3.2.0`) and recorded in the manifest, because *that* genuinely has a compatibility contract.

Layout on R2 (immutable paths + a mutable pointer):

```
r2://sig-releases/
  latest.json                                # {"release": "sig-2026.08.20+a3f9c1e2", ...} — the ONLY mutable object
  releases/sig-2026.08.20+a3f9c1e2/
      MANIFEST.json  CHECKSUMS.txt  CHECKSUMS.txt.sig
      entities.parquet  claims.parquet  ...  map.pmtiles  sig.db  osm_derived/...
      quality-report.html  sbom.cdx.json
r2://sig-snapshots/sha256/aa/bb/<sha256>     # raw evidence, content-addressed, forever
```

**Manifest format** — a Data Package descriptor with a `sig` profile:

```jsonc
{
  "profile": "https://<sig>/schemas/sig-datapackage-1.0.json",
  "name": "sig-2026.08.20",
  "id": "https://doi.org/10.5281/zenodo.XXXXXXX",     // Zenodo VERSION DOI (F11.9)
  "title": "Surveillance Infrastructure Graph — release 2026.08.20",
  "version": "2026.08.20+a3f9c1e2",
  "created": "2026-08-20T07:41:00Z",
  "homepage": "https://<sig>/releases/2026.08.20",
  "sig": {
    "concept_doi": "https://doi.org/10.5281/zenodo.YYYYYYY",
    "previous_release": "sig-2026.08.13+7d2b0f44",
    "ontology_version": "3.2.0",
    "code_commit": "e91c4a7...",
    "image_digest": "sha256:0f21...",
    "as_of": "2026-08-20T06:00:00Z",             // transaction-time cut for the whole release
    "counts": {"entities": 41822, "claims": 2903117, "evidence_artifacts": 388214,
               "sources_active": 61, "sources_unavailable": 7, "open_review_tasks": 1204},
    "coverage": {"states_with_data": 50, "estimated_completeness_note": "see /v1/coverage"},
    "quality": {"report": "quality-report.html", "checks_run": 74, "warnings": 9, "failures": 0},
    "reproduce": {"command": "docker run sig/pipeline@sha256:0f21... export --as-of 2026-08-20T06:00:00Z",
                  "sbom": "sbom.cdx.json", "pylock": "pylock.toml"}
  },
  "licenses": [
    {"name": "ODC-BY-1.0", "path": "https://opendatacommons.org/licenses/by/1-0/",
     "title": "SIG-original data"}                 // R2 owns the final choice; this is the placeholder
  ],
  "resources": [
    {"name": "claims", "path": "claims.parquet", "format": "parquet", "mediatype": "application/vnd.apache.parquet",
     "bytes": 1183928211, "hash": "sha256:ab34...",
     "schema": {"$ref": "https://<sig>/schemas/3.2.0/claim.json"},
     "sources": [{"title": "EFF Atlas of Surveillance", "path": "https://atlasofsurveillance.org/download.csv",
                  "license_status": "UNDETERMINED"}]},     // F11.8 — visible, not hidden
    {"name": "osm_derived_assets", "path": "osm_derived/assets.parquet", "format": "parquet",
     "bytes": 402118883, "hash": "sha256:cd77...",
     "licenses": [{"name": "ODbL-1.0", "path": "https://opendatacommons.org/licenses/odbl/1-0/"}],
     "sig": {"attribution": "© OpenStreetMap contributors",
             "separability_note": "This resource is a separate database under ODbL; joining it to other resources may create a Derivative Database."}}
  ]
}
```

The two things this manifest does that a bespoke one would not: **resource-level licensing** (which is how §14.1 Strategy A becomes enforceable, T-LIC-2) and **an explicit `reproduce` block** (which is how §14.3's "reproducible" becomes a command someone can run rather than a claim).

**Integrity and authenticity:** `CHECKSUMS.txt` lists sha256 for every artifact; `CHECKSUMS.txt.sig` is a detached signature (minisign or Sigstore) so a mirror cannot silently alter a release. This matters more than usual for SIG: it is a project whose data some parties would prefer altered.

---

## PART F — DEPLOYMENT AND ECONOMICS

## 7. Topology, cost, observability, sustainability

### 7.1 Storage economics — the decision that dominates the cost model

### F11.35 — R2 has zero egress fees; B2 has a 3× free-egress allowance; S3 charges beyond 100 GB/mo

**Claim:** Cloudflare R2 Standard storage is **$0.015/GB-month**, Infrequent Access $0.01/GB-month; Class A operations $4.50/million (IA $9.00/million), Class B $0.36/million (IA $0.90/million); **egress is free**; the monthly free tier (Standard only) is 10 GB-month storage, 1M Class A and 10M Class B operations, with egress free. Backblaze B2 starts at **$6.95/TB/month** (≈$0.00695/GB-month) pay-as-you-go with **free egress up to 3× average monthly storage**, then $0.01/GB, with Class A/B/C API calls free and Class D at $0.004/10,000 calls (first 2,500/day free) and 10 GB always free. Amazon S3 charges for storage and requests by class and provides only "the first 100GB per month, aggregated across all AWS Services and Regions" of internet egress free.
**Status:** VERIFIED (R2, B2 exactly; S3 PARTIALLY — the pricing page confirmed the 100 GB free-egress policy and the pay-per-request model but did not surface exact per-GB figures in the fetched content)
**Evidence:** https://developers.cloudflare.com/r2/pricing/; https://www.backblaze.com/cloud-storage/pricing; https://aws.amazon.com/s3/pricing/ (100 GB aggregate free egress; "You pay for requests made against your S3 buckets"; per-GB figures not surfaced).
**Retrieved:** 2026-08-20
**Implication for the spec:** **R2 is the primary object store; B2 is the mirror; S3 is not used.** The reasoning is entirely about egress, and the arithmetic is stark: a 2 GB bulk export downloaded 5,000 times in a month is 10 TB of egress. On R2 that costs **$0**. On S3 at typical internet egress rates it is a four-figure monthly bill that scales with SIG's success. **A public-interest bulk-data project on S3 is one viral article away from an existential invoice.** B2's 3×-storage free egress allowance (≈1.5 TB free at 500 GB stored) is generous but bounded, making it a good mirror and a poor primary. R2's free tier (10 GB + 1M/10M ops) also means the **bootstrap scale is genuinely $0 for storage**.
**Outline delta:** EXTENDS §14.3 ("downloadable datasets") with the constraint that determines whether that promise is affordable. The outline treats distribution as a policy question; it is primarily an egress-pricing question.

### 7.2 Compute, database, and monitoring price points

### F11.36 — Compute and Postgres price points

**Claim:** Fly.io `shared-cpu-1x` runs $0.0028/h (256 MB, ≈$2.02/mo), $0.0046/h (512 MB, ≈$3.32/mo), $0.0082/h (1 GB, ≈$5.92/mo), $0.0154/h (2 GB, ≈$11.11/mo); `shared-cpu-2x` $0.0056/h (512 MB) to $0.0309/h (4 GB, ≈$22.22/mo); additional RAM ≈$5 per 30 days per GB; volumes $0.15/GB-month; snapshots $0.08/GB-month with first 10 GB free; egress $0.02/GB (NA/EU). Neon: Free plan $0 with 100 CU-hours and 0.5 GB storage per project; Launch and Scale are pay-as-you-go with compute at $0.106 and $0.222 per CU-hour respectively and storage at **$0.35/GB-month**; **PostGIS is included on all plans**, as are autoscaling, branching, read replicas, and connection pooling. Supabase: Free $0 (500 MB database, 5 GB egress, paused after 1 week of inactivity); Pro $25/mo (8 GB database then $0.125/GB, 250 GB egress then $0.09/GB, $10 compute credit); Team $599/mo. Cloudflare Workers: free 100,000 requests/day with 10 ms CPU per invocation; paid from $5/month including 10M requests then $0.30/million and 30M CPU-ms then $0.02/million; static asset requests are free and unlimited. Sentry: Developer free ($0, 1 user, 5,000 errors); Team $26/mo billed annually (unlimited users, 50,000 errors); Business $80/mo.
**Status:** VERIFIED (Fly, Neon, Supabase, Cloudflare, Sentry). Hetzner Cloud instance pricing was **INACCESSIBLE** — the pricing table is JS-rendered (`ho-price-container` web components with `product-key` attributes and no inline values) and `api.hetzner.cloud/v1/pricing` requires a token (HTTP 401).
**Evidence:** https://fly.io/docs/about/pricing/; https://neon.com/pricing; https://supabase.com/pricing; https://developers.cloudflare.com/workers/platform/pricing/; https://sentry.io/pricing/; Hetzner: `curl` of https://www.hetzner.com/cloud/ returned only price *placeholders*, and `https://api.hetzner.cloud/v1/pricing` returned `{"error":{"code":"unauthorized",...,"message":"token is required"}}`.
**Retrieved:** 2026-08-20
**Implication for the spec:** Neon is the bootstrap database (PostGIS on all tiers, and the free tier is genuinely usable for early Stage-1 work). Supabase's **1-week inactivity pause on the free tier disqualifies it for SIG's free tier** — a project whose pipeline runs nightly cannot tolerate a database that sleeps. Fly is the bootstrap compute. Sentry's free Developer tier covers a 1-person project; Team at $26/mo is the first paid step. Cloudflare's free Workers tier plus free static-asset serving covers the entire web frontend at bootstrap. **Hetzner must be re-priced by a human before it appears in a budget** — R11 has used a conservative placeholder in §7.3 and flagged it as OQ-5.
**Outline delta:** N/A.

### 7.3 The three-scale cost model

All figures are USD/month, using the verified prices in F11.34–F11.36 and the Claude pricing in F11.37. **Numbers marked ⚠ are estimates derived from verified unit prices applied to R11's projected usage, not quoted totals.**

**Scale 1 — Bootstrap.** Single region, one contributor, Stage 1 of §17. ~50 sources, ~5k entities, nightly cadence, no browser scraping, LLM extraction on a few hundred documents/month.

| Line | Choice | Basis | $/mo |
|---|---|---|---|
| Postgres + PostGIS | Neon Free → Launch | Free tier 0.5 GB; ~5 GB storage @ $0.35 + light compute ⚠ | $0–8 |
| Object storage | R2 | ~40 GB snapshots + 15 GB releases; 10 GB free; ~45 GB @ $0.015 | $0.68 |
| Egress | R2 | zero-rated (F11.35) | **$0.00** |
| CDN + web | Cloudflare free | static assets unlimited/free; Workers free tier | $0.00 |
| Crawler compute | Fly shared-cpu-1x 512 MB | $3.32 (F11.36) | $3.32 |
| Orchestrator | Dagster OSS on the same machine | webserver+daemon co-located (F11.24) | $0.00 |
| Headless browser | none at this scale | — | $0.00 |
| LLM extraction | Claude Haiku 4.5 batch | ~400 docs/mo (§7.5 arithmetic) ⚠ | $1–3 |
| Error tracking | Sentry Developer (free) | 5,000 errors, 1 user (F11.36) | $0.00 |
| Metrics/logs | Prometheus + Loki on the Fly box, 7-day retention | self-hosted | $0.00 |
| Domain + DNS | registrar + Cloudflare | ⚠ | $1.50 |
| Zenodo DOIs | free (F11.9) | — | $0.00 |
| CI | GitHub Actions, public repo | free for public repos (F11.13) | $0.00 |
| Backups | R2 lifecycle copy + weekly `pg_dump` to R2 | included above | $0.00 |
| **Total** | | | **≈ $6–17; budget $32–48 with headroom** ⚠ |

The honest headline is **under $50/month, and plausibly under $20**. The headroom in the budgeted figure covers a Neon compute spike and a paid Sentry seat if a second contributor joins.

**Scale 2 — Steady state.** Stages 2–4 of §17. ~250 sources incl. ~1,500 Flock portals snapshotted daily, browser scraping for SPA portals, ~40k entities, ~3M claims, public API with real traffic, weekly releases.

| Line | Choice | Basis | $/mo |
|---|---|---|---|
| Postgres + PostGIS | Crunchy Bridge or self-managed on a dedicated VM | INACCESSIBLE pricing (Crunchy calculator is JS-only); comparable managed PG ⚠ | $60–120 |
| Object storage | R2 | ~1.2 TB snapshots + 250 GB releases ≈ 1.45 TB @ $0.015 | $21.75 |
| Egress | R2 | ~25 TB/mo of bulk downloads and PMTiles range requests: **zero-rated** | **$0.00** |
| R2 operations | Class A ~4M, Class B ~60M ⚠ | (4×$4.50) + (60×$0.36) | $39.60 |
| Mirror | Backblaze B2, 1.45 TB @ $6.95/TB | F11.35 | $10.08 |
| CDN + web | Cloudflare Workers Paid | $5 base + modest overage ⚠ | $5–12 |
| Crawler compute | 2 × Fly shared-cpu-2x 2 GB | 2 × $11.83 (F11.36) | $23.66 |
| Orchestrator | Fly shared-cpu-1x 2 GB (Dagster webserver+daemon) | $11.11 (F11.36) | $11.11 |
| Headless browser | 1 × shared-cpu-2x 4 GB, capped concurrency 2 | $22.22 (F11.36) | $22.22 |
| API | 2 × shared-cpu-1x 1 GB behind CDN | 2 × $5.92 | $11.84 |
| Volumes | ~100 GB @ $0.15 | F11.36 | $15.00 |
| LLM extraction | Claude Haiku 4.5 + Sonnet 5 batch mix | ~8,000 docs/mo (§7.5) ⚠ | $30–90 |
| Error tracking | Sentry Team | $26 annual-billed (F11.36) | $26.00 |
| Metrics/logs | Grafana Cloud free tier or self-hosted | ⚠ | $0–20 |
| Domain/DNS/misc | | ⚠ | $5 |
| **Total** | | | **≈ $280–430** ⚠ |

**Scale 3 — Ambitious.** Stages 5–6: broader technologies, international, high-frequency portal monitoring, ~1,500 sources, ~250k entities, ~30M claims, LLM extraction at volume, a public review platform with real contributor traffic.

| Line | Basis | $/mo |
|---|---|---|
| Postgres + PostGIS (HA, read replica) | managed, ~500 GB, 8 vCPU ⚠ | $400–800 |
| Object storage (R2) | ~12 TB snapshots + 2 TB releases @ $0.015 | $210 |
| Egress | **zero-rated on R2** | **$0.00** |
| R2 operations | ~30M Class A, ~400M Class B ⚠ | $279 |
| B2 mirror | 14 TB @ $6.95/TB | $97 |
| Compute (crawlers, workers, API, orchestrator) | ~10 instances ⚠ | $250–400 |
| Headless browser fleet | 4 instances, still concurrency-capped | $90 |
| CDN / Workers | paid + overage ⚠ | $50–150 |
| LLM extraction | ~120,000 docs/mo (§7.5) ⚠ | $450–1,400 |
| Observability | Grafana Cloud paid + Sentry Business | $130 |
| Search (if OpenSearch/Typesense added) | ⚠ | $50–120 |
| **Total** | | **≈ $2,000–3,600** ⚠ |

**The shape of these numbers is the finding.** From bootstrap to ambitious, storage-and-egress grows sub-linearly (because R2 zero-rates the part that would have exploded) while **LLM extraction and managed Postgres become the dominant costs**. That is a good position: both are directly controllable — LLM cost via model tier and batch mode (§7.5), Postgres via self-hosting. Neither is a cost that scales with *popularity*, which is the trap the outline's §14.3 ambitions would otherwise walk into.

### 7.4 LLM cost arithmetic

### F11.37 — Current Claude pricing, batch discount, and caching multipliers

**Claim:** Per million tokens (base input / output): Claude Opus 5 $5 / $25; Claude Sonnet 5 **$2 / $10** (the introductory price is now the standard price; the previously scheduled increase to $3/$15 on 2026-09-01 will not occur); Claude Haiku 4.5 $1 / $5; Claude Fable 5 $10 / $50. Prompt caching multipliers relative to base input: 5-minute cache write 1.25×, 1-hour cache write 2×, cache read (hit) 0.1×. **The Batch API gives a 50% discount on both input and output** — e.g. Haiku 4.5 batch $0.50 / $2.50, Sonnet 5 batch $1 / $5, Opus 5 batch $2.50 / $12.50. Batch and caching discounts stack. Claude 4.7-and-later models use a newer tokenizer producing ~30% more tokens for the same text. Web search costs $10 per 1,000 searches; web fetch has no additional charge; code execution is free when used with web search/fetch, otherwise 1,550 free hours/month per org then $0.05/hour/container.
**Status:** VERIFIED
**Evidence:** https://platform.claude.com/docs/en/about-claude/pricing (fetched after a documented 302 redirect from https://docs.claude.com/en/docs/about-claude/pricing) — the full model pricing table, the caching multiplier table, the batch pricing table, the tokenizer note, and the tool-specific pricing.
**Retrieved:** 2026-08-20
**Implication for the spec:** See the per-10k-document arithmetic below. The two operational levers that matter most: **use the Batch API for all non-interactive extraction (50% off, and SIG's extraction is never latency-sensitive)** and **cache the long, stable system prompt + schema** (0.1× reads after a 1.25× write pays back after a single reuse).
**Outline delta:** N/A (outline does not cost LLM usage).

**Token model per document.** Assume a typical SIG extraction unit: a single FOIA PDF page-set or one portal page, with a stable ~2,500-token system prompt (instructions + JSON schema + few-shot), plus document content, producing structured JSON with source spans.

| Document class | Content tokens (in) | Output tokens | Notes |
|---|---|---|---|
| Flock portal page (parsed text) | ~1,500 | ~800 | mostly deterministic; LLM used only for free-text policy prose |
| Short FOIA letter / memo (2–4 pp) | ~4,000 | ~1,200 | |
| Contract / MSA (15–40 pp) | ~30,000 | ~2,500 | the expensive class |
| Council agenda / minutes (10–30 pp) | ~20,000 | ~1,500 | |
| **Blended average** | **~12,000** | **~1,500** | R11's planning assumption ⚠ |

**Cost per 10,000 documents at the blended average (12k in / 1.5k out), with the 2,500-token system prompt cached:**

| Configuration | Input cost | Output cost | **Total / 10k docs** |
|---|---|---|---|
| Haiku 4.5, real-time, no cache | 10k × 14,500 × $1/M = $145.00 | 10k × 1,500 × $5/M = $75.00 | **$220.00** |
| Haiku 4.5, **batch**, cached prompt | (10k×12,000×$0.50/M) + (10k×2,500×$0.05/M) = $60.00 + $1.25 | 10k×1,500×$2.50/M = $37.50 | **$98.75** |
| Sonnet 5, real-time, no cache | 10k × 14,500 × $2/M = $290.00 | 10k × 1,500 × $10/M = $150.00 | **$440.00** |
| Sonnet 5, **batch**, cached prompt | (10k×12,000×$1/M) + (10k×2,500×$0.10/M) = $120.00 + $2.50 | 10k×1,500×$5/M = $75.00 | **$197.50** |
| Opus 5, **batch**, cached prompt | (10k×12,000×$2.50/M) + (10k×2,500×$0.25/M) = $300.00 + $6.25 | 10k×1,500×$12.50/M = $187.50 | **$493.75** |

*(Cache-read pricing is 0.1× base input per F11.37; the 1.25× write is amortized to negligible across 10k requests sharing one prompt. Batch halves both input and output.)*

**Recommended routing policy, and its cost consequence:**

- **Default: Haiku 4.5 in batch mode** for structured extraction from clean text → **≈$99 per 10k documents**.
- **Escalate to Sonnet 5 in batch** when Haiku's structured-output validation fails, when the document is a contract/policy requiring judgment, or when the gold-set accuracy for that document class falls below the §7.5 threshold → **≈$198 per 10k**.
- **Opus 5 only for adjudication samples and for building/refreshing the gold set** — i.e. tens to low hundreds of documents, not thousands.
- **Escalation is measured, not guessed:** the router records which tier handled each document, and the accuracy protocol (§7.5) reports per-tier accuracy so the routing rule is tuned against evidence.

At steady state (~8,000 docs/month, mostly Haiku with ~20% Sonnet escalation) this lands at **≈$95–140/month**, consistent with the $30–90 line in §7.3 for a lighter early mix and comfortably inside the ambitious-scale allowance.

**One critical planning note:** the ~30% tokenizer increase on 4.7+ models (F11.37) means any token estimate carried over from an older model is low. SIG must re-baseline with `count_tokens` against the exact model it uses before trusting a budget, and the extraction adapter should record actual `usage` on every call so the cost model is measured rather than assumed.

### 7.5 Observability

| Layer | Choice | Detail |
|---|---|---|
| **Structured logging** | `structlog` → JSON to stdout | Every log line carries `run_id`, `connector_id`, `ref_key`, and `snapshot_sha256` where applicable. The pipeline's log is queryable by evidence identifier, which is what you actually need at 2am. |
| **Metrics** | Prometheus (self-hosted at bootstrap; Grafana Cloud later) | Core series: `sig_fetch_total{connector,outcome}`, `sig_unavailable_total{connector,reason}`, `sig_claims_emitted{connector}`, `sig_review_tasks_open{type}`, `sig_politeness_incidents_total{host}`, `sig_llm_tokens{model,tier}`, `sig_source_last_success_seconds{source}`. |
| **Error tracking** | Sentry (Developer free → Team $26, F11.36) | With a hard rule: **`Unavailable` never goes to Sentry.** It is data (§1.5). Sentry sees programmer errors only, or the alert becomes noise and gets muted. |
| **Traces** | OpenTelemetry spans per stage, sampled | Optional at bootstrap; valuable once the browser fleet exists. |
| **Alerting** | Alertmanager → one channel | Only four page-worthy conditions: pipeline hard-failed; release gate failed (T-LIC/T-PRIV); politeness auto-pause triggered; partner feed access revoked. **Source staleness does NOT page** — it appears on the dashboard. |

**The public freshness dashboard — a trust affordance, specified.**

Served as a static page rebuilt each nightly run and backed by `GET /v1/sources/{id}/freshness`. Per source, it shows:

1. **Source name, tier (§9.1 A–F), and license status** — including `UNDETERMINED` in amber, which makes F11.8-class gaps publicly visible rather than internally embarrassing.
2. **Last successful capture** (absolute + relative), and **expected cadence** from `ops/freshness.yaml`.
3. **Status:** green (within cadence), amber (1–3 missed cycles), red (>3 missed), **grey (source unavailable — with the reason and the date it went unavailable)**.
4. **A 90-day sparkline of capture success**, which makes intermittent sources visible.
5. **If unavailable:** the `SourceUnavailableEvent` reason and, where escalated, a link to the resulting negative claim. *"This portal disappeared on 2026-04-02"* is a headline SIG publishes on its own status page.
6. **Claims contributed** and **open review tasks** attributable to that source.
7. A machine-readable `freshness.json` mirroring the page, so downstream consumers can gate on it.

The dashboard must show **observed** last-success, never scheduled cadence (F11.13's delay/drop behavior makes scheduled cadence a lie). A source page that says "updates daily" while the last success was 11 days ago is worse than no page at all — it converts a trust affordance into a credibility liability.

### 7.6 Sustainability: the $0/month degraded-but-alive mode

**The design goal: if funding goes to zero and every maintainer walks away, SIG's data stays available, citable, and — for a meaningful subset of sources — still updating, for years, with no human intervention and no bill.**

**Components (all verified free):**

| Component | Mechanism | Evidence |
|---|---|---|
| Compute | GitHub Actions, public repo — standard runners free (F11.13) | verified |
| Scheduling | Actions `schedule` cron, at `:17`/`:41`, never `:00` (F11.13) | verified |
| Storage | R2 free tier: 10 GB storage, 1M Class A, 10M Class B ops, free egress (F11.35) | verified |
| Hosting | Cloudflare Pages / static assets — unlimited free requests for static assets (F11.36) | verified |
| Query UI | **Datasette Lite** over the published `sig.db` — the browser is the server (F11.12) | verified |
| Map | **PMTiles** served by range request from R2 — no tile server (F11.11) | verified |
| Permanence | **Zenodo DOIs** on every release — survives SIG's own domain lapsing (F11.9) | verified |
| Database | **none.** Degraded mode has no Postgres. | — |

**How it works.** The degraded pipeline is a single Actions workflow that: checks out the repo → `uv sync --frozen` → runs `sig-ingest` for the subset of connectors that are cheap and API-based (Atlas CSV, OSM daily diffs filtered, MuckRock, RSS feeds) → writes results into a **SQLite file** rather than Postgres (`sig-store` has a SQLite backend; the store interface exists precisely so this is possible) → rebuilds `sig.db`, the Parquet/CSV exports, and the PMTiles → uploads to R2 → updates `latest.json`. The static site and Datasette Lite pick it up automatically.

**What is lost:** browser-scraped SPA portals (no headless browser), LLM extraction (no API key), the review queue (no humans), the dynamic as-of API (no server). What survives: **the entire evidence archive, every published release, the map, full-text and SQL query over the data, and continued ingestion of the API-based sources — indefinitely, at $0.**

**The three things that must be built at Stage 1 for this to work later:**

1. **The SQLite backend for `sig-store` must exist and be tested from day one.** Retrofitting it during a funding crisis will not happen.
2. **The keepalive workflow.** A weekly job that appends one line to `docs/freshness-log.md` and commits it, defeating the 60-day scheduled-workflow auto-disable (F11.13). Without this, degraded mode dies silently after two months — the most avoidable possible failure.
3. **The `latest.json` pointer + immutable release paths.** Because the pointer is the only mutable object, a degraded-mode release is a single small PUT and can never leave the site in a half-updated state.

**Additionally, and cheaply:** deposit each release to Zenodo (F11.9) and register the site with the Internet Archive. If SIG's domain lapses entirely, the DOIs still resolve to the data. That is the difference between a project that ended and a project that finished.

---

## PART G — LLM USE IN THE PIPELINE

## 8. Where LLMs belong, where they are forbidden, and the required scaffolding

### 8.1 The governing principle

The outline's §2 ALPR Watch section states the rule already, and it is the strongest sentence in the document for this purpose: *"Never overwrite source text with normalized semantics."* Combined with Q28's requirement that model-assisted matching generate review queues rather than writes, the LLM policy follows mechanically:

> **An LLM may propose. It may never publish. Every LLM output is a candidate that carries a citation to the exact source text it came from, and enters the graph only through a path that a human can inspect, sample, and reverse.**

### 8.2 Where LLMs ARE appropriate

| Use | Why it fits | Guardrail |
|---|---|---|
| **Unstructured document → candidate structured claims** (FOIA PDFs, contracts, policy documents, meeting minutes) | The alternative is nothing; deterministic parsing of arbitrary agency PDFs is not tractable | Structured output validated against the LinkML-generated JSON Schema; **per-field source span required**; `review_status='pending'` by default |
| **Free-text reason-code categorization** (the ALPR Watch problem: messy user-entered "Reason" fields) | Genuinely a judgment task with an open vocabulary | Raw text always retained; mapping is `normalization_method='llm:classify_vN'`; **fully reversible**; sampled for accuracy |
| **Entity alias suggestion** ("Metro PD" ≟ "Metropolitan Police Department") | Good at surface-form variation | **Suggestions only.** Feeds R7's candidate generation and the review queue. Never writes a merge. Q28. |
| **Summarization for the review UI** | Reduces reviewer time on a 40-page contract | Summary is **UI chrome, not data** — never stored as a claim, never exported, always displayed adjacent to the source text |
| **Document classification / routing** (is this a contract, an audit log, a policy, a rejection letter?) | Cheap, high-value triage; errors are self-correcting downstream | Low-stakes; recorded but not gated |
| **Extraction QA assistance** — flagging documents where the deterministic parser's output looks implausible | A second opinion that costs $0.001 | Produces review tasks only |

### 8.3 Where LLMs are FORBIDDEN

These are absolute, and each is enforced by a mechanism, not a guideline:

| Forbidden | Enforcement |
|---|---|
| **As the sole basis for a published factual claim** | An LLM-derived claim with `review_status='pending'` is excluded from every public export by a RELEASE gate; only `human_confirmed`, `human_corrected`, or `auto_accepted` (which requires a passing accuracy measurement for that field type, §8.5) can publish |
| **Silently overwriting source text** | `RawClaim.object_raw` is verbatim and immutable; normalization writes a *separate* row. Schema-enforced (T-SCH-4) |
| **Generating confidence numbers** | `NormalizedClaim.confidence` is computed from an explicit, documented rubric (source tier, corroboration count, recency, extraction method) — never from a model's self-report. A model-emitted probability is discarded at the adapter boundary. §9.3 of the outline demands explainable confidence; a model's number is not explainable. |
| **Entity merges** | `link()` accepts only `deterministic:*` or `review:human` as merge-authorizing methods. `llm:*` produces a `ReviewTask`. Q28. |
| **Deciding what is sensitive/publishable** | R8's privacy rules are deterministic regex/rule-based (T-PRIV-*). An LLM may *flag* for review; it may not clear for publication |
| **Writing the negative claims from source disappearance** | Deterministic (§1.5). A model must never infer that something ceased to exist |
| **Any use where its output is not attributable to a source span** | The adapter rejects any extraction whose fields lack spans (§8.4) |
| **Free-running agentic web browsing to "find sources"** | Violates the politeness architecture (§1.7) and produces unattributable evidence. Discovery is a connector, not an agent |

### 8.4 Required scaffolding

**1. Prompt versioning.** Prompts live in `packages/sig-extract/prompts/<task>/<version>.md`, are content-hashed, and are **never edited in place** — a change means a new version. `prompt_sha256` is recorded on every extraction (§3.5 `extraction` table). This makes "which prompt produced this claim?" answerable years later, and makes a prompt change a reviewable diff subject to the accuracy gate (§8.5).

**2. Model + version + params recorded on every extraction.** The `extraction` table's `CHECK (method <> 'llm' OR (model_id IS NOT NULL AND prompt_sha256 IS NOT NULL AND model_params_hash IS NOT NULL))` makes this a database constraint, not a convention. `model_id` is the exact id (e.g. `claude-haiku-4-5`), never an alias that could re-point.

**3. Deterministic settings.** Structured output mode with a strict JSON Schema; no sampling parameters relied upon for variability; the full request params hashed into `model_params_hash`. **Note:** determinism is *not* achievable from an LLM, which is precisely why RP-1 (§5.4) restricts its determinism guarantee to the deterministic stages and why LLM extractions are re-verified by sampling rather than by re-running.

**4. Structured output validation.** Every response is validated against the LinkML-generated JSON Schema for the target predicate set. A validation failure is retried once at the next model tier, then routed to human review. **A failed validation never degrades to "parse what we can" free-text handling** — that is the path by which garbage enters.

**5. Per-field source-span citation — the load-bearing requirement.** The prompt requires, and the schema enforces, that each extracted field carry the exact source text it came from:

```json
{"predicate": "retention_days",
 "value_raw": "thirty (30) days",
 "span": {"kind": "char_range", "locator": "18422:18441", "page": 7,
          "excerpt": "retained for a period of thirty (30) days"}}
```

The adapter then **verifies the span mechanically**: it slices the parsed document at the locator and checks the excerpt matches. **A span that does not resolve is a hallucination detector.** This single check catches the most dangerous LLM failure mode — a plausible value with no basis in the document — at near-zero cost, and it is checked again nightly across the corpus (T-SCH-6). Extractions failing span verification are rejected outright, not reviewed.

**6. Human review sampling rates.**

| Field class | Sampling rate | Rationale |
|---|---|---|
| New extractor or new prompt version, first 200 extractions | **100%** | Nothing publishes from an unvalidated prompt |
| Numeric claims that feed public aggregates (camera counts, retention, search counts) | **100% until 500 confirmations at ≥99% precision, then 10%** | These are the numbers a journalist will quote |
| Contract terms, dollar amounts, dates | **100%** initially, then 20% | High consequence, low volume |
| Reason-code categorization | **5%** ongoing, stratified over categories, 100% of `other`/low-agreement | High volume, low individual stakes, but taxonomy drift is real (T-VOC-3) |
| Entity alias suggestions | **100%** (they are review tasks by definition) | Q28 |
| Document classification | **2%** | Self-correcting |

Sampling is **stratified and recorded**, not "whatever the reviewer clicks." The review queue draws the sample; a reviewer cannot skip a sampled item without recording a reason.

**7. Accuracy-measurement protocol against a gold set.**

```
tests/gold/extraction/
  flock_portal_policy_v1.jsonl     # {"snapshot_sha256":..., "expected": [{predicate, value, span}]}
  foia_contract_v2.jsonl
  reason_codes_v3.jsonl
  _meta.yaml                        # annotator ids, date, inter-annotator agreement, sampling frame
```

Per (extractor, prompt_version, model, document class), report and gate on:

- **Field-level precision / recall / F1** against the gold set.
- **Span-validity rate** — the share of extracted fields whose span resolves (target: 100%; anything below is a hard fail).
- **Hallucination rate** — fields asserted that have no gold counterpart *and* whose span does not support them.
- **Abstention rate** — how often the model correctly declines to extract a field that is genuinely absent. **This is the most under-measured and most important metric**: a model that always produces a value will look accurate on documents that contain the answer and will invent values on documents that do not. SIG's corpus is full of documents that do not contain the answer.
- **Inter-annotator agreement on the gold set itself**, published in `_meta.yaml`. A gold set with 0.7 agreement cannot support a 0.98 precision claim, and pretending otherwise is self-deception.

**Gate:** an extractor may move to `auto_accepted` for a field class only when precision ≥ 0.97, span-validity = 1.00, and hallucination rate ≤ 0.005 on ≥200 gold examples. Any prompt or model change resets the gate to 100% sampling. Metrics are **published** in the release quality report — SIG's own extraction accuracy is part of its provenance claim.

**8. Cost and latency budgeting.**

- Per-run token budget declared per connector in config; exceeding it **stops the run and files a review task**, never silently truncates.
- Batch API for all extraction (50% discount, F11.37); real-time only for the interactive review UI.
- Prompt caching on the stable system prompt (0.1× reads, F11.37).
- Router: Haiku 4.5 → Sonnet 5 on validation failure or document class → Opus 5 for gold-set/adjudication only (§7.4).
- Per-document cost recorded on the `extraction` row from the response's `usage`, so the cost model is measured, not projected.

**9. Fallback when the model is unavailable.**

| Condition | Behavior |
|---|---|
| Rate limited (429) | SDK retry with backoff; then defer the batch to the next run. **Never spin.** |
| Overloaded (529) / API outage | Mark the documents `extraction_deferred` and continue the rest of the pipeline. LLM extraction is never on the critical path of a run. |
| Sustained outage (>24 h) | Documents queue; the freshness dashboard shows the LLM-derived predicates as stale; **deterministic extraction and all other sources keep running normally** |
| Structured-output validation fails twice | Route to human review. Never fall back to unvalidated free-text parsing. |
| Budget exhausted | Same as outage: defer, surface, do not degrade quality |
| No API key at all (degraded mode, §7.6) | LLM extraction is simply absent. Everything else runs. |

The architectural point: **the LLM is a strictly optional enrichment stage.** A SIG deployment with no LLM access produces a smaller graph, not a broken one. That property must be tested — the CI `pr-full` job runs the whole pipeline with the LLM adapter disabled and asserts it completes.

### 8.5 A note on AI-assisted contributions

Because SIG will attract AI-assisted contributions, `AGENTS.md` must state: generated parsers require golden fixtures from **real captured bytes** (§4.3 rule 1), generated migrations require a reviewed `.sql` diff (F11.32), and no PR may add a network call outside `PolitenessGateway`. These are the same rules as for humans; they simply need to be written down where a coding agent will read them.

---

## Open questions

**OQ-1 — DocumentCloud's programmatic surface is not documented at any canonical URL.** `documentcloud.org/api/` 404s, `documentcloud.org/help/api/` redirects to a Notion page that did not render usable content, and the repo README covers only local development (F11.15). *Spec should hedge by:* specifying the DocumentCloud connector as a class-2 cursored REST connector with the conservative default politeness budget and a `TODO(verify)` marker, and by making Q8 an explicit Stage-0 human task ("open the Notion API page in a browser, record base URL / auth / rate limits / redistribution terms in `ops/licenses.yaml`"). Do not let an implementer infer the API shape from the MuckRock API.

**OQ-2 — Legistar's API surface, auth model, and rate limits are unverified** (F11.6). *Hedge:* build the agenda-system connector against RSS/iCal first (which needs no auth and is common across Legistar/CivicClerk/PrimeGov), and treat the Legistar REST API as an optimization gated on reading `webapi.legistar.com/Help`. Assume **per-tenant** rate limits, which the gateway already supports via path-scoped budgets (F11.4).

**OQ-3 — EFF Atlas licensing is undetermined** (F11.8). *Hedge:* `source_license_id = UNDETERMINED` blocks redistribution by default (T-LIC-1 fails closed). SIG may link and reconcile immediately. Resolve by writing to `aos@eff.org` as part of §17 Stage 0. **This must not be resolved by assumption**; a wrong guess here would be a licensing violation against an organization SIG wants as an ally.

**OQ-4 — USAspending rate limits and bulk-download endpoints are undocumented at the API root** (F11.5). *Hedge:* conservative default budget plus adaptive de-escalation; cursored mode as the baseline with bulk download as an unvalidated optimization.

**OQ-5 — Hetzner Cloud pricing was inaccessible** (JS-rendered price components; `api.hetzner.cloud/v1/pricing` requires a token — F11.36). The steady-state self-hosted-Postgres line in §7.3 uses a conservative placeholder. *Hedge:* the cost table is built from verified Fly/Neon/Supabase/R2/B2/Sentry/Cloudflare prices; a human should confirm Hetzner or an equivalent before committing to the self-hosted path. The conclusion (bootstrap under $50/mo) does not depend on Hetzner.

**OQ-6 — Crunchy Bridge pricing is behind a JS calculator** and was not retrievable. *Hedge:* the steady-state managed-Postgres line is a range, and Neon's verified $0.35/GB-month storage plus CU-hour rates bound the low end.

**OQ-7 — OpenLineage's current spec version number was not visible** in the fetched README (F11.26). Immaterial to the recommendation (emit as a secondary output), but the implementer should pin a version.

**OQ-8 — Whether SIG's repository will be public from day one.** This is not a research question but it has large cost consequences: GitHub Actions is free for public repos (F11.13), which is the backbone of both CI and degraded mode. A private repo changes the bootstrap cost model and eliminates the $0 sustainability path. *Recommendation:* public from day one, with private storage only for restricted source documents (§20 Q31).

**OQ-9 — Whether Eyes on Flock / HIBF collaboration will yield a feed** (§17 Stage 0). The `partner_eyesonflock` connector is specified as a stub. If no feed materializes, SIG must decide whether to build an independent portal-discovery crawler — a decision with significant politeness and duplication implications (§19.5) that R11 deliberately does not pre-judge.

**OQ-10 — Data Package spec version.** The standard's structure was verified (F11.10) but a version string ("v2") was not surfaced. Pin the exact profile URL in `MANIFEST.json` when implementing.

---

## Spec requirements emitted

Each is concrete and testable. Test ids in brackets refer to §4.2 where a mechanized check exists.

**Connector architecture**

- **REQ-R11-01** — Every source adapter MUST implement the eight-stage `Connector` interface (§1.3). CI MUST fail if a class in `connectors/` does not satisfy the protocol.
- **REQ-R11-02** — `parse()`, `extract()`, and `normalize()` MUST be pure functions of their inputs plus a declared code version. No network, clock, randomness, or locale dependence. [RP-1; ruff `DTZ`]
- **REQ-R11-03** — Source snapshots MUST be content-addressed by lowercase-hex SHA-256 of the raw response bytes, stored at `sha256/<aa>/<bb>/<hex>`, and never mutated or overwritten. [T-DUP-4, T-REF-1] *(answers Q25)*
- **REQ-R11-04** — Parsed documents MUST carry a `canonical_sha256` over canonically-serialized JSON, used for change detection. [T-SCH-3]
- **REQ-R11-05** — `fetch()` MUST return `Unavailable` rather than raise for every condition in `UnavailableReason`; every `Unavailable` MUST write a `SourceUnavailableEvent`. A run consisting solely of unavailability MUST be recorded as successful.
- **REQ-R11-06** — Connectors MUST define an escalation policy from repeated unavailability to a domain event; Flock portals MUST escalate 3 consecutive 404/410 to `PortalDisappearedEvent`, which MUST generate an evidence-backed negative claim. *(implements §2 Layer B)*
- **REQ-R11-07** — Change detection MUST operate on structural diff of extracted canonical JSON. Diffing raw HTML or rendered text is prohibited. Changes MUST be emitted as per-field `FieldChange` events with a typed `kind`.
- **REQ-R11-08** — A `structure_changed` field-change on a previously-stable source MUST raise a parser-drift alert. [§4.3 canary]
- **REQ-R11-09** — All outbound HTTP MUST pass through a single `PolitenessGateway` enforcing per-host **and per-path** budgets, strict per-host serialization, Protego-parsed robots.txt with crawl-delay as a floor, a documented UA with contact, conditional requests, and adaptive de-escalation on 429/503. Connectors MUST NOT import an HTTP client directly. [import-linter check]
- **REQ-R11-10** — Politeness budgets MUST live in version-controlled `ops/politeness.toml`; a connector MUST NOT be able to raise its own budget in code. Robots overrides MUST require a per-host signed entry with written justification.
- **REQ-R11-11** — The OSM connector MUST read `state.txt` to obtain sequence numbers, MUST NOT increment blindly, MUST treat a sequence gap as a halt-and-alert, and SHOULD default to regional daily diffs. *(F11.1)*
- **REQ-R11-12** — Overpass MUST be capped at ≤2,000 requests/day and ≤200 MB/day and MUST NOT be used for bulk ingestion. *(F11.3)*
- **REQ-R11-13** — Browser-based connectors MUST capture both the settled DOM and every intercepted XHR/JSON response as separate content-addressed snapshots, and MUST run under a global concurrency cap. *(F11.16)*

**Orchestration and lineage**

- **REQ-R11-14** — Orchestration MUST be Dagster OSS, self-hosted with a Postgres instance; `import dagster` MUST appear only under `orchestration/`. [import-linter check]
- **REQ-R11-15** — Every pipeline stage MUST be invocable from a CLI with no orchestrator present, and CI MUST exercise the full nightly pipeline via that CLI. *(the escape hatch, §3.3)*
- **REQ-R11-16** — Every claim MUST carry non-null `run_id`, `connector_version`, `parser_version`, `extractor_version`, `normalizer_version`, `snapshot_sha256`, `parsed_doc_sha`, `extraction_id`, and ≥1 source span. [T-SCH-4, T-SCH-5, T-REF-2]
- **REQ-R11-17** — Every `ingest_run` MUST record `code_commit`, `image_digest`, `ontology_version`, and an environment blob. [RP-3]
- **REQ-R11-18** — Claim identity MUST include extractor and normalizer versions, so that re-extraction produces new claims rather than mutations; `load()` MUST be idempotent on `claim_key`. [T-DUP-1]
- **REQ-R11-19** — Replay MUST operate exclusively on archived snapshots and MUST be unable to reach the network.
- **REQ-R11-20** — A replay MUST preserve `observation_time`, `valid_from`, and `valid_to` from the original source and MUST set `recorded_at = now()`. Backdating `recorded_at` is prohibited. [T-TIME-8]
- **REQ-R11-21** — Superseded claims MUST be retained with `superseded_by`, `superseded_at`, and a typed reason (`parser_improved` | `normalization_revised` | `human_correction`). `source_changed` MUST NOT be modelled as supersession.
- **REQ-R11-22** — Every replay/backfill command MUST support `--dry-run` producing counts by supersession reason plus ≥20 sampled side-by-side diffs with source spans.
- **REQ-R11-23** — SIG SHOULD emit OpenLineage events as a secondary output; OpenLineage MUST NOT be the system of record for claim-level provenance. *(F11.26)*

**Data quality and testing**

- **REQ-R11-24** — Soda Core MUST NOT be used. *(Elastic License 2.0 — F11.20)*
- **REQ-R11-25** — The quality stack MUST be Pandera (in-pipeline), a SQL invariant suite executed by pytest (zero-rows-pass, with severity thresholds per F11.27), and Pointblank for the published per-release quality report.
- **REQ-R11-26** — All checks in the §4.2 taxonomy MUST be implemented, tagged by cadence (PR/RUN/NIGHTLY/RELEASE) and severity, and their results published in the release quality report.
- **REQ-R11-27** — T-GEO-1 (point-in-claimed-jurisdiction) MUST be implemented, and its failures MUST populate a jurisdictional-anomaly review queue rather than only failing a build.
- **REQ-R11-28** — Count-plausibility violations MUST write the claim, raise a review task, and hold the derived projection at its prior value. They MUST NOT block the write. *(T-PLAUS-1)*
- **REQ-R11-29** — Every parser MUST have committed golden fixtures of real captured bytes with `expected.parsed.json` and `expected.claims.json`; fixtures MUST pass the privacy gate before commit; `bless` regeneration MUST require human review of the diff.
- **REQ-R11-30** — A nightly canary suite MUST fetch 4–8 live targets, assert structural shape, claim-yield within 0.5×–2× of trailing baseline, presence of required predicates, and a warning floor; failures MUST auto-open an issue with the new snapshot attached as a candidate fixture.
- **REQ-R11-31** — Entity resolution MUST be gated in CI at precision ≥ 0.98 and recall ≥ 0.85 against a versioned gold set containing an `ambiguous` class; gold sets MUST be versioned by filename and never edited in place.
- **REQ-R11-32** — PR CI MUST block all network access except in tests explicitly marked `network`, enforced by an autouse fixture.
- **REQ-R11-33** — Bitemporal invariants MUST be property-tested with Hypothesis, including as-of monotonicity under replay.

**Runtime, repo, reproducibility**

- **REQ-R11-34** — Primary language Python, `requires-python = ">=3.13,<3.15"`, tested on 3.13 and 3.14. *(F11.30)*
- **REQ-R11-35** — Monorepo with a uv workspace and the §5.2 package layout; import boundaries enforced by an automated check.
- **REQ-R11-36** — `ontology/` MUST be LinkML-authored, with generated Pydantic/JSON Schema/SHACL/docs committed and drift-checked in CI. [T-SCH-3]
- **REQ-R11-37** — Dependencies MUST be managed by uv with `uv.lock` committed; each release MUST additionally publish a PEP 751 `pylock.toml` and a CycloneDX SBOM. *(F11.33)*
- **REQ-R11-38** — "Reproducible ingestion" MUST mean, and be tested as, RP-1 determinism, RP-2 reconstructible artifacts (double-build checksum match), RP-3 auditable environment, and RP-4 replayable history (nightly 50-claim regeneration check). *(implements §14.3)*
- **REQ-R11-39** — Pipeline releases MUST build a container image from a pinned base digest, and the image digest MUST be recorded on every run.

**API and exports**

- **REQ-R11-40** — The public read API MUST be FastAPI-based, REST, versioned by URL prefix, cursor-paginated (no offsets), with a committed OpenAPI document diffed in CI.
- **REQ-R11-41** — Every read endpoint MUST accept `as_of` (transaction time) and `valid_at` (validity time) independently; omission means "now"; future `as_of` MUST return 400; effective values MUST be echoed in body and headers.
- **REQ-R11-42** — Responses for a past `as_of` MUST be marked immutable and long-cached; omitted `as_of` MUST NOT be rewritten to a timestamp at the edge.
- **REQ-R11-43** — Rate limiting MUST be enforced at the CDN edge with anonymous/registered/partner tiers; **bulk artifact downloads MUST NOT be rate limited**.
- **REQ-R11-44** — Every release MUST publish Parquet, CSV, JSONL, GeoJSON, PMTiles, JSON-LD/N-Triples, SQLite, and DuckDB artifacts to immutable paths, plus `MANIFEST.json`, `CHECKSUMS.txt`, a detached signature, a Pointblank quality report, and an SBOM.
- **REQ-R11-45** — `MANIFEST.json` MUST be a Data Package descriptor with per-resource `licenses` and a `sig` profile extension carrying DOI, ontology version, code commit, image digest, counts, and a `reproduce` command. *(F11.10)*
- **REQ-R11-46** — OSM-derived data MUST occupy physically separate resources declaring ODbL with attribution and a separability note; a release MUST fail if OSM-derived columns appear in a non-ODbL resource. [T-LIC-2] *(implements §14.1 Strategy A)*
- **REQ-R11-47** — Release versioning MUST be `sig-YYYY.0M.0D+<8-hex-content-hash>`; the ontology MUST be versioned separately with semver.
- **REQ-R11-48** — Only `latest.json` may be mutable in the releases bucket; all other release objects MUST be immutable.
- **REQ-R11-49** — Every release MUST be deposited to Zenodo, minting a version DOI recorded in the manifest and the `release` table, with the concept DOI cited as the dataset identity. *(F11.9)*
- **REQ-R11-50** — Export MUST fail closed on license: any row tracing to a source with `UNDETERMINED` or incompatible license blocks the release. [T-LIC-1]

**Deployment, observability, economics**

- **REQ-R11-51** — Primary object storage MUST be Cloudflare R2 (zero egress) with a Backblaze B2 mirror; S3 MUST NOT be the primary bulk-download origin. *(F11.35)*
- **REQ-R11-52** — Bootstrap deployment MUST fit within ≈$50/month and MUST be documented as a single reproducible topology.
- **REQ-R11-53** — Logs MUST be structured JSON carrying `run_id`, `connector_id`, `ref_key`, and `snapshot_sha256`; `Unavailable` MUST NOT be reported to the error tracker.
- **REQ-R11-54** — A public freshness dashboard MUST publish, per source: last **observed** successful capture, expected cadence, status including a distinct "unavailable" state with reason and date, a 90-day success sparkline, license status, and a machine-readable `freshness.json`. Scheduled cadence MUST NOT be presented as observed freshness.
- **REQ-R11-55** — Only four conditions may page: pipeline hard failure, release gate failure, politeness auto-pause, partner access revocation.
- **REQ-R11-56** — A `$0` degraded mode MUST be implemented and tested from Stage 1: SQLite `sig-store` backend, GitHub Actions cron pipeline, R2 free-tier publication, static site with Datasette Lite and PMTiles, and a weekly keepalive workflow defeating the 60-day scheduled-workflow auto-disable. *(F11.13, F11.12, F11.11, F11.35)*
- **REQ-R11-57** — Scheduled workflows MUST NOT be scheduled on the hour. *(F11.13)*

**LLM policy**

- **REQ-R11-58** — LLM outputs MUST enter the graph only as candidates with `review_status='pending'`; publication requires `human_confirmed`, `human_corrected`, or `auto_accepted` under a passing accuracy gate.
- **REQ-R11-59** — Every LLM-extracted field MUST carry a source span that the adapter mechanically verifies against the parsed document; unresolvable spans MUST cause outright rejection, not review. [T-SCH-6]
- **REQ-R11-60** — Confidence values MUST be computed from a documented rubric; model-emitted probabilities MUST be discarded at the adapter boundary. *(implements §9.3)*
- **REQ-R11-61** — LLMs MUST NOT authorize entity merges, clear content for publication, overwrite raw source text, or generate negative claims. *(implements Q28, §2 ALPR Watch, §19.2)*
- **REQ-R11-62** — Prompts MUST be versioned files, content-hashed, never edited in place; `model_id`, `prompt_sha256`, and `model_params_hash` MUST be recorded on every LLM extraction and enforced by a database CHECK constraint.
- **REQ-R11-63** — Human review sampling rates MUST follow §8.4's table, MUST be stratified and recorded, and MUST reset to 100% on any prompt or model change.
- **REQ-R11-64** — Extraction accuracy MUST be measured against a versioned gold set reporting precision, recall, span-validity, hallucination rate, **abstention rate**, and inter-annotator agreement; results MUST be published in the release quality report.
- **REQ-R11-65** — LLM extraction MUST use the Batch API with prompt caching, MUST record per-call token usage, MUST enforce a per-run token budget that stops rather than truncates, and MUST be a strictly optional stage — CI MUST verify the pipeline completes with the LLM adapter disabled. *(F11.37)*
