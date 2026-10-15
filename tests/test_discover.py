import time

import pytest

from ckinject.discover import discover

from .mock_configurable_server import make_configurable_app, run_app_in_thread


@pytest.fixture(scope="module")
def mixed_server():
    # Only Accept (header) and "session" (cookie) are actually keyed.
    # Accept-Language, X-Unused (headers), "theme" (cookie), and "lang"
    # (query param) are deliberately NOT keyed -- discover() needs to
    # tell these apart correctly, not just find that *something* varies.
    app = make_configurable_app(
        keyed_headers=["Accept"],
        keyed_cookies=["session"],
        keyed_params=[],
    )
    server = run_app_in_thread(app, 8693)
    time.sleep(0.3)
    yield "http://127.0.0.1:8693"
    server.shutdown()


def test_discover_finds_keyed_header(mixed_server):
    results = discover(base_url=mixed_server, base_path="/", headers=["Accept"])
    assert len(results) == 1
    assert results[0].keyed is True


def test_discover_finds_unkeyed_header(mixed_server):
    results = discover(base_url=mixed_server, base_path="/", headers=["Accept-Language", "X-Unused"])
    assert all(r.keyed is False for r in results)


def test_discover_finds_keyed_cookie(mixed_server):
    results = discover(base_url=mixed_server, base_path="/", cookies=["session"])
    assert results[0].keyed is True


def test_discover_finds_unkeyed_cookie(mixed_server):
    results = discover(base_url=mixed_server, base_path="/", cookies=["theme"])
    assert results[0].keyed is False


def test_discover_finds_unkeyed_param(mixed_server):
    results = discover(base_url=mixed_server, base_path="/", params=["lang"])
    assert results[0].keyed is False


def test_discover_mixed_batch_classifies_each_correctly(mixed_server):
    results = discover(
        base_url=mixed_server,
        base_path="/",
        headers=["Accept", "Accept-Language"],
        cookies=["session", "theme"],
        params=["lang"],
    )
    by_fragment = {r.fragment: r.keyed for r in results}
    assert by_fragment["header:Accept"] is True
    assert by_fragment["header:Accept-Language"] is False
    assert by_fragment["cookie:session"] is True
    assert by_fragment["cookie:theme"] is False
    assert by_fragment["query:lang"] is False


def test_discover_on_fully_unkeyed_server():
    # Nothing keyed at all -- everything should come back unkeyed, and
    # nothing should be misclassified as inconclusive just because the
    # server has no dynamic keying.
    app = make_configurable_app()
    server = run_app_in_thread(app, 8694)
    time.sleep(0.3)
    try:
        results = discover(
            base_url="http://127.0.0.1:8694", base_path="/",
            headers=["Accept"], cookies=["session"], params=["lang"],
        )
        assert all(r.keyed is False for r in results)
    finally:
        server.shutdown()
