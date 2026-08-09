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

SteamGraveyard must never collect Steam credentials, persist Steam sessions, forge licenses, bypass
DRM or ownership checks, or download protected depots. The only client integration in V1 is an
operating-system request to open an allow-listed `steam://` URI. Steam remains responsible for every
license and installation decision.
