"""Dash 4.2+ production shape: ONE FastAPI app hosting both the tools API
and the Dash UI natively — no WSGIMiddleware, no a2wsgi threadpool bridge.

Mirrors the real deployment: FastAPI serves /api/tools/* (the computational
services) and Dash provides the UI, sharing the same event loop, middleware,
dependency injection, and lifespan.

Requires the dash4/ environment:
  dash4/.venv/bin/python -m uvicorn deploy.serve_dash4_native:api --port 8061
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI

from common import factories as F
from common.app_factory import ROOT, create_app

api = FastAPI(title="Tools API + Dash UI")


# ---- tools API routes: register BEFORE attaching Dash so they take
# precedence over Dash's catch-all page route ------------------------------
@api.get("/api/tools/{tab}/result")
async def tool_result(tab: int, size_kb: int = 200):
    """Example tool service endpoint — the kind of route the app already hosts."""
    return F.make_tool_result(tab, size_kb=size_kb)


@api.get("/api/health")
async def health():
    return {"status": "ok"}


# ---- Dash UI attached natively to the same FastAPI instance ---------------
dash_app = create_app(
    title="Dash 4 native (tools API + UI in one FastAPI app)",
    lazy_tabs=True,
    assets_folder=str(ROOT / "assets_partial"),
    server=api,  # Dash 4.2+: attach to the existing FastAPI app
)


# With the fastapi backend, server-side callbacks may be `async def` —
# useful for callbacks that call the tools API or other services without
# pinning a worker thread.
from dash import Input, Output, callback  # noqa: E402


@callback(
    Output(F.UI_STORE_IDS[0], "data", allow_duplicate=True),
    Input("tabs", "value"),
    prevent_initial_call=True,
)
async def note_tab_async(active):
    await asyncio.sleep(0)  # stand-in for `await client.get(...)` etc.
    return {"last_tab": active}
