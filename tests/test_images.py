import pytest
from conftest import make_image_bytes
from PIL import Image

from nano_banana.images import InvalidImageError, load_image


@pytest.mark.parametrize(
    ("fmt", "mime"),
    [("PNG", "image/png"), ("JPEG", "image/jpeg"), ("WEBP", "image/webp")],
)
def test_detects_mime_type_from_content(fmt, mime):
    img = load_image(make_image_bytes(fmt), "whatever.bin")
    assert img.mime_type == mime


@pytest.mark.parametrize("fmt", ["GIF", "BMP"])
def test_converts_formats_gemini_does_not_accept_to_png(fmt):
    img = load_image(make_image_bytes(fmt))
    assert img.mime_type == "image/png"
    with Image.open(__import__("io").BytesIO(img.data)) as reopened:
        assert reopened.format == "PNG"


def test_rejects_empty_file():
    with pytest.raises(InvalidImageError, match="empty"):
        load_image(b"", "a.png")


def test_rejects_non_image_bytes_even_with_image_extension():
    with pytest.raises(InvalidImageError, match="not a valid image"):
        load_image(b"<script>alert(1)</script>", "evil.png")


def test_rejects_unsupported_format():
    from io import BytesIO

    buffer = BytesIO()
    Image.new("RGB", (2, 2)).save(buffer, format="TIFF")
    with pytest.raises(InvalidImageError, match="unsupported format"):
        load_image(buffer.getvalue(), "x.tiff")
