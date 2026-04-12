"""Menu component and input handling."""

from typing import List, Optional

import pygame

from ..input import InputAction, InputMapper
from .button import Button


class Menu:
    """Simple menu system."""

    def __init__(
        self,
        title: str,
        options: List[str],
        x: int = 100,
        y: int = 100,
        show_title: bool = True,
        title_padding: int = 100,
    ):
        self.title = title
        self.options = options
        self.show_title = show_title
        self.title_padding = title_padding
        self.buttons: List[Button] = []
        self.selected = 0
        self.font = pygame.font.Font(None, 48)
        self.title_font = pygame.font.Font(None, 64)
        self.button_width = 300
        self.button_height = 70
        self.button_spacing = 90
        self.input_mapper = InputMapper(deadzone=0.45)

        button_x = x
        button_y = y + title_padding

        for i, option in enumerate(options):
            btn = Button(button_x, button_y + i * self.button_spacing, self.button_width, self.button_height, option)
            self.buttons.append(btn)

    def _move_selection(self, direction: int) -> None:
        """Move menu selection up or down."""
        self.selected = (self.selected + direction) % len(self.options)

    def _activate_selected(self) -> int:
        """Return the currently selected option index."""
        return self.selected

    def set_position(self, x: int, y: int) -> None:
        """Reposition all menu buttons while keeping current styling."""
        button_y = y + self.title_padding
        for i, button in enumerate(self.buttons):
            button.rect.x = x
            button.rect.y = button_y + i * self.button_spacing

    def draw(self, surface: pygame.Surface) -> None:
        """Draw menu."""
        if self.show_title and self.title and self.buttons:
            title_surf = self.title_font.render(self.title, True, (255, 255, 255))
            title_rect = title_surf.get_rect(center=(self.buttons[0].rect.center[0], self.buttons[0].rect.y - 22))
            surface.blit(title_surf, title_rect)

        for i, button in enumerate(self.buttons):
            button.draw(surface, self.font, selected=(i == self.selected))

    def handle_input(self, event: pygame.event.Event) -> Optional[int]:
        """Handle menu input, return selected option or None."""
        action = self.input_mapper.map_event(event)
        if action == InputAction.NAV_UP:
            self._move_selection(-1)
        elif action == InputAction.NAV_DOWN:
            self._move_selection(1)
        elif action == InputAction.CONFIRM:
            return self._activate_selected()

        if event.type == pygame.MOUSEBUTTONDOWN:
            for i, button in enumerate(self.buttons):
                if button.is_clicked(event.pos):
                    return i

        return None

    def update(self, mouse_pos: tuple[int, int], delta_time: float = 0.016) -> None:
        """Update menu interactions and visual state."""
        for i, button in enumerate(self.buttons):
            button.update(mouse_pos, delta_time)
            if not button.hover and i == self.selected:
                button.hover_strength += (0.65 - button.hover_strength) * min(1.0, delta_time * 8.0)
