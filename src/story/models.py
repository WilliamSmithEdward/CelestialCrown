"""Story and dialogue models and manager."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional


class DialogueBranch(Enum):
    """Story branching options."""

    LAW = "law"
    NEUTRAL = "neutral"
    CHAOS = "chaos"


@dataclass
class DialogueOption:
    """A dialogue choice for the player."""

    text: str
    leads_to: str
    alignment_impact: int = 0
    callback: Optional[Callable] = None


@dataclass
class DialogueNode:
    """A single dialogue/story beat."""

    id: str
    speaker: str
    text: str
    options: List[DialogueOption] = field(default_factory=list)
    next_dialogue: Optional[str] = None
    is_event: bool = False


class StoryManager:
    """Manages story progression, characters, and branching."""

    def __init__(self):
        self.dialogues: Dict[str, DialogueNode] = {}
        self.current_dialogue: Optional[DialogueNode] = None
        self.player_alignment = 0
        self.story_flags: Dict[str, bool] = {}
        self.recruits: List[str] = []

    def register_dialogue(self, node: DialogueNode) -> None:
        """Register a dialogue node."""
        self.dialogues[node.id] = node

    def start_dialogue(self, dialogue_id: str) -> DialogueNode:
        """Start a dialogue sequence."""
        if dialogue_id in self.dialogues:
            self.current_dialogue = self.dialogues[dialogue_id]
            return self.current_dialogue
        raise ValueError(f"Dialogue {dialogue_id} not found")

    def advance_dialogue(self, option_index: int = 0) -> Optional[DialogueNode]:
        """Advance to next dialogue based on player choice."""
        if not self.current_dialogue:
            return None

        if option_index < len(self.current_dialogue.options):
            option = self.current_dialogue.options[option_index]
            self.player_alignment += option.alignment_impact
            self.player_alignment = max(-100, min(100, self.player_alignment))

            if option.callback:
                option.callback()

            return self.start_dialogue(option.leads_to)

        if self.current_dialogue.next_dialogue:
            return self.start_dialogue(self.current_dialogue.next_dialogue)

        self.current_dialogue = None
        return None

    def set_story_flag(self, flag: str, value: bool = True) -> None:
        """Set a story event flag."""
        self.story_flags[flag] = value

    def check_story_flag(self, flag: str) -> bool:
        """Check if a story event has occurred."""
        return self.story_flags.get(flag, False)

    def recruit_character(self, character_id: str) -> None:
        """Add a character to recruits."""
        if character_id not in self.recruits:
            self.recruits.append(character_id)

    def get_alignment_type(self) -> str:
        """Get player alignment category."""
        if self.player_alignment > 33:
            return "LAW"
        if self.player_alignment < -33:
            return "CHAOS"
        return "NEUTRAL"


@dataclass
class Chapter:
    """A chapter/scenario in the story."""

    id: str
    name: str
    description: str
    opening_dialogue: str
    objectives: List[str] = field(default_factory=list)
    battles: List[str] = field(default_factory=list)
    opening_cutscene: Optional[str] = None
    closing_cutscene: Optional[str] = None
