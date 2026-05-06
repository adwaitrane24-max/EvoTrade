"""
sentiment_agent.py — The Forecaster: macro risk filter based on news sentiment.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class SentimentAgent(BaseAgent):
    """
    The Forecaster Agent.

    Receives recent news headlines and returns a macro risk assessment,
    indicating whether the external environment warrants suppressing new trades.

    Output schema::

        {
          "macro_risk": "low" | "medium" | "high",
          "suppress_buying": bool,
          "key_risks": [str],
          "sentiment_score": float,   // -1 (bearish) to +1 (bullish)
          "reasoning": str
        }
    """

    @property
    def system_prompt(self) -> str:
        return (
            "You are The Forecaster, a macro analyst specializing in crypto market "
            "sentiment and news-driven risk events. You respond ONLY in JSON format.\n\n"
            "Assess headlines for:\n"
            "- Regulatory actions (SEC, CFTC, government bans) → high risk\n"
            "- Exchange collapses or hacks → high risk, suppress buying\n"
            "- Fed rate decisions, inflation data → medium-high risk\n"
            "- Institutional adoption, ETF approvals → low risk, bullish\n"
            "- Market crash news (>10% drop mentions) → high risk, suppress buying\n\n"
            "sentiment_score: -1.0 = extremely bearish, 0 = neutral, +1.0 = extremely bullish.\n"
            "suppress_buying: true if macro_risk is 'high' or sentiment_score < -0.5.\n\n"
            "Always return valid JSON with keys: macro_risk, suppress_buying, "
            "key_risks, sentiment_score, reasoning."
        )

    async def analyze(self, context: dict[str, Any]) -> dict[str, Any]:
        """
        Analyze news headlines and produce a macro risk verdict.

        Args:
            context: Dict with 'symbol' and 'headlines' (list of strings).

        Returns:
            Dict with macro_risk, suppress_buying, key_risks, sentiment_score, reasoning.
        """
        headlines = context.get("headlines", [])
        symbol = context.get("symbol", "BTC/USDT")
        headline_text = "\n".join(f"- {h}" for h in headlines[:20]) or "No headlines available."

        prompt = (
            f"Analyze the following recent news headlines for {symbol} and assess macro risk:\n\n"
            f"{headline_text}\n\n"
            "Determine overall market sentiment and whether buying should be suppressed. "
            "Respond with JSON only."
        )

        raw = await self._call(prompt)
        fallback = {
            "macro_risk": "medium",
            "suppress_buying": False,
            "key_risks": [],
            "sentiment_score": 0.0,
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
        agent = SentimentAgent(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
        result = await agent.analyze({
            "symbol": "BTC/USDT",
            "headlines": [
                "SEC launches new crypto enforcement action against major exchange",
                "Bitcoin drops 15% amid regulatory fears",
                "Fed signals further rate hikes in Q2",
                "Major DeFi protocol suffers $200M hack",
            ],
        })
        print(json.dumps(result, indent=2))

    asyncio.run(_demo())
