# Celestial Crown Roadmap

## Roadmap Intent

This roadmap turns the project philosophy into a practical delivery plan for a full squad-based, real-time strategic RPG. It is organized by playable milestones, not just feature buckets.

## Development Principles

- Deliver vertically playable slices.
- Keep squad-level strategy as the center of every milestone.
- Tie each milestone to measurable acceptance criteria.
- Preserve test coverage and architecture quality while scaling content.

## Current Baseline (Completed)

- Core engine loop and state framework.
- Main menu, town layer, and strategic battle state skeleton.
- Campaign session persistence in-memory.
- Real-time strategic mission model with movement, captures, collisions, and mission completion.
- Auto-resolved combat and basic progression/reward loop.
- Design docs: DesignPhilosophy, Architecture, UIUXPhilosophy.
- Automated test suite with passing unit/integration tests.

## Phase 1: Command Loop Foundation (Near-Term)

### Goal
Make the strategic loop consistently fun and readable for repeated missions.

### Deliverables
- [x] Dedicated squad management screen (initial playable implementation).
- Squad formation editor (front/back row abstraction).
- Leader assignment and squad tactic presets.
- Order queue basics (primary target + fallback).
- Better enemy strategic behavior (objective weighting and lane pressure).
- Battle outcome report panel with clear causality summary.

### Acceptance Criteria
- Player can configure at least 4 squads with distinct roles.
- Map mission is fully playable without placeholder controls.
- Engagement reports explain outcomes in role/composition terms.
- All new systems covered by unit tests.

## Phase 2: Strategic Depth and Readability (Near/Mid-Term)

### Goal
Increase map-control depth and make multi-front pressure feel intentional.

### Deliverables
- Terrain modifiers (movement speed, route risk, and tactical affinity).
- Site rule expansion (towns, forts, temples, resources with unique strategic effects).
- Reinforcement and recovery range tied to controlled sites.
- [x] Intercept prediction indicators and threat overlays.
- [x] Procedural terrain background with ISO building sprites and squad tokens.
- Top-down camera mode (toggle from isometric view, unlocked in Phase 2).
- Pause-time command planning improvements.

### Acceptance Criteria
- Map control produces meaningful economic and tempo differences.
- Losing one lane can create measurable cascading pressure.
- Player can identify highest-risk front in under 3 seconds from map view.

## Phase 3: Army Growth and Class Arc (Mid-Term)

### Goal
Turn progression into long-term strategic expression instead of flat stat scaling.

### Deliverables
- Class promotion/evolution system with requirements.
- Expanded recruit pools and role-specialized classes.
- Squad synergy bonuses and leader auras.
- Equipment layer with constrained but meaningful choices.
- Persistent injury/fatigue or readiness system for rotation pressure.

### Acceptance Criteria
- Multiple viable squad archetypes can clear the same mission differently.
- Promotions are unlock-driven and feel aspirational.
- Squad composition decisions materially affect auto-resolve outcomes.

## Phase 4: Campaign Structure and Consequence (Mid/Late-Term)

### Goal
Make the campaign feel like a connected military arc with strategic and narrative consequences.

### Deliverables
- Chapter/mission pipeline loaded from data content.
- Branching mission flow with persistent world-state flags.
- Morality/reputation layer tied to liberation outcomes and casualties.
- Recruitment and class access influenced by campaign behavior.
- Mid-campaign events and crisis missions.

### Acceptance Criteria
- At least 2 distinct campaign routes are possible.
- Player decisions alter available units, missions, or tactical options.
- Campaign momentum feels cumulative, not reset between missions.

## Phase 5: UX and Production Hardening (Late-Term)

### Goal
Polish usability, onboarding, and reliability for sustained play.

### Deliverables
- Full HUD pass for strategic readability.
- Tutorialized onboarding for command loop and squad design.
- Save/load profiles and checkpoint strategy.
- Balancing pass with telemetry-driven tuning hooks.
- Stability/performance optimization for longer sessions.

### Acceptance Criteria
- New players can complete first full mission without confusion.
- Save/load is stable across chapter progression.
- Long-session play remains performant and readable.

## Phase 6: Content Expansion and Release Candidate (Late-Term)

### Goal
Ship a complete, replayable campaign experience.

### Deliverables
- Full campaign chapter set.
- Expanded class roster and enemy doctrine variety.
- Distinct mission archetypes (defend, breakthrough, escort, encirclement).
- Final balancing, difficulty tiers, and endgame outcomes.
- Release checklist and documentation pack.

### Acceptance Criteria
- End-to-end campaign is completable with multiple strategic styles.
- Replayability exists through route variation and roster expression.
- Release branch passes all tests and smoke scenarios.

## Continuous Tracks (Across All Phases)

### Testing and Quality
- Expand unit tests with each domain feature.
- Add integration scenarios for state flow and mission progression.
- Add deterministic simulation harnesses where possible for AI/combat validation.

### Architecture Hygiene
- Keep orchestration in states, rules in domain modules.
- Prevent monolith drift through focused module boundaries.
- Maintain clear ownership between campaign state and mission state.

### Content Pipeline
- Move hard-coded mission defaults into data-driven definitions.
- Standardize schema for missions, squads, sites, and events.
- Add validation tools for content authoring.

## Milestone Exit Checklist Template

Each milestone is considered complete when:
- Feature set is playable end-to-end.
- Design intent is reflected in UX, not only backend logic.
- Tests are added and passing.
- Known critical defects are resolved.
- Documentation is updated (Architecture, Philosophy, UI/UX, Roadmap deltas).

## Immediate Next Slice

Recommended immediate next implementation slice:
1. Add map threat overlay and intercept forecast.
2. Replace hard-coded mission setup with first data-loaded mission definition.
3. Expand squad management with leader assignment and row formation rules.
