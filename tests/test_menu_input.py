import pygame

from src.ui import Menu


def test_menu_keyboard_navigation_wraps() -> None:
    menu = Menu("", ["A", "B", "C"], 0, 0, show_title=False, title_padding=0)

    menu.handle_input(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_UP}))
    assert menu.selected == 2

    menu.handle_input(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_DOWN}))
    assert menu.selected == 0


def test_menu_return_selects_current_option() -> None:
    menu = Menu("", ["A", "B", "C"], 0, 0, show_title=False, title_padding=0)
    menu.selected = 1
    result = menu.handle_input(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RETURN}))
    assert result == 1
