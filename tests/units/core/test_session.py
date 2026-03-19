import sys
from pathlib import Path
import pytest

root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(root))

from openrat.core.session.session import Session
from openrat.core.governance.autonomy import AutonomyLevel
from openrat.errors import PolicyViolation, UserInputError


def test_session_dry_run_does_not_mutate_state():
    session = Session(
        autonomy=AutonomyLevel.OBSERVE,
        patch_policy="interactive",
        user_approvals={"observe"},
    )
    assert session.authorize("observe", dry_run=True) is True
    assert session.used_capabilities == set()


def test_session_authorize_records_used_when_not_dry_run():
    session = Session(
        autonomy=AutonomyLevel.OBSERVE,
        patch_policy="interactive",
        user_approvals={"observe"},
    )
    assert session.authorize("observe", dry_run=False) is True
    assert "observe" in session.used_capabilities


def test_session_rejects_excessive_autonomy():
    session = Session(autonomy=AutonomyLevel.OBSERVE, patch_policy="interactive")
    with pytest.raises(PolicyViolation, match="exceeds autonomy"):
        session.authorize("runtime.fix")


def test_session_auto_patch_policy_allows_within_autonomy():
    session = Session(autonomy=AutonomyLevel.PARAMS_ONLY, patch_policy="auto")
    assert session.authorize("params.modify") is True
    assert "params.modify" in session.used_capabilities


def test_session_invalid_patch_policy_raises():
    with pytest.raises(UserInputError, match="patch_policy"):
        Session(autonomy=AutonomyLevel.OBSERVE, patch_policy="invalid")
