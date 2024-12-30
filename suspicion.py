import dataclasses
import enum
from typing import Optional

from hexbytes import HexBytes


class SuspicionType(enum.IntEnum):
    # SEVERITY IN ASCENDING ORDER
    NONE = 0
    LIGHT = 1
    HARD = 2

    # Order of severity: None < LIGHT < HARD
    @staticmethod
    def get_most_severe(sus1: Optional['SuspicionType'], sus2: Optional['SuspicionType']):
        return SuspicionType(max(sus1.value, sus2.value))


@dataclasses.dataclass
class SuspicionStatus:
    sus: SuspicionType

    def found_suspicion(self, found: SuspicionType):
        self.sus = SuspicionType.get_most_severe(self.sus, found)


@dataclasses.dataclass
class SuspectedReentrancy:
    transaction: HexBytes
    type: SuspicionType
