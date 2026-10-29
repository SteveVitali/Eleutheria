# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P36.76 — the Axon Fusus ``Connect <Place>`` connector + marked-host screen.

Row 351 lands the first-class connector the I7-C12 candidate anticipated: the
per-agency `Connect <Place>` / Fusus white-label camera-registration surfaces
(``data/axon_connect_targets.toml`` — the committed I9a-C003 site set, six
hosts) are read as **public programme facts only**. R11-A16's clause is the
spine: the connector emits programme facts — never registrant bytes — and the
community-camera presence is a SIG-ACQ-020 candidate-of-record, not a feed
(SIG-INGEST-034: identifiers only out of a connector; resolution lives
elsewhere).

Two bounded targets per committed site (leg A — the OM-20 row-351 mutation
GATE-G5 named verbatim on 2026-10-25T18:40Z):

* ``connect_page`` — ONE recorded GET of the site's public registration page.
  The HTML is parsed in memory to the allowlisted programme fields
  (``axon_connect_vocab.toml [page]``): programme name, modes offered
  (registration / integration), publisher, and verbatim stated-use clauses.
  Any embedded payload key matching the committed Part VIII field denylist
  (F-330, ``connectors.field_denylist``) is refused by name, and the whole
  parse plus the canonical record pass P34.49's in-memory screen
  (``ops/at_rest_audit.toml`` via ``evidence.screen``) **before any bytes are
  persisted** (ADR-185): a page surfacing registrant-shaped fields is a whole
  refusal (:class:`ScreenedRefusal`), never a warning.
* ``marked_host_screen`` — ONE recorded GET of
  ``https://<host>:8443/faststream/login.html``. The persisted artifact is the
  ``sig.fusus-screen/1`` record (host, screen URL, status, committed markers
  hit, ``recognised``, sha256 + byte size + retrieval instant) — the login
  page's own bytes are never stored. A recognised marked host emits an
  ``acquisition_candidate`` record row — the bounded candidate shape — never
  a feed row.

There is no discovery: ``discover()`` walks exactly the committed inventory
(a ``parameters["targets"]`` binding outside it is refused loud), one polite
GET per target through the shared layer — opt-out register first (§26 rule
7), site-level opt-out next, robots recorded under GL-GATE-08, rate-limited,
challenge-stopped (a 401/403/451/2xx-interstitial ends the target's attempt —
recorded, never defeated; SIG-INGEST-037 permits no circumvention,
challenge-solving, header spoofing, proxy rotation, credentials or browser
automation anywhere in this module, and a test asserts none exists).

The source row (``axon_connect``) stays ``ingestion_permitted=false`` —
SIG-INGEST-037/038's fail-closed posture stands: leg B, the first real host's
wire/fetch as a connector run, is the operator's act (OP-26), separately
authorised. Nothing here flips it.
"""

from __future__ import annotations

import hashlib
import json
import re
import tomllib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from evidence.screen import ScreenDeclaration, declaration_from_table, screen_blob

from ._data import load_table
from .disappearance import failing_status_for_error, failing_status_for_http
from .field_denylist import is_denied
from .flock_portal import load_claims_for_l1
from .net import ChallengeEncountered, HostOptOut, ReservationRefused
from .stages import (
    CaptureRef,
    Connector,
    FetchResult,
    RunContext,
    SchemaRefusal,
    ScreenedRefusal,
    register,
)

CONNECTOR_NAME = "axon_connect"
SOURCE_ID = "axon_connect"

_TARGETS_TABLE = "axon_connect_targets"
_VOCAB_TABLE = "axon_connect_vocab"

TARGETS_SCHEMA = "sig.axon-connect-targets/1"
VOCAB_SCHEMA_ID = "sig.axon-connect-vocab/1"
PAGE_SCHEMA = "sig.axon-connect-page/1"
SCREEN_SCHEMA = "sig.fusus-screen/1"

#: The committed Part VIII screen declaration (P34.49 / ADR-185) — the same
#: document the at-rest audit parses, consumed through the same parser so the
#: connector-side screen is the auditable screen, never a drifted copy.
DEFAULT_SCREEN_DECLARATION = Path(__file__).resolve().parents[3] / "ops" / "at_rest_audit.toml"

#: Verbatim clause/terms captures are bounded — a runaway block flags itself.
_CLAUSE_CAP = 2_000
_TERMS_CAP = 100_000

#: Artifact/event identity prefixes (§3.1): the Connect site page is the
#: programme-surface artifact; the marked host is the screened host artifact.
SITE_ID_PREFIX = "connect_site"
HOST_ID_PREFIX = "fusus_host"

_JSON_SCRIPT_TYPES = frozenset({"application/json", "application/ld+json"})


# --- the committed site inventory (data, not code) ----------------------------


@dataclass(frozen=True)
class ConnectSite:
    """One committed candidate site — identifiers + provenance, never content."""

    site: str
    host: str
    registration_url: str
    agency: str
    jurisdiction: str
    status: str
    expect: tuple[str, ...]
    evidence: str
    opted_out: bool = False

    @property
    def screen_url(self) -> str:
        """The marked-host screen URL — ``https://<host>:8443/faststream/login.html``."""
        screen = _vocab()["screen"]
        return f"https://{self.host}:{int(screen['port'])}{str(screen['path'])}"


@dataclass(frozen=True)
class ConnectInventory:
    """The committed candidate-site set with its derivation provenance."""

    source_ref: str
    evidence_ref: str
    captured_on: str
    selection_rule: str
    sites: tuple[ConnectSite, ...]

    @property
    def urls(self) -> frozenset[str]:
        return frozenset(t["url"] for t in _targets_for(self))

    def site(self, site_id: str) -> ConnectSite | None:
        for s in self.sites:
            if s.site == site_id:
                return s
        return None

    def site_for_url(self, url: str) -> ConnectSite | None:
        for s in self.sites:
            if url in {s.registration_url, s.screen_url}:
                return s
        return None


def _vocab() -> Mapping[str, Any]:
    """The committed ``sig.axon-connect-vocab/1`` table (fail-closed on drift)."""
    table = load_table(_VOCAB_TABLE)
    if table.get("schema") != VOCAB_SCHEMA_ID:
        raise ValueError(f"axon_connect vocabulary must be {VOCAB_SCHEMA_ID!r}")
    return table


def predicate_allowlist() -> frozenset[str]:
    """The predicates this connector may write (§23.4 closed allowlist)."""
    return frozenset(str(p) for p in _vocab().get("predicate_allowlist") or ())


class PredicateNotAllowed(Exception):
    """A schema error: the connector tried to write outside its predicate allowlist."""


def assert_predicate_allowed(predicate_id: str) -> str:
    if predicate_id not in predicate_allowlist():
        raise PredicateNotAllowed(
            f"predicate {predicate_id!r} is not in the axon_connect allowlist "
            f"({sorted(predicate_allowlist())})"
        )
    return predicate_id


def load_inventory() -> ConnectInventory:
    """Parse + validate the committed site set (fail-closed on drift).

    A malformed inventory — wrong schema, unsorted or duplicate site ids, a
    registration URL whose host disagrees with the row's ``host``, an
    ``expect`` list left empty (the identity check would be unenforceable), a
    ``site_count`` that disagrees — refuses the load rather than addressing
    outside the committed set.
    """
    table = load_table(_TARGETS_TABLE)
    if table.get("schema") != TARGETS_SCHEMA:
        raise ValueError(f"axon_connect inventory schema must be {TARGETS_SCHEMA!r}")
    inv = table.get("inventory") or {}
    opted = {str(s) for s in (inv.get("opted_out_sites") or [])}
    sites: list[ConnectSite] = []
    for i, row in enumerate(inv.get("sites") or []):
        if not isinstance(row, dict):
            raise ValueError(f"axon_connect inventory site {i} must be a table")
        site = str(row.get("site") or "")
        host = str(row.get("host") or "")
        url = str(row.get("registration_url") or "")
        agency = str(row.get("agency") or "")
        expect = tuple(str(e) for e in (row.get("expect") or ()) if str(e).strip())
        if not site or not host or not url or not agency:
            raise ValueError(
                f"axon_connect inventory site {i} needs site/host/registration_url/agency"
            )
        parts = urlsplit(url)
        if parts.scheme != "https" or parts.netloc != host or not host:
            raise ValueError(
                f"axon_connect inventory site {i}: registration_url {url!r} "
                "is not an https URL on the row's host"
            )
        if not expect:
            raise ValueError(
                f"axon_connect inventory site {i}: an empty expect list leaves "
                "the page-identity check unenforceable (fail-closed)"
            )
        sites.append(
            ConnectSite(
                site=site,
                host=host,
                registration_url=url,
                agency=agency,
                jurisdiction=str(row.get("jurisdiction") or ""),
                status=str(row.get("status") or "lead"),
                expect=expect,
                evidence=str(row.get("evidence") or ""),
                opted_out=site in opted or host in opted,
            )
        )
    ids = [s.site for s in sites]
    if len(set(ids)) != len(ids):
        raise ValueError("axon_connect inventory carries duplicate site ids")
    if ids != sorted(ids):
        raise ValueError("axon_connect inventory is not site-sorted (deterministic order required)")
    declared = int(inv.get("site_count") or -1)
    if declared != len(sites):
        raise ValueError(
            f"axon_connect inventory site_count={declared} but {len(sites)} rows are committed"
        )
    return ConnectInventory(
        source_ref=str(inv.get("source_ref") or ""),
        evidence_ref=str(inv.get("evidence_ref") or ""),
        captured_on=str(inv.get("captured_on") or ""),
        selection_rule=str(inv.get("selection_rule") or ""),
        sites=tuple(sites),
    )


def _targets_for(inventory: ConnectInventory) -> list[dict[str, Any]]:
    """The two bounded targets per committed site — identifiers only."""
    out: list[dict[str, Any]] = []
    for s in inventory.sites:
        out.append(
            {
                "id": f"{s.site}:page",
                "url": s.registration_url,
                "kind": "connect_page",
                "site": s.site,
                "subject_id": f"{SITE_ID_PREFIX}:{s.site}",
            }
        )
        out.append(
            {
                "id": f"{s.site}:8443",
                "url": s.screen_url,
                "kind": "marked_host_screen",
                "site": s.site,
                "subject_id": f"{HOST_ID_PREFIX}:{s.host}",
            }
        )
    return out


def connect_targets() -> list[dict[str, Any]]:
    """The ``{"id","url","kind"}`` targets ``live_targets.toml`` delegates to."""
    return _targets_for(load_inventory())


# --- page parsing (pure — HTML text + embedded-JSON screen surface) ------------


class _ConnectPageScanner(HTMLParser):
    """Lift title text, visible text, terms blocks and embedded JSON islands."""

    def __init__(self, terms_ids: frozenset[str]) -> None:
        super().__init__(convert_charrefs=True)
        self._terms_ids = terms_ids
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []
        self.json_blocks: list[str] = []
        self.terms_blocks: list[str] = []
        self.license_links: list[dict[str, str]] = []
        self._in_title = False
        self._skip_depth = 0  # inside script/style — text there is not page copy
        self._script_buf: list[str] | None = None
        self._terms_tag: str | None = None
        self._terms_depth = 0
        self._terms_buf: list[str] = []
        self._license_buf: list[str] | None = None
        self._license_href = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {k.lower(): (v or "") for k, v in attrs}
        if tag == "title":
            self._in_title = True
        elif tag in {"style", "noscript"}:
            self._skip_depth += 1
        elif tag == "script":
            self._skip_depth += 1
            mtype = attr.get("type", "").split(";")[0].strip().lower()
            if mtype in _JSON_SCRIPT_TYPES:
                self._script_buf = []
        elif tag == "a" and "license" in {r.strip().lower() for r in attr.get("rel", "").split()}:
            self._license_buf = []
            self._license_href = attr.get("href", "")
        tid = attr.get("id", "").strip().lower()
        classes = {c.lower() for c in attr.get("class", "").split()}
        if self._terms_tag is not None:
            self._terms_depth += 1
        elif tid in self._terms_ids or (classes & self._terms_ids):
            self._terms_tag = tag
            self._terms_depth = 1
            self._terms_buf = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        elif tag in {"style", "noscript"} and self._skip_depth:
            self._skip_depth -= 1
        elif tag == "script":
            if self._script_buf is not None:
                self.json_blocks.append("".join(self._script_buf))
                self._script_buf = None
            if self._skip_depth:
                self._skip_depth -= 1
        elif tag == "a" and self._license_buf is not None:
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
            return
        if self._in_title:
            self.title_parts.append(data)
        if self._license_buf is not None:
            self._license_buf.append(data)
        if self._terms_tag is not None:
            self._terms_buf.append(data)
        if self._skip_depth == 0 and not self._in_title:
            self.text_parts.append(data)


class ConnectSchemaError(ValueError):
    """A served page cannot satisfy the committed Connect-page schema."""


@dataclass(frozen=True)
class ServedConnectPage:
    """The in-memory extraction of one served Connect page — programme facts only.

    Carries only allowlisted fields: the published programme name, the modes
    the page offers, verbatim stated-use clauses and terms text, and the
    refused field NAMES (never values). Raw page bytes are never stored; the
    original's sha256 + byte size ride the record as evidence (SIG-ENG-042).
    """

    site: str
    url: str
    programme_name: str
    modes_offered: tuple[str, ...]
    vendor_marked: bool
    stated_use_clauses: tuple[str, ...]
    terms_text: str | None
    terms_truncated: bool
    refused_fields: tuple[str, ...]
    page_sha256: str
    page_bytes: int

    def record(self) -> dict[str, Any]:
        """The canonical persisted artifact — the ONLY bytes capture() stores."""
        return {
            "schema": PAGE_SCHEMA,
            "site": self.site,
            "url": self.url,
            "programme_name": self.programme_name,
            "modes_offered": list(self.modes_offered),
            "vendor_marked": self.vendor_marked,
            "stated_use_clauses": list(self.stated_use_clauses),
            "terms_text": self.terms_text,
            "terms_truncated": self.terms_truncated,
            "refused_fields": list(self.refused_fields),
            "page_sha256": self.page_sha256,
            "page_bytes": self.page_bytes,
        }

    def record_bytes(self) -> bytes:
        return json.dumps(self.record(), sort_keys=True, ensure_ascii=False).encode("utf-8")


@dataclass(frozen=True)
class ParsedConnectPage:
    """parse output: the extraction + the page's raw embedded-JSON payloads.

    ``payloads`` is held only in memory (screened before persistence, never
    stored) so the in-memory screen examines what the page actually carried —
    a denied field's presence is itself a screenable hazard.
    """

    page: ServedConnectPage
    payloads: tuple[Any, ...]


_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _sentences(text: str) -> Iterable[str]:
    for chunk in _SENTENCE_SPLIT.split(" ".join(text.split())):
        chunk = chunk.strip()
        if chunk:
            yield chunk


def _programme_name(title: str) -> str:
    """The published programme brand — the ``<title>``'s page-label suffix split.

    The white-label template titles read ``"Home - Connect <Place>"`` /
    ``"Camera Registration - Connect <Place>"``; the brand is the last
    ``" - "`` segment when one exists, else the whole title verbatim.
    """
    title = " ".join(title.split())
    if " - " in title:
        tail = title.rsplit(" - ", 1)[-1].strip()
        if tail:
            return tail
    return title


def parse_connect_page(body: bytes, *, url: str, site: ConnectSite) -> ParsedConnectPage:
    """Committed-schema parse of a served Connect page (stage 1 of the served path).

    Extracts the allowlisted programme fields (brand name, modes offered,
    verbatim stated-use clauses, verbatim terms) from the visible text, scans
    every embedded JSON island for Part VIII-denied field NAMES, and verifies
    the page is the committed site's page — at least one ``expect`` token must
    appear, else the page is refused whole (:class:`ConnectSchemaError`; a
    page contradicting its committed site is never guessed).
    """
    text = body.decode("utf-8", errors="replace")
    terms_ids = frozenset(str(t).lower() for t in _vocab()["page"].get("terms_element_ids") or ())
    scanner = _ConnectPageScanner(terms_ids)
    scanner.feed(text)
    scanner.close()

    payloads: list[Any] = []
    denied_keys: set[str] = set()
    for block in scanner.json_blocks:
        try:
            doc = json.loads(block)
        except (json.JSONDecodeError, ValueError):
            continue
        payloads.append(doc)
        for d in _iter_dicts(doc):
            for key in d:
                if is_denied(str(key)):
                    denied_keys.add(str(key))

    visible = " ".join(scanner.text_parts)
    lower = visible.lower()
    # Page-identity check — the served page must be the committed site's.
    if not any(token.lower() in lower for token in site.expect):
        raise ConnectSchemaError(
            f"served page carries none of site {site.site!r}'s committed expect "
            "tokens — the page is not the committed site (refused, never guessed)"
        )

    vocab_page = _vocab()["page"]
    registration = any(
        str(m).lower() in lower for m in vocab_page.get("registration_markers") or ()
    )
    integration = any(str(m).lower() in lower for m in vocab_page.get("integration_markers") or ())
    if not (registration or integration):
        raise ConnectSchemaError(
            "no registration/integration marker — the page is not a Connect "
            "programme page under the committed schema"
        )
    modes = tuple(
        mode for mode, hit in (("registration", registration), ("integration", integration)) if hit
    )
    vendor_marked = any(str(m).lower() in lower for m in vocab_page.get("vendor_markers") or ())

    patterns = [str(p).lower() for p in vocab_page.get("stated_use_patterns") or ()]
    clauses: list[str] = []
    seen_clauses: set[str] = set()
    for sentence in _sentences(visible):
        sl = sentence.lower()
        if any(p in sl for p in patterns):
            clause = sentence[:_CLAUSE_CAP]
            if clause not in seen_clauses:
                seen_clauses.add(clause)
                clauses.append(clause)

    title = " ".join(scanner.title_parts).strip()
    terms_text: str | None = None
    if scanner.terms_blocks:
        terms_text = scanner.terms_blocks[0]
    elif scanner.license_links:
        link = scanner.license_links[0]
        label = link["text"] or link["href"]
        if label:
            terms_text = f"{label} ({link['href']})" if link["href"] else label
    truncated = False
    if terms_text is not None and len(terms_text) > _TERMS_CAP:
        terms_text = terms_text[:_TERMS_CAP]
        truncated = True

    return ParsedConnectPage(
        page=ServedConnectPage(
            site=site.site,
            url=url,
            programme_name=_programme_name(title) or site.site,
            modes_offered=modes,
            vendor_marked=vendor_marked,
            stated_use_clauses=tuple(clauses),
            terms_text=terms_text,
            terms_truncated=truncated,
            refused_fields=tuple(sorted(denied_keys)),
            page_sha256=hashlib.sha256(body).hexdigest(),
            page_bytes=len(body),
        ),
        payloads=tuple(payloads),
    )


def _iter_dicts(node: Any) -> Iterable[dict[str, Any]]:
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from _iter_dicts(v)
    elif isinstance(node, list):
        for item in node:
            yield from _iter_dicts(item)


# --- the marked-host screen record ----------------------------------------------


def fusus_screen_record(result: FetchResult, *, site: ConnectSite) -> dict[str, Any]:
    """Build the ``sig.fusus-screen/1`` record for a ``/:8443/faststream/login.html`` GET.

    The ONLY thing persisted for a marked-host target: host, screen URL, HTTP
    status, the committed marker names hit, ``recognised`` (>= ``min_hits`` of
    the vocabulary's markers present in a 2xx body), the page's real sha256 +
    byte size, and the retrieval instant. The login page's bytes are never
    stored anywhere (evidence-only screen — OM-20's "one GET").
    """
    screen = _vocab()["screen"]
    body = result.body or b""
    head = body[:131_072].decode("utf-8", errors="replace").lower()
    hit = sorted({m for m in (str(x).lower() for x in screen.get("markers") or ()) if m in head})
    recognised = int(result.status) == 200 and len(hit) >= int(screen.get("min_hits") or 1)
    return {
        "schema": SCREEN_SCHEMA,
        "host": site.host,
        "site": site.site,
        "screen_url": str(result.url),
        "status": int(result.status),
        "recognised": recognised,
        "markers_hit": hit,
        "page_sha256": hashlib.sha256(body).hexdigest(),
        "page_bytes": len(body),
        "retrieved_at": (
            result.retrieved_at.isoformat() if result.retrieved_at is not None else None
        ),
    }


def load_screen_declaration(path: str | Path | None = None) -> ScreenDeclaration:
    """The committed ``sig.at-rest-audit-decl/1`` — one parser, one document (ADR-185)."""
    p = Path(path) if path else DEFAULT_SCREEN_DECLARATION
    raw = tomllib.loads(p.read_text(encoding="utf-8"))
    return declaration_from_table(raw, source=str(p))


# --- refusal types local to this connector ---------------------------------------


class ConnectSiteOptedOut(HostOptOut):
    """A site-level opt-out: the agency asked SIG to stop addressing ITS site.

    The host-level register (§26 rule 7) is consulted by the shared fetcher
    before any egress; the committed inventory's ``opted_out_sites`` list is
    its site-granular counterpart, checked in ``fetch()`` before the request
    is issued. A subclass of :class:`HostOptOut` so the driver's
    rights-refusal path records it unchanged.
    """

    def __init__(self, site: str, url: str) -> None:
        self.site = site
        super().__init__(url, urlsplit(url).netloc, f"site {site!r} is opted out of screening")


class InterstitialEncountered(ChallengeEncountered):
    """A 2xx bot-management interstitial — a challenge, recorded as such.

    Any challenge ends the target's attempt (SIG-INGEST-013/037): recorded,
    never defeated. A subclass of :class:`ChallengeEncountered` so the driver
    records the ``access_restricted`` disappearance through the unchanged
    machinery while this connector's ledger keeps the finer ``interstitial``
    kind.
    """

    def __init__(self, url: str) -> None:
        super().__init__(
            f"{url!r} served a bot-management interstitial (2xx stub, not the "
            "page); the attempt ends here — recorded, never defeated "
            "(SIG-INGEST-013).",
            status=200,
        )


def _looks_like_interstitial(body: bytes) -> bool:
    """Whether the served 2xx body is a bot-management stub, not the real page."""
    markers = tuple(str(m).lower() for m in _vocab()["screen"].get("interstitial_markers") or ())
    head = body[:65_536].decode("utf-8", errors="replace").lower()
    return any(m in head for m in markers)


# --- the connector -----------------------------------------------------------------


@register
class AxonConnectConnector(Connector):
    """The `axon_connect` connector — Connect <Place> programme facts + the FUSUS screen.

    One polite GET per committed target per run through the shared politeness
    layer. The connector holds no HTTP client, no credential, no retry, and no
    circumvention capability of any kind (SIG-INGEST-011/013/037).
    """

    name = CONNECTOR_NAME
    version = "1.0.0"

    def __init__(
        self,
        *,
        inventory: ConnectInventory | None = None,
        screen: ScreenDeclaration | None = None,
        screen_declaration_path: str | Path | None = None,
    ) -> None:
        self._inventory = inventory or load_inventory()
        self._screen = screen or load_screen_declaration(screen_declaration_path)
        #: The run's per-target outcome ledger — one row per attempted target
        #: (served / refused + kind + counts-only detail; never content).
        self.outcomes: list[dict[str, Any]] = []
        #: The fetch → capture handoff: the artifacts this connector persists
        #: (the screened records), keyed by URL. Bounded by the committed set.
        self._artifacts: dict[str, bytes] = {}
        self._served: dict[str, ServedConnectPage] = {}
        self._screens: dict[str, dict[str, Any]] = {}

    # -- acquisition --

    def discover(self, ctx: RunContext) -> list[Mapping[str, Any]]:
        """The committed target set — identifiers, not content (SIG-INGEST-045i).

        ``parameters["targets"]`` (live_targets rows or a fixture subset) bound
        the run but must stay inside the committed inventory: a target outside
        it is discovery — refused loud.
        """
        given = ctx.parameters.get("targets")
        if not given:
            return [dict(t) for t in _targets_for(self._inventory)]
        known = self._inventory.urls
        out: list[Mapping[str, Any]] = []
        for t in given:
            url = str(t.get("url") or "")
            site = self._inventory.site_for_url(url)
            if url not in known or site is None:
                raise ValueError(
                    f"target {url!r} is not in the committed axon_connect "
                    "inventory — this connector discovers nothing; refusing to "
                    "address outside the committed set"
                )
            row = dict(t)
            kind = str(
                row.get("kind")
                or ("connect_page" if url == site.registration_url else "marked_host_screen")
            )
            row.setdefault("id", f"{site.site}:{'page' if kind == 'connect_page' else '8443'}")
            row.setdefault("site", site.site)
            row.setdefault(
                "subject_id",
                f"{SITE_ID_PREFIX}:{site.site}"
                if kind == "connect_page"
                else f"{HOST_ID_PREFIX}:{site.host}",
            )
            out.append(row)
        return out

    def fetch(self, ctx: RunContext, target: Mapping[str, Any]) -> FetchResult:
        """The single bounded GET; the ONLY egress (SIG-INGEST-011).

        Order of the served path: site opt-out → politeness fetch →
        interstitial check → kind dispatch (page parse / screen record) →
        in-memory Part VIII screen → admit. Every outcome lands on the run
        ledger BEFORE the exception carries it to the driver's recorded
        dispositions.
        """
        assert ctx.fetcher is not None, "connectors fetch only through the shared layer"
        url = str(target["url"])
        kind = str(target.get("kind") or "connect_page")
        site = self._inventory.site_for_url(url) or self._inventory.site(
            str(target.get("site") or "")
        )
        if site is None:
            raise ValueError(f"target {url!r} names no committed axon_connect site")
        if site.opted_out:
            self.outcomes.append(
                {
                    "site": site.site,
                    "url": url,
                    "kind": kind,
                    "result": "refused",
                    "refusal_kind": "opted_out",
                }
            )
            raise ConnectSiteOptedOut(site.site, url)
        try:
            result = ctx.fetcher.fetch(url)
        except HostOptOut:
            self.outcomes.append(
                {
                    "site": site.site,
                    "url": url,
                    "kind": kind,
                    "result": "refused",
                    "refusal_kind": "opt_out",
                }
            )
            raise
        except ReservationRefused as exc:
            self.outcomes.append(
                {
                    "site": site.site,
                    "url": url,
                    "kind": kind,
                    "result": "refused",
                    "refusal_kind": "rights_reservation",
                    "signals": sorted({s.kind for s in exc.verdict.signals}),
                }
            )
            raise
        except ChallengeEncountered as exc:
            self.outcomes.append(
                {
                    "site": site.site,
                    "url": url,
                    "kind": kind,
                    "result": "refused",
                    "refusal_kind": "challenge",
                    "status": exc.status,
                }
            )
            raise
        except Exception as exc:
            if failing_status_for_error(exc) is not None:
                self.outcomes.append(
                    {
                        "site": site.site,
                        "url": url,
                        "kind": kind,
                        "result": "refused",
                        "refusal_kind": "unreachable",
                    }
                )
            raise
        status = int(result.status)
        if failing_status_for_http(status) is not None:
            self.outcomes.append(
                {
                    "site": site.site,
                    "url": url,
                    "kind": kind,
                    "result": "refused",
                    "refusal_kind": f"http_{status}",
                    "status": status,
                }
            )
            return result
        if _looks_like_interstitial(result.body or b""):
            self.outcomes.append(
                {
                    "site": site.site,
                    "url": url,
                    "kind": kind,
                    "result": "refused",
                    "refusal_kind": "interstitial",
                    "status": status,
                }
            )
            raise InterstitialEncountered(url)
        if kind == "marked_host_screen":
            return self._fetch_screen(ctx, target, result, site)
        return self._fetch_page(ctx, target, result, site)

    def _fetch_page(
        self, ctx: RunContext, target: Mapping[str, Any], result: FetchResult, site: ConnectSite
    ) -> FetchResult:
        url = str(target["url"])
        try:
            parsed = parse_connect_page(result.body, url=url, site=site)
        except ConnectSchemaError as exc:
            self.outcomes.append(
                {
                    "site": site.site,
                    "url": url,
                    "kind": "connect_page",
                    "result": "refused",
                    "refusal_kind": "schema_refusal",
                    "detail": str(exc),
                }
            )
            raise SchemaRefusal(url, reason=str(exc)) from exc
        # ADR-185 persistence rule — the committed Part VIII screen runs IN
        # MEMORY over BOTH the embedded payloads the page served (a denied
        # field's presence is a whole-page refusal) and the canonical record
        # (the only bytes this connector writes), before any persistence.
        hits: dict[str, int] = {}
        for blob in (
            json.dumps(parsed.payloads, default=str).encode("utf-8"),
            parsed.page.record_bytes(),
        ):
            for cls, n in screen_blob(
                blob, source_id=SOURCE_ID, media_type="application/json", decl=self._screen
            ).items():
                hits[cls] = hits.get(cls, 0) + int(n)
        if hits:
            self.outcomes.append(
                {
                    "site": site.site,
                    "url": url,
                    "kind": "connect_page",
                    "result": "refused",
                    "refusal_kind": "screened",
                    "screen_hits": {k: int(v) for k, v in sorted(hits.items())},
                }
            )
            raise ScreenedRefusal(url, classes=sorted(hits), hits=hits)
        page = parsed.page
        self._served[url] = page
        self._artifacts[url] = page.record_bytes()
        self.outcomes.append(
            {
                "site": site.site,
                "url": url,
                "kind": "connect_page",
                "result": "served",
                "modes_offered": list(page.modes_offered),
                "vendor_marked": page.vendor_marked,
                "refused_fields": list(page.refused_fields),
                "page_sha256": page.page_sha256,
                "page_bytes": page.page_bytes,
                "screen": "clean",
            }
        )
        return result

    def _fetch_screen(
        self, ctx: RunContext, target: Mapping[str, Any], result: FetchResult, site: ConnectSite
    ) -> FetchResult:
        url = str(target["url"])
        record = fusus_screen_record(result, site=site)
        record_bytes = json.dumps(record, sort_keys=True, ensure_ascii=False).encode("utf-8")
        # The persisted screen record is screened too — fail-closed, even
        # though it carries no extracted field names by construction.
        hits = screen_blob(
            record_bytes, source_id=SOURCE_ID, media_type="application/json", decl=self._screen
        )
        if hits:
            self.outcomes.append(
                {
                    "site": site.site,
                    "url": url,
                    "kind": "marked_host_screen",
                    "result": "refused",
                    "refusal_kind": "screened",
                    "screen_hits": {k: int(v) for k, v in sorted(hits.items())},
                }
            )
            raise ScreenedRefusal(url, classes=sorted(hits), hits=hits)
        self._screens[url] = record
        self._artifacts[url] = record_bytes
        self.outcomes.append(
            {
                "site": site.site,
                "url": url,
                "kind": "marked_host_screen",
                "result": "served",
                "recognised": record["recognised"],
                "markers_hit": list(record["markers_hit"]),
                "page_sha256": record["page_sha256"],
                "page_bytes": record["page_bytes"],
                "screen": "clean",
            }
        )
        return result

    def capture(self, ctx: RunContext, fetched: FetchResult) -> CaptureRef:
        """Persist the screened record — NEVER the served page's own bytes.

        ``sig.axon-connect-page/1`` (programme fields + verbatim clauses +
        page sha256) or ``sig.fusus-screen/1`` (the marked-host screen record)
        is the only artifact this connector stores: the bytes the in-memory
        screen demonstrably passed (ADR-185).
        """
        stored = self._artifacts.get(fetched.url)
        if stored is None:
            # Defensive path (a capture handed a FetchResult that never passed
            # through this connector's fetch — e.g. a resumed mark): refuse
            # rather than persist unscreened bytes (fail-closed).
            raise ValueError(
                f"{fetched.url!r} has no screened artifact — refused to persist "
                "bytes the in-memory screen never saw (ADR-185)"
            )
        return ctx.captures.put(
            stored,
            media_type="application/json",
            source_uri=fetched.url,
            retrieved_at=fetched.retrieved_at,
        )

    # -- interpretation (pure functions of the screened capture) --

    def parse(self, ctx: RunContext, capture: CaptureRef) -> dict[str, Any]:
        """Read back the screened artifact (pure)."""
        doc = json.loads(ctx.captures.get(capture.digest).decode("utf-8"))
        if doc.get("schema") not in {PAGE_SCHEMA, SCREEN_SCHEMA}:
            raise ValueError(
                f"capture {capture.digest} is not a {PAGE_SCHEMA}/{SCREEN_SCHEMA} record"
            )
        doc["_capture_digest"] = capture.digest
        doc["_retrieved_at"] = capture.retrieved_at.isoformat() if capture.retrieved_at else None
        return doc

    def extract(self, ctx: RunContext, parsed: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        """One raw record per screened artifact — preserving raw values (P2)."""
        if parsed.get("schema") == SCREEN_SCHEMA:
            return [
                {
                    "record_kind": "fusus_marked_screen",
                    "host": str(parsed["host"]),
                    "site": str(parsed["site"]),
                    "screen_url": str(parsed["screen_url"]),
                    "status": int(parsed["status"]),
                    "recognised": bool(parsed["recognised"]),
                    "markers_hit": list(parsed.get("markers_hit") or []),
                    "page_sha256": str(parsed["page_sha256"]),
                    "page_bytes": int(parsed["page_bytes"]),
                    "capture_digest": str(parsed.get("_capture_digest", "")),
                    "retrieved_at": parsed.get("_retrieved_at"),
                }
            ]
        return [
            {
                "record_kind": "axon_connect_page",
                "site": str(parsed["site"]),
                "url": str(parsed["url"]),
                "programme_name": str(parsed["programme_name"]),
                "modes_offered": list(parsed.get("modes_offered") or []),
                "vendor_marked": bool(parsed.get("vendor_marked")),
                "stated_use_clauses": list(parsed.get("stated_use_clauses") or []),
                "terms_text": parsed.get("terms_text"),
                "refused_fields": list(parsed.get("refused_fields") or []),
                "page_sha256": str(parsed.get("page_sha256")),
                "page_bytes": int(parsed.get("page_bytes") or 0),
                "capture_digest": str(parsed.get("_capture_digest", "")),
                "retrieved_at": parsed.get("_retrieved_at"),
            }
        ]

    def normalize(
        self, ctx: RunContext, raw_claims: list[Mapping[str, Any]]
    ) -> list[dict[str, Any]]:
        """Claims + the candidate-of-record row, in served order.

        Per connect_page capture: the ``camera_registration_portal``
        programme-surface claim (artifact event), the
        ``camera_registry_publisher`` provenance claim, ``agency_name`` for the
        published brand, and one ``portal_stated_prohibited_use`` claim per
        verbatim clause. Per marked-host capture: ONE
        ``acquisition_candidate`` record row — the SIG-ACQ-020 candidate
        shape, never a feed. Every emitted field name is checked against the
        committed Part VIII denylist: a registrant-byte field in emitted
        facts fails loud (raise), never a warning.
        """
        attribution = _source_attribution(ctx)
        site_by_id = {s.site: s for s in self._inventory.sites}
        out: list[dict[str, Any]] = []
        for raw in raw_claims:
            denied = [k for k in raw.keys() if is_denied(str(k))]
            if denied:
                raise PredicateNotAllowed(
                    f"emitted fact carries Part VIII-denied field names {denied} — "
                    "registrant bytes fail loud, never a warning (R11-A16, SIG-PUB-002)"
                )
            if raw.get("record_kind") == "fusus_marked_screen":
                # The candidate-of-record: a FUSUS marked-host presence is a
                # recorded acquisition candidate — never a feed, never a claim
                # of deployment.
                out.append(
                    _stamp(
                        {
                            "record_kind": "acquisition_candidate",
                            "candidate_kind": "fusus_marked_host",
                            "subject_id": f"{HOST_ID_PREFIX}:{raw['host']}",
                            "host": str(raw["host"]),
                            "screen_url": str(raw["screen_url"]),
                            "status": int(raw["status"]),
                            "recognised": bool(raw["recognised"]),
                            "markers_hit": list(raw.get("markers_hit") or []),
                            "page_sha256": str(raw.get("page_sha256")),
                            "page_bytes": int(raw.get("page_bytes") or 0),
                            "capture_digest": str(raw.get("capture_digest") or ""),
                            "observed_at": _observed_date(raw.get("retrieved_at")),
                            "note": "a marked-host presence is a candidate-of-record "
                            "(SIG-ACQ-020), never a feed (R11-A16)",
                        },
                        attribution=attribution,
                    )
                )
                continue
            site_id = str(raw["site"])
            site = site_by_id.get(site_id)
            if site is None:
                raise ValueError(f"emitted record names uncommitted site {site_id!r}")
            subject = f"{SITE_ID_PREFIX}:{site_id}"
            observed = _observed_date(raw.get("retrieved_at"))
            capture_digest = str(raw.get("capture_digest") or "")
            out.append(
                _stamp(
                    {
                        "record_kind": "claim",
                        "subject_id": subject,
                        "predicate_id": assert_predicate_allowed("camera_registration_portal"),
                        "event_class": "artifact_event",
                        "value": True,
                        "raw_value": True,
                        "capture_digest": capture_digest,
                        "observed_at": observed,
                        "extracted_field": "programme_surface",
                    },
                    attribution=attribution,
                )
            )
            out.append(
                _stamp(
                    {
                        "record_kind": "claim",
                        "subject_id": subject,
                        "predicate_id": assert_predicate_allowed("camera_registry_publisher"),
                        "value": site.agency,
                        "raw_value": site.agency,
                        "capture_digest": capture_digest,
                        "extracted_field": "agency",
                        "note": "the committed inventory's publisher label — "
                        "the page is the agency's published surface",
                    },
                    attribution=attribution,
                )
            )
            out.append(
                _stamp(
                    {
                        "record_kind": "claim",
                        "subject_id": subject,
                        "predicate_id": assert_predicate_allowed("agency_name"),
                        "value": str(raw["programme_name"]),
                        "raw_value": str(raw["programme_name"]),
                        "capture_digest": capture_digest,
                        "extracted_field": "programme_name",
                    },
                    attribution=attribution,
                )
            )
            for clause in raw.get("stated_use_clauses") or []:
                out.append(
                    _stamp(
                        {
                            "record_kind": "claim",
                            "subject_id": subject,
                            "predicate_id": assert_predicate_allowed(
                                "portal_stated_prohibited_use"
                            ),
                            "value": str(clause),
                            "raw_value": str(clause),
                            "capture_digest": capture_digest,
                            "extracted_field": "stated_use_clause",
                            "note": "verbatim clause the published page states",
                        },
                        attribution=attribution,
                    )
                )
        return out

    def link(self, ctx: RunContext, normalized: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Candidate rows mint no entity refs (SIG-INGEST-034) — pass through."""
        return normalized

    def load(self, ctx: RunContext, linked: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Produce the L1 rows; the driver asserts them (live only — leg B)."""
        return load_claims_for_l1(linked)


def _observed_date(raw: Any) -> date | None:
    """The capture's retrieval date — SIG's own observation time."""
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


def _source_attribution(ctx: RunContext) -> str:
    """The source's recorded attribution (its rights block)."""
    try:
        return ctx.source.rights.attribution
    except AttributeError:  # pragma: no cover - defensive
        return "Axon Fusus Connect <Place> published programme page (P36.76)"


def _stamp(row: dict[str, Any], *, attribution: str = "") -> dict[str, Any]:
    """Stamp source attribution + the training-deny marker onto a row.

    No licence label is invented for an UNDETERMINED-rights source — the
    export gate stays fail-closed. ``ai_training_permitted = false`` is
    stamped explicitly so the training gate refuses regardless of how the row
    travels downstream (SIG-LIC-004b).
    """
    row["source_attribution"] = attribution
    row.setdefault("source_id", SOURCE_ID)
    row["ai_training_permitted"] = False
    if row.get("record_kind") == "claim":
        # The page is the programme's own published camera-registry surface —
        # the closed registry genre the row derives from (P35.14a).
        row.setdefault("evidence_genre", "camera_registry")
    return row


__all__ = [
    "CONNECTOR_NAME",
    "DEFAULT_SCREEN_DECLARATION",
    "HOST_ID_PREFIX",
    "PAGE_SCHEMA",
    "SCREEN_SCHEMA",
    "SITE_ID_PREFIX",
    "SOURCE_ID",
    "TARGETS_SCHEMA",
    "VOCAB_SCHEMA_ID",
    "AxonConnectConnector",
    "ConnectInventory",
    "ConnectSchemaError",
    "ConnectSite",
    "ConnectSiteOptedOut",
    "InterstitialEncountered",
    "ParsedConnectPage",
    "PredicateNotAllowed",
    "ServedConnectPage",
    "assert_predicate_allowed",
    "connect_targets",
    "fusus_screen_record",
    "load_inventory",
    "load_screen_declaration",
    "parse_connect_page",
    "predicate_allowlist",
]
