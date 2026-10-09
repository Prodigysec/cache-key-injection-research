"""
Minimal "edge cache" simulator standing in for Cloudflare in the local lab.

This is NOT a Cloudflare reimplementation. It only reproduces the single
documented behaviour needed for Scenario 4 (bypassing an edge cache to
reach and poison an origin cache):

  - If a request carries an `Authorization` header, bypass the edge cache
    entirely and forward to the origin (`CF-Cache-Status: BYPASS`).
  - Otherwise, cache responses in-memory keyed by Host + path + Accept and
    serve hits directly (`CF-Cache-Status: HIT` / `MISS`).

If you have your own domain on Cloudflare, prefer testing against the real
thing (with Origin Cache Control enabled) once you understand the
mechanism here -- real Cloudflare behaviour is authoritative, this is a
teaching stand-in.
"""
import os

import requests
from flask import Flask, Response, request

app = Flask(__name__)
ORIGIN = os.environ.get("ORIGIN_URL", "http://nginx:80")
_cache = {}

HOP_BY_HOP = {"content-encoding", "transfer-encoding", "content-length", "connection"}


def _cache_key(req):
    return "|".join([
        req.headers.get("Host", ""),
        req.path,
        req.headers.get("Accept", ""),
    ])


def _forward():
    headers = {k: v for k, v in request.headers.items() if k.lower() != "host"}
    return requests.get(
        ORIGIN + request.full_path.rstrip("?"),
        headers=headers,
        allow_redirects=False,
        timeout=10,
    )


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def proxy(path):
    has_auth = "Authorization" in request.headers
    key = _cache_key(request)

    if not has_auth and key in _cache:
        body, status, headers = _cache[key]
        resp = Response(body, status=status)
        for k, v in headers.items():
            resp.headers[k] = v
        resp.headers["CF-Cache-Status"] = "HIT"
        return resp

    upstream = _forward()
    headers = {k: v for k, v in upstream.headers.items() if k.lower() not in HOP_BY_HOP}

    if not has_auth:
        _cache[key] = (upstream.content, upstream.status_code, headers)

    resp = Response(upstream.content, status=upstream.status_code)
    for k, v in headers.items():
        resp.headers[k] = v
    resp.headers["CF-Cache-Status"] = "BYPASS" if has_auth else "MISS"
    return resp


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9090)
