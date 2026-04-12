"""Button component and shared UI color helpers."""

import math
import random

import pygame


def _clamp_rgb(color: tuple[int, int, int]) -> tuple[int, int, int]:
    """Clamp RGB values to pygame's valid color range."""
    return (
        max(0, min(255, int(color[0]))),
        max(0, min(255, int(color[1]))),
        max(0, min(255, int(color[2]))),
    )


class Button:
    """Simple rectangular button."""

    _texture_cache: dict[tuple[int, int], pygame.Surface] = {}

    @staticmethod
    def _build_vertical_gradient(
        width: int,
        height: int,
        top_color: tuple[int, int, int, int],
        bottom_color: tuple[int, int, int, int],
        oversample: int = 4,
    ) -> pygame.Surface:
        """Build a smooth vertical gradient by oversampling and scaling down."""
        sample_height = max(height, height * max(1, oversample))
        gradient = pygame.Surface((1, sample_height), pygame.SRCALPHA)

        for y in range(sample_height):
            t = y / max(1, sample_height - 1)
            eased = 0.5 - 0.5 * math.cos(t * math.pi)
            color = (
                int(top_color[0] * (1.0 - eased) + bottom_color[0] * eased),
                int(top_color[1] * (1.0 - eased) + bottom_color[1] * eased),
                int(top_color[2] * (1.0 - eased) + bottom_color[2] * eased),
                int(top_color[3] * (1.0 - eased) + bottom_color[3] * eased),
            )
            gradient.set_at((0, y), color)

        return pygame.transform.smoothscale(gradient, (width, height))

    def __init__(self, x: int, y: int, width: int, height: int, text: str):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.hover = False
        self.hover_strength = 0.0
        self.gleam_phase = random.uniform(0, 6.28318)

    @classmethod
    def _get_texture(cls, width: int, height: int) -> pygame.Surface:
        """Build and cache subtle button material texture."""
        key = (width, height)
        cached = cls._texture_cache.get(key)
        if cached is not None:
            return cached

        tex = pygame.Surface((width, height), pygame.SRCALPHA)

        tex.blit(
            cls._build_vertical_gradient(
                width,
                height,
                (255, 255, 255, 17),
                (255, 255, 255, 11),
                oversample=6,
            ),
            (0, 0),
        )

        tint_layer = cls._build_vertical_gradient(
            width,
            height,
            (114, 146, 178, 13),
            (108, 138, 176, 9),
            oversample=6,
        )
        tex.blit(tint_layer, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

        grain_count = max(40, int(width * height * 0.012))
        for _ in range(grain_count):
            gx = random.randint(0, width - 1)
            gy = random.randint(0, height - 1)
            alpha = random.randint(5, 18)
            val = random.randint(215, 255)
            tex.set_at((gx, gy), (val, val, val, alpha))

        streak_count = max(3, width // 90)
        for _ in range(streak_count):
            sx = random.randint(-20, width)
            sy = random.randint(0, height - 1)
            ex = sx + random.randint(16, 42)
            ey = max(0, min(height - 1, sy + random.randint(-8, 8)))
            col = (255, 255, 255, random.randint(8, 18))
            pygame.draw.aaline(tex, col, (sx, sy), (ex, ey))

        satin_h = max(6, height // 5)
        satin = cls._build_vertical_gradient(
            width - 8,
            satin_h,
            (255, 255, 255, 12),
            (255, 255, 255, 0),
            oversample=8,
        )
        tex.blit(satin, (4, 4))

        cls._texture_cache[key] = tex
        return tex

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, selected: bool = False) -> None:
        """Draw button."""
        pulse = 0.0
        if selected:
            pulse = 0.5 + 0.5 * math.sin(self.gleam_phase * 2.2)

        lift = int(2 * self.hover_strength) + (3 if selected else 0)
        draw_rect = self.rect.move(0, -lift)
        inner_rect = draw_rect.inflate(-6, -6)

        if selected:
            aura_rect = draw_rect.inflate(26, 18)
            aura = pygame.Surface((aura_rect.width, aura_rect.height), pygame.SRCALPHA)
            aura_alpha = 42 + int(18 * pulse)
            pygame.draw.rect(aura, (246, 220, 158, aura_alpha), aura.get_rect(), border_radius=18)
            surface.blit(aura, aura_rect)

            outer_aura_rect = draw_rect.inflate(42, 28)
            outer_aura = pygame.Surface((outer_aura_rect.width, outer_aura_rect.height), pygame.SRCALPHA)
            outer_alpha = 14 + int(8 * pulse)
            pygame.draw.rect(outer_aura, (160, 200, 255, outer_alpha), outer_aura.get_rect(), border_radius=22)
            surface.blit(outer_aura, outer_aura_rect)

        shadow_rect = draw_rect.copy()
        shadow_rect.x += 2
        shadow_rect.y += 4 + int(2 * self.hover_strength) + (1 if selected else 0)
        pygame.draw.rect(surface, (12, 20, 36), shadow_rect, border_radius=10)

        base_color = _clamp_rgb(
            (
                int(86 + 14 * self.hover_strength + (6 if selected else 0)),
                int(126 + 16 * self.hover_strength + (8 if selected else 0)),
                int(170 + 18 * self.hover_strength + (10 if selected else 0)),
            )
        )
        pygame.draw.rect(surface, base_color, draw_rect, border_radius=10)

        texture = self._get_texture(inner_rect.width, inner_rect.height)
        tex_alpha = 138 + int(14 * self.hover_strength) + (8 if selected else 0)
        textured = pygame.Surface((inner_rect.width, inner_rect.height), pygame.SRCALPHA)

        drift_x = int((math.sin(self.gleam_phase * 0.55) + 1.0) * 0.5 * 3.0)
        drift_y = int((math.cos(self.gleam_phase * 0.45) + 1.0) * 0.5 * 2.0)

        textured.blit(texture, (-drift_x, -drift_y))
        textured.blit(texture, (texture.get_width() - drift_x, -drift_y))
        textured.blit(texture, (-drift_x, texture.get_height() - drift_y))
        textured.blit(texture, (texture.get_width() - drift_x, texture.get_height() - drift_y))

        textured.set_alpha(tex_alpha)
        surface.blit(textured, inner_rect)

        outer_gold = _clamp_rgb(
            (
                int(214 + 24 * self.hover_strength + (20 if selected else 0)),
                int(194 + 22 * self.hover_strength + (18 if selected else 0)),
                int(148 + 16 * self.hover_strength + (14 if selected else 0)),
            )
        )
        inner_bronze = _clamp_rgb(
            (
                int(62 + 12 * self.hover_strength),
                int(46 + 8 * self.hover_strength),
                int(36 + 6 * self.hover_strength),
            )
        )
        pygame.draw.rect(surface, outer_gold, draw_rect, 3 if selected else 2, border_radius=11)
        pygame.draw.rect(surface, inner_bronze, inner_rect, 1, border_radius=8)

        if selected:
            highlight_rect = inner_rect.inflate(-18, -34)
            if highlight_rect.width > 0 and highlight_rect.height > 0:
                highlight = pygame.Surface((highlight_rect.width, highlight_rect.height), pygame.SRCALPHA)
                pygame.draw.rect(
                    highlight,
                    (255, 255, 255, 10 + int(4 * pulse)),
                    highlight.get_rect(),
                    border_radius=8,
                )
                surface.blit(highlight, highlight_rect)

        text_shadow = font.render(self.text, True, (10, 18, 32))
        text_color = (255, 252, 242) if selected else (242, 250, 255)
        text_surface = font.render(self.text, True, text_color)
        text_rect = text_surface.get_rect(center=draw_rect.center)
        shadow_rect = text_shadow.get_rect(center=(draw_rect.center[0] + 1, draw_rect.center[1] + 2))
        surface.blit(text_shadow, shadow_rect)
        surface.blit(text_surface, text_rect)

    def is_clicked(self, pos: tuple[int, int]) -> bool:
        """Check if button was clicked."""
        return self.rect.collidepoint(pos)

    def update(self, mouse_pos: tuple[int, int], delta_time: float = 0.016) -> None:
        """Update button hover state."""
        self.hover = self.rect.collidepoint(mouse_pos)
        target = 1.0 if self.hover else 0.0
        speed = 6.0
        self.hover_strength += (target - self.hover_strength) * min(1.0, delta_time * speed)
        self.gleam_phase += delta_time * (1.2 + self.hover_strength * 2.4)
