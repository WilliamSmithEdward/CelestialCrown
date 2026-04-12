"""Tests for battle grid system."""

import pytest

from src.battle.grid import BattleGrid
from src.entities import Unit, UnitClass
from src.exceptions import GridError


def test_battle_grid_creation():
    """Test grid instantiation."""
    grid = BattleGrid(12, 8)
    assert grid.width == 12
    assert grid.height == 8
    assert len(grid.units) == 0


def test_place_unit_success():
    """Test placing a unit on an empty tile."""
    grid = BattleGrid(12, 8)
    unit = Unit("u1", "Knight", UnitClass.KNIGHT)

    assert grid.place_unit(unit, 5, 5)
    assert unit.position_x == 5
    assert unit.position_y == 5
    assert grid.get_unit_at(5, 5) is unit


def test_place_unit_out_of_bounds():
    """Test placing a unit outside grid bounds."""
    grid = BattleGrid(12, 8)
    unit = Unit("u1", "Knight", UnitClass.KNIGHT)

    with pytest.raises(GridError):
        grid.place_unit(unit, 99, 99)


def test_place_unit_occupied_tile():
    """Test placing a unit on an occupied tile."""
    grid = BattleGrid(12, 8)
    unit1 = Unit("u1", "Knight", UnitClass.KNIGHT)
    unit2 = Unit("u2", "Mage", UnitClass.MAGE)

    grid.place_unit(unit1, 5, 5)

    with pytest.raises(GridError):
        grid.place_unit(unit2, 5, 5)


def test_move_unit_success():
    """Test moving a unit to a new position."""
    grid = BattleGrid(12, 8)
    unit = Unit("u1", "Knight", UnitClass.KNIGHT)

    grid.place_unit(unit, 5, 5)
    assert grid.move_unit(unit, 6, 6)

    assert unit.position_x == 6
    assert unit.position_y == 6
    assert grid.get_unit_at(5, 5) is None
    assert grid.get_unit_at(6, 6) is unit


def test_remove_unit():
    """Test removing a unit from the grid."""
    grid = BattleGrid(12, 8)
    unit = Unit("u1", "Knight", UnitClass.KNIGHT)

    grid.place_unit(unit, 5, 5)
    assert grid.remove_unit(unit)
    assert grid.get_unit_at(5, 5) is None
    assert "u1" not in grid.units


def test_get_adjacent_positions():
    """Test getting cardinally adjacent positions."""
    grid = BattleGrid(12, 8)
    adjacent = grid.get_adjacent_positions(5, 5)

    assert len(adjacent) == 4
    assert (4, 5) in adjacent  # left
    assert (6, 5) in adjacent  # right
    assert (5, 4) in adjacent  # up
    assert (5, 6) in adjacent  # down


def test_get_distance():
    """Test Manhattan distance calculation."""
    grid = BattleGrid(12, 8)

    assert grid.get_distance(0, 0, 3, 4) == 7
    assert grid.get_distance(5, 5, 5, 5) == 0
    assert grid.get_distance(0, 0, 0, 5) == 5


def test_grid_clear():
    """Test clearing the grid."""
    grid = BattleGrid(12, 8)
    unit1 = Unit("u1", "Knight", UnitClass.KNIGHT)
    unit2 = Unit("u2", "Mage", UnitClass.MAGE)

    grid.place_unit(unit1, 2, 2)
    grid.place_unit(unit2, 8, 7)

    grid.clear()

    assert len(grid.units) == 0
    assert grid.get_unit_at(2, 2) is None
    assert grid.get_unit_at(8, 7) is None
