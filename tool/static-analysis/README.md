# Static analysis: ambiguous cache key construction

Starter Semgrep rules implementing the taint model from
`docs/06-static-analysis-dataflow.md`: flag cache/lookup key construction
that concatenates two or more request-derived values with no delimiter
between them.

**Status: syntax-validated, not yet run against Semgrep.** This repo's
sandbox didn't have network access to install Semgrep, so
`semgrep-rules.yml` has been checked for valid YAML structure but the
rules themselves haven't been confirmed to actually fire correctly
against the fixtures. Run this before trusting them:

```bash
pip install semgrep
cd tool/static-analysis
semgrep --config semgrep-rules.yml fixtures/
```

Expected: every `VULNERABLE_*` function in `fixtures/python_examples.py`
flagged, every `SAFE_*` function not flagged. If that's not what you see,
the rule patterns need fixing — Semgrep's pattern-matching syntax is
fiddly (especially `metavariable-pattern` scoping), so treat a first
mismatch as likely, not surprising.

## What these rules catch (and don't)

- **Catches**: the common, local case — source and sink in the same
  function, built with an f-string/template literal or `+` concatenation.
- **Misses**: anything interprocedural (a header read in one function,
  concatenated into a key three call-frames away) — that needs CodeQL,
  see `docs/06-static-analysis-dataflow.md`'s per-ecosystem section.
- **Misses**: Nginx `proxy_cache_key` / Varnish `hash_data()` — those are
  config DSLs, not general-purpose languages Semgrep parses. Those need
  the dedicated linter described as "Track E" in
  `docs/03-research-roadmap.md` (not yet built — contributions welcome).
- **False positives are expected and by design**: every hit is a *lead*
  per `docs/06-static-analysis-dataflow.md`'s "What to do with a
  finding" section — confirm the separator is actually missing/weak and
  both sources are actually attacker-controlled before trusting it.

## Extending

- Add more source patterns as you find them in real frameworks (Django's
  `request.GET`, Express's `req.query`, Rails' `params[...]`, Spring's
  `request.getHeader(...)`).
- Add a `java` / `ruby` / `go` rule set following the same pattern once
  you have real target code in those languages — the rule shape
  (two-source concat into a `cache.get`/`cache.set`-style sink) is
  language-agnostic even though the Semgrep syntax per language differs.
- For the CodeQL path (interprocedural, or C-based proxies/Apache
  `mod_cache`), there's no starter query here yet — see
  `docs/06-static-analysis-dataflow.md`'s per-ecosystem section for the
  approach; that's a bigger undertaking than these Semgrep rules and
  deserves its own sub-project.
