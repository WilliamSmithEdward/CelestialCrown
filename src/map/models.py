"""Tile and map models."""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class TerrainType(Enum):
    """Types of terrain tiles."""

    GRASS = "grass"
    FOREST = "forest"
    WATER = "water"
    MOUNTAIN = "mountain"
    TOWN = "town"
    CASTLE = "castle"
    DESERT = "desert"
    ROAD = "road"


@dataclass
class Tile:
    """Individual map tile."""

    x: int
    y: int
    terrain: TerrainType
    walkable: bool = True
    encounter_chance: float = 0.0

    def __post_init__(self) -> None:
        if self.terrain in (TerrainType.WATER, TerrainType.MOUNTAIN):
            self.walkable = False


class TileMap:
    """2D tile map for game world."""

    def __init__(self, width: int, height: int, default_terrain: TerrainType = TerrainType.GRASS):
        self.width = width
        self.height = height
        self.tiles: List[List[Tile]] = []

        for y in range(height):
            row = []
            for x in range(width):
                row.append(Tile(x, y, default_terrain))
            self.tiles.append(row)

    def get_tile(self, x: int, y: int) -> Optional[Tile]:
        """Get tile at coordinates."""
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.tiles[y][x]
        return None

    def set_terrain(self, x: int, y: int, terrain: TerrainType) -> None:
        """Set terrain type for a tile."""
        tile = self.get_tile(x, y)
        if tile:
            tile.terrain = terrain
            tile.walkable = terrain not in (TerrainType.WATER, TerrainType.MOUNTAIN)

    def is_walkable(self, x: int, y: int) -> bool:
        """Check if a tile is walkable."""
        tile = self.get_tile(x, y)
        return tile.walkable if tile else False


class BattleMap:
    """Specialized map for tactical battles."""

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.terrain_map = TileMap(width, height)
        self.objects: dict[str, dict] = {}

    def is_blocked(self, x: int, y: int) -> bool:
        """Check if movement is blocked (terrain or objects)."""
        if not self.terrain_map.is_walkable(x, y):
            return True

        return any(
            obj.get("blocks", False)
            for obj in self.objects.values()
            if obj.get("x") == x and obj.get("y") == y
        )
