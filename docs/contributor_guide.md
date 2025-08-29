# Contributor Guide

This guide outlines the repository structure, how to build the project and the standards expected of contributions.

## Code Layout

- `assets/` – game data and JSON manifests.
- `core/` – fundamental logic and data structures.
- `events/` – game events and event handling helpers.
- `graphics/` – image utilities such as scaling helpers.
- `mapgen/` – procedural map generation algorithms.
- `render/` – window and map rendering code.
- `tests/` – automated test suite.
- additional packages like `ui/` and `tools/` contain user interface widgets and developer utilities.

## Build and Test

Create a development environment with the optional tooling extras:

```bash
pip install -e .[dev]
```

Run the test suite before submitting changes:

```bash
pytest
```

To produce a standalone build, install **PyInstaller** and run the provided spec:

```bash
pyinstaller fantaisie.spec
```

## Contribution Standards

- Follow PEP 8 style guidelines and keep imports sorted.
- Include tests and documentation alongside code changes.
- Ensure `pytest` and `make precommit-test` pass before committing.
- Write descriptive commit messages and reference related issues when applicable.
