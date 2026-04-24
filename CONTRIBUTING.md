# Contributing

Thanks for your interest in contributing. This is a HACS custom integration for the Gofanco Prophecy 4x4 HDMI Matrix — reconfigure flow, diagnostics, coordinator-based availability, and action exceptions are all implemented.

## Development setup

The repository ships with a VS Code devcontainer. Open it in VS Code and the container will:

1. Create a Python 3.12 virtual environment.
2. Install the integration and its test dependencies (`requirements_test.txt`).
3. Bootstrap a Home Assistant config directory at `.devcontainer/ha_config/` with a symlink to the integration, so edits appear live.

Outside the devcontainer:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements_test.txt
```

## Running checks

```bash
# Lint
ruff check custom_components tests
ruff format --check custom_components tests

# Strict typing (required)
mypy custom_components/gofanco_prophecy

# Tests
pytest
```

Both run in CI on every push and pull request ([.github/workflows/](.github/workflows/)).

## Pull request guidelines

- Add a test for any bug fix or new behavior.
- Keep changes focused; open a separate PR for unrelated cleanup.
- Update `README.md` when you add/remove functionality.
- Keep entity `unique_id`s stable. If you must change them, provide a config-entry migration in `__init__.py`.

## Reporting bugs

Use the [bug report template](.github/ISSUE_TEMPLATE/bug_report.yml). Please include:

- Home Assistant version.
- Integration version.
- Debug logs (`logger.gofanco_prophecy: debug` in `configuration.yaml`).
- Diagnostics download from the integration's overflow menu.
