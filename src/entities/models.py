"""Entity models for units, stats, and progression."""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from ..config import LEVEL_MAX, LEVEL_MIN
from .stats import Stats

logger = logging.getLogger(__name__)


class UnitClass(Enum):
    """Unit class types."""

    KNIGHT = "knight"
    MAGE = "mage"
    ARCHER = "archer"
    CLERIC = "cleric"
    ROGUE = "rogue"


class Alignment(Enum):
    """Unit alignment for story branching."""

    LAW = 100
    NEUTRAL = 0
    CHAOS = -100


@dataclass
class Equipment:
    """Unit equipment and items."""

    weapon: Optional[str] = None
    armor: Optional[str] = None
    accessory: Optional[str] = None


class Unit:
    """A single unit in battle (character or enemy)."""

    def __init__(self, unit_id: str, name: str, unit_class: UnitClass, level: int = 1):
        self.id = unit_id
        self.name = name
        self.unit_class = unit_class
        self.level = max(LEVEL_MIN, min(LEVEL_MAX, level))

        self.stats = Stats()
        self.current_hp = self.stats.hp
        self.equipment = Equipment()

        self.position_x = 0
        self.position_y = 0
        self.team = 0

        self.exp = 0
        self.exp_to_level = 100 * self.level

        self.status_effects: List[str] = []
        self.alignment = Alignment.NEUTRAL

        self.is_alive = True
        self.has_acted_this_turn = False
        logger.info(f"Unit {self.name} ({self.id}) created at level {self.level}")

    def take_damage(self, damage: int) -> int:
        """Apply damage, return actual damage taken."""
        actual_damage = max(1, damage - (self.stats.def_ // 3))
        self.current_hp -= actual_damage

        if self.current_hp <= 0:
            self.current_hp = 0
            self.is_alive = False
            logger.info(f"Unit {self.name} defeated")

        return actual_damage

    def heal(self, amount: int) -> int:
        """Heal unit, return actual amount healed."""
        actual_heal = min(amount, self.stats.hp - self.current_hp)
        self.current_hp += actual_heal
        return actual_heal

    def gain_exp(self, amount: int) -> None:
        """Add experience points."""
        self.exp += amount

        while self.exp >= self.exp_to_level and self.level < LEVEL_MAX:
            self.exp -= self.exp_to_level
            self.level_up()

    def level_up(self) -> None:
        """Increase unit level and improve stats."""
        if self.level < LEVEL_MAX:
            self.level += 1
            self.exp_to_level = 100 * self.level

            stat_growth = {
                UnitClass.KNIGHT: (8, 2, 3, 1, 1),
                UnitClass.MAGE: (5, 1, 1, 1, 3),
                UnitClass.ARCHER: (6, 1, 2, 2, 1),
                UnitClass.CLERIC: (6, 1, 2, 1, 2),
                UnitClass.ROGUE: (6, 2, 1, 3, 1),
            }

            growth = stat_growth.get(self.unit_class, (6, 2, 2, 2, 2))
            self.stats.hp += growth[0]
            self.stats.str += growth[1]
            self.stats.def_ += growth[2]
            self.stats.agl += growth[3]
            self.stats.int_ += growth[4]

            self.stats.clamp()
            self.current_hp = self.stats.hp
            logger.info(f"Unit {self.name} leveled up to {self.level}")

    def reset_turn(self) -> None:
        """Reset turn-based flags."""
        self.has_acted_this_turn = False

    def is_dead(self) -> bool:
        """Check if unit is defeated."""
        return not self.is_alive or self.current_hp <= 0

    def get_hp_percentage(self) -> float:
        """Get current HP as percentage."""
        if self.stats.hp == 0:
            return 0.0
        return (self.current_hp / self.stats.hp) * 100


@dataclass
class CharacterClass:
    """Recruitable character template."""

    id: str
    name: str
    description: str
    unit_class: UnitClass
    base_level: int = 1
    recruitment_cost: int = 100
    special_abilities: List[str] = field(default_factory=list)

