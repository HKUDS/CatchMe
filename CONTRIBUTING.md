# Contributing to CatchMe

Thanks for your interest in contributing to CatchMe! This guide will help you get started.

## Development Setup

```bash
# 1. Fork & clone
git clone https://github.com/<your-username>/catchme.git
cd catchme

# 2. Create a Python 3.11+ environment
conda create -n catchme python=3.11 -y && conda activate catchme

# 3. Install in editable mode with dev dependencies
pip install -e ".[dev]"
```

## Making Changes

1. **Create a branch** from `main`:
   ```bash
   git checkout -b feat/your-feature
   ```

2. **Write code** — keep the existing style. The project uses [ruff](https://docs.astral.sh/ruff/) for linting and formatting:
   ```bash
   ruff check catchme/          # lint
   ruff format catchme/         # auto-format
   ```

3. **Add tests** for new functionality. Tests live in `catchme/tests/` and use [pytest](https://docs.pytest.org/):
   ```bash
   pytest                       # run all tests
   pytest catchme/tests/test_store.py -v   # run a specific file
   ```

4. **Make sure CI passes locally** before pushing:
   ```bash
   ruff check catchme/ && ruff format --check catchme/ && pytest
   ```

## Project Structure

```
catchme/
├── __init__.py          # CatchMe public API
├── run.py               # CLI entry point
├── config.py            # Config dataclass
├── engine.py            # Recording engine
├── store.py             # SQLite event store
├── organizer.py         # Real-time event organizer
├── web.py               # Flask dashboard
├── recorders/           # Input recorders (window, keyboard, mouse, ...)
├── pipelines/           # filter → tree → summarize → retrieve
├── extractors/          # File & URL content extraction
├── services/            # LLM client & providers
├── static/              # Web frontend assets
└── tests/               # pytest test suite
```

## Submitting a Pull Request

1. Push your branch and open a PR against `main`.
2. Fill in a clear description of **what** changed and **why**.
3. CI will automatically run lint + tests across Python 3.11–3.13 on Linux, macOS, and Windows.
4. Address any review feedback — we aim to respond within a few days.

## Code Style

- **Python 3.11+** — use modern syntax (`match`, `X | Y` type unions, etc.)
- **Line length** — 100 characters (enforced by ruff formatter)
- **Imports** — sorted by ruff/isort; `catchme` recognized as first-party
- **Tests** — use `tmp_path` / `tmp_root` fixtures; mock external calls (LLM, filesystem); no network access in tests
- **No secrets** — never commit API keys or local CatchMe config files.

## What to Contribute

Here are some areas where contributions are especially welcome:

- **New recorders** — e.g., browser history, calendar events, Bluetooth proximity
- **Platform support** — improve Windows/Linux parity with macOS
- **Pipeline improvements** — better filtering heuristics, summarization prompts, retrieval strategies
- **Web dashboard** — new visualizations, UX improvements
- **Documentation** — tutorials, architecture docs, translations
- **Bug fixes** — check the [Issues](https://github.com/HKUDS/catchme/issues) page

## Reporting Issues

- Search existing issues first to avoid duplicates.
- Include your OS, Python version, and steps to reproduce.
- For privacy, **never paste raw activity data or API keys** in issues.

## License

By contributing, you agree that your contributions will be licensed under the [Apache License 2.0](LICENSE).
