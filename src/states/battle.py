"""Real-time strategic battle map state."""

from __future__ import annotations

import math
import random
from typing import List, Optional

from ._shared import PYGAME_AVAILABLE, pygame
from ..config import COLOR_BLACK, COLOR_WHITE
from ..core.campaign import CampaignSession
from ..core.gamestate import GameState, StateType


class BattleState(GameState):
    """Squad-based strategic map with terrain background, ISO building sprites, and squad tokens."""

    _SCENARIO_ID = "ch1_asterhold_gate"

    def __init__(self, session: CampaignSession | None = None):
        super().__init__()
        self.state_type = StateType.BATTLE
        self.session = session or CampaignSession.new_game()

        from ..strategy.mission_loader import load_mission
        self.mission = load_mission(self._SCENARIO_ID, chapter=self.session.chapter)
        # Inject player squads from session squad plans; keep only enemy squads from config
        player_squads = self.session.build_player_squads()
        # Position player squads near the player base site with staggered offsets
        base_site = self.mission.sites.get("player_base")
        base_x = base_site.x if base_site else 120.0
        base_y = base_site.y if base_site else 360.0
        for i, sq in enumerate(player_squads):
            sq.x = base_x + 55.0
            sq.y = base_y + (i - (len(player_squads) - 1) / 2.0) * 32.0
        self.mission.squads = player_squads + [s for s in self.mission.squads if s.owner != 0]

        self.selected_index = 0
        self.paused = False
        self.enemy_order_timer = 0.0
        self.status_message = "Assign squads with 1-6. TAB selects squad. SPACE pauses."

        self._map_renderer = None
        self._sprites = None
        self._map_cfg: Optional[dict] = None

        if PYGAME_AVAILABLE:
            self.title_font  = pygame.font.Font(None, 42)
            self.body_font   = pygame.font.Font(None, 28)
            self.small_font  = pygame.font.Font(None, 22)
            self.digit_font  = pygame.font.Font(None, 36)
        else:
            self.title_font = self.body_font = self.small_font = self.digit_font = None

    # ------------------------------------------------------------------
    # Lazy resource init
    # ------------------------------------------------------------------

    def _ensure_resources(self, screen) -> None:
        if self._sprites is not None:
            return

        import json, pathlib
        from ..strategy.map_def import MapDef
        from ..strategy.map_renderer import MapRenderer
        from ..strategy.sprite_registry import SpriteRegistry

        self._sprites = SpriteRegistry(pygame)

        cfg_path = (pathlib.Path(__file__).parent.parent.parent
                    / "data" / "scenarios" / f"{self._SCENARIO_ID}.json")
        if cfg_path.exists():
            with cfg_path.open(encoding="utf-8") as f:
                data = json.load(f)
            map_section = data.get("map", {})
        else:
            map_section = {}

        sw, sh = screen.get_size()
        map_section.setdefault("width", sw)
        map_section.setdefault("height", sh)

        map_def = MapDef.from_dict(map_section)
        self._map_renderer = MapRenderer(map_def, pygame)
        self._map_renderer.bake()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

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
            message = (f"Mission won. +{report.funds_reward}g and +{report.exp_reward} EXP."
                       if report.victory
                       else f"Mission lost. {report.party_losses} party losses.")
        if self.engine is not None:
            self.engine.change_state(TownState(session=self.session, status_message=message))

    # ------------------------------------------------------------------
    # GameState interface
    # ------------------------------------------------------------------

    def on_enter(self) -> None: pass
    def on_exit(self) -> None: pass

    def handle_event(self, event) -> None:
        if not PYGAME_AVAILABLE:
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                self.paused = not self.paused
                self.status_message = "Paused." if self.paused else "Resumed."
                return

            if event.key == pygame.K_TAB:
                squads = self._player_squads()
                if squads:
                    self.selected_index = (self.selected_index + 1) % len(squads)
                    self.status_message = f"Selected {squads[self.selected_index].name}."
                return

            if event.key == pygame.K_r:
                sel = self._selected_squad()
                if sel and self.mission.recall_squad(sel.id, owner=0):
                    self.status_message = f"{sel.name} recalling."
                return

            if event.key == pygame.K_ESCAPE:
                self._return_to_town("defeat", "Withdrew from battlefield.", False)
                return

            sel = self._selected_squad()
            if sel is None:
                return
            site_ids = self._site_order()
            key_map = {
                pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2,
                pygame.K_4: 3, pygame.K_5: 4, pygame.K_6: 5,
            }
            if event.key in key_map:
                idx = key_map[event.key]
                if 0 <= idx < len(site_ids):
                    site_id = site_ids[idx]
                    if self.mission.issue_order(sel.id, site_id):
                        self.status_message = f"{sel.name} to {self.mission.sites[site_id].name}."

    def update(self, delta_time: float) -> None:
        if self.paused:
            return
        self.enemy_order_timer += delta_time
        if self.enemy_order_timer >= 2.0:
            self.enemy_order_timer = 0.0
            self._issue_enemy_orders()
        self.mission.update(delta_time)
        if self.mission.last_engagement is not None:
            r = self.mission.last_engagement
            self.status_message = (f"Clash: {r.squad_a_id} vs {r.squad_b_id} | "
                                   f"Losses {r.losses_a}-{r.losses_b}")
        complete, result = self.mission.is_complete()
        if complete:
            self._return_to_town(result, "Mission complete.", True)

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------

    def render(self, screen) -> None:
        if not PYGAME_AVAILABLE:
            return

        self._ensure_resources(screen)
        width, height = screen.get_size()

        # 1. Terrain background (static bake + animated overlays)
        if self._map_renderer is not None:
            self._map_renderer.render(screen, self.mission.time_elapsed)
        else:
            screen.fill((64, 100, 48))

        # 2. Hot-lane detection
        hot_lanes: set = set()
        for squad in self.mission.squads:
            if squad.owner != 1 or squad.is_destroyed() or squad.target_site_id is None:
                continue
            for a_id, b_id in self.mission.lanes:
                if squad.target_site_id not in (a_id, b_id):
                    continue
                if a_id not in self.mission.sites or b_id not in self.mission.sites:
                    continue
                sa, sb = self.mission.sites[a_id], self.mission.sites[b_id]
                if self._point_seg_dist(squad.x, squad.y, sa.x, sa.y, sb.x, sb.y) < 80:
                    hot_lanes.add((a_id, b_id))

        # 3. Lane overlays
        lane_surf = pygame.Surface((width, height), pygame.SRCALPHA)
        for a_id, b_id in self.mission.lanes:
            if a_id not in self.mission.sites or b_id not in self.mission.sites:
                continue
            a, b = self.mission.sites[a_id], self.mission.sites[b_id]
            is_hot = (a_id, b_id) in hot_lanes
            lc = (200, 80, 60, 140) if is_hot else (220, 190, 120, 70)
            lw = 4 if is_hot else 3
            pygame.draw.line(lane_surf, lc, (int(a.x), int(a.y)), (int(b.x), int(b.y)), lw)
        screen.blit(lane_surf, (0, 0))

        # 4. Threat auras
        self._render_threat_overlays(screen)

        # 5. Site buildings
        site_ids = self._site_order()
        for idx, site_id in enumerate(site_ids):
            site = self.mission.sites[site_id]
            stype = site.site_type.name if hasattr(site.site_type, "name") else str(site.site_type)
            sw_s = 80 if stype == "BASE" else (70 if stype in ("FORT", "TEMPLE") else 60)
            sh_s = sw_s
            if self._sprites is not None:
                building = self._sprites.site_building(stype, site.owner, sw_s, sh_s)
                bx = int(site.x) - sw_s // 2
                by = int(site.y) - sh_s + 16
                screen.blit(building, (bx, by))
            if 0.0 < site.capture_progress < 100.0:
                self._draw_capture_ring(screen, site)
            if self.small_font is not None:
                lc2 = (200, 230, 255) if site.owner == 0 else ((255, 180, 160) if site.owner == 1 else (220, 220, 200))
                lbl = self.small_font.render(f"{idx + 1} {site.name}", True, lc2)
                lbl_x = int(site.x) - lbl.get_width() // 2
                lbl_y = int(site.y) - sh_s - 6
                shadow = self.small_font.render(f"{idx + 1} {site.name}", True, (10, 10, 10))
                screen.blit(shadow, (lbl_x + 1, lbl_y + 1))
                screen.blit(lbl, (lbl_x, lbl_y))

        # 6. Intercept forecast
        self._render_intercept_forecast(screen)

        # 7. Squad tokens
        selected = self._selected_squad()
        order_surf = pygame.Surface((width, height), pygame.SRCALPHA)
        for squad in self.mission.squads:
            if squad.is_destroyed():
                continue
            role_name = squad.role.value if hasattr(squad.role, "value") else "assault"
            if self._sprites is not None:
                token = self._sprites.squad_token(squad.owner, role_name, 44, 50)
                screen.blit(token, (int(squad.x) - 22, int(squad.y) - 40))
            if selected is not None and squad.id == selected.id:
                pygame.draw.circle(screen, (255, 240, 80), (int(squad.x), int(squad.y) - 14), 28, 2)
            if squad.target_site_id and squad.target_site_id in self.mission.sites:
                target = self.mission.sites[squad.target_site_id]
                lc3 = (120, 190, 255, 150) if squad.owner == 0 else (255, 120, 100, 110)
                pygame.draw.line(order_surf, lc3,
                                 (int(squad.x), int(squad.y) - 14),
                                 (int(target.x), int(target.y)), 1)
            if self.small_font is not None and selected is not None and squad.id == selected.id:
                tag = self.small_font.render(squad.name, True, (255, 240, 140))
                screen.blit(tag, (int(squad.x) - tag.get_width() // 2, int(squad.y) - 58))
        screen.blit(order_surf, (0, 0))

        # 8. HUD
        self._render_hud(screen, width, height)

    # ------------------------------------------------------------------
    # Overlay / VFX
    # ------------------------------------------------------------------

    def _render_threat_overlays(self, screen) -> None:
        pulse = int(45 + 30 * math.sin(self.mission.time_elapsed * 2.8))
        enemy_targets = {
            s.target_site_id
            for s in self.mission.squads
            if s.owner == 1 and not s.is_destroyed() and s.target_site_id
        }
        for site_id in enemy_targets:
            site = self.mission.sites.get(site_id)
            if site is None:
                continue
            r = 46
            surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (220, 50, 50, pulse), (r, r), r)
            screen.blit(surf, (int(site.x) - r, int(site.y) - r))

    def _render_intercept_forecast(self, screen) -> None:
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
                size = 9
                pts = [(ix, iy - size), (ix + size, iy), (ix, iy + size), (ix - size, iy)]
                pygame.draw.polygon(screen, (255, 215, 50), pts)
                pygame.draw.polygon(screen, (170, 120, 10), pts, 1)

    def _draw_capture_ring(self, screen, site) -> None:
        cx, cy = int(site.x), int(site.y)
        r = 32
        color = (80, 200, 120) if site.owner == 0 else (200, 80, 80) if site.owner == 1 else (200, 200, 80)
        angle = int(360 * site.capture_progress / 100)
        arc_surf = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
        pygame.draw.arc(arc_surf, (*color, 200),
                        (2, 2, r * 2, r * 2),
                        math.radians(90), math.radians(90 + angle), 4)
        screen.blit(arc_surf, (cx - r - 2, cy - r - 2))

    # ------------------------------------------------------------------
    # HUD
    # ------------------------------------------------------------------

    def _render_hud(self, screen, width: int, height: int) -> None:
        if self.digit_font is None or self.small_font is None or self.body_font is None:
            return

        if self._sprites is not None:
            clock_frame = self._sprites.hud_clock_frame(172, 76)
            clock_x = width - 186
            clock_y = 12
            screen.blit(clock_frame, (clock_x, clock_y))

            days = int(self.mission.time_elapsed // 60)
            d_surf = self.digit_font.render(f"{days:02d}", True, (240, 205, 100))
            screen.blit(d_surf, (clock_x + 18, clock_y + 26))

            total_sec = int(self.mission.time_elapsed)
            mins, secs = divmod(total_sec % 3600, 60)
            t_surf = self.digit_font.render(f"{mins:02d}:{secs:02d}", True, (215, 215, 215))
            screen.blit(t_surf, (clock_x + 82, clock_y + 26))

            lbl = self.small_font.render("DAYS", True, (175, 148, 78))
            screen.blit(lbl, (clock_x + 22, clock_y + 9))

        # Bottom strip
        strip_h = 54
        strip_surf = pygame.Surface((width, strip_h), pygame.SRCALPHA)
        strip_surf.fill((8, 10, 16, 195))
        screen.blit(strip_surf, (0, height - strip_h))

        pressure = self.mission.pressure_index
        hc = (255, 85, 65) if pressure > 5 else ((255, 200, 75) if pressure > 0 else (115, 215, 125))
        inc_line = self.body_font.render(
            f"CH {self.session.chapter}  |  Income {self.mission.player_income}g  |  Pressure {pressure:.0f}",
            True, hc,
        )
        screen.blit(inc_line, (16, height - strip_h + 6))

        status_s = self.small_font.render(self.status_message, True, (228, 216, 158))
        screen.blit(status_s, (16, height - strip_h + 30))

        ctrl_s = self.small_font.render(
            "TAB: squad  |  1-6: order  |  R: recall  |  SPACE: pause  |  ESC: withdraw",
            True, (138, 158, 188),
        )
        screen.blit(ctrl_s, (width // 2 - ctrl_s.get_width() // 2, height - strip_h + 30))

        if self.paused and self.title_font is not None:
            po = pygame.Surface((width, height), pygame.SRCALPHA)
            po.fill((0, 0, 0, 95))
            screen.blit(po, (0, 0))
            pt = self.title_font.render("— PAUSED —", True, (255, 235, 140))
            screen.blit(pt, (width // 2 - pt.get_width() // 2, height // 2 - pt.get_height() // 2))

    # ------------------------------------------------------------------
    # Geometry
    # ------------------------------------------------------------------

    @staticmethod
    def _segment_intersection(p1, p2, p3, p4):
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
    def _point_seg_dist(px, py, ax, ay, bx, by) -> float:
        dx, dy = bx - ax, by - ay
        seg_sq = dx * dx + dy * dy
        if seg_sq < 1e-10:
            return math.hypot(px - ax, py - ay)
        t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / seg_sq))
        return math.hypot(px - (ax + t * dx), py - (ay + t * dy))
