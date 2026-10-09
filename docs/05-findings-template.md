# Finding report template

Copy this into a new file per finding, e.g.
`findings/2026-10-09-target-acl-bypass.md` (gitignored by default if you
keep real target details private — add a `findings/` entry to
`.gitignore` if you don't want engagement-specific write-ups in version
control).

---

## Title

`<Target/Program> — Cache key injection enables <impact> on <endpoint>`

## Summary

One or two sentences: what the bug is, what it lets an attacker do, and
why it works (which fragments collide and how).

## Severity / impact classification

- [ ] Access-control bypass / cache deception
- [ ] CPDoS
- [ ] Stored XSS / content injection
- [ ] Cross-tenant data leakage
- [ ] Other: ______

Affected users: (all users of the shared cache? a subset? admin-only
content exposed to anyone?)

Cache scope: (CDN-wide edge cache / single origin instance / per-region?)

## Root cause

- Cache implementation: (Nginx / Varnish / CDN name / app-level / other)
- Cache key formula (if known, e.g. from config access, error messages,
  or inferred from behavior):
  ```
  <key formula>
  ```
- Fragment pair exploited: `<fragment A>` ↔ `<fragment B>`
- Why they're ambiguous: (no delimiter / shared charset allows shifting /
  encoding mismatch / other)

## Reproduction

### Prerequisites
- (Any state needed: a legitimate response already cached, a specific
  Host/vhost, etc.)

### Step 1 — Baseline request
```
GET /<path>?ckbuster=<id> HTTP/1.1
Host: <host>
<relevant headers>
```
Response: `<status>`, `X-Cache: MISS`, body: `<summary>`

### Step 2 — Colliding request
```
GET /<shifted-path>?ckbuster=<id> HTTP/1.1
Host: <host>
<shifted headers>
```
Response: `<status>`, `X-Cache: HIT`, body: `<summary — should match step 1
or demonstrate the poisoned/leaked content>`

### Step 3 — Impact confirmation
(Screenshot, body diff, or second victim-perspective request showing the
real-world consequence — e.g., an unauthenticated session receiving
admin content, or a second user receiving the poisoned response.)

## Evidence of safe testing

- Cache buster used: `<id>`
- Observed TTL: `<value>` (from `Age`/`Cache-Control`/retest timing)
- Confirmed no real user traffic was affected: `<how you confirmed this —
  e.g., unique buster meant this was a brand-new, isolated cache entry>`
- Cleanup performed (if applicable): `<purge request / expiry wait /
  N/A>`

## Suggested remediation

Reference the general fix from `docs/01-background.md` (preserve fragment
boundaries before hashing — delimiters, length-prefixing, or per-fragment
hashing) and anything specific to this target's stack.

## Timeline

| Date | Event |
|---|---|
| | Discovered |
| | Reported |
| | Acknowledged |
| | Fixed |
| | Disclosed (if applicable) |

## References

- Original research: https://www.yeswehack.com/lab/research-cache-key-injection
- This repo: reproduction lab and methodology used
