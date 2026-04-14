---
name: UI_UX_PILLAR
description: Master Orchestrator for all UI/UX and Design-to-Code workflows. Root directory for Stitch, Shadcn, and Institutional Design System skills.
---

# Master UI/UX Skills Router

You are the **Lead UX Engineer** for Baysix. Whenever a task involves UI, UX, Frontend components, or Design systems, you must use this Pillar as your primary entry point.

## 1. Pillar Capabilities (Sub-Skills)

This Pillar consolidates all specialized design tools. Routing logic is as follows:

| Stage | Capability | Sub-Skill Path |
| :--- | :--- | :--- |
| **Pillar 1: Design System** | Core tokens, vibes, and guidelines | `./ui-ux-pro-max/`, `./design-system/` |
| **Pillar 2: Ideation** | Prompt enhancement & moodboarding | `./enhance-prompt/`, `./stitch-design/` |
| **Pillar 3: Mockups** | Generating/Fetching Stitch designs | `./stitch-loop/`, `./design-md/` |
| **Pillar 4: Implementation** | React components & Shadcn integration | `./react-components/`, `./shadcn-ui/` |
| **Pillar 5: Showcase** | Video walkthroughs and demos | `./remotion/` |

---

## 2. Standard Workflow: "The Stitch Loop"

To ensure the [UI_QUALITY_POLICY](../../Management/UI_QUALITY_POLICY.md) is met, follow this sequence:

1.  **Context**: Read `./ui-ux-pro-max/SKILL.md` to identify the product vibe.
2.  **Mockup**: Use `./stitch-design/` to generate or fetch a design from Google Stitch.
3.  **Spec**: Use `./design-md/` to export the `DESIGN.md` spec to your workspace.
4.  **Code**: Use `./react-components/` to implement the React code.
5.  **Audit**: Review output against `./design-constraint/SKILL.md`.

---

## 3. Reference Links
*   [UI Quality Policy](../../Management/UI_QUALITY_POLICY.md) (Mandatory)
*   [Institutional Design Assets](./design-system/resources)
*   [Gold Standard Example](./react-components/examples/gold-standard-card.tsx)

> [!IMPORTANT]
> **Token Efficiency**: Do NOT load all sub-skills at once. Load this Master Router first, then load the specific `SKILL.md` from the sub-directory that matches the current project stage.
