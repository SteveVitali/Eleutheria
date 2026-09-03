# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""EDTF Level 1 encoding and the pinned, deterministic envelope derivation (§16.7).

Uncertain, approximate, and open-ended dates are stored as **EDTF Level 1**
strings (`valid_edtf`, `observed_edtf`, `published_at_edtf`) — never sharpened to
a false-precise timestamp (SIG-STORE-021/022, SIG-TIME-006). A source that says
"in early 2025" is `2025-03~`, and it MUST NOT become `2025-01-01`.

For indexed range queries the store also needs a machine-usable `tstzrange`
*envelope*. That envelope is derived by a **pinned, versioned, deterministic**
function (ADR-004, ADR-024): the same EDTF string always yields the same
envelope, and the widening rules are identified by `ENVELOPE_RULESET_VERSION`,
which an `ingest_run` records in its `ruleset_version` so every derivation is
reproducible and auditable. This module owns that function; it is the stable
interface every read path (API, export, UI) depends on.

The parser implements the EDTF (ISO 8601-2) Level 1 subset SIG uses: complete
dates and reduced-precision years/months; the `?` (uncertain), `~`
(approximate), and `%` (both) qualifiers; seasons (21-24); unspecified digits
(`X`); and intervals with open (`..`) or unknown (empty) ends. Level 2 is out of
scope. Only stdlib is used, so the derivation is dependency-free and its
determinism cannot drift with a third-party release (ADR-024's revisit trigger is
exactly the appearance of a maintained, deterministic Level 1 library).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

# The identifier an ingest_run stamps in `ruleset_version` for envelope
# derivation. Any change to the widening rules below MUST bump this string so a
# re-derivation is detectable and old envelopes stay attributable to old rules.
ENVELOPE_RULESET_VERSION = "edtf-envelope-1"

# Widening applied when a value is approximate (`~`) or approximate+uncertain
# (`%`). `?` (uncertain) is a *flag on the value*, not a claim that the true date
# is nearby, so it does NOT widen the envelope. These constants are the whole of
# the ruleset that ENVELOPE_RULESET_VERSION names.
_APPROX_YEAR_SLOP_YEARS = 1
_APPROX_MONTH_SLOP_MONTHS = 2
_APPROX_DAY_SLOP_DAYS = 5

_UTC = UTC

# Season code -> (start_month, month_span). EDTF Level 1 seasons (21-24).
_SEASONS: dict[int, tuple[int, int]] = {
    21: (3, 3),  # spring: Mar-May
    22: (6, 3),  # summer: Jun-Aug
    23: (9, 3),  # autumn: Sep-Nov
    24: (12, 3),  # winter: Dec-Feb (of the following year)
}


class EdtfError(ValueError):
    """The string is not valid EDTF Level 1 (as SIG uses it)."""


def _dt(year: int, month: int, day: int) -> datetime:
    return datetime(year, month, day, tzinfo=_UTC)


def _add_months(dt: datetime, months: int) -> datetime:
    total = (dt.year * 12 + (dt.month - 1)) + months
    year, month = divmod(total, 12)
    return _dt(year, month + 1, dt.day)


@dataclass(frozen=True)
class Envelope:
    """A half-open `[lower, upper)` instant range; `None` bound = infinite.

    Maps directly onto a PostgreSQL `tstzrange`: `lower is None` is `-infinity`,
    `upper is None` is `+infinity`. SIG stores envelopes half-open and
    lower-inclusive so adjacent intervals abut without overlap.
    """

    lower: datetime | None
    upper: datetime | None

    def to_tstzrange_literal(self) -> str:
        """Render as a SQL `tstzrange(...)` constructor call (bounds `'[)'`)."""
        lo = f"'{self.lower.isoformat()}'" if self.lower is not None else "NULL"
        hi = f"'{self.upper.isoformat()}'" if self.upper is not None else "NULL"
        return f"tstzrange({lo}, {hi}, '[)')"


@dataclass(frozen=True)
class EdtfDate:
    """A single reduced-precision EDTF date value (not an interval)."""

    year: int | None  # None only for the fully-unknown value
    month: int | None  # 1-12, or a season code 21-24, or None
    day: int | None
    uncertain: bool = False  # `?`
    approximate: bool = False  # `~` (or the approximate half of `%`)
    # For unspecified digits (`201X`, `19XX`), the [lower, upper) year span the
    # mask expands to. When set it overrides year-precision windowing.
    year_span: tuple[int, int] | None = None

    @property
    def precision(self) -> str:
        if self.year is None:
            return "none"
        if self.day is not None:
            return "day"
        if self.month is not None:
            return "month"
        return "year"


@dataclass(frozen=True)
class EdtfInterval:
    """An EDTF interval `start/end`; an endpoint is a date, `open`, or `unknown`."""

    start: EdtfDate | None  # None = open (`..`) or unknown (empty) start
    end: EdtfDate | None  # None = open (`..`) or unknown (empty) end
    start_open: bool = False  # `../` (known to extend) vs `/` (unknown)
    end_open: bool = False


EdtfValue = EdtfDate | EdtfInterval


# --- parsing -----------------------------------------------------------------

_QUALIFIER_RE = re.compile(r"([?~%])$")
_YEAR_ONLY_RE = re.compile(r"^-?\d{4}$")
_MASKED_YEAR_RE = re.compile(r"^\d{1,3}X{1,3}$")


def _split_qualifier(token: str) -> tuple[str, bool, bool]:
    """Strip a trailing `?`/`~`/`%`; return (body, uncertain, approximate)."""
    m = _QUALIFIER_RE.search(token)
    if not m:
        return token, False, False
    q = m.group(1)
    body = token[: m.start()]
    return body, q in "?%", q in "~%"


def _parse_date(token: str) -> EdtfDate:
    body, uncertain, approximate = _split_qualifier(token)
    if not body:
        raise EdtfError(f"empty EDTF date: {token!r}")

    # A leading '-' denotes a negative (BCE) year; strip it before splitting.
    neg = body.startswith("-")
    if neg:
        body = body[1:]
    parts = body.split("-")
    if not 1 <= len(parts) <= 3:
        raise EdtfError(f"not an EDTF Level 1 date: {token!r}")

    year_tok = parts[0]
    year_span: tuple[int, int] | None = None
    year: int | None
    if _MASKED_YEAR_RE.fullmatch(year_tok) and len(year_tok) == 4:
        lo = int(year_tok.replace("X", "0"))
        hi = int(year_tok.replace("X", "9")) + 1
        year, year_span = lo, (lo, hi)
    elif re.fullmatch(r"\d{4}", year_tok):
        year = int(year_tok)
    else:
        raise EdtfError(f"not an EDTF Level 1 year: {year_tok!r}")
    if neg:
        year = -year

    month: int | None = None
    day: int | None = None
    if len(parts) >= 2:
        month = _parse_masked_component(parts[1], lo=1, hi=24, name="month")
        if month is not None and 13 <= month <= 20:
            raise EdtfError(f"invalid EDTF month/season: {parts[1]!r}")
    if len(parts) == 3:
        if month is None:
            raise EdtfError(f"day present without month: {token!r}")
        day = _parse_masked_component(parts[2], lo=1, hi=31, name="day")

    date = EdtfDate(
        year=year,
        month=month,
        day=day,
        uncertain=uncertain,
        approximate=approximate,
        year_span=year_span,
    )
    # Validate a fully-specified day is a real calendar date.
    if date.day is not None and date.month is not None and date.month <= 12:
        try:
            _dt(date.year or 4, date.month, date.day)
        except ValueError as exc:
            raise EdtfError(f"impossible calendar date: {token!r}") from exc
    return date


def _parse_masked_component(tok: str, *, lo: int, hi: int, name: str) -> int | None:
    """Parse a month/day component that may be fully unspecified (`XX`)."""
    if len(tok) != 2:
        raise EdtfError(f"{name} must be two characters (EDTF): {tok!r}")
    if set(tok) == {"X"}:
        return None
    if not tok.isdigit():
        raise EdtfError(f"unspecified digits inside a component are Level 2: {tok!r}")
    val = int(tok)
    if not lo <= val <= hi:
        raise EdtfError(f"{name} out of range: {tok!r}")
    return val


def parse_edtf(value: str) -> EdtfValue:
    """Parse an EDTF Level 1 string; raise :class:`EdtfError` if invalid."""
    if not isinstance(value, str) or not value.strip():
        raise EdtfError("EDTF value must be a non-empty string")
    token = value.strip()

    # The fully-unknown value SIG writes as a bare `..` (both ends open).
    if token == "..":
        return EdtfInterval(start=None, end=None, start_open=True, end_open=True)

    if "/" in token:
        left, sep, right = token.partition("/")
        start, start_open = _parse_endpoint(left)
        end, end_open = _parse_endpoint(right)
        if start is None and end is None:
            raise EdtfError(f"interval with two empty ends: {token!r}")
        return EdtfInterval(start=start, end=end, start_open=start_open, end_open=end_open)

    return _parse_date(token)


def _parse_endpoint(tok: str) -> tuple[EdtfDate | None, bool]:
    """Parse one side of an interval: a date, `..` (open), or empty (unknown)."""
    if tok == "":
        return None, False  # unknown end
    if tok == "..":
        return None, True  # open end
    return _parse_date(tok), False


# --- canonical round-trip -----------------------------------------------------


def _fmt_component(val: int, width: int) -> str:
    return f"{val:0{width}d}"


def _canonical_date(d: EdtfDate) -> str:
    if d.year_span is not None:
        lo, _hi = d.year_span
        n_x = _mask_width(d.year_span)
        base = str(lo).zfill(4)
        body = base[: 4 - n_x] + "X" * n_x
    else:
        sign = "-" if (d.year is not None and d.year < 0) else ""
        body = (sign + _fmt_component(abs(d.year), 4)) if d.year is not None else ""
        if d.month is not None:
            body += "-" + _fmt_component(d.month, 2)
        if d.day is not None:
            body += "-" + _fmt_component(d.day, 2)
    if d.uncertain and d.approximate:
        body += "%"
    elif d.uncertain:
        body += "?"
    elif d.approximate:
        body += "~"
    return body


def _mask_width(year_span: tuple[int, int]) -> int:
    lo, hi = year_span
    span = hi - lo
    # span is 10**n for n masked digits.
    n = 0
    while span > 1:
        span //= 10
        n += 1
    return n


def canonical(value: str) -> str:
    """Return the canonical EDTF spelling; validates via a parse round-trip."""
    parsed = parse_edtf(value)
    if isinstance(parsed, EdtfDate):
        return _canonical_date(parsed)
    start = (
        ".."
        if parsed.start_open
        else ("" if parsed.start is None else _canonical_date(parsed.start))
    )
    end = ".." if parsed.end_open else ("" if parsed.end is None else _canonical_date(parsed.end))
    if parsed.start is None and parsed.end is None:
        return ".."
    return f"{start}/{end}"


# --- envelope derivation (the pinned, deterministic function) -----------------


def _date_window(d: EdtfDate) -> tuple[datetime, datetime]:
    """The precise `[lower, upper)` instant window for a date, before widening."""
    if d.year is None:
        raise EdtfError("cannot window a yearless date")
    if d.year_span is not None:
        lo, hi = d.year_span
        return _dt(lo, 1, 1), _dt(hi, 1, 1)
    if d.month is None:
        return _dt(d.year, 1, 1), _dt(d.year + 1, 1, 1)
    if d.month >= 21:  # season
        start_month, span = _SEASONS[d.month]
        lower = _dt(d.year, start_month, 1)
        return lower, _add_months(lower, span)
    if d.day is None:
        lower = _dt(d.year, d.month, 1)
        return lower, _add_months(lower, 1)
    lower = _dt(d.year, d.month, d.day)
    return lower, lower + timedelta(days=1)


def _widen(d: EdtfDate, lower: datetime, upper: datetime) -> tuple[datetime, datetime]:
    """Apply the approximate-qualifier widening for ENVELOPE_RULESET_VERSION."""
    if not d.approximate:
        return lower, upper
    if d.precision == "day":
        return lower - timedelta(days=_APPROX_DAY_SLOP_DAYS), upper + timedelta(
            days=_APPROX_DAY_SLOP_DAYS
        )
    if d.precision == "month":
        return _add_months(lower, -_APPROX_MONTH_SLOP_MONTHS), _add_months(
            upper, _APPROX_MONTH_SLOP_MONTHS
        )
    # year precision
    return _dt(lower.year - _APPROX_YEAR_SLOP_YEARS, 1, 1), _dt(
        upper.year + _APPROX_YEAR_SLOP_YEARS, 1, 1
    )


def derive_envelope(value: str, *, ruleset_version: str = ENVELOPE_RULESET_VERSION) -> Envelope:
    """Derive the deterministic `tstzrange` envelope for an EDTF string.

    Pure and total over valid EDTF Level 1: the same input always yields the same
    output. `ruleset_version` must match :data:`ENVELOPE_RULESET_VERSION`; a
    mismatch is refused rather than silently applying today's rules to a value
    derived under a different ruleset.
    """
    if ruleset_version != ENVELOPE_RULESET_VERSION:
        raise EdtfError(
            f"unknown envelope ruleset {ruleset_version!r}; "
            f"this build derives {ENVELOPE_RULESET_VERSION!r}"
        )
    parsed = parse_edtf(value)
    if isinstance(parsed, EdtfDate):
        date_lower, date_upper = _widen(parsed, *_date_window(parsed))
        return Envelope(lower=date_lower, upper=date_upper)

    # Interval: lower comes from the start's window lower, upper from the end's
    # window upper. An open/unknown end contributes an infinite bound.
    lower: datetime | None = None
    upper: datetime | None = None
    if parsed.start is not None:
        lower, _ = _widen(parsed.start, *_date_window(parsed.start))
    if parsed.end is not None:
        _, upper = _widen(parsed.end, *_date_window(parsed.end))
    return Envelope(lower=lower, upper=upper)


# --- kind inference (best-effort convenience over the authoritative columns) ---


# The authoritative bound kinds are the stored `valid_from_kind`/`valid_to_kind`
# columns (§9.3), set by the extractor. This helper reproduces the §16.7 table's
# inferred kinds from the EDTF spelling alone, for callers that have only the
# string (e.g. rendering `published_at_edtf`).
def infer_kinds(value: str) -> tuple[str, str]:
    """Infer `(from_kind, to_kind)` from an EDTF string per the §16.7 table.

    Best-effort convenience over the authoritative `valid_from_kind` /
    `valid_to_kind` columns, for callers holding only the EDTF string. The
    §16.7-tabulated cases are exact; a closed interval reports the natural kind of
    each known bound.
    """
    parsed = parse_edtf(value)
    if isinstance(parsed, EdtfDate):
        return _known_kind(parsed), _known_kind(parsed)
    # The fully-unknown sentinel (`..`, both ends open) is unknown at both bounds
    # — "the department has used ALPRs for years" (§16.7), not an ongoing edge.
    if parsed.start is None and parsed.end is None:
        return "unknown", "unknown"

    # from-kind: a known start is its natural kind; an open/unknown start is unknown.
    from_kind = "unknown" if parsed.start is None else _known_kind(parsed.start)
    # to-kind: a known end is "before" when the start is open/unknown (bounded
    # above only), else its natural kind; an open end is "ongoing", an unknown
    # (empty) end is "unknown".
    if parsed.end is not None:
        to_kind = "before" if parsed.start is None else _known_kind(parsed.end)
    elif parsed.end_open:
        to_kind = "ongoing"
    else:
        to_kind = "unknown"
    return from_kind, to_kind


def _known_kind(date: EdtfDate) -> str:
    if date.approximate:
        return "approximate"
    if date.uncertain:
        return "uncertain"
    return "exact"
