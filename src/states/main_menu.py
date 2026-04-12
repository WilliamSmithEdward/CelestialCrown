"""Main menu state implementation."""

import os

from ._shared import PYGAME_AVAILABLE, pygame
from ..config import COLOR_BLACK, SCREEN_HEIGHT, SCREEN_WIDTH
from ..core.gamestate import GameState, StateType
from ..core.services import AudioLoopService, LoopConfig
from ..effects import AnimatedBackground
from ..ui import Menu


class MainMenuState(GameState):
    """Main menu state."""

    def __init__(self):
        super().__init__()
        self.state_type = StateType.MAIN_MENU
        self.menu_button_width = 300
        self.menu_button_height = 70
        self.menu_spacing = 90
        self.menu_title_padding = 24
        self.menu_option_count = 4
        menu_block_height = (
            self.menu_title_padding
            + (self.menu_option_count - 1) * self.menu_spacing
            + self.menu_button_height
        )
        menu_x = (SCREEN_WIDTH - self.menu_button_width) // 2
        menu_y = (SCREEN_HEIGHT - menu_block_height) // 2
        self.menu = Menu(
            "",
            ["New Game", "Load Game", "Settings", "Quit"],
            menu_x,
            menu_y,
            show_title=False,
            title_padding=self.menu_title_padding,
        )
        if PYGAME_AVAILABLE:
            self.font = pygame.font.Font(None, 32)
            self.title_font = pygame.font.SysFont("georgia", 108, bold=True)
            self.title_sub_font = pygame.font.SysFont("georgia", 42, bold=True)
            self.credit_font = pygame.font.SysFont("georgia", 24, bold=False)
            self.background = AnimatedBackground(SCREEN_WIDTH, SCREEN_HEIGHT)

            music_path = os.path.normpath(
                os.path.join(os.path.dirname(__file__), "..", "..", "assets", "audio", "CelestialCrown_Intro.wav")
            )
            self.audio_loop = AudioLoopService(LoopConfig(path=music_path, volume=0.60, fade_seconds=2.2))
        else:
            self.font = None
            self.title_font = None
            self.title_sub_font = None
            self.credit_font = None
            self.background = None
            self.audio_loop = None

    def _render_spaced_text(self, font, text: str, color: tuple, tracking: int = 0):
        """Render text with consistent character spacing for cleaner typography."""
        glyphs = [font.render(ch, True, color) for ch in text]
        if not glyphs:
            return font.render("", True, color)

        width = sum(g.get_width() for g in glyphs) + tracking * max(0, len(glyphs) - 1)
        height = max(g.get_height() for g in glyphs)
        surf = pygame.Surface((width, height), pygame.SRCALPHA)

        x = 0
        for glyph in glyphs:
            surf.blit(glyph, (x, 0))
            x += glyph.get_width() + tracking
        return surf

    def _layout_for_size(self, screen_width: int, screen_height: int) -> None:
        """Center menu for the current render surface size."""
        menu_block_height = (
            self.menu_title_padding
            + (self.menu_option_count - 1) * self.menu_spacing
            + self.menu_button_height
        )
        menu_x = (screen_width - self.menu_button_width) // 2
        menu_y = (screen_height - menu_block_height) // 2
        self.menu.set_position(menu_x, menu_y)

    def on_enter(self) -> None:
        """Called when entering state."""
        if self.audio_loop is not None:
            self.audio_loop.start()

    def on_exit(self) -> None:
        """Called when leaving state."""
        if self.audio_loop is not None:
            self.audio_loop.stop()

    def handle_event(self, event) -> None:
        """Handle input."""
        result = self.menu.handle_input(event)
        if result is not None:
            if result == 0:
                print("Starting new game...")
            elif result == 1:
                print("Loading game...")
            elif result == 2:
                print("Opening settings...")
            elif result == 3 and PYGAME_AVAILABLE:
                pygame.event.post(pygame.event.Event(pygame.QUIT))

    def update(self, delta_time: float) -> None:
        """Update logic."""
        if PYGAME_AVAILABLE:
            if self.audio_loop is not None:
                self.audio_loop.update(delta_time)
            self.menu.update(pygame.mouse.get_pos(), delta_time)
            if self.background:
                self.background.update(delta_time)

    def render(self, screen) -> None:
        """Render to screen."""
        if not PYGAME_AVAILABLE:
            return

        screen_width, screen_height = screen.get_size()
        self._layout_for_size(screen_width, screen_height)
        if self.background and (self.background.width != screen_width or self.background.height != screen_height):
            self.background = AnimatedBackground(screen_width, screen_height)
        if self.background:
            self.background.set_avoid_regions([])

        if self.background:
            self.background.draw(screen)
        else:
            screen.fill(COLOR_BLACK)

        if self.title_font:
            title_center = (screen_width // 2, screen_height // 6)

            shadow = self._render_spaced_text(self.title_font, "CELESTIAL CROWN", (42, 24, 12), tracking=1)
            shadow_rect = shadow.get_rect(center=(title_center[0] + 3, title_center[1] + 5))
            screen.blit(shadow, shadow_rect)

            for ox, oy in [(-2, 0), (2, 0), (0, -2), (0, 2), (-2, -2), (2, 2), (-2, 2), (2, -2)]:
                outline = self._render_spaced_text(self.title_font, "CELESTIAL CROWN", (88, 52, 24), tracking=1)
                outline_rect = outline.get_rect(center=(title_center[0] + ox, title_center[1] + oy))
                screen.blit(outline, outline_rect)

            title_main = self._render_spaced_text(self.title_font, "CELESTIAL CROWN", (224, 188, 108), tracking=1)
            title_highlight = self._render_spaced_text(
                self.title_font,
                "CELESTIAL CROWN",
                (255, 236, 186),
                tracking=1,
            )
            title_rect = title_main.get_rect(center=title_center)
            highlight_rect = title_highlight.get_rect(center=(title_center[0], title_center[1] - 2))
            screen.blit(title_main, title_rect)
            screen.blit(title_highlight, highlight_rect)

            if self.title_sub_font:
                subtitle_shadow = self._render_spaced_text(
                    self.title_sub_font,
                    "Chronicles of the Fallen Star",
                    (18, 12, 8),
                    tracking=1,
                )
                subtitle = self._render_spaced_text(
                    self.title_sub_font,
                    "Chronicles of the Fallen Star",
                    (240, 216, 164),
                    tracking=1,
                )
                subtitle_rect = subtitle.get_rect(center=(screen_width // 2, title_center[1] + 82))

                subtitle_plate = pygame.Surface((subtitle_rect.width + 40, subtitle_rect.height + 14), pygame.SRCALPHA)
                pygame.draw.rect(subtitle_plate, (10, 12, 24, 128), subtitle_plate.get_rect(), border_radius=10)
                pygame.draw.rect(subtitle_plate, (198, 168, 118, 72), subtitle_plate.get_rect(), 1, border_radius=10)
                screen.blit(subtitle_plate, subtitle_plate.get_rect(center=subtitle_rect.center))

                shadow_rect = subtitle_shadow.get_rect(center=(subtitle_rect.centerx + 1, subtitle_rect.centery + 2))
                screen.blit(subtitle_shadow, shadow_rect)
                screen.blit(subtitle, subtitle_rect)

                line_y = subtitle_rect.bottom + 14
                left_start = screen_width // 2 - 290
                left_end = screen_width // 2 - 80
                right_start = screen_width // 2 + 80
                right_end = screen_width // 2 + 290
                pygame.draw.line(screen, (130, 102, 65), (left_start, line_y), (left_end, line_y), 2)
                pygame.draw.line(screen, (130, 102, 65), (right_start, line_y), (right_end, line_y), 2)
                pygame.draw.circle(screen, (210, 176, 110), (screen_width // 2, line_y), 4)

        if self.menu.buttons:
            first = self.menu.buttons[0].rect
            last = self.menu.buttons[-1].rect
            last_bottom = last.y + last.height
            panel_rect = pygame.Rect(first.x - 58, first.y - 34, first.width + 116, (last_bottom - first.y) + 70)
            panel = pygame.Surface((panel_rect.width, panel_rect.height), pygame.SRCALPHA)
            pygame.draw.rect(panel, (14, 20, 34, 92), panel.get_rect(), border_radius=18)
            pygame.draw.rect(panel, (184, 208, 230, 46), panel.get_rect(), 1, border_radius=18)
            screen.blit(panel, panel_rect)

        self.menu.draw(screen)

        if self.font:
            version_shadow = self.font.render("v0.1.0 - Framework Edition", True, (20, 20, 36))
            version_text = self.font.render("v0.1.0 - Framework Edition", True, (178, 178, 250))
            screen.blit(version_shadow, (32, screen_height - 48))
            screen.blit(version_text, (30, screen_height - 50))

            hint_shadow = self.font.render(
                "↑/↓ or Xbox D-Pad/Stick  |  Enter/Start/A Select",
                True,
                (18, 30, 32),
            )
            hint_text = self.font.render(
                "↑/↓ or Xbox D-Pad/Stick  |  Enter/Start/A Select",
                True,
                (140, 226, 226),
            )
            hint_rect = hint_text.get_rect(center=(screen_width // 2, screen_height - 50))
            hint_shadow_rect = hint_shadow.get_rect(center=(screen_width // 2 + 1, screen_height - 48))
            screen.blit(hint_shadow, hint_shadow_rect)
            screen.blit(hint_text, hint_rect)

        if self.credit_font:
            credit_text = "Created by William E. Smith, 2026"
            credit_shadow = self.credit_font.render(credit_text, True, (14, 16, 26))
            credit_main = self.credit_font.render(credit_text, True, (206, 196, 170))
            credit_glow = self.credit_font.render(credit_text, True, (248, 236, 206))

            credit_rect = credit_main.get_rect(bottomright=(screen_width - 30, screen_height - 30))
            plate = pygame.Surface((credit_rect.width + 28, credit_rect.height + 14), pygame.SRCALPHA)
            pygame.draw.rect(plate, (10, 14, 24, 92), plate.get_rect(), border_radius=10)
            pygame.draw.rect(plate, (188, 168, 128, 48), plate.get_rect(), 1, border_radius=10)
            screen.blit(plate, plate.get_rect(center=credit_rect.center))

            screen.blit(credit_shadow, (credit_rect.x + 1, credit_rect.y + 2))
            screen.blit(credit_main, credit_rect)
            screen.blit(credit_glow, (credit_rect.x, credit_rect.y - 1))
