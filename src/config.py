"""Game configuration and constants"""

# Display settings
SCREEN_WIDTH = 2560
SCREEN_HEIGHT = 1440
FPS = 60
DISPLAY_MODE = "windowed"  # "windowed" or "fullscreen"

# Grid settings
TILE_SIZE = 96  # Increased from 64 for higher resolution
GRID_WIDTH = 20
GRID_HEIGHT = 11

# Game settings
GAME_TITLE = "Celestial Crown"
DEFAULT_MAP_FILE = "data/scenarios/chapter1.yaml"

# Battle settings
MAX_UNITS_PER_SIDE = 12
MAX_PARTY_SIZE = 12

# UI settings
HUD_HEIGHT = 200
MENU_ITEM_HEIGHT = 64
UI_FONT_SIZE = 18

# Alignment system (like Ogre Battle)
ALIGNMENT_LAW = 100
ALIGNMENT_NEUTRAL = 0
ALIGNMENT_CHAOS = -100

# Color palette
COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)
COLOR_GRAY = (128, 128, 128)
COLOR_RED = (255, 0, 0)
COLOR_GREEN = (0, 255, 0)
COLOR_BLUE = (0, 0, 255)
COLOR_YELLOW = (255, 255, 0)
COLOR_CYAN = (0, 255, 255)
COLOR_MAGENTA = (255, 0, 255)

# Unit stats ranges
STAT_MIN = 1
STAT_MAX = 99
LEVEL_MIN = 1
LEVEL_MAX = 50

# Unit types
UNIT_TYPES = {
    "knight": {"base_hp": 40, "base_str": 8, "base_def": 7, "base_agl": 5},
    "mage": {"base_hp": 25, "base_str": 4, "base_def": 4, "base_agl": 6},
    "archer": {"base_hp": 30, "base_str": 6, "base_def": 5, "base_agl": 8},
    "cleric": {"base_hp": 28, "base_str": 5, "base_def": 5, "base_agl": 5},
    "rogue": {"base_hp": 28, "base_str": 7, "base_def": 4, "base_agl": 9},
}
