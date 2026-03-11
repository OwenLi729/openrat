from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class ToolProposal:
    tool_name: str
    payload: Dict[str, Any]


class BaseTool:
    name = "BaseTool"
    description = ""
    required_autonomy_level = 0

    def __init__(self, governance=None):
        self.governance = governance

    def validate(self, proposal: ToolProposal):
        # check proposal type
        if not isinstance(proposal, ToolProposal):
            raise TypeError("proposal must be a ToolProposal")

        # autonomy check
        if self.governance is not None:
            level = getattr(self.governance, "autonomy_level", 0)
            if level < self.required_autonomy_level:
                raise PermissionError("insufficient autonomy level for this tool")
        # delegate to subclass payload validator when present
        validator = getattr(self, "_validate_payload", None)
        if callable(validator):
            validator(proposal.payload)

        return True
