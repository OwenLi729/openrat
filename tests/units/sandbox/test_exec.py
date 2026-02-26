import sys
import pytest
from pathlib import Path
import os

# make sure the workspace root is on sys.path so our top-level
# `sandbox` package can be imported when pytest collects under
# tests/units/sandbox (which would otherwise create a conflicting
# namespace package).
root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(root))

from sandbox.exec import run_command
from sandbox.exec import ExecutionResult

FIXTURES_DIR = Path(__file__).parent / "fixtures"

def test_bad():
    result = run_command([sys.executable, str(FIXTURES_DIR / "bad_script.py")])
    assert result.return_code != 0
    assert "This is a bad script" in result.stderr
    assert "Traceback" in result.stderr
    assert result.stdout == ""


def test_exit():
    result = run_command([sys.executable, str(FIXTURES_DIR / "exit_code.py")])
    assert result.return_code == 5


def test_hello():
    result = run_command([sys.executable, str(FIXTURES_DIR / "hello.py")])
    assert result.return_code == 0
    assert "hello world" in result.stdout.lower()

def test_infinite():
    result = run_command([sys.executable, str(FIXTURES_DIR / "infinite_loop.py")], timeout=1)
    assert result.timed_out
    assert result.return_code == -1
    assert result.stdout == ""