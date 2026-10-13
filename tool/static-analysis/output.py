"""Shared JSON/SARIF output; findings are leads, parse errors are fatal."""
import json
from pathlib import Path


def sarif(findings, tool):
    return {'version': '2.1.0', '$schema': 'https://json.schemastore.org/sarif-2.1.0.json',
            'runs': [{'tool': {'driver': {'name': tool}}, 'results': [
                {'ruleId': f['rule'], 'level': 'warning' if f['score'] in ('NONE', 'WEAK') else 'note',
                 'message': {'text': f['message']},
                 'locations': [{'physicalLocation': {'artifactLocation': {'uri': Path(f['path']).resolve().as_uri()},
                                'region': {'startLine': f['line']}}}], 'properties': f}
                for f in findings]}]}


def emit(findings, fmt, tool):
    if fmt == 'json':
        print(json.dumps(findings, indent=2))
    elif fmt == 'sarif':
        print(json.dumps(sarif(findings, tool), indent=2))
    else:
        for f in findings:
            print(f"{f['path']}:{f['line']}: {f['message']}")
        print(f'{len(findings)} boundaries inspected')
