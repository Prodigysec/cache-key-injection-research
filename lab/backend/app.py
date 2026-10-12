"""
Minimal backend for the cache key injection lab.

Intentionally simple: it just reflects what a real app would plausibly do
(serve a homepage, serve an admin dashboard behind an upstream ACL, reflect
Host into a script src for a CDN-friendly asset loader pattern). The
interesting behaviour lives in nginx.conf, not here.
"""
from flask import Flask, request

app = Flask(__name__)

ADMIN_HTML = """<html><body>
<h1>Admin Dashboard</h1>
<p>Secret admin token: S3cr3t-Admin-Token-DO-NOT-LEAK</p>
</body></html>"""

HOME_HTML = "<html><body><h1>Welcome home</h1></body></html>"


@app.after_request
def add_headers(resp):
    resp.headers["X-Backend"] = "lab-backend"
    return resp


@app.route("/")
def root():
    # Reflects the Host header into a script src — the sink used by the
    # cross-scheme stored-XSS scenario (scenario 3).
    host = request.headers.get("Host", "unknown")
    return f"""<html><head></head><body>
<h1>Welcome home</h1>
<script src="//{host}/main.js"></script>
</body></html>"""


@app.route("/home")
def home():
    return HOME_HTML


@app.route("/admin")
def admin():
    return ADMIN_HTML


@app.route("/anyendpoint")
def anyendpoint():
    return "dummy endpoint ok"


@app.route("/XYZ")
def xyz():
    return "secret endpoint XYZ reached"


@app.route("/fuzz", defaults={"rest": ""})
@app.route("/fuzz<rest>")
def fuzz(rest):
    # General-purpose target for ckinject's generic boundary probe
    # (see tool/README.md). Unlike the scenario-specific endpoints above,
    # this accepts ANY suffix after /fuzz and reflects back the full path
    # plus every header/query param ckinject's default pairs test, so a
    # genuine boundary collision is visible in the response body/fingerprint
    # instead of every request just 404ing identically. Paired with
    # nginx.conf's "location /fuzz" (prefix match, same ambiguous key as
    # the other scenarios) rather than an exact-match location.
    fields = {
        "path": request.path,
        "accept": request.headers.get("Accept", ""),
        "accept_language": request.headers.get("Accept-Language", ""),
        "accept_encoding": request.headers.get("Accept-Encoding", ""),
        "x_test_header": request.headers.get("X-Test-Header", ""),
        "ckprobe": request.args.get("ckprobe", ""),
    }
    return "|".join(f"{k}={v}" for k, v in fields.items())


# Everything else (/ad, /h, /anyend, /XY, ...) falls through to Flask's
# default 404 — this is intentional. The CPDoS and cache-deception
# scenarios rely on the *cache* serving a stored response for these paths
# on a collision; the backend itself should never normally answer them
# with anything sensitive.

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
