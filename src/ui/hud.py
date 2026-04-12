"""HUD rendering components."""

import pygame


class HUD:
    """Heads-up display for battle."""

    def __init__(self, screen_width: int, screen_height: int):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.font = pygame.font.Font(None, 24)

    def draw_unit_info(self, surface: pygame.Surface, unit, x: int, y: int) -> None:
        """Draw unit information display."""
        info_text = [
            f"{unit.name} Lv.{unit.level}",
            f"HP: {unit.current_hp}/{unit.stats.hp}",
            f"STR:{unit.stats.str} DEF:{unit.stats.def_} AGL:{unit.stats.agl}",
        ]

        for i, text in enumerate(info_text):
            surface.blit(self.font.render(text, True, (255, 255, 255)), (x, y + i * 25))

    def draw_hp_bar(self, surface: pygame.Surface, unit, x: int, y: int, width: int, height: int) -> None:
        """Draw unit health bar."""
        percent = unit.get_hp_percentage() / 100.0

        pygame.draw.rect(surface, (50, 50, 50), (x, y, width, height))

        health_width = int(width * percent)
        color = (0, 255, 0) if percent > 0.5 else (255, 255, 0) if percent > 0.25 else (255, 0, 0)
        pygame.draw.rect(surface, color, (x, y, health_width, height))

        pygame.draw.rect(surface, (255, 255, 255), (x, y, width, height), 2)
