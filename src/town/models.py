"""Town and facility models."""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


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
            logger.info(f"Facility {self.id} upgraded to level {self.level}")
            return True
        logger.warning(f"Facility {self.id} already at max level")
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
        logger.info(f"Facility {facility.name} ({facility.id}) built in {self.name}")

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

