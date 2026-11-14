"""Nano Banana: a Flask web app for generating and remixing images with Gemini."""

from __future__ import annotations

import base64
import logging

from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import HTTPException, RequestEntityTooLarge

from .config import Settings
from .gemini import GeminiImageGenerator, GenerationError, ImageGenerator
from .images import InvalidImageError, UploadedImage, load_image

__all__ = ["create_app"]

logger = logging.getLogger(__name__)


def _error(message: str, status: int):
    return jsonify(success=False, error=message), status


def create_app(
    settings: Settings | None = None,
    generator: ImageGenerator | None = None,
) -> Flask:
    """Application factory.

    ``generator`` can be injected (e.g. in tests); otherwise a Gemini-backed
    generator is created lazily on first use when an API key is configured.
    """
    settings = settings or Settings.from_env()
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=settings.secret_key,
        MAX_CONTENT_LENGTH=settings.max_content_length,
    )
    app.extensions["nano_banana.settings"] = settings

    if settings.gemini_api_key is None and generator is None:
        logger.warning("GEMINI_API_KEY is not set; image generation is disabled.")

    state: dict[str, ImageGenerator | None] = {"generator": generator}

    def get_generator() -> ImageGenerator | None:
        if state["generator"] is None and settings.gemini_api_key:
            state["generator"] = GeminiImageGenerator(
                api_key=settings.gemini_api_key, model=settings.gemini_model
            )
        return state["generator"]

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' blob: data:; "
            "style-src 'self'; script-src 'self'; frame-ancestors 'none'",
        )
        return response

    @app.get("/")
    def index():
        return render_template(
            "index.html",
            max_images=settings.max_images,
            max_upload_mb=settings.max_upload_mb,
            max_prompt_chars=settings.max_prompt_chars,
            configured=settings.gemini_api_key is not None or generator is not None,
        )

    @app.get("/healthz")
    def healthz():
        return jsonify(status="ok")

    @app.post("/generate")
    def generate():
        prompt = (request.form.get("prompt") or "").strip()
        if not prompt:
            return _error("Please enter a prompt.", 400)
        if len(prompt) > settings.max_prompt_chars:
            return _error(f"Prompt is too long (max {settings.max_prompt_chars} characters).", 400)

        files = [f for f in request.files.getlist("images") if f and f.filename]
        if len(files) > settings.max_images:
            return _error(f"Upload at most {settings.max_images} images.", 400)

        images: list[UploadedImage] = []
        for upload in files:
            try:
                images.append(load_image(upload.read(), upload.filename or "upload"))
            except InvalidImageError as exc:
                return _error(str(exc), 400)

        image_generator = get_generator()
        if image_generator is None:
            return _error("The server is not configured with a GEMINI_API_KEY.", 503)

        try:
            result = image_generator.generate(prompt, images)
        except GenerationError as exc:
            return _error(exc.user_message, exc.status_code)

        return jsonify(
            success=True,
            mime_type=result.mime_type,
            image=base64.b64encode(result.data).decode("ascii"),
            text=result.text,
        )

    @app.errorhandler(RequestEntityTooLarge)
    def too_large(_exc):
        return _error(f"Upload is too large (max {settings.max_upload_mb} MB in total).", 413)

    @app.errorhandler(HTTPException)
    def http_error(exc: HTTPException):
        if request.path == "/generate":
            return _error(exc.description or exc.name, exc.code or 500)
        return exc

    @app.errorhandler(Exception)
    def unhandled(exc: Exception):
        logger.exception("Unhandled error")
        return _error("An unexpected error occurred.", 500)

    return app
