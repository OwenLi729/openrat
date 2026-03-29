from dataclasses import dataclass, field
from enum import Enum


class PatchPolicy(str, Enum):
	DISABLED = "disabled"
	INTERACTIVE = "interactive"
	AUTO = "auto"


class PatchOperation(str, Enum):
	PROPOSE = "propose"
	APPLY = "apply"


@dataclass
class PatchManager:
	"""Constrains patch operations by declared scope.

	Scope values are free-form labels provided by caller/tooling.
	"""

	declared_scope: set[str] = field(default_factory=set)

	def allows_scope(self, scope: str | None) -> bool:
		if not self.declared_scope:
			return True
		if scope is None:
			return False
		return scope in self.declared_scope

	def declare_scope(self, *scope: str) -> None:
		for item in scope:
			normalized = str(item).strip()
			if normalized:
				self.declared_scope.add(normalized)
