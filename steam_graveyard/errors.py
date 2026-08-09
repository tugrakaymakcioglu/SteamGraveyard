"""User-facing error types."""


class SteamGraveyardError(Exception):
    """Base class for errors that should be presented without a traceback."""


class ConfigurationError(SteamGraveyardError):
    """The application configuration is incomplete or invalid."""


class DatabaseError(SteamGraveyardError):
    """The local database could not be used safely."""


class DatabaseCorruptionError(DatabaseError):
    """SQLite reported that the database is corrupt."""


class CatalogError(SteamGraveyardError):
    """The Steam catalog could not be fetched or validated."""


class SnapshotSafetyError(CatalogError):
    """A suspicious catalog snapshot was rejected."""


class LauncherError(SteamGraveyardError):
    """Steam could not be opened through the operating system."""


class ClipboardError(SteamGraveyardError):
    """The Steam URI could not be copied."""
