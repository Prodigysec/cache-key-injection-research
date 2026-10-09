#!/usr/bin/env bash
# Simulates the real admin accessing /admin from localhost, so there is a
# cached entry for an attacker to later collide into via cache key
# injection. Runs curl *inside* the nginx container so the request's
# source IP is 127.0.0.1 as seen by nginx's `allow 127.0.0.1;` ACL.
set -euo pipefail

echo "Seeding /admin cache entry (as if accessed by the real admin from localhost)..."
docker exec ck_nginx curl -s -H "Accept: */*" http://127.0.0.1:80/admin -o /dev/null -D -
echo
echo "Done. A cache entry for key: https|backend_upstream|/admin||*/*  should now exist."
