# Graphite Control UI Style (15/10 Upgrade)

## Core Principles

- Keep signal high: one screen answers decisions, threats, opportunities, and system health.
- Fast actions first: command palette and inline create reduce clicks and context switching.
- Premium restraint: dark graphite base, sparse signal colors, and no decorative clutter.

## Advanced Patterns Added

- Global command palette (`Cmd+K` / `Ctrl+K`) for search + actions.
- Reusable tactical side panel for quick views and context actions.
- Decision Calendar with weekly grid and decision-type chips.
- Today cockpit structure:
  - `DECISIONS`
  - `THREATS`
  - `OPPORTUNITIES`
  - High-signal intelligence feed with mute/filter controls.
- Density mode (`Calm` / `Dense`) persisted with local storage.
- Toast confirmations for key create actions.

## Interaction Rules

- `Esc` closes overlays (palette and tactical panel).
- Focus rings are always visible (`:focus-visible`) for keyboard navigation.
- Motion timing stays subtle (`120–180ms`, no bounce).
- Signal glows only on risk/critical status chips, never as decoration.

## Status System

- `PASS` => green
- `FAIL` => red
- `BLOCKED` => red
- `RISK` => amber
- `DUE` => amber

Use consistent `status-chip` styles across dashboard, workflows, clients, and calendar.

## Empty-State Rules

- Never fake data.
- Show explicit placeholders and a direct CTA (e.g., “Connect data”, “Open CRM”, “Open workflows”).
