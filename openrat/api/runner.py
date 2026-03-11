from pathlib import Path
from typing import Optional, Dict, Any
import shutil
import tempfile

from openrat.executors import LocalExecutor, ProductionDockerExecutor


def _validate_experiment_path(path: str) -> Path:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Experiment file not found: {path}")
    p = p.resolve()
    cwd = Path.cwd().resolve()
    try:
        p.relative_to(cwd)
    except Exception:
        # restrict running experiments outside current working directory
        raise PermissionError("Experiment path must live inside the current working directory")
    return p


def _choose_executor(preferred: Optional[str], docker_image: str):
    # prefer docker when available unless explicitly asked for local
    if preferred == "local":
        return LocalExecutor()

    if preferred == "docker":
        return ProductionDockerExecutor(image=docker_image)

    import shutil as _sh

    if _sh.which("docker"):
        return ProductionDockerExecutor(image=docker_image)

    return LocalExecutor()


def run(path: str, *, executor: Optional[str] = None, timeout: Optional[int] = None, docker_image: str = "python:3.11", isolate: bool = True, memory: str = "512m", cpus: str = "1.0") -> Dict[str, Any]:
    """Run an experiment file using the chosen executor.

    By default this will copy the experiment into a per-run ephemeral directory
    and execute inside that directory to limit filesystem access. The runner will
    create separate `code/` (read-only) and `outputs/` (writable) mounts for Docker.
    """
    p = _validate_experiment_path(path)
    exec_obj = _choose_executor(executor, docker_image)

    if isolate:
        with tempfile.TemporaryDirectory(prefix="openrat-run-") as td:
            td_path = Path(td)
            code_dir = td_path / "code"
            outputs_dir = td_path / "outputs"
            code_dir.mkdir()
            outputs_dir.mkdir()
            # copy experiment into code subdir
            dest = code_dir / p.name
            shutil.copy2(p, dest)

            payload = {
                # run using container-local paths
                "command": ["python", f"/code/{dest.name}"],
                "cwd": str(outputs_dir),
                "timeout": timeout,
                "code_dir": str(code_dir),
                "outputs_dir": str(outputs_dir),
                "limits": {"memory": memory, "cpus": cpus},
            }
            result = exec_obj.execute(payload)
            return result

    payload = {
        "command": ["python", str(p)],
        "cwd": str(p.parent),
        "timeout": timeout,
    }

    result = exec_obj.execute(payload)
    return result


class OpenRatAgent:
    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        self.executor = self.config.get("executor")
        self.docker_image = self.config.get("docker_image", "python:3.11")

    def run(self, path: str, timeout: Optional[int] = None, isolate: bool = True, memory: str = "512m", cpus: str = "1.0"):
        return run(path, executor=self.executor, timeout=timeout, docker_image=self.docker_image, isolate=isolate, memory=memory, cpus=cpus)
