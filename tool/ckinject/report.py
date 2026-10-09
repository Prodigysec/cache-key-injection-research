"""Human-readable and JSON report output for ckinject results."""
from __future__ import annotations

import dataclasses
import json
import sys
from typing import Iterable

from .prober import ProbeResult


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


def to_json(results: Iterable[ProbeResult]) -> str:
    return json.dumps([dataclasses.asdict(r) for r in results], indent=2)


def write_json(results: Iterable[ProbeResult], path: str) -> None:
    with open(path, "w") as f:
        f.write(to_json(results))
