# Bantu-OS Services Tests

import os

import pytest

from bantu_os.services import (
    FileService,
    NetworkService,
    ProcessService,
    SchedulerService,
)


class TestFileService:
    """Tests for FileService."""

    def test_read_write(self, tmp_path):
        service = FileService(base_path=str(tmp_path))
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, Bantu-OS!")

        content = service.read(str(test_file))
        assert content == "Hello, Bantu-OS!"

    def test_write_new_file(self, tmp_path):
        service = FileService(base_path=str(tmp_path))
        result = service.write(str(tmp_path / "new.txt"), "Test content")

        assert result["path"] == str(tmp_path / "new.txt")
        assert result["size"] == 12
        assert result["checksum"] is not None

    def test_write_with_overwrite(self, tmp_path):
        service = FileService(base_path=str(tmp_path))
        test_file = tmp_path / "test.txt"
        test_file.write_text("Original")

        service.write(str(test_file), "New content", allow_overwrite=True)
        assert test_file.read_text() == "New content"

    def test_write_without_overwrite_raises(self, tmp_path):
        service = FileService(base_path=str(tmp_path))
        test_file = tmp_path / "test.txt"
        test_file.write_text("Original")

        with pytest.raises(FileExistsError):
            service.write(str(test_file), "New content")

    def test_delete_requires_confirmation(self, tmp_path):
        service = FileService(base_path=str(tmp_path))
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test")

        with pytest.raises(PermissionError):
            service.delete(str(test_file))

        result = service.delete(str(test_file), confirm=True)
        assert result is True
        assert not test_file.exists()

    def test_stat(self, tmp_path):
        service = FileService(base_path=str(tmp_path))
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello")

        stat = service.stat(str(test_file))
        assert stat["name"] == "test.txt"
        assert stat["type"] == "file"
        assert stat["size"] == 5
        assert stat["checksum"] is not None

    def test_ensure_dir(self, tmp_path):
        service = FileService(base_path=str(tmp_path))
        new_dir = tmp_path / "nested" / "deep"

        result = service.ensure_dir(str(new_dir))
        assert result["created"] is True
        assert new_dir.exists()


class TestProcessService:
    """Tests for ProcessService."""

    def test_list_processes(self):
        service = ProcessService()
        processes = service.list_processes(limit=10)

        assert isinstance(processes, list)
        assert len(processes) <= 10
        assert all("pid" in p for p in processes)
        assert all("name" in p for p in processes)

    def test_get_system_stats(self):
        service = ProcessService()
        stats = service.get_system_stats()

        assert "cpu" in stats
        assert "memory" in stats
        assert "disk" in stats
        assert "process_count" in stats

    def test_check_process_exists(self):
        service = ProcessService()
        # Current process should exist
        assert service.check_process_exists(os.getpid()) is True
        # Non-existent process
        assert service.check_process_exists(99999999) is False


class TestSchedulerService:
    """Tests for SchedulerService."""

    def test_schedule_once(self, tmp_path):
        db_path = tmp_path / "test_scheduler.db"
        service = SchedulerService(db_path=str(db_path))

        result = service.schedule(
            name="Test Task",
            action="echo test",
            schedule_type="once",
            schedule_value="2099-01-01T00:00:00",
        )

        assert result["name"] == "Test Task"
        assert result["schedule_type"] == "once"
        assert result["status"] == "pending"

    def test_list_tasks(self, tmp_path):
        db_path = tmp_path / "test_scheduler.db"
        service = SchedulerService(db_path=str(db_path))

        service.schedule(name="Task 1", action="cmd1")
        service.schedule(name="Task 2", action="cmd2")

        tasks = service.list_tasks()
        assert len(tasks) >= 2

    def test_cancel_task(self, tmp_path):
        db_path = tmp_path / "test_scheduler.db"
        service = SchedulerService(db_path=str(db_path))

        result = service.schedule(name="Cancel Me", action="cmd")
        task_id = result["id"]

        cancelled = service.cancel(task_id)
        assert cancelled["status"] == "cancelled"

    def test_get_stats(self, tmp_path):
        db_path = tmp_path / "test_scheduler.db"
        service = SchedulerService(db_path=str(db_path))

        service.schedule(name="Task 1", action="cmd1")

        stats = service.get_stats()
        assert stats["total_tasks"] >= 1
        assert "timestamp" in stats


class TestNetworkService:
    """Tests for NetworkService."""

    def test_dns_lookup(self):
        service = NetworkService()
        result = service.dns_lookup("google.com")

        assert result["resolved"] is True
        assert len(result["addresses"]) > 0
        assert any(a["address"] for a in result["addresses"])

    def test_check_port(self):
        service = NetworkService()
        # Google's DNS port 53
        result = service.check_port("8.8.8.8", 53)

        # May or may not be open depending on firewall
        assert "open" in result
        assert "host" in result
        assert "port" in result

    def test_get_local_ip(self):
        service = NetworkService()
        result = service.get_local_ip()

        assert "local_ip" in result or "error" in result

    def test_check_url(self):
        service = NetworkService()
        result = service.check_url("https://httpbin.org/get")

        assert "url" in result
        assert "reachable" in result

    def test_blocked_host(self):
        service = NetworkService()
        service.add_blocked_host("blocked.example.com")

        assert "blocked.example.com" in service._blocked_hosts


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
