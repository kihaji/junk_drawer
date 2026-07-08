"""Production-style mounting: Dash inside FastAPI under uvicorn.

Mirrors the recommended setup for a K8s deployment:
  * a2wsgi.WSGIMiddleware (Starlette/FastAPI's WSGIMiddleware is deprecated);
    `workers` sizes the threadpool every Dash callback runs in.
  * Dash assets served by Starlette StaticFiles (async, bypasses the Flask
    threadpool entirely). Mounted BEFORE the Dash catch-all.
  * Long browser caching for assets — safe because Dash appends ?m=<mtime>
    to every asset URL for cache busting.
  * Compression intentionally NOT done here: enable gzip/brotli at the
    nginx ingress instead (see deploy/ingress-notes.md). If you can't touch
    the ingress, uncomment the GZipMiddleware line as a fallback.

Run:  uv run uvicorn deploy.serve_fastapi:fastapi_app --port 8060
"""

import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from a2wsgi import WSGIMiddleware
from fastapi import FastAPI
from starlette.staticfiles import StaticFiles

from common.app_factory import ROOT, create_app

dash_app = create_app(
    title="Production mount",
    lazy_tabs=True,
    assets_folder=str(ROOT / "assets_partial"),
)
# Flask still serves anything StaticFiles misses; give those long cache too.
dash_app.server.config["SEND_FILE_MAX_AGE_DEFAULT"] = timedelta(days=365)

fastapi_app = FastAPI()
# fastapi_app.add_middleware(GZipMiddleware, minimum_size=1000)  # ingress fallback

fastapi_app.mount(
    "/assets", StaticFiles(directory=str(ROOT / "assets_partial")), name="dash-assets"
)
fastapi_app.mount("/", WSGIMiddleware(dash_app.server, workers=20))
