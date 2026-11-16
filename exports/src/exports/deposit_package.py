# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The Zenodo production deposit *package* (P37.55, D-J3-9 [B-21] = yes).

D-J3-9's answered decision scopes the production Zenodo deposit (and the
torrents) to **openly licensed compartments only**, after the attribution fix
— explicitly *never* the two GL-GATE-07 risk-accepted lanes:

* ``operator_accepted`` (``LicenseRef-OperatorAccepted-DBRight``) — the
  operator's accepted sui-generis database-right basis for non-US rows;
* ``public_record`` (``LicenseRef-PublicRecord-FactualCompilation``) — the
  Feist factual-compilation basis for US rows.

Both are *publication* bases the operator carries on the site and in exports;
they are **not** deposit bases — bytes already deposited cannot be recalled
(J3 R-4), so the deposit surface is narrower than the served surface on
purpose.

This module assembles the package the operator uploads (the manual publish is
OP-19): the included compartment files, a filtered ``manifest.json``, the
``digests.json`` digest manifest (every artifact's digest, including the
excluded lanes — the citation still pins them), the Zenodo ``metadata`` block,
and a ``deposit-package.json`` descriptor recording exactly what was included
and what was excluded and why. Filtering is **allow-list, fail-closed** — a
compartment not on the declared open list cannot ship:

* an artifact whose compartment is named in ``DENIED_COMPARTMENTS`` is
  excluded (``denied-compartment``);
* an artifact whose ``license`` string *contains* a denied licence token is
  excluded (``denied-license``) — this catches any combined-licence surface
  (``CC-BY-4.0 AND … AND LicenseRef-OperatorAccepted-DBRight AND …``) that no
  compartment-name list would see;
* an artifact in an ``evidence*`` compartment is excluded **by size**
  (``evidence-bytes`` — §38.2: evidence bytes never travel to Zenodo; their
  digests do);
* an artifact whose compartment is **not in** ``OPEN_COMPARTMENTS`` is
  excluded (``not-open-compartment``) — the allow-list is the
  ``policy/data/licenses.toml`` compartments declared under a real open
  licence, plus ``metadata`` (the export's own CC-BY-4.0 descriptor docs the
  deposit is made of). This is what refuses the ``web`` surface indexes
  (derived views, not a deposit surface) and ``derived_facts``
  (``LicenseRef-DerivedFacts-Citations`` — a counsel-approved *publication*
  basis like the GL-GATE-07 lanes, not an open licence);
* an artifact missing ``path``/``license``/``compartment``/``sha256``, or a
  file whose bytes do not hash to the manifest's recorded digest, **fails the
  build** — a package that mislabels or mis-carries bytes is worse than none.

Nothing here touches the network or a credential: the package is bytes on
disk plus the metadata the upload needs. The publish is the operator's.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import dataclass
from typing import Any

from .manifest import canonical_json
from .zenodo import DepositMetadata, zenodo_metadata

PACKAGE_SCHEMA = "sig.deposit-package/1"
PACKAGE_DESCRIPTOR = "deposit-package.json"
DIGESTS_PATH = "digests.json"
MANIFEST_PATH = "manifest.json"

#: D-J3-9's never-set — the two GL-GATE-07 risk-accepted lanes, denied by both
#: compartment name and licence token (the token form also refuses any
#: combined-licence surface carrying a risk-lane token).
DENIED_COMPARTMENTS: frozenset[str] = frozenset({"operator_accepted", "public_record"})
DENIED_LICENSE_TOKENS: tuple[str, ...] = (
    "LicenseRef-OperatorAccepted-DBRight",
    "LicenseRef-PublicRecord-FactualCompilation",
)

#: The allow-list — every ``[compartments.*]`` in
#: ``policy/src/policy/data/licenses.toml`` declared under a real open licence
#: (incl. the open-data ``LicenseRef`` ODL family), plus ``metadata`` (the
#: export's own CC-BY-4.0 descriptor docs — ``datapackage.json``,
#: ``exclusions.json``, ``provenance.ttl`` — the deposit is made of them).
#: Deliberately absent: the two risk lanes, ``derived_facts`` (a publication
#: basis, not an open licence), ``web`` (derived view indexes), ``evidence*``.
OPEN_COMPARTMENTS: frozenset[str] = frozenset(
    {
        "code",
        "sig_graph",
        "osm_physical",
        "portal",
        "ontology",
        "osm_contribution",
        "dot511_ccbysa2",
        "ogc_canada2",
        "ogl_uk3",
        "ccby3",
        "ottawa_odl2",
        "peel_odl1",
        "stalbert_odl1",
        "france_licence_ouverte",
        "metadata",
    }
)


class DepositPackageError(RuntimeError):
    """A fail-closed package-build refusal (missing manifest, data gap,
    integrity mismatch)."""


@dataclass(frozen=True)
class PackageReport:
    """The accounting a package build emits (``sig.deposit-package/1``)."""

    source_export: str
    release_id: str
    concept_id: str
    package_dir: str
    included_files: int
    included_bytes: int
    included_compartments: tuple[str, ...]
    included_licenses: tuple[str, ...]
    excluded: dict[str, dict[str, object]]  # reason -> {files, compartments}
    generated_at: str

    def as_json(self) -> dict[str, object]:
        return {
            "schema": PACKAGE_SCHEMA,
            "source_export": self.source_export,
            "release_id": self.release_id,
            "concept_id": self.concept_id,
            "package_dir": self.package_dir,
            "included": {
                "files": self.included_files,
                "bytes": self.included_bytes,
                "compartments": list(self.included_compartments),
                "licenses": list(self.included_licenses),
            },
            "excluded": self.excluded,
            "generated_at": self.generated_at,
        }


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def classify_artifact(artifact: dict[str, object]) -> str | None:
    """The exclusion reason for one manifest artifact, or ``None`` = include.

    Reasons: ``denied-compartment`` / ``denied-license`` / ``evidence-bytes`` /
    ``not-open-compartment``.
    """
    compartment = artifact.get("compartment")
    license_id = artifact.get("license")
    if not isinstance(compartment, str) or not compartment:
        raise DepositPackageError(
            f"artifact {artifact.get('path')!r} has no compartment — a data gap "
            "fails the package build, never silently defaults (SIG-LIC-004a)"
        )
    if not isinstance(license_id, str) or not license_id:
        raise DepositPackageError(
            f"artifact {artifact.get('path')!r} has no license — a data gap "
            "fails the package build, never silently defaults (SIG-LIC-004a)"
        )
    if compartment in DENIED_COMPARTMENTS:
        return "denied-compartment"
    if any(token in license_id for token in DENIED_LICENSE_TOKENS):
        return "denied-license"
    if compartment.startswith("evidence"):
        return "evidence-bytes"
    if compartment not in OPEN_COMPARTMENTS:
        return "not-open-compartment"
    return None


def build_deposit_package(
    export_dir: str,
    out_dir: str,
    *,
    generated_at: str = "",
) -> PackageReport:
    """Assemble the openly-licensed-compartments deposit package.

    ``export_dir`` is a built export (``sig-exports build --out``); ``out_dir``
    receives the package: included artifact files at their manifest paths, a
    filtered ``manifest.json``, ``digests.json``, ``deposit-package.json``, and
    ``README.md`` (the OP-19 upload note). Returns the accounting report.
    """
    manifest_file = os.path.join(export_dir, MANIFEST_PATH)
    if not os.path.isfile(manifest_file):
        raise DepositPackageError(f"no manifest.json in export dir {export_dir!r}")
    with open(manifest_file, encoding="utf-8") as fh:
        manifest_doc = json.load(fh)
    artifacts = manifest_doc.get("artifacts")
    if not isinstance(artifacts, list):
        raise DepositPackageError(f"{manifest_file}: 'artifacts' is not a list")
    release_id = str(manifest_doc.get("release_id") or "")
    concept_id = str(manifest_doc.get("concept_id") or "")
    if not release_id or not concept_id:
        raise DepositPackageError(
            f"{manifest_file}: missing release_id/concept_id — not a built export"
        )

    included: list[dict[str, object]] = []
    excluded: dict[str, dict[str, Any]] = {}
    for a in artifacts:
        reason = classify_artifact(a)
        if reason is None:
            included.append(a)
        else:
            entry = excluded.setdefault(reason, {"files": 0, "compartments": set()})
            entry["files"] = int(entry["files"]) + 1
            entry["compartments"].add(str(a["compartment"]))

    if not included:
        raise DepositPackageError(
            "every artifact was excluded — the package would deposit nothing; "
            "refusing (a package that claims a release but carries no bytes is "
            "worse than none)"
        )

    os.makedirs(out_dir, exist_ok=True)
    included_bytes = 0
    for a in included:
        rel = str(a.get("path") or "")
        recorded = str(a.get("sha256") or "")
        if not rel or not recorded:
            raise DepositPackageError(
                f"artifact {rel or a.get('name')!r} lacks path/sha256 — a data gap "
                "fails the package build"
            )
        src = os.path.join(export_dir, rel)
        if not os.path.isfile(src):
            raise DepositPackageError(f"manifest path {rel!r} not on disk in {export_dir!r}")
        actual = _sha256(src)
        if actual != recorded:
            raise DepositPackageError(
                f"{rel}: bytes do not hash to the manifest's recorded sha256 — "
                "the export on disk is not what its manifest says; refusing"
            )
        dst = os.path.join(out_dir, rel)
        os.makedirs(os.path.dirname(dst) or out_dir, exist_ok=True)
        shutil.copyfile(src, dst)
        included_bytes += os.path.getsize(dst)

    # The filtered manifest keeps the export's identity and drops the excluded
    # artifact entries — the package *is* the openly-licensed subset of the
    # same release.
    filtered_manifest = dict(manifest_doc)
    filtered_manifest["artifacts"] = included
    with open(os.path.join(out_dir, MANIFEST_PATH), "w", encoding="utf-8") as fh:
        fh.write(canonical_json(filtered_manifest).decode("utf-8"))
    # The digest manifest pins every artifact — including the excluded lanes —
    # so the deposit still cites the whole release by digest (§38.2).
    with open(os.path.join(out_dir, DIGESTS_PATH), "w", encoding="utf-8") as fh:
        fh.write(
            canonical_json({str(a["path"]): str(a["sha256"]) for a in artifacts}).decode("utf-8")
        )

    included_licenses = tuple(sorted({str(a["license"]) for a in included}))
    included_compartments = tuple(sorted({str(a["compartment"]) for a in included}))
    excluded_json: dict[str, dict[str, Any]] = {
        reason: {
            "files": entry["files"],
            "compartments": sorted(entry["compartments"]),
        }
        for reason, entry in sorted(excluded.items())
    }
    metadata = zenodo_metadata(
        DepositMetadata(
            title=f"SIG dataset release {release_id}",
            version=release_id,
            concept_id=concept_id,
            licenses=included_licenses,
        )
    )
    descriptor: dict[str, Any] = {
        "schema": PACKAGE_SCHEMA,
        "release_id": release_id,
        "concept_id": concept_id,
        "source_export": os.path.abspath(export_dir),
        "generated_at": generated_at,
        "scope": (
            "openly licensed compartments only — allow-list "
            "(D-J3-9 [B-21] = yes, after the attribution fix); never "
            "operator_accepted / public_record / derived_facts / web / "
            "evidence bytes (§38.2, digests ride digests.json)"
        ),
        "zenodo_metadata": metadata,
        "included": {
            "files": len(included),
            "bytes": included_bytes,
            "compartments": list(included_compartments),
            "licenses": list(included_licenses),
        },
        "excluded": excluded_json,
    }
    with open(os.path.join(out_dir, PACKAGE_DESCRIPTOR), "w", encoding="utf-8") as fh:
        fh.write(json.dumps(descriptor, indent=2, sort_keys=True) + "\n")
    with open(os.path.join(out_dir, "README.md"), "w", encoding="utf-8") as fh:
        fh.write(_readme(descriptor))

    return PackageReport(
        source_export=os.path.abspath(export_dir),
        release_id=release_id,
        concept_id=concept_id,
        package_dir=os.path.abspath(out_dir),
        included_files=len(included),
        included_bytes=included_bytes,
        included_compartments=included_compartments,
        included_licenses=included_licenses,
        excluded=excluded_json,
        generated_at=generated_at,
    )


def _readme(descriptor: dict[str, Any]) -> str:
    inc: dict[str, Any] = descriptor["included"]
    exc: dict[str, dict[str, Any]] = descriptor["excluded"]
    excluded_lines = (
        "\n".join(
            f"- `{reason}`: {entry['files']} file(s) in {', '.join(entry['compartments'])}"
            for reason, entry in exc.items()
        )
        or "- none"
    )
    return f"""# SIG Zenodo deposit package — {descriptor["release_id"]}

Assembled by `sig-exports deposit-package` (P37.55, D-J3-9 [B-21] = yes):
**openly licensed compartments only, after the attribution fix.**

- Included: {inc["files"]} file(s) / {inc["bytes"]} bytes
  in compartments {", ".join(f"`{c}`" for c in inc["compartments"])}
  ({", ".join(f"`{lic}`" for lic in inc["licenses"])}).
{excluded_lines}
- `manifest.json` — the filtered artifact list; `digests.json` — every
  artifact's digest, the excluded lanes included (the citation still pins
  them); `deposit-package.json` — the descriptor + the Zenodo `metadata`
  block to paste or upload against.

## OP-19 — the operator's manual publish (HG-07)

The publish is irreversible and operator-run. Either:

1. web upload: create the Zenodo deposition, upload every file in this
   directory *except* `README.md`, set the metadata block from
   `deposit-package.json` → publish → record the concept + version DOIs in
   `docs/build/reports/DEPOSITS.md` (a `production` row, `10.5281/…`); or
2. CLI: `sig-exports deposit --in <this-dir> --production` with
   `SIG_ZENODO_TOKEN` set — the same fail-closed gate as the sandbox leg.

Never cite a `10.5072/…` sandbox DOI as the production concept DOI
(RISK-P21-08).
"""


__all__ = [
    "DENIED_COMPARTMENTS",
    "DENIED_LICENSE_TOKENS",
    "OPEN_COMPARTMENTS",
    "DepositPackageError",
    "PackageReport",
    "PACKAGE_SCHEMA",
    "PACKAGE_DESCRIPTOR",
    "build_deposit_package",
    "classify_artifact",
]
