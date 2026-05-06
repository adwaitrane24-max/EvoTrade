"""
council.py — Multi-Agent Council orchestrator.
Runs Critic → Guardian → Forecaster in sequence and aggregates a final fitness score.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import pandas as pd

from agents.backtesting_agent import BacktestingAgent
from agents.risk_model_agent import RiskModelAgent
from agents.sentiment_agent import SentimentAgent
from genetic.gene import Gene
from stress_test.backtest_runner import BacktestResult, BacktestRunner
from stress_test.monte_carlo import MonteCarloEngine, MonteCarloResult

logger = logging.getLogger(__name__)


class CouncilResult:
    """Aggregated verdict from all three council agents."""

    def __init__(
        self,
        critic: dict,
        guardian: dict,
        forecaster: dict,
        final_fitness_delta: float,
    ) -> None:
        self.critic = critic
        self.guardian = guardian
        self.forecaster = forecaster
        self.final_fitness_delta = final_fitness_delta

    def to_dict(self) -> dict[str, Any]:
        return {
            "critic": self.critic,
            "guardian": self.guardian,
            "forecaster": self.forecaster,
            "final_fitness_delta": self.final_fitness_delta,
        }


class AgentCouncil:
    """
    Orchestrates the three specialist agents in sequence and combines their outputs.

    Fitness delta computation:
        delta = (
            -0.40 × critic_penalty
            -0.30 × guardian_penalty
            -0.30 × forecaster_penalty
        )

    where each penalty is derived from the agent's structured output.

    Args:
        api_key: Anthropic API key.
        symbol: Trading pair for sentiment context.
        headlines: Recent news headlines (list of strings).
        mc_engine: Optional pre-configured MonteCarloEngine.
        bt_runner: Optional pre-configured BacktestRunner.
    """

    def __init__(
        self,
        api_key: str,
        symbol: str = "BTC/USDT",
        headlines: Optional[list[str]] = None,
        mc_engine: Optional[MonteCarloEngine] = None,
        bt_runner: Optional[BacktestRunner] = None,
    ) -> None:
        self._api_key = api_key
        self.symbol = symbol
        self.headlines = headlines or []
        self._mc_engine = mc_engine or MonteCarloEngine(n_paths=200)
        self._bt_runner = bt_runner or BacktestRunner()

        self._critic    = BacktestingAgent(api_key)
        self._guardian  = RiskModelAgent(api_key)
        self._forecaster = SentimentAgent(api_key)

    async def score(self, gene: Gene, price_df: pd.DataFrame) -> float:
        """
        Run all three agents and return a fitness delta to be added to the base GA fitness.

        Args:
            gene: The strategy to evaluate.
            price_df: Historical price data for backtesting.

        Returns:
            Float delta in range [-1, 0.2] (penalties or small bonus).
        """
        result = await self.evaluate(gene, price_df)
        return result.final_fitness_delta

    async def evaluate(self, gene: Gene, price_df: pd.DataFrame) -> CouncilResult:
        """
        Full council evaluation: backtest → MC → agents → aggregate.

        Args:
            gene: Trading strategy gene.
            price_df: Historical OHLCV data.

        Returns:
            CouncilResult with individual agent verdicts and composite delta.
        """
        # ── Gather data for agents ────────────────────────────────────────────
        bt_result: Optional[BacktestResult] = None
        mc_result: Optional[MonteCarloResult] = None

        try:
            bt_result = self._bt_runner.run(gene, price_df)
        except Exception as exc:
            logger.warning("Backtest failed during council eval: %s", exc)

        try:
            mc_result = self._mc_engine.evaluate(gene)
        except Exception as exc:
            logger.warning("Monte Carlo failed during council eval: %s", exc)

        # ── Critic ────────────────────────────────────────────────────────────
        critic_context: dict = {
            "sharpe_ratio": bt_result.sharpe_ratio if bt_result else 0,
            "total_return_pct": bt_result.total_return_pct if bt_result else 0,
            "max_drawdown_pct": bt_result.max_drawdown_pct if bt_result else 0,
            "num_trades": bt_result.num_trades if bt_result else 0,
            "win_rate": bt_result.win_rate if bt_result else 0,
            "profit_factor": bt_result.profit_factor if bt_result else 0,
        }
        try:
            critic_out = await self._critic.analyze(critic_context)
        except Exception as exc:
            logger.warning("Critic agent failed: %s", exc)
            critic_out = {"overfit_detected": False, "fitness_penalty": 0.0, "reasoning": str(exc)}

        # ── Guardian ──────────────────────────────────────────────────────────
        guardian_context: dict = {
            "var_95": mc_result.var_95 if mc_result else -0.10,
            "survival_rate": mc_result.survival_rate if mc_result else 0.8,
            "crash_survival_rate": mc_result.crash_survival_rate if mc_result else 0.6,
            "mean_return": mc_result.mean_return if mc_result else 0.05,
            "gene": {
                "stop_loss_pct": gene.stop_loss_pct,
                "position_size_pct": gene.position_size_pct,
            },
        }
        try:
            guardian_out = await self._guardian.analyze(guardian_context)
        except Exception as exc:
            logger.warning("Guardian agent failed: %s", exc)
            guardian_out = {"risk_score": 5.0, "recommended_position_size": 0.10, "reasoning": str(exc)}

        # ── Forecaster ────────────────────────────────────────────────────────
        forecaster_context: dict = {
            "symbol": self.symbol,
            "headlines": self.headlines,
        }
        try:
            forecaster_out = await self._forecaster.analyze(forecaster_context)
        except Exception as exc:
            logger.warning("Forecaster agent failed: %s", exc)
            forecaster_out = {"macro_risk": "medium", "suppress_buying": False, "sentiment_score": 0.0}

        # ── Aggregate ─────────────────────────────────────────────────────────
        delta = self._compute_delta(critic_out, guardian_out, forecaster_out)

        logger.info("Council delta=%.4f | overfit=%s | risk=%.1f | macro=%s",
                    delta,
                    critic_out.get("overfit_detected"),
                    guardian_out.get("risk_score", 5),
                    forecaster_out.get("macro_risk"))

        return CouncilResult(
            critic=critic_out,
            guardian=guardian_out,
            forecaster=forecaster_out,
            final_fitness_delta=delta,
        )

    @staticmethod
    def _compute_delta(critic: dict, guardian: dict, forecaster: dict) -> float:
        """
        Translate agent outputs into a numeric fitness delta.

        Weights: critic 40 %, guardian 30 %, forecaster 30 %.
        """
        # Critic penalty
        critic_penalty = float(critic.get("fitness_penalty", 0.0))
        if critic.get("overfit_detected"):
            critic_penalty = min(critic_penalty - 0.5, -0.5)

        # Guardian penalty: risk_score 0–10 → 0 to -0.5
        risk_score = float(guardian.get("risk_score", 5.0))
        guardian_penalty = -((risk_score - 3.0) / 10.0) if risk_score > 3 else 0.0

        # Forecaster penalty
        macro = forecaster.get("macro_risk", "medium")
        sentiment = float(forecaster.get("sentiment_score", 0.0))
        macro_penalty = {"low": 0.0, "medium": -0.05, "high": -0.30}.get(macro, -0.05)
        if forecaster.get("suppress_buying"):
            macro_penalty -= 0.20
        forecaster_penalty = macro_penalty + min(0, sentiment * 0.10)

        delta = 0.40 * critic_penalty + 0.30 * guardian_penalty + 0.30 * forecaster_penalty
        return float(max(-1.0, min(0.2, delta)))


if __name__ == "__main__":
    import asyncio
    import os
    import yfinance as yf
    from dotenv import load_dotenv

    load_dotenv()
    logging.basicConfig(level=logging.INFO)

    async def _demo() -> None:
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            print("ANTHROPIC_API_KEY not set — skipping demo.")
            return

        df = yf.Ticker("BTC-USD").history(period="1y")
        gene = Gene.random()
        council = AgentCouncil(api_key=api_key, symbol="BTC/USDT")
        result = await council.evaluate(gene, df)
        import json
        print(json.dumps(result.to_dict(), indent=2))

    asyncio.run(_demo())
