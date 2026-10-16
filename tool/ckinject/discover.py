"""
Black-box discovery of WHICH fragments a cache keys on, as a precursor
to `probe`'s boundary-ambiguity testing. `probe` assumes you already know
two fragments are both keyed and adjacent; `discover` answers the prior
question -- is this header/cookie/param part of the key at all?

Not "surefire" (see docs/04-testing-methodology.md): this tests a
candidate list via a differential oracle, it can't prove a fragment
outside that list doesn't matter, and a flaky/non-deterministic target
can produce inconclusive results. Treat KEYED findings as a basis for
building `probe --pair` tests, not as settled fact on their own.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import requests

from .fragments import Slot, cookie_slot, header_slot, query_slot
from .prober import _build_request, _fingerprint, _send, random_marker

# Response headers that commonly expose cache status, checked best-effort
# for extra evidence alongside the content fingerprint (never relied on
# alone, since many targets -- especially CDN-fronted ones -- omit all of
# these).
_CACHE_STATUS_HEADERS = [
    "X-Cache", "X-Cache-Status", "CF-Cache-Status", "X-Varnish",
    "Akamai-Cache-Status", "Fastly-Debug-Digest", "Age",
]


@dataclass
class DiscoverResult:
    fragment: str
    kind: str  # "header" | "cookie" | "query"
    keyed: Optional[bool]  # True/False, or None if inconclusive
    note: str
    value1: str
    value2: str
    fp_a: tuple
    fp_a2: tuple
    fp_b: tuple
    cache_status_a: dict = field(default_factory=dict)
    cache_status_b: dict = field(default_factory=dict)


def _cache_status(resp: requests.Response) -> dict:
    return {h: resp.headers[h] for h in _CACHE_STATUS_HEADERS if h in resp.headers}


def discover_fragment(
    base_url: str,
    base_path: str,
    slot: Slot,
    kind: str,
    value1: str,
    value2: str,
    session: Optional[requests.Session] = None,
    timeout: float = 10.0,
    verify: bool = True,
) -> DiscoverResult:
    """Is `slot` part of the cache key? Uses a single, fresh, isolated
    buster for all three requests below so they're pinned to the same
    cache namespace -- the only thing that should distinguish them is
    the fragment value itself.
    """
    session = session or requests.Session()
    cache_buster = random_marker(10)

    req_a = _build_request(base_url, base_path)
    slot.apply(req_a, value1)
    req_a2 = _build_request(base_url, base_path)
    slot.apply(req_a2, value1)
    req_b = _build_request(base_url, base_path)
    slot.apply(req_b, value2)

    r_a = _send(session, base_url, req_a, timeout, verify, cache_buster)
    r_a2 = _send(session, base_url, req_a2, timeout, verify, cache_buster)
    r_b = _send(session, base_url, req_b, timeout, verify, cache_buster)

    fp_a, fp_a2, fp_b = _fingerprint(r_a), _fingerprint(r_a2), _fingerprint(r_b)

    if fp_a != fp_a2:
        keyed = None
        note = (
            "baseline repeat (same value, same buster) didn't match itself -- "
            "target may be non-deterministic, not actually caching this path, "
            "or the buster collided with something; treat as inconclusive"
        )
    elif fp_b == fp_a:
        keyed = False
        note = "same cached response regardless of this fragment's value"
    else:
        keyed = True
        note = "different value produced a distinct response -- likely keyed"

    return DiscoverResult(
        fragment=slot.name, kind=kind, keyed=keyed, note=note,
        value1=value1, value2=value2,
        fp_a=fp_a, fp_a2=fp_a2, fp_b=fp_b,
        cache_status_a=_cache_status(r_a), cache_status_b=_cache_status(r_b),
    )


def discover(
    base_url: str,
    base_path: str,
    headers: Optional[list[str]] = None,
    cookies: Optional[list[str]] = None,
    params: Optional[list[str]] = None,
    value1: Optional[str] = None,
    value2: Optional[str] = None,
    session: Optional[requests.Session] = None,
    timeout: float = 10.0,
    verify: bool = True,
) -> list[DiscoverResult]:
    # Fresh random values by default -- NOT a fixed "ckdiscoverA"/"B". A
    # real, persistent cache remembers what you tested last time; fixed
    # literals mean every rerun risks hitting whatever got cached under
    # that exact value on a PREVIOUS run (including a run against a
    # since-fixed target that cached an error response). The in-memory
    # mock server used in tests/ starts empty every time, which is
    # exactly why this never surfaced there -- it only bites a real,
    # persistent cache across repeated invocations.
    if value1 is None:
        value1 = "ckdiscoverA-" + random_marker(8)
    if value2 is None:
        value2 = "ckdiscoverB-" + random_marker(8)

    session = session or requests.Session()
    results = []
    for h in (headers or []):
        results.append(discover_fragment(base_url, base_path, header_slot(h), "header", value1, value2, session, timeout, verify))
    for c in (cookies or []):
        results.append(discover_fragment(base_url, base_path, cookie_slot(c), "cookie", value1, value2, session, timeout, verify))
    for p in (params or []):
        results.append(discover_fragment(base_url, base_path, query_slot(p), "query", value1, value2, session, timeout, verify))
    return results
