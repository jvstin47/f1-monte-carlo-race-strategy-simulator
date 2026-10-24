"""
Root application entrypoint.
Preserves backward compatibility for existing deployment commands (e.g. `python main.py`)
and test imports (`from main import app`), delegating to the modular `app` package.
"""

import os
from app.main import app, create_app
from app.core.config import settings
from app.api.dependencies import resolve_track_params

__all__ = ["app", "create_app", "resolve_track_params", "settings"]

if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", settings.PORT))
    uvicorn.run("app.main:app", host=settings.HOST, port=port)
