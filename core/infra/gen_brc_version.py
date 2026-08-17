"""Backward-compat shim: BRC version stamp now lives in gen_version.py.

Kept so the existing BRC headless-compile step keeps working unchanged.
New systems should call `python core/infra/gen_version.py <system>`.
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from core.infra.gen_version import gen


def main() -> None:
    gen("brc")


if __name__ == "__main__":
    main()
