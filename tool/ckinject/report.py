"""Human-readable and JSON report output for ckinject results."""
from __future__ import annotations

import dataclasses
import json
import sys
from typing import Iterable

from .discover import DiscoverResult
from .prober import ProbeResult


def print_discover_results(results: list[DiscoverResult]) -> int:
    keyed_count = 0
    for r in results:
        if r.keyed is True:
            status, keyed_count = "KEYED", keyed_count + 1
        elif r.keyed is False:
            status = "unkeyed"
        else:
            status = "inconclusive"
        cs = r.cache_status_a or r.cache_status_b
        cs_str = f" cache-status={cs}" if cs else ""
        print(f"[{status:12}] {r.kind:6} {r.fragment:30} "
              f"a={r.fp_a} a2={r.fp_a2} b={r.fp_b}{cs_str}")
        print(f"               values tested: {r.value1!r} / {r.value2!r}")
        print(f"               note: {r.note}")
    print()
    print(f"{keyed_count} fragment(s) appear keyed, out of {len(results)} tested")
    return keyed_count


def print_results(results: list[ProbeResult]) -> int:
    hits = 0
    for r in results:
        status = "COLLISION" if r.collided else "no collision"
        marker = f"{r.marker[:r.split_index]}|{r.marker[r.split_index:]}"
        print(f"[{status:11}] {r.pair:40} split={marker:16} "
              f"baseline={r.baseline_fp} shifted={r.shifted_fp} control={r.control_fp}")
        if r.note:
            print(f"              note: {r.note}")
        if r.collided:
            hits += 1
    print()
    print(f"{hits} collision(s) found across {len(results)} probe(s)")
    return hits


def to_json(results: Iterable[ProbeResult] | Iterable[DiscoverResult]) -> str:
    return json.dumps([dataclasses.asdict(r) for r in results], indent=2)


def write_json(results: Iterable[ProbeResult] | Iterable[DiscoverResult], path: str) -> None:
    with open(path, "w") as f:
        f.write(to_json(results))
