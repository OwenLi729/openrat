from collections.abc import Mapping
from typing import Any


class BaseExecutor:
    """Executor interface used by the router.

    Executors should perform minimal work synchronously and return a serializable
    status mapping. Long-running or real execution should be handled by a worker/daemon.
    """

    def execute(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        raise NotImplementedError()
