# Public corpus collection

Run `python collect.py --output /path/out --limit-per-repo 8`, then `python scan.py /path/out --output results.json` using the pinned requirements. No deployment is contacted. GitHub's repository, commit, tree and blob APIs are used; repositories must be public. Optional `--search` uses authenticated code search (GH_TOKEN/GITHUB_TOKEN); credentials are never printed or stored. The pilot used public seed-repository enumeration without code search.

Collection writes a manifest atomically after each file, records SHA256 and a commit-specific public URL, reuses the first collected commit for each repository on resume, skips existing files, retries interrupted/server-error responses, and stops a repo on rate-limit denial. Collection errors are historical, retained in the manifest; they mean the sample may be incomplete. Large trees can be truncated by GitHub. Downloaded files and manifests belong in a workspace outside the repository.

The scanner records parse failures separately, retains NONE/WEAK/UNKNOWN/STRONG diagnostics separately and invokes Semgrep on the same directory. Nginx/VCL files provide no Python/JS/TS Semgrep coverage: a zero count there cannot estimate rule precision. The committed manifest and measured pilot outputs are under ../results/. No private individual's deployment is named.
