"""MapRenderer — bakes static terrain layers once, composites animated overlays per-frame.

Coordinate system
-----------------
World coordinates (from the scenario JSON) are scaled by MAP_SCALE and then
offset by an (cam_x, cam_y) camera position for screen rendering:

    screen_x = world_x * MAP_SCALE - cam_x
    screen_y = world_y * MAP_SCALE - cam_y

``bake()`` pre-renders all static layers onto a surface of size
(world_w * MAP_SCALE, world_h * MAP_SCALE).  The camera pans this surface over
the viewport without re-baking.  Call ``set_camera(cam_x, cam_y)`` each frame
before ``render()``.

Extending animated terrains
----------------------------
1. Add terrain name to ANIMATED_TERRAINS in map_def.py.
2. Define palette entry in TERRAIN_PALETTE in map_def.py.
3. Add ``_render_animated_<terrain>(screen, layer, t)`` here.
   The dispatcher in ``_render_animated_layer`` calls it automatically.
"""

from __future__ import annotations

import math
import random
from typing import Any, Dict, List, Optional, Tuple

from .map_def import LayerDef, MapDef

# World units are scaled by this factor when baking / projecting.
# Values > 1.0 make the baked map larger than the typical viewport, enabling
# the camera to pan around it.
MAP_SCALE: float = 1.8


class MapRenderer:
    """Owns the static baked surface and per-frame animated overlays."""

    def __init__(self, map_def: MapDef, pygame):
        self._def = map_def
        self._pg = pygame
        self._static_surf: Optional[Any] = None
        # Smoothed paths in BAKE space (world * scale). Camera offset applied at render time.
        self._smoothed: Dict[str, List[Tuple[int, int]]] = {}
        self._scale: float = MAP_SCALE
        self._zoom: float = 1.0
        # Camera offset in bake-surface pixels (set each frame via set_camera)
        self._cam_x: float = 0.0
        self._cam_y: float = 0.0
        self._display_scale: float = 1.0
        self._fast_scale_mode: bool = False
        self._render_origin_x: float = 0.0
        self._render_origin_y: float = 0.0
        self._render_scale_x: float = 1.0
        self._render_scale_y: float = 1.0
        # Baked surface dimensions (set in bake())
        self._bake_w: int = map_def.width
        self._bake_h: int = map_def.height
        self._map_w: int = map_def.width
        self._map_h: int = map_def.height
        self._pad_x: int = 0
        self._pad_y: int = 0
        # Viewport dimensions (set in bake())
        self._screen_w: int = map_def.width
        self._screen_h: int = map_def.height
        self._detail_scale: float = 1.0
        self._void_brush_cache: Dict[Tuple[int, Tuple[int, int, int], int], Any] = {}
        # Precomputed starfield + dust for the void background.
        rng = random.Random(map_def.seed + 991)
        self._void_stars = [
            (
                rng.random(),
                rng.random(),
                rng.random() * math.tau,
                rng.choice((1, 1, 1, 2, 2, 3)),
                rng.randint(90, 220),
                rng.choice((0, 1, 2)),
            )
            for _ in range(220)
        ]
        self._void_dust = [
            (rng.random(), rng.random(), rng.random() * math.tau, rng.randint(18, 52), rng.randint(10, 24))
            for _ in range(36)
        ]
        # Subtle shooting-star state.
        self._void_fx_rng = random.Random(map_def.seed + 1777)
        self._void_shooting: List[Dict[str, float]] = []
        self._void_last_t: Optional[float] = None
        self._void_next_shoot_t: float = self._void_fx_rng.uniform(1.4, 3.6)
        self._void_cached_surf: Optional[Any] = None
        self._void_cached_size: Tuple[int, int] = (0, 0)
        self._void_cached_t: float = -1.0
        self._void_cache_step: float = 1.0 / 30.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def project(self, wx: float, wy: float) -> Tuple[float, float]:
        """Convert world coordinates to current screen coordinates."""
        s = self._effective_scale()
        return (wx * s + self._pad_x - self._cam_x, wy * s + self._pad_y - self._cam_y)

    def project_display(self, wx: float, wy: float) -> Tuple[float, float]:
        """Convert world coordinates to actual current on-screen coordinates."""
        bx, by = self._wb(wx, wy)
        return (
            (bx - self._render_origin_x) * self._render_scale_x,
            (by - self._render_origin_y) * self._render_scale_y,
        )

    def set_zoom(self, zoom: float) -> None:
        """Set map zoom factor used for baking and projection."""
        self._zoom = max(0.4, min(2.5, float(zoom)))

    def get_zoom(self) -> float:
        return self._zoom

    def set_camera(self, cam_x: float, cam_y: float) -> None:
        """Set camera scroll offset (bake-surface pixels)."""
        self._cam_x = cam_x
        self._cam_y = cam_y

    def set_display_scale(self, display_scale: float) -> None:
        """Set runtime display scale relative to baked pixels."""
        self._display_scale = max(1e-4, float(display_scale))

    def set_fast_scale_mode(self, enabled: bool) -> None:
        """When enabled, use faster lower-quality scaling for interactive zoom frames."""
        self._fast_scale_mode = bool(enabled)

    def cam_max(self, screen_w: int, screen_h: int) -> Tuple[float, float]:
        """Return (max_cam_x, max_cam_y) for clamping the camera scroll."""
        return (
            max(0.0, float(self._bake_w - screen_w)),
            max(0.0, float(self._bake_h - screen_h)),
        )

    def bake(self, screen_w: Optional[int] = None, screen_h: Optional[int] = None, detail_scale: float = 1.0) -> None:
        """Render all static layers onto a cached Surface of size (world * scale)."""
        sw = screen_w or self._def.width
        sh = screen_h or self._def.height
        self._detail_scale = max(0.15, min(1.0, float(detail_scale)))
        self._screen_w = sw
        self._screen_h = sh
        s = self._effective_scale()
        self._map_w = int(self._def.width * s)
        self._map_h = int(self._def.height * s)
        # Padding lets camera center near-edge points and reveals void outside map edges.
        self._pad_x = max(180, sw // 2)
        self._pad_y = max(120, (sh - 54) // 2)
        self._bake_w = self._map_w + self._pad_x * 2
        self._bake_h = self._map_h + self._pad_y * 2

        pg = self._pg
        surf = pg.Surface((self._bake_w, self._bake_h), pg.SRCALPHA)
        surf.fill((0, 0, 0, 0))
        rng = random.Random(self._def.seed)

        for layer in self._def.layers:
            if layer.animated:
                # Pre-compute smoothed paths in bake space (no cam offset yet)
                if layer.points:
                    world_pts = [(int(p[0]), int(p[1])) for p in layer.points]
                    smooth_world = _chaikin(world_pts, iterations=3)
                    self._smoothed[layer.id] = [self._wb(wx, wy) for wx, wy in smooth_world]
                self._bake_animated_base(surf, layer)
            else:
                self._bake_static_layer(surf, layer, rng)

        self._static_surf = surf

    def render(self, screen, time_elapsed: float, render_void: bool = True) -> None:
        """Blit static + animated map layers; optionally include void background."""
        if render_void:
            self._render_void_background(screen, time_elapsed)
        if self._static_surf is None:
            return
        sw, sh = screen.get_size()
        src_w = min(self._bake_w, max(1, int(math.ceil(sw / self._display_scale))))
        src_h = min(self._bake_h, max(1, int(math.ceil(sh / self._display_scale))))
        cx = int(min(max(0.0, self._cam_x), max(0.0, self._bake_w - src_w)))
        cy = int(min(max(0.0, self._cam_y), max(0.0, self._bake_h - src_h)))
        self._render_origin_x = float(cx)
        self._render_origin_y = float(cy)
        self._render_scale_x = sw / max(1.0, float(src_w))
        self._render_scale_y = sh / max(1.0, float(src_h))
        view = self._static_surf.subsurface((cx, cy, src_w, src_h))
        if src_w == sw and src_h == sh:
            screen.blit(view, (0, 0))
        else:
            if self._fast_scale_mode:
                scaled = self._pg.transform.scale(view, (sw, sh))
            else:
                scaled = self._pg.transform.smoothscale(view, (sw, sh))
            screen.blit(scaled, (0, 0))
        for layer in self._def.layers:
            if layer.animated:
                self._render_animated_layer(screen, layer, time_elapsed)

    def render_void(self, screen, time_elapsed: float, freeze: bool = False) -> None:
        """Render only the outer void background, with optional cached freeze mode."""
        sw, sh = screen.get_size()

        needs_refresh = (
            self._void_cached_surf is None
            or self._void_cached_size != (sw, sh)
            or (not freeze and abs(time_elapsed - self._void_cached_t) >= self._void_cache_step)
        )

        if needs_refresh:
            self._void_cached_surf = self._pg.Surface((sw, sh), self._pg.SRCALPHA)
            self._render_void_background(self._void_cached_surf, time_elapsed)
            self._void_cached_size = (sw, sh)
            self._void_cached_t = time_elapsed

        if self._void_cached_surf is not None:
            screen.blit(self._void_cached_surf, (0, 0))
            if freeze:
                # Keep a small amount of motion while avoiding expensive full void redraw.
                self._render_void_twinkle_overlay(screen, time_elapsed)

    def _render_void_twinkle_overlay(self, screen, t: float) -> None:
        """Cheap star twinkle overlay used when full void redraw is intentionally frozen."""
        sw, sh = screen.get_size()
        overlay = self._pg.Surface((sw, sh), self._pg.SRCALPHA)
        for i, (nx, ny, phase, radius, base_alpha, layer) in enumerate(self._void_stars):
            if i % 3 != 0:
                continue
            x = int(nx * sw)
            y = int(ny * sh)
            tw = 0.55 + 0.45 * math.sin(t * (1.8 + layer * 0.6) + phase)
            a = max(12, min(150, int(base_alpha * 0.45 * tw)))
            self._pg.draw.circle(overlay, (226, 210, 255, a), (x, y), max(1, radius - 1))
        screen.blit(overlay, (0, 0))

    def _render_void_background(self, screen, t: float) -> None:
        """Draw a dark-purple outerspace backdrop with layered shimmer and parallax."""
        sw, sh = screen.get_size()
        # Base fill and radial depth gradient.
        screen.fill((6, 4, 18))
        vignette = self._pg.Surface((sw, sh), self._pg.SRCALPHA)
        cx, cy = sw // 2, sh // 2
        max_r = int(math.hypot(cx, cy))
        for i in range(7):
            frac = i / 6.0
            r = int(max_r * (0.25 + frac * 0.85))
            a = int(34 + 24 * frac)
            col = (6, 4, 16, a)
            self._pg.draw.circle(vignette, col, (cx, cy), r, width=max(8, int(max_r * 0.05)))
        screen.blit(vignette, (0, 0))

        # Animated nebula flow ribbons built from layered glow passes.
        haze = self._pg.Surface((sw, sh), self._pg.SRCALPHA)
        for idx, (base_y, amp1, amp2, speed, drift, phase, radius, c0, c1) in enumerate([
            (0.23, 34.0, 18.0, 0.11, 0.030, 0.2, 72, (48, 15, 94), (94, 42, 138)),
            (0.58, 42.0, 22.0, 0.09, 0.022, 1.6, 84, (42, 13, 84), (84, 36, 126)),
            (0.79, 28.0, 16.0, 0.13, 0.036, 2.7, 64, (36, 11, 74), (72, 31, 112)),
        ]):
            points = []
            for x in range(-24, sw + 25, 8):
                xf = x / max(1, sw)
                # Slow left-to-right drift of the wave field.
                phase_x = xf - t * drift
                y = (
                    sh * base_y
                    + math.sin(phase_x * math.tau * 1.55 + t * speed * 0.25 + phase) * amp1
                    + math.sin(phase_x * math.tau * 3.85 - t * (speed * 0.20) + phase * 1.5) * amp2
                )
                points.append((x, y))
            self._draw_nebula_ribbon(haze, points, radius, c0, c1, t, idx)
        screen.blit(haze, (0, 0))

        # Multi-layer starfield with subtle parallax from camera movement.
        star_overlay = self._pg.Surface((sw, sh), self._pg.SRCALPHA)
        for nx, ny, phase, radius, base_alpha, layer in self._void_stars:
            if layer == 0:
                color = (188, 170, 245)
            elif layer == 1:
                color = (224, 204, 255)
            else:
                color = (245, 234, 255)

            # Keep void position screen-stable; animate via twinkle only.
            x = int(nx * sw)
            y = int(ny * sh)
            tw = 0.55 + 0.45 * math.sin(t * (2.2 + layer * 0.9) + phase)
            a = max(20, min(255, int(base_alpha * tw)))
            self._pg.draw.circle(star_overlay, (*color, a), (x, y), radius)
            if radius >= 2 and layer == 2:
                # Stronger cinematic bloom on bright foreground stars.
                bloom_a = min(255, a + 56)
                self._pg.draw.circle(star_overlay, (*color, max(24, a // 4)), (x, y), radius + 2)
                self._pg.draw.line(star_overlay, (*color, bloom_a), (x - 4, y), (x + 4, y), 1)
                self._pg.draw.line(star_overlay, (*color, bloom_a), (x, y - 4), (x, y + 4), 1)
        screen.blit(star_overlay, (0, 0))

        # Fine sparkle mist to prevent flat areas between nebula bands.
        mist = self._pg.Surface((sw, sh), self._pg.SRCALPHA)
        for i in range(80):
            x = int(((i * 0.6180339) % 1.0) * sw)
            y = int(((i * 0.3819660 + 0.23) % 1.0) * sh)
            a = int(12 + 10 * (0.5 + 0.5 * math.sin(t * 0.9 + i)))
            self._pg.draw.circle(mist, (170, 150, 220, a), (x, y), 1)
        screen.blit(mist, (0, 0))

        self._update_and_render_shooting_stars(screen, t)

    def _update_and_render_shooting_stars(self, screen, t: float) -> None:
        """Spawn and draw occasional subtle shooting stars in the void."""
        if self._void_last_t is None:
            self._void_last_t = t
        dt = max(0.0, min(0.1, t - self._void_last_t))
        self._void_last_t = t

        sw, sh = screen.get_size()

        # Spawn one subtle meteor every few seconds.
        if t >= self._void_next_shoot_t and len(self._void_shooting) < 3:
            angle = self._void_fx_rng.uniform(0.22, 0.42)  # down-right drift
            speed = self._void_fx_rng.uniform(520.0, 760.0)
            spawn = self._random_visible_void_point(sw, sh)
            if spawn is not None:
                self._void_shooting.append(
                    {
                        "x": spawn[0],
                        "y": spawn[1],
                        "vx": math.cos(angle) * speed,
                        "vy": math.sin(angle) * speed,
                        "age": 0.0,
                        "life": self._void_fx_rng.uniform(0.42, 0.72),
                        "tail": self._void_fx_rng.uniform(70.0, 130.0),
                    }
                )
                self._void_next_shoot_t = t + self._void_fx_rng.uniform(1.9, 4.4)
            else:
                # If no void is visible right now, retry soon.
                self._void_next_shoot_t = t + 0.6

        overlay = self._pg.Surface((sw, sh), self._pg.SRCALPHA)
        alive: List[Dict[str, float]] = []
        for star in self._void_shooting:
            star["age"] += dt
            if star["age"] >= star["life"]:
                continue

            star["x"] += star["vx"] * dt
            star["y"] += star["vy"] * dt

            # Cull stars fully out of view.
            if star["x"] > sw + 180 or star["y"] > sh + 180:
                continue

            p = max(0.0, 1.0 - (star["age"] / star["life"]))
            # Smooth fade curve to avoid abrupt brightness change.
            p_smooth = p * p * (3.0 - 2.0 * p)
            base_a = int(180 * p_smooth)
            if base_a <= 0:
                continue

            vx = star["vx"]
            vy = star["vy"]
            vlen = math.hypot(vx, vy)
            if vlen < 1e-9:
                continue
            dx = vx / vlen
            dy = vy / vlen
            tail = star["tail"] * (0.55 + 0.45 * p_smooth)

            # Tail with denser segments for smoother apparent motion.
            segs = 18
            for i in range(segs):
                u0 = i / segs
                u1 = (i + 1) / segs
                x0 = star["x"] - dx * tail * u0
                y0 = star["y"] - dy * tail * u0
                x1 = star["x"] - dx * tail * u1
                y1 = star["y"] - dy * tail * u1
                amid = (u0 + u1) * 0.5
                a = int(base_a * ((1.0 - amid) ** 1.9))
                self._pg.draw.aaline(overlay, (232, 224, 255, a), (x0, y0), (x1, y1))

            # Faint secondary tail for smoother bloom.
            self._pg.draw.aaline(
                overlay,
                (208, 188, 255, max(24, base_a // 4)),
                (star["x"], star["y"]),
                (star["x"] - dx * tail * 1.08, star["y"] - dy * tail * 1.08),
            )

            # Small bright head.
            self._pg.draw.circle(overlay, (246, 240, 255, min(220, base_a + 60)), (int(star["x"]), int(star["y"])), 2)
            alive.append(star)

        self._void_shooting = alive
        screen.blit(overlay, (0, 0))

    def _random_visible_void_point(self, sw: int, sh: int) -> Optional[Tuple[float, float]]:
        """Return a random on-screen point that lies outside the visible map area."""
        map_left = self._pad_x - self._cam_x
        map_top = self._pad_y - self._cam_y
        map_right = map_left + self._map_w
        map_bottom = map_top + self._map_h

        def _inside_map(x: float, y: float) -> bool:
            return map_left <= x <= map_right and map_top <= y <= map_bottom

        # Rejection sample inside viewport until we hit visible void.
        for _ in range(48):
            x = self._void_fx_rng.uniform(0.0, float(sw))
            y = self._void_fx_rng.uniform(0.0, float(sh))
            if not _inside_map(x, y):
                return (x, y)
        return None

    def _draw_nebula_ribbon(self, surf, points, radius: int, c0, c1, t: float, idx: int) -> None:
        """Draw smooth ribbon gradients using layered soft-brush stamps."""
        pg = self._pg
        # Outer to inner glow passes; each pass uses a soft radial alpha brush.
        passes = [
            (1.08, 24, 0.18),
            (0.72, 36, 0.46),
            (0.44, 48, 0.78),
        ]
        # Pulse between low/high transparency states per ribbon.
        pulse_mix = 0.5 + 0.5 * math.sin(t * 1.2 + idx * 1.35)
        alpha_mult = 0.35 + 0.25 * pulse_mix
        for scale, alpha, mix in passes:
            r = max(2, int(radius * scale))
            col = _lerp(c0, c1, mix)
            pulsed_alpha = max(1, min(255, int(alpha * alpha_mult)))
            brush = self._get_soft_brush(r, col, pulsed_alpha)
            bw = brush.get_width()
            spacing = max(2, int(r * 0.33))

            for i in range(len(points) - 1):
                x0, y0 = points[i]
                x1, y1 = points[i + 1]
                dx = x1 - x0
                dy = y1 - y0
                seg_len = math.hypot(dx, dy)
                steps = max(1, int(seg_len / spacing))
                for s in range(steps + 1):
                    u = s / steps
                    x = x0 + dx * u
                    y = y0 + dy * u
                    # Very small shimmer warp so texture is alive, but still clean.
                    y += math.sin((i + u) * 0.55 + t * 1.1 + idx) * 0.7
                    surf.blit(brush, (int(x - bw * 0.5), int(y - bw * 0.5)))

        # No explicit center line; keep ribbon fully gradient-based.

    def _get_soft_brush(self, radius: int, color: Tuple[int, int, int], max_alpha: int):
        key = (radius, color, max_alpha)
        cached = self._void_brush_cache.get(key)
        if cached is not None:
            return cached

        pg = self._pg
        size = radius * 2 + 1
        cx = radius
        cy = radius
        brush = pg.Surface((size, size), pg.SRCALPHA)
        r_f = float(max(1, radius))
        for py in range(size):
            dy = py - cy
            for px in range(size):
                dx = px - cx
                d = math.hypot(dx, dy) / r_f
                if d > 1.0:
                    continue
                a = int(max_alpha * ((1.0 - d) ** 2.3))
                if a > 0:
                    brush.set_at((px, py), (color[0], color[1], color[2], a))

        self._void_brush_cache[key] = brush
        return brush

    # ------------------------------------------------------------------
    # World → bake coordinate helpers
    # ------------------------------------------------------------------

    def _wb(self, wx: float, wy: float) -> Tuple[int, int]:
        """World coordinates → bake surface coordinates (integer)."""
        s = self._effective_scale()
        return (int(wx * s) + self._pad_x, int(wy * s) + self._pad_y)

    def _wbs(self, v) -> int:
        """Scale a scalar world value to bake-surface pixels (minimum 1)."""
        s = self._effective_scale()
        return max(1, int(float(v) * s))

    def _effective_scale(self) -> float:
        return self._scale * self._zoom

    # ------------------------------------------------------------------
    # Static bake helpers
    # ------------------------------------------------------------------

    def _bake_static_layer(self, surf, layer: LayerDef, rng: random.Random) -> None:
        t = layer.layer_type
        if t == "fill":
            self._bake_fill(surf, layer, rng)
        elif t == "rect":
            self._bake_rect(surf, layer, rng)
        elif t == "circle":
            self._bake_circle(surf, layer, rng)
        elif t == "path":
            self._bake_road(surf, layer)
        elif t == "polygon":
            self._bake_polygon(surf, layer)

    def _bake_fill(self, surf, layer: LayerDef, rng: random.Random) -> None:
        pg = self._pg
        p  = layer.effective_palette
        b  = p.get("base",  (88, 138, 62))
        lt = p.get("light", (106, 158, 74))
        dk = p.get("dark",  (64, 108, 44))
        x0, y0 = self._pad_x, self._pad_y
        bw, bh = self._map_w, self._map_h

        pg.draw.rect(surf, b, (x0, y0, bw, bh))

        # Two-pass organic scatter over the full bake surface
        area = bw * bh
        for _ in range(int((area / 1200) * self._detail_scale)):
            x = int(rng.uniform(x0, x0 + bw))
            y = int(rng.uniform(y0, y0 + bh))
            r = rng.randint(18, 52)
            c = _lerp(b, lt if rng.random() < 0.5 else dk, rng.random() * 0.18)
            pg.draw.circle(surf, c, (x, y), r)
        for _ in range(int((area / 160) * self._detail_scale)):
            x = int(rng.uniform(x0, x0 + bw))
            y = int(rng.uniform(y0, y0 + bh))
            r = rng.randint(2, 7)
            c = _lerp(b, lt if rng.random() < 0.5 else dk, rng.random() * 0.13)
            pg.draw.circle(surf, c, (x, y), r)

    def _bake_rect(self, surf, layer: LayerDef, rng: random.Random) -> None:
        if layer.rect is None:
            return
        x, y, w, h = (float(v) for v in layer.rect)
        p  = layer.effective_palette
        b  = p.get("base",  (164, 138, 84))
        lt = p.get("light", (188, 162, 104))
        dk = p.get("dark",  (132, 106, 62))

        bx, by = self._wb(x, y)
        bw, bh = self._wbs(w), self._wbs(h)
        self._pg.draw.rect(surf, b, (bx, by, bw, bh))

        # Organic scatter inside rect
        area = max(1, bw * bh)
        for _ in range(int((area / 260) * self._detail_scale)):
            rx = int(rng.uniform(bx, bx + bw))
            ry = int(rng.uniform(by, by + bh))
            rr = rng.randint(5, 16)
            t2 = rng.random()
            c = _lerp(b, lt, t2 * 0.35) if t2 < 0.4 else (_lerp(b, dk, t2 * 0.25) if t2 < 0.7 else b)
            self._pg.draw.circle(surf, c, (rx, ry), rr)

        # Edge highlight / shadow
        self._pg.draw.line(surf, lt, (bx,      by),      (bx + bw, by),      3)  # top
        self._pg.draw.line(surf, lt, (bx,      by),      (bx,      by + bh), 3)  # left
        self._pg.draw.line(surf, dk, (bx,      by + bh), (bx + bw, by + bh), 3)  # bottom
        self._pg.draw.line(surf, dk, (bx + bw, by),      (bx + bw, by + bh), 3)  # right

    def _bake_circle(self, surf, layer: LayerDef, rng: random.Random) -> None:
        if layer.center is None:
            return
        pcx, pcy = self._wb(layer.center[0], layer.center[1])
        r  = self._wbs(layer.radius)
        p  = layer.effective_palette
        b  = p.get("base",  (46,  92, 38))
        lt = p.get("light", (58, 112, 46))
        dk = p.get("dark",  (32,  68, 26))

        self._pg.draw.circle(surf, b, (pcx, pcy), r)
        for _ in range(int(r * 0.7 * self._detail_scale)):
            angle = rng.random() * math.tau
            dist  = rng.random() * r * 0.85
            tx = int(pcx + math.cos(angle) * dist)
            ty = int(pcy + math.sin(angle) * dist)
            cr = rng.randint(max(1, int(r * 0.08)), max(2, int(r * 0.22)))
            shade = _lerp(b, lt if rng.random() < 0.5 else dk, rng.random() * 0.6)
            self._pg.draw.circle(surf, shade, (tx, ty), cr)
        self._pg.draw.arc(
            surf, lt,
            (pcx - r, pcy - r, r * 2, r * 2),
            math.radians(110), math.radians(200),
            max(2, r // 14),
        )

    def _bake_road(self, surf, layer: LayerDef) -> None:
        world_pts = [(int(p[0]), int(p[1])) for p in layer.points]
        smooth_w  = _chaikin(world_pts, iterations=1)
        bake_pts  = [self._wb(wx, wy) for wx, wy in smooth_w]
        p  = layer.effective_palette
        edge  = p.get("edge",  (152, 128, 72))
        fill  = p.get("fill",  (192, 170, 110))
        ew = self._wbs(p.get("edge_width", 10))
        fw = self._wbs(p.get("fill_width",  6))
        for i in range(len(bake_pts) - 1):
            self._pg.draw.line(surf, edge, bake_pts[i], bake_pts[i + 1], ew)
        for i in range(len(bake_pts) - 1):
            self._pg.draw.line(surf, fill, bake_pts[i], bake_pts[i + 1], fw)

    def _bake_polygon(self, surf, layer: LayerDef) -> None:
        if not layer.points:
            return
        pts = [self._wb(p[0], p[1]) for p in layer.points]
        p = layer.effective_palette
        self._pg.draw.polygon(surf, p.get("base", (80, 120, 60)), pts)

    # ------------------------------------------------------------------
    # Animated base bake (static bank color drawn once)
    # ------------------------------------------------------------------

    def _bake_animated_base(self, surf, layer: LayerDef) -> None:
        if layer.terrain in ("river", "water"):
            self._bake_river_base(surf, layer)

    def _bake_river_base(self, surf, layer: LayerDef) -> None:
        smoothed = self._smoothed.get(layer.id)
        if not smoothed:
            return
        p    = layer.effective_palette
        bank = p.get("bank",  (118,  96,  58))
        deep = p.get("deep",  (54,  102, 178))
        bw   = self._wbs(p.get("bank_width",  24))
        ww   = self._wbs(p.get("water_width", 15))
        for i in range(len(smoothed) - 1):
            self._pg.draw.line(surf, bank, smoothed[i], smoothed[i + 1], bw)
        for i in range(len(smoothed) - 1):
            self._pg.draw.line(surf, deep, smoothed[i], smoothed[i + 1], ww)

    # ------------------------------------------------------------------
    # Per-frame animated dispatch
    # ------------------------------------------------------------------

    def _render_animated_layer(self, screen, layer: LayerDef, t: float) -> None:
        if layer.terrain in ("river", "water"):
            self._render_animated_river(screen, layer, t)

    def _render_animated_river(self, screen, layer: LayerDef, t: float) -> None:
        smoothed = self._smoothed.get(layer.id)
        if not smoothed or len(smoothed) < 2:
            return

        p = layer.effective_palette
        shimmer_color = p.get("light", (88, 148, 220))
        speed = float(p.get("shimmer_speed", 55.0))

        # Apply camera offset to produce screen-space points
        ox = self._render_origin_x
        oy = self._render_origin_y
        sx = self._render_scale_x
        sy = self._render_scale_y
        screen_pts = [((bx - ox) * sx, (by - oy) * sy) for bx, by in smoothed]

        # Arc-length parameterisation for evenly-spaced dashes
        lengths = [0.0]
        for i in range(len(screen_pts) - 1):
            dx = screen_pts[i + 1][0] - screen_pts[i][0]
            dy = screen_pts[i + 1][1] - screen_pts[i][1]
            lengths.append(lengths[-1] + math.hypot(dx, dy))
        total = lengths[-1]
        if total < 1.0:
            return

        spacing  = 36.0
        dash_len = 12.0
        offset   = (t * speed) % spacing

        overlay = self._pg.Surface((self._screen_w, self._screen_h), self._pg.SRCALPHA)
        dist = offset
        while dist < total:
            d_end = min(dist + dash_len, total)
            ps = _pos_at(screen_pts, lengths, dist)
            pe = _pos_at(screen_pts, lengths, d_end)
            alpha = int(130 + 70 * math.sin(dist * 0.16 + t * 1.6))
            self._pg.draw.line(
                overlay,
                (*shimmer_color, alpha),
                (int(ps[0]), int(ps[1])),
                (int(pe[0]), int(pe[1])),
                3,
            )
            dist += spacing
        screen.blit(overlay, (0, 0))


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def _chaikin(pts: List[Tuple[int, int]], iterations: int = 2) -> List[Tuple[int, int]]:
    for _ in range(iterations):
        new = [pts[0]]
        for i in range(len(pts) - 1):
            x0, y0 = pts[i]
            x1, y1 = pts[i + 1]
            new.append((int(x0 * 0.75 + x1 * 0.25), int(y0 * 0.75 + y1 * 0.25)))
            new.append((int(x0 * 0.25 + x1 * 0.75), int(y0 * 0.25 + y1 * 0.75)))
        new.append(pts[-1])
        pts = new
    return pts


def _pos_at(pts: List[Tuple[int, int]], lengths: List[float], d: float) -> Tuple[float, float]:
    if d <= 0:
        return pts[0]
    if d >= lengths[-1]:
        return pts[-1]
    for i in range(len(lengths) - 1):
        if lengths[i] <= d <= lengths[i + 1]:
            seg = lengths[i + 1] - lengths[i]
            if seg < 1e-9:
                return pts[i]
            t = (d - lengths[i]) / seg
            return (
                pts[i][0] + t * (pts[i + 1][0] - pts[i][0]),
                pts[i][1] + t * (pts[i + 1][1] - pts[i][1]),
            )
    return pts[-1]


def _lerp(a: Tuple[int, int, int], b: Tuple[int, int, int], t: float) -> Tuple[int, int, int]:
    t = max(0.0, min(1.0, t))
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )
