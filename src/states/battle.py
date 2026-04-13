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
    """Squad-based strategic map with terrain background, building sprites, and squad tokens."""

    _SCENARIO_ID = "ch1_asterhold_gate"
    _IGNORE_DEFEAT_FOR_TESTING = True

    def __init__(self, session: CampaignSession | None = None):
        super().__init__()
        self.state_type = StateType.BATTLE
        self.session = session or CampaignSession.new_game()

        from ..strategy.mission_loader import load_mission
        self.mission = load_mission(self._SCENARIO_ID, chapter=self.session.chapter)
        # Testing override: keep battle running even if enemy captures player base.
        self.mission.ignore_player_base_defeat = True
        player_squads = self.session.build_player_squads()
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
        # Camera scroll state (pixels into the baked map surface)
        self._cam_x: float = 0.0
        self._cam_y: float = 0.0
        self._cam_max_x: float = 0.0
        self._cam_max_y: float = 0.0
        self._cam_vx: float = 0.0
        self._cam_vy: float = 0.0
        # Bake map at max zoom once, then runtime zoom uses scene scaling only.
        self._zoom: float = 1.45
        self._zoom_visual: float = 0.95
        self._zoom_target: float = 0.95
        self._zoom_sprite_ref: float = 0.95
        self._zoom_wheel_step: float = 0.07
        self._zoom_min: float = 0.08
        self._zoom_max: float = 2.4
        self._zoom_input_idle: float = 999.0
        self._zoom_anchor_screen: Optional[tuple] = None
        self._scene_surf = None
        self._lane_surf = None
        self._order_surf = None
        self._render_surf_size: tuple = (0, 0)
        self._text_cache = {}
        self._view_origin_x: float = 0.0
        self._view_origin_y: float = 0.0
        self._view_display_scale: float = 1.0
        # Which edges are currently being scrolled: [left, right, up, down]
        self._scroll_flags: List[bool] = [False, False, False, False]
        self._screen_size: tuple = (1280, 720)

        if PYGAME_AVAILABLE:
            self.title_font = pygame.font.Font(None, 42)
            self.body_font  = pygame.font.Font(None, 28)
            self.small_font = pygame.font.Font(None, 22)
            self.digit_font = pygame.font.Font(None, 36)
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
        self._map_renderer.set_zoom(self._zoom)
        self._map_renderer.bake(sw, sh)

        _HUD_H = 54
        self._screen_size = (sw, sh)
        self._update_camera_bounds_for_zoom(self._zoom_visual)
        # Start camera centered on the player's main base.
        player_base = self.mission.sites.get("player_base") if self.mission.sites else None
        if player_base is not None:
            focus_x, focus_y = self._map_renderer._wb(player_base.x, player_base.y)
        elif self.mission.sites:
            xs = [site.x for site in self.mission.sites.values()]
            ys = [site.y for site in self.mission.sites.values()]
            wx = (min(xs) + max(xs)) * 0.5
            wy = (min(ys) + max(ys)) * 0.5
            focus_x, focus_y = self._map_renderer._wb(wx, wy)
        else:
            focus_x = self._map_renderer._bake_w * 0.5
            focus_y = self._map_renderer._bake_h * 0.5
        display_scale = self._display_scale_for_zoom(self._zoom_visual)
        self._cam_x = min(self._cam_max_x, max(0.0, focus_x - sw * 0.5 / display_scale))
        self._cam_y = min(self._cam_max_y, max(0.0, focus_y - (sh - _HUD_H) * 0.5 / display_scale))

        fit_scale_x = sw / max(1.0, float(self._map_renderer._map_w))
        fit_scale_y = (sh - _HUD_H) / max(1.0, float(self._map_renderer._map_h))
        fit_zoom_min = self._zoom * min(fit_scale_x, fit_scale_y)
        # Respect the configured lower zoom bound instead of forcing a higher auto-fit floor.
        self._zoom_min = max(0.05, min(self._zoom_min, fit_zoom_min, self._zoom_max))
        self._zoom_target = max(self._zoom_min, self._zoom_target)
        self._zoom_visual = max(self._zoom_min, self._zoom_visual)
        self._update_camera_bounds_for_zoom(self._zoom_visual)

    def _rebake_for_zoom(self, detail_scale: float = 1.0) -> None:
        if self._map_renderer is None:
            return
        sw, sh = self._screen_size
        hud_h = 54
        if self._zoom_anchor_screen is None:
            anchor_x = sw * 0.5
            anchor_y = (sh - hud_h) * 0.5
        else:
            anchor_x = max(0.0, min(float(sw - 1), float(self._zoom_anchor_screen[0])))
            anchor_y = max(0.0, min(float(sh - hud_h - 1), float(self._zoom_anchor_screen[1])))
        # Preserve world-space focal point across zoom rebakes.
        old_zoom = self._map_renderer.get_zoom()
        old_scale = self._map_renderer._scale * old_zoom
        old_center_x = self._cam_x + anchor_x
        old_center_y = self._cam_y + anchor_y
        world_focus_x = (old_center_x - self._map_renderer._pad_x) / max(1e-6, old_scale)
        world_focus_y = (old_center_y - self._map_renderer._pad_y) / max(1e-6, old_scale)

        self._map_renderer.set_zoom(self._zoom)
        self._map_renderer.bake(sw, sh, detail_scale=detail_scale)
        self._cam_max_x, self._cam_max_y = self._map_renderer.cam_max(sw, sh - hud_h)

        focus_px_x, focus_px_y = self._map_renderer._wb(world_focus_x, world_focus_y)
        target_cam_x = min(self._cam_max_x, max(0.0, focus_px_x - anchor_x))
        target_cam_y = min(self._cam_max_y, max(0.0, focus_px_y - anchor_y))

        # Solve camera directly at the pivot-anchored target and keep visual zoom in sync.
        self._cam_x = target_cam_x
        self._cam_y = target_cam_y
        self._zoom_visual = self._zoom
        # Avoid residual edge-scroll momentum causing a pop after settle.
        self._cam_vx = 0.0
        self._cam_vy = 0.0

    def _rebake_quality_only(self, detail_scale: float = 1.0) -> None:
        """Rebake visuals without re-centering focus or starting camera handoff."""
        if self._map_renderer is None:
            return
        sw, sh = self._screen_size
        hud_h = 54
        self._map_renderer.set_zoom(self._zoom)
        self._map_renderer.bake(sw, sh, detail_scale=detail_scale)
        self._cam_max_x, self._cam_max_y = self._map_renderer.cam_max(sw, sh - hud_h)
        self._cam_x = min(self._cam_max_x, max(0.0, self._cam_x))
        self._cam_y = min(self._cam_max_y, max(0.0, self._cam_y))

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

    def _p(self, wx: float, wy: float) -> tuple:
        """Project world coordinate to screen coordinate (accounts for camera)."""
        if self._map_renderer is not None:
            px, py = self._map_renderer.project_display(wx, wy)
            return (int(px), int(py))
        return (int(wx), int(wy))

    def _display_scale_for_zoom(self, zoom_level: float) -> float:
        return max(1e-4, float(zoom_level) / max(1e-4, self._zoom))

    def _active_zoom_min(self) -> float:
        """Minimum zoom that still changes the rendered map at current viewport size."""
        if self._map_renderer is None:
            return self._zoom_min
        sw, sh = self._screen_size
        fit_scale_x = sw / max(1.0, float(self._map_renderer._bake_w))
        fit_scale_y = sh / max(1.0, float(self._map_renderer._bake_h))
        fit_floor = self._zoom * max(fit_scale_x, fit_scale_y)
        return max(self._zoom_min, fit_floor)

    def _update_camera_bounds_for_zoom(self, zoom_level: float) -> None:
        if self._map_renderer is None:
            return
        sw, sh = self._screen_size
        hud_h = 54
        display_scale = self._display_scale_for_zoom(zoom_level)
        view_w = sw / display_scale
        view_h = (sh - hud_h) / display_scale
        self._cam_max_x = max(0.0, float(self._map_renderer._bake_w) - view_w)
        self._cam_max_y = max(0.0, float(self._map_renderer._bake_h) - view_h)
        self._cam_x = min(self._cam_max_x, max(0.0, self._cam_x))
        self._cam_y = min(self._cam_max_y, max(0.0, self._cam_y))

    def _apply_visual_zoom(self, new_zoom_visual: float) -> None:
        active_min = self._active_zoom_min()
        clamped_zoom = max(active_min, min(self._zoom_max, float(new_zoom_visual)))
        if self._map_renderer is None:
            self._zoom_visual = clamped_zoom
            return

        sw, sh = self._screen_size
        hud_h = 54
        if self._zoom_anchor_screen is None:
            anchor_x = sw * 0.5
            anchor_y = (sh - hud_h) * 0.5
        else:
            anchor_x = max(0.0, min(float(sw - 1), float(self._zoom_anchor_screen[0])))
            anchor_y = max(0.0, min(float(sh - hud_h - 1), float(self._zoom_anchor_screen[1])))

        old_display = self._display_scale_for_zoom(self._zoom_visual)
        bake_anchor_x = self._cam_x + anchor_x / old_display
        bake_anchor_y = self._cam_y + anchor_y / old_display

        self._zoom_visual = clamped_zoom
        new_display = self._display_scale_for_zoom(self._zoom_visual)
        self._update_camera_bounds_for_zoom(self._zoom_visual)
        self._cam_x = min(self._cam_max_x, max(0.0, bake_anchor_x - anchor_x / new_display))
        self._cam_y = min(self._cam_max_y, max(0.0, bake_anchor_y - anchor_y / new_display))

    def _ensure_render_surfaces(self, width: int, height: int) -> None:
        if self._scene_surf is None or self._render_surf_size != (width, height):
            self._scene_surf = pygame.Surface((width, height), pygame.SRCALPHA)
            self._lane_surf = pygame.Surface((width, height), pygame.SRCALPHA)
            self._order_surf = pygame.Surface((width, height), pygame.SRCALPHA)
            self._render_surf_size = (width, height)
            self._text_cache.clear()

    def _scaled_label(self, text: str, color: tuple, scale: float, fast_preview: bool):
        if self.small_font is None:
            return None
        q = max(0.5, min(2.0, float(scale)))
        key = (text, color, int(round(q * 100)), bool(fast_preview))
        cached = self._text_cache.get(key)
        if cached is not None:
            return cached

        surf = self.small_font.render(text, True, color)
        if abs(q - 1.0) > 0.001:
            tw = max(1, int(round(surf.get_width() * q)))
            th = max(1, int(round(surf.get_height() * q)))
            if fast_preview:
                surf = pygame.transform.scale(surf, (tw, th))
            else:
                surf = pygame.transform.smoothscale(surf, (tw, th))
        self._text_cache[key] = surf
        return surf

    # ------------------------------------------------------------------
    # GameState interface
    # ------------------------------------------------------------------

    def on_enter(self) -> None: pass
    def on_exit(self) -> None: pass

    def handle_event(self, event) -> None:
        if not PYGAME_AVAILABLE:
            return
        if event.type == pygame.MOUSEWHEEL:
            sw, sh = self._screen_size
            mx, my = pygame.mouse.get_pos()
            hud_h = 54
            active_min = self._active_zoom_min()
            self._zoom_anchor_screen = (
                max(0, min(sw - 1, int(mx))),
                max(0, min(sh - hud_h - 1, int(my))),
            )
            self._zoom_input_idle = 0.0
            prev_target = self._zoom_target
            self._zoom_target = max(
                active_min,
                min(self._zoom_max, self._zoom_target + event.y * self._zoom_wheel_step),
            )
            # Immediate response to wheel input before per-frame smoothing catches up.
            delta = self._zoom_target - prev_target
            self._apply_visual_zoom(self._zoom_visual + delta * 0.1)
            self.status_message = f"Zoom {int(self._zoom_target * 100)}%"
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
        self._zoom_input_idle += delta_time

        # High-FPS zoom preview: animate visual zoom every frame (no rebake stages).
        if abs(self._zoom_target - self._zoom_visual) > 1e-4:
            blend = 1.0 - math.exp(-20.0 * max(0.0, delta_time))
            next_zoom_visual = self._zoom_visual + (self._zoom_target - self._zoom_visual) * blend
            if abs(self._zoom_target - next_zoom_visual) < 5e-4:
                next_zoom_visual = self._zoom_target
            self._apply_visual_zoom(next_zoom_visual)

        if abs(self._zoom_target - self._zoom_visual) <= 1e-4:
            self._zoom_anchor_screen = None

        self._update_camera_bounds_for_zoom(self._zoom_visual)

        # Edge-scroll with smooth acceleration/deceleration (works while paused).
        if PYGAME_AVAILABLE:
            _ZONE = 92.0
            _MAX_SPEED = 900.0
            _HUD_H = 54.0
            sw2, sh2 = self._screen_size
            mx, my = pygame.mouse.get_pos()

            def _edge_curve(v: float) -> float:
                # Deadzone + smoothstep curve removes boundary stepping/jitter.
                v = max(0.0, min(1.0, v))
                if v <= 0.04:
                    return 0.0
                t = (v - 0.04) / 0.96
                return t * t * (3.0 - 2.0 * t)

            left = _edge_curve((_ZONE - mx) / _ZONE)
            right = _edge_curve((mx - (sw2 - _ZONE)) / _ZONE)
            up = _edge_curve((_ZONE - my) / _ZONE)
            down_limit = sh2 - _HUD_H
            down = _edge_curve((my - (down_limit - _ZONE)) / _ZONE)

            target_vx = (right - left) * _MAX_SPEED
            target_vy = (down - up) * _MAX_SPEED
            v_blend = 1.0 - math.exp(-16.0 * max(0.0, delta_time))
            self._cam_vx += (target_vx - self._cam_vx) * v_blend
            self._cam_vy += (target_vy - self._cam_vy) * v_blend
            # Extra damping when not actively driven keeps camera glide soft and stable.
            if abs(target_vx) < 1e-3:
                self._cam_vx *= math.exp(-14.0 * max(0.0, delta_time))
            if abs(target_vy) < 1e-3:
                self._cam_vy *= math.exp(-14.0 * max(0.0, delta_time))

            self._scroll_flags[0] = left > 0.05
            self._scroll_flags[1] = right > 0.05
            self._scroll_flags[2] = up > 0.05
            self._scroll_flags[3] = down > 0.05

            self._cam_x += self._cam_vx * delta_time
            self._cam_y += self._cam_vy * delta_time

            if self._cam_x < 0.0:
                self._cam_x = 0.0
                if self._cam_vx < 0.0:
                    self._cam_vx = 0.0
            elif self._cam_x > self._cam_max_x:
                self._cam_x = self._cam_max_x
                if self._cam_vx > 0.0:
                    self._cam_vx = 0.0

            if self._cam_y < 0.0:
                self._cam_y = 0.0
                if self._cam_vy < 0.0:
                    self._cam_vy = 0.0
            elif self._cam_y > self._cam_max_y:
                self._cam_y = self._cam_max_y
                if self._cam_vy > 0.0:
                    self._cam_vy = 0.0

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
            if result == "defeat" and self._IGNORE_DEFEAT_FOR_TESTING:
                self.status_message = "Testing mode: defeat ignored. Continue simulation."
            else:
                self._return_to_town(result, "Mission complete.", True)

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------

    def render(self, screen) -> None:
        if not PYGAME_AVAILABLE:
            return

        self._ensure_resources(screen)
        width, height = screen.get_size()
        self._ensure_render_surfaces(width, height)
        scene = self._scene_surf
        lane_surf = self._lane_surf
        order_surf = self._order_surf
        if scene is None or lane_surf is None or order_surf is None:
            scene = pygame.Surface((width, height), pygame.SRCALPHA)
            lane_surf = pygame.Surface((width, height), pygame.SRCALPHA)
            order_surf = pygame.Surface((width, height), pygame.SRCALPHA)
            self._scene_surf = scene
            self._lane_surf = lane_surf
            self._order_surf = order_surf
            self._render_surf_size = (width, height)
        scene.fill((0, 0, 0, 0))
        lane_surf.fill((0, 0, 0, 0))
        order_surf.fill((0, 0, 0, 0))
        display_scale = self._display_scale_for_zoom(self._zoom_visual)
        preview_comp = 1.0
        fast_preview = self._zoom_input_idle < 0.22
        drew_void = False

        # 1. Terrain background (static bake + animated overlays)
        if self._map_renderer is not None:
            self._map_renderer.render_void(screen, self.mission.time_elapsed)
            drew_void = True
            self._map_renderer.set_camera(self._cam_x, self._cam_y)
            self._map_renderer.set_display_scale(display_scale)
            interactive_zoom = self._zoom_input_idle < 0.12 or abs(self._zoom_target - self._zoom_visual) > 0.002
            self._map_renderer.set_fast_scale_mode(interactive_zoom)
            self._map_renderer.render(scene, self.mission.time_elapsed, render_void=False)

            # Derive sprite scaling from actual map on-screen scale after render clamping/fitting.
            base_display = self._display_scale_for_zoom(self._zoom_sprite_ref)
            effective_display = math.sqrt(
                max(1e-6, self._map_renderer._render_scale_x)
                * max(1e-6, self._map_renderer._render_scale_y)
            )
            sprite_zoom_ratio = effective_display / max(1e-6, base_display)
            if sprite_zoom_ratio >= 1.0:
                preview_comp = pow(sprite_zoom_ratio, 1.2)
            else:
                preview_comp = pow(sprite_zoom_ratio, 0.85)
            preview_comp = max(0.55, min(1.9, preview_comp))
        else:
            scene.fill((64, 100, 48))

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
        for a_id, b_id in self.mission.lanes:
            if a_id not in self.mission.sites or b_id not in self.mission.sites:
                continue
            a, b = self.mission.sites[a_id], self.mission.sites[b_id]
            is_hot = (a_id, b_id) in hot_lanes
            lc = (200, 80, 60, 140) if is_hot else (220, 190, 120, 70)
            lw = 4 if is_hot else 3
            pygame.draw.line(lane_surf, lc, self._p(a.x, a.y), self._p(b.x, b.y), lw)
        scene.blit(lane_surf, (0, 0))

        # 4. Threat auras
        self._render_threat_overlays(scene)

        # 5. Site buildings
        site_ids = self._site_order()
        for idx, site_id in enumerate(site_ids):
            site = self.mission.sites[site_id]
            stype = site.site_type.name if hasattr(site.site_type, "name") else str(site.site_type)
            base_sw_s = 80 if stype == "BASE" else (70 if stype in ("FORT", "TEMPLE") else 60)
            # Keep building sprites visually stable while preview zoom scales the scene.
            sw_s = int(round(base_sw_s * preview_comp))
            sw_s = max(42, min(140, sw_s))
            sh_s = sw_s
            bx_s, by_s = self._p(site.x, site.y)
            if self._sprites is not None:
                building = self._sprites.site_building(stype, site.owner, sw_s, sh_s)
                scene.blit(building, (bx_s - sw_s // 2, by_s - sh_s + 16))
            if 0.0 < site.capture_progress < 100.0:
                self._draw_capture_ring(scene, site)

        # 6. Intercept forecast
        self._render_intercept_forecast(scene)

        # 7. Squad tokens + order lines
        selected = self._selected_squad()
        for squad in self.mission.squads:
            if squad.is_destroyed():
                continue
            role_name = squad.role.value if hasattr(squad.role, "value") else "assault"
            sx, sy = self._p(squad.x, squad.y)
            if self._sprites is not None:
                tok_w = max(30, min(88, int(round(44 * preview_comp))))
                tok_h = max(34, min(100, int(round(50 * preview_comp))))
                token = self._sprites.squad_token(squad.owner, role_name, tok_w, tok_h)
                scene.blit(token, (sx - tok_w // 2, sy - int(tok_h * 0.8)))
            if selected is not None and squad.id == selected.id:
                sel_r = max(16, min(52, int(round(28 * preview_comp))))
                sel_w = max(1, int(round(2 * preview_comp)))
                pygame.draw.circle(scene, (255, 240, 80), (sx, sy - 14), sel_r, sel_w)
            if squad.target_site_id and squad.target_site_id in self.mission.sites:
                target = self.mission.sites[squad.target_site_id]
                lc3 = (120, 190, 255, 150) if squad.owner == 0 else (255, 120, 100, 110)
                pygame.draw.line(order_surf, lc3,
                                 (sx, sy - 14), self._p(target.x, target.y), 1)
            if self.small_font is not None and selected is not None and squad.id == selected.id:
                tag = self._scaled_label(squad.name, (255, 240, 140), preview_comp, fast_preview)
                if tag is None:
                    continue
                scene.blit(tag, (sx - tag.get_width() // 2, sy - 58))
        scene.blit(order_surf, (0, 0))

        # Scene is already rendered at runtime zoom from the full baked map.
        if not drew_void:
            screen.fill((0, 0, 0))
        screen.blit(scene, (0, 0))

        # 8. HUD
        self._render_hud(screen, width, height)

        # 9. Edge-scroll arrows (on top of everything)
        self._render_scroll_arrows(screen, width, height)

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
            cx, cy = self._p(site.x, site.y)
            screen.blit(surf, (cx - r, cy - r))

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
                ix, iy = self._p(result[0], result[1])
                key = (ix // 24, iy // 24)
                if key in drawn:
                    continue
                drawn.add(key)
                size = 9
                pts = [(ix, iy - size), (ix + size, iy), (ix, iy + size), (ix - size, iy)]
                pygame.draw.polygon(screen, (255, 215, 50), pts)
                pygame.draw.polygon(screen, (170, 120, 10), pts, 1)

    def _draw_capture_ring(self, screen, site) -> None:
        cx, cy = self._p(site.x, site.y)
        r = 32
        color = (80, 200, 120) if site.owner == 0 else (200, 80, 80) if site.owner == 1 else (200, 200, 80)
        angle = int(360 * site.capture_progress / 100)
        arc_surf = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
        pygame.draw.arc(arc_surf, (*color, 200),
                        (2, 2, r * 2, r * 2),
                        math.radians(90), math.radians(90 + angle), 4)
        screen.blit(arc_surf, (cx - r - 2, cy - r - 2))

    # ------------------------------------------------------------------
    # Scroll arrows
    # ------------------------------------------------------------------

    def _render_scroll_arrows(self, screen, width: int, height: int) -> None:
        """Draw pulsing golden arrows at edges that are actively scrolling."""
        if not any(self._scroll_flags):
            return
        pg = pygame
        pulse = 0.5 + 0.5 * math.sin(self.mission.time_elapsed * 5.0)
        hud_h = 54
        cx  = width // 2
        cy  = (height - hud_h) // 2
        sz  = 26   # half-width of arrow base
        pad = 18   # tip distance from screen edge

        # (flag_idx, tip, base_left, base_right)
        arrow_defs = [
            (0, (pad,             cy),
                (pad + sz, cy - sz),  (pad + sz, cy + sz)),            # left
            (1, (width - pad,     cy),
                (width - pad - sz, cy - sz), (width - pad - sz, cy + sz)),  # right
            (2, (cx,              pad),
                (cx - sz, pad + sz),  (cx + sz, pad + sz)),            # up
            (3, (cx, height - hud_h - pad),
                (cx - sz, height - hud_h - pad - sz),
                (cx + sz, height - hud_h - pad - sz)),                  # down
        ]

        overlay = pg.Surface((width, height), pg.SRCALPHA)
        for flag_idx, tip, bl, br in arrow_defs:
            if not self._scroll_flags[flag_idx]:
                continue
            tri = [tip, bl, br]
            alpha_main = int(200 + 55 * pulse)
            alpha_glow = int(55 * pulse)
            for expansion in (12, 8, 4):
                eg = _expand_triangle(tri, expansion)
                pg.draw.polygon(overlay, (255, 220, 80, alpha_glow), eg)
            pg.draw.polygon(overlay, (255, 220, 60, alpha_main), tri)
            pg.draw.polygon(overlay, (255, 255, 200, 230), tri, 2)
        screen.blit(overlay, (0, 0))

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


def _expand_triangle(pts, amount: float):
    """Expand a triangle outward from its centroid by *amount* pixels."""
    cx = sum(p[0] for p in pts) / 3.0
    cy = sum(p[1] for p in pts) / 3.0
    result = []
    for px, py in pts:
        dx, dy = px - cx, py - cy
        d = math.hypot(dx, dy)
        if d < 1e-9:
            result.append((int(px), int(py)))
        else:
            result.append((int(px + dx / d * amount), int(py + dy / d * amount)))
    return result
