import hashlib
import json
import urllib.parse
from flask import request


def no_separator(cache):
    a = request.path
    b = request.headers.get('Accept')
    key = f"{a}{b}"
    # ruleid: cache-key-python-no-delimiter
    cache.set(key, 'value')
    # ruleid: cache-key-python-no-delimiter
    cache.get(request.GET.get('tenant') + request.cookies.get('session'))
    # ruleid: cache-key-python-no-delimiter
    cache.delete(hashlib.sha256((a + b).encode()).hexdigest())
    # ruleid: cache-key-python-no-delimiter
    cache.get(urllib.parse.quote(a, safe='') + urllib.parse.quote(b, safe=''))


def weak(cache):
    a = request.query_params.get('tenant')
    b = request.url.path
    # ruleid: cache-key-python-weak-delimiter
    cache.get(a + '|' + b)
    # ruleid: cache-key-python-weak-delimiter
    cache.get(f'{a}:{b}')


def safe(cache):
    a = request.path
    b = request.headers.get('Accept')
    # ok: cache-key-python-no-delimiter, cache-key-python-weak-delimiter
    cache.get(a + a)
    # ok: cache-key-python-no-delimiter, cache-key-python-weak-delimiter
    cache.get(f'{a}{a}')
    # ok: cache-key-python-no-delimiter, cache-key-python-weak-delimiter
    cache.get(a + 'fixed-suffix')
    # ok: cache-key-python-no-delimiter, cache-key-python-weak-delimiter
    cache.get(json.dumps([a, b]))
    # ok: cache-key-python-no-delimiter, cache-key-python-weak-delimiter
    cache.get(json.dumps((a, b)))
    # ok: cache-key-python-no-delimiter, cache-key-python-weak-delimiter
    cache.get(hashlib.sha256(a.encode()).hexdigest() + hashlib.sha256(b.encode()).hexdigest())
    # ok: cache-key-python-no-delimiter, cache-key-python-weak-delimiter
    cache.get(f'{len(a)}:{a}{len(b)}:{b}')
    # ok: cache-key-python-no-delimiter, cache-key-python-weak-delimiter
    cache.get(urllib.parse.quote(a, safe='') + '|' + urllib.parse.quote(b, safe=''))
    # ok: cache-key-python-no-delimiter, cache-key-python-weak-delimiter
    cache.set('fixed-key', a + b)
    # ok: cache-key-python-no-delimiter, cache-key-python-weak-delimiter
    print(a + b)


def make_cache_key():
    # ruleid: cache-key-python-no-delimiter
    return request.path + request.args.get('tenant')
