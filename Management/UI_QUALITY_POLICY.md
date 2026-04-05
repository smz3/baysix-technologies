# Baysix UI Quality Policy: The "Stitch Standard"

**Target**: All AI Agents (Antigravity, Claude, Gemini).
**Goal**: Zero "AI UI Slop." Every component must look institutional-grade and follow strict architectural constraints.

---

## 1. The Design-First Mandate
Before writing a single line of React code, the agent **MUST**:
1.  Generate a high-fidelity mockup in **Google Stitch**.
2.  Export the `DESIGN.md` using the `design-md` skill.
3.  Adopt the exported theme tokens (colors, typography, spacing).

**NEVER**: Generate UI from a plain text prompt without a Stitch-validated design system.

---

## 2. Forbidden "Slop" Patterns
The following patterns are strictly prohibited in the Baysix repository:
*   **Hex Code Proliferation**: No `#RRGGBB` in component files. Use Tailwind theme mapping (e.g. `bg-surface-primary`).
*   **In-File Logic**: Business logic or complex event handlers inside the `.tsx` file. Use `src/hooks`.
*   **Data Hardcoding**: Hardcoded display strings or lists. Use `src/data/mockData.ts` or an API service.
*   **Single-File Monoliths**: Components exceeding 150 lines. Split into atomic sub-components.
*   **Loose Types**: Using `any` or missing Prop interfaces.

---

## 3. The Gold Standard Checklist
Before submitting a component for review, verify:
- [ ] **Modularity**: Is this component atomic? (e.g. `RiskCard`, `PValueMetric`).
- [ ] **Type Safety**: Does it have a `Readonly<[Name]Props>` interface?
- [ ] **Aesthetics**: Does it use the institutional font pairing (Inter + JetBrains Mono) and the agreed color palette?
- [ ] **Performance**: Are expensive calculations memoized? Are images using WebP/AVIF?

---

## 4. Enforcement
The `ui-reviewer` gate will reject any code that deviates from these 4 pillars. Repeated "slop" offenses will trigger a temporary lockout of the agent from the frontend directories until the `UI_QUALITY_POLICY.md` is re-read.

> [!TIP]
> ** Institutional Vibe**: Think "Bloomberg Terminal" meeting "Modern Fintech." High density, high precision, low fluff.
