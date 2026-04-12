"""Campaign/session model for running a full game loop."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List
import random

from ..battle import CombatSystem
from ..entities import Unit, UnitClass
from ..town import Facility, FacilityType, Town, TownManager


@dataclass
class BattleReport:
    """Outcome details from a single battle."""

    victory: bool
    rounds: int
    enemies_defeated: int
    party_losses: int
    funds_reward: int = 0
    exp_reward: int = 0


@dataclass
class CampaignSession:
    """Persistent run state shared across game states."""

    town: Town
    town_manager: TownManager
    party: List[Unit]
    chapter: int = 1
    battle_index: int = 1
    day: int = 1
    max_chapters: int = 5
    last_report: BattleReport | None = None
    game_over: bool = False
    victory: bool = False

    @staticmethod
    def new_game() -> "CampaignSession":
        """Create a fresh campaign with a starter town and party."""
        town = Town(name="Asterhold", funds=5000, population=230, morale=55)
        town.add_facility(Facility("tavern", "Wayfarer's Tavern", FacilityType.TAVERN))
        town.add_facility(Facility("barracks", "Ironwatch Barracks", FacilityType.BARRACKS))
        town.add_facility(Facility("treasury", "Sunvault Treasury", FacilityType.TREASURY))

        party = [
            Unit("p_knight", "Aldric", UnitClass.KNIGHT, level=1),
            Unit("p_mage", "Serin", UnitClass.MAGE, level=1),
            Unit("p_archer", "Nyra", UnitClass.ARCHER, level=1),
        ]
        for unit in party:
            unit.team = 0

        return CampaignSession(town=town, town_manager=TownManager(town), party=party)

    def generate_enemy_party(self) -> List[Unit]:
        """Create an enemy squad scaled by chapter and battle progress."""
        base_level = min(1 + self.chapter + (self.battle_index // 2), 12)
        size = min(2 + self.chapter, 6)

        enemy_classes = [
            UnitClass.KNIGHT,
            UnitClass.MAGE,
            UnitClass.ARCHER,
            UnitClass.CLERIC,
            UnitClass.ROGUE,
        ]
        enemies: List[Unit] = []
        for i in range(size):
            unit_class = random.choice(enemy_classes)
            enemy = Unit(f"e_{self.chapter}_{self.battle_index}_{i}", f"Raider {i + 1}", unit_class, level=base_level)
            enemy.team = 1
            enemies.append(enemy)
        return enemies

    def recruit_unit(self) -> bool:
        """Recruit a random class unit if town has enough funds."""
        recruit_cost = 1200
        if not self.town_manager.spend_funds(recruit_cost):
            return False

        pool = [UnitClass.KNIGHT, UnitClass.MAGE, UnitClass.ARCHER, UnitClass.CLERIC, UnitClass.ROGUE]
        chosen_class = random.choice(pool)
        recruit_id = f"p_{len(self.party) + 1}_{self.day}"
        recruit = Unit(recruit_id, f"Recruit {len(self.party) + 1}", chosen_class, level=max(1, self.chapter - 1))
        recruit.team = 0
        self.party.append(recruit)
        return True

    def rest_party(self) -> None:
        """Fully recover party HP at the end of day activities."""
        for unit in self.party:
            unit.current_hp = unit.stats.hp
            unit.is_alive = True
            unit.reset_turn()

    def remove_dead_units(self) -> None:
        """Permanently remove dead units from the party."""
        self.party = [u for u in self.party if u.is_alive]

    def resolve_current_battle(self) -> BattleReport:
        """Auto-resolve one battle and apply rewards/consequences."""
        self.rest_party()
        enemies = self.generate_enemy_party()
        rounds = 0

        while any(u.is_alive for u in self.party) and any(e.is_alive for e in enemies):
            rounds += 1
            all_units = [u for u in self.party if u.is_alive] + [e for e in enemies if e.is_alive]
            all_units.sort(key=lambda unit: unit.stats.agl, reverse=True)

            for actor in all_units:
                if not actor.is_alive:
                    continue

                if actor.team == 0:
                    targets = [enemy for enemy in enemies if enemy.is_alive]
                else:
                    targets = [ally for ally in self.party if ally.is_alive]

                if not targets:
                    break

                target = random.choice(targets)
                damage, hit, _critical = CombatSystem.execute_attack(actor, target)
                if hit and damage > 0:
                    target.take_damage(damage)

            if rounds >= 40:
                break

        alive_party = [u for u in self.party if u.is_alive]
        alive_enemies = [e for e in enemies if e.is_alive]
        party_losses = len(self.party) - len(alive_party)
        enemies_defeated = len(enemies) - len(alive_enemies)

        victory = len(alive_enemies) == 0 and len(alive_party) > 0
        funds_reward = 0
        exp_reward = 0

        if victory:
            funds_reward = 700 + self.chapter * 150 + enemies_defeated * 90
            exp_reward = 40 + self.chapter * 10
            self.town_manager.add_funds(funds_reward)
            for unit in alive_party:
                unit.gain_exp(exp_reward)

            self.battle_index += 1
            if self.battle_index > 3:
                self.battle_index = 1
                self.chapter += 1

            if self.chapter > self.max_chapters:
                self.victory = True
                self.game_over = True
        else:
            self.town_manager.adjust_morale(-10)
            self.remove_dead_units()
            if len(self.party) == 0:
                self.game_over = True

        self.day += 1
        self.town_manager.next_turn()

        report = BattleReport(
            victory=victory,
            rounds=rounds,
            enemies_defeated=enemies_defeated,
            party_losses=party_losses,
            funds_reward=funds_reward,
            exp_reward=exp_reward,
        )
        self.last_report = report
        return report
