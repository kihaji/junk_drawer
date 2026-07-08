# Dash optimization lab

Experiments measuring initial-page-load and data-transfer optimizations for
a Dash 3.x + dash-mantine-components app (7 tabs x 10 graphs, 9 modals,
20 stores). **Conclusions and the full write-up: [docs/FINDINGS.md](docs/FINDINGS.md).**

## Setup

Everything runs through uv (`uv sync` recreates the environment; Playwright's
chromium is installed via `uv run playwright install chromium`).

## Layout

- `common/app_factory.py` — one parameterized app; every optimization is a flag
- `common/factories.py` — shared component builders (tabs, graphs, modals, stores)
- `apps/` — six Dash 3 variants: `baseline`, `lazy_keepmounted`,
  `lazy_callback`, `partial_plotly`, `compressed`, `combined`. Each runs
  standalone: `uv run python -m apps.baseline`
- `apps/d4_*` + `dash4/` — Dash 4.4 sub-project (own venv). Run with
  `dash4/.venv/bin/python -m uvicorn apps.d4_fastapi:server --port 8056`;
  benchmark with `--python dash4/.venv/bin/python --asgi`
- `assets/` — non-minified clientside JS (mirrors the real app);
  `assets_partial/` adds the 1.3 MB plotly.js cartesian bundle
- `benchmarks/measure.py` — headless-Chromium page-load benchmark:
  `uv run python benchmarks/measure.py apps.baseline --runs 3`
- `benchmarks/measure_stores.py` — captures `_dash-update-component` payload
  sizes for one tool run (store wire-cost demo)
- `deploy/` — production pieces: Dash 3 FastAPI mount via a2wsgi
  (`serve_fastapi.py`), Dash 4.2+ native mount with tools API + async
  callbacks (`serve_dash4_native.py`), background callbacks + ONE Celery app
  shared by Dash and the API (`serve_dash4_background.py` +
  `celery_shared.py`; filesystem broker so no Redis needed locally),
  multi-stage Dockerfile with esbuild minification, ingress compression notes

## Headline numbers (localhost, median of 3)

| Variant | Render-settled | Wire bytes |
|---|---|---|
| baseline | 909 ms | 7.3 MB |
| combined (lazy tabs + partial plotly + gzip) | 388 ms | 2.2 MB |

And the store demo (real Chrome): a 570 kB store used as a server-callback
Input re-uploads all 570 kB on every trigger; the same store read by a
clientside callback makes no network request at all.


Also

Use fastapi-offline instead of the hand rolled stuff
plotly.js-cartesian-dist-min is a npm lib
