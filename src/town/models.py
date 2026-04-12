"""Town and facility models."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class FacilityType(Enum):
    """Types of town facilities."""

    TAVERN = "tavern"
    BLACKSMITH = "blacksmith"
    TEMPLE = "temple"
    LIBRARY = "library"
    TREASURY = "treasury"
    BARRACKS = "barracks"


@dataclass
class Facility:
    """A building in the player's town/base."""

    id: str
    name: str
    type: FacilityType
    level: int = 1
    functions: List[str] = field(default_factory=list)
    upgrade_cost: int = 1000

    def upgrade(self) -> bool:
        """Upgrade the facility."""
        if self.level < 5:
            self.level += 1
            self.upgrade_cost = int(self.upgrade_cost * 1.5)
            return True
        return False


@dataclass
class Town:
    """Player home base/town."""

    name: str
    funds: int = 10000
    facilities: Dict[str, Facility] = field(default_factory=dict)
    population: int = 100
    morale: int = 50

    def add_facility(self, facility: Facility) -> None:
        """Build a new facility."""
        self.facilities[facility.id] = facility

    def get_facility(self, facility_id: str) -> Optional[Facility]:
        """Get facility by ID."""
        return self.facilities.get(facility_id)

    def add_funds(self, amount: int) -> None:
        """Add money to town treasury."""
        self.funds += amount

    def spend_funds(self, amount: int) -> bool:
        """Attempt to spend money, return success."""
        if self.funds >= amount:
            self.funds -= amount
            return True
        return False

    def change_morale(self, delta: int) -> None:
        """Change town morale."""
        self.morale = max(0, min(100, self.morale + delta))

    def get_recruitment_cost_modifier(self) -> float:
        """Get cost multiplier based on morale."""
        return 0.5 + (self.morale / 100.0)


class TownManager:
    """Manages town activities and state."""

    def __init__(self, town: Town):
        self.town = town
        self.income_per_turn = 500

    def next_turn(self) -> None:
        """Handle turn progression."""
        self.town.add_funds(self.income_per_turn)

        if self.town.morale < 50:
            self.town.change_morale(1)
        elif self.town.morale > 50:
            self.town.change_morale(-1)
