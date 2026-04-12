"""Animated background effect orchestration."""

import math
import random
from typing import List, Tuple

import pygame
import pygame.gfxdraw

from .primitives import OrbEffect, _draw_aa_filled_circle, _mix_color, _scale_color


class AnimatedBackground:
    """Mystical animated background with orbs and energy effects."""

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.orbs: List[OrbEffect] = []
        self.time = 0.0
        self.stars: List[Tuple[float, float, int]] = []
        self.star_tints: List[Tuple[int, int, int]] = []
        self.shooting_stars: List[dict] = []
        self.energy_waves: List[dict] = []
        self.show_energy_waves = False
        self.nebulae: List[dict] = []
        self.dust_motes: List[Tuple[float, float, int]] = []
        self.light_shafts: List[dict] = []
        self.aurora_bands: List[dict] = []
        self.show_light_shafts = False
        self.show_aurora_bands = False
        self.show_nebula_circles = False
        self.show_dust_motes = False
        self.avoid_regions: List[pygame.Rect] = []
        self.base_background = self._build_base_background(width, height)
        self.sorted_orbs: List[OrbEffect] = []

        colors = [
            (132, 188, 255),
            (186, 226, 255),
            (255, 244, 208),
            (255, 218, 138),
            (255, 178, 114),
            (255, 142, 112),
            (174, 146, 255),
            (120, 236, 255),
            (255, 156, 222),
        ]

        positions = [
            (width * 0.2, height * 0.2),
            (width * 0.5, height * 0.15),
            (width * 0.8, height * 0.3),
            (width * 0.3, height * 0.6),
            (width * 0.7, height * 0.7),
            (width * 0.5, height * 0.5),
            (width * 0.15, height * 0.4),
            (width * 0.85, height * 0.8),
            (width * 0.45, height * 0.25),
            (width * 0.65, height * 0.35),
        ]
        for x, y in positions:
            self.orbs.append(OrbEffect(x, y, random.choice(colors), random.uniform(20, 45)))
        self.sorted_orbs = sorted(self.orbs, key=lambda o: o.depth)

        star_count = 400 if (width * height) > 2000000 else 150
        for _ in range(star_count):
            self.stars.append((random.uniform(0, width), random.uniform(0, height), random.randint(50, 200)))
            self.star_tints.append(random.choice([(230, 235, 255), (255, 244, 220), (210, 230, 255), (255, 216, 178), (210, 255, 250)]))

        for _ in range(12):
            self.nebulae.append(
                {
                    "x": random.uniform(0, width),
                    "y": random.uniform(0, height),
                    "radius": random.uniform(180, 420),
                    "drift": random.uniform(8, 22),
                    "phase": random.uniform(0, math.tau),
                    "color": random.choice([(96, 78, 160), (68, 104, 174), (116, 70, 132), (70, 130, 164)]),
                }
            )

        for _ in range(7):
            self.light_shafts.append(
                {
                    "x": random.uniform(-width * 0.1, width * 1.1),
                    "spread": random.uniform(120, 280),
                    "reach": random.uniform(height * 0.35, height * 0.85),
                    "phase": random.uniform(0, math.tau),
                    "speed": random.uniform(0.08, 0.2),
                    "alpha": random.randint(12, 28),
                    "color": random.choice([(126, 106, 184), (100, 140, 196), (144, 116, 168)]),
                }
            )

        for i in range(4):
            self.aurora_bands.append(
                {
                    "base_y": height * (0.22 + i * 0.08),
                    "amp": random.uniform(18, 42),
                    "freq": random.uniform(0.006, 0.012),
                    "speed": random.uniform(18, 36),
                    "phase": random.uniform(0, math.tau),
                    "color": random.choice([(116, 148, 220), (138, 112, 208), (92, 170, 206)]),
                }
            )

        for _ in range(220):
            self.dust_motes.append((random.uniform(0, width), random.uniform(0, height), random.randint(20, 80)))

        self.vignette = self._build_vignette_surface(width, height)

        for i in range(5):
            self.energy_waves.append(
                {
                    "y": height * (0.1 + i * 0.15),
                    "speed": random.uniform(30, 80),
                    "amplitude": random.uniform(40, 80),
                    "color": random.choice(colors),
                }
            )

    def _build_base_background(self, width: int, height: int) -> pygame.Surface:
        base = pygame.Surface((width, height), pygame.SRCALPHA)
        for y in range(height):
            ratio = y / max(1, height)
            pygame.draw.line(base, (int(20 + ratio * 34), int(16 + ratio * 26), int(42 + ratio * 66)), (0, y), (width, y))

        grade = pygame.Surface((width, height), pygame.SRCALPHA)
        for y in range(height):
            t = y / max(1, height)
            cool = _mix_color((12, 24, 78), (22, 12, 48), t)
            pygame.draw.line(grade, (cool[0], cool[1], cool[2], int(28 + 14 * (1.0 - t))), (0, y), (width, y))
        base.blit(grade, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        return base

    def set_avoid_regions(self, regions: List[pygame.Rect]) -> None:
        self.avoid_regions = list(regions)

    def _is_in_avoid_region(self, x: float, y: float, padding: int = 0) -> bool:
        for region in self.avoid_regions:
            if padding > 0:
                if region.inflate(padding * 2, padding * 2).collidepoint(x, y):
                    return True
            elif region.collidepoint(x, y):
                return True
        return False

    def update(self, delta_time: float) -> None:
        self.time += delta_time
        for orb in self.orbs:
            orb.update(delta_time)

        if random.random() < 0.3:
            self.shooting_stars.append(
                {
                    "x": random.uniform(0, self.width),
                    "y": random.uniform(0, self.height * 0.3),
                    "vx": random.uniform(100, 300),
                    "vy": random.uniform(50, 150),
                    "lifetime": random.uniform(0.5, 1.5),
                    "max_lifetime": 1.0,
                    "color": random.choice([(255, 220, 100), (200, 220, 255), (255, 180, 100)]),
                }
            )

        for star in self.shooting_stars:
            star["x"] += star["vx"] * delta_time
            star["y"] += star["vy"] * delta_time
            star["lifetime"] -= delta_time
        self.shooting_stars = [s for s in self.shooting_stars if s["lifetime"] > 0]

    def _build_vignette_surface(self, width: int, height: int) -> pygame.Surface:
        vignette = pygame.Surface((width, height), pygame.SRCALPHA)
        cx = width // 2
        cy = height // 2
        max_dist = math.hypot(cx, cy)
        for y in range(height):
            for x in range(width):
                dist = math.hypot(x - cx, y - cy)
                ratio = dist / max_dist
                if ratio > 0.55:
                    vignette.set_at((x, y), (8, 10, 18, int(min(120, (ratio - 0.55) * 220))))
        return vignette

    def _draw_nebula_texture(self, surface: pygame.Surface) -> None:
        layer = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        for nebula in self.nebulae:
            drift_x = math.cos(self.time * 0.08 + nebula["phase"]) * nebula["drift"]
            drift_y = math.sin(self.time * 0.06 + nebula["phase"]) * nebula["drift"]
            cx = int(nebula["x"] + drift_x)
            cy = int(nebula["y"] + drift_y)
            base_radius = int(nebula["radius"])
            color = nebula["color"]
            for layer_idx in range(4, 0, -1):
                pygame.draw.circle(layer, (*color, int(10 + 8 * layer_idx)), (cx, cy), max(12, int(base_radius * layer_idx / 4)))
        surface.blit(layer, (0, 0))

    def _draw_light_shafts(self, surface: pygame.Surface) -> None:
        layer = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        for shaft in self.light_shafts:
            sway = math.sin(self.time * shaft["speed"] + shaft["phase"]) * 90
            cx = shaft["x"] + sway
            spread = shaft["spread"]
            reach = shaft["reach"]
            c = shaft["color"]
            a = shaft["alpha"]
            poly = [(int(cx - spread * 0.24), 0), (int(cx + spread * 0.24), 0), (int(cx + spread), int(reach)), (int(cx - spread), int(reach))]
            pygame.draw.polygon(layer, (c[0], c[1], c[2], a), poly)
        surface.blit(layer, (0, 0))

    def _draw_aurora_ribbons(self, surface: pygame.Surface) -> None:
        layer = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        step = 56
        for band in self.aurora_bands:
            prev = None
            for x in range(-step, self.width + step, step):
                y = band["base_y"] + math.sin((x * band["freq"]) + (self.time * band["speed"] * 0.01) + band["phase"]) * band["amp"]
                current = (x, int(y))
                if prev:
                    c = band["color"]
                    pygame.draw.aaline(layer, (c[0], c[1], c[2], 66), prev, current)
                    pygame.draw.aaline(layer, (c[0], c[1], c[2], 28), (prev[0], prev[1] + 2), (current[0], current[1] + 2))
                prev = current
        surface.blit(layer, (0, 0))

    def draw(self, surface: pygame.Surface) -> None:
        surface.blit(self.base_background, (0, 0))
        if self.show_light_shafts:
            self._draw_light_shafts(surface)
        if self.show_nebula_circles:
            self._draw_nebula_texture(surface)
        if self.show_aurora_bands:
            self._draw_aurora_ribbons(surface)

        for idx, (x, y, brightness) in enumerate(self.stars):
            if self._is_in_avoid_region(x, y, padding=6):
                continue
            alpha = (brightness + int(90 * math.sin(self.time * 2.8 + x * 0.02 + y * 0.02))) % 255
            tint = self.star_tints[idx]
            star_color = (
                min(255, int(tint[0] * (alpha / 255.0))),
                min(255, int(tint[1] * (alpha / 255.0))),
                min(255, int(tint[2] * (alpha / 255.0))),
            )
            sx = int(x)
            sy = int(y)
            pygame.gfxdraw.pixel(surface, sx, sy, star_color)
            if brightness > 180 and int(self.time * 20 + sx + sy) % 4 == 0:
                _draw_aa_filled_circle(surface, sx, sy, 1, _mix_color(star_color, (255, 255, 255), 0.45))
            if brightness > 165 and int(self.time * 10 + x + y) % 6 == 0:
                glint_color = _scale_color((220, 230, 255), 0.7)
                pygame.gfxdraw.line(surface, sx - 2, sy, sx + 2, sy, glint_color)
                pygame.gfxdraw.line(surface, sx, sy - 2, sx, sy + 2, glint_color)

        if self.show_dust_motes:
            for x, y, alpha in self.dust_motes:
                dust_flicker = int(alpha + 20 * math.sin(self.time * 0.7 + x * 0.01))
                pygame.gfxdraw.pixel(surface, int(x), int(y), (dust_flicker, dust_flicker, dust_flicker))

        for star in self.shooting_stars:
            if self._is_in_avoid_region(star["x"], star["y"], padding=12):
                continue
            alpha = int(255 * (star["lifetime"] / star["max_lifetime"]))
            color = tuple(min(255, int(c * alpha / 255)) for c in star["color"])
            head_x = int(star["x"])
            head_y = int(star["y"])
            _draw_aa_filled_circle(surface, head_x, head_y, 2, _scale_color(color, 1.1))
            for segment in range(1, 6):
                t = segment / 6
                trail_x = int(star["x"] - star["vx"] * 0.05 * segment)
                trail_y = int(star["y"] - star["vy"] * 0.05 * segment)
                trail_color = _scale_color(color, 0.9 * (1 - t))
                pygame.gfxdraw.line(surface, trail_x, trail_y, head_x, head_y, trail_color)

        if self.show_energy_waves:
            self._draw_energy_waves(surface)

        for orb in self.sorted_orbs:
            if self._is_in_avoid_region(orb.x, orb.y, padding=int(orb.radius + 36)):
                continue
            orb.draw(surface)

        surface.blit(self.vignette, (0, 0))

    def _draw_energy_waves(self, surface: pygame.Surface) -> None:
        for i in range(4):
            y = (self.time * 60 + i * 80) % self.height
            prev_point = None
            for x in range(0, self.width + 50, 30):
                point = (x, y + math.sin((x + self.time * 120) * 0.01) * 50)
                if prev_point:
                    wave_color = (120 + int(60 * math.sin(self.time * 2 + i)), 80, 180)
                    pygame.gfxdraw.line(surface, int(prev_point[0]), int(prev_point[1]), int(point[0]), int(point[1]), wave_color)
                prev_point = point

        for i in range(3):
            x = (self.time * 40 + i * 180) % self.width
            prev_point = None
            for y in range(0, self.height + 50, 30):
                point = (x + math.sin((y + self.time * 100) * 0.01) * 50, y)
                if prev_point:
                    wave_color = (80, 120 + int(60 * math.sin(self.time * 2 + i)), 200)
                    pygame.gfxdraw.line(surface, int(prev_point[0]), int(prev_point[1]), int(point[0]), int(point[1]), wave_color)
                prev_point = point
