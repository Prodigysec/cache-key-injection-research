"""
A tiny in-process stand-in for the Nginx lab, used to unit-test
ckinject's probing logic without needing Docker. Two modes:

- vulnerable=True:  key = buster + path + Accept        (ambiguous, like
                    the article's "$scheme$proxy_host$uri...$http_accept")
- vulnerable=False: key = buster + "|" + path + "|" + Accept  (delimited,
                    the recommended fix)

The buster is read from the X-Ckinject-Buster header, matching
tool/ckinject/prober.py's real behavior (it moved there from a query
parameter -- see that module's comment for why a query-param buster
breaks this exact test for a path<->header pair). It's folded into both
modes' keys purely to give each probe iteration its own isolated cache
entry here, the same role it plays in the real lab.

This is test scaffolding only, not a realistic cache implementation.
"""
from flask import Flask, request
from werkzeug.serving import make_server


def make_app(vulnerable: bool) -> Flask:
    app = Flask(__name__)
    cache: dict[str, str] = {}

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def catch_all(path):
        full_path = "/" + path
        accept = request.headers.get("Accept", "")
        buster = request.headers.get("X-Ckinject-Buster", "")

        if vulnerable:
            key = buster + full_path + accept
        else:
            key = buster + "|" + full_path + "|" + accept

        if key in cache:
            resp = app.response_class(cache[key], status=200)
            resp.headers["X-Cache"] = "HIT"
            return resp

        body = f"path={full_path} accept={accept}"
        cache[key] = body
        resp = app.response_class(body, status=200)
        resp.headers["X-Cache"] = "MISS"
        return resp

    return app


def run_app_in_thread(app: Flask, port: int):
    server = make_server("127.0.0.1", port, app)
    import threading

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server
