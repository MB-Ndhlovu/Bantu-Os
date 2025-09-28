"""
Task Manager - Handles task creation, execution, and lifecycle.
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class Task:
    """Represents a task to be executed by an agent."""
    id: str
    name: str
    description: str
    parameters: Dict[str, Any]
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None

class TaskManager:
    """Manages tasks and their execution."""
    
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.task_queue: List[Task] = []
    
    def create_task(self, name: str, description: str, parameters: Dict[str, Any]) -> str:
        """Create a new task and add it to the queue."""
        task_id = f"task_{len(self.tasks) + 1}"
        task = Task(
            id=task_id,
            name=name,
            description=description,
            parameters=parameters
        )
        self.tasks[task_id] = task
        self.task_queue.append(task)
        return task_id
    
    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """Get the status of a task."""
        if task_id in self.tasks:
            return self.tasks[task_id].status
        return None
    
    def get_task_result(self, task_id: str) -> Optional[Any]:
        """Get the result of a completed task."""
        if task_id in self.tasks and self.tasks[task_id].status == TaskStatus.COMPLETED:
            return self.tasks[task_id].result
        return None
