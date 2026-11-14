from __future__ import annotations

from collections.abc import Sequence
from io import BytesIO

import pytest
from PIL import Image

from nano_banana import create_app
from nano_banana.config import Settings
from nano_banana.gemini import GeneratedImage, GenerationError
from nano_banana.images import UploadedImage


def make_image_bytes(fmt: str = "PNG", size: tuple[int, int] = (4, 4)) -> bytes:
    buffer = BytesIO()
    mode = "RGB" if fmt in {"JPEG", "BMP"} else "RGBA"
    Image.new(mode, size, (255, 200, 0)).save(buffer, format=fmt)
    return buffer.getvalue()


class FakeGenerator:
    def __init__(self, result: GeneratedImage | None = None, error: Exception | None = None):
        self.result = result or GeneratedImage(data=b"\x89PNGfake", mime_type="image/png")
        self.error = error
        self.calls: list[tuple[str, list[UploadedImage]]] = []

    def generate(self, prompt: str, images: Sequence[UploadedImage] = ()) -> GeneratedImage:
        self.calls.append((prompt, list(images)))
        if self.error:
            raise self.error
        return self.result


@pytest.fixture
def settings() -> Settings:
    return Settings(gemini_api_key="test-key", secret_key="test", max_images=3, max_upload_mb=1)


@pytest.fixture
def fake_generator() -> FakeGenerator:
    return FakeGenerator()


@pytest.fixture
def client(settings: Settings, fake_generator: FakeGenerator):
    app = create_app(settings=settings, generator=fake_generator)
    app.config["TESTING"] = True
    return app.test_client()


__all__ = ["FakeGenerator", "GenerationError", "make_image_bytes"]
