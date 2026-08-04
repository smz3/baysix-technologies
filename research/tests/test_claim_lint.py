"""claim_lint (task 291) — the regression suite is this session's actual errors.

Every HARD case below is a real thing that shipped to Syafiq on 2026-08-04.
If one of these ever passes the linter again, the guard has regressed.
"""
import importlib.util
import json
import subprocess
import uuid
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / ".claude" / "hooks" / "scripts" / "claim_lint.py"

_spec = importlib.util.spec_from_file_location("claim_lint", SCRIPT)
claim_lint = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(claim_lint)


def _run(msg, event="Stop", session="pytest"):
    p = subprocess.run(
        [sys.executable, "-X", "utf8", str(SCRIPT)],
        input=json.dumps({
            "hook_event_name": event,
            "session_id": session,
            "last_assistant_message": msg,
        }),
        capture_output=True, text=True,
    )
    return p.returncode, p.stdout + p.stderr


# --------------------------------------------------------------- HARD blocks

def test_tstat_without_effective_n_blocks():
    """The 2026-08-04 error: t=+8.02 off 44,212 overlapping samples."""
    hard, _ = claim_lint.lint(
        "RR=1 at S=100 is the only clean config. p_long = 0.5191, "
        "t = +8.02, n=44,212 random entries, median resolve 14.4 hours."
    )
    assert any(h.startswith("STAT_NO_N") for h in hard)


def test_tstat_with_effective_n_passes():
    hard, _ = claim_lint.lint(
        "p_long = 0.5191, t = +8.02 on raw n=44,212 — but trades overlap ~14x, "
        "so effective n is ~3,070 and the honest t is +2.1. MEASURED, result_id 69."
    )
    assert hard == []


def test_naming_a_statistic_without_a_value_does_not_block():
    """FP found by the guard blocking a handover reply: a bare '\\bt-stat\\b' fired
    on prose that only DISCUSSED the concept. The check is about reporting a value."""
    hard, _ = claim_lint.lint(
        "A cold session reading the results table gets the corrected t-stat, not "
        "the inflated one, which is the whole point of writing the correction down."
    )
    assert hard == []


def test_reported_tstat_value_still_blocks():
    for txt in ("The t-stat of 3.4 settles it and there is nothing further to add here.",
                "We measured t-stat = +8.02 across the window, which looked conclusive.",
                "The z = 7.19 figure was the one quoted throughout the whole review."):
        hard, _ = claim_lint.lint(txt)
        assert any(h.startswith("STAT_NO_N") for h in hard), txt


def test_dead_markdown_path_blocks():
    hard, _ = claim_lint.lint(
        "The full spec lives in [the plan](docs/reference/does_not_exist_xyz.md) "
        "and it explains the whole mechanism in detail."
    )
    assert any(h.startswith("DEAD_PATH") for h in hard)


def test_live_markdown_path_passes():
    hard, _ = claim_lint.lint(
        "I read [justmarkets.yaml](brokers/justmarkets.yaml) and confirmed the "
        "active Pro margin figure is the observed one, not the reference block."
    )
    assert not any(h.startswith("DEAD_PATH") for h in hard)


def test_dotdot_and_dotfile_paths_resolve():
    """FP found by the linter blocking its own spec edit: lstrip('./') ate the
    dot in '.claude', reporting a live path as dead."""
    hard, _ = claim_lint.lint(
        "The guard is [claim_lint.py](../../.claude/hooks/scripts/claim_lint.py) "
        "with its suite at [tests](../../research/tests/test_claim_lint.py) on disk."
    )
    assert hard == []


def test_bad_schema_column_blocks():
    """The 2026-08-03 error: asserting columns that do not exist."""
    if not claim_lint._tables():
        pytest.skip("research.db not available")
    hard, _ = claim_lint.lint(
        "The provenance travels on tester_runs.made_up_column_xyz for every row "
        "written by the ingest path, so the venue is always recoverable."
    )
    assert any(h.startswith("BAD_SCHEMA") for h in hard)


def test_real_schema_column_passes():
    if not claim_lint._tables():
        pytest.skip("research.db not available")
    hard, _ = claim_lint.lint(
        "The metric lands in step4_results.metric_value once the gate is open, "
        "and the run provenance sits alongside it for later forensics."
    )
    assert not any(h.startswith("BAD_SCHEMA") for h in hard)


# --------------------------------------------------------------- WARN surface

def test_attribution_warns():
    """The 2026-08-04 error: crediting Syafiq with a stop size he never gave."""
    _, warn = claim_lint.lint(
        "Your half-pot instinct: half right. The 100-pip stop is correct "
        "because it is the 2 percent rake corner of the feasible set."
    )
    assert any(w.startswith("ATTRIBUTION") for w in warn)


def test_unadjudicated_decision_warns():
    _, warn = claim_lint.lint(
        "The config is decided: target 80 dollars, floor 2.50, RR=1, flat min "
        "lot throughout. That is the answer and it is what we will build on."
    )
    assert any(w.startswith("UNADJUDICATED") for w in warn)


def test_decision_with_tester_citation_does_not_warn():
    _, warn = claim_lint.lint(
        "The config is decided on the back of the MT5 tester run: real ticks, "
        "run_id 42, net of cost. That is the arbiter and it has now spoken."
    )
    assert not any(w.startswith("UNADJUDICATED") for w in warn)


def test_absolute_without_provenance_warns():
    _, warn = claim_lint.lint(
        "No strategy survives at this account size, and the spread makes it "
        "impossible to trade profitably at any horizon we might consider."
    )
    assert any(w.startswith("ABSOLUTE") for w in warn)


# --------------------------------------------------------------- plumbing

def test_short_and_empty_messages_pass():
    assert claim_lint.lint("") == ([], [])
    assert claim_lint.lint("Done.") == ([], [])


def test_stop_event_blocks_with_exit_2():
    # unique session id per run: the loop-guard counter persists on disk, so a
    # fixed id trips the MAX_BLOCKS pass-through on the third pytest run.
    code, out = _run("p = 0.5191 and t = +8.02 across the whole in-sample window here.",
                     session=f"exit2test-{uuid.uuid4()}")
    assert code == 2
    assert "claim_lint" in out


def test_loop_guard_stops_blocking_after_max_attempts():
    """A guard that can hang the session is worse than no guard."""
    sid = f"loopguard-{uuid.uuid4()}"
    msg = "p = 0.5191 and t = +8.02 across the whole in-sample window here."
    codes = [_run(msg, session=sid)[0] for _ in range(claim_lint.MAX_BLOCKS + 1)]
    assert codes[:claim_lint.MAX_BLOCKS] == [2] * claim_lint.MAX_BLOCKS
    assert codes[-1] == 0


def test_clean_message_exits_zero():
    code, _ = _run(
        "I read [justmarkets.yaml](brokers/justmarkets.yaml); the active Pro "
        "margin is the observed per-lot figure. CITED, no statistics claimed."
    )
    assert code == 0


def test_pretooluse_blocks_dead_path_in_markdown_write():
    p = subprocess.run(
        [sys.executable, "-X", "utf8", str(SCRIPT)],
        input=json.dumps({
            "hook_event_name": "PreToolUse",
            "session_id": "pytest",
            "tool_name": "Write",
            "tool_input": {
                "file_path": str(REPO / "memory" / "fake_handover.md"),
                "content": "Next step is in [the plan](docs/plans/not_a_real_file_xyz.md) "
                           "which carries the full sequence and the rationale.",
            },
        }),
        capture_output=True, text=True,
    )
    assert p.returncode == 2
    assert "DEAD_PATH" in p.stdout


def test_pretooluse_skips_stat_check():
    """Prose statistics are a Stop concern; a doc full of numbers is not blocked."""
    p = subprocess.run(
        [sys.executable, "-X", "utf8", str(SCRIPT)],
        input=json.dumps({
            "hook_event_name": "PreToolUse",
            "session_id": "pytest",
            "tool_name": "Write",
            "tool_input": {
                "file_path": str(REPO / "docs" / "scratch.md"),
                "content": "The measured value was t = +8.02 across the sample window, "
                           "recorded here for the record and for later reference.",
            },
        }),
        capture_output=True, text=True,
    )
    assert p.returncode == 0


def test_env_escape_hatch(monkeypatch):
    p = subprocess.run(
        [sys.executable, "-X", "utf8", str(SCRIPT)],
        input=json.dumps({
            "hook_event_name": "Stop",
            "session_id": "pytest-off",
            "last_assistant_message": "t = +8.02 with no effective n anywhere in this message.",
        }),
        capture_output=True, text=True,
        env={**__import__("os").environ, "CLAIM_LINT": "off"},
    )
    assert p.returncode == 0


def test_statistic_inside_code_span_is_mentioned_not_asserted():
    """FP found by the guard blocking a reply that quoted its own test fixture."""
    hard, _ = claim_lint.lint(
        "The pattern is `t-stat of 3.4` and the fence below shows the fixture, "
        "neither of which asserts anything at all about the actual market.\n"
        "```\nt = +8.02\n```\n"
    )
    assert hard == []


def test_statistic_in_plain_prose_still_blocks_alongside_code_spans():
    hard, _ = claim_lint.lint(
        "The pattern is `t-stat of 3.4`, but the measurement itself gave "
        "t = +8.02 across the whole in-sample window and that settles it."
    )
    assert any(h.startswith("STAT_NO_N") for h in hard)


def test_schema_in_code_span_still_checked():
    if not claim_lint._tables():
        pytest.skip("research.db not available")
    hard, _ = claim_lint.lint(
        "Provenance travels on `tester_runs.made_up_column_xyz` for every row "
        "the ingest path writes, so the venue is always recoverable later."
    )
    assert any(h.startswith("BAD_SCHEMA") for h in hard)
