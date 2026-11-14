"""Gunicorn settings, loaded automatically by ``gunicorn wsgi:app``."""

import os

bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"
workers = int(os.getenv("WEB_CONCURRENCY", "2"))
# Image generation can take well over gunicorn's 30s default.
timeout = int(os.getenv("GUNICORN_TIMEOUT", "120"))
accesslog = "-"
