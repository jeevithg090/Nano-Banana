"""WSGI entry point for production servers, e.g. ``gunicorn wsgi:app``."""

import logging

from dotenv import load_dotenv

from nano_banana import create_app

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

app = create_app()
