"""Town state implementation."""

from __future__ import annotations

from ._shared import PYGAME_AVAILABLE, pygame
from ..config import COLOR_BLACK, COLOR_WHITE
from ..core.campaign import CampaignSession
from ..core.gamestate import GameState, StateType
from ..ui import Menu


class TownState(GameState):
    """Town/base management state."""

    def __init__(self, session: CampaignSession | None = None, status_message: str = ""):
        super().__init__()
        self.state_type = StateType.TOWN
        self.session = session or CampaignSession.new_game()
        self.status_message = status_message
        self.menu = None

        if PYGAME_AVAILABLE:
            self.title_font = pygame.font.Font(None, 62)
            self.body_font = pygame.font.Font(None, 34)
            self.small_font = pygame.font.Font(None, 28)
            self.menu = Menu(
                "Town Command",
                [
                    "Deploy to Strategic Map",
                    "Manage Squads",
                    "Recruit Unit (1200g)",
                    "Upgrade Facility (1500g)",
                    "Rest Party",
                    "Return to Main Menu",
                ],
                x=0,
                y=0,
                show_title=False,
                title_padding=0,
            )
            self.menu.button_width = 360
            self.menu.button_height = 64
            self.menu.button_spacing = 74
            for button in self.menu.buttons:
                button.rect.width = 360
                button.rect.height = 64
        else:
            self.title_font = None
            self.body_font = None
            self.small_font = None

    def _layout_menu(self, width: int, height: int) -> None:
        if self.menu is None:
            return
        menu_x = width - 430
        menu_y = 280
        self.menu.set_position(menu_x, menu_y)

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

        if result == 0:
            from .battle import BattleState

            if self.engine is not None:
                self.engine.change_state(BattleState(session=self.session))
        elif result == 1:
            from .squad_management import SquadManagementState

            if self.engine is not None:
                self.engine.change_state(SquadManagementState(session=self.session))
        elif result == 2:
            if self.session.recruit_unit():
                self.status_message = "A new mercenary joined your banner."
            else:
                self.status_message = "Not enough funds to recruit."
        elif result == 3:
            upgraded = False
            for facility in self.session.town.facilities.values():
                if facility.level < 5 and self.session.town.spend_funds(1500):
                    upgraded = facility.upgrade()
                    break
            self.status_message = "Facility upgraded." if upgraded else "Cannot upgrade any facility right now."
        elif result == 4:
            self.session.rest_party()
            self.status_message = "Party fully rested."
        elif result == 5:
            from .main_menu import MainMenuState

            if self.engine is not None:
                self.engine.change_state(MainMenuState())

    def update(self, delta_time: float) -> None:
        if PYGAME_AVAILABLE and self.menu is not None:
            self.menu.update(pygame.mouse.get_pos(), delta_time)

    def render(self, screen) -> None:
        if not PYGAME_AVAILABLE:
            return

        width, height = screen.get_size()
        screen.fill(COLOR_BLACK)
        self._layout_menu(width, height)

        if self.title_font is not None:
            title = self.title_font.render("Asterhold Command", True, (233, 213, 170))
            screen.blit(title, (60, 40))

        if self.body_font is not None and self.small_font is not None:
            if self.session.game_over:
                final_text = "Campaign Complete" if self.session.victory else "Campaign Defeat"
                final_color = (128, 226, 148) if self.session.victory else (230, 112, 112)
                done = self.body_font.render(final_text, True, final_color)
                screen.blit(done, (60, 98))

            summary_lines = [
                f"Chapter: {self.session.chapter}/{self.session.max_chapters}",
                f"Battle: {self.session.battle_index}/3",
                f"Day: {self.session.day}",
                f"Funds: {self.session.town.funds}g",
                f"Morale: {self.session.town.morale}",
                f"Population: {self.session.town.population}",
                f"Party Size: {len(self.session.party)}",
            ]

            line_y = 150
            for line in summary_lines:
                surf = self.body_font.render(line, True, COLOR_WHITE)
                screen.blit(surf, (60, line_y))
                line_y += 42

            section = self.body_font.render("Facilities", True, (218, 188, 128))
            screen.blit(section, (60, line_y + 6))
            line_y += 46

            for facility in self.session.town.facilities.values():
                f_line = f"{facility.name} - Lv {facility.level}"
                surf = self.small_font.render(f_line, True, (184, 210, 232))
                screen.blit(surf, (70, line_y))
                line_y += 30

            section = self.body_font.render("Party", True, (218, 188, 128))
            screen.blit(section, (60, line_y + 8))
            line_y += 50

            for unit in self.session.party:
                hp = f"{unit.current_hp}/{unit.stats.hp}"
                info = f"{unit.name} ({unit.unit_class.value.title()}) Lv {unit.level} HP {hp}"
                surf = self.small_font.render(info, True, (214, 224, 200))
                screen.blit(surf, (70, line_y))
                line_y += 30

            if self.session.last_report is not None:
                report = self.session.last_report
                outcome = "Victory" if report.victory else "Defeat"
                report_text = (
                    f"Last Battle: {outcome} | Rounds {report.rounds} | "
                    f"Enemy Losses {report.enemies_defeated} | Party Losses {report.party_losses}"
                )
                surf = self.small_font.render(report_text, True, (160, 190, 210))
                screen.blit(surf, (60, height - 84))

            if self.status_message:
                status_surf = self.small_font.render(self.status_message, True, (236, 216, 136))
                screen.blit(status_surf, (60, height - 48))

        if self.menu is not None:
            self.menu.draw(screen)
