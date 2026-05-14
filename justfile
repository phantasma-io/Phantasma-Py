[private]
just:
    just -l

PP:="PYTHONPATH=$(pwd)/src"

[group('test')]
test:
    {{PP}} uv run --extra dev pytest

[group('test')]
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
release-smoke:
    rm -rf /tmp/phantasma-sdk-py-release-smoke
    python -m venv /tmp/phantasma-sdk-py-release-smoke
    /tmp/phantasma-sdk-py-release-smoke/bin/python -m pip install --upgrade pip
    /tmp/phantasma-sdk-py-release-smoke/bin/python -m pip install --force-reinstall dist/*.whl
    /tmp/phantasma-sdk-py-release-smoke/bin/python -c 'from importlib.metadata import version; import phantasma_py; from phantasma_py.vm import ScriptBuilder; assert phantasma_py.__version__ == version("phantasma-sdk-py"); assert ScriptBuilder.begin().call_interop("Runtime.Test", ["alpha", 7]).end_script_hex()'

[group('publish')]
release-check:
    rm -rf dist
    test -z "$(git status --porcelain)" || (git status --short && false)
    just check
    just release-smoke

[group('publish')]
publish:
    just release-check
    UV_PUBLISH_USERNAME="$(python -c 'import configparser, pathlib; c=configparser.RawConfigParser(); c.read(pathlib.Path.home()/".pypirc"); print(c["pypi"]["username"])')" UV_PUBLISH_PASSWORD="$(python -c 'import configparser, pathlib; c=configparser.RawConfigParser(); c.read(pathlib.Path.home()/".pypirc"); print(c["pypi"]["password"])')" uv publish dist/*
