[private]
just:
    just -l

PP:="PYTHONPATH=$(pwd)/src"

[group('run')]
test:
    {{PP}} uv run pytest

[group('run')]
test:
    {{PP}} uv run pytest
