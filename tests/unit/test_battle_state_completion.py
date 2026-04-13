import math

from src.states import BattleState
from src.states.engagement import EngagementState


def test_battle_state_ignores_defeat_in_testing_mode() -> None:
    battle = BattleState()
    calls = []

    battle.mission.update = lambda delta_time, resolve_collisions=True: None
    battle.mission.is_complete = lambda: (True, "defeat")
    battle._return_to_town = lambda result, message, apply_outcome: calls.append((result, message, apply_outcome))

    battle.update(0.016)

    assert calls == []
    assert "defeat ignored" in battle.status_message.lower()


def test_battle_state_still_exits_on_victory() -> None:
    battle = BattleState()
    calls = []

    battle.mission.update = lambda delta_time, resolve_collisions=True: None
    battle.mission.is_complete = lambda: (True, "victory")
    battle._return_to_town = lambda result, message, apply_outcome: calls.append((result, message, apply_outcome))

    battle.update(0.016)

    assert calls == [("victory", "Mission complete.", True)]


def test_battle_state_dev_start_primes_immediate_engagement() -> None:
    battle = BattleState(start_in_engagement=True)
    allies = battle.mission.allied_squads(0)
    enemies = battle.mission.allied_squads(1)

    nearest = min(
        math.hypot(a.x - e.x, a.y - e.y)
        for a in allies
        for e in enemies
    )

    assert nearest <= battle.mission.collision_radius


def test_battle_state_pushes_engagement_state_on_collision() -> None:
    class _DummyEngine:
        def __init__(self):
            self.pushed = None

        def push_state(self, state):
            self.pushed = state

    battle = BattleState(start_in_engagement=True)
    engine = _DummyEngine()
    battle.engine = engine
    battle.mission.is_complete = lambda: (False, "")

    battle.update(0.016)

    assert isinstance(engine.pushed, EngagementState)
