import pytest
from vcl_keylint import lint


def analyze(tmp_path, text):
    path = tmp_path / 'test.vcl'
    path.write_text(text)
    return lint(path)


def test_framed_calls(tmp_path):
    assert analyze(tmp_path, 'sub vcl_hash { hash_data(req.url); hash_data(req.http.Accept); return(lookup); }') == []


def test_join(tmp_path):
    result = analyze(tmp_path, 'sub vcl_hash { hash_data(req.url + req.http.Accept); }')
    assert result[0]['score'] == 'NONE'
    assert result[0]['builtin_appended_on_some_path']


def test_weak(tmp_path):
    assert analyze(tmp_path, 'sub vcl_hash { hash_data(req.url + "|" + req.http.Accept); return(lookup); }')[0]['score'] == 'WEAK'


def test_single_twice(tmp_path):
    assert analyze(tmp_path, 'sub vcl_hash { hash_data(req.url + req.url); }') == []


def test_call_branch_and_dead_code(tmp_path):
    result = analyze(tmp_path, '''sub helper { if (req.http.X) { hash_data(req.url + req.http.Accept); } else { hash_data(req.url); } }
sub vcl_hash { call helper; return(lookup); hash_data(req.url + req.http.Dead); }''')
    assert len(result) == 1
    assert result[0]['right'] == 'req.http.Accept'
    assert not result[0]['builtin_appended_on_some_path']


def test_elsif(tmp_path):
    result = analyze(tmp_path, 'sub vcl_hash { if (req.http.X) { hash_data(req.url); } elsif (req.http.Y) { hash_data(req.url + req.http.Accept); } else { hash_data("separator"); } }')
    assert len(result) == 1


def test_unknown_and_recursion(tmp_path):
    result = analyze(tmp_path, 'sub vcl_hash { call missing; call vcl_hash; hash_data(std.tolower(req.url)); }')
    assert len(result) == 3
    assert all(f['score'] == 'UNKNOWN' for f in result)


def test_malformed(tmp_path):
    with pytest.raises(ValueError):
        analyze(tmp_path, 'sub vcl_hash { hash_data(req.url);')


def test_public_builtin():
    from pathlib import Path
    assert lint(Path(__file__).parent / 'fixtures/varnish-builtin-hash.vcl') == []
