"""Sprite registry for the strategic map.

Loads PNG assets from assets/sprites/ when present.
Falls back to procedurally generated placeholder surfaces when not.
All surfaces are cached in-process so they're only built once.
"""

from __future__ import annotations

import math
import pathlib
from typing import Any, Dict, Optional

_SPRITES_DIR = pathlib.Path(__file__).parent.parent.parent / "assets" / "sprites"

# role → accent color for squad tokens
_ROLE_COLORS = {
    "assault":  (220, 90,  60),
    "defense":  (80,  140, 220),
    "support":  (80,  210, 140),
    "hunter":   (200, 160, 50),
    "skirmish": (180, 80,  220),
}

# site-type → (fill, edge) for buildings
_SITE_COLORS = {
    "BASE":     ((72,  96, 148), (140, 180, 255)),
    "TOWN":     ((128, 108, 68), (210, 185, 130)),
    "FORT":     ((100, 100, 112),(180, 175, 200)),
    "TEMPLE":   ((110, 88,  155),(200, 170, 240)),
    "RESOURCE": ((100, 128, 60), (180, 210, 100)),
}

_OWNER_TINT = {
     0: (0,  18, 40,  60),   # allied — blue wash
     1: (50,  0,  0,  60),   # enemy  — red wash
    -1: (0,   0,  0,   0),   # neutral — no tint
}


class SpriteRegistry:
    """Cached sprite surfaces for strategic map rendering."""

    def __init__(self, pygame):
        self._pg = pygame
        self._cache: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Public accessors
    # ------------------------------------------------------------------

    def squad_token(self, owner: int, role: str, w: int = 48, h: int = 56) -> Any:
        key = f"squad_{owner}_{role}_{w}x{h}"
        if key not in self._cache:
            png_key = f"squads/squad_{'allied' if owner == 0 else 'enemy'}_{role.lower()}.png"
            self._cache[key] = self._load_or_placeholder(png_key, w, h,
                                                          lambda: self._make_squad_token(owner, role, w, h))
        return self._cache[key]

    def site_building(self, site_type: str, owner: int, w: int = 80, h: int = 80) -> Any:
        key = f"site_{site_type}_{owner}_{w}x{h}"
        if key not in self._cache:
            variant = "allied" if owner == 0 else ("enemy" if owner == 1 else "neutral")
            sprite_key = self._site_sprite_key(site_type, variant)
            png_key = f"sites/{sprite_key}.png"
            self._cache[key] = self._load_or_placeholder(png_key, w, h,
                                                          lambda: self._make_site_building(site_type, owner, w, h))
        return self._cache[key]

    def hud_clock_frame(self, w: int = 160, h: int = 88) -> Any:
        key = f"hud_clock_{w}x{h}"
        if key not in self._cache:
            self._cache[key] = self._load_or_placeholder("hud/hud_clock_frame.png", w, h,
                                                          lambda: self._make_hud_clock(w, h))
        return self._cache[key]

    # ------------------------------------------------------------------
    # Placeholder generators
    # ------------------------------------------------------------------

    def _make_squad_token(self, owner: int, role: str, w: int, h: int) -> Any:
        pg = self._pg
        surf = pg.Surface((w, h), pg.SRCALPHA)

        # Body circle
        body_color = (80, 140, 200) if owner == 0 else (200, 80, 80)
        cx, cy = w // 2, h // 2 + 4
        r = min(w, h) // 2 - 5
        pg.draw.circle(surf, body_color, (cx, cy), r)

        # Role accent ring
        accent = _ROLE_COLORS.get(role.lower(), (200, 200, 200))
        pg.draw.circle(surf, accent, (cx, cy), r, 3)

        # Dark outline
        pg.draw.circle(surf, (20, 20, 30), (cx, cy), r, 1)

        # Shadow  (semi-transparent dark oval at bottom)
        shadow = pg.Surface((w, 10), pg.SRCALPHA)
        pg.draw.ellipse(shadow, (0, 0, 0, 80), (4, 2, w - 8, 6))
        surf.blit(shadow, (0, h - 12))

        return surf

    def _make_site_building(self, site_type: str, owner: int, w: int, h: int) -> Any:
        pg = self._pg
        surf = pg.Surface((w, h), pg.SRCALPHA)

        fill, edge = _SITE_COLORS.get(site_type.upper(), ((120, 120, 120), (200, 200, 200)))

        # ISO body: pseudo-isometric box
        cx = w // 2
        by = h - 8          # bottom of building

        if site_type.upper() == "FORT":
            self._draw_iso_tower(surf, cx, by, w, h, fill, edge, pg)
        elif site_type.upper() == "BASE":
            self._draw_iso_gatehouse(surf, cx, by, w, h, fill, edge, pg, owner)
        elif site_type.upper() == "TOWN":
            self._draw_iso_town(surf, cx, by, w, h, fill, edge, pg)
        elif site_type.upper() == "TEMPLE":
            self._draw_iso_spire(surf, cx, by, w, h, fill, edge, pg)
        else:
            self._draw_iso_box(surf, cx, by, w, h, fill, edge, pg)

        # Owner tint overlay
        tint = _OWNER_TINT.get(owner, (0, 0, 0, 0))
        if tint[3] > 0:
            t = pg.Surface((w, h), pg.SRCALPHA)
            t.fill(tint)
            surf.blit(t, (0, 0))

        return surf

    # --- ISO shape helpers ---

    def _draw_iso_box(self, surf, cx, by, w, h, fill, edge, pg):
        bw, bh = int(w * 0.6), int(h * 0.5)
        rect = (cx - bw // 2, by - bh, bw, bh)
        pg.draw.rect(surf, fill, rect)
        pg.draw.rect(surf, edge, rect, 2)
        # roof parallelogram
        roof = [(cx - bw // 2, by - bh), (cx, by - bh - int(h * 0.25)),
                (cx + bw // 2, by - bh), (cx, by - bh + 2)]
        pg.draw.polygon(surf, edge, roof)

    def _draw_iso_tower(self, surf, cx, by, w, h, fill, edge, pg):
        bw, bh = int(w * 0.46), int(h * 0.55)
        rect = (cx - bw // 2, by - bh, bw, bh)
        pg.draw.rect(surf, fill, rect)
        pg.draw.rect(surf, edge, rect, 2)
        # battlements
        bt_w = max(4, bw // 5)
        for i in range(5):
            if i % 2 == 0:
                bx = cx - bw // 2 + i * bt_w
                pg.draw.rect(surf, edge, (bx, by - bh - bt_w, bt_w, bt_w))
        # ISO roof shadow
        shadow_pts = [(cx - bw // 2, by - bh), (cx, by - bh - int(h * 0.18)),
                      (cx + bw // 2, by - bh)]
        pg.draw.polygon(surf, _lerp3(fill, (255, 255, 255), 0.35), shadow_pts)

    def _draw_iso_gatehouse(self, surf, cx, by, w, h, fill, edge, pg, owner):
        bw, bh = int(w * 0.7), int(h * 0.6)
        rect = (cx - bw // 2, by - bh, bw, bh)
        pg.draw.rect(surf, fill, rect)
        pg.draw.rect(surf, edge, rect, 2)
        # arch
        arch_w = max(8, bw // 3)
        arch_h = max(8, bh // 3)
        arch_rect = (cx - arch_w // 2, by - arch_h, arch_w, arch_h)
        pg.draw.rect(surf, (20, 20, 30), arch_rect)
        pg.draw.arc(surf, edge, (cx - arch_w // 2, by - arch_h - arch_w // 2, arch_w, arch_w),
                    0, math.pi, 2)
        # pennant
        pennant_color = (60, 120, 220) if owner == 0 else (200, 40, 40)
        pole_x, pole_y = cx + bw // 4, by - bh - 2
        pg.draw.line(surf, (160, 160, 160), (pole_x, pole_y), (pole_x, pole_y - int(h * 0.35)), 2)
        flag = [(pole_x, pole_y - int(h * 0.35)),
                (pole_x + int(w * 0.22), pole_y - int(h * 0.28)),
                (pole_x, pole_y - int(h * 0.18))]
        pg.draw.polygon(surf, pennant_color, flag)

    def _draw_iso_town(self, surf, cx, by, w, h, fill, edge, pg):
        # Three small buildings
        offsets = [(-int(w * 0.22), 0), (0, -int(h * 0.08)), (int(w * 0.2), int(h * 0.04))]
        sizes   = [(int(w * 0.32), int(h * 0.38)),
                   (int(w * 0.38), int(h * 0.45)),
                   (int(w * 0.28), int(h * 0.32))]
        for (ox, oy), (bw, bh) in zip(offsets, sizes):
            r = (cx + ox - bw // 2, by + oy - bh, bw, bh)
            pg.draw.rect(surf, fill, r)
            pg.draw.rect(surf, edge, r, 2)
            # pitched roof
            roof = [(cx + ox - bw // 2, by + oy - bh),
                    (cx + ox,            by + oy - bh - int(bh * 0.45)),
                    (cx + ox + bw // 2, by + oy - bh)]
            pg.draw.polygon(surf, _lerp3(fill, (240, 200, 140), 0.5), roof)
            pg.draw.lines(surf, edge, False, roof, 1)

    def _draw_iso_spire(self, surf, cx, by, w, h, fill, edge, pg):
        bw, bh = int(w * 0.44), int(h * 0.52)
        rect = (cx - bw // 2, by - bh, bw, bh)
        pg.draw.rect(surf, fill, rect)
        pg.draw.rect(surf, edge, rect, 2)
        # arched windows
        for wx in [cx - bw // 4, cx + bw // 4]:
            wh = max(6, bh // 4)
            pg.draw.rect(surf, (20, 20, 50), (wx - 4, by - bh + 8, 8, wh))
        # spire
        spire = [(cx - bw // 6, by - bh),
                 (cx,           by - bh - int(h * 0.42)),
                 (cx + bw // 6, by - bh)]
        pg.draw.polygon(surf, _lerp3(fill, (255, 255, 255), 0.5), spire)
        pg.draw.lines(surf, edge, True, spire, 1)

    # ------------------------------------------------------------------
    # Clock HUD placeholder
    # ------------------------------------------------------------------

    def _make_hud_clock(self, w: int, h: int) -> Any:
        pg = self._pg
        surf = pg.Surface((w, h), pg.SRCALPHA)
        # Brass plate
        pg.draw.rect(surf, (80, 62, 30, 220), (0, 0, w, h), border_radius=8)
        pg.draw.rect(surf, (160, 130, 60, 255), (0, 0, w, h), 2, border_radius=8)
        # Gear motif (circle with notches)
        gx, gy, gr = w - 28, 20, 14
        pg.draw.circle(surf, (130, 100, 40, 200), (gx, gy), gr)
        pg.draw.circle(surf, (180, 145, 60, 255), (gx, gy), gr, 2)
        for i in range(8):
            angle = i * math.tau / 8
            nx = int(gx + math.cos(angle) * (gr + 4))
            ny = int(gy + math.sin(angle) * (gr + 4))
            pg.draw.circle(surf, (180, 145, 60, 200), (nx, ny), 3)
        return surf

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_or_placeholder(self, rel_path: str, w: int, h: int, fallback) -> Any:
        full = _SPRITES_DIR / rel_path
        if full.exists():
            try:
                img = self._pg.image.load(str(full)).convert_alpha()
                return self._pg.transform.scale(img, (w, h))
            except Exception:
                pass
        return fallback()

    @staticmethod
    def _site_sprite_key(site_type: str, variant: str) -> str:
        mapping = {
            "BASE":     f"base_{'allied' if variant == 'allied' else 'enemy'}_owned",
            "FORT":     f"fort_stone_{variant}",
            "TOWN":     f"town_small_{variant}",
            "TEMPLE":   f"temple_sky_{variant}",
            "RESOURCE": f"resource_ore_{variant}",
        }
        return mapping.get(site_type.upper(), f"fort_stone_{variant}")


# ---------------------------------------------------------------------------

def _lerp3(a, b, t):
    t = max(0.0, min(1.0, t))
    return (int(a[0] + (b[0] - a[0]) * t),
            int(a[1] + (b[1] - a[1]) * t),
            int(a[2] + (b[2] - a[2]) * t))
