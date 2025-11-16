# Tool Versions

| Tool | Version | Source | Last Verified |
| --- | --- | --- | --- |
| `node` | 22.17.0 | Context7 MCP lookup (returned `v22.17.0`) | 2025-11-14 |
| `python` | 3.13.9 | Context7 MCP lookup | 2025-11-14 |
| `pnpm` | 10.22.0 | npm registry query (pinned for Nx monorepo) | 2025-11-14 |
| `npm:nx` | 22.0.3 | npm registry query | 2025-11-14 |
| `pulumi` | 3.207.0 | GitHub releases (mise plugin) | 2025-11-14 |
| `devbox` | 0.16.0 | Jetify release referenced in devbox docs | 2025-11-14 |
| `rust` | 1.91.1 | Rust releases (mise plugin) | 2025-11-14 |
| `age` | 1.2.1 | GitHub releases | 2025-11-14 |
| `pipx:ansible-core` | 2.18.1 | PyPI release channel | 2025-11-14 |
| `pipx:molecule` | 5.1.0 | PyPI release channel | 2025-11-14 |

All entries live in `.mise.toml`. Run `mise install` anytime you update the file to sync local installations. Record the verification date whenever you bump versions, ideally tied to Context7 MCP or upstream release notes.
