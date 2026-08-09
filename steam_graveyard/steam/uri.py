"""Safe Steam URI construction."""

from __future__ import annotations

from steam_graveyard.models import ActivationMethod, validate_uint32


def build_steam_uri(method: ActivationMethod | str, activation_id: int | str | None) -> str | None:
    """Build an allow-listed Steam URI without attempting any license bypass."""
    parsed_method = ActivationMethod(method)
    if parsed_method is ActivationMethod.NONE:
        if activation_id is not None:
            raise ValueError("activation ID must be omitted when activation method is none")
        return None
    if activation_id is None:
        raise ValueError("activation ID is required")
    identifier = validate_uint32(activation_id, label="activation ID")
    return f"steam://{parsed_method.value}/{identifier}"
