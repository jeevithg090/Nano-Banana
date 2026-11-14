# 🍌 Nano Banana Image Mixer

A small Flask web app for **generating images from text** and **remixing your own images** with
Google's Gemini image model (nicknamed "Nano Banana"). Type a prompt, optionally drop in up
to five reference images, and download the result.

## Features

- **Text to image**: describe an image and generate it.
- **Image mixing and editing**: upload 1–5 images and describe how to combine or change them.
- **Drag and drop** uploads with thumbnails and per-image removal.
- **Download** the generated image in the format the model returned.
- **Clear error messages** for quota limits, rejected API keys, safety blocks and invalid uploads.
- **Stateless**: uploads and results stay in memory and are never written to disk, so the app
  runs fine on multiple instances or read-only filesystems.
- **Responsive and accessible UI**: works at phone widths, supports keyboard use, announces
  status to screen readers and follows the system dark mode.

## Tech stack

| Layer | Choice |
| --- | --- |
| Backend | Python 3.10+, Flask 3 |
| AI | [Google Gen AI SDK](https://github.com/googleapis/python-genai) (`google-genai`), default model `gemini-2.5-flash-image` |
| Image validation | Pillow |
| Frontend | Server-rendered Jinja template, plain CSS and JavaScript (no build step) |
| Production server | Gunicorn |
| Tooling | pytest, Ruff (lint and format) |

## How it works

```
Browser (templates/index.html + static/app.js)
   │  POST /generate  (multipart: prompt + images[])
   ▼
Flask app  (nano_banana/__init__.py)
   │  validate prompt length and image count
   │  images.load_image(): check real file content with Pillow, detect MIME type,
   │                        convert GIF/BMP to PNG
   ▼
GeminiImageGenerator  (nano_banana/gemini.py)
   │  models.generate_content(prompt + image parts, modalities IMAGE+TEXT)
   │  extract_image(): first inline image in any part, or a typed GenerationError
   ▼
JSON response { success, image (base64), mime_type, text }
   │
   ▼
Browser turns the base64 into a Blob URL to preview and download
```

Errors are returned as `{"success": false, "error": "..."}` with a matching HTTP status
(400 bad input, 413 upload too large, 422 safety block, 429 quota, 502 upstream failure,
503 no API key configured). Upstream error details are logged on the server, not sent to the
browser.

## Getting started

### Prerequisites

- Python 3.10 or newer
- A Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey)

### Install

```bash
git clone https://github.com/jeevithg090/Nano-Banana.git
cd Nano-Banana
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt   # or requirements.txt for runtime only
cp .env.example .env              # then set GEMINI_API_KEY in .env
```

### Run (development)

```bash
python -m nano_banana
```

Open <http://127.0.0.1:5000>. The app starts without an API key too; the page then shows a
"Server not configured" notice and `/generate` returns 503.

### Check your API key

```bash
python scripts/smoke_test.py "a banana wearing a superhero costume"
```

This makes one real API call (it uses quota) and saves the image under `generated/`.

## Environment variables

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `GEMINI_API_KEY` | Yes | – | Google AI Studio API key. |
| `GEMINI_MODEL` | No | `gemini-2.5-flash-image` | Gemini model that supports image output. |
| `FLASK_SECRET_KEY` | No | random per process | Flask secret key. Set a fixed value in production. |
| `MAX_IMAGES` | No | `5` | Maximum images per request. |
| `MAX_UPLOAD_MB` | No | `16` | Maximum total request size in MB. |
| `MAX_PROMPT_CHARS` | No | `2000` | Maximum prompt length. |
| `HOST` / `PORT` | No | `127.0.0.1` / `5000` | Development server address (`python -m nano_banana`). Gunicorn uses `PORT` (default `8000`). |
| `FLASK_DEBUG` | No | `0` | Enable the Flask debugger for local development only. |
| `WEB_CONCURRENCY` | No | `2` | Gunicorn worker count. |
| `GUNICORN_TIMEOUT` | No | `120` | Gunicorn worker timeout in seconds. |

Variables are read from the process environment; a `.env` file in the project root is loaded
automatically.

## Tests and linting

```bash
pytest              # unit and HTTP tests; the Gemini API is faked, no key needed
ruff check .        # lint
ruff format .       # format
```

## Deployment

The app is a standard WSGI application exposed as `wsgi:app`. `gunicorn.conf.py` is picked up
automatically and binds to `0.0.0.0:$PORT` with a 120 second timeout, because image generation
can take longer than Gunicorn's 30 second default.

```bash
pip install -r requirements.txt
export GEMINI_API_KEY=...  FLASK_SECRET_KEY=...
gunicorn wsgi:app
```

This works on any platform that runs a Python web process (Render, Railway, Fly.io, Heroku,
Cloud Run, a VM behind nginx, ...). Use `GET /healthz` for health checks.

Before exposing it publicly, keep in mind that every request spends your Gemini quota. There
is no authentication or rate limiting built in, so put it behind a login, a rate-limiting
proxy, or both.

## Project structure

```
.
├── nano_banana/
│   ├── __init__.py        # create_app() factory, routes, error handling, security headers
│   ├── __main__.py        # development server (python -m nano_banana)
│   ├── config.py          # Settings loaded from environment variables
│   ├── gemini.py          # Gemini client wrapper, response parsing, error classification
│   ├── images.py          # upload validation and MIME detection
│   ├── templates/
│   │   └── index.html     # page markup
│   └── static/
│       ├── app.css        # styles (light and dark)
│       ├── app.js         # upload, preview, submit and result handling
│       └── favicon.svg
├── tests/                 # pytest suite
├── scripts/
│   └── smoke_test.py      # live API check
├── wsgi.py                # production entry point
├── gunicorn.conf.py
├── pyproject.toml         # Ruff and pytest configuration
├── requirements.txt
├── requirements-dev.txt
└── .env.example
```

## Prompt tips

- Be specific about subject, setting, style, lighting, colours and composition.
- When mixing, say what each image contributes, for example "put the person from the first
  image in the scene from the second, in watercolour style".
