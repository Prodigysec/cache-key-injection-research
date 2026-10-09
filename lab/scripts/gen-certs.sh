#!/usr/bin/env bash
# Generates a self-signed cert for the lab's HTTPS listener.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../nginx/certs" && pwd)"
mkdir -p "$DIR"

if [[ -f "$DIR/selfsigned.crt" && -f "$DIR/selfsigned.key" ]]; then
    echo "Certs already exist in $DIR, skipping."
    exit 0
fi

openssl req -x509 -nodes -newkey rsa:2048 \
    -keyout "$DIR/selfsigned.key" \
    -out "$DIR/selfsigned.crt" \
    -days 365 \
    -subj "/CN=dummywebsite.localhost" \
    -addext "subjectAltName=DNS:dummywebsite.localhost,DNS:localhost,DNS:example.com"

echo "Generated self-signed cert in $DIR"
