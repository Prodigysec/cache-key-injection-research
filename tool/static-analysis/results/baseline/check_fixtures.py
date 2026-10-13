#!/usr/bin/env python3
"""
Runs the Semgrep rules against fixtures/python_examples.py and checks
that every VULNERABLE_* function gets at least one hit and every
SAFE_* function gets none. Exits non-zero (with a clear message) if
the rules don't match expectations -- this is what actually validates
semgrep-rules.yml, since the sandbox that originally wrote this repo
had no network access to install/run Semgrep itself.

Usage:
    pip install semgrep
    python3 check_fixtures.py
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
FIXTURE = HERE / "fixtures" / "python_examples.py"
RULES = HERE / "semgrep-rules.yml"


def function_ranges(path: Path) -> dict[str, tuple[int, int]]:
    """Map function name -> (start_line, end_line) by scanning for `def `
    at column 0 (fixtures are flat, no nesting) and using the next such
    line (or EOF) as the end boundary."""
    lines = path.read_text().splitlines()
    starts = [(i + 1, line.split("(")[0].replace("def ", "").strip())
              for i, line in enumerate(lines) if line.startswith("def ")]
    ranges = {}
    for idx, (start, name) in enumerate(starts):
        end = starts[idx + 1][0] - 1 if idx + 1 < len(starts) else len(lines)
        ranges[name] = (start, end)
    return ranges


def run_semgrep() -> list[int]:
    result = subprocess.run(
        ["semgrep", "--config", str(RULES), "--json", "--quiet", str(FIXTURE)],
        capture_output=True, text=True,
    )
    if result.returncode not in (0, 1):  # semgrep exits 1 when findings exist
        print(result.stderr, file=sys.stderr)
        raise SystemExit(f"semgrep failed with exit code {result.returncode}")
    data = json.loads(result.stdout)
    return [r["start"]["line"] for r in data["results"]]


def main() -> int:
    ranges = function_ranges(FIXTURE)
    hit_lines = run_semgrep()

    failures = []
    for name, (start, end) in ranges.items():
        hits_in_range = [l for l in hit_lines if start <= l <= end]
        if name.startswith("VULNERABLE_") and not hits_in_range:
            failures.append(f"  MISSED: {name} (lines {start}-{end}) expected a hit, got none")
        if name.startswith("SAFE_") and hits_in_range:
            failures.append(f"  FALSE POSITIVE: {name} (lines {start}-{end}) got hit(s) at {hits_in_range}")

    if failures:
        print("semgrep-rules.yml does not match fixture expectations:")
        for f in failures:
            print(f)
        return 1

    print(f"OK: all {sum(1 for n in ranges if n.startswith('VULNERABLE_'))} VULNERABLE_* "
          f"functions flagged, all {sum(1 for n in ranges if n.startswith('SAFE_'))} "
          f"SAFE_* functions clean.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
