"""Parameterized app factory — one code path, optimizations toggled by flags.

Every variant in apps/ is `create_app(...)` with different flags, so measured
differences are attributable to exactly one change.
"""

from __future__ import annotations

from pathlib import Path

import dash_mantine_components as dmc
import plotly.graph_objects as go
from dash import (
    ALL,
    ClientsideFunction,
    Dash,
    Input,
    Output,
    State,
    callback,
    clientside_callback,
    dcc,
    html,
    no_update,
)
from dash.exceptions import PreventUpdate

from common import factories as F

ROOT = Path(__file__).resolve().parent.parent
ASSETS = str(ROOT / "assets")


def create_app(
    *,
    title: str = "Dash optimization lab",
    keep_mounted: bool = True,
    lazy_tabs: bool = False,
    compress: bool = False,
    assets_folder: str = ASSETS,
    backend: str | None = None,
    server=None,
) -> Dash:
    """Build the 7-tab / 70-graph / 9-modal / 20-store app.

    keep_mounted : dmc.Tabs keepMounted — False leaves hidden panels
        unmounted (graphs don't render until the tab is visited).
    lazy_tabs    : build tab content server-side only on first activation
        (build-once pattern); implies the initial layout has empty panels.
    compress     : enable flask-compress gzip on Dash responses.
    backend      : Dash 4.2+ only — e.g. "fastapi" for the native ASGI
        backend (omit on Dash 3, where the kwarg doesn't exist).
    server       : Dash 4.2+ only — attach to an existing FastAPI instance.
    """
    extra = {}
    if backend is not None:
        extra["backend"] = backend
    if server is not None:
        extra["server"] = server
    app = Dash(
        __name__,
        assets_folder=assets_folder,
        title=title,
        compress=compress,
        # Lazy tab content means some component IDs (run-tool buttons, graphs)
        # are not in the initial layout; suppress startup validation for those.
        suppress_callback_exceptions=lazy_tabs,
        **extra,
    )

    # ------------------------------------------------------------------ layout
    if lazy_tabs:
        # Empty placeholder per panel; content is rendered on first visit.
        panels = [
            dmc.TabsPanel(html.Div(id={"type": "panel", "tab": i}), value=tid, pt="md")
            for i, tid in enumerate(F.TAB_IDS)
        ]
    else:
        panels = [
            dmc.TabsPanel(F.tab_panel_content(i), value=tid, pt="md")
            for i, tid in enumerate(F.TAB_IDS)
        ]

    tabs = dmc.Tabs(
        id="tabs",
        value=F.TAB_IDS[0],
        keepMounted=keep_mounted,
        children=[
            dmc.TabsList(
                [dmc.TabsTab(f"Tab {i}", value=tid) for i, tid in enumerate(F.TAB_IDS)]
            ),
            *panels,
        ],
    )

    modals = [
        dmc.Modal(id=mid, title=f"Modal {i}", children=F.modal_body(i), opened=False)
        for i, mid in enumerate(F.MODAL_IDS)
    ]
    modal_buttons = dmc.Group(
        [
            dmc.Button(f"Open modal {i}", id=f"open-{mid}", variant="light", size="xs")
            for i, mid in enumerate(F.MODAL_IDS)
        ]
    )

    stores = [dcc.Store(id=sid, storage_type="memory") for sid in F.TOOL_STORE_IDS] + [
        dcc.Store(id=sid, storage_type="memory", data={}) for sid in F.UI_STORE_IDS
    ]

    app.layout = dmc.MantineProvider(
        html.Div(
            [dmc.Title(title, order=3), modal_buttons, tabs, *modals, *stores],
            style={"padding": 16},
        )
    )

    # --------------------------------------------------------------- callbacks
    if lazy_tabs:
        _register_lazy_panel_callbacks()
    _register_tool_callbacks()
    _register_modal_callbacks()
    _register_ui_state_callbacks()
    return app


def _register_lazy_panel_callbacks() -> None:
    """Build-once: render a tab's content the first time it becomes active."""
    for i in range(F.N_TABS):

        @callback(
            Output({"type": "panel", "tab": i}, "children"),
            Input("tabs", "value"),
            State({"type": "panel", "tab": i}, "children"),
        )
        def render_panel(active, existing, i=i):
            if active != F.TAB_IDS[i] or existing:
                raise PreventUpdate
            return F.tab_panel_content(i)


def _register_tool_callbacks() -> None:
    for tab, store_id in enumerate(F.TOOL_STORE_IDS):

        @callback(
            Output(store_id, "data"),
            Input({"type": "run-tool", "tab": tab}, "n_clicks"),
            prevent_initial_call=True,
        )
        def run_tool(n_clicks, tab=tab):
            # prevent_initial_call does NOT stop this firing when the button
            # is inserted into the layout by a lazy-tab callback (see
            # https://dash.plotly.com/advanced-callbacks) — guard explicitly.
            if not n_clicks:
                raise PreventUpdate
            return F.make_tool_result(tab)

        @callback(
            Output({"type": "graph", "tab": tab, "idx": ALL}, "figure"),
            Input(store_id, "data"),
            prevent_initial_call=True,
        )
        def draw_graphs(data, tab=tab):
            if not data:
                return no_update
            step = max(1, len(data["x"]) // 500)
            x, y = data["x"][::step], data["y"][::step]
            figs = []
            for i in range(F.GRAPHS_PER_TAB):
                fig = go.Figure(go.Scatter(x=x, y=y, mode="markers"))
                fig.update_layout(title=f"Tab {tab} / Graph {i}", height=300)
                figs.append(fig)
            return figs

        clientside_callback(
            ClientsideFunction(namespace="tools", function_name="summarizeToolResult"),
            Output({"type": "tool-status", "tab": tab}, "children"),
            Input(store_id, "data"),
            prevent_initial_call=True,
        )


def _register_modal_callbacks() -> None:
    for i, mid in enumerate(F.MODAL_IDS):

        @callback(
            Output(mid, "opened"),
            Input(f"open-{mid}", "n_clicks"),
            prevent_initial_call=True,
        )
        def open_modal(n_clicks):
            return True

        @callback(
            Output(f"modal-{i}-result", "children"),
            Output(F.UI_STORE_IDS[i % len(F.UI_STORE_IDS)], "data", allow_duplicate=True),
            Input(f"modal-{i}-apply", "n_clicks"),
            State(f"modal-{i}-name", "value"),
            State(f"modal-{i}-choice", "value"),
            State(f"modal-{i}-amount", "value"),
            State(F.UI_STORE_IDS[i % len(F.UI_STORE_IDS)], "data"),
            prevent_initial_call=True,
        )
        def apply_modal(n_clicks, name, choice, amount, ui_state, i=i):
            ui_state = dict(ui_state or {})
            ui_state[f"modal-{i}"] = {"name": name, "choice": choice, "amount": amount}
            return f"applied: {name or '(no name)'} / {choice} / {amount}", ui_state


def _register_ui_state_callbacks() -> None:
    clientside_callback(
        ClientsideFunction(namespace="tools", function_name="markTabVisited"),
        Output(F.UI_STORE_IDS[-1], "data", allow_duplicate=True),
        Input("tabs", "value"),
        State(F.UI_STORE_IDS[-1], "data"),
        prevent_initial_call=True,
    )
