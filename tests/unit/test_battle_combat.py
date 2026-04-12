"""Tests for combat system."""

import pytest

from src.battle.combat import CombatSystem
from src.entities import Unit, UnitClass
from src.exceptions import CombatError


def test_damage_calculation():
    """Test damage calculation considers STR and DEF."""
    attacker = Unit("a1", "Knight", UnitClass.KNIGHT, level=1)
    defender = Unit("d1", "Mage", UnitClass.MAGE, level=1)

    # Both have default stats: STR=10, DEF=10
    damage = CombatSystem.calculate_damage(attacker, defender)

    # base = 10 + random(-5, 10), defense_reduction = 10 // 2 = 5
    # min damage = max(1, (10-5) + (-5)) = max(1, 0) = 1
    # max damage = max(1, (10-5) + 10) = 15
    assert 1 <= damage <= 15


def test_hit_chance_calculation():
    """Test hit chance based on agility difference."""
    attacker = Unit("a1", "Knight", UnitClass.KNIGHT, level=1)
    defender = Unit("d1", "Archer", UnitClass.ARCHER, level=1)

    # Knight: AGL=10, Archer: AGL=10 (same), so hit chance should be base 0.85
    hit_chance = CombatSystem.calculate_hit_chance(attacker, defender)
    assert 0.3 <= hit_chance <= 0.95
    assert abs(hit_chance - 0.85) < 0.1


def test_critical_chance_calculation():
    """Test critical chance based on agility."""
    unit = Unit("u1", "Archer", UnitClass.ARCHER, level=1)

    # Archer: AGL=10 (default), critical = (10 / 100) * 0.3 = 0.03
    crit_chance = CombatSystem.calculate_critical_chance(unit)
    assert crit_chance == pytest.approx(0.03, abs=0.001)


def test_execute_attack_miss():
    """Test attack that misses."""
    attacker = Unit("a1", "Knight", UnitClass.KNIGHT, level=1)
    defender = Unit("d1", "Archer", UnitClass.ARCHER, level=1)

    # Can't guarantee a miss, but we can test return signature
    damage, hit, is_crit = CombatSystem.execute_attack(attacker, defender)

    if not hit:
        assert damage == 0
        assert not is_crit


def test_execute_attack_hit():
    """Test attack that hits."""
    attacker = Unit("a1", "Knight", UnitClass.KNIGHT, level=1)
    defender = Unit("d1", "Mage", UnitClass.MAGE, level=1)

    # Run multiple times to get a hit
    for _ in range(100):
        damage, hit, is_crit = CombatSystem.execute_attack(attacker, defender)
        if hit:
            assert damage > 0
            break


def test_execute_attack_dead_attacker():
    """Test that attacking with a dead unit raises an error."""
    attacker = Unit("a1", "Knight", UnitClass.KNIGHT, level=1)
    defender = Unit("d1", "Mage", UnitClass.MAGE, level=1)

    attacker.is_alive = False

    with pytest.raises(CombatError):
        CombatSystem.execute_attack(attacker, defender)


def test_execute_attack_dead_defender():
    """Test that attacking a dead unit raises an error."""
    attacker = Unit("a1", "Knight", UnitClass.KNIGHT, level=1)
    defender = Unit("d1", "Mage", UnitClass.MAGE, level=1)

    defender.is_alive = False

    with pytest.raises(CombatError):
        CombatSystem.execute_attack(attacker, defender)
