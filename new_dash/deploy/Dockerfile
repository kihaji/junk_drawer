# Multi-stage build: minify assets JS/CSS with esbuild, then a slim Python
# runtime. Dev checkouts stay unminified; every prod image is minified.

# ---- stage 1: minify assets --------------------------------------------
FROM node:22-alpine AS assetbuild
WORKDIR /build
COPY assets ./assets
RUN npm install -g esbuild@0.25 && \
    find assets -name '*.js' -exec sh -c \
      'esbuild "$1" --minify --sourcemap --target=es2020 --outfile="$1" --allow-overwrite' _ {} \; && \
    find assets -name '*.css' -exec sh -c \
      'esbuild "$1" --minify --outfile="$1" --allow-overwrite' _ {} \;
# Notes:
#  * minify IN PLACE (same filenames) — a foo.min.js next to foo.js would be
#    auto-included by Dash a second time, and same names preserve load order
#    and window.dash_clientside namespace references.
#  * no --bundle: per-file minify only; bundling changes scoping/ordering
#    for no real gain under HTTP/2.
#  * --sourcemap ships external .map files; browsers fetch them only when
#    devtools is open, so prod users pay nothing.

# ---- stage 2: runtime ----------------------------------------------------
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY . .
COPY --from=assetbuild /build/assets ./assets

# One uvicorn worker per pod; scale with HPA replicas, not in-pod workers.
CMD ["uv", "run", "uvicorn", "deploy.serve_fastapi:fastapi_app", \
     "--host", "0.0.0.0", "--port", "8000"]
