from src.entities import Unit, UnitClass


def test_unit_takes_damage_and_dies() -> None:
    unit = Unit("u1", "Hero", UnitClass.KNIGHT, level=1)
    unit.take_damage(10_000)
    assert unit.current_hp == 0
    assert unit.is_dead()


def test_unit_level_up_from_experience() -> None:
    unit = Unit("u1", "Hero", UnitClass.KNIGHT, level=1)
    unit.gain_exp(200)
    assert unit.level >= 2
    assert unit.current_hp == unit.stats.hp
