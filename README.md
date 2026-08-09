<div align="center">

```text
  _________ __                         ________                              .___
 /   _____//  |_  ____ _____    _____ /  _____/___________ ___  _______  ___| _/
 \_____  \\   __\/ __ \\__  \  /     /   \  __\_  __ \__  \\ \_  __ \/ __ |
 /        \|  | \  ___/ / __ \|  Y Y \    \_\  \  | \// __ \_|  | \/ /_/ |
/_______  /|__|  \___  >____  /__|_|  /\______  /__|  (____  /|__|  \____ |
        \/           \/     \/      \/        \/           \/            \/
```

# SteamGraveyard

**Discover forgotten Steam games.**

A guided, local-first terminal catalog for researching delisted Steam games,
browsing games, DLC, and demos, and opening only verified Steam-supported actions.

[![CI](https://github.com/tugrakaymakcioglu/SteamGraveyard/actions/workflows/tests.yml/badge.svg)](https://github.com/tugrakaymakcioglu/SteamGraveyard/actions/workflows/tests.yml)
[![Version 1.1](https://img.shields.io/badge/version-1.1.0-66d9ef)](CHANGELOG.md)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-2ea44f.svg)](LICENSE)
[![Textual](https://img.shields.io/badge/UI-Textual-6f42c1)](https://textual.textualize.io/)

</div>

---

Games disappear from storefronts. Their histories should not disappear with them.

SteamGraveyard turns a versioned SQLite dataset into a responsive terminal catalog. It helps
researchers, preservation-minded players, and curious developers inspect catalog history without
collecting Steam credentials or pretending that an AppID grants ownership. The application is
useful offline, keeps provenance beside verification claims, and delegates every license decision
to the official Steam client.

> [!IMPORTANT]
> SteamGraveyard does **not** bypass Steam ownership, licensing, DRM, or payment systems. It only
> opens Steam-supported URI actions. Steam decides whether a license or installation is available
> for an account. AppIDs and package/SubIDs do not grant ownership.

![SteamGraveyard interface preview](docs/screenshot.svg)

## New in 1.1

[Read the complete SteamGraveyard 1.1 release notes](docs/releases/v1.1.0.md).

- **Guided first launch** — the TUI explains where to create a Steam Web API key, validates it with
  one read-only request, and lets users continue offline.
- **Secure by default** — validated keys are stored in Windows Credential Manager, macOS Keychain,
  or Linux Secret Service when a backend is available; they are never written to the dataset.
- **Category browser** — switch between games, DLC, curated demos, verified-free items, and
  delisted records from one dropdown.
- **One-click handoff** — verified items expose an explicit button that delegates to the official
  Steam client; unverified items keep the button disabled.
- **SteamDB research links** — open the matching SteamDB page on demand without scraping or
  automatically fetching SteamDB.
- **Windows double-click launcher** — first-time setup and later launches use the same file.

## Why SteamGraveyard

- **Fast terminal workflow** — browse a paged Textual table designed for large local datasets.
- **Search that forgives typos** — find games by title, AppID, or aliases with FTS5 and RapidFuzz.
- **Evidence before labels** — unverified claimability remains `UNKNOWN`; stale checks are visible.
- **Conservative change detection** — one missing scan is suspicion, not proof of delisting.
- **Safe Steam handoff** — supported `steam://` URIs are opened through the operating system.
- **Offline by design** — the catalog, search, details, and exports work without a network.
- **Automation-ready data** — consume deterministic JSON, CSV, JSONL, or the SQLite database.

## Install

### Windows — easiest path

1. [Download the latest Windows ZIP](https://github.com/tugrakaymakcioglu/SteamGraveyard/releases/latest/download/SteamGraveyard-Windows.zip).
2. Extract the ZIP.
3. Double-click `START_STEAM_GRAVEYARD.bat`.

The launcher checks Python, creates a private `.venv`, installs the application, and opens the TUI.
If Python is missing, it shows the exact [Python 3.12+ download page](https://www.python.org/downloads/)
instead of closing silently. Run the same file every time; setup is idempotent.

### Install from GitHub

```bash
python -m pip install "git+https://github.com/tugrakaymakcioglu/SteamGraveyard.git@v1.1.0"
steam-graveyard
```

Python 3.12 or newer is required. The application creates its local database on first launch and
imports the bundled conservative seed, so an API key is **not** required for offline browsing.

### First launch

The setup screen contains the official [Steam Web API key page](https://steamcommunity.com/dev/apikey),
short instructions, a masked `API KEY` field, and an offline option. Paste a standard 32-character
user key and press `Enter`. SteamGraveyard checks the key with a single-result catalog request,
stores it in the operating system credential vault when available, and starts a background catalog
update. For local-only use, enter `localhost` if Steam's domain field accepts it; otherwise use a
domain you control. A Steam password, cookie, guard code, or account token is never requested.

Environment-based configuration remains available for servers and advanced users. An explicit
`STEAM_API_KEY` value from the environment or `.env` takes precedence over secure local storage.

### Developer checkout

```bash
git clone https://github.com/tugrakaymakcioglu/SteamGraveyard.git
cd SteamGraveyard
python -m venv .venv
```

Activate the environment:

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

```bash
# Linux / macOS
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Quick start

```bash
# Open the terminal UI
steam-graveyard

# Search without opening the TUI
steam-graveyard search "lawbreakers"

# Inspect a known AppID
steam-graveyard game 350280

# Export the current local database
steam-graveyard export

# Re-open guided setup or remove the saved key
steam-graveyard setup
steam-graveyard forget-key
```

### Keyboard controls

| Key | Action |
| --- | --- |
| `↑` / `↓` | Move through games and load adjacent result pages |
| `Ctrl+S` | Open live search |
| `Enter` | Open the selected game or send a verified action to Steam |
| `C` | Copy the verified Steam URI on the detail screen |
| `D` | Open the selected AppID on SteamDB for manual research |
| `S` | Open the official Steam Store page |
| `R` | Refresh the catalog using `STEAM_API_KEY` |
| `Esc` | Close search or return to the catalog |
| `Q` | Quit |

## CLI reference

```text
steam-graveyard                         Open the TUI
steam-graveyard search QUERY [--limit] Search names, AppIDs, and aliases
steam-graveyard game APPID             Show one local record
steam-graveyard latest [--limit]       Show recent catalog events
steam-graveyard claimable [--limit]    List source-verified claimable games
steam-graveyard category CATEGORY      List games, dlc, demos, free, or delisted
steam-graveyard delisted [--limit]     List confirmed delisted games
steam-graveyard update                 Run a complete Steam catalog scan
steam-graveyard export                 Rebuild JSON, CSV, and JSONL exports
steam-graveyard setup                  Re-open guided API key setup
steam-graveyard forget-key             Remove the securely stored API key
```

Use `--data-dir PATH` before a command to isolate a dataset. Configuration can also be supplied
through the environment variables documented in [`.env.example`](.env.example).

## How it works

```text
Official Steam catalog API (games + DLC)
          │ complete, type-aware, paginated scan
          ▼
Validated gzip snapshot ──► snapshot safety guard
          │
          ▼
SQLite transaction ──► events + missing-scan state ──► deterministic exports
          │
          ├──► categorized Textual TUI / fuzzy search
          ├──► Rich CLI
          └──► user-initiated SteamDB / Steam Store research links
```

Catalog updates use Valve's supported, paginated
[`IStoreService/GetAppList/v1`](https://partner.steamgames.com/doc/webapi/IStoreService)
interface. Games and DLC are requested separately so their type remains explicit. The endpoint does
not expose a demo filter or prove that an item is free; demos and claimability therefore remain
source-curated. The deprecated `ISteamApps/GetAppList/v2` endpoint is not used.

A full scan requires a Steam Web API key:

```bash
cp .env.example .env
# Set STEAM_API_KEY in .env, then:
steam-graveyard update
```

On Windows PowerShell, use `Copy-Item .env.example .env`. Steam Web API keys are managed through
Valve's [Web API key page](https://steamcommunity.com/dev/apikey).

Secrets are never committed, printed, written to structured logs, or stored in SQLite.

### SteamDB and autonomous metadata

SteamDB is an excellent manual research reference, but it [does not provide a public API and does
not permit automated scraping/crawling](https://steamdb.info/faq/). SteamGraveyard therefore never
scrapes SteamDB. It only builds deterministic `https://steamdb.info/app/<appid>/` links and opens
them after an explicit user click.

SteamDB describes its underlying data path as SteamKit plus Steam's own update system. A future
headless enrichment worker can use anonymous SteamKit/PICS to produce a reviewed, versioned dataset
without adding .NET or Steam credentials to the desktop experience. Hidden and deleted records may
still require access tokens that a normal API key cannot provide, so unavailable evidence remains
`UNKNOWN` rather than being guessed.

See [Steam data sources](docs/DATA_SOURCES.md) for the provider matrix and autonomous enrichment
boundary.

### Delisting detection

A disappeared AppID is not immediately classified as delisted. Only successful, complete scans
advance the state machine:

```text
ACTIVE → SUSPECTED_DELISTING → DELISTED
                              ↘ RELISTED when the AppID returns
```

The default confirmation threshold is three consecutive complete scans. Failed and partial scans
do not change missing counters. A snapshot smaller than 80% of the preceding successful snapshot
is rejected to reduce the risk of mass false positives.

### Claimability and Steam URIs

Catalog presence, an AppID, or a working URI says nothing about license availability.
SteamGraveyard therefore separates catalog status from claim status:

- `CLAIMABLE` — a maintained source confirms that Steam currently offers the license.
- `OWNERS_ONLY` — existing owners may be able to install it; Steam still verifies ownership.
- `UNKNOWN` — no sufficiently current evidence exists.
- `UNAVAILABLE` — a maintained source confirms that no supported activation is available.

Only `CLAIMABLE` and `OWNERS_ONLY` records with validated activation metadata expose an action:

```text
steam://install/<appid>
steam://subscriptioninstall/<subid>
```

SteamGraveyard does not log in to Steam, inspect an account, forge a license, download protected
depots, or alter the Steam client. “Add / Open in Steam” means handing an allow-listed URI to Steam;
it is not a license grant. Claimability data must be curated separately from catalog scans.

Maintainers can validate and import a reviewable JSON batch with
`python scripts/import_verifications.py records.json`. Each record must include the AppID, exact
claim status, UTC verification time, method, original source object, and any activation metadata.
The importer applies the same safety validation as the application and rebuilds the public exports.

### Popularity score

Popularity is deterministic and normalized to `0–100`:

| Component | Weight | Normalization |
| --- | ---: | --- |
| Historical peak players | 50% | `log1p(value) / log1p(1,000,000)` |
| Review count | 30% | `log1p(value) / log1p(1,000,000)` |
| Review score | 20% | `score / 100` |

Missing components are not invented. Available weights are re-normalized; when every component is
missing, the score remains `null` and the UI displays `—`.

## Data and provenance

Runtime state is stored in `data/steam_graveyard.db` for a source checkout. The binary database,
logs, and raw snapshots are intentionally ignored by Git. Stable public exports live in:

- `data/export/games.json`
- `data/export/games.csv`
- `data/export/events.jsonl`

Core tables are `games`, `events`, `sources`, `verification_history`, and `scan_runs`. All exported
timestamps are ISO 8601 UTC and every format carries `schema_version: 1`.

The bundled seed is deliberately small. It identifies LawBreakers from an
[official Steam announcement](https://store.steampowered.com/news/?appgroupname=LawBreakers&appids=350280&feed=steam_community_announcements),
but keeps both delisting and claimability conservative where the available evidence does not prove
their current state. SteamGraveyard never upgrades historical context into a current claimability
claim.

Version 1.1 also includes source-timestamped examples for Team Fortress 2, Counter-Strike 2, and
the We Were Here Tomorrow Demo, verified as free-to-play or a free demo on their official Steam
Store pages on the dataset date. These checks can become stale and do not override Steam's
account-level decision.

## Reliability and failure behavior

- Missing network: the TUI shows `OFFLINE MODE`; local features remain available.
- Missing API key: guided setup appears; offline browsing remains available.
- Invalid API key: one small validation request fails in place without saving or displaying the key.
- Missing credential backend: the validated key remains session-only and the user receives a warning.
- Rate limits and transient server errors: bounded retry honors `Retry-After`.
- Missing Steam handler: no shell fallback or unsafe command construction is attempted.
- Corrupt database: the file is preserved and recovery guidance is shown; it is never silently
  deleted.
- Clipboard failure: the TUI remains open and reports the failure.

## Development

```bash
ruff check .
ruff format --check .
mypy steam_graveyard scripts
pytest
python -m build
```

Tests use mock transports, temporary SQLite databases, and Textual's headless pilot. They never
open a real Steam client. Pull requests run the same gates on Linux and Python 3.12.

The scheduled catalog workflow reads `STEAM_API_KEY` from GitHub Actions secrets. With no key it
exits successfully with an explicit skip summary. Dataset commits are opt-in through the repository
variable `STEAM_GRAVEYARD_AUTO_COMMIT=true`.

See [CONTRIBUTING.md](CONTRIBUTING.md) before proposing dataset or code changes. Security reports
belong in the private process described by [SECURITY.md](SECURITY.md), not in public issues.

## Roadmap

- **V1:** TUI, search, SQLite dataset, safe Steam URI launcher, snapshot diff, claim status, exports
- **V1.1:** guided secure setup, category browser, game/DLC scans, verified one-click handoff,
  SteamDB research links, Windows double-click launcher
- **V1.2:** anonymous SteamKit/PICS enrichment worker, reviewed demo/package relationships,
  signed versioned metadata releases
- **V2:** optional remote API, web dashboard, notifications, historical catalog analysis

Authenticated Steam account features remain outside the desktop scope. They would require a
separate security and privacy review before any future design work.

## License and trademark notice

SteamGraveyard is available under the [MIT License](LICENSE).

Steam and the Steam logo are trademarks and/or registered trademarks of Valve Corporation. This
project is independent, is not endorsed by Valve, and does not include Valve assets.
