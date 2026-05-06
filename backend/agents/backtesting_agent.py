"""
backtesting_agent.py — The Critic: detects overfitting and luck vs. genuine edge.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class BacktestingAgent(BaseAgent):
    """
    The Critic Agent.

    Receives backtest performance metrics and identifies whether results
    are likely due to overfitting, lucky market conditions, or a real edge.

    Output schema::

        {
          "overfit_detected": bool,
          "reasoning": str,
          "confidence": float,       // 0–1
          "fitness_penalty": float   // adjustment to GA fitness (-1 to 0)
        }
    """

    @property
    def system_prompt(self) -> str:
        return (
            "You are The Critic, a quantitative trading analyst specializing in "
            "identifying overfitting and distinguishing genuine trading edges from "
            "lucky outcomes in backtests. You respond ONLY in JSON format.\n\n"
            "Analyze backtest metrics critically. Flag overfitting if:\n"
            "- Sharpe ratio > 3 on historical data (likely curve-fit)\n"
            "- Win rate > 80% (statistically improbable)\n"
            "- Very few trades (<10) with high returns\n"
            "- Profit factor > 5 (unrealistic)\n"
            "- Out-of-sample underperformance exceeds 40% of in-sample\n\n"
            "Always return valid JSON with keys: overfit_detected, reasoning, "
            "confidence, fitness_penalty."
        )

    async def analyze(self, context: dict[str, Any]) -> dict[str, Any]:
        """
        Analyze backtest results for overfitting signals.

        Args:
            context: Dict containing backtest metrics (sharpe, drawdown, trades, win_rate, etc.).

        Returns:
            Dict with overfit_detected, reasoning, confidence, fitness_penalty.
        """
        prompt = (
            f"Analyze these backtest results for a crypto trading strategy:\n\n"
            f"```json\n{json.dumps(context, indent=2)}\n```\n\n"
            "Determine whether these results indicate genuine alpha or overfitting. "
            "Respond with JSON only."
        )

        raw = await self._call(prompt)
        fallback = {
            "overfit_detected": False,
            "reasoning": "Could not parse agent response.",
            "confidence": 0.5,
            "fitness_penalty": 0.0,
        }
        result = self._parse_json(raw, fallback)
        result.setdefault("fitness_penalty", 0.0)
        return result


if __name__ == "__main__":
    import asyncio
    import os
    from dotenv import load_dotenv

    load_dotenv()
    logging.basicConfig(level=logging.INFO)

    async def _demo() -> None:
        agent = BacktestingAgent(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
        result = await agent.analyze({
            "sharpe_ratio": 4.2,
            "total_return_pct": 320,
            "max_drawdown_pct": 8,
            "num_trades": 6,
            "win_rate": 0.83,
            "profit_factor": 6.1,
        })
        print(json.dumps(result, indent=2))

    asyncio.run(_demo())
