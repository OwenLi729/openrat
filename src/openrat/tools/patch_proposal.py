from collections.abc import Mapping
from typing import Any

from .base import BaseTool, ToolProposal
from openrat.core.errors import UserInputError


class PatchProposalTool(BaseTool):
    """Create patch proposals without applying them."""

    name = "patch_proposal"
    description = "propose code/config patches while respecting patch policy"
    capability = "runtime.fix"
    required_autonomy_level = 2

    def _validate_payload(self, payload: Mapping[str, Any]) -> None:
        if not isinstance(payload, Mapping):
            raise UserInputError("payload must be a mapping")

        if not payload.get("patch_id"):
            raise UserInputError("patch_id is required")

        summary = payload.get("summary")
        if summary is not None and not isinstance(summary, str):
            raise UserInputError("summary must be a string when provided")

        scope = payload.get("scope")
        if scope is not None and not isinstance(scope, str):
            raise UserInputError("scope must be a string when provided")

    def run(self, payload: Mapping[str, Any], session: Any) -> Mapping[str, Any]:
        proposal = ToolProposal(self.name, payload, self.capability)
        self.governance = session
        self.validate(proposal)

        patch_id = str(payload["patch_id"])
        scope = payload.get("scope")
        summary = payload.get("summary", "")
        metadata = {
            "summary": summary,
            "changes": payload.get("changes", ()),
            "source": self.name,
        }

        self.propose_patch(
            session,
            patch_id=patch_id,
            scope=scope,
            metadata=metadata,
        )

        return {
            "status": "proposed",
            "patch_id": patch_id,
            "scope": scope,
            "summary": summary,
            "applied": False,
        }
