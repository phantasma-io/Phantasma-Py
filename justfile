[private]
just:
    just -l

PP:="PYTHONPATH=$(pwd)/src"

[group('run')]
test:
    {{PP}} uv run pytest

[group('build')]
build:
    uv build

[group('publish')]
publish:
    uv publish
