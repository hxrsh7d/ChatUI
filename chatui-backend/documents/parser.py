"""
Document text extraction.

Supported formats: PDF, TXT, Markdown, DOCX (per the project brief's
"Support initially" list). Every extractor takes raw bytes (never a
trusted client filename/MIME) and returns plain text, or raises
ValueError with a message safe to show the user.
"""

from __future__ import annotations

import io

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md", ".markdown", ".docx"}
SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}

# Real content-sniffing, independent of whatever Content-Type / filename
# the client claims. This is what item 32 ("never blindly trust the
# client-provided MIME type") requires.
MAGIC_BYTES = {
    b"%PDF-": "pdf",
    b"PK\x03\x04": "zip",  # docx (and pptx/xlsx) are zip containers
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"\xff\xd8\xff": "image/jpeg",
    b"GIF87a": "image/gif",
    b"GIF89a": "image/gif",
    b"RIFF": "image/webp",  # WEBP files start RIFF....WEBP; refined below
}


def sniff_image_mime(data: bytes) -> str | None:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def sniff_kind(data: bytes, filename: str) -> str:
    for magic, kind in MAGIC_BYTES.items():
        if data.startswith(magic):
            return "docx" if kind == "zip" and filename.lower().endswith(".docx") else kind

    # No recognizable binary magic -> only trust it as plain text if it
    # actually decodes as UTF-8 text and the extension matches.
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext in (".txt", ".md", ".markdown"):
        try:
            data.decode("utf-8")
            return "text"
        except UnicodeDecodeError:
            raise ValueError("File claims to be plain text but is not valid UTF-8.")

    raise ValueError("Unrecognized or unsupported file type.")


def extract_text(data: bytes, filename: str) -> str:
    kind = sniff_kind(data, filename)

    if kind == "text":
        return data.decode("utf-8", errors="replace")

    if kind == "pdf":
        return _extract_pdf(data)

    if kind == "docx":
        return _extract_docx(data)

    raise ValueError(f"Unsupported document type: {kind}")


def _extract_pdf(data: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ValueError("PDF support requires the 'pypdf' package.") from exc

    reader = PdfReader(io.BytesIO(data))
    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception:
            raise ValueError("This PDF is password-protected and cannot be read.")

    pages = []
    for page in reader.pages:
        try:
            pages.append(page.extract_text() or "")
        except Exception:
            pages.append("")
    text = "\n\n".join(pages).strip()
    if not text:
        raise ValueError("No extractable text found (this may be a scanned/image-only PDF).")
    return text


def _extract_docx(data: bytes) -> str:
    try:
        import docx
    except ImportError as exc:
        raise ValueError("DOCX support requires the 'python-docx' package.") from exc

    document = docx.Document(io.BytesIO(data))
    parts = [p.text for p in document.paragraphs if p.text.strip()]
    for table in document.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells if c.text.strip()]
            if cells:
                parts.append(" | ".join(cells))

    text = "\n".join(parts).strip()
    if not text:
        raise ValueError("No extractable text found in this DOCX file.")
    return text
