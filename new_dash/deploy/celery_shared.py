"""ONE Celery app shared by Dash background callbacks and the tools API.

In production point broker/backend at Redis:
    celery_app = Celery(__name__, broker=REDIS_URL, backend=REDIS_URL)
Here a filesystem broker/backend is used so the demo runs without Redis —
the mechanics (worker process, task registration, polling) are identical.

The key insight: dash.CeleryManager(celery_app) registers each background
callback as an ordinary task named "background_callback_<hash>" on THIS app,
so your own API tasks and Dash's tasks share one broker and one worker fleet.
"""

import time
from pathlib import Path

from celery import Celery

_QUEUE_DIR = Path(__file__).resolve().parent.parent / ".celery-demo"
for sub in ("in", "out", "processed", "results"):
    (_QUEUE_DIR / sub).mkdir(parents=True, exist_ok=True)

celery_app = Celery(
    "tools",
    broker_url="filesystem://",
    broker_transport_options={
        "data_folder_in": str(_QUEUE_DIR / "in"),
        "data_folder_out": str(_QUEUE_DIR / "in"),  # same dir: loopback queue
        "processed_folder": str(_QUEUE_DIR / "processed"),
        "store_processed": True,
    },
    result_backend=f"file://{_QUEUE_DIR / 'results'}",
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
)


# DEMO-ONLY shim: the filesystem result backend joins bytes paths with the
# str keys Dash's CeleryManager uses. Redis (production) accepts str keys,
# so none of this is needed there.
from celery.backends.filesystem import FilesystemBackend  # noqa: E402

_orig_filename = FilesystemBackend._filename


def _filename(self, key):
    if isinstance(key, str):
        key = key.encode()
    return _orig_filename(self, key)


FilesystemBackend._filename = _filename

_orig_delete = FilesystemBackend.delete


def _delete(self, key):
    try:
        _orig_delete(self, key)
    except FileNotFoundError:
        pass  # Redis DEL on a missing key is a no-op; mirror that


FilesystemBackend.delete = _delete


# ---- the team's OWN task, enqueued by FastAPI endpoints -------------------
@celery_app.task(name="tools.heavy_compute")
def heavy_compute(n: int) -> dict:
    """Stand-in for a computational tool invoked via the REST API."""
    time.sleep(2)
    return {"n": n, "result": sum(i * i for i in range(n))}
