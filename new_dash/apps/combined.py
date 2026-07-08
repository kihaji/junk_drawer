"""Variant 5 — everything together: build-once lazy tabs + partial plotly
bundle + compression. The "apply all recommendations" configuration.

Run:  uv run python -m apps.combined
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.app_factory import ROOT, create_app

app = create_app(
    title="Combined optimizations",
    lazy_tabs=True,
    compress=True,
    assets_folder=str(ROOT / "assets_partial"),
)
server = app.server

if __name__ == "__main__":
    app.run(debug=True, port=8055)
