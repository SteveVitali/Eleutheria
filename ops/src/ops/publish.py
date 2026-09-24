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

#: The per-compartment licence + attribution index written at the public root (ADR-106).
LICENCE_INDEX = "LICENCES.json"

#: The canonical licence URLs for the licences SIG publishes most (others resolve to SPDX).
_LICENCE_URLS: dict[str, str] = {
    "CC-BY-4.0": "https://creativecommons.org/licenses/by/4.0/",
    "CC-BY-SA-4.0": "https://creativecommons.org/licenses/by-sa/4.0/",
    "CC-BY-SA-2.0": "https://creativecommons.org/licenses/by-sa/2.0/",
    "CC0-1.0": "https://creativecommons.org/publicdomain/zero/1.0/",
    "ODbL-1.0": "https://opendatacommons.org/licenses/odbl/1-0/",
}

#: The attribution line each licence's re-user must carry. ODbL-1.0 is the OpenStreetMap
#: attribution (§42.3, SIG-GEO-013); every other compartment names SIG plus the per-row
#: source attribution the rows carry (SIG-EXPORT-006).
_ATTRIBUTION: dict[str, str] = {
    "ODbL-1.0": "© OpenStreetMap contributors (ODbL-1.0); compiled by the SIG project",
    "CC-BY-4.0": "© The SIG project — CC-BY-4.0",
}
_DEFAULT_ATTRIBUTION = (
    "The SIG project, plus the per-row source attribution each record carries (SIG-EXPORT-006)"
)


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
#: the loopback curation app). The static build emits them (the web test suite exercises
#: them), but the PUBLIC origin never carries them (P30.3).
NON_PUBLIC_WEB_PATHS: tuple[str, ...] = ("curate",)


def strip_non_public_web(dist: Path) -> list[str]:
    """Remove the non-public routes from a built ``web/dist`` before the public sync."""
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


def _licence_url(license_id: str) -> str:
    return _LICENCE_URLS.get(license_id, f"https://spdx.org/licenses/{license_id}.html")


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
                "license_url": _licence_url(license_id),
                "share_alike": bool(facts.get("share_alike", False)),
                "attribution_required": bool(facts.get("attribution_required", True)),
                "attribution": _ATTRIBUTION.get(license_id, _DEFAULT_ATTRIBUTION),
                "paths": sorted(entry["paths"]),
            }
        )
    doc = {
        "schema": "sig/public-licence-index/1.0.0",
        "release_id": manifest.get("release_id"),
        "note": (
            "Each compartment is a separate dataset under exactly one licence; compartments "
            "are never merged into one downloadable database. The public website is a produced "
            "work drawing on all of them, with the attribution each licence requires."
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
