# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Deterministic CycloneDX SBOM per release (P37.4a, R11-OPS-08, SIG-SEC-006).

"SBOM per release" must mean *the same bytes for the same code*: a release is
immutable (ADR-132) and reproducible (SIG-EXPORT-003), so its bill of materials
is rendered from the committed ``pylock.toml`` — the exact dependency closure
the pipeline ran — never from the ambient ``.venv`` (which drifts with the
runner). ``make sbom`` keeps the environment-introspection variant for the
operator's ad-hoc audits; the release artifact is this renderer's output.

Shape: CycloneDX 1.5 JSON, ``metadata.component`` = the workspace itself,
``components[]`` = one ``library`` entry per locked package with purl +
distribution hashes. No timestamps, no random serials — the document is a pure
function of the lockfile, so the SHA256SUMS line that covers it is stable
across rebuilds (the same property SHA256SUMS itself has).
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any
from urllib.parse import quote

SBOM_FILE = "sbom.cdx.json"
SBOM_MINISIG_FILE = "sbom.cdx.json.minisig"
DEFAULT_LOCK = "pylock.toml"
SPEC_VERSION = "1.5"


def _purl(name: str, version: str | None) -> str:
    # PEP 503 normalisation for the purl spec: lowercase, runs of -_. collapse.
    norm = "".join(
        "-" if ch in "_." else ch.lower()
        for i, ch in enumerate(name)
        if not (ch in "_-" and i > 0 and name[i - 1] in "_-.")
    )
    return f"pkg:pypi/{norm}@{quote(version, safe='')}" if version else f"pkg:pypi/{norm}"


def _component(pkg: dict[str, Any]) -> dict[str, Any]:
    name = str(pkg["name"])
    workspace = pkg.get("directory")  # uv workspace member (editable, unversioned)
    version = None if workspace else str(pkg.get("version") or "0.0.0")
    purl = _purl(name, version)
    hashes: list[dict[str, str]] = []
    seen: set[str] = set()
    dists = [pkg.get("sdist"), *(pkg.get("wheels") or [])]
    for dist in (d for d in dists if isinstance(d, dict)):
        sha = (dist.get("hashes") or {}).get("sha256")
        if sha and sha not in seen:
            seen.add(sha)
            hashes.append({"alg": "SHA-256", "content": str(sha)})
    comp: dict[str, Any] = {
        "type": "library",
        "bom-ref": purl,
        "name": name,
        "purl": purl,
        "scope": "required",
        "properties": [{"name": "sig:lockfile", "value": DEFAULT_LOCK}],
    }
    if version is not None:
        comp["version"] = version
    if workspace:
        comp["properties"].append(
            {"name": "sig:workspace_member", "value": str(workspace.get("path") or "")}
        )
    if hashes:
        comp["hashes"] = hashes
    return comp


def render_sbom(lock_path: Path | str) -> bytes:
    """Render the CycloneDX 1.5 SBOM for the committed lockfile — deterministic.

    Components sort by purl; keys sort lexically; the document carries no
    timestamp/serial so rebuilds over one lockfile are byte-identical.
    """
    lock_path = Path(lock_path)
    lock = tomllib.loads(lock_path.read_text(encoding="utf-8"))
    packages = sorted(
        (dict(p) for p in lock.get("packages") or []),
        key=lambda p: _component(p)["purl"],
    )
    doc: dict[str, Any] = {
        "$schema": "http://cyclonedx.org/schema/bom-1.5.schema.json",
        "bomFormat": "CycloneDX",
        "specVersion": SPEC_VERSION,
        "version": 1,
        "metadata": {
            "component": {
                "type": "application",
                "bom-ref": "pkg:generic/sig-workspace",
                "name": "sig-workspace",
                "description": (
                    "SIG release pipeline workspace — dependencies locked by "
                    f"{DEFAULT_LOCK} (uv export, committed)"
                ),
            },
            "tools": [{"name": "exports.sbom", "version": SPEC_VERSION}],
            "properties": [
                {"name": "sig:source", "value": DEFAULT_LOCK},
                {"name": "sig:deterministic", "value": "true"},
            ],
        },
        "components": [_component(p) for p in packages],
        "dependencies": [
            {
                "ref": "pkg:generic/sig-workspace",
                "dependsOn": [str(c["bom-ref"]) for c in (_component(p) for p in packages)],
            }
        ],
    }
    return (json.dumps(doc, indent=1, sort_keys=True) + "\n").encode("utf-8")


REPO_ROOT = Path(__file__).resolve().parents[3]


def emit_sbom(
    export_dir: Path | str,
    *,
    lock_path: Path | str | None = None,
    signing_secret_b64: str | None = None,
) -> dict[str, Any]:
    """Write ``sbom.cdx.json`` (+ ``sbom.cdx.json.minisig`` when signed).

    Returns ``{"emitted": False}`` when no lockfile resolves — an SBOM is
    skipped honestly, never rendered from the ambient environment (the
    pipeline's lock is the only deterministic input).
    """
    root = Path(export_dir)
    lock = Path(lock_path) if lock_path is not None else REPO_ROOT / DEFAULT_LOCK
    if not lock.is_file():
        return {"emitted": False, "reason": f"lockfile absent: {lock}"}
    data = render_sbom(lock)
    (root / SBOM_FILE).write_bytes(data)
    result: dict[str, Any] = {"emitted": True, "sbom": SBOM_FILE, "signed": False}
    if signing_secret_b64:
        from .minisign import public_key_for_secret, sign_detached

        (root / SBOM_MINISIG_FILE).write_text(
            sign_detached(
                data,
                signing_secret_b64,
                trusted_comment="SIG release SBOM — CycloneDX (P37.4a)",
            ),
            encoding="utf-8",
        )
        (root / "sig-release.minisign.pub").write_text(
            public_key_for_secret(signing_secret_b64), encoding="utf-8"
        )
        result["signed"] = True
    return result


__all__ = [
    "DEFAULT_LOCK",
    "SBOM_FILE",
    "SBOM_MINISIG_FILE",
    "emit_sbom",
    "render_sbom",
]
