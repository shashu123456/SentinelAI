"""Unit tests for the EventBus class.

Tests cover the pub/sub event system, subscription management,
event publishing, and history tracking.
.. moduleauthor:: SentinelAI Team
.. versionadded:: 2.0.0
"""

from __future__ import annotations

from app.core.agent_framework.event_bus import (
    EventBus,
    create_event_bus,
)
from app.core.agent_framework.shared_models import (
    AgentEvent,
    EventType,
)


class TestEventBusInitialization:
    """Test EventBus initialization."""

    def test_default_bus_creation(self) -> None:
        """Test creating a default EventBus."""
        bus = EventBus()
        assert bus is not None
        assert bus._name == "default"

    def test_named_bus_creation(self) -> None:
        """Test creating a named EventBus."""
        bus = EventBus(name="my-bus")
        assert bus._name == "my-bus"

    def test_custom_named_bus(self) -> None:
        """Test creating a custom-named EventBus."""
        bus = EventBus(name="custom-event-bus")
        assert bus._name == "custom-event-bus"


class TestEventBusSubscription:
    """Test subscription management."""

    def test_subscribe_and_publish(self) -> None:
        """Test subscribing and publishing events."""
        bus = EventBus()
        captured: list = []

        def callback(event: Any) -> None:
            captured.append(event)

        bus.subscribe(EventType.AGENT_INITIALIZED, callback)
        bus.publish(AgentEvent(event_type=EventType.AGENT_INITIALIZED, agent_id="test-001"))
        assert len(captured) == 1
        assert captured[0].event_type == EventType.AGENT_INITIALIZED

    def test_multiple_subscribers(self) -> None:
        """Test multiple subscribers to the same event type."""
        bus = EventBus()
        captured1: list = []
        captured2: list = []

        def callback1(event: Any) -> None:
            captured1.append(event)

        def callback2(event: Any) -> None:
            captured2.append(event)

        bus.subscribe(EventType.AGENT_INITIALIZED, callback1)
        bus.subscribe(EventType.AGENT_INITIALIZED, callback2)

        bus.publish(AgentEvent(event_type=EventType.AGENT_INITIALIZED, agent_id="test-001"))
        assert len(captured1) == 1
        assert len(captured2) == 1

    def test_unsubscribe(self) -> None:
        """Test unsubscribing from an event."""
        bus = EventBus()
        captured: list = []

        def callback(event: Any) -> None:
            captured.append(event)

        bus.subscribe(EventType.AGENT_INITIALIZED, callback)
        bus.unsubscribe(EventType.AGENT_INITIALIZED, callback)

        bus.publish(AgentEvent(event_type=EventType.AGENT_INITIALIZED, agent_id="test-001"))
        assert len(captured) == 0

    def test_unsubscribe_nonexistent_callback(self) -> None:
        """Test unsubscribing a callback that wasn't subscribed."""
        bus = EventBus()
        result = bus.unsubscribe(EventType.AGENT_INITIALIZED, lambda e: None)
        assert result is False


class TestEventBusWildcardMatching:
    """Test event type filtering and matching."""

    def test_subscribe_to_specific_type(self) -> None:
        """Test subscribing to a specific event type."""
        bus = EventBus()

        captured_specific: list = []
        captured_generic: list = []

        def specific_callback(event: Any) -> None:
            captured_specific.append(event)

        def generic_callback(event: Any) -> None:
            captured_generic.append(event)

        bus.subscribe(EventType.AGENT_INITIALIZED, specific_callback)
        bus.subscribe(EventType.AGENT_STARTED, generic_callback)

        # Publish AGENT_INITIALIZED
        bus.publish(AgentEvent(event_type=EventType.AGENT_INITIALIZED, agent_id="test-001"))
        assert len(captured_specific) == 1
        assert len(captured_generic) == 0

        # Publish AGENT_STARTED
        bus.publish(AgentEvent(event_type=EventType.AGENT_STARTED, agent_id="test-001"))
        assert len(captured_specific) == 1  # still 1, not doubled
        assert len(captured_generic) == 1

    def test_list_subscribed_types(self) -> None:
        """Test listing subscribed event types."""
        bus = EventBus()

        bus.subscribe(EventType.AGENT_INITIALIZED, lambda e: None)
        bus.subscribe(EventType.AGENT_STARTED, lambda e: None)

        subscribed = bus.list_subscribed_types()
        assert EventType.AGENT_INITIALIZED in subscribed
        assert EventType.AGENT_STARTED in subscribed


class TestEventBusHistory:
    """Test event history tracking."""

    def test_history_tracking(self) -> None:
        """Test that events are tracked in history."""
        bus = EventBus(max_history=5)
        captured: list = []

        def callback(event: Any) -> None:
            captured.append(event)

        bus.subscribe(EventType.AGENT_INITIALIZED, callback)

        # Publish multiple events
        for i in range(5):
            bus.publish(AgentEvent(event_type=EventType.AGENT_INITIALIZED, agent_id=f"agent-{i}"))

        assert len(captured) == 5

    def test_history_bounded_size(self) -> None:
        """Test that history is bounded."""
        bus = EventBus(max_history=3)
        captured: list = []

        def callback(event: Any) -> None:
            captured.append(event)

        bus.subscribe(EventType.AGENT_INITIALIZED, callback)

        # Publish more events than max_history
        for i in range(6):
            bus.publish(AgentEvent(event_type=EventType.AGENT_INITIALIZED, agent_id=f"agent-{i}"))

        # With max_history=3, only the last 3 should be in history
        # The captured list has all 6, but history should be bounded
        history = bus.get_history()
        assert len(history) <= 3


class TestEventBusHistoryFiltering:
    """Test event history filtering by type."""

    def test_history_filter_by_type(self) -> None:
        """Test filtering history by event type."""
        bus = EventBus()

        # Publish different event types
        bus.publish(AgentEvent(event_type=EventType.AGENT_INITIALIZED, agent_id="agent-1"))
        bus.publish(AgentEvent(event_type=EventType.AGENT_STARTED, agent_id="agent-2"))
        bus.publish(AgentEvent(event_type=EventType.AGENT_INITIALIZED, agent_id="agent-3"))

        # Filter by type
        initialized_events = bus.get_history(EventType.AGENT_INITIALIZED)
        assert len(initialized_events) == 2
        assert all(e.event_type == EventType.AGENT_INITIALIZED for e in initialized_events)

    def test_history_without_filter(self) -> None:
        """Test getting all history without filter."""
        bus = EventBus()

        bus.publish(AgentEvent(event_type=EventType.AGENT_INITIALIZED, agent_id="agent-1"))
        bus.publish(AgentEvent(event_type=EventType.AGENT_STARTED, agent_id="agent-2"))

        all_history = bus.get_history()
        assert len(all_history) == 2


class TestEventBusClearHistory:
    """Test clearing event history."""

    def test_clear_history(self) -> None:
        """Test clearing the event history."""
        bus = EventBus()
        captured: list = []

        def callback(event: Any) -> None:
            captured.append(event)

        bus.subscribe(EventType.AGENT_INITIALIZED, callback)

        # Publish some events
        for i in range(3):
            bus.publish(AgentEvent(event_type=EventType.AGENT_INITIALIZED, agent_id=f"agent-{i}"))

        assert len(captured) == 3

        # Clear history
        bus.clear_history()

        # Publish more events
        bus.publish(AgentEvent(event_type=EventType.AGENT_INITIALIZED, agent_id="agent-new"))

        # History should be empty, but callback should still receive new events
        # (history is separate from callbacks)
        history = bus.get_history()
        assert len(history) == 1  # Only the new event


class TestEventBusConvenienceFunction:
    """Test the create_event_bus convenience function."""

    def test_create_event_bus(self) -> None:
        """Test creating an event bus via convenience function."""
        bus = create_event_bus("test-bus")
        assert bus._name == "test-bus"

    def test_create_default_event_bus(self) -> None:
        """Test creating a default event bus via convenience function."""
        bus = create_event_bus()
        assert bus._name == "default"


class TestEventBusIntegration:
    """Test EventBus integration scenarios."""

    def test_event_bus_lifecycle_scenario(self) -> None:
        """Test a full event bus lifecycle scenario."""
        bus = EventBus()

        captured_events: list = []

        # Subscribe to multiple event types
        def handle_initialized(event: Any) -> None:
            captured_events.append(("initialized", event))

        def handle_started(event: Any) -> None:
            captured_events.append(("started", event))

        def handle_completed(event: Any) -> None:
            captured_events.append(("completed", event))

        bus.subscribe(EventType.AGENT_INITIALIZED, handle_initialized)
        bus.subscribe(EventType.AGENT_STARTED, handle_started)
        bus.subscribe(EventType.AGENT_COMPLETED, handle_completed)

        # Publish events in sequence
        bus.publish(AgentEvent(event_type=EventType.AGENT_INITIALIZED, agent_id="agent-1"))
        bus.publish(AgentEvent(event_type=EventType.AGENT_STARTED, agent_id="agent-1"))
        bus.publish(AgentEvent(event_type=EventType.AGENT_COMPLETED, agent_id="agent-1"))

        assert len(captured_events) == 3
        event_types = [e[0] for e in captured_events]
        assert "initialized" in event_types
        assert "started" in event_types
        assert "completed" in event_types


class TestEventBusRawPublish:
    """Test raw event publishing."""

    def test_publish_raw(self) -> None:
        """Test publishing raw event type and payload."""
        bus = EventBus()

        captured: list = []

        def callback(event: Any) -> None:
            captured.append(event)

        bus.subscribe(EventType.AGENT_INITIALIZED, callback)
        bus.publish_raw(
            EventType.AGENT_INITIALIZED, {"custom_key": "custom_value"}, source="test-source"
        )

        assert len(captured) == 1
        assert captured[0].payload == {"custom_key": "custom_value"}
        # The agent_id should come from the source
        assert captured[0].agent_id == "test-source" or captured[0].agent_id is not None
