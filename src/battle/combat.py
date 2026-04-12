"""Combat system: calculations and action mechanics."""

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple

from ..entities import Unit
from ..exceptions import CombatError


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

    def __repr__(self) -> str:
        return f"Action({self.actor.name}, {self.action_type.value}, target={self.target.name if self.target else None})"


class CombatSystem:
    """Handles combat calculations and mechanics."""

    @staticmethod
    def calculate_damage(attacker: Unit, defender: Unit) -> int:
        """Calculate damage based on attacker and defender stats."""
        if not attacker.is_alive or not defender.is_alive:
            raise CombatError("Cannot calculate damage; unit is not alive")

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
        if not attacker.is_alive:
            raise CombatError(f"Attacker {attacker.name} is not alive")
        if not defender.is_alive:
            raise CombatError(f"Defender {defender.name} is not alive")

        if random.random() > CombatSystem.calculate_hit_chance(attacker, defender):
            return 0, False, False

        is_critical = random.random() < CombatSystem.calculate_critical_chance(attacker)
        damage = CombatSystem.calculate_damage(attacker, defender)
        if is_critical:
            damage = int(damage * 1.5)

        return damage, True, is_critical
