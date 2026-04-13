"""Main entry point for Celestial Crown"""

from src.core.gameengine import GameEngine
from src.core.campaign import CampaignSession
from src.states import BattleState


def main():
    """Initialize and run the game"""
    try:
        engine = GameEngine()

        # DEV: drop straight into the battle map with an immediate squad clash.
        session = CampaignSession.new_game()
        engine.change_state(BattleState(session=session, start_in_engagement=True))
        
        # Run game loop
        engine.run()
    except Exception as e:
        print(f"\n❌ Error during game execution: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
