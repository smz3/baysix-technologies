# Architecture — Navigation Index

**Start here. Read in this order.**

| # | File | What it is |
|---|------|-----------|
| 1 | **`ENGINE_BLUEPRINT.md`** | **THE authoritative design.** Read this first. Declares the canonical architecture, the engine/strategy split, the validate-first build order, and the falsification gate. Everything else supports it. |
| 2 | `engine-architecture/` | The canonical architecture in depth (Co-Work docs): Data Layer, Context Engine, Regime Engine, Signal/Execution, Options Flow. The blueprint adopts these. |
| 3 | `engine-diagram/` | SVG diagrams of the system and each L4/L5 engine. |
| 4 | `ADR-001 … ADR-005` | Architecture Decision Records — the locked-in choices (factor model, regime detection, signal combination, IC method, cost model) with their upgrade triggers. Read the relevant ADR before modifying any engine component. |

## Status legend
- **Active:** ADR-001, ADR-003, ADR-004, ADR-005
- **Active, extension pending:** ADR-002 (HMM chosen; BOCPD + 4-dimension extension to be recorded in Slice 3)
- **Superseded:** `_superseded/engine-design-v1.md` — the old v1 paradigm, kept for provenance only. Do not build from it.

## Governance rule
No engine component changes without reading its ADR first. Proposing a change not covered by an ADR → write a new ADR and get Syafiq's approval before coding. (Full protocol: `ENGINE_BLUEPRINT.md` §6.)

## Folder map
```
architecture/
├── README.md                  ← you are here
├── ENGINE_BLUEPRINT.md        ← authoritative design (read first)
├── ADR-001..005.md            ← locked decisions
├── engine-architecture/       ← canonical architecture, in depth
├── engine-diagram/            ← SVG diagrams
└── _superseded/               ← old designs, provenance only — do not build from
```
