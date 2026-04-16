"""
Bantu-OS Process Scheduler
Manages process scheduling with priority queues and time-slicing.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Callable


class ProcessState(IntEnum):
    NEW = 0
    READY = 1
    RUNNING = 2
    WAITING = 3
    TERMINATED = 4


@dataclass
class Process:
    pid: int
    name: str
    priority: int = 0
    state: ProcessState = ProcessState.NEW
    created_at: float = field(default_factory=time.time)
    cpu_time_used: float = 0.0
    last_scheduled_at: float = 0.0
    func: Callable = None
    args: tuple = ()
    result: any = None


class Scheduler:
    def __init__(self, quantum_ms: float = 10.0) -> None:
        self.quantum_ms = quantum_ms
        self._ready_queues: list[list[Process]] = [ [], [], [], [] ]  # priority 0-3
        self._waiting: list[Process] = []
        self._terminated: list[Process] = []
        self._next_pid = 1
        self._running: Process | None = None

    def add_process(self, name: str, func: Callable, args: tuple = (), priority: int = 1) -> Process:
        proc = Process(pid=self._next_pid, name=name, priority=min(max(priority, 0), 3), func=func, args=args)
        self._next_pid += 1
        self._ready_queues[proc.priority].insert(0, proc)
        proc.state = ProcessState.READY
        return proc

    def schedule(self) -> Process | None:
        now = time.time()

        # Check waiting processes — move ready ones back
        still_waiting = []
        for p in self._waiting:
            # For demo: waiting processes become ready after quantum
            if now - p.last_scheduled_at >= self.quantum_ms / 1000.0:
                p.state = ProcessState.READY
                self._ready_queues[p.priority].insert(0, p)
            else:
                still_waiting.append(p)
        self._waiting = still_waiting

        # Pick highest priority non-empty queue
        for prio in range(3, -1, -1):
            if self._ready_queues[prio]:
                proc = self._ready_queues[prio].pop()
                proc.state = ProcessState.RUNNING
                proc.last_scheduled_at = now
                self._running = proc
                return proc

        self._running = None
        return None

    def run_current(self) -> any:
        if not self._running:
            return None
        try:
            result = self._running.func(*self._running.args)
            self._running.result = result
            self._running.state = ProcessState.TERMINATED
            self._terminated.append(self._running)
            self._running = None
            return result
        except Exception as e:
            self._running.state = ProcessState.TERMINATED
            self._terminated.append(self._running)
            self._running = None
            raise e

    def yield_cpu(self) -> None:
        """Called by a process to voluntarily yield the CPU."""
        if self._running:
            self._running.state = ProcessState.READY
            self._ready_queues[self._running.priority].insert(0, self._running)
            self._running = None

    def wait(self, pid: int) -> None:
        for p in self._ready_queues[self._running.priority] if self._running else []:
            if p.pid == pid:
                p.state = ProcessState.WAITING
                self._waiting.append(p)
                break

    def list_processes(self) -> list[Process]:
        out = []
        for q in self._ready_queues:
            out.extend(q)
        out.extend(self._waiting)
        out.extend(self._terminated)
        if self._running:
            out.append(self._running)
        return out

    def get_state_counts(self) -> dict:
        counts = {state.name: 0 for state in ProcessState}
        for p in self.list_processes():
            counts[p.state.name] += 1
        return counts