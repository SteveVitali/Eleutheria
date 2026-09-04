# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""File classification that runs *before* parsing (§24.1, SIG-PARSE-002).

Real records responses do not arrive as one clean document. They arrive as **mixed-format
ZIPs**: scanned faxes, password-protected PDFs, XLSX with merged headers, and native
exports with multiple sheets — all in one archive. Parsing the archive as if it were a
single format silently produces garbage, so SIG **classifies first and records the
verdict**, and for an archive it classifies **every member** (:func:`classify_archive`).
The verdict then selects the cheapest sufficient layer (:mod:`parsing.layers`).

Classification here is a **deterministic function of the bytes** — signature sniffing plus
the archive's own manifest (via the stdlib :mod:`zipfile`) — with no third-party parser and
no network. That keeps it testable against committed fixtures (SIG-PARSE-007) and cheap
enough to run on every ingest. It detects the four archetypes the spec calls out:

* a **scanned fax** — an image member (TIFF/JPEG/PNG) or an image-only PDF → OCR;
* a **password-protected PDF** — an ``/Encrypt`` trailer → not auto-extractable, human;
* an **XLSX with merged headers** — a ``<mergeCells>`` range in a sheet → structured, flagged;
* a **multi-sheet native export** — more than one ``xl/worksheets/sheetN.xml`` → structured.
"""

from __future__ import annotations

import io
import re
import zipfile
from dataclasses import dataclass, field, replace
from enum import StrEnum
from typing import Any

from .layers import ExtractionLayer

__all__ = [
    "FileFormat",
    "ClassificationVerdict",
    "ArchiveClassification",
    "classify",
    "classify_archive",
    "cheapest_sufficient_layer",
]


class FileFormat(StrEnum):
    """The container/format a capture is in, as classification sees it (SIG-PARSE-002)."""

    CSV = "csv"
    TSV = "tsv"
    JSON = "json"
    GEOJSON = "geojson"
    XLSX = "xlsx"
    XLS = "xls"
    PDF = "pdf"
    HTML = "html"
    XML = "xml"
    IMAGE = "image"
    ZIP = "zip"
    PLAINTEXT = "plaintext"
    UNKNOWN = "unknown"


#: Formats that are already structured — a layer-1 structured import reads them.
_STRUCTURED: frozenset[FileFormat] = frozenset(
    {
        FileFormat.CSV,
        FileFormat.TSV,
        FileFormat.JSON,
        FileFormat.GEOJSON,
        FileFormat.XLSX,
        FileFormat.XLS,
    }
)


@dataclass(frozen=True)
class ClassificationVerdict:
    """The recorded verdict for one file/member, produced before parsing (SIG-PARSE-002).

    ``file_format`` is the sniffed format; the four booleans flag the archetypes that
    change how (or whether) a value can be extracted; ``recommended_layer`` is the cheapest
    layer that suffices given the verdict (``None`` for an archive container, whose members
    carry their own verdicts). ``notes`` records the signals the verdict rests on so the
    classification is inspectable. :meth:`to_row` renders the shape recorded alongside the
    extraction.
    """

    filename: str
    file_format: FileFormat
    scanned: bool = False
    encrypted: bool = False
    merged_headers: bool = False
    multi_sheet: bool = False
    sheet_count: int | None = None
    recommended_layer: ExtractionLayer | None = None
    notes: tuple[str, ...] = ()

    def to_row(self) -> dict[str, Any]:
        """The recorded classification verdict (SIG-PARSE-002)."""
        return {
            "filename": self.filename,
            "file_format": self.file_format.value,
            "scanned": self.scanned,
            "encrypted": self.encrypted,
            "merged_headers": self.merged_headers,
            "multi_sheet": self.multi_sheet,
            "sheet_count": self.sheet_count,
            "recommended_layer": (
                None if self.recommended_layer is None else self.recommended_layer.method
            ),
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class ArchiveClassification:
    """A mixed-format archive classified per member (SIG-PARSE-002).

    ``members`` is one :class:`ClassificationVerdict` per file in the archive, in archive
    order — the per-member verdict the spec requires, because a single archive routinely
    mixes a scanned fax, an encrypted PDF, and a multi-sheet XLSX that each need a different
    layer.
    """

    filename: str
    members: tuple[ClassificationVerdict, ...] = field(default_factory=tuple)

    def to_row(self) -> dict[str, Any]:
        return {
            "filename": self.filename,
            "file_format": FileFormat.ZIP.value,
            "members": [m.to_row() for m in self.members],
        }


def cheapest_sufficient_layer(verdict: ClassificationVerdict) -> ExtractionLayer:
    """The cheapest layer that suffices for a classified file (§24.1, SIG-PARSE-001).

    Encodes the §24.1 table: structured formats read at layer 1; stable HTML/XML at layer 2;
    a digital-native PDF at layer 3 (text); a scanned image or image-only PDF at layer 5
    (OCR); prose plaintext at layer 6 (LLM-assisted, §25). A **password-protected PDF**
    cannot be auto-extracted at all, so it routes to human transcription (layer 7); an
    unrecognised format does the same — "everything else" is layer 7.
    """
    fmt = verdict.file_format
    if verdict.encrypted:
        return ExtractionLayer.HUMAN_TRANSCRIPTION
    if fmt in _STRUCTURED:
        return ExtractionLayer.STRUCTURED_IMPORT
    if fmt in (FileFormat.HTML, FileFormat.XML):
        return ExtractionLayer.SELECTOR_TEMPLATE
    if fmt is FileFormat.IMAGE:
        return ExtractionLayer.OCR
    if fmt is FileFormat.PDF:
        return ExtractionLayer.OCR if verdict.scanned else ExtractionLayer.PDF_TEXT
    if fmt is FileFormat.PLAINTEXT:
        return ExtractionLayer.LLM_ASSISTED
    return ExtractionLayer.HUMAN_TRANSCRIPTION


def classify(filename: str, data: bytes) -> ClassificationVerdict:
    """Classify one file before parsing and record the verdict (SIG-PARSE-002).

    A deterministic function of ``filename`` (its extension is a hint) and ``data`` (its
    signature bytes and, for an Office/OOXML container, its zip manifest). For an actual
    archive prefer :func:`classify_archive`, which classifies each member; calling
    :func:`classify` on a zip returns a bare ``ZIP`` verdict with no single layer.
    """
    fmt, notes = _sniff_format(filename, data)

    scanned = encrypted = merged_headers = multi_sheet = False
    sheet_count: int | None = None

    if fmt is FileFormat.IMAGE:
        scanned = True
        notes = (*notes, "image format — treated as a scanned document")
    elif fmt is FileFormat.PDF:
        encrypted = b"/Encrypt" in data
        if encrypted:
            notes = (*notes, "PDF /Encrypt trailer — password-protected, not auto-extractable")
        elif _pdf_is_image_only(data):
            scanned = True
            notes = (*notes, "PDF carries image XObjects and no font — image-only (scanned)")
    elif fmt is FileFormat.XLSX:
        sheet_count, merged_headers = _xlsx_signals(data)
        multi_sheet = sheet_count is not None and sheet_count > 1
        if multi_sheet:
            notes = (*notes, f"workbook has {sheet_count} sheets")
        if merged_headers:
            notes = (*notes, "worksheet carries a <mergeCells> range (merged headers)")

    verdict = ClassificationVerdict(
        filename=filename,
        file_format=fmt,
        scanned=scanned,
        encrypted=encrypted,
        merged_headers=merged_headers,
        multi_sheet=multi_sheet,
        sheet_count=sheet_count,
        notes=notes,
    )
    if fmt is FileFormat.ZIP:
        return verdict  # an archive container carries no single layer; see classify_archive
    return replace(verdict, recommended_layer=cheapest_sufficient_layer(verdict))


def classify_archive(filename: str, data: bytes) -> ArchiveClassification:
    """Classify every member of a mixed-format archive (SIG-PARSE-002).

    Opens the ZIP and classifies each member with :func:`classify`, preserving archive
    order — so a records response that bundles a scanned fax, an encrypted PDF, and a
    multi-sheet XLSX yields one verdict per member, each routed to its own layer. Raises
    :class:`zipfile.BadZipFile` if ``data`` is not a valid archive.
    """
    members: list[ClassificationVerdict] = []
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            members.append(classify(info.filename, zf.read(info)))
    return ArchiveClassification(filename=filename, members=tuple(members))


# --- signature sniffing -------------------------------------------------------

_IMAGE_MAGIC: tuple[bytes, ...] = (
    b"\x89PNG\r\n\x1a\n",  # PNG
    b"\xff\xd8\xff",  # JPEG
    b"II*\x00",  # little-endian TIFF (common fax container)
    b"MM\x00*",  # big-endian TIFF
    b"GIF87a",
    b"GIF89a",
)


def _sniff_format(filename: str, data: bytes) -> tuple[FileFormat, tuple[str, ...]]:
    """Sniff the format from magic bytes first, then the extension as a fallback."""
    head = data[:512]
    if data[:5] == b"%PDF-":
        return FileFormat.PDF, ("magic: %PDF",)
    if any(data.startswith(magic) for magic in _IMAGE_MAGIC):
        return FileFormat.IMAGE, ("magic: image signature",)
    if data[:4] == b"PK\x03\x04":
        # A ZIP container — but OOXML (XLSX) is a ZIP too. Look at the manifest.
        if _zip_is_xlsx(data):
            return FileFormat.XLSX, ("zip manifest: xl/workbook.xml (OOXML spreadsheet)",)
        return FileFormat.ZIP, ("magic: PK zip archive",)
    if data[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        return FileFormat.XLS, ("magic: OLE2 compound document",)

    stripped = head.lstrip()
    lowered = stripped[:64].lower()
    if lowered.startswith(b"<?xml"):
        return FileFormat.XML, ("content: <?xml prolog",)
    if lowered.startswith(b"<!doctype html") or lowered.startswith(b"<html"):
        return FileFormat.HTML, ("content: html document",)
    if stripped[:1] in (b"{", b"["):
        if b'"FeatureCollection"' in head or (b'"type"' in head and b'"geometry"' in data[:4096]):
            return FileFormat.GEOJSON, ("content: JSON with GeoJSON markers",)
        return FileFormat.JSON, ("content: JSON document",)

    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    by_ext: dict[str, FileFormat] = {
        "csv": FileFormat.CSV,
        "tsv": FileFormat.TSV,
        "json": FileFormat.JSON,
        "geojson": FileFormat.GEOJSON,
        "xlsx": FileFormat.XLSX,
        "xls": FileFormat.XLS,
        "pdf": FileFormat.PDF,
        "html": FileFormat.HTML,
        "htm": FileFormat.HTML,
        "xml": FileFormat.XML,
        "tif": FileFormat.IMAGE,
        "tiff": FileFormat.IMAGE,
        "png": FileFormat.IMAGE,
        "jpg": FileFormat.IMAGE,
        "jpeg": FileFormat.IMAGE,
        "txt": FileFormat.PLAINTEXT,
    }
    if ext in by_ext:
        return by_ext[ext], (f"extension: .{ext}",)
    if _looks_textual(data):
        return FileFormat.PLAINTEXT, ("content: printable text, no known signature",)
    return FileFormat.UNKNOWN, ("no recognised signature or extension",)


def _zip_is_xlsx(data: bytes) -> bool:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            names = set(zf.namelist())
    except zipfile.BadZipFile:
        return False
    return "xl/workbook.xml" in names or (
        "[Content_Types].xml" in names and any(n.startswith("xl/") for n in names)
    )


_SHEET_RE = re.compile(r"^xl/worksheets/sheet\d+\.xml$")


def _xlsx_signals(data: bytes) -> tuple[int | None, bool]:
    """Return ``(sheet_count, has_merged_cells)`` for an XLSX, reading only its manifest."""
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            names = zf.namelist()
            sheets = [n for n in names if _SHEET_RE.match(n)]
            merged = any(b"<mergeCells" in zf.read(n) for n in sheets)
    except zipfile.BadZipFile:
        return None, False
    return (len(sheets) if sheets else None), merged


def _pdf_is_image_only(data: bytes) -> bool:
    """Heuristic: a PDF that carries image XObjects but no embedded font is scanned.

    A digital-native PDF embeds fonts to render its text; a scanned document is a page
    image wrapped in PDF, so it carries an image XObject and no ``/Font``. This is a
    deterministic byte-level signal — good enough to route to OCR (layer 5) versus PDF text
    (layer 3); a false call is corrected downstream, never a silent drop.
    """
    return (b"/Image" in data or b"/DCTDecode" in data) and b"/Font" not in data


def _looks_textual(data: bytes, sample: int = 1024) -> bool:
    if not data:
        return False
    chunk = data[:sample]
    if b"\x00" in chunk:
        return False
    printable = sum(1 for b in chunk if b in (9, 10, 13) or 32 <= b < 127)
    return printable / len(chunk) > 0.9
