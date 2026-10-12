# Executed static-analysis results

This is a source/configuration research run, not a claim that the scanned projects are safe. Traffic was sent only to the existing local lab. No upstream issue, PR, or disclosure was opened.

## Tool versions and evidence

The executed versions were Semgrep 1.180.0, Crossplane 0.5.8, CodeQL CLI 2.23.8, codeql/cpp-all 6.1.3, pytest 8.3.3 and Python 3.14.6 on Windows. Python dependencies and compatible transitive constraints are pinned in [requirements.txt](../tool/static-analysis/requirements.txt); the CodeQL pack and lock are in [codeql/](../tool/static-analysis/codeql/). CI uses Python 3.12; the hosted workflow itself was not run in this session.

Raw outputs, original baseline inputs, manifests and extraction inventories are in [results/](../tool/static-analysis/results/). SARIF files are gzip-compressed without discarding extraction diagnostics. Upstream clones, databases and downloaded corpus files remain outside the repository; the collector can recreate the public sample from its pinned manifest.

## Semgrep before and after

The unchanged original rules and helper were actually run with a complete Semgrep installation:

~~~text
Semgrep 1.180.0
python tool/static-analysis/check_fixtures.py
OK: all 3 VULNERABLE_* functions flagged, all 3 SAFE_* functions clean.
exit 0
~~~

The raw scan had four hits: the f-string rule at line 19 twice (get and set), at line 23 once, and the plus rule at line 28. The helper's SAFE_delimited classification was wrong: a bare pipe can appear in request input. It had no JS/TS coverage. When the old rules were run on the new annotated fixtures, they produced two hits: one expected Python finding and one false positive for a repeated single source. They matched 1 of 23 expected positive locations and missed 22; this is fixture performance, not corpus recall. The speculative GraphQL rule lacked a demonstrated request-to-key flow and was removed; no measured GraphQL false positive is claimed.

The replacement uses four taint rules: Python and JS/TS, each with no-delimiter and weak-delimiter severities. Conditional labels require two request-derived operands at a joined expression and then a modeled cache-key sink. Fragment hashing, structural JSON serialization, tested length-prefix and encoding forms have negative tests. Hashing the complete joined value remains a positive case.

Each command below was run separately, exiting zero:

~~~text
semgrep --test --config tool/static-analysis/semgrep-rules.yml tool/static-analysis/fixtures/native/semgrep-rules.py
2/2: ✓ All tests passed
semgrep --test --config tool/static-analysis/semgrep-rules.yml tool/static-analysis/fixtures/native/semgrep-rules.js
2/2: ✓ All tests passed
semgrep --test --config tool/static-analysis/semgrep-rules.yml tool/static-analysis/fixtures/native/semgrep-rules.ts
2/2: ✓ All tests passed
No tests for fixes found.
~~~

There are 23 expected finding locations and 22 negative statements. File-config plus directory-target discovery failed inside Semgrep 1.180.0 with an IndexError; explicit file pairs work and are used in CI. Receiver names, request accessors and sanitizer forms are heuristic and bounded. Same-source aliases can still false-positive. Arbitrary builders, interprocedural flow, Java/Spring, Go, Rails, decorators and generic middleware wrappers are not comprehensively modeled. Passing these fixtures does not establish general accuracy.

## Configuration linters and runtime follow-up

The Nginx CLI parses grammar using Crossplane, tokenizes key arguments, and reports NONE, WEAK, STRONG or UNKNOWN boundaries as text, JSON or SARIF. Its documented variable table includes attacker control, charset and length properties with official references. NONE means absent framing in the expression, not a confirmed exploitable deployment. Includes are not expanded. Character constraints, correlations and actual routing still need manual checks.

The VCL linter implements a bounded subset of subroutines, conditional branches, calls, returns and hash expressions. Unsupported control flow produces UNKNOWN. Crucially, actual upstream Varnish frames separate hash_data calls, so separate calls are not reported merely because they contain request values. Ambiguous concatenation within one call remains a lead. Tests include an excerpt of public builtin VCL with a pinned source reference.

~~~text
python -m pytest tests/ -q
3 passed in 7.97s
python -m pytest tool/static-analysis/tests -q
18 passed in 0.72s
~~~

The linter tests include lab/nginx/nginx.conf; the CLI also ran on that file. Local pytest plugin autoload was disabled to avoid an unrelated globally installed pytest-asyncio version conflict.

The already-running local Nginx 1.27.5 stack reproduced the URI/Accept collision. With one fresh nonce, /anyendpoint and Accept: static-N returned 200 and dummy endpoint ok. /anyend and Accept: pointstatic-N returned the same 200/body. A fresh-key /anyend control returned 404. The X-Debug-Key values confirmed the differing URI/Accept fragments, whose concatenations are equal. X-Cache was absent, so this evidence does not include a cache HIT header or backend request trace. The initial helper required that absent header and exited 1; the corrected response/control assertion exited 0. An earlier /fuzz attempt returned 404/MISS throughout because the running backend did not expose that newer route. No stack rebuild or lab source change was made. See [local-lab.txt](../tool/static-analysis/results/local-lab.txt).

## Public corpus: a pilot, not measured precision

The resumable collector used public GitHub repository, commit, tree and blob APIs. It pins commits, records content SHA256, checkpoints atomically, spaces requests and respects rate-limit failures. Selection was extension-based (.conf and .vcl), sorted and capped at eight files per seed repository. This biases the sample toward early filenames and does not target actual key definitions.

| Public project | Files | Kind |
| --- | ---: | --- |
| nginx/nginx | 2 | Nginx |
| varnishcache/varnish-cache | 3 | VCL |
| h5bp/server-configs-nginx | 8 | Nginx |
| Total | 13 | 10 Nginx, 3 VCL |

The [manifest](../tool/static-analysis/results/corpus-manifest.json) records exact commits and paths. A Magento recursive tree response remained incomplete after retries and was excluded. An attempted GitHub code search for proxy_cache_key extension:conf returned HTTP 401; no authenticated search results were collected.

The final scanner exited zero: 13 files parsed, zero parse errors, zero reported boundaries/findings. The sampled Nginx files contained no explicit key definitions. Semgrep also exited zero with zero findings/errors, but paths.scanned was empty: this config-only corpus contains no supported Python/JS/TS application code. It provides zero Semgrep coverage.

Manual hit triage has sample size n=0: there are no hits to label true-positive, false-positive or needs-more-context. Measured precision is therefore undefined (0/0), not 100%. A small non-hit audit checked builtin VCL's separately framed calls, example VCL's reliance on builtin hashing, and the Nginx default configuration's lack of an explicit key. These are non-hit checks, not a precision sample. A larger key-bearing configuration and application corpus is required to finish this workstream. [Raw scan](../tool/static-analysis/results/corpus-scan.json).

## CodeQL execution and coverage

The upstream revisions inspected and extracted were:

| Project | Commit | Extraction commands (success / partial / failed) | Query results |
| --- | --- | --- | --- |
| Nginx | 2b5c2b605b5df669da5dec6749dcc76c07d1315d | 0 / 272 / 0 | 0 |
| Varnish | 0038dd19804fd92cd8bd4bfe92e5a515a57d5e8e | 1 / 222 / 0 | 0 |
| Apache httpd, sparse cache modules | 9e1473f2c6143401cc4ade0a5188966532ac30e8 | 0 / 11 / 0 | 0 |

Both request-to-cache-key and ambiguous-APR-concatenation queries compiled and executed on all three databases: **no findings**. The source, propagator and sink models include request fields, APR string builders, Nginx formatting/output pointers and real cache/hash inputs. The general flow query produces leads, not ambiguity proofs; the narrower concatenation query does not prove source charset or attacker control.

Windows build-mode=none extraction lacked generated/platform/APR headers. Inventory found ngx_http_file_cache_create_key but not ngx_http_proxy_create_key; it found VRT_hashdata/HSH_AddString and Apache's default/canonical key functions. Name presence does not prove complete bodies or dataflow. These zero results cannot establish upstream safety. Earlier compilation failed with paging/native-memory errors; sequential single-threaded execution at the effective minimum 2466 MB succeeded. Joern was not used. Full Apache clone failed with an HTTP/2 interruption; an HTTP/1.1 sparse clone succeeded. See [status](../tool/static-analysis/results/codeql-status.txt), command logs, inventories and compressed SARIF in results/.

## Corrections verified against primary sources

1. Varnish's separate hash_data calls have framing: [VRT_hashdata](https://github.com/varnishcache/varnish-cache/blob/0038dd19804fd92cd8bd4bfe92e5a515a57d5e8e/bin/varnishd/cache/cache_vrt.c#L723) invokes [HSH_AddString](https://github.com/varnishcache/varnish-cache/blob/0038dd19804fd92cd8bd4bfe92e5a515a57d5e8e/bin/varnishd/cache/cache_hash.c#L216), including the separator path. User fallthrough invokes builtin hashing; return(lookup) prevents it. [Upstream hashing guide](https://github.com/varnishcache/varnish-cache/blob/0038dd19804fd92cd8bd4bfe92e5a515a57d5e8e/doc/sphinx/users-guide/vcl-hashing.rst).
2. Apache's cache_generate_key_default is in [cache_storage.c](https://github.com/apache/httpd/blob/9e1473f2c6143401cc4ade0a5188966532ac30e8/modules/cache/cache_storage.c#L666), not cache_util.c. It delegates to cache_canonicalise_key; [mod_cache.c](https://github.com/apache/httpd/blob/9e1473f2c6143401cc4ade0a5188966532ac30e8/modules/cache/mod_cache.c#L2517) registers the optional/default selection. The explicit structural separators require semantic assessment, not an automatic vulnerability label.
3. Nginx's documented default is $scheme$proxy_host$request_uri, close to $scheme$proxy_host$uri$is_args$args. The lab adds an Accept fragment. [Official proxy_cache_key documentation](https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_cache_key), [variable documentation](https://nginx.org/en/docs/http/ngx_http_core_module.html#variables).
4. Fastly documents req.hash and its own vcl_hash behavior; upstream Varnish implementation details should not be assumed for it. [req.hash](https://www.fastly.com/documentation/reference/vcl/variables/cache-object/req-hash/), [vcl_hash](https://www.fastly.com/documentation/reference/vcl/subroutines/hash/).
5. Bare-pipe joining is not a general remedy; charset-aware encoding or structural framing matters. Weak delimiters and absence of delimiters are static leads, not sufficiency proofs. Claims of universal detection or zero false negatives were removed. Whole-tuple JSON encoding must not be conflated with concatenating unconstrained fragments.

## Workstream status and next steps

| Workstream | Status | Reason |
| --- | --- | --- |
| Semgrep and CI | Partial | Real baseline, rewritten Python/JS/TS rules and native tests pass; broader frameworks/key builders remain unmodeled. CI commands verified locally, hosted workflow not run. |
| Nginx linter | Done within documented scope | Real parser, variable table, structured output, tests and lab flagging executed. |
| VCL linter | Done within documented subset | Control flow and public fixtures tested; upstream framing and builtin behavior corrected. |
| Public corpus | Partial | Collector/scanner executed; only 13 config files, no hits, no app coverage, precision undefined. |
| Upstream CodeQL | Partial | Databases and queries executed with no findings; incomplete extraction, including missing Nginx proxy key builder. |

Ranked follow-up: (1) the local lab URI/Accept boundary, because a response collision with a fresh-key negative control was reproduced; (2) custom Nginx key definitions joining variable-length URI/args/header values, because constraints and routing determine exploitability; (3) joins inside one VCL hash_data call and application cache-key builders, because the models require more real-world examples. Items 2 and 3 are investigation categories, not findings against a named deployment. No new upstream bug was confirmed, so no responsible-disclosure draft is warranted.

No decision is needed to commit this work. To extend it, priorities are an authenticated key-bearing/app-code corpus and Linux build-based extraction with complete upstream dependencies. Those are outstanding research steps, not completed validation.
