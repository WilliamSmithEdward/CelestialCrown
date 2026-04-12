"""Squad management state for composition, roles, and tactics."""

from __future__ import annotations

from ._shared import PYGAME_AVAILABLE, pygame
from ..config import COLOR_BLACK, COLOR_WHITE
from ..core.campaign import CampaignSession
from ..core.gamestate import GameState, StateType


class SquadManagementState(GameState):
    """Manage squad plans between missions."""

    def __init__(self, session: CampaignSession):
        super().__init__()
        self.state_type = StateType.INVENTORY
        self.session = session
        self.selected_squad_index = 0
        self.selected_unit_index = 0
        self.status_message = "Arrows: navigate | M: move unit | R: role | T: tactic | ESC: return"

        if PYGAME_AVAILABLE:
            self.title_font = pygame.font.Font(None, 56)
            self.body_font = pygame.font.Font(None, 32)
            self.small_font = pygame.font.Font(None, 26)
        else:
            self.title_font = None
            self.body_font = None
            self.small_font = None

    def on_enter(self) -> None:
        self.session._sync_squad_plans()

    def on_exit(self) -> None:
        pass

    def _clamp_indices(self) -> None:
        plans = self.session.squad_plans
        if not plans:
            self.selected_squad_index = 0
            self.selected_unit_index = 0
            return

        self.selected_squad_index = max(0, min(self.selected_squad_index, len(plans) - 1))
        unit_count = len(plans[self.selected_squad_index].unit_ids)
        if unit_count == 0:
            self.selected_unit_index = 0
        else:
            self.selected_unit_index = max(0, min(self.selected_unit_index, unit_count - 1))

    def _selected_unit_id(self) -> str | None:
        plans = self.session.squad_plans
        if not plans:
            return None
        plan = plans[self.selected_squad_index]
        if not plan.unit_ids:
            return None
        return plan.unit_ids[self.selected_unit_index]

    def handle_event(self, event) -> None:
        if not PYGAME_AVAILABLE:
            return

        if event.type != pygame.KEYDOWN:
            return

        plans = self.session.squad_plans
        if event.key == pygame.K_ESCAPE:
            from .town import TownState

            if self.engine is not None:
                self.engine.change_state(TownState(session=self.session, status_message="Squad plans updated."))
            return

        if not plans:
            return

        if event.key == pygame.K_LEFT:
            self.selected_squad_index = (self.selected_squad_index - 1) % len(plans)
            self.selected_unit_index = 0
        elif event.key == pygame.K_RIGHT:
            self.selected_squad_index = (self.selected_squad_index + 1) % len(plans)
            self.selected_unit_index = 0
        elif event.key == pygame.K_UP:
            plan = plans[self.selected_squad_index]
            if plan.unit_ids:
                self.selected_unit_index = (self.selected_unit_index - 1) % len(plan.unit_ids)
        elif event.key == pygame.K_DOWN:
            plan = plans[self.selected_squad_index]
            if plan.unit_ids:
                self.selected_unit_index = (self.selected_unit_index + 1) % len(plan.unit_ids)
        elif event.key == pygame.K_r:
            plan = plans[self.selected_squad_index]
            self.session.cycle_squad_role(plan.id)
            self.status_message = f"{plan.name} role set to {plan.role.value}."
        elif event.key == pygame.K_t:
            plan = plans[self.selected_squad_index]
            self.session.cycle_squad_tactic(plan.id)
            self.status_message = f"{plan.name} tactic set to {plan.tactic.value}."
        elif event.key == pygame.K_m:
            unit_id = self._selected_unit_id()
            if unit_id is not None and len(plans) > 1:
                target_idx = (self.selected_squad_index + 1) % len(plans)
                if self.session.move_unit_to_plan(unit_id, target_idx):
                    self.status_message = f"Moved {unit_id} to {plans[target_idx].name}."
                else:
                    self.status_message = "Move not possible (would empty source squad)."

        self._clamp_indices()

    def update(self, delta_time: float) -> None:
        self._clamp_indices()

    def render(self, screen) -> None:
        if not PYGAME_AVAILABLE:
            return

        screen.fill(COLOR_BLACK)
        width, height = screen.get_size()

        if self.title_font is None or self.body_font is None or self.small_font is None:
            return

        title = self.title_font.render("Squad Management", True, (232, 204, 144))
        screen.blit(title, (40, 30))

        plans = self.session.squad_plans
        if not plans:
            empty = self.body_font.render("No squad plans available.", True, COLOR_WHITE)
            screen.blit(empty, (40, 120))
            return

        panel_width = max(320, (width - 80) // max(1, len(plans)))
        base_y = 130

        for idx, plan in enumerate(plans):
            x = 40 + idx * panel_width
            panel_rect = pygame.Rect(x, base_y, panel_width - 18, height - 250)
            selected = idx == self.selected_squad_index
            bg_color = (34, 42, 58) if selected else (24, 28, 36)
            edge_color = (220, 188, 120) if selected else (96, 104, 118)

            pygame.draw.rect(screen, bg_color, panel_rect, border_radius=10)
            pygame.draw.rect(screen, edge_color, panel_rect, 2, border_radius=10)

            name_text = self.body_font.render(plan.name, True, COLOR_WHITE)
            role_text = self.small_font.render(f"Role: {plan.role.value.title()}", True, (176, 220, 240))
            tactic_text = self.small_font.render(f"Tactic: {plan.tactic.value.title()}", True, (204, 214, 148))
            screen.blit(name_text, (x + 14, base_y + 12))
            screen.blit(role_text, (x + 14, base_y + 52))
            screen.blit(tactic_text, (x + 14, base_y + 78))

            y = base_y + 122
            if not plan.unit_ids:
                empty = self.small_font.render("(No units assigned)", True, (168, 168, 168))
                screen.blit(empty, (x + 14, y))
                continue

            for unit_idx, unit_id in enumerate(plan.unit_ids):
                unit = next((member for member in self.session.party if member.id == unit_id), None)
                if unit is None:
                    continue

                is_selected_unit = selected and unit_idx == self.selected_unit_index
                line_color = (255, 240, 170) if is_selected_unit else (222, 226, 230)
                line = self.small_font.render(
                    f"{unit.name} ({unit.unit_class.value.title()}) Lv {unit.level}",
                    True,
                    line_color,
                )
                screen.blit(line, (x + 14, y))
                y += 30

        footer = self.small_font.render(self.status_message, True, (220, 210, 150))
        help_line = self.small_font.render(
            "LEFT/RIGHT squad | UP/DOWN unit | R role | T tactic | M move selected unit | ESC back",
            True,
            (166, 188, 216),
        )
        screen.blit(footer, (40, height - 78))
        screen.blit(help_line, (40, height - 48))
