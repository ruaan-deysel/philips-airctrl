# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Async Python library and CLI for controlling Philips air purifiers over encrypted CoAP. Provides network discovery, device data extraction, and an interactive Home Assistant setup wizard.

## Development Commands

```bash
# Setup
uv sync --extra dev              # Install all dependencies including dev

# Testing (100% coverage required — enforced via fail_under = 100)
uv run pytest                    # Run full suite with coverage
uv run pytest tests/test_cli.py  # Run a single test file
uv run pytest tests/test_cli.py::TestParseArgs::test_status  # Run a single test
uv run pytest -k "test_discover" # Run tests matching a pattern
uv run pytest -m "not slow"      # Skip slow tests

# Linting & Formatting
uv run ruff check src/ tests/    # Lint
uv run ruff check --fix src/ tests/  # Lint with auto-fix
uv run ruff format src/ tests/   # Format
uv run mypy                      # Type check (strict mode)

# Security
uv run bandit -c pyproject.toml -r src/

# Pre-commit
uv run pre-commit run --all-files
```

## Architecture

```
src/philips_airctrl/
├── __main__.py          # CLI entry point → calls cli.main()
├── cli.py               # Argument parsing and command dispatch (argparse)
├── coap/
│   ├── client.py        # Async CoAP client (Client class) — device communication
│   └── encryption.py    # AES-CBC encryption/decryption for CoAP payloads
├── discovery.py         # Network scanning for Philips devices (DeviceDiscovery)
├── device_info.py       # Device capability analysis and reporting (DeviceInfoExtractor)
├── models.py            # All Pydantic v2 data models (DeviceInfo, DeviceReport, HAConfig, etc.)
├── setup_wizard.py      # Interactive CLI wizard using click (SetupWizard)
└── _version.py          # Single source of truth for package version
```

**Data flow:** CLI → Discovery/Client → Encryption → Device. Models are shared across all modules.

## Key Conventions

- **Python >=3.11** with src/ layout, built with hatchling
- **Pydantic v2** for all data models — use `model_validate()`, not `parse_obj()`
- **Async/await** throughout — tests use `asyncio_mode = "auto"` (no manual decorator needed)
- **Line length**: 100 characters (ruff)
- **Ruff rules**: E, W, F, I, N, UP, B, SIM, TCH, RUF, S (bandit security checks)
- **mypy strict**: `disallow_untyped_defs=true` — all functions need type annotations
- **Test style**: pytest class-based organization with `unittest.mock` (AsyncMock for async)
- **Version**: Edit `src/philips_airctrl/_version.py` — hatch reads it dynamically
