import os
from collections.abc import Generator

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest


@pytest.fixture(scope="session", autouse=True)
def pygame_session() -> Generator[None, None, None]:
    pygame.init()
    pygame.font.init()
    pygame.display.set_mode((1, 1))
    yield
    pygame.font.quit()
    pygame.quit()
