import pygame

from src.input import InputAction, InputMapper


def test_mapper_keyboard_navigation() -> None:
    mapper = InputMapper()
    up = mapper.map_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_UP}))
    down = mapper.map_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_DOWN}))
    assert up == InputAction.NAV_UP
    assert down == InputAction.NAV_DOWN


def test_mapper_confirm_keys() -> None:
    mapper = InputMapper()
    result = mapper.map_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RETURN}))
    assert result == InputAction.CONFIRM
