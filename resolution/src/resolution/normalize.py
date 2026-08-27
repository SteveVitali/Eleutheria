# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""``normalize_org_name()``: a pure, deterministic, **versioned** organisation-name
normaliser with a committed test-vector suite that runs in CI (SIG-IDENT-022).

Every ingest path calls this one function, so its behaviour is a contract, not an
implementation detail. Three properties make it safe to depend on:

* **Pure & deterministic** — same input, same output, no clock/locale/network.
* **Versioned data** — the ruleset (``data/normalize_rules.toml``) and the acronym
  table (``data/acronym_alias.toml``) are data, not code; the version is bumped
  when a rule changes and the committed vectors (``data/normalize_vectors.toml``)
  are updated in the same commit.
* **Acronyms by exact lookup only** — ``LAPD``/``NYPD``/``LASD``/``CHP`` resolve
  by an exact whole-string table lookup and are **never** fuzzy-matched, because
  fuzzy-matching initials is precisely how two unrelated agencies with similar
  initials get silently merged.

It also collapses "Sheriff's Office" and "Sheriff's Department" to one canonical
suffix so the same body written either way normalises identically.
"""

from __future__ import annotations

import re
import tomllib
import unicodedata
from functools import cache
from importlib.resources import files
from typing import Any

__all__ = [
    "normalize_org_name",
    "resolve_acronym",
    "ruleset_version",
    "NORMALIZE_RULESET_VERSION",
]


@cache
def _load(name: str) -> dict[str, Any]:
    """Read one of the package's versioned normalise data tables."""
    resource = files("resolution").joinpath("data", f"{name}.toml")
    with resource.open("rb") as fh:
        return tomllib.load(fh)


def ruleset_version() -> str:
    """The version of the active normalise ruleset (SIG-IDENT-022)."""
    return str(_load("normalize_rules")["version"])


# The ruleset version is part of the module's public surface: a resolver records
# it alongside every normalised-name match so a later reader knows which rules
# produced the value (see resolution.cascade match_evidence).
NORMALIZE_RULESET_VERSION = ruleset_version()

# Match runs of anything that is not an ASCII letter or digit (after folding), so
# punctuation and separators become word boundaries.
_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def _acronyms() -> dict[str, str]:
    return {k.upper(): v for k, v in _load("acronym_alias")["acronyms"].items()}


def resolve_acronym(name: str) -> str | None:
    """Return the canonical expansion if ``name`` is a known acronym, else ``None``.

    Lookup is an **exact, case-insensitive, whole-string** table hit — a prefix, a
    superstring, or a typo of an acronym is deliberately a miss (SIG-IDENT-022). No
    fuzzy matching is ever attempted here.
    """
    return _acronyms().get(name.strip().upper())


def _fold(text: str) -> str:
    """Lowercase + strip accents (NFKD, drop combining marks) + expand ``&``.

    Apostrophes (straight and typographic) are deleted rather than treated as a
    boundary, so the possessive ``Sheriff's`` folds to the single token
    ``sheriffs`` — which the suffix-collapse rule then canonicalises.
    """
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    without_apostrophes = stripped.replace("'", "").replace("\u2019", "")
    return without_apostrophes.casefold().replace("&", " and ")


def _tokenize(folded: str) -> list[str]:
    return [t for t in _NON_ALNUM.split(folded) if t]


def _expand_abbreviations(tokens: list[str]) -> list[str]:
    table: dict[str, str] = _load("normalize_rules").get("abbreviations", {})
    return [table.get(tok, tok) for tok in tokens]


def _collapse_suffix(tokens: list[str]) -> list[str]:
    """Collapse a trailing known suffix phrase to its one canonical form."""
    rules = _load("normalize_rules").get("suffix_collapse", [])
    for rule in rules:
        canonical = rule["canonical"].split()
        for variant in rule["variants"]:
            var_tokens = variant.split()
            if tokens[len(tokens) - len(var_tokens) :] == var_tokens:
                return tokens[: len(tokens) - len(var_tokens)] + canonical
    return tokens


def normalize_org_name(name: str) -> str:
    """Normalise an organisation name deterministically (SIG-IDENT-022).

    Pipeline (each step versioned by ``data/normalize_rules.toml``):

    1. **Exact acronym expansion** — if the whole trimmed string is a known acronym
       it is replaced by its canonical expansion (exact lookup only; never fuzzy).
    2. **Fold** — strip accents, casefold, expand ``&`` → ``and``.
    3. **Tokenise** on non-alphanumerics (punctuation becomes a boundary; the
       possessive in ``Sheriff's`` becomes ``sheriffs``).
    4. **Expand** unambiguous token abbreviations (``dept`` → ``department``).
    5. **Collapse** a trailing canonical suffix (``sheriff department`` →
       ``sheriff office``).

    Returns a single space-joined lowercase string; the empty string for input
    that is empty or all punctuation.
    """
    expanded = resolve_acronym(name)
    source = expanded if expanded is not None else name
    tokens = _tokenize(_fold(source))
    tokens = _expand_abbreviations(tokens)
    tokens = _collapse_suffix(tokens)
    return " ".join(tokens)
