"""
Tests for the process scheduler.
"""

from bantu_os.core.scheduler import ProcessState, Scheduler


def dummy_task():
    return 42


def test_scheduler_add_process():
    s = Scheduler(quantum_ms=10.0)
    p = s.add_process("test_proc", dummy_task, priority=1)
    assert p.pid == 1
    assert p.name == "test_proc"
    assert p.state == ProcessState.READY


def test_scheduler_runs_highest_priority():
    s = Scheduler(quantum_ms=10.0)
    s.add_process("low", dummy_task, priority=0)
    s.add_process("high", dummy_task, priority=3)

    proc = s.schedule()
    assert proc.priority == 3
    assert proc.name == "high"


def test_scheduler_quantum_yields_cpu():
    s = Scheduler(quantum_ms=50.0)
    s.add_process("p1", dummy_task, priority=2)
    s.add_process("p2", dummy_task, priority=2)

    p1 = s.schedule()
    assert p1.state == ProcessState.RUNNING

    s.yield_cpu()
    assert p1.state == ProcessState.READY

    p2 = s.schedule()
    assert p2.name == "p2"
    assert p2.pid != p1.pid


def test_scheduler_terminates_and_returns():
    s = Scheduler(quantum_ms=10.0)
    s.add_process("add", lambda: 2 + 2)

    proc = s.schedule()
    result = s.run_current()
    assert result == 4
    assert proc.state == ProcessState.TERMINATED
    assert s._running is None


def test_scheduler_list_processes():
    s = Scheduler(quantum_ms=10.0)
    s.add_process("a", dummy_task, priority=1)
    s.add_process("b", dummy_task, priority=2)

    procs = s.list_processes()
    assert len(procs) == 2


def test_scheduler_state_counts():
    s = Scheduler(quantum_ms=10.0)
    s.add_process("p1", dummy_task, priority=1)
    s.add_process("p2", dummy_task, priority=1)

    counts = s.get_state_counts()
    assert counts["READY"] == 2
