"""Battle state implementation."""

from __future__ import annotations

from ._shared import PYGAME_AVAILABLE, pygame
from ..config import COLOR_BLACK, COLOR_WHITE
from ..core.campaign import CampaignSession
from ..core.gamestate import GameState, StateType
from ..ui import Menu


class BattleState(GameState):
    """Tactical battle state."""

    def __init__(self, session: CampaignSession | None = None):
        super().__init__()
        self.state_type = StateType.BATTLE
        self.session = session or CampaignSession.new_game()
        self.menu = None
        self.result_message = ""

        if PYGAME_AVAILABLE:
            self.title_font = pygame.font.Font(None, 64)
            self.body_font = pygame.font.Font(None, 34)
            self.small_font = pygame.font.Font(None, 28)
            self.menu = Menu(
                "Battle Command",
                ["Auto Resolve Battle", "Retreat to Town"],
                x=0,
                y=0,
                show_title=False,
                title_padding=0,
            )
            self.menu.button_width = 340
            self.menu.button_height = 68
            self.menu.button_spacing = 82
            for button in self.menu.buttons:
                button.width = 340
                button.height = 68
                button.rect.width = 340
                button.rect.height = 68
        else:
            self.title_font = None
            self.body_font = None
            self.small_font = None

    def _layout_menu(self, width: int) -> None:
        if self.menu is None:
            return
        self.menu.set_position(width - 400, 360)

    def on_enter(self) -> None:
        pass

    def on_exit(self) -> None:
        pass

    def handle_event(self, event) -> None:
        if not PYGAME_AVAILABLE or self.menu is None:
            return

        result = self.menu.handle_input(event)
        if result is None:
            return

        from .town import TownState

        if result == 0:
            report = self.session.resolve_current_battle()
            if report.victory:
                self.result_message = (
                    f"Victory in {report.rounds} rounds. +{report.funds_reward}g, +{report.exp_reward} EXP"
                )
            else:
                self.result_message = (
                    f"Defeat after {report.rounds} rounds. Lost {report.party_losses} units."
                )

            if self.engine is not None:
                self.engine.change_state(TownState(session=self.session, status_message=self.result_message))
        elif result == 1:
            if self.engine is not None:
                self.engine.change_state(TownState(session=self.session, status_message="Retreated to town."))

    def update(self, delta_time: float) -> None:
        if PYGAME_AVAILABLE and self.menu is not None:
            self.menu.update(pygame.mouse.get_pos(), delta_time)

    def render(self, screen) -> None:
        if not PYGAME_AVAILABLE:
            return

        width, height = screen.get_size()
        screen.fill(COLOR_BLACK)
        self._layout_menu(width)

        if self.title_font is not None:
            title = self.title_font.render("Battlefront", True, (236, 196, 120))
            screen.blit(title, (60, 40))

        if self.body_font is not None:
            chapter_line = f"Chapter {self.session.chapter} - Skirmish {self.session.battle_index}/3"
            chapter_text = self.body_font.render(chapter_line, True, COLOR_WHITE)
            screen.blit(chapter_text, (60, 118))

            enemy_count = min(2 + self.session.chapter, 6)
            level_estimate = min(1 + self.session.chapter + (self.session.battle_index // 2), 12)
            details = [
                f"Party Units: {len(self.session.party)}",
                f"Expected Enemy Units: {enemy_count}",
                f"Expected Enemy Level: {level_estimate}",
                "Combat uses turn order by agility and hit/crit formulas.",
                "Victory grants funds and experience; defeat can cost morale and units.",
            ]

            y = 176
            for line in details:
                line_surf = self.small_font.render(line, True, (194, 220, 235))
                screen.blit(line_surf, (70, y))
                y += 36

            if self.result_message:
                msg = self.small_font.render(self.result_message, True, (236, 216, 136))
                screen.blit(msg, (60, height - 60))

        if self.menu is not None:
            self.menu.draw(screen)
