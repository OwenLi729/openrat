"""
End-to-end integration test: CLI/API → Session → Spec → Plan → DAG → Tool → DockerExecutor → Artifact

This test exercises the *full* framework stack end-to-end:

    Openrat.create_session()
        └─ build_plan()               ← Spec → Plan (incl. approval checks)
               └─ execute_plan()       ← DAG execution under Session governance
                       └─ BaseTool     ← domain tool with capability enforcement
                               └─ DockerExecutor.execute()  ← real subprocess.run
                                       └─ Artifact           ← immutable result + diagnostics

Tests that require Docker are guarded with ``pytest.mark.skipif`` so they can
be skipped safely in environments where Docker is unavailable (e.g. lightweight
CI). The subprocess-stubbed variants run in all environments and still exercise
every layer except the actual container spawning.
"""
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any
from collections.abc import Mapping

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from openrat import Openrat, BaseTool
from openrat.core.governance.autonomy import AutonomyLevel
from openrat.core.artifact import Artifact
from openrat.core.errors import PolicyViolation
from openrat.executors.docker_executor import DockerExecutor
from openrat.tasks.dag.task import TaskState

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

DOCKER_AVAILABLE = shutil.which("docker") is not None
# A working Docker binary is not enough — the daemon must also be reachable.
if DOCKER_AVAILABLE:
    try:
        _check = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=5,
        )
        DOCKER_AVAILABLE = _check.returncode == 0
    except Exception:
        DOCKER_AVAILABLE = False


class _ObserveTool(BaseTool):
    """Minimal observe-capability tool that records its invocation."""

    capability = "observe"

    def __init__(self):
        super().__init__(governance=None)
        self.invocations: list[Mapping[str, Any]] = []

    def run(self, payload: Mapping[str, Any], session: Any) -> dict:
        self.invocations.append(dict(payload))
        return {"observed": payload.get("name", "unknown")}


class _DockerObserveTool(BaseTool):
    """Observe tool that delegates to DockerExecutor under the hood."""

    capability = "observe"

    def __init__(self, executor: DockerExecutor):
        super().__init__(governance=None)
        self._executor = executor
        self.invocations: list[dict] = []

    def run(self, payload: Mapping[str, Any], session: Any) -> dict:
        self.invocations.append(dict(payload))
        name = payload.get("name", "")
        result = self._executor.execute(
            payload={
                "command": ["python", "-c", f"print('observed:{name}')"],
                "limits": {},
            },
        )
        return {
            "observed": payload.get("name", "unknown"),
            "executor_result": result,
        }


# ---------------------------------------------------------------------------
# Layer 1 — DockerExecutor unit smoke-test (subprocess stubbed)
# ---------------------------------------------------------------------------

class TestDockerExecutorStubbed:
    """DockerExecutor behaviour verified with a subprocess.run stub."""

    def test_executes_command_and_returns_completed(self, monkeypatch):
        completed = subprocess.CompletedProcess(
            args=["docker"], returncode=0, stdout="hello\n", stderr=""
        )
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: completed)

        executor = DockerExecutor(image="python:3.11")
        result = executor.execute(
            payload={
                "command": ["python", "-c", "print('hello')"],
                "limits": {},
            },
        )

        assert result["status"] == "completed"
        assert result["executor"] == "docker"
        assert result["return_code"] == 0
        assert "hello" in result["stdout"]
        assert result["timed_out"] is False

    def test_non_zero_exit_code_returns_failed(self, monkeypatch):
        completed = subprocess.CompletedProcess(
            args=["docker"], returncode=1, stdout="", stderr="error"
        )
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: completed)

        executor = DockerExecutor(image="python:3.11")
        result = executor.execute(
            payload={
                "command": ["python", "-c", "import sys; sys.exit(1)"],
                "limits": {},
            },
        )

        assert result["status"] == "failed"
        assert result["return_code"] == 1
        assert "error" in result["stderr"]

    def test_resource_limits_passed_to_docker_command(self, monkeypatch):
        captured: list[list[str]] = []

        def fake_run(cmd, *a, **kw):
            captured.append(list(cmd))
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

        monkeypatch.setattr("subprocess.run", fake_run)

        executor = DockerExecutor(image="python:3.11")
        executor.execute(
            payload={
                "command": ["python", "--version"],
                "limits": {"memory": "256m", "cpus": "0.5"},
            },
        )

        assert captured, "subprocess.run was never called"
        cmd = captured[0]
        assert "--memory" in cmd
        assert "256m" in cmd
        assert "--cpus" in cmd
        assert "0.5" in cmd
        assert "--network" in cmd
        assert "none" in cmd


# ---------------------------------------------------------------------------
# Layer 2 — Full framework stack (stubbed DockerExecutor subprocess)
# ---------------------------------------------------------------------------

class TestFullStackStubbed:
    """Full CLI/API → Session → Spec → Plan → DAG → Tool → DockerExecutor → Artifact
    with subprocess.run stubbed so no Docker daemon is needed."""

    def _make_completed(self, stdout: str = "ok\n"):
        return subprocess.CompletedProcess(
            args=["docker"], returncode=0,
            stdout=stdout,   # text=True path: str
            stderr="",
        )

    def test_single_task_flow_produces_artifact(self, monkeypatch):
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: self._make_completed())

        app = Openrat({"executor": "docker", "docker_image": "python:3.11"})
        session = app.create_session(
            autonomy=AutonomyLevel.OBSERVE,
            patch_policy="interactive",
            user_approvals={"observe"},
        )
        spec = app.spec_from_final_json({
            "goals": ["collect metrics"],
            "metrics": {"count": {"target": 1}},
            "tasks": {
                "t1": {"tool": "observe", "input": {"name": "alpha"}, "capability": "observe"},
            },
            "dependencies": {},
            "constraints": {"patch_policy": "interactive"},
        })

        plan = app.build_plan(spec, session)
        assert plan.requires_approval is False

        observe_tool = _ObserveTool()
        artifact = app.execute_plan(plan, session, tools={"observe": observe_tool})

        # DAG completed
        assert plan.dag.state["t1"].state == TaskState.SUCCESS
        # Tool was invoked
        assert len(observe_tool.invocations) == 1
        assert observe_tool.invocations[0]["name"] == "alpha"
        # Artifact is well-formed
        assert isinstance(artifact, Artifact)
        summary = artifact.summarize()
        assert summary["status"] == "success"
        assert artifact.to_dict()["observations"]["t1"]["observed"] == "alpha"
        # Governance diagnostics present in artifact
        diag = artifact.to_dict()["diagnostics"]
        assert "governance" in diag
        gov = diag["governance"]
        assert "autonomy" in gov
        assert gov["autonomy"] == int(AutonomyLevel.OBSERVE)

    def test_two_task_sequential_dependency(self, monkeypatch):
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: self._make_completed())

        app = Openrat({"executor": "docker", "docker_image": "python:3.11"})
        session = app.create_session(
            autonomy=AutonomyLevel.OBSERVE,
            patch_policy="interactive",
            user_approvals={"observe"},
        )
        spec = app.spec_from_final_json({
            "goals": ["observe two things in order"],
            "metrics": {"count": {"target": 2}},
            "tasks": {
                "t1": {"tool": "observe", "input": {"name": "first"}, "capability": "observe"},
                "t2": {"tool": "observe", "input": {"name": "second"}, "capability": "observe"},
            },
            "dependencies": {"t2": ["t1"]},
            "constraints": {"patch_policy": "interactive"},
        })

        plan = app.build_plan(spec, session)
        observe_tool = _ObserveTool()
        artifact = app.execute_plan(plan, session, tools={"observe": observe_tool})

        assert plan.dag.state["t1"].state == TaskState.SUCCESS
        assert plan.dag.state["t2"].state == TaskState.SUCCESS
        assert len(observe_tool.invocations) == 2
        names = [inv["name"] for inv in observe_tool.invocations]
        # t1 must be invoked before t2 (dependency ordering)
        assert names.index("first") < names.index("second")

        obs = artifact.to_dict()["observations"]
        assert obs["t1"]["observed"] == "first"
        assert obs["t2"]["observed"] == "second"

    def test_governance_policy_violation_blocks_execution(self, monkeypatch):
        """A task requiring 'params.modify' capability should be blocked when the
        session only authorises 'observe' and the plan requires approval."""
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: self._make_completed())

        app = Openrat({"executor": "docker", "docker_image": "python:3.11"})
        session = app.create_session(
            autonomy=AutonomyLevel.OBSERVE,
            patch_policy="interactive",
            user_approvals={"observe"},      # NOTE: NO "params.modify" approval
        )
        spec = app.spec_from_final_json({
            "goals": ["test policy enforcement"],
            "metrics": {"count": {"target": 1}},
            "tasks": {
                "t1": {"tool": "observe", "input": {"name": "ok"}, "capability": "observe"},
                "t2": {"tool": "modify",  "input": {"name": "bad"}, "capability": "params.modify"},
            },
            "dependencies": {"t2": ["t1"]},
            "constraints": {"patch_policy": "interactive"},
        })

        plan = app.build_plan(spec, session)
        assert plan.requires_approval is True

        class _ModifyTool(BaseTool):
            capability = "params.modify"
            def run(self, payload, session):
                return {"modified": payload.get("name")}

        with pytest.raises(PolicyViolation, match="requires approval"):
            app.execute_plan(
                plan,
                session,
                tools={"observe": _ObserveTool(), "modify": _ModifyTool()},
            )

    def test_artifact_logs_are_immutable_tuple(self, monkeypatch):
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: self._make_completed())

        app = Openrat({"executor": "docker", "docker_image": "python:3.11"})
        session = app.create_session(
            autonomy=AutonomyLevel.OBSERVE,
            patch_policy="interactive",
            user_approvals={"observe"},
        )
        spec = app.spec_from_final_json({
            "goals": ["check artifact immutability"],
            "metrics": {"count": {"target": 1}},
            "tasks": {
                "t1": {"tool": "observe", "input": {"name": "check"}, "capability": "observe"},
            },
            "dependencies": {},
            "constraints": {"patch_policy": "interactive"},
        })

        plan = app.build_plan(spec, session)
        artifact = app.execute_plan(plan, session, tools={"observe": _ObserveTool()})

        assert isinstance(artifact.logs, tuple), "logs must be an immutable tuple"
        assert isinstance(artifact.patches_applied, tuple), "patches_applied must be an immutable tuple"
        assert isinstance(artifact.id.hex, str), "artifact.id must be a UUID"

    def test_docker_executor_is_used_for_direct_run(self, monkeypatch):
        """app.run() (direct, non-planned) should route through DockerExecutor."""
        stdout_text = "hello from docker\n"
        completed = subprocess.CompletedProcess(
            args=["docker"], returncode=0,
            stdout=stdout_text, stderr="",  # text=True returns str
        )
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: completed)

        # Use a fixture script that actually exists in the repo
        fixtures_dir = Path(__file__).resolve().parents[1] / "units" / "sandbox" / "fixtures"
        hello_script = str(fixtures_dir / "hello.py")

        app = Openrat({"executor": "docker", "docker_image": "python:3.11"})
        result = app.run(hello_script, timeout=30, isolate=True)

        assert result["status"] == "completed"
        assert result["executor"] == "docker"
        assert result["return_code"] == 0
        assert "hello" in result["stdout"]


# ---------------------------------------------------------------------------
# Layer 3 — Real Docker execution (skipped if Docker unavailable)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not DOCKER_AVAILABLE, reason="Docker daemon not available")
class TestRealDockerExecution:
    """These tests spawn real Docker containers.

    They are skipped in environments where ``docker`` is not on PATH.
    Run them locally or in a Docker-in-Docker CI environment.
    """

    def test_docker_executor_runs_python_script(self):
        executor = DockerExecutor(image="python:3.11")
        result = executor.execute(
            payload={
                "command": ["python", "-c", "print('e2e ok')"],
                "limits": {"memory": "128m", "cpus": "0.5"},
            },
        )

        assert result["status"] == "completed"
        assert result["executor"] == "docker"
        assert result["return_code"] == 0
        assert "e2e ok" in result["stdout"]
        assert result["timed_out"] is False
        assert result["duration"] >= 0

    def test_docker_executor_captures_stderr(self):
        executor = DockerExecutor(image="python:3.11")
        result = executor.execute(
            payload={
                "command": ["python", "-c", "import sys; sys.stderr.write('err msg\\n')"],
                "limits": {},
            },
        )

        assert result["status"] == "completed"
        assert "err msg" in result["stderr"]

    def test_docker_executor_non_zero_exit(self):
        executor = DockerExecutor(image="python:3.11")
        result = executor.execute(
            payload={
                "command": ["python", "-c", "import sys; sys.exit(42)"],
                "limits": {},
            },
        )

        assert result["status"] == "failed"
        assert result["return_code"] == 42

    def test_full_stack_with_real_docker(self):
        """Full Session → Spec → Plan → DAG → _DockerObserveTool → DockerExecutor → Artifact."""
        executor = DockerExecutor(image="python:3.11")

        app = Openrat({"executor": "docker", "docker_image": "python:3.11"})
        session = app.create_session(
            autonomy=AutonomyLevel.OBSERVE,
            patch_policy="interactive",
            user_approvals={"observe"},
        )
        spec = app.spec_from_final_json({
            "goals": ["run real docker observation"],
            "metrics": {"count": {"target": 1}},
            "tasks": {
                "t1": {
                    "tool": "docker_observe",
                    "input": {"name": "real_run"},
                    "capability": "observe",
                },
            },
            "dependencies": {},
            "constraints": {"patch_policy": "interactive"},
        })

        plan = app.build_plan(spec, session)
        assert plan.requires_approval is False

        docker_tool = _DockerObserveTool(executor)
        artifact = app.execute_plan(
            plan, session, tools={"docker_observe": docker_tool}
        )

        assert plan.dag.state["t1"].state == TaskState.SUCCESS
        assert len(docker_tool.invocations) == 1

        obs = artifact.to_dict()["observations"]["t1"]
        assert obs["observed"] == "real_run"
        exec_result = obs["executor_result"]
        assert exec_result["status"] == "completed"
        assert exec_result["executor"] == "docker"
        assert "observed:real_run" in exec_result["stdout"]

        diag = artifact.to_dict()["diagnostics"]
        assert "governance" in diag
        assert diag["governance"]["autonomy"] == int(AutonomyLevel.OBSERVE)
