from src.states import BattleState


def test_battle_state_ignores_defeat_in_testing_mode() -> None:
    battle = BattleState()
    calls = []

    battle.mission.update = lambda delta_time: None
    battle.mission.is_complete = lambda: (True, "defeat")
    battle._return_to_town = lambda result, message, apply_outcome: calls.append((result, message, apply_outcome))

    battle.update(0.016)

    assert calls == []
    assert "defeat ignored" in battle.status_message.lower()


def test_battle_state_still_exits_on_victory() -> None:
    battle = BattleState()
    calls = []

    battle.mission.update = lambda delta_time: None
    battle.mission.is_complete = lambda: (True, "victory")
    battle._return_to_town = lambda result, message, apply_outcome: calls.append((result, message, apply_outcome))

    battle.update(0.016)

    assert calls == [("victory", "Mission complete.", True)]
