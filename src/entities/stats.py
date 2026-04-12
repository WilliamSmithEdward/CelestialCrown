"""Character statistics and stat management."""

from dataclasses import dataclass

from ..config import STAT_MAX, STAT_MIN


@dataclass
class Stats:
    """Character base statistics."""

    hp: int = 30
    str: int = 10
    def_: int = 10
    agl: int = 10
    int_: int = 10
    wil: int = 10

    def clamp(self) -> None:
        """Ensure all stats are within valid range."""
        self.hp = max(STAT_MIN, min(STAT_MAX, self.hp))
        self.str = max(STAT_MIN, min(STAT_MAX, self.str))
        self.def_ = max(STAT_MIN, min(STAT_MAX, self.def_))
        self.agl = max(STAT_MIN, min(STAT_MAX, self.agl))
        self.int_ = max(STAT_MIN, min(STAT_MAX, self.int_))
        self.wil = max(STAT_MIN, min(STAT_MAX, self.wil))

    def __str__(self) -> str:
        return f"HP:{self.hp} STR:{self.str} DEF:{self.def_} AGL:{self.agl} INT:{self.int_} WIL:{self.wil}"
