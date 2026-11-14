#!/usr/bin/env python3
"""Live smoke test: generate one image with the configured Gemini key.

Usage: python scripts/smoke_test.py "a banana wearing a costume" [-o out.png]

This calls the real API (and uses quota); it is not part of the pytest suite.
"""

from __future__ import annotations

import argparse
import mimetypes
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from nano_banana.config import Settings
from nano_banana.gemini import GeminiImageGenerator, GenerationError


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "prompt", nargs="?", default="Generate an image of a banana wearing a costume."
    )
    parser.add_argument(
        "-o", "--output", type=Path, help="output file (default: generated/smoke.<ext>)"
    )
    args = parser.parse_args()

    load_dotenv()
    settings = Settings.from_env()
    if not settings.gemini_api_key:
        print("GEMINI_API_KEY is not set (see .env.example).", file=sys.stderr)
        return 2

    generator = GeminiImageGenerator(settings.gemini_api_key, settings.gemini_model)
    print(f"Model: {settings.gemini_model}\nPrompt: {args.prompt}")
    try:
        result = generator.generate(args.prompt)
    except GenerationError as exc:
        print(f"Failed: {exc.user_message}", file=sys.stderr)
        return 1

    ext = mimetypes.guess_extension(result.mime_type) or ".png"
    output = args.output or Path("generated") / f"smoke{ext}"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(result.data)
    print(f"Saved {len(result.data)} bytes to {output}")
    if result.text:
        print(f"Model text: {result.text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
