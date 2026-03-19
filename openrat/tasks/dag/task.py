from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any


class TaskState(str, Enum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class TaskExecution:
    task_id: str
    state: TaskState = TaskState.PENDING
    attempts: int = 0
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error: Optional[str] = None
    outputs: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Task:
    id: str
    tool_name: str
    input: Any
    retries: int = 0
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, Callable, Iterable

class TaskState(str, Enum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class TaskExecution:
    task_id: str
    state: TaskState = TaskState.PENDING
    attempts: int = 0
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error: Optional[str] = None
    outputs: Dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class Task:
    id: str
    tool_name: str
    input: Any
    retries: int = 0