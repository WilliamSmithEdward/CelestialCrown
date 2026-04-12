"""Event dispatching system for decoupled game logic."""

from typing import Callable, Dict, List, Optional, Any


class Event:
    """Base event class."""

    def __init__(self, event_type: str, **data):
        self.event_type = event_type
        self.data = data

    def __repr__(self) -> str:
        return f"Event({self.event_type}, {self.data})"


class EventBus:
    """Simple publish-subscribe event bus for game events."""

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}

    def subscribe(self, event_type: str, callback: Callable) -> None:
        """Subscribe a callback to an event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: str, callback: Callable) -> None:
        """Unsubscribe a callback from an event type."""
        if event_type in self._subscribers:
            self._subscribers[event_type].remove(callback)

    def emit(self, event: Event) -> None:
        """Emit an event to all subscribers."""
        if event.event_type in self._subscribers:
            for callback in self._subscribers[event.event_type]:
                try:
                    callback(event)
                except Exception as e:
                    # Log error but don't stop other subscribers
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error in event callback for {event.event_type}: {e}")

    def clear(self) -> None:
        """Clear all subscribers."""
        self._subscribers.clear()


# Global event bus instance
_global_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get or create the global event bus."""
    global _global_bus
    if _global_bus is None:
        _global_bus = EventBus()
    return _global_bus


def reset_event_bus() -> None:
    """Reset the global event bus (useful for testing)."""
    global _global_bus
    _global_bus = EventBus()
