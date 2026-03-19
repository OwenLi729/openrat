from importlib import import_module

__all__ = ["Artifact", "ExperimentSpec", "Session", "AutonomyLevel"]

_EXPORTS = {
	"Artifact": ("openrat.core.artifact", "Artifact"),
	"ExperimentSpec": ("openrat.core.instructions", "ExperimentSpec"),
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