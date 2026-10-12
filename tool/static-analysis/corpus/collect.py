"""Resumable public-only GitHub API corpus collection; no deployment traffic.

Optional code search requires GH_TOKEN/GITHUB_TOKEN. Default sampling is
lexicographic, capped per repo and deliberately NOT representative.
"""
import argparse
import base64
import hashlib
import http.client
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

DEFAULT_REPOS = ['nginx/nginx', 'varnishcache/varnish-cache', 'magento/magento2', 'h5bp/server-configs-nginx']


class API:
    def __init__(self):
        self.headers = {'User-Agent': 'cache-key-injection-research', 'Accept': 'application/vnd.github+json'}
        token = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
        if token:
            self.headers['Authorization'] = 'Bearer ' + token

    def get(self, endpoint):
        for attempt in range(4):
            req = urllib.request.Request('https://api.github.com/' + endpoint, headers=self.headers)
            try:
                with urllib.request.urlopen(req, timeout=60) as response:
                    data = json.load(response)
                    if response.headers.get('X-RateLimit-Remaining') == '0':
                        delay = max(1, int(response.headers.get('X-RateLimit-Reset', '0')) - int(time.time()))
                        # Save progress and stop instead of waiting an hour.
                        raise RuntimeError(f'GitHub rate limit exhausted; resume after {delay}s')
                    return data
            except (http.client.IncompleteRead, TimeoutError) as error:
                if attempt == 3:
                    raise RuntimeError('incomplete GitHub response after retries') from error
                time.sleep(2 ** attempt)
            except urllib.error.HTTPError as error:
                if error.code in (403, 429):
                    raise RuntimeError('GitHub denied request/rate limited; saved corpus is resumable') from error
                if error.code not in (500, 502, 503, 504) or attempt == 3:
                    raise
                time.sleep(2 ** attempt)


def save_manifest(path, manifest):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    tmp.replace(path)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--repo', action='append')
    p.add_argument('--limit-per-repo', type=int, default=8)
    p.add_argument('--search', help='Optional authenticated GitHub code-search query; public repos checked again')
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    manifest_path = args.output / 'manifest.json'
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {'sampling': 'public seed repos, sorted paths, capped per repo', 'files': [], 'errors': []}
    api = API()
    repos = args.repo or list(DEFAULT_REPOS)
    if args.search:
        try:
            items = api.get('search/code?q=' + urllib.parse.quote(args.search))['items']
            repos += [item['repository']['full_name'] for item in items]
        except (OSError, RuntimeError, ValueError) as error:
            manifest['errors'].append({'search': args.search, 'error': str(error)})
            save_manifest(manifest_path, manifest)
            print(f'Code search unavailable: {error}', flush=True)
    for repo in dict.fromkeys(repos):
        try:
            info = api.get('repos/' + repo)
            if info['private']:
                raise RuntimeError('private repositories excluded')
            pinned = next((f['commit'] for f in manifest['files'] if f['repo'] == repo), None)
            commit = pinned or api.get('repos/' + repo + '/commits/' + info['default_branch'])['sha']
            tree = api.get('repos/' + repo + '/git/trees/' + commit + '?recursive=1')
            if tree.get('truncated'):
                manifest['errors'].append({'repo': repo, 'error': 'tree truncated; sampling incomplete'})
            entries = sorted((x for x in tree['tree'] if x['type'] == 'blob' and
                              (x['path'].endswith('.vcl') or x['path'].endswith('.conf'))), key=lambda x: x['path'])[:args.limit_per_repo]
            for entry in entries:
                source = f'https://github.com/{repo}/blob/{commit}/{entry["path"]}'
                existing = next((f for f in manifest['files'] if f['source'] == source), None)
                if existing and (args.output / existing['file']).exists():
                    continue
                blob = api.get('repos/' + repo + '/git/blobs/' + entry['sha'])
                content = base64.b64decode(blob['content'])
                digest = hashlib.sha256(content).hexdigest()
                filename = digest[:16] + Path(entry['path']).suffix
                (args.output / filename).write_bytes(content)
                manifest['files'].append({'repo': repo, 'commit': commit, 'upstream_path': entry['path'], 'source': source,
                                          'file': filename, 'sha256': digest, 'kind': 'vcl' if filename.endswith('.vcl') else 'nginx'})
                save_manifest(manifest_path, manifest)
                print(source, flush=True)
                time.sleep(0.2)
        except (OSError, ValueError, RuntimeError, KeyError) as error:
            manifest['errors'].append({'repo': repo, 'error': str(error)})
            print(f'{repo}: {error}', flush=True)
        save_manifest(manifest_path, manifest)
    print(f'{len(manifest["files"])} public files collected; {len(manifest["errors"])} errors')
    return int(bool(manifest['errors']))


if __name__ == '__main__':
    raise SystemExit(main())
