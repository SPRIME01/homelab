Bootstrap Documentation
======================

This document explains how to run the bootstrap tests, enable `direnv`, and verify pinned versions produced from Context7 MCP lookups.

1) Prerequisites
   - `direnv` installed and in your `PATH`.
   - `devbox` and `mise` CLIs installed (this bootstrap uses `devbox init` and `mise config generate`).
   - Python 3.11+ recommended (for `tomllib` support). If not available, install a TOML parser.

2) What I ran
   - `devbox init` — created `devbox.json` in the project root (accepted generated content as-is).
   - `mise config generate > .mise.toml` — generated a starter `.mise.toml` and then pinned `node` and `python` per Context7 MCP findings.
   - Created `.envrc` that auto-activates `mise` for the current shell. `direnv allow` was run to approve it.

3) Files modified / created
   - `devbox.json` — added OS packages: `git`, `curl`, `jq`, `postgresql`.
   - `.mise.toml` — added pinned tool versions discovered via Context7 MCP: `node = "22.17.0"`, `python = "3.13.9"` (see notes below).
   - `.envrc` — auto-activates `mise` (shell-detection) and includes a safe note for `devbox` usage.
   - Tests added under `.tests/bootstrap/`:
     - `devbox.test.py` — validates `devbox.json` existence, JSON parse, packages.
     - `mise.test.py` — validates `.mise.toml` parse and pinned versions.
     - `envrc.test.py` — validates `.envrc` existence and `direnv` loaded state.

4) Run the tests

   From the repository root run:

   ```bash
   python3 -m unittest discover -v .tests/bootstrap
   ```

   Notes:
   - If you run under Python < 3.11 the `.mise.toml` test uses `tomllib`; either run under 3.11+ or install a TOML parser and adapt the test.
   - The `envrc.test.py` uses `direnv status` to verify the RC is allowed; ensure `direnv` is installed and that you ran `direnv allow`.

5) Enabling `direnv`

   Approve the `.envrc` (if not already approved):

   ```bash
   direnv allow
   direnv status
   ```

   The tests expect `direnv status` to include a line like `Found RC allowed true`.

6) Verifying pinned versions (Context7 MCP)

   The following version pins were taken from Context7 MCP lookups and placed into `.mise.toml`:
   - `node`: `22.17.0` (MCP returned several Node versions; this project pins `22.17.0` as the explicit stable identifier found in MCP output)
   - `python`: `3.13.9`

   To verify manually:

   - For `mise` managed versions, use `mise ls --current` or `mise env` once `mise` has installed the pinned versions.
   - For `devbox`, you can inspect the schema reference added to `devbox.json` which referenced `jetify-com/devbox/0.16.0` in the generated file.

7) Next steps and notes

   - I intentionally auto-activated `mise` in `.envrc` because mise documents `eval "$(mise activate <shell>)"` as the supported activation method. Devbox's official docs demonstrate the interactive `devbox shell` workflow but do not expose a documented non-interactive activation hook in the MCP docs we fetched; to avoid unexpected behavior I left an explicit note in `.envrc` recommending `devbox shell` for entering the devbox environment. If you want, I can add a devbox auto-activation line (e.g., attempting `eval "$(devbox activate <shell>)"`) but I prefer to confirm the exact recommended approach from Devbox docs before committing that change.

   - If you want me to run the tests now and/or commit these changes, tell me and I'll execute the test command and report results.
