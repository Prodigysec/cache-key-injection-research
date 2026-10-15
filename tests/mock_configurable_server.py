"""
A mock cache server whose keyed fragments are configurable, used to
unit-test ckinject.discover's differential oracle: does it correctly
classify fragments that genuinely are part of the key as KEYED, and
fragments that aren't as unkeyed, without needing Docker/a real cache.

Unlike mock_cache_server.py (which simulates ambiguous concatenation for
prober.py's boundary tests), this simulates ORDINARY, unambiguous keying
-- the thing discover.py needs to tell apart from "not in the key at
all" is presence vs. absence, not boundary safety.
"""
from __future__ import annotations

import json
import threading

from flask import Flask, request
from werkzeug.serving import make_server


def _parse_cookies(cookie_header: str) -> dict:
    result = {}
    for part in (cookie_header or "").split(";"):
        if "=" in part:
            k, v = part.strip().split("=", 1)
            result[k] = v
    return result


def make_configurable_app(keyed_headers=None, keyed_cookies=None, keyed_params=None) -> Flask:
    app = Flask(__name__)
    cache: dict[str, str] = {}
    keyed_headers = keyed_headers or []
    keyed_cookies = keyed_cookies or []
    keyed_params = keyed_params or []

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def catch_all(path):
        buster = request.headers.get("X-Ckinject-Buster", "")
        cookies = _parse_cookies(request.headers.get("Cookie", ""))

        key_parts = [buster, "/" + path]
        key_parts += [f"h:{h}={request.headers.get(h, '')}" for h in keyed_headers]
        key_parts += [f"c:{c}={cookies.get(c, '')}" for c in keyed_cookies]
        key_parts += [f"p:{p}={request.args.get(p, '')}" for p in keyed_params]
        key = "|".join(key_parts)

        if key in cache:
            resp = app.response_class(cache[key], status=200)
            resp.headers["X-Cache"] = "HIT"
            return resp

        # Only reflects the KEYED fragments -- an unkeyed fragment under
        # test never reaches this branch at all when it should've been a
        # HIT, which is the point: a real cache's HIT never re-invokes
        # the backend either.
        body = json.dumps({
            "path": "/" + path,
            "headers": {h: request.headers.get(h, "") for h in keyed_headers},
            "cookies": {c: cookies.get(c, "") for c in keyed_cookies},
            "params": {p: request.args.get(p, "") for p in keyed_params},
        })
        cache[key] = body
        resp = app.response_class(body, status=200)
        resp.headers["X-Cache"] = "MISS"
        return resp

    return app


def run_app_in_thread(app: Flask, port: int):
    server = make_server("127.0.0.1", port, app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server
