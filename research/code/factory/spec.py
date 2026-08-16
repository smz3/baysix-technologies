"""StrategySpec — the unit of work, and the reason this factory is portable.

A strategy here is a JSON document, not a source file. The four axes mirror the
MT5 meta-EA that already works (entry / filters / exit / risk), lifted one level so
they are language-agnostic:

    Python oracle   the spec dispatches over modules — no codegen at all
    NinjaTrader 8   one meta-strategy carries the axes as enum inputs, compiled
                    ONCE, and parameter mutation travels through a template XML

That split is what keeps the loop safe. Compile is the fragile seam on every
platform, and under this design it fires only when a genuinely new primitive is
added — not on every candidate.

## `mechanism` is mandatory, and it is not documentation

Every spec must state, in one falsifiable sentence, why the edge should exist. A
candidate with no mechanism is a lottery ticket, and lottery tickets do not get a
slot in a batch. This is what keeps a small pre-registered batch honest once a
human stops supplying the hypotheses: it makes a failure *informative* rather than
merely disappointing.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

__all__ = ["StrategySpec", "SpecError", "ENTRY_TYPES", "EXIT_TYPES", "FILTERS", "RISK_MODES"]


class SpecError(ValueError):
    """A spec that cannot be trusted to mean the same thing on two engines."""


#: The primitive vocabulary. A spec may only name something in these sets, because
#: an unknown primitive is silently skipped by one engine and honoured by the other
#: — which produces two different strategies wearing the same config hash.
ENTRY_TYPES = frozenset({
    "DONCHIAN_BREAK",     # close beyond the N-bar extreme
    "BREAK_RETEST",       # break, then first retouch of the broken level
    "ATR_REVERSION",      # fade at >= k ATRs from an anchor
    "SESSION_RANGE_BREAK",  # break of the prior session's range
    "MOMENTUM_SLOPE",     # sign of an N-bar regression slope
})

EXIT_TYPES = frozenset({
    "FIXED_RR",           # take profit at RR * risk
    "TRAIL_ATR",          # arm at R, then trail k ATRs
    "BREAK_EVEN_TRAIL",   # move to break-even at R, then trail
    "TIME_STOP",          # close after N signal-timeframe bars
    "SESSION_FLAT",       # close at session end, no overnight
})

FILTERS = frozenset({
    "SESSION_RTH",        # regular trading hours only
    "SESSION_GLOBEX",     # overnight session only
    "VOL_FLOOR",          # ATR at or above a minimum
    "VOL_CEILING",        # ATR at or below a maximum
    "COST_RATIO",         # stop must be >= k round-trip costs
    "TREND_HTF",          # higher-timeframe direction agrees
    "NO_ROLLOVER",        # sit out the contract roll window
    "NO_HIGH_IMPACT_NEWS",
})

RISK_MODES = frozenset({
    "CONTRACTS_FIXED",    # always n contracts
    "RISK_FRAC",          # fraction of equity per trade
    "RISK_FIXED_USD",     # constant dollar risk per trade
})

_TF = re.compile(r"^(M1|M3|M5|M15|M30|H1|H2|H4|D1)$")
_SPEC_VERSION = "1.0.0"


@dataclass(frozen=True)
class StrategySpec:
    family: str
    instrument: str
    signal_tf: str
    entry: dict[str, Any]
    exit: dict[str, Any]
    risk: dict[str, Any]
    mechanism: str
    filters: tuple[str, ...] = ()
    spec_version: str = _SPEC_VERSION
    notes: str = ""

    def __post_init__(self) -> None:
        self.validate()

    # -- validation --------------------------------------------------------- #

    def validate(self) -> None:
        if not _TF.match(self.signal_tf):
            raise SpecError(
                f"signal_tf {self.signal_tf!r} is not one of the supported "
                f"timeframes; an engine that silently reinterprets it produces a "
                f"different strategy under the same hash"
            )

        etype = self.entry.get("type")
        if etype not in ENTRY_TYPES:
            raise SpecError(f"unknown entry type {etype!r}; expected one of {sorted(ENTRY_TYPES)}")

        xtype = self.exit.get("type")
        if xtype not in EXIT_TYPES:
            raise SpecError(f"unknown exit type {xtype!r}; expected one of {sorted(EXIT_TYPES)}")

        rmode = self.risk.get("mode")
        if rmode not in RISK_MODES:
            raise SpecError(f"unknown risk mode {rmode!r}; expected one of {sorted(RISK_MODES)}")

        unknown = set(self.filters) - FILTERS
        if unknown:
            raise SpecError(f"unknown filters {sorted(unknown)}; expected from {sorted(FILTERS)}")

        if len(set(self.filters)) != len(self.filters):
            raise SpecError(
                f"duplicate filters in {self.filters}; the filter set is a SET and a "
                f"repeat changes the config hash without changing the strategy"
            )

        self._validate_mechanism()

    def _validate_mechanism(self) -> None:
        text = (self.mechanism or "").strip()
        if len(text) < 25:
            raise SpecError(
                "mechanism is missing or too short. State in one falsifiable "
                "sentence why this edge should exist — a candidate with no stated "
                "reason is a lottery ticket and does not get a slot in a batch."
            )
        lazy = ("it works", "backtest", "optimis", "optimiz", "curve fit", "tbd", "n/a")
        low = text.lower()
        if any(w in low for w in lazy):
            raise SpecError(
                f"mechanism {text!r} describes evidence or search, not a mechanism. "
                f"Name the market behaviour — who is trading, and why that leaves a "
                f"repeatable footprint."
            )

    # -- identity ----------------------------------------------------------- #

    def canonical(self) -> dict[str, Any]:
        """The subset that DEFINES the strategy. Prose is excluded on purpose.

        `mechanism` and `notes` are required and are not part of the identity:
        rewording the explanation must not mint a new config, and two specs that
        differ only in wording must collide so the trial counter stays honest.
        """
        body = asdict(self)
        body.pop("mechanism", None)
        body.pop("notes", None)
        body["filters"] = sorted(self.filters)
        return body

    @property
    def config_hash(self) -> str:
        blob = json.dumps(self.canonical(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(blob.encode()).hexdigest()[:16]

    # -- io ----------------------------------------------------------------- #

    def to_json(self) -> str:
        payload = asdict(self)
        payload["filters"] = sorted(self.filters)
        payload["config_hash"] = self.config_hash
        return json.dumps(payload, indent=2, sort_keys=True)

    def write(self, path: str | Path) -> Path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(self.to_json(), encoding="utf-8")
        return p

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "StrategySpec":
        data = dict(payload)
        stored = data.pop("config_hash", None)
        data["filters"] = tuple(data.get("filters", ()))
        spec = cls(**data)
        if stored is not None and stored != spec.config_hash:
            raise SpecError(
                f"config_hash mismatch: file says {stored}, recomputes to "
                f"{spec.config_hash}. The spec was hand-edited after it was written, "
                f"which breaks the link between a result and the strategy that made it."
            )
        return spec

    @classmethod
    def load(cls, path: str | Path) -> "StrategySpec":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))
