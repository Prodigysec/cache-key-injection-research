from pathlib import Path
import json
import pytest
from nginx_keylint import boundaries, lint
from output import sarif


def test_lab():
    path = Path(__file__).resolve().parents[3] / 'lab/nginx/nginx.conf'
    findings = lint(path)
    assert any(f['left'] == 'args' and f['right'] == 'http_accept' and f['score'] == 'NONE' for f in findings)
    assert any(f['left'] == 'scheme' and f['right'] == 'host' for f in findings)
    json.dumps(sarif(findings, 'nginx-keylint'))


@pytest.mark.parametrize('key,score', [
    ('$uri$http_accept', 'NONE'), ('\x24{uri}|\x24{http_accept}', 'WEAK'),
    ('$scheme|$server_port', 'STRONG'), ('$unknown $other', 'UNKNOWN'),
    ('$uri:$http_accept', 'WEAK'), ('$args/$cookie_user', 'WEAK')])
def test_boundaries(key, score):
    assert list(boundaries(key))[0]['score'] == score


def test_real_parser(tmp_path):
    conf = tmp_path / 'nginx.conf'
    conf.write_text('# proxy_cache_key "$uri$http_accept";\nhttp { server { proxy_cache_key "$uri|$http_accept"; }}')
    result = lint(conf)
    assert len(result) == 1
    assert result[0]['line'] == 2
    assert result[0]['score'] == 'WEAK'


def test_malformed(tmp_path):
    conf = tmp_path / 'nginx.conf'
    conf.write_text('http { proxy_cache_key "$uri$http_accept";')
    with pytest.raises(ValueError):
        lint(conf)
