"""Variant 1 — dmc.Tabs(keepMounted=False): hidden panels stay unmounted.

One-line change: only the active tab's 10 graphs render at load. Layout JSON
and callbacks are unchanged.

Run:  uv run python -m apps.lazy_keepmounted
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.app_factory import create_app

app = create_app(title="Lazy: keepMounted=False", keep_mounted=False)
server = app.server

if __name__ == "__main__":
    app.run(debug=True, port=8051)
