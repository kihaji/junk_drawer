"""Dash 4 + native FastAPI backend + all optimizations (lazy build-once tabs,
partial plotly bundle, compression).

Requires the dash4/ environment:
  uv run --project dash4 --no-sync python -m apps.d4_combined
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.app_factory import ROOT, create_app

app = create_app(
    title="Dash 4 combined",
    lazy_tabs=True,
    compress=True,
    assets_folder=str(ROOT / "assets_partial"),
    backend="fastapi",
)
server = app.server

if __name__ == "__main__":
    app.run(debug=True, port=8057)
