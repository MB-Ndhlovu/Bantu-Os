# Bantu-OS Scheduler Service
# AI-native task scheduling with persistence and patterns

from __future__ import annotations

import json
import sqlite3
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


class ScheduleType(Enum):
    """Types of schedules."""

    ONCE = "once"
    RECURRING = "recurring"
    CRON = "cron"
    INTERVAL = "interval"


class TaskStatus(Enum):
    """Task status values."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ScheduledTask:
    """Scheduled task definition."""

    id: str
    name: str
    schedule_type: str
    schedule_value: str  # cron expr, interval secs, or ISO datetime
    action: str  # command or function reference
    params: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"
    created_at: str = ""
    next_run: Optional[str] = None
    last_run: Optional[str] = None
    run_count: int = 0
    error: Optional[str] = None

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class SchedulerService:
    """
    System service for AI-powered task scheduling.

    Supports one-time tasks, recurring intervals, and cron-like schedules.
    Persisted to SQLite for system resilience.
    """

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = str(Path("/home/workspace/bantu_os/data/scheduler.db"))

        # Ensure data directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        self.db_path = db_path
        self._lock = threading.Lock()
        self._callbacks: Dict[str, Callable] = {}

        self._init_db()

    def _init_db(self) -> None:
        """Initialize the SQLite database schema."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    schedule_type TEXT NOT NULL,
                    schedule_value TEXT NOT NULL,
                    action TEXT NOT NULL,
                    params TEXT DEFAULT '{}',
                    status TEXT DEFAULT 'pending',
                    created_at TEXT NOT NULL,
                    next_run TEXT,
                    last_run TEXT,
                    run_count INTEGER DEFAULT 0,
                    error TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS task_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    status TEXT NOT NULL,
                    result TEXT,
                    error TEXT,
                    FOREIGN KEY (task_id) REFERENCES tasks(id)
                )
            """)
            conn.commit()
            conn.close()

    def schedule(
        self,
        name: str,
        action: str,
        *,
        schedule_type: str = "once",
        schedule_value: str = "",
        task_id: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Schedule a new task."""
        import uuid

        task_id = task_id or str(uuid.uuid4())[:8]

        task = ScheduledTask(
            id=task_id,
            name=name,
            schedule_type=schedule_type,
            schedule_value=schedule_value,
            action=action,
            params=params or {},
        )

        # Calculate next run time
        task.next_run = self._calculate_next_run(schedule_type, schedule_value)

        with self._lock:
            conn = sqlite3.connect(self.db_path)
            conn.execute(
                """
                INSERT INTO tasks (id, name, schedule_type, schedule_value, action, params, status, created_at, next_run)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    task.id,
                    task.name,
                    task.schedule_type,
                    task.schedule_value,
                    task.action,
                    json.dumps(task.params),
                    task.status,
                    task.created_at,
                    task.next_run,
                ),
            )
            conn.commit()
            conn.close()

        self._log_operation("schedule", task.id, name)

        return asdict(task)

    def cancel(self, task_id: str) -> Dict[str, Any]:
        """Cancel a scheduled task."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cur = conn.execute(
                "SELECT id, name, status FROM tasks WHERE id = ?", (task_id,)
            )
            row = cur.fetchone()

            if not row:
                raise ValueError(f"Task {task_id} not found")

            conn.execute(
                "UPDATE tasks SET status = ? WHERE id = ?", ("cancelled", task_id)
            )
            conn.commit()
            conn.close()

        self._log_operation("cancel", task_id, row[1])

        return {
            "task_id": task_id,
            "status": "cancelled",
            "timestamp": datetime.now().isoformat(),
        }

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task details by ID."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cur = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            row = cur.fetchone()
            conn.close()

        if not row:
            return None

        return {
            "id": row[0],
            "name": row[1],
            "schedule_type": row[2],
            "schedule_value": row[3],
            "action": row[4],
            "params": json.loads(row[5]),
            "status": row[6],
            "created_at": row[7],
            "next_run": row[8],
            "last_run": row[9],
            "run_count": row[10],
            "error": row[11],
        }

    def list_tasks(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all tasks, optionally filtered by status."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            if status:
                cur = conn.execute(
                    "SELECT * FROM tasks WHERE status = ? ORDER BY created_at DESC",
                    (status,),
                )
            else:
                cur = conn.execute("SELECT * FROM tasks ORDER BY created_at DESC")

            rows = cur.fetchall()
            conn.close()

        return [
            {
                "id": r[0],
                "name": r[1],
                "schedule_type": r[2],
                "schedule_value": r[3],
                "action": r[4],
                "params": json.loads(r[5]),
                "status": r[6],
                "created_at": r[7],
                "next_run": r[8],
                "last_run": r[9],
                "run_count": r[10],
                "error": r[11],
            }
            for r in rows
        ]

    def get_pending_tasks(self) -> List[Dict[str, Any]]:
        """Get tasks that are due to run."""
        now = datetime.now().isoformat()
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cur = conn.execute(
                "SELECT * FROM tasks WHERE status = ? AND (next_run IS NULL OR next_run <= ?)",
                ("pending", now),
            )
            rows = cur.fetchall()
            conn.close()

        return [
            {
                "id": r[0],
                "name": r[1],
                "schedule_type": r[2],
                "schedule_value": r[3],
                "action": r[4],
                "params": json.loads(r[5]),
                "status": r[6],
                "created_at": r[7],
                "next_run": r[8],
                "last_run": r[9],
                "run_count": r[10],
                "error": r[11],
            }
            for r in rows
        ]

    def record_run(
        self,
        task_id: str,
        status: str,
        result: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        """Record a task execution."""
        now = datetime.now().isoformat()

        with self._lock:
            conn = sqlite3.connect(self.db_path)

            # Update task run count and last run
            conn.execute(
                """
                UPDATE tasks
                SET last_run = ?, run_count = run_count + 1, status = ?, error = ?
                WHERE id = ?
            """,
                (now, status, error, task_id),
            )

            # Update next run for recurring tasks
            cur = conn.execute(
                "SELECT schedule_type, schedule_value FROM tasks WHERE id = ?",
                (task_id,),
            )
            row = cur.fetchone()
            if row and row[0] != "once":
                next_run = self._calculate_next_run(row[0], row[1])
                conn.execute(
                    "UPDATE tasks SET next_run = ? WHERE id = ?", (next_run, task_id)
                )
            else:
                conn.execute(
                    "UPDATE tasks SET status = ? WHERE id = ?", ("completed", task_id)
                )

            # Log the run
            conn.execute(
                """
                INSERT INTO task_runs (task_id, started_at, completed_at, status, result, error)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (task_id, now, now, status, result, error),
            )

            conn.commit()
            conn.close()

    def get_task_history(self, task_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get execution history for a task."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cur = conn.execute(
                "SELECT * FROM task_runs WHERE task_id = ? ORDER BY started_at DESC LIMIT ?",
                (task_id, limit),
            )
            rows = cur.fetchall()
            conn.close()

        return [
            {
                "id": r[0],
                "task_id": r[1],
                "started_at": r[2],
                "completed_at": r[3],
                "status": r[4],
                "result": r[5],
                "error": r[6],
            }
            for r in rows
        ]

    def register_callback(self, task_id: str, callback: Callable) -> None:
        """Register a callback function for a task."""
        self._callbacks[task_id] = callback

    def get_callback(self, task_id: str) -> Optional[Callable]:
        """Get registered callback for a task."""
        return self._callbacks.get(task_id)

    def _calculate_next_run(
        self, schedule_type: str, schedule_value: str
    ) -> Optional[str]:
        """Calculate next run time based on schedule type and value."""
        now = datetime.now()

        if schedule_type == "once":
            try:
                dt = datetime.fromisoformat(schedule_value)
                return dt.isoformat() if dt > now else None
            except ValueError:
                return None

        elif schedule_type == "interval":
            try:
                seconds = int(schedule_value)
                return (now + timedelta(seconds=seconds)).isoformat()
            except ValueError:
                return None

        elif schedule_type == "recurring":
            try:
                minutes = int(schedule_value)
                return (now + timedelta(minutes=minutes)).isoformat()
            except ValueError:
                return None

        # For cron, simplified implementation (full cron would need croniter)
        elif schedule_type == "cron":
            # Default to hourly for now
            return (now + timedelta(hours=1)).isoformat()

        return None

    def _log_operation(self, operation: str, task_id: str, details: Any) -> None:
        """Log scheduler operations."""
        # Could integrate with main logging system
        pass

    def cleanup_old_runs(self, days: int = 30) -> int:
        """Clean up old task run records."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cur = conn.execute("DELETE FROM task_runs WHERE started_at < ?", (cutoff,))
            deleted = cur.rowcount
            conn.commit()
            conn.close()

        return deleted

    def get_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)

            total = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
            pending = conn.execute(
                "SELECT COUNT(*) FROM tasks WHERE status = ?", ("pending",)
            ).fetchone()[0]
            running = conn.execute(
                "SELECT COUNT(*) FROM tasks WHERE status = ?", ("running",)
            ).fetchone()[0]
            completed = conn.execute(
                "SELECT COUNT(*) FROM tasks WHERE status = ?", ("completed",)
            ).fetchone()[0]
            failed = conn.execute(
                "SELECT COUNT(*) FROM tasks WHERE status = ?", ("failed",)
            ).fetchone()[0]

            total_runs = conn.execute("SELECT COUNT(*) FROM task_runs").fetchone()[0]

            conn.close()

        return {
            "total_tasks": total,
            "pending": pending,
            "running": running,
            "completed": completed,
            "failed": failed,
            "total_runs": total_runs,
            "callbacks_registered": len(self._callbacks),
            "timestamp": datetime.now().isoformat(),
        }
