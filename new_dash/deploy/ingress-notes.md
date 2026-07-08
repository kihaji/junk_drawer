# Kubernetes ingress: compression + HTTP/2

Compress at the edge, in exactly ONE layer. Keep `Dash(compress=False)` and no
GZipMiddleware in the app — Python-level compression burns worker CPU and the
a2wsgi threadpool.

ingress-nginx ConfigMap:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ingress-nginx-controller
data:
  use-gzip: "true"
  gzip-level: "5"
  gzip-types: "application/javascript application/json text/css text/html image/svg+xml"
  enable-brotli: "true"      # ~20-30% smaller than gzip; controller must be built with brotli
  brotli-level: "6"
  brotli-types: "application/javascript application/json text/css text/html image/svg+xml"
```

`application/json` matters as much as JS here: every `_dash-update-component`
callback response (figures!) and `_dash-layout` is JSON and compresses ~85-95%.

Caveat: community ingress-nginx was retired in March 2026 (no more security
fixes). If migrating to a Gateway API implementation or another controller,
carry the same compress-at-the-edge pattern over.

HTTP/2 is on by default for TLS in ingress-nginx (`use-http2: "true"`);
multiplexing makes unbundled per-file assets cheap — which is why
minify-without-bundle is sufficient.

Measured in this repo (localhost, so payload only — no latency effect):
gzip took the total initial-load wire size from 7.3 MB to 2.0 MB.
