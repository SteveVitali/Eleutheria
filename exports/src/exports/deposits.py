# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The append-only deposit ledger, ``docs/build/DEPOSITS.md`` (P21.5, §38.2).

Every Zenodo deposit — dry-run, sandbox, or (later) production — is recorded here as a
**dated, append-only row** (P1–P3). The environment column is load-bearing: a *sandbox*
DOI (``10.5072/…``) is a throwaway test identifier and MUST NOT be cited as if it were
the production ``10.5281/…`` concept DOI (RISK-P21-08). The first production deposit is a
one-command operator action that appends its own row here.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .zenodo import Deposition

_HEADER = """<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# DEPOSITS — the SIG Zenodo deposit ledger (append-only, §38.2, SIG-EXPORT-002)

Each row is a dated deposit of a bulk-export release. **The `environment` column is
binding:** a `sandbox` DOI (`10.5072/…`) is a throwaway Zenodo *test* identifier minted
on `sandbox.zenodo.org`; it is **not** citable and is **not** the production concept DOI
(`10.5281/…`) — see RISK-P21-08. A `dry-run` row was produced offline by
`FakeZenodoTransport` (no network, no account) and pins the deposit *policy* only.

The first **production** deposit is a one-command operator action
(`sig-exports deposit` without `--sandbox`/`--dry-run`, with `SIG_ZENODO_SANDBOX_TOKEN`
swapped for a production token) that appends its row below.

| date | release_id | environment | concept_doi | version_doi | files |
|---|---|---|---|---|---|
"""


@dataclass(frozen=True)
class DepositRecord:
    """One row of the deposit ledger."""

    release_id: str
    environment: str  # "dry-run" | "sandbox" | "production"
    deposition: Deposition
    when: date

    def as_row(self) -> str:
        return (
            f"| {self.when.isoformat()} | {self.release_id} | {self.environment} "
            f"| {self.deposition.concept_doi} | {self.deposition.version_doi} "
            f"| {len(self.deposition.files)} |\n"
        )


def render_ledger(records: list[DepositRecord]) -> str:
    """Render the full append-only ledger document from its rows."""
    return _HEADER + "".join(r.as_row() for r in records)


def append_record(existing: str | None, record: DepositRecord) -> str:
    """Append ``record`` to the ledger text (creating the header if absent).

    Append-only: an existing ledger keeps every prior row verbatim; only the new row is
    added at the end (P1–P3, never rewrite history).
    """
    if not existing or not existing.strip():
        return _HEADER + record.as_row()
    body = existing if existing.endswith("\n") else existing + "\n"
    return body + record.as_row()


__all__ = ["DepositRecord", "render_ledger", "append_record"]
