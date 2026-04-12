from src.core.gameengine import GameEngine
from src.states import BattleState, MainMenuState


def test_engine_changes_state() -> None:
    engine = GameEngine()

    menu = MainMenuState()
    engine.change_state(menu)
    assert engine.current_state is menu

    battle = BattleState()
    engine.change_state(battle)
    assert engine.current_state is battle
