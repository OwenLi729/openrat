from importlib import import_module

"""OpenRat API entry points.

Public API:
  - Openrat: Primary framework facade

Internal runtime (not for external use):
  - OpenRatAgent: Low-level runtime adapter
  - run(): Direct execution helper
"""

__all__ = ["Openrat"]

_EXPORTS = {
	"Openrat": ("openrat.api.openrat", "Openrat"),
}


def __getattr__(name):
	if name not in _EXPORTS:
		raise AttributeError(name)
	module_name, symbol = _EXPORTS[name]
	module = import_module(module_name)
	value = getattr(module, symbol)
	globals()[name] = value
	return value
