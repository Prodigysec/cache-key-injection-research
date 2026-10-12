import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nginx_keylint import lint as nginx_lint
from vcl_keylint import lint as vcl_lint


def main():
    p = argparse.ArgumentParser()
    p.add_argument('corpus', type=Path)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    manifest = json.loads((args.corpus / 'manifest.json').read_text())
    findings, errors = [], []
    for item in manifest['files']:
        try:
            results = (vcl_lint if item['kind'] == 'vcl' else nginx_lint)(args.corpus / item['file'])
            findings += [{**f, 'source': item['source'], 'corpus_file': item['file']} for f in results]
        except (ValueError, OSError, SyntaxError) as error:
            errors.append({'source': item['source'], 'error': str(error)})
    command = [sys.executable, '-m', 'semgrep', '--metrics=off', '--disable-version-check', '--config',
               str(Path(__file__).resolve().parents[1] / 'semgrep-rules.yml'), '--json', str(args.corpus)]
    semgrep = subprocess.run(command, capture_output=True, text=True, encoding='utf-8')
    try:
        semgrep_json = json.loads(semgrep.stdout)
    except ValueError:
        semgrep_json = {'results': [], 'errors': [semgrep.stderr]}
    report = {'files': len(manifest['files']), 'by_kind': dict(Counter(f['kind'] for f in manifest['files'])),
              'collection_errors': manifest['errors'], 'parse_errors': errors,
              'boundary_counts': dict(Counter(f['score'] for f in findings)), 'findings': findings,
              'semgrep': {'exit_code': semgrep.returncode, 'output': semgrep_json, 'stderr': semgrep.stderr},
              'note': 'Config corpus has no Python/JS/TS; zero Semgrep coverage is not precision evidence.'}
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k not in ('findings', 'semgrep')}, indent=2))
    return int(bool(errors) or semgrep.returncode not in (0, 1))


if __name__ == '__main__':
    raise SystemExit(main())
