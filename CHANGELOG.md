# Changelog

All notable changes to SteamGraveyard are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.1.0] - 2026-08-09

[Read the complete SteamGraveyard 1.1 release notes](docs/releases/v1.1.0.md).

### Added

- Guided first-run Steam Web API key setup with masked input, live validation, and offline fallback.
- Operating-system credential-vault storage through Keyring with a session-only safe fallback.
- Separate official catalog scans for games and DLC, plus categorized TUI and CLI views.
- Explicit Steam Store and SteamDB research links opened only after user action.
- One-click Steam handoff button that remains disabled without source-verified activation metadata.
- Double-click Windows setup/launcher and source-verified free-to-play and demo seed examples.
- Tests for credential handling, setup navigation, content typing, categories, and external links.

### Changed

- Updated the package version and public documentation for the V1.1 beginner-first workflow.
- Clarified that SteamDB has no public API, is never scraped, and is used only as a research link.

## [0.1.0] - 2026-08-09

### Added

- Local-first Textual catalog with paged navigation and live fuzzy search.
- SQLite schema, migrations, conservative seed data, and stable JSON/CSV/JSONL exports.
- Supported Steam Store catalog pagination, guarded snapshots, and three-scan delisting confirmation.
- Safe cross-platform Steam URI and clipboard adapters with claimability gates.
- Rich CLI commands for search, game details, events, statuses, updates, and exports.
- Offline operation, structured logs, user-friendly errors, tests, and GitHub Actions workflows.
- Security policy, contribution guidance, issue forms, and pull request quality checklist.

[Unreleased]: https://github.com/tugrakaymakcioglu/SteamGraveyard/commits/main
[1.1.0]: https://github.com/tugrakaymakcioglu/SteamGraveyard/releases/tag/v1.1.0
[0.1.0]: https://github.com/tugrakaymakcioglu/SteamGraveyard/tree/main
