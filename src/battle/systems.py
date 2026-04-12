"""Battle state management: turn order and overall battle flow."""

import logging
from typing import List, Optional, Tuple

from ..entities import Unit
from ..exceptions import BattleError
from .grid import BattleGrid
from .combat import Action, ActionType

logger = logging.getLogger(__name__)


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
        logger.info(f"Battle initialized: {len(player_units)} players vs {len(enemy_units)} enemies")

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
        logger.info(f"Round {self.round_number} started")

    def is_battle_over(self) -> Tuple[bool, str]:
        """Check if battle is finished, return (is_over, winner)."""
        player_alive = any(u.is_alive for u in self.player_units)
        enemies_alive = any(u.is_alive for u in self.enemy_units)

        if not player_alive:
            logger.info("Battle over: DEFEAT")
            return True, "DEFEAT"
        if not enemies_alive:
            logger.info("Battle over: VICTORY")
            return True, "VICTORY"
        return False, ""
