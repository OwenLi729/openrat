from enum import Enum


class AutonomyLevel(int, Enum):
    OBSERVE = 0
    PARAMS_ONLY = 1
    RUNTIME_REPAIR = 2
    EXTENDED_EDIT = 3