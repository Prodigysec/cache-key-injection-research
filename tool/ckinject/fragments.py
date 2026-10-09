"""
Fragment "slots" — ways to place a value into an HTTP request, used to
test whether two adjacent cache-key fragments are separated by a real
boundary or just concatenated.

Each Slot knows how to apply a string value (or None, meaning "leave this
part of the request at its default / unset") onto a mutable request spec
dict with keys: "path" (str, appended to base path), "headers" (dict),
"params" (dict, query string).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional


@dataclass(frozen=True)
class Slot:
    name: str
    apply: Callable[[dict, Optional[str]], None]


def path_suffix_slot() -> Slot:
    def apply(req: dict, value: Optional[str]) -> None:
        if value is not None:
            req["path"] = req["path"] + value
    return Slot("path_suffix", apply)


def header_slot(header_name: str) -> Slot:
    def apply(req: dict, value: Optional[str]) -> None:
        # requests/urllib3 silently inject defaults (Accept, Accept-Encoding,
        # User-Agent, Connection) for any header you don't set explicitly.
        # "Unset" has to mean "explicitly empty", not "omitted", or the
        # baseline/control requests would pick up a library default instead
        # of a true empty fragment -- which would break the collision test.
        req["headers"][header_name] = value if value is not None else ""
    return Slot(f"header:{header_name}", apply)


def query_slot(param_name: str) -> Slot:
    def apply(req: dict, value: Optional[str]) -> None:
        if value is not None:
            req["params"][param_name] = value
    return Slot(f"query:{param_name}", apply)


def cookie_slot(cookie_name: str) -> Slot:
    def apply(req: dict, value: Optional[str]) -> None:
        req["headers"]["Cookie"] = f"{cookie_name}={value}" if value is not None else ""
    return Slot(f"cookie:{cookie_name}", apply)


# Default candidate pairs to probe against a target. (slot_a, slot_b) —
# slot_a is conceptually "first in the key", slot_b "second", though the
# prober doesn't assume order matters beyond matching the article's
# technique of appending to the path and shifting into the next fragment.
#
# Extend this list as you discover application-specific keyed fragments
# (Track B/custom headers in docs/03-research-roadmap.md).
DEFAULT_PAIRS = [
    (path_suffix_slot(), header_slot("Accept")),
    (path_suffix_slot(), header_slot("Accept-Language")),
    (path_suffix_slot(), header_slot("Accept-Encoding")),
    (path_suffix_slot(), header_slot("X-Test-Header")),
    (query_slot("ckprobe"), header_slot("Accept")),
    (header_slot("Accept"), header_slot("Accept-Language")),
]


def pairs_from_names(names: list[str]) -> list[tuple[Slot, Slot]]:
    """Build a custom pair list from 'slotkind:value' strings, e.g.
    'path,header:Accept' 'header:X-Foo,header:X-Bar'. Mainly for CLI use.
    """
    def _make(spec: str) -> Slot:
        if spec == "path":
            return path_suffix_slot()
        if spec.startswith("header:"):
            return header_slot(spec.split(":", 1)[1])
        if spec.startswith("query:"):
            return query_slot(spec.split(":", 1)[1])
        if spec.startswith("cookie:"):
            return cookie_slot(spec.split(":", 1)[1])
        raise ValueError(f"Unrecognized slot spec: {spec}")

    pairs = []
    for entry in names:
        a_spec, b_spec = entry.split(",")
        pairs.append((_make(a_spec.strip()), _make(b_spec.strip())))
    return pairs
