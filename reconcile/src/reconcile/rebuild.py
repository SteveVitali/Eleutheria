# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Byte-identical L3 rebuild (§28.7, SIG-RECON-019/020/021).

A resolution (the L3 decision record) MUST be reproducible from ``(claims +
ruleset_version + resolver_version + as_of pair)``, verified by the stored
``input_digest`` (SIG-RECON-020). This module reruns :func:`reconcile.resolve.RESOLVE`
over the same inputs and asserts the rebuild is identical to the stored decision —
the reproducibility contract every citing surface depends on.

Two guarantees this enforces:

* **Reproducible.** :func:`verify_reproducible` reruns the resolver and checks the
  fresh ``input_digest`` **and** the full :meth:`~reconcile.resolve.Resolution.decision_key`
  (everything but wall-clock ``computed_at``) match the stored record.
* **Never edited in place** (SIG-RECON-021). The rebuild returns a *new*
  :class:`~reconcile.resolve.Resolution`; a mismatch (a changed claim, a bumped
  ruleset) is a :class:`NonReproducible`, signalling that a new resolution must
  supersede the old one — never an in-place edit.

The committed sample (``data/l3_rebuild_sample.json``) plus
:func:`load_sample` are what CI regenerates and asserts against (SIG-STORE-018).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from importlib.resources import files
from typing import Any

from .resolve import RESOLVE, RESOLVER_VERSION, Claim, Resolution
from .ruleset import Ruleset, load_ruleset


class NonReproducible(RuntimeError):
    """Raised when a rebuild does not reproduce the stored resolution (SIG-RECON-020)."""


def rebuild_resolution(
    stored: Resolution,
    claims: list[Claim],
    *,
    ruleset: Ruleset | None = None,
) -> Resolution:
    """Recompute a stored resolution from its inputs (SIG-RECON-020).

    Reruns the resolver over ``claims`` at the stored ``as_of`` pair. The
    ``blocking_contradiction`` (``U7``) manual input is replayed from the stored
    ``unresolved_code``. Refuses to compare across versions: if the current
    ``ruleset_version``/``resolver_version`` differ from the stored ones, the
    inputs are not the same and a mismatch would be a legitimate recompute, not a
    reproduction — that is a :class:`NonReproducible`.
    """
    rs = ruleset or load_ruleset()
    if stored.ruleset_version != rs.version:
        raise NonReproducible(
            f"ruleset_version differs: stored {stored.ruleset_version!r} vs current "
            f"{rs.version!r}; a version change requires a fresh (superseding) resolution"
        )
    if stored.resolver_version != RESOLVER_VERSION:
        raise NonReproducible(
            f"resolver_version differs: stored {stored.resolver_version!r} vs current "
            f"{RESOLVER_VERSION!r}; a version change requires a fresh (superseding) resolution"
        )
    return RESOLVE(
        stored.subject_id,
        stored.predicate_id,
        claims,
        as_of_world=stored.as_of_world,
        as_of_belief=stored.as_of_belief,
        ruleset=rs,
        blocking_contradiction=stored.unresolved_code == "U7",
    )


def verify_reproducible(
    stored: Resolution,
    claims: list[Claim],
    *,
    ruleset: Ruleset | None = None,
) -> Resolution:
    """Rebuild and assert byte-identity with the stored resolution (SIG-RECON-020).

    Returns the rebuilt resolution on success; raises :class:`NonReproducible`
    when the fresh ``input_digest`` or ``decision_key`` diverge from the stored
    record.
    """
    rebuilt = rebuild_resolution(stored, claims, ruleset=ruleset)
    if rebuilt.input_digest != stored.input_digest:
        raise NonReproducible(
            f"input_digest mismatch: stored {stored.input_digest} != rebuilt {rebuilt.input_digest}"
        )
    if rebuilt.decision_key() != stored.decision_key():
        raise NonReproducible(
            "decision_key mismatch: the rebuilt resolution differs from the stored one "
            "(the decision is not byte-identical)"
        )
    return rebuilt


# --- the committed CI sample (SIG-RECON-020 / SIG-STORE-018) ------------------

_SAMPLE = "l3_rebuild_sample.json"


def _claim_from_dict(d: dict[str, Any]) -> Claim:
    """Deserialize one claim from the sample fixture (scalar fields only)."""
    kwargs: dict[str, Any] = dict(d)
    kwargs["observed_at"] = date.fromisoformat(d["observed_at"])
    for key in ("valid_from", "valid_to"):
        if kwargs.get(key):
            kwargs[key] = date.fromisoformat(kwargs[key])
    if "derived_from_claim_ids" in kwargs:
        kwargs["derived_from_claim_ids"] = tuple(kwargs["derived_from_claim_ids"])
    return Claim(**kwargs)


@dataclass(frozen=True)
class RebuildSample:
    """A committed reproducibility sample: inputs + the expected decision (§28.7)."""

    subject_id: str
    predicate_id: str
    as_of_world: date
    as_of_belief: date
    ruleset_version: str
    resolver_version: str
    claims: list[Claim]
    expected_input_digest: str
    expected_decision_key: list[object]

    def resolve(self, *, ruleset: Ruleset | None = None) -> Resolution:
        """Recompute the resolution the sample describes, at a fixed ``computed_at``
        (so the whole record — not just the decision key — is byte-stable)."""
        return RESOLVE(
            self.subject_id,
            self.predicate_id,
            self.claims,
            as_of_world=self.as_of_world,
            as_of_belief=self.as_of_belief,
            ruleset=ruleset or load_ruleset(),
            computed_at=datetime(2026, 1, 1),
        )


def load_sample() -> RebuildSample:
    """Load the committed L3 rebuild sample (SIG-RECON-020)."""
    raw = json.loads(files("reconcile").joinpath("data", _SAMPLE).read_text("utf-8"))
    return RebuildSample(
        subject_id=raw["subject_id"],
        predicate_id=raw["predicate_id"],
        as_of_world=date.fromisoformat(raw["as_of_world"]),
        as_of_belief=date.fromisoformat(raw["as_of_belief"]),
        ruleset_version=raw["ruleset_version"],
        resolver_version=raw["resolver_version"],
        claims=[_claim_from_dict(c) for c in raw["claims"]],
        expected_input_digest=raw["expected_input_digest"],
        expected_decision_key=list(raw["expected_decision_key"]),
    )


__all__ = [
    "NonReproducible",
    "RebuildSample",
    "load_sample",
    "rebuild_resolution",
    "verify_reproducible",
]
