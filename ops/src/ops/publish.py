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

2. **Only publishable, licence-separated compartments go public (§42 / Part VIII).** The
   licence-compartmented bundle is partitioned into ``exports/out/public`` (synced
   public-read) and ``exports/out/restricted`` (kept PRIVATE). The classification is
   **data-driven and fail-closed** off ``policy.licensing``: an artifact is public *iff*
   it carries ONE known licence with no recorded export exclusion, and — when it sits in a
   registered ``[compartments.*]`` row — that compartment's declared licence. Every
   ``UNDETERMINED`` / unknown / counsel-pending-excluded byte, and every **mixed-licence**
   artifact (a compound SPDX expression, or a licence that disagrees with its compartment),
   lands in the PRIVATE compartment. :func:`assert_public_clean` re-scans the built public
   tree and raises loudly on any leak — including two licences inside one public
   compartment (the ``assert_separated`` invariant, re-proven over the public tree) —
   belt-and-suspenders over the partition, so a producer bug cannot silently push a
   restricted or mixed byte to a public object.

ADR-106 supersedes ADR-096's classifier rule (operator decision 2026-09-24, counsel
clearance operator-reported, ``D-P30.3-COUNSEL``): the share-alike compartments (ODbL-1.0
``osm_physical``, CC-BY-SA) are no longer restricted *for being share-alike* — they are
published as their own separate, attributed compartments beside the CC-BY ``sig_graph``,
never merged with it (ODbL 4.4(a)); the rendered site is the 4.4(b) produced work that
shows every layer with "© OpenStreetMap contributors" attribution. :func:`write_licence_index`
labels each public compartment with its SPDX licence + attribution.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

from .alerts import utcnow
from .degraded import DegradedBuildError, Runner, build_static_site

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Sequence

    from .gcs import GcsBucket
    from .observe import ProbeResult

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

#: The per-compartment licence + attribution index written at the public root (ADR-106).
LICENCE_INDEX = "LICENCES.json"

#: The canonical licence URLs for the licences SIG publishes — resolution lives
#: in ``policy.licensing.license_url`` (licenses.toml ``license_url`` fact →
#: canonical map → SPDX page; ``LicenseRef-*`` without a fact resolves ``None``
#: and the index emits the honest absence, P34.21a / E2-12).

#: The attribution line each licence's re-user must carry. ODbL-1.0 is the OpenStreetMap
#: attribution (§42.3, SIG-GEO-013); every other compartment names SIG plus the per-row
#: source attribution the rows carry (SIG-EXPORT-006).
_ATTRIBUTION: dict[str, str] = {
    "ODbL-1.0": "© OpenStreetMap contributors (ODbL-1.0); compiled by the SIG project",
    "CC-BY-4.0": "© The SIG project — CC-BY-4.0",
}
_DEFAULT_ATTRIBUTION = (
    "The SIG project, plus the per-source attribution each row's _rights block and the "
    "compartment's ATTRIBUTION.json carry (SIG-EXPORT-006)"
)


#: The publication-basis label every public descriptor carries (E2 H-6; OM-08,
#: ADR-167/ADR-182) — the single source of truth is ``exports.manifest.PUBLICATION_BASIS``;
#: the same string lands in ``manifest.json``, ``datapackage.json`` and ``LICENCES.json``.
def _publication_basis() -> str:
    from exports.manifest import PUBLICATION_BASIS

    return PUBLICATION_BASIS


class PublishError(RuntimeError):
    """The public cut-over cannot proceed — fails LOUD (never a fabricated green)."""


class CompartmentLeak(PublishError):
    """A restricted/ODbL/UNDETERMINED artifact reached the public compartment (§42)."""


class AttributionLeak(PublishError):
    """An attribution-required row reached publication with no credit (E2-12/ADR-194)."""


def _iter_jsonl_rows(root: Path) -> Iterable[tuple[str, int, dict[str, Any]]]:
    """Every (relpath, line_no, row) of every ``*.jsonl`` file under ``root``."""
    for path in sorted(root.rglob("*.jsonl")):
        rel = str(path.relative_to(root))
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                yield rel, i, row


def attribution_violations(root: Path) -> list[str]:
    """The E2-12 publish-time gate, file-tree form.

    Scans every ``*.jsonl`` row under ``root`` for a ``_rights`` block that
    declares ``attribution_required = true`` with an absent or whitespace-only
    ``attribution`` — the same rule ``exports.compartments.enrich_rows``
    applies at build. Returns the human-readable violation list
    (``path:line source_id``); empty is the pass. Runs identically at export
    preparation (the public partition) and at ``publish-web`` (the staged
    export tree) so a defected bundle can never reach a public object.
    """
    violations: list[str] = []
    for rel, line_no, row in _iter_jsonl_rows(root):
        rights = row.get("_rights")
        if not isinstance(rights, dict):
            continue
        if not rights.get("attribution_required", False):
            continue
        attribution = rights.get("attribution")
        if attribution is None or not str(attribution).strip():
            source = rights.get("source_id") or row.get("source_id") or "(unknown)"
            violations.append(f"{rel}:{line_no} source_id={source}")
    return violations


def assert_attribution_complete(root: Path) -> None:
    """Fail closed when a public row names no upstream to credit (E2-12 / ADR-194)."""
    violations = attribution_violations(root)
    if violations:
        raise AttributionLeak(
            f"attribution gate refused {root}: {len(violations)} public row(s) carry "
            "attribution_required=true with empty attribution (E2-12 / ADR-194 — "
            "SIG-CONTRIB-020 requires every claim's upstream to be named):\n  "
            + "\n  ".join(violations[:50])
            + ("\n  …" if len(violations) > 50 else "")
        )


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
    if (export_dir / _WEB_DIR / "presentation").exists():
        raise PublishError(
            f"{export_dir}/{_WEB_DIR}/presentation/ exists: that is the fixture-export harness's "
            "DEMO presentation data (P27.5), never national data. Refusing to build the public "
            "site from it (P30.3, ADR-106 §6)."
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
        dist = build_static_site(**kwargs)
    except DegradedBuildError as exc:
        raise PublishError(
            f"the public export-mode build FAILED: {exc}. The public site is not shipped "
            "off a broken build (never a fixtures fall-back)."
        ) from exc
    strip_non_public_web(dist)
    return dist


#: Build routes that are NOT public surfaces: the authenticated curation app's static shell
#: (``/curate/**`` — "Authenticated curation surface — not public", ADR-068; served only by
#: the loopback curation app). Since P34.10 the default build never emits them at all
#: (``web/src/internal/`` injects only under ``SIG_BUILD_INTERNAL=1``) — this strip stays
#: as belt-and-suspenders over a build that was run with the internal flag set; the
#: allow-list assertion in :func:`assert_allowlisted_tree` is the primary gate.
NON_PUBLIC_WEB_PATHS: tuple[str, ...] = ("curate",)


def strip_non_public_web(dist: Path) -> list[str]:
    """Remove any non-public routes from a built ``web/dist`` before the public sync."""
    removed: list[str] = []
    for rel in NON_PUBLIC_WEB_PATHS:
        target = dist / rel
        if target.exists():
            shutil.rmtree(target)
            removed.append(rel)
    return removed


# --- 2. the published vs restricted compartment partition ---------------------


def _registry(registry: dict[str, Any] | None) -> dict[str, Any]:
    if registry is not None:
        return registry
    from policy.licensing import load_table

    return dict(load_table("licenses"))


#: Characters that make a licence value a compound (multi-licence) SPDX expression rather than
#: ONE licence id — an artifact carrying one is a mixed-licence artifact and never public.
_COMPOUND_MARKERS = (" ", "(", ")", ",", ";", "+", "/")


def _is_single_license_id(license_id: object) -> bool:
    """True iff ``license_id`` is ONE plain licence id (not absent, not a list, not an SPDX
    ``A AND B`` / ``A OR B`` / ``A WITH B`` expression) — a compound value marks a
    mixed-licence artifact (ADR-106)."""
    if not isinstance(license_id, str) or not license_id.strip():
        return False
    return not any(marker in license_id for marker in _COMPOUND_MARKERS)


def restriction_reason(
    compartment: str, license_id: object, registry: dict[str, Any] | None = None
) -> str | None:
    """Why an artifact must stay PRIVATE, or ``None`` when it may ship to a public object.

    Fail-closed and data-driven off ``policy/data/licenses.toml`` (ADR-106, superseding the
    ADR-096 rule that also restricted every share-alike licence):

    * ``mixed-licence`` — the licence is absent, a list, or a compound SPDX expression: one
      artifact must carry ONE licence (SIG-EXPORT-005; ODbL never merged with CC-BY, 4.4(a));
    * ``unknown-licence`` — ``UNDETERMINED`` or any licence not in the registry;
    * ``excluded:<key>`` — a recorded export exclusion (counsel-pending, HG-02);
    * ``unregistered-compartment`` — no ``[compartments.*]`` row (nor the export's own
      ``web``/``metadata`` compartments) declares the artifact's compartment;
    * ``compartment-licence-mismatch`` — the artifact's compartment declares a DIFFERENT
      licence (a mis-filed or merged file).

    Share-alike (ODbL-1.0, CC-BY-SA-*) is NOT itself a reason: those compartments publish as
    their own separate, attributed downloads (operator decision 2026-09-24, D-P30.3-COUNSEL).
    """
    from policy.licensing import license_export_disposition

    if not _is_single_license_id(license_id):
        return "mixed-licence"
    assert isinstance(license_id, str)  # narrowed by _is_single_license_id
    reg = _registry(registry)
    if license_id not in reg.get("licenses", {}):  # UNDETERMINED / unknown — never public
        return "unknown-licence"
    disposition = license_export_disposition(license_id, reg)
    if disposition is not None:  # counsel-pending / recorded exclusion
        return f"excluded:{disposition['exclusion']}"
    declared_license = _declared_compartment_license(compartment, reg)
    if declared_license is None:  # a compartment nothing declares — never public
        return "unregistered-compartment"
    if declared_license != license_id:
        return "compartment-licence-mismatch"
    return None


#: The export's OWN non-data compartments (``exports.spine_export``): the SIG render surfaces
#: (``web``) and the bundle descriptors (``metadata``), both SIG-original CC-BY-4.0. They are not
#: ``[compartments.*]`` rows (a row there would re-route CC-BY site data into them), so they are
#: declared here — an artifact in either must carry exactly that licence (e.g. an all-OSM
#: ``web/map.json`` labelled ODbL-1.0 is a mismatch → restricted, never a second licence in the
#: public ``web`` compartment).
_EXPORT_OWN_COMPARTMENTS: dict[str, str] = {"web": "CC-BY-4.0", "metadata": "CC-BY-4.0"}


def _declared_compartment_license(compartment: str, reg: dict[str, Any]) -> str | None:
    declared = reg.get("compartments", {}).get(compartment)
    if declared is not None:
        return str(declared.get("license"))
    return _EXPORT_OWN_COMPARTMENTS.get(compartment)


def classify_compartment(
    compartment: str, license_id: str | None, registry: dict[str, Any] | None = None
) -> str:
    """``"public"`` iff this artifact may ship to a public object, else ``"restricted"``.

    Public requires ONE known licence with no recorded export exclusion that agrees with its
    registered compartment (:func:`restriction_reason`). ODbL-1.0 / CC-BY-SA-4.0 compartments
    are public as SEPARATE compartments (ADR-106); ``UNDETERMINED``/unknown, excluded and
    mixed-licence artifacts resolve to ``"restricted"`` — never public (§42 / Part VIII).
    """
    reason = restriction_reason(compartment, license_id, registry)
    return "public" if reason is None else "restricted"


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
        if not src.is_file():
            raise PublishError(
                f"manifest artifact {rel!r} is missing from {export_root} — refusing to publish "
                "a manifest that lists bytes it does not carry."
            )
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
    """Prove no restricted / UNDETERMINED / mixed-licence byte reached the public tree (§42).

    Re-reads ``public_root/manifest.json`` and re-classifies every artifact; raises
    :class:`CompartmentLeak` naming any artifact that is NOT public. Re-proves the
    ``assert_separated`` invariant over the public tree — every public compartment carries
    exactly ONE licence (so the ODbL layer can never sit in a file or directory with the CC-BY
    graph, 4.4(a)). Also cross-checks the physical tree so a file copied in outside the
    manifest cannot slip through. Runs after :func:`partition_export` and before the public
    sync (ADR-096 / ADR-106).
    """
    reg = _registry(registry)
    manifest = read_manifest(public_root)
    listed: dict[str, dict[str, Any]] = {}
    leaks: list[str] = []
    licences_by_compartment: dict[str, set[str]] = {}
    for art in manifest.get("artifacts", []):
        listed[art["path"]] = art
        compartment = str(art.get("compartment", ""))
        reason = restriction_reason(compartment, art.get("license"), reg)
        if reason is not None:
            leaks.append(
                f"{art['path']} (compartment={art.get('compartment')!r} "
                f"licence={art.get('license')!r}: {reason})"
            )
        licences_by_compartment.setdefault(compartment, set()).add(str(art.get("license")))
    for compartment, licences in sorted(licences_by_compartment.items()):
        if len(licences) > 1:
            leaks.append(
                f"compartment {compartment!r} mixes licences {sorted(licences)} "
                "(mixed-licence compartment — each licence ships as its own compartment)"
            )
    # Cross-check the physical tree: every data file present must be a public-listed artifact
    # (the two root descriptors this module writes are the only exceptions).
    for path in sorted(public_root.rglob("*")):
        if not path.is_file() or path.name in (_MANIFEST, LICENCE_INDEX):
            continue
        rel = str(path.relative_to(public_root))
        if rel not in listed:
            leaks.append(f"{rel} (present in the public tree but not a published artifact)")
    if leaks:
        raise CompartmentLeak(
            "public compartment leak — these artifacts must NOT reach a public object "
            "(§42 / Part VIII; UNDETERMINED, excluded and mixed-licence never public):\n  "
            + "\n  ".join(leaks)
        )


def _licence_url(license_id: str, registry: dict[str, Any] | None = None) -> str | None:
    from policy.licensing import license_url

    return license_url(license_id, registry)


def write_licence_index(public_root: Path, registry: dict[str, Any] | None = None) -> Path:
    """Label every public compartment with its SPDX licence + attribution (ADR-106).

    Writes ``public_root/LICENCES.json``: one entry per public compartment — its single
    licence, the licence URL, share-alike / attribution-required facts from
    ``policy/data/licenses.toml``, the attribution line a re-user must carry (ODbL:
    "© OpenStreetMap contributors"), and the artifact paths it covers. The downloadable
    datasets stay licence-SEPARATED; this index is how a re-user knows which regime governs
    which file (per-row source attribution travels in the rows themselves, SIG-EXPORT-006).
    """
    reg = _registry(registry)
    manifest = read_manifest(public_root)
    by_compartment: dict[str, dict[str, Any]] = {}
    for art in manifest.get("artifacts", []):
        compartment = str(art.get("compartment", ""))
        license_id = str(art.get("license"))
        entry = by_compartment.setdefault(
            compartment,
            {"compartment": compartment, "license": license_id, "paths": []},
        )
        entry["paths"].append(art["path"])
    compartments: list[dict[str, Any]] = []
    for compartment in sorted(by_compartment):
        entry = by_compartment[compartment]
        license_id = entry["license"]
        facts = reg.get("licenses", {}).get(license_id, {})
        compartments.append(
            {
                "compartment": compartment,
                "license": license_id,
                "license_url": _licence_url(license_id, reg),
                "share_alike": bool(facts.get("share_alike", False)),
                "attribution_required": bool(facts.get("attribution_required", True)),
                "attribution": _ATTRIBUTION.get(license_id, _DEFAULT_ATTRIBUTION),
                "paths": sorted(entry["paths"]),
            }
        )
    doc = {
        "schema": "sig/public-licence-index/1.0.0",
        "release_id": manifest.get("release_id"),
        "publication_basis": _publication_basis(),
        "note": (
            "Each compartment is a separate dataset under exactly one licence; compartments "
            "are never merged into one downloadable database. The public website is a produced "
            "work drawing on all of them, with the attribution each licence requires. A "
            "compartment whose licence is a project LicenseRef carries license_url=null — its "
            "terms are the recorded basis named in its ATTRIBUTION.json and rows."
        ),
        "compartments": compartments,
    }
    out = public_root / LICENCE_INDEX
    out.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out


@dataclass(frozen=True)
class PrepareResult:
    """The outcome of the local public-prepare (build + partition + clean, network-free)."""

    dist: Path
    partition: PartitionResult

    def as_lines(self) -> list[str]:
        return [
            f"public build: {self.dist}  (SIG_DATA_SOURCE=export)",
            *self.partition.as_lines(),
            "public compartment clean: every public artifact carries ONE known licence, one "
            "licence per compartment (ODbL never merged with CC-BY); no UNDETERMINED/excluded/"
            "mixed-licence byte reaches a public object; LICENCES.json labels each compartment",
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
    # E2-12 / ADR-194: the publish-time attribution gate at export preparation —
    # an attribution-required public row carrying no credit refuses the build
    # before LICENCES.json or any sync can bless it.
    assert_attribution_complete(pub)
    write_licence_index(pub, registry=registry)
    assert_public_clean(pub, registry=registry)  # the index adds no data byte — re-proven
    assert_site_matches_partition(dist, pub)
    return PrepareResult(dist=dist, partition=partition)


def assert_site_matches_partition(dist: Path, public_root: Path) -> None:
    """The public SITE may serve no licence compartment the public PARTITION withholds.

    The site is built from the full export, so a compartment moved to restricted (e.g. by a
    recorded ``export_disposition = "excluded"`` row, the ADR-106 rollback path) must also leave
    the site: every per-compartment tile archive in ``dist/tiles/`` must be a PUBLIC artifact of
    the partition (``web/tiles/<name>``), or this raises :class:`CompartmentLeak` before any sync.
    """
    manifest = read_manifest(public_root)
    public_paths = {str(a["path"]) for a in manifest.get("artifacts", [])}
    tiles_dir = dist / "tiles"
    leaks = (
        [
            f"tiles/{p.name}"
            for p in sorted(tiles_dir.glob("*-sites.pmtiles"))
            if f"{_WEB_DIR}/tiles/{p.name}" not in public_paths
        ]
        if tiles_dir.is_dir()
        else []
    )
    if leaks:
        raise CompartmentLeak(
            "the public site would serve compartments the public partition withholds:\n  "
            + "\n  ".join(leaks)
        )


# --- 3. the one allow-listed publish path (P34.10, SIG-OPS-003/004) -----------
#
# `sig-ops publish-web` is the ONLY way public bytes reach a public bucket — the
# durable fix for the hand-typed `gcloud storage rsync --delete-unmatched` that
# bypassed the build and re-published /curate/** (S0 F-02, G1 §3.2). The command
# composes: prepare (export build + compartment partition) → allow-list and
# content assertions → release record → ONE sync → post-sync absence probes.
# The sync never deletes the release trees (`r/`, `releases/`, `entity/`,
# `conf/` plus the release-pipeline root objects) — a web redeploy can retire a
# stale site page but can never touch an immutable release namespace.

#: The committed allow-list (data, not code). ``--allowlist`` /
#: ``SIG_PUBLIC_ROUTES`` override it; neither is ever auto-created.
DEFAULT_ALLOWLIST_PATH = Path("ops") / "public_routes.toml"

#: The release record the publish writes into the synced tree (SIG-OPS-004).
RELEASE_RECORD = ".sig-release.json"
RELEASE_RECORD_SCHEMA = "sig/web-release-record/1.0.0"

#: Namespaces the site sync NEVER deletes — the immutable release trees owned by
#: the release pipeline (G2 0b: ``r/``, ``releases/<pub>/``, ``entity/``,
#: ``conf/``). ``releases/`` is protected wholesale (superset of
#: ``releases/<pub>/``) so the sync can never remove ``releases/index.html``,
#: which exactly one generator owns (the release tool, P35.53).
PROTECTED_PREFIXES: tuple[str, ...] = ("r/", "releases/", "entity/", "conf/")

#: Release-pipeline root objects that are not under a protected prefix but are
#: never web-build output: the compat index and the per-release ``release.json``
#: that SIG-REL-009 links every page to. Protected by name, like the prefixes.
PROTECTED_NAMES: frozenset[str] = frozenset({"compat_index.json", "release.json"})

#: The top-level entries a staged RELEASE tree (--release-tree) may carry — the
#: namespaces the release pipeline owns. Anything else (e.g. a staged
#: ``index.html`` that would clobber the site root) refuses the publish.
RELEASE_TREE_TOP_LEVEL: frozenset[str] = frozenset(
    {"r", "releases", "entity", "conf", "compat_index.json", "release.json"}
)


def is_protected_object(name: str) -> bool:
    """True iff the bucket object ``name`` is a release-tree byte the site sync
    must never delete or overwrite (the immutable namespaces + the release
    pipeline's root objects)."""
    return name in PROTECTED_NAMES or any(name.startswith(p) for p in PROTECTED_PREFIXES)


@dataclass(frozen=True)
class PublicAllowlist:
    """The parsed ``ops/public_routes.toml``.

    ``top_level`` is the set of top-level entries a built tree may carry;
    ``required`` is the subset every public build MUST emit (conditional
    entries — the reserved 404 page, the publish's own release record,
    export-mode-only ``tiles/`` — are listable but not required);
    ``denied_routes`` are the never-public routes probed absent post-publish.
    """

    top_level: frozenset[str]
    denied_routes: tuple[str, ...]
    required: frozenset[str] = frozenset()

    def as_json(self) -> dict[str, Any]:
        return {
            "top_level": sorted(self.top_level),
            "required": sorted(self.required),
            "denied_routes": list(self.denied_routes),
        }


def load_allowlist(path: str | Path | None = None) -> PublicAllowlist:
    """Parse the committed allow-list (``ops/public_routes.toml``).

    Resolution order: explicit ``path`` → ``$SIG_PUBLIC_ROUTES`` →
    ``ops/public_routes.toml`` relative to the repo root. An explicitly
    chosen path (argument or env) that does not exist fails LOUD — a mistyped
    path must never silently substitute the default. Fails loud on a missing
    file or a malformed/empty ``top_level`` set — an absent allow-list must
    never read as "everything is allowed".
    """
    candidates: list[Path] = []
    if path:
        candidates.append(Path(path))
    env_path = os.environ.get("SIG_PUBLIC_ROUTES", "").strip()
    if env_path:
        candidates.append(Path(env_path))
    candidates.append(Path(__file__).resolve().parents[3] / DEFAULT_ALLOWLIST_PATH)
    if len(candidates) > 1 and not candidates[0].is_file():
        raise PublishError(
            f"the allow-list {candidates[0]} does not exist — refusing to "
            "silently publish against a substitute (SIG-OPS-003)."
        )
    resolved = next((c for c in candidates if c.is_file()), candidates[-1])
    if not resolved.is_file():
        raise PublishError(
            f"the committed allow-list is absent: {resolved}. Nothing may be "
            "published without it (SIG-OPS-003)."
        )
    with resolved.open("rb") as fh:
        doc = tomllib.load(fh)
    top = doc.get("allowlist", {}).get("top_level", [])
    if not top:
        raise PublishError(f"{resolved} carries an empty [allowlist].top_level — refusing.")
    denied = tuple(str(d.get("path", "")) for d in doc.get("denied", []))
    if any(not d.startswith("/") or not d.endswith("/") for d in denied):
        raise PublishError(
            f"{resolved}: every [[denied]] path must be a route — leading and "
            f"trailing '/' required (got {denied!r})."
        )
    required = frozenset(str(e) for e in doc.get("allowlist", {}).get("required", []))
    if required - frozenset(str(e) for e in top):
        raise PublishError(
            f"{resolved}: [allowlist].required names entries absent from "
            f"top_level: {sorted(required - frozenset(str(e) for e in top))}"
        )
    return PublicAllowlist(
        top_level=frozenset(str(e) for e in top),
        denied_routes=denied,
        required=required,
    )


def _top_level_entries(dist: Path) -> set[str]:
    return {p.name for p in dist.iterdir()}


def _iter_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*") if p.is_file())


def assert_allowlisted_tree(dist: Path, allowlist: PublicAllowlist) -> None:
    """Refuse a built tree holding any top-level entry off the allow-list.

    This is the check the hand rsync bypassed: ``publish-web`` exits non-zero
    when ``dist`` contains a directory or file not committed to
    ``ops/public_routes.toml`` — a planted ``curate/``, an unlisted namespace,
    or any new route nobody approved for the public surface.
    """
    violations: list[str] = []
    present = _top_level_entries(dist)
    for entry in sorted(present):
        if entry not in allowlist.top_level:
            violations.append(f"{entry}/  (not on the committed allow-list)")
    # …and the other direction: a route the allow-list REQUIRES that the build
    # did not emit means a silently broken build — refuse it the same way.
    for entry in sorted(allowlist.required - present):
        violations.append(f"{entry}/  (required by the allow-list but not built)")
    if violations:
        raise PublishError(
            "publish refused — the built tree holds top-level entries that are "
            "not on the committed allow-list (ops/public_routes.toml, "
            "SIG-OPS-003):\n  " + "\n  ".join(violations)
        )


#: The curation shell's internal-layout marker (``CurateLayout`` renders it on
#: every /curate/** page): a built public page carrying it was produced from an
#: internal layout — refused regardless of which route it sits on.
_CURATE_BANNER = 'data-testid="curate-auth-banner"'

#: A form action pointed at a loopback host: the curation app's write endpoint
#: is ``http://127.0.0.1:8001`` (loopback-only by design, ADR-068) — such an
#: action on a public page means internal form markup leaked into the tree.
_LOOPBACK_ACTION = re.compile(
    r"""(?:action|formaction)\s*=\s*["']https?://(?:localhost|127\.0\.0\.1|0\.0\.0\.0|\[?::1\]?)[:"'/]""",
    re.IGNORECASE,
)

#: A demo-fixture marker: a URL (href/src/action) whose path contains a
#: ``demo_`` segment, or a rendered generated-task descriptor whose fields carry
#: a ``demo_`` id (the fixtures' demonstrator absences are ``demo_*``).
_DEMO_HREF = re.compile(r"""(?:href|src|action)\s*=\s*["'][^"']*/demo_[^"']*["']""", re.IGNORECASE)
_DEMO_TASK_FIELD = re.compile(r'data-testid="task-field-[^"]+"[^>]*>\s*demo_', re.IGNORECASE)


def assert_public_tree_content(dist: Path) -> None:
    """Refuse a tree carrying internal/demo markers (G1 §3.2 item 3).

    Scans every ``.html`` in the tree for the curation-shell banner
    (``data-testid="curate-auth-banner"`` — any internal-layout page, wherever
    it sits), a form action bound to a loopback host (the curation app's write
    endpoint), and ``demo_`` task markers — in page markup AND in path segments
    (a ``task/new/demo_*/index.html`` route is refused by name).
    """
    violations: list[str] = []
    for path in _iter_files(dist):
        rel = path.relative_to(dist).as_posix()
        if any(part.startswith("demo_") for part in path.relative_to(dist).parts):
            violations.append(f"{rel}: path carries a demo_ segment (demo fixture content)")
            continue
        if path.suffix != ".html":
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if _CURATE_BANNER in text:
            violations.append(
                f'{rel}: carries data-testid="curate-auth-banner" — a page built '
                "from an internal curation layout can never ship public"
            )
        for m in _LOOPBACK_ACTION.finditer(text):
            violations.append(
                f"{rel}: form action on a loopback host ({m.group(0)[:60]}…) — the "
                "loopback-only curation write path must never ship public"
            )
        for m in _DEMO_TASK_FIELD.finditer(text):
            violations.append(
                f"{rel}: a generated-task descriptor carries a demo_ id "
                f"({m.group(0)[:80]}…) — demo fixture content is never publishable"
            )
        for m in _DEMO_HREF.finditer(text):
            violations.append(f"{rel}: links a demo_ route ({m.group(0)[:60]}…)")
    if violations:
        raise PublishError(
            "publish refused — the built tree carries internal/demo markers "
            "(SIG-OPS-003):\n  " + "\n  ".join(violations)
        )


#: The committed copy batches (B-2 / P34.11): every sentence a public page renders
#: under a ``data-copy`` marker is a sha256-pinned row in a ``batch-*.md`` file
#: under this directory. P34.17 makes republish #1 refuse to ship a pending
#: sentence — the publish is the last line that can enforce the batch-
#: confirmation rule in code (GATE-G4 / copy batch #1). P34.20: the gate scans
#: EVERY committed batch, not just the first — a pending row in batch-02+ is
#: ``pending`` (refused at --apply), never a false ``untracked`` report.
DEFAULT_COPY_BATCH_DIR = Path("docs/build/reports/copy-batches")

#: ``data-copy="HO-02 HO-03"`` — the whitespace-separated row ids an element binds.
_DATA_COPY_ATTR = re.compile(r'data-copy="([^"]+)"')

#: P34.17 / R1.2 (B-8 + OP-10): the dispute page names the operator's e-mail
#: address — injected at build time via ``SIG_DISPUTE_EMAIL``, never committed —
#: and carries ``data-intake-email="unset"`` when it was not injected. A
#: publishable tree must never ship the unset marker.
_INTAKE_EMAIL_UNSET = 'data-intake-email="unset"'


def load_copy_batch_statuses(batch_path: Path) -> dict[str, str]:
    """Parse ``id → status`` from the copy-batch table (same shape the
    ``tests/unit/test_p34_11_copy_batch.py`` binding suite reads)."""
    statuses: dict[str, str] = {}
    for line in batch_path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")]
        cells = cells[1:-1] if cells and cells[0] == "" else cells
        if len(cells) != 5:
            continue
        rid, _page, _text, _sha, status = cells
        if rid in ("id", "—") or set(rid) <= {"-", ":"}:
            continue
        statuses[rid] = status
    return statuses


def check_publishable_copy(dist: Path, batch_path: Path | None = None) -> list[str]:
    """The republish-#1 copy gate (P34.17 / B-2): every ``data-copy`` sentence
    rendered in the tree must resolve to a ``confirmed`` copy-batch row, and the
    dispute page must carry an injected intake address. Returns the violations —
    a publish MUST refuse when the list is non-empty.

    Rows bound to elements that are not in this tree (governance-doc rows,
    retired-page rows) are irrelevant — only rendered sentences are checked.
    ``data-notice`` strings (N-1…N-7) are exempt by the recorded notice
    allowance.

    ``batch_path`` pins a single batch file; unset, the gate reads EVERY
    ``batch-*.md`` under the committed batches directory (P34.20 — a pending
    row in any batch still refuses ``--apply``).
    """
    batches: list[Path]
    if batch_path is not None:
        batches = [batch_path]
    else:
        batch_dir = Path(__file__).resolve().parents[3] / DEFAULT_COPY_BATCH_DIR
        batches = sorted(batch_dir.glob("batch-*.md")) if batch_dir.is_dir() else []
    if not batches or any(not b.is_file() for b in batches):
        return [
            f"no copy batch found ({batch_path or DEFAULT_COPY_BATCH_DIR}) — "
            "copy status cannot be proven"
        ]
    statuses: dict[str, str] = {}
    for batch in batches:
        statuses.update(load_copy_batch_statuses(batch))
    violations: list[str] = []
    for path in _iter_files(dist):
        if path.suffix != ".html":
            continue
        rel = path.relative_to(dist).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        for m in _DATA_COPY_ATTR.finditer(text):
            for rid in m.group(1).split():
                status = statuses.get(rid)
                if status is None:
                    violations.append(
                        f"{rel}: data-copy id {rid!r} has no row in the copy batch "
                        "(untracked sentence)"
                    )
                elif status != "confirmed":
                    violations.append(
                        f"{rel}: data-copy id {rid!r} is '{status}' in the copy batch — "
                        "only operator-confirmed sentences may ship"
                    )
        if rel == "dispute/index.html" and _INTAKE_EMAIL_UNSET in text:
            violations.append(
                f"{rel}: {_INTAKE_EMAIL_UNSET} — the dispute page was built without "
                "SIG_DISPUTE_EMAIL; it must name the operator's e-mail address (B-8)"
            )
    return violations


def tree_manifest(root: Path, *, exclude: frozenset[str] = frozenset()) -> list[tuple[str, str]]:
    """``(relpath, sha256)`` for every file under ``root`` except ``exclude``."""
    rows: list[tuple[str, str]] = []
    for path in _iter_files(root):
        rel = path.relative_to(root).as_posix()
        if rel in exclude:
            continue
        rows.append((rel, hashlib.sha256(path.read_bytes()).hexdigest()))
    return rows


def tree_digest(root: Path, *, exclude: frozenset[str] = frozenset()) -> str:
    """The published-tree digest: sha256 over the sorted ``rel<TAB>sha256``
    manifest — the tamper-evident fingerprint a release record pins."""
    h = hashlib.sha256()
    for rel, digest in tree_manifest(root, exclude=exclude):
        h.update(rel.encode("utf-8"))
        h.update(b"\t")
        h.update(digest.encode("ascii"))
        h.update(b"\n")
    return f"sha256:{h.hexdigest()}"


def write_release_record(
    dist: Path,
    *,
    release_id: str,
    git_commit: str,
    built_at: str,
    data_release: str | None = None,
    image_digests: Sequence[str] = (),
    bucket: str | None = None,
    allowlist_path: str = str(DEFAULT_ALLOWLIST_PATH),
) -> Path:
    """Write ``dist/.sig-release.json`` — the release record every publish leaves
    (SIG-OPS-004): release id, git commit, build time, image digests (none for a
    static site — the field is recorded empty so the shape never varies), and
    the published-tree digest over every synced byte except the record itself.
    """
    digest = tree_digest(dist, exclude=frozenset({RELEASE_RECORD}))
    doc = {
        "schema": RELEASE_RECORD_SCHEMA,
        "release_id": release_id,
        "git_commit": git_commit,
        "built_at": built_at,
        "tree_digest": digest,
        "tree_digest_scope": (
            "sha256 over the sorted (relpath, sha256) manifest of every file "
            f"under the published tree except {RELEASE_RECORD} itself"
        ),
        "image_digests": sorted(image_digests),
        "data_release": data_release,
        "bucket": bucket,
        "allowlist": allowlist_path,
        "publisher": "sig-ops publish-web",
    }
    out = dist / RELEASE_RECORD
    out.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out


def assert_release_tree(tree: Path) -> None:
    """A staged release tree may carry ONLY the release namespaces (``r/``,
    ``releases/``, ``entity/``, ``conf/``, ``compat_index.json``,
    ``release.json``) — a staged ``index.html`` would clobber the site root."""
    if not tree.is_dir():
        raise PublishError(f"--release-tree {tree} is not a directory")
    bad = sorted(e.name for e in tree.iterdir() if e.name not in RELEASE_TREE_TOP_LEVEL)
    if bad:
        raise PublishError(
            "publish refused — the staged release tree carries entries outside "
            f"the release namespaces ({', '.join(sorted(RELEASE_TREE_TOP_LEVEL))}):\n  "
            + "\n  ".join(bad)
        )


_CONTENT_TYPES: dict[str, str] = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".mjs": "application/javascript; charset=utf-8",
    ".json": "application/json",
    ".jsonl": "application/jsonl",
    ".txt": "text/plain; charset=utf-8",
    ".xml": "application/xml",
    ".ics": "text/calendar; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".webp": "image/webp",
    ".ico": "image/x-icon",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".pmtiles": "application/octet-stream",
    ".webmanifest": "application/manifest+json",
}


def _content_type(path: Path) -> str:
    return _CONTENT_TYPES.get(path.suffix.lower(), "application/octet-stream")


@dataclass(frozen=True)
class SyncPlan:
    """The dry-run/apply contract for one tree sync (SIG-OPS-004).

    ``uploads`` is every local object the sync writes; ``deletes`` is every
    remote object the sync removes — computed with the protected release
    namespaces already excluded, so ``deletes`` can NEVER name a byte under
    ``r/``, ``releases/``, ``entity/``, ``conf/`` or the release-pipeline root
    objects (``protected_kept`` records exactly those skips for the audit
    trail). ``remote`` is None when the destination listing was not read (a
    dry-run without a bucket handle cannot compute deletions — reported, never
    assumed empty).
    """

    uploads: tuple[str, ...]
    deletes: tuple[str, ...]
    protected_kept: tuple[str, ...]
    remote_known: bool


def plan_site_sync(local_names: Iterable[str], remote_names: Iterable[str] | None) -> SyncPlan:
    """Compute the site sync: upload every local object; delete remote objects
    the local tree no longer carries — EXCEPT the protected release namespaces,
    which the site sync may never touch (the report records them as
    ``protected_kept`` so the skip is audited, not silent)."""
    local = sorted(set(local_names))
    deletes: tuple[str, ...] = ()
    kept: tuple[str, ...] = ()
    if remote_names is not None:
        remote = set(remote_names)
        extras = remote - set(local)
        deletes = tuple(sorted(n for n in extras if not is_protected_object(n)))
        kept = tuple(sorted(n for n in remote if is_protected_object(n)))
    return SyncPlan(
        uploads=tuple(local),
        deletes=deletes,
        protected_kept=kept,
        remote_known=remote_names is not None,
    )


def sync_tree(
    bucket: GcsBucket,
    src: Path,
    *,
    delete_extras: bool,
    plan: SyncPlan | None = None,
) -> SyncPlan:
    """The ONE repository-owned sync primitive (SIG-OPS-004 — replaces every
    hand-typed ``gcloud storage rsync``).

    Uploads every file under ``src`` (content-typed by suffix). Deletion happens
    ONLY when ``delete_extras`` — the site tree — and only the remote extras the
    plan computed; the release-tree and public-export legs call this with
    ``delete_extras=False`` (append-only — a publish never deletes a release or
    compartment byte). Deletion is double-guarded: the plan never lists a
    protected name, and :func:`is_protected_object` re-checks every delete at
    the write so a plan bug cannot delete a release tree either.
    """
    local_names = [p.relative_to(src).as_posix() for p in _iter_files(src)]
    if plan is None:
        if delete_extras:
            plan = plan_site_sync(local_names, bucket.list_objects(""))
        else:
            plan = SyncPlan(
                uploads=tuple(sorted(local_names)),
                deletes=(),
                protected_kept=(),
                remote_known=False,
            )
    for path in _iter_files(src):
        rel = path.relative_to(src).as_posix()
        bucket.put_object(rel, path.read_bytes(), content_type=_content_type(path))
    if delete_extras:
        for name in plan.deletes:
            if is_protected_object(name):  # belt-and-suspenders on the plan
                raise PublishError(
                    f"sync plan would delete protected object {name!r} — refusing "
                    "(the site sync can never touch the release namespaces)"
                )
            bucket.delete_object(name)
    return plan


@dataclass(frozen=True)
class PublishWebResult:
    """The outcome record of one ``publish-web`` run (dry-run or applied)."""

    applied: bool
    dist: Path
    record: dict[str, Any]
    site_plan: SyncPlan
    release_tree: Path | None = None
    release_plan: SyncPlan | None = None
    export_tree: Path | None = None
    export_plan: SyncPlan | None = None
    absent_probes: tuple[ProbeResult, ...] = ()
    #: P34.17 / B-2: rendered sentences whose copy-batch row is missing or not
    #: ``confirmed`` (plus an unset dispute-intake address). A dry run prints
    #: them as warnings; ``--apply`` refuses.
    copy_violations: tuple[str, ...] = ()
    #: P35.5 / SIG-TRANSP-019: the zero-egress mirror leg's preflight plan
    #: (dry-run) or applied outcome lines.
    mirror_lines: tuple[str, ...] = ()

    def as_lines(self) -> list[str]:
        mode = "APPLIED" if self.applied else "DRY-RUN (nothing synced)"
        lines = [
            f"publish-web {mode}: {self.dist}",
            f"  release record: {self.dist / RELEASE_RECORD} "
            f"(release_id={self.record['release_id']}, "
            f"commit={self.record['git_commit']}, digest={self.record['tree_digest']})",
            f"  site sync: {len(self.site_plan.uploads)} uploads, "
            f"{len(self.site_plan.deletes)} deletes"
            + ("" if self.site_plan.remote_known else " (remote unlisted — deletes uncomputed)"),
            f"  protected remote objects kept: {len(self.site_plan.protected_kept)}",
        ]
        if self.release_plan is not None:
            lines.append(
                f"  release-tree sync ({self.release_tree}): "
                f"{len(self.release_plan.uploads)} uploads, deletes disabled "
                "(release namespaces are append-only)"
            )
        if self.export_plan is not None:
            lines.append(
                f"  public-export sync ({self.export_tree}): "
                f"{len(self.export_plan.uploads)} uploads, deletes disabled"
            )
        if self.absent_probes:
            ok = sum(1 for p in self.absent_probes if p.ok)
            lines.append(
                f"  absence probes: {ok}/{len(self.absent_probes)} denied routes "
                "confirmed absent (HTTP 404) on the public origins"
            )
        if self.copy_violations:
            lines.append(
                f"  copy gate: {len(self.copy_violations)} rendered sentence(s) not "
                "operator-confirmed in the copy batch — --apply would REFUSE (B-2):"
            )
            lines.extend(f"    {v}" for v in self.copy_violations[:50])
            if len(self.copy_violations) > 50:
                lines.append(f"    … and {len(self.copy_violations) - 50} more")
        lines.extend(f"  {line}" for line in self.mirror_lines)
        return lines


class MirrorOutcome(Protocol):
    """The reported result of an applied mirror leg (P35.5)."""

    def as_lines(self) -> Sequence[str]: ...


class MirrorLeg(Protocol):
    """A zero-egress mirror step attachable to the publish (P35.5/SIG-TRANSP-019).

    ``preflight()`` proves the leg before any write — it raises (refuses) or
    returns the plan lines the result reports. ``push()`` runs the leg after
    the site/release/export syncs and the absence probes, returning an outcome
    (``ops.mirror_push.MirrorPushLeg`` is the production shape).
    """

    def preflight(self) -> Sequence[str]: ...

    def push(self) -> MirrorOutcome: ...


def run_publish_web(
    *,
    dist: Path,
    apply: bool,
    bucket: GcsBucket | None = None,
    allowlist_path: str | Path | None = None,
    release_tree: Path | None = None,
    export_tree: Path | None = None,
    export_bucket: GcsBucket | None = None,
    release_id: str | None = None,
    git_commit: str | None = None,
    now: str | None = None,
    data_release: str | None = None,
    image_digests: Sequence[str] = (),
    absent_verify: Callable[[], Sequence[ProbeResult]] | None = None,
    copy_batch_path: str | Path | None = None,
    mirror: MirrorLeg | None = None,
) -> PublishWebResult:
    """The one publish path (SIG-OPS-003/004): assert → record → sync → verify.

    Order and refusal discipline: the allow-list + content assertions run
    BEFORE anything is written or synced; the release record is written into
    the tree that is synced; the site sync deletes only remote extras OUTSIDE
    the protected release namespaces; the staged release tree and the public
    export tree sync append-only (a publish never deletes a release tree or a
    compartment byte); and an applied run must prove every denied route absent
    on every resolvable public origin via ``absent_verify`` (injected by the
    CLI from ``ops/cadence.toml`` — the same probe rows the 6-hourly sweep
    carries).

    ``apply=False`` computes and prints the same plan against a remote LISTING
    (read-only) and performs no write. Without a bucket handle the plan is
    local-only (deletes reported as uncomputed).
    """
    if not dist.is_dir() or not any(dist.iterdir()):
        raise PublishError(f"publish refused — {dist} is absent or empty; build first")
    allowlist = load_allowlist(allowlist_path)
    assert_allowlisted_tree(dist, allowlist)
    assert_public_tree_content(dist)
    # P34.17 / B-2: the copy gate — every rendered `data-copy` sentence must be
    # an operator-confirmed batch row and /dispute/ must name the injected
    # address. Dry run reports the violations so the pre-go check is complete;
    # --apply refuses.
    copy_violations = tuple(
        check_publishable_copy(
            dist, Path(copy_batch_path).resolve() if copy_batch_path is not None else None
        )
    )
    if release_tree is not None:
        assert_release_tree(release_tree)
    if export_tree is not None and not export_tree.is_dir():
        raise PublishError(f"--export-tree {export_tree} is not a directory")
    # E2-12 / ADR-194: the same attribution gate the export build ran, re-applied
    # to the exact bytes about to sync — an attribution-required row with empty
    # credit refuses the publish before ANY write or sync happens.
    if export_tree is not None:
        assert_attribution_complete(export_tree)
    else:
        assert_attribution_complete(dist)

    # P35.5 / SIG-TRANSP-019: the mirror leg's preflight runs BEFORE the release
    # record is written — a mirror that is disabled, metered-egress, over its
    # push caps, or in egress alarm refuses the whole publish with nothing sent.
    mirror_lines: tuple[str, ...] = ()
    if mirror is not None:
        mirror_lines = tuple(mirror.preflight())

    commit = git_commit or _git_head()
    built_at = now or utcnow()
    rid = release_id or f"web-{built_at.replace('-', '').replace(':', '')[:15]}Z-{commit[:8]}"
    write_release_record(
        dist,
        release_id=rid,
        git_commit=commit,
        built_at=built_at,
        data_release=data_release,
        image_digests=image_digests,
        bucket=bucket.bucket if bucket else None,
    )
    record = json.loads((dist / RELEASE_RECORD).read_text(encoding="utf-8"))

    local_names = [p.relative_to(dist).as_posix() for p in _iter_files(dist)]
    remote_names: list[str] | None = None
    if bucket is not None:
        remote_names = bucket.list_objects("")
    site_plan = plan_site_sync(local_names, remote_names)
    release_plan: SyncPlan | None = None
    export_plan: SyncPlan | None = None

    probes: tuple[ProbeResult, ...] = ()
    if apply:
        if copy_violations:
            raise PublishError(
                "publish refused — republish #1 ships only operator-confirmed "
                "copy (B-2 / copy batch #1) and a named dispute address:\n  "
                + "\n  ".join(copy_violations)
            )
        if bucket is None:
            raise PublishError(
                "publish-web --apply needs a destination bucket (--bucket, "
                "SIG_WEB_BUCKET or SIG_GCP_PROJECT) — nothing was synced"
            )
        if export_tree is not None and export_bucket is None:
            raise PublishError(
                "--export-tree needs --export-bucket (the public compartment "
                "bucket) — refusing to run a partial publish; nothing was synced"
            )
        if absent_verify is None:
            raise PublishError(
                "post-sync verification is mandatory: no absence-probe callable "
                "was provided (the CLI wires it from ops/cadence.toml)"
            )
        site_plan = sync_tree(bucket, dist, delete_extras=True, plan=site_plan)
        if release_tree is not None:
            release_plan = sync_tree(bucket, release_tree, delete_extras=False)
        if export_tree is not None:
            assert export_bucket is not None  # refused above — never partial
            export_plan = sync_tree(export_bucket, export_tree, delete_extras=False)
        probes = tuple(absent_verify())
        present = [p for p in probes if not p.ok]
        if not probes:
            raise PublishError(
                "post-sync verify ran ZERO absence probes — no public origin "
                "resolved from ops/cadence.toml; the publish cannot prove the "
                "denied routes are absent (SIG-OPS-003)"
            )
        if present:
            raise PublishError(
                "post-sync verify FAILED — denied routes are reachable on a "
                "public origin after the sync (SIG-OPS-003):\n  "
                + "\n  ".join(f"{p.service}: {p.detail}" for p in present)
            )
        if mirror is not None:
            mirror_lines = tuple(mirror.push().as_lines())
    else:
        if release_tree is not None:
            release_plan = plan_site_sync(
                (p.relative_to(release_tree).as_posix() for p in _iter_files(release_tree)),
                None,
            )
        if export_tree is not None:
            export_plan = plan_site_sync(
                (p.relative_to(export_tree).as_posix() for p in _iter_files(export_tree)),
                None,
            )

    return PublishWebResult(
        applied=apply,
        dist=dist,
        record=record,
        site_plan=site_plan,
        release_tree=release_tree,
        release_plan=release_plan,
        export_tree=export_tree,
        export_plan=export_plan,
        absent_probes=probes,
        copy_violations=copy_violations,
        mirror_lines=mirror_lines,
    )


def _git_head(repo_root: Path | None = None) -> str:
    """The checked-out commit the publish records (git, not a hand value)."""
    import subprocess

    root = repo_root or Path(__file__).resolve().parents[3]
    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=root, check=False
    )
    if proc.returncode != 0:
        raise PublishError(f"cannot resolve the git commit for the release record: {proc.stderr}")
    return proc.stdout.strip()


__all__ = [
    "DEFAULT_NATIONAL_EXPORT",
    "DEFAULT_ALLOWLIST_PATH",
    "PrepareResult",
    "PublishWebResult",
    "MirrorLeg",
    "MirrorOutcome",
    "PublicAllowlist",
    "PROTECTED_NAMES",
    "PROTECTED_PREFIXES",
    "RELEASE_RECORD",
    "RELEASE_RECORD_SCHEMA",
    "RELEASE_TREE_TOP_LEVEL",
    "SyncPlan",
    "assert_allowlisted_tree",
    "assert_public_tree_content",
    "assert_release_tree",
    "is_protected_object",
    "load_allowlist",
    "plan_site_sync",
    "run_publish_web",
    "sync_tree",
    "tree_digest",
    "tree_manifest",
    "write_release_record",
    "run_public_prepare",
    "PublishError",
    "CompartmentLeak",
    "PartitionResult",
    "public_export_dir",
    "assert_export_present",
    "build_public_web",
    "classify_compartment",
    "restriction_reason",
    "strip_non_public_web",
    "assert_site_matches_partition",
    "NON_PUBLIC_WEB_PATHS",
    "write_licence_index",
    "LICENCE_INDEX",
    "read_manifest",
    "export_watermark",
    "partition_export",
    "assert_public_clean",
]
