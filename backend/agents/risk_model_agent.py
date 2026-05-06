"""
risk_model_agent.py — The Guardian: VaR analysis and position-sizing recommendations.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class RiskModelAgent(BaseAgent):
    """
    The Guardian Agent.

    Receives Monte Carlo VaR statistics and Gene parameters, then recommends
    adjusted position sizing and assigns a risk score.

    Output schema::

        {
          "risk_score": float,                      // 0 (safe) – 10 (extreme)
          "recommended_position_size": float,       // fraction of capital 0–1
          "var_assessment": str,
          "stop_loss_recommendation": float,
          "reasoning": str
        }
    """

    @property
    def system_prompt(self) -> str:
        return (
            "You are The Guardian, a risk management specialist focused on "
            "protecting trading capital through rigorous VaR analysis and "
            "position sizing. You respond ONLY in JSON format.\n\n"
            "Guidelines:\n"
            "- Risk score 0-3: conservative, position size up to 30%\n"
            "- Risk score 4-6: moderate, position size up to 15%\n"
            "- Risk score 7-10: aggressive, position size capped at 5%\n"
            "- If 95% VaR exceeds -20%, recommend halving position size\n"
            "- If crash survival rate < 50%, increase stop-loss tightness\n"
            "- Never recommend position sizes > 50% regardless of metrics\n\n"
            "Always return valid JSON with keys: risk_score, recommended_position_size, "
            "var_assessment, stop_loss_recommendation, reasoning."
        )

    async def analyze(self, context: dict[str, Any]) -> dict[str, Any]:
        """
        Assess risk and recommend position parameters.

        Args:
            context: Dict containing VaR data, Monte Carlo results, and gene params.

        Returns:
            Dict with risk_score, recommended_position_size, and reasoning.
        """
        prompt = (
            f"Analyze the following risk metrics for a crypto trading strategy:\n\n"
            f"```json\n{json.dumps(context, indent=2)}\n```\n\n"
            "Provide risk score, position sizing recommendation, and stop-loss advice. "
            "Respond with JSON only."
        )

        raw = await self._call(prompt)
        fallback = {
            "risk_score": 5.0,
            "recommended_position_size": 0.10,
            "var_assessment": "Unable to assess",
            "stop_loss_recommendation": 0.03,
            "reasoning": "Could not parse agent response.",
        }
        return self._parse_json(raw, fallback)


if __name__ == "__main__":
    import asyncio
    import os
    from dotenv import load_dotenv

    load_dotenv()
    logging.basicConfig(level=logging.INFO)

    async def _demo() -> None:
        agent = RiskModelAgent(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
        result = await agent.analyze({
            "var_95": -0.18,
            "survival_rate": 0.72,
            "crash_survival_rate": 0.45,
            "mean_return": 0.08,
            "gene": {
                "stop_loss_pct": 0.05,
                "position_size_pct": 0.30,
            },
        })
        print(json.dumps(result, indent=2))

    asyncio.run(_demo())
