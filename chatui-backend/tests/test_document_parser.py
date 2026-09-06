"""Tests for documents/parser.py -- text extraction and content sniffing."""

import io

import pytest

from documents.parser import extract_text, sniff_image_mime, sniff_kind


def test_plain_text_extraction():
    data = "Hello world.\n\nSecond paragraph.".encode("utf-8")
    text = extract_text(data, "notes.txt")
    assert "Hello world" in text
    assert "Second paragraph" in text


def test_markdown_extension_accepted_as_text():
    data = "# Title\n\nSome content.".encode("utf-8")
    text = extract_text(data, "readme.md")
    assert "Title" in text


def test_invalid_utf8_text_rejected():
    data = bytes([0xFF, 0xFE, 0x00, 0x01])
    with pytest.raises(ValueError):
        extract_text(data, "broken.txt")


def test_unsupported_extension_rejected():
    with pytest.raises(ValueError):
        extract_text(b"whatever content", "malware.exe")


def test_docx_extraction():
    docx_module = pytest.importorskip("docx")
    buf = io.BytesIO()
    doc = docx_module.Document()
    doc.add_paragraph("Quarterly revenue grew 18% in Q3 2026.")
    doc.add_paragraph("CFO Jane Whitfield credited the APAC expansion.")
    doc.save(buf)
    text = extract_text(buf.getvalue(), "report.docx")
    assert "Quarterly revenue" in text
    assert "Jane Whitfield" in text


def test_pdf_extraction():
    canvas_module = pytest.importorskip("reportlab.pdfgen.canvas")
    buf = io.BytesIO()
    c = canvas_module.Canvas(buf)
    c.drawString(100, 750, "Employee handbook excerpt.")
    c.drawString(100, 730, "All staff receive 22 days of paid leave per year.")
    c.save()
    text = extract_text(buf.getvalue(), "handbook.pdf")
    assert "Employee handbook" in text
    assert "22 days" in text


def test_pdf_magic_bytes_detected_even_with_wrong_extension():
    # The sniffer should trust real content over a lying filename -- this
    # is the "never blindly trust the client-provided MIME type" guarantee.
    data = b"%PDF-1.4\n%fake-but-has-the-right-magic-bytes"
    assert sniff_kind(data, "innocent.txt") == "pdf"


def test_png_magic_bytes_sniffed_correctly(tiny_png_bytes):
    assert sniff_image_mime(tiny_png_bytes) == "image/png"


def test_jpeg_magic_bytes_sniffed_correctly():
    assert sniff_image_mime(b"\xff\xd8\xff\xe0" + b"\x00" * 20) == "image/jpeg"


def test_non_image_bytes_not_sniffed_as_image():
    assert sniff_image_mime(b"this is definitely not an image") is None


def test_empty_pdf_with_no_text_raises_clear_error():
    canvas_module = pytest.importorskip("reportlab.pdfgen.canvas")
    buf = io.BytesIO()
    c = canvas_module.Canvas(buf)
    c.save()  # a valid PDF with a blank page, no text at all
    with pytest.raises(ValueError):
        extract_text(buf.getvalue(), "blank.pdf")
