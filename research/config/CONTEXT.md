# research/config/ — versioned objectives (the factory's frozen recipe)

One job: hold the one declared objective per system, version-bumped on change, never
silently edited. Every autonomous loop reads this folder every run and writes to it
never.

## Inputs
- Working: none — this folder is read-only reference for every pass a loop runs.
- Reference: `docs/private/mandate.md` (gitignored) — the account-size/target context
  behind `grw_fitness.json`'s parameters.

## Process
1. A parameter inside the objective file (e.g. `stake_usd` / `target_mult` /
   `floor_frac` in `grw_fitness.json`) is part of the objective, not a tuning knob —
   changing one bumps the version and starts a new trial family, per that file's own
   `change_policy`.
2. `implemented_by` names the exact `.mqh` / `.py` file that reads this file at run
   time — check that pointer still resolves before trusting either side.
3. Passes scored under a superseded version are never pooled with passes under the
   current one; `parked_objective` (where present) records why it was parked and what
   would revive it.

## Outputs
- None. This folder is read by the platform code named in `implemented_by`; it never
  writes anything itself.

## Human check
Before bumping a version, query the passes table this objective feeds (e.g.
`grw_passes`) for the current row count and cite it in the changelog entry — never
estimate it. Editing this file is never automated; a human writes the changelog entry
by hand.
