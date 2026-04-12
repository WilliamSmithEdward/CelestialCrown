from src.battle import BattleGrid, CombatSystem
from src.entities import Unit, UnitClass


def test_battle_grid_cardinal_adjacency() -> None:
    grid = BattleGrid(4, 4)
    adj = set(grid.get_adjacent_positions(1, 1))
    assert adj == {(0, 1), (2, 1), (1, 0), (1, 2)}


def test_attack_result_shape() -> None:
    attacker = Unit("a", "Attacker", UnitClass.KNIGHT)
    defender = Unit("d", "Defender", UnitClass.KNIGHT)
    damage, hit, critical = CombatSystem.execute_attack(attacker, defender)
    assert isinstance(damage, int)
    assert isinstance(hit, bool)
    assert isinstance(critical, bool)
