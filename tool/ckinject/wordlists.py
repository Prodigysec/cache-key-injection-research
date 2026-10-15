"""
Candidate fragment names for `ckinject discover` (see discover.py).

These are starting points, not an exhaustive or authoritative list --
no such list can exist, since app-specific header/cookie/param names are
unbounded (see docs/04-testing-methodology.md's "surefire?" discussion).
Always extend these with anything recon turns up for the specific target
(a Vary header, cookies set by the app, params that show up in its own
links/forms) via --extra-header/--extra-cookie/--extra-param.
"""
from __future__ import annotations

# Headers real caches commonly key on, beyond the handful ckinject's
# `probe` command already defaults to testing boundaries for.
DEFAULT_HEADERS = [
    "Accept",
    "Accept-Language",
    "Accept-Encoding",
    "Accept-Charset",
    "Authorization",
    "Origin",
    "Referer",
    "User-Agent",
    "X-Forwarded-For",
    "X-Forwarded-Host",
    "X-Forwarded-Proto",
    "X-Forwarded-Scheme",
    "X-Original-URL",
    "X-Rewrite-URL",
    "X-Host",
    "Front-End-Https",
    "Save-Data",
    "DNT",
    "Sec-CH-UA",
    "Sec-CH-UA-Mobile",
    "Sec-CH-UA-Platform",
]

# Cookie NAMES are inherently app-specific -- these are just common
# patterns (locale/session/feature-flag conventions) worth trying blind;
# real recon (what the app actually sets) matters far more than this list.
DEFAULT_COOKIES = [
    "session",
    "sessionid",
    "PHPSESSID",
    "JSESSIONID",
    "locale",
    "lang",
    "language",
    "currency",
    "theme",
    "ab_test",
    "experiment",
    "plan",
    "tier",
]

# Query parameters some caches key on wholesale (everything in the query
# string) and some key on selectively; worth testing even though many
# apps/CDNs strip or ignore most params by default.
DEFAULT_PARAMS = [
    "lang",
    "locale",
    "currency",
    "ref",
    "utm_source",
    "page",
    "sort",
    "format",
]
