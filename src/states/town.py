"""Town state implementation."""

from ._shared import PYGAME_AVAILABLE, pygame
from ..config import COLOR_BLACK, COLOR_WHITE
from ..core.gamestate import GameState, StateType


class TownState(GameState):
    """Town/base management state."""

    def __init__(self):
        super().__init__()
        self.state_type = StateType.TOWN

    def on_enter(self) -> None:
        pass

    def on_exit(self) -> None:
        pass

    def handle_event(self, event) -> None:
        pass

    def update(self, delta_time: float) -> None:
        pass

    def render(self, screen) -> None:
        if not PYGAME_AVAILABLE:
            return
        screen.fill(COLOR_BLACK)
        font = pygame.font.Font(None, 32)
        text = font.render("Town - Coming Soon", True, COLOR_WHITE)
        screen_w, screen_h = screen.get_size()
        text_rect = text.get_rect(center=(screen_w // 2, screen_h // 2))
        screen.blit(text, text_rect)
