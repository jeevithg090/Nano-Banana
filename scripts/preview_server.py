#!/usr/bin/env python3
"""Run the web UI offline with a stub generator (no API key, no quota used).

Usage: python scripts/preview_server.py [--port 5001] [--delay 2] [--fail]

Instead of calling Gemini, ``/generate`` returns a placeholder image that is
clearly labelled as preview output. Useful for working on the frontend, for
demos and for taking screenshots. ``--fail`` makes every request return the
"quota exceeded" error so the error state can be checked.
"""

from __future__ import annotations

import argparse
import sys
import textwrap
import time
from collections.abc import Sequence
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from nano_banana import create_app
from nano_banana.config import Settings
from nano_banana.gemini import ErrorKind, GeneratedImage, GenerationError
from nano_banana.images import UploadedImage

SIZE = 768


def _font(size: int) -> ImageFont.ImageFont:
    for name in ("DejaVuSans-Bold.ttf", "Arial Bold.ttf", "arialbd.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def render_placeholder(prompt: str, images: Sequence[UploadedImage]) -> bytes:
    """Draw a labelled placeholder: a gradient (or the inputs tiled) plus the prompt."""
    canvas = Image.new("RGB", (SIZE, SIZE))
    if images:
        tile = SIZE // len(images)
        for i, upload in enumerate(images):
            with Image.open(BytesIO(upload.data)) as src:
                part = src.convert("RGB").resize((tile, SIZE))
            canvas.paste(part, (i * tile, 0))
    else:
        draw = ImageDraw.Draw(canvas)
        for y in range(SIZE):
            t = y / SIZE
            draw.line(
                [(0, y), (SIZE, y)],
                fill=(int(255 - 60 * t), int(214 - 120 * t), int(64 + 80 * t)),
            )

    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rectangle([0, SIZE - 230, SIZE, SIZE], fill=(20, 18, 13, 200))
    draw.text((32, SIZE - 210), "PREVIEW MODE · no API call made", font=_font(26), fill="#ffd84d")
    body = "\n".join(textwrap.wrap(prompt, 44)[:4])
    draw.multiline_text((32, SIZE - 165), body, font=_font(24), fill="#ffffff", spacing=8)
    canvas = Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")

    out = BytesIO()
    canvas.save(out, format="PNG")
    return out.getvalue()


class PreviewGenerator:
    def __init__(self, delay: float, fail: bool) -> None:
        self.delay = delay
        self.fail = fail

    def generate(self, prompt: str, images: Sequence[UploadedImage] = ()) -> GeneratedImage:
        time.sleep(self.delay)
        if self.fail:
            raise GenerationError(ErrorKind.QUOTA_EXCEEDED)
        return GeneratedImage(
            data=render_placeholder(prompt, images),
            mime_type="image/png",
            text="Preview mode: this placeholder was drawn locally instead of by Gemini.",
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5001)
    parser.add_argument("--delay", type=float, default=2.0, help="seconds to wait per request")
    parser.add_argument("--fail", action="store_true", help="always return a quota error")
    args = parser.parse_args()

    settings = Settings.from_env()
    app = create_app(settings=settings, generator=PreviewGenerator(args.delay, args.fail))
    print(f"Preview server (stub generator) on http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
