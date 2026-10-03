# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P34.12 research-queue truth fixes (K11 RQ-00, C3 NEW-10/NEW-13, F-113/F-274).

Source-level invariants for the retired fixture intake surface and the honest
queue card:

* no `/task/new/` route, link or "has been generated" copy can return;
* the export shaper carries no `contributor`/`unknown` placeholders and the
  "not yet classified" label is the SAME literal in Python and TypeScript;
* the queue page renders unique task anchors derived from rendered rows and
  names itself in its provenance scope line;
* the publish allow-list demotes `task` out of `required` and denies the
  retired `/task/new/` prefix;
* batch-01 keeps the retired `T-01` row (append-only) and binds the new
  sentences (HW-10 template, RQ-01/XC-03 literals).
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

PUBLIC_DIRS = ["web/src/pages", "web/src/components", "web/src/layouts"]

GENERATED_TASK_COPY = re.compile(r"has been generated", re.IGNORECASE)
TASK_NEW_LINK = re.compile(r'href="[^"]*/task/new/')


def _source(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def _public_astro_files() -> list[Path]:
    files: list[Path] = []
    for base in PUBLIC_DIRS:
        for path in (REPO_ROOT / base).rglob("*.astro"):
            if "internal" in path.parts:
                continue
            files.append(path)
    return sorted(files)


def _batch_text(rid: str) -> str:
    for line in (
        (REPO_ROOT / "docs/build/reports/copy-batches/batch-01.md")
        .read_text(encoding="utf-8")
        .splitlines()
    ):
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")]
        cells = cells[1:-1] if cells and cells[0] == "" else cells
        if len(cells) == 5 and cells[0] == rid:
            return cells[2]
    raise AssertionError(f"batch row {rid} not found")


def test_task_new_route_is_gone_from_pages_and_libs() -> None:
    """The fixture intake surface is retired wholesale (RQ-00 / F-274): the page,
    the slug codec lib, its unit test, the absence registry and the dossier
    derivation no longer exist anywhere the site can reach."""
    assert not (REPO_ROOT / "web/src/pages/task").exists(), "web/src/pages/task/ must not exist"
    assert not (REPO_ROOT / "web/src/lib/task.ts").exists()
    assert not (REPO_ROOT / "web/tests/unit/task.test.ts").exists()
    for rel in ["web/src/lib/fixtures.ts", "web/src/lib/dossier.ts"]:
        src = _source(rel)
        removed_names = (
            "TASKABLE_ABSENCES",
            "dossierTaskableAbsences",
            "absenceTaskHref",
            "AbsenceTaskParams",
        )
        for removed in removed_names:
            assert removed not in src, f"{rel}: {removed} must be retired"
            # (the dossier doc comment may NAME the retired seam — see below)


def test_no_task_new_link_or_generated_copy_anywhere_public() -> None:
    """No public page, component or layout may link `/task/new/` or render
    'has been generated' text (F-113). Sweeps raw source — identifiers and
    comments are inert; links and prose are not."""
    offenders: list[str] = []
    for path in _public_astro_files():
        src = path.read_text(encoding="utf-8")
        for m in TASK_NEW_LINK.finditer(src):
            offenders.append(f"{path.relative_to(REPO_ROOT)}: link {m.group(0)!r}")
        # The generated-task markup the mock page rendered can never return.
        for marker in ('data-testid="generated-task"', 'data-testid="task-field-'):
            if marker in src:
                offenders.append(f"{path.relative_to(REPO_ROOT)}: marker {marker!r}")
        # The forbidden sentence itself (visible markup text: tags stripped).
        text = re.sub(r"<!--.*?-->", " ", src, flags=re.S)
        text = re.sub(r"<[^>]*>", " ", text)
        for _m in GENERATED_TASK_COPY.finditer(text):
            offenders.append(f"{path.relative_to(REPO_ROOT)}: 'has been generated' copy")
    assert offenders == [], "retired intake surface artifacts remain:\n" + "\n".join(offenders)


def test_absence_hatch_is_a_named_absence_not_a_link() -> None:
    """SIG-UI-007's gap affordance degrades to a named absence until RQ-03 ships
    real `/task/<handle>/` pages — never a mock intake link."""
    src = _source("web/src/components/AbsenceHatch.astro")
    assert "<a" not in src and "absenceTaskHref" not in src
    markers = (
        'data-testid="absence-hatch"',
        "data-absence-kind",
        "data-absence-subject",
        "data-absence-predicate",
    )
    for marker in markers:
        assert marker in src, f"AbsenceHatch lost {marker}"


def test_export_queue_shaper_has_no_placeholders_and_the_label_is_shared() -> None:
    """`_research_queue` must not invent `contributor`/`unknown`/`[]` — and the
    'not yet classified' literal is one contract spelled identically in the
    export and the web surface."""
    py = _source("exports/src/exports/spine_export.py")
    ts = _source("web/src/lib/research-queue.ts")
    for placeholder in ('"contributor"', '"unknown"'):
        assert placeholder not in py, f"spine_export still fabricates {placeholder}"
    assert 'NOT_YET_CLASSIFIED = "not yet classified"' in py
    assert 'NOT_YET_CLASSIFIED = "not yet classified"' in ts
    # The batch pins the literal twice — once per implementation file.
    assert _batch_text("RQ-01") == "not yet classified"
    assert _batch_text("XC-03") == "not yet classified"
    # The catalog join is real: dispositions/assignee/effort come from the
    # TaskType registry, not the row.
    assert "_task_catalog()" in py and "spec.dispositions" in py


def test_queue_page_renders_unique_task_anchors_and_live_filters() -> None:
    src = _source("web/src/pages/research-queue.astro")
    assert "assertUniqueTaskAnchors(capped.rows)" in src
    assert "jurisdictionAnchors(capped.rows)" in src
    assert "taskAnchor(card)" in src
    # The retired duplicate-id scheme must not return.
    assert "jurisdiction-${" not in src and "id={`jurisdiction-" not in src


def test_queue_page_names_its_provenance_scope() -> None:
    """C3 NEW-13: the queue's 'How we know this' names the page it describes."""
    src = _source("web/src/pages/research-queue.astro")
    assert 'provenanceName="research queue"' in src
    comp = _source("web/src/components/HowWeKnowThis.astro")
    assert 'data-copy="HW-10"' in comp
    assert _batch_text("HW-10") in comp or "{pageName}" in comp
    layout = _source("web/src/layouts/BaseLayout.astro")
    assert "provenanceName" in layout and "pageName" in layout


def test_allowlist_demotes_task_and_denies_the_retired_prefix() -> None:
    from ops.publish import load_allowlist  # noqa: PLC0415 — test-local import

    allow = load_allowlist(REPO_ROOT / "ops" / "public_routes.toml")
    assert "task" in allow.top_level  # real /task/<handle>/ pages stay publishable
    assert "task" not in allow.required  # a build emitting no task/ must not fail
    assert "/task/new/" in allow.denied_routes


def test_retired_task_page_batch_row_stays_recorded_never_shippable() -> None:
    """T-01 is batch history for a deleted page: still in batch-01 (append-only),
    carried by nothing."""
    text = _batch_text("T-01")
    assert text == "Return to the dossier index."
    # Its sha still verifies — the record is intact, the page is gone.
    for line in (
        (REPO_ROOT / "docs/build/reports/copy-batches/batch-01.md")
        .read_text(encoding="utf-8")
        .splitlines()
    ):
        if line.startswith("| T-01 "):
            cells = [c.strip() for c in line.split("|")]
            cells = cells[1:-1]
            assert cells[3] == hashlib.sha256(cells[2].encode("utf-8")).hexdigest()
