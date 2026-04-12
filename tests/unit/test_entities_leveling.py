"""Tests for unit leveling and stat growth."""

import pytest

from src.entities import Unit, UnitClass


def test_unit_take_damage():
    """Test unit taking damage reduces HP."""
    unit = Unit("u1", "Knight", UnitClass.KNIGHT, level=1)
    initial_hp = unit.current_hp

    actual_damage = unit.take_damage(5)

    assert unit.current_hp < initial_hp
    assert actual_damage > 0


def test_unit_defeat():
    """Test unit dies when HP reaches 0."""
    unit = Unit("u1", "Knight", UnitClass.KNIGHT, level=1)

    unit.take_damage(1000)

    assert unit.current_hp == 0
    assert not unit.is_alive
    assert unit.is_dead()


def test_unit_heal():
    """Test unit healing."""
    unit = Unit("u1", "Knight", UnitClass.KNIGHT, level=1)

    unit.take_damage(5)
    damaged_hp = unit.current_hp

    heal_amount = unit.heal(10)

    assert unit.current_hp > damaged_hp
    assert heal_amount > 0


def test_unit_heal_over_max():
    """Test healing cannot exceed max HP."""
    unit = Unit("u1", "Knight", UnitClass.KNIGHT, level=1)
    max_hp = unit.stats.hp

    unit.take_damage(5)
    unit.heal(1000)

    assert unit.current_hp <= max_hp


def test_unit_gain_exp_no_levelup():
    """Test gaining small amount of experience doesn't level up."""
    unit = Unit("u1", "Knight", UnitClass.KNIGHT, level=1)
    initial_level = unit.level

    unit.gain_exp(10)

    assert unit.level == initial_level


def test_unit_gain_exp_level_up():
    """Test gaining enough experience levels up."""
    unit = Unit("u1", "Knight", UnitClass.KNIGHT, level=1)
    initial_level = unit.level
    exp_needed = unit.exp_to_level

    unit.gain_exp(exp_needed)

    assert unit.level > initial_level


def test_unit_level_up_stat_growth():
    """Test leveling up increases stats."""
    unit = Unit("u1", "Knight", UnitClass.KNIGHT, level=1)
    initial_hp = unit.stats.hp
    initial_str = unit.stats.str

    unit.level_up()

    assert unit.stats.hp > initial_hp
    assert unit.stats.str > initial_str


def test_unit_reset_turn():
    """Test resetting turn flags."""
    unit = Unit("u1", "Knight", UnitClass.KNIGHT, level=1)

    unit.has_acted_this_turn = True
    unit.reset_turn()

    assert not unit.has_acted_this_turn


def test_unit_get_hp_percentage():
    """Test HP percentage calculation."""
    unit = Unit("u1", "Knight", UnitClass.KNIGHT, level=1)

    assert unit.get_hp_percentage() == 100.0

    unit.take_damage(unit.stats.hp // 2)
    assert 40 < unit.get_hp_percentage() <= 60

    unit.current_hp = 0
    assert unit.get_hp_percentage() == 0


def test_unit_max_level():
    """Test unit cannot exceed max level."""
    from src.config import LEVEL_MAX

    unit = Unit("u1", "Knight", UnitClass.KNIGHT, level=LEVEL_MAX)

    unit.level_up()

    assert unit.level == LEVEL_MAX
