"""MapRenderer — bakes static terrain layers once, composites animated layers each frame.

Usage
-----
    renderer = MapRenderer(map_def, pygame)
    renderer.bake()                          # call once after pygame is ready

    # in game loop:
    renderer.render(screen, time_elapsed)    # static blit + animated overlays

Extending
---------
To add a new animated terrain, add an entry to ANIMATED_TERRAINS in map_def.py
and add a matching `_render_animated_<terrain>` method here.
The dispatcher in `_render_animated_layer` will call it automatically.
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
        # Pre-computed smoothed paths per animated layer id
        self._smoothed: Dict[str, List[Tuple[int, int]]] = {}
        self._rng = random.Random(map_def.seed)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def bake(self) -> None:
        """Render all non-animated layers to a cached Surface.
        Must be called after pygame.display is initialised.
        """
        pg = self._pg
        w, h = self._def.width, self._def.height
        surf = pg.Surface((w, h))
        rng = random.Random(self._def.seed)

        for layer in self._def.layers:
            if layer.animated:
                # Pre-compute smoothed path for animated draw, bake base color only
                if layer.points:
                    self._smoothed[layer.id] = _chaikin(
                        [(int(p[0]), int(p[1])) for p in layer.points],
                        iterations=3,
                    )
                self._bake_animated_base(surf, layer)
            else:
                self._bake_static_layer(surf, layer, rng)

        self._static_surf = surf

    def render(self, screen, time_elapsed: float) -> None:
        """Blit the static surface then composite all animated layers."""
        if self._static_surf is None:
            screen.fill((64, 100, 48))
            return

        w, h = screen.get_size()
        sw, sh = self._static_surf.get_size()
        if (sw, sh) != (w, h):
            scaled = self._pg.transform.scale(self._static_surf, (w, h))
            screen.blit(scaled, (0, 0))
        else:
            screen.blit(self._static_surf, (0, 0))

        for layer in self._def.layers:
            if layer.animated:
                self._render_animated_layer(screen, layer, time_elapsed)

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
            self._bake_polygon(surf, layer, rng)

    def _bake_fill(self, surf, layer: LayerDef, rng: random.Random) -> None:
        p = layer.effective_palette
        w, h = self._def.width, self._def.height
        surf.fill(p.get("base", (80, 120, 60)))
        b = p.get("base", (80, 120, 60))
        lt = p.get("light", b)
        dk = p.get("dark", b)
        # Scatter two passes: medium blobs + fine stipple
        for _ in range((w * h) // 1200):
            x = rng.randint(0, w)
            y = rng.randint(0, h)
            r = rng.randint(28, 62)
            c = _lerp(b, lt if rng.random() < 0.5 else dk, rng.random() * 0.18)
            self._pg.draw.circle(surf, c, (x, y), r)
        for _ in range((w * h) // 180):
            x = rng.randint(0, w)
            y = rng.randint(0, h)
            r = rng.randint(2, 8)
            c = _lerp(b, lt if rng.random() < 0.5 else dk, rng.random() * 0.13)
            self._pg.draw.circle(surf, c, (x, y), r)

    def _bake_rect(self, surf, layer: LayerDef, rng: random.Random) -> None:
        if layer.rect is None:
            return
        x, y, w, h = (int(v) for v in layer.rect)
        p = layer.effective_palette
        b  = p.get("base",  (140, 120, 80))
        lt = p.get("light", (180, 160, 100))
        dk = p.get("dark",  (110,  90, 55))
        # Tiled scatter within rect
        scale = 14
        cols = max(1, w // scale + 2)
        rows = max(1, h // scale + 2)
        for gy in range(rows):
            for gx in range(cols):
                t = rng.random()
                c = _lerp(b, lt, t * 0.35) if t < 0.4 else (_lerp(b, dk, t * 0.25) if t < 0.7 else b)
                rx = x + gx * scale
                ry = y + gy * scale
                rw = min(scale, x + w - rx)
                rh_ = min(scale, y + h - ry)
                if rw > 0 and rh_ > 0:
                    self._pg.draw.rect(surf, c, (rx, ry, rw, rh_))
        # ISO edge highlight/shadow
        self._pg.draw.line(surf, lt, (x, y + h), (x, y), 3)
        self._pg.draw.line(surf, lt, (x, y), (x + w, y), 3)
        self._pg.draw.line(surf, dk, (x + w, y), (x + w, y + h), 3)
        self._pg.draw.line(surf, dk, (x, y + h), (x + w, y + h), 3)

    def _bake_circle(self, surf, layer: LayerDef, rng: random.Random) -> None:
        if layer.center is None:
            return
        cx, cy = int(layer.center[0]), int(layer.center[1])
        r = int(layer.radius)
        p = layer.effective_palette
        b  = p.get("base",  (46, 92, 38))
        lt = p.get("light", (58, 112, 46))
        dk = p.get("dark",  (32, 68, 26))
        self._pg.draw.circle(surf, b, (cx, cy), r)
        for _ in range(int(r * 0.6)):
            angle = rng.random() * math.tau
            dist = rng.random() * r * 0.85
            tx = cx + int(math.cos(angle) * dist)
            ty = cy + int(math.sin(angle) * dist)
            cr = rng.randint(int(r * 0.08), int(r * 0.22))
            shade = _lerp(b, lt if rng.random() < 0.5 else dk, rng.random() * 0.6)
            self._pg.draw.circle(surf, shade, (tx, ty), cr)
        self._pg.draw.arc(
            surf, lt,
            (cx - r, cy - r, r * 2, r * 2),
            math.radians(110), math.radians(200),
            max(2, r // 14),
        )

    def _bake_road(self, surf, layer: LayerDef) -> None:
        pts = [(int(p[0]), int(p[1])) for p in layer.points]
        smoothed = _chaikin(pts, iterations=1)
        p = layer.effective_palette
        edge  = p.get("edge",  (152, 128, 72))
        fill  = p.get("fill",  (192, 170, 110))
        ew = int(p.get("edge_width", 10))
        fw = int(p.get("fill_width", 6))
        for i in range(len(smoothed) - 1):
            self._pg.draw.line(surf, edge, smoothed[i], smoothed[i + 1], ew)
        for i in range(len(smoothed) - 1):
            self._pg.draw.line(surf, fill, smoothed[i], smoothed[i + 1], fw)

    def _bake_polygon(self, surf, layer: LayerDef, rng: random.Random) -> None:
        if not layer.points:
            return
        pts = [(int(p[0]), int(p[1])) for p in layer.points]
        p = layer.effective_palette
        b = p.get("base", (80, 120, 60))
        self._pg.draw.polygon(surf, b, pts)

    # ------------------------------------------------------------------
    # Animated base bake (bank / bed color — no shimmering)
    # ------------------------------------------------------------------

    def _bake_animated_base(self, surf, layer: LayerDef) -> None:
        """Bake only the non-moving parts of an animated terrain (e.g. river bank)."""
        terrain = layer.terrain
        if terrain in ("river", "water"):
            self._bake_river_base(surf, layer)

    def _bake_river_base(self, surf, layer: LayerDef) -> None:
        smoothed = self._smoothed.get(layer.id)
        if not smoothed:
            return
        p = layer.effective_palette
        bank  = p.get("bank",  (118, 96, 58))
        deep  = p.get("deep",  (54, 102, 178))
        bw = int(p.get("bank_width", 24))
        ww = int(p.get("water_width", 15))
        for i in range(len(smoothed) - 1):
            self._pg.draw.line(surf, bank, smoothed[i], smoothed[i + 1], bw)
        for i in range(len(smoothed) - 1):
            self._pg.draw.line(surf, deep, smoothed[i], smoothed[i + 1], ww)

    # ------------------------------------------------------------------
    # Per-frame animated layer dispatch
    # ------------------------------------------------------------------

    def _render_animated_layer(self, screen, layer: LayerDef, t: float) -> None:
        terrain = layer.terrain
        if terrain in ("river", "water"):
            self._render_animated_river(screen, layer, t)
        # Future: lava, magic_pool, etc.

    def _render_animated_river(self, screen, layer: LayerDef, t: float) -> None:
        smoothed = self._smoothed.get(layer.id)
        if not smoothed or len(smoothed) < 2:
            return

        p = layer.effective_palette
        shimmer_color = p.get("light", (88, 148, 220))
        speed = float(p.get("shimmer_speed", 55.0))

        # Build cumulative arc-length parameterization
        lengths = [0.0]
        for i in range(len(smoothed) - 1):
            dx = smoothed[i + 1][0] - smoothed[i][0]
            dy = smoothed[i + 1][1] - smoothed[i][1]
            lengths.append(lengths[-1] + math.hypot(dx, dy))
        total = lengths[-1]
        if total < 1.0:
            return

        # Draw shimmer dashes every `spacing` pixels, offset by time
        spacing = 38.0
        dash_len = 14.0
        offset = (t * speed) % spacing

        dist = offset
        while dist < total:
            d_start = dist
            d_end = min(dist + dash_len, total)
            p_start = _pos_at(smoothed, lengths, d_start)
            p_end   = _pos_at(smoothed, lengths, d_end)
            # Vary alpha slightly per dash using positional seed
            alpha = int(140 + 60 * math.sin(dist * 0.18 + t * 1.4))
            surf = self._pg.Surface((self._def.width, self._def.height), self._pg.SRCALPHA)
            self._pg.draw.line(
                surf,
                (*shimmer_color, alpha),
                (int(p_start[0]), int(p_start[1])),
                (int(p_end[0]), int(p_end[1])),
                3,
            )
            screen.blit(surf, (0, 0))
            dist += spacing


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
    """Interpolate a position at arc-length d along the polyline."""
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
