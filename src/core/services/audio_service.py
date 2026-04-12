"""Small audio loop service for state-driven music playback."""

import os
from dataclasses import dataclass

import pygame


@dataclass
class LoopConfig:
    path: str
    volume: float = 0.60
    fade_seconds: float = 2.2


class AudioLoopService:
    """Manage a single looping track with fade boundaries."""

    def __init__(self, config: LoopConfig):
        self.config = config
        self.enabled = False
        self.duration = 0.0
        self.elapsed = 0.0
        self.fading = False

    def start(self) -> None:
        """Start loop playback if track exists and mixer is available."""
        if not self.config.path or not os.path.exists(self.config.path):
            self.enabled = False
            return

        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init()

            if self.duration <= 0.0:
                self.duration = pygame.mixer.Sound(self.config.path).get_length()

            pygame.mixer.music.load(self.config.path)
            pygame.mixer.music.set_volume(self.config.volume)
            pygame.mixer.music.play(0, fade_ms=int(self.config.fade_seconds * 1000))

            self.enabled = True
            self.elapsed = 0.0
            self.fading = False
        except (pygame.error, OSError):
            self.enabled = False

    def stop(self) -> None:
        """Stop playback with a short fade."""
        try:
            if pygame.mixer.get_init() is not None and pygame.mixer.music.get_busy():
                pygame.mixer.music.fadeout(500)
        except pygame.error:
            pass

        self.enabled = False
        self.fading = False

    def update(self, delta_time: float) -> None:
        """Update fade-loop timing and restart at loop boundaries."""
        if not self.enabled:
            return

        try:
            self.elapsed += delta_time

            if self.duration > 0.0 and not self.fading:
                fade_start = max(0.0, self.duration - self.config.fade_seconds - 0.08)
                if self.elapsed >= fade_start:
                    pygame.mixer.music.fadeout(int(self.config.fade_seconds * 1000))
                    self.fading = True

            if self.fading and not pygame.mixer.music.get_busy():
                pygame.mixer.music.load(self.config.path)
                pygame.mixer.music.set_volume(self.config.volume)
                pygame.mixer.music.play(0, fade_ms=int(self.config.fade_seconds * 1000))
                self.elapsed = 0.0
                self.fading = False

            if not self.fading and not pygame.mixer.music.get_busy():
                pygame.mixer.music.load(self.config.path)
                pygame.mixer.music.set_volume(self.config.volume)
                pygame.mixer.music.play(0, fade_ms=int(self.config.fade_seconds * 1000))
                self.elapsed = 0.0
        except (pygame.error, OSError):
            self.enabled = False
