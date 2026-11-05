# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P36.66b (TX-13b split b; ADR-161/162; SIG-REL-008; D-J3-6 [B-19] = yes)
— the ``v/<pub>/`` + ``s/<pub>/`` site trees the G3 §5.2 build stage
requires.

The same export-mode Astro build runs twice — latest view (``SIG_BASE_PATH=/``)
→ ``v/<pub>/`` and snapshot (``SIG_BASE_PATH=/s/<pub>``) → ``s/<pub>/``. This
module is the pipeline leg that assembles those two dist trees into the
built release's ``work_dir`` so ``verb_stage``'s plan picks them up
(``staged/{r,v,s,releases}/<pub>/``), and it emits the pieces the release
model owns *here*, at build time, not at serve time:

* ``release.json`` — the release's own ``sig.site-release/1`` copy at each
  tree's root (the ``describedby`` target every stamped page names).
* ``s/<pub>/page_index.json`` — the **withdrawal index** (J3 §8.1): route →
  embedded entity/claim/artifact ids, so a withdrawn record's snapshot
  pages answer 410 with the tombstone body — ``apply_withdrawals`` already
  consumes every ``page_index.json`` under the staged tree; a withdrawal
  leaves a tombstone, never a gap.
* ``v/<pub>/entity/<type>/<id>/`` convenience stubs + the
  ``compat_index.json`` copy — the latest-view overlays the serving map
  resolves inside ``v/<latest>`` (G3 §4.2); mutable, never citations.

Containment (SIG-REL-008 / the §5.3 rule): every same-origin link inside
the snapshot tree must stay under ``/s/<pub>/`` except the declared
exception namespaces — ``/r/`` records, ``/releases/``, the live ``/v1/``
API and the ``/intake/`` receiver (labelled "live, not a citation",
SIG-UI-076) — and the declared legacy ``?as_of_`` selector form. The
assembler re-scans the emitted bytes at the pipeline seam: a link that
escapes through ANY construction fails the leg, never silently ships.

Nothing here publishes: the trees stay under ``work_dir`` until the
operator's Class S promote exposes them (HG-11 is the operator's gate).
"""

from __future__ import annotations

import json
import os
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from . import release_pipeline as rp

#: The p-<64hex> publication-id shape (release_identity.publication_id).
PUB_RE = re.compile(r"^p-[0-9a-f]{64}$")

#: The wire schema id of the withdrawal index (J3 §8.1) — consumed by
#: ``exports.release.apply_withdrawals``' page_index coverage.
PAGE_INDEX_SCHEMA = "sig.page-index/1"

#: Namespaces a snapshot never contains — the declared SIG-REL-008
#: exceptions, mirrored from ``web/src/lib/paths.ts`` OUTSIDE_BASE_PREFIXES
#: so the seam check never trusts the code it audits (the web-side
#: ``check-snapshot-mount.mjs`` carries the same list for the same reason).
OUTSIDE_BASE_PREFIXES: tuple[str, ...] = ("/r/", "/releases/", "/v1/", "/intake/")

#: The emitted-HTML attribute set the containment scan reads — the same
#: four the web-side mount check declares.
_ATTR_RE = re.compile(r'(?:href|src|action|poster)="([^"]*)"')

#: Embedded-id markers a snapshot page may carry — the ``data-*``
#: attributes the components already emit (WhereThisComesFrom /
#: ArtifactRows / DossierFigureDetails / evidence pages) plus entity
#: references reachable through a released-record link.
_ID_ATTRS = {
    "entity_ids": re.compile(r'data-entity-id="([^"]+)"'),
    "claim_ids": re.compile(r'data-claim-id="([^"]+)"'),
    "artifact_ids": re.compile(r'data-artifact-id="([^"]+)"'),
}
_RECORD_ENTITY_RE = re.compile(
    r"/r/p-[0-9a-f]{64}/c/[A-Za-z0-9_.~-]+/entity/[A-Za-z0-9_.~-]+/([A-Za-z0-9_.~-]+)"
)


def _html_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.html") if p.is_file())


def scan_containment(html: str, *, base: str) -> list[str]:
    """The §5.3/SIG-REL-008 containment rule over one emitted page —
    mirror of ``web/scripts/check-snapshot-mount.mjs`` ``scanHtml``: a
    root-absolute link must start with the snapshot base or a declared
    exception; a protocol-relative link is a fail on its own."""
    violations: list[str] = []
    for m in _ATTR_RE.finditer(html):
        v = m.group(1)
        if v.startswith("//"):
            violations.append(f"protocol-relative {v[:80]} — never allowed")
            continue
        if v.startswith("/"):
            if not v.startswith(base) and not any(v.startswith(p) for p in OUTSIDE_BASE_PREFIXES):
                violations.append(f"root-absolute {v[:80]} escapes the snapshot base")
    return violations


def embedded_ids(html: str) -> dict[str, list[str]]:
    """The entity/claim/artifact ids one emitted page embeds — from the
    ``data-*-id`` markers plus released-record links (a record route
    carries the real entity id in its path)."""
    out: dict[str, set[str]] = {k: set() for k in _ID_ATTRS}
    for key, pattern in _ID_ATTRS.items():
        for m in pattern.finditer(html):
            out[key].add(m.group(1))
    for m in _RECORD_ENTITY_RE.finditer(html):
        out["entity_ids"].add(m.group(1))
    return {k: sorted(v) for k, v in out.items()}


def page_index_document(snapshot_root: Path, pub: str) -> dict[str, Any]:
    """``sig.page-index/1`` — the withdrawal index: every emitted page
    route under ``s/<pub>/`` and the record ids it embeds.
    ``apply_withdrawals`` denies a listed route whole when a disposition
    denies any embedded id."""
    if not PUB_RE.match(pub):
        raise rp.PipelineError("bad-input", f"publication id {pub!r} is not p-<64hex>")
    pages: list[dict[str, Any]] = []
    for page in _html_files(snapshot_root):
        rel = page.relative_to(snapshot_root).as_posix()
        if rel.endswith("index.html"):
            route = rel[: -len("index.html")]
        else:
            route = rel
        route = f"s/{pub}/{route}"
        ids = embedded_ids(page.read_text(encoding="utf-8", errors="replace"))
        row: dict[str, Any] = {"route": route}
        for key in ("entity_ids", "claim_ids", "artifact_ids"):
            if ids[key]:
                row[key] = ids[key]
        pages.append(row)
    return {
        "schema": PAGE_INDEX_SCHEMA,
        "publication_id": pub,
        "pages": sorted(pages, key=lambda r: r["route"]),
    }


def _copy_tree(src: Path, dst: Path) -> None:
    """Copy a dist tree into the namespace — hardlinks where possible
    (the staged tree and the build dir are the same immutable bytes)."""
    for p in sorted(src.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(src)
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            if target.exists():
                target.unlink()
            os.link(p, target)
        except OSError:
            shutil.copyfile(p, target)


def _refuse_existing(root: Path, label: str) -> None:
    """An already-populated namespace refuses: nothing staged is ever
    overwritten (SIG-REL-005) — a rebuild names a new publication id."""
    if root.exists() and any(root.iterdir()):
        raise rp.PipelineError(
            "tree-exists",
            f"{root} is already populated — the {label} tree is never "
            "overwritten in place; a rebuilt release carries a new pub",
        )


def assemble_site_trees(
    work_dir: Path | str,
    pub: str,
    *,
    latest_dist: Path | str | None = None,
    snapshot_dist: Path | str | None = None,
    compat_index: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble ``work_dir/{v,s}/<pub>/`` from the two Astro dist trees.

    * ``latest_dist`` — the base-``/`` export build → ``v/<pub>/`` (the
      latest-view tree the promoted release's serving root mounts).
    * ``snapshot_dist`` — the ``SIG_BASE_PATH=/s/<pub>`` build →
      ``s/<pub>/`` (the forever-citable snapshot).

    Refuses a missing/dist-less tree and a snapshot whose same-origin
    links escape the base (SIG-ENG-042: an unverifiable surface fails).
    """
    work_dir = Path(work_dir)
    if not PUB_RE.match(pub):
        raise rp.PipelineError("bad-input", f"publication id {pub!r} is not p-<64hex>")

    release_json = work_dir / f"releases/{pub}/release.json"
    if not release_json.is_file():
        release_json = work_dir / "release.json"
    if not release_json.is_file():
        raise rp.PipelineError(
            "no-release-json",
            f"no release.json under {work_dir} for {pub} — build_release "
            "runs first (the stamp's machine twin is never invented)",
        )

    result: dict[str, Any] = {"publication_id": pub, "trees": {}, "page_index": None}

    # -- the snapshot tree -------------------------------------------------
    if snapshot_dist is not None:
        src = Path(snapshot_dist)
        if not src.is_dir() or not any(src.iterdir()):
            raise rp.PipelineError(
                "empty-dist", f"snapshot dist {src} is empty — a vacuous snapshot fails"
            )
        sroot = work_dir / "s" / pub
        _refuse_existing(sroot, "s")
        violations: list[str] = []
        for page in _html_files(src):
            for v in scan_containment(
                page.read_text(encoding="utf-8", errors="replace"), base=f"/s/{pub}/"
            ):
                violations.append(f"{page.relative_to(src)}: {v}")
        if violations:
            raise rp.PipelineError(
                "containment",
                f"snapshot tree carries {len(violations)} same-origin link(s) "
                f"escaping /s/{pub}/ (SIG-REL-008):\n  " + "\n  ".join(violations[:20]),
            )
        _copy_tree(src, sroot)
        shutil.copyfile(release_json, sroot / "release.json")
        index = page_index_document(sroot, pub)
        (sroot / "page_index.json").write_text(
            json.dumps(index, sort_keys=True, indent=None, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        result["trees"]["s"] = {
            "pages": len(_html_files(sroot)),
            "containment_violations": 0,
        }
        result["page_index"] = {"pages": len(index["pages"])}

    # -- the latest-view tree ---------------------------------------------
    if latest_dist is not None:
        src = Path(latest_dist)
        if not src.is_dir() or not any(src.iterdir()):
            raise rp.PipelineError(
                "empty-dist", f"latest-view dist {src} is empty — a vacuous build fails"
            )
        vroot = work_dir / "v" / pub
        _refuse_existing(vroot, "v")
        _copy_tree(src, vroot)
        shutil.copyfile(release_json, vroot / "release.json")
        # The latest-view overlays (G3 §4.2): the /entity/<t>/<id>/
        # convenience stubs + the compat_index copy resolve inside
        # v/<latest>. The stubs are mutable pointers — never citations —
        # emitted from the release's own record index.
        stubs = _emit_entity_stubs(work_dir, vroot, pub)
        compat = compat_index or {"schema": "sig.compat-index/1", "entries": []}
        (vroot / "compat_index.json").write_text(
            json.dumps(compat, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        result["trees"]["v"] = {
            "pages": len(_html_files(vroot)),
            "entity_stubs": stubs,
        }
    return result


def _emit_entity_stubs(work_dir: Path, vroot: Path, pub: str) -> int:
    """The ``/entity/<type>/<id>/`` convenience stubs under the latest
    view — the same ``entity_stub`` the exports overlay emits (a pointer
    at THIS release's record route), from the release's own
    ``records.index.jsonl`` per compartment."""
    from exports.release_pages import entity_stub, release_stamp_view

    stamp: dict[str, Any] | None = None
    site_rel = work_dir / f"releases/{pub}/release.json"
    if site_rel.is_file():
        try:
            doc = json.loads(site_rel.read_bytes())
            stamp = release_stamp_view(doc, describedby="/release.json", variant="latest")
        except (OSError, ValueError):
            stamp = None
    count = 0
    for comp_dir in sorted((work_dir / "r" / pub / "c").glob("*")):
        idx = comp_dir / "records.index.jsonl"
        if not idx.is_file():
            continue
        for line in idx.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except ValueError:
                continue
            et, eid = str(row.get("entity_type") or ""), str(row.get("entity_id") or "")
            path = str(row.get("path") or "")
            if not et or not eid or not path:
                continue
            stub = entity_stub(
                entity_type=et,
                entity_id=eid,
                latest_publication=pub,
                record_href="/" + path.lstrip("/"),
                stamp=stamp,
            )
            out = vroot / "entity" / et / eid / "index.html"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(stub)
            count += 1
    return count


def verb_sites(
    store: rp.Store,
    *,
    apply_: bool,
    work_dir: str | Path,
    latest_dist: str | Path | None = None,
    snapshot_dist: str | Path | None = None,
    publication_id: str | None = None,
    break_lock: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """``sites`` — the P36.66b build leg: assemble ``v/<pub>/`` +
    ``s/<pub>/`` under ``work_dir`` from the two Astro export-mode dist
    trees, emit ``release.json`` copies + ``s/<pub>/page_index.json`` +
    the latest-view overlays, and journal the ``sites`` event.

    ``--snapshot-dist`` and ``--latest-dist`` name the two build outputs;
    either may be omitted only when its namespace is already assembled
    (a resume) — a missing tree is a refusal, never a fabricated one.
    """
    work_dir = Path(work_dir)
    pub = publication_id or rp._publication_id_of(work_dir)
    result: dict[str, Any] = {
        "verb": "sites",
        "publication_id": pub,
        "applied": False,
    }
    plan = []
    if latest_dist is not None:
        plan.append(f"v/{pub}/ ← {latest_dist}")
    if snapshot_dist is not None:
        plan.append(f"s/{pub}/ ← {snapshot_dist} (+ release.json, page_index.json)")
    plan.append("emit v/<pub>/entity/* stubs + compat_index.json")
    if not apply_:
        result["dry_run"] = True
        result["plan"] = plan
        return result
    now = now or datetime.now(UTC)
    with rp.acquire_lock(store, "sites", break_lock=break_lock, now=now) as lock:
        out = assemble_site_trees(
            work_dir,
            pub,
            latest_dist=latest_dist,
            snapshot_dist=snapshot_dist,
        )
        lock.refresh()
        name = rp.emit_event(
            store,
            "sites",
            pub,
            {
                "outcome": "recorded",
                "trees": out.get("trees"),
                "page_index": out.get("page_index"),
            },
            now=now,
        )
        result.update(
            applied=True,
            event=name,
            trees=out.get("trees"),
            page_index=out.get("page_index"),
        )
    return result
