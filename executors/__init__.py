"""Compatibility shim exposing openrat.executors at top-level `executors`.

This keeps older imports and monkeypatch targets working while the canonical
implementation lives under `openrat.executors`.
"""
from importlib import import_module

from openrat.executors import (
    _REGISTRY,
    EXECUTORS,
    DockerExecutor,
    ProductionDockerExecutor,
    LocalExecutor,
    set_executor_policy,
    EXECUTOR_POLICY,
)

__all__ = [
    "_REGISTRY",
    "EXECUTORS",
    "DockerExecutor",
    "ProductionDockerExecutor",
    "LocalExecutor",
    "set_executor_policy",
    "EXECUTOR_POLICY",
]
