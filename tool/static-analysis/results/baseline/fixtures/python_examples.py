"""
Fixtures for tool/static-analysis/semgrep-rules.yml.

Run:
    semgrep --config ../semgrep-rules.yml python_examples.py

Expect: VULNERABLE_* functions to be flagged, SAFE_* functions to not be.
"""
from flask import request

cache = {}  # stand-in for any cache.get/cache.set-style object


# --- Should be flagged by cache-key-concat-no-delimiter-fstring ---
def VULNERABLE_fstring_concat():
    accept = request.headers.get("Accept")
    path = request.path
    key = f"{path}{accept}"
    return cache.get(key) or cache.set(key, "value")


def VULNERABLE_fstring_concat_inline():
    return cache.get(f"{request.path}{request.headers.get('Accept')}")


# --- Should be flagged by cache-key-concat-no-delimiter-plus ---
def VULNERABLE_plus_concat():
    return cache.get(request.path + request.headers.get("Accept"))


# --- Should NOT be flagged: delimiter present between the two sources ---
def SAFE_delimited():
    return cache.get(f"{request.path}|{request.headers.get('Accept')}")


# --- Should NOT be flagged: only one request-derived value, no second source ---
def SAFE_single_source():
    return cache.get(f"prefix:{request.path}")


# --- Should NOT be flagged: fragments hashed independently before joining ---
def SAFE_independent_hash():
    import hashlib
    a = hashlib.sha256(request.path.encode()).hexdigest()
    b = hashlib.sha256(request.headers.get("Accept", "").encode()).hexdigest()
    return cache.get(a + b)
