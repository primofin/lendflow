"""LF-005: file type is decided from the file's first bytes, never from name or headers."""

import pytest

from app.services.file_sniffing import detect_mime

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 20
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
PDF = b"%PDF-1.7\n" + b"\x00" * 20


@pytest.mark.parametrize(
    ("data", "mime"),
    [(JPEG, "image/jpeg"), (PNG, "image/png"), (PDF, "application/pdf")],
)
def test_lf005_detects_supported_types(data, mime):
    assert detect_mime(data) == mime


@pytest.mark.parametrize(
    "data",
    [
        b"",
        b"hello world",
        b"MZ\x90\x00" + b"\x00" * 20,  # Windows executable
        b"<html><script>alert(1)</script></html>",
        b"GIF89a" + b"\x00" * 20,
        b"PK\x03\x04" + b"\x00" * 20,  # zip / office
        b"\x89PNG" + b"\x00" * 20,  # truncated PNG signature
        b"\xff\xd8" + b"\x00" * 20,  # truncated JPEG signature
        b"junk%PDF-1.4",  # PDF marker not at the start
    ],
)
def test_lf005_rejects_everything_else(data):
    assert detect_mime(data) is None
