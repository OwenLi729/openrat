from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseExecutor(ABC):
    """Abstract executor interface used by the router.

    Executors should perform minimal work synchronously and return a serializable
    status dict. Long-running or real execution should be handled by a worker/daemon.
    """

    @abstractmethod
    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError()
