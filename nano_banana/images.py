"""Validation of user-uploaded images."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

from PIL import Image, UnidentifiedImageError

# Pillow format name -> MIME type accepted by the Gemini API.
SUPPORTED_FORMATS: dict[str, str] = {
    "PNG": "image/png",
    "JPEG": "image/jpeg",
    "WEBP": "image/webp",
    "GIF": "image/gif",
    "BMP": "image/bmp",
}

# Formats Gemini does not accept directly are converted to PNG.
_CONVERT_TO_PNG = {"GIF", "BMP"}


class InvalidImageError(ValueError):
    """Raised when an uploaded file is not a supported image."""


@dataclass(frozen=True)
class UploadedImage:
    data: bytes
    mime_type: str


def load_image(data: bytes, filename: str = "upload") -> UploadedImage:
    """Validate raw bytes as an image and return them with a reliable MIME type.

    The MIME type is detected from the file content, never from the
    client-supplied name or Content-Type header.
    """
    if not data:
        raise InvalidImageError(f"{filename} is empty.")
    try:
        with Image.open(BytesIO(data)) as probe:
            fmt = probe.format
            probe.verify()
    except (UnidentifiedImageError, OSError, SyntaxError) as exc:
        raise InvalidImageError(f"{filename} is not a valid image.") from exc

    if fmt not in SUPPORTED_FORMATS:
        raise InvalidImageError(f"{filename} has an unsupported format ({fmt}).")

    if fmt in _CONVERT_TO_PNG:
        with Image.open(BytesIO(data)) as img:
            buffer = BytesIO()
            img.convert("RGBA").save(buffer, format="PNG")
        return UploadedImage(data=buffer.getvalue(), mime_type="image/png")

    return UploadedImage(data=data, mime_type=SUPPORTED_FORMATS[fmt])
