"""Input actions used across UI and gameplay."""

from enum import Enum


class InputAction(Enum):
    """High-level actions independent of device-specific events."""

    NAV_UP = "nav_up"
    NAV_DOWN = "nav_down"
    CONFIRM = "confirm"
    CANCEL = "cancel"
