"""Variant 3 — partial plotly.js bundle: assets_partial/ contains
plotly-cartesian.min.js (1.3 MB vs ~4.5 MB full bundle). dcc.Graph detects
window.Plotly from the assets script and skips downloading async-plotlyjs.

Only valid if every trace type used is in the cartesian bundle
(scatter/bar/box/heatmap/etc. — no 3d, maps, or sankey).

Run:  uv run python -m apps.partial_plotly
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.app_factory import ROOT, create_app

app = create_app(
    title="Partial plotly.js bundle",
    assets_folder=str(ROOT / "assets_partial"),
)
server = app.server

if __name__ == "__main__":
    app.run(debug=True, port=8053)
