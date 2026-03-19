from importlib import import_module

__all__ = ["Openrat", "OpenRatAgent", "run"]

_EXPORTS = {
	"Openrat": ("openrat.api.openrat", "Openrat"),
	"OpenRatAgent": ("openrat.api.runner", "OpenRatAgent"),
	"run": ("openrat.api.runner", "run"),
}


def __getattr__(name):
	if name not in _EXPORTS:
		raise AttributeError(name)
	module_name, symbol = _EXPORTS[name]
	module = import_module(module_name)
	value = getattr(module, symbol)
	globals()[name] = value
	return value
