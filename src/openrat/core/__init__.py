from importlib import import_module

"""Core framework types (Session, Artifact, ExperimentSpec, AutonomyLevel).

These types represent:
  - Artifact: Immutable execution results (value type)
  - ExperimentSpec: Declarative experiment intent (immutable specification)
  - Session: Execution authority and approval state (mutable during execution)
  - AutonomyLevel: Governance levels for capability authorization

All are accessible via the main openrat package.
"""

__all__ = ["Artifact", "ExperimentSpec", "Session", "AutonomyLevel"]

_EXPORTS = {
	"Artifact": ("openrat.core.artifact", "Artifact"),
	"ExperimentSpec": ("openrat.core.experiment_spec", "ExperimentSpec"),
	"Session": ("openrat.core.session.session", "Session"),
	"AutonomyLevel": ("openrat.core.governance.autonomy", "AutonomyLevel"),
}


def __getattr__(name):
	if name not in _EXPORTS:
		raise AttributeError(name)
	module_name, symbol = _EXPORTS[name]
	module = import_module(module_name)
	value = getattr(module, symbol)
	globals()[name] = value
	return value