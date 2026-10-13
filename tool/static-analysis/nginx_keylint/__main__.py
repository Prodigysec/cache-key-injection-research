import argparse
import sys
from . import lint
from output import emit


def main():
    parser = argparse.ArgumentParser(description='Lint parsed Nginx cache key boundaries (leads only).')
    parser.add_argument('paths', nargs='+')
    parser.add_argument('--format', choices=['text', 'json', 'sarif'], default='text')
    parser.add_argument('--fail-on-findings', action='store_true')
    args = parser.parse_args()
    try:
        findings = [f for p in args.paths for f in lint(p)]
    except (ValueError, OSError) as error:
        print(f'parse error: {error}', file=sys.stderr)
        return 2
    emit(findings, args.format, 'nginx-keylint')
    return int(args.fail_on_findings and any(f['score'] in ('NONE', 'WEAK') for f in findings))


if __name__ == '__main__':
    sys.exit(main())
