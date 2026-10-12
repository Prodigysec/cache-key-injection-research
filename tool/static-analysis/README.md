# Static analysis: ambiguous cache key construction

Semgrep **1.180.0** has been installed and run. The original six-function Python checker passed; expanded tests showed misses and a repeated-source false positive. The replacement taint rules have native annotated fixtures for every targeted language: Python, JavaScript and TypeScript. Exact outputs and upstream/corpus limitations are in [docs/07](../../docs/07-corpus-scan-results.md) and [results](results/).

## Install and verify

Use Python 3.12 in CI, or the tested Python 3.14.6 Windows environment. Install in a virtual environment:

```bash
pip install -r tool/static-analysis/requirements.txt
for fixture in tool/static-analysis/fixtures/native/semgrep-rules.{py,js,ts}; do
  semgrep --test --config tool/static-analysis/semgrep-rules.yml "$fixture"
done
python -m pytest tool/static-analysis/tests -q
python -m pytest tests/ -q
```

Explicit fixture files avoid a Semgrep 1.180.0 directory-target pairing bug. Native tests check both rule IDs and exact finding lines, including safe near-misses. The old checker and its original rules/fixtures are archived under results/baseline/ for reproducibility; the legacy helper's bare-pipe SAFE label is incorrect as a general security claim.

## Rule scope

Four `mode: taint` rules distinguish absent boundaries (WARNING) from common weak separators (INFO). Request accessors receive REQUEST; operand-focused conditional sources establish LEFT and RIGHT; a join receives JOIN only when both sides are request-derived. A fragment-hash label prevents fixed-width digest joins from receiving JOIN; hashing an already joined value retains JOIN. Final cache key arguments are sinks, so a tainted cache value alone is not flagged. Default propagation carries assignments, string operations and hash inputs; no custom propagator is needed for these tested local cases.

Python source shapes include Flask/Django headers, GET, args, cookies and path, plus Starlette/FastAPI query_params and URL path. JS/TS includes conventional Express req, Koa ctx.request and Fastify request accessors. Receiver names containing cache, plus redis/memcached/client, are heuristic sink models for get/set/delete. Named make_cache_key/cache_key/key_func return values and Next.js unstable_cache key arguments are modeled as leads. Generic Python decorator wiring, functools/cachetools integration, Express middleware wrappers, Java/Spring, Go and Rails are **not comprehensively modeled**.

Sanitizers cover JSON encoding of the entire list/tuple, the tested length-prefix form, and percent encoding with `safe=""` plus a pipe excluded by the encoded alphabet. Per-fragment hashing currently models selected Python hashlib digests and JS crypto SHA-256 hex digests. Percent encoding followed by undelimited concatenation remains flagged. Hash truncation, unequal digest widths, unmodeled wrappers, reassignment and aliases need review.

These are intraprocedural CE rules and do not prove two independent source identities. Syntactically repeated operands are excluded; two aliases of the same request field can still false-positive. Fixed/constrained domains, source-dependent delimiters, arbitrary formatting methods, incremental builders, alternate request variable names and cross-function flows remain coverage limits. String separator filtering is conservative: no absence of a warning proves safety. The old speculative query ID plus JSON rule was removed because it lacked request-flow evidence.

## Config CLIs

Run from tool/static-analysis (or add that directory to PYTHONPATH):

```bash
python -m nginx_keylint ../../lab/nginx/nginx.conf
python -m nginx_keylint /path/nginx.conf --format sarif
python -m vcl_keylint /path/cache.vcl --format json
```

Formats: text, JSON and SARIF 2.1.0. Parse errors exit 2; `--fail-on-findings` exits 1 for NONE/WEAK leads, otherwise 0. Nginx uses Crossplane **0.5.8**, parses one file without include expansion, and scores all adjacent template variables. [Variable definitions and conservative bounds](nginx_keylint/VARIABLES.md) cite official Nginx docs. NONE confirms unframed construction, not exploitable independent control.

The VCL parser covers sub, if/elsif/else, call, return and simple string strands. It bounds branch paths and marks unsupported reachable code UNKNOWN. Upstream Varnish adds a separator after **every hash_data call**: separate calls are safe from this particular boundary ambiguity. The linter flags joins **inside a call**; it does not invent cross-call findings. Builtin URL/Host hashing follows fallthrough and is suppressed by a user return. Fastly req.hash is outside coverage.

[Corpus collection](corpus/README.md) is public-only, rate-aware and resumable. [CodeQL](codeql/README.md) records the pinned CLI/library, real zero-result queries and predominantly partial C extraction. No live third-party target is contacted. Findings are leads: follow docs/06 before claiming a bug or impact.
