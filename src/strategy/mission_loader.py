"""Load StrategicMission instances from JSON scenario configs."""

from __future__ import annotations

import json
import pathlib
import random
from typing import Any, Dict

from .models import (
    Squad,
    SquadRole,
    SquadTactic,
    StrategicMission,
    StrategicSite,
    SiteType,
    _generate_units,
)

_SCENARIOS_DIR = pathlib.Path(__file__).parent.parent.parent / "data" / "scenarios"

_SITE_TYPE_MAP = {
    "BASE": SiteType.BASE,
    "TOWN": SiteType.TOWN,
    "TEMPLE": SiteType.TEMPLE,
    "FORT": SiteType.FORT,
    "RESOURCE": SiteType.RESOURCE,
}

_ROLE_MAP = {
    "ASSAULT": SquadRole.ASSAULT,
    "DEFENSE": SquadRole.DEFENSE,
    "SUPPORT": SquadRole.SUPPORT,
    "HUNTER": SquadRole.HUNTER,
    "SKIRMISH": SquadRole.SKIRMISH,
}


def load_mission(scenario_id: str, chapter: int = 1) -> StrategicMission:
    """Load a StrategicMission from a JSON scenario file.

    Falls back to create_default_mission if the file is not found.
    """
    path = _SCENARIOS_DIR / f"{scenario_id}.json"
    if not path.exists():
        from .models import create_default_mission
        return create_default_mission(chapter)

    with path.open(encoding="utf-8") as f:
        data: Dict[str, Any] = json.load(f)

    sites = {}
    for s in data.get("sites", []):
        site = StrategicSite(
            id=s["id"],
            name=s["name"],
            x=float(s["x"]),
            y=float(s["y"]),
            site_type=_SITE_TYPE_MAP.get(s["type"], SiteType.FORT),
            owner=int(s.get("owner", -1)),
            value=int(s.get("value", 100)),
            sprite=s.get("sprite"),
        )
        sites[site.id] = site

    squads = []

    for sp in data.get("player_squads", []):
        squads.append(Squad(
            id=sp["id"],
            name=sp["name"],
            units=_generate_units(sp["id"], 0, chapter),
            owner=0,
            x=float(sp.get("x", 120)),
            y=float(sp.get("y", 360)),
            speed=float(sp.get("speed", 120)),
            role=_ROLE_MAP.get(sp.get("role", "ASSAULT"), SquadRole.ASSAULT),
        ))

    for es in data.get("enemy_squads", []):
        squads.append(Squad(
            id=es["id"],
            name=es["name"],
            units=_generate_units(es["id"], 1, chapter + 1),
            owner=1,
            x=float(es.get("x", 1030)) + random.randint(-20, 20),
            y=float(es.get("y", 360)) + random.randint(-60, 60),
            speed=float(es.get("speed", 110)),
            role=_ROLE_MAP.get(es.get("role", "ASSAULT"), SquadRole.ASSAULT),
            tactic=SquadTactic.AGGRESSIVE,
        ))

    lanes = data.get("lanes", [])

    return StrategicMission(sites=sites, squads=squads, lanes=lanes)
