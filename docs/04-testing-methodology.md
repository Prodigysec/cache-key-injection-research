# Testing methodology for live targets

Cache poisoning is unusual among web bug classes: a careless test can
actually poison a response that real users receive. Read this before
pointing anything at a target that isn't your own lab.

## Authorization first

Only test systems where you have explicit permission: a bug bounty
program's defined scope, a pentest engagement's rules of engagement, or
infrastructure you own. Nothing here authorizes testing third parties.

## Blast-radius discipline

1. **Always use a cache buster — but put it in a header, not a query
   parameter, when you're testing a path↔header boundary.** The point of
   a buster is to isolate your test from real traffic, but a query-string
   buster becomes a third, uncontrolled fragment in the key — and in a
   very common key formula (anything keying on the full request URI, or
   on `$is_args$args` the way this repo's lab does), that fragment sits
   physically *between* the path and the header you're trying to collide.
   That silently breaks the exact boundary-shift test you're running,
   without any error — you'll just see "no collision" and have no idea
   it's an artifact of your own cache buster rather than a confirmed
   negative. (This bit `tool/ckinject` itself during development — see
   its changelog/commit history. Use a header like `X-<yourname>-Buster`
   with a random value instead; a query-param buster is still fine when
   you aren't testing a path- or query-adjacent-to-header pair.)
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

**There's no surefire way to find every fragment a cache keys on.** The
candidate space (every possible header, every cookie name, every query
param) is technically unbounded, so black-box testing can only confirm
or rule out what you thought to test — never prove you found everything.
What follows is a systematic process that gets you close, not a complete
algorithm.

Check the `Vary` header first — every field it lists is (at minimum) a
strong candidate for being part of the key, though it's neither necessary
(some caches key without declaring `Vary`) nor sufficient (some CDN edge
caches ignore the origin's `Vary` entirely and key on their own rules).

For each candidate — `Accept`, `Accept-Language`, `Accept-Encoding`,
`Host`, scheme, any app-specific cookie that visibly changes content
(language, A/B test, currency, theme), plus anything recon turns up —
confirm it's actually keyed with the differential oracle: send two
requests differing only in that field, with a buster isolating the test
(point 1 above), and check whether you get two separate cache entries
(two first-hit `MISS` + distinct bodies) or the same entry collapsing
both.

`ckinject discover` automates exactly this against a built-in candidate
list of headers/cookies/params (extendable with `--extra-header`/
`--extra-cookie`/`--extra-param` for anything recon-specific), and
suggests `probe --pair` commands for whatever it finds keyed:

```bash
ckinject discover --target https://example.com --base-path /somepath
```

Limitations worth knowing before trusting a `KEYED`/`unkeyed` verdict: it
tests arbitrary distinguishable string values, not semantically valid
ones (a malformed `Authorization` header might get rejected differently
than a malformed `Accept` header, producing a false `KEYED` from an error
page rather than real keying — override `--value1`/`--value2` if a
candidate's default values look likely to trip validation); a target that
isn't deterministic for the test path reports `inconclusive` rather than
guessing; and conditional/partial keying (a fragment matters only for
certain paths or certain value ranges) can evade a flat single-path test
— rerun against a few different base paths if the target's behavior looks
inconsistent.

### 3. Boundary probe (the core technique)

For each pair of fragments you suspect sit adjacent in the key (e.g. URI
tail and a header value, or scheme and Host):

```
Baseline:
  GET /anyendpoint HTTP/1.1
  Host: target.com
  X-Ck-Buster: R1
  X-Test-Header: 123

Shifted:
  GET /anyend HTTP/1.1          <- same buster value R1, same header slot
  Host: target.com
  X-Ck-Buster: R1
  X-Test-Header: point123
```

(Buster in a header, not `?ckbuster=R1` in the query string — see point 1
above. A query-string buster here would sit between the URI and
`X-Test-Header` in a key formula like the one in this repo's lab, and
would silently invalidate this exact test.)

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
