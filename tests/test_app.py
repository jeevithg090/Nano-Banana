import base64
from io import BytesIO

from conftest import FakeGenerator, make_image_bytes

from nano_banana import create_app
from nano_banana.config import Settings
from nano_banana.gemini import ErrorKind, GenerationError


def upload(data: bytes, name: str = "a.png"):
    return (BytesIO(data), name)


def test_index_renders_with_metadata(client):
    res = client.get("/")
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert "<title>Nano Banana Image Mixer</title>" in html
    assert 'name="description"' in html
    assert "Server not configured" not in html
    assert res.headers["X-Content-Type-Options"] == "nosniff"
    assert "default-src 'self'" in res.headers["Content-Security-Policy"]


def test_static_assets_served(client):
    for path in (
        "/static/app.js",
        "/static/app.css",
        "/static/theme.js",
        "/static/favicon.svg",
        "/static/og-image.png",
        "/static/apple-touch-icon.png",
    ):
        assert client.get(path).status_code == 200


def test_healthz(client):
    assert client.get("/healthz").get_json() == {"status": "ok"}


def test_generate_text_only(client, fake_generator):
    res = client.post("/generate", data={"prompt": "  a banana  "})
    body = res.get_json()
    assert res.status_code == 200
    assert body["success"] is True
    assert base64.b64decode(body["image"]) == fake_generator.result.data
    assert body["mime_type"] == "image/png"
    assert fake_generator.calls == [("a banana", [])]


def test_generate_with_images_passes_detected_mime_types(client, fake_generator):
    res = client.post(
        "/generate",
        data={
            "prompt": "mix",
            "images": [upload(make_image_bytes("JPEG"), "x.png"), upload(make_image_bytes("PNG"))],
        },
        content_type="multipart/form-data",
    )
    assert res.status_code == 200
    _, images = fake_generator.calls[0]
    assert [i.mime_type for i in images] == ["image/jpeg", "image/png"]


def test_missing_prompt_returns_json_400(client, fake_generator):
    res = client.post("/generate", data={"prompt": "   "})
    assert res.status_code == 400
    assert res.get_json() == {"success": False, "error": "Please enter a prompt."}
    assert fake_generator.calls == []


def test_prompt_too_long(client, settings):
    res = client.post("/generate", data={"prompt": "x" * (settings.max_prompt_chars + 1)})
    assert res.status_code == 400
    assert "too long" in res.get_json()["error"]


def test_too_many_images(client, settings):
    files = [upload(make_image_bytes(), f"{i}.png") for i in range(settings.max_images + 1)]
    res = client.post(
        "/generate", data={"prompt": "p", "images": files}, content_type="multipart/form-data"
    )
    assert res.status_code == 400
    assert "at most 3" in res.get_json()["error"]


def test_invalid_image_rejected(client, fake_generator):
    res = client.post(
        "/generate",
        data={"prompt": "p", "images": [upload(b"not an image", "fake.png")]},
        content_type="multipart/form-data",
    )
    assert res.status_code == 400
    assert "fake.png is not a valid image" in res.get_json()["error"]
    assert fake_generator.calls == []


def test_upload_too_large_returns_json_413(client):
    big = b"0" * (1024 * 1024 + 1)
    res = client.post(
        "/generate",
        data={"prompt": "p", "images": [upload(big, "big.png")]},
        content_type="multipart/form-data",
    )
    assert res.status_code == 413
    assert res.get_json()["success"] is False


def test_generation_error_maps_to_status(settings):
    gen = FakeGenerator(error=GenerationError(ErrorKind.QUOTA_EXCEEDED, "secret upstream detail"))
    client = create_app(settings=settings, generator=gen).test_client()
    res = client.post("/generate", data={"prompt": "p"})
    assert res.status_code == 429
    body = res.get_json()
    assert "quota" in body["error"].lower()
    assert "secret upstream detail" not in body["error"]


def test_unexpected_error_is_json_500(settings):
    gen = FakeGenerator(error=RuntimeError("boom"))
    client = create_app(settings=settings, generator=gen).test_client()
    res = client.post("/generate", data={"prompt": "p"})
    assert res.status_code == 500
    assert res.get_json() == {"success": False, "error": "An unexpected error occurred."}


def test_app_starts_without_api_key_and_reports_503():
    client = create_app(settings=Settings(gemini_api_key=None, secret_key="s")).test_client()
    page = client.get("/").get_data(as_text=True)
    assert "Server not configured" in page
    res = client.post("/generate", data={"prompt": "p"})
    assert res.status_code == 503


def test_get_generate_not_allowed_returns_json(client):
    res = client.get("/generate")
    assert res.status_code == 405
    assert res.get_json()["success"] is False


def test_unknown_route_404_is_html(client):
    res = client.get("/nope")
    assert res.status_code == 404
    assert res.mimetype == "text/html"


def test_404_page_is_branded_with_link_home(client):
    html = client.get("/nope").get_data(as_text=True)
    assert "<title>Page not found" in html
    assert 'href="/"' in html
    assert "Back to the mixer" in html


def test_index_has_social_meta_and_limits(client, settings):
    html = client.get("/").get_data(as_text=True)
    assert 'property="og:image"' in html
    assert "/static/og-image.png" in html
    assert 'data-max-images="3"' in html
    assert f'maxlength="{settings.max_prompt_chars}"' in html
    assert 'id="liveStatus"' in html
