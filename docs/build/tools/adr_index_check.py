#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""G8-1/G8-2 — the ADR index tells the truth, and every superseded / amended / qualified /
extended / revisited ADR carries its appended status line (P34.32; B4 G8; COV-14; SIG-ENG-039).

Two checks over ``docs/adr/`` (failures print, exit 1; vacuous = no ADR files, exit 3):

**A. Index.** ``docs/adr/README.md`` is regenerated in memory with the same parse as
``scripts/docs/adr-index.sh`` — every row must carry a parseable ADR number, title, owning
ticket/phase and status, and the committed file must match a fresh regeneration byte for
byte. A ``—`` cell is a violation when (a) the ADR number is ≥ 146 (the T1 template boundary —
a new ADR must use the indexed header fields, G8-1 hard failure) or (b) the file *does* carry
a matching header field the generator should have read (an unexplained ``—``). It is a warning
only when the field is genuinely absent from a legacy file's header (ADR-120 names no
Ticket/Phase — the generator adapts to the header forms in use, it cannot invent an owner;
BM-COMPAT-06's warn-only legacy gap).

**B. Supersession / qualification (G8-2, COV-14).** An ADR named in a later ADR's declaration
field must carry the matching appended ``- **Status:** <Kind> by ADR-NNN (<YYYY-MM-DD>)`` line
in its ``## Status updates`` section — the one legal body change a landed ADR permits
(BM-ADR-01, G2 ``frozen-after-landing``).

Checked declaration surfaces (fields, plus sentence-initial body declarations):

* ``Supersedes:`` / ``Amends:`` / ``Qualifies:`` / ``Extends:`` / ``Revises:`` / ``Revisits:``
  — the field's kind; every ``ADR-NNN`` token in the value is a target;
* ``Amends / qualifies / extends:``, ``Relationship to landed ADRs:``,
  ``Relation to landed ADRs:`` — the verbs in the value pick the kind
  (``supersedes`` → Superseded, ``amends`` → Amended, ``qualifies`` → Qualified,
  ``extends`` → Extended, ``revisits``/``revises`` → Revisited) and the following
  ``ADR-NNN`` list the targets;
* decision text — a sentence that *starts* ``ADR-NNN(, and|, ADR-MMM) (is|are) <kind>``
  (e.g. ADR-167's "ADR-086 and ADR-106 are qualified, not superseded.") or carries the
  first-person form ``This ADR (supersedes|amends|qualifies|extends|revisits) ADR-NNN``.

Related-family fields (``Related:``, ``Relates to:``, ``Related / amends:``) are
bibliographic *lists*, but an annotation can carry a declaration — the convention's own
history confirms this (ADR-075's ``Superseded by ADR-081`` line answers a "departs from its
DECISION" note; ADR-092's line answers ADR-099's "this ADR supersedes that posture" note).
So each ``ADR-NNN`` token's annotation span (its parenthetical, capped at the next ADR
token) is scanned for:

* a first-person declaration — ``this (ADR )?(supersedes|amends|qualifies|extends|
  revises|revisits|departs)`` (``departs`` → Superseded, ``revises`` → Revisited);
* a kind marker — ``— <kind>``, ``**<kind>**``, ``is <kind>`` or ``the <kind> <noun>``
  (e.g. "the superseded classifier"). A kind word wins over a first-person verb in the
  same span: ADR-194's "this extends — qualified, not rewritten" requires Qualified.

Not obligations: a bare ``Related: ADR-NNN`` reference (the spec's own counter-example);
an annotation with no closed-vocabulary signal (``this mirrors`` / ``this generalises`` /
``the read API the per-claim attribution extends`` are mechanism notes); a value starting
``none``; mentions inside quoted spans (``'…'``, ``"…"``, ```` `…` ````); a
``no status line for ADR-NNN`` / ``assigns ADR-NNN's … line to`` /
``leaves ADR-NNN … unchanged`` note; ``records``-supersession phrases ("It supersedes
records, not ADR decisions"); a ``not <kind>`` clause; a self-reference.

The target's satisfying line must read ``- **Status:** <Kind> by <…ADR-NNN…> (<YYYY-MM-DD>)``
inside its ``## Status updates`` section (a ``… and ADR-MMM`` shared line satisfies each named
source; a trailing "— §3 only" qualifier is fine). A named target with no file fails closed
(an unexplained edge). Section-scoped, so ``### Trigger evaluation`` prose can never satisfy
or fabricate a line.

Run:  python3 docs/build/tools/adr_index_check.py [--adr-dir DIR]
Test: uv run pytest docs/build/tools/test_adr_index_check.py
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[3]
ADR_DIR = ROOT / "docs/adr"
GENERATOR = ROOT / "scripts/docs/adr-index.sh"

NEW_ADR_BOUNDARY = 146  # T1 template boundary: a `—` cell on ADR-146+ is a hard failure (G8-1).

KINDS = ("Superseded", "Amended", "Qualified", "Extended", "Revisited")
_KIND_WORD = r"(Superseded|Amended|Qualified|Extended|Revisited)"

# field labels that declare relationships. Single-kind labels name the kind; the combined and
# relationship labels are verb-scanned.
_LABEL_KIND = {
    "supersedes": "Superseded",
    "amends": "Amended",
    "qualifies": "Qualified",
    "extends": "Extended",
    "revises": "Revisited",
    "revisits": "Revisited",
}
_VERB_FIELDS = {"amends / qualifies / extends", "relationship to landed adrs",
                "relation to landed adrs"}
_VERB_KIND = {"supersed": "Superseded", "amend": "Amended", "qualif": "Qualified",
              "extend": "Extended", "revis": "Revisited"}

_FIELD_RE = re.compile(r"^\s*-\s*(?:\*\*)?([A-Za-z][A-Za-z /]{1,60}?)(?:\*\*)?:\s*(.*)$")
_H1_RE = re.compile(r"^#\s+ADR-(\d+)\s*(:|—|-)\s*(.*)$", re.M)
_H2_RE = re.compile(r"^## ", re.M)
_STATUS_LINE_RE = re.compile(
    r"^\s*-\s*(?:\*\*)?Status:(?:\*\*)?\s*" + _KIND_WORD + r"\s+by\s+(.*)$"
)
_DATE_RE = re.compile(r"\(\d{4}-\d{2}-\d{2}[^)]*\)")
_VERB_LIST_RE = re.compile(
    r"(supersed\w+|amend\w+|qualif\w+|extend\w+|revis\w*)\s+"
    r"(?:that\s+|the\s+)?(ADR-\d{3}(?:\s*(?:,?\s*and|,|/)\s*ADR-\d{3})*)",
    re.I,
)
_ADR_LIST_RE = re.compile(r"ADR-(\d{3})")
# Related-family annotation signals — kind word beats first-person verb in the same span.
_REL_KIND_RE = re.compile(
    r"—\s*\**\s*(superseded|amended|qualified|extended|revisited)\b"
    r"|\*\*(superseded|amended|qualified|extended|revisited)\*\*"
    r"|\bis\s+(superseded|amended|qualified|extended|revisited)\b"
    r"|\bthe\s+(superseded|amended|qualified|extended|revisited)\s+\w",
    re.I,
)
_REL_VERB_RE = re.compile(
    r"\bthis\b[^.;]{0,60}?(supersedes|amends|qualifies|extends|revises|revisits|departs)\b",
    re.I,
)
_REL_FIELDS = {"related", "relates to", "related / amends"}
_BODY_DECL_RE = re.compile(
    r"(?m)^\s*(?:\d+\.\s*|[-*]\s*)?\**\s*(ADR-\d{3}(?:\s*(?:,|and)\s*ADR-\d{3})*)\s+"
    r"(?:is|are)\s+" + _KIND_WORD.lower() + r"\b",
    re.I,
)
_THIS_ADR_RE = re.compile(
    r"This ADR\s+(supersedes|amends|qualifies|extends|revisits|revises)\s+(ADR-\d{3})", re.I
)


def _strip_quotes(text: str) -> str:
    """Blank quoted spans (a quoted mention never declares): '…', "…", `…`."""
    text = re.sub(r"`[^`]*`", "``", text)
    text = re.sub(r"'[^'\n]*'", "''", text)
    text = re.sub(r'"[^"\n]*"', '""', text)
    return text


def fields(text: str):
    """Yield ``(label, value)`` for every ``- Label:``-style line, anywhere in the file.

    A field's value is its own line plus continuation lines until the next bullet
    (``- ``), heading or blank line — deeper-indented ``- `` sub-bullets are excluded, which
    keeps plan-note bullets (e.g. ADR-162's "'a new ADR extending ADR-132'") out of the value.
    Handles ``- **Label:**``, ``- Label:``, ``**Label:**`` and ``Label:``; the label is
    matched case-insensitively by the caller.
    """
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        m = _FIELD_RE.match(lines[i])
        if not m:
            i += 1
            continue
        label = m.group(1).strip()
        val = re.sub(r"^\*+\s*", "", m.group(2))  # `**Label:** v` leaves a leading `**`
        j = i + 1
        while (
            j < len(lines)
            and lines[j].strip()
            and not re.match(r"^\s*-\s|^\s*#", lines[j])
        ):
            val += " " + lines[j].strip()
            j += 1
        yield label, val
        i = j


def header_field(text: str, label: str) -> str:
    """First header field (above the first ``## `` heading) with an exact label match.

    Byte-for-byte port of the generator's awk ``field()``: the value is the remainder of
    the label's own line only — a wrapped continuation line is NOT joined (that is how the
    committed index's truncated cells were produced; the generator adapts, bodies stay frozen).
    """
    # the generator's two forms: `**Label:** v` / `Label: v`, bullet optional
    pat = re.compile(
        r"^\s*(?:-\s*)?(?:\*\*" + re.escape(label) + r":\*\*|" + re.escape(label) + r":)[ \t]*(.*)$",
        re.I,
    )
    for line in _H2_RE.split(text, maxsplit=1)[0].splitlines():
        m = pat.match(line)
        if m:
            return m.group(1).strip()
    return ""


def status_update_lines(text: str) -> list[tuple[str, list[str], str]]:
    """``(kind, [ADR-NNN refs], raw)`` for each appended status line in ``## Status updates``."""
    sec = re.search(r"(?ms)^## Status updates\s*$(.*?)(?=^## |\Z)", text)
    if not sec:
        return []
    out: list[tuple[str, list[str], str]] = []
    for line in sec.group(1).splitlines():
        m = _STATUS_LINE_RE.match(line)
        if m:
            refs = ["ADR-" + n for n in _ADR_LIST_RE.findall(m.group(2))]
            out.append((m.group(1).capitalize(), refs, line.strip()))
    return out


def _kind_of_verb(verb: str) -> str:
    stem = re.match(r"(supersed|amend|qualif|extend|revis|depart)", verb.lower()).group(1)
    return _VERB_KIND.get(stem) or {"depart": "Superseded"}[stem]


def _related_span(val: str, tok_end: int, next_tok_start: int | None) -> str:
    """The annotation span for an ``ADR-NNN`` token in a Related-family field: its
    parenthetical (cut at the closing ``),``/``);``/``).``) or the tail until the next
    ADR token, capped at 220 chars."""
    span = val[tok_end : next_tok_start if next_tok_start is not None else len(val)]
    m = re.match(r"[^()]*\((.*)", span, re.S)
    if m:
        close = re.search(r"\)\s*[,;.]\s*", m.group(1))
        if close:
            span = span[: m.start(1) + close.start() + 1]
    return span[:220]


def obligations(path: pathlib.Path) -> dict[tuple[str, str], str]:
    """``{(target, kind): where-declared}`` — every status line this ADR's text requires."""
    text = _strip_quotes(path.read_text(encoding="utf-8"))
    adr = re.match(r"ADR-\d{3}", path.name).group(0)
    reqs: dict[tuple[str, str], str] = {}
    for label, val in fields(text):
        lab = label.lower()
        if re.match(r"\s*none\b", val, re.I):
            continue
        cancel = set(re.findall(r"no status line for (ADR-\d{3})", val, re.I))
        cancel |= set(re.findall(r"assigns (ADR-\d{3})'s", val, re.I))
        cancel |= set(re.findall(r"leaves (ADR-\d{3})[^;]*unchanged", val, re.I))
        if lab in _LABEL_KIND:
            for t in _ADR_LIST_RE.findall(val):
                reqs.setdefault(("ADR-" + t, _LABEL_KIND[lab]), f"`{label}:` field")
        elif lab in _VERB_FIELDS:
            for verb, targets in _VERB_LIST_RE.findall(val):
                kind = _kind_of_verb(verb)
                for t in _ADR_LIST_RE.findall(targets):
                    reqs.setdefault(("ADR-" + t, kind), f"`{label}:` field")
        elif lab in _REL_FIELDS:
            toks = list(_ADR_LIST_RE.finditer(val))
            for i, tok in enumerate(toks):
                span = _related_span(val, tok.end(), toks[i + 1].start() if i + 1 < len(toks) else None)
                km = _REL_KIND_RE.search(span)
                if km:
                    kind = next(k.capitalize() for k in km.groups() if k)
                else:
                    vm = _REL_VERB_RE.search(span)
                    if not vm:
                        continue
                    kind = _kind_of_verb(vm.group(1))
                reqs.setdefault(("ADR-" + tok.group(1), kind), f"`{label}:` annotation")
        reqs = {k: v for k, v in reqs.items() if k[0] not in cancel}
    # sentence-initial body declarations ("ADR-086 and ADR-106 are qualified, not superseded.")
    for m in _BODY_DECL_RE.finditer(text):
        kind = m.group(2).capitalize()
        for t in _ADR_LIST_RE.findall(m.group(1)):
            reqs.setdefault(("ADR-" + t, kind), "body declaration")
    # first-person body declarations ("This ADR amends ADR-030")
    for m in _THIS_ADR_RE.finditer(text):
        kind = _kind_of_verb(m.group(1))
        reqs.setdefault((m.group(2), kind), "body declaration")
    return {k: v for k, v in reqs.items() if k[0] != adr}  # a file can never supersede itself


# ── index regeneration (a Python port of scripts/docs/adr-index.sh row()) ──────────────────

def _cell(v: str) -> str:
    return v.replace("|", "\\|")


def _title_of(text: str) -> str:
    m = _H1_RE.search(text)
    return m.group(3).strip() if m else ""


def _status_of(text: str) -> str:
    lines = status_update_lines(text)
    if lines:
        _kind, _refs, raw = lines[-1]
        # port of the generator's status_line(): strip `- `, all `**`, `Status:`, trailing space
        v = re.sub(r"^\s*-\s*", "", raw).replace("**", "")
        return re.sub(r"^Status:\s*", "", v).rstrip()
    return header_field(text, "Status")


def _owner_of(text: str) -> str:
    for lab in ("Ticket", "Phase", "Phase / ticket"):
        v = header_field(text, lab)
        if v:
            return v
    return ""


def index_rows(adr_dir: pathlib.Path) -> list[tuple[str, str, str, str, str]]:
    """``(file, adr_id, title, owner, status)`` per ADR file, numeric order (the generated table)."""
    files = []
    for f in adr_dir.glob("ADR-*.md"):
        m = re.match(r"ADR-0*(\d+)", f.name)
        if m:
            files.append((int(m.group(1)), f))
    rows = []
    for _n, f in sorted(files):
        text = f.read_text(encoding="utf-8")
        m = _H1_RE.search(text)
        adr_id = ("ADR-" + m.group(1)) if m else re.match(r"ADR-\d+", f.name).group(0)
        rows.append((f.name, adr_id, _title_of(text), _owner_of(text), _status_of(text)))
    return rows


def generate_index(adr_dir: pathlib.Path) -> str:
    """What ``adr-index.sh --check`` prints: the generated table + preserved trailing section."""
    out = [
        "<!-- generated by build-memory adr-index; do not edit -->",
        "# Architecture Decision Records",
        "",
        "One row per ADR, numeric order. Regenerate with `build-memory adr-index`",
        "(`scripts/adr-index.sh`); never hand-edit — the validator diffs a regeneration.",
        "",
        "| ADR | Title | Ticket | Status |",
        "|---|---|---|---|",
    ]
    for name, adr_id, title, owner, status in index_rows(adr_dir):
        out.append(
            f"| [{adr_id}]({name}) | {_cell(title or '—')} | {_cell(owner or '—')} | {_cell(status or '—')} |"
        )
    readme = adr_dir / "README.md"
    if readme.is_file():
        m = _H2_RE.search(readme.read_text(encoding="utf-8"))
        if m:
            out.append("")
            out.append(readme.read_text(encoding="utf-8")[m.start():].rstrip("\n"))
    return "\n".join(out) + "\n"


def _field_present(text: str, which: str) -> bool:
    """The file carries the header field the cell derives from (present-but-unparsed ⇒ viol)."""
    if which == "title":
        return bool(_H1_RE.search(text))
    if which == "owner":
        return any(header_field(text, lab) for lab in ("Ticket", "Phase", "Phase / ticket"))
    if which == "status":
        return bool(header_field(text, "Status") or status_update_lines(text))
    return False


def check(root: pathlib.Path, adr_dir: pathlib.Path | None = None):
    """``(errors, warnings, stats)`` — see the module docstring for the rules."""
    adr_dir = adr_dir or (root / "docs/adr")
    errors: list[str] = []
    warnings: list[str] = []
    files = [f for f in adr_dir.glob("ADR-*.md") if re.match(r"ADR-\d+", f.name)]
    if not files:
        return ["vacuous: no ADR-*.md files"], warnings, {"offered": 0, "evaluated": 0}

    # A. index — regenerated table vs the committed file, then per-cell `—` reasons.
    readme = adr_dir / "README.md"
    rows = index_rows(adr_dir)
    if readme.is_file():
        expected = generate_index(adr_dir)
        if readme.read_text(encoding="utf-8") != expected:
            errors.append(
                "docs/adr/README.md does not match a fresh adr-index regeneration "
                "(hand-edited or stale) — regenerate with `bash scripts/docs/adr-index.sh docs/adr`"
            )
    else:
        errors.append("docs/adr/README.md is missing — regenerate with `bash scripts/docs/adr-index.sh docs/adr`")

    for name, adr_id, title, owner, status in rows:
        nnn = int(re.search(r"\d+", adr_id).group(0))
        text = (adr_dir / name).read_text(encoding="utf-8")
        for cell_name, value in (("title", title), ("owner", owner), ("status", status)):
            if value:
                continue
            present = _field_present(text, cell_name)
            if present or nnn >= NEW_ADR_BOUNDARY:
                why = (
                    f"the field is present but did not parse"
                    if present
                    else f"ADR-{nnn:03d} is new (≥ ADR-146) — the template header fields are required"
                )
                errors.append(f"{name}: index {cell_name} cell reads '—' ({why})")
            else:
                warnings.append(
                    f"{name}: index {cell_name} cell reads '—' (no {cell_name} header field — "
                    "a genuinely absent legacy field; the generator adapts, bodies stay frozen)"
                )

    # B. supersession — every checked declaration has its matching appended line.
    by_name = {f.name[:7]: f for f in files}
    obligations_count = 0
    for f in sorted(files):
        src = f.name[:7]
        for (target, kind), where in sorted(obligations(f).items()):
            obligations_count += 1
            tf = by_name.get(target)
            if tf is None:
                errors.append(
                    f"{f.name}: {where} names {target} ({kind}) but no {target}-*.md file exists"
                )
                continue
            lines = status_update_lines(tf.read_text(encoding="utf-8"))
            hits = [(k, refs, raw) for k, refs, raw in lines if k == kind and src in refs]
            if not hits:
                errors.append(
                    f"{f.name}: {where} declares {target} {kind}, but {tf.name} carries no "
                    f"`- **Status:** {kind} by {src} (<date>)` line in `## Status updates`"
                )
            elif not any(_DATE_RE.search(raw) for _, _, raw in hits):
                errors.append(
                    f"{tf.name}: the `{kind} by {src}` status line lacks the `(<date -u>)` date"
                )
    stats = {
        "offered": len(files),
        "index_rows": len(rows),
        "declarations": obligations_count,
        "evaluated": len(rows) + obligations_count,
    }
    return errors, warnings, stats


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="G8-1/G8-2 ADR index + supersession status-line check")
    ap.add_argument("root", nargs="?", default=str(ROOT), help="repo root (default: the tool's)")
    ap.add_argument("--adr-dir", default=None, help="ADR directory (default: <root>/docs/adr)")
    ap.add_argument("--shell-diff", action="store_true",
                    help="also diff README against `bash scripts/docs/adr-index.sh --check` "
                         "(belt-and-suspenders for the Python port)")
    args = ap.parse_args(argv)
    root = pathlib.Path(args.root).resolve()
    adr_dir = pathlib.Path(args.adr_dir).resolve() if args.adr_dir else None
    errors, warnings, stats = check(root, adr_dir=adr_dir)
    if errors and errors[0].startswith("vacuous"):
        print(f"adr-index: vacuous — {errors[0]}", file=sys.stderr)
        return 3
    for e in errors:
        print(f"  ✗ {e}")
    for w in warnings:
        print(f"  ~ {w}")
    if args.shell_diff and (adr_dir or root / "docs/adr").is_dir():
        ad = adr_dir or root / "docs/adr"
        gen = subprocess.run(["bash", str(GENERATOR), "--check", str(ad)],
                             capture_output=True, text=True)
        if gen.returncode == 0 and (ad / "README.md").is_file() and \
                (ad / "README.md").read_text() != gen.stdout:
            print("  ✗ README.md != `adr-index.sh --check` output (shell generator diff)")
            errors.append("shell-diff")
    print(
        f"adr-index: offered {stats['offered']} ADR files / {stats['index_rows']} index rows / "
        f"{stats['declarations']} declarations · evaluated {stats['evaluated']} "
        f"· {'OK' if not errors else f'{len(errors)} violation(s)'}"
        + (f", {len(warnings)} warning(s)" if warnings else "")
    )
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
