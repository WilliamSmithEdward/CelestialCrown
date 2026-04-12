"""Procedural terrain background generator for the strategic mission map.

Generates a static Surface using the terrain_features in a scenario config.
The result is cached to assets/maps/ by scenario_id + seed so it's only
computed once per seed change.

Isometric aesthetic is achieved via:
  - Angled highlight/shadow on terrain patches (top-left light source)
  - Layered noise passes for natural colour variation
  - River rendered with spline-like smooth polyline + banks
  - Dirt roads as double-edge sandy strips
"""

from __future__ import annotations

import hashlib
import math
import pathlib
import random
from typing import Any, Dict, List, NamedTuple, Optional, Tuple

_CACHE_DIR = pathlib.Path(__file__).parent.parent.parent / "assets" / "maps"
_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------

_GRASS_BASE   = (88,  138,  62)
_GRASS_LIGHT  = (106, 158,  74)
_GRASS_DARK   = (64,  108,  44)
_HIGHLAND_BASE  = (164, 138,  84)
_HIGHLAND_LIGHT = (188, 162, 104)
_HIGHLAND_DARK  = (132, 106,  62)
_FOREST_BASE  = (46,  92,   38)
_FOREST_LIGHT = (58,  112,  46)
_FOREST_DARK  = (32,  68,   26)
_RIVER_DEEP   = (54,  102, 178)
_RIVER_LIGHT  = (88,  148, 220)
_RIVER_BANK   = (162, 148,  96)
_ROAD_FILL    = (192, 170, 110)
_ROAD_EDGE    = (152, 128,  72)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_map_surface(scenario_id: str, map_cfg: Dict[str, Any], pygame) -> Any:
    """Return a pygame Surface for the terrain background.

    If a cached PNG exists for (scenario_id, seed) it is loaded directly.
    Otherwise the surface is generated and saved.
    """
    width  = int(map_cfg.get("width",  1280))
    height = int(map_cfg.get("height",  720))
    seed   = int(map_cfg.get("terrain_seed", 0))
    cache_key = f"{scenario_id}_{seed}_{width}x{height}"
    cache_hash = hashlib.md5(cache_key.encode()).hexdigest()[:12]
    cache_path = _CACHE_DIR / f"terrain_{cache_hash}.png"

    if cache_path.exists():
        return pygame.image.load(str(cache_path)).convert()

    surf = _generate(width, height, seed, map_cfg.get("terrain_features", []), pygame)
    pygame.image.save(surf, str(cache_path))
    return surf


def invalidate_cache():
    """Delete all cached terrain PNGs (call after changing terrain_features)."""
    for p in _CACHE_DIR.glob("terrain_*.png"):
        p.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Internal generation
# ---------------------------------------------------------------------------

def _generate(width: int, height: int, seed: int,
              features: List[Dict[str, Any]], pygame) -> Any:
    rng = random.Random(seed)
    surf = pygame.Surface((width, height))

    # 1. Base grass layer with dithered noise
    _fill_noise(surf, width, height, rng, _GRASS_BASE, _GRASS_LIGHT, _GRASS_DARK, scale=48)

    # 2. Terrain features
    for feat in features:
        ftype = feat.get("type", "")
        if ftype == "highland":
            _draw_highland(surf, feat["rect"], rng, pygame)
        elif ftype == "forest":
            _draw_forest(surf, feat["center"], feat["radius"], rng, pygame)

    # 3. River (drawn before road so road overlaps banks)
    for feat in features:
        if feat.get("type") == "river":
            _draw_river(surf, feat["points"], rng, pygame)

    # 4. Roads
    for feat in features:
        if feat.get("type") == "road":
            _draw_road(surf, feat["points"], pygame)

    # 5. Isometric vignette (darken edges slightly)
    _iso_vignette(surf, width, height, pygame)

    return surf


# ---------------------------------------------------------------------------
# Sub-renderers
# ---------------------------------------------------------------------------

def _fill_noise(surf, width: int, height: int, rng: random.Random,
                base, light, dark, scale: int = 48) -> None:
    """Fill surface with per-cell colour noise at `scale` pixel block size."""
    cols = max(1, width  // scale + 2)
    rows = max(1, height // scale + 2)
    for gy in range(rows):
        for gx in range(cols):
            r2 = rng.random()
            if r2 < 0.33:
                c = _lerp_color(base, light, rng.random() * 0.5)
            elif r2 < 0.66:
                c = _lerp_color(base, dark, rng.random() * 0.4)
            else:
                c = base
            x0 = gx * scale
            y0 = gy * scale
            import pygame as pg
            pg.draw.rect(surf, c, (x0, y0, scale, scale))


def _draw_highland(surf, rect: List[int], rng: random.Random, pygame) -> None:
    x, y, w, h = rect
    # Base plateau colour with noise
    _fill_noise_rect(surf, x, y, w, h, rng, _HIGHLAND_BASE, _HIGHLAND_LIGHT, _HIGHLAND_DARK, pygame)
    # Top-left highlight edge (ISO light source)
    pygame.draw.line(surf, _HIGHLAND_LIGHT, (x, y + h), (x, y), 3)
    pygame.draw.line(surf, _HIGHLAND_LIGHT, (x, y), (x + w, y), 3)
    # Bottom-right shadow edge
    pygame.draw.line(surf, _HIGHLAND_DARK, (x + w, y), (x + w, y + h), 3)
    pygame.draw.line(surf, _HIGHLAND_DARK, (x, y + h), (x + w, y + h), 3)


def _fill_noise_rect(surf, x: int, y: int, w: int, h: int, rng: random.Random,
                     base, light, dark, pygame) -> None:
    scale = 32
    cols = max(1, w // scale + 2)
    rows = max(1, h // scale + 2)
    for gy in range(rows):
        for gx in range(cols):
            r2 = rng.random()
            c = _lerp_color(base, light, r2 * 0.5) if r2 < 0.4 else (_lerp_color(base, dark, r2 * 0.3) if r2 < 0.7 else base)
            rx = x + gx * scale
            ry = y + gy * scale
            rw = min(scale, x + w - rx)
            rh = min(scale, y + h - ry)
            if rw > 0 and rh > 0:
                pygame.draw.rect(surf, c, (rx, ry, rw, rh))


def _draw_forest(surf, center: List[float], radius: float,
                 rng: random.Random, pygame) -> None:
    cx, cy = int(center[0]), int(center[1])
    r = int(radius)
    # Fill base
    pygame.draw.circle(surf, _FOREST_BASE, (cx, cy), r)
    # Cluster-dots for canopy texture
    num_clusters = int(radius * 0.6)
    for _ in range(num_clusters):
        angle = rng.random() * math.tau
        dist  = rng.random() * radius * 0.85
        tx = cx + int(math.cos(angle) * dist)
        ty = cy + int(math.sin(angle) * dist)
        cr = rng.randint(int(radius * 0.08), int(radius * 0.22))
        shade = _lerp_color(_FOREST_BASE, _FOREST_LIGHT if rng.random() < 0.5 else _FOREST_DARK, rng.random() * 0.6)
        pygame.draw.circle(surf, shade, (tx, ty), cr)
    # ISO highlight arc top-left
    pygame.draw.arc(surf, _FOREST_LIGHT,
                    (cx - r, cy - r, r * 2, r * 2),
                    math.radians(110), math.radians(200), max(2, r // 14))


def _draw_river(surf, points: List[List[float]], rng: random.Random, pygame) -> None:
    pts = [(int(p[0]), int(p[1])) for p in points]
    smoothed = _chaikin(pts, iterations=3)

    # Bank (sandy edge, slightly wider)
    for i in range(len(smoothed) - 1):
        pygame.draw.line(surf, _RIVER_BANK, smoothed[i], smoothed[i + 1], 18)

    # Deep water
    for i in range(len(smoothed) - 1):
        pygame.draw.line(surf, _RIVER_DEEP, smoothed[i], smoothed[i + 1], 12)

    # Light shimmer strip
    for i in range(len(smoothed) - 1):
        mx = (smoothed[i][0] + smoothed[i + 1][0]) // 2
        my = (smoothed[i][1] + smoothed[i + 1][1]) // 2
        pygame.draw.line(surf, _RIVER_LIGHT, smoothed[i], (mx, my), 3)


def _draw_road(surf, points: List[List[float]], pygame) -> None:
    pts = [(int(p[0]), int(p[1])) for p in points]
    smoothed = _chaikin(pts, iterations=2)

    # Outer edge (darker)
    for i in range(len(smoothed) - 1):
        pygame.draw.line(surf, _ROAD_EDGE, smoothed[i], smoothed[i + 1], 10)

    # Fill (sandy)
    for i in range(len(smoothed) - 1):
        pygame.draw.line(surf, _ROAD_FILL, smoothed[i], smoothed[i + 1], 6)


def _iso_vignette(surf, width: int, height: int, pygame) -> None:
    """Darken the map perimeter to reinforce the isometric inward-focus feel."""
    overlay = pygame.Surface((width, height), pygame.SRCALPHA)
    margin = 80
    for i in range(margin):
        alpha = int(120 * (1 - i / margin))
        c = (0, 0, 0, alpha)
        pygame.draw.rect(overlay, c, (i, i, width - i * 2, height - i * 2), 1)
    surf.blit(overlay, (0, 0))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _chaikin(pts: List[Tuple[int, int]], iterations: int = 2) -> List[Tuple[int, int]]:
    """Chaikin curve smoothing."""
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


def _lerp_color(a: Tuple[int, int, int], b: Tuple[int, int, int], t: float) -> Tuple[int, int, int]:
    t = max(0.0, min(1.0, t))
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )
