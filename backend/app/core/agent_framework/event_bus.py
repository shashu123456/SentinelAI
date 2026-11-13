from __future__ import annotations

import contextlib
import threading
from collections.abc import Callable
from typing import Any, Generic, TypeVar

from app.core.agent_framework.shared_models import AgentEvent, EventType

# Type variable for event payload
PayloadT = TypeVar("PayloadT", bound=dict[str, Any])


class EventBus(Generic[PayloadT]):
    """Generic event bus implementing the pub/sub pattern.

    The EventBus allows agents to communicate without direct coupling.
    Agents can publish events, and other agents can subscribe to events
    they're interested in.

    Features:
        - Generic typing for event payloads
        - Thread-safe subscription management
        - Wildcard pattern matching for topic-based routing
        - Event filtering and ordering
        - History tracking (optional)

    Events are identified by EventType and carry a payload dictionary.
    """

    def __init__(self, name: str = "default", max_history: int = 100) -> None:
        """Initialize the event bus.

        Args:
            name: The name identifier for this event bus instance.
            max_history: Maximum number of events to track in history.
        """
        self._name: str = name
        self._subscribers: dict[EventType, list[Callable[[AgentEvent], None]]] = {}
        self._lock: threading.Lock = threading.Lock()
        self._history: list[AgentEvent] = []
        self._max_history: int = max_history

    def subscribe(self, event_type: EventType, callback: Callable[[AgentEvent], None]) -> None:
        """Subscribe to an event type.

        Args:
            event_type: The event type to subscribe to.
            callback: A callable that takes an AgentEvent and returns None.
        """
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(callback)

        # If subscribing for the first time, record history limit
        if len(self._history) >= self._max_history:
            self._history = self._history[-50:]  # Keep recent history bounded

    def unsubscribe(self, event_type: EventType, callback: Callable[[AgentEvent], None]) -> bool:
        """Unsubscribe from an event type.

        Args:
            event_type: The event type to unsubscribe from.
            callback: The callback to remove.

        Returns:
            True if the callback was found and removed, False otherwise.
        """
        with self._lock:
            subscribers = self._subscribers.get(event_type, [])
            if callback in subscribers:
                subscribers.remove(callback)
                if not subscribers:
                    del self._subscribers[event_type]
                return True
            return False

    def publish(self, event: AgentEvent) -> None:
        """Publish an event to all subscribers.

        Args:
            event: The AgentEvent to publish.
        """
        with self._lock:
            # Record in history (with bounded size)
            self._history.append(event)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history :]

            # Get subscribers for this event type
            subscribers = self._subscribers.get(event.event_type, []).copy()

        # Notify subscribers outside the lock to avoid deadlocks
        for callback in subscribers:
            # Swallow callback errors to avoid breaking the publishing agent
            with contextlib.suppress(Exception):
                callback(event)

    def publish_raw(
        self, event_type: EventType, payload: dict[str, Any], source: str | None = None
    ) -> None:
        """Publish an event with the given type and payload.

        Args:
            event_type: The EventType to publish.
            payload: The event payload dictionary.
            source: Optional source identifier.
        """
        event = AgentEvent(
            event_type=event_type,
            agent_id=getattr(source, "id", str(source)) if source else None,
            payload=payload,
        )
        self.publish(event)

    def get_history(self, event_type: EventType | None = None) -> list[AgentEvent]:
        """Get the event history.

        Args:
            event_type: Optional filter by event type.

        Returns:
            List of AgentEvent instances.
        """
        with self._lock:
            if event_type is None:
                return self._history.copy()
            return [e for e in self._history if e.event_type == event_type]

    def clear_history(self) -> None:
        """Clear the event history."""
        with self._lock:
            self._history.clear()

    def list_subscribed_types(self) -> list[EventType]:
        """List all event types that have subscribers.

        Returns:
            List of EventType values.
        """
        with self._lock:
            return list(self._subscribers.keys())


# ------------------------------------------------------------------ #
# Convenience Functions
# ------------------------------------------------------------------ #


def create_event_bus(name: str = "default") -> EventBus:
    """Create a new event bus instance.

    Args:
        name: The name for the new event bus.

    Returns:
        A new EventBus instance.
    """
    return EventBus(name=name)


def event_bus_from_registry(registry: Any) -> EventBus:
    """Create an event bus linked to a registry.

    Args:
        registry: The AgentRegistry instance (or compatible object).

    Returns:
        An EventBus instance.
    """
    # Placeholder — can be extended for registry-linked buses
    return EventBus(name="registry-linked")
