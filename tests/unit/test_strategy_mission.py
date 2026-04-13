from src.entities import Unit, UnitClass
from src.strategy import SiteType, Squad, create_default_mission


def _make_unit(unit_id: str, unit_class: UnitClass = UnitClass.KNIGHT) -> Unit:
    unit = Unit(unit_id, unit_id, unit_class, level=2)
    unit.team = 0
    return unit


def test_issue_order_sets_target() -> None:
    mission = create_default_mission(chapter=1)
    squad = mission.allied_squads(0)[0]

    ok = mission.issue_order(squad.id, "center_fort")

    assert ok is True
    assert squad.target_site_id == "center_fort"


def test_capture_flips_site_owner() -> None:
    mission = create_default_mission(chapter=1)
    site = mission.sites["west_town"]
    site.owner = -1

    squad = Squad("a_test", "Test", units=[_make_unit("a_u1")], owner=0, x=site.x, y=site.y)
    mission.squads = [squad]

    for _ in range(20):
        mission.update(0.4)

    assert site.owner == 0


def test_mission_complete_when_enemy_base_captured() -> None:
    mission = create_default_mission(chapter=1)
    enemy_base = mission.sites["enemy_base"]

    enemy_base.owner = 0

    complete, result = mission.is_complete()

    assert complete is True
    assert result == "victory"


def test_mission_defeat_when_player_base_captured_by_default() -> None:
    mission = create_default_mission(chapter=1)
    player_base = mission.sites["player_base"]

    player_base.owner = 1
    complete, result = mission.is_complete()

    assert complete is True
    assert result == "defeat"


def test_mission_not_defeat_when_player_base_captured_with_override() -> None:
    mission = create_default_mission(chapter=1)
    mission.ignore_player_base_defeat = True
    player_base = mission.sites["player_base"]

    player_base.owner = 1
    complete, result = mission.is_complete()

    assert complete is False
    assert result == ""


def test_income_reflects_controlled_sites() -> None:
    mission = create_default_mission(chapter=1)
    for site in mission.sites.values():
        if site.site_type == SiteType.RESOURCE:
            site.owner = 0

    mission.update(0.1)

    assert mission.player_income > 0
