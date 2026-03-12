"""Tool registry for openrat.tools."""

class ToolRegistry:
    def __init__(self):
        self._tools = {}

    def register(self, name: str, tool):
        """Register a callable tool under `name`."""
        self._tools[name] = tool

    def get(self, name: str):
        return self._tools.get(name)

    def list(self):
        return list(self._tools.keys())

    def execute(self, name: str, arguments: dict):
        """Look up tool by name and call it with arguments dict."""
        tool = self._tools.get(name)
        if tool is None:
            raise KeyError(f"tool '{name}' not found in registry")
        return tool(arguments)
