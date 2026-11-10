"""SessionStore — Persists and manages scan sessions.

Responsibilities:
• Session lifecycle management (create, retrieve, update, delete sessions)
• Session state persistence using SQLite
• Session isolation and metadata storage
• Session cleanup and expiration
"""

from __future__ import annotations

import json
import sqlite3
import threading
from typing import Any

from app.core.execution.execution_state import ExecutionState, ScanSession

# Use a relative path for the default database so tests work across environments.
# This ensures the same connection sees previously created data (unlike :memory:).
_DEFAULT_DB_RELATIVE_PATH = "sessions_store.db"


class SessionStore:
    """Manages scan session persistence using SQLite.

    In production, this would use Cloudflare D1. For development and testing,
    it uses a local SQLite database with the same schema interface.
    The default database path uses a relative path so the same connection
    sees previously created data (unlike :memory: which creates a new DB each time).
    """

    def __init__(self, database_path: str | None = None) -> None:
        """Initialize the SessionStore.

        Args:
            database_path: Path to SQLite database file. If None, uses a
                          relative path 'sessions_store.db' in the current
                          working directory. Pass ':memory:' explicitly for
                          true in-memory testing (not recommended for multi-connect use).
        """
        self._lock = threading.Lock()
        self._database_path = database_path or _DEFAULT_DB_RELATIVE_PATH

    def _connect(self) -> sqlite3.Connection:
        """Get a database connection with tables ensured.

        Since we use a persistent file path (not :memory:), tables persist
        across connects.

        Returns:
            SQLite connection with sessions and session_history tables.
        """
        conn = sqlite3.connect(self._database_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                target_path TEXT,
                status TEXT NOT NULL,
                config TEXT,
                started_at REAL,
                completed_at REAL,
                duration REAL,
                error TEXT,
                files_scanned INTEGER DEFAULT 0,
                lines_scanned INTEGER DEFAULT 0,
                findings_count INTEGER DEFAULT 0,
                languages_detected TEXT DEFAULT '[]',
                agent_result TEXT,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
            """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS session_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                status TEXT NOT NULL,
                timestamp REAL NOT NULL,
                error TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
            """)

        conn.commit()
        return conn

    def create_session(
        self,
        session_id: str,
        agent_id: str,
        target_path: str,
        config: dict[str, Any] | None = None,
    ) -> ScanSession:
        """Create a new scan session.

        Args:
            session_id: Unique session identifier
            agent_id: Agent identifier
            target_path: Path being scanned
            config: Execution configuration

        Returns:
            New ScanSession instance
        """
        with self._lock:
            now = __import__("time").time()
            conn = self._connect()
            cursor = conn.cursor()

            session = ScanSession(
                session_id=session_id,
                agent_id=agent_id,
                target_path=target_path,
                config=config,
                created_at=now,
                updated_at=now,
                started_at=now,
            )

            # Build column list and placeholders dynamically to ensure alignment
            columns = [
                "session_id",
                "agent_id",
                "target_path",
                "status",
                "config",
                "started_at",
                "completed_at",
                "duration",
                "error",
                "files_scanned",
                "lines_scanned",
                "findings_count",
                "languages_detected",
                "agent_result",
                "created_at",
                "updated_at",
            ]
            placeholders = ", ".join(["?"] * len(columns))
            col_str = ", ".join(columns)

            sql = f"INSERT INTO sessions ({col_str}) VALUES ({placeholders})"

            # Serialize agent_result - use to_dict if available, otherwise str
            agent_result_val = (
                session.agent_result.to_dict()
                if session.agent_result and hasattr(session.agent_result, "to_dict")
                else str(session.agent_result) if session.agent_result else None
            )

            values = (
                session.session_id,
                session.agent_id,
                session.target_path,
                session.status.value,
                json.dumps(session.config) if session.config else None,
                session.started_at,
                session.completed_at,
                session.duration,
                session.error,
                session.files_scanned,
                session.lines_scanned,
                session.findings_count,
                json.dumps(session.languages_detected) if session.languages_detected else "[]",
                agent_result_val,
                session.created_at,
                session.updated_at,
            )

            cursor.execute(sql, values)

            conn.commit()
            conn.close()

            return session

    def get_session(self, session_id: str) -> ScanSession | None:
        """Retrieve a session by ID.

        Args:
            session_id: Session identifier

        Returns:
            ScanSession instance or None if not found
        """
        with self._lock:
            conn = self._connect()
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT session_id, agent_id, target_path, status, config,
                       started_at, completed_at, duration, error,
                       files_scanned, lines_scanned, findings_count,
                       languages_detected, agent_result, created_at, updated_at
                FROM sessions WHERE session_id = ?
                """,
                (session_id,),
            )

            row = cursor.fetchone()
            conn.close()

            if row is None:
                return None

            (
                session_id,
                agent_id,
                target_path,
                status,
                config,
                started_at,
                completed_at,
                duration,
                error,
                files_scanned,
                lines_scanned,
                findings_count,
                languages_detected,
                agent_result,
                created_at,
                updated_at,
            ) = row

            from app.core.execution.execution_state import ExecutionState, ScanSession

            status_enum = ExecutionState(status)

            session = ScanSession(
                session_id=session_id,
                agent_id=agent_id,
                target_path=target_path,
                status=status_enum,
                created_at=created_at,
                started_at=started_at,
                completed_at=completed_at,
                duration=duration or 0.0,
                config=json.loads(config) if config else None,
                error=error,
                files_scanned=files_scanned,
                lines_scanned=lines_scanned,
                findings_count=findings_count,
                languages_detected=json.loads(languages_detected) if languages_detected else [],
                agent_result=None,
            )

            if agent_result:
                try:
                    # Deserialize agent result - check for dict first, then string
                    if isinstance(agent_result, str):
                        # Could be a JSON string or str representation
                        try:
                            import json as _json

                            parsed = _json.loads(agent_result)
                            if isinstance(parsed, dict):
                                session.agent_result = parsed
                            else:
                                session.agent_result = parsed
                        except Exception:
                            session.agent_result = agent_result
                    elif isinstance(agent_result, dict):
                        session.agent_result = agent_result
                    else:
                        session.agent_result = agent_result
                except Exception:
                    pass

            return session

    def update_session(self, session: ScanSession) -> None:
        """Update an existing session with current state.

        This method re-fetches the latest session state from the database using
        the session_id, ensuring we always work with the most recent data. This
        is especially important when the session object passed in was obtained
        before recent modifications (e.g., after complete() was called on a
        different session object).

        Args:
            session: ScanSession instance with updated state
        """
        with self._lock:
            conn = self._connect()
            cursor = conn.cursor()

            # Re-fetch the latest session state from the database using the session_id
            # This ensures we always work with the most recent data, especially important
            # when the session object passed in was obtained before recent modifications
            cursor.execute(
                """
                SELECT session_id, agent_id, target_path, status, config, started_at,
                       completed_at, duration, error, files_scanned, lines_scanned, findings_count,
                       languages_detected, agent_result, created_at, updated_at
                FROM sessions WHERE session_id = ?
                """,
                (session.session_id,),
            )
            row = cursor.fetchone()

            if row is None:
                # Session doesn't exist; create it instead
                self.create_session(
                    session_id=session.session_id,
                    agent_id=session.agent_id,
                    target_path=session.target_path,
                    config=session.config,
                )
                # Use the newly created session's data
                row = cursor.execute(
                    """
                    SELECT session_id, agent_id, target_path, status, config, started_at,
                           completed_at, duration, error, files_scanned, lines_scanned, findings_count,
                           languages_detected, agent_result, created_at, updated_at
                    FROM sessions WHERE session_id = ?
                    """,
                    (session.session_id,),
                ).fetchone()

            # Unpack the re-fetched row data
            (
                db_session_id,
                db_agent_id,
                db_target_path,
                db_status,
                db_config,
                db_started_at,
                db_completed_at,
                db_duration,
                db_error,
                db_files_scanned,
                db_lines_scanned,
                db_findings_count,
                db_languages_detected,
                db_agent_result,
                db_created_at,
                db_updated_at,
            ) = row

            # Use the re-fetched status as the base, but detect completion from agent_result
            # if the in-memory session has a result that indicates completion
            set_status = db_status
            if db_agent_result is None and session.agent_result is not None:
                # The in-memory session has a result (e.g., from complete()) that wasn't persisted yet
                # Use the in-memory agent_result and mark as completed
                set_status = ExecutionState.COMPLETED.value

            # Build SET clause dynamically using the re-fetched status
            set_parts = []
            values = []

            set_parts.append("status = ?")
            values.append(set_status)

            set_parts.append("config = ?")
            values.append(json.dumps(session.config) if session.config else None)

            # Use started_at from the in-memory session if set, otherwise keep the DB value
            started_at_val = session.started_at if session.started_at is not None else db_started_at
            set_parts.append("started_at = ?")
            values.append(started_at_val)

            set_parts.append("completed_at = ?")
            values.append(session.completed_at)

            set_parts.append("duration = ?")
            values.append(session.duration)

            set_parts.append("error = ?")
            values.append(session.error)

            set_parts.append("files_scanned = ?")
            values.append(session.files_scanned)

            set_parts.append("lines_scanned = ?")
            values.append(session.lines_scanned)

            set_parts.append("findings_count = ?")
            values.append(session.findings_count)

            set_parts.append("languages_detected = ?")
            values.append(
                json.dumps(session.languages_detected) if session.languages_detected else "[]"
            )

            # Serialize agent_result - use to_dict if available, otherwise str
            agent_result_val = (
                session.agent_result.to_dict()
                if session.agent_result and hasattr(session.agent_result, "to_dict")
                else str(session.agent_result) if session.agent_result else db_agent_result
            )
            set_parts.append("agent_result = ?")
            values.append(agent_result_val)

            set_parts.append("updated_at = ?")
            values.append(session.updated_at)

            set_clause = ", ".join(set_parts)

            cursor.execute(
                f"UPDATE sessions SET {set_clause} WHERE session_id = ?",
                (*values, session.session_id),
            )

            # Record in history
            cursor.execute(
                """
                INSERT INTO session_history (session_id, status, timestamp, error)
                VALUES (?, ?, ?, ?)
                """,
                (
                    session.session_id,
                    session.status.value,
                    __import__("time").time(),
                    session.error,
                ),
            )

            conn.commit()
            conn.close()

    def delete_session(self, session_id: str) -> bool:
        """Delete a session.

        Args:
            session_id: Session identifier

        Returns:
            True if session was deleted, False if not found
        """
        with self._lock:
            conn = self._connect()
            cursor = conn.cursor()

            cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            rows_deleted_sessions = cursor.rowcount

            cursor.execute("DELETE FROM session_history WHERE session_id = ?", (session_id,))
            rows_deleted_history = cursor.rowcount

            deleted = rows_deleted_sessions > 0 or rows_deleted_history > 0

            conn.commit()
            conn.close()

            return deleted

    def list_sessions(
        self,
        status: str | None = None,
        agent_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """List sessions with optional filtering.

        Args:
            status: Filter by status (e.g., 'completed', 'failed')
            agent_id: Filter by agent_id
            limit: Maximum number of sessions to return

        Returns:
            List of session dictionaries
        """
        with self._lock:
            conn = self._connect()
            cursor = conn.cursor()

            query = (
                "SELECT session_id, agent_id, target_path, status, started_at, "
                "completed_at, duration, error, files_scanned, findings_count, "
                "created_at FROM sessions WHERE 1=1"
            )
            params = []

            if status:
                query += " AND status = ?"
                params.append(status)

            if agent_id:
                query += " AND agent_id = ?"
                params.append(agent_id)

            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)

            rows = cursor.fetchall()
            conn.close()

            return [
                {
                    "session_id": row[0],
                    "agent_id": row[1],
                    "target_path": row[2],
                    "status": row[3],
                    "started_at": row[4],
                    "completed_at": row[5],
                    "duration": row[6],
                    "error": row[7],
                    "files_scanned": row[8],
                    "findings_count": row[9],
                    "created_at": row[10],
                }
                for row in rows
            ]

    def cleanup_expired(self, max_age_hours: int = 24) -> int:
        """Clean up sessions older than specified age.

        Args:
            max_age_hours: Maximum age in hours

        Returns:
            Number of sessions deleted
        """
        with self._lock:
            cutoff = __import__("time").time() - (max_age_hours * 3600)
            conn = self._connect()
            cursor = conn.cursor()

            cursor.execute(
                """
                DELETE FROM sessions WHERE created_at < ?
                DELETE FROM session_history WHERE timestamp < ?
                """,
                (cutoff, cutoff),
            )

            deleted = cursor.rowcount
            conn.commit()
            conn.close()

            return deleted
