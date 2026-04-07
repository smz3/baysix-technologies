"""
Supabase client — IPC bus and persistent state store.

Tables:
  zone_outcomes   — B2B zone lifecycle tracking
  trading_context — Latest CIO JSON payload (polled by MT5 EA every 15 min)
  agent_logs      — Every agent run log (feeds sigma-quant Swarm Terminal)
  pnl_records     — Daily P&L per instrument
"""

import os
from datetime import datetime, timezone
from typing import Any

from dotenv import load_dotenv

load_dotenv()


class SupabaseClient:
    def __init__(self):
        self._url = os.getenv("SUPABASE_URL", "")
        self._key = (
            os.getenv("SUPABASE_SERVICE_ROLE_KEY", "") or os.getenv("SUPABASE_KEY", "")
        )
        self._client = None

    @property
    def is_available(self) -> bool:
        return bool(
            self._url
            and not self._url.startswith("https://your-project")
            and self._key
            and not self._key.startswith("your-")
        )

    @property
    def client(self):
        if self._client is None:
            from supabase import create_client
            self._client = create_client(self._url, self._key)
        return self._client

    def upsert_trading_context(self, payload: dict[str, Any]) -> bool:
        """Write latest CIO output. MT5 EA polls row id=1."""
        if not self.is_available:
            return False
        try:
            self.client.table("trading_context").upsert(
                {"id": 1, "payload": payload, "updated_at": _now_iso()},
                on_conflict="id",
            ).execute()
            return True
        except Exception as e:
            print(f"[Supabase] upsert_trading_context failed: {e}")
            return False

    def log_agent_run(
        self,
        agent_name: str,
        status: str,
        output_snippet: str,
        run_duration_ms: int = 0,
        regime: str = "UNKNOWN",
    ) -> bool:
        """Log agent run. Feeds sigma-quant Swarm Terminal."""
        if not self.is_available:
            return False
        try:
            self.client.table("agent_logs").insert({
                "agent_name": agent_name,
                "status": status,
                "output_snippet": output_snippet[:500],
                "run_duration_ms": run_duration_ms,
                "regime": regime,
                "created_at": _now_iso(),
            }).execute()
            return True
        except Exception as e:
            print(f"[Supabase] log_agent_run failed: {e}")
            return False

    def record_zone_outcome(
        self,
        zone_id: str,
        instrument: str,
        direction: str,
        entry_price: float,
        regime: str,
        tp1_hit: bool = False,
        tp2_hit: bool = False,
        tp3_hit: bool = False,
        invalidated: bool = False,
    ) -> bool:
        """Track a deployed B2B zone and its lifecycle outcome."""
        if not self.is_available:
            return False
        try:
            self.client.table("zone_outcomes").insert({
                "zone_id": zone_id,
                "instrument": instrument,
                "direction": direction,
                "entry_price": entry_price,
                "regime": regime,
                "tp1_hit": tp1_hit,
                "tp2_hit": tp2_hit,
                "tp3_hit": tp3_hit,
                "invalidated": invalidated,
                "created_at": _now_iso(),
            }).execute()
            return True
        except Exception as e:
            print(f"[Supabase] record_zone_outcome failed: {e}")
            return False

    def record_pnl(
        self,
        date_str: str,
        instrument: str,
        pnl_usd: float,
        num_trades: int,
        regime: str = "UNKNOWN",
    ) -> bool:
        """Record daily P&L per instrument. Upserts on (date, instrument)."""
        if not self.is_available:
            return False
        try:
            self.client.table("pnl_records").upsert(
                {
                    "date": date_str,
                    "instrument": instrument,
                    "pnl_usd": pnl_usd,
                    "num_trades": num_trades,
                    "regime": regime,
                    "updated_at": _now_iso(),
                },
                on_conflict="date,instrument",
            ).execute()
            return True
        except Exception as e:
            print(f"[Supabase] record_pnl failed: {e}")
            return False


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
