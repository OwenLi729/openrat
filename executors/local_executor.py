try:
    from openrat.sandbox.exec import run_command
except Exception:
    run_command = None

# Keep symbol available for monkeypatching in tests
