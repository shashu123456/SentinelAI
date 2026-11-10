"""Conversation Memory — persistent memory for AI copilot conversations.

Stores conversation history, extracts entities, maintains context windows,
and provides retrieval-augmented generation context.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class MemoryEntry:
    role: str  # user, assistant, system
    content: str
    timestamp: str = ""
    intent: str = ""
    entities: dict = field(default_factory=dict)
    tool_used: str = ""
    scan_id: int | None = None

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "intent": self.intent,
            "entities": self.entities,
            "tool_used": self.tool_used,
        }


class ConversationMemory:
    """Manages conversation history with context windows and entity tracking."""

    def __init__(self, max_history: int = 50, context_window: int = 10):
        self._memories: dict[int, list[MemoryEntry]] = {}  # user_id -> entries
        self._max_history = max_history
        self._context_window = context_window
        self._entity_index: dict[int, dict[str, list[str]]] = (
            {}
        )  # user_id -> {entity_type: [values]}

    def add_entry(
        self,
        user_id: int,
        role: str,
        content: str,
        intent: str = "",
        tool_used: str = "",
        scan_id: int | None = None,
    ) -> None:
        """Add a conversation entry."""
        if user_id not in self._memories:
            self._memories[user_id] = []
            self._entity_index[user_id] = {}

        entry = MemoryEntry(
            role=role,
            content=content,
            timestamp=datetime.now(UTC).isoformat(),
            intent=intent,
            entities=self._extract_entities(content),
            tool_used=tool_used,
            scan_id=scan_id,
        )

        self._memories[user_id].append(entry)

        # Trim old history
        if len(self._memories[user_id]) > self._max_history:
            self._memories[user_id] = self._memories[user_id][-self._max_history :]

        # Update entity index
        for etype, values in entry.entities.items():
            if etype not in self._entity_index[user_id]:
                self._entity_index[user_id][etype] = []
            for v in values:
                if v not in self._entity_index[user_id][etype]:
                    self._entity_index[user_id][etype].append(v)

    def get_context_window(self, user_id: int) -> list[dict]:
        """Get the recent conversation context for AI prompts."""
        entries = self._memories.get(user_id, [])
        return [e.to_dict() for e in entries[-self._context_window :]]

    def get_full_history(self, user_id: int) -> list[dict]:
        """Get full conversation history."""
        entries = self._memories.get(user_id, [])
        return [e.to_dict() for e in entries]

    def get_entities(self, user_id: int) -> dict[str, list[str]]:
        """Get all extracted entities for a user."""
        return self._entity_index.get(user_id, {})

    def get_mentions_of(self, user_id: int, entity_type: str) -> list[str]:
        """Get all mentions of a specific entity type."""
        return self._entity_index.get(user_id, {}).get(entity_type, [])

    def build_memory_context(self, user_id: int) -> str:
        """Build a context string from conversation memory for AI prompts."""
        entries = self._memories.get(user_id, [])
        if not entries:
            return "No prior conversation context."

        recent = entries[-self._context_window :]
        lines = ["=== CONVERSATION MEMORY ==="]

        # Recent topics
        intents = [e.intent for e in recent if e.intent]
        if intents:
            from collections import Counter

            top_intents = Counter(intents).most_common(3)
            lines.append(f"Recent topics: {', '.join(i[0] for i in top_intents)}")

        # Mentioned entities
        entities = self._entity_index.get(user_id, {})
        if entities:
            lines.append("Previously discussed:")
            for etype, values in list(entities.items())[:5]:
                lines.append(f"  {etype}: {', '.join(values[:5])}")

        # Recent scan context
        recent_scans = [e.scan_id for e in recent if e.scan_id]
        if recent_scans:
            lines.append(f"Recent scan context: {recent_scans[-1]}")

        return "\n".join(lines)

    def clear(self, user_id: int) -> None:
        """Clear conversation memory for a user."""
        self._memories.pop(user_id, None)
        self._entity_index.pop(user_id, None)

    def _extract_entities(self, text: str) -> dict[str, list[str]]:
        """Extract security-relevant entities from text."""
        entities: dict[str, list[str]] = {}
        lower = text.lower()

        # CWE references
        import re

        cwes = re.findall(r"cwe[- ]?(\d+)", lower)
        if cwes:
            entities["cwe"] = [f"CWE-{c}" for c in cwes]

        # OWASP categories
        owasps = re.findall(r"(?:api|a)[-_ ]?(\d{1,2})", lower)
        if owasps:
            entities["owasp"] = [f"API{o}" for o in owasps if 1 <= int(o) <= 10]

        # Severity mentions
        severities = []
        for sev in ["critical", "high", "medium", "low"]:
            if sev in lower:
                severities.append(sev.capitalize())
        if severities:
            entities["severity"] = severities

        # Endpoint mentions
        endpoints = re.findall(r"(/[\w/\-{}]+)", text)
        if endpoints:
            entities["endpoint"] = endpoints

        # Scan IDs
        scan_ids = re.findall(r"scan\s*#?(\d+)", lower)
        if scan_ids:
            entities["scan_id"] = scan_ids

        return entities


_memory = None


def get_conversation_memory() -> ConversationMemory:
    global _memory
    if _memory is None:
        _memory = ConversationMemory()
    return _memory
