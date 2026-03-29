from dataclasses import dataclass, field
from datetime import datetime, timezone
from collections.abc import Mapping
from typing import Any
from uuid import UUID, uuid4

from openrat.core.governance.autonomy import AutonomyLevel, required_level_for
from openrat.core.governance.patch import PatchManager, PatchOperation, PatchPolicy
from openrat.core.errors import PolicyViolation, UserInputError


@dataclass
class Session:
    """Execution authority and approval state for a run session."""

    autonomy: AutonomyLevel
    patch_policy: str  # "disabled" | "interactive" | "auto"
    user_approvals: set[str] = field(default_factory=set)
    used_capabilities: set[str] = field(default_factory=set)
    blocked_capabilities: set[str] = field(default_factory=set)
    patch_manager: PatchManager = field(default_factory=PatchManager)
    patches_proposed: list[dict[str, Any]] = field(default_factory=list)
    patches_applied: list[dict[str, Any]] = field(default_factory=list)
    governance_events: list[dict[str, Any]] = field(default_factory=list)
    id: UUID = field(default_factory=uuid4)
    _locked_authority: bool = field(default=False, init=False, repr=False)

    def __setattr__(self, name: str, value: Any) -> None:
        if getattr(self, "_locked_authority", False) and name in {"autonomy", "patch_policy"}:
            current = getattr(self, name)
            if current != value:
                raise PolicyViolation("Authority changes require explicit user action")
        object.__setattr__(self, name, value)

    def __post_init__(self) -> None:
        try:
            PatchPolicy(self.patch_policy)
        except ValueError:
            raise UserInputError("patch_policy must be one of: disabled, interactive, auto")
        self._locked_authority = True

    @property
    def autonomy_level(self) -> int:
        return int(self.autonomy)

    def _log_event(
        self,
        *,
        action: str,
        capability: str | None,
        outcome: str,
        reason: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        self.governance_events.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action": action,
                "capability": capability,
                "outcome": outcome,
                "reason": reason,
                "metadata": dict(metadata or {}),
            }
        )

    def check_capability(self, capability: str) -> tuple[bool, str | None]:
        level = required_level_for(capability)
        if level is None:
            return False, f"Capability '{capability}' is unknown"

        if self.autonomy < level:
            return False, f"Capability '{capability}' exceeds autonomy"

        if self.user_approvals and capability not in self.user_approvals:
            return False, f"Capability '{capability}' is not explicitly approved"

        return True, None

    def authorize(
        self,
        capability: str,
        dry_run: bool = False,
        *,
        action: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> bool:
        """Return True if capability is allowed; dry-run does not mutate state."""
        allowed, reason = self.check_capability(capability)
        if dry_run:
            return allowed

        if not allowed:
            self.blocked_capabilities.add(capability)
            self._log_event(
                action=action or "capability.authorize",
                capability=capability,
                outcome="blocked",
                reason=reason,
                metadata=metadata,
            )
            raise PolicyViolation(reason or f"Capability '{capability}' is not authorized")

        self.used_capabilities.add(capability)
        self._log_event(
            action=action or "capability.authorize",
            capability=capability,
            outcome="allowed",
            metadata=metadata,
        )
        return True

    def authorize_patch_operation(
        self,
        operation: str,
        *,
        scope: str | None = None,
        dry_run: bool = False,
        metadata: Mapping[str, Any] | None = None,
    ) -> bool:
        try:
            op = PatchOperation(operation)
        except ValueError:
            if dry_run:
                return False
            self._log_event(
                action="patch.authorize",
                capability=None,
                outcome="blocked",
                reason=f"Unknown patch operation '{operation}'",
                metadata=metadata,
            )
            raise PolicyViolation(f"Unknown patch operation '{operation}'")

        if not self.patch_manager.allows_scope(scope):
            reason = "Patch operation exceeds declared patch scope"
            if dry_run:
                return False
            self._log_event(
                action="patch.authorize",
                capability=None,
                outcome="blocked",
                reason=reason,
                metadata={**dict(metadata or {}), "scope": scope, "operation": op.value},
            )
            raise PolicyViolation(reason)

        policy = PatchPolicy(self.patch_policy)
        if policy != PatchPolicy.DISABLED and op == PatchOperation.APPLY:
            reason = "Patch policy is enabled; patches may only be proposed"
            if dry_run:
                return False
            self._log_event(
                action="patch.authorize",
                capability=None,
                outcome="blocked",
                reason=reason,
                metadata={**dict(metadata or {}), "scope": scope, "operation": op.value},
            )
            raise PolicyViolation(reason)

        if dry_run:
            return True

        self._log_event(
            action="patch.authorize",
            capability=None,
            outcome="allowed",
            metadata={**dict(metadata or {}), "scope": scope, "operation": op.value},
        )
        return True

    def record_patch(
        self,
        *,
        patch_id: str,
        operation: str,
        scope: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        self.authorize_patch_operation(operation, scope=scope, metadata=metadata)

        entry = {
            "patch_id": patch_id,
            "operation": operation,
            "scope": scope,
            "metadata": dict(metadata or {}),
        }

        if operation == PatchOperation.PROPOSE.value:
            self.patches_proposed.append(entry)
            self._log_event(
                action="patch.proposed",
                capability=None,
                outcome="allowed",
                metadata=entry,
            )
            return

        self.patches_applied.append(entry)
        self._log_event(
            action="patch.applied",
            capability=None,
            outcome="allowed",
            metadata=entry,
        )

    def approve(self, capability: str) -> None:
        """Record explicit user approval for a capability."""
        if not self.authorize(capability, dry_run=True):
            raise PolicyViolation(f"Cannot approve capability '{capability}' beyond current autonomy")
        self.user_approvals.add(capability)

    def update_authority(
        self,
        *,
        autonomy: AutonomyLevel | None = None,
        patch_policy: str | None = None,
        user_initiated: bool = False,
    ) -> None:
        if not user_initiated:
            raise PolicyViolation("Authority changes require explicit user action")

        self._locked_authority = False
        try:
            if autonomy is not None:
                self.autonomy = autonomy
            if patch_policy is not None:
                try:
                    PatchPolicy(patch_policy)
                except ValueError:
                    raise UserInputError("patch_policy must be one of: disabled, interactive, auto")
                self.patch_policy = patch_policy
        finally:
            self._locked_authority = True

    def governance_report(self) -> dict[str, Any]:
        return {
            "session_id": str(self.id),
            "autonomy": int(self.autonomy),
            "patch_policy": self.patch_policy,
            "used_capabilities": sorted(self.used_capabilities),
            "blocked_capabilities": sorted(self.blocked_capabilities),
            "patches_proposed": list(self.patches_proposed),
            "patches_applied": list(self.patches_applied),
            "events": list(self.governance_events),
        }