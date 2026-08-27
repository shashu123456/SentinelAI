"""Request ID utility.

Provides a context-variable based mechanism to access the current request ID
from anywhere in the application without threading it through every function call.
"""

from contextvars import ContextVar

_current_request_id: ContextVar[str | None] = ContextVar("current_request_id", default=None)


def set_request_id(request_id: str) -> None:
    """Set the current request ID in the context."""
    _current_request_id.set(request_id)


def get_request_id() -> str | None:
    """Get the current request ID, or None if not set."""
    return _current_request_id.get()
