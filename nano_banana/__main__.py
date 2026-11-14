"""Run the development server: ``python -m nano_banana``."""

from __future__ import annotations

import logging
import os

from dotenv import load_dotenv


def main() -> None:
    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    from . import create_app

    app = create_app()
    app.run(
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "5000")),
        debug=os.getenv("FLASK_DEBUG", "").lower() in {"1", "true", "yes"},
    )


if __name__ == "__main__":
    main()
