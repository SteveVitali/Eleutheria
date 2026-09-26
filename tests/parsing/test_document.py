# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The document-bytes engines the P25.5 extraction adapters run on (§24 layers 2-3).

``html_text`` / ``html_links`` are the layer-2 helpers a resource-index /
index-page adapter uses on captured bytes; ``pdf_text_pages`` is the layer-3
``pdf_text`` engine. All are pure functions of captured bytes — no network —
and fail closed: a malformed / encrypted / image-only / non-PDF byte string
yields no text, never a partial or fabricated page.
"""

from __future__ import annotations

from parsing.document import (
    byte_range_locator,
    html_links,
    html_text,
    page_locator_for,
    pdf_text_pages,
)
from support import minimal_pdf

# --- layer 2: HTML text + link discovery ---------------------------------------


def test_html_text_drops_markup_noise_and_normalizes_whitespace() -> None:
    data = (
        b"<html><head><title>T</title><style>body{color:red}</style></head>"
        b"<body><script>var x=1;</script><p>Hello   <b>world</b></p>"
        b"<svg><path d='M0 0'/></svg></body></html>"
    )
    text = html_text(data)
    assert "Hello world" in text
    assert "var x" not in text and "color:red" not in text and "M0 0" not in text


def test_html_text_on_non_html_bytes_never_raises() -> None:
    text = html_text(b"%PDF-1.4 binary \x00\xff")
    assert text.startswith("%PDF-1.4 binary")
    assert html_text(b"") == ""


def test_html_links_resolves_relative_and_dedups_in_document_order() -> None:
    data = (
        b'<a href="/post-final/alpr-impact-and-use-policy.pdf">ALPR IUP</a>'
        b'<a href="https://other.example/x.pdf">cross host</a>'
        b'<a href="mailto:a@b.c">mail</a>'
        b'<a href="javascript:void(0)">js</a>'
        b'<a href="#frag">frag</a>'
        b'<a href="/post-final/alpr-impact-and-use-policy.pdf">dup</a>'
        b'<a href="../rel/doc.pdf">rel</a>'
    )
    links = html_links(data, "https://www.nyc.gov/site/nypd/post-act.page")
    urls = [link.url for link in links]
    assert urls == [
        "https://www.nyc.gov/post-final/alpr-impact-and-use-policy.pdf",
        "https://other.example/x.pdf",
        "https://www.nyc.gov/site/rel/doc.pdf",
    ]
    assert links[0].anchor == "ALPR IUP" and links[0].ordinal == 0


def test_byte_range_locator_finds_the_literal_in_the_capture() -> None:
    data = b"header;SMC 14.18;trailer"
    loc = byte_range_locator(data, "SMC 14.18")
    assert loc == {"kind": "byte_range", "start": 7, "end": 16}
    assert data[loc["start"] : loc["end"]] == b"SMC 14.18"
    assert byte_range_locator(data, "smc 14.18") is not None  # case-insensitive fallback
    assert byte_range_locator(data, "not present") is None


# --- layer 3: digital-native PDF text -------------------------------------------


def test_pdf_text_pages_extracts_per_page_text() -> None:
    data = minimal_pdf([["PAGE ONE text"], ["PAGE TWO", "second line"]])
    pages = pdf_text_pages(data)
    assert len(pages) == 2
    assert "PAGE ONE text" in pages[0]
    assert "PAGE TWO" in pages[1] and "second line" in pages[1]


def test_page_locator_is_one_based() -> None:
    pages = ("nothing here", "the retention policy lives here")
    assert page_locator_for(pages, "retention policy") == {"kind": "page", "page": 2}
    assert page_locator_for(pages, "missing") is None


def test_pdf_text_pages_fails_closed_on_non_pdf_bytes() -> None:
    assert pdf_text_pages(b"<!doctype html><html>404 page</html>") == ()
    assert pdf_text_pages(b"%PDF-1.4\nfake truncated") == ()
    assert pdf_text_pages(b"") == ()


def test_pdf_text_pages_reports_no_text_layer_for_image_only() -> None:
    # A structurally valid PDF page with no text objects = a scanned/image-only
    # document: the layer-3 engine yields pages with no text, never fabricates.
    data = minimal_pdf([[]])
    pages = pdf_text_pages(data)
    assert pages == ("",) or pages == ()
