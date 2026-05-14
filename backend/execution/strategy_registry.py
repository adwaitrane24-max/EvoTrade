"""
strategy_registry.py — Strategy lifecycle controller (PRD §17).

Manages:
  • candidate registration  — a freshly evolved AlphaGene
  • shadow mode             — generate signals without placing real orders,
                              compare against the current live strategy
  • hot swap                — atomic flip of the `active_strategy_id` pointer
                              read at candle-close boundaries by the live loop
  • rollback                — automatic, if shadow PnL or live drawdown
                              exceeds thresholds (PRD Appendix C)

The registry holds the last N strategies + metadata so any swap can be
undone instantly.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from genetic.gene import Gene

logger = logging.getLogger(__name__)

_REGISTRY_PATH = Path(__file__).parent.parent.parent / "outputs" / "strategy_registry.json"


class StrategyStatus(str, Enum):
    CANDIDATE = "candidate"
    SHADOW    = "shadow"
    LIVE      = "live"
    RETIRED   = "retired"
    ROLLED_BACK = "rolled_back"


@dataclass
class StrategyRecord:
    id: str
    gene: Gene
    status: StrategyStatus
    origin: str                                # "gen1", "gen2", ..., "manual"
    created_at: str
    activated_at: Optional[str] = None
    retired_at: Optional[str] = None
    fitness_at_creation: Optional[float] = None
    metadata: dict = field(default_factory=dict)

    # Live-vs-shadow tracking
    shadow_signals: int = 0
    shadow_agreement_pct: float = 0.0
    shadow_paper_pnl_pct: float = 0.0

    # Live tracking (only relevant when status == LIVE)
    live_max_dd_pct: float = 0.0
    live_pnl_pct: float = 0.0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "gene": self.gene.to_dict(),
            "status": self.status.value,
            "origin": self.origin,
            "created_at": self.created_at,
            "activated_at": self.activated_at,
            "retired_at": self.retired_at,
            "fitness_at_creation": self.fitness_at_creation,
            "metadata": self.metadata,
            "shadow_signals": self.shadow_signals,
            "shadow_agreement_pct": self.shadow_agreement_pct,
            "shadow_paper_pnl_pct": self.shadow_paper_pnl_pct,
            "live_max_dd_pct": self.live_max_dd_pct,
            "live_pnl_pct": self.live_pnl_pct,
        }


@dataclass
class DeploymentPolicy:
    """Thresholds gating shadow → live and live → rollback transitions (PRD App. C)."""
    min_shadow_signals: int = 20                 # need at least this many before swap
    max_shadow_lag_pct: float = 1.5              # shadow PnL must not trail baseline by more than this %
    auto_rollback_dd_pct: float = 8.0            # roll back if live DD exceeds this %
    rollback_check_window_s: float = 60 * 5      # min time before re-checking after a swap


class StrategyRegistry:
    """
    Single source of truth for "what gene is the live engine using right now?"
    Live loop reads `active_strategy_id` at candle-close boundaries.
    """

    def __init__(
        self,
        path: Path = _REGISTRY_PATH,
        policy: Optional[DeploymentPolicy] = None,
    ) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.policy = policy or DeploymentPolicy()
        self._lock = asyncio.Lock()
        self._records: dict[str, StrategyRecord] = {}
        self._active_id: Optional[str] = None
        self._shadow_id: Optional[str] = None
        self._last_swap_ts: float = 0.0
        self._load()

    # ── persistence ──────────────────────────────────────────────────────────

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            for r in data.get("records", []):
                gene = Gene(
                    rsi_period=int(r["gene"]["rsi_period"]),
                    ma_short=int(r["gene"]["ma_short"]),
                    ma_long=int(r["gene"]["ma_long"]),
                    stop_loss_pct=float(r["gene"]["stop_loss_pct"]),
                    take_profit_pct=float(r["gene"]["take_profit_pct"]),
                    position_size_pct=float(r["gene"]["position_size_pct"]),
                )
                rec = StrategyRecord(
                    id=r["id"], gene=gene,
                    status=StrategyStatus(r["status"]),
                    origin=r["origin"], created_at=r["created_at"],
                    activated_at=r.get("activated_at"),
                    retired_at=r.get("retired_at"),
                    fitness_at_creation=r.get("fitness_at_creation"),
                    metadata=r.get("metadata") or {},
                )
                self._records[rec.id] = rec
            self._active_id = data.get("active_strategy_id")
            self._shadow_id = data.get("shadow_strategy_id")
        except Exception as exc:
            logger.warning("StrategyRegistry load failed: %s", exc)

    def _persist(self) -> None:
        snapshot = {
            "active_strategy_id": self._active_id,
            "shadow_strategy_id": self._shadow_id,
            "records": [r.to_dict() for r in self._records.values()],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self.path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")

    # ── registration ─────────────────────────────────────────────────────────

    async def register_candidate(
        self,
        gene: Gene,
        origin: str,
        fitness: Optional[float] = None,
        metadata: Optional[dict] = None,
    ) -> StrategyRecord:
        async with self._lock:
            rec = StrategyRecord(
                id=str(uuid.uuid4()),
                gene=gene,
                status=StrategyStatus.CANDIDATE,
                origin=origin,
                created_at=datetime.now(timezone.utc).isoformat(),
                fitness_at_creation=fitness,
                metadata=metadata or {},
            )
            self._records[rec.id] = rec
            self._persist()

            # Supabase mirror (best-effort)
            try:
                from persistence.supabase_client import supabase
                asyncio.create_task(supabase().insert_strategy(
                    strategy_id=rec.id, gene=gene.to_dict(),
                    status=rec.status.value, origin=origin,
                    fitness=fitness, metadata=metadata or {},
                ))
            except Exception:
                pass

            logger.info("Registered candidate %s from %s", rec.id, origin)
            return rec

    async def promote_to_shadow(self, strategy_id: str) -> StrategyRecord:
        """Promote a candidate to shadow mode (still no live orders)."""
        async with self._lock:
            rec = self._records.get(strategy_id)
            if not rec or rec.status != StrategyStatus.CANDIDATE:
                raise ValueError(f"Strategy {strategy_id} not promotable to shadow")

            # Demote any current shadow
            if self._shadow_id and self._shadow_id != strategy_id:
                old = self._records.get(self._shadow_id)
                if old:
                    old.status = StrategyStatus.RETIRED
                    old.retired_at = datetime.now(timezone.utc).isoformat()

            rec.status = StrategyStatus.SHADOW
            self._shadow_id = strategy_id
            self._persist()
            return rec

    # ── shadow tracking ──────────────────────────────────────────────────────

    async def record_shadow_signal(
        self, strategy_id: str, *, agree_with_live: bool, paper_pnl_pct: float,
    ) -> None:
        async with self._lock:
            rec = self._records.get(strategy_id)
            if not rec or rec.status != StrategyStatus.SHADOW:
                return
            rec.shadow_signals += 1
            # rolling agreement
            n = rec.shadow_signals
            prev_agree = rec.shadow_agreement_pct * (n - 1) / 100.0
            rec.shadow_agreement_pct = ((prev_agree + (1 if agree_with_live else 0)) / n) * 100.0
            rec.shadow_paper_pnl_pct = paper_pnl_pct
            self._persist()

    # ── hot swap ─────────────────────────────────────────────────────────────

    async def hot_swap_to(self, strategy_id: str, *, force: bool = False) -> dict:
        """
        Atomically promote `strategy_id` to LIVE.
        Returns a result dict; raises only on schema errors.
        """
        async with self._lock:
            rec = self._records.get(strategy_id)
            if not rec:
                raise ValueError(f"Unknown strategy {strategy_id}")

            # Check policy unless forced (forced is for first-deploy or manual)
            if not force and rec.status == StrategyStatus.SHADOW:
                if rec.shadow_signals < self.policy.min_shadow_signals:
                    return {
                        "status": "blocked",
                        "reason": f"need_min_shadow_signals_{self.policy.min_shadow_signals}",
                        "current": rec.shadow_signals,
                    }
                # baseline = current live's recent PnL
                live = self._records.get(self._active_id) if self._active_id else None
                if live:
                    lag = (live.live_pnl_pct - rec.shadow_paper_pnl_pct)
                    if lag > self.policy.max_shadow_lag_pct:
                        return {
                            "status": "blocked",
                            "reason": "shadow_underperforms_baseline",
                            "lag_pct": round(lag, 2),
                        }

            # Demote previous live
            previous_live: Optional[StrategyRecord] = None
            if self._active_id and self._active_id != strategy_id:
                previous_live = self._records.get(self._active_id)
                if previous_live:
                    previous_live.status = StrategyStatus.RETIRED
                    previous_live.retired_at = datetime.now(timezone.utc).isoformat()

            rec.status = StrategyStatus.LIVE
            rec.activated_at = datetime.now(timezone.utc).isoformat()
            rec.live_max_dd_pct = 0.0
            rec.live_pnl_pct = 0.0
            self._active_id = rec.id
            if self._shadow_id == rec.id:
                self._shadow_id = None
            self._last_swap_ts = time.time()
            self._persist()

            # Supabase mirror
            try:
                from persistence.supabase_client import supabase
                asyncio.create_task(supabase().update_strategy_status(
                    rec.id, status="live", activated_at=rec.activated_at,
                ))
                if previous_live:
                    asyncio.create_task(supabase().update_strategy_status(
                        previous_live.id, status="retired",
                        retired_at=previous_live.retired_at,
                    ))
            except Exception:
                pass

            logger.info("Hot-swap → %s (origin=%s)", rec.id, rec.origin)
            return {
                "status": "ok",
                "active_strategy_id": rec.id,
                "previous_strategy_id": previous_live.id if previous_live else None,
            }

    # ── rollback ─────────────────────────────────────────────────────────────

    async def rollback(self, *, reason: str = "auto") -> dict:
        """Roll the live pointer back to the most recent retired strategy."""
        async with self._lock:
            current = self._records.get(self._active_id) if self._active_id else None
            if not current:
                return {"status": "nothing_to_rollback"}

            # Find most recent retired strategy that isn't this one
            retired = [
                r for r in self._records.values()
                if r.status == StrategyStatus.RETIRED and r.id != current.id
            ]
            if not retired:
                return {"status": "no_previous_strategy", "current": current.id}
            retired.sort(key=lambda r: r.retired_at or "", reverse=True)
            previous = retired[0]

            current.status = StrategyStatus.ROLLED_BACK
            current.retired_at = datetime.now(timezone.utc).isoformat()
            previous.status = StrategyStatus.LIVE
            previous.activated_at = datetime.now(timezone.utc).isoformat()
            self._active_id = previous.id
            self._last_swap_ts = time.time()
            self._persist()

            logger.warning("Rollback: %s → %s (%s)", current.id, previous.id, reason)
            return {
                "status": "ok",
                "rolled_back_from": current.id,
                "active_strategy_id": previous.id,
                "reason": reason,
            }

    # ── live tracking + auto-rollback gate ───────────────────────────────────

    async def update_live_metrics(
        self, strategy_id: str, *, pnl_pct: float, max_dd_pct: float,
    ) -> Optional[dict]:
        """
        Update live metrics. If drawdown breaches policy and the swap is older
        than `rollback_check_window_s`, auto-rollback is fired.

        Returns a rollback-result dict if an auto-rollback fired, else None.
        """
        async with self._lock:
            rec = self._records.get(strategy_id)
            if not rec or rec.status != StrategyStatus.LIVE:
                return None
            rec.live_pnl_pct = pnl_pct
            rec.live_max_dd_pct = max(rec.live_max_dd_pct, max_dd_pct)
            self._persist()

            since_swap = time.time() - self._last_swap_ts
            if (
                rec.live_max_dd_pct >= self.policy.auto_rollback_dd_pct
                and since_swap >= self.policy.rollback_check_window_s
            ):
                return await self._auto_rollback(reason="auto_rollback_dd_breach")
        return None

    async def _auto_rollback(self, reason: str) -> dict:
        # NOTE: caller already holds _lock
        current = self._records.get(self._active_id) if self._active_id else None
        if not current:
            return {"status": "nothing_to_rollback"}

        retired = [
            r for r in self._records.values()
            if r.status == StrategyStatus.RETIRED and r.id != current.id
        ]
        if not retired:
            return {"status": "no_previous_strategy"}
        retired.sort(key=lambda r: r.retired_at or "", reverse=True)
        previous = retired[0]

        current.status = StrategyStatus.ROLLED_BACK
        current.retired_at = datetime.now(timezone.utc).isoformat()
        previous.status = StrategyStatus.LIVE
        previous.activated_at = datetime.now(timezone.utc).isoformat()
        self._active_id = previous.id
        self._last_swap_ts = time.time()
        self._persist()
        return {
            "status": "rolled_back",
            "from": current.id,
            "to": previous.id,
            "reason": reason,
        }

    # ── read accessors ───────────────────────────────────────────────────────

    @property
    def active_strategy_id(self) -> Optional[str]:
        return self._active_id

    @property
    def shadow_strategy_id(self) -> Optional[str]:
        return self._shadow_id

    def get(self, strategy_id: str) -> Optional[StrategyRecord]:
        return self._records.get(strategy_id)

    def active(self) -> Optional[StrategyRecord]:
        return self._records.get(self._active_id) if self._active_id else None

    def shadow(self) -> Optional[StrategyRecord]:
        return self._records.get(self._shadow_id) if self._shadow_id else None

    def list_all(self) -> list[StrategyRecord]:
        return list(self._records.values())


if __name__ == "__main__":
    async def _demo():
        reg = StrategyRegistry()
        gene_a = Gene()
        gene_b = Gene(rsi_period=21, ma_short=20, ma_long=80)

        a = await reg.register_candidate(gene_a, origin="gen1", fitness=0.30)
        b = await reg.register_candidate(gene_b, origin="gen2", fitness=0.42)

        # First deploy must be forced
        print(await reg.hot_swap_to(a.id, force=True))

        await reg.promote_to_shadow(b.id)
        for _ in range(25):
            await reg.record_shadow_signal(b.id, agree_with_live=True, paper_pnl_pct=2.0)
        print(await reg.hot_swap_to(b.id))

        await reg.update_live_metrics(b.id, pnl_pct=-1.0, max_dd_pct=10.0)
        # Note: rollback_check_window_s gates the auto-rollback in real use.
        print(await reg.rollback(reason="manual_demo"))

    asyncio.run(_demo())
