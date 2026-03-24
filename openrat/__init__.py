from importlib import import_module

"""OpenRat: Experiment execution framework with planning & autonomy.

Primary Public API:
  Openrat: Framework workflow (session → spec → plan → artifact)

Data Types & Governance:
  ExperimentSpec: Experiment intent definition
  Session, AutonomyLevel: Execution authority & governance
  Artifact: Execution results

Extension Points:
  BaseTool: Tool implementation framework
  ToolRegistry: Named tool registry

For workflow documentation, see docs/AGENTS.md.
For executor configuration, see docs/EXECUTOR_POLICY.md.
"""

__all__ = [
	"Openrat",
	"BaseTool",
	"Artifact",
	"ExperimentSpec",
	"Session",
]


_EXPORTS = {
	"Openrat": ("openrat.api.openrat", "Openrat"),
	"BaseTool": ("openrat.tools.base", "BaseTool"),
	"Artifact": ("openrat.core.artifact", "Artifact"),
	"ExperimentSpec": ("openrat.core.experiment_spec", "ExperimentSpec"),
	"Session": ("openrat.core.session.session", "Session"),
}


def __getattr__(name):
	if name not in _EXPORTS:
		raise AttributeError(name)

	module_name, symbol = _EXPORTS[name]
	module = import_module(module_name)
	value = getattr(module, symbol)
	globals()[name] = value
	return value

