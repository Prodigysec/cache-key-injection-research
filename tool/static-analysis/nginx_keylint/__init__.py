"""Conservative analysis of parsed Nginx cache-key templates."""
import re
from pathlib import Path

# None means charset unknown, not that every byte is accepted by Nginx.
VARIABLES = {
    'request_uri': (True, None, True), 'uri': (True, None, True),
    'args': (True, None, True), 'scheme': (True, set('htps'), True),
    'host': (True, None, True), 'proxy_host': (False, None, True),
    'server_port': (False, set('0123456789'), True),
    'request_method': (True, set("!#$%&'*+-.^_`|~0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"), True),
    'is_args': (True, set('?'), True),
}
TOKEN = re.compile(r'\$(?:\{([A-Za-z_][A-Za-z_0-9]*)\}|([A-Za-z_][A-Za-z_0-9]*))')


def variable(name):
    if name.startswith(('http_', 'cookie_', 'arg_')):
        return True, None, True
    return VARIABLES.get(name, (None, None, None))


def boundaries(template):
    """Regex tokenizes an already parsed argument; it never parses config text."""
    refs = list(TOKEN.finditer(template))
    for left, right in zip(refs, refs[1:]):
        a, b = left.group(1) or left.group(2), right.group(1) or right.group(2)
        sep = template[left.end():right.start()]
        av, bv = variable(a), variable(b)
        if not sep:
            score = 'NONE'
        elif any(av[1] is not None and bv[1] is not None and c not in av[1] and c not in bv[1] for c in sep):
            score = 'STRONG'
        elif any(c in '|:/-' for c in sep):
            score = 'WEAK'
        else:
            score = 'UNKNOWN'
        yield {'left': a, 'right': b, 'separator': sep, 'score': score,
               'attacker_controlled': [av[0], bv[0]],
               'variable_length': [av[2], bv[2]],
               'classification': 'confirmed-unsafe-construction' if score == 'NONE' else score.lower(),
               'message': f'{a} → {b}: {score}; a static lead, collision feasibility needs review'}


def lint(path):
    import crossplane
    parsed = crossplane.parse(str(path), check_ctx=False, check_args=False, single=True)
    if parsed['status'] != 'ok':
        raise ValueError(str(parsed['errors']))
    findings = []
    def walk(nodes):
        for node in nodes:
            if node['directive'] in {'proxy_cache_key', 'fastcgi_cache_key', 'uwsgi_cache_key', 'scgi_cache_key'}:
                if len(node['args']) != 1:
                    raise ValueError('cache key directive needs exactly one argument')
                for item in boundaries(node['args'][0]):
                    findings.append({**item, 'path': str(path), 'line': node['line'],
                                     'directive': node['directive'], 'template': node['args'][0],
                                     'rule': 'nginx-key-boundary-' + item['score'].lower()})
            walk(node.get('block', []))
    for config in parsed['config']:
        walk(config['parsed'])
    return findings
