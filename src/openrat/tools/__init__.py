"""Tool framework for extensibility.

Concrete tools:
- ExecutorTool
- LogReaderTool
- FileInspectorTool
- PatchProposalTool

Core primitives:
- BaseTool
- ToolRegistry
"""

from .base import BaseTool
from .registry import ToolRegistry
from .executor import ExecutorTool, Executor
from .log_reader import LogReaderTool
from .file_inspector import FileInspectorTool
from .patch_proposal import PatchProposalTool

__all__ = [
    "BaseTool",
    "ToolRegistry",
    "ExecutorTool",
    "Executor",
    "LogReaderTool",
    "FileInspectorTool",
    "PatchProposalTool",
]
