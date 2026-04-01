from pathlib import Path
from collections.abc import Mapping
from typing import Any

from .base import BaseTool, ToolProposal
from openrat.core.errors import UserInputError


class FileInspectorTool(BaseTool):
    """Inspect generated files in a read-only manner."""

    name = "file_inspector"
    description = "inspect files produced by execution"
    capability = "observe"
    required_autonomy_level = 0

    DEFAULT_MAX_BYTES = 8192

    def _validate_payload(self, payload: Mapping[str, Any]) -> None:
        if not isinstance(payload, Mapping):
            raise UserInputError("payload must be a mapping")
        if "path" not in payload:
            raise UserInputError("path is required")

        mode = payload.get("mode", "text")
        if mode not in {"text", "stat"}:
            raise UserInputError("mode must be 'text' or 'stat'")

        max_bytes = payload.get("max_bytes", self.DEFAULT_MAX_BYTES)
        if not isinstance(max_bytes, int) or max_bytes <= 0:
            raise UserInputError("max_bytes must be a positive integer")

    def run(self, payload: Mapping[str, Any], session: Any) -> Mapping[str, Any]:
        proposal = ToolProposal(self.name, payload, self.capability)
        self.governance = session
        self.validate(proposal)

        path_value = str(payload["path"])
        base_dir = Path(str(payload.get("base_dir", Path.cwd()))).resolve()
        target = (base_dir / path_value).resolve() if not Path(path_value).is_absolute() else Path(path_value).resolve()

        try:
            target.relative_to(base_dir)
        except ValueError as exc:
            raise UserInputError("path must be inside base_dir") from exc

        if not target.exists():
            raise UserInputError(f"path does not exist: {target}")

        if target.is_dir():
            entries = sorted(p.name for p in target.iterdir())
            return {
                "status": "ok",
                "path": str(target),
                "kind": "directory",
                "entries": entries,
            }

        stat = target.stat()
        mode = payload.get("mode", "text")
        if mode == "stat":
            return {
                "status": "ok",
                "path": str(target),
                "kind": "file",
                "size": stat.st_size,
                "modified_ts": stat.st_mtime,
            }

        max_bytes = int(payload.get("max_bytes", self.DEFAULT_MAX_BYTES))
        raw = target.read_bytes()[:max_bytes]
        text = raw.decode("utf-8", errors="replace")
        return {
            "status": "ok",
            "path": str(target),
            "kind": "file",
            "size": stat.st_size,
            "content": text,
            "truncated": stat.st_size > max_bytes,
        }
