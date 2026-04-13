"""MapRenderer — bakes static terrain layers once, composites animated layers each frame.

Coordinate system
-----------------
All world coordinates (from scenario JSON) are converted to isometric screen
coordinates via ``project()``:

    screen_x = iso_ox + (world_x - world_y) * iso_s
    screen_y = iso_oy + (world_x + world_y) * iso_s * 0.5

This produces a classic 2:1 isometric (diamond) layout.
``iso_s`` and ``(iso_ox, iso_oy)`` are computed in ``bake()`` so the whole
diamond fits within the screen, leaving room for the bottom HUD strip.

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


class MapRenderer:
    """Owns the static baked surface and per-frame animated overlays."""

    def __init__(self, map_def: MapDef, pygame):
        self._def = map_def
        self._pg = pygame
        self._static_surf: Optional[Any] = None
        # Smoothed paths in SCREEN space (set during bake for animated layers)
        self._smoothed: Dict[str, List[Tuple[int, int]]] = {}
        self._rng = random.Random(map_def.seed)
        # Isometric projection parameters (set in bake)
        self._iso_s: float = 0.5
        self._iso_ox: float = 0.0
        self._iso_oy: float = 0.0
        self._screen_w: int = map_def.width
        self._screen_h: int = map_def.height

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def project(self, wx: float, wy: float) -> Tuple[float, float]:
        """Convert world coordinates to isometric screen coordinates."""
        sx = self._iso_ox + (wx - wy) * self._iso_s
        sy = self._iso_oy + (wx + wy) * self._iso_s * 0.5
        return (sx, sy)

    def bake(self, screen_w: Optional[int] = None, screen_h: Optional[int] = None) -> None:
        """Render all static layers to a cached Surface.
        Pass screen dimensions so the diamond is fitted to the actual window.
        """
        sw = screen_w or self._def.width
        sh = screen_h or self._def.height
        self._screen_w = sw
        self._screen_h = sh
        self._compute_iso_params(sw, sh)

        pg = self._pg
        surf = pg.Surface((sw, sh))
        rng = random.Random(self._def.seed)

        for layer in self._def.layers:
            if layer.animated:
                # Pre-compute smoothed path in screen space
                if layer.points:
                    world_pts = [(int(p[0]), int(p[1])) for p in layer.points]
                    smooth_world = _chaikin(world_pts, iterations=3)
                    self._smoothed[layer.id] = [
                        (int(px), int(py))
                        for px, py in (self.project(x, y) for x, y in smooth_world)
                    ]
                self._bake_animated_base(surf, layer)
            else:
                self._bake_static_layer(surf, layer, rng)

        # Darken area outside the ISO diamond
        self._bake_iso_vignette(surf, sw, sh)
        self._static_surf = surf

    def render(self, screen, time_elapsed: float) -> None:
        """Blit the static surface then composite animated layers."""
        if self._static_surf is None:
            screen.fill((22, 32, 18))
            return
        screen.blit(self._static_surf, (0, 0))
        for layer in self._def.layers:
            if layer.animated:
                self._render_animated_layer(screen, layer, time_elapsed)

    # ------------------------------------------------------------------
    # ISO projection parameters
    # ------------------------------------------------------------------

    def _compute_iso_params(self, sw: int, sh: int) -> None:
        ww, wh = self._def.width, self._def.height
        hud_reserve = 68
        usable_h = sh - hud_reserve

        # ISO diamond world-unit dimensions: width = W+H, height = (W+H)/2
        dw = float(ww + wh)
        dh = dw * 0.5

        s_w = sw * 0.96 / dw
        s_h = usable_h * 0.96 / dh
        self._iso_s = min(s_w, s_h)
        s = self._iso_s

        # Center diamond horizontally:
        #   diamond x-center = iso_ox + (W - H) * s / 2 = sw / 2
        self._iso_ox = sw / 2.0 - (ww - wh) * s / 2.0
        # Position with upward bias (leave room for HUD below)
        self._iso_oy = (usable_h - dh * s) * 0.35 + 8.0

    def _diamond_corners(self) -> List[Tuple[int, int]]:
        """Four screen-space corners of the world rectangle in ISO projection."""
        ww, wh = self._def.width, self._def.height
        return [
            (int(px), int(py))
            for px, py in [
                self.project(0,  0),
                self.project(ww, 0),
                self.project(ww, wh),
                self.project(0,  wh),
            ]
        ]

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
        sw, sh = self._screen_w, self._screen_h

        # Background (outside diamond)
        surf.fill(_lerp(dk, (18, 26, 14), 0.7))

        # ISO diamond as base fill
        diamond = self._diamond_corners()
        pg.draw.polygon(surf, b, diamond)

        # Bounding box of diamond for scatter
        x0 = min(v[0] for v in diamond)
        y0 = min(v[1] for v in diamond)
        x1 = max(v[0] for v in diamond)
        y1 = max(v[1] for v in diamond)
        area = max(1, (x1 - x0) * (y1 - y0))

        # Two-pass organic scatter (blobs then fine stipple)
        for _ in range(int(area / 1200)):
            x = int(rng.uniform(x0, x1))
            y = int(rng.uniform(y0, y1))
            r = rng.randint(18, 52)
            c = _lerp(b, lt if rng.random() < 0.5 else dk, rng.random() * 0.18)
            pg.draw.circle(surf, c, (x, y), r)
        for _ in range(int(area / 160)):
            x = int(rng.uniform(x0, x1))
            y = int(rng.uniform(y0, y1))
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

        # Project all four corners into screen space
        corners = [
            (int(px), int(py))
            for px, py in [
                self.project(x,     y),
                self.project(x + w, y),
                self.project(x + w, y + h),
                self.project(x,     y + h),
            ]
        ]
        self._pg.draw.polygon(surf, b, corners)

        # Scatter within bounding box
        cx0 = min(v[0] for v in corners); cx1 = max(v[0] for v in corners)
        cy0 = min(v[1] for v in corners); cy1 = max(v[1] for v in corners)
        area = max(1, (cx1 - cx0) * (cy1 - cy0))
        for _ in range(int(area / 260)):
            rx = int(rng.uniform(cx0, cx1))
            ry = int(rng.uniform(cy0, cy1))
            rr = rng.randint(5, 16)
            t2 = rng.random()
            c = _lerp(b, lt, t2 * 0.35) if t2 < 0.4 else (_lerp(b, dk, t2 * 0.25) if t2 < 0.7 else b)
            self._pg.draw.circle(surf, c, (rx, ry), rr)

        # ISO highlight/shadow edges
        self._pg.draw.line(surf, lt, corners[0], corners[1], 3)  # top
        self._pg.draw.line(surf, lt, corners[0], corners[3], 3)  # left
        self._pg.draw.line(surf, dk, corners[2], corners[3], 3)  # bottom
        self._pg.draw.line(surf, dk, corners[1], corners[2], 3)  # right

    def _bake_circle(self, surf, layer: LayerDef, rng: random.Random) -> None:
        if layer.center is None:
            return
        pcx, pcy = self.project(layer.center[0], layer.center[1])
        r  = int(layer.radius * self._iso_s * 1.4)
        p  = layer.effective_palette
        b  = p.get("base",  (46,  92, 38))
        lt = p.get("light", (58, 112, 46))
        dk = p.get("dark",  (32,  68, 26))

        self._pg.draw.circle(surf, b, (int(pcx), int(pcy)), r)
        for _ in range(int(r * 0.7)):
            angle = rng.random() * math.tau
            dist  = rng.random() * r * 0.85
            tx = int(pcx + math.cos(angle) * dist)
            ty = int(pcy + math.sin(angle) * dist)
            cr = rng.randint(max(1, int(r * 0.08)), max(2, int(r * 0.22)))
            shade = _lerp(b, lt if rng.random() < 0.5 else dk, rng.random() * 0.6)
            self._pg.draw.circle(surf, shade, (tx, ty), cr)
        self._pg.draw.arc(
            surf, lt,
            (int(pcx) - r, int(pcy) - r, r * 2, r * 2),
            math.radians(110), math.radians(200),
            max(2, r // 14),
        )

    def _bake_road(self, surf, layer: LayerDef) -> None:
        world_pts  = [(int(p[0]), int(p[1])) for p in layer.points]
        smooth_w   = _chaikin(world_pts, iterations=1)
        projected  = [(int(px), int(py)) for px, py in (self.project(x, y) for x, y in smooth_w)]
        p  = layer.effective_palette
        edge  = p.get("edge",  (152, 128, 72))
        fill  = p.get("fill",  (192, 170, 110))
        ew = int(p.get("edge_width", 10))
        fw = int(p.get("fill_width",  6))
        for i in range(len(projected) - 1):
            self._pg.draw.line(surf, edge, projected[i], projected[i + 1], ew)
        for i in range(len(projected) - 1):
            self._pg.draw.line(surf, fill, projected[i], projected[i + 1], fw)

    def _bake_polygon(self, surf, layer: LayerDef) -> None:
        if not layer.points:
            return
        pts = [(int(px), int(py)) for px, py in (self.project(p[0], p[1]) for p in layer.points)]
        p = layer.effective_palette
        self._pg.draw.polygon(surf, p.get("base", (80, 120, 60)), pts)

    # ------------------------------------------------------------------
    # ISO corner vignette
    # ------------------------------------------------------------------

    def _bake_iso_vignette(self, surf, sw: int, sh: int) -> None:
        """Darken the four corners outside the ISO diamond with a soft alpha mask."""
        pg = self._pg
        diamond = self._diamond_corners()

        mask = pg.Surface((sw, sh), pg.SRCALPHA)
        mask.fill((0, 0, 0, 200))
        # Transparent cut-out over the diamond area
        pg.draw.polygon(mask, (0, 0, 0, 0), diamond)

        # Soft inner glow: progressively lighter rings inward from the edge
        cx = sum(v[0] for v in diamond) // 4
        cy = sum(v[1] for v in diamond) // 4
        for i in range(1, 20):
            t  = i / 20.0
            inner = [
                (int(v[0] + (cx - v[0]) * t * 0.08),
                 int(v[1] + (cy - v[1]) * t * 0.08))
                for v in diamond
            ]
            alpha = int(120 * (1 - t))
            pg.draw.polygon(mask, (0, 0, 0, alpha), inner, 3)

        surf.blit(mask, (0, 0))
        # Hard border
        pg.draw.polygon(surf, (12, 18, 10), diamond, 2)

    # ------------------------------------------------------------------
    # Animated base bake (bank color — per-frame shimmer drawn live)
    # ------------------------------------------------------------------

    def _bake_animated_base(self, surf, layer: LayerDef) -> None:
        if layer.terrain in ("river", "water"):
            self._bake_river_base(surf, layer)

    def _bake_river_base(self, surf, layer: LayerDef) -> None:
        smoothed = self._smoothed.get(layer.id)
        if not smoothed:
            return
        p  = layer.effective_palette
        bank  = p.get("bank",  (118,  96,  58))
        deep  = p.get("deep",  (54,  102, 178))
        bw = int(p.get("bank_width",  24))
        ww = int(p.get("water_width", 15))
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

        # Arc-length parameterisation so dashes are evenly spaced
        lengths = [0.0]
        for i in range(len(smoothed) - 1):
            dx = smoothed[i + 1][0] - smoothed[i][0]
            dy = smoothed[i + 1][1] - smoothed[i][1]
            lengths.append(lengths[-1] + math.hypot(dx, dy))
        total = lengths[-1]
        if total < 1.0:
            return

        spacing  = 36.0
        dash_len = 12.0
        offset   = (t * speed) % spacing

        # One SRCALPHA surface for all shimmer dashes (avoid per-dash allocation)
        overlay = self._pg.Surface((self._screen_w, self._screen_h), self._pg.SRCALPHA)
        dist = offset
        while dist < total:
            d_end = min(dist + dash_len, total)
            ps = _pos_at(smoothed, lengths, dist)
            pe = _pos_at(smoothed, lengths, d_end)
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
