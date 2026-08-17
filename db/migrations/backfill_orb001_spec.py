"""
Backfill — attach params_json knobs to ORB-001's live-config rows (task 57).

ORB-001 predates the spec workflow, so its component rows carried a value
(e.g. exit="trail_1R") but no structured knobs. This is the worked example for
get_spec(): we annotate the four live rows (the design that was ultimately
falsified on sorted ticks) with the knobs that defined them. Strategy-level death
lives in the config rows / lineage — the spec card is the component design surface.

Idempotent: set_params is an UPDATE keyed by log_id; re-running just rewrites the
same JSON. Run: python db/migrations/backfill_orb001_spec.py
"""
from core import strategy_log as sl

# log_id -> knobs (pure component params; component itself is already a column).
# Sourced from get_live_config('ORB-001') + the ORB-001 memory notes.
SPEC = {
    11: {  # anchor  09:00/N5
        "session_open": "09:00",
        "range_minutes": 5,
        "tz": "broker_server",
        "note": "London-session opening range; switched 08:00->09:00/N5 (strategy_log #11)",
    },
    9: {   # exit  trail_1R
        "type": "trailing_stop",
        "trail_distance_R": 1.0,
        "initial_stop": "OR_opposite_boundary",
        "target": "trail_only_no_fixed_tp",
    },
    4: {   # sizing  ModeA_minlot_5pct
        "mode": "A_fixed_fractional",
        "risk_pct": 5.0,
        "min_lot": 0.01,
        "compounding": False,
        "account_usd": 50,
    },
    5: {   # entry  immediate_breakout
        "trigger": "first_touch_of_OR_boundary",
        "confirm": False,
        "delay_bars": 0,
    },
}


def main():
    for log_id, knobs in SPEC.items():
        sl.set_params(log_id, knobs)
    print("\n=== get_spec('ORB-001') after backfill ===")
    for comp, card in sl.get_spec("ORB-001").items():
        p = card["params"]
        keys = list(p) if p else "—"
        print(f"  {comp:8} {card['status']:8} {card['value']:20} "
              f"dead={card['dead_variants']}  params={keys}")


if __name__ == "__main__":
    main()
