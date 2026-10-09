"""
A tiny in-process stand-in for the Nginx lab, used to unit-test
ckinject's probing logic without needing Docker. Two modes:

- vulnerable=True:  key = ckbuster + path + Accept        (ambiguous, like
                    the article's "$scheme$proxy_host$uri...$http_accept")
- vulnerable=False: key = ckbuster + "|" + path + "|" + Accept  (delimited,
                    the recommended fix)

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
        ckbuster = request.args.get("ckbuster", "")

        if vulnerable:
            key = ckbuster + full_path + accept
        else:
            key = ckbuster + "|" + full_path + "|" + accept

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
