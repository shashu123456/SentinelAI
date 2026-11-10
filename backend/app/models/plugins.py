"""Plugin system database models.

Tracks plugin installation, configuration, enabled state, and execution history.
"""

from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.database import Base


class PluginRecord(Base):
    """Installed plugin record in the database."""

    __tablename__ = "plugins"
    __table_args__ = (
        UniqueConstraint("plugin_id", name="uq_plugins_plugin_id"),
        Index("ix_plugins_status", "status"),
        Index("ix_plugins_plugin_type", "plugin_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Identity
    plugin_id: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    plugin_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    author: Mapped[str | None] = mapped_column(String(200), nullable=True)
    homepage: Mapped[str | None] = mapped_column(String(500), nullable=True)
    license: Mapped[str] = mapped_column(String(50), default="MIT", nullable=False)

    # Status
    status: Mapped[str] = mapped_column(
        String(20), default="installed", nullable=False
    )  # installed, enabled, disabled, error, updating

    # Configuration
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    permissions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Compatibility
    min_platform_version: Mapped[str] = mapped_column(String(20), default="1.0.0", nullable=False)
    max_platform_version: Mapped[str] = mapped_column(String(20), default="", nullable=False)

    # Dependencies
    dependencies: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Entry point
    entry_point: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Organization scope (NULL = global plugin)
    organization_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("organizations.id"), nullable=True
    )

    # Execution stats
    total_executions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    successful_executions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_executions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    avg_latency_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    last_executed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Error tracking
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_since: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Lifecycle
    installed_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    enabled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    # Relationships
    organization = relationship("Organization")
    installer = relationship("User", foreign_keys=[installed_by])


class PluginExecutionLog(Base):
    """Immutable log of plugin executions."""

    __tablename__ = "plugin_execution_logs"
    __table_args__ = (
        Index("ix_plugin_exec_plugin_id", "plugin_id"),
        Index("ix_plugin_exec_created_at", "created_at"),
        Index("ix_plugin_exec_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    plugin_id: Mapped[str] = mapped_column(String(200), nullable=False)

    # Execution context
    organization_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Result
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # success, error, timeout
    duration_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Metadata
    result_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
