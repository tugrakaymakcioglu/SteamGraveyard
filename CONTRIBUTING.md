# Contributing to SteamGraveyard

Thank you for helping preserve accurate, useful catalog history. Code quality matters here, but data
quality and user safety matter just as much.

## Ground rules

- Never add code that requests Steam passwords, Steam Guard data, session cookies, or account tokens.
- Never implement DRM, ownership, payment, depot, manifest, or license bypasses.
- Never label a record `CLAIMABLE` without a current, reviewable source and verification timestamp.
- Prefer `UNKNOWN` when evidence is incomplete or conflicting.
- Keep unrelated changes out of a pull request.

## Development setup

```bash
python -m venv .venv
python -m pip install -e ".[dev]"
ruff check .
ruff format --check .
mypy steam_graveyard
pytest
```

Use Python 3.12 or newer. Tests must not open the real Steam client or require network access.

## Pull requests

1. Open an issue for substantial behavior or schema changes.
2. Add or update tests with the implementation.
3. Document public CLI, configuration, schema, and safety changes.
4. Run every local quality gate.
5. Explain the evidence behind dataset changes and link the original source.

### Dataset evidence

A claimability contribution must include the exact status, verification time, method, original URL,
and a short note explaining what the source proves. A shutdown announcement is not automatically
proof that a Steam license is currently unavailable. An AppID or working Steam URI is never proof
of ownership or claimability.

## Commit style

Use short, imperative commit subjects, for example:

```text
Add guarded catalog snapshot imports
Document claimability source requirements
```

By contributing, you agree that your contribution is licensed under the repository's MIT License.
