"""
Tests for task_manager — task creation, lifecycle, and queue management.
"""

from __future__ import annotations

import pytest

from bantu_os.agents.task_manager import (
    TaskManager,
    TaskStatus,
)


class TestTaskManager:
    """Unit tests for TaskManager."""

    @pytest.fixture
    def tm(self) -> TaskManager:
        return TaskManager()

    def test_create_task_returns_valid_id(self, tm: TaskManager) -> None:
        tid = tm.create_task("Test task", "A test description", {"key": "value"})
        assert tid.startswith("task_")
        assert tm.get_task_status(tid) == TaskStatus.PENDING

    def test_create_task_adds_to_queue(self, tm: TaskManager) -> None:
        tid = tm.create_task("Queued task", "", {})
        assert any(t.id == tid for t in tm.task_queue)
        assert len(tm.task_queue) == 1

    def test_multiple_tasks_unique_ids(self, tm: TaskManager) -> None:
        ids = [tm.create_task(f"Task {i}", "", {}) for i in range(5)]
        assert len(set(ids)) == 5

    def test_get_task_status_pending(self, tm: TaskManager) -> None:
        tid = tm.create_task("Pending check", "", {})
        assert tm.get_task_status(tid) == TaskStatus.PENDING

    def test_get_task_status_unknown_id(self, tm: TaskManager) -> None:
        assert tm.get_task_status("nonexistent") is None

    def test_get_task_result_not_completed(self, tm: TaskManager) -> None:
        tid = tm.create_task("Not done", "", {})
        assert tm.get_task_result(tid) is None

    def test_task_attributes_stored(self, tm: TaskManager) -> None:
        tid = tm.create_task("Attribute check", "description here", {"param": 42})
        task = tm.tasks[tid]
        assert task.name == "Attribute check"
        assert task.description == "description here"
        assert task.parameters == {"param": 42}
        assert task.status == TaskStatus.PENDING
        assert task.result is None
        assert task.error is None

    def test_task_status_enum_values(self) -> None:
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
