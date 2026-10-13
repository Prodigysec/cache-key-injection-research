import argparse
import sys
from . import lint
from output import emit


def main():
    p = argparse.ArgumentParser(description='Upstream Varnish VCL hash strands linter (bounded subset).')
    p.add_argument('paths', nargs='+')
    p.add_argument('--format', choices=['text', 'json', 'sarif'], default='text')
    p.add_argument('--fail-on-findings', action='store_true')
    args = p.parse_args()
    try:
        findings = [f for path in args.paths for f in lint(path)]
    except (ValueError, OSError, SyntaxError) as error:
        print(f'parse error: {error}', file=sys.stderr)
        return 2
    emit(findings, args.format, 'vcl-keylint')
    return int(args.fail_on_findings and any(f['score'] in ('NONE', 'WEAK') for f in findings))


if __name__ == '__main__':
    sys.exit(main())
