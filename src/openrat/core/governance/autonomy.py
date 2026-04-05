from enum import Enum


class AutonomyLevel(int, Enum):
    OBSERVE = 0 
    PARAMS_ONLY = 1
    RUNTIME_REPAIR = 2 
    EXTENDED_EDIT = 3


CAPABILITY_OBSERVE = "observe"
CAPABILITY_HOST_EXEC = "host.exec"
CAPABILITY_PARAMS_MODIFY = "params.modify"
CAPABILITY_RUNTIME_FIX = "runtime.fix"
CAPABILITY_CODE_EDIT = "code.edit"


CAPABILITY_MIN_LEVEL: dict[str, AutonomyLevel] = {
    CAPABILITY_OBSERVE: AutonomyLevel.OBSERVE,
    CAPABILITY_HOST_EXEC: AutonomyLevel.EXTENDED_EDIT,
    CAPABILITY_PARAMS_MODIFY: AutonomyLevel.PARAMS_ONLY,
    CAPABILITY_RUNTIME_FIX: AutonomyLevel.RUNTIME_REPAIR,
    CAPABILITY_CODE_EDIT: AutonomyLevel.EXTENDED_EDIT,
}


def required_level_for(capability: str) -> AutonomyLevel | None:
    return CAPABILITY_MIN_LEVEL.get(capability)


def is_known_capability(capability: str) -> bool:
    return capability in CAPABILITY_MIN_LEVEL