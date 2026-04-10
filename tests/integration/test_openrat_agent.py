"""
Integration tests for OpenRatAgent — chat(), run(), built-in tool, custom tools,
validate_experiment_path, and loop wiring.
"""
import sys
import os
import tempfile
from pathlib import Path
import pytest
import subprocess

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from openrat.api.runner import OpenRatAgent, validate_experiment_path
from openrat.core.errors import UserInputError, EnvironmentError, LocalExecutionBypassesSandboxError
from openrat.model.types import Message, ModelResponse, ToolCall
from openrat.core.artifact import Artifact


# ── Helpers ───────────────────────────────────────────────────────────────────

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "units" / "sandbox" / "fixtures"


class _FakeAdapterFinal:
    """Immediately returns a final response with no tool calls."""
    def __init__(self, content="stub response"):
        self._content = content
        self.calls = []

    def generate(self, messages):
        self.calls.append([m.content for m in messages])
        return ModelResponse(content=self._content, tool_calls=[])


class _FakeAdapterRunsTool:
    """First turn: requests run_experiment; second turn: final answer."""
    def __init__(self, experiment_path):
        self._path = experiment_path
        self.call_count = 0

    def generate(self, messages):
        self.call_count += 1
        if self.call_count == 1:
            return ModelResponse(
                content=None,
                tool_calls=[
                    ToolCall(
                        id="tc1",
                        name="run_experiment",
                        arguments={"path": self._path},
                    )
                ],
            )
        return ModelResponse(content="experiment complete", tool_calls=[])


# ── chat() — basic ─────────────────────────────────────────────────────────────

def test_chat_without_provider_raises():
    agent = OpenRatAgent({"executor": "docker"})
    with pytest.raises(UserInputError, match="No model configured"):
        agent.chat("hello")


def test_chat_with_string_message(monkeypatch):
    adapter = _FakeAdapterFinal("ok")
    agent = OpenRatAgent({"provider": "openai_compatible", "api_key": None, "model_name": "x"})
    agent.agent_loop.adapter = adapter
    resp = agent.chat("ping")
    assert resp.content == "ok"
    assert len(adapter.calls) == 1
    assert adapter.calls[0][0] == "ping"


def test_chat_with_message_list(monkeypatch):
    adapter = _FakeAdapterFinal("reply")
    agent = OpenRatAgent({"provider": "openai_compatible", "api_key": None, "model_name": "x"})
    agent.agent_loop.adapter = adapter
    msgs = [
        Message(role="system", content="you are helpful"),
        Message(role="user",   content="do something"),
    ]
    resp = agent.chat(msgs)
    assert resp.content == "reply"


def test_chat_preserves_message_order(monkeypatch):
    """Messages passed to the adapter should be in the original order."""
    adapter = _FakeAdapterFinal()
    agent = OpenRatAgent({"provider": "openai_compatible", "api_key": None, "model_name": "x"})
    agent.agent_loop.adapter = adapter
    msgs = [
        Message(role="system", content="sys"),
        Message(role="user",   content="usr"),
    ]
    agent.chat(msgs)
    assert adapter.calls[0] == ["sys", "usr"]


# ── agent_loop wiring ──────────────────────────────────────────────────────────

def test_agent_loop_is_none_without_provider():
    agent = OpenRatAgent({"executor": "docker"})
    assert agent.agent_loop is None


def test_agent_loop_built_with_provider():
    agent = OpenRatAgent({"provider": "claude", "api_key": None, "model_name": "x"})
    assert agent.agent_loop is not None
    assert agent.tool_registry is not None


# ── built-in run_experiment tool ───────────────────────────────────────────────

def test_run_experiment_tool_is_registered():
    agent = OpenRatAgent({"provider": "openai_compatible", "api_key": None, "model_name": "x"})
    assert "run_experiment" in agent.tool_registry.list()


def test_run_experiment_tool_returns_error_without_path():
    agent = OpenRatAgent({"provider": "openai_compatible", "api_key": None, "model_name": "x"})
    result = agent.tool_registry.execute("run_experiment", {})
    assert result["status"] == "error"
    assert "path" in result["reason"]


def test_run_experiment_tool_actually_runs_script(monkeypatch):
    """run_experiment tool calls agent.run() which calls the docker executor."""
    completed = subprocess.CompletedProcess(args=["docker"], returncode=0, stdout="hello world", stderr="")
    monkeypatch.setattr("subprocess.run", lambda *a, **kw: completed)

    agent = OpenRatAgent({"provider": "openai_compatible", "api_key": None, "model_name": "x", "executor": "docker"})
    result = agent.tool_registry.execute(
        "run_experiment",
        {"path": str(FIXTURES_DIR / "hello.py")},
    )
    assert result["status"] == "completed"
    assert result["return_code"] == 0
    assert result["executor"] == "docker"


# ── custom tool registration ───────────────────────────────────────────────────

def test_custom_tool_registered_and_callable():
    agent = OpenRatAgent(
        {
            "provider": "openai_compatible",
            "api_key": None,
            "model_name": "x",
            "autonomy": 3,
            "user_approvals": {"host.exec"},
        }
    )

    def greet(args):
        return {"greeting": f"hello {args['name']}"}

    agent.tool_registry.register("greet", greet, capability="host.exec")
    result = agent.tool_registry.execute("greet", {"name": "openrat"})
    assert result == {"greeting": "hello openrat"}


def test_chat_loop_invokes_custom_tool(monkeypatch):
    """Full loop: adapter requests custom tool → tool executes → adapter finishes."""
    calls = []

    def my_tool(args):
        calls.append(args)
        return {"value": 99}

    class _AdapterCallsTool:
        def __init__(self):
            self.n = 0

        def generate(self, messages):
            self.n += 1
            if self.n == 1:
                return ModelResponse(
                    content=None,
                    tool_calls=[ToolCall(id="t1", name="my_tool", arguments={"x": 1})],
                )
            return ModelResponse(content="done", tool_calls=[])

    agent = OpenRatAgent(
        {
            "provider": "openai_compatible",
            "api_key": None,
            "model_name": "x",
            "autonomy": 3,
            "user_approvals": {"host.exec"},
        }
    )
    agent.tool_registry.register("my_tool", my_tool, capability="host.exec")
    agent.agent_loop.adapter = _AdapterCallsTool()

    resp = agent.chat("go")
    assert resp.content == "done"
    assert calls == [{"x": 1}]


# ── multi-turn loop drives run_experiment ──────────────────────────────────────

def test_chat_drives_run_experiment_tool(monkeypatch):
    completed = subprocess.CompletedProcess(args=["docker"], returncode=0, stdout="hello world\n", stderr="")
    monkeypatch.setattr("subprocess.run", lambda *a, **kw: completed)

    experiment_path = str(FIXTURES_DIR / "hello.py")
    adapter = _FakeAdapterRunsTool(experiment_path)

    agent = OpenRatAgent({
        "provider": "openai_compatible",
        "api_key": None,
        "model_name": "x",
        "executor": "docker",
    })
    agent.agent_loop.adapter = adapter

    resp = agent.chat("run the experiment", max_turns=5)
    assert resp.content == "experiment complete"
    assert adapter.call_count == 2


# ── validate_experiment_path ──────────────────────────────────────────────────

def test_validate_path_file_not_found():
    with pytest.raises(EnvironmentError):
        validate_experiment_path("/tmp/does_not_exist_openrat_test.py")


def test_validate_path_outside_cwd_raises():
    # /tmp is outside the current working directory
    with tempfile.NamedTemporaryFile(suffix=".py", dir="/tmp", delete=False) as f:
        fpath = f.name
    try:
        with pytest.raises(EnvironmentError, match="current working directory"):
            validate_experiment_path(fpath)
    finally:
        os.unlink(fpath)


def test_validate_path_inside_cwd_returns_resolved():
    # Use a real fixture file that lives inside the repo (cwd)
    p = validate_experiment_path(str(FIXTURES_DIR / "hello.py"))
    assert p.is_absolute()
    assert p.exists()


# ── OpenRatAgent.run() direct execution ────────────────────────────────────────

def test_direct_run_returns_completed(monkeypatch):
    completed = subprocess.CompletedProcess(args=["docker"], returncode=0, stdout="hello world\n", stderr="")
    monkeypatch.setattr("subprocess.run", lambda *a, **kw: completed)
    agent = OpenRatAgent({"executor": "docker"})
    result = agent.run(str(FIXTURES_DIR / "hello.py"), isolate=True)
    assert result["status"] == "completed"
    assert result["return_code"] == 0
    assert result["executor"] == "docker"


def test_direct_run_isolate_false_still_passes_resource_limits(monkeypatch):
    captured = {"cmd": None}

    def _fake_run(cmd, *a, **kw):
        captured["cmd"] = list(cmd)
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="ok\n", stderr="")

    monkeypatch.setattr("subprocess.run", _fake_run)

    agent = OpenRatAgent({"executor": "docker"})
    result = agent.run(str(FIXTURES_DIR / "hello.py"), isolate=False)

    assert result["status"] == "completed"
    assert captured["cmd"] is not None
    assert "--memory" in captured["cmd"]
    assert "512m" in captured["cmd"]
    assert "--cpus" in captured["cmd"]
    assert "1.0" in captured["cmd"]


def test_direct_run_local_requires_explicit_selection(monkeypatch):
    completed = subprocess.CompletedProcess(args=["python"], returncode=0, stdout="hello world\n", stderr="")
    monkeypatch.setattr("subprocess.run", lambda *a, **kw: completed)
    agent = OpenRatAgent({"executor": "local"})
    result = agent.run(str(FIXTURES_DIR / "hello.py"), isolate=True)
    assert result["status"] == "completed"
    assert result["executor"] == "local"
    assert result["security_error"] == LocalExecutionBypassesSandboxError.DEFAULT_MESSAGE


def test_direct_run_docker_missing_does_not_fallback_to_local(monkeypatch):
    monkeypatch.setattr("openrat.api.runner.shutil.which", lambda name: None)
    agent = OpenRatAgent({"executor": "docker"})
    with pytest.raises(EnvironmentError, match="docker is not available"):
        agent.run(str(FIXTURES_DIR / "hello.py"), isolate=True)


def test_runner_governance_metadata_records_executor(monkeypatch):
    completed = subprocess.CompletedProcess(args=["python"], returncode=0, stdout="hello world\n", stderr="")
    monkeypatch.setattr("subprocess.run", lambda *a, **kw: completed)
    agent = OpenRatAgent({"executor": "local"})
    agent.run(str(FIXTURES_DIR / "hello.py"), isolate=False)
    events = agent.session.governance_report()["events"]
    assert events[-1]["metadata"]["executor"] == "local"


def test_direct_artifact_records_executor(monkeypatch):
    completed = subprocess.CompletedProcess(args=["python"], returncode=0, stdout="hello world\n", stderr="")
    monkeypatch.setattr("subprocess.run", lambda *a, **kw: completed)

    agent = OpenRatAgent({"executor": "local"})
    result = agent.run(str(FIXTURES_DIR / "hello.py"), isolate=False)
    artifact = Artifact.from_execution_result(result=result, session=agent.session, path=str(FIXTURES_DIR / "hello.py"))

    assert artifact.metadata["executor"] == "local"
    assert artifact.diagnostics["execution_error"] == LocalExecutionBypassesSandboxError.DEFAULT_MESSAGE
