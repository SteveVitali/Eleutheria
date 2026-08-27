# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""ORI9 validation, the UCR↔USPS state-code table, and the civil-ORI flag
(SIG-IDENT-002/003).

An ORI is the FBI Originating Agency Identifier. SIG treats it as an opaque
nine-character token validated **by pattern only** (``^[A-Z0-9]{9}$``) — never by
assuming positions 1–2 are a USPS state code. The UCR/NCIC state prefix an ORI
carries diverges from USPS for some jurisdictions (Nebraska ``NB``→``NE``, Guam
``GM``→``GU``…), so translating it requires the reference table here, and even then
the result is an enrichment hint, not identity evidence.

Two safety rules live here:

* **Pattern, not position (SIG-IDENT-002).** :func:`validate_ori` accepts any
  nine-char ``[A-Z0-9]`` string and rejects everything else; it never parses the
  prefix to decide validity.
* **The civil-ORI flag (SIG-IDENT-003).** An ORI whose *ninth* character is
  alphabetic is a probable civil/applicant-fingerprinting ORI and MUST NOT be
  auto-linked to a surveillance-operating organisation without a second
  corroborating source. :func:`is_civil_ori` detects it; the cascade refuses to
  auto-write on it.
"""

from __future__ import annotations

import re
import tomllib
from functools import cache
from importlib.resources import files
from typing import Any

__all__ = [
    "ORI_PATTERN",
    "OriValidationError",
    "validate_ori",
    "is_valid_ori",
    "is_civil_ori",
    "ucr_to_usps",
    "usps_to_ucr",
    "ucr_usps_divergences",
]

# The ONLY validity test for an ORI (SIG-IDENT-002): nine uppercase alphanumerics.
ORI_PATTERN = re.compile(r"^[A-Z0-9]{9}$")


class OriValidationError(ValueError):
    """An ORI failed the ``^[A-Z0-9]{9}$`` pattern (SIG-IDENT-002)."""


def is_valid_ori(value: str) -> bool:
    """Whether ``value`` is a syntactically valid ORI9 (pattern only)."""
    return bool(ORI_PATTERN.fullmatch(value))


def validate_ori(value: str) -> str:
    """Return ``value`` unchanged if it is a valid ORI9, else raise (SIG-IDENT-002).

    Validation is purely by pattern — the state prefix is **never** consulted, so
    an ORI with an unusual prefix is still valid and one with the right prefix but
    wrong shape is still invalid.
    """
    if not is_valid_ori(value):
        raise OriValidationError(
            f"ORI {value!r} MUST match ^[A-Z0-9]{{9}}$ (SIG-IDENT-002); "
            "ORIs are validated by pattern, never by a positional state assumption"
        )
    return value


def is_civil_ori(value: str) -> bool:
    """Whether an ORI's ninth character is alphabetic — a civil/applicant ORI flag.

    A trailing letter marks a probable civil/applicant-fingerprinting ORI
    (SIG-IDENT-003), which MUST NOT be auto-linked to a surveillance-operating
    organisation without a second corroborating source. Raises on a malformed ORI
    (a non-ORI has no meaningful ninth character).
    """
    validate_ori(value)
    return value[8].isalpha()


@cache
def _table() -> dict[str, Any]:
    resource = files("resolution").joinpath("data", "ucr_usps.toml")
    with resource.open("rb") as fh:
        return tomllib.load(fh)


def ucr_usps_divergences() -> dict[str, str]:
    """The UCR→USPS codes that differ (the rest are identity) — incl NB→NE, GM→GU."""
    return dict(_table()["divergences"])


def ucr_to_usps(ucr_code: str) -> str:
    """Translate a two-character UCR/NCIC state code to its USPS code (SIG-IDENT-002).

    A divergent code (``NB``, ``GM``) maps through the table; every other code is
    returned uppercased unchanged (UCR and USPS agree). This is a translation
    helper, not an ORI validator, and its output is never identity evidence.
    """
    code = ucr_code.upper()
    return ucr_usps_divergences().get(code, code)


def usps_to_ucr(usps_code: str) -> str:
    """Inverse of :func:`ucr_to_usps` (USPS → UCR), identity where they agree."""
    code = usps_code.upper()
    inverse = {v: k for k, v in ucr_usps_divergences().items()}
    return inverse.get(code, code)
