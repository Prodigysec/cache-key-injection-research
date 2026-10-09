"""
Targeted check for the scheme<->host boundary collision (the stored-XSS
primitive from the original research): shifting the trailing 's' of
'https' into the start of the Host header value.

This is kept separate from the generic slot-based prober in prober.py
because it requires real scheme switching (http vs https on two
different ports/URLs), which the generic Slot abstraction doesn't model.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

import requests


@dataclass
class SchemeCheckResult:
    host_header_accepted: bool
    http_https_equivalent: bool
    host_reflected: bool
    notes: list


def _fp(resp: requests.Response, n: int = 2048) -> tuple:
    return (resp.status_code, hashlib.sha256(resp.content[:n]).hexdigest()[:16])


def check(
    http_url: str,
    https_url: str,
    real_host: str,
    probe_host: str = "ckinject-probe.invalid",
    path: str = "/",
    timeout: float = 10.0,
    verify_tls: bool = False,
) -> SchemeCheckResult:
    """
    http_url / https_url: base URLs for the plain-HTTP and HTTPS listeners
      of the SAME target, e.g. "http://target.com" and "https://target.com"
      (or your lab's localhost:8080 / localhost:8443).
    real_host: the legitimate Host header value you're testing.
    probe_host: an arbitrary distinguishable Host value to test whether
      the vhost accepts arbitrary Host headers (does not need to resolve).
    """
    notes = []
    session = requests.Session()
    cb = "ckbuster=" + hashlib.sha256(probe_host.encode()).hexdigest()[:8]

    # 1. Does the vhost accept/reflect an arbitrary Host header?
    r_probe = session.get(f"{http_url}{path}?{cb}1", headers={"Host": probe_host}, timeout=timeout, verify=verify_tls)
    host_reflected = probe_host in r_probe.text
    if host_reflected:
        notes.append(f"Host value '{probe_host}' reflected in response body — check the sink (script src? link? redirect?).")
    else:
        notes.append("Host value not found in response body; reflection-based impact (e.g. stored XSS) would need a different sink.")

    # 2. Does the real host behave the same over HTTP and HTTPS (no forced redirect)?
    r_http = session.get(f"{http_url}{path}?{cb}2", headers={"Host": real_host}, timeout=timeout, verify=verify_tls, allow_redirects=False)
    r_https = session.get(f"{https_url}{path}?{cb}2", headers={"Host": real_host}, timeout=timeout, verify=verify_tls, allow_redirects=False)
    http_https_equivalent = (
        r_http.status_code < 300 and r_https.status_code < 300 and _fp(r_http) == _fp(r_https)
    )
    if r_http.status_code in (301, 302, 307, 308):
        notes.append(f"HTTP->HTTPS redirect observed (status {r_http.status_code}) — cross-scheme collision likely blocked.")
    if not http_https_equivalent:
        notes.append("HTTP and HTTPS responses differ or one failed; cross-scheme collision prerequisite not confirmed.")

    # 3. Host-header acceptance is 'accepted' if the probe request didn't error/get rejected outright.
    host_header_accepted = r_probe.status_code < 500

    return SchemeCheckResult(
        host_header_accepted=host_header_accepted,
        http_https_equivalent=http_https_equivalent,
        host_reflected=host_reflected,
        notes=notes,
    )


def build_shifted_host(real_host: str) -> str:
    """Given 'https' + real_host as the intended key, return the Host
    value to send over PLAIN HTTP that reproduces the same concatenated
    key: move the trailing 's' of 'https' onto the front of the host.
    e.g. real_host='dummywebsite.localhost' -> 'sdummywebsite.localhost'
    Only meaningful when the key pattern is literally "$scheme$host...".
    """
    return "s" + real_host
