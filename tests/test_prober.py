import time

import pytest

from ckinject.fragments import header_slot, path_suffix_slot
from ckinject.prober import probe_pair

from .mock_cache_server import make_app, run_app_in_thread


@pytest.fixture(scope="module")
def vulnerable_server():
    app = make_app(vulnerable=True)
    server = run_app_in_thread(app, 8591)
    time.sleep(0.2)
    yield "http://127.0.0.1:8591"
    server.shutdown()


@pytest.fixture(scope="module")
def safe_server():
    app = make_app(vulnerable=False)
    server = run_app_in_thread(app, 8592)
    time.sleep(0.2)
    yield "http://127.0.0.1:8592"
    server.shutdown()


def test_detects_collision_on_ambiguous_key(vulnerable_server):
    results = probe_pair(
        base_url=vulnerable_server,
        base_path="/",
        slot_a=path_suffix_slot(),
        slot_b=header_slot("Accept"),
        marker_length=10,
    )
    assert any(r.collided for r in results), (
        "Expected at least one split offset to demonstrate a collision "
        "against the intentionally-vulnerable mock server"
    )


def test_no_collision_on_delimited_key(safe_server):
    results = probe_pair(
        base_url=safe_server,
        base_path="/",
        slot_a=path_suffix_slot(),
        slot_b=header_slot("Accept"),
        marker_length=10,
    )
    assert not any(r.collided for r in results), (
        "Delimited key should never show a boundary collision"
    )