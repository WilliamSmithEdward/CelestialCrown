"""Battle grid system for position and unit tracking."""

from typing import List, Optional, Tuple

from ..entities import Unit
from ..exceptions import GridError


class BattleGrid:
    """Grid-based battle map."""

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.tiles: List[List[Optional[str]]] = [[None for _ in range(width)] for _ in range(height)]
        self.units: dict[str, Unit] = {}

    def place_unit(self, unit: Unit, x: int, y: int) -> bool:
        """Place a unit at coordinates, return success."""
        if not self._is_valid_position(x, y):
            raise GridError(f"Invalid position ({x}, {y})")

        if self.tiles[y][x] is not None:
            raise GridError(f"Position ({x}, {y}) already occupied")

        unit.position_x = x
        unit.position_y = y
        self.tiles[y][x] = unit.id
        self.units[unit.id] = unit
        return True

    def move_unit(self, unit: Unit, x: int, y: int) -> bool:
        """Move a unit to new coordinates."""
        if not self._is_valid_position(x, y):
            raise GridError(f"Invalid destination ({x}, {y})")

        if self.tiles[y][x] is not None and self.tiles[y][x] != unit.id:
            raise GridError(f"Destination ({x}, {y}) occupied by another unit")

        # Clear old position
        if self._is_valid_position(unit.position_x, unit.position_y):
            self.tiles[unit.position_y][unit.position_x] = None

        # Place at new position
        unit.position_x = x
        unit.position_y = y
        self.tiles[y][x] = unit.id
        return True

    def remove_unit(self, unit: Unit) -> bool:
        """Remove a unit from the grid."""
        if unit.id not in self.units:
            return False

        if self._is_valid_position(unit.position_x, unit.position_y):
            self.tiles[unit.position_y][unit.position_x] = None

        del self.units[unit.id]
        return True

    def get_adjacent_positions(self, x: int, y: int) -> List[Tuple[int, int]]:
        """Get valid adjacent positions (cardinal only, 4-way)."""
        positions = []
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = x + dx, y + dy
            if self._is_valid_position(nx, ny):
                positions.append((nx, ny))
        return positions

    def get_unit_at(self, x: int, y: int) -> Optional[Unit]:
        """Get unit at position."""
        if self._is_valid_position(x, y):
            unit_id = self.tiles[y][x]
            return self.units.get(unit_id) if unit_id else None
        return None

    def _is_valid_position(self, x: int, y: int) -> bool:
        """Check if position is within grid bounds."""
        return 0 <= x < self.width and 0 <= y < self.height

    def get_distance(self, x1: int, y1: int, x2: int, y2: int) -> int:
        """Manhattan distance between positions."""
        return abs(x1 - x2) + abs(y1 - y2)

    def clear(self) -> None:
        """Clear all units from grid."""
        self.tiles = [[None for _ in range(self.width)] for _ in range(self.height)]
        self.units.clear()
