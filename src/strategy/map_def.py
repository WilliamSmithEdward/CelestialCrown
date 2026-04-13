"""Map definition model — loaded from the `map.layers` section of a scenario JSON.

A MapDef is a pure data object with no pygame dependency.
The MapRenderer consumes it to produce both a baked static Surface and
per-frame animated overlays.

Layer types
-----------
fill     : fills the entire surface with the terrain
rect     : axis-aligned rectangle  { rect: [x, y, w, h] }
circle   : filled circle           { center: [cx, cy], radius: r }
path     : polyline (roads/rivers) { points: [[x,y],...], width: px }
polygon  : arbitrary polygon       { points: [[x,y],...] }

Animated terrains (rendered live each frame)
--------------------------------------------
river / water    : downstream shimmer dashes
lava             : slow heat-glow pulse  (future)
magic_pool       : rotating hue pulse   (future)
forest           : subtle edge canopy   (future – currently static bake)
"""

from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# Terrains that require per-frame animation
ANIMATED_TERRAINS: frozenset = frozenset({"river", "water", "lava", "magic_pool"})

# Terrain visual defaults (can be overridden per-layer via "color_*" keys)
TERRAIN_PALETTE: Dict[str, Dict[str, Any]] = {
    "grass": {
        "base":  (88,  138,  62),
        "light": (106, 158,  74),
        "dark":  (64,  108,  44),
    },
    "highland": {
        "base":  (164, 138,  84),
        "light": (188, 162, 104),
        "dark":  (132, 106,  62),
    },
    "forest": {
        "base":  (46,   92,  38),
        "light": (58,  112,  46),
        "dark":  (32,   68,  26),
    },
    "river": {
        "bank":  (118,  96,  58),
        "deep":  (54,  102, 178),
        "light": (88,  148, 220),
        "shimmer_speed": 55.0,   # px/s downstream
        "bank_width": 24,
        "water_width": 15,
    },
    "water": {  # standing water — same look, slower shimmer
        "bank":  (100,  80,  44),
        "deep":  (46,   88, 160),
        "light": (74,  128, 200),
        "shimmer_speed": 20.0,
        "bank_width": 20,
        "water_width": 14,
    },
    "road": {
        "fill": (192, 170, 110),
        "edge": (152, 128,  72),
        "fill_width": 6,
        "edge_width": 10,
    },
    "lava": {
        "base":  (200,  60,  10),
        "light": (240, 140,  20),
        "dark":  (140,  20,   5),
        "shimmer_speed": 30.0,
    },
}


@dataclass
class LayerDef:
    """A single visual layer on the strategic map."""

    id: str
    terrain: str          # key into TERRAIN_PALETTE
    layer_type: str       # fill | rect | circle | path | polygon

    # Geometry — which fields are used depends on layer_type
    points: List[List[float]] = field(default_factory=list)   # path / polygon
    rect: Optional[List[float]] = None                         # rect [x,y,w,h]
    center: Optional[List[float]] = None                       # circle
    radius: float = 0.0                                        # circle
    width: float = 10.0                                        # path stroke width

    # Optional per-layer palette overrides (merged over TERRAIN_PALETTE defaults)
    palette: Dict[str, Any] = field(default_factory=dict)

    # Resolved flag — set by MapDef.load()
    animated: bool = False

    @property
    def effective_palette(self) -> Dict[str, Any]:
        base = dict(TERRAIN_PALETTE.get(self.terrain, {}))
        base.update(self.palette)
        return base


@dataclass
class MapDef:
    """Full map definition loaded from JSON."""

    width: int
    height: int
    seed: int
    layers: List[LayerDef]

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "MapDef":
        layers = []
        for raw in data.get("layers", []):
            terrain = raw.get("terrain", "grass")
            layer = LayerDef(
                id=raw.get("id", ""),
                terrain=terrain,
                layer_type=raw.get("type", "fill"),
                points=raw.get("points", []),
                rect=raw.get("rect"),
                center=raw.get("center"),
                radius=float(raw.get("radius", 0.0)),
                width=float(raw.get("width", 10.0)),
                palette=raw.get("palette", {}),
                animated=terrain in ANIMATED_TERRAINS,
            )
            layers.append(layer)

        return MapDef(
            width=int(data.get("width", 1280)),
            height=int(data.get("height", 720)),
            seed=int(data.get("seed", 0)),
            layers=layers,
        )

    @staticmethod
    def load(path: pathlib.Path) -> "MapDef":
        with path.open(encoding="utf-8") as f:
            return MapDef.from_dict(json.load(f))
