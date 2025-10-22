## Linting setup — ShellCheck and markdownlint

This page explains how to install ShellCheck and markdownlint locally and how to enable the project's pre-commit hooks so linting runs automatically when you commit.

Supported install methods shown: apt (Debian/Ubuntu), Homebrew (macOS/Linux), npm, and direct package managers where applicable.

1) ShellCheck (shell script linter)

- Debian/Ubuntu (apt):

  ```bash
  sudo apt update && sudo apt install -y shellcheck
  ```

- Homebrew (macOS / Linux with Homebrew):

  ```bash
  brew install shellcheck
  ```

- From source (if you need a specific version):

  See https://github.com/koalaman/shellcheck for instructions. Installation via your platform package manager is recommended.

2) markdownlint (Markdown linter)

- npm (recommended for cross-platform usage):

  ```bash
  npm install -g markdownlint-cli
  # Optionally install the default rules plugin
  npm install -g markdownlint-cli markdownlint
  ```

- Homebrew (macOS / Linux):

  ```bash
  brew install markdownlint-cli
  ```

3) Enable the project's pre-commit hooks (recommended)

The repository includes a `.pre-commit-config.yaml` and local wrapper scripts that will run ShellCheck and markdownlint if they are installed. To enable the hooks locally:

```bash
# Install Python pre-commit tool (if not already installed)
python3 -m pip install --user pre-commit

# Install git hooks defined in .pre-commit-config.yaml
pre-commit install --install-hooks

# Optionally run hooks across all files to validate your workspace
pre-commit run --all-files
```

Notes
- The project's pre-commit configuration uses local wrapper scripts (`scripts/run-shellcheck.sh` and `scripts/run-markdownlint.sh`) so contributors without the tools installed won't be blocked; however, installing the tools locally gives full lint feedback.
- If you prefer strict enforcement, change the hooks to use the official pre-commit mirrors and pin versions in `.pre-commit-config.yaml` (this requires network access for `pre-commit install --install-hooks`).

If you need help installing these tools on your platform, tell me your OS and package manager and I can provide a tailored command set.
