# Contributing to NovaPort-MCP

Thank you for your interest in contributing to NovaPort-MCP! This document provides guidelines and instructions for contributing to this Model Context Protocol (MCP) server implementation.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Environment Setup](#development-environment-setup)
- [Running Tests](#running-tests)
- [Code Style](#code-style)
- [Pull Request Process](#pull-request-process)
- [Issue Reporting](#issue-reporting)
- [Documentation](#documentation)
- [Testing Requirements](#testing-requirements)
- [Release Process](#release-process)

## Code of Conduct

This project adheres to a [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## Getting Started

NovaPort-MCP is a robust, database-backed Model Context Protocol server for managing structured project context. Before contributing, please:

1. Read this contributing guide thoroughly
2. Check existing [issues](../../issues) and [pull requests](../../pulls)
3. Review the [README.md](README.md) for project overview
4. Familiarize yourself with the [architecture documentation](docs/deep_dive.md)

## Development Environment Setup

### Prerequisites

- **Python 3.11+** (required)
- **Poetry** for dependency management
- **PostgreSQL** (optional, SQLite used by default for development)
- **Git** for version control

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/siroopfles/novaport-mcp.git
   cd novaport-mcp
   ```

2. **Install Poetry** (if not already installed):
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

3. **Install dependencies**:
   ```bash
   poetry install
   ```

4. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Initialize the database**:
   ```bash
   poetry run alembic upgrade head
   ```

6. **Verify installation**:
   ```bash
   poetry run novaport-mcp --help
   ```

### Development Tools

The project uses the following development tools (automatically installed with `poetry install`):

- **pytest** - Testing framework
- **black** - Code formatting
- **ruff** - Linting and import sorting
- **mypy** - Type checking
- **pytest-cov** - Coverage reporting

## Running Tests

### Full Test Suite

```bash
poetry run pytest
```

### With Coverage

```bash
poetry run pytest --cov=src --cov-report=html --cov-report=term
```

### Specific Test Files

```bash
poetry run pytest tests/test_api/test_context.py
```

### Running Tests with Different Verbosity

```bash
poetry run pytest -v  # Verbose
poetry run pytest -s  # Show print statements
```

### Integration Tests

```bash
poetry run pytest tests/test_api/ -k "not unit"
```

## Code Style

This project follows strict code style guidelines to ensure consistency and readability.

### Formatting

- **Line length**: 88 characters (Black standard)
- **Code formatter**: Black
- **Import sorting**: Ruff

### Running Code Style Tools

```bash
# Format code
poetry run black src tests

# Check linting
poetry run ruff check src tests

# Fix auto-fixable linting issues
poetry run ruff check --fix src tests

# Type checking
poetry run mypy src
```

### Pre-commit Checks

Before committing, ensure:

```bash
# Run all checks
poetry run black --check src tests
poetry run ruff check src tests
poetry run mypy src
poetry run pytest
```

### Code Style Rules

- Use type hints for all function parameters and return values
- Follow PEP 8 naming conventions
- Write descriptive docstrings for all public functions and classes
- Use async/await patterns consistently with SQLAlchemy 2.0
- Prefer explicit imports over wildcard imports
- Keep functions focused and single-purpose

## Pull Request Process

### Branch Naming

Use descriptive branch names with prefixes:

- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation updates
- `refactor/` - Code refactoring
- `test/` - Test additions/improvements

Examples:
- `feature/add-search-filters`
- `fix/context-loading-error`
- `docs/update-api-examples`

### Commit Message Format

Follow the conventional commits specification:

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Test additions/changes
- `chore`: Maintenance tasks

Examples:
- `feat(api): add search filtering for custom data`
- `fix(db): resolve connection pooling issue`
- `docs(readme): update installation instructions`

### Pull Request Guidelines

1. **Create a descriptive title** that summarizes the change
2. **Fill out the PR template** completely
3. **Keep PRs focused** - one feature or fix per PR
4. **Update documentation** if the change affects user-facing functionality
5. **Add tests** for new features or bug fixes
6. **Ensure all checks pass** (tests, linting, type checking)
7. **Request review** from maintainers

### Review Process

- All PRs require at least one review from a maintainer
- Address review feedback promptly
- Keep discussions constructive and professional
- Update your branch if requested

## Issue Reporting

### Bug Reports

When reporting bugs, please include:

1. **Clear title** describing the issue
2. **Steps to reproduce** the bug
3. **Expected behavior** vs actual behavior
4. **Environment details**:
   - Operating system
   - Python version
   - NovaPort-MCP version
   - Database type (SQLite/PostgreSQL)
5. **Error messages** and stack traces
6. **Minimal code example** if applicable

### Feature Requests

For feature requests, please provide:

1. **Clear description** of the proposed feature
2. **Use case** and motivation
3. **Proposed implementation** (if you have ideas)
4. **Alternatives considered**
5. **Breaking changes** (if any)

### Enhancement Suggestions

- Check existing issues first
- Be specific about the improvement
- Explain the benefit to users
- Consider backwards compatibility

## Documentation

### Requirements

- **Update documentation** for any user-facing changes
- **Add docstrings** to all new public functions and classes
- **Update API documentation** if endpoints change
- **Include code examples** for new features

### Documentation Standards

- Use **reStructuredText** format for Python docstrings
- Follow **Google style** docstring format
- Keep documentation **up-to-date** with code changes
- Include **type annotations** in function signatures

### Building Documentation

```bash
# Generate API documentation (if sphinx is set up)
poetry run sphinx-build -b html docs docs/_build
```

## Testing Requirements

### Test Coverage

- **Minimum coverage**: 80% for new code
- **Preferred coverage**: 90%+ for critical components
- **Test types**: Unit tests, integration tests, API tests

### Writing Tests

1. **Test new features** thoroughly
2. **Test edge cases** and error conditions
3. **Use descriptive test names** that explain what is being tested
4. **Follow AAA pattern**: Arrange, Act, Assert
5. **Mock external dependencies** appropriately

### Test Organization

```
tests/
├── test_api/          # API endpoint tests
├── test_services/     # Service layer tests
├── test_db/          # Database layer tests
└── conftest.py       # Shared fixtures
```

### Example Test

```python
import pytest
from httpx import AsyncClient

async def test_create_custom_data_success(client: AsyncClient):
    """Test successful creation of custom data entry."""
    # Arrange
    payload = {
        "category": "test",
        "key": "example",
        "data": {"value": "test"}
    }
    
    # Act
    response = await client.post("/custom-data", json=payload)
    
    # Assert
    assert response.status_code == 201
    assert response.json()["key"] == "example"
```

## Release Process

### Version Numbering

This project follows [Semantic Versioning](https://semver.org/):

- **MAJOR**: Breaking changes
- **MINOR**: New features (backwards compatible)
- **PATCH**: Bug fixes (backwards compatible)

### Pre-release Checklist

- [ ] All tests pass
- [ ] Documentation is updated
- [ ] Version is bumped in `pyproject.toml`
- [ ] RELEASE_NOTES.md is updated
- [ ] Migration scripts tested (if applicable)

## Getting Help

- **GitHub Issues**: For bug reports and feature requests
- **Email**: selfpooris@gmail.com for security issues
- **Documentation**: Check [docs/deep_dive.md](docs/deep_dive.md) for architecture details

## License

By contributing to NovaPort-MCP, you agree that your contributions will be licensed under the [Apache License 2.0](LICENSE).

---

Thank you for contributing to NovaPort-MCP! Your help makes this project better for everyone.