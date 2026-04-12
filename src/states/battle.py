"""Real-time strategic battle map state."""

from __future__ import annotations

import math
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

    @staticmethod
    def _segment_intersection(p1, p2, p3, p4):
        """Return the intersection point of segments p1→p2 and p3→p4, or None."""
        x1, y1 = p1; x2, y2 = p2; x3, y3 = p3; x4, y4 = p4
        denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(denom) < 1e-9:
            return None
        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
        u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom
        if 0.0 <= t <= 1.0 and 0.0 <= u <= 1.0:
            return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))
        return None

    @staticmethod
    def _point_seg_dist(px: float, py: float, ax: float, ay: float, bx: float, by: float) -> float:
        """Minimum distance from point to segment."""
        dx, dy = bx - ax, by - ay
        seg_sq = dx * dx + dy * dy
        if seg_sq < 1e-10:
            return math.hypot(px - ax, py - ay)
        t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / seg_sq))
        return math.hypot(px - (ax + t * dx), py - (ay + t * dy))

    def _render_threat_overlays(self, screen) -> None:
        """Pulsing danger aura behind any site currently targeted by an enemy squad."""
        pulse = int(50 + 28 * math.sin(self.mission.time_elapsed * 2.8))
        enemy_targets = {
            s.target_site_id
            for s in self.mission.squads
            if s.owner == 1 and not s.is_destroyed() and s.target_site_id
        }
        for site_id in enemy_targets:
            site = self.mission.sites.get(site_id)
            if site is None:
                continue
            r = 38
            surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (220, 55, 55, pulse), (r, r), r)
            screen.blit(surf, (int(site.x) - r, int(site.y) - r))

    def _render_intercept_forecast(self, screen) -> None:
        """Yellow warning diamonds where a player and enemy squad path are forecast to cross."""
        p_squads = [s for s in self.mission.squads if s.owner == 0 and not s.is_destroyed() and s.target_site_id]
        e_squads = [s for s in self.mission.squads if s.owner == 1 and not s.is_destroyed() and s.target_site_id]
        drawn: set = set()
        for ps in p_squads:
            ps_target = ps.target_site_id
            if ps_target is None:
                continue
            pt = self.mission.sites.get(ps_target)
            if pt is None:
                continue
            for es in e_squads:
                es_target = es.target_site_id
                if es_target is None:
                    continue
                et = self.mission.sites.get(es_target)
                if et is None:
                    continue
                result = self._segment_intersection(
                    (ps.x, ps.y), (pt.x, pt.y),
                    (es.x, es.y), (et.x, et.y),
                )
                if result is None:
                    continue
                ix, iy = int(result[0]), int(result[1])
                key = (ix // 24, iy // 24)
                if key in drawn:
                    continue
                drawn.add(key)
                size = 8
                pts = [(ix, iy - size), (ix + size, iy), (ix, iy + size), (ix - size, iy)]
                pygame.draw.polygon(screen, (255, 210, 50), pts)
                pygame.draw.polygon(screen, (180, 130, 10), pts, 1)

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

        hot_lanes: set = set()
        for squad in self.mission.squads:
            if squad.owner != 1 or squad.is_destroyed() or squad.target_site_id is None:
                continue
            for a_id, b_id in lane_pairs:
                if squad.target_site_id not in (a_id, b_id):
                    continue
                sa = self.mission.sites[a_id]
                sb = self.mission.sites[b_id]
                if self._point_seg_dist(squad.x, squad.y, sa.x, sa.y, sb.x, sb.y) < 80:
                    hot_lanes.add((a_id, b_id))

        for a_id, b_id in lane_pairs:
            a = self.mission.sites[a_id]
            b = self.mission.sites[b_id]
            lane_color = (155, 64, 58) if (a_id, b_id) in hot_lanes else (58, 70, 88)
            pygame.draw.line(screen, lane_color, (int(a.x), int(a.y)), (int(b.x), int(b.y)), 2)

        self._render_threat_overlays(screen)

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

        self._render_intercept_forecast(screen)

        if self.title_font is not None:
            title = self.title_font.render("Strategic Battlefield", True, (233, 206, 146))
            screen.blit(title, (28, 20))

        if self.body_font is not None and self.small_font is not None:
            pressure = self.mission.pressure_index
            hud_color = (255, 100, 80) if pressure > 5 else (255, 200, 90) if pressure > 0 else (140, 225, 140)
            line1 = self.body_font.render(
                f"Chapter {self.session.chapter} | Income {self.mission.player_income} | Pressure {pressure:.1f}",
                True,
                hud_color,
            )
            line2 = self.small_font.render(self.status_message, True, (222, 214, 154))
            line3 = self.small_font.render("TAB: cycle squad | 1-6: order to site | R: recall | SPACE: pause | ESC: withdraw", True, (164, 184, 214))
            screen.blit(line1, (28, height - 86))
            screen.blit(line2, (28, height - 56))
            screen.blit(line3, (28, height - 30))
