# Static analysis: tracing ambiguous cache key construction as a taint-flow problem

Everything in `docs/02`–`04` is black-box: you send requests and infer the
key's structure from behavior. This doc covers the white-box complement —
tracing the actual data flow, in source, from request-derived values to
the string (or hash input) that becomes the cache key. The payoff:

- Black-box fuzzing proves a collision *exists* for the pairs you thought
  to test. Source-level tracing can identify places a given codebase
  concatenates two or more variable-length tainted fragments without a
  delimiter — including pairs you'd never have guessed to fuzz.
- It generalizes the "ambiguous concatenation before hashing" insight from
  `docs/01-background.md` into something checkable mechanically, once per
  codebase, instead of once per black-box target.

## The taint model

Define the bug class as a standard source → propagator → sink problem:

- **Source**: any value derived from the request that can vary per
  request and that the application/cache treats as part of the cache
  identity — a header value, a cookie, a query parameter, a path
  segment, the scheme, the negotiated language, a feature-flag/tenant
  value pulled from a JWT, etc. In most codebases these are easy to
  enumerate: `req.headers[...]`, `request.GET[...]`, `$http_*` Nginx
  variables, `req.Cookie(...)`, GraphQL `variables`, and so on.
- **Propagator (the interesting part)**: string concatenation, string
  formatting (f-strings, `.format()`, template literals, `sprintf`,
  Nginx's bare variable concatenation in `proxy_cache_key`), or
  `+=`/`Append`-style building of a key string from two or more sources.
  The propagator is "unsafe" specifically when it joins **two or more
  variable-length tainted values with no fixed, non-taintable separator
  between them** — that's the exact condition for the collision in
  `docs/01-background.md`.
- **Sink**: the final string (or bytes) handed to a hash function
  (`md5`, `crc32`, Nginx's internal key hasher) or used directly as a
  lookup key into a cache store (`cache.get(key)`, `redis.get(key)`,
  a dict/map keyed by the string, Varnish's `hash_data()` accumulator).

A finding is: **a path from ≥2 distinct sources through an unsafe
propagator to a single sink**, where no propagator step in between
inserts a fixed, taint-free separator (a literal character/byte that
cannot itself appear as part of either source's value — see the note on
"weak" delimiters below).

### Delimiters can be unsafe too — don't stop at "is there a separator"

A naive version of this analysis just flags "concatenation with no
separator at all." That under-counts real bugs. A separator is only a
real fix if it's impossible for either adjacent source value to contain
that separator character itself (or an encoded form of it that gets
decoded before hashing). E.g. `path + "|" + accept` is still exploitable
if `path` can itself contain a literal `|` (most URL path segments allow
arbitrary bytes once percent-decoded) — the attacker just needs to also
control the fixed point. This is a conservative lead, not a sufficient proof: separator occurrence in only one source can still permit an unambiguous first/last-separator split. A thorough static check should flag:

- No separator at all → confirmed unframed construction; collision feasibility still needs source/control and length review. Fixed lengths, constrained alphabets and dependent sources can prevent collisions.
- A separator drawn from a charset either source can contain → likely
  still unsafe, flag for manual review.
- A separator that's structurally impossible for either source to
  contain (e.g. a NUL byte in a context where NUL can't survive
  transport, or a length-prefix encoding instead of a literal
  character) → likely safe.
- Each fragment hashed independently before concatenating the digests
  (`md5(path) + md5(accept)`) → safe, this is the recommended fix from
  `docs/01-background.md`.

## Per-ecosystem approach

Each cache implementation needs a different analysis strategy because
they're different languages/DSLs. Roughly in order of how tractable the
analysis is:

### Nginx (`proxy_cache_key`, `fastcgi_cache_key`, etc.)

Not a general-purpose language — it's a declarative config directive, a
single string template. No real dataflow analysis needed, just a
pattern-matcher. This is already covered as "Track E: static analyzer"
in `docs/03-research-roadmap.md` — a linter that parses the directive's
string argument, splits it on `$variable` boundaries, and flags any
adjacent pair of variables where neither is a fixed literal. Treat this
as the baseline/reference implementation before tackling the harder
ecosystems below; the scoring logic (separator strength, above) belongs
here too.

### Varnish VCL (upstream Varnish, not Fastly)

Verified against commit [0038dd1](https://github.com/varnishcache/varnish-cache/tree/0038dd19804fd92cd8bd4bfe92e5a515a57d5e8e).
[`VRT_hashdata`](https://github.com/varnishcache/varnish-cache/blob/0038dd19804fd92cd8bd4bfe92e5a515a57d5e8e/bin/varnishd/cache/cache_vrt.c#L723) feeds each strand into the hash, then invokes `HSH_AddString(..., NULL)`.
[`HSH_AddString`](https://github.com/varnishcache/varnish-cache/blob/0038dd19804fd92cd8bd4bfe92e5a515a57d5e8e/bin/varnishd/cache/cache_hash.c#L216) appends an internal separator byte on that NULL call.
Thus `hash_data(req.url); hash_data(req.http.host);` preserves the call boundary; the old claim that this idiom needs an extra literal call was wrong. A literal call can add data but is unnecessary for call framing. Within one call, `hash_data(req.url + req.http.Accept)` still joins strands before the call's final separator.

The bounded subset parser in `tool/static-analysis/vcl_keylint/` handles subroutines, if/elsif/else, call, return and string/variable strands. It explores both branches without proving conditions satisfiable, caps paths, and reports unsupported reachable statements as UNKNOWN. It does not parse the entire VCL language or track set-variable provenance. Separate calls are never flagged as raw-concatenation bugs.

[Upstream hashing documentation](https://github.com/varnishcache/varnish-cache/blob/0038dd19804fd92cd8bd4bfe92e5a515a57d5e8e/doc/sphinx/users-guide/vcl-hashing.rst) states that builtin URL and Host/server-IP hashing follows user code on fallthrough; `return(lookup)` stops that append. The builtin implementation itself uses framed calls. This version-specific source review is not a runtime collision reproduction.

### Apache (`mod_cache`, `mod_cache_disk`) and other C-based proxies

These are general C codebases. Use a real static analysis tool with
interprocedural taint tracking:

- **CodeQL** (C/C++ query pack) — define a source query for request
  field accessors (`apr_table_get(r->headers_in, ...)`, `r->uri`,
  `r->parsed_uri.query`), a sink query for the cache-key construction
  functions (the optional `ap_cache_generate_key` hook and its default
  `cache_generate_key_default`),
  and a taint-tracking query connecting them through `apr_pstrcat`/
  `apr_psprintf`/string concatenation calls with no intervening literal.
- Alternative: **Joern** (works well for C, has a good dataflow query
  language, lower setup cost than CodeQL for a single targeted query).
- This is genuinely deep work — budget it as its own sub-project, not a
  quick add-on. Worth it because a confirmed bug in `mod_cache` itself
  (not just a misconfiguration) would be a disclosure to the Apache
  project, not just a single bug bounty target.

At inspected Apache commit [9e1473f](https://github.com/apache/httpd/tree/9e1473f2c6143401cc4ade0a5188966532ac30e8), the default lives in [cache_storage.c](https://github.com/apache/httpd/blob/9e1473f2c6143401cc4ade0a5188966532ac30e8/modules/cache/cache_storage.c#L666), not cache_util.c. It delegates to `cache_canonicalise_key`, whose final assembly includes `://`, formatted port material and `?`. [mod_cache.c](https://github.com/apache/httpd/blob/9e1473f2c6143401cc4ade0a5188966532ac30e8/modules/cache/mod_cache.c#L2517) selects the default when no optional hook is registered. These are real key paths; source inspection alone does not prove a collision.

### CDN "custom cache key" UIs (Cloudflare Cache Rules, Fastly, CloudFront)

Closed source — no static analysis possible on the platform's own
implementation. The practical approach here is still black-box (Track D
in the roadmap): configure a custom key with 2+ components on your own
account and observe behavior, since you can't read Cloudflare's/AWS's
source. If a platform's custom-key feature uses **VCL under the hood**
(Fastly does), inspect its own documented semantics. Fastly uses [req.hash](https://www.fastly.com/documentation/reference/vcl/variables/cache-object/req-hash/) and [vcl_hash](https://www.fastly.com/documentation/reference/vcl/subroutines/hash/); do not transfer upstream Varnish VRT_hashdata framing assumptions to it. Fastly is outside the current linter coverage.

### App-level caches and GraphQL/API gateway caches (Python/JS/Java/Ruby/Go)

This is the highest-value, most tractable target for general-purpose
taint tools, and the most consequential (Track C: collisions here can
cross authorization boundaries, not just poison an HTTP response).

- **Semgrep** — fast to write, works across languages, good enough for
  *intraprocedural* cases (source and sink in the same function/call
  chain), which covers a large fraction of real cache-key bugs since
  key-building functions tend to be small and local. See
  `tool/static-analysis/semgrep-rules.yml` in this repo for a starting
  rule set (Python/JS patterns like `cache.set(f"{a}{b}", ...)` and
  `redis.get(req.path + req.headers.get(...))`).
- **CodeQL** — needed when the source and the sink are in different
  functions/files (e.g. a request field is read in a view/controller,
  passed through two layers of helper functions, and only concatenated
  into a key deep inside a caching decorator/middleware). CodeQL's
  per-language standard libraries already model common web framework
  sources (Flask/Django `request.*`, Express `req.*`, Spring
  `HttpServletRequest`), so you mostly need to write the *sink* and
  *propagator* definitions yourself — the sources are often already
  modeled.
- GraphQL specifically: trace from `variables` (the source, since
  persisted-query caching keys on `(query_id, variables)`) through
  whatever serializes `variables` into the cache key — JSON-encoding the complete tuple/list of fragments preserves boundaries. Encoding variables alone does not establish how the complete key is framed, but it also does not prove a collision. The former GraphQL pattern matched any query ID plus JSON without request-flow evidence; it was speculative and is not treated as a confirmed finding.

## What to do with a finding

Same as everywhere else in this repo: a static finding is a *lead*, not
a confirmed bug. Before reporting (or before trusting it enough to build
a lab scenario around it):

1. Confirm the flagged sources are actually both attacker-controllable
   in a live deployment (some "sources" are only ever set by trusted
   internal code, not the end request).
2. Confirm the sink is actually used as a cache lookup key (not, e.g., a
   log line that happens to concatenate the same fields).
3. Where feasible, reproduce the collision dynamically — build a
   `lab/` scenario against the real OSS component (self-host Apache +
   `mod_cache`, a real Varnish instance with the flagged VCL pattern) and
   confirm it the same way `docs/02-reproduction-guide.md` does for
   Nginx, rather than relying on the static finding alone.
4. If the finding is in an open-source project's own code (Apache,
   Varnish, Nginx) rather than a specific deployment's config, this is a
   **supply-chain-level disclosure** — report it to the project directly
   following their security process, not as a single bug bounty
   submission.

## Suggested order of attack

1. Start with the Nginx/VCL linters (`tool/static-analysis/`) — they're
   the lowest-effort, highest-signal-to-noise starting point and
   directly extend Track E.
2. Pull a corpus of real-world Varnish VCL and Nginx configs (GitHub code
   search, plus any configs you have legitimate access to) and run the
   linters across them at scale — this alone will likely surface more
   instances of the article's exact bug pattern than any amount of
   individual black-box testing.
3. Only move to CodeQL/Joern on C codebases (`mod_cache`, Nginx's own
   core) once the config-level linting is solid — it's a much bigger
   time investment and the payoff (an upstream OSS disclosure) is a
   different kind of win than a bug bounty payout.
4. In parallel, the Semgrep rules for app-level/GraphQL caches are cheap
   to run against any source-available bug bounty target you're already
   looking at — treat this as a lightweight addition to recon, not a
   separate project phase.

## Verified execution status

See `07-corpus-scan-results.md` and `tool/static-analysis/results/` for measured outputs, pinned revisions and limitations. Nginx docs specify [`$scheme$proxy_host$request_uri`](https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_cache_key), close to `$scheme$proxy_host$uri$is_args$args`. The lab uses customized request-host/header variants; do not conflate them with the built-in key. The [core hash input](https://github.com/nginx/nginx/blob/2b5c2b605b5df669da5dec6749dcc76c07d1315d/src/http/ngx_http_file_cache.c#L228) iterates key buffers with MD5 updates; hashing alone adds no fragment framing.

A bare pipe separator in docs/01 is not a generally sufficient remediation. Use structural encoding of the complete tuple, fixed-width per-fragment digests, or escaping tied to a separator excluded by the encoded alphabet. Percent-quoting alone followed by undelimited concatenation is still ambiguous.
