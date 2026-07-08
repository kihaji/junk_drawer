"""Single-modal Plotly Dash app built with dash-mantine-components.

Layout (see modal.png):
    Modal (opened on load)
    ├── Box                     -> placeholder for a future map
    └── Fieldset "Filters"
        ├── DateInput "From"  +  DateInput "To"   (side by side)
        ├── MultiSelect "Sources"                 (capped to a single row)
        └── TextInput  "Ids"

The Sources MultiSelect must never grow taller than one row. Mantine 7's
MultiSelect has no built-in "+N more" behaviour, so that is handled in
assets/multiselect_singlerow.js (a class-name-agnostic MutationObserver).
"""

from dash import Dash, Input, Output, State, _dash_renderer, callback, html
import dash_mantine_components as dmc

# dash-mantine-components 2.x renders against React 18.
_dash_renderer._set_react_version("18.2.0")

app = Dash(__name__)
server = app.server

# Static sample data so the single-row overflow is easy to exercise.
SOURCE_OPTIONS = [
    {"value": "src_a", "label": "Source A"},
    {"value": "src_b", "label": "Source B"},
    {"value": "src_c", "label": "Source C"},
    {"value": "src_d", "label": "Source D"},
    {"value": "src_e", "label": "Source E"},
    {"value": "src_f", "label": "Source F"},
    {"value": "src_g", "label": "Source G"},
    {"value": "src_h", "label": "Source H"},
]


def map_placeholder() -> dmc.Box:
    """Bordered box that a Plotly map figure will live in later."""
    return dmc.Box(
        children=dmc.Center(
            dmc.Text("Map goes here", c="dimmed", size="sm"),
            h="100%",
        ),
        h=240,
        style={
            "border": "1px solid var(--mantine-color-gray-4)",
            "borderRadius": "var(--mantine-radius-md)",
        },
    )


def filters_fieldset() -> dmc.Fieldset:
    """The blue area in the mock-up: the filter controls."""
    date_row = dmc.Group(
        children=[
            dmc.DateInput(
                id="filter-from",
                label="From",
                placeholder="Start date",
                valueFormat="YYYY-MM-DD",
                w="100%",
            ),
            dmc.DateInput(
                id="filter-to",
                label="To",
                placeholder="End date",
                valueFormat="YYYY-MM-DD",
                w="100%",
            ),
        ],
        grow=True,
        wrap="nowrap",
    )

    # Wrapper keeps our overflow badge positioned relative to the input.
    sources = dmc.Box(
        className="ms-wrapper",
        children=[
            dmc.MultiSelect(
                id="filter-sources",
                label="Sources",
                placeholder="Select sources",
                data=SOURCE_OPTIONS,
                searchable=True,
                clearable=True,
                className="single-row-ms",
            ),
            # Populated/positioned entirely by the assets JS module.
            html.Div(className="ms-overflow-badge"),
        ],
    )

    ids = dmc.TextInput(
        id="filter-ids",
        label="Ids",
        placeholder="Comma-separated ids",
    )

    return dmc.Fieldset(
        legend="Filters",
        children=dmc.Stack([date_row, sources, ids], gap="md"),
    )


def modal() -> dmc.Modal:
    return dmc.Modal(
        id="main-modal",
        opened=True,
        title="Query",
        size="lg",
        centered=True,
        closeOnClickOutside=False,
        children=dmc.Stack(
            children=[map_placeholder(), filters_fieldset()],
            gap="lg",
        ),
    )


app.layout = dmc.MantineProvider(
    children=dmc.Box(
        children=[
            dmc.Button("Open modal", id="open-modal", variant="light", m="md"),
            modal(),
        ]
    )
)


@callback(
    Output("main-modal", "opened"),
    Input("open-modal", "n_clicks"),
    State("main-modal", "opened"),
    prevent_initial_call=True,
)
def reopen_modal(_n_clicks, opened):
    """Lets the user reopen the modal after closing it (it starts open)."""
    return True if not opened else opened


if __name__ == "__main__":
    app.run(debug=True)
