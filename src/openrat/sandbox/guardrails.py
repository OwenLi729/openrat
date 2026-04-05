from collections.abc import Sequence

from openrat.core.errors import UserInputError

_DANGEROUS_PATTERNS: tuple[str, ...] = (
    "rm -rf /",
    "curl | sh",
    "curl|sh",
    "wget | sh",
    "wget|sh",
    ":(){ :|:& };:",
    "mkfs",
)


def validate_command_guardrails(command: Sequence[str]) -> None:
    if not command or not all(isinstance(part, str) for part in command):
        raise UserInputError("command must be a non-empty list[str]")

    normalized = " ".join(command).lower()
    for pattern in _DANGEROUS_PATTERNS:
        if pattern in normalized:
            raise UserInputError(f"command blocked by guardrail pattern: '{pattern}'")
