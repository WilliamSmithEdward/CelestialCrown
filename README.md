# Celestial Crown

A tactical RPG framework inspired by **Ogre Battle: March of the Black Queen**.

## Overview

Celestial Crown is a Python-based game engine for creating tactical RPGs with grid-based battles, character recruitment, town management, and branching stories with an alignment system.

## Features

### Game Systems
- **Tactical Grid-Based Battles**: Cardinal direction (winding) movement on grid maps
- **Character Management**: Recruit, level, and equip units with different classes
- **Town/Base Management**: Manage facilities, funds, and morale
- **Story System**: Branching dialogue with alignment-based choices
- **Combat System**: Attack calculations, criticals, hit chance, and special abilities
- **Unit Progression**: Experience, leveling, stat growth by class

### Architecture
- **Modular Design**: Cleanly separated core systems (battle, entities, map, story, town)
- **State-Based Engine**: Game state stack for menus, battles, and story sequences
- **Configuration-Driven**: Easy customization through `config.py`
- **Extensible Framework**: Base classes for easy subclassing and expansion

## Project Structure

```
CelestialCrown/
├── main.py                 # Entry point
├── requirements.txt        # Runtime dependencies
├── requirements-dev.txt    # Development/test dependencies
├── pytest.ini              # Test configuration
├── src/
│   ├── config.py          # Game configuration and constants
│   ├── states/            # Game state implementations
│   ├── effects/           # Visual effect package (background + primitives)
│   ├── input/             # Device-agnostic input mapping/actions
│   ├── core/              # Game engine, state management, and services
│   ├── entities/          # Units and characters (models.py)
│   ├── battle/            # Battle systems (systems.py)
│   ├── map/               # Map models (models.py)
│   ├── ui/                # UI components (button.py, menu.py, hud.py)
│   ├── story/             # Story/dialogue models (models.py)
│   └── town/              # Town models (models.py)
├── tests/                 # Automated test suite
│   ├── conftest.py
│   ├── test_battle.py
│   ├── test_entities.py
│   ├── test_menu_input.py
│   ├── test_story.py
│   └── test_town.py
├── assets/                # Game assets (sprites, maps, UI)
└── data/                  # Game data (scenarios, characters)
```

## Getting Started

### Installation

1. Install Python 3.9+
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Running the Game

```bash
python main.py
```

### Running Tests

```bash
pip install -r requirements-dev.txt
python -m pytest
```

### Integration Tests

```bash
python -m pytest tests/integration
```

## Core Concepts

### Units and Characters
Units are individual combatants with:
- Stats: HP, STR (Attack), DEF (Defense), AGL (Agility), INT (Magic), WIL (Resistance)
- Classes: Knight, Mage, Archer, Cleric, Rogue
- Equipment system for weapons, armor, and accessories
- Experience and leveling with class-based stat growth

### Battle Grid
- Tactical grid-based battles (12x8 standard)
- Cardinal-direction movement (north, south, east, west - no diagonals)
- Range-based combat with hit/miss/critical calculations
- Turn order based on unit agility

### Alignment System
Units and the player have alignment (-100 Chaos to +100 Law):
- Dialogues offer choices that shift alignment
- Different endings based on final alignment
- Affects NPC interactions and available recruits

### Town Management
- Multiple facility types (Tavern, Blacksmith, Temple, Library, etc.)
- Income generation and unit recruitment
- Morale system affecting recruitment costs
- Facility upgrades

## Extending the Framework

### Create a Custom Unit Class
```python
from src.entities import Unit, UnitClass

class MyUnit(Unit):
    def __init__(self, unit_id, name):
        super().__init__(unit_id, name, UnitClass.KNIGHT)
        # Custom initialization
```

### Add Custom Battles
```python
from src.battle import BattleState, BattleGrid

# Create battle grid and place units
grid = BattleGrid(12, 8)
# Add your units...
```

### Create Story Scenarios
```python
from src.story import DialogueNode, StoryManager

manager = StoryManager()
node = DialogueNode(
    id="test_scene",
    speaker="NPC",
    text="Hello adventurer!",
    next_dialogue="next_scene_id"
)
manager.register_dialogue(node)
```

## Development Roadmap

- [ ] Complete battle UI with unit selection and action menus
- [ ] Town management interface
- [ ] Map/scenario editor
- [ ] Save/load system
- [ ] AI opponents for single-player battles
- [ ] Multiplayer battle networking (optional)
- [ ] Sound and music system
- [ ] Sprite animation system
- [ ] Tutorial and example scenarios

## Notes

This is a framework designed to be extended. The core systems are in place, but UI implementations, asset creation, and scenario design are left to you.

## License

This software is proprietary and confidential. All rights reserved. See [LICENSE](LICENSE) file for details.
