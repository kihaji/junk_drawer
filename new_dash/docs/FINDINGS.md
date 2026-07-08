# Dash Optimization Investigation — Findings

Context: a Dash 3.x + dash-mantine-components app (7 tabs x ~10 graphs, 9
heavily-wired modals, ~20 dcc.Stores, unminified assets JS), mounted in
FastAPI under uvicorn on Kubernetes, with 2+ s initial page loads.

This repo reproduces that structure (`apps/baseline.py`) and measures each
optimization in isolation. Sources for every claim are linked at the end of
each section.

---

## Measured results (localhost, headless Chromium, median of 3 runs)

| Variant | Render-settled | Wire bytes | Graphs mounted |
|---|---|---|---|
| `apps/baseline` | 909 ms | 7.32 MB | 70 |
| `apps/lazy_keepmounted` (`keepMounted=False`) | 682 ms | 7.32 MB | 10 |
| `apps/lazy_callback` (build-once panels) | 850 ms | 8.03 MB* | 10 |
| `apps/partial_plotly` (cartesian bundle) | 548 ms | 3.82 MB | 70 |
| `apps/compressed` (gzip) | 916 ms | 2.02 MB | 70 |
| `apps/combined` (lazy + partial + gzip) | **388 ms** | **2.18 MB** | 10 |

\* build-once adds 7 initial panel-render callbacks; on localhost that shows
as extra requests, in production it trades a smaller `_dash-layout`
(30.8 kB → 14.5 kB) for one round trip per first tab visit.

**Localhost hides your real problem.** Download of 7.3 MB of JS is free on
loopback; on a real network it's most of your 2+ s. The settled-time column
shows the *render* cost (mostly `Plotly.newPlot` x 70); the wire column shows
the *network* cost. Production wins compound: combined = 57% less render time
AND 70% fewer bytes.

Measured separately in real Chrome (via browser instrumentation on
`_dash-update-component`):

| Callback | Upload | Download |
|---|---|---|
| `run_tool` → writes 570 kB store | 276 B | 569 kB |
| `draw_graphs` — store is a server-callback Input | **570 kB** | 157 kB |
| `summarizeToolResult` — clientside, reads same store | 0 (no request) | 0 |

---

## Q1. Initial page load / 70 empty graphs

**Verdict: this is your 2 seconds, and it's two separate costs.**

1. **Render cost.** An "empty" `dcc.Graph` is not free — plotly.js builds the
   full scaffolding (SVG layers, axes, drag/hover layers, resize observers)
   per graph, ~10–30 ms of main-thread work each. 70 at once ≈ 0.7–2 s.
2. **Network cost.** The full plotly.js async chunk is ~3.5 MB alone; with
   dash-renderer + dmc the baseline ships 7.3 MB of JS (2.0 MB gzipped).

**Fixes, in order of effort:**

- **One line:** `dmc.Tabs(keepMounted=False)`. Mantine unmounts hidden
  panels, so only the active tab's graphs render. The components stay in the
  Dash layout, so **no callback changes at all** — pattern-matching outputs to
  hidden graphs match nothing and apply when the panel mounts. Cost: each tab
  switch re-runs ~10 x `newPlot` (~100–300 ms) and plotly-internal UI state
  (zoom not written back to `figure`) resets — use `uirevision` in figures.
- **Bigger, structural:** build-once lazy panels (`apps/lazy_callback.py`):
  panels start empty, a callback renders content on first activation, then
  `PreventUpdate` keeps it (revisits are instant, state preserved, since
  `keepMounted` stays True). Also shrinks `_dash-layout` by half. Requires
  `suppress_callback_exceptions=True` (or `app.validation_layout`) and one
  round trip on first visit of each tab.
- **Placeholder divs:** where graphs are empty until a tool runs anyway,
  render an `html.Div` skeleton and swap in the `dcc.Graph` with the data.
  You avoid paying `newPlot` for graphs that show nothing.
- **Partial plotly.js bundle:** drop `plotly-cartesian.min.js` (1.3 MB vs
  ~4.5 MB) into `assets/` — dcc.Graph uses it instead of downloading the full
  async chunk. Only if every trace type you use is in the bundle (cartesian =
  scatter/bar/box/heatmap/…, no 3d/maps/sankey). Silent non-render if you use
  a missing trace type, and you must update the file when upgrading plotly.
  Measured: fastest single-change render win (548 ms) because parsing 1.3 MB
  is much cheaper than 4.5 MB.
- If tabs are genuinely independent views, **Dash Pages** (`dash.page_container`)
  is the strongest lazy form — a page's layout is only fetched when navigated
  to — at the cost of re-instantiating layouts per navigation (state must
  live in stores).

Sources: [dmc.Tabs](https://www.dash-mantine-components.com/components/tabs) ·
[Mantine Tabs keepMounted](https://mantine.dev/core/tabs/) ·
[dcc.Graph](https://dash.plotly.com/dash-core-components/graph) ·
[dcc.Tabs content-as-callback](https://dash.plotly.com/dash-core-components/tabs) ·
[plotly.js partial bundles](https://github.com/plotly/plotly.js/blob/master/dist/README.md) ·
[async-plotlyjs size thread](https://community.plotly.com/t/smaller-version-of-async-plotlyjs-js-its-so-big-and-loads-so-slow/42247)

## Q2. Nine modals → one swapped modal?

**Verdict: don't. Keep the 9 modals; they're already nearly free.**

- `dmc.Modal` defaults to `keepMounted=False` and renders via a portal —
  a **closed modal mounts zero DOM nodes**. Nine closed modals cost only
  their share of `_dash-layout` JSON (a few kB of form controls — noise next
  to 70 graphs).
- The single-swapped-modal refactor is expensive *because* your modals are
  heavily wired: callbacks whose Input/State live in swapped-out content
  either silently never fire (all Inputs missing) or throw "nonexistent
  object" errors (State missing when another Input fires). Working around
  that needs `suppress_callback_exceptions` + `allow_optional` (Dash 3.1+) /
  `optional=True` (Dash 3.3+) on many dependencies, `allow_duplicate` fan-in
  on the shared modal, and you lose typed-in state on every swap plus a
  round trip before each modal opens.

**Do instead:**
1. Ensure every modal-internal callback has `prevent_initial_call=True` —
   the initial-callback storm is the real modal-related load cost.
2. Make open/close clientside or one pattern-matching MATCH callback —
   removes ~18 server callbacks, opens become instant.
3. If one modal has genuinely heavy children (big table/graph), lazy-load
   just those children on first open — surgical, not wholesale.

Sources: [dmc.Modal](https://www.dash-mantine-components.com/components/modal) ·
[callback gotchas](https://dash.plotly.com/callback-gotchas) ·
[advanced callbacks / allow_optional](https://dash.plotly.com/advanced-callbacks) ·
[validation_layout](https://dash.plotly.com/urls) ·
[pattern-matching callbacks](https://dash.plotly.com/pattern-matching-callbacks)

## Q3. Twenty dcc.Stores with large data

**Verdict: store COUNT is a non-issue. Store SIZE x server-callback coupling
is the issue — and you have both patterns, so split them.**

Measured here: a 570 kB store consumed by one server-side callback re-uploads
its **entire contents on every trigger** (State is not cheaper than Input on
the wire). At your 1–10 MB, that's 2–4+ s of upload per trigger on a typical
uplink before your Python even runs. The same store read clientside made
zero requests.

Decision framework:

| Situation | Verdict |
|---|---|
| Small (<100 kB) UI-state stores as State in many server callbacks | Fine — non-issue. Many small stores is the RIGHT shape; keep one writer per store. |
| Large tool-result store, `memory`, read only clientside | Fine — near-zero cost after the initial write. |
| Large store with `storage_type='session'/'local'` | Fix — JSON.stringify on every write on the main thread + 5–10 MB quota. Use `memory`. |
| Large store as Input/State on ANY server callback | **Your slowdown.** Drop the dependency or move data server-side. |
| Server callback rewrites a large store wholesale | Use `Patch()` to append/assign only the delta. |

**Patterns to adopt:**

- **Hard partition by consumer.** Tool-result stores: written once (or
  Patch-appended), read only by clientside callbacks. Enforce by naming
  convention (`id={"role": "cs", ...}`) and audit with the dev-tools
  callback graph.
- **Server-side data with a token store** when the server also needs the
  data: cache the payload server-side (flask-caching/Redis/diskcache keyed
  per session), put only `{"key": ..., "version": n}` (~100 B) in the store.
  `dash-extensions`' `ServersideOutputTransform` packages this pattern.
  If data is needed both clientside AND serverside, ship it to the browser
  once and ALSO keep it in the server cache — the token doubles as the
  version signal for both.
- **`Patch()` for growth over time** — append tool results without
  re-shipping the accumulated store from the server (docs example: 368 kB
  full update → 380 B patch). Limits: Patch can't read current values, and
  the browser still holds (and grows) the full object — prune explicitly.
  Dash 3.3 adds `dash_clientside.Patch` for the same on the client side.
- Long tool runs: **background callbacks** (Celery+Redis in production)
  writing to the cache, callback returns the token.
- `pip install orjson` — Dash uses it automatically; meaningful for
  serializing large store writes.

Sources: [sharing data between callbacks](https://dash.plotly.com/sharing-data-between-callbacks) ·
[dcc.Store reference](https://dash.plotly.com/dash-core-components/store) ·
[Store.react.js (deep-equals + storage behavior)](https://github.com/plotly/dash/blob/dev/components/dash-core-components/src/components/Store.react.js) ·
[Patch / partial properties](https://dash.plotly.com/partial-properties) ·
[serverside caching show-and-tell](https://community.plotly.com/t/show-and-tell-server-side-caching/42854) ·
[background callbacks](https://dash.plotly.com/background-callbacks)

## Q4. Minifying assets JS in the FastAPI/uvicorn/K8s deployment

**Verdict: Dash does zero minification of your assets (its own bundles are
already minified when `debug=False`). Minify at image build time with
esbuild; compress at the ingress; long-cache assets.**

- **esbuild in a multi-stage Docker build** (`deploy/Dockerfile`): per-file
  `--minify --sourcemap --target=es2020`, **in place** (same filenames — a
  `foo.min.js` next to `foo.js` would be auto-included twice), **no
  `--bundle`** (changes scoping/ordering for no gain under HTTP/2).
  Minifying never renames `window.dash_clientside.ns.fn` assignments, so
  `ClientsideFunction` references keep working. Skip Python-only minifiers
  (rjsmin/jsmin) — regex-based, unsafe on modern JS.
- **Sourcemaps: ship the external `.map` files.** Browsers fetch them only
  when devtools is open — zero cost to users, debuggable prod stack traces.
- **Inline clientside-callback strings** are embedded in the index HTML —
  re-downloaded every page load, never minified by your build. Keep only
  one-liners inline; move everything substantial to `assets/` via
  `ClientsideFunction` (identical runtime behavior, but cacheable/minifiable).
- **Compression: at the nginx ingress, one layer only** (gzip level ~5 +
  brotli; include `application/json` — callback responses and `_dash-layout`
  compress 85–95%). Keep `Dash(compress=False)`. Measured here: 7.3 MB →
  2.0 MB. See `deploy/ingress-notes.md`.
- **Caching:** Dash's component bundles are content-fingerprinted and
  already served with 1-year cache. Your assets get `?m=<mtime>`
  cache-busting automatically but NO max-age — add
  `server.config["SEND_FILE_MAX_AGE_DEFAULT"] = timedelta(days=365)`.
- **Mounting specifics** (`deploy/serve_fastapi.py`):
  - Use `a2wsgi.WSGIMiddleware` — Starlette/FastAPI's WSGIMiddleware is
    deprecated. Its threadpool (default **10 workers**) is your Dash
    concurrency ceiling per pod; every callback occupies one thread. Size
    `workers=`, keep callbacks fast, scale with HPA replicas rather than
    in-pod uvicorn workers.
  - Mount `StaticFiles` for `/assets` BEFORE the Dash mount so asset requests
    bypass the Flask threadpool entirely.
  - Longer term: Dash 4.2+ supports `backend="fastapi"` natively — no WSGI
    bridge at all. An upgrade project, but the endgame for this stack.

Sources: [external resources / assets](https://dash.plotly.com/external-resources) ·
[Dash reference (compress, serve_locally)](https://dash.plotly.com/reference) ·
[clientside callbacks](https://dash.plotly.com/clientside-callbacks) ·
[a2wsgi](https://github.com/abersheeran/a2wsgi) ·
[Starlette WSGI deprecation](https://github.com/encode/starlette/issues/1503) ·
[ingress-nginx ConfigMap](https://kubernetes.github.io/ingress-nginx/user-guide/nginx-configuration/configmap/)

## Q5. Other optimizations worth adopting (ranked)

1. **Measure first, always**: dev-tools callback graph (compute vs network
   time per callback), browser Network tab filtered to `_dash-layout` /
   `_dash-update-component`, and throttle to "Fast 4G" — localhost lies.
2. **Kill the initial callback storm**: `Dash(prevent_initial_callbacks=True)`
   app-wide, opt back in per callback. Suppressed callbacks make no request
   at all.
3. **Clientside callbacks for UI-only logic** — zero round trip, zero worker
   time (you already do this; extend it).
4. **`Patch` / `extendData` instead of returning whole figures** (docs
   example: 368 kB → 380 B); `uirevision` to preserve zoom when you must
   return full figures.
5. **Flatten callback chains** — each link is a full round trip; combine with
   multi-output callbacks and `ctx.triggered_id`.
6. **Memoize expensive data work** with flask-caching (Redis) so results are
   shared across workers and callbacks.
7. **orjson + NumPy arrays**: plotly.py 6 base64-encodes typed arrays —
   up to ~10x faster figure serialization vs Python lists; orjson speeds
   Dash's JSON responses (docs cite up to 750 ms on data-heavy callbacks).
8. **Production hygiene**: `debug=False`, all `dev_tools_*` off; readiness
   probe on a cheap route.
9. **Big traces**: `scattergl` past ~15k points (mind the ~8–16 WebGL context
   browser cap — another reason not to mount 70 graphs), plotly-resampler
   for large time series.
10. **Background callbacks** for tool runs that exceed a few seconds, so
    they don't pin the a2wsgi threadpool.

Full research reports with all citations were gathered from
dash.plotly.com, dash-mantine-components.com, Mantine docs, the plotly/dash
source and CHANGELOG, community.plotly.com, and FastAPI/Starlette/a2wsgi
docs and issues.

---

## Q6. Dash 4.2+ and the native FastAPI backend

**Verdict: worth adopting, in two phases. Dash 4 doesn't make rendering
faster — every optimization above still applies — but the native FastAPI
backend removes the WSGI bridge and fits the "tools API + Dash UI in one
FastAPI app" architecture exactly. One critical caveat: callbacks must
become `async def`.**

The `dash4/` sub-project runs the same lab on Dash 4.4.0 (dmc 2.8.0 resolves
cleanly; dmc is developed/tested against Dash 4).

### Measured (same benchmark, Dash 4.4)

| Variant | Render-settled | Wire bytes |
|---|---|---|
| baseline, Flask backend (dash 4) | 1,010 ms | 7.13 MB |
| baseline, FastAPI backend (`apps/d4_fastapi`) | 1,006 ms | 7.13 MB |
| combined, FastAPI backend (`apps/d4_combined`) | 456 ms | 2.10 MB |

Same story as Dash 3 (909 ms / 388 ms) within noise: the renderer is not
faster for this workload, backend choice doesn't affect client rendering,
and lazy tabs + partial plotly + compression deliver the same ~2.2x render
and ~70% wire reduction. `compress=True` works on the FastAPI backend
(implemented as Starlette GZipMiddleware).

### What Dash 4 changes (research summary)

- **4.0 is a dcc UI redesign, not an API break** — "all props remain the
  same", but every dcc form component looks different and custom CSS
  targeting dcc internals breaks (new CSS-variable theming). dmc-heavy apps
  are mostly insulated; QA any bare `dcc.*` inputs. React stays 18.3.1, so
  dmc 2.x carries over. No official migration guide; the 4.0 blog + CHANGELOG
  are it. 4.4 requires Python ≥3.9.
- **4.2 "Freedom Update"**: `Dash(backend="fastapi")` or — your case —
  `Dash(server=your_fastapi_app)`. Verified here: tools API routes registered
  at import time win over Dash's catch-all (it's added lazily at lifespan
  startup), `/docs` keeps working, async `def` callbacks run natively on the
  event loop (verified end-to-end in `deploy/serve_dash4_native.py`).
- **WebSocket callbacks** (opt-in, 4.2+): `set_props` streaming mid-callback,
  persistent callbacks — interesting for streaming tool progress into the UI
  without `dcc.Interval` polling. Needs `uvicorn[standard]` and a
  WS-passing ingress; use ≥4.3 for the proxy-path fix.

### Gotchas verified or sourced

1. **Sync callbacks block the event loop on the FastAPI backend.** The
   dispatch handler is async and does NOT offload sync callbacks to a
   threadpool (source-level finding in `dash/backends/_fastapi.py`). Your
   current a2wsgi setup at least gives sync callbacks 10+ threads; a naive
   switch could REGRESS concurrency. Convert callbacks to `async def`
   (awaiting I/O) or wrap blocking work in `anyio.to_thread.run_sync`.
2. **Unknown GET paths return the Dash index (200), not 404** — the
   catch-all has no prefix. Add an `/api/{path:path}` 404 guard so typo'd
   API URLs don't get HTML.
3. **The extension/devtools may show PreventUpdate responses oddly** — the
   server actually returns 204 (verified against uvicorn access logs).
4. **Lazy tabs + `prevent_initial_call=True` gotcha (applies to Dash 3
   too):** callbacks whose Input is *inserted* into the layout by another
   callback fire anyway on insertion. Observed live: visiting a lazy tab
   auto-ran its tool. Guard with `if not n_clicks: raise PreventUpdate`.
5. **Flask-isms don't carry over**: flask-caching → your own cache
   (Redis/fastapi-cache); `SEND_FILE_MAX_AGE_DEFAULT` → add a middleware
   setting `Cache-Control` on `/assets`; `before_request` → Starlette
   middleware (which now natively covers Dash traffic — a win vs the WSGI
   bridge). Component bundles keep their 1-year fingerprint caching.
6. **Dev-mode open bug**: callbacks double-register under
   `uvicorn --reload` with `backend="fastapi"` (plotly/dash#3818).
7. **Maturity**: the backend GA'd 2026-06-01; 4.3/4.4 were partly fastapi
   fixes (POST middleware deadlock, catch-all RuntimeError, WS scaling).
   Pin `dash>=4.4`. Early-adopter territory for another release or two;
   the Flask backend + a2wsgi remains a fully supported fallback on Dash 4.

### Migration plan for your app

- **Phase 1 (low risk, ~days):** Dash 3.x → 4.4 keeping WSGIMiddleware
  unchanged. Visual QA for the dcc redesign; no code changes expected.
- **Phase 2 (medium, ~1 week + soak):** drop the WSGI bridge —
  `Dash(server=your_fastapi_app)`, uvicorn entrypoint becomes the FastAPI
  app. Convert callbacks to `async def`. Add the `/api` 404 guard. Replace
  flask-caching/config usages. Optionally adopt WS callbacks for tool
  progress streaming.

Working example of the target architecture: `deploy/serve_dash4_native.py`
(tools API + lazy-tab Dash UI + async callback on one FastAPI app).

Sources: [Server Backends docs](https://dash.plotly.com/server-backends) ·
[Dash 4.2 backend blog](https://plotly.com/blog/dash-4.2-choose-your-backend-fastapi-and-quart-support) ·
[Dash 4.0 dcc refresh blog](https://plotly.com/blog/dash-core-components-gets-a-design-driven-refresh-with-dash-4/) ·
[CHANGELOG](https://github.com/plotly/dash/blob/dev/CHANGELOG.md) ·
[WebSocket callbacks](https://dash.plotly.com/websocket-callbacks) ·
[dash/backends/_fastapi.py](https://github.com/plotly/dash/blob/dev/dash/backends/_fastapi.py) ·
[plotly/dash#3818](https://github.com/plotly/dash/issues/3818)

---

## Q7. Background callbacks on Dash 4 + sharing Celery with the tools API

**Verdict: background callbacks work unchanged under the FastAPI backend
(pin ≥4.3), and the API side does NOT need its own task system — one Celery
app serves both.** Verified live here: `deploy/serve_dash4_background.py`
runs a Dash `background=True` callback (progress bar, `running=` button
disable, final result) and a FastAPI-enqueued task through the SAME Celery
worker; the worker's task list shows `background_callback_<hash>` and
`tools.heavy_compute` side by side.

### Mechanics (unchanged from Dash 2/3)

- `@callback(background=True, running=..., progress=..., cancel=...)` with a
  `CeleryManager(celery_app)` (production) or `DiskcacheManager` (dev only).
- No `dcc.Interval` needed: dash-renderer polls `_dash-update-component`
  every `interval` ms (default 1000) with a `cacheKey`/`job`; the server
  returns progress until the result is in the Celery result backend.
  This flow is backend-agnostic — identical under FastAPI.
- Version notes: **4.2's FastAPI backend broke background callbacks**
  (context serialization crash, fixed in 4.3 #3817); 4.4 fixed error
  handling in `async def` background callbacks (#3822) — yes, the callback
  body may be async in 4.4 (run via `asyncio.run` inside the worker).

### Sharing one Celery app (the key architectural answer)

`CeleryManager` wraps a **normal, user-constructed `Celery` instance** and
registers each background callback on it as an ordinary task named
`background_callback_<sha256(callback id + source)>`. Nothing is exclusive:
register your own tasks on the same app and `.delay()` them from FastAPI
endpoints. Recommended split:

```python
celery_app.conf.task_routes = {
    "background_callback_*": {"queue": "dash"},  # UI jobs
    "api.tasks.*":           {"queue": "api"},   # tools API jobs
}
```

Gotchas, all verified or sourced:
- **The worker must import the Dash app module** — the
  `background_callback_*` tasks only register as a side effect of the
  `@callback(background=True)` decorators running. Symptom of a miss:
  "Received unregistered task of type background_callback_…".
- **Web and worker must run byte-identical callback source** — the task
  name hashes the callback's source code, so version skew silently breaks
  dispatch. Deploy both from the same image tag; restart workers on every
  deploy.
- **What crosses the broker**: not a pickled function — just
  `(result_key, progress_key, JSON args, serialized context)`; results are
  JSON (`PlotlyJSONEncoder`) in the result backend.
- **Pool choice**: prefork (default) — `cancel=` uses
  `control.terminate()`, which only kills tasks on prefork; `--pool=solo/
  threads` can't cancel mid-run.
- The demo uses a filesystem broker/backend to avoid needing Redis; the two
  shims in `deploy/celery_shared.py` (str→bytes keys, delete-missing-key
  no-op) are filesystem-backend-only artifacts — Redis needs neither.

### FastAPI-side background processing: recommendation

| Option | Verdict |
|---|---|
| Reuse the Dash Celery app for API tasks | **Yes — recommended.** One broker, one worker fleet split by queue, one monitoring stack. |
| FastAPI `BackgroundTasks` | Only for fire-and-forget trivia (emails, cache pokes) — in-process, dies with the pod, no status/retry. Not for tools. |
| Second queue system (arq/dramatiq/taskiq) | Two job systems to operate for no capability gain — Dash's manager is Celery-only. Avoid. |

### WebSocket callbacks are a complement, not a replacement

WS callbacks (4.2+, FastAPI/Quart only) run **in-process** in the web pod —
no broker, no persistence; a pod restart or dropped socket loses the work.
Use background callbacks for minutes-long, cancellable, restart-surviving
tool runs; use WS (`persistent=True`, `set_props` streaming) for
latency-sensitive live updates. There is no `background=True, websocket=True`
combo; the practical hybrid is a Celery job writing progress that a WS or
polling callback surfaces.

### K8s shape

Web pods (uvicorn, FastAPI+Dash) + worker pods (`celery -A app:celery_app
worker -Q dash,api`) + Redis (broker AND result backend; set
`result_expires`). Same image for web and worker (source-hash rule above).
Scale workers on queue depth (KEDA on Redis list length); liveness probe via
`celery inspect ping`. Background-callback polling is stateless HTTP — no
sticky sessions; only WS callbacks need ingress WebSocket support.

Sources: [background callbacks](https://dash.plotly.com/background-callbacks) ·
[celery_manager.py](https://github.com/plotly/dash/blob/dev/dash/background_callback/managers/celery_manager.py) ·
[managers/__init__.py (task-name hash)](https://github.com/plotly/dash/blob/dev/dash/background_callback/managers/__init__.py) ·
[#3817 (4.3 fix)](https://github.com/plotly/dash/pull/3817) ·
[#3822 (4.4 async fix)](https://github.com/plotly/dash/pull/3822) ·
[websocket callbacks](https://dash.plotly.com/websocket-callbacks) ·
[community: Celery+Redis monitoring showcase](https://community.plotly.com/t/creating-and-monitoring-background-tasks-with-celery-and-redis/90458) ·
[Celery concurrency/pools](https://docs.celeryq.dev/en/latest/userguide/concurrency/index.html)

---

## Recommended sequence for your real app

1. `dmc.Tabs(keepMounted=False)` + audit `prevent_initial_call` everywhere
   (one afternoon, no architecture change).
2. Ingress gzip/brotli + `SEND_FILE_MAX_AGE_DEFAULT` + esbuild build stage
   (deploy-only changes, no app code).
3. Audit which server callbacks take large stores as Input/State (Network
   tab: any `_dash-update-component` request uploading >100 kB). Break those
   dependencies — clientside where possible, token + server-side cache where
   not.
4. Partial plotly.js bundle if your trace types allow it.
5. Consider build-once lazy panels and placeholder-div graph swap for the
   heaviest tabs.
6. Leave the modals alone.
7. Upgrade to Dash 4.4 on the current architecture (Phase 1), then adopt the
   native FastAPI backend with async callbacks (Phase 2) — see Q6.
