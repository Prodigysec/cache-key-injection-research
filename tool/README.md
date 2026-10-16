# ckinject

A black-box cache key fuzzer, in two stages:

- `discover` — which headers/cookies/query params is the cache actually
  keying on at all? (Not "surefire" — see docs/04-testing-methodology.md
  for what this can and can't prove.)
- `probe` — for a pair of fragments you already believe are keyed, is the
  boundary between them ambiguous? Automates the split-marker technique:
  sends a baseline, a boundary-shifted, and a control request, and
  reports where the cache collapses two different requests into the same
  key.

Run `discover` first to find candidates, then feed what it finds into
`probe --pair` to test for the actual exploitable collision.

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

### Fragment discovery (run this first)

```bash
ckinject discover --target http://localhost:8080 --base-path /discoverlab
```

(Against this repo's lab specifically, use `/discoverlab` rather than
`/fuzz` — `/fuzz` only keys on one header, which doesn't show off a tool
meant to classify headers, cookies, *and* query params. See
`docs/02-reproduction-guide.md`'s "Fragment discovery target" section.)

Tests a built-in candidate list of common headers, cookies, and query
params (`tool/ckinject/wordlists.py`), plus anything you add, against the
target's actual caching behavior — not a boundary test, just "is this
fragment part of the key at all?" For each one it reports `KEYED`,
`unkeyed`, or `inconclusive` (the target didn't behave deterministically
enough to tell), and suggests `--pair` combinations to feed into `probe`
for anything found keyed.

Always extend the built-in lists with whatever recon turns up for the
real target — an app-specific cookie name, a custom header, a param you
saw in its own requests. The defaults are generic starting points, not a
claim of completeness:

```bash
ckinject discover --target https://example.com --base-path /somepath \
  --extra-header X-App-Tenant \
  --extra-cookie locale_pref \
  --extra-param currency
```

Use `--no-default-wordlist` to test only your own `--extra-*` names, and
`--value1`/`--value2` to change the two probe values if the defaults
(`ckdiscoverA`/`ckdiscoverB`) would trip up validation on a picky header
(e.g. `Authorization` expecting a particular format).

A result of `inconclusive` means the baseline request didn't match itself
on repeat — the target may not be deterministic for that path, isn't
actually caching it, or something about the probe tripped an error page.
Try a different `--base-path`.

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

This is a starting point, not a finished scanner. `discover` (above)
covers the "which fragments are keyed at all" gap that used to be
entirely manual. See `docs/03-research-roadmap.md` Track E for what's
still open:

- Encoding-based probes (percent-encoding, Unicode normalization, case
  folding) instead of pure ASCII-shift splitting.
- Duplicate-header probes (does the key use the first or last value when
  a header is repeated?).
- Multi-layer-aware mode: run the same probe through a CDN-fronted URL
  and a direct-to-origin URL (when both are reachable) and diff results
  to spot edge/origin key mismatches.
- A purely *passive* triage pass (no active probing at all — just
  `Vary`/`X-Cache`-style header inspection across a list of URLs) to
  prioritize which targets are worth running `discover`/`probe` against
  in the first place, for large scopes.

Contributions/ideas welcome via issues or PRs on the parent repo.
