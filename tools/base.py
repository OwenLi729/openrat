from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict

@dataclass
class ToolProposal:
    tool_name: str
    payload: Dict[str, Any]

class BaseTool(ABC):
    name: str
    required_autonomy_level: int

    def __init__(self, governance):
        self.governance = governance  # policy engine reference

    def validate(self, proposal: ToolProposal):
        """Validate schema + autonomy policy"""
        self._check_autonomy()
        self._validate_payload(proposal.payload)

    def _check_autonomy(self):
        if self.governance.autonomy_level < self.required_autonomy_level:
            raise PermissionError(f"{self.name} requires level {self.required_autonomy_level}")

    @abstractmethod
    def _validate_payload(self, payload: Dict[str, Any]):
        pass

    @abstractmethod
    def execute(self, proposal: ToolProposal):
        pass