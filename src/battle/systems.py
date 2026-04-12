"""Battle systems: turn order, grid operations, and combat calculations."""

from dataclasses import dataclass, field
from enum import Enum
import random
from typing import List, Optional, Tuple

from ..entities import Unit


class ActionType(Enum):
    """Types of actions units can take in battle."""

    ATTACK = "attack"
    MAGIC = "magic"
    SKILL = "skill"
    DEFEND = "defend"
    ITEM = "item"
    WAIT = "wait"


@dataclass
class Action:
    """Represents a unit's action in combat."""

    actor: Unit
    action_type: ActionType
    target: Optional[Unit] = None
    targets: List[Unit] = field(default_factory=list)
    power: int = 0


class BattleGrid:
    """Grid-based battle map."""

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.tiles: List[List[Optional[str]]] = [
            [None for _ in range(width)] for _ in range(height)
        ]
        self.units: dict[str, Unit] = {}

    def place_unit(self, unit: Unit, x: int, y: int) -> bool:
        """Place a unit at coordinates, return success."""
        if self._is_valid_position(x, y) and self.tiles[y][x] is None:
            unit.position_x = x
            unit.position_y = y
            self.tiles[y][x] = unit.id
            self.units[unit.id] = unit
            return True
        return False

    def move_unit(self, unit: Unit, x: int, y: int) -> bool:
        """Move a unit to new coordinates."""
        if not self._is_valid_position(x, y):
            return False

        self.tiles[unit.position_y][unit.position_x] = None
        unit.position_x = x
        unit.position_y = y
        self.tiles[y][x] = unit.id
        return True

    def get_adjacent_positions(self, x: int, y: int) -> List[Tuple[int, int]]:
        """Get valid adjacent positions (cardinal only)."""
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


class CombatSystem:
    """Handles combat calculations and mechanics."""

    @staticmethod
    def calculate_damage(attacker: Unit, defender: Unit) -> int:
        """Calculate damage based on attacker and defender stats."""
        base_damage = attacker.stats.str + random.randint(-5, 10)
        defense_reduction = defender.stats.def_ // 2
        return max(1, base_damage - defense_reduction)

    @staticmethod
    def calculate_hit_chance(attacker: Unit, defender: Unit) -> float:
        """Calculate hit probability (0.0 to 1.0)."""
        base_hit = 0.85
        agl_difference = (attacker.stats.agl - defender.stats.agl) / 100.0
        return max(0.3, min(0.95, base_hit + agl_difference))

    @staticmethod
    def calculate_critical_chance(attacker: Unit) -> float:
        """Calculate critical hit probability."""
        return (attacker.stats.agl / 100.0) * 0.3

    @staticmethod
    def execute_attack(attacker: Unit, defender: Unit) -> Tuple[int, bool, bool]:
        """Execute an attack, return (damage, hit, critical)."""
        if random.random() > CombatSystem.calculate_hit_chance(attacker, defender):
            return 0, False, False

        is_critical = random.random() < CombatSystem.calculate_critical_chance(attacker)
        damage = CombatSystem.calculate_damage(attacker, defender)
        if is_critical:
            damage = int(damage * 1.5)
        return damage, True, is_critical


class BattleState:
    """Manages overall battle state and turn order."""

    def __init__(self, player_units: List[Unit], enemy_units: List[Unit]):
        self.grid = BattleGrid(12, 8)
        self.player_units = player_units
        self.enemy_units = enemy_units
        self.all_units = player_units + enemy_units

        self.turn_order: List[Unit] = []
        self.current_turn_index = 0
        self.round_number = 1
        self.actions_queue: List[Action] = []

        self._calculate_turn_order()

    def _calculate_turn_order(self) -> None:
        """Calculate turn order based on agility."""
        self.turn_order = sorted(self.all_units, key=lambda u: u.stats.agl, reverse=True)

    def get_current_unit(self) -> Optional[Unit]:
        """Get unit whose turn it is."""
        if 0 <= self.current_turn_index < len(self.turn_order):
            return self.turn_order[self.current_turn_index]
        return None

    def end_turn(self) -> None:
        """Move to next unit's turn."""
        self.current_turn_index += 1
        if self.current_turn_index >= len(self.turn_order):
            self._complete_round()

    def _complete_round(self) -> None:
        """Handle end-of-round cleanup."""
        self.round_number += 1
        self.current_turn_index = 0
        for unit in self.all_units:
            if unit.is_alive:
                unit.reset_turn()

    def is_battle_over(self) -> Tuple[bool, str]:
        """Check if battle is finished, return (is_over, winner)."""
        player_alive = any(u.is_alive for u in self.player_units)
        enemies_alive = any(u.is_alive for u in self.enemy_units)

        if not player_alive:
            return True, "DEFEAT"
        if not enemies_alive:
            return True, "VICTORY"
        return False, ""
