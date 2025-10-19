# Just recipes for homelab workspace

set shell := ["bash", "-cu"]

default:
    @just --list

setup:
    direnv allow
    mise install
    devbox install

doctor:
    ./scripts/doctor.sh

build:
    npx nx run-many --target=build --all

test:
    npx nx run-many --target=test --all

lint:
    npx nx run-many --target=lint --all

deploy:
    npx nx run-many --target=deploy --all

ci-bootstrap:
    ./lib/env-loader.sh ci
    npx nx run-many --target=lint --all

env-check:
        # Idempotent smoke check: bootstrap devbox, ensure uv/python venv, run lint+test
        devbox install --tidy-lockfile || true
        if command -v devbox >/dev/null 2>&1; then \
            devbox run bash -lc "uv python install 3.12 >/dev/null 2>&1 || true; if [ ! -d .venv ]; then uv venv .venv --python 3.12 >/dev/null 2>&1 || python3 -m venv .venv; fi; source .venv/bin/activate >/dev/null 2>&1 || true"; \
        else \
            python3 -m venv .venv || true; source .venv/bin/activate || true; \
        fi
        npx nx run-many --target=lint --all
        npx nx run-many --target=test --all

promote-stage:
    git push origin HEAD:stage

promote-main:
    git push origin stage:main
