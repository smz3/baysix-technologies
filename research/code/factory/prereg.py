"""Pre-registration — the rule that decides promotion is written BEFORE the run.

The failure this prevents is specific and it is not hypothetical: rank enough
configurations by any noisy metric and the top of the distribution is the luckiest
one, not the best one. Run that unattended and the false winner gets logged as a
result and becomes the next cycle's foundation.

The fix is not better statistics afterwards. It is deciding the bar in advance and
being unable to move it:

*   `register()` writes `prereg.json`, hashes it, and **refuses to overwrite** one
    that already exists. Changing a threshold opens a NEW batch with a new id. The
    old batch stays on the record, including its failure — that is what keeps the
    trial count honest.

*   Every judged candidate carries the `prereg_sha` it was judged against, so a
    verdict reached under a moved goalpost is self-evident from the row alone.

*   `load()` re-hashes on read and raises on mismatch. A hand-edited prereg is not
    a prereg.

*   **The holdout window is never handed to the search.** Not as a filter, not as
    a sanity check, not "just to look". Looking is spending it, so `oos_spent`
    latches to true and never returns.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from research.code.factory.adjudicate import ADJUDICATION_VARS, RuleError, _names_in

__all__ = ["Prereg", "PreregError", "register", "load", "prereg_sha"]


class PreregError(RuntimeError):
    pass


#: Fields a prereg MUST declare before a single candidate may run. `mechanism` is
#: here on purpose: a batch with no stated reason the edge should exist is a
#: lottery ticket, and lottery tickets do not get a slot.
REQUIRED = (
    "batch_id", "family", "instrument", "hypothesis", "mechanism",
    "objective_ref", "is_window", "oos_window", "n_trials_budget", "promote_if",
)


def prereg_sha(payload: dict[str, Any]) -> str:
    """sha256 of the prereg with the sha field removed, canonically serialised.

    Deterministic across dict ordering and whitespace, so the hash tracks MEANING
    rather than formatting.
    """
    body = {k: v for k, v in payload.items() if k != "prereg_sha"}
    blob = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()


def _git(repo: Path) -> tuple[str | None, int | None]:
    """(short_sha, dirty). A DIRTY tree means the batch is exploratory and its
    numbers cannot be cited as evidence — so the flag travels with the row."""
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=repo,
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        dirty = bool(subprocess.run(
            ["git", "status", "--porcelain"], cwd=repo,
            capture_output=True, text=True, check=True,
        ).stdout.strip())
        return sha, int(dirty)
    except Exception:
        return None, None


def _as_date(v: Any, label: str) -> date:
    if isinstance(v, date) and not isinstance(v, datetime):
        return v
    if isinstance(v, datetime):
        return v.date()
    try:
        return date.fromisoformat(str(v))
    except ValueError as exc:
        raise PreregError(f"{label} must be YYYY-MM-DD, got {v!r}") from exc


@dataclass(frozen=True)
class Prereg:
    payload: dict[str, Any]
    path: Path

    @property
    def batch_id(self) -> str:
        return self.payload["batch_id"]

    @property
    def sha(self) -> str:
        return self.payload["prereg_sha"]

    @property
    def promote_if(self) -> str:
        return self.payload["promote_if"]

    @property
    def kill_if(self) -> str | None:
        return self.payload.get("kill_if")

    @property
    def is_window(self) -> tuple[date, date]:
        a, b = self.payload["is_window"]
        return _as_date(a, "is_window[0]"), _as_date(b, "is_window[1]")

    @property
    def oos_window(self) -> tuple[date, date]:
        a, b = self.payload["oos_window"]
        return _as_date(a, "oos_window[0]"), _as_date(b, "oos_window[1]")

    @property
    def n_trials_budget(self) -> int:
        return int(self.payload["n_trials_budget"])

    def verify(self) -> None:
        recomputed = prereg_sha(self.payload)
        if recomputed != self.payload.get("prereg_sha"):
            raise PreregError(
                f"{self.path} has been edited since registration: stored sha "
                f"{self.payload.get('prereg_sha')}, recomputes to {recomputed}. A "
                f"hand-edited pre-registration is not a pre-registration. Register a "
                f"new batch instead."
            )


def _validate(payload: dict[str, Any]) -> None:
    missing = [k for k in REQUIRED if not payload.get(k)]
    if missing:
        raise PreregError(f"prereg is missing required fields: {', '.join(missing)}")

    for key in ("is_window", "oos_window"):
        w = payload[key]
        if not (isinstance(w, (list, tuple)) and len(w) == 2):
            raise PreregError(f"{key} must be [start, end] as YYYY-MM-DD")

    is_a, is_b = (_as_date(v, "is_window") for v in payload["is_window"])
    oos_a, oos_b = (_as_date(v, "oos_window") for v in payload["oos_window"])

    if is_b >= is_a and is_b > oos_a:
        raise PreregError(
            f"IS window ends {is_b} AFTER OOS starts {oos_a} — overlapping windows "
            f"make the holdout worthless, because the search has already seen the "
            f"data it is supposed to be tested on"
        )
    if is_b <= is_a:
        raise PreregError(f"is_window ends before it starts: {is_a} -> {is_b}")
    if oos_b <= oos_a:
        raise PreregError(f"oos_window ends before it starts: {oos_a} -> {oos_b}")

    if int(payload["n_trials_budget"]) < 1:
        raise PreregError("n_trials_budget must be at least 1")

    if len(str(payload["mechanism"]).strip()) < 25:
        raise PreregError(
            "mechanism is required and must be a real sentence: WHY should this edge "
            "exist? A batch with no mechanism is a lottery ticket."
        )

    # The rules must be parseable and must only reference declared variables. Catch
    # it here, at registration — not hours later when results are waiting.
    for label in ("promote_if", "kill_if"):
        rule = payload.get(label)
        if not rule:
            continue
        try:
            unknown = _names_in(rule) - set(ADJUDICATION_VARS)
        except SyntaxError as exc:
            raise PreregError(f"{label} does not parse: {rule!r} ({exc})") from exc
        if unknown:
            raise PreregError(
                f"{label} references undeclared variables {sorted(unknown)}. "
                f"Allowed: {', '.join(ADJUDICATION_VARS)}"
            )

    # A promote rule that never reads the holdout is not a holdout test.
    if not any(n.startswith("oos_") for n in _names_in(payload["promote_if"])):
        raise PreregError(
            f"promote_if {payload['promote_if']!r} never references an oos_ variable. "
            f"A promotion rule decided entirely in-sample is a ranking, not a test."
        )


def register(
    runs_dir: str | Path,
    *,
    batch_id: str,
    family: str,
    instrument: str,
    hypothesis: str,
    mechanism: str,
    objective_ref: str,
    is_window: Sequence[Any],
    oos_window: Sequence[Any],
    n_trials_budget: int,
    promote_if: str,
    kill_if: str | None = None,
    venue_search: str = "pyoracle",
    venue_arbiter: str | None = "nt8",
    notes: str = "",
    repo: str | Path | None = None,
) -> Prereg:
    """Freeze a batch before it runs. Returns the Prereg; refuses to overwrite.

    `objective_ref` must name the objective file AND its fingerprint, e.g.
    `barrier_prop_topstep50k_v1.0.0.json@<fingerprint>`. A result that cannot say
    which question it answered is not a result.
    """
    root = Path(runs_dir) / batch_id
    target = root / "prereg.json"
    if target.exists():
        raise PreregError(
            f"{target} already exists and pre-registrations are immutable. To change "
            f"a threshold, register a NEW batch_id — the old batch stays on the "
            f"record, including its failure, which is what keeps the trial count "
            f"honest."
        )

    sha, dirty = _git(Path(repo) if repo else root.parents[1])

    payload: dict[str, Any] = {
        "batch_id": batch_id,
        "family": family,
        "instrument": instrument,
        "hypothesis": hypothesis,
        "mechanism": mechanism,
        "objective_ref": objective_ref,
        "is_window": [str(_as_date(is_window[0], "is_window[0]")),
                      str(_as_date(is_window[1], "is_window[1]"))],
        "oos_window": [str(_as_date(oos_window[0], "oos_window[0]")),
                       str(_as_date(oos_window[1], "oos_window[1]"))],
        "n_trials_budget": int(n_trials_budget),
        "promote_if": promote_if,
        "kill_if": kill_if,
        "venue_search": venue_search,
        "venue_arbiter": venue_arbiter,
        "notes": notes,
        "registered_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_sha": sha,
        "git_dirty": dirty,
        "oos_spent": False,
    }

    _validate(payload)
    payload["prereg_sha"] = prereg_sha(payload)

    root.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return Prereg(payload, target)


def load(path: str | Path) -> Prereg:
    """Read a prereg and re-hash it. Raises if it was edited after registration."""
    p = Path(path)
    if p.is_dir():
        p = p / "prereg.json"
    if not p.exists():
        raise PreregError(f"no pre-registration at {p} — a batch cannot run without one")
    pre = Prereg(json.loads(p.read_text(encoding="utf-8")), p)
    pre.verify()
    return pre
