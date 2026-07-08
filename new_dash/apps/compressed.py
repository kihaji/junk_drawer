"""Variant 4 — compress=True (flask-compress): gzip/brotli on Dash responses,
including _dash-layout, callback responses, and served JS bundles.

In your K8s deployment this belongs at the ingress (nginx) level instead, but
this shows the payload difference.

Run:  uv run python -m apps.compressed
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.app_factory import create_app

app = create_app(title="Compressed responses", compress=True)
server = app.server

if __name__ == "__main__":
    app.run(debug=True, port=8054)
