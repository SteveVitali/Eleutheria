# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P34.18 — personal-handle source-id re-key (S0 RI-01, DR-C6-01 / B-3, ADR-178).

A committed, idempotent script that renames the handle-bearing registry
identifiers to neutral ids and scrubs the e-mail-shaped owner strings / handle
tokens out of the registry's non-id text (A-0.1 / OD-17). It:

* reads the handle list from its **gitignored** path
  (``docs/build/logs/next-phase/C3/personal_like_ids.txt``) — the list itself is
  never committed and is never printed;
* derives a deterministic neutral id per retired id
  (``camreg_us_ny_<n>`` where the layer's jurisdiction is recorded, otherwise
  ``camreg_und_<n>``; the surname id → ``okc_council_statement``);
* rewrites the functional files that carry the old tokens (registry TOMLs,
  live targets, the runner map, cadence batches, the P26.16 batch tool, the
  express-terms disclosure table, the camera-site gold set, the seeded OKC
  surname-id sites and their tests);
* ``git mv``s the per-source rights-annex files and updates ``review_packet``
  paths;
* sweeps **every tracked file** for the retired tokens (findings CSVs, run
  ledgers, reports, live_runs/ contents) and ``git mv``s every tracked path
  that carries one (``live_runs/p2616/camreg_*/``) — the acceptance criterion
  is *zero handle-list entries in the repo tip's tracked files*; git history
  retains the old strings and OD-20's correction note discloses that
  (append-only: the recorded claims in the spine are never touched);
* emits the committed **keyed-digest** alias table
  (``policy/data/source_aliases.json`` — sha256 keys, never plaintext handles),
  the **restricted** plaintext old→new map (gitignored, mode 0600 — the
  ``sig-restricted`` object L2 inserts), and a counts-only dry-run report;
* verifies afterwards: zero handle-list entries in tracked files, zero
  e-mail-shaped owner strings in the two registry files.

The report counts — it never prints a handle (contract deliverable 2).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
import subprocess
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]

HANDLE_LIST = REPO_ROOT / "docs/build/logs/next-phase/C3/personal_like_ids.txt"
SUPPRESSED_VALUES = REPO_ROOT / "docs/build/logs/p34.18/suppressed_values.txt"
RESTRICTED_MAP_OUT = REPO_ROOT / "docs/build/logs/p34.18/restricted_source_map.json"
REPORT_OUT = REPO_ROOT / "docs/build/logs/p34.18/rekey_report.json"
ALIAS_TABLE_OUT = REPO_ROOT / "policy/src/policy/data/source_aliases.json"

SOURCES_TOML = REPO_ROOT / "connectors/src/connectors/data/sources.toml"
TARGETS_TOML = REPO_ROOT / "connectors/src/connectors/data/camera_registry_targets.toml"
ANNEX_ROOT = REPO_ROOT / "docs/build/reports/rights/annex"
CURRENT_PROJECTION = REPO_ROOT / "docs/build/reports/current"

RESTRICTED_MAP_SCHEMA = "sig/restricted-source-map/1.0.0"

#: Functional files that carry retired tokens in *structured* positions (row
#: ids, owner parens, agency values) needing context-aware passes. Every other
#: tracked file — records, findings, run ledgers — is handled by the tree
#: sweep below: the tip carries no handle-list entries (contract acceptance);
#: git history retains them and OD-20's correction note discloses that.
TOKEN_FILES = [
    "connectors/src/connectors/data/sources.toml",
    "connectors/src/connectors/data/camera_registry_targets.toml",
    "connectors/src/connectors/data/live_targets.toml",
    "connectors/src/connectors/runner.py",
    "ops/cadence.toml",
    "docs/build/tools/p2616_batch.py",
    "policy/src/policy/data/express_terms.json",
    "resolution/src/resolution/data/camera_site_gold.json",
    "tests/unit/test_express_terms_disclosure.py",
]

#: Files that carry the surname id and the hand-seeded OKC fixture
#: compounds/prose that derive from it.
SURNAME_FILES = [
    "ops/src/ops/seed.py",
    "ops/src/ops/seed_correction.py",
    "ops/src/ops/dossier_packet.py",
    "exports/src/exports/web_dossier.py",
    "tests/acceptance/okc_slice.py",
    "tests/acceptance/fixtures/okc_sources.json",
    "tests/db/test_okc_seed_correction.py",
    "tests/e2e/test_composed_stack.py",
    "tests/api/test_store_pg.py",
    "tests/reconcile/test_materialize_contradictions.py",
    "tests/reconcile/test_counts.py",
    "tests/ops/test_okc_dossier_packet.py",
]


#: Prose replacements for the seeded OKC narrative — the surname is replaced by
#: the institutional office. Built from the handle list at runtime so this
#: committed file carries no handle literal (the sweep scans tracked files).
def _surname(handles: list[str]) -> str | None:
    return next((h for h in handles if not h.startswith("camreg_")), None)


def _surname_prose(surname: str) -> list[tuple[str, str]]:
    cap = surname.capitalize()
    return [
        (f"OKCPD Chief {cap}", "the OKCPD chief"),
        (f"Chief {cap}'s", "the OKCPD chief's"),
        (f"Chief {cap}", "the OKCPD chief"),
        (f"{cap}'s", "the OKCPD chief's"),
        (cap, "the chief"),
    ]


#: E-mail-derived account token (a bare ``X@Y`` host suffix counts — ArcGIS
#: owner names are e-mail-derived and often drop the TLD). Used only in
#: owner-position contexts; a ``contact`` field or a verbatim licence quote is
#: not an owner string.
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)*")
#: The owner token inside ``(owner X)`` — stops at ``,``/``)`` so a trailing
#: clause (``, N rows observed …``) is preserved.
_OWNER_TOKEN = re.compile(r"(?<=\(owner )[^,)]+")
_TOKEN_RUN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


@dataclass
class Plan:
    source_map: dict[str, str] = field(default_factory=dict)
    target_map: dict[str, str] = field(default_factory=dict)
    token_map: dict[str, str] = field(default_factory=dict)  # compound tokens (surname slugs)
    phrase_map: dict[str, str] = field(default_factory=dict)  # surname prose replacements
    surname: str | None = None
    suppressed_values: set[str] = field(default_factory=set)
    owner_paren_scrubs: int = 0
    email_scrubs: int = 0


def load_handles(path: Path = HANDLE_LIST) -> list[str]:
    """Read the gitignored handle list (one retired identifier per line)."""
    if not path.exists():
        raise FileNotFoundError(
            f"handle list not found at {path} — it is gitignored; restore it "
            "from the planning worktree before re-keying (contract Load list)"
        )
    return sorted({ln.strip() for ln in path.read_text().splitlines() if ln.strip()})


def _neutral_source_ids(handles: list[str]) -> dict[str, str]:
    """Deterministic neutral ids: ``camreg_us_ny_<n>`` for the NY-resolved
    layers, ``camreg_und_<n>`` otherwise; the surname id gets a fixed name."""
    out: dict[str, str] = {}
    ny = sorted(h for h in handles if re.fullmatch(r"camreg_nyc_\w+_ny", h))
    und = sorted(h for h in handles if h.startswith("camreg_") and h not in ny)
    for i, old in enumerate(ny, 1):
        out[old] = f"camreg_us_ny_{i:03d}"
    for i, old in enumerate(und, 1):
        out[old] = f"camreg_und_{i:03d}"
    for h in handles:
        if not h.startswith("camreg_"):
            out[h] = "okc_council_statement"  # the surname id (J4 NEW-6)
    return out


def _handle_variants(old_source_id: str) -> list[str]:
    """Handle substrings a target id may lead with (longest first)."""
    h = old_source_id.removeprefix("camreg_")
    variants = [h]
    m = re.fullmatch(r"nyc_(\w+)_ny", h)
    if m:
        variants += [f"nyc_{m.group(1)}", m.group(1)]
    return sorted(set(variants), key=len, reverse=True)


def _neutral_target_id(old_target: str, old_source: str, new_source: str) -> str:
    """``<new_source>_<descriptor>`` — the leading handle run is dropped."""
    rest = old_target
    for v in _handle_variants(old_source):
        if rest == v:
            rest = ""
            break
        if rest.startswith(v + "_"):
            rest = rest[len(v) + 1 :]
            break
    if not rest or any(v in rest for v in _handle_variants(old_source) if len(v) > 3):
        rest = "cameras"
    return f"{new_source}_{rest}"


def build_plan(handles: list[str]) -> Plan:
    plan = Plan()
    plan.source_map = _neutral_source_ids(handles)
    plan.surname = _surname(handles)
    if plan.surname:
        plan.phrase_map = dict(_surname_prose(plan.surname))

    tgt = tomllib.loads(TARGETS_TOML.read_text())
    for row in tgt["targets"]:
        sid, tid = row.get("source_id"), row.get("id")
        if sid in plan.source_map and isinstance(tid, str):
            plan.target_map[tid] = _neutral_target_id(tid, sid, plan.source_map[sid])

    # Compound fixture tokens containing the surname id (okc-<surname>-…,
    # <surname>-…). The surname itself never appears as a literal in this file.
    if plan.surname:
        sn = plan.surname
        for rel in SURNAME_FILES:
            text = (REPO_ROOT / rel).read_text(encoding="utf-8")
            for tok in set(_TOKEN_RUN.findall(text)):
                if sn not in tok or ("-" not in tok and tok != sn):
                    continue  # slug compounds + the bare id — attr access/prose excluded
                if tok == sn:
                    new = "okc_council_statement"
                elif tok.startswith(sn):
                    new = "okc-council" + tok[len(sn) :]
                else:
                    new = tok.replace(sn, "council")
                if new != tok:
                    plan.token_map[tok] = new

    # Owner strings + handle tokens to scrub from non-id text also seed the
    # suppressed camera_operator digests (the one account-handle operator value
    # digests onto this same class — L2 NEW-4).
    scrubbed = _collect_scrubbed_tokens(plan)
    plan.suppressed_values = {t.lower() for t in scrubbed}
    if SUPPRESSED_VALUES.exists():
        plan.suppressed_values |= {
            ln.strip() for ln in SUPPRESSED_VALUES.read_text().splitlines() if ln.strip()
        }
    return plan


def _owner_token_hit(token: str, handles: list[str], *, renamed_row: bool) -> bool:
    """Should this ``(owner X)`` token be scrubbed? E-mail-shaped always;
    handle-bearing always; any owner token inside a renamed row."""
    t = token.strip()
    if _EMAIL.search(t):
        return True
    low = t.lower()
    if any(h.removeprefix("camreg_") in low for h in handles if h.startswith("camreg_")):
        return True
    return renamed_row


def _scrub_owner_parens(text: str, handles: list[str], *, renamed_row: bool) -> tuple[str, int]:
    count = 0

    def sub(m: re.Match[str]) -> str:
        nonlocal count
        if _owner_token_hit(m.group(0), handles, renamed_row=renamed_row):
            count += 1
            return "[account withheld]"
        return m.group(0)

    return _OWNER_TOKEN.sub(sub, text), count


def _scrub_name_parens(value: str, old_source: str) -> str:
    """Drop handle-bearing tokens inside a renamed row's ``name`` parentheses."""
    handles = _handle_variants(old_source) + [old_source.removeprefix("camreg_")]

    def fix_paren(m: re.Match[str]) -> str:
        inner = m.group(1)
        kept = []
        for tok in inner.split():
            bare = tok.strip(",").lower()
            if len(bare) < 2:
                kept.append(tok)
                continue
            if any(bare in h.lower() or h.lower() in bare for h in handles):
                continue
            if "@" in bare:
                continue
            kept.append(tok)
        joined = " ".join(kept).strip()
        return f"({joined})" if joined else ""

    out = re.sub(r"\(([^)]*)\)", fix_paren, value)
    return re.sub(r" {2,}", " ", out)


def _collect_scrubbed_tokens(plan: Plan) -> set[str]:
    """Every personal/e-mail-shaped token the rekey removes — fed to the
    suppressed-value digest set. Institutional owner names that stay in the
    text are *not* collected."""
    handles = [h for h in plan.source_map if h.startswith("camreg_")]
    out: set[str] = set()
    text = SOURCES_TOML.read_text() + TARGETS_TOML.read_text()
    for m in _OWNER_TOKEN.finditer(text):
        tok = m.group(0).strip()
        if tok != "[account withheld]" and _owner_token_hit(tok, handles, renamed_row=False):
            out.add(tok)
    for m in re.finditer(r'agency = "([^"]*)"', TARGETS_TOML.read_text()):
        if _EMAIL.search(m.group(1)):
            out.add(m.group(1))
    # Tokens the name-paren scrub removes inside renamed rows.
    src = tomllib.loads(SOURCES_TOML.read_text())
    for old in plan.source_map:
        row = src.get("sources", {}).get(old)
        if not row:
            continue
        for m in re.finditer(r"\(([^)]*)\)", str(row.get("name", ""))):
            for tok in m.group(1).split():
                bare = tok.strip(",").lower()
                if len(bare) >= 2 and any(bare in h or h in bare for h in _handle_variants(old)):
                    out.add(tok.strip(","))
    return out


def _rewrite_text(text: str, plan: Plan, handles: list[str], path: Path) -> tuple[str, int]:
    """Apply the token map + non-id scrubs to one file. Returns (new, count)."""
    n = 0
    # 1. Token replacements, longest key first (compounds before stems).
    mapping = {**plan.token_map, **plan.source_map, **plan.target_map}
    for old in sorted(mapping, key=len, reverse=True):
        new = mapping[old]
        if old in text:
            text, k = text.replace(old, new), text.count(old)
            n += k
    # 2. Surname prose (only in the surname file set).
    if any(str(path).endswith(rel) for rel in SURNAME_FILES):
        for old, new in sorted(plan.phrase_map.items(), key=lambda kv: -len(kv[0])):
            if old in text:
                n += text.count(old)
                text = text.replace(old, new)
    # 3. (owner X) scrubs — whole file; renamed-row handling is inside.
    text, k = _scrub_owner_parens(text, handles, renamed_row=False)
    n += k
    # 4. E-mail-shaped agency values in the targets file.
    if path.name == "camera_registry_targets.toml":

        def agency_sub(m: re.Match[str]) -> str:
            nonlocal n
            if _EMAIL.search(m.group(1)):
                n += 1
                return 'agency = "(account withheld)"'
            return m.group(0)

        text = re.sub(r'agency = "([^"]*)"', agency_sub, text)
    return text, n


def _scrub_sources_toml(plan: Plan, handles: list[str]) -> tuple[str, int]:
    """sources.toml needs per-row context: renamed rows get name-paren and
    owner scrubs; every row gets the e-mail-shaped owner scrub."""
    text = SOURCES_TOML.read_text()
    n = 0
    current: str | None = None
    renamed = set(plan.source_map)
    new2old = {v: k for k, v in plan.source_map.items()}
    out_lines: list[str] = []
    for line in text.splitlines(keepends=True):
        m = re.match(r"\[sources\.([A-Za-z0-9_.-]+)", line)
        if m:
            current = m.group(1)
        old_source = current if current in renamed else new2old.get(current or "")
        if old_source is not None:
            if line.lstrip().startswith("name ="):
                new = _scrub_name_parens(line, old_source)
                if new != line:
                    n += 1
                    line = new
            line, k = _scrub_owner_parens(line, handles, renamed_row=True)
            n += k
        else:
            line, k = _scrub_owner_parens(line, handles, renamed_row=False)
            n += k
        out_lines.append(line)
    text = "".join(out_lines)
    for old in sorted(plan.source_map, key=len, reverse=True):
        if old in text:
            n += text.count(old)
            text = text.replace(old, plan.source_map[old])
    return text, n


def _git_mv(old: Path, new: Path) -> None:
    new.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "mv", str(old.relative_to(REPO_ROOT)), str(new.relative_to(REPO_ROOT))],
        cwd=REPO_ROOT,
        check=True,
    )


#: Tree-sweep exclusions: gitignored inputs/outputs (untracked anyway, listed
#: for clarity) and the emitted artifacts whose digests must not be rewritten.
TREE_EXCLUDE = {
    HANDLE_LIST,
    SUPPRESSED_VALUES,
    RESTRICTED_MAP_OUT,
    REPORT_OUT,
    ALIAS_TABLE_OUT,
}


#: A bare surname id-token (word-bounded; compounds are mapped first). Built
#: per-plan from the handle list — no handle literal lives in this file.
def _bare_surname_re(plan: Plan) -> re.Pattern[str] | None:
    if not plan.surname:
        return None
    return re.compile(rf"(?<![A-Za-z0-9_.-]){re.escape(plan.surname)}(?![A-Za-z0-9_.-])")


def _tracked_files() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    )
    return [REPO_ROOT / p for p in out.stdout.splitlines() if p.strip()]


def _rewrite_tree_text(text: str, plan: Plan, handles: list[str]) -> tuple[str, int]:
    """The whole-tree pass: every token mapping, the surname prose, and bare
    handle/id occurrences — applied to records and functional files alike."""
    n = 0
    mapping = {**plan.token_map, **plan.source_map, **plan.target_map}
    for old in sorted(mapping, key=len, reverse=True):
        if old in text:
            n += text.count(old)
            text = text.replace(old, mapping[old])
    for old, new in sorted(plan.phrase_map.items(), key=lambda kv: -len(kv[0])):
        if old in text:
            n += text.count(old)
            text = text.replace(old, new)
    bare = _bare_surname_re(plan)
    if bare is not None:
        text, k = bare.subn("okc_council_statement", text)
        n += k
    text, k = _scrub_owner_parens(text, handles, renamed_row=False)
    n += k
    return text, n


def _sweep_tracked_tree(
    plan: Plan, handles: list[str], *, dry_run: bool, counts: dict[str, int]
) -> None:
    """Rewrite every remaining tracked file carrying a retired token and
    ``git mv`` every tracked path that carries one. Idempotent: a second run
    finds nothing."""
    already = {REPO_ROOT / rel for rel in TOKEN_FILES + SURNAME_FILES}
    mapping = {**plan.token_map, **plan.source_map, **plan.target_map}
    old_ids = sorted(mapping, key=len, reverse=True)

    # 1. Path renames first (live_runs/p2616/camreg_*/ and any other carrier).
    for rel in [p for p in _tracked_files() if p not in TREE_EXCLUDE]:
        rel_s = str(rel.relative_to(REPO_ROOT))
        new_rel = rel_s
        for old in old_ids:
            new_rel = new_rel.replace(old, mapping[old])
        bare = _bare_surname_re(plan)
        if bare is not None:
            new_rel = bare.sub("okc_council_statement", new_rel)
        if new_rel != rel_s:
            counts["paths_moved"] += 1
            if not dry_run:
                _git_mv(rel, REPO_ROOT / new_rel)

    # 2. Content sweep over every tracked text file.
    for path in _tracked_files():
        if path in TREE_EXCLUDE or path in already:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue  # binary or vanished (already moved)
        new_text, k = _rewrite_tree_text(text, plan, handles)
        if new_text != text:
            counts["files_rewritten"] += 1
            counts["occurrences_replaced"] += k
            if not dry_run:
                path.write_text(new_text)


def apply_plan(plan: Plan, handles: list[str], *, dry_run: bool) -> dict[str, int]:
    counts = {
        "sources_renamed": len(plan.source_map),
        "targets_renamed": len(plan.target_map),
        "compound_tokens": len(plan.token_map),
        "files_rewritten": 0,
        "occurrences_replaced": 0,
        "annex_files_moved": 0,
        "paths_moved": 0,
        "suppressed_value_digests": len(plan.suppressed_values),
    }
    # Registry sources file: row-aware pass.
    new_text, k = _scrub_sources_toml(plan, handles)
    if new_text != SOURCES_TOML.read_text():
        counts["files_rewritten"] += 1
        counts["occurrences_replaced"] += k
        if not dry_run:
            SOURCES_TOML.write_text(new_text)

    for rel in TOKEN_FILES[1:] + SURNAME_FILES:
        path = REPO_ROOT / rel
        text = path.read_text(encoding="utf-8")
        new_text, k = _rewrite_text(text, plan, handles, path)
        if new_text != text:
            counts["files_rewritten"] += 1
            counts["occurrences_replaced"] += k
            if not dry_run:
                path.write_text(new_text)

    # Annex review packets: git mv + content rewrite (ids + owner tokens).
    for md in sorted(ANNEX_ROOT.rglob("camreg_*.md")):
        stem = md.stem
        if stem in plan.source_map:
            new_path = md.with_name(f"{plan.source_map[stem]}.md")
            text = md.read_text(encoding="utf-8")
            new_text, k = _rewrite_text(text, plan, handles, md)
            counts["annex_files_moved"] += 1
            counts["occurrences_replaced"] += k
            if not dry_run:
                if not md.exists():
                    continue
                _git_mv(md, new_path)
                new_path.write_text(new_text)

    # Whole-tree sweep: acceptance requires zero handle-list entries in the
    # repo tip's tracked files — records are re-keyed in place (git history
    # retains the originals; OD-20 discloses), paths are git-mv'd.
    _sweep_tracked_tree(plan, handles, dry_run=dry_run, counts=counts)
    return counts


def verify(plan: Plan, handles: list[str]) -> dict[str, int]:
    """Post-apply assertion: no retired token in functional files; no
    e-mail-shaped owner string in the registry files."""
    leftovers: dict[str, int] = {}
    targets = [REPO_ROOT / rel for rel in TOKEN_FILES + SURNAME_FILES]
    targets += list(ANNEX_ROOT.rglob("*.md"))
    retired = set(plan.source_map) | set(plan.target_map) | set(plan.token_map) | set(handles)
    if plan.surname:
        retired |= {plan.surname, plan.surname.capitalize()}
    for path in targets:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for tok in retired:
            if tok and tok in text:
                leftovers[str(path.relative_to(REPO_ROOT))] = leftovers.get(
                    str(path.relative_to(REPO_ROOT)), 0
                ) + text.count(tok)
    for reg in (SOURCES_TOML, TARGETS_TOML):
        for m in _OWNER_TOKEN.finditer(reg.read_text()):
            if _EMAIL.search(m.group(0)):
                leftovers[str(reg.relative_to(REPO_ROOT))] = (
                    leftovers.get(str(reg.relative_to(REPO_ROOT)), 0) + 1
                )
    for path in ANNEX_ROOT.rglob("camreg_*.md"):
        if path.stem in plan.source_map:
            leftovers[str(path.relative_to(REPO_ROOT))] = (
                leftovers.get(str(path.relative_to(REPO_ROOT)), 0) + 1
            )
    # The acceptance sweep: no handle-list entry in ANY tracked file, path or
    # content (git history is the disclosed retention, not the tip).
    for path in _tracked_files():
        rel = str(path.relative_to(REPO_ROOT))
        k = sum(rel.count(h) for h in handles)
        if k:
            leftovers[rel + " (path)"] = leftovers.get(rel + " (path)", 0) + k
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        k = sum(text.count(h) for h in handles)
        if k:
            leftovers[rel] = leftovers.get(rel, 0) + k
    return leftovers


def _load_prior_map(path: Path) -> dict | None:
    if not path.exists():
        return None
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("schema") != RESTRICTED_MAP_SCHEMA:
        raise ValueError(f"{path}: not a {RESTRICTED_MAP_SCHEMA} document")
    return raw


def _merge_prior(plan: Plan, map_path: Path) -> None:
    """Union the previously emitted restricted map into the plan.

    Idempotency: on a re-run the tree no longer carries the old tokens, so the
    rediscovered plan is empty — the prior map restores the full old→new
    relation and also lets a *late* file containing an old id still be
    rewritten (append-only semantics)."""
    prior = _load_prior_map(map_path)
    if not prior:
        return
    merged_sources = dict(prior.get("sources") or {})
    merged_sources.update(plan.source_map)
    plan.source_map = merged_sources
    merged_targets = dict(prior.get("targets") or {})
    merged_targets.update(plan.target_map)
    plan.target_map = merged_targets
    merged_tokens = dict(prior.get("compound_tokens") or {})
    merged_tokens.update(plan.token_map)
    plan.token_map = merged_tokens
    merged_phrases = dict(prior.get("phrases") or {})
    merged_phrases.update(plan.phrase_map)
    plan.phrase_map = merged_phrases
    plan.suppressed_values |= set(prior.get("suppressed_values") or [])


def emit(plan: Plan, *, dry_run: bool, map_out: Path) -> dict[str, Any]:
    """Write the keyed-digest alias table (committed) and the restricted
    plaintext map (gitignored, 0600)."""
    from policy.source_aliases import ALIAS_SCHEMA, digest_token

    restricted = {
        "schema": RESTRICTED_MAP_SCHEMA,
        "ticket": "P34.18",
        "adr": "ADR-178",
        "decision": "DR-C6-01 / B-3 — restricted old→new map; never public",
        "sources": dict(sorted(plan.source_map.items())),
        "targets": dict(sorted(plan.target_map.items())),
        "compound_tokens": dict(sorted(plan.token_map.items())),
        "phrases": dict(sorted(plan.phrase_map.items())),
        "suppressed_values": sorted(plan.suppressed_values),
    }
    restricted_bytes = json.dumps(restricted, sort_keys=True, indent=2).encode()
    map_digest = "sha256:" + hashlib.sha256(restricted_bytes).hexdigest()

    suppressed = sorted({digest_token(v) for v in plan.suppressed_values})
    aliases = {
        "schema": ALIAS_SCHEMA,
        "kind": "sig/source-alias-records",
        "ticket": "P34.18",
        "adr": "ADR-178",
        "decision": "DR-C6-01 / B-3 — neutral ids; old ids resolve append-only; map restricted",
        "note": (
            "Keys are sha256 digests of retired identifiers — the table repeats "
            "no handle. The plaintext old→new map is restricted (sig-restricted; "
            "never in the repo or any export). Alias rows are append-only; an "
            "old id resolves to its neutral public id without rewriting the "
            "recorded claims (SIG-STORE-011)."
        ),
        "restricted_map_digest": map_digest,
        "source_aliases": {
            digest_token(old): plan.source_map[old] for old in sorted(plan.source_map)
        },
        "target_aliases": {
            digest_token(old): plan.target_map[old] for old in sorted(plan.target_map)
        },
        "token_aliases": {digest_token(old): plan.token_map[old] for old in sorted(plan.token_map)},
        "phrase_aliases": {digest_token(old): new for old, new in sorted(plan.phrase_map.items())},
        "redaction_aliases": {
            digest_token(tok): "[account withheld]" for tok in sorted(plan.suppressed_values)
        },
        "suppressed_value_digests": suppressed,
    }
    if not dry_run:
        map_out.parent.mkdir(parents=True, exist_ok=True)
        map_out.write_bytes(restricted_bytes)
        map_out.chmod(stat.S_IRUSR | stat.S_IWUSR)
        ALIAS_TABLE_OUT.write_text(json.dumps(aliases, sort_keys=True, indent=2) + "\n")
    return {"restricted_map_digest": map_digest, "alias_rows": len(plan.source_map)}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="sig-connectors rekey-personal-ids",
        description="P34.18 personal-handle source-id re-key (dry-run by default).",
    )
    p.add_argument("--handles", type=Path, default=HANDLE_LIST)
    p.add_argument("--apply", action="store_true", help="write changes (default: dry-run)")
    p.add_argument("--report", type=Path, default=REPORT_OUT)
    p.add_argument("--restricted-out", type=Path, default=RESTRICTED_MAP_OUT)
    args = p.parse_args(argv)

    handles = load_handles(args.handles)
    plan = build_plan(handles)
    _merge_prior(plan, args.restricted_out)
    counts: dict[str, Any] = apply_plan(plan, handles, dry_run=not args.apply)
    counts.update(emit(plan, dry_run=not args.apply, map_out=args.restricted_out))
    if args.apply:
        leftovers = verify(plan, handles)
        counts["functional_leftovers"] = sum(leftovers.values())
        if leftovers:
            counts["leftover_files"] = len(leftovers)
        counts["verification"] = "pass" if not leftovers else "FAIL"
        report = {"counts": counts, "verification": counts["verification"]}
        if leftovers:
            report["leftovers"] = leftovers
    else:
        report = {"dry_run": True, "counts": counts}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    print(json.dumps(report["counts"], sort_keys=True))
    return 0 if report.get("verification", "dry-run") in ("pass", "dry-run") else 1


if __name__ == "__main__":
    sys.exit(main())
