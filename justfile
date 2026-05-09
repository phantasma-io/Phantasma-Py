[private]
just:
    just -l

PP:="PYTHONPATH=$(pwd)/src"

[group('run')]
test:
    {{PP}} uv run --extra dev pytest

check:
    just f-check
    just lint
    just typecheck
    just test
    just build

[group('build')]
build:
    uv build

[group('format')]
f:
    uv run --extra dev ruff format src tests examples
    uv run --extra dev ruff check --fix src tests examples

[group('format')]
f-check:
    uv run --extra dev ruff format --check src tests examples
    uv run --extra dev ruff check src tests examples

[group('lint')]
lint:
    uv run --extra dev ruff check src tests examples

[group('lint')]
typecheck:
    {{PP}} uv run --extra dev mypy src/phantasma_py

[group('publish')]
publish:
    rm -rf dist
    test -z "$(git status --porcelain)" || (git status --short && false)
    just check
    UV_PUBLISH_USERNAME="$(python -c 'import configparser, pathlib; c=configparser.RawConfigParser(); c.read(pathlib.Path.home()/".pypirc"); print(c["pypi"]["username"])')" UV_PUBLISH_PASSWORD="$(python -c 'import configparser, pathlib; c=configparser.RawConfigParser(); c.read(pathlib.Path.home()/".pypirc"); print(c["pypi"]["password"])')" uv publish dist/*
