import importlib.util
from io import BytesIO
from pathlib import Path

import pytest
from conftest import make_image_bytes
from PIL import Image

from nano_banana.images import load_image

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "preview_server.py"


def load_module():
    spec = importlib.util.spec_from_file_location("preview_server", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_placeholder_without_inputs_is_png():
    preview = load_module()
    data = preview.render_placeholder("a banana", [])
    with Image.open(BytesIO(data)) as img:
        assert img.format == "PNG"
        assert img.size == (preview.SIZE, preview.SIZE)


def test_preview_generator_uses_inputs_and_can_fail():
    preview = load_module()
    images = [load_image(make_image_bytes("PNG", (8, 8)), "a.png")]
    result = preview.PreviewGenerator(delay=0, fail=False).generate("mix", images)
    assert result.mime_type == "image/png"
    assert "Preview mode" in (result.text or "")

    failing = preview.PreviewGenerator(delay=0, fail=True)
    with pytest.raises(preview.GenerationError) as excinfo:
        failing.generate("mix")
    assert excinfo.value.status_code == 429
