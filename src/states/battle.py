"""Real-time strategic battle map state."""

from __future__ import annotations

import random
from typing import List

from ._shared import PYGAME_AVAILABLE, pygame
from ..config import COLOR_BLACK, COLOR_WHITE
from ..core.campaign import CampaignSession
from ..core.gamestate import GameState, StateType


class BattleState(GameState):
    """Squad-based strategic map with auto-resolved engagements."""

    def __init__(self, session: CampaignSession | None = None):
        super().__init__()
        self.state_type = StateType.BATTLE
        self.session = session or CampaignSession.new_game()
        self.mission = self.session.create_strategic_mission()
        self.selected_index = 0
        self.paused = False
        self.enemy_order_timer = 0.0
        self.status_message = "Assign squads with 1-6. TAB selects squad. SPACE pauses."

        if PYGAME_AVAILABLE:
            self.title_font = pygame.font.Font(None, 58)
            self.body_font = pygame.font.Font(None, 30)
            self.small_font = pygame.font.Font(None, 24)
        else:
            self.title_font = None
            self.body_font = None
            self.small_font = None

    def on_enter(self) -> None:
        pass

    def on_exit(self) -> None:
        pass

    def _player_squads(self):
        return self.mission.allied_squads(0)

    def _selected_squad(self):
        squads = self._player_squads()
        if not squads:
            return None
        self.selected_index %= len(squads)
        return squads[self.selected_index]

    def _site_order(self) -> List[str]:
        return list(self.mission.sites.keys())

    def _issue_enemy_orders(self) -> None:
        player_sites = [site.id for site in self.mission.sites.values() if site.owner == 0]
        fallback = ["center_fort", "west_town", "player_base"]

        for squad in self.mission.allied_squads(1):
            if squad.target_site_id is None or random.random() < 0.35:
                targets = player_sites if player_sites else fallback
                self.mission.issue_order(squad.id, random.choice(targets))

    def _return_to_town(self, result: str, message: str, apply_outcome: bool) -> None:
        from .town import TownState

        if apply_outcome:
            report = self.session.apply_mission_outcome(result, income_bonus=self.mission.player_income)
            if report.victory:
                message = f"Mission won. +{report.funds_reward}g and +{report.exp_reward} EXP."
            else:
                message = f"Mission lost. {report.party_losses} party losses."

        if self.engine is not None:
            self.engine.change_state(TownState(session=self.session, status_message=message))

    def handle_event(self, event) -> None:
        if not PYGAME_AVAILABLE:
            return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                self.paused = not self.paused
                self.status_message = "Simulation paused." if self.paused else "Simulation resumed."
                return

            if event.key == pygame.K_TAB:
                squads = self._player_squads()
                if squads:
                    self.selected_index = (self.selected_index + 1) % len(squads)
                    selected = squads[self.selected_index]
                    self.status_message = f"Selected {selected.name}."
                return

            if event.key == pygame.K_r:
                selected = self._selected_squad()
                if selected and self.mission.recall_squad(selected.id, owner=0):
                    self.status_message = f"{selected.name} recalling to allied stronghold."
                return

            if event.key == pygame.K_ESCAPE:
                self._return_to_town(result="defeat", message="Withdrew from battlefield.", apply_outcome=False)
                return

            selected = self._selected_squad()
            if selected is None:
                return

            site_ids = self._site_order()
            key_map = {
                pygame.K_1: 0,
                pygame.K_2: 1,
                pygame.K_3: 2,
                pygame.K_4: 3,
                pygame.K_5: 4,
                pygame.K_6: 5,
            }
            if event.key in key_map:
                idx = key_map[event.key]
                if 0 <= idx < len(site_ids):
                    site_id = site_ids[idx]
                    if self.mission.issue_order(selected.id, site_id):
                        site_name = self.mission.sites[site_id].name
                        self.status_message = f"{selected.name} ordered to {site_name}."

    def update(self, delta_time: float) -> None:
        if self.paused:
            return

        self.enemy_order_timer += delta_time
        if self.enemy_order_timer >= 2.0:
            self.enemy_order_timer = 0.0
            self._issue_enemy_orders()

        self.mission.update(delta_time)

        if self.mission.last_engagement is not None:
            report = self.mission.last_engagement
            self.status_message = (
                f"Engagement {report.squad_a_id} vs {report.squad_b_id} | "
                f"Losses {report.losses_a}-{report.losses_b}"
            )

        complete, result = self.mission.is_complete()
        if complete:
            self._return_to_town(result=result, message="Mission complete.", apply_outcome=True)

    def render(self, screen) -> None:
        if not PYGAME_AVAILABLE:
            return

        width, height = screen.get_size()
        screen.fill(COLOR_BLACK)

        lane_pairs = [
            ("player_base", "west_town"),
            ("west_town", "center_fort"),
            ("center_fort", "east_temple"),
            ("east_temple", "enemy_base"),
            ("center_fort", "ore_field"),
            ("ore_field", "enemy_base"),
        ]

        for a_id, b_id in lane_pairs:
            a = self.mission.sites[a_id]
            b = self.mission.sites[b_id]
            pygame.draw.line(screen, (58, 70, 88), (int(a.x), int(a.y)), (int(b.x), int(b.y)), 2)

        site_ids = self._site_order()
        for idx, site_id in enumerate(site_ids):
            site = self.mission.sites[site_id]
            if site.owner == 0:
                color = (100, 190, 255)
            elif site.owner == 1:
                color = (220, 96, 96)
            else:
                color = (174, 174, 174)

            pygame.draw.circle(screen, color, (int(site.x), int(site.y)), 22)
            pygame.draw.circle(screen, (15, 18, 24), (int(site.x), int(site.y)), 22, 2)

            if self.small_font is not None:
                label = self.small_font.render(f"{idx + 1}:{site.name}", True, COLOR_WHITE)
                screen.blit(label, (int(site.x) - 45, int(site.y) - 44))

        selected = self._selected_squad()
        for squad in self.mission.squads:
            if squad.is_destroyed():
                continue

            squad_color = (96, 210, 122) if squad.owner == 0 else (236, 118, 118)
            pygame.draw.circle(screen, squad_color, (int(squad.x), int(squad.y)), 11)

            if selected is not None and squad.id == selected.id:
                pygame.draw.circle(screen, (248, 238, 142), (int(squad.x), int(squad.y)), 16, 2)

            if squad.target_site_id and squad.target_site_id in self.mission.sites:
                target = self.mission.sites[squad.target_site_id]
                pygame.draw.line(
                    screen,
                    (82, 122, 160) if squad.owner == 0 else (160, 82, 82),
                    (int(squad.x), int(squad.y)),
                    (int(target.x), int(target.y)),
                    1,
                )

        if self.title_font is not None:
            title = self.title_font.render("Strategic Battlefield", True, (233, 206, 146))
            screen.blit(title, (28, 20))

        if self.body_font is not None and self.small_font is not None:
            line1 = self.body_font.render(
                f"Chapter {self.session.chapter} | Mission Income {self.mission.player_income} | Pressure {self.mission.pressure_index:.1f}",
                True,
                COLOR_WHITE,
            )
            line2 = self.small_font.render(self.status_message, True, (222, 214, 154))
            line3 = self.small_font.render("TAB: cycle squad | 1-6: order to site | R: recall | SPACE: pause | ESC: withdraw", True, (164, 184, 214))
            screen.blit(line1, (28, height - 86))
            screen.blit(line2, (28, height - 56))
            screen.blit(line3, (28, height - 30))
