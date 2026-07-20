# Kikuchi Lab

Kikuchi Lab is a local-first companion project for reproducible, crisp,
high-resolution EBSD Kikuchi-pattern simulation. Its first milestone is one
exceptional forsterite pattern generated with an ebsdsim master pattern and a
kikuchipy detector projection.

The approved design and executable implementation plan live under
`docs/superpowers/`. Repo-native work state lives in `docs/work/`. Large or
machine-specific products belong in the ignored `local/` directory.

Start with [the repository map](docs/architecture/REPO_MAP.md) and the
[local product catalog](docs/products/ARTIFACT_CATALOG.yml). The catalog keeps
the selected science-art, animation, and printable products discoverable while
keeping generated media out of source control.

The [Kikuchi Atlas](docs/atlas/README.md) turns the phase registry and local
product catalog into a browsable local publication surface without erasing the
scientific distinction between a visual derivative and an indexing reference.

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
uv run python scripts/product_status.py
```

Build the canonical spherical intensity-relief globe from a verified master product:

```bash
uv run kikuchi-lab relief globe build \
  --master-pattern local/benchmarks/forsterite-resolution-501/COD-9000319-ebsdsim.bundle/master-437f865cd0f68384.npz \
  --recipe recipes/relief/forsterite-intensity-globe.yml \
  --output local/relief-globes/forsterite-501
```

The command publishes one immutable, content-addressed five-file bundle. It refuses an
existing completed or partial destination instead of overwriting it.

This repository is intentionally local-only. Do not add a Git remote unless
the project owner explicitly chooses a publication location later.
