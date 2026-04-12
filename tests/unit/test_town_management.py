"""Tests for town management."""

import pytest

from src.town import Facility, FacilityType, Town, TownManager


def test_town_creation():
    """Test town initialization."""
    town = Town("Capital", funds=5000, population=150, morale=60)

    assert town.name == "Capital"
    assert town.funds == 5000
    assert town.population == 150
    assert town.morale == 60


def test_add_facility():
    """Test adding a facility to town."""
    town = Town("Capital")
    facility = Facility("f1", "Inn", FacilityType.TAVERN)

    town.add_facility(facility)

    assert facility.id in town.facilities
    assert town.get_facility("f1") is facility


def test_facility_upgrade():
    """Test upgrading a facility."""
    facility = Facility("f1", "Smith", FacilityType.BLACKSMITH, level=1, upgrade_cost=1000)

    assert facility.upgrade()
    assert facility.level == 2
    assert facility.upgrade_cost > 1000


def test_facility_max_level():
    """Test facility cannot exceed max level."""
    facility = Facility("f1", "Smith", FacilityType.BLACKSMITH, level=5)

    assert not facility.upgrade()
    assert facility.level == 5


def test_town_add_funds():
    """Test adding funds to town."""
    town = Town("Capital", funds=1000)

    town.add_funds(500)

    assert town.funds == 1500


def test_town_spend_funds_success():
    """Test successfully spending funds."""
    town = Town("Capital", funds=1000)

    assert town.spend_funds(500)
    assert town.funds == 500


def test_town_spend_funds_insufficient():
    """Test spending funds with insufficient balance."""
    town = Town("Capital", funds=100)

    assert not town.spend_funds(500)
    assert town.funds == 100


def test_town_change_morale():
    """Test adjusting town morale."""
    town = Town("Capital", morale=50)

    town.change_morale(10)
    assert town.morale == 60

    town.change_morale(-20)
    assert town.morale == 40


def test_town_morale_clamp():
    """Test morale cannot go below 0 or above 100."""
    town = Town("Capital", morale=50)

    town.change_morale(100)
    assert town.morale == 100

    town.change_morale(-150)
    assert town.morale == 0


def test_town_recruitment_modifier():
    """Test recruitment cost modifier based on morale."""
    town = Town("Capital", morale=50)

    modifier = town.get_recruitment_cost_modifier()
    assert modifier == pytest.approx(1.0, abs=0.01)

    town.morale = 100
    modifier = town.get_recruitment_cost_modifier()
    assert modifier == pytest.approx(1.5, abs=0.01)

    town.morale = 0
    modifier = town.get_recruitment_cost_modifier()
    assert modifier == pytest.approx(0.5, abs=0.01)


def test_town_manager_next_turn():
    """Test town manager turn progression."""
    town = Town("Capital", funds=1000, morale=50)
    manager = TownManager(town)

    manager.next_turn()

    assert town.funds == 1000 + 500  # income added
    assert town.morale == 50  # no change since morale is 50


def test_town_manager_morale_drift():
    """Test morale drifts back toward 50."""
    town = Town("Capital", morale=30)
    manager = TownManager(town)

    manager.next_turn()

    assert town.morale == 31  # increased by 1


def test_town_manager_spend_funds():
    """Test town manager can spend funds with logging."""
    town = Town("Capital", funds=1000)
    manager = TownManager(town)

    assert manager.spend_funds(200)
    assert town.funds == 800

    assert not manager.spend_funds(900)
    assert town.funds == 800
