"""Dash 4.4 native FastAPI backend + background callbacks + shared Celery.

Demonstrates the target production shape for long-running tools:

  * ONE Celery app (deploy/celery_shared.py) serves BOTH:
      - a Dash background callback (background=True, CeleryManager)
      - the tools API's own task, enqueued from a FastAPI endpoint
  * The browser polls Dash for background-callback progress/results;
    API clients poll GET /api/jobs/{id} for their task.

Run (two processes, both from the dash4 environment):
  dash4/.venv/bin/python -m uvicorn deploy.serve_dash4_background:api --port 8064
  dash4/.venv/bin/python -m celery -A deploy.serve_dash4_background:celery_app \
      worker --loglevel=info --pool=solo
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import dash_mantine_components as dmc
from celery.result import AsyncResult
from dash import CeleryManager, Dash, Input, Output, callback, html
from fastapi import FastAPI

from deploy.celery_shared import celery_app, heavy_compute

api = FastAPI(title="Tools API + Dash UI + shared Celery")


# ---- API side: enqueue the team's own task, poll for its result -----------
@api.post("/api/tools/heavy/{n}")
async def start_heavy(n: int):
    task = heavy_compute.delay(n)
    return {"job_id": task.id}


@api.get("/api/jobs/{job_id}")
async def job_status(job_id: str):
    res = AsyncResult(job_id, app=celery_app)
    return {"status": res.status, "result": res.result if res.ready() else None}


# ---- Dash side: background callback on the SAME celery app ----------------
background_manager = CeleryManager(celery_app)

dash_app = Dash(
    __name__,
    server=api,
    background_callback_manager=background_manager,
)

dash_app.layout = dmc.MantineProvider(
    html.Div(
        [
            dmc.Button("Run background job", id="run"),
            dmc.Progress(id="bar", value=0, w=300, mt="md"),
            dmc.Text(id="out", mt="md"),
        ],
        style={"padding": 24},
    )
)


@callback(
    Output("out", "children"),
    Input("run", "n_clicks"),
    background=True,
    running=[(Output("run", "disabled"), True, False)],
    progress=[Output("bar", "value")],
    prevent_initial_call=True,
)
def long_job(set_progress, n_clicks):
    for i in range(1, 6):
        time.sleep(1)
        set_progress(i * 20)
    return f"background job #{n_clicks} finished at {time.strftime('%H:%M:%S')}"
