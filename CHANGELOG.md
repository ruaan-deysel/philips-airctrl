# Changelog - philips-airctrl (Enhanced Home Assistant Fork)

All notable changes to this enhanced fork will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> **Note**: This is an enhanced fork of the original aioairctrl package with significant additional features for Home Assistant integration. Version numbers start from 0.3.0 to distinguish from the original package.

## [Unreleased]

### Security

#### OWASP Top 10 Review & Fixes

- **[A01 Broken Access Control / Path Traversal]** `setup_wizard.py`: Sanitise the
  device name obtained from the network before using it to construct file-system paths.
  A maliciously crafted device name (e.g. `../../etc/passwd`) could previously escape
  the intended output directory.  The name is now reduced to word characters and
  hyphens via `re.sub` before being interpolated into `Path` objects.

- **[A03 Injection]** `cli.py`: Changed `str.split("=")` to `str.split("=", 1)` when
  parsing `KEY=VALUE` CLI arguments.  The previous form raised an unhandled
  `ValueError` for values that contained a `=` character (e.g. base64-encoded tokens),
  which could be triggered by user input.

- **[A08 Software and Data Integrity]** `publish.yml`: Pinned `actions/checkout` and
  `actions/setup-python` to immutable commit SHAs instead of mutable version tags,
  preventing a supply-chain attack via tag mutation.

#### Dependabot (OWASP A06 – Vulnerable and Outdated Components)

- Added `.github/dependabot.yml` to keep Python (`pip`) and GitHub Actions
  dependencies automatically up to date with weekly pull requests.

#### OSV Vulnerability Scanning (osv.dev)

- Added `.github/workflows/security.yml` running
  [google/osv-scanner-action](https://github.com/google/osv-scanner-action) against
  the `uv.lock` lockfile on every push/PR to `main` and on a weekly schedule.
  Results are uploaded to the GitHub Security tab as SARIF.

## [0.3.0] - 2025-01-27 - **Major Home Assistant Integration Release**

### Added - **🏠 Home Assistant Integration Features**
- **🔍 Automatic Device Discovery** - Network scanning for Philips air purifiers
- **📊 Comprehensive Device Analysis** - Extract 70+ data points with capability detection
- **🧙‍♂️ Interactive Setup Wizard** - User-friendly guided setup for non-technical users
- **📁 Multiple Export Formats** - JSON and YAML output for easy integration
- **🏠 Home Assistant Configuration Generation** - Ready-to-use HA configs
- **📋 Device Information Export** - Complete device analysis for integration development
- **🤝 Community Contribution Workflow** - Easy device info sharing for ha-philips-airpurifier project

### Added - **🛠️ Development & Quality Improvements**
- Comprehensive test suite with 75%+ coverage
- Type hints throughout the codebase
- Modern pyproject.toml configuration
- Pre-commit hooks configuration
- GitHub Actions CI/CD pipeline
- Detailed README with usage examples
- Development documentation
- Code quality tools (Black, Flake8, MyPy)

### Changed - **🔄 Fork & Package Changes**
- **BREAKING**: Package renamed to `philips-airctrl` to distinguish from original
- **BREAKING**: No longer available on PyPI - must install from source
- **BREAKING**: CLI argument structure updated for new commands
- **BREAKING**: Migrated from setup.py to pyproject.toml
- Updated Python version requirement to 3.8+
- Enhanced CLI argument parsing for better testability
- Modernized code formatting with Black
- Updated project metadata and maintainer information

### Changed - **🛠️ Technical Improvements**
- Improved error handling in client code
- Fixed encryption key overflow handling
- Enhanced async/await patterns throughout codebase

### Fixed
- Fixed bare except clause in client.py
- Fixed f-string without placeholders
- Fixed module imports organization
- Fixed encryption context key incrementation overflow
- Improved async/await patterns in tests

### Security
- Updated dependencies to latest versions
- Added security scanning configuration
- Improved error handling to prevent information leakage

### Development
- Added comprehensive test suite for all modules
- Set up automated testing with pytest
- Added code coverage reporting
- Implemented pre-commit hooks for code quality
- Added development environment setup documentation

## [0.2.5] - Previous Release

### Features
- Basic CoAP client functionality
- Encrypted communication with Philips air purifiers
- Command-line interface
- Status monitoring and control
- Device observation capabilities

### Known Issues
- Limited test coverage
- No type hints
- Basic error handling
- Manual dependency management

---

## Development Notes

### Version 0.2.6 Improvements Summary

This release represents a major modernization and quality improvement of the philips-airctrl library:

1. **Testing Infrastructure**: Added comprehensive test suite covering encryption, client functionality, and CLI operations with proper async mocking.

2. **Code Quality**: Implemented modern Python development practices including type hints, code formatting, and linting.

3. **Project Structure**: Migrated to modern pyproject.toml configuration and removed deprecated setup.py.

4. **Documentation**: Significantly enhanced README with detailed usage examples, API reference, and development guidelines.

5. **Development Workflow**: Added pre-commit hooks, CI/CD pipeline, and automated quality checks.

6. **Maintainability**: Improved error handling, fixed code quality issues, and added proper async patterns.

### Migration Guide from 0.2.5 to 0.2.6

The API remains backward compatible, but there are some development-related changes:

- **Python Version**: Now requires Python 3.8+ (was 3.6+)
- **Installation**: No changes to installation process
- **API**: All existing API calls remain the same
- **CLI**: All existing CLI commands work unchanged

For developers:
- Use `pip install -e ".[dev]"` for development dependencies
- Run tests with `pytest` instead of manual testing
- Use `black` for code formatting
- Use `pre-commit` for automated quality checks

### Future Roadmap

- Add support for more Philips air purifier models
- Implement device discovery functionality
- Add configuration file support
- Enhance error messages and user feedback
- Add integration with home automation systems
