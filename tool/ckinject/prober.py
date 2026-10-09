"""
Core boundary-probing logic: the black-box split-marker technique from
docs/04-testing-methodology.md, automated across candidate fragment pairs.

For a pair (slot_a, slot_b) and a random marker M:

  R1 (baseline): slot_a = M,              slot_b = unset
  R2 (shifted):   slot_a = M[:k],          slot_b = M[k:]     for each split k
  R3 (control):   slot_a = M[:k],          slot_b = unset

If R2's response matches R1's (same fingerprint) while R3's differs from
both, the cache collapsed two different requests into the same key by
shifting bytes across the slot_a/slot_b boundary — a real collision, not
a coincidence of both requests happening to 404 identically.
"""
from __future__ import annotations

import hashlib
import secrets
import string
from dataclasses import dataclass, field
from typing import Optional

import requests

from .fragments import Slot


def random_marker(length: int = 12) -> str:
    return "".join(secrets.choice(string.ascii_lowercase) for _ in range(length))


@dataclass
class ProbeResult:
    pair: str
    marker: str
    split_index: int
    collided: bool
    baseline_fp: tuple
    shifted_fp: tuple
    control_fp: tuple
    baseline_req: dict
    shifted_req: dict
    control_req: dict
    note: str = ""


def _fingerprint(resp: requests.Response, body_bytes: int = 2048) -> tuple:
    body_hash = hashlib.sha256(resp.content[:body_bytes]).hexdigest()[:16]
    return (resp.status_code, len(resp.content), body_hash)


def _build_request(base_url: str, base_path: str) -> dict:
    return {"path": base_path, "headers": {}, "params": {}}


def _send(session: requests.Session, base_url: str, req: dict, timeout: float, verify: bool, cache_buster: str) -> requests.Response:
    params = dict(req["params"])
    params.setdefault("ckbuster", cache_buster)
    path = req["path"]
    if not path.startswith("/"):
        # Guards against a bare "" or a no-leading-slash base_path (from
        # the CLI or a caller) combined with path_suffix_slot() producing
        # something like "base_urlMARKER" with no "/" at all, which
        # requests/urllib3 can't parse as a URL.
        path = "/" + path
    url = base_url.rstrip("/") + path
    return session.get(url, headers=req["headers"], params=params, timeout=timeout, verify=verify, allow_redirects=False)


def probe_pair(
    base_url: str,
    base_path: str,
    slot_a: Slot,
    slot_b: Slot,
    session: Optional[requests.Session] = None,
    marker_length: int = 12,
    split_offsets: Optional[list[int]] = None,
    timeout: float = 10.0,
    verify: bool = True,
) -> list[ProbeResult]:
    """Probe one (slot_a, slot_b) pair across several split points.

    IMPORTANT: every call uses a fresh random marker AND a fresh cache
    buster, so each probe is isolated and never touches a cache entry
    another request (yours or a real user's) might also hit. Never reuse
    markers across probes on a live target.
    """
    session = session or requests.Session()
    marker = random_marker(marker_length)
    offsets = split_offsets or sorted(set([1, 2, 3, marker_length // 2, marker_length - 1]))
    offsets = [o for o in offsets if 0 < o < marker_length]

    results = []
    for k in offsets:
        cache_buster = random_marker(8)
        part_a, part_b = marker[:k], marker[k:]

        baseline_req = _build_request(base_url, base_path)
        slot_a.apply(baseline_req, marker)
        slot_b.apply(baseline_req, None)

        shifted_req = _build_request(base_url, base_path)
        slot_a.apply(shifted_req, part_a)
        slot_b.apply(shifted_req, part_b)

        control_req = _build_request(base_url, base_path)
        slot_a.apply(control_req, part_a)
        slot_b.apply(control_req, None)

        r1 = _send(session, base_url, baseline_req, timeout, verify, cache_buster)
        r2 = _send(session, base_url, shifted_req, timeout, verify, cache_buster)
        r3 = _send(session, base_url, control_req, timeout, verify, cache_buster)

        fp1, fp2, fp3 = _fingerprint(r1), _fingerprint(r2), _fingerprint(r3)
        collided = (fp1 == fp2) and (fp1 != fp3)

        results.append(
            ProbeResult(
                pair=f"{slot_a.name} <-> {slot_b.name}",
                marker=marker,
                split_index=k,
                collided=collided,
                baseline_fp=fp1,
                shifted_fp=fp2,
                control_fp=fp3,
                baseline_req=baseline_req,
                shifted_req=shifted_req,
                control_req=control_req,
                note="" if fp1 != fp3 or collided else "baseline==control: this pair may not be keyed distinctly, inconclusive",
            )
        )
    return results