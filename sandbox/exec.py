import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List

@dataclass
class ExecutionResult:
    command: List[str]
    cwd: Path
    return_code: int
    stdout: str
    stderr: str
    start_time: float
    end_time: float
    timed_out: bool

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time

    @property
    def succeeded(self) -> bool:
        return self.return_code == 0 and not self.timed_out

def run_command(
    command: List[str],
    cwd: Optional[Path] = None,
    timeout: Optional[int] = None,
) -> ExecutionResult:
    """
    Execute a command in a subprocess with log capture and timeout support.

    Args:
        command: e.g. ["python", "experiment.py"]
        cwd: working directory for execution
        timeout: max seconds before killing process

    Returns:
        ExecutionResult
    """

    if cwd is None:
        cwd = Path.cwd()

    start_time = time.time()
    timed_out = False

    try:
        completed = subprocess.run(
            command,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        return_code = completed.returncode
        stdout = completed.stdout
        stderr = completed.stderr

    except subprocess.TimeoutExpired as e:
        timed_out = True
        return_code = -1
        stdout = e.stdout or ""
        stderr = (e.stderr or "") + "\nProcess timed out."

    end_time = time.time()

    return ExecutionResult(
        command=command,
        cwd=cwd,
        return_code=return_code,
        stdout=stdout,
        stderr=stderr,
        start_time=start_time,
        end_time=end_time,
        timed_out=timed_out,
    )


