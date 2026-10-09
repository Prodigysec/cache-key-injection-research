# Testing methodology for live targets

Cache poisoning is unusual among web bug classes: a careless test can
actually poison a response that real users receive. Read this before
pointing anything at a target that isn't your own lab.

## Authorization first

Only test systems where you have explicit permission: a bug bounty
program's defined scope, a pentest engagement's rules of engagement, or
infrastructure you own. Nothing here authorizes testing third parties.

## Blast-radius discipline

1. **Always use a cache buster.** Append a unique, high-entropy query
   parameter (`?ckbuster=<random>`) to every probe request so you create
   and observe your own isolated cache entry instead of touching one real
   users might hit. Never omit this "just to check quickly."
2. **Prefer low-traffic, low-sensitivity endpoints for initial probing.**
   Dummy/test endpoints, 404 pages, or a path you know is rarely hit are
   safer first targets than the homepage or a sensitive page.
3. **Keep TTLs in mind.** If you successfully poison something, note the
   cache's `proxy_cache_valid` / TTL behavior (often visible via `Age` or
   `X-Cache` headers across repeated requests) so you know how long your
   test artifact will linger and can plan around it.
4. **Verify content, not just headers.** An `X-Cache: HIT` alone doesn't
   prove impact — diff the actual response body/headers against what the
   endpoint should return. Programs want evidence of what a *real* victim
   would have received.
5. **Have a cleanup plan.** If your test poisons a cache entry a real
   user could hit before it expires, know how to invalidate it (purge
   API, waiting out the TTL, or triggering a fresh legitimate request if
   that's sufficient) and be ready to do so immediately, especially for
   anything beyond your own cache-busted key.

## Step-by-step black-box test (no source/config visibility)

### 1. Confirm a shared cache exists

Look for `X-Cache`, `CF-Cache-Status`, `Age`, or repeatable response-time
drops on identical requests. If there's no shared cache, this bug class
doesn't apply.

### 2. Enumerate candidate keyed fragments

Check the `Vary` header — every field it lists is (at minimum) a strong
candidate for being part of the key. Also test common candidates even
when absent from `Vary` (some implementations key without declaring
`Vary`): `Accept`, `Accept-Language`, `Accept-Encoding`, `Host`, scheme,
any app-specific cookie that visibly changes content (language, A/B test,
currency, theme).

For each candidate, confirm it's actually keyed: send two requests
differing only in that field, with a cache buster, and check whether you
get two separate cache entries (two first-hit `MISS` + distinct bodies) or
the same entry.

### 3. Boundary probe (the core technique)

For each pair of fragments you suspect sit adjacent in the key (e.g. URI
tail and a header value, or scheme and Host):

```
Baseline:
  GET /anyendpoint?ckbuster=R1 HTTP/1.1
  Host: target.com
  X-Test-Header: 123

Shifted:
  GET /anyend?ckbuster=R1 HTTP/1.1          <- same cache buster value R1
  Host: target.com
  X-Test-Header: point123
```

If the shifted request returns the baseline's cached response (same
cache buster, same content), the cache concatenates those two fragments
without a boundary and you've found a collision. Repeat across every
candidate pair from step 2 — this is what `tool/ckinject` automates.

### 4. Determine impact

Once you have a reliable collision primitive:

- Is there an ACL-protected or sensitive endpoint whose path/value you
  can reconstruct via the collision while your own request fails the ACL
  independently? → cache deception.
- Can you pre-poison a key for a legitimate, frequently-requested
  resource with an error/garbage response before real traffic arrives? →
  CPDoS. (Test this with extreme care — this is the scenario most likely
  to affect real users. Strongly prefer testing this only against your
  own infrastructure or with the program's explicit sign-off.)
- Is there a reflected value (Host, a header, a query param) that lands
  in an executable sink (`<script src>`, inline handler, `href`) in a
  cacheable response, reachable via a collision that lets you control the
  reflected value independent of a "real" request to that path? → stored
  XSS / content injection.
- Is there a CDN/edge layer in front of the cache you're targeting? Test
  known edge-bypass triggers (see `docs/03-research-roadmap.md`, Track D)
  to determine whether you can reach and poison the inner cache directly.

### 5. Document precisely

Capture, for the report:

- Exact baseline and colliding requests (raw HTTP, not just curl
  commands — triagers need to reproduce byte-for-byte).
- Response headers proving the collision (`X-Cache`/`CF-Cache-Status`
  transitions from MISS→HIT across the two requests).
- The actual differing content served (screenshot or body diff).
- Your cache-buster discipline — explicitly state you isolated your test
  and didn't affect real traffic, and give the TTL/expiry you observed.

See `docs/05-findings-template.md` for a ready-to-fill report skeleton.
