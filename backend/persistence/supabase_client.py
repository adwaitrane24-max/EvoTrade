"""
supabase_client.py — Thin async-friendly client for the EvoTrade tables.

Design rules:
  • All methods are no-ops when SUPABASE_URL is empty (offline/dev mode).
  • Network calls run inside `asyncio.to_thread` so they don't block the
    live trading loop.
  • Service role key is the canonical writer for trades/audit logs because
    they require RLS bypass; if not provided we fall back to the user's JWT.
  • Plaintext secrets are never sent here — broker connections store only
    the AES-256-GCM ciphertext envelope.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Lazy import so that `import config` (which forces requirements) doesn't
# pull in supabase as a hard dependency at module load time.
try:
    from supabase import Client, create_client                              # type: ignore
    _SDK_AVAILABLE = True
except Exception:                                                            # pragma: no cover
    Client = None  # type: ignore[misc, assignment]
    create_client = None  # type: ignore[assignment]
    _SDK_AVAILABLE = False


class SupabaseClient:
    """
    EvoTrade-flavored wrapper. Use `instance()` to fetch the singleton.

    The wrapper stays usable when Supabase is unconfigured: every write becomes
    a logged no-op so the rest of the system never has to branch on it.
    """

    _singleton: Optional["SupabaseClient"] = None

    def __init__(self) -> None:
        self.url = os.getenv("SUPABASE_URL", "")
        self.anon_key = os.getenv("SUPABASE_ANON_KEY", "")
        self.service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        self.user_jwt = os.getenv("SUPABASE_USER_JWT", "")
        self.user_id = os.getenv("EVOTRADE_USER_ID", "")
        self._client: Optional[Client] = None

        if not self.url or not _SDK_AVAILABLE:
            logger.info("Supabase disabled (missing URL or SDK not installed).")
            return

        # Prefer service role on the backend; falls back to user JWT, then anon.
        key = self.service_key or self.user_jwt or self.anon_key
        if not key:
            logger.warning("Supabase URL set but no auth key; client disabled.")
            return

        try:
            self._client = create_client(self.url, key)
            logger.info("Supabase client ready (auth=%s).",
                        "service" if self.service_key else "user_jwt" if self.user_jwt else "anon")
        except Exception as exc:
            logger.warning("Supabase client init failed: %s", exc)
            self._client = None

    @classmethod
    def instance(cls) -> "SupabaseClient":
        if cls._singleton is None:
            cls._singleton = cls()
        return cls._singleton

    @property
    def enabled(self) -> bool:
        return self._client is not None

    # ── core helpers ─────────────────────────────────────────────────────────

    async def _insert(self, table: str, row: dict[str, Any]) -> Optional[dict]:
        """Insert one row off the event loop. Returns the inserted row, or None."""
        if not self._client:
            return None
        if self.user_id and "user_id" not in row:
            row["user_id"] = self.user_id
        try:
            return await asyncio.to_thread(self._sync_insert, table, row)
        except Exception as exc:
            logger.warning("Supabase insert into %s failed: %s", table, exc)
            return None

    def _sync_insert(self, table: str, row: dict[str, Any]) -> dict:
        resp = self._client.table(table).insert(row).execute()
        data = getattr(resp, "data", None) or []
        return data[0] if data else {}

    async def _upsert(self, table: str, row: dict[str, Any], on_conflict: str) -> Optional[dict]:
        if not self._client:
            return None
        if self.user_id and "user_id" not in row:
            row["user_id"] = self.user_id
        try:
            return await asyncio.to_thread(self._sync_upsert, table, row, on_conflict)
        except Exception as exc:
            logger.warning("Supabase upsert into %s failed: %s", table, exc)
            return None

    def _sync_upsert(self, table: str, row: dict[str, Any], on_conflict: str) -> dict:
        resp = self._client.table(table).upsert(row, on_conflict=on_conflict).execute()
        data = getattr(resp, "data", None) or []
        return data[0] if data else {}

    # ── domain helpers (one per logical write site) ─────────────────────────

    async def insert_strategy(self, *, gene: dict, status: str, origin: str,
                              fitness: Optional[float] = None,
                              metadata: Optional[dict] = None,
                              strategy_id: Optional[str] = None) -> Optional[dict]:
        row = {
            "genes": gene,
            "status": status,
            "origin": origin,
            "fitness": fitness,
            "metadata": metadata or {},
        }
        if strategy_id:
            row["id"] = strategy_id
        return await self._insert("evotrade_strategies", row)

    async def update_strategy_status(self, strategy_id: str, *,
                                      status: str,
                                      activated_at: Optional[str] = None,
                                      retired_at: Optional[str] = None) -> None:
        if not self._client:
            return
        patch: dict[str, Any] = {"status": status}
        if activated_at:
            patch["activated_at"] = activated_at
        if retired_at:
            patch["retired_at"] = retired_at
        try:
            await asyncio.to_thread(
                lambda: self._client.table("evotrade_strategies")
                                .update(patch).eq("id", strategy_id).execute()
            )
        except Exception as exc:
            logger.warning("Strategy update failed: %s", exc)

    async def insert_evolution_run(self, *, symbol: str, risk_profile: str,
                                    n_generations: int, population_size: int,
                                    run_id: Optional[str] = None) -> Optional[dict]:
        row = {
            "symbol": symbol,
            "risk_profile": risk_profile,
            "n_generations": n_generations,
            "population_size": population_size,
            "status": "running",
        }
        if run_id:
            row["id"] = run_id
        return await self._insert("evotrade_evolution_runs", row)

    async def complete_evolution_run(self, run_id: str, *,
                                      final_alpha_gene_id: Optional[str],
                                      fitness_history: list[float]) -> None:
        if not self._client:
            return
        try:
            await asyncio.to_thread(
                lambda: self._client.table("evotrade_evolution_runs")
                                .update({
                                    "status": "completed",
                                    "final_alpha_gene_id": final_alpha_gene_id,
                                    "fitness_history": fitness_history,
                                    "completed_at": "now()",
                                }).eq("id", run_id).execute()
            )
        except Exception as exc:
            logger.warning("complete_evolution_run failed: %s", exc)

    async def insert_generation_result(self, *, run_id: str, generation: int,
                                        candidates: list[dict],
                                        top_3: list[dict],
                                        alpha_gene: dict,
                                        best_fitness: float,
                                        avg_fitness: float) -> Optional[dict]:
        return await self._insert("evotrade_generation_results", {
            "run_id": run_id, "generation": generation,
            "candidates": candidates, "top_3": top_3,
            "alpha_gene": alpha_gene,
            "best_fitness": best_fitness, "avg_fitness": avg_fitness,
        })

    async def insert_backtest_result(self, *, strategy_id: str, metrics: dict) -> Optional[dict]:
        return await self._insert("evotrade_backtest_results", {
            "strategy_id": strategy_id,
            "sharpe_ratio": metrics.get("sharpe_ratio"),
            "max_drawdown_pct": metrics.get("max_drawdown"),
            "win_rate": metrics.get("win_rate"),
            "trades": metrics.get("total_trades"),
            "profit_factor": metrics.get("profit_factor"),
            "fitness_score": metrics.get("fitness_score"),
            "total_return_pct": metrics.get("profit_pct"),
            "raw_metrics": metrics,
        })

    async def insert_monte_carlo_result(self, *, strategy_id: str,
                                         metrics: dict) -> Optional[dict]:
        return await self._insert("evotrade_monte_carlo_results", {
            "strategy_id": strategy_id,
            "paths": metrics.get("paths") or metrics.get("n_runs", 0),
            "survivability_pct": metrics.get("survivability_pct")
                                  or (metrics.get("survival_rate", 0.0) * 100),
            "tail_dd_95_pct": metrics.get("tail_dd_95_pct"),
            "worst_case_return_pct": metrics.get("worst_case_return_pct"),
            "robust_fitness": metrics.get("robust_fitness"),
            "raw_metrics": metrics,
        })

    async def insert_ai_card(self, *, run_id: Optional[str], generation: Optional[int],
                              strategy_id: Optional[str], reasoning: dict) -> Optional[dict]:
        meta = reasoning.get("_meta") or {}
        return await self._insert("evotrade_ai_reasoning_cards", {
            "run_id": run_id, "generation": generation,
            "strategy_id": strategy_id,
            "reasoning_json": reasoning,
            "model": meta.get("model", "unknown"),
            "source": meta.get("source", "fallback"),
            "latency_s": meta.get("latency_s"),
        })

    async def insert_trade(self, *, fill: dict, strategy_id: Optional[str]) -> Optional[dict]:
        return await self._insert("evotrade_trades", {
            "strategy_id": strategy_id,
            "symbol": fill.get("symbol"),
            "side": fill.get("side"),
            "type": fill.get("type", "MARKET"),
            "qty": fill.get("qty"),
            "fill_price": fill.get("fill_price"),
            "mark_price": fill.get("mark_price"),
            "fee_usdt": fill.get("fee_usdt"),
            "slip_bps_used": fill.get("slip_bps_used"),
            "status": fill.get("status", "filled"),
            "broker_order_id": fill.get("broker_order_id"),
            "is_paper": True,
            "regime_at_entry": fill.get("regime"),
            "metadata": {k: v for k, v in fill.items()
                         if k not in {"symbol", "side", "type", "qty",
                                      "fill_price", "mark_price", "fee_usdt",
                                      "slip_bps_used", "status",
                                      "broker_order_id", "regime"}},
        })

    async def insert_risk_event(self, *, event_type: str, reason: str,
                                 payload: Optional[dict] = None) -> Optional[dict]:
        return await self._insert("evotrade_risk_events", {
            "event_type": event_type,
            "reason": reason,
            "payload": payload or {},
        })

    async def insert_audit_log(self, *, audit_id: str, event_type: str,
                                payload: dict, prev_hash: str, hash: str) -> Optional[dict]:
        return await self._insert("evotrade_audit_logs", {
            "audit_id": audit_id,
            "event_type": event_type,
            "payload": payload,
            "prev_hash": prev_hash,
            "hash": hash,
        })

    async def upsert_position(self, *, symbol: str, qty: float, avg_price: float,
                               is_paper: bool = True) -> Optional[dict]:
        return await self._upsert(
            "evotrade_positions",
            {"symbol": symbol, "qty": qty, "avg_price": avg_price, "is_paper": is_paper},
            on_conflict="user_id,symbol,is_paper",
        )

    async def insert_broker_connection(self, *, broker: str, envelope: dict) -> Optional[dict]:
        return await self._insert("evotrade_broker_connections", {
            "broker": broker,
            "envelope_v": envelope.get("v", 1),
            "envelope_alg": envelope.get("alg", "AES-256-GCM"),
            "envelope_nonce": envelope.get("nonce"),
            "envelope_ct": envelope.get("ct"),
            "envelope_aad": envelope.get("aad"),
            "is_active": True,
        })

    async def insert_dashboard_event(self, *, event_type: str, payload: dict) -> Optional[dict]:
        return await self._insert("evotrade_dashboard_events", {
            "event_type": event_type, "payload": payload,
        })


def supabase() -> SupabaseClient:
    """Module-level convenience accessor."""
    return SupabaseClient.instance()
