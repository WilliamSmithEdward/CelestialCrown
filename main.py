"""Main entry point for Celestial Crown"""

from src.core.gameengine import GameEngine
from src.states import MainMenuState


def main():
    """Initialize and run the game"""
    try:
        engine = GameEngine()
        
        # Start with main menu
        main_menu = MainMenuState()
        engine.change_state(main_menu)
        
        # Run game loop
        engine.run()
    except Exception as e:
        print(f"\n❌ Error during game execution: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
