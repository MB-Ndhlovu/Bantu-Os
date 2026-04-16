from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
INIT_C_PATH = REPO_ROOT / 'bantu_os' / 'init' / 'init.c'


class TestInitC:
    @pytest.fixture(scope='class')
    def init_binary(self, tmp_path_factory) -> Path:
        if not INIT_C_PATH.exists():
            pytest.skip(f'init.c not found at {INIT_C_PATH}')
        tmp = tmp_path_factory.mktemp('init_build')
        binary = tmp / 'bantu_init'
        result = subprocess.run(
            ['gcc', '-o', str(binary), '-Wall', '-Wextra', '-std=c11', str(INIT_C_PATH)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            pytest.fail(f'gcc compile failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}')
        return binary

    def test_init_compiles(self, init_binary: Path):
        assert init_binary.exists(), 'Compiled init binary should exist'
        assert init_binary.stat().st_size > 0, 'Binary should be non-empty'

    def test_init_runs_and_prints_banner(self, init_binary: Path):
        result = subprocess.run(
            [str(init_binary)],
            capture_output=True,
            text=True,
            timeout=5,
        )
        # init forks and becomes PID 1 in a real Linux environment.
        # In a test environment it will likely exit or fail — we just check
        # the banner line was printed to stdout before it exits/forks.
        assert '[init] bantu_os init starting' in result.stdout, (
            f'Expected init banner in output:\n{result.stdout}\nSTDERR:\n{result.stderr}'
        )

    def test_init_registers_services(self, init_binary: Path):
        result = subprocess.run(
            [str(init_binary)],
            capture_output=True,
            text=True,
            timeout=5,
        )
        # Check that all three registered services appear in output
        for svc in ('systemd', 'logger', 'netmanager'):
            assert svc in result.stdout, (
                f'Service {svc!r} not registered in init output:\n{result.stdout}\nSTDERR:\n{result.stderr}'
            )