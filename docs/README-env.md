# Quick environment setup (homelab)

This file contains the minimal copy-paste commands to get a development shell matching CI.

1) Install Devbox tools (one-time):

```bash
devbox install --tidy-lockfile
```

2) Allow direnv (local only):

```bash
direnv allow
```

3) Create a project `.venv` (uv-managed if available):

```bash
# If devbox+uv are available inside your shell
devbox run bash -lc "uv python install 3.12 || true; uv venv .venv --python 3.12 || python3 -m venv .venv"
# or fallback
python3 -m venv .venv
source .venv/bin/activate
```

4) Run a quick smoke check (lint + tests):

```bash
just env-check
```

Notes:
- CI uses `./lib/env-loader.sh ci` (no direnv). Workflows persist the venv via `$GITHUB_ENV` / `$GITHUB_PATH` so subsequent steps inherit the environment.
- Avoid auto-spawning `devbox shell` from `.envrc`; we evaluate devbox's direnv snippet into the current shell instead.
