# Contributing to MetricLens

## Setup

```bash
git clone https://github.com/sidharthkriplani/metriclens
cd metriclens
pip install -e ".[dev]"
```

## Running tests

```bash
pytest
```

All 19 tests must pass before submitting a pull request.

## Code style

```bash
ruff check src tests examples
```

## What to contribute

- Bug reports and fixes, especially edge cases in decomposition math
- Additional metric types
- CLI support (planned for v0.2)
- Additional demo datasets
- Documentation improvements

## Out of scope for v0

- LiftMap Mode (planned for v2.0)
- Shapley attribution (planned for v1.0)
- Bootstrap confidence intervals (planned for v1.0)

## Pull request checklist

- Tests pass (`pytest`)
- Ruff passes (`ruff check src tests`)
- New functionality has tests
- METHODOLOGY.md updated if decomposition math changes
- CHANGELOG.md entry added
