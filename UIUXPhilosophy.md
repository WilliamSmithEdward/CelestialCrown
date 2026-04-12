# Celestial Crown UI/UX Philosophy

## Purpose

This document defines the UI and UX principles for Celestial Crown as a squad-based, real-time strategic RPG. The interface must help the player make high-impact command decisions quickly and confidently under pressure.

## Core UX Goal

The player should always be able to answer three questions at a glance:
- What is happening right now?
- What will happen next if I do nothing?
- Which command gives me the best tradeoff in this moment?

The UI exists to reduce strategic ambiguity, not to increase spectacle at the cost of clarity.

## Design Priorities

1. Strategic readability over decorative complexity.
2. Fast command issuance over deep click paths.
3. Explainability of outcomes over opaque simulation.
4. Consistent interaction patterns across states.
5. Accessibility and comfort for long sessions.

## Information Hierarchy

### Primary Layer: Battlefield Situation
Highest priority information:
- Site ownership and objective status.
- Ally squad positions, destinations, and role identity.
- Enemy squad movement and pressure vectors.
- Frontline stability and collapsing lanes.

This layer should remain legible while the map is moving in real time.

### Secondary Layer: Command Context
Second priority information:
- Selected squad details (role, health, leader, readiness).
- Current orders and travel intent.
- Intercept risks and expected contact points.
- Tactical posture (aggressive, balanced, safe).

### Tertiary Layer: Deep Detail
Lower priority information on demand:
- Individual unit stats and class traits.
- Equipment and progression nuances.
- Detailed combat event logs.

## Map UX Principles

### 1) Frontline Legibility
- Ownership must be obvious through color, shape, and iconography.
- Movement routes and destinations should be visually persistent.
- Threat direction should be clear without opening extra panels.

### 2) Command Latency Must Be Low
- Selecting squads and assigning destinations should require minimal input steps.
- Common actions (deploy, redirect, recall, pause) must be one-step interactions.
- Real-time flow should not force frequent menu diving.

### 3) Multi-Front Awareness
- The player should not lose track of side lanes during central engagements.
- Critical alerts should prioritize strategic impact, not raw event volume.
- Quiet fronts still need lightweight status visibility.

## Squad UX Principles

### 1) Squad Identity First
Every squad panel should immediately communicate:
- Role and intended purpose.
- Leader status.
- Current combat readiness.
- Composition shape (frontline vs support).

### 2) Reconfiguration Should Feel Core
- Rearranging squads should be fast and reversible.
- Role changes should preview likely strengths and weaknesses.
- The UI should help compare squads by purpose, not only by level.

### 3) Explain Matchups
When a squad wins or loses, provide concise reasons tied to:
- Composition and role interactions.
- Survivability and damage profile.
- Tactical setting choices.

## Auto-Resolve Combat UX Principles

The combat presentation should reinforce strategic causality.

Required readability:
- Who acted and in what sequence.
- Momentum shifts and key turning points.
- Why the result happened in plain terms.

Avoid turning auto-resolve into a noisy feed of low-signal events.

## Input Model Principles

- Keyboard/controller parity for core actions.
- Predictable navigation and confirm/cancel behavior.
- Explicit pause controls for real-time pressure management.
- No hidden critical commands.

Controls should support both rapid command players and deliberate planners.

## Visual Language

- Use stable, consistent color semantics for ally/enemy/neutral states.
- Reserve high-contrast accents for actionable urgency.
- Distinguish information types with typography and spacing, not only color.
- Maintain clean silhouettes for squad/site markers at all camera scales.

## Motion and Feedback

- Motion should communicate state change, not decorate static UI.
- Order acknowledgments must be immediate and unambiguous.
- Captures, interceptions, and front collapses should produce clear feedback with minimal interruption.

Feedback should be informative, brief, and strategically relevant.

## Accessibility and Comfort

- Support scalable text and UI density options over time.
- Avoid relying on color alone for ownership or alert states.
- Keep core interactions playable without high APM demands.
- Minimize cognitive overload from overlapping alerts.

## State-by-State UX Expectations

### Main Menu
- Clear path to continue/start command flow quickly.
- Visual identity should establish tone without slowing entry.

### Town/Management
- Emphasize roster quality, readiness, and strategic resource decisions.
- Keep squad construction and restructuring central.

### Strategic Battle Map
- Prioritize lane pressure, route choices, and command responsiveness.
- Maintain clarity during simultaneous movement and engagements.

### Battle Outcome/Report
- Summarize consequences in tactical terms the player can act on next mission.

## Error Prevention and Recovery

- Prevent accidental irreversible actions when possible.
- Confirm high-impact decisions (withdraw, disband, major spend).
- Make order changes and rerouting easy during mission flow.

The player should feel in control even when under pressure.

## UX Anti-Goals

Avoid:
- UI clutter that obscures strategic reality.
- Excessive modal interruptions during real-time play.
- Hidden mechanics with no readable feedback path.
- Deep menu nesting for high-frequency actions.

## Success Criteria

The UI/UX is successful when players consistently report:
- They understand the battlefield state at a glance.
- They can issue commands quickly without friction.
- They can explain why engagements were won or lost.
- They feel strategic ownership over campaign momentum.
