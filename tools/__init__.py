"""Compatibility shim exposing `openrat.tools` at top-level `tools`.

This keeps older imports working while the canonical package is `openrat`.
"""
from importlib import import_module

__all__ = []

# Lazy import submodules from openrat.tools when accessed
def __getattr__(name):
    module = import_module(f"openrat.tools.{name}")
    globals()[name] = module
    return module
"""Tools for OpenRat."""

from . import base, executor, registry

__all__ = ["base", "executor", "registry"]
