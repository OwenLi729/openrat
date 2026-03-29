"""Governance primitives for autonomy and capability authorization.

Framework internal. Exported elements are AutonomyLevel (accessible via core package).
"""

from openrat.core.governance.autonomy import (
	AutonomyLevel,
	CAPABILITY_CODE_EDIT,
	CAPABILITY_OBSERVE,
	CAPABILITY_PARAMS_MODIFY,
	CAPABILITY_RUNTIME_FIX,
)
from openrat.core.governance.patch import PatchManager, PatchOperation, PatchPolicy

__all__ = [
	"AutonomyLevel",
	"CAPABILITY_OBSERVE",
	"CAPABILITY_PARAMS_MODIFY",
	"CAPABILITY_RUNTIME_FIX",
	"CAPABILITY_CODE_EDIT",
	"PatchManager",
	"PatchOperation",
	"PatchPolicy",
]
