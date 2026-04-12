# Celestial Crown — Sprite Art Specification

## Scope

This document defines every sprite category needed for the strategic mission map view. All dimensions, palettes, and delivery formats are fixed constraints — the code renderer loads these exactly. Deviations require a code change.

---

## Global Rules

| Property | Requirement |
|---|---|
| Format | PNG-32 (RGBA, transparency preserved) |
| Resolution philosophy | 2× working canvas, exported at 1× gameplay size |
| Color depth | Full color, unlimited palette |
| Outline | 1 px anti-aliased dark outline on all opaque edges |
| Drop shadow | Soft radial shadow on a separate `_shadow.png` layer (optional, composited at runtime) |
| Anchor point | Horizontally centered, bottom edge = ground contact point |
| Naming convention | `{category}_{variant}.png` — all lowercase, underscores only |

---

## 1. Strategic Site Buildings

Buildings sit permanently on the map. They must read clearly at their rendered size and have strong silhouette differentiation between types.

### Delivery sizes

| Sprite key | Gameplay size (px) | Variants |
|---|---|---|
| `base_allied` | 96 × 96 | `_owned`, `_neutral`, `_captured` |
| `base_enemy` | 96 × 96 | `_owned`, `_damaged` |
| `fort_stone` | 80 × 80 | `_neutral`, `_allied`, `_enemy` |
| `town_small` | 72 × 72 | `_neutral`, `_allied`, `_enemy` |
| `temple_sky` | 80 × 88 | `_neutral`, `_allied`, `_enemy` |
| `resource_ore` | 64 × 64 | `_neutral`, `_allied`, `_enemy` |

### Art direction

- **`base_allied`** — Fortified stone gate tower, warm-grey stone, blue-pennant banner, arched doorway. ISO front-facing. Allied = banner flies. Captured = banner torn.
- **`base_enemy`** — Dark bastion, black stone, red iron spikes on ramparts, iron gate. Enemy pennant is deep crimson.
- **`fort_stone`** — Compact tower with battlements. Stone-grey, single flag pole. Neutral = bare pole. Allied/Enemy = colour-tinted pennant.
- **`town_small`** — Cluster of 3–4 small medieval buildings, thatched roofs, cobbled lane implied. Warm ochre tones.
- **`temple_sky`** — Elegant spire, pale blue stonework, gold trim on arched windows. ISO front-facing.
- **`resource_ore`** — Mining scaffold over a rocky outcrop, dark iron ore veins visible. Cart wheel implied.

### Ownership tinting at runtime

All site sprites are tinted in code when owner changes. The art must use close-to-neutral midtones so tinting reads cleanly:
- Player (owner 0): `+15` blue channel, `+8` green
- Enemy (owner 1): `+20` red channel, `−8` blue
- Neutral (owner −1): no tint

---

## 2. Squad Tokens (Map Units)

Squad tokens are the moving pieces on the map. They should read as groups of characters, not individual units.

### Delivery sizes

| Sprite key | Gameplay size (px) | Frames | Notes |
|---|---|---|---|
| `squad_allied_assault` | 48 × 56 | 4 idle (2 fps) | Knight lead, 2 soldiers behind |
| `squad_allied_defense` | 48 × 56 | 4 idle | Shield wall arrangement |
| `squad_allied_support` | 48 × 56 | 4 idle | Robed figure + 2 guards |
| `squad_allied_hunter` | 48 × 56 | 4 idle | Ranger lead, crouched |
| `squad_allied_skirmish` | 48 × 56 | 4 idle | Light armor, split formation |
| `squad_enemy_*` | 48 × 56 | 4 idle | Same roles, red/black palette |

All variants above also need:
- `_move` — 6-frame walk cycle (used while `target_site_id` is set)
- `_combat` — 4-frame clash loop (used during engagement)
- `_retreat` — 4-frame limping/falling-back loop

### Art direction

- **ISO three-quarter view** — characters face bottom-right (camera south-east).
- Group silhouette: foreground hero character at full detail, 1–2 smaller flanking figures at 60% opacity behind.
- Allied palette: steel/silver armor, blue-tinted cloaks, warm skin tones.
- Enemy palette: dark iron, crimson trim, pale or shadowed faces.
- Selection ring is drawn in code — do NOT bake it into the sprite.

### Spritesheet layout

All frames for a single sprite key in a horizontal strip:
```
[idle_0][idle_1][idle_2][idle_3][move_0]...[move_5][combat_0]...[combat_3][retreat_0]...[retreat_3]
```
Total frames per full sheet: 4 + 6 + 4 + 4 = 18 frames  
Sheet size (gameplay px): 48 × 18 = **864 × 56 px**

---

## 3. HUD Elements

| Sprite key | Gameplay size (px) | Notes |
|---|---|---|
| `hud_clock_frame` | 160 × 88 | Decorative frame for timer (top-right) |
| `hud_day_badge` | 56 × 40 | Day counter pill badge |
| `hud_pressure_bar` | 200 × 24 | Fills red/amber/green; anchor left |
| `hud_income_icon` | 24 × 24 | Gold coin icon |

### Art direction

- Aged brass/clockwork aesthetic. Riveted metal frame. Faint gear motifs.
- Timer digits are baked into the frame sprite as masked regions (code renders numbers over them).
- Keep fully opaque to guarantee legibility on busy terrain.

---

## 4. Overlay / VFX Sprites

| Sprite key | Gameplay size (px) | Frames | Notes |
|---|---|---|---|
| `vfx_intercept_diamond` | 20 × 20 | 8 (spin loop, 12 fps) | Yellow warning diamond |
| `vfx_threat_pulse` | 80 × 80 | 8 (pulse loop, 10 fps) | Red radial glow ring |
| `vfx_capture_ring` | 64 × 64 | 6 (spin, 8 fps) | Site capture progress ring |
| `vfx_engagement_clash` | 72 × 72 | 10 (hit loop) | Sword-clash spark burst |

---

## 5. Delivery Checklist

```
assets/sprites/
  sites/
    base_allied_owned.png
    base_allied_captured.png
    base_enemy_owned.png
    base_enemy_damaged.png
    fort_stone_neutral.png
    fort_stone_allied.png
    fort_stone_enemy.png
    town_small_neutral.png
    town_small_allied.png
    town_small_enemy.png
    temple_sky_neutral.png
    temple_sky_allied.png
    temple_sky_enemy.png
    resource_ore_neutral.png
    resource_ore_allied.png
    resource_ore_enemy.png
  squads/
    squad_allied_assault.png        ← full 18-frame horizontal sheet
    squad_allied_defense.png
    squad_allied_support.png
    squad_allied_hunter.png
    squad_allied_skirmish.png
    squad_enemy_assault.png
    squad_enemy_defense.png
    squad_enemy_support.png
    squad_enemy_hunter.png
    squad_enemy_skirmish.png
  hud/
    hud_clock_frame.png
    hud_day_badge.png
    hud_pressure_bar.png
    hud_income_icon.png
  vfx/
    vfx_intercept_diamond.png       ← 8-frame horizontal sheet
    vfx_threat_pulse.png
    vfx_capture_ring.png
    vfx_engagement_clash.png
```

---

## 6. Placeholder Policy

Until real sprites are delivered, the renderer draws procedurally generated stand-ins using the same anchor/size contracts. Placeholder squad tokens are colored circles with role-colored rings. Placeholder buildings are flat polygons with type-colored fills. The renderer detects missing files via `Path.exists()` and falls back silently.
