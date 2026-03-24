from dataclasses import dataclass, field
from uuid import UUID, uuid4

from openrat.core.governance.autonomy import AutonomyLevel
from openrat.errors import PolicyViolation, UserInputError


@dataclass
class Session:
    """Execution authority and approval state for a run session."""

    autonomy: AutonomyLevel
    patch_policy: str  # "disabled" | "interactive" | "auto"
    user_approvals: set[str] = field(default_factory=set)
    used_capabilities: set[str] = field(default_factory=set)
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if self.patch_policy not in {"disabled", "interactive", "auto"}:
            raise UserInputError("patch_policy must be one of: disabled, interactive, auto")

    def authorize(self, capability: str, dry_run: bool = False) -> bool:
        """Return True if capability is allowed; dry-run does not mutate state."""

        if not self._allowed_by_autonomy(capability):
            if dry_run:
                return False
            raise PolicyViolation(f"Capability '{capability}' exceeds autonomy")

        if capability in self.user_approvals:
            if not dry_run:
                self.used_capabilities.add(capability)
            return True

        if self.patch_policy == "auto":
            if not dry_run:
                self.used_capabilities.add(capability)
            return True

        if dry_run:
            return False

        raise PolicyViolation(f"Capability '{capability}' requires explicit approval")

    def _allowed_by_autonomy(self, capability: str) -> bool:
        """Map declared capability to required autonomy level."""
        required = {
            "observe": AutonomyLevel.OBSERVE,
            "params.modify": AutonomyLevel.PARAMS_ONLY,
            "runtime.fix": AutonomyLevel.RUNTIME_REPAIR,
            "code.edit": AutonomyLevel.EXTENDED_EDIT,
        }

        level = required.get(capability)
        if level is None:
            return False

        return self.autonomy >= level

    def approve(self, capability: str) -> None:
        """Record explicit user approval for a capability."""
        self.user_approvals.add(capability)