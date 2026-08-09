# Security Policy

## Supported versions

Security fixes are applied to the latest release and the default branch.

## Reporting a vulnerability

Please use GitHub's private vulnerability reporting feature for this repository. Do not publish
credentials, proof-of-concept account abuse, or sensitive Steam data in a public issue.

Include:

- the affected version or commit;
- reproduction steps that do not target another person's account;
- the expected and observed behavior;
- the potential impact;
- a suggested mitigation, if available.

You should receive an acknowledgment within seven days. A validated report will be coordinated
privately until a fix and disclosure timeline are ready.

## Security boundaries

SteamGraveyard must never collect Steam passwords, Steam Guard codes, cookies, account tokens, or
Steam sessions; forge licenses; bypass DRM or ownership checks; or download protected depots. A
standard Web API key is validated over HTTPS and stored in the operating system credential vault
when available. It must never enter logs, datasets, screenshots, or issue reports.

Client integration is limited to operating-system requests for allow-listed `steam://` URIs and
explicitly requested HTTPS research pages. Steam remains responsible for every license and
installation decision.
