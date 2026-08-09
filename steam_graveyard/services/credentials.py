"""Secure Steam Web API key validation and local credential storage."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

import keyring
from keyring.errors import KeyringError
from pydantic import SecretStr

from steam_graveyard.config import Settings
from steam_graveyard.errors import ConfigurationError

API_KEY_PAGE = "https://steamcommunity.com/dev/apikey"
API_TERMS_PAGE = "https://steamcommunity.com/dev/apiterms"
_API_KEY_PATTERN = re.compile(r"^[0-9A-Fa-f]{32}$")


@dataclass(frozen=True, slots=True)
class CredentialResult:
    persisted: bool
    message: str


class CredentialStore(Protocol):
    def load(self) -> str | None: ...

    def save(self, api_key: str) -> CredentialResult: ...

    def delete(self) -> CredentialResult: ...


def normalize_api_key(value: str) -> str:
    """Return a canonical key without ever including it in an error message."""
    normalized = value.strip()
    if not _API_KEY_PATTERN.fullmatch(normalized):
        raise ConfigurationError(
            "A Steam Web API key must contain exactly 32 hexadecimal characters."
        )
    return normalized.upper()


class KeyringCredentialStore:
    """Persist credentials in Windows Credential Manager, Keychain, or Secret Service."""

    service_name = "SteamGraveyard"
    username = "steam-web-api-key"

    def load(self) -> str | None:
        try:
            stored = keyring.get_password(self.service_name, self.username)
        except KeyringError:
            return None
        if not stored:
            return None
        try:
            return normalize_api_key(stored)
        except ConfigurationError:
            return None

    def save(self, api_key: str) -> CredentialResult:
        normalized = normalize_api_key(api_key)
        try:
            keyring.set_password(self.service_name, self.username, normalized)
        except KeyringError:
            return CredentialResult(
                False,
                "The key is valid but secure system storage is unavailable; it will be used only "
                "for this session.",
            )
        return CredentialResult(
            True, "The API key was saved in your operating system credential vault."
        )

    def delete(self) -> CredentialResult:
        try:
            keyring.delete_password(self.service_name, self.username)
        except keyring.errors.PasswordDeleteError:
            return CredentialResult(True, "No saved Steam API key was found.")
        except KeyringError:
            return CredentialResult(False, "The operating system credential vault is unavailable.")
        return CredentialResult(True, "The saved Steam API key was removed.")


def hydrate_api_key(settings: Settings, credential_store: CredentialStore | None = None) -> bool:
    """Load a stored key only when an environment or `.env` key is absent."""
    if settings.steam_api_key is not None:
        return True
    stored = (credential_store or KeyringCredentialStore()).load()
    if stored is None:
        return False
    settings.steam_api_key = SecretStr(stored)
    return True
