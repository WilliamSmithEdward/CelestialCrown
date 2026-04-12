"""Quick start guide for Celestial Crown development"""

# QUICK START GUIDE - Celestial Crown

## Running the Game
```bash
python main.py
```
Launches the main menu with pygame UI.

## Running Examples
```bash
python examples.py
```
Demonstrates all core systems:
- Tactical battle mechanics
- Story/dialogue system
- Town management
- Unit leveling and progression

## Project Architecture

### Key Modules

**src/core/** - Game engine and state management
- `gameengine.py`: Main game loop and state stack
- `gamestate.py`: Base classes for all game states

**src/entities/** - Characters and units
- `Unit`: Individual combatant with stats, equipment, progression
- `UnitClass`: Different class types with unique stat growth
- `Stats`: HP, STR, DEF, AGL, INT, WIL attributes
- `Equipment`: Weapon, armor, accessory system

**src/battle/** - Tactical combat system
- `BattleGrid`: 12x8 grid for positioning units (cardinal movement only)
- `CombatSystem`: Damage calculations, hit/miss, critical strikes
- `BattleState`: Turn management and battle flow
- `Action`: Represents unit actions in combat

**src/map/** - World and battle maps
- `TileMap`: Grid-based world terrain
- `BattleMap`: Tactical battle arena
- `TerrainType`: Grass, forest, water, mountain, etc.

**src/story/** - Narrative and branching
- `StoryManager`: Tracks alignment, story flags, recruits
- `DialogueNode`: Individual story beats
- `DialogueOption`: Player dialogue choices with alignment impact
- `Chapter`: Campaign chapters with objectives

**src/town/** - Base management
- `Town`: Player home base with facilities and treasury
- `Facility`: Buildings (Tavern, Blacksmith, Temple, etc.)
- `TownManager`: Handles income, morale, and upgrades

**src/ui/** - User interface
- `Menu`: Generic menu system with keyboard/mouse support
- `Button`: Clickable UI elements
- `HUD`: Heads-up display for battle information

## Common Tasks

### 1. Create a Battle Scenario
```python
from src.entities import Unit, UnitClass
from src.battle import BattleState

# Create units
knight = Unit("hero_1", "Sir Roland", UnitClass.KNIGHT, level=5)
mage = Unit("hero_2", "Elara", UnitClass.MAGE, level=4)

enemy = Unit("goblin_1", "Goblin Chief", UnitClass.ROGUE, level=3)
enemy.team = 1  # Set as enemy

# Create battle
battle = BattleState([knight, mage], [enemy])

# Battle starts with turn order based on agility
current_unit = battle.get_current_unit()
```

### 2. Create Story Content
```python
from src.story import DialogueNode, DialogueOption, StoryManager

manager = StoryManager()

# Create dialogue
node = DialogueNode(
    id="scene_1",
    speaker="NPC_Name",
    text="Hello!",
    options=[
        DialogueOption("Yes", leads_to="scene_2", alignment_impact=10),
        DialogueOption("No", leads_to="scene_3", alignment_impact=-10)
    ]
)

manager.register_dialogue(node)
manager.start_dialogue("scene_1")
```

### 3. Create New Unit Class
```python
from src.entities import Unit, UnitClass

class Hero(Unit):
    def __init__(self, name):
        super().__init__("hero_001", name, UnitClass.KNIGHT)
        self.is_protagonist = True
        # Custom initialization
```

### 4. Build Town Facilities
```python
from src.town import Town, Facility, FacilityType

town = Town("My Town")

tavern = Facility("tavern_1", "The Inn", FacilityType.TAVERN)
blacksmith = Facility("smith_1", "Forge", FacilityType.BLACKSMITH)

town.add_facility(tavern)
town.add_facility(blacksmith)

# Generate income each turn
town.add_funds(500)
```

## Key Design Patterns

### Alignment System (Ogre Battle Style)
- Range: -100 (Chaotic) to +100 (Lawful)
- Dialogue choices modify alignment
- Final alignment determines ending
- Example: lawful player = honorable ending; chaotic = dark ending

### Turn Order
- Calculated by unit agility stat
- Higher agility = act sooner
- Reset each round

### Stat Growth
- Each unit class has different growth rates
- Knights: High HP/DEF, low AGI
- Mages: High INT, low STR/DEF
- Rogues: High AGI/STR, low DEF

### Grid Movement
- **Cardinal directions only** (winding)
- North, South, East, West
- No diagonal movement
- Manhattan distance for range calculations

## Extending the Framework

### Adding New States
Create a class inheriting from `GameState`:
```python
from src.core.gamestate import GameState, StateType

class MyNewState(GameState):
    def __init__(self):
        super().__init__()
        self.state_type = StateType.CUSTOM  # or existing type
        
    def on_enter(self): pass
    def on_exit(self): pass
    def handle_event(self, event): pass
    def update(self, delta_time): pass
    def render(self, screen): pass
```

### Adding Combat Actions
Modify `CombatSystem` to add new action types:
```python
from src.battle import ActionType

# Add to ActionType enum
class ActionType(Enum):
    ATTACK = "attack"
    MAGIC = "magic"
    SKILL = "skill"  # Add custom skills here
```

### Adding Status Effects
Extend `Unit.status_effects` list:
```python
unit.status_effects.append("poisoned")
# Check in combat: if "poisoned" in unit.status_effects
```

## Configuration
Edit `src/config.py` to customize:
- Grid size (GRID_WIDTH, GRID_HEIGHT)
- Screen resolution (SCREEN_WIDTH, SCREEN_HEIGHT)
- Unit stats ranges (STAT_MIN, STAT_MAX)
- Game balance values (experience rates, damage multipliers, etc.)

## Tips & Best Practices

1. **Unit Positioning**: Always place units on valid grid tiles before battle
2. **Stat Balancing**: Test unit matchups to ensure reasonable difficulty
3. **Story Branching**: Keep track of alignment thresholds (use flags)
4. **Performance**: Grid operations use O(height*width) - 12x8 is efficient
5. **Extensibility**: Most systems are designed to be subclassed
6. **Testing**: Use `examples.py` as a template for new features

## Next Steps for Your Game

1. Create sprite assets for units and terrain
2. Implement the battle UI rendering (unit selection, action menus)
3. Create town management UI
4. Design and implement your story chapters
5. Add sound effects and music
6. Create scenario files (YAML or JSON) for battles and maps
7. Implement save/load system
8. Add AI opponents for single-player campaigns

Happy developing! 🎮
