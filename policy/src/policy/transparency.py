# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The transparency scrub — J4 S-1…S-14 as code (J3 §9.1, SIG-TRANSP-022, P35.31).

ONE module, ONE vocabulary (J3 T-6): every transparency surface — the
transparency exports (rows 311/313), statements (row 315), the status lane
(P36.43), the publish secret gate (``ops/publish.py``), the actual-capture
writer (``db/claim_sink.py``) and the ``/v1/evidence`` read — consumes these
functions. A second scrub implementation is a defect, not a convenience.

Every rule is fail-closed:

* a field with no rule is not published — the emit contract is
  :func:`explicit_columns` (S-12), never ``SELECT *``;
* a secret-shaped value anywhere in the publish set aborts the publish —
  :func:`find_secrets` is the detector the single allow-listed publish path
  runs over EVERY file (S-1's block clause, SIG-TRANSP-022);
* an unknown redistribution lane or Part VIII class derives the most
  restrictive storage tier (:func:`derive_storage_tier` — NEW-2/F-400; never
  ``public`` by default).

``policy`` is a leaf package: caller-injected signals arrive as parameters,
never imports. ``person_screen=`` is the same convention as
:mod:`policy.labels` (api/exports call sites pass
``resolution.partner_identity.natural_person_signal``); ``packet_limited`` /
``sig_labelled_cc0`` / ``part_viii_class`` are the registry flags row 313's
``[redistribution]`` fields will carry — until then the lane derives from the
rights record the registry already carries (:func:`interim_lane`, the interim
basis — recorded, never guessed).
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any
from urllib.parse import unquote_plus, urlsplit, urlunsplit


class ScrubViolation(ValueError):
    """A transparency surface asked for a field the scrub rules never export."""


# ---------------------------------------------------------------------------
# The vocabularies — closed sets, one spelling everywhere
# ---------------------------------------------------------------------------

#: The redistribution lanes (J4 §4 / D-J3-1 / row 313's ``[redistribution]``
#: field). ``unknown`` is a real verdict — fail closed, never a blank.
LANE_RAW_OK = "raw-ok"
LANE_DERIVED_ONLY = "derived-only"
LANE_LINK_ONLY = "link-only"
LANE_RESTRICTED = "restricted"
LANE_UNKNOWN = "unknown"

REDISTRIBUTION_LANES: frozenset[str] = frozenset(
    {LANE_RAW_OK, LANE_DERIVED_ONLY, LANE_LINK_ONLY, LANE_RESTRICTED, LANE_UNKNOWN}
)

#: The capture storage tiers (SIG-EVID-009). The string values mirror
#: ``evidence.tiers.StorageTier``; ``policy`` stays a leaf so it never imports
#: the evidence package — the check constraint in ``db/deploy/evidence.sql``
#: is the binding spelling.
TIER_PUBLIC = "public"
TIER_RESTRICTED = "restricted"
TIER_SEALED = "sealed"

STORAGE_TIERS: frozenset[str] = frozenset({TIER_PUBLIC, TIER_RESTRICTED, TIER_SEALED})

#: Restrictiveness order — a read path may tighten a served tier, never relax it.
_TIER_RANK = {TIER_PUBLIC: 0, TIER_RESTRICTED: 1, TIER_SEALED: 2}

#: J4 §9: the Part VIII classes whose material can never publish (P8-1 audit
#: material, P8-2 released records, P8-4 private-registrant programs) → sealed.
PART_VIII_SEALED_CLASSES: frozenset[str] = frozenset({"P8-1", "P8-2", "P8-4"})

#: The full P8 class set (J4 §9). Classes outside the sealed set are still
#: byte-screened (field drops, derived-only lanes) — recorded, never absent.
PART_VIII_CLASSES: frozenset[str] = frozenset({f"P8-{i}" for i in range(1, 10)})

#: The recorded values that mean "the Part VIII read ran and found no hazard"
#: — J4's matrix writes ``none-known``; callers may pass ``clear``.
PART_VIII_CLEAR_VALUES: frozenset[str] = frozenset({"clear", "none-known"})

# --- absence tokens (J3 §4.3 — the absence is a value, not a gap) -------------

NO_UPSTREAM_URL = "no_upstream_url_recorded"
IP_REMOVED = "ip_removed"
PERSONAL_DATA_REMOVED = "personal_data_removed"
ROLE_UNSPECIFIED = "role_unspecified"
INTERNAL_LOCATION_PREFIX = "internal:"

# --- J3 §3.5: the never-exported list -----------------------------------------

#: Fields the scrubbed artifact can never carry. ``explicit_columns`` refuses
#: a column set naming one; the list is also iterated by tests asserting the
#: fields stay out of every scrubbed artifact.
NEVER_EXPORTED_FIELDS: frozenset[str] = frozenset(
    {
        # S-3 / J4 §8 N — ingest_run.environment, env vars, runtime config
        "environment",
        "env",
        "runtime_config",
        # J4 §8 N — ingest_run.parameters.run_record_uri (opaque id instead)
        "run_record_uri",
        # J4 §8 N / SIG-EVID-012 — the access log never leaves the restricted store
        "evidence_access_log",
        "access_log",
        "requester",
        "purpose",
        # J4 §8 N — assertion_quarantine.payload (counts by reason class only)
        "payload",
        # J3 §3.5 — rights reviewer identity beyond ROLE (Part VIII §0.7)
        "reviewed_by",
        # J4 §8 T→S-14 — raw capture headers beyond the allow-list
        "headers",
        "request_headers",
        "response_headers",
        # J4 §8 N — Cloud Logging (raw logs hold gs:// and container paths)
        "cloud_logging",
        "log_payload",
        # J3 §3.5 — probe targets (uptime/latency aggregates only)
        "probe_target",
        "probe_targets",
        # S-4 — raw error/refusal text; the error CLASS + count publishes
        "detail",
        "refusal_reason",
        "exception",
        "stacktrace",
        "stack_trace",
        # S-8 — free text from records: excerpts, search reasons, snippets
        # (SIG-PUB-014a). ``matched_terms`` vocabulary ids are fine.
        "search_reason",
        "search_reasons",
        "snippet",
        "snippets",
        "free_text",
    }
)


# ---------------------------------------------------------------------------
# S-1 — credentials: query-param/header stripping + the secret-shaped block
# ---------------------------------------------------------------------------

#: J4 S-1 verbatim: credential-like URL query parameter names, matched
#: case-insensitively on the parameter NAME.
CREDENTIAL_QUERY_RE = re.compile(
    r"^(api_?key|apikey|key|token|access_token|auth|sig|signature|secret"
    r"|password|session|jwt|code)$",
    re.IGNORECASE,
)

#: J4 S-1: headers dropped outright wherever headers are carried.
CREDENTIAL_HEADERS: frozenset[str] = frozenset(
    {"authorization", "x-api-key", "cookie", "set-cookie", "proxy-authorization"}
)

#: J4 S-14: the header allow-list — everything else drops (cookies, ``Server``,
#: ``Via``, ``X-*``, ``CF-*``, request ids, and every credential header).
HEADER_ALLOWLIST: frozenset[str] = frozenset(
    {"content-type", "content-length", "etag", "last-modified", "date"}
)


def strip_credential_query_params(url: str) -> str:
    """S-1: drop credential-shaped query parameters from a URL — fail closed.

    A parameter whose NAME matches :data:`CREDENTIAL_QUERY_RE` is stripped;
    every other parameter, the path and the fragment are preserved byte-for-byte
    (the query segments are split, never re-encoded). A URL whose query cannot
    be read loses the whole query rather than passing it through unexamined.
    """
    if "?" not in url:
        return url
    try:
        parts = urlsplit(url)
    except ValueError:
        return url.split("?", 1)[0]
    segments = [s for s in parts.query.split("&") if s]
    kept = [
        s
        for s in segments
        if not CREDENTIAL_QUERY_RE.match(unquote_plus(s.split("=", 1)[0]).strip())
    ]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "&".join(kept), parts.fragment))


def scrub_headers(headers: Mapping[str, str]) -> dict[str, str]:
    """S-14 (subsuming S-1's header drop): keep ONLY the allow-listed names —
    ``Content-Type``, ``Content-Length``, ``ETag``, ``Last-Modified``, ``Date``.
    """
    return {k: v for k, v in headers.items() if str(k).lower() in HEADER_ALLOWLIST}


@dataclass(frozen=True)
class SecretFinding:
    """One secret-shaped hit in a scanned text (S-1's publish-block clause).

    Carries the pattern CLASS and the 1-based line number — never the matched
    value (a refusal message must not echo the secret it caught).
    """

    pattern_class: str
    line: int


#: The closed set of detector classes (J4 S-1's block list + the canonical
#: secret shapes the publish gate also refuses — private-key blocks, the GCP
#: API-key shape). Tests plant one specimen per class.
SECRET_PATTERN_CLASSES: frozenset[str] = frozenset(
    {
        "jwt",
        "aws_access_key",
        "key_hex",
        "bearer_token",
        "private_key",
        "gcp_api_key",
    }
)

_SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    # JWT: base64url header starting ``eyJ`` (``{"…``) + two more segments.
    ("jwt", re.compile(r"eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}(?:\.[A-Za-z0-9_-]*)?")),
    # AWS-style access key ids (AKIA long-term, ASIA session).
    ("aws_access_key", re.compile(r"(?:AKIA|ASIA)[0-9A-Z]{16}")),
    # J4 verbatim: ≥32 hex characters after ``key=`` (``api[_-]?key=``,
    # ``SIGNING_KEY=`` etc. match — an over-match is the safe direction).
    ("key_hex", re.compile(r"key\s*=\s*[\"']?[0-9a-f]{32,}", re.IGNORECASE)),
    # A ``Bearer `` authorisation value.
    ("bearer_token", re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]{16,}")),
    # A PEM private-key block marker.
    ("private_key", re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----")),
    # The GCP API-key shape.
    ("gcp_api_key", re.compile(r"AIza[0-9A-Za-z_-]{35}")),
)


def find_secrets(text: str) -> list[SecretFinding]:
    """The secret-shaped values a text carries — S-1's publish-block clause.

    One :class:`SecretFinding` per pattern hit (the class and the line, never
    the value). An empty list is the only pass: a single hit anywhere in the
    publish set aborts the publish — fail closed, SIG-TRANSP-022; a warning is
    never a pass.
    """
    findings: list[SecretFinding] = []
    for pattern_class, rx in _SECRET_PATTERNS:
        for m in rx.finditer(text):
            findings.append(SecretFinding(pattern_class, text.count("\n", 0, m.start()) + 1))
    findings.sort(key=lambda f: (f.line, f.pattern_class))
    return findings


# ---------------------------------------------------------------------------
# S-2 — internal locations become opaque ids
# ---------------------------------------------------------------------------

_INTERNAL_LOCATION_RES: tuple[re.Pattern[str], ...] = (
    # Restricted-bucket GCS URIs (``gs://…-sig-restricted/…``).
    re.compile(r"gs://[A-Za-z0-9._-]*-sig-restricted[A-Za-z0-9._/-]*"),
    # GCP service-account e-mail addresses.
    re.compile(r"[a-z0-9-]+@[a-z0-9-]+\.iam\.gserviceaccount\.com"),
    # Home-directory paths (POSIX and macOS) — they also name a person.
    re.compile(r"(?:/Users|/home|/root)/[^\s'\"]+"),
    # Container workspace / job-execution paths.
    re.compile(r"/workspace/[^\s'\"]+"),
)


def opaque_id(value: str, *, kind: str = "internal") -> str:
    """A deterministic opaque id standing in for an internal value (S-2's
    replacement; J3 §3.5's ``run_record_uri`` stand-in — never the value)."""
    digest = hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:12]
    return f"{kind}:{digest}"


def scrub_internal_locations(text: str) -> str:
    """S-2: restricted ``gs://`` URIs, container/home paths and service-account
    e-mails are replaced by deterministic ``internal:<hash>`` opaque ids — the
    location itself never survives."""
    out = text
    for rx in _INTERNAL_LOCATION_RES:
        out = rx.sub(lambda m: opaque_id(m.group(0)), out)
    return out


# ---------------------------------------------------------------------------
# S-3 + S-12 — explicit-column emission; never-exported fields
# ---------------------------------------------------------------------------


def explicit_columns(row: Mapping[str, Any], columns: Iterable[str]) -> dict[str, Any]:
    """S-12 (+ S-3 and J3 §3.5): copy exactly ``columns`` out of ``row``.

    The emit contract of every scrubbed view:

    * ``columns`` must be a non-empty named list — ``SELECT *`` does not exist
      on a transparency surface;
    * naming a :data:`NEVER_EXPORTED_FIELDS` member raises — a never-exported
      field reaching the emit layer is a defect, not data;
    * a named column absent from ``row`` emits ``None`` — an honest absence
      the caller renders with its surface's absence token.
    """
    cols = [str(c) for c in columns]
    if not cols:
        raise ScrubViolation(
            "explicit_columns requires a named column list — SELECT * is not "
            "a transparency surface (S-12)"
        )
    refused = sorted(NEVER_EXPORTED_FIELDS.intersection(cols))
    if refused:
        raise ScrubViolation(f"never-exported fields in the column list: {refused} (J3 §3.5)")
    return {c: row.get(c) for c in cols}


# ---------------------------------------------------------------------------
# S-4 — error text becomes a closed vocabulary class
# ---------------------------------------------------------------------------

#: The closed S-4 vocabulary. ``upstream_http_<code>`` is the open
#: ``upstream_http_(\d{3})`` pattern inside it; ``unclassified_error`` is the
#: fail-closed fallback — a detail that maps to nothing is a class, never text.
ERROR_CLASSES: frozenset[str] = frozenset(
    {
        "db_connection_lost",
        "storage_error",
        "read_timeout",
        "constraint_violation",
        "robots_unavailable",
        "robots_disallow",
        "politeness_refusal",
        "quota_reached",
        "content_drift",
        "disappearance",
        "unclassified_error",
    }
)

_UPSTREAM_HTTP_RE = re.compile(r"^upstream_http_[1-5][0-9]{2}$")

_HTTP_STATUS_RE = re.compile(r"(?:http|status|code)[^0-9]{0,10}([1-5][0-9]{2})", re.IGNORECASE)

_ERROR_CLASS_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"constraint|violat", re.IGNORECASE), "constraint_violation"),
    (
        re.compile(r"robots[^\n]{0,40}(disallow|denied|forbid)", re.IGNORECASE),
        "robots_disallow",
    ),
    (
        re.compile(r"robots[^\n]{0,40}(unavail|unreachable|fail|error)", re.IGNORECASE),
        "robots_unavailable",
    ),
    (re.compile(r"politeness", re.IGNORECASE), "politeness_refusal"),
    (re.compile(r"quota", re.IGNORECASE), "quota_reached"),
    (re.compile(r"content.?drift|digest.?mismatch", re.IGNORECASE), "content_drift"),
    (
        re.compile(r"disappear|link.?rotted|gone", re.IGNORECASE),
        "disappearance",
    ),
    (re.compile(r"timeout|timed out|deadline", re.IGNORECASE), "read_timeout"),
    (
        re.compile(r"connect|psycopg|postgres|database", re.IGNORECASE),
        "db_connection_lost",
    ),
    (
        re.compile(r"gs://|gcs|storage|bucket|blob|disk|filesystem|errno", re.IGNORECASE),
        "storage_error",
    ),
)


def valid_error_class(value: str) -> bool:
    """Is ``value`` a member of the closed S-4 vocabulary?"""
    return value in ERROR_CLASSES or bool(_UPSTREAM_HTTP_RE.match(value))


def error_class(detail: object) -> str:
    """S-4: an error/refusal detail becomes a closed-vocabulary class —
    never exception text, SQL or constraint names on a public surface."""
    if detail is None:
        return "unclassified_error"
    text = str(detail)
    m = _HTTP_STATUS_RE.search(text)
    if m:
        return f"upstream_http_{m.group(1)}"
    for rx, cls in _ERROR_CLASS_RULES:
        if rx.search(text):
            return cls
    return "unclassified_error"


def error_counts(details: Iterable[object]) -> dict[str, int]:
    """The publishable shape of a detail list: class → count (S-4)."""
    counts: dict[str, int] = {}
    for d in details:
        cls = error_class(d)
        counts[cls] = counts.get(cls, 0) + 1
    return counts


# ---------------------------------------------------------------------------
# S-5 — IP addresses drop
# ---------------------------------------------------------------------------

_IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_IPV6_RE = re.compile(r"\b(?:[0-9a-fA-F]{1,4}:){2,7}(?:[0-9a-fA-F]{1,4}|:)\b")


def _valid_ipv4(text: str) -> bool:
    try:
        return all(0 <= int(o) <= 255 for o in text.split("."))
    except ValueError:
        return False


def contains_ip_address(text: str) -> bool:
    """Does the text carry an IP address (S-5)?"""
    return any(_valid_ipv4(m.group(0)) for m in _IPV4_RE.finditer(text)) or bool(
        _IPV6_RE.search(text)
    )


def strip_ip_addresses(text: str) -> str:
    """S-5: drop every IP address (never a partial mask — the whole token goes).
    A dotted token that cannot be an IPv4 address (an octet over 255) passes —
    it was never an IP."""
    out = _IPV4_RE.sub(lambda m: IP_REMOVED if _valid_ipv4(m.group(0)) else m.group(0), text)
    return _IPV6_RE.sub(IP_REMOVED, out)


# ---------------------------------------------------------------------------
# S-6 — upstream URLs: host always, full URL only for open lanes + gate-passed
# ---------------------------------------------------------------------------


def upstream_host(url: str) -> str:
    """The publishable host of an upstream URL (S-6): lower-cased hostname,
    userinfo/port/trailing dot stripped. An IP host returns ``""`` — S-5 wins."""
    try:
        host = (urlsplit(str(url)).hostname or "").lower().rstrip(".")
    except ValueError:
        return ""
    return "" if _valid_ipv4(host) or ":" in host else host


@dataclass(frozen=True)
class ScrubbedUrl:
    """The S-6 publication form of an upstream URL.

    ``host`` is always publishable. ``url`` carries the full S-1-scrubbed URL
    only where the lane and the publication gate allow it; otherwise
    ``path_sha256`` carries the host + path-hash form (a filename can name a
    private person — J4 S-6 note).
    """

    host: str
    url: str | None = None
    path_sha256: str | None = None


#: The lanes whose full upstream URL may publish (J4 S-6): ``link-only``
#: sources publish the host, not the URL.
_URL_PUBLISHING_LANES: frozenset[str] = frozenset({LANE_RAW_OK, LANE_DERIVED_ONLY})


def scrub_source_url(url: str | None, *, lane: str, gate_passed: bool) -> ScrubbedUrl | None:
    """S-6 (after S-1): the publishable form of an upstream URL.

    * the host is always publishable;
    * the full credential-stripped URL publishes only for ``raw-ok`` /
      ``derived-only`` lanes whose document/record passed the publication gate;
    * every other lane or a gate refusal publishes host + a hash of the path;
    * ``None``/empty input returns ``None`` — the caller renders
      :data:`NO_UPSTREAM_URL`.
    """
    text = str(url or "").strip()
    if not text:
        return None
    clean = strip_credential_query_params(text)
    host = upstream_host(clean)
    if lane in _URL_PUBLISHING_LANES and gate_passed:
        return ScrubbedUrl(host=host, url=clean)
    parts = urlsplit(clean)
    path_key = hashlib.sha256(f"{parts.path}?{parts.query}".encode()).hexdigest()[:16]
    return ScrubbedUrl(host=host, path_sha256=path_key)


# ---------------------------------------------------------------------------
# S-7 — personal data never publishes
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")
_PHONE_RE = re.compile(r"\+?\d[\d .()/-]{7,}\d")
#: A name-shaped candidate: two-or-more Capitalised words (optional middle
#: initial). Only consulted through the injected ``person_screen`` — the screen
#: decides, this module never guesses (the labels.py injection convention).
_NAME_CANDIDATE_RE = re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z]\.?)?(?:\s+[A-Z][a-z]+)+\b")


def scrub_personal(
    text: str,
    *,
    names: Iterable[str] = (),
    person_screen: Callable[[str], bool] | None = None,
) -> str:
    """S-7: no person names, e-mails or phone numbers (Part VIII §0.7).

    E-mail and phone shapes and every supplied ``names`` entry drop to
    ``personal_data_removed``. When ``person_screen`` is injected it is
    consulted on each Capitalised name-shaped candidate — the caller's
    ``natural_person_signal`` decides, never a guessed heuristic.
    """
    out = _EMAIL_RE.sub(PERSONAL_DATA_REMOVED, text)
    out = _PHONE_RE.sub(PERSONAL_DATA_REMOVED, out)
    for name in names:
        if name:
            out = out.replace(str(name), PERSONAL_DATA_REMOVED)
    if person_screen is not None:
        out = _NAME_CANDIDATE_RE.sub(
            lambda m: PERSONAL_DATA_REMOVED if person_screen(m.group(0)) else m.group(0),
            out,
        )
    return out


def reviewer_role(
    reviewed_by: str | None, *, person_screen: Callable[[str], bool] | None = None
) -> str:
    """J3 §3.5 / S-7: rights reviewers publish by ROLE only.

    A recorded value that is e-mail-shaped or a person-name shape — bare, or
    flagged by the injected ``person_screen`` — refuses to
    :data:`ROLE_UNSPECIFIED`; the identity is never echoed.
    """
    value = str(reviewed_by or "").strip()
    if not value or "@" in value:
        return ROLE_UNSPECIFIED
    if _NAME_CANDIDATE_RE.fullmatch(value):
        return ROLE_UNSPECIFIED
    if person_screen is not None and person_screen(value):
        return ROLE_UNSPECIFIED
    return value


# ---------------------------------------------------------------------------
# S-9 — withdrawal tombstones
# ---------------------------------------------------------------------------


def tombstone_id(withdrawn_id: object) -> str:
    """S-9: a withdrawn claim/capture/artifact reference publishes as a
    deterministic opaque tombstone id — never the withdrawn identifier itself."""
    digest = hashlib.sha256(str(withdrawn_id).encode("utf-8")).hexdigest()[:16]
    return f"tombstone:{digest}"


# ---------------------------------------------------------------------------
# S-10 — timestamps: full ISO-8601 UTC, never date-only
# ---------------------------------------------------------------------------


def iso_utc(value: object) -> str | None:
    """S-10: a full ISO-8601 UTC timestamp — the ``retrieved_at`` date-only
    defect (J4 S-10, J1) is fixed here, once.

    ``datetime``/``date`` values normalise to ``…T…Z``; ISO strings pass
    through with ``+00:00`` normalised to ``Z``; ``None``/empty is ``None`` —
    the caller renders its absence token.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
        return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")
    if isinstance(value, date):
        return (
            datetime(value.year, value.month, value.day, tzinfo=UTC)
            .isoformat()
            .replace("+00:00", "Z")
        )
    text = str(value).strip()
    if not text:
        return None
    return text[:-6] + "Z" if text.endswith("+00:00") else text


# ---------------------------------------------------------------------------
# S-11 — gated/refused sources publish a registry-only row
# ---------------------------------------------------------------------------

#: The closed reason-class vocabulary S-11 rows carry (J3 §4.3's
#: ``terms`` · ``part_viii`` · ``not_reviewed`` plus the lifecycle classes).
GATED_REASON_CLASSES: frozenset[str] = frozenset(
    {"terms", "part_viii", "not_reviewed", "refused", "gated", "unknown_lane"}
)

#: The fields a gated/refused row may carry — name, publisher, status, reason
#: class, homepage (J3 §4.3's registry-only page). Never runs, captures,
#: samples or probe details.
GATED_SOURCE_COLUMNS: tuple[str, ...] = (
    "source_id",
    "name",
    "publisher",
    "publisher_type",
    "status",
    "homepage_url",
)


def gated_source_row(source: Mapping[str, Any], *, reason_class: str) -> dict[str, Any]:
    """S-11: the registry-only row a gated, refused or unknown-lane source
    publishes. ``reason_class`` must come from the closed vocabulary."""
    if reason_class not in GATED_REASON_CLASSES:
        raise ScrubViolation(f"unknown gated reason class {reason_class!r}")
    row = explicit_columns(source, GATED_SOURCE_COLUMNS)
    row["reason_class"] = reason_class
    return row


# ---------------------------------------------------------------------------
# S-13 — robots outcomes: per-host disclosure
# ---------------------------------------------------------------------------

ROBOTS_OUTCOMES: frozenset[str] = frozenset({"obeyed", "disallowed", "unavailable", "disregarded"})

#: The decision reference a ``disregarded`` disclosure names (Q-J4-4 / D-J3-2:
#: host + count + policy reference — never per-URL detail).
ROBOTS_DISREGARD_DECISION_REF = "GL-GATE-08"


def robots_disclosure_rows(
    outcomes: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """S-13: per-host robots outcome rows. ``obeyed``, ``disallowed`` and
    ``unavailable`` always publish; ``disregarded`` publishes as host + count +
    the GL-GATE-08 reference. An outcome outside the vocabulary fails closed."""
    rows: list[dict[str, Any]] = []
    for o in outcomes:
        outcome = str(o.get("outcome") or "")
        if outcome not in ROBOTS_OUTCOMES:
            raise ScrubViolation(f"unknown robots outcome {outcome!r} (S-13)")
        row: dict[str, Any] = {
            "host": str(o.get("host") or ""),
            "outcome": outcome,
            "count": int(o.get("count") or 0),
        }
        if outcome == "disregarded":
            row["decision_ref"] = ROBOTS_DISREGARD_DECISION_REF
        rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# The redistribution lane — interim derivation (NEW-2 / F-400)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LaneDecision:
    """A redistribution-lane verdict plus the basis that produced it.

    ``basis`` names where the inputs came from — ``interim:rights-record``
    until row 313's ``[redistribution]`` fields land — so a consumer records
    the interim basis rather than implying a reviewed lane field.
    """

    lane: str
    basis: str = "interim:rights-record"


#: J4 R-12: the explicit upstream open licences/dedications the interim basis
#: can read. ``LicenseRef-DerivedFacts-Citations`` / ``-PublicRecord-
#: FactualCompilation`` / ``-OperatorAccepted-DBRight`` are deliberately absent —
#: they are derived-only bases (R-7…R-9), matched before this set is consulted.
_OPEN_LICENCE_PREFIXES: tuple[str, ...] = (
    "CC0",
    "CC-BY-",
    "CC-BY-SA-",
    "ODbL",
    "PDDL",
    "OGL",
    "etalab",  # Licence Ouverte (Etalab)
    "LicenseRef-Ottawa-ODL",
    "LicenseRef-Peel-ODL",
    "LicenseRef-StAlbert-ODL",
    "MIT",
    "AGPL",
)

#: NC/ND Creative Commons variants restrict redistribution/derivatives — R-2
#: territory, never raw-ok even though the CC-BY prefix matches.
_RESTRICTIVE_CC_PREFIXES: tuple[str, ...] = (
    "CC-BY-NC",
    "CC-BY-ND",
    "CC-BY-SA-NC",
    "CC-BY-SA-ND",
)


def open_upstream_licence(spdx: str | None) -> bool:
    """J4 R-12: is the declared expression an explicit upstream open licence —
    CC0/PD/PDDL, CC-BY*/CC-BY-SA* (never an NC/ND variant), ODbL, OGL-UK/Canada,
    the municipal ODLs, Licence Ouverte, MIT/AGPL?"""
    s = str(spdx or "").strip()
    if not s or s == "UNDETERMINED":
        return False
    if any(s.startswith(p) for p in _RESTRICTIVE_CC_PREFIXES):
        return False
    return any(s.startswith(p) for p in _OPEN_LICENCE_PREFIXES)


def _redist_value(value: object) -> str:
    """Normalise a recorded redistributable flag to the spine vocabulary."""
    if value is True:
        return "yes"
    if value is False:
        return "no"
    v = str(value or "").strip()
    return v if v in {"yes", "no", "review_required", "UNDETERMINED"} else ""


def interim_lane(
    *,
    custody_posture: object = None,
    spdx: object = None,
    redistributable: object = None,
    reviewed: object = None,
    refused: object = False,
    packet_limited: object = False,
    sig_labelled_cc0: object = False,
    basis: str = "interim:rights-record",
) -> LaneDecision:
    """The interim redistribution lane — J4's R-rules over the rights record
    the registry already carries (the row-313 ``[redistribution]`` fields are
    not landed yet; the interim basis is recorded, never guessed).

    Precedence follows J4's ordered rule list — the first matching rule wins:

    * refused (a recorded do-not-ingest / permission-declined decision) →
      ``restricted`` (R-1);
    * recorded ``redistributable = no`` → ``restricted`` (R-3);
    * unreviewed or unresolved rights (no completed review, or no ``yes``, or
      ``UNDETERMINED``/absent SPDX) → ``link-only`` on a ``LINK`` custody, else
      ``unknown`` (R-5 — fail closed);
    * custody ``LINK`` → ``link-only`` (R-6);
    * custody ``DERIVE`` or ``LicenseRef-DerivedFacts-Citations`` →
      ``derived-only`` (R-7);
    * ``LicenseRef-PublicRecord-FactualCompilation`` /
      ``LicenseRef-OperatorAccepted-DBRight`` → ``derived-only`` (R-8/R-9);
    * caller-injected ``packet_limited`` / ``sig_labelled_cc0`` →
      ``derived-only`` (R-10/R-11 — packet facts the record cannot read);
    * an explicit upstream open licence → ``raw-ok`` (R-12);
    * anything else → ``unknown``.
    """
    custody = str(custody_posture or "").strip().upper()
    spdx_s = str(spdx or "").strip()
    redist = _redist_value(redistributable)

    if refused:
        return LaneDecision(LANE_RESTRICTED, basis)
    if redist == "no":
        return LaneDecision(LANE_RESTRICTED, basis)
    if not reviewed or redist != "yes" or not spdx_s or spdx_s == "UNDETERMINED":
        # R-5 / unresolved: an unreviewed or undecided rights record can never
        # evidence raw republication — link-only on a LINK custody, else unknown.
        return LaneDecision(LANE_LINK_ONLY if custody == "LINK" else LANE_UNKNOWN, basis)
    if custody == "LINK":
        return LaneDecision(LANE_LINK_ONLY, basis)
    if custody == "DERIVE" or spdx_s == "LicenseRef-DerivedFacts-Citations":
        return LaneDecision(LANE_DERIVED_ONLY, basis)
    if spdx_s in (
        "LicenseRef-PublicRecord-FactualCompilation",
        "LicenseRef-OperatorAccepted-DBRight",
    ):
        return LaneDecision(LANE_DERIVED_ONLY, basis)
    if packet_limited or sig_labelled_cc0:
        return LaneDecision(LANE_DERIVED_ONLY, basis)
    if open_upstream_licence(spdx_s):
        return LaneDecision(LANE_RAW_OK, basis)
    return LaneDecision(LANE_UNKNOWN, basis)


# ---------------------------------------------------------------------------
# Storage-tier derivation (J3 §3.3 item 4 / NEW-2 / F-400)
# ---------------------------------------------------------------------------


def derive_storage_tier(lane: str | None, part_viii_class: str | None = None) -> str:
    """The J3 tier mapping — fail closed, NEVER ``public`` by default.

    * ``restricted`` lane or a P8-1/P8-2/P8-4 class → ``sealed``;
    * ``derived-only`` / ``link-only`` → ``restricted``;
    * ``raw-ok`` + a recorded P8-clear → ``public``;
    * ``raw-ok`` + a recorded non-sealed P8 class → ``restricted`` (the bytes
      stay field-screened);
    * ``raw-ok`` + an unevidenced class → ``sealed``;
    * an unknown or absent lane → ``sealed``.
    """
    lane_v = str(lane or "").strip()
    p8 = str(part_viii_class or "").strip()
    if lane_v == LANE_RESTRICTED or p8 in PART_VIII_SEALED_CLASSES:
        return TIER_SEALED
    if lane_v in (LANE_DERIVED_ONLY, LANE_LINK_ONLY):
        return TIER_RESTRICTED
    if lane_v == LANE_RAW_OK:
        if p8 in PART_VIII_CLEAR_VALUES:
            return TIER_PUBLIC
        if p8 in PART_VIII_CLASSES:
            return TIER_RESTRICTED
        return TIER_SEALED
    return TIER_SEALED


def more_restrictive_tier(a: str | None, b: str | None) -> str:
    """The more restrictive of two tiers — the read path may tighten, never
    relax. An unrecognised value ranks as — and normalises to — ``sealed``;
    the answer is always a member of :data:`STORAGE_TIERS`."""
    ta = str(a or "")
    tb = str(b or "")
    if ta not in _TIER_RANK:
        ta = TIER_SEALED
    if tb not in _TIER_RANK:
        tb = TIER_SEALED
    return ta if _TIER_RANK[ta] >= _TIER_RANK[tb] else tb


@dataclass(frozen=True)
class TierDerivation:
    """The served storage tier and the basis that produced it.

    ``basis`` is ``recorded`` when the served value is the row's recorded tier
    and ``derived_at_read`` when the lane+class floor tightened a row written
    before the writer derivation landed — the served value names its basis,
    never a silent ``public`` upgrade (F-400).
    """

    tier: str
    basis: str
    recorded_tier: str | None = None


def served_storage_tier(
    recorded_tier: str | None,
    *,
    lane: str | None,
    part_viii_class: str | None = None,
) -> TierDerivation:
    """The tier a public read serves: the MORE restrictive of the recorded tier
    and the lane+Part VIII derivation.

    Rows written before the writer fix carry the constant ``'public'``; the
    derivation catches the ones the lane would never have allowed (a legacy
    row is handled without a silent ``public`` upgrade, and the adjustment is
    labelled). A recorded ``sealed``/``restricted`` is never relaxed — the
    floor tightens only.
    """
    recorded = str(recorded_tier or "")
    if recorded not in STORAGE_TIERS:
        recorded = TIER_SEALED
    derived = derive_storage_tier(lane, part_viii_class)
    effective = more_restrictive_tier(recorded, derived)
    if effective == recorded:
        return TierDerivation(tier=effective, basis="recorded")
    return TierDerivation(tier=effective, basis="derived_at_read", recorded_tier=recorded)


# ---------------------------------------------------------------------------
# The transparency view column allow-lists (P35.33 / J3 §3.3 items 1–2)
# ---------------------------------------------------------------------------

#: The columns ``v_transparency_run`` may carry — the scrub vocabulary's
#: positive allow-list for the run surface. A view column this list does
#: not name fails the closure test (the contract's "every field scrubbed
#: through ``policy.transparency``"): run-level fields shared by more than
#: one execution land NULL and the export renders ``not_recorded (shared
#: run)`` (K10 §18 C-13); ``detail``, ``parameters``, ``environment``,
#: ``backfilled_from`` and the gs:// WORM locators are never-exported
#: (S-2/S-3/S-4) and never appear here.
TRANSPARENCY_RUN_VIEW_COLUMNS: tuple[str, ...] = (
    "report_id",
    "run_id",
    "source_id",
    "link_basis",
    "clock_basis",
    "shared_run",
    "started_at",
    "finished_at",
    "duration_seconds",
    "completion_status",
    "claims_considered",
    "claims_inserted",
    "claims_duplicate",
    "fetches",
    "records_emitted",
    "robots_outcomes",
    "refusal_classes",
    "rate_limit_events",
    "disappearances",
    "document_outcomes",
    "quota_reached",
    "budget_reached",
    "error_class",
    "per_fetch",
    "connector_name",
    "connector_version",
    "code_commit",
    "recorded_at",
)

#: The columns ``v_transparency_capture`` may carry. ``target_key`` /
#: ``source_uri`` pass through the S-6 URL scrub at emission (the view is
#: ``sig_export``-only — the artifact, not the view, is the publication
#: boundary); a sealed-tier capture's URL never leaves this surface. The
#: trailing four are P35.41's freshness columns (``capture_freshness_marks``):
#: the emitted record-set fingerprint and the upstream's DECLARED change
#: value with its basis — declared metadata only, never raw headers.
TRANSPARENCY_CAPTURE_VIEW_COLUMNS: tuple[str, ...] = (
    "run_id",
    "target_key",
    "state",
    "source_uri",
    "records",
    "mark_digest",
    "capture_classification",
    "storage_tier",
    "byte_size",
    "media_type",
    "retrieved_at",
    "mark_recorded_at",
    "bytes_retained",
    "redaction_applied",
    "redacted_derivative",
    "http_status",
    "source_id",
    "shared_run",
    "records_digest",
    "upstream_modified_at",
    "upstream_token",
    "upstream_modified_basis",
)

#: The columns ``v_transparency_source`` may carry (P35.35 / J3 §3.3 item 3):
#: the registry-of-record identity + posture fields, the rights record, the
#: latest rights decision's basis/reviewer-ROLE/decided_at, the recorded
#: ``[redistribution]`` lane fields the sink mirrors into
#: ``source_redistribution``, and the last-seen freshness columns. The view is
#: ``sig_export``-only — the artifact, not the view, is the publication
#: boundary: classified upstream terms text, registry ``notes``,
#: ``auth_model``/``access_method``/``contact`` and every never-exported field
#: stay off the list (a P8-1 payload is never a column).
TRANSPARENCY_SOURCE_VIEW_COLUMNS: tuple[str, ...] = (
    "source_id",
    "name",
    "source_kind",
    "homepage_url",
    "custody_posture",
    "compact_status",
    "ingestion_permitted",
    "robots_policy",
    "last_verified_at",
    "spdx_expression",
    "attribution_text",
    "redistributable",
    "derivative_permitted",
    "terms_url",
    "terms_reviewed",
    "terms_reviewed_at",
    "retrieval_date",
    "rights_decision_basis",
    "rights_decision_reviewer",
    "rights_decided_at",
    "lane",
    "lane_evidence",
    "lane_evidence_uri",
    "lane_decision_authority",
    "lane_review_needed",
    "part_viii_class",
    "packet_limited",
    "sig_labelled_cc0",
    "last_execution_at",
    "last_capture_at",
)

#: The columns ``v_claim_sightings`` may carry (P35.44 / DSRC-01, K5 §3.1):
#: the establishing-link edge list the dossier/source contribution aggregate
#: reads — one row per claim×``claim_evidence``(role ``establishes``)×capture
#: ×artifact, exposing only what the aggregate's publication gates and
#: first/last-seen computation need. The view is ``sig_export``-only — the
#: artifact, not the view, is the publication boundary: raw locators, excerpts,
#: evidence content/digests, OCFL object identifiers, capture URLs and every
#: other never-exported field stay off the list.
CLAIM_SIGHTING_VIEW_COLUMNS: tuple[str, ...] = (
    "claim_id",
    "subject_id",
    "object_entity",
    "predicate_id",
    "sensitivity_tier",
    "rights_id",
    "sys_period",
    "capture_id",
    "role",
    "binding_status",
    "bound_at",
    "artifact_id",
    "source_id",
    "run_id",
    "retrieved_at",
)


# ---------------------------------------------------------------------------
# The bounded free-text scrub (S-2 + S-5 + S-7 in one pass)
# ---------------------------------------------------------------------------


def scrub_text(
    text: str,
    *,
    names: Iterable[str] = (),
    person_screen: Callable[[str], bool] | None = None,
) -> str:
    """The composite scrub a bounded, reviewed free-text field passes —
    internal locations (S-2), IP addresses (S-5), personal data (S-7).

    S-8 fields (record excerpts, search reasons, snippets) are NEVER inputs to
    this function — they are never-exported and never reach a surface. S-4
    error text is a different rule: class + count, never this pass.
    """
    out = scrub_internal_locations(text)
    out = strip_ip_addresses(out)
    return scrub_personal(out, names=names, person_screen=person_screen)
