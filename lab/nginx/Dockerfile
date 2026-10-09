FROM nginx:1.27
# curl is used by scripts/seed-admin-cache.sh to make a loopback request
# that nginx sees as coming from 127.0.0.1 (simulating the real admin's
# localhost-only access in the ACL-bypass / cache-deception scenario).
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*
