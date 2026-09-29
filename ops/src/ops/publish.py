# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The public cut-over producer: build the real-data site + partition the export into
the published vs restricted compartments (P27.8 / LAUNCH.8, §38, §42.3, ADR-096).

`sig-ops deploy --target gcp` publishes the public surface. Two invariants govern what
that surface may carry, and this module enforces both **before** any byte is synced:

1. **The public build reads the real national export, or it fails loud.** The static
   site (`web/dist`) is built with ``SIG_DATA_SOURCE=export`` against the P27.4 national
   export (``exports/out/national`` by default; ``SIG_EXPORT_DIR`` overrides). There is
   **never** a silent fall-back to the committed fixtures for the public build — a green
   public build off a missing export would ship a demo wearing the national name
   (§38.1, the §3.1 defining standard). :func:`assert_export_present` fails closed.

2. **Only the published compartment goes public (§42 / Part VIII).** The licence-
   compartmented bundle is partitioned into ``exports/out/public`` (synced public-read)
   and ``exports/out/restricted`` (kept PRIVATE). The classification is **data-driven and
   fail-closed** off ``policy.licensing``: a compartment is public *iff* its licence is
   non-``share_alike`` and carries no recorded export exclusion — so the share-alike
   layers (ODbL-1.0 OSM-derived, CC-BY-SA-4.0 portal) and every ``UNDETERMINED`` /
   counsel-pending byte land in the PRIVATE compartment (00_MANIFEST cross-cutting
   invariant: *ODbL + UNDETERMINED never public*). :func:`assert_public_clean` re-scans
   the built public tree and raises loudly on any leak — belt-and-suspenders over the
   partition, so a producer bug cannot silently push a restricted byte to a public object.

ADR-096 records the reconciliation with §42.3 (which publishes the ODbL layer as a
*separate file*): the national cut-over ships only the CC-BY published compartment; the
ODbL national layer's public release is a dedicated, gated decision (D-LEGAL.1-1), so it
stays in the private compartment here rather than the CC-BY public bucket.
"""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .degraded import DegradedBuildError, Runner, build_static_site

#: The default national export the public build reads (the P27.4 `--from-spine` bundle).
#: `SIG_EXPORT_DIR` overrides; there is deliberately NO fixtures default for the public
#: build (the web dev default `exports/out/okc` lives in `web/src/lib/data.ts`, not here).
DEFAULT_NATIONAL_EXPORT = "exports/out/national"

#: The manifest that must exist for a directory to count as a real export (never a
#: fixtures tree). The per-artifact fail-loud on individual `web/*.json` surfaces is the
#: web build's own contract (`web/src/lib/data.ts`, proven by P27.5); here we assert the
#: bundle is present at all.
_MANIFEST = "manifest.json"
_WEB_DIR = "web"


class PublishError(RuntimeError):
    """The public cut-over cannot proceed — fails LOUD (never a fabricated green)."""


class CompartmentLeak(PublishError):
    """A restricted/ODbL/UNDETERMINED artifact reached the public compartment (§42)."""


# --- 1. the export-mode public build ------------------------------------------


def public_export_dir(repo_root: Path | None = None) -> Path:
    """The export directory the public build reads (env override → national default)."""
    override = os.environ.get("SIG_EXPORT_DIR", "").strip()
    if override:
        return Path(override)
    base = repo_root or Path.cwd()
    return base / DEFAULT_NATIONAL_EXPORT


def assert_export_present(export_dir: Path) -> Path:
    """Assert ``export_dir`` is a real export bundle, or raise :class:`PublishError`.

    Fails closed on a missing directory, a missing ``manifest.json`` (the mark of a real
    export, not a fixtures tree), or a missing ``web/`` surface subtree. This is what
    stops the public build from silently falling back to fixtures when the national
    export has not been produced (D-P27.4-1).
    """
    if not export_dir.exists() or not export_dir.is_dir():
        raise PublishError(
            f"the public build's export directory is absent: {export_dir}. The national "
            "export (P27.4, `sig-exports build --from-spine … --out exports/out/national`) "
            "must be produced first — the public build NEVER falls back to fixtures."
        )
    if not (export_dir / _MANIFEST).is_file():
        raise PublishError(
            f"{export_dir} has no {_MANIFEST}: it is not a real export bundle. Refusing to "
            "build the public site from it (no fixtures fall-back for the public build)."
        )
    if not (export_dir / _WEB_DIR).is_dir():
        raise PublishError(
            f"{export_dir} has no {_WEB_DIR}/ subtree: the web surfaces the site renders are "
            "absent. Rebuild the export before the public cut-over."
        )
    return export_dir


def build_public_web(
    *,
    repo_root: Path,
    export_dir: Path | None = None,
    runner: Runner | None = None,
) -> Path:
    """Build ``web/dist`` from the real national export (``SIG_DATA_SOURCE=export``).

    Asserts the export is present (fails loud, never fixtures), then drives the same
    static build the degraded/keepalive posture uses. Raises :class:`PublishError` if the
    export is absent or the build fails — the public site is never shipped off a stale or
    fabricated bundle.
    """
    resolved = assert_export_present(export_dir or public_export_dir(repo_root))
    kwargs: dict[str, Any] = {
        "repo_root": repo_root,
        "data_source": "export",
        "export_dir": str(resolved),
    }
    if runner is not None:
        kwargs["runner"] = runner
    try:
        return build_static_site(**kwargs)
    except DegradedBuildError as exc:
        raise PublishError(
            f"the public export-mode build FAILED: {exc}. The public site is not shipped "
            "off a broken build (never a fixtures fall-back)."
        ) from exc


# --- 2. the published vs restricted compartment partition ---------------------


def _registry(registry: dict[str, Any] | None) -> dict[str, Any]:
    if registry is not None:
        return registry
    from policy.licensing import load_table

    return dict(load_table("licenses"))


def classify_compartment(
    compartment: str, license_id: str | None, registry: dict[str, Any] | None = None
) -> str:
    """``"public"`` iff this artifact may ship to a public object, else ``"restricted"``.

    Fail-closed and data-driven off ``policy/data/licenses.toml``: public requires a
    KNOWN, non-``share_alike`` licence with no recorded export exclusion. So ODbL-1.0 /
    CC-BY-SA-4.0 (share-alike), any ``UNDETERMINED``/unknown licence, and any
    counsel-pending excluded licence resolve to ``"restricted"`` — never public
    (00_MANIFEST cross-cutting invariant; §42 / Part VIII).
    """
    from policy.licensing import license_export_disposition

    reg = _registry(registry)
    facts = reg.get("licenses", {}).get(license_id or "")
    if facts is None:  # unknown / UNDETERMINED licence — never public
        return "restricted"
    if facts.get("share_alike", False):  # ODbL-1.0, CC-BY-SA-4.0
        return "restricted"
    if license_export_disposition(license_id or "", reg) is not None:  # counsel-pending
        return "restricted"
    return "public"


def read_manifest(export_root: Path) -> dict[str, Any]:
    """Parse ``export_root/manifest.json`` (raises :class:`PublishError` if unreadable)."""
    path = export_root / _MANIFEST
    try:
        return json.loads(path.read_text(encoding="utf-8"))  # type: ignore[no-any-return]
    except (OSError, json.JSONDecodeError) as exc:
        raise PublishError(f"cannot read export manifest {path}: {exc}") from exc


def export_watermark(export_root: Path) -> dict[str, Any]:
    """The built-from watermark: the release/provenance stamp the site was built from.

    Reads ``manifest.reproducibility_inputs`` (as-of belief/snapshot, resolver + ruleset
    versions) plus ``release_id``/``content_key``/``concept_id`` — the exact spine/export
    state the public surface renders, recorded at cut-over (P27.8 deliverable 3).
    """
    m = read_manifest(export_root)
    ri = dict(m.get("reproducibility_inputs", {}))
    return {
        "release_id": m.get("release_id"),
        "content_key": m.get("content_key"),
        "concept_id": m.get("concept_id"),
        "as_of_snapshot": ri.get("as_of_snapshot"),
        "as_of_belief": ri.get("as_of_belief"),
        "ruleset_version": ri.get("ruleset_version"),
        "resolver_version": ri.get("resolver_version"),
    }


@dataclass(frozen=True)
class PartitionResult:
    """The outcome of partitioning an export into public + restricted compartments."""

    public_root: Path
    restricted_root: Path
    public_artifacts: tuple[str, ...] = ()
    restricted_artifacts: tuple[str, ...] = ()
    watermark: dict[str, Any] = field(default_factory=dict)

    def as_lines(self) -> list[str]:
        return [
            f"partition: {len(self.public_artifacts)} public → {self.public_root}",
            f"           {len(self.restricted_artifacts)} restricted → {self.restricted_root}",
            f"           built-from: {self.watermark.get('release_id') or '<no release_id>'}",
        ]


def _write_manifest(root: Path, source: dict[str, Any], artifacts: list[dict[str, Any]]) -> None:
    """Write a manifest listing only ``artifacts`` (compartment-filtered), keeping the
    provenance/watermark top-level fields intact."""
    doc = {k: v for k, v in source.items() if k != "artifacts"}
    doc["artifacts"] = artifacts
    root.mkdir(parents=True, exist_ok=True)
    (root / _MANIFEST).write_text(
        json.dumps(doc, sort_keys=True, separators=(",", ":")), encoding="utf-8"
    )


def partition_export(
    export_root: Path,
    public_root: Path,
    restricted_root: Path,
    registry: dict[str, Any] | None = None,
) -> PartitionResult:
    """Split the compartmented export into a PUBLISHED tree and a PRIVATE tree.

    Every manifest artifact is copied into ``public_root`` or ``restricted_root`` by
    :func:`classify_compartment`; each root gets its own compartment-filtered manifest.
    Returns the per-tier artifact lists and the built-from watermark. This is the
    producer step the deploy sync consumes (``exports/out/public`` → ``…-sig-public``
    public-read; ``exports/out/restricted`` → ``…-sig-restricted`` PRIVATE).
    """
    reg = _registry(registry)
    manifest = read_manifest(export_root)
    for root in (public_root, restricted_root):
        if root.exists():
            shutil.rmtree(root)
        root.mkdir(parents=True, exist_ok=True)
    public_arts: list[dict[str, Any]] = []
    restricted_arts: list[dict[str, Any]] = []
    for art in manifest.get("artifacts", []):
        rel = art["path"]
        src = export_root / rel
        tier = classify_compartment(art.get("compartment", ""), art.get("license"), reg)
        dst_root = public_root if tier == "public" else restricted_root
        dst = dst_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_file():
            shutil.copy2(src, dst)
        (public_arts if tier == "public" else restricted_arts).append(art)
    _write_manifest(public_root, manifest, public_arts)
    _write_manifest(restricted_root, manifest, restricted_arts)
    return PartitionResult(
        public_root=public_root,
        restricted_root=restricted_root,
        public_artifacts=tuple(sorted(a["path"] for a in public_arts)),
        restricted_artifacts=tuple(sorted(a["path"] for a in restricted_arts)),
        watermark=export_watermark(export_root),
    )


def assert_public_clean(public_root: Path, registry: dict[str, Any] | None = None) -> None:
    """Prove no restricted/ODbL/UNDETERMINED byte reached the public compartment (§42).

    Re-reads ``public_root/manifest.json`` and re-classifies every artifact; raises
    :class:`CompartmentLeak` naming any artifact that is NOT public. Also cross-checks the
    physical tree so a file copied in outside the manifest cannot slip through. This runs
    after :func:`partition_export` and before the public sync — the deliverable-2 proof.
    """
    reg = _registry(registry)
    manifest = read_manifest(public_root)
    listed: dict[str, dict[str, Any]] = {}
    leaks: list[str] = []
    for art in manifest.get("artifacts", []):
        listed[art["path"]] = art
        tier = classify_compartment(art.get("compartment", ""), art.get("license"), reg)
        if tier != "public":
            leaks.append(
                f"{art['path']} (compartment={art.get('compartment')!r} "
                f"licence={art.get('license')!r})"
            )
    # Cross-check the physical tree: every data file present must be a public-listed artifact.
    for path in sorted(public_root.rglob("*")):
        if not path.is_file() or path.name == _MANIFEST:
            continue
        rel = str(path.relative_to(public_root))
        if rel not in listed:
            leaks.append(f"{rel} (present in the public tree but not a published artifact)")
    if leaks:
        raise CompartmentLeak(
            "public compartment leak — these artifacts must NOT reach a public object "
            "(§42 / Part VIII; ODbL + UNDETERMINED never public):\n  " + "\n  ".join(leaks)
        )


@dataclass(frozen=True)
class PrepareResult:
    """The outcome of the local public-prepare (build + partition + clean, network-free)."""

    dist: Path
    partition: PartitionResult

    def as_lines(self) -> list[str]:
        return [
            f"public build: {self.dist}  (SIG_DATA_SOURCE=export)",
            *self.partition.as_lines(),
            "public compartment clean: no ODbL/share-alike/UNDETERMINED byte reaches a public "
            "object",
        ]


def run_public_prepare(
    *,
    repo_root: Path,
    export_dir: Path | None = None,
    public_root: Path | None = None,
    restricted_root: Path | None = None,
    runner: Runner | None = None,
    registry: dict[str, Any] | None = None,
) -> PrepareResult:
    """Produce the public surface locally (no network): build ``web/dist`` from the real
    national export, partition the bundle into published + restricted compartments, and
    PROVE the public compartment is clean. Fails loud (:class:`PublishError`) at the first
    honest obstacle (absent export, broken build, or a compartment leak) — never a
    fabricated green. The gcloud syncs are the operator's cut-over step (they run this
    prepared output; ``sig-ops deploy`` prints them)."""
    resolved = assert_export_present(export_dir or public_export_dir(repo_root))
    dist = build_public_web(repo_root=repo_root, export_dir=resolved, runner=runner)
    pub = public_root or (repo_root / "exports" / "out" / "public")
    res = restricted_root or (repo_root / "exports" / "out" / "restricted")
    partition = partition_export(resolved, pub, res, registry=registry)
    assert_public_clean(pub, registry=registry)
    return PrepareResult(dist=dist, partition=partition)


__all__ = [
    "DEFAULT_NATIONAL_EXPORT",
    "PrepareResult",
    "run_public_prepare",
    "PublishError",
    "CompartmentLeak",
    "PartitionResult",
    "public_export_dir",
    "assert_export_present",
    "build_public_web",
    "classify_compartment",
    "read_manifest",
    "export_watermark",
    "partition_export",
    "assert_public_clean",
]
