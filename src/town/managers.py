"""Town management: economic and facility systems."""

import logging

from .models import Town

logger = logging.getLogger(__name__)


class TownManager:
    """Manages town activities, finances, and state progression."""

    def __init__(self, town: Town):
        self.town = town
        self.income_per_turn = 500
        logger.info(f"Town manager initialized for {town.name}")

    def next_turn(self) -> None:
        """Handle turn progression: income, morale drift."""
        self.town.add_funds(self.income_per_turn)
        logger.debug(f"Added {self.income_per_turn} funds to {self.town.name} (now: {self.town.funds})")

        if self.town.morale < 50:
            self.town.change_morale(1)
        elif self.town.morale > 50:
            self.town.change_morale(-1)

        logger.debug(f"Town morale: {self.town.morale}")

    def add_funds(self, amount: int) -> None:
        """Add funds with logging."""
        self.town.add_funds(amount)
        logger.debug(f"Added {amount} funds to {self.town.name}")

    def spend_funds(self, amount: int) -> bool:
        """Spend funds with logging."""
        if self.town.spend_funds(amount):
            logger.debug(f"Spent {amount} funds from {self.town.name}")
            return True
        logger.warning(f"Insufficient funds for {self.town.name}: needed {amount}, have {self.town.funds}")
        return False

    def adjust_morale(self, delta: int) -> None:
        """Change morale with logging."""
        old_morale = self.town.morale
        self.town.change_morale(delta)
        logger.debug(f"{self.town.name} morale changed from {old_morale} to {self.town.morale}")
