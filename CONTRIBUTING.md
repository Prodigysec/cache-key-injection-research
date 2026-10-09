# Contributing

This is a research project, not a product — contributions of all sizes
are welcome: new lab scenarios, new `ckinject` probe types, write-ups of
findings against other cache implementations, corrections.

## Ground rules

- **Authorized testing only.** Nothing added here should assume or
  encourage testing systems without permission. If you're contributing a
  finding or example, use your own lab, a CTF, or a target you had
  explicit authorization for, and scrub anything identifying a real
  program/target unless you have permission to name it (check the
  program's disclosure policy first).
- **No real victim data.** Lab scenarios and examples should use
  synthetic data only (`S3cr3t-Admin-Token-DO-NOT-LEAK` style markers, not
  anything resembling a real secret format).
- **Keep the lab self-contained.** Anything added to `lab/` should run
  fully offline via `docker compose up`. If you add a new scenario that
  needs an external service (a real CDN, a real third-party cache), add a
  simulated stand-in in `lab/` (see `lab/edge-sim/` for the pattern) and
  clearly document it as a simplified simulation.

## Adding a new lab scenario

1. Add the Nginx `location` block (or new service) to `lab/nginx/nginx.conf`
   / `lab/docker-compose.yml`.
2. Add a case to `lab/scripts/run-scenario.sh`.
3. Document it in `docs/02-reproduction-guide.md` following the existing
   format (config excerpt, numbered curl steps, expected result).
4. If it demonstrates a new impact class or fragment pair, add a
   checklist item (checked off) to the relevant track in
   `docs/03-research-roadmap.md`.

## Extending `ckinject`

- New fragment types go in `tool/ckinject/fragments.py` as a new
  `*_slot()` factory function returning a `Slot`.
- New probe strategies (encoding-based, duplicate-header, multi-layer)
  should live as a new module alongside `prober.py`, exposed as a new CLI
  subcommand in `cli.py` — keep `probe` (the generic ASCII-shift test)
  and `scheme-check` focused on what they already do.
- Add a test in `tests/` using `tests/mock_cache_server.py` (extend it if
  your probe strategy needs different mock-server behavior) — every new
  probe type should have both a "vulnerable" and a "safe" mock case, same
  pattern as `tests/test_prober.py`.
- Run `python -m pytest tests/ -v` before opening a PR.

## Reporting a real finding

Don't open a public issue/PR with details of a live, unpatched
vulnerability in a third party's system. Use `docs/05-findings-template.md`
to write it up for the affected program directly. Once it's fixed and
the program's disclosure policy allows it, a sanitized write-up or a new
lab scenario reproducing the general pattern (not the specific target) is
a great contribution back here.

## Style

- Shell scripts: `set -euo pipefail`, keep them readable over clever.
- Python: standard library + `requests`/`flask` only unless there's a
  strong reason otherwise — this should stay easy to read and audit.
- Docs: match the existing tone — direct, technical, no filler.
