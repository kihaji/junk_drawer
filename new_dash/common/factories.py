"""Shared component factories used by both the baseline and optimized apps.

The goal is that both apps render *identical* content so that any timing
difference comes from HOW the content is delivered, not WHAT is rendered.
"""

from __future__ import annotations

import numpy as np
import dash_mantine_components as dmc
from dash import dcc, html

N_TABS = 7
GRAPHS_PER_TAB = 10
N_MODALS = 9

TAB_IDS = [f"tab-{i}" for i in range(N_TABS)]
MODAL_IDS = [f"modal-{i}" for i in range(N_MODALS)]

# ~20 stores, mirroring the real app: a large "tool result" store per tab
# (populated over time as tools run) plus assorted UI-state stores.
TOOL_STORE_IDS = [f"store-tool-{i}" for i in range(N_TABS)]  # 7 large stores
UI_STORE_IDS = [f"store-ui-{i}" for i in range(13)]  # 13 small UI-state stores


def empty_graph(tab: int, idx: int) -> dcc.Graph:
    """One empty graph, as in the real app before any tool has run."""
    return dcc.Graph(
        id={"type": "graph", "tab": tab, "idx": idx},
        figure={"data": [], "layout": {"title": {"text": f"Tab {tab} / Graph {idx}"}}},
        style={"height": 300},
    )


def tab_panel_content(tab: int) -> html.Div:
    """The full content of one tab: a tool-run button plus 10 empty graphs."""
    return html.Div(
        [
            dmc.Group(
                [
                    dmc.Button(f"Run tool {tab}", id={"type": "run-tool", "tab": tab}),
                    dmc.Text(id={"type": "tool-status", "tab": tab}, size="sm"),
                ]
            ),
            dmc.SimpleGrid(
                cols=2,
                children=[empty_graph(tab, i) for i in range(GRAPHS_PER_TAB)],
            ),
        ]
    )


def modal_body(i: int) -> list:
    """Interactive modal contents — IDs are referenced by server callbacks."""
    return [
        dmc.TextInput(id=f"modal-{i}-name", label="Name", placeholder="value..."),
        dmc.Select(
            id=f"modal-{i}-choice",
            label="Choice",
            data=[{"value": v, "label": v.title()} for v in ("alpha", "beta", "gamma")],
            value="alpha",
        ),
        dmc.NumberInput(id=f"modal-{i}-amount", label="Amount", value=10),
        dmc.Group(
            [
                dmc.Button("Apply", id=f"modal-{i}-apply"),
                dmc.Text(id=f"modal-{i}-result", size="sm"),
            ],
            mt="md",
        ),
    ]


def make_tool_result(tab: int, size_kb: int = 2000) -> dict:
    """Simulate a large tool result (~size_kb of JSON once serialized)."""
    n = size_kb * 16  # ~16 floats/kB as JSON text
    rng = np.random.default_rng(tab)
    return {
        "tab": tab,
        "x": rng.random(n).round(6).tolist(),
        "y": rng.random(n).round(6).tolist(),
    }
