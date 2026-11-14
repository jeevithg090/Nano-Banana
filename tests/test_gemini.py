from types import SimpleNamespace as NS

import pytest

from nano_banana.gemini import (
    ErrorKind,
    GeminiImageGenerator,
    GenerationError,
    classify_exception,
    extract_image,
)
from nano_banana.images import UploadedImage


def response(*parts, block_reason=None, finish_reason=None):
    return NS(
        candidates=[NS(content=NS(parts=list(parts)), finish_reason=finish_reason)],
        prompt_feedback=NS(block_reason=block_reason) if block_reason else None,
    )


def text_part(text):
    return NS(text=text, inline_data=None)


def image_part(data=b"img", mime="image/png"):
    return NS(text=None, inline_data=NS(data=data, mime_type=mime))


def test_extract_image_finds_image_after_text_part():
    # The original implementation only inspected parts[0] and missed this.
    result = extract_image(response(text_part("Here you go"), image_part(b"abc", "image/jpeg")))
    assert result.data == b"abc"
    assert result.mime_type == "image/jpeg"
    assert result.text == "Here you go"


def test_extract_image_defaults_mime_type():
    result = extract_image(response(image_part(b"x", None)))
    assert result.mime_type == "image/png"


def test_extract_image_raises_no_image_when_only_text():
    with pytest.raises(GenerationError) as info:
        extract_image(response(text_part("I can't draw that")))
    assert info.value.kind is ErrorKind.NO_IMAGE


def test_extract_image_reports_blocked_prompt():
    blocked = NS(candidates=None, prompt_feedback=NS(block_reason="SAFETY"))
    with pytest.raises(GenerationError) as info:
        extract_image(blocked)
    assert info.value.kind is ErrorKind.BLOCKED
    assert info.value.status_code == 422


def test_extract_image_reports_safety_finish_reason():
    with pytest.raises(GenerationError) as info:
        extract_image(response(finish_reason="FinishReason.IMAGE_SAFETY"))
    assert info.value.kind is ErrorKind.BLOCKED


def test_extract_image_handles_empty_response():
    with pytest.raises(GenerationError) as info:
        extract_image(NS(candidates=None, prompt_feedback=None))
    assert info.value.kind is ErrorKind.NO_IMAGE


class CodedError(Exception):
    def __init__(self, code, message=""):
        super().__init__(message)
        self.code = code


@pytest.mark.parametrize(
    ("exc", "kind"),
    [
        (CodedError(429), ErrorKind.QUOTA_EXCEEDED),
        (Exception("RESOURCE_EXHAUSTED: quota"), ErrorKind.QUOTA_EXCEEDED),
        (CodedError(403), ErrorKind.INVALID_API_KEY),
        (CodedError(400, "API key not valid"), ErrorKind.INVALID_API_KEY),
        (CodedError(500, "internal"), ErrorKind.UPSTREAM),
        (TimeoutError("timed out"), ErrorKind.UPSTREAM),
    ],
)
def test_classify_exception(exc, kind):
    assert classify_exception(exc) is kind


class FakeModels:
    def __init__(self, result=None, error=None):
        self.result, self.error, self.kwargs = result, error, None

    def generate_content(self, **kwargs):
        self.kwargs = kwargs
        if self.error:
            raise self.error
        return self.result


def test_generator_sends_prompt_and_images_with_real_mime_types():
    models = FakeModels(result=response(image_part(b"out")))
    gen = GeminiImageGenerator("k", "test-model", client=NS(models=models))

    out = gen.generate("mix", [UploadedImage(b"png-bytes", "image/png")])

    assert out.data == b"out"
    assert models.kwargs["model"] == "test-model"
    parts = models.kwargs["contents"][0].parts
    assert parts[0].text == "mix"
    assert parts[1].inline_data.mime_type == "image/png"
    assert parts[1].inline_data.data == b"png-bytes"


def test_generator_wraps_sdk_errors():
    models = FakeModels(error=CodedError(429, "Too many requests"))
    gen = GeminiImageGenerator("k", "m", client=NS(models=models))
    with pytest.raises(GenerationError) as info:
        gen.generate("p")
    assert info.value.kind is ErrorKind.QUOTA_EXCEEDED
    assert info.value.status_code == 429
