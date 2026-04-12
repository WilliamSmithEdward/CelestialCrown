# Development Guide

## Architecture Direction

- Keep package init files as export surfaces only.
- Place implementation code in focused modules such as models.py, systems.py, and component files.
- Keep game loop and state transitions in src/core.
- Keep state rendering and orchestration in src/states/.

## Iteration Workflow

1. Implement feature in the smallest focused module.
2. Add or update tests in tests/ for that feature.
3. Run python -m pytest.
4. Run python main.py for a smoke check.
5. Refactor only after tests are green.

## Testing Scope

- test_entities.py: progression, health, and unit state transitions.
- test_battle.py: tactical grid logic and combat API stability.
- test_story.py: branching/alignment behavior.
- test_town.py: economy/facility rules.
- test_menu_input.py: keyboard/controller menu navigation behavior.

## Suggested Next Structure Additions

- src/core/services/ for save/load, content loading, and audio services.
- Expand src/states/ with additional focused state modules as features grow.
- src/input/ package for unified keyboard/controller action mapping.
- tests/integration/ for state transition and content loading tests.
