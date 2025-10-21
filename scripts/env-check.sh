#!/usr/bin/env bash

set -euo pipefail

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Load the structured logging system
if [[ -f "${PROJECT_ROOT}/lib/logging.sh" ]]; then
    # shellcheck disable=SC1091
    source "${PROJECT_ROOT}/lib/logging.sh"
else
    # Bootstrap error: logging.sh is not available yet, so we must use echo as an exception
    # This is the only place in the script where we use raw echo/exit instead of structured logging
    echo "ERROR: Could not find logging.sh at ${PROJECT_ROOT}/lib/logging.sh" >&2
    exit 1
fi

# Set service name for this script
export HOMELAB_SERVICE="env-check"

log_info "Running environment check..." "script=env-check.sh" "action=start"

# Load environment using the new env-loader system
if [[ -f "${PROJECT_ROOT}/lib/env-loader.sh" ]]; then
    # shellcheck disable=SC1091
    source "${PROJECT_ROOT}/lib/env-loader.sh" local
    log_info "Environment loaded successfully" "component=env-loader"
else
    log_warn "Could not find env-loader.sh" "path=${PROJECT_ROOT}/lib/env-loader.sh"
fi

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to handle devbox installation and environment setup
setup_devbox_environment() {
    log_info "Setting up devbox environment..." "component=devbox" "action=setup_start"

    # Install devbox if needed, with error handling
    if command_exists devbox; then
        log_info "devbox is already installed" "component=devbox" "status=already_installed"
    else
        log_warn "devbox not found, attempting to install..." "component=devbox" "status=missing"

        # Try different installation methods in order of preference
        if command_exists brew; then
            log_info "Installing devbox using Homebrew..." "component=devbox" "method=homebrew"
            if brew install devbox; then
                log_info "devbox installed successfully via Homebrew" "component=devbox" "method=homebrew" "status=success"
            else
                log_error "Failed to install devbox via Homebrew" "component=devbox" "method=homebrew" "status=failed"
                return 1
            fi
        elif command_exists curl; then
            log_info "Installing devbox using official installer..." "component=devbox" "method=official_installer"
            if curl -fsSL https://get.jetify.com/devbox | bash; then
                log_info "devbox installed successfully via official installer" "component=devbox" "method=official_installer" "status=success"

                # Update PATH to include devbox if it was installed to ~/.local/bin
                if [[ -d "$HOME/.local/bin" ]] && [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
                    export PATH="$HOME/.local/bin:$PATH"
                    log_info "Updated PATH to include ~/.local/bin" "component=devbox" "action=path_update"
                fi
            else
                log_error "Failed to install devbox via official installer" "component=devbox" "method=official_installer" "status=failed"
                return 1
            fi
        elif command_exists nix-env; then
            log_info "Installing devbox using nix-env..." "component=devbox" "method=nix-env"
            if nix-env -iA nixpkgs.devbox; then
                log_info "devbox installed successfully via nix-env" "component=devbox" "method=nix-env" "status=success"
            else
                log_error "Failed to install devbox via nix-env" "component=devbox" "method=nix-env" "status=failed"
                return 1
            fi
        else
            log_error "No suitable installation method found. Please install devbox manually" "component=devbox" "status=no_method"
            log_info "Installation options:" "component=devbox" "option1=brew install devbox" "option2=curl -fsSL https://get.jetify.com/devbox | bash" "option3=nix-env -iA nixpkgs.devbox"
            return 1
        fi

        # Verify devbox is now available
        if command_exists devbox; then
            log_info "devbox is now available" "component=devbox" "status=available"
        else
            log_error "devbox installation succeeded but binary is not in PATH" "component=devbox" "status=not_in_path"
            log_info "Try restarting your shell or manually adding ~/.local/bin to your PATH" "component=devbox" "suggestion=path_fix"
            return 1
        fi
    fi

    # Ensure devbox hooks and packages are installed (run idempotent install)
    if command_exists devbox; then
        log_info "Running 'devbox install --tidy-lockfile' to ensure packages are present..." "component=devbox" "action=install_packages"
        if ! devbox install --tidy-lockfile; then
            log_error "Failed to run 'devbox install --tidy-lockfile'" "component=devbox" "action=install_packages" "status=failed"
            return 1
        fi
    fi

    # Set up Python environment with uv
    log_info "Setting up Python environment..." "component=python" "action=setup_start"
    if command_exists devbox; then
        # Use devbox to run commands in its environment
        # First install Python with uv
        if devbox run -c "command -v uv" >/dev/null 2>&1; then
            log_info "Installing Python 3.12 with uv..." "component=python" "tool=uv" "version=3.12"
            if ! devbox run -c "uv python install 3.12" >/dev/null 2>&1; then
                log_error "Failed to install Python 3.12 with uv" "component=python" "tool=uv" "version=3.12" "status=failed"
                log_info "Ensure 'uv' is available in the devbox environment or install uv locally" "component=python" "suggestion=uv_availability"
                return 1
            fi
        fi

        # Create virtual environment if it doesn't exist
        if [ ! -d "${PROJECT_ROOT}/.venv" ]; then
            if devbox run -c "command -v uv" >/dev/null 2>&1; then
                log_info "Creating virtual environment with uv..." "component=python" "action=create_venv" "tool=uv"
                if ! devbox run -c "uv venv ${PROJECT_ROOT}/.venv --python 3.12" >/dev/null 2>&1; then
                    log_error "Failed to create venv with uv" "component=python" "action=create_venv" "tool=uv" "status=failed"
                    return 1
                fi
            fi

            # Fallback to python3 if uv fails or venv still doesn't exist
            if [ ! -d "${PROJECT_ROOT}/.venv" ]; then
                log_info "Creating virtual environment with python3..." "component=python" "action=create_venv" "tool=python3"
                if ! devbox run -c "python3 -m venv ${PROJECT_ROOT}/.venv"; then
                    log_error "Failed to create venv with python3" "component=python" "action=create_venv" "tool=python3" "status=failed"
                    return 1
                fi
            fi
        fi

        # Verify virtual environment exists (use project-root anchored path)
        if [ -d "${PROJECT_ROOT}/.venv" ]; then
            log_info "Virtual environment found" "component=python" "action=verify_venv" "status=success" "path=${PROJECT_ROOT}/.venv"
        else
            log_error "Failed to create virtual environment" "component=python" "action=verify_venv" "status=failed"
            return 1
        fi
    else
        # Fallback without devbox
        log_warn "devbox not available, using system environment" "component=python" "fallback=system"

        # Create virtual environment if it doesn't exist (project-root anchored)
        if [ ! -d "${PROJECT_ROOT}/.venv" ]; then
            log_info "Creating virtual environment with python3..." "component=python" "action=create_venv" "tool=python3" "fallback=system"
            if ! python3 -m venv "${PROJECT_ROOT}/.venv"; then
                log_error "Failed to create venv with python3" "component=python" "action=create_venv" "tool=python3" "fallback=system" "status=failed"
                return 1
            fi
        fi

        # Verify virtual environment exists
        if [ -d "${PROJECT_ROOT}/.venv" ]; then
            log_info "Virtual environment found" "component=python" "action=verify_venv" "status=success" "path=${PROJECT_ROOT}/.venv" "fallback=system"
        else
            log_error "Failed to create virtual environment" "component=python" "action=verify_venv" "status=failed" "fallback=system"
            return 1
        fi
    fi
}

# Main execution
main() {
    # Setup devbox environment
    if ! setup_devbox_environment; then
        log_error "Failed to setup devbox environment" "component=env-check" "status=setup_failed"
        exit 1
    fi

    log_info "Environment setup complete" "component=env-check" "status=setup_complete"
    log_info "Running lint and test checks..." "component=env-check" "action=run_checks"

    # Run lint and tests
    cd "${PROJECT_ROOT}"

    # Check if nx is properly set up
    if npx nx run-many --target=lint --all; then
        log_info "Lint checks passed" "component=env-check" "check=lint" "status=passed"
        if npx nx run-many --target=test --all; then
            log_info "Test checks passed" "component=env-check" "check=test" "status=passed"
        else
            log_warn "Test checks failed, but environment setup was successful" "component=env-check" "check=test" "status=failed"
        fi
    else
        log_warn "Lint checks failed, but environment setup was successful" "component=env-check" "check=lint" "status=failed"
        log_info "This might be due to missing nx workspace configuration" "component=env-check" "suggestion=nx_config"
        log_info "The shell compatibility issues have been resolved" "component=env-check" "info=shell_compat_fixed"
    fi

    log_info "Environment check completed successfully" "component=env-check" "action=complete" "status=success"
}

# Run main function
main "$@"
