# Kikuchi Lab

Kikuchi Lab is a local-first companion project for reproducible, crisp,
high-resolution EBSD Kikuchi-pattern simulation. Its first milestone is one
exceptional forsterite pattern generated with an ebsdsim master pattern and a
kikuchipy detector projection.

The approved design and executable implementation plan live under
`docs/superpowers/`. Repo-native work state lives in `docs/work/`. Large or
machine-specific products belong in the ignored `local/` directory.

## Development

Use uv's managed arm64 Python 3.12 runtime:

```bash
uv python install 3.12
UV_PYTHON_PREFERENCE=only-managed uv sync --python 3.12
uv run python -c 'import platform; assert platform.machine() == "arm64"'
uv run pytest -q
uv run ruff check src tests
```

Inspect the current package version:

```bash
uv run kikuchi-lab version
```

This repository is intentionally local-only. Do not add a Git remote unless
the project owner explicitly chooses a publication location later.
