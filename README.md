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

Prerequisites: Docker Desktop (or Docker Engine) running with Linux containers,
Docker Compose and Buildx, Bash (Git Bash on Windows), OpenSSL, and Python/pip
for the CLI tool.

```bash
# 1. Stand up the lab
cd lab
bash scripts/start-lab.sh

# 2. Reproduce the ACL-bypass / cache-deception scenario
curl -s -o /dev/null -w "%{http_code}\n" -H "Accept: */*" http://localhost:8080/admin  # 403, denied (not localhost)
bash scripts/seed-admin-cache.sh                              # seeds the cache as if requested from localhost
curl -s -H "Accept: min*/*" http://localhost:8080/ad -D -      # collides, returns cached admin response

# 3. Run the fuzzer against the lab
cd ../tool
pip install -e .
ckinject probe --target http://localhost:8080 --baseline-path /anyendpoint
```

The startup script creates the certificate directory and generates certificates
using relative paths compatible with Windows OpenSSL. It reuses existing
nonempty certificates, exports the Compose build configuration to a temporary
file, builds through Bake directly, and starts containers with `--no-build`.
This avoids the Compose-to-Bake pipe error and the deprecated
`COMPOSE_BAKE=false` workaround. The temporary file is removed on exit,
and a failed setup step prevents startup.

The script resolves paths from its own location. From the repository root,
run `bash lab/scripts/start-lab.sh`; if you are already in
`lab/nginx/certs`, run `bash ../../scripts/start-lab.sh`. Run it again to
rebuild and restart after code changes. Check service status from `lab/`
with `docker compose ps`.

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