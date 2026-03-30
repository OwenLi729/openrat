"""
Example: Framework workflow with governance.

Demonstrates the full Openrat workflow:
1. Create a session with governance constraints
2. Define an experiment spec
3. Build a plan
4. Execute with policy enforcement
5. Inspect the audit trail

Usage:
    python examples/framework_workflow.py
"""

from openrat import (
    Openrat,
    Session,
    AutonomyLevel,
    ExperimentSpec,
    BaseTool,
    ToolRegistry,
)

# ── Session Setup ─────────────────────────────────────────────────────────────
# Define governance constraints for this run
session = Session(
    autonomy=AutonomyLevel.OBSERVE,  # Allow only observation (run, diagnose)
    patch_policy="disabled",          # Don't auto-apply patches
)

# ── Experiment Definition ─────────────────────────────────────────────────────
# Define your experiment intent
spec = ExperimentSpec(
    goals=["Train model", "Evaluate on test set"],
    metrics=["accuracy", "loss"],
    tasks=[
        {
            "id": "train",
            "name": "Training task",
            "tool": "executor",
            "payload": {
                "command": ["python", "train.py"],
                "timeout": 300,
            },
        },
        {
            "id": "evaluate",
            "name": "Evaluation task",
            "tool": "executor",
            "payload": {
                "command": ["python", "evaluate.py"],
                "timeout": 60,
            },
            "depends_on": ["train"],
        },
    ],
)

# ── Framework Setup ───────────────────────────────────────────────────────────
app = Openrat({
    "executor": "docker",
    "docker_image": "python:3.11",
})

# ── Build the Plan ────────────────────────────────────────────────────────────
# The plan represents how to execute the spec under governance
plan = app.build_plan(spec, session)

print(f"Plan built with {len(plan.dag.tasks)} tasks")
print(f"Session autonomy: {session.autonomy}")
print()

# ── Execute the Plan ──────────────────────────────────────────────────────────
# Create a basic tool registry (in a real setup, you'd register actual tools)
tools = {}

try:
    artifact = app.execute_plan(plan, session, tools=tools)
    
    # ── Results & Audit Trail ──────────────────────────────────────────────────
    print("Execution complete")
    print(f"Status: {artifact.status}")
    print()
    
    # Inspect governance report
    gov_report = artifact.governance_report()
    print("Governance Report:")
    print(f"  Session ID: {gov_report['session_id']}")
    print(f"  Autonomy: {gov_report['autonomy']} (0 = observe only)")
    print(f"  Used capabilities: {gov_report['used_capabilities']}")
    print(f"  Blocked capabilities: {gov_report['blocked_capabilities']}")
    print(f"  Patches proposed: {len(gov_report['patches_proposed'])}")
    print(f"  Patches applied: {len(gov_report['patches_applied'])}")
    print(f"  Governance events: {len(gov_report['events'])}")
    
except Exception as e:
    print(f"Execution failed: {e}")
    print()
    print("Governance audit trail before failure:")
    gov_report = session.governance_report()
    for event in gov_report["events"]:
        print(f"  - {event['action']}: {event['outcome']} ({event['reason']})")
