"""Baseline — everything static in the initial layout, no optimizations.

Run:  uv run python -m apps.baseline
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.app_factory import create_app

app = create_app(title="Baseline")
server = app.server

if __name__ == "__main__":
    app.run(debug=True, port=8050)
