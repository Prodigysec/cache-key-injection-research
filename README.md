# Cache Key Injection Research

A reproducible lab, a boundary-fuzzing CLI tool, and a research roadmap for
**cache key injection** — a cache poisoning subclass where a cache builds its
key by concatenating request-derived fragments without clear boundaries,
letting an attacker shift data between fragments to force a key collision
between two *different* requests.

This project is built around the public research by Alex "Brumens" Brumen
(YesWeHack Lab), ["Cache key injection: Smuggling poison through the
door"](https://www.yeswehack.com/lab/research-cache-key-injection), and
extends it with:

- A self-contained Docker lab that reproduces every documented primitive
  (ACL bypass / cache deception, CPDoS, cross-scheme stored XSS, and the
  Cloudflare-bypass-to-origin scenario) so you can see and verify each
  collision yourself.
- `ckinject`, a black-box boundary-fuzzing CLI for finding key-boundary
  ambiguity on real targets (authorized testing only).
- A research roadmap covering unexplored fragment pairs, other cache
  implementations (Varnish, CDNs, app-level caches), encoding/normalization
  angles, and higher-severity impact classes (cross-tenant leakage, plan/tier
  confusion) beyond what the original write-up demonstrated.
- A findings template and testing methodology for turning a lab result into
  a reportable bug bounty submission.

## ⚠️ Scope and ethics

Everything here is for **authorized testing only**: your own lab, CTFs, or
programs/targets where you have explicit permission (bug bounty scope,
pentest engagement, your own infrastructure). Cache poisoning affects
*other users*, not just the tester — see `docs/04-testing-methodology.md`
for cache-buster discipline and blast-radius controls before touching
anything live. Do not use `ckinject` against systems you are not authorized
to test.

## Layout

```
docs/                     Background, reproduction guide, roadmap, methodology, findings template
lab/                       Docker lab: Nginx + backend, one scenario per documented primitive
tool/ckinject/             Boundary-fuzzing CLI (black-box key-collision prober)
tests/                     Automated checks that the lab scenarios behave as documented
```

## Quick start

```bash
# 1. Stand up the lab
cd lab
chmod +x scripts/*.sh
./scripts/gen-certs.sh
docker compose up -d --build

# 2. Reproduce the ACL-bypass / cache-deception scenario
curl -s -o /dev/null -w "%{http_code}\n" -H "Accept: */*" http://localhost:8080/admin  # 403, denied (not localhost)
./scripts/seed-admin-cache.sh                                  # seeds the cache as if requested from localhost
curl -s -H "Accept: min*/*" http://localhost:8080/ad -D -      # collides, returns cached admin response

# 3. Run the fuzzer against the lab
cd ../tool
pip install -e .
ckinject probe --target http://localhost:8080 --baseline-path /anyendpoint
```

See `docs/02-reproduction-guide.md` for the full walkthrough of all four
scenarios, and `docs/03-research-roadmap.md` for what to build on next.

## Credit

Original research: Alex Brumen ([@Brumens2](https://x.com/Brumens2)),
researcher enablement analyst at YesWeHack. This repo is an independent
reproduction/extension for research and bug bounty purposes; it is not
published or endorsed by YesWeHack. Read the original write-up first:
https://www.yeswehack.com/lab/research-cache-key-injection

## License

MIT for all code in this repo (`lab/`, `tool/`, `tests/`). See `LICENSE`.