"""Example scenario demonstrating the tactical RPG framework"""

from src.entities import Unit, UnitClass
from src.battle import BattleState, CombatSystem
from src.story import DialogueNode, DialogueOption, StoryManager
from src.town import Town, Facility, FacilityType


def example_battle():
    """Create and demonstrate a simple battle"""
    print("=" * 60)
    print("CELESTIAL CROWN - Battle System Example")
    print("=" * 60)
    
    # Create player units
    knight = Unit("unit_001", "Sir Galahad", UnitClass.KNIGHT, level=3)
    knight.stats.hp = 45
    knight.stats.str = 12
    knight.stats.def_ = 10
    knight.stats.agl = 6
    
    mage = Unit("unit_002", "Elara", UnitClass.MAGE, level=2)
    mage.stats.hp = 28
    mage.stats.str = 6
    mage.stats.def_ = 5
    mage.stats.agl = 8
    mage.stats.int_ = 14
    
    # Create enemy units
    goblin1 = Unit("enemy_001", "Goblin", UnitClass.ROGUE, level=1)
    goblin1.team = 1
    goblin1.stats.hp = 15
    goblin1.stats.str = 6
    
    goblin2 = Unit("enemy_002", "Goblin", UnitClass.ROGUE, level=1)
    goblin2.team = 1
    goblin2.stats.hp = 15
    goblin2.stats.str = 6
    
    # Create battle
    battle = BattleState([knight, mage], [goblin1, goblin2])
    
    print(f"\n▼ STARTING BATTLE")
    print(f"Player Units: {', '.join([f'{u.name} (Lv.{u.level})' for u in battle.player_units])}")
    print(f"Enemy Units: {', '.join([f'{u.name} (Lv.{u.level})' for u in battle.enemy_units])}")
    
    # Simulate a few rounds
    for round_num in range(1, 4):
        print(f"\n▼ ROUND {round_num}")
        
        for unit in battle.turn_order:
            if not unit.is_alive:
                continue
                
            print(f"\n  → {unit.name}'s turn")
            
            # Simple AI: attack first enemy alive
            if unit.team == 0:  # Player
                target = next((u for u in battle.enemy_units if u.is_alive), None)
            else:  # Enemy
                target = next((u for u in battle.player_units if u.is_alive), None)
            
            if target:
                damage, hit, critical = CombatSystem.execute_attack(unit, target)
                
                if hit:
                    actual_damage = target.take_damage(damage)
                    crit_text = " CRITICAL!" if critical else ""
                    print(f"    {unit.name} attacks {target.name} for {actual_damage} damage{crit_text}")
                    
                    if target.is_dead():
                        print(f"    {target.name} has been defeated!")
                else:
                    print(f"    {unit.name}'s attack MISSED!")
        
        # Check if battle is over
        is_over, result = battle.is_battle_over()
        if is_over:
            print(f"\n▼ BATTLE RESULT: {result}")
            break
    
    # Summary
    print("\n" + "=" * 60)
    print("UNIT STATUS AFTER BATTLE:")
    for unit in battle.all_units:
        status = "DEFEATED" if unit.is_dead() else f"{unit.current_hp}/{unit.stats.hp} HP"
        print(f"  {unit.name}: {status}")
    print("=" * 60)


def example_story():
    """Demonstrate the story and alignment system"""
    print("\n" + "=" * 60)
    print("CELESTIAL CROWN - Story System Example")
    print("=" * 60)
    
    manager = StoryManager()
    
    # Create dialogue nodes
    intro = DialogueNode(
        id="intro",
        speaker="King Aldric",
        text="Welcome, brave adventurer! Dark forces threaten our kingdom.",
        options=[
            DialogueOption(
                text="I will help you at any cost!",
                leads_to="lawful_path",
                alignment_impact=20
            ),
            DialogueOption(
                text="What's in it for me?",
                leads_to="neutral_path",
                alignment_impact=0
            ),
            DialogueOption(
                text="Your kingdom's fate is of no concern.",
                leads_to="chaotic_path",
                alignment_impact=-20
            )
        ]
    )
    
    lawful = DialogueNode(
        id="lawful_path",
        speaker="King Aldric",
        text="Your noble heart will be rewarded. Go forth with my blessing!"
    )
    
    neutral = DialogueNode(
        id="neutral_path",
        speaker="King Aldric",
        text="Ah, a pragmatist. We can work with that."
    )
    
    chaotic = DialogueNode(
        id="chaotic_path",
        speaker="King Aldric",
        text="Insolent fool! Guards, seize them!"
    )
    
    manager.register_dialogue(intro)
    manager.register_dialogue(lawful)
    manager.register_dialogue(neutral)
    manager.register_dialogue(chaotic)
    
    # Simulate dialogue
    current_node = manager.start_dialogue("intro")
    print(f"\n{current_node.speaker}: {current_node.text}\n")
    
    print("Options:")
    for i, option in enumerate(current_node.options):
        print(f"  {i}. {option.text}")
    
    # Choose lawful path
    choice = 0
    current_node = manager.advance_dialogue(choice)
    if current_node:
        print(f"\nPlayer chose: {current_node.speaker}'s response")
        print(f"{current_node.speaker}: {current_node.text}")
    print(f"\nPlayer Alignment: {manager.player_alignment} ({manager.get_alignment_type()})")


def example_town():
    """Demonstrate town management"""
    print("\n" + "=" * 60)
    print("CELESTIAL CROWN - Town Management Example")
    print("=" * 60)
    
    town = Town("Evergrad", funds=5000, population=250, morale=60)
    
    # Add facilities
    tavern = Facility("facility_001", "The Wanderer's Inn", FacilityType.TAVERN, level=1)
    blacksmith = Facility("facility_002", "Ironforge Smithy", FacilityType.BLACKSMITH, level=1)
    
    town.add_facility(tavern)
    town.add_facility(blacksmith)
    
    print(f"\nTown: {town.name}")
    print(f"Population: {town.population}")
    print(f"Morale: {town.morale}/100")
    print(f"Treasury: {town.funds} gold\n")
    
    print("Facilities:")
    for facility in town.facilities.values():
        print(f"  • {facility.name} (Level {facility.level}) - {facility.type.value}")
    
    # Simulate some turns
    print("\n▼ After 10 turns of management:")
    for _ in range(10):
        town.add_funds(500)  # Income
        town.population += 5  # Growth
    
    print(f"Population: {town.population}")
    print(f"Treasury: {town.funds} gold")


def example_unit_progression():
    """Show unit leveling and stat growth"""
    print("\n" + "=" * 60)
    print("CELESTIAL CROWN - Unit Progression Example")
    print("=" * 60)
    
    # Create a knight
    knight = Unit("demo_knight", "Sir Roland", UnitClass.KNIGHT, level=1)
    
    print(f"\n{knight.name} - {knight.unit_class.value.upper()}")
    print(f"Level: {knight.level}")
    print(f"HP: {knight.stats.hp} | STR: {knight.stats.str} | DEF: {knight.stats.def_} | AGL: {knight.stats.agl}")
    
    # Gain experience and level up
    print("\nGaining experience...")
    knight.gain_exp(150)  # Enough to level up to 2
    
    print(f"\n{knight.name} reached Level {knight.level}!")
    print(f"HP: {knight.stats.hp} | STR: {knight.stats.str} | DEF: {knight.stats.def_} | AGL: {knight.stats.agl}")
    
    # Level up to 5
    for _ in range(3):
        knight.gain_exp(300)
    
    print(f"\n{knight.name} is now Level {knight.level}!")
    print(f"HP: {knight.stats.hp} | STR: {knight.stats.str} | DEF: {knight.stats.def_} | AGL: {knight.stats.agl}")


if __name__ == "__main__":
    try:
        example_battle()
        example_story()
        example_town()
        example_unit_progression()
        
        print("\n" + "=" * 60)
        print("✓ All examples completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Error during example: {e}")
        import traceback
        traceback.print_exc()
