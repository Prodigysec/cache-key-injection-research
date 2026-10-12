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
docker compose -f docker-compose.yml up -d --no-build
docker compose -f docker-compose.yml ps
