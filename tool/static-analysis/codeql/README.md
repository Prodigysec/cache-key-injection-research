# C/C++ query pack

Pinned CLI: CodeQL **2.23.8**; library: **codeql/cpp-all 6.1.3**, transitive versions in codeql-pack.lock.yml.

`cache_generate_key_default` delegates to `cache_canonicalise_key` in Apache cache_storage.c at the inspected revision, so both names are modeled. The source model covers request fields and inbound APR table reads, plus Varnish request accessor calls. The propagator model covers APR-returned strings and selected Nginx sprintf output buffers. The sink model covers default/canonical Apache key assignments and Nginx/Varnish hash inputs. These are narrow, name-based models: VRT_GetHdr context, native pointer aliases, complex copy/array operations and optional callbacks need review.

`request-to-cache-key.ql` reports general flow leads, not collisions. `ambiguous-cache-concat.ql` requires adjacent nonliteral APR concat operands with distinct modeled sources and a **local** flow from the join to a real key sink; it is not an all-framework ambiguity detector. `extraction-inventory.ql` checks whether key function definitions survived extraction. Neither query establishes variable-length control or excludes all safe delimiter constraints.

Build public checkouts outside the repo, using pinned revisions in ../results/upstream-revisions.json:

```powershell
codeql pack install tool/static-analysis/codeql
codeql database create /path/db --language=cpp --build-mode=none --source-root=/path/source --threads=1
codeql query compile --check-only tool/static-analysis/codeql --threads=1 --ram=2466
codeql database analyze /path/db tool/static-analysis/codeql/request-to-cache-key.ql tool/static-analysis/codeql/ambiguous-cache-concat.ql --format=sarifv2.1.0 --output=/path/result.sarif --threads=1 --ram=2466
```

The current Windows no-build extractions are predominantly **partial** (missing platform/generated/APR headers). A zero-result scan on these databases is not evidence that the components are free of this bug class. Exact results and failed attempts belong in ../results/ and docs/07. Joern was not used; CodeQL extraction was feasible, though coverage and memory constrained. Runtime lab tests require Docker access and are separate from static query execution.
