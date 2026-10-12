# ckinject

A black-box cache key boundary fuzzer. Automates the split-marker
technique from `docs/04-testing-methodology.md`: for a set of candidate
fragment pairs (URI, headers, query params, cookies), it sends a
baseline, a boundary-shifted, and a control request, and reports where
the cache collapses two different requests into the same key.

**Authorized testing only.** Your own lab, or in-scope/permitted targets.
Every probe uses a fresh random marker and cache buster so it never
touches another request's (yours or a real user's) cache entry — but you
are still sending real traffic to a real cache; read the methodology doc
before pointing this at anything live.

## Install

```bash
cd tool
pip install -e .
# or, without installing the package:
pip install -r requirements.txt
python -m ckinject.cli probe --target http://localhost:8080
```

Everything below uses the bare `ckinject` command for brevity. If it's
not on PATH after `pip install -e .` (common on Windows — pip warns
about this at install time), substitute `python -m ckinject.cli`
everywhere you see `ckinject` below; they're equivalent.

## Usage

### Generic boundary probe

```bash
ckinject probe --target http://localhost:8080 --base-path /fuzz
```

Against the lab in this repo, use `/fuzz` specifically — it's the one
general-purpose target built to accept arbitrary path suffixes. The
other lab endpoints (`/admin`, `/anyendpoint`, `/home`, ...) are
exact-match Nginx locations demonstrating one specific pair from the
original article each, and won't route a suffixed path anywhere useful.

Runs the default candidate pairs (URI suffix vs. `Accept`,
`Accept-Language`, `Accept-Encoding`, a custom test header; `Accept` vs.
`Accept-Language`; a query param vs. `Accept`) against the target. Add
your own with repeatable `--pair`:

```bash
ckinject probe --target https://example.com --base-path /somepath \
  --pair "path,header:X-App-Lang" \
  --pair "header:X-Tenant,header:Accept"
```

Slot syntax: `path`, `header:<Name>`, `query:<name>`, `cookie:<name>`.

Save full results (including the raw request specs for each probe, useful
when writing up a finding) with `--output report.json`.

### Scheme/Host cross-scheme check

Checks the specific prerequisites for the `https`→`s`+host collision
(Host-header acceptance, HTTP/HTTPS equivalence, Host reflection) and, if
they hold, tells you exactly what to send next:

```bash
ckinject scheme-check \
  --http-url http://localhost:8080 \
  --https-url https://localhost:8443 \
  --host dummywebsite.localhost \
  --insecure
```

## Extending

This is a starting point, not a finished scanner. See
`docs/03-research-roadmap.md` Track E for planned extensions:

- Encoding-based probes (percent-encoding, Unicode normalization, case
  folding) instead of pure ASCII-shift splitting.
- Duplicate-header probes (does the key use the first or last value when
  a header is repeated?).
- Multi-layer-aware mode: run the same probe through a CDN-fronted URL
  and a direct-to-origin URL (when both are reachable) and diff results
  to spot edge/origin key mismatches.
- A passive fingerprinting pass (`ckinject scan`) that triages a list of
  URLs by cache-related headers before spending active-probe budget.

Contributions/ideas welcome via issues or PRs on the parent repo.
