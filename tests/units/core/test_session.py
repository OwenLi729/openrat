import sys
from pathlib import Path
import pytest

root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(root))

from openrat.core.session.session import Session
from openrat.core.governance.autonomy import AutonomyLevel
from openrat.core.errors import PolicyViolation, UserInputError


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


def test_host_exec_requires_explicit_opt_in_even_without_approval_mode():
    session = Session(autonomy=AutonomyLevel.EXTENDED_EDIT, patch_policy="interactive")
    with pytest.raises(PolicyViolation, match="explicit user opt-in"):
        session.authorize("host.exec")


def test_host_exec_allowed_with_explicit_approval_and_sufficient_autonomy():
    session = Session(
        autonomy=AutonomyLevel.EXTENDED_EDIT,
        patch_policy="interactive",
        user_approvals={"host.exec"},
    )
    assert session.authorize("host.exec") is True


def test_session_auto_patch_policy_allows_within_autonomy():
    session = Session(autonomy=AutonomyLevel.PARAMS_ONLY, patch_policy="auto")
    assert session.authorize("params.modify") is True
    assert "params.modify" in session.used_capabilities


def test_session_invalid_patch_policy_raises():
    with pytest.raises(UserInputError, match="patch_policy"):
        Session(autonomy=AutonomyLevel.OBSERVE, patch_policy="invalid")


def test_patch_policy_enabled_blocks_patch_apply():
    session = Session(autonomy=AutonomyLevel.EXTENDED_EDIT, patch_policy="interactive")
    with pytest.raises(PolicyViolation, match="interactive policy"):
        session.record_patch(patch_id="p1", operation="apply", scope="runtime")


def test_patch_policy_enabled_allows_patch_propose():
    session = Session(autonomy=AutonomyLevel.EXTENDED_EDIT, patch_policy="interactive")
    session.record_patch(patch_id="p2", operation="propose", scope="runtime")
    assert len(session.patches_proposed) == 1
    assert session.patches_proposed[0]["patch_id"] == "p2"


def test_patch_policy_disabled_blocks_propose_and_apply():
    session = Session(autonomy=AutonomyLevel.EXTENDED_EDIT, patch_policy="disabled")

    with pytest.raises(PolicyViolation, match="disabled by patch policy"):
        session.record_patch(patch_id="p3", operation="propose", scope="runtime")

    with pytest.raises(PolicyViolation, match="disabled by patch policy"):
        session.record_patch(patch_id="p4", operation="apply", scope="runtime")


def test_cannot_mutate_authority_without_explicit_user_action():
    session = Session(autonomy=AutonomyLevel.OBSERVE, patch_policy="disabled")
    with pytest.raises(PolicyViolation, match="explicit user action"):
        session.autonomy = AutonomyLevel.EXTENDED_EDIT


def test_update_authority_requires_user_initiated_flag():
    session = Session(autonomy=AutonomyLevel.OBSERVE, patch_policy="disabled")
    with pytest.raises(PolicyViolation, match="explicit user action"):
        session.update_authority(autonomy=AutonomyLevel.PARAMS_ONLY)
