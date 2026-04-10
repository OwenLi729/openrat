"""Canonical error types for the Openrat framework.

All Openrat-specific exceptions live here. The package-root
``openrat.errors`` module re-exports everything from this module
for backward compatibility.
"""
from __future__ import annotations

from typing import Optional


class OpenratError(Exception):
    """Base class for all Openrat-specific exceptions."""

    def __init__(
        self,
        message: str,
        *,
        cause: Optional[BaseException] = None,
        hint: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.cause = cause
        self.hint = hint

    def __str__(self) -> str:
        msg = super().__str__()
        if self.hint:
            msg += f"\nHint: {self.hint}"
        return msg


class UserInputError(OpenratError):
    """Invalid user input (config, command, or instruction)."""


class PolicyViolation(OpenratError):
    """Action was disallowed by the active autonomy policy."""


class ExecutionError(OpenratError):
    """Openrat failed while orchestrating execution."""


class EnvironmentError(OpenratError):
    """Execution environment is invalid or incomplete."""


class InternalError(OpenratError):
    """Invariant violation or unreachable state inside Openrat."""


class LocalExecutionBypassesSandboxError(OpenratError):
    """Trusted-host execution does not provide container sandboxing."""

    DEFAULT_MESSAGE = "Local execution bypasses container sandboxing."

    def __init__(
        self,
        message: str | None = None,
        *,
        cause: Optional[BaseException] = None,
        hint: Optional[str] = None,
    ) -> None:
        super().__init__(message or self.DEFAULT_MESSAGE, cause=cause, hint=hint)


__all__ = [
    "OpenratError",
    "UserInputError",
    "PolicyViolation",
    "ExecutionError",
    "EnvironmentError",
    "InternalError",
    "LocalExecutionBypassesSandboxError",
]
