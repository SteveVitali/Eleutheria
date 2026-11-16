# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P37.61a — the RULING H-1 fallback transform: turn the captured served tree
(``gs://…-sig-web`` at the 2026-09-27 build) into the minimal-delta dist that
``sig-ops publish-web`` syncs.

The transform is committed engineering, never a hand-edit of the tree. It does
exactly four things, each enumerated in its report:

1. **The three harmful items stop serving** (RULING H-1):
   - ``visual-language/`` — every object removed → the route answers exactly
     HTTP 404 on every resolvable origin (the denied-route probe form; no
     redirect is ever written).
   - ``editorial-standards/index.html`` — its ``<main>`` replaced by the
     holding notice: the ``data-notice="N-1"`` "Not yet performed." allowed
     notice plus unmarked holding copy naming that a previously published
     review record was incorrect and removed. NO ``data-copy`` attributes —
     the current-source honest variant's real batch rows stay ``pending``
     (``D-P35.38a-1``, an operator sitting, out of ticket scope).
   - The dispute promise ``one click, no account required`` replaced
     site-wide by the ``DL-01`` wording as PLAIN TEXT: ``— reports arrive by
     e-mail.`` The link to ``/dispute/`` is kept; the rendered sentence reads
     "Something wrong, or a privacy or safety concern? Dispute or correct
     this record — reports arrive by e-mail."

2. **``/dispute/`` beyond the promise line.** The served page predates the
   P34.17 honest rewrite and describes an operative one-click channel; the
   corrections inbox is disabled. Its ``<main>`` is replaced wholesale by the
   honest-wording page — no ``data-copy`` markers, no promise of an inbox,
   naming the real channel ("Reports and corrections arrive by e-mail."; an
   operator-provided ``SIG_DISPUTE_EMAIL`` value is never written into a
   file, OP-10).

3. **The gate-swept delta** (required-gate engineering — the scripted path's
   own enforcement): every object under a ``[[denied]]`` route or a cadence
   ``http-absent`` path (the denied-route probes refuse them post-sync, so
   they are swept pre-sync), every ``demo_*`` object, and excisions inside
   surviving markup limited to the refused artifact (a ``demo_`` href, a
   loopback ``action``). A ``data-testid="task-field-*"`` demo id or a
   curate-shell banner marks a whole internal page — the OBJECT is removed.
   A secret-shaped hit or a ``data-copy`` attribute resolving to a
   ``pending``/untracked batch row REFUSES the transform outright
   (pause-not-strip — the publish's copy/secret gates can never be smuggled
   past).

The dist input scope is the whole captured tree as captured minus the swept
delta plus the injected pages — lane objects the capture carried upload back
byte-identical (the publish's keep-set covers lane objects freshened after
capture). Denied-prefix sweeps: ``curate/``, ``curate/submit/``,
``task/new/``, ``task/new/demo_roundtrip/``, ``releases/``,
``research-dossier/``, ``intake/``, ``visual-language/`` (the union of
``ops/public_routes.toml`` ``[[denied]]`` and the cadence ``http-absent``
target paths).
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from .publish import (
    _CURATE_BANNER,
    _DEMO_TASK_FIELD,
    _LOOPBACK_ACTION,
    PublishError,
    check_publishable_copy,
    load_allowlist,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

#: The denied-route prefixes swept whole-object: the union of the canonical
#: allow-list's ``[[denied]]`` rows and the cadence ``http-absent`` target
#: paths is derived at run time; these literals are the floor the derivation
#: must contain (the transform REFUSES if a source lists fewer — a profile
#: never weakens the denied set).
_FLOOR_DENIED_PREFIXES: tuple[str, ...] = (
    "curate/",
    "task/new/",
    "releases/",
    "research-dossier/",
    "intake/",
    "visual-language/",
)

#: The dispute promise RULING H-1 item 3 removes — the full sentence, replaced
#: by the DL-01 honest wording as plain text (the anchor to /dispute/ is kept;
#: the rendered sentence matches the current source verbatim).
_PROMISE = "one click, no account required"
_HONEST = "reports arrive by e-mail"

#: A ``demo_`` href/src/action inside an otherwise-surviving page — the
#: refused artifact is the link TARGET, so the excision removes the attribute
#: only (the page keeps its text). Whole ``demo_*`` objects are removed by the
#: path sweep instead.
_DEMO_HREF_ATTR = re.compile(
    r"""(?:href|src|action)\s*=\s*["'][^"']*/demo_[^"']*["']""", re.IGNORECASE
)
_LOOPBACK_ACTION_ATTR = _LOOPBACK_ACTION

_MAIN_RE = re.compile(r"<main id=\"main\">.*</main>", re.DOTALL)

#: The P37.61a holding notice for ``/editorial-standards/`` — the ruling's
#: default authorised variant: the ``data-notice="N-1"`` "Not yet performed."
#: allowed notice plus unmarked holding copy. No ``data-copy`` attributes.
_EDITORIAL_HOLDING_MAIN = (
    '<main id="main"><h1>Editorial standards</h1>'
    "<p>SIG's editorial standards are what make its record usable as "
    "evidence. This page is temporarily reduced to a holding notice while "
    "it is republished.</p>"
    '<h2 id="review-heading">Hostile-reader review</h2>'
    '<p data-testid="review-status" data-notice="N-1">Not yet performed.</p>'
    "<p>A previously published record on this page describing a completed "
    "hostile-reader review was incorrect and has been removed.</p>"
    '<p class="sig-dispute" data-testid="dispute-link-block">Something wrong, '
    'or a privacy or safety concern?<a data-testid="dispute-link" '
    'href="/dispute/">Dispute or correct this record</a> — reports arrive by '
    "e-mail.</p></main>"
)

#: The P37.61a honest ``/dispute/`` — the honest-wording page minus the
#: ``data-copy`` markers (the intake promise is gone; the channel named is
#: e-mail with no promise of an inbox or a response time).
_DISPUTE_HONEST_MAIN = (
    '<main id="main"><h1>Dispute or correct a record</h1>'
    "<p>Anyone can ask SIG to correct, annotate, suppress, or remove a "
    "record — or dispute an accurate one and attach a response.</p>"
    "<h2>How to report</h2>"
    "<p>Reports and corrections arrive by e-mail.</p>"
    "<p>Senders disclose the address they send from. SIG promises no "
    "response time.</p>"
    '<h2 id="priority-heading">Handling order</h2>'
    "<p>SIG handles reports in this order: privacy-harm and safety reports "
    "first, then factual corrections, then everything else.</p>"
    '<h2 id="outcomes-heading">What can happen</h2>'
    '<ul class="sig-dispute-outcomes" aria-labelledby="outcomes-heading">'
    "<li><strong>Correct</strong> — a new, corrected assertion is appended; "
    "the prior value is preserved and stays citable.</li>"
    "<li><strong>Annotate</strong> — a response is attached alongside the "
    "claim, even when the claim is accurate.</li>"
    "<li><strong>Suppress</strong> — removed from public view, retained "
    "internally under seal.</li>"
    "<li><strong>Delete</strong> — reserved for material SIG must not hold at "
    "all; a content-free tombstone records that a deletion occurred.</li>"
    "<li><strong>Refuse</strong> — declined, with published reasoning. "
    "Refusal is a real, exercisable option.</li></ul>"
    '<p class="sig-dispute" data-testid="dispute-link-block">Something wrong, '
    'or a privacy or safety concern?<a data-testid="dispute-link" '
    'href="/dispute/">Dispute or correct this record</a> — reports arrive by '
    "e-mail.</p></main>"
)


@dataclass(frozen=True)
class TransformReport:
    """The enumerated swept delta + injected pages of one transform run —
    the run-ledger evidence (every removed object and every excision named)."""

    removed_objects: tuple[str, ...] = ()
    excisions: tuple[str, ...] = ()
    injected_pages: tuple[str, ...] = ()
    promise_replacements: int = 0
    kept_files: int = 0
    notes: tuple[str, ...] = ()

    def as_lines(self) -> list[str]:
        lines = [
            f"removed objects ({len(self.removed_objects)}):",
            *(f"  - {n}" for n in self.removed_objects),
            f"markup excisions ({len(self.excisions)}):",
            *(f"  - {n}" for n in self.excisions),
            f"injected pages ({len(self.injected_pages)}):",
            *(f"  - {n}" for n in self.injected_pages),
            f"promise replacements: {self.promise_replacements}",
            f"kept files: {self.kept_files}",
        ]
        lines.extend(f"note: {n}" for n in self.notes)
        return lines


def denied_prefixes(
    allowlist_path: str | Path | None = None,
    cadence_path: str | Path | None = None,
) -> frozenset[str]:
    """The object prefixes swept whole-object: the union of the canonical
    allow-list's ``[[denied]]`` routes and the cadence ``http-absent`` target
    paths, plus the floor set — a narrower source never weakens the sweep
    (the union can only grow)."""
    prefixes = set(_FLOOR_DENIED_PREFIXES)
    allow = load_allowlist(allowlist_path)
    prefixes.update(route.lstrip("/") for route in allow.denied_routes)
    from .scheduled import load_cadence

    cadence = load_cadence(cadence_path)
    for spec in cadence.probe_targets:
        if spec.kind == "http-absent" and spec.path:
            prefixes.add(spec.path.lstrip("/"))
    return frozenset(prefixes)


def _iter_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*") if p.is_file())


def _replace_main(path: Path, new_main: str) -> None:
    text = path.read_text(encoding="utf-8")
    if not _MAIN_RE.search(text):
        raise PublishError(
            f'{path}: no <main id="main">…</main> element to replace — the '
            "injected page shape is not what the transform expects"
        )
    path.write_text(_MAIN_RE.sub(lambda _m: new_main, text, count=1), encoding="utf-8")


def transform_prestatetree(
    src: Path,
    dst: Path,
    *,
    allowlist_path: str | Path | None = None,
    cadence_path: str | Path | None = None,
) -> TransformReport:
    """Transform the captured pre-state tree ``src`` into the P37.61a dist
    ``dst``. Returns the enumerated swept delta + injected pages (the run
    ledger's evidence). Refuses — never partially transforms — on a secret
    hit, a ``data-copy`` attribute resolving to a pending/untracked batch row,
    or a refused marker that cannot be cleanly excised (pause-not-strip).
    """
    if not src.is_dir():
        raise PublishError(f"pre-state tree {src} is not a directory")
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)

    denied = denied_prefixes(allowlist_path, cadence_path)
    removed: list[str] = []
    excisions: list[str] = []
    notes: list[str] = []

    # 1. Whole-object sweep: denied-route prefixes + demo_* path segments.
    for path in _iter_files(dst):
        rel = path.relative_to(dst).as_posix()
        parts = path.relative_to(dst).parts
        if any(rel.startswith(p) for p in denied):
            path.unlink()
            removed.append(rel)
        elif any(part.startswith("demo_") for part in parts):
            path.unlink()
            removed.append(rel)

    # 2. Markup excisions in surviving files — limited to the refused artifact;
    #    a whole internal page (curate banner, task-field demo id) removes the
    #    OBJECT; anything else refuses (pause-not-strip).
    for path in _iter_files(dst):
        if path.suffix != ".html":
            continue
        rel = path.relative_to(dst).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        if _CURATE_BANNER in text or _DEMO_TASK_FIELD.search(text):
            path.unlink()
            removed.append(rel)
            excisions.append(f"{rel}: whole object (internal/demo marker page)")
            continue
        new_text = _DEMO_HREF_ATTR.sub("", text)
        new_text = _LOOPBACK_ACTION_ATTR.sub("", new_text)
        if new_text != text:
            n_demo = len(_DEMO_HREF_ATTR.findall(text))
            n_loop = len(_LOOPBACK_ACTION_ATTR.findall(text))
            excisions.append(f"{rel}: excised {n_demo} demo_ href(s), {n_loop} loopback action(s)")
            path.write_text(new_text, encoding="utf-8")

    # 3. The three named items.
    promise_count = 0
    for path in _iter_files(dst):
        if path.suffix != ".html":
            continue
        text = path.read_text(encoding="utf-8")
        if _PROMISE in text:
            hits = text.count(_PROMISE)
            path.write_text(text.replace(_PROMISE, _HONEST), encoding="utf-8")
            promise_count += hits
    if promise_count == 0:
        raise PublishError(
            f"the captured tree carries no {_PROMISE!r} promise — the transform "
            "expected the 09-27 dispute-link text; refusing rather than "
            "inventing a third path (the contract's pause rule)"
        )

    injected: list[str] = []
    editorial = dst / "editorial-standards" / "index.html"
    if not editorial.is_file():
        raise PublishError(
            "the captured tree lacks editorial-standards/index.html — the "
            "holding-notice injection has nothing to replace"
        )
    _replace_main(editorial, _EDITORIAL_HOLDING_MAIN)
    injected.append("editorial-standards/index.html (holding notice, N-1 notice)")

    dispute = dst / "dispute" / "index.html"
    if not dispute.is_file():
        raise PublishError(
            "the captured tree lacks dispute/index.html — the honest-page "
            "injection has nothing to replace"
        )
    _replace_main(dispute, _DISPUTE_HONEST_MAIN)
    injected.append("dispute/index.html (honest wording, no data-copy markers)")

    # 4. Prune emptied directories (the denied sweep can empty a namespace —
    #    task/ holds only task/new/** in the served tree).
    pruned = 0
    for d in sorted(
        (p for p in dst.rglob("*") if p.is_dir()),
        key=lambda p: len(p.parts),
        reverse=True,
    ):
        if not any(d.iterdir()):
            d.rmdir()
            pruned += 1
    if pruned:
        notes.append(f"pruned {pruned} emptied director(y/ies)")

    # 5. Gate-echo checks — refuse BEFORE the publish ever sees the tree:
    #    pause-not-strip on unexpected data-copy collisions (a pending or
    #    untracked rendered sentence), the internal-marker sweep and the
    #    secret scan (a hit inside a real page is never auto-deleted).
    from .publish import assert_public_tree_content, assert_publish_set_secret_free

    copy_violations = check_publishable_copy(dst)
    if copy_violations:
        raise PublishError(
            "transform refused — the captured tree carries data-copy sentences "
            "the copy gate cannot confirm (pause-not-strip; the operator's "
            "copy-batch sitting is out of ticket scope):\n  " + "\n  ".join(copy_violations[:50])
        )
    assert_publish_set_secret_free(dst)
    assert_public_tree_content(dst)

    kept = len(_iter_files(dst))
    return TransformReport(
        removed_objects=tuple(sorted(removed)),
        excisions=tuple(excisions),
        injected_pages=tuple(injected),
        promise_replacements=promise_count,
        kept_files=kept,
        notes=tuple(notes),
    )


def main(argv: Sequence[str] | None = None) -> int:
    """CLI: ``python -m ops.republish_transform --src <captured> --dst <dist>``."""
    parser = argparse.ArgumentParser(
        prog="republish-transform",
        description=(
            "P37.61a — transform the captured served tree into the "
            "minimal-delta publish dist (RULING H-1 fallback path)."
        ),
    )
    parser.add_argument("--src", required=True, help="the captured pre-state tree")
    parser.add_argument("--dst", required=True, help="the output dist directory")
    parser.add_argument(
        "--allowlist", default=None, help="denied-route source (default: canonical)"
    )
    parser.add_argument(
        "--cadence", default=None, help="http-absent source (default: ops/cadence.toml)"
    )
    args = parser.parse_args(argv)
    try:
        report = transform_prestatetree(
            Path(args.src).resolve(),
            Path(args.dst).resolve(),
            allowlist_path=args.allowlist,
            cadence_path=args.cadence,
        )
    except PublishError as exc:
        print(str(exc), file=sys.stderr)
        return 3
    for line in report.as_lines():
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
