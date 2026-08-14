"""Claim provenance — every number this factory reports declares where it came from.

Ported deliberately from the baysix-technologies research protocol (Loop A). The
origin failure is on record there: an audit of one planning session found four
substantive errors in six turns, zero self-caught, and three of them were asserted
from memory. The one that WAS caught got caught only because a query was run
instead of recalled.

That is the entire mechanism. Recall produces errors; execution catches them.

    MEASURED  output of a command run this session          -> cite the command
    DERIVED   arithmetic over MEASURED values               -> cite the formula
    CITED     read from a file or URL this session          -> cite path or URL
    ASSUMED   not verified, stated deliberately             -> cite what would falsify it
    RECALLED  from memory / habit / another project         -> BANNED

`RECALLED` is not a class you may pass. It exists in this file only as a named
rejection, so that `Provenance("RECALLED")` fails loudly rather than being spelled
some other way and slipping through.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


class Provenance(enum.Enum):
    MEASURED = "MEASURED"
    DERIVED = "DERIVED"
    CITED = "CITED"
    ASSUMED = "ASSUMED"

    @classmethod
    def _missing_(cls, value: object) -> None:
        if isinstance(value, str) and value.upper() == "RECALLED":
            raise ValueError(
                "RECALLED is a banned provenance class. If the number came from "
                "memory, it is not evidence: run the command (MEASURED), compute it "
                "(DERIVED), read the source (CITED), or state it as ASSUMED with "
                "what would falsify it."
            )
        raise ValueError(
            f"unknown provenance {value!r}; expected one of "
            f"{[m.value for m in cls]}"
        )


#: Provenance classes that require an explicit falsifier rather than a citation.
_NEEDS_FALSIFIER = frozenset({Provenance.ASSUMED})


@dataclass(frozen=True)
class Claim:
    """A single reportable number, inseparable from its provenance.

    The point of making this a type rather than a convention: a bare float can be
    passed into a promotion decision without anyone noticing it was never measured.
    A `Claim` cannot be constructed without answering the question.
    """

    name: str
    value: Any
    provenance: Provenance
    #: The command, formula, path or URL that backs the value. For ASSUMED, this
    #: field holds what would falsify the assumption instead.
    source: str
    unit: str | None = None
    at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("a claim must be named")
        if not self.source or not self.source.strip():
            what = (
                "what would falsify it"
                if self.provenance in _NEEDS_FALSIFIER
                else "the command, formula, path or URL that backs it"
            )
            raise ValueError(
                f"claim {self.name!r} is {self.provenance.value} but declares no "
                f"source; state {what}"
            )

    @property
    def is_evidence(self) -> bool:
        """True when the claim may be fed into a promotion decision.

        ASSUMED values are legitimate to state and illegitimate to promote on.
        That distinction is the whole reason the class exists.
        """
        return self.provenance is not Provenance.ASSUMED

    def cite(self) -> str:
        unit = f" {self.unit}" if self.unit else ""
        verb = "falsified by" if self.provenance in _NEEDS_FALSIFIER else "source"
        return (
            f"{self.name} = {self.value}{unit} "
            f"[{self.provenance.value}; {verb}: {self.source}]"
        )

    def to_row(self) -> dict[str, Any]:
        """Flat mapping for the ledger. Provenance travels with the value, always."""
        return {
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
            "provenance": self.provenance.value,
            "source": self.source,
            "claimed_at": self.at.isoformat(),
        }


def measured(name: str, value: Any, command: str, unit: str | None = None) -> Claim:
    return Claim(name, value, Provenance.MEASURED, command, unit)


def derived(name: str, value: Any, formula: str, unit: str | None = None) -> Claim:
    return Claim(name, value, Provenance.DERIVED, formula, unit)


def cited(name: str, value: Any, source: str, unit: str | None = None) -> Claim:
    return Claim(name, value, Provenance.CITED, source, unit)


def assumed(name: str, value: Any, falsified_by: str, unit: str | None = None) -> Claim:
    """State a value that has NOT been verified, plus what would prove it wrong.

    The falsifier is mandatory. An assumption with no stated falsifier is
    indistinguishable from a belief, and beliefs do not belong in a ledger.
    """
    return Claim(name, value, Provenance.ASSUMED, falsified_by, unit)


def require_evidence(*claims: Claim) -> None:
    """Guard for any code path that decides something. Raises on ASSUMED input.

    Use at the top of adjudication, promotion, and anything that writes a verdict.
    """
    weak = [c for c in claims if not c.is_evidence]
    if weak:
        listed = "; ".join(c.cite() for c in weak)
        raise ValueError(
            "decision blocked: these inputs are ASSUMED, not evidence -> " + listed
        )
