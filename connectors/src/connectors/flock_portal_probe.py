# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P36.74 — the probe-only Flock transparency-portal connector (WV-10 / ADR-188).

WV-10 waives SIG-INGEST-035's no-direct-capture clause for Flock transparency
portals ONLY, and only this far: one gentle, rate-limited GET per known portal
per run under the project UA (P35.38a), and the attempt STOPS on any bot
challenge, 403 or interstitial — recorded as a refusal with its kind. No
challenge-solving, header spoofing, proxy rotation or browser automation exists
anywhere in this module (SIG-INGEST-013, SIG-INGEST-036/037 stand), and a test
asserts none appears. The aggregator-source and compartment clauses of
SIG-INGEST-035 stand: Eyes on Flock remains the portal-layer source and probe
output lands in the CC BY-SA 4.0 ``portal`` compartment, never the CC-BY graph
(SIG-LIC-004a).

The probe set is **committed data, not discovery**: the portals already known
from the aggregator's inventory snapshot (``data/flock_portal_probe_targets.toml``,
917 portals — I3-L005), slug-sorted, with the snapshot's date and digest
recorded. ADR-188 adds no discovery method; a target outside the committed set
is refused at ``discover()``.

The served-page path, in order:

1. **mirror-schema parse** — the page's embedded JSON payload is read against
   the mirror's own aggregate-only field map (``flock_portal_vocab.toml``);
   out-of-scope keys are dropped and named on the outcome (never values);
   a payload carrying no portal object or contradicting the probed slug is
   refused whole (:class:`SchemaRefusal`);
2. **reconcile** — the served portal is reconciled against the mirror's entity
   set (existence claim keyed on the slug) and its configured-sharing edges run
   through P08.2's §29.3 reconciler, never re-implemented here;
3. **in-memory Part VIII screen** — the embedded payload AND the canonical
   extraction are screened via P34.49's machinery
   (:func:`evidence.screen.screen_blob` over the committed
   ``ops/at_rest_audit.toml`` declaration) before ANY persistence; a page
   surfacing SIG-PUB-002/I7/F-406-shaped fields anywhere is refused whole
   (:class:`ScreenedRefusal`) and its raw bytes are never written (ADR-185);
4. **verbatim terms capture** — the portal's terms/licence text is lifted
   verbatim (never normalized) into the screened artifact and the probe-run
   record's terms table;
5. **CC BY-SA 4.0 stamping** — every emitted row carries the ``portal``
   compartment and ``ai_training_permitted = false`` (SIG-LIC-004a/004b).

The vendor's raw page bytes are deliberately NOT archived: the screen's rule
table is defined over parsed field structure, so the honest pre-persistence
gate is to persist the screened extraction (``sig.flock-portal-page/1``) — the
bytes the screen demonstrably passed — never the page itself.

Every run yields exactly one ``sig.probe-run/1`` record
(:func:`probe_run_record`): per-portal ``served``/``refused`` outcomes with the
refusal kind, the inventory's provenance, the deduplicated verbatim terms, and
an output digest. An all-refused run is a PASS — expected yield today is ≈ 0
(F2.1) and a refusal is data, not an error to hide. A run that attempted
nothing is a FAIL (SIG-ENG-042).

The source row stays ``ingestion_permitted=false`` — activation is the
operator's P36.12 Wave-B execution under ING-GO-B; nothing here flips it.
"""

from __future__ import annotations

import json
import tomllib
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlsplit

from evidence.screen import ScreenDeclaration, declaration_from_table, screen_blob
from reconcile.sharing import SharingReconciliation, reconcile_sharing

from . import flock_portal
from ._data import load_table
from .disappearance import failing_status_for_error, failing_status_for_http
from .flock_portal import (
    CC_BY_SA_LICENSE,
    PORTAL_COMPARTMENT,
    declared_freshness_claim,
    fallback_tasks_for_gaps,
    field_claim,
    portal_exists_claim,
    portal_id,
    portal_snapshot_date,
    sharing_observations_for_portal,
    vocab,
    vocab_version,
)
from .net import ChallengeEncountered, HostOptOut, ReservationRefused
from .stages import (
    CaptureRef,
    Connector,
    FetchResult,
    RunContext,
    SchemaRefusal,
    ScreenedRefusal,
    content_digest,
    register,
)

if TYPE_CHECKING:
    from .pipeline import RunReport

#: The registry source this probe runs against — the pre-existing
#: link-only `flock_transparency_portals` row (stays ingestion_permitted=false
#: until the operator's P36.12 ING-GO-B flip).
PROBE_SOURCE_ID = "flock_transparency_portals"
PROBE_CONNECTOR_NAME = "flock_portal_probe"

#: Committed data tables (SIG-ENG-001).
_TARGETS_TABLE = "flock_portal_probe_targets"
_SCHEMA_TABLE = "flock_portal_probe_schema"

#: Record/page schemas.
PROBE_RUN_VERSION = "sig.probe-run/1"
PAGE_SCHEMA = "sig.flock-portal-page/1"
TARGETS_SCHEMA = "sig.flock-portal-probe-targets/1"
PROBE_SCHEMA_ID = "sig.flock-portal-probe-schema/1"

#: The stable probe identifier stamped on the run record (SIG-OPS-011 shape).
PROBE_ID = "flock-portal-probe"

#: The committed Part VIII screen declaration (P34.49 / ADR-185) — the SAME
#: document the at-rest audit parses, consumed through the same parser
#: (:func:`evidence.screen.declaration_from_table`) so a connector-side screen
#: is the auditable screen, never a drifted second copy. Resolves
#: repo-relative like ops' own loader; injectable for tests/relocations.
DEFAULT_SCREEN_DECLARATION = Path(__file__).resolve().parents[3] / "ops" / "at_rest_audit.toml"

#: Verbatim terms are captured whole but bounded (a runaway payload never
#: bloats the record); a truncated capture flags itself on the artifact.
_TERMS_CAP = 100_000

#: A served page's embedded data block: a JSON script island (the vendor page
#: is a JS app — ``__NEXT_DATA__``-style) is the only content surface the
#: mirror schema reads.
_JSON_SCRIPT_TYPES = frozenset({"application/json", "application/ld+json"})
_EMBEDDED_SCRIPT_IDS = frozenset(
    {
        "__next_data__",
        "__portal_data__",
        "portal-data",
        "portal_data",
        "flock-portal-data",
    }
)

#: HTML void elements — they never open a nesting depth for terms capture.
_VOID_TAGS = frozenset(
    {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }
)


# --- committed probe inventory ------------------------------------------------


@dataclass(frozen=True)
class ProbeTarget:
    """One known portal: an identifier and its URL — never content (SIG-INGEST-045i)."""

    slug: str
    url: str
    #: A portal-level opt-out recorded ahead of any fetch (§26 rule 7's
    #: portal-granular twin: the agency asked SIG to stop probing ITS portal
    #: out-of-band). Derived data carries none; the column exists so a recorded
    #: opt-out is honoured without a rebuild.
    opted_out: bool = False


@dataclass(frozen=True)
class ProbeInventory:
    """The committed probe set with its derivation provenance (ADR-188: none discovered)."""

    source_uri: str
    upstream_snapshot_date: str
    captured_on: str
    snapshot_sha256: str
    selection_rule: str
    upstream_portals: int
    waiver: str
    portals: tuple[ProbeTarget, ...]

    @property
    def urls(self) -> frozenset[str]:
        return frozenset(p.url for p in self.portals)

    @property
    def slug_for_url(self) -> dict[str, str]:
        return {p.url: p.slug for p in self.portals}

    def target(self, slug: str) -> ProbeTarget | None:
        for p in self.portals:
            if p.slug == slug:
                return p
        return None


def load_probe_inventory() -> ProbeInventory:
    """Parse + validate the committed probe target set (fail-closed on drift).

    A malformed inventory — wrong schema, unsorted or duplicate slugs, a URL
    that is not ``https://<host>/<slug>``, a ``portal_count`` that disagrees —
    refuses the load rather than probing outside the committed set.
    """
    table = load_table(_TARGETS_TABLE)
    if table.get("schema") != TARGETS_SCHEMA:
        raise ValueError(f"probe inventory schema must be {TARGETS_SCHEMA!r}")
    inv = table.get("inventory") or {}
    portals: list[ProbeTarget] = []
    opted = {str(s) for s in (inv.get("opted_out_portals") or [])}
    for i, row in enumerate(inv.get("portals") or []):
        if not isinstance(row, dict):
            raise ValueError(f"probe inventory portal {i} must be a table")
        slug = str(row.get("slug") or "")
        url = str(row.get("url") or "")
        if not slug or not url:
            raise ValueError(f"probe inventory portal {i} needs slug + url")
        parts = urlsplit(url)
        if parts.scheme != "https" or not parts.netloc or parts.path.strip("/") != slug:
            raise ValueError(
                f"probe inventory portal {i}: url {url!r} is not https://<host>/{slug}"
            )
        portals.append(ProbeTarget(slug=slug, url=url, opted_out=slug in opted))
    slugs = [p.slug for p in portals]
    if len(set(slugs)) != len(slugs):
        raise ValueError("probe inventory carries duplicate slugs")
    if slugs != sorted(slugs):
        raise ValueError("probe inventory is not slug-sorted (deterministic order required)")
    declared = int(inv.get("portal_count") or -1)
    if declared != len(portals):
        raise ValueError(
            f"probe inventory portal_count={declared} but {len(portals)} rows are committed"
        )
    return ProbeInventory(
        source_uri=str(inv.get("source_uri") or ""),
        upstream_snapshot_date=str(inv.get("upstream_snapshot_date") or ""),
        captured_on=str(inv.get("captured_on") or ""),
        snapshot_sha256=str(inv.get("snapshot_sha256") or ""),
        selection_rule=str(inv.get("selection_rule") or ""),
        upstream_portals=int(inv.get("upstream_portals") or 0),
        waiver=str(inv.get("waiver") or ""),
        portals=tuple(portals),
    )


def probe_targets() -> list[dict[str, str]]:
    """The ``{"id","url","kind"}`` targets ``live_targets.toml`` delegates to.

    Identifiers only — the committed known-portal list; the connector's
    ``discover()`` falls back to exactly this when no ``parameters["targets"]``
    bound the run.
    """
    return _targets_for(load_probe_inventory())


def _targets_for(inventory: ProbeInventory) -> list[dict[str, str]]:
    """The ``{"id","url","kind","subject_id"}`` rows for one inventory."""
    return [
        {
            "id": p.slug,
            "url": p.url,
            "kind": "portal_page",
            "subject_id": portal_id(p.slug),
        }
        for p in inventory.portals
    ]


# --- the mirror schema (data, not code) ----------------------------------------


def probe_schema() -> Mapping[str, Any]:
    """The committed probe mirror schema (``flock_portal_probe_schema.toml``)."""
    table = load_table(_SCHEMA_TABLE)
    if table.get("schema") != PROBE_SCHEMA_ID:
        raise ValueError(f"probe schema must be {PROBE_SCHEMA_ID!r}")
    return table


def allowed_field_names() -> frozenset[str]:
    """Every upstream key the mirror vocabulary admits — the aggregate-only set.

    The union of the vocab's mapped field names, the identity/context fields,
    the two sharing-list fields and the declared-freshness field — the mirror's
    own portal schema, shared verbatim (P36.74: "parsed with the mirror's
    portal schema"). Aggregate-only by construction: no per-search, per-plate
    or per-person field exists in it.
    """
    v = vocab()
    identity = v.get("identity") or {}
    sharing = v.get("sharing") or {}
    names: set[str] = set()
    names.update(str(k) for k in (v.get("fields") or {}).keys())
    names.update(str(f) for f in (identity.get("context_fields") or ()))
    for key in ("slug_field", "portal_url_field"):
        if identity.get(key):
            names.add(str(identity[key]))
    for key in ("shared_with_field", "received_from_field"):
        if sharing.get(key):
            names.add(str(sharing[key]))
    if v.get("snapshot_field"):
        names.add(str(v["snapshot_field"]))
    return frozenset(names)


def _denied_patterns() -> tuple[str, ...]:
    """The refused field-name globs (per-search/per-plate/per-person surface)."""
    return tuple(str(p).lower() for p in probe_schema().get("denied_fields") or ())


def _terms_field_names() -> frozenset[str]:
    return frozenset(str(f).lower() for f in probe_schema().get("terms_fields") or ())


def _terms_element_ids() -> frozenset[str]:
    return frozenset(str(f).lower() for f in probe_schema().get("terms_element_ids") or ())


def _interstitial_markers() -> tuple[str, ...]:
    return tuple(str(m).lower() for m in probe_schema().get("interstitial_markers") or ())


def _iter_dicts(node: Any) -> Iterable[dict[str, Any]]:
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from _iter_dicts(v)
    elif isinstance(node, list):
        for item in node:
            yield from _iter_dicts(item)


def _denied_keys(doc: Any) -> list[str]:
    """Denied field NAMES present in the embedded payload — names, never values."""
    import fnmatch

    patterns = _denied_patterns()
    allowed = {n.lower() for n in allowed_field_names()}
    terms = _terms_field_names()
    hits: set[str] = set()
    for d in _iter_dicts(doc):
        for k in d.keys():
            kl = str(k).lower()
            if kl in allowed or kl in terms:
                continue
            if any(fnmatch.fnmatch(kl, p) for p in patterns):
                hits.add(str(k))
    return sorted(hits)


# --- the committed Part VIII screen declaration --------------------------------


def load_screen_declaration(path: str | Path | None = None) -> ScreenDeclaration:
    """The committed ``sig.at-rest-audit-decl/1`` — one parser, one document.

    Parsed through :func:`evidence.screen.declaration_from_table`, the same
    TOML→declaration mapping ``ops.at_rest_audit`` uses, so the connector's
    in-memory screen applies the committed rule table byte-for-byte (ADR-185).
    """
    p = Path(path) if path else DEFAULT_SCREEN_DECLARATION
    raw = tomllib.loads(p.read_text(encoding="utf-8"))
    return declaration_from_table(raw, source=str(p))


# --- the served-page record -----------------------------------------------------


@dataclass(frozen=True)
class ServedPage:
    """The in-memory mirror-schema extraction of one served portal page.

    Carries only what the schema admits: the flat allowlisted field map
    (``portal``), the verbatim terms text, and the refused field NAMES. The raw
    page bytes are never stored.
    """

    slug: str
    url: str
    portal: Mapping[str, Any]
    terms_text: str | None
    terms_truncated: bool
    refused_fields: tuple[str, ...]

    def terms_digest(self) -> str | None:
        """The content digest (base32 multihash) the terms table + outcome rows reference."""
        if not self.terms_text:
            return None
        return content_digest({"terms": self.terms_text})

    def record(self) -> dict[str, Any]:
        """The canonical persisted artifact — the ONLY bytes capture() stores."""
        return {
            "schema": PAGE_SCHEMA,
            "slug": self.slug,
            "url": self.url,
            "portal": dict(self.portal),
            "terms_text": self.terms_text,
            "terms_digest": self.terms_digest(),
            "terms_truncated": self.terms_truncated,
            "refused_fields": list(self.refused_fields),
        }

    def record_bytes(self) -> bytes:
        return json.dumps(self.record(), sort_keys=True, ensure_ascii=False).encode("utf-8")


@dataclass(frozen=True)
class ParsedPage:
    """parse_portal_page's output: the extraction + the raw embedded payloads.

    ``payloads`` is the embedded-JSON material the page served — held only in
    memory, screened before persistence, and never stored. It exists so the
    in-memory screen examines what the page actually carried (a denied field's
    presence is itself a screenable hazard), not only what we kept.
    """

    page: ServedPage
    payloads: tuple[Any, ...]


# --- page parsing (pure — HTML + embedded JSON) ---------------------------------


class _PageScanner(HTMLParser):
    """Lift the embedded JSON blocks and terms blocks out of a served page."""

    def __init__(self, terms_ids: frozenset[str]) -> None:
        super().__init__(convert_charrefs=True)
        self._terms_ids = terms_ids
        self.json_blocks: list[str] = []
        self.terms_blocks: list[str] = []
        self.license_links: list[dict[str, str]] = []
        self._script_buf: list[str] | None = None
        self._terms_tag: str | None = None
        self._terms_depth = 0
        self._terms_buf: list[str] = []
        self._license_buf: list[str] | None = None
        self._license_href = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {k.lower(): (v or "") for k, v in attrs}
        if tag == "script":
            mtype = attr.get("type", "").split(";")[0].strip().lower()
            sid = attr.get("id", "").strip().lower()
            if mtype in _JSON_SCRIPT_TYPES or sid in _EMBEDDED_SCRIPT_IDS:
                self._script_buf = []
        elif tag == "meta" and attr.get("name", "").lower() in self._terms_ids:
            content = attr.get("content", "")
            if content.strip():
                self.terms_blocks.append(content)
        elif tag == "a" and "license" in {r.strip().lower() for r in attr.get("rel", "").split()}:
            self._license_buf = []
            self._license_href = attr.get("href", "")
        if tag.lower() in _VOID_TAGS:
            return
        if self._terms_tag is not None:
            self._terms_depth += 1
            return
        tid = attr.get("id", "").strip().lower()
        classes = {c.lower() for c in attr.get("class", "").split()}
        if tid in self._terms_ids or (classes & self._terms_ids):
            self._terms_tag = tag
            self._terms_depth = 1
            self._terms_buf = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._script_buf is not None:
            self.json_blocks.append("".join(self._script_buf))
            self._script_buf = None
        if tag == "a" and self._license_buf is not None:
            text = "".join(self._license_buf).strip()
            self.license_links.append({"text": text, "href": self._license_href})
            self._license_buf = None
            self._license_href = ""
        if self._terms_tag is not None:
            self._terms_depth -= 1
            if self._terms_depth <= 0:
                text = "".join(self._terms_buf)
                if text.strip():
                    self.terms_blocks.append(text)
                self._terms_tag = None
                self._terms_buf = []

    def handle_data(self, data: str) -> None:
        if self._script_buf is not None:
            self._script_buf.append(data)
        if self._license_buf is not None:
            self._license_buf.append(data)
        if self._terms_tag is not None:
            self._terms_buf.append(data)


class PortalSchemaError(ValueError):
    """An embedded payload cannot satisfy the mirror schema (internal signal)."""


def _looks_like_interstitial(body: bytes) -> bool:
    """Whether the served 2xx body is a bot-management stub, not a portal page.

    The markers are committed data (``interstitial_markers``) — a 2xx challenge
    page is a refusal kind exactly like a 403 under WV-10.
    """
    head = body[:65_536].decode("utf-8", errors="replace").lower()
    return any(m in head for m in _interstitial_markers())


def _scalar_or_scalar_list(value: Any) -> bool:
    """Aggregate-only shape: a scalar or a flat list of scalars.

    A dict or list-of-dicts is row-level material — refused.
    """
    if isinstance(value, dict):
        return False
    if isinstance(value, list):
        return all(not isinstance(v, (dict, list)) for v in value)
    return True


def parse_portal_page(body: bytes, *, url: str, slug: str) -> ParsedPage:
    """Mirror-schema parse of a served portal page (stage 1 of the served path).

    Extracts the allowlisted aggregate fields from every embedded JSON block,
    lifts the terms text verbatim, and records refused field names — a pure
    function of the bytes. Raises :class:`PortalSchemaError` when no parseable
    portal payload exists or the payload's declared slug contradicts the
    probed target (identity mismatch — the page is refused, never guessed).
    """
    text = body.decode("utf-8", errors="replace")
    scanner = _PageScanner(_terms_element_ids())
    scanner.feed(text)
    scanner.close()

    payloads: list[Any] = []
    for block in scanner.json_blocks:
        try:
            payloads.append(json.loads(block))
        except (json.JSONDecodeError, ValueError):
            continue
    if not payloads:
        raise PortalSchemaError(
            "no embedded JSON payload — the page is not readable under the mirror schema"
        )

    allowed = allowed_field_names()
    portal: dict[str, Any] = {}
    refused: set[str] = set()
    slug_mismatch = False
    for doc in payloads:
        refused.update(_denied_keys(doc))
        for d in _iter_dicts(doc):
            for key, value in d.items():
                kl = str(key).lower()
                if kl == "slug" and isinstance(value, str) and value.strip():
                    if value.strip() != slug:
                        slug_mismatch = True
                if key not in allowed or key in portal:
                    continue
                if _scalar_or_scalar_list(value):
                    portal[key] = value
                else:
                    # Row-level material under an allowlisted key — the field is
                    # refused, never partially extracted.
                    refused.add(str(key))
    if slug_mismatch:
        raise PortalSchemaError("embedded payload declares a different portal slug")
    if not portal:
        raise PortalSchemaError(
            "no portal object under the mirror schema — the payload carries no "
            "allowlisted portal field"
        )

    terms_text = _terms_text(payloads, scanner)
    truncated = False
    if terms_text is not None and len(terms_text) > _TERMS_CAP:
        terms_text = terms_text[:_TERMS_CAP]
        truncated = True
    return ParsedPage(
        page=ServedPage(
            slug=slug,
            url=url,
            portal=portal,
            terms_text=terms_text,
            terms_truncated=truncated,
            refused_fields=tuple(sorted(refused)),
        ),
        payloads=tuple(payloads),
    )


def _terms_text(payloads: Sequence[Any], scanner: _PageScanner) -> str | None:
    """The portal's terms/licence text, VERBATIM — never normalized or paraphrased.

    Order: the embedded payload's terms fields (document order), then the
    HTML terms element, then a ``rel=license`` link rendered as
    ``"<text> (<href>)"``. ``None`` is an honest absence, never a fabrication.
    """
    names = _terms_field_names()
    for doc in payloads:
        for d in _iter_dicts(doc):
            for key, value in d.items():
                if str(key).lower() in names and isinstance(value, str) and value.strip():
                    return value
    if scanner.terms_blocks:
        return scanner.terms_blocks[0]
    for link in scanner.license_links:
        label = link["text"] or link["href"]
        if label:
            return f"{label} ({link['href']})" if link["href"] else label
    return None


# --- refusal types local to the probe -------------------------------------------


class InterstitialEncountered(ChallengeEncountered):
    """A 2xx bot-management interstitial — a challenge, recorded as such.

    WV-10: "any challenge, 403 or interstitial ends that portal's attempt". A
    subclass of :class:`ChallengeEncountered` so the driver records the
    ``access_restricted`` disappearance through the unchanged machinery; the
    probe's own ledger keeps the finer ``interstitial`` kind.
    """

    def __init__(self, url: str) -> None:
        super().__init__(
            f"{url!r} served a bot-management interstitial (2xx stub, not the "
            "portal page); the attempt ends here (WV-10/ADR-188) — recorded, "
            "never defeated (SIG-INGEST-013).",
            status=200,
        )


class PortalOptedOut(HostOptOut):
    """A portal-level opt-out: the agency asked SIG to stop probing ITS portal.

    The host-level register (§26 rule 7) is consulted by the shared fetcher
    before any egress; the committed inventory's ``opted_out_portals`` list is
    its portal-granular counterpart, checked in ``fetch()`` before the request
    is issued. A subclass of :class:`HostOptOut` so the driver's rights-refusal
    path records it unchanged.
    """

    def __init__(self, slug: str, url: str) -> None:
        self.slug = slug
        super().__init__(url, urlsplit(url).netloc, f"portal {slug!r} is opted out of probing")


# --- the connector ----------------------------------------------------------------


@register
class FlockPortalProbeConnector(Connector):
    """The `flock_portal_probe` connector — WV-10/ADR-188 probe-only.

    One polite GET per committed portal per run through the shared politeness
    layer (opt-out → robots-recorded → rate-limited → challenge-raising). The
    connector holds no HTTP client, no credential, no retry, and no
    circumvention capability of any kind.
    """

    name = PROBE_CONNECTOR_NAME
    version = "1.0.0"

    def __init__(
        self,
        *,
        inventory: ProbeInventory | None = None,
        screen: ScreenDeclaration | None = None,
        screen_declaration_path: str | Path | None = None,
    ) -> None:
        self._inventory = inventory or load_probe_inventory()
        self._screen = screen or load_screen_declaration(screen_declaration_path)
        #: The run's per-portal outcome ledger — one row per attempted target,
        #: the probe-run record's raw material. ``served``/``refused`` +
        #: refusal kind + counts-only screen detail; never content.
        self.outcomes: list[dict[str, Any]] = []
        #: Served pages this run parsed (fetch → capture handoff AND the
        #: verbatim-terms surface the run record reads). Bounded by the served
        #: count — today ≈ 0.
        self._served: dict[str, ServedPage] = {}

    # -- acquisition --

    def discover(self, ctx: RunContext) -> list[Mapping[str, Any]]:
        """The committed probe set — identifiers, not content (SIG-INGEST-045i).

        ``parameters["targets"]`` (live_targets rows or a fixture subset) bound
        the run but must stay inside the committed inventory: a target outside
        it is discovery — refused loud, per WV-10/ADR-188.
        """
        given = ctx.parameters.get("targets")
        if not given:
            return [dict(t) for t in _targets_for(self._inventory)]
        known = self._inventory.urls
        by_url = self._inventory.slug_for_url
        out: list[Mapping[str, Any]] = []
        for t in given:
            url = str(t.get("url") or "")
            if url not in known:
                raise ValueError(
                    f"target {url!r} is not in the committed probe inventory — "
                    "ADR-188 adds no discovery method; refusing to probe outside "
                    "the known-portal set (WV-10)"
                )
            row = dict(t)
            row.setdefault("id", by_url[url])
            row.setdefault("subject_id", portal_id(str(row["id"])))
            out.append(row)
        return out

    def fetch(self, ctx: RunContext, target: Mapping[str, Any]) -> FetchResult:
        """The single polite probe request; the ONLY egress (SIG-INGEST-011).

        Order of the served path: portal opt-out → politeness fetch →
        interstitial check → mirror-schema parse → in-memory Part VIII screen
        → admit. Every outcome is recorded on the run ledger BEFORE the
        exception carries it to the driver's recorded-disposition paths.
        """
        assert ctx.fetcher is not None, "connectors fetch only through the shared layer"
        url = str(target["url"])
        slug = str(target.get("id") or self._inventory.slug_for_url.get(url) or url)
        opted = self._inventory.target(slug)
        if opted is not None and opted.opted_out:
            # §26 rule 7 at portal granularity — zero egress for this portal.
            self.outcomes.append(
                {
                    "portal": slug,
                    "url": url,
                    "result": "refused",
                    "refusal_kind": "PortalOptedOut",
                }
            )
            raise PortalOptedOut(slug, url)
        try:
            result = ctx.fetcher.fetch(url)
        except HostOptOut:
            self.outcomes.append(
                {"portal": slug, "url": url, "result": "refused", "refusal_kind": "opt_out"}
            )
            raise
        except ReservationRefused as exc:
            self.outcomes.append(
                {
                    "portal": slug,
                    "url": url,
                    "result": "refused",
                    "refusal_kind": "rights_reservation",
                    "signals": sorted({s.kind for s in exc.verdict.signals}),
                }
            )
            raise
        except ChallengeEncountered as exc:
            self.outcomes.append(
                {
                    "portal": slug,
                    "url": url,
                    "result": "refused",
                    "refusal_kind": "challenge",
                    "status": exc.status,
                }
            )
            raise
        except Exception as exc:
            # A transport-level failure — recorded as unreachable; anything
            # else propagates unrecorded (the run record's coverage check
            # catches an unmeasured fetch as a FAIL, never silent).
            if failing_status_for_error(exc) is not None:
                self.outcomes.append(
                    {
                        "portal": slug,
                        "url": url,
                        "result": "refused",
                        "refusal_kind": "unreachable",
                    }
                )
            raise
        status = int(result.status)
        if failing_status_for_http(status) is not None:
            # A mapped failing status (404/410/401/451) — the driver records
            # the disappearance; the ledger keeps the precise HTTP kind.
            self.outcomes.append(
                {
                    "portal": slug,
                    "url": url,
                    "result": "refused",
                    "refusal_kind": f"http_{status}",
                    "status": status,
                }
            )
            return result
        if _looks_like_interstitial(result.body):
            self.outcomes.append(
                {
                    "portal": slug,
                    "url": url,
                    "result": "refused",
                    "refusal_kind": "interstitial",
                    "status": status,
                }
            )
            raise InterstitialEncountered(url)
        try:
            parsed = parse_portal_page(result.body, url=url, slug=slug)
        except PortalSchemaError as exc:
            self.outcomes.append(
                {
                    "portal": slug,
                    "url": url,
                    "result": "refused",
                    "refusal_kind": "schema_refusal",
                    "detail": str(exc),
                }
            )
            raise SchemaRefusal(url, reason=str(exc)) from exc
        # ADR-185 persistence rule — the screen runs IN MEMORY before any
        # bytes are persisted, over BOTH the embedded payload the page served
        # (a denied field's presence is a whole-page refusal) and the
        # canonical extraction (the only bytes this connector writes).
        hits: dict[str, int] = {}
        for blob in (
            json.dumps(parsed.payloads, default=str).encode("utf-8"),
            parsed.page.record_bytes(),
        ):
            for cls, n in screen_blob(
                blob, source_id=PROBE_SOURCE_ID, media_type="application/json", decl=self._screen
            ).items():
                hits[cls] = hits.get(cls, 0) + int(n)
        if hits:
            self.outcomes.append(
                {
                    "portal": slug,
                    "url": url,
                    "result": "refused",
                    "refusal_kind": "screened",
                    "screen_hits": {k: int(v) for k, v in sorted(hits.items())},
                }
            )
            raise ScreenedRefusal(url, classes=sorted(hits), hits=hits)
        page = parsed.page
        self._served[url] = page
        self.outcomes.append(
            {
                "portal": slug,
                "url": url,
                "result": "served",
                "fields_extracted": len(page.portal),
                "fields_refused": list(page.refused_fields),
                "terms_captured": page.terms_text is not None,
                "terms_digest": page.terms_digest(),
                "screen": "clean",
            }
        )
        return result

    def capture(self, ctx: RunContext, fetched: FetchResult) -> CaptureRef:
        """Persist the screened extraction — NEVER the vendor's raw page bytes.

        ``sig.flock-portal-page/1`` (allowlisted fields + verbatim terms +
        refused field names) is the only artifact this connector stores: the
        bytes the in-memory screen demonstrably passed (ADR-185). The served
        HTML is held in memory for the fetch → capture handoff and dropped.
        """
        page = self._served.get(fetched.url)
        if page is None:
            # Defensive path (a capture handed a FetchResult that never passed
            # through this connector's fetch — e.g. a resumed mark): re-derive
            # through the same pure parser and re-screen before persistence.
            slug = self._inventory.slug_for_url.get(fetched.url)
            if slug is None:
                raise ValueError(f"{fetched.url!r} is outside the committed probe inventory")
            reparsed = parse_portal_page(fetched.body, url=fetched.url, slug=slug)
            hits = screen_blob(
                reparsed.page.record_bytes(),
                source_id=PROBE_SOURCE_ID,
                media_type="application/json",
                decl=self._screen,
            )
            if hits:
                raise ScreenedRefusal(fetched.url, classes=sorted(hits), hits=hits)
            page = reparsed.page
        return ctx.captures.put(
            page.record_bytes(),
            media_type="application/json",
            source_uri=fetched.url,
            retrieved_at=fetched.retrieved_at,
        )

    # -- interpretation (pure functions of the screened capture) --

    def parse(self, ctx: RunContext, capture: CaptureRef) -> dict[str, Any]:
        """Read back the screened ``sig.flock-portal-page/1`` artifact (pure)."""
        doc = json.loads(ctx.captures.get(capture.digest).decode("utf-8"))
        if doc.get("schema") != PAGE_SCHEMA:
            raise ValueError(f"capture {capture.digest} is not a {PAGE_SCHEMA} page record")
        doc["_capture_digest"] = capture.digest
        doc["_retrieved_at"] = capture.retrieved_at.isoformat() if capture.retrieved_at else None
        return doc

    def extract(self, ctx: RunContext, parsed: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        """One raw record per served portal — preserving raw values (P2)."""
        return [
            {
                "record_kind": "flock_portal_probe_page",
                "slug": str(parsed["slug"]),
                "portal": dict(parsed.get("portal") or {}),
                "terms_text": parsed.get("terms_text"),
                "terms_digest": parsed.get("terms_digest"),
                "terms_truncated": bool(parsed.get("terms_truncated")),
                "refused_fields": list(parsed.get("refused_fields") or []),
                "capture_digest": str(parsed.get("_capture_digest", "")),
                "retrieved_at": parsed.get("_retrieved_at"),
            }
        ]

    def normalize(
        self, ctx: RunContext, raw_claims: list[Mapping[str, Any]]
    ) -> list[dict[str, Any]]:
        """Reconcile + claim, in the served-page order, stamped CC-BY-SA portal.

        Per portal: existence claim + declared-freshness + one claim per
        allowlisted field (the mirror's predicate map — aggregate-only), plus
        fallback routes for absent fields; then the served set's sharing edges
        through P08.2's §29.3 reconciler. Every row is stamped to the probe
        source (never the aggregator's id) with the ``portal`` compartment and
        ``ai_training_permitted = false``.
        """
        attribution = _probe_attribution(ctx)
        out: list[dict[str, Any]] = []
        portals: list[Mapping[str, Any]] = []
        for raw in raw_claims:
            slug = str(raw["slug"])
            portal = dict(raw["portal"])
            portals.append(portal)
            capture_digest = str(raw.get("capture_digest", ""))
            declared = portal_snapshot_date(portal)
            observed = _observed_date(raw.get("retrieved_at")) or declared
            out.append(portal_exists_claim(slug, observed, True, attribution=attribution))
            out.append(
                declared_freshness_claim(slug, portal, capture_digest, attribution=attribution)
            )
            for upstream_field in vocab()["fields"]:
                if upstream_field not in portal:
                    continue
                claim = field_claim(
                    slug,
                    upstream_field,
                    portal[upstream_field],
                    declared,
                    capture_digest,
                    attribution=attribution,
                )
                if claim is not None:
                    out.append(claim)
            out.extend(fallback_tasks_for_gaps(portal, slug, attribution=attribution))
        # Reconcile the configured-sharing edges across the served portals —
        # P08.2's reconciler consumed, never re-implemented (§29.3). Only the
        # deterministic edges enter the claim stream, same as the mirror.
        out.extend(
            flock_portal._sharing_edge_rows(
                self.reconcile_sharing(portals), attribution=attribution
            )
        )
        # The probe's own source id — never the aggregator's — on every row.
        for row in out:
            row["source_id"] = PROBE_SOURCE_ID
        return out

    def reconcile_sharing(self, portals: Iterable[Mapping[str, Any]]) -> SharingReconciliation:
        """P08.2's §29.3 reconciler over the served portals' sharing lists."""
        observations = []
        for portal in portals:
            slug = str(portal.get(str(vocab()["identity"]["slug_field"]), "")).strip()
            observed_at = portal_snapshot_date(portal)
            if not slug or observed_at is None:
                continue
            observations.extend(sharing_observations_for_portal(portal, slug, observed_at))
        return reconcile_sharing(observations)

    def link(self, ctx: RunContext, normalized: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Attach the partner's portal entity-ref to sharing-edge claims (P31.6)."""
        out: list[dict[str, Any]] = []
        for row in normalized:
            if (
                row.get("record_kind") == "claim"
                and row.get("predicate_id") == "configured_sharing_partner"
                and not row.get("object_ref")
                and str(row.get("to_org") or "").strip()
            ):
                row = dict(row)
                row["object_ref"] = flock_portal._portal_partner_ref(str(row["to_org"]))
            out.append(row)
        return out

    def load(self, ctx: RunContext, linked: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Produce the L1 rows; the driver asserts them (live only)."""
        return flock_portal.load_claims_for_l1(linked)


# --- the probe-run record (sig.probe-run/1) --------------------------------------


def _observed_date(raw: Any) -> date | None:
    """The capture's retrieval date — SIG's own observation time for a served page."""
    if isinstance(raw, datetime):
        return raw.date()
    if isinstance(raw, date):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            return datetime.fromisoformat(raw.strip()).date()
        except ValueError:
            try:
                return date.fromisoformat(raw.strip()[:10])
            except ValueError:
                return None
    return None


def _probe_attribution(ctx: RunContext) -> str:
    """The probe source's recorded attribution (its rights block)."""
    try:
        return ctx.source.rights.attribution
    except AttributeError:  # pragma: no cover - defensive; ctx.source is a SourceRecord
        return "Flock Safety transparency portal (served page under WV-10/ADR-188)"


def _utcnow() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def probe_run_record(
    connector: FlockPortalProbeConnector,
    report: RunReport,
    *,
    run_id: str,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Build the run's single ``sig.probe-run/1`` record (SIG-OPS-011 shape).

    One record per run, one result row per committed portal — ``served``,
    ``refused`` (with its kind), ``deferred`` (budget/limit), ``resumed`` or
    ``not_attempted``. Counts-only: field NAMES and screen CLASS counts, never
    a value. The verbatim terms texts deduplicate into ``terms`` keyed by
    digest — the verbatim-terms capture on the rights-record surface.
    """
    inv = connector._inventory
    outcomes = {str(o["portal"]): o for o in connector.outcomes}
    capture_by_url = {c.source_uri: c.digest for c in report.captures}
    disappeared = {str(d.event.artifact_id): d.event.failing_status for d in report.disappearances}
    skipped = {str(s.get("id")): str(s.get("reason")) for s in report.sweep_skipped}
    resumed_keys = [str(r.get("target", "")) for r in report.resumed]
    claims_by_subject: dict[str, int] = {}
    for c in report.claims:
        sid = str(c.get("subject_id") or "")
        if sid:
            claims_by_subject[sid] = claims_by_subject.get(sid, 0) + 1

    terms_table: dict[str, str] = {}
    for page in connector._served.values():
        if page.terms_text:
            terms_table[str(page.terms_digest())] = page.terms_text

    results: list[dict[str, Any]] = []
    for t in inv.portals:
        o = outcomes.get(t.slug)
        row: dict[str, Any] = {"portal": t.slug, "url": t.url}
        if o is not None:
            row.update({k: v for k, v in o.items() if k not in {"portal", "url"}})
            if o.get("result") == "served":
                digest = capture_by_url.get(t.url)
                if digest:
                    row["capture_digest"] = digest
                row["claims"] = claims_by_subject.get(portal_id(t.slug), 0)
        elif t.slug in skipped:
            row.update({"result": "deferred", "refusal_kind": skipped[t.slug]})
        elif t.slug in disappeared:
            row.update({"result": "refused", "refusal_kind": disappeared[t.slug]})
        elif any(k.startswith(f"{t.url}#") for k in resumed_keys):
            row.update({"result": "served", "resumed": True})
        else:
            row["result"] = "not_attempted"
        results.append(row)

    attempted = sum(1 for r in results if r["result"] in {"served", "refused"})
    served = sum(1 for r in results if r["result"] == "served")
    refused = sum(1 for r in results if r["result"] == "refused")
    deferred = sum(1 for r in results if r["result"] == "deferred")
    # SIG-ENG-042: a run that attempted nothing measured nothing — FAIL. And
    # every fetch the driver issued MUST have a ledger outcome (an unmeasured
    # fetch means an exception slipped past the classifier — fail loud).
    coverage_ok = attempted > 0 and int(report.fetches) == len(connector.outcomes)
    overall = "pass" if coverage_ok else "fail"

    record: dict[str, Any] = {
        "version": PROBE_RUN_VERSION,
        "generated_at": generated_at or _utcnow(),
        "probe": PROBE_ID,
        "run_id": run_id,
        "source_id": PROBE_SOURCE_ID,
        "connector": f"{PROBE_CONNECTOR_NAME}/{connector.version}",
        "vocab_version": vocab_version(),
        "waiver": {
            "id": "WV-10",
            "adr": "ADR-188",
            "text": (
                "I waive INGEST-035's no-direct-capture clause; SIG may fetch "
                "Flock portal pages only when served without a challenge, and "
                "stops on any challenge."
            ),
        },
        "inventory": {
            "schema": TARGETS_SCHEMA,
            "source_uri": inv.source_uri,
            "upstream_snapshot_date": inv.upstream_snapshot_date,
            "snapshot_sha256": inv.snapshot_sha256,
            "selection_rule": inv.selection_rule,
            "portal_count": len(inv.portals),
        },
        "checks": {
            "coverage": {
                "verdict": "pass" if coverage_ok else "fail",
                "attempted": attempted,
                "of": len(inv.portals),
                "fetches": int(report.fetches),
            },
            "served": {"verdict": "pass", "count": served},
            "refusals": {"verdict": "pass", "count": refused, "deferred": deferred},
            "part_viii_screen": {
                "verdict": "pass",
                "screened": served,
                "refusals": sum(1 for r in results if r.get("refusal_kind") == "screened"),
            },
            "compartment": {
                "verdict": (
                    "pass"
                    if all(
                        c.get("compartment") == PORTAL_COMPARTMENT
                        and c.get("license") == CC_BY_SA_LICENSE
                        and c.get("ai_training_permitted") is False
                        for c in report.claims
                    )
                    else "fail"
                ),
                "claims": len(report.claims),
            },
        },
        "results": results,
        "terms": terms_table,
        "overall": overall,
    }
    record["output_digest"] = content_digest(
        {"results": results, "claims_fingerprint": report.fingerprint}
    )
    return record


def write_probe_run_record(record: Mapping[str, Any], directory: Path) -> Path:
    """Write the ``sig.probe-run/1`` record under the ops/probe-records surface.

    ``<directory>/<YYYY-MM-DD>/<generated_at>-<digest8>.json`` — append-only,
    one object per run, never an overwrite.
    """
    ts = str(record.get("generated_at") or _utcnow())
    day = ts[:10]
    digest = str(record.get("output_digest") or "nodigest")[:8]
    out = directory / day / f"{ts.replace(':', '-')}-{digest}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return out


__all__ = [
    "CC_BY_SA_LICENSE",
    "DEFAULT_SCREEN_DECLARATION",
    "PAGE_SCHEMA",
    "PORTAL_COMPARTMENT",
    "PROBE_CONNECTOR_NAME",
    "PROBE_ID",
    "PROBE_RUN_VERSION",
    "PROBE_SOURCE_ID",
    "TARGETS_SCHEMA",
    "FlockPortalProbeConnector",
    "InterstitialEncountered",
    "ParsedPage",
    "PortalOptedOut",
    "PortalSchemaError",
    "ProbeInventory",
    "ProbeTarget",
    "ServedPage",
    "allowed_field_names",
    "load_probe_inventory",
    "load_screen_declaration",
    "parse_portal_page",
    "probe_run_record",
    "probe_schema",
    "probe_targets",
    "write_probe_run_record",
]
