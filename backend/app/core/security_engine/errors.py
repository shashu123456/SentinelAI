"""Structured error and warning types for OpenAPI/Swagger parsing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class SpecParseError(ValueError):
    """Raised when an API specification is structurally invalid.

    Attributes:
        spec_type: "openapi" or "swagger" when detected, else None.
        version: The detected spec version string, if any.
        endpoint: ``"METHOD /path"`` when the error is tied to a specific
            operation, else None.
    """

    def __init__(
        self,
        message: str,
        *,
        spec_type: str | None = None,
        version: str | None = None,
        endpoint: str | None = None,
    ) -> None:
        super().__init__(message)
        self.spec_type = spec_type
        self.version = version
        self.endpoint = endpoint

    def __str__(self) -> str:
        location = ""
        if self.endpoint:
            location = f" at {self.endpoint}"
        return f"{super().__str__()}{location}"


@dataclass
class ParseWarning:
    """A non-fatal issue encountered while parsing a specification."""

    message: str
    code: str
    location: str | None = None
    detail: Any = None

    def to_dict(self) -> dict:
        return {
            "message": self.message,
            "code": self.code,
            "location": self.location,
            "detail": self.detail,
        }


class WarningSink:
    """Collects :class:`ParseWarning` objects during a single parse run."""

    def __init__(self) -> None:
        self._warnings: list[ParseWarning] = []

    def add(
        self,
        code: str,
        message: str,
        *,
        location: str | None = None,
        detail: Any = None,
    ) -> None:
        self._warnings.append(ParseWarning(message, code, location, detail))

    def to_list(self) -> list[dict]:
        return [w.to_dict() for w in self._warnings]

    @property
    def warnings(self) -> list[ParseWarning]:
        return list(self._warnings)
