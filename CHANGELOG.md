# Changelog - philips-airctrl (Enhanced Home Assistant Fork)

All notable changes to this enhanced fork will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> **Note**: This is an enhanced fork of the original aioairctrl package with significant additional features for Home Assistant integration. Version numbers start from 0.3.0 to distinguish from the original package.

## [1.1.0] - 2026-05-29

### Added
- **Observe-free one-shot status reads** (#6) - `Client.get_status()` now accepts
  an `observe: bool = True` parameter. When `observe=False`, the CoAP observation
  used to elicit a response is cancelled immediately after the first reply, so no
  lingering server-side subscription remains. This is intended for discovery
  probes, bounded polling, and single status checks on devices with a limited
  number of observer slots. The default (`observe=True`) preserves the previous
  behaviour for full backward compatibility.

### Changed
- One-shot callers (`discover`, `device-info`, and the `status` CLI command) now
  use `get_status(observe=False)` so they no longer leave observations registered
  on the device.

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
