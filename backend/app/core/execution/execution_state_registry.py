"""ExecutionStateRegistry — In-memory registry keyed by execution_id.

Responsibilities:
• Store and retrieve ExecutionState instances in an in-memory dictionary
• Thread-safe access using RLock (concurrent reads, exclusive writes)
• Pure registry layer — no persistence, no execution logic, no state machine

ExecutionState remains the single source of truth; this registry only references
ExecutionState instances without implementing any execution logic, state machine,
or event handling.

No persistence beyond the internal dictionary. No SQLite. No database.
No EventBus. No ExecutionEngine. No ExecutionRuntime.
No WorkflowDefinition. No persistence. No metrics.
No reporting. No business logic. No execution logic.
No state machine duplication.
"""

from __future__ import annotations

import builtins
import threading

from app.core.execution.execution_state import ExecutionState


class ExecutionStateRegistry:
    """In-memory registry for ExecutionState instances keyed by execution_id.

    This is a pure storage layer that stores and retrieves ExecutionState instances.
    Thread safety is provided via a read-write lock: concurrent reads (get, list) can
    proceed simultaneously, while writes (register, update, remove, clear) require
    exclusive access.

    ExecutionState remains the single source of truth; this registry only references
    ExecutionState instances without implementing any execution logic, state machine,
    or event handling.

    Example:
        >>> registry = ExecutionStateRegistry()
        >>> from app.core.execution.execution_state import ExecutionState, ExecutionStatus
        >>> state = ExecutionState(execution_id="exec-1", status=ExecutionStatus.RUNNING)
        >>> registry.register(state)
        >>> retrieved = registry.get("exec-1")
        >>> registry.remove("exec-1")
    """

    def __init__(self) -> None:
        """Initialize an empty ExecutionStateRegistry with a read-write lock."""
        self._store: dict[str, ExecutionState] = {}
        self._lock = threading.RLock()

    def register(self, state: ExecutionState) -> None:
        """Store an ExecutionState instance keyed by execution_id.

        If a state with the same execution_id already exists, it is replaced.

        Args:
            state: The ExecutionState instance to store.
        """
        with self._lock:
            self._store[state.execution_id] = state

    def get(self, execution_id: str) -> ExecutionState | None:
        """Retrieve a stored ExecutionState by execution_id.

        Args:
            execution_id: The execution ID to look up.

        Returns:
            The ExecutionState instance if found, otherwise None.
        """
        with self._lock:
            return self._store.get(execution_id)

    def update(self, state: ExecutionState) -> None:
        """Update a stored ExecutionState.

        Replaces the existing state for the given execution_id. If no state
        exists for that ID, it is stored (same behavior as register).

        Args:
            state: The ExecutionState instance to store/update.
        """
        with self._lock:
            self._store[state.execution_id] = state

    def remove(self, execution_id: str) -> bool:
        """Remove a session by execution_id.

        Args:
            execution_id: The execution ID to remove.

        Returns:
            True if a state was found and removed, False if not found.
        """
        with self._lock:
            if execution_id in self._store:
                del self._store[execution_id]
                return True
            return False

    def list(self) -> builtins.list[ExecutionState]:
        """Return all stored ExecutionState instances.

        Concurrent calls to list() can proceed simultaneously without blocking
        each other (read lock allows multiple concurrent readers).

        Returns:
            A list of all stored ExecutionState instances.
        """
        with self._lock:
            return list(self._store.values())

    def clear(self) -> None:
        """Remove all sessions.

        Bulk reset (e.g., for testing or restart). Concurrent reads will
        complete before the store is cleared.
        """
        with self._lock:
            self._store.clear()
