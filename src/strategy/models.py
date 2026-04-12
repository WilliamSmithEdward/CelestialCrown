"""Real-time strategic map models for squad-based missions."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import math
import random
from typing import Dict, List, Optional, Tuple

from ..battle import CombatSystem
from ..entities import Unit, UnitClass


class SiteType(Enum):
    """Strategic site categories."""

    BASE = "base"
    TOWN = "town"
    TEMPLE = "temple"
    FORT = "fort"
    RESOURCE = "resource"


class SquadRole(Enum):
    """Strategic role for a squad."""

    ASSAULT = "assault"
    DEFENSE = "defense"
    SUPPORT = "support"
    HUNTER = "hunter"
    SKIRMISH = "skirmish"


class SquadTactic(Enum):
    """High-level automated combat behavior."""

    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"
    SAFE = "safe"


@dataclass
class StrategicSite:
    """A capture point or objective on the strategic map."""

    id: str
    name: str
    x: float
    y: float
    site_type: SiteType
    owner: int = -1  # -1 neutral, 0 player, 1 enemy
    value: int = 100
    capture_progress: float = 0.0
    sprite: Optional[str] = None  # sprite key for renderer


@dataclass
class Squad:
    """A formation of units that moves and fights as one actor on the map."""

    id: str
    name: str
    units: List[Unit] = field(default_factory=list)
    owner: int = 0
    x: float = 0.0
    y: float = 0.0
    speed: float = 120.0
    role: SquadRole = SquadRole.ASSAULT
    tactic: SquadTactic = SquadTactic.BALANCED
    target_site_id: Optional[str] = None
    is_retreating: bool = False

    def alive_units(self) -> List[Unit]:
        """Return currently alive units in this squad."""
        return [unit for unit in self.units if unit.is_alive]

    def is_destroyed(self) -> bool:
        """Check if squad has no surviving members."""
        return len(self.alive_units()) == 0


@dataclass
class EngagementReport:
    """Result of a squad-vs-squad collision."""

    squad_a_id: str
    squad_b_id: str
    winner_owner: int
    rounds: int
    losses_a: int
    losses_b: int


@dataclass
class StrategicMission:
    """Live battlefield simulation with squads, sites, and pressure."""

    sites: Dict[str, StrategicSite]
    squads: List[Squad]
    lanes: List[List[str]] = field(default_factory=list)
    time_elapsed: float = 0.0
    player_income: int = 0
    enemy_income: int = 0
    pressure_index: float = 0.0
    last_engagement: Optional[EngagementReport] = None

    capture_radius: float = 52.0
    collision_radius: float = 36.0

    def get_site(self, site_id: str) -> Optional[StrategicSite]:
        """Return site by id."""
        return self.sites.get(site_id)

    def allied_squads(self, owner: int) -> List[Squad]:
        """Get squads owned by a side."""
        return [squad for squad in self.squads if squad.owner == owner and not squad.is_destroyed()]

    def issue_order(self, squad_id: str, site_id: str) -> bool:
        """Assign a destination site to a squad."""
        if site_id not in self.sites:
            return False

        for squad in self.squads:
            if squad.id == squad_id and not squad.is_destroyed():
                squad.target_site_id = site_id
                squad.is_retreating = False
                return True
        return False

    def recall_squad(self, squad_id: str, owner: int) -> bool:
        """Recall squad to nearest allied base/fort."""
        squad = next((s for s in self.squads if s.id == squad_id and s.owner == owner), None)
        if squad is None or squad.is_destroyed():
            return False

        home_sites = [
            site
            for site in self.sites.values()
            if site.owner == owner and site.site_type in (SiteType.BASE, SiteType.FORT)
        ]
        if not home_sites:
            return False

        nearest = min(home_sites, key=lambda site: _distance(squad.x, squad.y, site.x, site.y))
        squad.target_site_id = nearest.id
        squad.is_retreating = True
        return True

    def update(self, delta_time: float) -> None:
        """Advance mission simulation in real time."""
        self.time_elapsed += max(0.0, delta_time)
        self._move_squads(delta_time)
        self._resolve_captures(delta_time)
        self._resolve_collisions()
        self._update_income_and_pressure()

    def _move_squads(self, delta_time: float) -> None:
        for squad in self.squads:
            if squad.target_site_id is None or squad.is_destroyed():
                continue

            target = self.sites.get(squad.target_site_id)
            if target is None:
                continue

            dx = target.x - squad.x
            dy = target.y - squad.y
            dist = math.hypot(dx, dy)
            if dist < 1e-5:
                continue

            step = squad.speed * max(0.0, delta_time)
            if step >= dist:
                squad.x = target.x
                squad.y = target.y
            else:
                squad.x += (dx / dist) * step
                squad.y += (dy / dist) * step

    def _resolve_captures(self, delta_time: float) -> None:
        for site in self.sites.values():
            nearby = [
                squad for squad in self.squads if not squad.is_destroyed() and _distance(squad.x, squad.y, site.x, site.y) <= self.capture_radius
            ]
            if not nearby:
                site.capture_progress = max(0.0, site.capture_progress - delta_time * 5.0)
                continue

            player_presence = sum(1 for squad in nearby if squad.owner == 0)
            enemy_presence = sum(1 for squad in nearby if squad.owner == 1)
            if player_presence == enemy_presence:
                continue

            if player_presence > enemy_presence:
                captor = 0
                diff = player_presence - enemy_presence
            else:
                captor = 1
                diff = enemy_presence - player_presence

            if site.owner == captor:
                site.capture_progress = min(100.0, site.capture_progress + delta_time * 6.0)
            else:
                site.capture_progress += delta_time * 20.0 * diff
                if site.capture_progress >= 100.0:
                    site.owner = captor
                    site.capture_progress = 0.0

    def _resolve_collisions(self) -> None:
        self.last_engagement = None
        for i, squad_a in enumerate(self.squads):
            if squad_a.is_destroyed():
                continue
            for squad_b in self.squads[i + 1 :]:
                if squad_b.is_destroyed() or squad_a.owner == squad_b.owner:
                    continue
                if _distance(squad_a.x, squad_a.y, squad_b.x, squad_b.y) <= self.collision_radius:
                    self.last_engagement = _resolve_engagement(squad_a, squad_b)

    def _update_income_and_pressure(self) -> None:
        player_sites = [site for site in self.sites.values() if site.owner == 0]
        enemy_sites = [site for site in self.sites.values() if site.owner == 1]
        self.player_income = sum(site.value for site in player_sites)
        self.enemy_income = sum(site.value for site in enemy_sites)

        front_threat = len(self.allied_squads(1)) - len(self.allied_squads(0))
        territory_delta = len(enemy_sites) - len(player_sites)
        self.pressure_index = float(front_threat * 3 + territory_delta * 5)

    def is_complete(self) -> Tuple[bool, str]:
        """Return completion state and result string."""
        player_alive = len(self.allied_squads(0)) > 0
        enemy_alive = len(self.allied_squads(1)) > 0

        player_base = next((site for site in self.sites.values() if site.id == "player_base"), None)
        enemy_base = next((site for site in self.sites.values() if site.id == "enemy_base"), None)

        if enemy_base is not None and enemy_base.owner == 0:
            return True, "victory"
        if player_base is not None and player_base.owner == 1:
            return True, "defeat"
        if not enemy_alive:
            return True, "victory"
        if not player_alive:
            return True, "defeat"
        return False, ""


def create_default_mission(chapter: int = 1) -> StrategicMission:
    """Create a starter mission with lanes, strategic sites, and enemy pressure."""
    sites = {
        "player_base": StrategicSite("player_base", "Asterhold Gate", 120, 360, SiteType.BASE, owner=0, value=160),
        "west_town": StrategicSite("west_town", "Lowmarket", 300, 280, SiteType.TOWN, owner=-1, value=90),
        "center_fort": StrategicSite("center_fort", "Rookspire", 520, 360, SiteType.FORT, owner=-1, value=120),
        "east_temple": StrategicSite("east_temple", "Sky Chapel", 740, 280, SiteType.TEMPLE, owner=-1, value=100),
        "ore_field": StrategicSite("ore_field", "Iron Vein", 860, 500, SiteType.RESOURCE, owner=1, value=110),
        "enemy_base": StrategicSite("enemy_base", "Dread Bastion", 1030, 360, SiteType.BASE, owner=1, value=170),
    }

    allied_squads = [
        Squad("a_1", "Vanguard", _generate_units("a1", 0, chapter), owner=0, x=120, y=360, speed=130.0, role=SquadRole.ASSAULT),
        Squad("a_2", "Wardens", _generate_units("a2", 0, chapter), owner=0, x=140, y=420, speed=115.0, role=SquadRole.DEFENSE),
    ]

    enemy_count = min(2 + chapter, 5)
    enemy_squads: List[Squad] = []
    for i in range(enemy_count):
        enemy_squads.append(
            Squad(
                f"e_{i + 1}",
                f"Legion {i + 1}",
                _generate_units(f"e{i+1}", 1, chapter + 1),
                owner=1,
                x=1030 + random.randint(-30, 20),
                y=340 + random.randint(-80, 80),
                speed=110.0 + random.randint(-8, 8),
                role=random.choice([SquadRole.ASSAULT, SquadRole.HUNTER, SquadRole.SKIRMISH]),
            )
        )

    default_lanes = [
        ["player_base", "west_town"],
        ["west_town", "center_fort"],
        ["center_fort", "east_temple"],
        ["east_temple", "enemy_base"],
        ["center_fort", "ore_field"],
        ["ore_field", "enemy_base"],
    ]
    return StrategicMission(sites=sites, squads=allied_squads + enemy_squads, lanes=default_lanes)


def _resolve_engagement(squad_a: Squad, squad_b: Squad) -> EngagementReport:
    alive_a = squad_a.alive_units()
    alive_b = squad_b.alive_units()
    start_a = len(alive_a)
    start_b = len(alive_b)

    rounds = 0
    while alive_a and alive_b and rounds < 8:
        rounds += 1
        turn_order = sorted(alive_a + alive_b, key=lambda unit: unit.stats.agl, reverse=True)
        for actor in turn_order:
            if not actor.is_alive:
                continue

            if actor in alive_a:
                targets = [unit for unit in alive_b if unit.is_alive]
            else:
                targets = [unit for unit in alive_a if unit.is_alive]

            if not targets:
                break

            target = random.choice(targets)
            damage, hit, _critical = CombatSystem.execute_attack(actor, target)
            if hit and damage > 0:
                target.take_damage(damage)

        alive_a = [unit for unit in squad_a.units if unit.is_alive]
        alive_b = [unit for unit in squad_b.units if unit.is_alive]

    losses_a = start_a - len(alive_a)
    losses_b = start_b - len(alive_b)
    if len(alive_a) > len(alive_b):
        winner = squad_a.owner
    elif len(alive_b) > len(alive_a):
        winner = squad_b.owner
    else:
        winner = squad_a.owner if random.random() < 0.5 else squad_b.owner

    return EngagementReport(
        squad_a_id=squad_a.id,
        squad_b_id=squad_b.id,
        winner_owner=winner,
        rounds=rounds,
        losses_a=losses_a,
        losses_b=losses_b,
    )


def _distance(x1: float, y1: float, x2: float, y2: float) -> float:
    return math.hypot(x2 - x1, y2 - y1)


def _generate_units(prefix: str, team: int, level: int) -> List[Unit]:
    classes = [UnitClass.KNIGHT, UnitClass.MAGE, UnitClass.ARCHER]
    units: List[Unit] = []
    for index, unit_class in enumerate(classes):
        unit = Unit(f"{prefix}_{index}", f"{prefix.upper()}-{index + 1}", unit_class, level=max(1, level))
        unit.team = team
        units.append(unit)
    return units
