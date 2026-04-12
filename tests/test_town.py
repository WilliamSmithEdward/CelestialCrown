from src.town import Facility, FacilityType, Town


def test_town_spend_funds() -> None:
    town = Town(name="Avalon", funds=500)
    assert town.spend_funds(300)
    assert town.funds == 200
    assert not town.spend_funds(999)


def test_facility_upgrade_increases_cost() -> None:
    facility = Facility(id="f1", name="Forge", type=FacilityType.BLACKSMITH, upgrade_cost=1000)
    old_cost = facility.upgrade_cost
    assert facility.upgrade()
    assert facility.level == 2
    assert facility.upgrade_cost > old_cost
