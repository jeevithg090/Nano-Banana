"""Thin wrapper around the Google Gen AI SDK for image generation."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol

from .images import UploadedImage

logger = logging.getLogger(__name__)


class ErrorKind(str, Enum):
    QUOTA_EXCEEDED = "quota_exceeded"
    INVALID_API_KEY = "invalid_api_key"
    BLOCKED = "blocked"
    NO_IMAGE = "no_image"
    UPSTREAM = "upstream"


ERROR_MESSAGES: dict[ErrorKind, str] = {
    ErrorKind.QUOTA_EXCEEDED: (
        "API quota exceeded. Wait for the quota to reset or use a different API key."
    ),
    ErrorKind.INVALID_API_KEY: "The Gemini API key was rejected. Check GEMINI_API_KEY.",
    ErrorKind.BLOCKED: "The request was blocked by the model's safety filters. "
    "Try rephrasing your prompt.",
    ErrorKind.NO_IMAGE: "The model did not return an image. Try a more descriptive prompt.",
    ErrorKind.UPSTREAM: "Image generation failed. Please try again.",
}

ERROR_STATUS: dict[ErrorKind, int] = {
    ErrorKind.QUOTA_EXCEEDED: 429,
    ErrorKind.INVALID_API_KEY: 502,
    ErrorKind.BLOCKED: 422,
    ErrorKind.NO_IMAGE: 502,
    ErrorKind.UPSTREAM: 502,
}


class GenerationError(Exception):
    """A failure that can be shown to the user."""

    def __init__(self, kind: ErrorKind, detail: str | None = None) -> None:
        super().__init__(detail or ERROR_MESSAGES[kind])
        self.kind = kind
        self.detail = detail

    @property
    def user_message(self) -> str:
        return ERROR_MESSAGES[self.kind]

    @property
    def status_code(self) -> int:
        return ERROR_STATUS[self.kind]


@dataclass(frozen=True)
class GeneratedImage:
    data: bytes
    mime_type: str
    text: str | None = None


class ImageGenerator(Protocol):
    def generate(self, prompt: str, images: Sequence[UploadedImage] = ()) -> GeneratedImage: ...


def classify_exception(exc: Exception) -> ErrorKind:
    """Map an SDK/transport exception to a user-facing error category."""
    code = getattr(exc, "code", None)
    message = str(exc).lower()
    if code == 429 or "resource_exhausted" in message or "quota" in message:
        return ErrorKind.QUOTA_EXCEEDED
    if code in (401, 403) or "api key" in message or "api_key" in message:
        return ErrorKind.INVALID_API_KEY
    return ErrorKind.UPSTREAM


def extract_image(response: Any) -> GeneratedImage:
    """Return the first image found in any part of any candidate.

    Raises GenerationError if the response holds no image.
    """
    texts: list[str] = []
    for candidate in getattr(response, "candidates", None) or []:
        content = getattr(candidate, "content", None)
        for part in getattr(content, "parts", None) or []:
            inline = getattr(part, "inline_data", None)
            if inline is not None and getattr(inline, "data", None):
                return GeneratedImage(
                    data=inline.data,
                    mime_type=getattr(inline, "mime_type", None) or "image/png",
                    text=" ".join(texts) or None,
                )
            if getattr(part, "text", None):
                texts.append(part.text)

    feedback = getattr(response, "prompt_feedback", None)
    if feedback is not None and getattr(feedback, "block_reason", None):
        raise GenerationError(ErrorKind.BLOCKED, f"Prompt blocked: {feedback.block_reason}")
    for candidate in getattr(response, "candidates", None) or []:
        reason = str(getattr(candidate, "finish_reason", "") or "")
        if "SAFETY" in reason or "PROHIBITED" in reason or "BLOCKLIST" in reason:
            raise GenerationError(ErrorKind.BLOCKED, f"Candidate blocked: {reason}")
    raise GenerationError(ErrorKind.NO_IMAGE, " ".join(texts) or None)


class GeminiImageGenerator:
    """Generates images with a Gemini image model."""

    def __init__(self, api_key: str, model: str, client: Any | None = None) -> None:
        if client is None:
            from google import genai

            client = genai.Client(api_key=api_key)
        self._client = client
        self._model = model

    def generate(self, prompt: str, images: Sequence[UploadedImage] = ()) -> GeneratedImage:
        from google.genai import types

        parts = [types.Part.from_text(text=prompt)]
        parts.extend(
            types.Part.from_bytes(data=img.data, mime_type=img.mime_type) for img in images
        )
        config = types.GenerateContentConfig(response_modalities=["IMAGE", "TEXT"])
        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=[types.Content(role="user", parts=parts)],
                config=config,
            )
        except Exception as exc:
            kind = classify_exception(exc)
            if kind is ErrorKind.UPSTREAM:
                logger.exception("Gemini request failed")
            else:
                logger.warning("Gemini request failed (%s): %s", kind.value, exc)
            raise GenerationError(kind, str(exc)) from exc
        return extract_image(response)
