# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The host-level opt-out register (§26 rule 7, SIG-INGEST-036; P36.1a / ADR-168).

Rule 7 requires opt-outs to be honoured **immediately** — "immediately" cannot
mean "after a rebuild and redeploy". This module is the runtime consult:
``PoliteFetcher.fetch`` checks the register *before every fetch* — before even
the robots probe — and refuses a listed host with no egress at all; the loader
gate consults it for the source-level verdict.

Two layers make "immediately" real:

* The **committed register** (``data/opt_out_register.toml``) is the reviewed,
  append-only record — the artifact of record every run consults by default.
* ``$SIG_OPT_OUT_REGISTER`` may name an operator-supplied register file that
  takes precedence (a mounted artifact on the ingest host). Swapping that file
  applies an entry on the next run with **no code change, no image rebuild** —
  the mechanism E2-06/NEW-3 found missing.

The register is consulted, never publicised here (the disclosure option is
Stream J). Rows are append-only: an entry is evidence-bearing
(``host`` + ``recorded_on`` + ``evidence``) and malformed rows fail closed.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from datetime import date
from importlib.resources import files
from pathlib import Path
from typing import Any

#: The environment variable naming an operator-supplied register file that
#: overrides the packaged default (the "immediately" seam, §26 rule 7).
OPT_OUT_REGISTER_ENV = "SIG_OPT_OUT_REGISTER"

#: The packaged register artifact (committed, append-only).
_PACKAGED_REGISTER = "opt_out_register.toml"


class OptOutRegisterError(ValueError):
    """A malformed opt-out register — parsing fails closed."""


def normalize_host(host: str) -> str:
    """Canonical host form: lowercase, no scheme, no port, no trailing dot."""
    h = host.strip().lower()
    for scheme in ("https://", "http://"):
        if h.startswith(scheme):
            h = h[len(scheme) :]
    h = h.split("/", 1)[0].split(":", 1)[0].rstrip(".")
    return h


@dataclass(frozen=True)
class OptOutEntry:
    """One recorded host-level opt-out (§26 rule 7). Evidence-bearing: the
    ``evidence`` field names where the opt-out was received (a dispute/intake
    record, an operator instruction, a host's published request)."""

    host: str
    recorded_on: date
    evidence: str
    note: str = ""

    @property
    def reason(self) -> str:
        """The refusal reason the gate/fetch path records."""
        return (
            f"host {self.host!r} is on the opt-out register "
            f"(recorded {self.recorded_on.isoformat()}, §26 rule 7, "
            f"evidence: {self.evidence})"
        )


@dataclass(frozen=True)
class OptOutRegister:
    """The parsed host-level opt-out register — a set of listed hosts."""

    entries: tuple[OptOutEntry, ...] = ()
    source: str = "packaged"

    def entry_for(self, host: str) -> OptOutEntry | None:
        """The entry listing ``host``, or ``None`` (sub-domains included).

        A listed host covers itself and its sub-domains: opting out of
        ``example.org`` covers ``www.example.org``. The reverse is not true —
        an entry for ``a.example.org`` lists only that host and below.
        """
        normalized = normalize_host(host)
        for entry in self.entries:
            listed = entry.host
            if normalized == listed or normalized.endswith("." + listed):
                return entry
        return None

    def reason_for(self, host: str) -> str | None:
        """The refusal reason for ``host``, or ``None`` when not listed."""
        entry = self.entry_for(host)
        return entry.reason if entry is not None else None

    def is_listed(self, host: str) -> bool:
        """Whether ``host`` is on the register."""
        return self.entry_for(host) is not None

    def listed_hosts(self, hosts: list[str] | tuple[str, ...]) -> list[OptOutEntry]:
        """The entries covering any of ``hosts`` — the gate's coverage view."""
        out: list[OptOutEntry] = []
        seen: set[str] = set()
        for host in hosts:
            entry = self.entry_for(host)
            if entry is not None and entry.host not in seen:
                out.append(entry)
                seen.add(entry.host)
        return out


def _parse_entries(table: dict[str, Any], source: str) -> tuple[OptOutEntry, ...]:
    rows = table.get("opt_outs", [])
    if not isinstance(rows, list):
        raise OptOutRegisterError(
            f"{source}: [[opt_outs]] must be an array of tables (got {type(rows).__name__})"
        )
    entries: list[OptOutEntry] = []
    seen: set[str] = set()
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            raise OptOutRegisterError(f"{source}: opt_outs[{i}] is not a table")
        host_raw = str(row.get("host", "")).strip()
        if not host_raw:
            raise OptOutRegisterError(f"{source}: opt_outs[{i}] lacks a host")
        host = normalize_host(host_raw)
        if not host:
            raise OptOutRegisterError(f"{source}: opt_outs[{i}] host {host_raw!r} is empty")
        recorded_on = row.get("recorded_on")
        if not isinstance(recorded_on, date):
            raise OptOutRegisterError(
                f"{source}: opt_outs[{i}] ({host}) recorded_on must be a TOML date — "
                "an opt-out is recorded the day it lands (OM-04)"
            )
        evidence = str(row.get("evidence", "")).strip()
        if not evidence:
            raise OptOutRegisterError(
                f"{source}: opt_outs[{i}] ({host}) lacks evidence — a register entry "
                "is asserted only on evidence (§3.1)"
            )
        if host in seen:
            raise OptOutRegisterError(f"{source}: duplicate opt-out host {host!r}")
        seen.add(host)
        entries.append(
            OptOutEntry(
                host=host,
                recorded_on=recorded_on,
                evidence=evidence,
                note=str(row.get("note", "")).strip(),
            )
        )
    return tuple(entries)


def parse_register(text: str, *, source: str = "inline") -> OptOutRegister:
    """Parse register TOML text; fail closed on any malformed row."""
    try:
        table = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise OptOutRegisterError(f"{source}: invalid TOML — {exc}") from exc
    return OptOutRegister(entries=_parse_entries(table, source), source=source)


def register_path() -> Path | None:
    """The operator-supplied register path (``$SIG_OPT_OUT_REGISTER``), if set."""
    raw = os.environ.get(OPT_OUT_REGISTER_ENV, "").strip()
    return Path(raw) if raw else None


def load_register(path: Path | None = None) -> OptOutRegister:
    """Load the operative opt-out register.

    Precedence: an explicit ``path``, then ``$SIG_OPT_OUT_REGISTER``, then the
    committed packaged register. Loading happens per call site (a fetcher
    loads once at construction; the gate per verdict) so a swapped
    operator-supplied file takes effect on the next run — no rebuild
    (§26 rule 7's "immediately").
    """
    override = path or register_path()
    if override is not None:
        try:
            text = override.read_text(encoding="utf-8")
        except OSError as exc:
            raise OptOutRegisterError(
                f"opt-out register {override} unreadable: {exc} — the register is "
                "fail-closed; a missing override refuses, it does not silently pass"
            ) from exc
        return parse_register(text, source=str(override))
    resource = files("connectors").joinpath("data", _PACKAGED_REGISTER)
    return parse_register(resource.read_text(encoding="utf-8"), source=_PACKAGED_REGISTER)


def opt_out_reasons(hosts: list[str] | tuple[str, ...]) -> list[str]:
    """The refusal reasons covering any of ``hosts`` — the gate's view."""
    register = load_register()
    return [entry.reason for entry in register.listed_hosts(hosts)]


__all__ = [
    "OPT_OUT_REGISTER_ENV",
    "OptOutEntry",
    "OptOutRegister",
    "OptOutRegisterError",
    "load_register",
    "normalize_host",
    "opt_out_reasons",
    "parse_register",
    "register_path",
]
