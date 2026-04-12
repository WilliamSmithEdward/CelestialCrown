"""Shared state module helpers."""

from typing import TYPE_CHECKING

try:
    import pygame  # type: ignore

    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False

if TYPE_CHECKING:
    import pygame  # type: ignore
