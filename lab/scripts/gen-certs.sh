#!/usr/bin/env bash
# Generates a self-signed cert for the lab's HTTPS listener.
set -euo pipefail

LAB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$LAB_DIR"
mkdir -p nginx/certs
DIR="$(cd nginx/certs && pwd)"

if [[ -s "$DIR/selfsigned.crt" && -s "$DIR/selfsigned.key" ]]; then
    echo "Certs already exist in $DIR, skipping."
    exit 0
fi

# Windows OpenSSL needs relative output paths when MSYS conversion is
# disabled to preserve the /CN= subject argument. Keep these settings
# scoped to OpenSSL so other commands retain normal path conversion.
(
    cd "$DIR"
    MSYS2_ARG_CONV_EXCL="*" MSYS_NO_PATHCONV=1 openssl req -x509 -nodes -newkey rsa:2048 \
        -keyout selfsigned.key \
        -out selfsigned.crt \
        -days 365 \
        -subj "/CN=dummywebsite.localhost" \
        -addext "subjectAltName=DNS:dummywebsite.localhost,DNS:localhost,DNS:example.com"
)

if [[ ! -s "$DIR/selfsigned.crt" || ! -s "$DIR/selfsigned.key" ]]; then
    echo "ERROR: cert generation appears to have failed (empty or missing output files)." >&2
    exit 1
fi

echo "Generated self-signed cert in $DIR"
