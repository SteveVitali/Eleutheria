# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The downloads-center artifacts (P36.50, R11-K13-TX-10b / J3 §6,
SIG-TRANSP-014/015/018, SIG-REL-015, SIG-UI-082).

Everything here is *derived from the export's own bytes* — the listing can
never describe a file the release does not carry:

* **Per-source slices** — ``by-source/<source_id>/`` holds the source's
  ``sites.csv.gz`` slice (when the source contributes site rows) and its
  **per-source statements slice** (``statements.jsonl.gz``, K9 C-8's
  claim-level statements file), plus the bundle's own ``ATTRIBUTION.txt`` /
  ``LICENCE.txt``. A source is sliced under exactly the licence compartment
  its rows landed in — the slice inherits the compartment's licence, never a
  re-computed one (SIG-LIC-004a).
* **Per-bundle ``ATTRIBUTION.txt`` / ``LICENCE.txt``** — generated from the
  same ``sig.compartment-attribution/2`` payload the JSON form carries, so the
  captured terms verbatim and the operator-accepted basis (D-J3-5 [A-8] = b —
  no withdrawal; ADR-183) are stated identically in every form. A publish with
  a required-but-empty attribution fails (SIG-TRANSP-015) — the attribution
  payload is ``None`` only for a compartment with no rows, and then no bundle
  is emitted either.
* **``SHA256SUMS`` + the pipeline minisign signature** — GNU-format checksums
  over every manifest-listed artifact plus ``manifest.json`` itself (the two
  self-referential members — ``SHA256SUMS`` and ``SHA256SUMS.minisig`` — can
  never list themselves). ``SHA256SUMS.minisig`` is the detached minisign
  signature over ``SHA256SUMS`` emitted when the OP-20 pipeline key is
  provisioned (``SIG_RELEASE_MINISIGN_SECRET``); the public key file
  ``sig-release.minisign.pub`` ships beside it. When the key is not
  provisioned the export declares ``unsigned`` with the reason — never a
  fabricated signature, never a silent omission.
* **``sig.download-listing/1``** — the machine-readable listing ``/data/`` and
  the immutable ``/releases/<pub>/data/`` page render: every downloadable file
  with licence, attribution, size, row count, sha256 and format, grouped by
  compartment / source slice / release-integrity / transparency-metadata
  (SIG-TRANSP-014). Download links name the R2 host's content-hash keys
  (A-3 = a — ``files.surveillancegraph.org/<release_id>/<path>.<sha12>``, the
  ``r2-public`` mirror row in ``ops/mirrors.toml``); the mirror block carries
  the row's committed enabled posture verbatim.
"""

from __future__ import annotations

import csv
import gzip
import io
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .manifest import PUBLICATION_BASIS, sha256_hex
from .minisign import public_key_for_secret, sign_detached, verify_detached
from .push import content_hash_key

# --------------------------------------------------------------------------- #
# Constants                                                                    #
# --------------------------------------------------------------------------- #

#: The listing document schema (manifest ``schema`` + the doc's own key).
SCHEMA = "sig.download-listing/1"
#: The verify report schema.
VERIFY_SCHEMA = "sig.download-verify/1"
#: The per-source extract package schema (``by-source/<id>/datapackage.json``,
#: P36.68 / UX9-4 — the per-source Frictionless resource list SIG-TRANSP-032
#: requires beside the extract files themselves).
SOURCE_EXTRACT_SCHEMA = "sig.source-extract/1"
#: The Frictionless data-package profile the per-source package declares.
DATAPACKAGE_PROFILE = "https://datapackage.org/profiles/2.0/datapackage.json"

SHA256SUMS_FILE = "SHA256SUMS"
MINISIG_FILE = "SHA256SUMS.minisig"
PUBKEY_FILE = "sig-release.minisign.pub"
MANIFEST_FILE = "manifest.json"

#: The committed mirror registry row the download links resolve against
#: (P35.5 / D-J3-4, A-3 = a — the R2 host).
MIRROR_REGISTRY = Path(__file__).resolve().parents[3] / "ops" / "mirrors.toml"
MIRROR_ROW = "r2-public"
MIRROR_BASE_FALLBACK = "https://files.surveillancegraph.org"

#: The ADR-183 operator-accepted basis — the adopted sentence, verbatim
#: (D-J3-5 [A-8] = b: no withdrawal; each bundle states the captured terms and
#: the operator-accepted basis).
ADR_183_BASIS = (
    "I accept the express-terms risk for all ≈8,088 currently public rows, "
    "including the non-commercial ones; A-9 applies to new sources only."
)

#: The "changes made by SIG" notice CC-BY-family re-users must carry (J3 §6.7 —
#: rendered once here, never per row).
SIG_CHANGES_NOTICE = (
    "Changes made by SIG: source records were normalised, licence-sliced and "
    "re-serialised; upstream bytes are not republished here."
)

#: Members beside the manifest that the listing names but does not checksum —
#: a file cannot hash itself.
_SELF_NAMED = (SHA256SUMS_FILE, MINISIG_FILE, PUBKEY_FILE)

# P37.4a (SIG-SEC-006): declared sidecars that ARE listed in SHA256SUMS without
# being manifest members — the deterministic CycloneDX SBOM is emitted beside
# the sums and verified by the same signature.
SBOM_FILE = "sbom.cdx.json"
SBOM_MINISIG_FILE = "sbom.cdx.json.minisig"
SIDECAR_SUMS_MEMBERS = (SBOM_FILE,)


class DownloadError(RuntimeError):
    """A downloads contract violation — always loud, never partial."""


# --------------------------------------------------------------------------- #
# The mirror row (committed registry posture, never re-decided here)          #
# --------------------------------------------------------------------------- #


def mirror_posture(registry_path: Path | str | None = None) -> dict[str, Any]:
    """The ``r2-public`` mirror row projected into the listing.

    Reads ``ops/mirrors.toml`` (the committed registry — the listing reports
    the row's own ``enabled``/``status`` verbatim, never a re-derived state).
    Absent row ⇒ the base URL fallback with ``enabled: false`` recorded.
    """
    path = Path(registry_path) if registry_path else MIRROR_REGISTRY
    row: dict[str, Any] = {}
    if path.is_file():
        import tomllib

        for entry in tomllib.loads(path.read_text(encoding="utf-8")).get("mirror", []):
            if entry.get("name") == MIRROR_ROW:
                row = dict(entry)
                break
    return {
        "provider": str(row.get("provider") or "cloudflare-r2"),
        "base_url": str(row.get("url") or MIRROR_BASE_FALLBACK),
        "bucket": str(row.get("bucket") or ""),
        "enabled": bool(row.get("enabled", False)),
        "status": str(row.get("status") or "not provisioned"),
        "note": (
            "Download links name the R2 host's content-hash keys; the mirror "
            "row's committed enabled posture is reported verbatim — objects "
            "resolve once the publish leg has pushed them."
        ),
    }


def download_href(mirror_base: str, release_id: str, path: str, sha256: str) -> str:
    """The public URL of a download — the R2 host's content-hash key (A-3 = a)."""
    return f"{mirror_base.rstrip('/')}/{content_hash_key(release_id, path, sha256)}"


# --------------------------------------------------------------------------- #
# ATTRIBUTION.txt / LICENCE.txt per bundle                                   #
# --------------------------------------------------------------------------- #


def attribution_txt(payload: Mapping[str, Any], *, title: str) -> bytes:
    """The ``ATTRIBUTION.txt`` form of a ``sig.compartment-attribution/2`` payload.

    Renders the SAME payload the JSON form carries — every source named with
    its registry attribution, terms URL and row count; express-terms sources
    additionally carry the captured terms verbatim + the operator-accepted
    basis (ADR-183, D-J3-5 [A-8] = b). Required-but-empty attribution fails
    upstream at the gate (SIG-TRANSP-015); a ``None`` payload is a bug here.
    """
    if payload is None:
        raise DownloadError(f"ATTRIBUTION.txt refuses an empty payload for {title!r}")
    lines = [
        f"# ATTRIBUTION — {title}",
        "",
        f"Licence: {payload['license']}",
        "Licence URL: "
        + (payload.get("license_url") or "project LicenseRef — see per-source terms/basis below"),
        f"Attribution required: {'yes' if payload.get('attribution_required') else 'no'}",
        "",
        f"Publication basis: {payload.get('publication_basis') or PUBLICATION_BASIS}",
        "",
        str(payload.get("note") or ""),
        "",
        SIG_CHANGES_NOTICE,
        "",
        "## Sources",
    ]
    for src in payload.get("sources") or []:
        lines.append("")
        lines.append(f"- {src.get('name') or src['source_id']} ({src['source_id']})")
        lines.append(f"  rows: {src.get('rows')}")
        lines.append(f"  licence: {src.get('license')}")
        lines.append(
            f"  attribution required: {'yes' if src.get('attribution_required') else 'no'}"
        )
        if src.get("attribution"):
            lines.append(f"  attribution: {src['attribution']}")
        if src.get("terms_url"):
            lines.append(f"  terms: {src['terms_url']}")
        if src.get("rights_ids"):
            lines.append(f"  rights records: {', '.join(src['rights_ids'])}")
        if src.get("captured_terms_verbatim"):
            lines.append(f"  captured terms (verbatim): {src['captured_terms_verbatim']}")
            lines.append(f"  captured terms evidence: {src.get('captured_terms_evidence')}")
            lines.append(f"  publication basis: {src.get('publication_basis')}")
            lines.append(f"  operator-accepted basis (ADR-183): {ADR_183_BASIS}")
    return ("\n".join(lines) + "\n").encode("utf-8")


def licence_txt(license_id: str, license_url: str | None, *, compartment: str) -> bytes:
    """The ``LICENCE.txt`` for one bundle — the compartment licence + pointer."""
    lines = [
        f"# LICENCE — {compartment}",
        "",
        f"The contents of this bundle are licensed under {license_id}.",
    ]
    if license_url:
        lines += ["", f"Licence text: {license_url}"]
    else:
        lines += [
            "",
            "This is a project LicenseRef — the terms are stated per source in "
            "ATTRIBUTION.txt (captured terms verbatim) together with the "
            "recorded publication basis.",
        ]
    lines += [
        "",
        "Per-source attribution, terms URLs and any captured terms live in "
        "ATTRIBUTION.txt beside this file.",
        "",
    ]
    return ("\n".join(lines)).encode("utf-8")


# --------------------------------------------------------------------------- #
# Per-source slices (sites where applicable, statements always — K9 C-8)      #
# --------------------------------------------------------------------------- #


def _gzip(data: bytes) -> bytes:
    """Deterministic gzip (mtime=0, no filename — byte-stable, SIG-EXPORT-003)."""
    buf = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=buf, mtime=0) as fh:
        fh.write(data)
    return buf.getvalue()


def _csv_slice_on(csv_bytes: bytes, field: str, values: frozenset[str]) -> tuple[bytes, int]:
    """Filter a ``sites.csv`` stream to rows whose ``field`` is in ``values``."""
    text = csv_bytes.decode("utf-8")
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        return b"", 0
    header = rows[0]
    try:
        idx = header.index(field)
    except ValueError as exc:
        raise DownloadError(f"sites.csv carries no {field} column") from exc
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(header)
    kept = 0
    for row in rows[1:]:
        if idx < len(row) and row[idx] in values:
            writer.writerow(row)
            kept += 1
    return out.getvalue().encode("utf-8"), kept


def _csv_slice(csv_bytes: bytes, source_ids: frozenset[str]) -> tuple[bytes, int]:
    """Filter a ``sites.csv`` stream to the given slice source ids."""
    return _csv_slice_on(csv_bytes, "source_id", source_ids)


def _jsonl_slice_on(jsonl_bytes: bytes, field: str, values: frozenset[str]) -> tuple[bytes, int]:
    """Filter a ``statements.jsonl`` stream to rows whose ``field`` is in ``values``."""
    kept: list[bytes] = []
    for line in jsonl_bytes.splitlines(keepends=True):
        if not line.strip():
            continue
        if str(json.loads(line).get(field)) in values:
            kept.append(line)
    return b"".join(kept), len(kept)


def _jsonl_slice(jsonl_bytes: bytes, source_ids: frozenset[str]) -> tuple[bytes, int]:
    """Filter a ``statements.jsonl`` stream to the given slice source ids."""
    return _jsonl_slice_on(jsonl_bytes, "source_id", source_ids)


def slice_source_ids(rows: Sequence[Mapping[str, Any]]) -> dict[str, frozenset[str]]:
    """``base source id`` → the slice ``source_id``s emitted for it.

    A source sliced under two rights records appears once per record
    (``source@rights_id`` — SIG-LIC-004a); the per-source bundle groups the
    base id's slices under one ``by-source/<base>/`` directory.
    """
    out: dict[str, set[str]] = {}
    for row in rows:
        sid = str(row.get("source_id") or "")
        base = sid.split("@", 1)[0]
        out.setdefault(base, set()).add(sid)
    return {k: frozenset(v) for k, v in out.items()}


def source_attribution_payload(
    source_id: str,
    compartment_payload: Mapping[str, Any],
) -> dict[str, Any] | None:
    """The per-source slice of a compartment attribution payload."""
    sources = [
        s
        for s in compartment_payload.get("sources") or []
        if str(s.get("source_id")) == source_id
        or source_id in (s.get("slice_source_ids") or [])
        or str(s.get("source_id")) == source_id.split("@", 1)[0]
    ]
    if not sources:
        return None
    return {**dict(compartment_payload), "sources": sources}


def source_datapackage(
    source_id: str,
    files: Mapping[str, bytes],
    counts: Mapping[str, int],
    *,
    license_id: str,
    license_url: str | None,
    compartment: str,
    release_id: str | None = None,
) -> bytes:
    """The ``by-source/<source_id>/datapackage.json`` — the per-source
    Frictionless package (P36.68 / UX9-4, SIG-TRANSP-032).

    One resource per emitted file, each carrying its format, byte size and
    sha256 — the extract's identity is its own bytes', never a parallel
    derivation. ``license_url`` falls back to the LicenseRef posture the
    ATTRIBUTION.txt states (a LicenseRef has no canonical URL).
    """
    resources: list[dict[str, Any]] = []
    for path in sorted(files):
        data = files[path]
        name = path.rsplit("/", 1)[-1]
        res: dict[str, Any] = {
            "name": name,
            "path": name,
            "format": _format_of(path),
            "mediatype": {
                "csv.gz": "text/csv",
                "jsonl.gz": "application/x-ndjson",
                "json": "application/json",
                "txt": "text/plain",
            }.get(_format_of(path), "application/octet-stream"),
            "bytes": len(data),
            "sha256": sha256_hex(data),
        }
        if counts.get(path) is not None:
            res["rows"] = int(counts[path])
        if name == "statements.jsonl.gz":
            res["schema"] = "sig.statement/1"
        resources.append(res)
    doc: dict[str, Any] = {
        "schema": SOURCE_EXTRACT_SCHEMA,
        "profile": "data-package",
        "$schema": DATAPACKAGE_PROFILE,
        "name": f"sig-source-{source_id}",
        "title": f"SIG per-source extract — {source_id}",
        "source_id": source_id,
        "compartment": compartment,
        "licenses": [
            {
                "name": license_id,
                **({"path": license_url} if license_url else {}),
                "title": license_id,
            }
        ],
        "resources": resources,
        "note": (
            "Per-release derived extract of one source — sites where "
            "applicable, statements always (K9 C-8). sha256/bytes are "
            "computed over the emitted files themselves; registry "
            "attribution and captured terms live in ATTRIBUTION.txt "
            "beside this file (SIG-TRANSP-032)."
        ),
    }
    if release_id:
        doc["release_id"] = release_id
    from .manifest import canonical_json

    return canonical_json(doc)


def emit_source_slice(
    source_id: str,
    *,
    sites_csv: bytes | None,
    statements_jsonl: bytes | None,
    slice_ids: frozenset[str],
    attribution_payload: Mapping[str, Any] | None,
    license_id: str,
    license_url: str | None,
    compartment: str | None = None,
    release_id: str | None = None,
) -> tuple[dict[str, bytes], dict[str, int]]:
    """The ``by-source/<source_id>/`` files for one source.

    Returns ``(files, row_counts)``: the statements slice always (K9 C-8),
    the sites slice when the source contributes site rows, the per-source
    ``datapackage.json`` resource list (SIG-TRANSP-032), plus the bundle's
    ATTRIBUTION.txt / LICENCE.txt (SIG-TRANSP-015 — a required-but-empty
    attribution refuses loudly).
    """
    files: dict[str, bytes] = {}
    counts: dict[str, int] = {}
    prefix = f"by-source/{source_id}"
    if sites_csv is not None:
        data, kept = _csv_slice(sites_csv, slice_ids)
        if kept:
            files[f"{prefix}/sites.csv.gz"] = _gzip(data)
            counts[f"{prefix}/sites.csv.gz"] = kept
    if statements_jsonl is not None:
        data, kept = _jsonl_slice(statements_jsonl, slice_ids)
        if kept:
            files[f"{prefix}/statements.jsonl.gz"] = _gzip(data)
            counts[f"{prefix}/statements.jsonl.gz"] = kept
    if not files:
        return {}, {}
    payload = source_attribution_payload(source_id, attribution_payload or {})
    if payload is None:
        raise DownloadError(
            f"by-source/{source_id} has no attribution row in its compartment "
            "payload — the bundle would ship required-but-empty attribution "
            "(SIG-TRANSP-015)"
        )
    files[f"{prefix}/ATTRIBUTION.txt"] = attribution_txt(
        payload, title=f"per-source slice {source_id}"
    )
    files[f"{prefix}/LICENCE.txt"] = licence_txt(license_id, license_url, compartment=source_id)
    files[f"{prefix}/datapackage.json"] = source_datapackage(
        source_id,
        files,
        counts,
        license_id=license_id,
        license_url=license_url,
        compartment=compartment or source_id,
        release_id=release_id,
    )
    return files, counts


# --------------------------------------------------------------------------- #
# Per-dossier slices (P36.53 / K5 §6, SIG-DSRC-007) — country/admin-1 only     #
# --------------------------------------------------------------------------- #

#: D-K5-1 [B-22] "as recommended": country and admin-1 dossier slices are
#: materialised; county/place dossiers slice the national files by the
#: statements' placement columns (the recipe block) — never a materialised
#: file (≈4× the national bytes, R-K5-4). ``unplaced`` is materialised too —
#: the data-quality report's own rows are a named, downloadable set.
DOSSIER_SLICE_LEVELS: frozenset[str] = frozenset({"country", "state_province"})
DOSSIER_SLICE_DIR = "by-dossier"


def _base_source_id(source_id: str) -> str:
    """The base source id of a (possibly rights-suffixed) slice key."""
    return source_id.split("@", 1)[0]


def dossier_attribution_payload(
    source_ids: frozenset[str],
    compartment_payload: Mapping[str, Any],
) -> dict[str, Any] | None:
    """The dossier-compartment slice of a compartment attribution payload.

    ``source_ids`` are the dossier's contributing BASE source ids inside this
    compartment. A contributing source with no attribution row fails loudly —
    the bundle would otherwise ship required-but-empty attribution
    (SIG-TRANSP-015); returns ``None`` only for a dossier with no
    contributing source in this compartment (no bundle is emitted then).
    """
    if not source_ids:
        return None
    payload_sources = list(compartment_payload.get("sources") or [])
    missing = source_ids - {_base_source_id(str(s.get("source_id")) or "") for s in payload_sources}
    if missing:
        raise DownloadError(
            f"dossier slice: sources {sorted(missing)} have no attribution row "
            "in the compartment payload — the bundle would ship "
            "required-but-empty attribution (SIG-TRANSP-015)"
        )
    sources = [
        s
        for s in payload_sources
        if _base_source_id(str(s.get("source_id")) or "") in source_ids
        or str(s.get("source_id") or "") in source_ids
        or set(s.get("slice_source_ids") or ()) & source_ids
    ]
    return {**dict(compartment_payload), "sources": sources}


def emit_dossier_slice(
    slug_path: str,
    compartment: str,
    *,
    sites_csv: bytes | None,
    statements_jsonl: bytes | None,
    subject_ids: frozenset[str],
    source_ids: frozenset[str],
    permitted_source_ids: frozenset[str],
    attribution_payload: Mapping[str, Any] | None,
    license_id: str,
    license_url: str | None,
) -> tuple[dict[str, bytes], dict[str, int]]:
    """The ``by-dossier/<slug>/<compartment>/`` files for one dossier slice.

    ``subject_ids`` is the dossier's member-record set (the same subjects its
    ``records`` figure counts); ``source_ids`` its contributing base sources
    inside this compartment; ``permitted_source_ids`` the compartment's own
    gated slice sources — the ingestion/licence gates' verdict. A dossier
    naming a source outside the permitted set is REFUSED here with no
    override path: an unflipped (``ingestion_permitted=false``) or
    licence-refused source never reaches a download slice (HG-03 E4, K4
    NEW-4). Returns ``(files, row_counts)``; ``({}, {})`` when the dossier
    carries no rows in this compartment (no bundle then — never an empty one).
    """
    unpermitted = {s for s in source_ids if s not in permitted_source_ids}
    if unpermitted:
        raise DownloadError(
            f"by-dossier/{slug_path}/{compartment}: sources "
            f"{sorted(unpermitted)} are outside the compartment's gated slice "
            "set — an unflipped source never reaches a dossier download "
            "(HG-03 E4; the gate decides, the builder only enforces)"
        )
    files: dict[str, bytes] = {}
    counts: dict[str, int] = {}
    prefix = f"{DOSSIER_SLICE_DIR}/{slug_path}/{compartment}"
    if sites_csv is not None:
        data, kept = _csv_slice_on(sites_csv, "entity_id", subject_ids)
        if kept:
            files[f"{prefix}/sites.csv.gz"] = _gzip(data)
            counts[f"{prefix}/sites.csv.gz"] = kept
    if statements_jsonl is not None:
        data, kept = _jsonl_slice_on(statements_jsonl, "entity_id", subject_ids)
        if kept:
            files[f"{prefix}/statements.jsonl.gz"] = _gzip(data)
            counts[f"{prefix}/statements.jsonl.gz"] = kept
    if not files:
        return {}, {}
    payload = dossier_attribution_payload(source_ids, attribution_payload or {})
    if payload is None:
        raise DownloadError(
            f"by-dossier/{slug_path}/{compartment} has no contributing source "
            "with an attribution row — the bundle would ship "
            "required-but-empty attribution (SIG-TRANSP-015)"
        )
    files[f"{prefix}/ATTRIBUTION.txt"] = attribution_txt(
        payload, title=f"dossier {slug_path} · {compartment} compartment"
    )
    files[f"{prefix}/LICENCE.txt"] = licence_txt(
        license_id, license_url, compartment=f"dossier {slug_path} · {compartment}"
    )
    return files, counts


# --------------------------------------------------------------------------- #
# SHA256SUMS + signature                                                     #
# --------------------------------------------------------------------------- #


def sha256sums_bytes(entries: Sequence[tuple[str, str]]) -> bytes:
    """GNU ``sha256sum`` output — ``<hex>  <path>`` per line, sorted by path."""
    lines = [f"{sha}  {path}" for path, sha in sorted(entries, key=lambda e: e[0])]
    return ("\n".join(lines) + "\n").encode("utf-8")


def write_integrity_files(
    export_dir: Path | str,
    *,
    signing_secret_b64: str | None = None,
) -> dict[str, Any]:
    """Write ``SHA256SUMS`` (+ ``SHA256SUMS.minisig`` + the public key when signed).

    The checksums cover every manifest-listed artifact plus ``manifest.json``
    itself — the two self-referential members and the public key are named,
    never hashed into their own file. When the OP-20 pipeline secret is
    provisioned (``signing_secret_b64`` from ``SIG_RELEASE_MINISIGN_SECRET``)
    the detached minisign signature and its public-key document land beside
    the sums; absent, ``SHA256SUMS`` ships alone and the export honestly
    carries no signature (the listing already declares ``unsigned``).
    """
    root = Path(export_dir)
    manifest = json.loads((root / MANIFEST_FILE).read_text(encoding="utf-8"))
    entries: list[tuple[str, str]] = [
        (str(a["path"]), str(a["sha256"])) for a in manifest.get("artifacts") or []
    ]
    entries.append((MANIFEST_FILE, sha256_hex((root / MANIFEST_FILE).read_bytes())))
    for sidecar in SIDECAR_SUMS_MEMBERS:
        sidecar_path = root / sidecar
        if sidecar_path.is_file():
            entries.append((sidecar, sha256_hex(sidecar_path.read_bytes())))
    sums = sha256sums_bytes(entries)
    (root / SHA256SUMS_FILE).write_bytes(sums)
    result: dict[str, Any] = {
        "sha256sums": SHA256SUMS_FILE,
        "entries": len(entries),
        "signed": False,
    }
    if signing_secret_b64:
        sig = sign_detached(sums, signing_secret_b64)
        pub = public_key_for_secret(signing_secret_b64)
        (root / MINISIG_FILE).write_bytes(sig.encode("utf-8"))
        (root / PUBKEY_FILE).write_bytes(pub.encode("utf-8"))
        result["signed"] = True
    return result


def verify_downloads(export_dir: Path | str) -> dict[str, Any]:
    """Verify an export dir's download integrity — a ``sig.download-verify/1`` report.

    Checks every manifest artifact (bytes + sha256 on disk), every
    ``SHA256SUMS`` line (exists + matches) and the completeness of the sums
    file (every artifact + manifest.json listed), then the detached signature
    when ``SHA256SUMS.minisig`` is present (its public key must sit beside it).
    An unsigned export reports ``state: unsigned`` — never a fabricated pass.
    """
    root = Path(export_dir)
    failures: list[str] = []
    checked = 0
    manifest_path = root / MANIFEST_FILE
    artifacts: list[Mapping[str, Any]] = []
    if not manifest_path.is_file():
        failures.append("manifest.json absent")
    else:
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            artifacts = manifest.get("artifacts") or []
        except Exception as exc:  # noqa: BLE001 — corrupt bytes are a failure, never a crash
            failures.append(f"manifest.json unparseable: {exc}")
        for a in artifacts:
            p = root / str(a["path"])
            if not p.is_file():
                failures.append(f"{a['path']}: manifest-listed but absent on disk")
                continue
            data = p.read_bytes()
            if sha256_hex(data) != str(a["sha256"]):
                failures.append(f"{a['path']}: sha256 mismatch vs manifest")
            _bs = a.get("byte_size")
            if _bs is not None and len(data) != int(_bs):
                failures.append(f"{a['path']}: byte_size mismatch vs manifest")
            checked += 1

    sums_path = root / SHA256SUMS_FILE
    listed: dict[str, str] = {}
    if not sums_path.is_file():
        failures.append("SHA256SUMS absent")
    else:
        for line in sums_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            sha, sep, path = line.partition("  ")
            if not sep or len(sha) != 64:
                failures.append(f"SHA256SUMS line not '<sha256>  <path>': {line!r}")
                continue
            listed[path] = sha
            p = root / path
            if not p.is_file():
                failures.append(f"{path}: listed in SHA256SUMS but absent")
                continue
            if sha256_hex(p.read_bytes()) != sha:
                failures.append(f"{path}: sha256 mismatch vs SHA256SUMS")
        for a in artifacts:
            if str(a["path"]) not in listed:
                failures.append(f"{a['path']}: manifest artifact missing from SHA256SUMS")
        if MANIFEST_FILE not in listed:
            failures.append("manifest.json missing from SHA256SUMS")
        for extra in (
            set(listed)
            - {str(a["path"]) for a in artifacts}
            - {MANIFEST_FILE}
            - set(SIDECAR_SUMS_MEMBERS)
        ):
            failures.append(f"{extra}: in SHA256SUMS but not a manifest member")

    sig_path = root / MINISIG_FILE
    pub_path = root / PUBKEY_FILE
    signed = sig_path.is_file()
    if signed:
        if not pub_path.is_file():
            failures.append(f"{PUBKEY_FILE} absent beside {MINISIG_FILE}")
        elif sums_path.is_file() and not verify_detached(
            sums_path.read_bytes(),
            sig_path.read_text(encoding="utf-8"),
            pub_path.read_text(encoding="utf-8"),
        ):
            failures.append("SHA256SUMS.minisig does not verify against the public key")
    return {
        "schema": VERIFY_SCHEMA,
        "export_dir": str(root),
        "state": "incomplete" if failures else ("signed" if signed else "unsigned"),
        "signed": signed and not failures,
        "artifacts_checked": checked,
        "sha256sums_entries": len(listed),
        "failures": failures,
    }


# --------------------------------------------------------------------------- #
# The sig.download-listing/1 document                                        #
# --------------------------------------------------------------------------- #


def _file_kind(path: str) -> str:
    if path.startswith("by-source/"):
        return "source-slice"
    if path.startswith(f"{DOSSIER_SLICE_DIR}/"):
        return "dossier-slice"
    if path.endswith(("/ATTRIBUTION.txt", "/LICENCE.txt", "/ATTRIBUTION.json")):
        return "attribution"
    if path.startswith("web/") or path.startswith("transparency/"):
        return "transparency"
    return "compartment"


def _format_of(path: str) -> str:
    name = path.rsplit("/", 1)[-1]
    for ext in (".csv.gz", ".jsonl.gz"):
        if name.endswith(ext):
            return ext.lstrip(".")
    return name.rsplit(".", 1)[-1] if "." in name else "file"


def download_listing(
    artifacts: Sequence[Any],
    *,
    release_id: str,
    generated_at: str,
    mirror: Mapping[str, Any],
    signed: bool,
    source_names: Mapping[str, str] | None = None,
    dossier_names: Mapping[str, str] | None = None,
    publication_id: str | None = None,
    release: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """The ``sig.download-listing/1`` document over the manifest's artifacts.

    Every listed file carries licence, compartment, format, byte size, row
    count (where a row stream), sha256 and its R2-host content-hash URL. The
    two self-referential members and the listing itself are *named* in the
    integrity block, never listed (a file cannot list its own checksum).
    """
    names = dict(source_names or {})
    files: list[dict[str, Any]] = []
    for a in artifacts:

        def _g(k: str, d: Any = None, _a: Any = a) -> Any:
            return _a.get(k, d) if isinstance(_a, Mapping) else getattr(_a, k, d)

        path = str(_g("path"))
        if path == "web/downloads.json":
            continue  # the listing can never list itself
        parts = path.split("/")
        row: dict[str, Any] = {
            "path": path,
            "name": str(_g("name") or parts[-1]),
            "kind": _file_kind(path),
            "format": _format_of(path),
            "media_type": str(_g("media_type") or "application/octet-stream"),
            "compartment": _g("compartment"),
            "license": str(_g("license") or ""),
            "byte_size": int(_g("byte_size") or 0),
            "sha256": str(_g("sha256") or ""),
            "href": download_href(
                str(mirror["base_url"]), release_id, path, str(_g("sha256") or "")
            ),
        }
        if _g("row_count") is not None:
            row["row_count"] = int(_g("row_count"))
        if _g("schema") is not None:
            row["schema"] = str(_g("schema"))
        if path.startswith("by-source/") and len(parts) > 1:
            row["source_id"] = parts[1]
        if path.startswith(f"{DOSSIER_SLICE_DIR}/") and len(parts) > 3:
            # by-dossier/<slug-path>/<compartment>/<file> — the slug keeps its
            # own path segments (usa/ca/harris-county-48201).
            row["dossier_slug"] = "/".join(parts[1:-2])
            row["dossier_compartment"] = parts[-2]
        files.append(row)
    files.sort(key=lambda r: str(r["path"]))

    groups: list[dict[str, Any]] = []
    by_comp: dict[str, list[str]] = {}
    for f in files:
        comp = str(f.get("compartment") or "metadata")
        by_comp.setdefault(comp, []).append(str(f["path"]))
    for comp in sorted(by_comp):
        comp_files = by_comp[comp]
        lic = next((str(f["license"]) for f in files if f["path"] == comp_files[0]), "")
        groups.append(
            {
                "id": f"compartment:{comp}",
                "kind": "compartment",
                "title": f"{comp} compartment",
                "license": lic,
                "files": [p for p in comp_files if not p.startswith("by-source/")],
            }
        )
    source_ids = sorted(
        {
            str(f["source_id"])
            for f in files
            if f.get("kind") == "source-slice" and f.get("source_id")
        }
    )
    for sid in source_ids:
        s_files = [str(f["path"]) for f in files if f.get("source_id") == sid]
        comp = next((str(f["compartment"]) for f in files if f.get("source_id") == sid), "")
        lic = next((str(f["license"]) for f in files if f.get("source_id") == sid), "")
        groups.append(
            {
                "id": f"source:{sid}",
                "kind": "source",
                "title": names.get(sid) or sid,
                "source_id": sid,
                "compartment": comp,
                "license": lic,
                "files": s_files,
            }
        )
    dossier_slugs = sorted(
        {
            str(f["dossier_slug"])
            for f in files
            if f.get("kind") == "dossier-slice" and f.get("dossier_slug")
        }
    )
    names = dict(dossier_names or {})
    for slug in dossier_slugs:
        d_files = [str(f["path"]) for f in files if f.get("dossier_slug") == slug]
        comp = next(
            (str(f["dossier_compartment"]) for f in files if f.get("dossier_slug") == slug),
            "",
        )
        lic = next((str(f["license"]) for f in files if f.get("dossier_slug") == slug), "")
        groups.append(
            {
                "id": f"dossier:{slug}",
                "kind": "dossier",
                "title": names.get(slug) or slug,
                "dossier_slug": slug,
                "compartment": comp,
                "license": lic,
                "files": d_files,
            }
        )
    release_files = [
        str(f["path"])
        for f in files
        if "/" not in str(f["path"]) or str(f["path"]).startswith("schemas/")
    ]
    if release_files:
        groups.append(
            {
                "id": "release",
                "kind": "release",
                "title": "Release descriptor + integrity files",
                "license": "CC-BY-4.0",
                "files": release_files + [SHA256SUMS_FILE, MINISIG_FILE, PUBKEY_FILE],
            }
        )
    transparency_files = [
        str(f["path"]) for f in files if str(f["path"]).startswith(("web/", "transparency/"))
    ]
    if transparency_files:
        groups.append(
            {
                "id": "transparency",
                "kind": "transparency",
                "title": "Transparency + web-consumption metadata",
                "license": "CC-BY-4.0",
                "files": transparency_files,
            }
        )

    doc: dict[str, Any] = {
        "schema": SCHEMA,
        "release_id": release_id,
        "publication_id": publication_id,
        "generated_at": generated_at,
        "mirror": dict(mirror),
        "signature": {
            "algorithm": "minisign",
            "key": "OP-20 — the SIG release pipeline's minisign key (Secret Manager; SIG-REL-015)",
            "state": "signed" if signed else "unsigned",
            "checksum_file": SHA256SUMS_FILE,
            "signature_file": MINISIG_FILE,
            "public_key_file": PUBKEY_FILE,
            **(
                {}
                if signed
                else {"reason": "the pipeline key is not yet provisioned (OP-20 — operator action)"}
            ),
            "note": "the signature proves integrity, never approval (SIG-REL-015)",
        },
        "files": files,
        "groups": groups,
        "counts": {
            "files": len(files),
            "bytes": sum(int(f["byte_size"]) for f in files),
            "compartments": len(by_comp),
            "sources": len(source_ids),
            "dossier_slices": len(dossier_slugs),
        },
        "metadata": {
            "datapackage": "datapackage.json",
            "catalog": "catalog.jsonld",
            "dictionary": "dictionary.json",
            "provenance": "provenance.jsonld",
            "manifest": MANIFEST_FILE,
        },
        "note": (
            "Every file is listed with the licence and attribution its "
            "bundle's ATTRIBUTION.txt/LICENCE.txt states verbatim — captured "
            "terms and the operator-accepted basis (ADR-183, no withdrawal): "
            "a bad bundle is corrected by a new release, never retracted "
            "silently. The listing names but cannot list itself or the "
            "integrity files' self-referential members."
        ),
    }
    if release is not None:
        doc["release"] = dict(release)
    return doc


__all__ = [
    "ADR_183_BASIS",
    "DownloadError",
    "MANIFEST_FILE",
    "MINISIG_FILE",
    "MIRROR_BASE_FALLBACK",
    "MIRROR_REGISTRY",
    "MIRROR_ROW",
    "PUBKEY_FILE",
    "SCHEMA",
    "SHA256SUMS_FILE",
    "SIG_CHANGES_NOTICE",
    "SOURCE_EXTRACT_SCHEMA",
    "VERIFY_SCHEMA",
    "DOSSIER_SLICE_DIR",
    "DOSSIER_SLICE_LEVELS",
    "attribution_txt",
    "dossier_attribution_payload",
    "download_href",
    "download_listing",
    "emit_dossier_slice",
    "emit_source_slice",
    "licence_txt",
    "mirror_posture",
    "sha256sums_bytes",
    "slice_source_ids",
    "source_attribution_payload",
    "source_datapackage",
    "verify_downloads",
    "write_integrity_files",
]
