#!/usr/bin/env bash
# Generate certificates, build with Bake directly, and start the lab.
set -euo pipefail

LAB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$LAB_DIR"

bash scripts/gen-certs.sh

# Avoid the deprecated internal Compose builder and the Compose-to-Bake
# stdin pipe that can fail with "read |0: file already closed".
# Compose generates the tags so up --no-build uses the same images.
BAKE_FILE="$(mktemp ./.bake.XXXXXX.json)"
trap 'rm -f -- "$BAKE_FILE"' EXIT
export COMPOSE_BAKE=true

docker compose -f docker-compose.yml build --print > "$BAKE_FILE"
docker buildx bake -f "$BAKE_FILE" --load

# --force-recreate matters here, not just cosmetic: nginx.conf is
# bind-mounted, not baked into the nginx image, so a content-only edit
# to it never changes the nginx service's image or Compose-visible
# config -- without --force-recreate, `up -d` sees nothing it thinks
# needs recreating and leaves the already-running nginx container
# serving whatever config it loaded at ITS last start, silently stale
# even after this script "successfully" rebuilds the backend. This bit
# the lab more than once before this was added.
docker compose -f docker-compose.yml up -d --no-build --force-recreate
docker compose -f docker-compose.yml ps
