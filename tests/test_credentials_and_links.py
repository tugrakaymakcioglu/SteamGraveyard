from __future__ import annotations

from dataclasses import dataclass

import pytest
from pydantic import SecretStr

from steam_graveyard.config import Settings
from steam_graveyard.errors import ConfigurationError
from steam_graveyard.models import Game
from steam_graveyard.services.credentials import (
    CredentialResult,
    KeyringCredentialStore,
    hydrate_api_key,
    normalize_api_key,
)
from steam_graveyard.services.links import (
    open_steamdb_page,
    open_store_page,
    steam_store_url,
    steamdb_app_url,
)

VALID_KEY = "0123456789abcdef0123456789abcdef"


@dataclass
class FakeCredentialStore:
    value: str | None = None
    saved: str | None = None

    def load(self) -> str | None:
        return self.value

    def save(self, api_key: str) -> CredentialResult:
        self.saved = api_key
        return CredentialResult(True, "saved")

    def delete(self) -> CredentialResult:
        self.value = None
        return CredentialResult(True, "deleted")


def test_api_key_normalization_never_echoes_invalid_value() -> None:
    assert normalize_api_key(f" {VALID_KEY} ") == VALID_KEY.upper()
    invalid = "not-a-secret"
    with pytest.raises(ConfigurationError) as captured:
        normalize_api_key(invalid)
    assert invalid not in str(captured.value)


def test_hydrate_api_key_prefers_explicit_settings(settings: Settings) -> None:
    settings.steam_api_key = SecretStr(VALID_KEY)
    store = FakeCredentialStore(value="f" * 32)
    assert hydrate_api_key(settings, store)
    assert settings.steam_api_key.get_secret_value() == VALID_KEY


def test_hydrate_api_key_uses_secure_store(settings: Settings) -> None:
    store = FakeCredentialStore(value=VALID_KEY)
    assert hydrate_api_key(settings, store)
    assert settings.steam_api_key is not None
    assert settings.steam_api_key.get_secret_value() == VALID_KEY


def test_keyring_store_handles_unavailable_backend(monkeypatch) -> None:
    def fail_get(*_args: str) -> str | None:
        from keyring.errors import NoKeyringError

        raise NoKeyringError()

    def fail_set(*_args: str) -> None:
        from keyring.errors import NoKeyringError

        raise NoKeyringError()

    monkeypatch.setattr("steam_graveyard.services.credentials.keyring.get_password", fail_get)
    monkeypatch.setattr("steam_graveyard.services.credentials.keyring.set_password", fail_set)
    store = KeyringCredentialStore()
    assert store.load() is None
    assert not store.save(VALID_KEY).persisted


def test_keyring_store_round_trip(monkeypatch) -> None:
    saved: list[str] = []
    monkeypatch.setattr(
        "steam_graveyard.services.credentials.keyring.get_password",
        lambda *_args: VALID_KEY,
    )
    monkeypatch.setattr(
        "steam_graveyard.services.credentials.keyring.set_password",
        lambda _service, _username, value: saved.append(value),
    )
    monkeypatch.setattr(
        "steam_graveyard.services.credentials.keyring.delete_password",
        lambda *_args: None,
    )
    store = KeyringCredentialStore()
    assert store.load() == VALID_KEY.upper()
    assert store.save(VALID_KEY).persisted
    assert saved == [VALID_KEY.upper()]
    assert store.delete().persisted


def test_allowlisted_research_and_store_links() -> None:
    game = Game(appid=350280, name="LawBreakers")
    assert steamdb_app_url(game.appid) == "https://steamdb.info/app/350280/"
    assert steam_store_url(game.appid) == "https://store.steampowered.com/app/350280/"
    opened: list[str] = []
    assert open_steamdb_page(game, opener=lambda url: not opened.append(url)).success
    assert opened == ["https://steamdb.info/app/350280/"]
    failed = open_store_page(game, opener=lambda _url: False)
    assert not failed.success
    assert "could not" in failed.message
    errored = open_store_page(game, opener=lambda _url: (_ for _ in ()).throw(OSError("closed")))
    assert not errored.success
