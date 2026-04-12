"""Effects primitives: color helpers, particles, lightning, and orb rendering."""

import math
import random
from typing import List, Sequence, Tuple

import pygame
import pygame.gfxdraw


def _scale_color(color: Sequence[int], factor: float) -> Tuple[int, int, int]:
    """Scale RGB color safely."""
    r = color[0] if len(color) > 0 else 0
    g = color[1] if len(color) > 1 else r
    b = color[2] if len(color) > 2 else g
    return (
        max(0, min(255, int(r * factor))),
        max(0, min(255, int(g * factor))),
        max(0, min(255, int(b * factor))),
    )


def _mix_color(a: Sequence[int], b: Sequence[int], t: float) -> Tuple[int, int, int]:
    """Linear blend between two RGB colors."""
    tt = max(0.0, min(1.0, t))
    return (
        int(a[0] * (1.0 - tt) + b[0] * tt),
        int(a[1] * (1.0 - tt) + b[1] * tt),
        int(a[2] * (1.0 - tt) + b[2] * tt),
    )


def _draw_aa_filled_circle(
    surface: pygame.Surface,
    x: int,
    y: int,
    radius: int,
    color: Sequence[int],
) -> None:
    """Draw a filled circle with anti-aliased edge."""
    if radius <= 0:
        return
    rgb = _scale_color(color, 1.0)
    pygame.gfxdraw.filled_circle(surface, x, y, radius, rgb)
    pygame.gfxdraw.aacircle(surface, x, y, radius, rgb)


class Sparkle:
    """A quick sparkling effect."""

    def __init__(self, x: float, y: float, color: Tuple[int, int, int], size: float = 3.0):
        self.x = x
        self.y = y
        self.color = color
        self.size = size
        self.lifetime = random.uniform(0.3, 0.8)
        self.max_lifetime = self.lifetime
        self.rotation = random.uniform(0, 2 * math.pi)

    def update(self, delta_time: float) -> None:
        self.lifetime -= delta_time
        self.rotation += delta_time * random.uniform(5, 15)

    def get_alpha(self) -> float:
        return self.lifetime / self.max_lifetime

    def draw(self, surface: pygame.Surface) -> None:
        if self.lifetime <= 0:
            return

        alpha_ratio = self.get_alpha()
        color = _scale_color(self.color, 0.8 + 0.7 * alpha_ratio)

        points = []
        for i in range(4):
            angle = self.rotation + (i * math.pi / 2)
            points.append((self.x + math.cos(angle) * self.size, self.y + math.sin(angle) * self.size))

        cx, cy = int(self.x), int(self.y)
        for point in points:
            pygame.gfxdraw.line(surface, cx, cy, int(point[0]), int(point[1]), color)
        pygame.gfxdraw.filled_circle(
            surface,
            cx,
            cy,
            1,
            _scale_color((255, 245, 220), 0.8 + 0.2 * alpha_ratio),
        )


class LightningBolt:
    """Animated lightning effect."""

    def __init__(self, x1: float, y1: float, x2: float, y2: float, color: Tuple[int, int, int] = (100, 200, 255)):
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        self.color = color
        self.lifetime = random.uniform(0.18, 0.36)
        self.max_lifetime = self.lifetime
        self.phase = random.uniform(0, math.tau)
        self.main_path = self._generate_segments()
        self.branches = self._generate_branches()

    def _generate_segments(self) -> List[Tuple[float, float]]:
        control_points = [(self.x1, self.y1)]
        dx = self.x2 - self.x1
        dy = self.y2 - self.y1
        dist = max(1.0, math.hypot(dx, dy))
        nx = -dy / dist
        ny = dx / dist

        steps = 10
        for i in range(1, steps):
            t = i / steps
            x = self.x1 + dx * t
            y = self.y1 + dy * t
            taper = math.sin(math.pi * t)
            offset = random.uniform(-1.0, 1.0) * (dist * 0.04) * taper
            x += nx * offset
            y += ny * offset
            control_points.append((x, y))

        control_points.append((self.x2, self.y2))

        smooth_path: List[Tuple[float, float]] = []
        segment_count = len(control_points) - 1
        for i in range(segment_count):
            p0 = control_points[max(0, i - 1)]
            p1 = control_points[i]
            p2 = control_points[i + 1]
            p3 = control_points[min(len(control_points) - 1, i + 2)]

            for j in range(9):
                t = j / 8
                t2 = t * t
                t3 = t2 * t
                x = 0.5 * (
                    2 * p1[0]
                    + (-p0[0] + p2[0]) * t
                    + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2
                    + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3
                )
                y = 0.5 * (
                    2 * p1[1]
                    + (-p0[1] + p2[1]) * t
                    + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2
                    + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3
                )
                smooth_path.append((x, y))

        return smooth_path

    def _generate_branches(self) -> List[List[Tuple[float, float]]]:
        branches: List[List[Tuple[float, float]]] = []
        if len(self.main_path) < 12:
            return branches

        for _ in range(random.randint(1, 2)):
            start_idx = random.randint(6, len(self.main_path) - 8)
            sx, sy = self.main_path[start_idx]
            tx, ty = self.main_path[min(len(self.main_path) - 1, start_idx + 2)]
            dx = tx - sx
            dy = ty - sy
            seg_len = max(1.0, math.hypot(dx, dy))
            nx = -dy / seg_len
            ny = dx / seg_len
            branch_len = random.uniform(18, 45)
            bend = random.uniform(-0.7, 0.7)
            ex = sx + nx * branch_len + dx * bend
            ey = sy + ny * branch_len + dy * bend
            midx = (sx + ex) * 0.5 + random.uniform(-6, 6)
            midy = (sy + ey) * 0.5 + random.uniform(-6, 6)
            branches.append([(sx, sy), (midx, midy), (ex, ey)])
        return branches

    def update(self, delta_time: float) -> None:
        self.lifetime -= delta_time
        self.phase += delta_time * 26.0

    def _revealed_polyline(self, points: List[Tuple[float, float]], reveal: float) -> List[Tuple[float, float]]:
        if len(points) < 2:
            return points
        if reveal <= 0.0:
            return [points[0]]
        if reveal >= 1.0:
            return points

        span = (len(points) - 1) * reveal
        idx = int(span)
        frac = span - idx
        out = points[: idx + 1]
        if idx < len(points) - 1:
            x1, y1 = points[idx]
            x2, y2 = points[idx + 1]
            out.append((x1 + (x2 - x1) * frac, y1 + (y2 - y1) * frac))
        return out

    def draw(self, surface: pygame.Surface) -> None:
        if self.lifetime <= 0 or len(self.main_path) < 2:
            return

        alpha_ratio = self.lifetime / self.max_lifetime
        life_progress = 1.0 - alpha_ratio
        reveal_main = 1.0 - pow(1.0 - life_progress, 3)
        flicker = 0.86 + 0.14 * math.sin(self.phase)

        main_points = self._revealed_polyline(self.main_path, reveal_main)
        branch_revealed: List[List[Tuple[float, float]]] = []
        for idx, branch in enumerate(self.branches):
            start = 0.55 + idx * 0.10
            branch_reveal = max(0.0, min(1.0, (life_progress - start) / 0.35))
            bp = self._revealed_polyline(branch, branch_reveal)
            if len(bp) > 1:
                branch_revealed.append(bp)

        all_points: List[Tuple[float, float]] = []
        if len(main_points) > 1:
            all_points.extend(main_points)
        for bp in branch_revealed:
            all_points.extend(bp)
        if not all_points:
            return

        min_x = int(min(p[0] for p in all_points)) - 6
        min_y = int(min(p[1] for p in all_points)) - 6
        max_x = int(max(p[0] for p in all_points)) + 6
        max_y = int(max(p[1] for p in all_points)) + 6

        layer_w = max(1, max_x - min_x + 1)
        layer_h = max(1, max_y - min_y + 1)
        layer = pygame.Surface((layer_w, layer_h), pygame.SRCALPHA)

        def draw_polyline(points: List[Tuple[float, float]], strength: float) -> None:
            for i in range(len(points) - 1):
                x1, y1 = points[i][0] - min_x, points[i][1] - min_y
                x2, y2 = points[i + 1][0] - min_x, points[i + 1][1] - min_y
                t = i / max(1, len(points) - 1)
                envelope = 0.55 + 0.45 * math.sin(math.pi * t)
                inten = strength * envelope * alpha_ratio * flicker
                dx = x2 - x1
                dy = y2 - y1
                d = max(1.0, math.hypot(dx, dy))
                nx = -dy / d
                ny = dx / d
                glow = (*_scale_color(self.color, 0.75), int(52 * inten))
                core = (*_mix_color(self.color, (245, 250, 255), 0.45), int(210 * inten))
                pygame.draw.aaline(layer, glow, (x1 - nx, y1 - ny), (x2 - nx, y2 - ny))
                pygame.draw.aaline(layer, glow, (x1 + nx, y1 + ny), (x2 + nx, y2 + ny))
                pygame.draw.aaline(layer, core, (x1, y1), (x2, y2))

        if len(main_points) > 1:
            draw_polyline(main_points, 1.0)

        for branch_points in branch_revealed:
            draw_polyline(branch_points, 0.62)

        if len(main_points) > 0:
            hx, hy = main_points[-1][0] - min_x, main_points[-1][1] - min_y
            head_alpha = int(180 * alpha_ratio)
            pygame.gfxdraw.filled_circle(
                layer,
                int(hx),
                int(hy),
                2,
                (*_mix_color(self.color, (255, 255, 255), 0.6), max(0, head_alpha)),
            )
        surface.blit(layer, (min_x, min_y), special_flags=pygame.BLEND_RGBA_ADD)


class Particle:
    """A single particle in an effect."""

    def __init__(
        self,
        x: float,
        y: float,
        vx: float = 0,
        vy: float = 0,
        lifetime: float = 1.0,
        color: Tuple[int, int, int] = (255, 255, 255),
        size: float = 2.0,
    ):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.lifetime = lifetime
        self.max_lifetime = lifetime
        self.color = color
        self.size = size
        self.alive = True
        self.trail: List[Tuple[float, float]] = [(x, y)]

    def update(self, delta_time: float) -> None:
        self.vx *= (1.0 - min(0.18, delta_time * 1.8))
        self.vy *= (1.0 - min(0.18, delta_time * 1.8))
        self.x += self.vx * delta_time
        self.y += self.vy * delta_time
        self.lifetime -= delta_time

        self.trail.append((self.x, self.y))
        if len(self.trail) > 5:
            self.trail.pop(0)

        if self.lifetime <= 0:
            self.alive = False

    def get_alpha(self) -> float:
        return self.lifetime / self.max_lifetime

    def draw(self, surface: pygame.Surface) -> None:
        alpha_ratio = self.get_alpha()
        for i, (tx, ty) in enumerate(self.trail[:-1]):
            t = (i + 1) / max(1, len(self.trail))
            trail_color = _scale_color(self.color, 0.35 * t * alpha_ratio)
            _draw_aa_filled_circle(surface, int(tx), int(ty), 1, trail_color)

        ring_color = _scale_color(self.color, 0.35 * alpha_ratio)
        pygame.gfxdraw.aacircle(surface, int(self.x), int(self.y), max(1, int(self.size + 1)), ring_color)
        _draw_aa_filled_circle(
            surface,
            int(self.x),
            int(self.y),
            max(1, int(self.size)),
            _scale_color(self.color, 0.75 + 0.25 * alpha_ratio),
        )


class OrbEffect:
    """Animated floating orb/sphere with glow."""

    def __init__(self, x: float, y: float, color: Tuple[int, int, int], radius: float = 15):
        self.x = x
        self.y = y
        self.base_x = x
        self.base_y = y
        self.color = color
        self.radius = radius
        self.time = random.uniform(0, 2 * math.pi)
        self.depth = random.uniform(0, 1)
        self.orbit_radius = random.uniform(60, 150)
        self.orbit_speed = random.uniform(0.2, 0.5)
        self.glow_intensity = 0.5
        self.particles: List[Particle] = []
        self.sparkles: List[Sparkle] = []
        self.lightning_bolts: List[LightningBolt] = []
        self.spark_timer = 0
        self.rune_phase = random.uniform(0, 2 * math.pi)
        self.texture_phase = random.uniform(0, math.tau)
        self.corona_phase = random.uniform(0, math.tau)
        self.show_runes = False
        self.show_particle_spray = False
        self.show_sparkle_spray = False
        self.surface_cells: List[dict] = []
        self.planets: List[dict] = []
        self._bloom_variants: List[pygame.Surface] = []
        self._bloom_center = 0
        self._spike_layer: pygame.Surface | None = None
        self._spike_center = 0
        self._sheen_layer: pygame.Surface | None = None
        self._sheen_center = 0
        self._corona_scratch: pygame.Surface | None = None
        self._planet_shadow_scratch: dict[int, pygame.Surface] = {}

        for _ in range(random.randint(6, 11)):
            self.surface_cells.append(
                {
                    "angle": random.uniform(0, math.tau),
                    "radius_factor": random.uniform(0.12, 0.78),
                    "size_factor": random.uniform(0.06, 0.20),
                    "speed": random.uniform(0.1, 0.6),
                    "temp": random.uniform(0.7, 1.2),
                }
            )

        planet_count = random.randint(1, 3)
        orbit_start = self.radius * 1.9
        for idx in range(planet_count):
            self.planets.append(
                {
                    "orbit": orbit_start + idx * random.uniform(14, 24),
                    "size": random.uniform(2.2, 4.2),
                    "phase": random.uniform(0, math.tau),
                    "speed": random.uniform(0.15, 0.65) * (1.0 / (1.0 + idx * 0.25)),
                    "tilt": random.uniform(0.5, 0.95),
                    "color": random.choice(
                        [
                            (170, 205, 255),
                            (255, 214, 156),
                            (255, 168, 132),
                            (170, 255, 222),
                            (198, 166, 255),
                        ]
                    ),
                    "ring": random.random() < 0.28,
                }
            )

        self._build_cached_layers()

    def _build_cached_layers(self) -> None:
        max_bloom_radius = max(6, int(self.radius * 3.5))
        bloom_size = max(24, max_bloom_radius * 2 + 10)
        bc = bloom_size // 2
        self._bloom_center = bc

        self._bloom_variants = []
        for level in range(8):
            glow = level / 7.0
            bloom = pygame.Surface((bloom_size, bloom_size), pygame.SRCALPHA)
            bloom_color = _scale_color(self.color, 0.85 + glow * 0.35)
            for rr, a in ((max(5, int(self.radius * 3.2)), 10), (max(4, int(self.radius * 2.6)), 16), (max(3, int(self.radius * 2.0)), 24)):
                pygame.gfxdraw.filled_circle(bloom, bc, bc, rr, (bloom_color[0], bloom_color[1], bloom_color[2], a))
            self._bloom_variants.append(bloom)

        spike_layer_size = max(24, int(self.radius * 6))
        self._spike_center = spike_layer_size // 2
        spike = pygame.Surface((spike_layer_size, spike_layer_size), pygame.SRCALPHA)
        c = self._spike_center
        spike_len = max(8, int(self.radius * 2.3))
        spike_color = (*_scale_color(self.color, 0.95), 64)
        pygame.draw.aaline(spike, spike_color, (c - spike_len, c), (c + spike_len, c))
        pygame.draw.aaline(spike, spike_color, (c, c - spike_len), (c, c + spike_len))
        diag = max(6, int(spike_len * 0.7))
        pygame.draw.aaline(spike, (*_scale_color(self.color, 0.7), 38), (c - diag, c - diag), (c + diag, c + diag))
        pygame.draw.aaline(spike, (*_scale_color(self.color, 0.7), 38), (c - diag, c + diag), (c + diag, c - diag))
        self._spike_layer = spike

        sheen_size = max(8, int(self.radius * 2.4))
        self._sheen_center = sheen_size // 2
        sheen = pygame.Surface((sheen_size, sheen_size), pygame.SRCALPHA)
        c_sheen = self._sheen_center
        r = max(3, int(self.radius * 0.95))
        pygame.gfxdraw.filled_circle(sheen, c_sheen, c_sheen, r, (255, 255, 255, 28))
        pygame.gfxdraw.aacircle(sheen, c_sheen, c_sheen, r, (255, 255, 255, 40))
        pygame.gfxdraw.filled_circle(sheen, c_sheen + int(self.radius * 0.30), c_sheen + int(self.radius * 0.24), r, (0, 0, 0, 0))
        self._sheen_layer = sheen

        self._corona_scratch = pygame.Surface((bloom_size, bloom_size), pygame.SRCALPHA)

    def _get_planet_shadow_surface(self, pr: int) -> pygame.Surface:
        if pr not in self._planet_shadow_scratch:
            self._planet_shadow_scratch[pr] = pygame.Surface((pr * 4, pr * 4), pygame.SRCALPHA)
        return self._planet_shadow_scratch[pr]

    def update(self, delta_time: float) -> None:
        self.time += delta_time * self.orbit_speed
        self.rune_phase += delta_time * (0.5 + self.depth)
        self.texture_phase += delta_time * 0.7
        self.corona_phase += delta_time * 1.2

        self.x = self.base_x + math.cos(self.time) * self.orbit_radius
        self.y = self.base_y + math.sin(self.time) * self.orbit_radius * 0.5
        self.glow_intensity = 0.6 + 0.4 * math.sin(self.time * 2)

        if self.show_particle_spray and random.random() < 0.6:
            for _ in range(random.randint(2, 4)):
                self.particles.append(
                    Particle(
                        self.x + random.uniform(-8, 8),
                        self.y + random.uniform(-8, 8),
                        vx=random.uniform(-40, 40),
                        vy=random.uniform(-40, 40),
                        lifetime=random.uniform(0.4, 0.8),
                        color=self.color,
                        size=random.uniform(3, 6),
                    )
                )

        if self.show_sparkle_spray and random.random() < 0.7:
            for _ in range(random.randint(2, 5)):
                self.sparkles.append(
                    Sparkle(
                        self.x + random.uniform(-self.radius * 2, self.radius * 2),
                        self.y + random.uniform(-self.radius * 2, self.radius * 2),
                        color=self.color,
                        size=random.uniform(2, 5),
                    )
                )

        self.spark_timer += delta_time
        if self.spark_timer > random.uniform(0.5, 2.0):
            if random.random() < 0.4:
                target_orb = (self.base_x + random.uniform(-200, 200), self.base_y + random.uniform(-200, 200))
                self.lightning_bolts.append(LightningBolt(self.x, self.y, target_orb[0], target_orb[1], self.color))
            self.spark_timer = 0

        for particle in self.particles:
            particle.update(delta_time)
        self.particles = [p for p in self.particles if p.alive]

        for sparkle in self.sparkles:
            sparkle.update(delta_time)
        self.sparkles = [s for s in self.sparkles if s.lifetime > 0]

        for bolt in self.lightning_bolts:
            bolt.update(delta_time)
        self.lightning_bolts = [b for b in self.lightning_bolts if b.lifetime > 0]

    def draw(self, surface: pygame.Surface) -> None:
        bc = self._bloom_center
        bloom_idx = max(0, min(7, int(self.glow_intensity * 7.0)))
        surface.blit(self._bloom_variants[bloom_idx], (int(self.x) - bc, int(self.y) - bc), special_flags=pygame.BLEND_RGBA_ADD)

        corona_layer = self._corona_scratch
        if corona_layer is None:
            return
        corona_layer.fill((0, 0, 0, 0))
        for i in range(8):
            ang = self.corona_phase + i * (math.tau / 8)
            ray_len = self.radius * (1.8 + 0.35 * math.sin(self.corona_phase * 1.7 + i))
            x1 = bc + math.cos(ang) * (self.radius * 1.15)
            y1 = bc + math.sin(ang) * (self.radius * 1.15)
            x2 = bc + math.cos(ang) * ray_len
            y2 = bc + math.sin(ang) * ray_len
            pygame.draw.aaline(corona_layer, (*_scale_color(self.color, 0.75), 28), (x1, y1), (x2, y2))
        surface.blit(corona_layer, (int(self.x) - bc, int(self.y) - bc), special_flags=pygame.BLEND_RGBA_ADD)

        for ring_level in range(3, 0, -1):
            ring_radius = int(self.radius * (1.05 + ring_level * 0.30 + self.glow_intensity * 0.18))
            glow_color = _scale_color(self.color, 0.22 + self.glow_intensity * (4 - ring_level) * 0.16)
            pygame.gfxdraw.aacircle(surface, int(self.x), int(self.y), ring_radius, glow_color)

        core_radius = int(self.radius)
        for i in range(core_radius, 0, -1):
            fade = (core_radius - i) / core_radius
            warm_center = (
                min(255, int(self.color[0] + (255 - self.color[0]) * 0.60)),
                min(255, int(self.color[1] + (248 - self.color[1]) * 0.60)),
                min(255, int(self.color[2] + (230 - self.color[2]) * 0.38)),
            )
            fade_color = (
                int(self.color[0] * (1 - fade) + warm_center[0] * fade),
                int(self.color[1] * (1 - fade) + warm_center[1] * fade),
                int(self.color[2] * (1 - fade) + warm_center[2] * fade),
            )
            _draw_aa_filled_circle(surface, int(self.x), int(self.y), i, _scale_color(fade_color, 0.72 + 0.28 * fade))

        for cell in self.surface_cells:
            ang = self.texture_phase * cell["speed"] + cell["angle"]
            dist = self.radius * cell["radius_factor"]
            cx = int(self.x + math.cos(ang) * dist)
            cy = int(self.y + math.sin(ang) * dist * 0.9)
            cell_r = max(1, int(self.radius * cell["size_factor"]))
            base = _scale_color(self.color, cell["temp"])
            cell_color = (
                min(255, int(base[0] + (255 - base[0]) * 0.22)),
                min(255, int(base[1] + (244 - base[1]) * 0.14)),
                min(255, int(base[2] + (216 - base[2]) * 0.08)),
            )
            _draw_aa_filled_circle(surface, cx, cy, cell_r, cell_color)

        _draw_aa_filled_circle(surface, int(self.x), int(self.y), max(1, int(self.radius * 0.22)), (255, 248, 226))
        _draw_aa_filled_circle(
            surface,
            int(self.x - self.radius * 0.35),
            int(self.y - self.radius * 0.35),
            max(1, int(self.radius * 0.35)),
            (255, 255, 255),
        )

        if self._spike_layer is not None:
            surface.blit(self._spike_layer, (int(self.x) - self._spike_center, int(self.y) - self._spike_center))
        if self._sheen_layer is not None:
            surface.blit(self._sheen_layer, (int(self.x) - self._sheen_center, int(self.y) - self._sheen_center))

        for planet in self.planets:
            orbit = planet["orbit"]
            px = self.x + math.cos(self.texture_phase * planet["speed"] + planet["phase"]) * orbit
            py = self.y + math.sin(self.texture_phase * planet["speed"] + planet["phase"]) * orbit * planet["tilt"]
            pr = max(1, int(planet["size"]))

            if planet is self.planets[-1]:
                pygame.gfxdraw.aacircle(surface, int(self.x), int(self.y), int(orbit), _scale_color(self.color, 0.14))

            pop_planet = _mix_color(planet["color"], (255, 250, 236), 0.18)
            _draw_aa_filled_circle(surface, int(px), int(py), pr, pop_planet)

            lx = self.x - px
            ly = self.y - py
            ll = max(1.0, math.hypot(lx, ly))
            ldx = lx / ll
            ldy = ly / ll
            _draw_aa_filled_circle(surface, int(px + ldx * pr * 0.35), int(py + ldy * pr * 0.35), max(1, int(pr * 0.42)), (255, 252, 236))

            shadow = self._get_planet_shadow_surface(pr)
            shadow.fill((0, 0, 0, 0))
            sc = shadow.get_width() // 2
            pygame.gfxdraw.filled_circle(shadow, sc, sc, pr, (0, 0, 0, 72))
            pygame.gfxdraw.filled_circle(shadow, int(sc + ldx * pr * 0.58), int(sc + ldy * pr * 0.58), pr, (0, 0, 0, 0))
            surface.blit(shadow, (int(px) - sc, int(py) - sc))

            rim_col = _mix_color(planet["color"], (210, 235, 255), 0.45)
            pygame.gfxdraw.aacircle(surface, int(px), int(py), pr, rim_col)
            pygame.draw.aaline(
                surface,
                _scale_color((255, 255, 255), 0.72),
                (int(px - pr * 0.72), int(py - pr * 0.18)),
                (int(px + pr * 0.72), int(py + pr * 0.12)),
            )

            if planet["ring"]:
                ring_w = max(2, int(pr * 2.2))
                ring_h = max(1, int(pr * 0.9))
                ring_rect = pygame.Rect(int(px - ring_w), int(py - ring_h), ring_w * 2, ring_h * 2)
                pygame.draw.ellipse(surface, _scale_color(planet["color"], 0.65), ring_rect, 1)
                pygame.draw.ellipse(surface, _scale_color(planet["color"], 1.12), ring_rect.inflate(-1, -1), 1)

        for bolt in self.lightning_bolts:
            bolt.draw(surface)
        if self.show_particle_spray:
            for particle in self.particles:
                particle.draw(surface)
        if self.show_sparkle_spray:
            for sparkle in self.sparkles:
                sparkle.draw(surface)
