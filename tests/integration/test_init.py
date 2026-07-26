from __future__ import annotations

import os
import signal
import subprocess
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
INIT_DIR = REPO_ROOT / "init"
INIT_C_PATH = INIT_DIR / "init.c"
SERVICES_C_PATH = INIT_DIR / "services.c"


class TestInitC:
    @pytest.fixture(scope="class")
    def init_binary(self, tmp_path_factory) -> Path:
        if not INIT_C_PATH.exists():
            pytest.skip(f"init.c not found at {INIT_C_PATH}")
        tmp = tmp_path_factory.mktemp("init_build")
        binary = tmp / "bantu_init"
        result = subprocess.run(
            [
                "gcc",
                "-o",
                str(binary),
                "-Wall",
                "-Wextra",
                "-std=c11",
                "-Wno-unused-parameter",
                str(INIT_C_PATH),
                str(SERVICES_C_PATH),
                str(INIT_C_PATH.parent / "registry_socket.c"),
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            pytest.fail(
                f"gcc compile failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
            )
        return binary

    def test_init_compiles(self, init_binary: Path):
        assert init_binary.exists(), "Compiled init binary should exist"
        assert init_binary.stat().st_size > 0, "Binary should be non-empty"

    def test_init_runs_and_prints_banner(self, init_binary: Path, tmp_path):
        process = subprocess.Popen(
            [str(init_binary)],
            env={**os.environ, "BANTU_INIT_REGISTRY_SOCKET": str(tmp_path / "registry" / "init.sock")},
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
        )
        time.sleep(0.2)
        os.killpg(process.pid, signal.SIGTERM)
        output, _ = process.communicate(timeout=5)
        combined = output
        assert (
            "Bantu-OS init starting" in combined
        ), f"Expected init banner in output:\nSTDOUT:\n{output}"

    def test_init_registers_services(self, init_binary: Path, tmp_path):
        process = subprocess.Popen(
            [str(init_binary)],
            env={**os.environ, "BANTU_INIT_REGISTRY_SOCKET": str(tmp_path / "registry" / "init.sock")},
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
        )
        time.sleep(0.2)
        os.killpg(process.pid, signal.SIGTERM)
        output, _ = process.communicate(timeout=5)
        combined = output
        for svc in ("syslog", "network"):
            assert (
                svc in combined
            ), f"Service {svc!r} not registered in init output:\nSTDOUT:\n{output}"
