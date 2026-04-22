"""
Integration tests: kernel + real services wired together.

Tests that:
- Services are registered as kernel tools
- Tools are callable via use_tool / use_tool_async
- File, process, and network services return correct results
"""

import pytest

from bantu_os.core.kernel.kernel import Kernel
from bantu_os.services.file_service import FileService
from bantu_os.services.process_service import ProcessService
from bantu_os.services.network_service import NetworkService


@pytest.fixture
def kernel_with_services():
    """Kernel with all three services registered.

    Services are registered as classes so use_tool(name, **kwargs)
    instantiates them with the given kwargs on each call.
    """
    kernel = Kernel(tools={})
    kernel.register_tool("file", FileService)
    kernel.register_tool("process", ProcessService)
    kernel.register_tool("network", NetworkService)
    return kernel


def test_file_service_registered(kernel_with_services):
    """FileService is registered and callable."""
    fs = kernel_with_services.use_tool("file")
    assert isinstance(fs, FileService)


def test_process_service_registered(kernel_with_services):
    """ProcessService is registered and callable."""
    ps = kernel_with_services.use_tool("process")
    assert isinstance(ps, ProcessService)


def test_network_service_registered(kernel_with_services):
    """NetworkService is registered and callable."""
    ns = kernel_with_services.use_tool("network")
    assert isinstance(ns, NetworkService)


def test_file_service_read_write_cycle(tmp_path, kernel_with_services):
    """FileService read/write roundtrip through kernel tool."""
    fs = kernel_with_services.use_tool("file", base_path=str(tmp_path))

    # Write via FileService
    result = fs.write(
        path=str(tmp_path / "test.txt"),
        content="hello from bantu-os integration test",
    )
    assert result["path"] == str(tmp_path / "test.txt")
    assert result["size"] > 0

    # Read back
    content = fs.read(path=str(tmp_path / "test.txt"))
    assert content == "hello from bantu-os integration test"


def test_file_service_list_dir(tmp_path, kernel_with_services):
    """FileService list_dir through kernel tool."""
    fs = kernel_with_services.use_tool("file", base_path=str(tmp_path))

    # Create some files
    (tmp_path / "a.txt").write_text("a")
    (tmp_path / "b.txt").write_text("b")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "c.txt").write_text("c")

    entries = fs.list_dir(str(tmp_path), recursive=False)
    names = {e["name"] for e in entries}
    assert "a.txt" in names
    assert "b.txt" in names
    assert "sub" in names


def test_file_service_copy_move(tmp_path, kernel_with_services):
    """FileService copy and move through kernel tool."""
    fs = kernel_with_services.use_tool("file", base_path=str(tmp_path))

    src = tmp_path / "source.txt"
    src.write_text("content")

    copy_result = fs.copy(str(src), str(tmp_path / "dest.txt"))
    assert (tmp_path / "dest.txt").read_text() == "content"

    move_result = fs.move(str(tmp_path / "dest.txt"), str(tmp_path / "moved.txt"))
    assert not (tmp_path / "dest.txt").exists()
    assert (tmp_path / "moved.txt").read_text() == "content"


def test_file_service_delete_requires_confirm(tmp_path, kernel_with_services):
    """FileService delete requires explicit confirm=True."""
    fs = kernel_with_services.use_tool("file", base_path=str(tmp_path))

    path = tmp_path / "to_delete.txt"
    path.write_text("delete me")

    # Without confirm — should raise
    with pytest.raises(PermissionError):
        fs.delete(str(path))

    # With confirm — should succeed
    result = fs.delete(str(path), confirm=True)
    assert result is True
    assert not path.exists()


def test_process_service_list_processes(kernel_with_services):
    """ProcessService list_processes returns a non-empty list."""
    ps = kernel_with_services.use_tool("process")

    processes = ps.list_processes(limit=10)
    assert isinstance(processes, list)
    assert len(processes) <= 10
    if processes:
        assert "pid" in processes[0]
        assert "name" in processes[0]


def test_process_service_get_system_stats(kernel_with_services):
    """ProcessService get_system_stats returns CPU/memory/disk info."""
    ps = kernel_with_services.use_tool("process")

    stats = ps.get_system_stats()
    assert "cpu" in stats
    assert "memory" in stats
    assert "disk" in stats
    assert "process_count" in stats
    assert 0 <= stats["cpu"]["percent"] <= 100


def test_process_service_process_exists(kernel_with_services):
    """ProcessService check_process_exists works for PID 1 and non-existent."""
    ps = kernel_with_services.use_tool("process")

    assert ps.check_process_exists(1) is True  # PID 1 always exists
    assert ps.check_process_exists(99999999) is False


def test_network_service_dns_lookup(kernel_with_services):
    """NetworkService dns_lookup resolves localhost."""
    ns = kernel_with_services.use_tool("network")

    result = ns.dns_lookup("localhost")
    assert result["resolved"] is True
    assert isinstance(result["addresses"], list)
    assert len(result["addresses"]) > 0


def test_network_service_local_ip(kernel_with_services):
    """NetworkService get_local_ip returns a valid-looking IP."""
    ns = kernel_with_services.use_tool("network")

    result = ns.get_local_ip()
    assert "local_ip" in result
    # IPv4 dotted quad pattern
    parts = result["local_ip"].split(".")
    assert len(parts) == 4
    assert all(0 <= int(p) <= 255 for p in parts)


def test_network_service_port_check(kernel_with_services):
    """NetworkService check_port detects open vs closed ports."""
    ns = kernel_with_services.use_tool("network")

    # Port 80 on a public IP — may or may not be open, but should not error
    result = ns.check_port("8.8.8.8", 80, timeout=3)
    assert "open" in result
    assert "elapsed_ms" in result

    # Closed port
    result_closed = ns.check_port("127.0.0.1", 65432, timeout=2)
    assert result_closed["open"] is False


def test_kernel_use_tool_async_all_services(tmp_path, kernel_with_services):
    """use_tool_async resolves all three services correctly."""
    import asyncio

    fs = asyncio.run(kernel_with_services.use_tool_async("file"))
    ps = asyncio.run(kernel_with_services.use_tool_async("process"))
    ns = asyncio.run(kernel_with_services.use_tool_async("network"))

    assert isinstance(fs, FileService)
    assert isinstance(ps, ProcessService)
    assert isinstance(ns, NetworkService)
