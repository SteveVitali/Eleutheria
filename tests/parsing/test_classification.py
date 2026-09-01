# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""File classification before parsing (§24.1, SIG-PARSE-002): format sniffing, the four
mixed-archive archetypes (scanned fax, password-protected PDF, merged-header XLSX,
multi-sheet native export), the cheapest-sufficient layer each verdict selects, and the
per-member classification of a committed real records-response archive."""

from __future__ import annotations

from pathlib import Path

from parsing.classification import (
    ArchiveClassification,
    FileFormat,
    classify,
    classify_archive,
)
from parsing.layers import ExtractionLayer

_FIXTURES = Path(__file__).parent / "fixtures"
_MIXED = _FIXTURES / "records" / "mixed_response.zip"

# minimal signature payloads for the leaf-format checks
_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
_DIGITAL_PDF = b"%PDF-1.7\n<< /Type /Font /BaseFont /Helvetica >>\nstream ... endstream\n%%EOF"
_SCANNED_PDF = b"%PDF-1.7\n<< /XObject << /Im0 << /Subtype /Image /DCTDecode >> >> >>\n%%EOF"
_ENCRYPTED_PDF = b"%PDF-1.7\ntrailer << /Root 1 0 R /Encrypt 9 0 R >>\n%%EOF"


def test_leaf_formats_are_sniffed_from_signatures() -> None:
    assert classify("a.png", _PNG).file_format is FileFormat.IMAGE
    assert classify("data.json", b'{"a": 1}').file_format is FileFormat.JSON
    assert (
        classify("x", b'{"type": "FeatureCollection", "features": []}').file_format
        is FileFormat.GEOJSON
    )
    assert classify("page.html", b"<!doctype html><html></html>").file_format is FileFormat.HTML
    assert classify("d.xml", b"<?xml version='1.0'?><r/>").file_format is FileFormat.XML
    assert classify("roster.csv", b"a,b\n1,2\n").file_format is FileFormat.CSV
    assert classify("note.txt", b"just some prose here").file_format is FileFormat.PLAINTEXT
    assert classify("blob", b"\x00\x01\x02\x03\xff").file_format is FileFormat.UNKNOWN


def test_scanned_image_routes_to_ocr() -> None:
    verdict = classify("fax.png", _PNG)
    assert verdict.scanned is True
    assert verdict.recommended_layer is ExtractionLayer.OCR


def test_encrypted_pdf_is_flagged_and_routed_to_human() -> None:
    verdict = classify("protected.pdf", _ENCRYPTED_PDF)
    assert verdict.encrypted is True
    assert verdict.scanned is False
    # A password-protected PDF cannot be auto-extracted at all → human transcription.
    assert verdict.recommended_layer is ExtractionLayer.HUMAN_TRANSCRIPTION


def test_digital_pdf_routes_to_pdf_text_and_scanned_pdf_to_ocr() -> None:
    assert classify("c.pdf", _DIGITAL_PDF).recommended_layer is ExtractionLayer.PDF_TEXT
    scanned = classify("s.pdf", _SCANNED_PDF)
    assert scanned.scanned is True
    assert scanned.recommended_layer is ExtractionLayer.OCR


def test_the_verdict_is_recordable() -> None:
    row = classify("fax.png", _PNG).to_row()
    assert row["file_format"] == "image"
    assert row["scanned"] is True
    assert row["recommended_layer"] == "ocr"
    assert "notes" in row and isinstance(row["notes"], list)


def test_a_bare_zip_carries_no_single_layer() -> None:
    import io
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("a.txt", "hi")
    verdict = classify("bundle.zip", buf.getvalue())
    assert verdict.file_format is FileFormat.ZIP
    assert verdict.recommended_layer is None


def test_mixed_response_archive_is_classified_per_member() -> None:
    # SIG-PARSE-002 / AC3: a real records response is a mixed-format archive; every member
    # is classified before parsing and routed to its own cheapest sufficient layer.
    archive = classify_archive("mixed_response.zip", _MIXED.read_bytes())
    assert isinstance(archive, ArchiveClassification)
    by_name = {m.filename: m for m in archive.members}
    assert set(by_name) == {
        "roster.csv",
        "scanned_fax.tiff",
        "protected.pdf",
        "digital_contract.pdf",
        "merged_headers.xlsx",
        "native_export.xlsx",
    }

    assert by_name["roster.csv"].recommended_layer is ExtractionLayer.STRUCTURED_IMPORT

    fax = by_name["scanned_fax.tiff"]
    assert fax.file_format is FileFormat.IMAGE and fax.scanned
    assert fax.recommended_layer is ExtractionLayer.OCR

    protected = by_name["protected.pdf"]
    assert protected.encrypted
    assert protected.recommended_layer is ExtractionLayer.HUMAN_TRANSCRIPTION

    assert by_name["digital_contract.pdf"].recommended_layer is ExtractionLayer.PDF_TEXT

    merged = by_name["merged_headers.xlsx"]
    assert merged.file_format is FileFormat.XLSX
    assert merged.merged_headers is True
    assert merged.multi_sheet is False
    assert merged.recommended_layer is ExtractionLayer.STRUCTURED_IMPORT

    native = by_name["native_export.xlsx"]
    assert native.multi_sheet is True
    assert native.sheet_count == 2
    assert native.recommended_layer is ExtractionLayer.STRUCTURED_IMPORT


def test_archive_row_records_every_member() -> None:
    archive = classify_archive("mixed_response.zip", _MIXED.read_bytes())
    row = archive.to_row()
    assert row["file_format"] == "zip"
    assert len(row["members"]) == 6
