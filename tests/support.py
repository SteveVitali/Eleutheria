# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Shared constants for the SIG skeleton test suite."""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# The exact §47 repository layout (docs/2_canonical_design_spec.md §47, SIG-ENG-012).
SIG47_DIRS: tuple[str, ...] = (
    "ontology",
    "db",
    "connectors",
    "parsing",
    "resolution",
    "reconcile",
    "inference",
    "tasks",
    "api",
    "web",
    "exports",
    "orchestration",
    "policy",
    "ops",
    "docs",
    "tests",
)

# The subset of §47 that are Python workspace packages (i.e. not web/ docs/ tests/).
NON_PACKAGE_DIRS: frozenset[str] = frozenset({"web", "docs", "tests"})

# Python packages added by ADR after the frozen §47 layout. `evidence/` (the OCFL
# write-once evidence store, §17) is one: §17 needs a home and §47 names none, so
# ADR-023 adds it as a workspace member. New entries here MUST cite an ADR.
ADR_EXTENSION_PACKAGES: tuple[str, ...] = ("evidence",)

PY_PACKAGES: tuple[str, ...] = (
    tuple(d for d in SIG47_DIRS if d not in NON_PACKAGE_DIRS) + ADR_EXTENSION_PACKAGES
)


def workspace_members() -> list[str]:
    """Read the uv workspace members declared in the root pyproject.toml."""
    with (REPO_ROOT / "pyproject.toml").open("rb") as fh:
        data = tomllib.load(fh)
    return list(data["tool"]["uv"]["workspace"]["members"])


# --- Ontology (P01.1) test helpers -------------------------------------------

# Vendor/product tokens that MUST NOT appear as a schema identifier or vocab slug
# (SIG-ONTO-022/053/055; P7 "capability before vendor"). Matched against slug/name
# *tokens* (split on - . _), never as substrings, so that e.g. "ring" does not
# collide with "sharing". Vendor names may legitimately appear in a technology's
# evidence-signature strings (they are evidence, not identifiers) — those are not
# checked here.
VENDOR_TOKENS: frozenset[str] = frozenset(
    {
        "flock",
        "falcon",
        "motorola",
        "vigilant",
        "learn",
        "rekor",
        "axon",
        "genetec",
        "clearview",
        "fusus",
        "shotspotter",
        "soundthinking",
        "coplink",
        "crimetracer",
        "cellebrite",
        "graykey",
        "grayshift",
        "securus",
        "evolv",
        "gaggle",
        "goguardian",
        "predpol",
        "geofeedia",
        "palantir",
        "accurint",
        "briefcam",
        "ande",
        "rapidhit",
        "verkada",
        "ring",
        "amazon",
        "fogreveal",
        "fog",
        "dataminr",
        "sourcewell",
        "omnia",
        "spot",
    }
)


def ontology_schema_path() -> object:
    from ontology.generate import schema_path

    return schema_path()


def load_schemaview() -> object:
    """A LinkML SchemaView over the merged ontology source."""
    from linkml_runtime import SchemaView

    return SchemaView(str(ontology_schema_path()), merge_imports=True)


def load_vocab(name: str) -> dict:
    from ontology.generate import _load_vocab

    return _load_vocab(name)


def generated_dir() -> Path:
    from ontology.generate import generated_dir as _gd

    return _gd()


def load_generated_pydantic() -> object:
    """Import the generated Pydantic module from the committed artifact tree."""
    import importlib.util

    path = generated_dir() / "pydantic" / "sig_models.py"
    spec = importlib.util.spec_from_file_location("sig_generated_models", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    prior = sys.dont_write_bytecode
    sys.dont_write_bytecode = True  # do not litter the generated tree with a .pyc
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = prior
    return module


def slug_tokens(slug: str) -> set[str]:
    """Split an identifier/slug into lowercase tokens on `- . _`."""
    import re

    return {t for t in re.split(r"[-._]", slug.lower()) if t}


def minimal_pdf(pages: list[list[str]]) -> bytes:
    """A valid, deterministic one-font PDF whose pages carry ``pages`` text lines.

    Shared test fixture builder (P25.5): connectors' PDF-text extraction must be
    exercised over bytes pypdf actually parses — a hand-rolled minimal document
    (uncompressed content stream + base Helvetica) keeps the fixture small and
    byte-stable across platforms, so shadow/replay runs stay deterministic.
    """
    objects: list[bytes] = []
    kids = " ".join(f"{3 + i * 2} 0 R" for i in range(len(pages)))
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode())
    font_obj = 3 + len(pages) * 2
    for i, lines in enumerate(pages):
        page_obj = 3 + i * 2
        content_obj = page_obj + 1
        stream_lines = "BT /F1 10 Tf 50 780 Td 12 TL\n"
        for line in lines:
            esc = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            stream_lines += f"({esc}) Tj T*\n"
        stream_lines += "ET"
        stream = stream_lines.encode()
        objects.append(
            (
                "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                f"/Contents {content_obj} 0 R "
                f"/Resources << /Font << /F1 {font_obj} 0 R >> >> >>"
            ).encode()
        )
        objects.append(
            b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream"
        )
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    out = b"%PDF-1.4\n"
    offsets: list[int] = []
    for i, obj in enumerate(objects, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()
    return out
