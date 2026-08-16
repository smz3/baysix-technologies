"""outputs — the ONE place a results folder is named (task 349).

THE RULE
    research/outputs/<idea_id>/<run_id>/
Nothing else creates a folder under `outputs/`. Ask this module for a path; do not
build one with a string.

WHY THE RULE EXISTS (MEASURED 2026-08-16)
There was never a convention, so every screen script hardcoded its own output path and
whatever folder name its author picked became permanent. `research/outputs/` ended up
with 6 stray top-level `fob_*` folders plus 4 loose files sitting beside the real one —
13 files, none touched since 2026-07-10, and no way to tell which run produced which.
Those files were deleted 2026-08-16; this module is what stops the folder refilling.

WHY IT IS RULE-FIRST AND NOT A ONE-OFF TIDY
The autonomous loop is the thing that will create thousands of these. Moving folders
without fixing the naming just resets the clock, and the loop invents new names on its
next pass. So the convention lands BEFORE the loop ships, not after.

THE OTHER HALF
`run_id` is the primary key of the `runs` table (task 356, migration 042). The folder
name and the registry row are one answer to "what is this folder": the path says which
run, the row says what that run was. Store the path you get back on
`runs.output_dir` so the link is readable from either end.

EXPLORATORY WORK
`idea_id` is optional on a run, because not every backtest serves a registered
falsifiable idea. Those land under `_exploratory/` rather than being allowed to
scatter at the top level — visible as unfiled, still inside the convention.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OUTPUTS_ROOT = REPO / "research" / "outputs"
UNFILED = "_exploratory"

_SAFE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _check(part: str, label: str) -> str:
    """Reject anything that would climb out of OUTPUTS_ROOT or need quoting."""
    part = str(part).strip()
    if not part:
        raise ValueError(f"{label} cannot be empty")
    if not _SAFE.match(part):
        raise ValueError(
            f"{label}={part!r} is not a safe path segment "
            "(letters, digits, dot, dash, underscore; must not start with a separator)"
        )
    return part


def run_dir(run_id: int | str, idea_id: str | None = None,
            create: bool = True) -> Path:
    """The folder for one run. Creates it unless create=False.

    >>> run_dir(42, "FOB-001")
    .../research/outputs/FOB-001/run_42/
    """
    bucket = _check(idea_id, "idea_id") if idea_id else UNFILED
    run = str(run_id)
    run = _check(run if run.startswith("run_") else f"run_{run}", "run_id")
    path = OUTPUTS_ROOT / bucket / run
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


def rel(path: Path) -> str:
    """Repo-relative string form — what belongs in `runs.output_dir`."""
    return path.resolve().relative_to(REPO).as_posix()


def strays() -> list[Path]:
    """Anything under outputs/ that breaks the rule. Empty list = clean.

    A file at the root, or a folder whose children are not `run_*`, was written by
    something that bypassed this module.
    """
    if not OUTPUTS_ROOT.exists():
        return []
    out = []
    for child in OUTPUTS_ROOT.iterdir():
        if child.is_file():
            out.append(child)
            continue
        for grand in child.iterdir():
            if not grand.name.startswith("run_"):
                out.append(grand)
    return out
