# Steam data sources

SteamGraveyard separates current catalog facts, historical observations, and claimability evidence.
No single Steam endpoint provides all three.

## V1.1 source policy

| Need | Source | Automation | Trust boundary |
| --- | --- | --- | --- |
| Current games and DLC | Valve `IStoreService/GetAppList/v1` | Complete paginated scan | Requires a standard Web API key |
| Delisting candidates | Differences between successful local snapshots | Automatic | Three complete misses by default |
| Free/owners-only status | Timestamped official Store evidence or reviewed import | Curated | Becomes stale; Steam decides eligibility |
| Demo relationships | Reviewed import | Curated | The catalog endpoint has no demo filter |
| Historical cross-check | SteamDB AppID page | User opens the page | Never fetched or scraped by the app |

## Why SteamDB is not fetched

SteamDB's [FAQ](https://steamdb.info/faq/) says that it has no public API and does not allow
automatic scraping or crawling. SteamGraveyard only constructs a deterministic AppID link and opens
it after an explicit user action. SteamDB is not a download, API, fallback, or hidden dependency.

## Can the SteamDB data path be automated independently?

Partly. SteamDB documents that it uses [SteamKit](https://github.com/SteamRE/SteamKit) and Steam's
own change notification system. A compliant enrichment worker can anonymously observe public
Steam PICS app/package metadata and publish a versioned snapshot. That worker cannot reproduce
SteamDB's complete history immediately:

- deleted, hidden, beta, or restricted records may require app/package access tokens;
- a normal Steam Web API key does not contain those tokens;
- free package availability is not equivalent to account eligibility;
- a long-running history must be accumulated over time rather than inferred retroactively.

Bundling SteamKit directly in the beginner desktop path would add a .NET runtime and a persistent
Steam-network client. V1.1 keeps the desktop install Python-only. The planned V1.2 design runs the
anonymous enrichment worker in repository automation, validates and signs its output, and lets the
desktop consume the static dataset without receiving a Steam password, cookie, or session token.

## Non-negotiable rules

- Never infer `CLAIMABLE` from catalog presence, an AppID, or a working URI.
- Never advance missing counters after a partial or failed scan.
- Never automate SteamDB requests.
- Never ask for a Steam password, Steam Guard code, cookie, or account token.
- Never describe a Steam URI request as a guaranteed license grant.
