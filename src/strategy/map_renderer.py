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
        # Camera offset in bake-surface pixels (set each frame via set_camera)
        self._cam_x: float = 0.0
        self._cam_y: float = 0.0
        # Baked surface dimensions (set in bake())
        self._bake_w: int = map_def.width
        self._bake_h: int = map_def.height
        # Viewport dimensions (set in bake())
        self._screen_w: int = map_def.width
        self._screen_h: int = map_def.height

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def project(self, wx: float, wy: float) -> Tuple[float, float]:
        """Convert world coordinates to current screen coordinates."""
        return (wx * self._scale - self._cam_x, wy * self._scale - self._cam_y)

    def set_camera(self, cam_x: float, cam_y: float) -> None:
        """Set camera scroll offset (bake-surface pixels)."""
        self._cam_x = cam_x
        self._cam_y = cam_y

    def cam_max(self, screen_w: int, screen_h: int) -> Tuple[float, float]:
        """Return (max_cam_x, max_cam_y) for clamping the camera scroll."""
        return (
            max(0.0, float(self._bake_w - screen_w)),
            max(0.0, float(self._bake_h - screen_h)),
        )

    def bake(self, screen_w: Optional[int] = None, screen_h: Optional[int] = None) -> None:
        """Render all static layers onto a cached Surface of size (world * scale)."""
        sw = screen_w or self._def.width
        sh = screen_h or self._def.height
        self._screen_w = sw
        self._screen_h = sh
        self._bake_w = int(self._def.width * self._scale)
        self._bake_h = int(self._def.height * self._scale)

        pg = self._pg
        surf = pg.Surface((self._bake_w, self._bake_h))
        rng = random.Random(self._def.seed)

        for layer in self._def.layers:
            if layer.animated:
                # Pre-compute smoothed paths in bake space (no cam offset yet)
                if layer.points:
                    world_pts = [(int(p[0]), int(p[1])) for p in layer.points]
                    smooth_world = _chaikin(world_pts, iterations=3)
                    self._smoothed[layer.id] = [
                        (int(wx * self._scale), int(wy * self._scale))
                        for wx, wy in smooth_world
                    ]
                self._bake_animated_base(surf, layer)
            else:
                self._bake_static_layer(surf, layer, rng)

        self._static_surf = surf

    def render(self, screen, time_elapsed: float) -> None:
        """Blit the static surface (panned by camera) then composite animated layers."""
        if self._static_surf is None:
            screen.fill((22, 32, 18))
            return
        cx, cy = int(self._cam_x), int(self._cam_y)
        screen.blit(self._static_surf, (-cx, -cy))
        for layer in self._def.layers:
            if layer.animated:
                self._render_animated_layer(screen, layer, time_elapsed)

    # ------------------------------------------------------------------
    # World → bake coordinate helpers
    # ------------------------------------------------------------------

    def _wb(self, wx: float, wy: float) -> Tuple[int, int]:
        """World coordinates → bake surface coordinates (integer)."""
        return (int(wx * self._scale), int(wy * self._scale))

    def _wbs(self, v) -> int:
        """Scale a scalar world value to bake-surface pixels (minimum 1)."""
        return max(1, int(float(v) * self._scale))

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
        bw, bh = self._bake_w, self._bake_h

        surf.fill(b)

        # Two-pass organic scatter over the full bake surface
        area = bw * bh
        for _ in range(int(area / 1200)):
            x = int(rng.uniform(0, bw))
            y = int(rng.uniform(0, bh))
            r = rng.randint(18, 52)
            c = _lerp(b, lt if rng.random() < 0.5 else dk, rng.random() * 0.18)
            pg.draw.circle(surf, c, (x, y), r)
        for _ in range(int(area / 160)):
            x = int(rng.uniform(0, bw))
            y = int(rng.uniform(0, bh))
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
        for _ in range(int(area / 260)):
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
        cx, cy = int(self._cam_x), int(self._cam_y)
        screen_pts = [(bx - cx, by - cy) for bx, by in smoothed]

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
