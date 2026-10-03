# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Append-only source-identifier aliases (P34.18 / ADR-178, S0 RI-01).

A cohort of public source identifiers was minted from personal ArcGIS account
handles (and one surname, ``okc_council_statement``'s predecessor). The operator
re-keyed them (DR-C6-01 / B-3: "Re-key, map restricted"): the registry now uses
neutral identifiers, the plaintext old→new map is **restricted** (an insert-only
object in ``sig-restricted``, never in the repo or any public artifact), and
this data file carries only **keyed digests** — ``sha256`` of each retired
identifier — so public/export surfaces can resolve or neutralise an old token
without ever republishing the handle (SIG-PUB-002).

Alias semantics:

* **Append-only.** Old identifiers never disappear: claims keep their recorded
  ``source_id`` forever (SIG-STORE-011, P1–P3). Resolving to the neutral id is
  an export/read-time projection, never a spine rewrite.
* **Keyless.** Keys are ``sha256:<hex>`` digests of the retired token, so the
  committed table itself repeats no handle. A token that resolves to nothing
  passes through unchanged — the table is identity for every non-retired id.
* **Composed identifiers.** Subject ids, claim ids, evidence/permalink ids and
  tile properties embed source and target ids as tokens
  (``traffic_camera:<source>:<target>:<ref>`` and friends). ``resolve_text``
  rewrites every retired token it finds, wherever it appears, so nothing
  publicly renderable repeats a handle (TS-04).
* **Suppressed values.** ``camera_operator`` claim values that are themselves
  account handles digest onto ``suppressed_value_digests``; the export/read
  seams mark them ``publication_permitted = False`` (the full predicate fix is
  P35.26's).
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from functools import cache
from pathlib import Path

ALIAS_SCHEMA = "sig/source-alias-records/1.0.0"
RESTRICTED_MAP_SCHEMA = "sig/restricted-source-map/1.0.0"

#: The local (gitignored) restricted-map file emitted by the re-key. On the
#: hosted side the same document is the insert-only ``sig-restricted`` object
#: L2 writes (ADR-178; HG-09 secret-handling posture).
RESTRICTED_MAP_PATH = (
    Path(__file__).resolve().parents[3] / "docs/build/logs/p34.18/restricted_source_map.json"
)

#: Identifier characters: source/target/claim/subject ids are slug tokens;
#: ``@`` is included so an e-mail-shaped owner token resolves as ONE run (it
#: would otherwise split at the ``@`` and never match its redaction digest).
_TOKEN_RUN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._@-]*")


def _digests(value: str) -> tuple[str, str]:
    """The token digest, original and lowercased: suppressed/redaction entries
    are keyed by the lowercased form (owner tokens preserve case)."""
    return digest_token(value), digest_token(value.lower())


def digest_token(value: str) -> str:
    """Return the keyed digest ``sha256:<hex>`` of a retired identifier."""
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SourceAliases:
    """The resolved alias tables. All maps are digest-keyed."""

    #: sha256 of a retired source id → the neutral source id.
    source: Mapping[str, str]
    #: sha256 of a retired target id → the neutral target id.
    target: Mapping[str, str]
    #: sha256 of any retired token (source, target, or a compound fixture id
    #: such as a compound slug carrying the surname id) → its neutral replacement.
    token: Mapping[str, str]
    #: sha256 of a retired multi-word phrase (space-joined runs, e.g. a
    #: personal name inside a recorded attribution) → its neutral replacement.
    phrase: Mapping[str, str]
    #: sha256 of a scrubbed owner/account token → a neutral redaction label
    #: (``[account withheld]``). Owner tokens in recorded text are redacted,
    #: not re-keyed.
    redaction: Mapping[str, str]
    #: sha256s of ``camera_operator`` values that are account handles;
    #: claims whose value digests onto this set are not publishable.
    suppressed_value_digests: frozenset[str]
    #: sha256 of the restricted plaintext map file (audit anchor only —
    #: the map itself never ships in the repo or any export).
    restricted_map_digest: str | None

    @property
    def empty(self) -> bool:
        return not (self.source or self.target or self.token or self.phrase or self.redaction)

    def restricted_old_ids(self, map_path: str | Path | None = None) -> list[str]:
        """The plaintext retired identifiers — read from the **restricted**
        old→new map (the gitignored local file or the ``sig-restricted``
        object; DR-C6-01 / B-3). Returns ``[]`` when the map is absent —
        callers (e.g. the renamed-routes conf generator) are operator-side and
        must never log or print the returned values."""
        path = Path(map_path) if map_path else RESTRICTED_MAP_PATH
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except OSError:
            return []
        if not isinstance(raw, dict) or raw.get("schema") != RESTRICTED_MAP_SCHEMA:
            return []
        ids: list[str] = []
        for section in ("sources", "targets", "compound_tokens", "phrases"):
            table = raw.get(section) or {}
            ids.extend(str(k) for k in table if isinstance(k, str))
        return ids

    def is_suppressed_value(self, value: str) -> bool:
        """True when ``value`` digests onto a suppressed operator value."""
        return any(d in self.suppressed_value_digests for d in _digests(value))

    def resolve_token(self, token: str) -> str:
        """Resolve one identifier token; identity when unmapped."""
        d, dl = _digests(token)
        return self.token.get(d, self.token.get(dl, self.redaction.get(dl, token)))

    def _sub(self, m: re.Match[str]) -> str:
        run = m.group(0)
        d, dl = _digests(run)
        hit = self.token.get(d, self.token.get(dl))
        if hit is not None:
            return hit
        red = self.redaction.get(d, self.redaction.get(dl))
        if red is not None:
            return red
        if "-" in run:
            parts = run.split("-")
            resolved = [
                self.token.get(
                    digest_token(p),
                    self.token.get(
                        digest_token(p.lower()),
                        self.redaction.get(digest_token(p.lower()), p),
                    ),
                )
                for p in parts
            ]
            if resolved != parts:
                return "-".join(resolved)
        return run

    def resolve_text(self, text: str) -> str:
        """Rewrite every retired token or phrase inside ``text``.

        Consecutive identifier runs separated by single spaces are tried as
        n-grams (longest first, up to 3) against the phrase map, so a recorded
        ``the OKCPD chief`` attribution resolves as a unit before the bare
        ``the chief`` token is redacted. Single runs consult the token map, then the
        owner-token redaction map, then a ``-``-segment pass so a handle
        embedded mid-compound is still neutralised.
        """
        if self.empty:
            return text
        matches = list(_TOKEN_RUN.finditer(text))
        if not matches:
            return text
        out: list[str] = []
        prev_end = 0
        i = 0
        n = len(matches)
        while i < n:
            m = matches[i]
            best: tuple[int, str] | None = None
            # Longest space-joined n-gram first (≤3 runs).
            for width in (3, 2):
                if i + width > n:
                    continue
                gap_ok = all(
                    text[matches[i + j].end() : matches[i + j + 1].start()] == " "
                    for j in range(width - 1)
                )
                if not gap_ok:
                    continue
                joined = " ".join(matches[i + j].group(0) for j in range(width))
                hit = self.phrase.get(digest_token(joined))
                if hit is not None:
                    best = (width, hit)
                    break
            if best is not None:
                width, hit = best
                out.append(text[prev_end : matches[i].start()])
                out.append(hit)
                prev_end = matches[i + width - 1].end()
                i += width
                continue
            out.append(text[prev_end : m.start()])
            out.append(self._sub(m))
            prev_end = m.end()
            i += 1
        out.append(text[prev_end:])
        return "".join(out)


_EMPTY = SourceAliases(
    source={},
    target={},
    token={},
    phrase={},
    redaction={},
    suppressed_value_digests=frozenset(),
    restricted_map_digest=None,
)


def _validate(raw: object, where: str) -> SourceAliases:
    if not isinstance(raw, dict) or raw.get("schema") != ALIAS_SCHEMA:
        raise ValueError(f"{where}: not a {ALIAS_SCHEMA} document")
    out = {
        section: {
            str(k): str(v)
            for k, v in (raw.get(section) or {}).items()
            if isinstance(k, str) and isinstance(v, str)
        }
        for section in (
            "source_aliases",
            "target_aliases",
            "token_aliases",
            "phrase_aliases",
            "redaction_aliases",
        )
    }
    for section, table in out.items():
        for k, v in table.items():
            if not re.fullmatch(r"sha256:[0-9a-f]{64}", k):
                raise ValueError(f"{where}: {section} key is not a sha256 digest")
            if section == "redaction_aliases":
                continue
            # Phrase replacements are prose ("the OKCPD chief's"); the rest are
            # identifier-shaped.
            pattern = (
                r"[A-Za-z0-9][A-Za-z0-9_.' -]*"
                if section == "phrase_aliases"
                else r"[a-z0-9][a-z0-9_. -]*"
            )
            if not re.fullmatch(pattern, v):
                raise ValueError(f"{where}: {section} value {v!r} is not an identifier")
    suppressed = frozenset(
        d
        for d in raw.get("suppressed_value_digests") or []
        if isinstance(d, str) and re.fullmatch(r"sha256:[0-9a-f]{64}", d)
    )
    token = dict(out["source_aliases"])
    token.update(out["target_aliases"])
    token.update(out["token_aliases"])
    return SourceAliases(
        source=out["source_aliases"],
        target=out["target_aliases"],
        token=token,
        phrase=out["phrase_aliases"],
        redaction=out["redaction_aliases"],
        suppressed_value_digests=suppressed,
        restricted_map_digest=raw.get("restricted_map_digest") or None,
    )


@cache
def load_source_aliases(path: str | None = None) -> SourceAliases:
    """Load the committed alias table (cached). An absent table resolves to
    the empty (identity) table so pre-P34.18 checkouts keep working."""
    if path is not None:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        return _validate(raw, path)
    try:
        from ._data import load_json_table

        return _validate(load_json_table("source_aliases"), "policy/data/source_aliases.json")
    except FileNotFoundError:
        return _EMPTY


def resolve_source_id(source_id: str, aliases: SourceAliases | None = None) -> str:
    """Resolve a recorded ``source_id`` to its public identifier."""
    a = aliases if aliases is not None else load_source_aliases()
    return a.resolve_token(source_id)


def resolve_public_text(text: object, aliases: SourceAliases | None = None) -> object:
    """Walk a JSON-shaped value and rewrite retired identifier tokens in every
    string — the export/read hygiene layer (TS-04). Non-strings pass through.
    """
    a = aliases if aliases is not None else load_source_aliases()
    if a.empty:
        return text
    if isinstance(text, str):
        return a.resolve_text(text)
    if isinstance(text, Mapping):
        return {k: resolve_public_text(v, a) for k, v in text.items()}
    if isinstance(text, (list, tuple)):
        return [resolve_public_text(v, a) for v in text]
    return text
