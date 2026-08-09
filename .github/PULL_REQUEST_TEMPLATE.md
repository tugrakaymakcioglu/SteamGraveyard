## Summary

<!-- Explain the user-visible outcome and why the change is needed. -->

## Validation

- [ ] `ruff check .`
- [ ] `ruff format --check .`
- [ ] `mypy steam_graveyard`
- [ ] `pytest`
- [ ] No test opened a real Steam client

## Safety and data provenance

- [ ] This change does not request or store Steam credentials, tokens, cookies, or Steam Guard data.
- [ ] This change does not bypass ownership, licensing, DRM, payments, depots, or manifests.
- [ ] New claimability labels include a source, method, and verification timestamp, or remain `UNKNOWN`.
- [ ] Dataset sources are original and the description states exactly what they prove.

## Screenshots or output

<!-- Include sanitized output for user-interface or CLI changes when useful. -->
