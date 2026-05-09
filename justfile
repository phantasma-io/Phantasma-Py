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
    uv publish
