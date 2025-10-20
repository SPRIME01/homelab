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
        ./scripts/env-check.sh

promote-stage:
    git push origin HEAD:stage

promote-main:
    git push origin stage:main
