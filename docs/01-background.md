# Background: what cache key injection is

## Source research

This project reproduces and extends: Alex Brumen, ["Cache key injection:
Smuggling poison through the
door"](https://www.yeswehack.com/lab/research-cache-key-injection),
YesWeHack Lab, September 2026.

Read the original first — this document summarizes the model, not the
article itself.

## The core bug class

Most cache poisoning research (e.g. James Kettle's ["Web Cache
Entanglement"](https://portswigger.net/research/web-cache-entanglement) and
earlier "practical web cache poisoning" work) targets **unkeyed**
fragments: request data the cache *forwards to the origin* but does *not*
include in the cache key. The classic fix is "key everything that affects
the response."

Cache key injection inverts the question: what if the key itself is built
unsafely, even when every fragment that matters *is* keyed?

A cache key is typically built like this (Nginx default, roughly):

```
key = scheme + host + uri
```

or with custom additions:

```
key = scheme + host + uri + is_args + args + http_accept
```

The vulnerability condition: **fragments are concatenated as raw strings
with no delimiter, length-prefix, or structural encoding.** If that's true,
then for two different requests R1 and R2:

```
f1(R1) + f2(R1) + f3(R1) == f1(R2) + f2(R2) + f3(R2)
```

can hold as a *string equality* even though the fragment values differ,
simply by shifting characters across the fragment boundary. The cache
cannot tell the difference — it hashes (or stores) the final string, and a
colliding string is a colliding key regardless of how it was assembled.

This matters because:

- Defenders reason about *which fields are keyed*, not *how the keyed
  fields are joined*. "It's in the key, so it's safe" is the exact
  assumption this bug breaks.
- It requires no cache rule misconfiguration in the traditional sense
  (missing `Vary`, missing key inclusion) — only a *concatenation*
  mistake, which is extremely common because most cache key DSLs
  (Nginx `proxy_cache_key`, Varnish `hash_data()`, CDN "custom cache key"
  UIs) default to plain string joining.

## Minimal reproduction of the mechanism

Given `proxy_cache_key "$scheme$proxy_host$uri$is_args$args$http_accept"`:

Legitimate request:
```
GET / HTTP/1.1
Host: example.com
Accept: */*
```
→ fragments: `"https" + "myapp" + "/" + "" + "" + "*/*"` → key `httpsmyapp/*/*`

Attacker request:
```
GET /* HTTP/1.1
Host: example.com
Accept: /*
```
→ fragments: `"https" + "myapp" + "/*" + "" + "" + "/*"` → key `httpsmyapp/*/*`

Same final key, different endpoint and different `Accept` value. The
attacker shifted two characters (`*`, `/`) from the `Accept` fragment into
the URI fragment, with the concatenated result unchanged.

## Four demonstrated impact chains (reproduced in `lab/`)

| # | Technique | Fragment pair exploited | Impact |
|---|-----------|--------------------------|--------|
| 1 | URI ↔ `Accept` boundary shift | `$uri` / `$http_accept` | Cache deception without user interaction — ACL-protected `/admin` response served to unauthenticated attacker |
| 2 | Same primitive, pre-cache timing | `$uri` / `$http_accept` | CPDoS — attacker pre-poisons a 404 under the key for a legitimate page |
| 3 | Scheme ↔ Host boundary shift | `$scheme` / `$host` | Cross-scheme collision → reflected Host in `<script src>` → stored XSS |
| 4 | CDN bypass header (`Authorization`) + URI ↔ header shift | edge bypass + `$uri` / `$http_accept` | Reach and poison an origin cache sitting behind a CDN edge cache |

## Why hashing the key doesn't fix it

Hashing (`md5("httpsmyapp/*/*")`) is applied *after* the ambiguous
concatenation. Two different inputs that concatenate to the same string
still hash identically. The fix has to happen **before** hashing, by
preserving fragment boundaries — e.g. `scheme|host|uri|accept` or a
structured encoding (length-prefixed, JSON-encoded, or hashing each
fragment independently and concatenating the *digests*).

Next: `02-reproduction-guide.md` to build and run the lab.
