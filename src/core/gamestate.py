"""Game state management base classes"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any


class StateType(Enum):
    """Enumeration of game state types"""
    MAIN_MENU = "main_menu"
    TOWN = "town"
    BATTLE = "battle"
    STORY = "story"
    PAUSE_MENU = "pause_menu"
    INVENTORY = "inventory"


class GameState(ABC):
    """Base class for all game states"""
    
    def __init__(self):
        self.state_type: StateType = StateType.MAIN_MENU
        self.engine: Any = None
        
    @abstractmethod
    def on_enter(self) -> None:
        """Called when state becomes active"""
        pass
        
    @abstractmethod
    def on_exit(self) -> None:
        """Called when state is deactivated"""
        pass
        
    def on_pause(self) -> None:
        """Called when state is pushed to stack (paused)"""
        pass
        
    def on_resume(self) -> None:
        """Called when state is resumed from stack"""
        pass
        
    @abstractmethod
    def handle_event(self, event) -> None:
        """Handle pygame events"""
        pass
        
    @abstractmethod
    def update(self, delta_time: float) -> None:
        """Update state logic"""
        pass
        
    @abstractmethod
    def render(self, screen) -> None:
        """Render state to surface"""
        pass
