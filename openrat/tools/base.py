from dataclasses import dataclass
from collections.abc import Mapping
from typing import Any
from openrat.errors import UserInputError, PolicyViolation


@dataclass
class ToolProposal:
    tool_name: str
    payload: Mapping[str, Any]


class BaseTool:
    """Base class for custom tools callable by LLM agents.
    
    Subclass this to extend the framework with domain-specific tools.
    Override `name`, `description`, and `required_autonomy_level` in subclasses.
    """
    name = "BaseTool"
    description = ""
    required_autonomy_level = 0

    def __init__(self, governance: Any = None):
        self.governance = governance

    def validate(self, proposal: ToolProposal) -> bool:
        # check proposal type
        if not isinstance(proposal, ToolProposal):
            raise UserInputError("proposal must be a ToolProposal")

        # autonomy check
        if self.governance is not None:
            level = getattr(self.governance, "autonomy_level", 0)
            if level < self.required_autonomy_level:
                raise PolicyViolation("insufficient autonomy level for this tool")
        # delegate to subclass payload validator when present
        validator = getattr(self, "_validate_payload", None)
        if callable(validator):
            validator(proposal.payload)

        return True
