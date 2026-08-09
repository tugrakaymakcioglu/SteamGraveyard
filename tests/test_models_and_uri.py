from __future__ import annotations

import pytest
from pydantic import ValidationError

from steam_graveyard.models import ActivationMethod, ClaimStatus, Game, validate_uint32
from steam_graveyard.steam.uri import build_steam_uri


@pytest.mark.parametrize("value", [1, "350280", 4_294_967_295])
def test_validate_uint32_accepts_valid_identifiers(value: int | str) -> None:
    assert validate_uint32(value) == int(value)


@pytest.mark.parametrize("value", [0, -1, 4_294_967_296, "1.5", "\uff11\uff12\uff13", True])
def test_validate_uint32_rejects_invalid_identifiers(value: object) -> None:
    with pytest.raises(ValueError):
        validate_uint32(value)  # type: ignore[arg-type]


def test_build_install_uri() -> None:
    assert build_steam_uri(ActivationMethod.INSTALL, 350280) == "steam://install/350280"


def test_build_subscription_uri() -> None:
    assert (
        build_steam_uri(ActivationMethod.SUBSCRIPTION_INSTALL, "12345")
        == "steam://subscriptioninstall/12345"
    )


def test_none_activation_has_no_uri() -> None:
    assert build_steam_uri(ActivationMethod.NONE, None) is None
    with pytest.raises(ValueError):
        build_steam_uri(ActivationMethod.NONE, 1)


def test_unverified_game_cannot_expose_activation() -> None:
    with pytest.raises(ValidationError, match="activation is allowed"):
        Game(
            appid=12,
            name="Unsafe",
            claim_status=ClaimStatus.UNKNOWN,
            activation_method=ActivationMethod.INSTALL,
            activation_id="12",
        )


def test_non_unknown_claim_requires_source_and_time() -> None:
    with pytest.raises(ValidationError, match="verification time and source"):
        Game(appid=12, name="Unsupported claim", claim_status=ClaimStatus.UNAVAILABLE)


def test_game_normalizes_names_and_aliases() -> None:
    game = Game(appid="42", name="  A   Game ", aliases=[" Alias ", "alias", ""])
    assert game.appid == 42
    assert game.name == "A Game"
    assert game.aliases == ["Alias"]
