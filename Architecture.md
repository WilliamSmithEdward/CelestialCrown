# Celestial Crown Architecture

## Purpose

This document defines the target architecture for a squad-based, real-time strategic RPG and maps that architecture to the current implementation state.

## High-Level Layers

### 1) Core Runtime Layer
Location: src/core

Responsibilities:
- Engine lifecycle and main loop.
- State transitions and stack behavior.
- Shared campaign/session state.
- Cross-cutting services (logging, events, save/load in future).

Current key modules:
- src/core/gameengine.py
- src/core/gamestate.py
- src/core/campaign.py
- src/core/events.py
- src/core/logging.py

### 2) Domain Systems Layer
Location: src/battle, src/strategy, src/entities, src/town, src/story, src/map

Responsibilities:
- Battle calculations and turn rules.
- Real-time strategic mission simulation.
- Unit progression, stats, and classes.
- Economy, facilities, and town progression.
- Story alignment and branching structures.

Current key modules:
- src/battle/grid.py
- src/battle/combat.py
- src/battle/systems.py
- src/strategy/models.py
- src/entities/models.py
- src/entities/stats.py
- src/town/models.py
- src/town/managers.py
- src/story/models.py

### 3) Presentation and Interaction Layer
Location: src/states, src/ui, src/input, src/effects

Responsibilities:
- State-specific orchestration and rendering.
- Input-to-action mapping.
- HUD/menu components.
- Visual effects and readability affordances.

Current key modules:
- src/states/main_menu.py
- src/states/town.py
- src/states/battle.py
- src/ui/menu.py
- src/input/*

### 4) Content and Data Layer
Location: data, assets

Responsibilities:
- Scenario definitions and static game content.
- Audio/visual assets and mission metadata.
- Externalized balancing tables over time.

## Runtime Flow

1. main.py creates GameEngine and enters MainMenuState.
2. Main menu starts CampaignSession and transitions to TownState.
3. TownState handles roster/economy actions and deploys to BattleState.
4. BattleState runs a real-time StrategicMission simulation with squad orders.
5. Mission result is applied to CampaignSession progression.
6. Control returns to TownState for reinforcement and next deployment cycle.

## Core Domain Model

### Unit
- Atomic character entity with stats and progression.
- Lives in src/entities/models.py + src/entities/stats.py.

### Squad
- Strategic command actor containing multiple units.
- Holds role, tactic, position, target, and owner.
- Lives in src/strategy/models.py.

### StrategicSite
- Capturable objective with ownership and value.
- Drives map control and income pressure.
- Lives in src/strategy/models.py.

### StrategicMission
- Real-time battlefield simulation for movement, capture, collisions, and mission completion.
- Lives in src/strategy/models.py.

### CampaignSession
- Persistent run state across states and missions.
- Owns town, party, chapter progress, mission outcomes.
- Lives in src/core/campaign.py.

## State Responsibilities

### MainMenuState
- Entry point UX.
- Creates a new campaign session.
- Should eventually support load settings/profile selection.

### TownState
- Between-mission management layer.
- Recruitment, recovery, upgrades, squad preparation.
- Deploys the player into strategic missions.

### BattleState
- Real-time strategic map control loop.
- Squad selection, movement orders, recall, pause, and mission outcome resolution.

## Data Ownership Rules

- CampaignSession is the source of truth for persistent progression.
- StrategicMission owns transient mission-time simulation state.
- States orchestrate, they do not own core domain rules.
- Domain modules should remain deterministic and testable where possible.

## Error and Observability Strategy

- Domain exceptions are centralized in src/exceptions.py.
- Logging setup is centralized in src/core/logging.py.
- Startup display diagnostics are emitted by src/core/gameengine.py.
- EventBus in src/core/events.py is available for future decoupled signaling.

## Testing Strategy

Current testing structure:
- tests/unit for focused system behavior.
- tests/integration for state transition/runtime checks.

Coverage focus:
- Unit progression and combat math.
- Grid and battle mechanics.
- Town economy and facility rules.
- Strategic mission map control and completion logic.
- Engine state transition behavior.

## Extension Roadmap

### Near Term
- Dedicated squad management screen (formation rows, leader assignment, tactics presets).
- Mission templates loaded from data rather than hard-coded defaults.
- Save/load for CampaignSession and mission history.
- Richer enemy AI routing and objective weighting.

### Mid Term
- Class evolution and requirement-based promotions.
- Terrain affinity and movement lane modifiers.
- Tactical behavior profiles for squads and leaders.
- Story consequences tied to mission and alignment outcomes.

### Long Term
- Full content pipeline for chapters, maps, and recruitment pools.
- Advanced battle playback/replay UI for outcome explainability.
- Endgame structure with faction variants and branching conclusions.

## Architectural Guardrails

- Keep src/states focused on orchestration and rendering.
- Keep gameplay rules in domain modules, not UI components.
- Keep package __init__.py files as export surfaces only.
- Favor composable modules over large monolithic system files.
- Every new gameplay feature should ship with focused tests.
