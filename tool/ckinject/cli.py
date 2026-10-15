"""
ckinject -- command-line entry point.

Authorized testing only: your own lab, or targets/scope you have explicit
permission to test. See ../../docs/04-testing-methodology.md.
"""
from __future__ import annotations

import argparse
import sys

import requests

from . import __version__
from .discover import discover
from .fragments import DEFAULT_PAIRS, pairs_from_names
from .prober import probe_pair
from .report import print_discover_results, print_results, write_json
from .scheme_check import build_shifted_host, check as scheme_check_fn
from .wordlists import DEFAULT_COOKIES, DEFAULT_HEADERS, DEFAULT_PARAMS


def cmd_probe(args: argparse.Namespace) -> int:
    pairs = pairs_from_names(args.pair) if args.pair else DEFAULT_PAIRS
    session = requests.Session()
    all_results = []
    for slot_a, slot_b in pairs:
        results = probe_pair(
            base_url=args.target,
            base_path=args.base_path,
            slot_a=slot_a,
            slot_b=slot_b,
            session=session,
            marker_length=args.marker_length,
            verify=not args.insecure,
        )
        all_results.extend(results)

    hits = print_results(all_results)
    if args.output:
        write_json(all_results, args.output)
        print(f"\nFull results written to {args.output}")
    return 0 if hits == 0 else 1


def cmd_discover(args: argparse.Namespace) -> int:
    headers = list(DEFAULT_HEADERS) if not args.no_default_wordlist else []
    cookies = list(DEFAULT_COOKIES) if not args.no_default_wordlist else []
    params = list(DEFAULT_PARAMS) if not args.no_default_wordlist else []
    headers += args.extra_header or []
    cookies += args.extra_cookie or []
    params += args.extra_param or []

    if not (headers or cookies or params):
        print("Nothing to test: wordlists disabled and no --extra-* given.", file=sys.stderr)
        return 2

    results = discover(
        base_url=args.target,
        base_path=args.base_path,
        headers=headers,
        cookies=cookies,
        params=params,
        value1=args.value1,
        value2=args.value2,
        verify=not args.insecure,
    )
    print_discover_results(results)
    if args.output:
        write_json(results, args.output)
        print(f"\nFull results written to {args.output}")

    # r.fragment is already a full slot spec ("header:Accept", "cookie:session",
    # "query:lang" -- see fragments.py's *_slot() naming), so these pair
    # directly into `probe --pair`.
    keyed_names = [r.fragment for r in results if r.keyed]
    if keyed_names:
        print("\nNext: feed these into `probe --pair` to test boundary ambiguity between them, e.g.:")
        for a, b in zip(keyed_names, keyed_names[1:]):
            print(f'  --pair "{a},{b}"')
    return 0


def cmd_scheme_check(args: argparse.Namespace) -> int:
    result = scheme_check_fn(
        http_url=args.http_url,
        https_url=args.https_url,
        real_host=args.host,
        probe_host=args.probe_host,
        path=args.path,
        verify_tls=not args.insecure,
    )
    print(f"Host header accepted:      {result.host_header_accepted}")
    print(f"HTTP/HTTPS equivalent:      {result.http_https_equivalent}")
    print(f"Host reflected in body:    {result.host_reflected}")
    for n in result.notes:
        print(f"  note: {n}")

    if result.http_https_equivalent and result.host_reflected:
        shifted = build_shifted_host(args.host)
        print()
        print("All prerequisites look present for the cross-scheme collision.")
        print(f"Try sending, over PLAIN HTTP, a request with:  Host: {shifted}")
        print(f"Then a normal HTTPS request with:               Host: {args.host}")
        print("and check whether the HTTPS response reflects the shifted host value.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ckinject", description=__doc__)
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="command", required=True)

    probe = sub.add_parser("probe", help="Boundary-fuzz candidate fragment pairs for key ambiguity")
    probe.add_argument("--target", required=True, help="Base URL, e.g. http://localhost:8080")
    probe.add_argument("--base-path", default="/", help="Path to probe (default: /)")
    probe.add_argument("--marker-length", type=int, default=12)
    probe.add_argument("--pair", action="append", help="Custom pair 'slotA,slotB', e.g. 'path,header:X-Foo'. Repeatable.")
    probe.add_argument("--insecure", action="store_true", help="Disable TLS verification")
    probe.add_argument("--output", help="Write full JSON results to this path")
    probe.set_defaults(func=cmd_probe)

    discover_p = sub.add_parser("discover", help="Find which headers/cookies/query params a cache keys on")
    discover_p.add_argument("--target", required=True, help="Base URL, e.g. http://localhost:8080")
    discover_p.add_argument("--base-path", default="/", help="Path to probe (default: /). Prefer a stable, cacheable, non-session-specific path.")
    discover_p.add_argument("--extra-header", action="append", help="Additional header name to test. Repeatable.")
    discover_p.add_argument("--extra-cookie", action="append", help="Additional cookie name to test. Repeatable.")
    discover_p.add_argument("--extra-param", action="append", help="Additional query param name to test. Repeatable.")
    discover_p.add_argument("--no-default-wordlist", action="store_true", help="Skip the built-in candidate lists; test only --extra-* names")
    discover_p.add_argument("--value1", default="ckdiscoverA", help="First test value (default: ckdiscoverA)")
    discover_p.add_argument("--value2", default="ckdiscoverB", help="Second, distinct test value (default: ckdiscoverB)")
    discover_p.add_argument("--insecure", action="store_true", help="Disable TLS verification")
    discover_p.add_argument("--output", help="Write full JSON results to this path")
    discover_p.set_defaults(func=cmd_discover)

    scheme = sub.add_parser("scheme-check", help="Check prerequisites for the scheme<->host cross-scheme collision")
    scheme.add_argument("--http-url", required=True, help="e.g. http://localhost:8080")
    scheme.add_argument("--https-url", required=True, help="e.g. https://localhost:8443")
    scheme.add_argument("--host", required=True, help="The real Host value to test")
    scheme.add_argument("--probe-host", default="ckinject-probe.invalid")
    scheme.add_argument("--path", default="/")
    scheme.add_argument("--insecure", action="store_true")
    scheme.set_defaults(func=cmd_scheme_check)

    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
