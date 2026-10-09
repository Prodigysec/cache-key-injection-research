from ckinject.scheme_check import build_shifted_host


def test_build_shifted_host_moves_trailing_s():
    assert build_shifted_host("dummywebsite.localhost") == "sdummywebsite.localhost"
    assert build_shifted_host("example.com") == "sexample.com"
