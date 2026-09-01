# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Build the committed ``records/mixed_response.zip`` parser fixture (SIG-PARSE-007).

Real public-records responses arrive as one mixed-format archive. This script constructs a
representative one — a scanned fax, a password-protected PDF, a digital-native PDF, an XLSX
with merged headers, a multi-sheet native export, and a plain CSV — so the classifier
(:mod:`parsing.classification`) is pinned against a real archive shape rather than a mock.

The archive is a **committed binary fixture**; this builder is committed alongside it to
document its provenance and to regenerate it deterministically:

    uv run python tests/parsing/fixtures/build_mixed_response.py

``tests/parsing/test_classification.py`` asserts the per-member verdicts. Regenerating must
not change them without a corresponding, reviewed test change.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_OUT = _HERE / "records" / "mixed_response.zip"


def _tiff_bytes() -> bytes:
    """A minimal little-endian TIFF header — the shape of a scanned fax page."""
    return b"II*\x00" + b"\x08\x00\x00\x00" + b"\x00" * 32


def _encrypted_pdf() -> bytes:
    """A PDF whose trailer carries an /Encrypt reference — password-protected."""
    return (
        b"%PDF-1.7\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"trailer\n<< /Root 1 0 R /Encrypt 9 0 R /ID [<00><00>] >>\n"
        b"%%EOF\n"
    )


def _digital_pdf() -> bytes:
    """A digital-native PDF: it embeds a font and carries no image XObject."""
    return (
        b"%PDF-1.7\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"3 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
        b"4 0 obj\n<< /Length 20 >>\nstream\nBT (ALPR contract) Tj ET\nendstream\nendobj\n"
        b"trailer\n<< /Root 1 0 R >>\n%%EOF\n"
    )


def _xlsx(*, sheets: int, merged: bool) -> bytes:
    """A minimal-but-valid OOXML workbook: ``sheets`` worksheets, optional merged headers."""
    sheet_refs = "".join(
        f'<sheet name="Sheet{i}" sheetId="{i}" r:id="rId{i}"/>' for i in range(1, sheets + 1)
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f"<sheets>{sheet_refs}</sheets></workbook>"
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        + "".join(
            f'<Relationship Id="rId{i}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            f'Target="worksheets/sheet{i}.xml"/>'
            for i in range(1, sheets + 1)
        )
        + "</Relationships>"
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" '
        'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        "</Types>"
    )
    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rIdWb" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/></Relationships>'
    )

    def sheet_xml(idx: int) -> str:
        merge = (
            '<mergeCells count="1"><mergeCell ref="A1:C1"/></mergeCells>'
            if merged and idx == 1
            else ""
        )
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            "<sheetData/>" + merge + "</worksheet>"
        )

    import io

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", root_rels)
        zf.writestr("xl/workbook.xml", workbook)
        zf.writestr("xl/_rels/workbook.xml.rels", rels)
        for i in range(1, sheets + 1):
            zf.writestr(f"xl/worksheets/sheet{i}.xml", sheet_xml(i))
    return buf.getvalue()


def build() -> bytes:
    """Build the mixed-format records-response archive bytes."""
    import io

    buf = io.BytesIO()
    # Fixed dates so the archive is byte-deterministic across regenerations.
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, payload in (
            ("roster.csv", b"agency,cameras\nOKC PD,12\n"),
            ("scanned_fax.tiff", _tiff_bytes()),
            ("protected.pdf", _encrypted_pdf()),
            ("digital_contract.pdf", _digital_pdf()),
            ("merged_headers.xlsx", _xlsx(sheets=1, merged=True)),
            ("native_export.xlsx", _xlsx(sheets=2, merged=False)),
        ):
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, payload)
    return buf.getvalue()


def main() -> None:
    _OUT.parent.mkdir(parents=True, exist_ok=True)
    _OUT.write_bytes(build())
    print(f"wrote {_OUT} ({_OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
