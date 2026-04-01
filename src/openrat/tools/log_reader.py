from collections.abc import Mapping
from typing import Any

from .base import BaseTool, ToolProposal
from openrat.core.errors import UserInputError


class LogReaderTool(BaseTool):
    """Read execution logs from artifact-like objects or mappings."""

    name = "log_reader"
    description = "read logs from artifact execution outputs"
    capability = "observe"
    required_autonomy_level = 0

    DEFAULT_MAX_CHARS = 10_000

    def _validate_payload(self, payload: Mapping[str, Any]) -> None:
        if not isinstance(payload, Mapping):
            raise UserInputError("payload must be a mapping")
        if "artifact" not in payload:
            raise UserInputError("artifact is required")
        max_chars = payload.get("max_chars", self.DEFAULT_MAX_CHARS)
        if not isinstance(max_chars, int) or max_chars <= 0:
            raise UserInputError("max_chars must be a positive integer")

    def run(self, payload: Mapping[str, Any], session: Any) -> Mapping[str, Any]:
        proposal = ToolProposal(self.name, payload, self.capability)
        self.governance = session
        self.validate(proposal)

        artifact = payload["artifact"]
        max_chars = int(payload.get("max_chars", self.DEFAULT_MAX_CHARS))
        task_id = payload.get("task_id")

        if hasattr(artifact, "to_dict"):
            data = artifact.to_dict()
        elif isinstance(artifact, Mapping):
            data = dict(artifact)
        else:
            raise UserInputError("artifact must be a mapping or object with to_dict()")

        logs = data.get("logs", ())
        if not isinstance(logs, (list, tuple)):
            logs = [str(logs)]

        observations = data.get("observations", {})
        task_logs = None
        if task_id is not None and isinstance(observations, Mapping):
            task_obs = observations.get(str(task_id), {})
            if isinstance(task_obs, Mapping):
                task_logs = task_obs.get("logs")

        if task_logs is not None:
            if isinstance(task_logs, (list, tuple)):
                lines = [str(item) for item in task_logs]
            else:
                lines = [str(task_logs)]
        else:
            lines = [str(item) for item in logs]

        text = "\n".join(lines)
        truncated = len(text) > max_chars
        if truncated:
            text = text[:max_chars]

        return {
            "status": "ok",
            "task_id": str(task_id) if task_id is not None else None,
            "log_text": text,
            "truncated": truncated,
            "line_count": len(lines),
        }
