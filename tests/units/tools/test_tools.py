import sys
from pathlib import Path

import pytest

root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(root))

from openrat.core.errors import PolicyViolation, UserInputError
from openrat.core.governance.autonomy import AutonomyLevel
from openrat.core.session.session import Session
from openrat.tools.file_inspector import FileInspectorTool
from openrat.tools.log_reader import LogReaderTool
from openrat.tools.patch_proposal import PatchProposalTool


def test_log_reader_reads_logs_from_mapping_artifact():
    tool = LogReaderTool()
    session = Session(
        autonomy=AutonomyLevel.OBSERVE,
        patch_policy="interactive",
        user_approvals={"observe"},
    )

    result = tool.run(
        {
            "artifact": {
                "logs": ["line1", "line2"],
                "observations": {},
            },
            "max_chars": 100,
        },
        session,
    )

    assert result["status"] == "ok"
    assert result["line_count"] == 2
    assert "line1" in result["log_text"]


def test_file_inspector_reads_text_file(tmp_path):
    file_path = tmp_path / "out.txt"
    file_path.write_text("hello tools")

    tool = FileInspectorTool()
    session = Session(
        autonomy=AutonomyLevel.OBSERVE,
        patch_policy="interactive",
        user_approvals={"observe"},
    )

    result = tool.run(
        {
            "path": str(file_path),
            "base_dir": str(tmp_path),
            "mode": "text",
            "max_bytes": 50,
        },
        session,
    )

    assert result["status"] == "ok"
    assert result["kind"] == "file"
    assert "hello tools" in result["content"]


def test_file_inspector_blocks_path_outside_base_dir(tmp_path):
    inside = tmp_path / "inside.txt"
    outside = tmp_path.parent / "outside.txt"
    inside.write_text("inside")
    outside.write_text("outside")

    tool = FileInspectorTool()
    session = Session(
        autonomy=AutonomyLevel.OBSERVE,
        patch_policy="interactive",
        user_approvals={"observe"},
    )

    with pytest.raises(UserInputError, match="inside base_dir"):
        tool.run(
            {
                "path": str(outside),
                "base_dir": str(tmp_path),
                "mode": "text",
            },
            session,
        )


def test_patch_proposal_records_proposed_patch_only():
    tool = PatchProposalTool()
    session = Session(
        autonomy=AutonomyLevel.RUNTIME_REPAIR,
        patch_policy="interactive",
        user_approvals={"runtime.fix"},
    )

    result = tool.run(
        {
            "patch_id": "p-1",
            "scope": "tests",
            "summary": "adjust test fixture",
            "changes": [{"file": "x.py", "op": "replace"}],
        },
        session,
    )

    assert result["status"] == "proposed"
    assert result["applied"] is False
    assert len(session.patches_proposed) == 1
    assert len(session.patches_applied) == 0
    assert session.patches_proposed[0]["operation"] == "propose"


def test_patch_proposal_enforces_runtime_fix_capability():
    tool = PatchProposalTool()
    session = Session(
        autonomy=AutonomyLevel.OBSERVE,
        patch_policy="interactive",
        user_approvals={"observe"},
    )

    with pytest.raises(PolicyViolation):
        tool.run(
            {
                "patch_id": "p-2",
                "scope": "tests",
                "summary": "should be blocked",
            },
            session,
        )
