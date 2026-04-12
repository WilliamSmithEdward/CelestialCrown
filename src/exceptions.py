"""Domain-specific exception classes for Celestial Crown."""


class CelestialCrownError(Exception):
    """Base exception for all game-related errors."""

    pass


class BattleError(CelestialCrownError):
    """Raised when a battle operation fails."""

    pass


class GridError(BattleError):
    """Raised when a grid operation fails."""

    pass


class CombatError(BattleError):
    """Raised when a combat calculation fails."""

    pass


class UnitError(CelestialCrownError):
    """Raised when unit state operation fails."""

    pass


class TownError(CelestialCrownError):
    """Raised when town operation fails."""

    pass


class FacilityError(TownError):
    """Raised when facility operation fails."""

    pass


class StoryError(CelestialCrownError):
    """Raised when story/narrative operation fails."""

    pass


class ConfigError(CelestialCrownError):
    """Raised when configuration is invalid."""

    pass
