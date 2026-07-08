"""Variant 2 — build-once lazy tabs: panel content rendered by a callback the
first time its tab becomes active, then kept (keepMounted default True so
revisits are instant and preserve graph state).

Also shrinks the initial _dash-layout payload since hidden tab content is
never serialized into it.

Run:  uv run python -m apps.lazy_callback
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.app_factory import create_app

app = create_app(title="Lazy: build-once callback", lazy_tabs=True)
server = app.server

if __name__ == "__main__":
    app.run(debug=True, port=8052)
