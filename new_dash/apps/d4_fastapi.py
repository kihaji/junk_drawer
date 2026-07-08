"""Dash 4.2+ native FastAPI backend — same app, no WSGI bridge.

Requires the dash4/ environment:
  uv run --project dash4 --no-sync python -m apps.d4_fastapi
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.app_factory import create_app

app = create_app(title="Dash 4 native FastAPI backend", backend="fastapi")
server = app.server  # a fastapi.FastAPI instance

if __name__ == "__main__":
    app.run(debug=True, port=8056)
