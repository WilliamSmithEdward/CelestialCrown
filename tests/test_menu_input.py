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


def test_menu_switches_between_mouse_and_nav_modes() -> None:
    menu = Menu("", ["A", "B", "C"], 0, 0, show_title=False, title_padding=0)

    menu.handle_input(pygame.event.Event(pygame.MOUSEMOTION, {"pos": (10, 10)}))
    assert menu._input_mode == "mouse"

    menu.handle_input(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_DOWN}))
    assert menu._input_mode == "nav"


def test_menu_mouse_hover_controls_focus_visual() -> None:
    menu = Menu("", ["A", "B", "C"], 0, 0, show_title=False, title_padding=0)
    menu.handle_input(pygame.event.Event(pygame.MOUSEMOTION, {"pos": (0, 0)}))

    menu.selected = 2
    menu.buttons[0].hover = False
    menu.buttons[1].hover = True
    menu.buttons[2].hover = False

    calls: list[tuple[int, bool]] = []
    for idx, button in enumerate(menu.buttons):
        button.draw = lambda surface, font, selected=False, idx=idx: calls.append((idx, bool(selected)))

    surface = pygame.Surface((800, 600))
    menu.draw(surface)

    assert calls == [(0, False), (1, True), (2, False)]


def test_menu_nav_focus_uses_selected_index() -> None:
    menu = Menu("", ["A", "B", "C"], 0, 0, show_title=False, title_padding=0)
    menu.handle_input(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_DOWN}))

    menu.selected = 2
    for button in menu.buttons:
        button.hover = False

    calls: list[tuple[int, bool]] = []
    for idx, button in enumerate(menu.buttons):
        button.draw = lambda surface, font, selected=False, idx=idx: calls.append((idx, bool(selected)))

    surface = pygame.Surface((800, 600))
    menu.draw(surface)

    assert calls == [(0, False), (1, False), (2, True)]
