# Research roadmap

The original write-up explicitly frames itself as scratching the surface.
This doc breaks that into concrete, trackable workstreams. Each one lists
a hypothesis, how to test it, and what tooling it needs (link to `tool/`
where relevant). Treat this as a backlog — check items off, open an issue
per item, whatever works for you.

## Track A — Other cache implementations

The bug class is "ambiguous concatenation before hashing," not an Nginx
bug. Audit each of these for the same pattern:

- [ ] **Varnish VCL** — `hash_data()` calls are developer-written, string
      by string, in `vcl_hash`. Pull a corpus of real-world VCL configs
      (GitHub code search for `hash_data`) and check how many concatenate
      two variable-length attacker-influenced fields with no delimiter.
      Build a `lab/varnish/` variant of this lab mirroring the Nginx one.
- [ ] **Apache `mod_cache` / `mod_cache_disk`** — key construction rules
      differ; check `CacheKeyBaseURL` and header-based key customization
      modules for the same raw-concatenation pattern.
- [ ] **CDN custom cache key UIs** — Cloudflare Cache Rules ("Custom Cache
      Key" with header/cookie/query component lists), Fastly VCL
      `vcl_hash`, CloudFront Cache Policies (header/cookie/query
      allowlists serialized into a key), Akamai cache-id customization.
      For each: does the platform delimit components, or naively
      join/hash a concatenated string? This requires an account on each
      platform you test — do this only on infrastructure you own.
- [ ] **Application-level caches** — Redis/Memcached keys built in app
      code, e.g. `f"{tenant_id}{resource_path}"` or similar f-string /
      string-concat patterns. Grep open-source codebases for this pattern
      around cache-key construction (`cache.get(` / `cache.set(` calls
      with concatenated args). This is the highest-impact variant because
      collisions here can cross **authorization boundaries**, not just
      HTTP response caching — see Track C.
- [ ] **GraphQL / API gateway response caches** — persisted-query ID +
      serialized variables as the cache key. Check whether variables are
      JSON-encoded (safe-ish) or naively concatenated into the ID.

## Track B — Encoding and normalization angles

The article's collisions are pure string-splitting. These are unexplored
variants that could create collisions even when a naive split doesn't
look possible:

- [ ] **Percent-encoding mismatches** — does the cache key logic
      percent-decode before or after concatenation? If decoding happens
      post-concatenation (or not at all) but the backend decodes before
      routing, `%2F` vs `/` could create a key-stable but
      route-ambiguous collision.
- [ ] **Unicode normalization (NFC/NFKC/NFKD)** — if the key is built from
      a Unicode string and normalized at some point (or not), look for
      characters that normalize into the fragment boundary's delimiter or
      neighboring fragment.
- [ ] **Case folding** — header names/values are often lowercased
      somewhere in the pipeline. Does the *key* use the lowercased or raw
      value? A mismatch between the key's casing and the backend's
      casing-sensitive routing could open a parallel collision class.
- [ ] **Whitespace / tab handling** — leading/trailing whitespace
      stripping differences between the proxy's key-building code and the
      backend's parser.
- [ ] **Duplicate headers** — if `Accept` appears twice, which value does
      the cache key use vs. which value does the backend use? A mismatch
      is a free collision primitive with no character-shifting required.
- [ ] **HTTP request smuggling combos** — can smuggling be used to inject
      a *second* value for a keyed header that only the frontend (cache)
      sees, decoupling the key's view of a fragment from the backend's?

## Track C — Higher-severity impact classes

The article demonstrates ACL bypass, CPDoS, and stored XSS. These are
plausible escalations not yet shown publicly — look for them specifically:

- [ ] **Cross-tenant data leakage** — in multi-tenant SaaS, if a
      tenant/account identifier is a keyed cookie or header adjacent to
      another keyed fragment, a collision could serve Tenant A's cached
      response to Tenant B. This is a severity jump from the article's
      scenarios (info disclosure/XSS on one app) to **cross-customer
      disclosure**, which most bounty programs rate far higher.
- [ ] **Plan/tier confusion** — if a subscription tier or feature-flag
      cookie is keyed (common for serving different UI to free vs. paid
      users), a boundary collision could leak premium content to free
      users, or vice versa (business-logic/billing impact).
- [ ] **Session or auth-state bleed** — if any session-adjacent value is
      keyed (e.g., a "logged in as role X" cookie used only for cache
      variation, not actual auth), check whether a collision can cause one
      user's authenticated response to be served under an unauthenticated
      key, or vice versa.
- [ ] **CSP/nonce reuse** — if a cached page embeds a per-response CSP
      nonce and a collision causes the *wrong* cached page (with a stale
      nonce) to be served alongside a live page expecting that nonce, does
      it weaken the CSP in a detectable way?
- [ ] **Cache-based request smuggling amplification** — chain a key
      collision with an unkeyed-fragment poisoning primitive (the
      "traditional" cache poisoning class) for compounding impact: use the
      key collision to control *which* response slot gets poisoned by the
      unkeyed-fragment payload.

## Track D — Multi-layer cache chains

The article's Cloudflare section is a single bypass trick
(`Authorization` header). This deserves its own sub-research track:

- [ ] **Enumerate known edge-bypass triggers per CDN** beyond
      `Authorization`: `Set-Cookie` in the response, `Cache-Control:
      private`/`no-store` interactions, `Vary: *`, size limits, specific
      file extensions, `Pragma: no-cache` handling differences. For each
      trigger, test whether it reaches a backend origin cache with its own
      ambiguous key.
- [ ] **Three-layer chains** — browser cache → CDN edge → origin cache.
      Each layer may key differently. Map out, per layer, which fragments
      are keyed and how they're joined; the juiciest bugs tend to sit at
      *mismatches between adjacent layers*, not within a single layer.
- [ ] **Edge-layer self-collision** — if the edge cache's *own* key is
      also naive concatenation (not just a bypass trick to reach the
      origin), a single request could poison the edge cache directly,
      affecting the CDN's full cached footprint for that key, not just one
      origin entry.

## Track E — Tooling and automation

- [ ] **Boundary fuzzer** (`tool/ckinject`, in this repo) — black-box
      detection of ambiguous key boundaries via the split-marker technique.
      See `tool/README.md` for current capabilities and `TODO`s there for
      where to extend it (encoding-based probes from Track B,
      multi-layer-aware mode for Track D).
- [x] **Fragment discovery** (`ckinject discover`) — the precursor
      question `probe` used to assume an answer to: is a given
      header/cookie/query param part of the key *at all*. Built-in
      candidate lists plus `--extra-*` for recon-specific names; tested
      against a configurable mock server (`tests/test_discover.py`). Not
      "surefire" (see `docs/04-testing-methodology.md`) — a flat
      candidate-list scan can't prove completeness or catch
      conditional/partial keying.
- [ ] **Passive fingerprinting pass** — before active fuzzing, flag likely
      candidates at scale: presence of `Vary` with multiple fields,
      `X-Cache`/`CF-Cache-Status`/`Age` headers, response differences
      across header permutations. Useful as a prioritization filter over
      a large bug bounty scope before spending active-fuzz budget.
- [ ] **VCL / Nginx config static analyzer** — for whitebox engagements
      or source-available targets, a simple linter that flags
      `proxy_cache_key` / `hash_data()` patterns concatenating 2+
      variable-length fragments without a separator. Coverage and precision require measurement; cheaper than black-box fuzzing
      when you have the config. See Track F below — this is the starting
      point for a fuller dataflow-based version of the same idea.

## Track F — Static dataflow analysis (source-level taint tracing)

Every other track above is black-box: infer the key's structure from
behavior. This track goes white-box: trace the actual data flow, in
source, from request-derived values through string concatenation to the
final cache key, across the real codebases of the cache implementations
themselves. Full methodology, per-ecosystem approach (Nginx, Varnish
VCL, Apache `mod_cache`, app-level/GraphQL caches), and a starter
Semgrep rule set live in `docs/06-static-analysis-dataflow.md` and
`tool/static-analysis/`.

- [ ] Run the starter Semgrep rules (`tool/static-analysis/`) against
      any source-available bug bounty target already in scope — cheap
      addition to normal recon, not a separate project phase.
- [ ] Build the VCL control-flow-aware linter described in the doc
      (parse `vcl_hash`, track reachable `hash_data()` call sequences per
      branch) — meaningfully harder than the Nginx string-split linter
      above because VCL has real control flow.
- [ ] Pull a real-world Nginx/VCL config corpus (GitHub code search) and
      run both linters at scale — likely the highest find-rate-per-hour
      activity in this entire roadmap, since it needs no live target at
      all.
- [ ] Scope out a CodeQL/Joern pass on `mod_cache` (Apache) or Nginx's
      own core as a separate, bigger sub-project — an upstream OSS
      finding here is a different kind of win (project disclosure) than
      a single bug bounty target.
- [ ] Extend the Semgrep rules to more languages/frameworks (Java/Spring,
      Ruby/Rails, Go) as you encounter real app-level caching code in
      those stacks during engagements.

## Suggested order of attack for a solo researcher

1. Run the lab (`docs/02-reproduction-guide.md`) until all four scenarios
   are second nature — you need to recognize the *shape* of this bug
   instantly in a HAR file or a cache-behavior diff.
2. Build out Track E's fuzzer far enough to automate the split-marker
   test from the original article (already scaffolded in `tool/`).
3. Pick ONE of Track A/B/C/D/F to go deep on based on what you have
   access to (your own CDN account → Track D; access to a multi-tenant
   SaaS target in scope → Track C; source-available target → Track F's
   static analysis). Depth beats breadth for actually finding a
   reportable bug. Track F is worth prioritizing if you want the best
   find-rate per hour of effort with no live target required at all.
4. Use `docs/04-testing-methodology.md` before touching anything live,
   and `docs/05-findings-template.md` once you have something to report.

## Static-analysis implementation update (2026-10-12)

Track E has parser-backed Nginx boundary linting and a bounded upstream-Varnish subset interpreter with tests. Track F execution and corpus measurements are recorded in docs/07. Upstream Varnish hash_data calls are internally framed: separate calls are not the unsafe adjacency claimed in the earlier roadmap. Config findings remain leads; include expansion, source correlations, middleware semantics and complete C extraction remain coverage limits. Track C impact escalation still needs a demonstrated collision and authorization-boundary effect.
