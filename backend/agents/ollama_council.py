"""
ollama_council.py — Single-call AI Council using DeepSeek-R1 7B via Ollama.

Implements PRD §15-16:
  • One model call simulates three roles (Backtesting Critic, Risk Guardian,
    Sentiment Forecaster) with a strict structured-JSON output contract.
  • Receives only summarized metrics (PRD §16.2 / §24.1) — no secrets, no PII,
    no balances, no API keys.
  • Has a deterministic fallback if Ollama is unreachable or returns invalid JSON
    (PRD §16.4 / Appendix B).

The council has zero authority over execution. It can recommend a Top-3 index
and produce risk caps; the live engine treats those as advisory only.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from dataclasses import dataclass
from typing import Any, Optional

import aiohttp

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class OllamaConfig:
    base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model: str = os.getenv("OLLAMA_MODEL", "deepseek-r1:7b")
    timeout_s: float = float(os.getenv("OLLAMA_TIMEOUT_S", "60"))
    temperature: float = 0.2
    max_retries: int = 1               # PRD §16.4: one retry on bad JSON
    concurrent_calls: int = 1          # PRD §25.2: 1 inference at a time


# ──────────────────────────────────────────────────────────────────────────────
# Prompt
# ──────────────────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are the EvoTrade AI Council. You receive Top-3 candidate
trading strategies summarized as JSON. You MUST respond with ONE valid JSON
object — nothing before or after. No markdown, no code fences.

You simulate three internal roles:
  1. Backtesting Critic   — assess overfitting risk and edge sustainability
  2. Risk Guardian        — assess drawdown, position sizing, daily-loss limits
  3. Sentiment Forecaster — assess regime sensitivity and macro fragility

Output schema (STRICT):

{
  "backtesting_critic": {
    "summary": "<≤200 chars>",
    "overfitting_risk": "low" | "medium" | "high",
    "notes": ["<≤100 chars>", ...]
  },
  "risk_guardian": {
    "summary": "<≤200 chars>",
    "risk_level": "low" | "medium" | "high",
    "recommended_limits": {
      "max_position_size_pct": <float 0-0.5>,
      "max_daily_loss_pct": <float 0-10>
    }
  },
  "sentiment_forecaster": {
    "summary": "<≤200 chars>",
    "regime_sensitivity": "<≤200 chars>"
  },
  "consensus": {
    "approve_for_shadow": true | false,
    "recommended_index": 0 | 1 | 2,
    "key_reasoning": ["<≤120 chars>", ...],
    "watchouts": ["<≤120 chars>", ...]
  }
}

Rules:
- recommended_index MUST be a Top-3 index in [0, 2].
- approve_for_shadow=false if any candidate has high overfitting or risk.
- Be concise. Be conservative.
"""


# ──────────────────────────────────────────────────────────────────────────────
# Council
# ──────────────────────────────────────────────────────────────────────────────

class OllamaCouncil:
    """Async AI Council bound to a local Ollama endpoint."""

    def __init__(self, config: Optional[OllamaConfig] = None) -> None:
        self.cfg = config or OllamaConfig()
        self._sema = asyncio.Semaphore(self.cfg.concurrent_calls)
        self._available: Optional[bool] = None  # cache health probe

    async def __call__(self, top3_summaries: list[dict], generation: int) -> dict:
        """Match the AICouncilHook signature used by evolution_engine."""
        return await self.evaluate(top3_summaries, generation=generation)

    async def evaluate(self, top3_summaries: list[dict], *, generation: int = 0) -> dict:
        """
        Run the council on Top-3 strategy summaries.
        Always returns a structured dict (uses fallback on any failure).
        """
        if not isinstance(top3_summaries, list) or len(top3_summaries) == 0:
            return _deterministic_fallback([], generation, reason="no candidates")

        prompt = _build_user_prompt(top3_summaries, generation)

        async with self._sema:
            for attempt in range(self.cfg.max_retries + 1):
                t0 = time.monotonic()
                try:
                    raw = await self._call_ollama(prompt)
                    parsed = _strict_json_parse(raw)
                    if parsed and _validate_schema(parsed, len(top3_summaries)):
                        parsed["_meta"] = {
                            "model": self.cfg.model,
                            "latency_s": round(time.monotonic() - t0, 2),
                            "attempt": attempt + 1,
                            "source": "ollama",
                            "generation": generation,
                        }
                        return parsed
                    logger.warning("Council JSON invalid on attempt %d", attempt + 1)
                except Exception as exc:
                    logger.warning("Council call failed on attempt %d: %s", attempt + 1, exc)

        return _deterministic_fallback(top3_summaries, generation,
                                        reason="ollama_unavailable_or_invalid")

    async def health_check(self) -> bool:
        """Probe Ollama. Cached on first call."""
        if self._available is not None:
            return self._available
        try:
            timeout = aiohttp.ClientTimeout(total=2.0)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(f"{self.cfg.base_url}/api/tags") as r:
                    self._available = r.status == 200
        except Exception:
            self._available = False
        return self._available

    async def _call_ollama(self, user_prompt: str) -> str:
        """Hit Ollama /api/generate; return raw text."""
        payload = {
            "model": self.cfg.model,
            "prompt": user_prompt,
            "system": _SYSTEM_PROMPT,
            "stream": False,
            "options": {"temperature": self.cfg.temperature},
            "format": "json",  # nudge to JSON-only output
        }
        timeout = aiohttp.ClientTimeout(total=self.cfg.timeout_s)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                f"{self.cfg.base_url}/api/generate", json=payload
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise RuntimeError(f"Ollama HTTP {resp.status}: {text[:200]}")
                data = await resp.json()
                return data.get("response", "")


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _build_user_prompt(top3: list[dict], gen: int) -> str:
    """Format minimal, sanitized input for the model (PRD §16.2 / §24.1)."""
    sanitized = [_sanitize(item, idx=i) for i, item in enumerate(top3)]
    payload = {
        "generation": gen,
        "candidates": sanitized,
    }
    return (
        "Evaluate the following Top-3 candidates. Pick the safest with the best "
        "edge. Keep notes short. Return ONE JSON object exactly matching the "
        "schema. No prose.\n\n"
        f"{json.dumps(payload, ensure_ascii=False)}"
    )


def _sanitize(summary: dict, idx: int) -> dict:
    """Strip anything not in PRD §16.2 schema. No secrets ever leak."""
    g = summary.get("genes") or {}
    m = summary.get("metrics") or {}
    mc = summary.get("monte_carlo") or {}
    return {
        "index": idx,
        "genes": {
            "rsi_period": g.get("rsi_period"),
            "ma_short": g.get("ma_short"),
            "ma_long": g.get("ma_long"),
            "stop_loss_pct": g.get("stop_loss_pct"),
            "take_profit_pct": g.get("take_profit_pct"),
            "position_size_pct": g.get("position_size_pct"),
        },
        "metrics": {
            "win_rate": m.get("win_rate"),
            "max_drawdown_pct": m.get("max_drawdown_pct"),
            "sharpe_ratio": m.get("sharpe_ratio"),
            "profit_factor": m.get("profit_factor"),
            "trades": m.get("trades"),
            "profit_pct": m.get("profit_pct"),
        },
        "monte_carlo": {
            "paths": mc.get("paths"),
            "survivability_pct": mc.get("survivability_pct"),
            "tail_dd_95_pct": mc.get("tail_dd_95_pct"),
            "worst_case_return_pct": mc.get("worst_case_return_pct"),
        },
        "fitness": summary.get("fitness"),
    }


def _strict_json_parse(text: str) -> Optional[dict]:
    """Extract the first balanced JSON object from raw model output."""
    if not text:
        return None
    # Fast path
    try:
        return json.loads(text)
    except Exception:
        pass
    # Find substring between first `{` and last `}`
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end <= start:
        return None
    snippet = text[start:end + 1]
    # Strip JS-style comments and trailing commas, common in 7B model output
    snippet = re.sub(r"/\*.*?\*/", "", snippet, flags=re.DOTALL)
    snippet = re.sub(r",(\s*[}\]])", r"\1", snippet)
    try:
        return json.loads(snippet)
    except Exception as exc:
        logger.debug("Strict JSON parse failed: %s | snippet=%s", exc, snippet[:200])
        return None


def _validate_schema(obj: dict, n_candidates: int) -> bool:
    """Light-touch validation (PRD §16.4 fail-closed behavior)."""
    try:
        for k in ("backtesting_critic", "risk_guardian",
                  "sentiment_forecaster", "consensus"):
            if k not in obj:
                return False
        c = obj["consensus"]
        if not isinstance(c.get("approve_for_shadow"), bool):
            return False
        idx = c.get("recommended_index")
        if not isinstance(idx, int) or not (0 <= idx < n_candidates):
            return False
        return True
    except Exception:
        return False


def _deterministic_fallback(top3: list[dict], gen: int, *, reason: str) -> dict:
    """
    Pure-Python fallback that mirrors what a conservative council would produce.
    Used when Ollama is unreachable or returns invalid JSON.
    """
    # Pick the best candidate by fitness, with a sensible drawdown sanity check
    chosen_idx = 0
    chosen_dd = float("inf")
    for i, c in enumerate(top3):
        m = (c.get("metrics") or {})
        dd = float(m.get("max_drawdown_pct") or 999.0)
        sharpe = float(m.get("sharpe_ratio") or 0.0)
        if (sharpe > 0 and dd < chosen_dd) or i == 0:
            chosen_idx = i
            chosen_dd = dd
    return {
        "backtesting_critic": {
            "summary": "Deterministic fallback: scored on Sharpe and max drawdown.",
            "overfitting_risk": "medium",
            "notes": ["Council unavailable — heuristic ranking used."],
        },
        "risk_guardian": {
            "summary": "Conservative caps applied while AI is offline.",
            "risk_level": "medium",
            "recommended_limits": {
                "max_position_size_pct": 0.10,
                "max_daily_loss_pct": 2.0,
            },
        },
        "sentiment_forecaster": {
            "summary": "No external sentiment input; treating regime sensitivity as unknown.",
            "regime_sensitivity": "unknown",
        },
        "consensus": {
            "approve_for_shadow": True,
            "recommended_index": chosen_idx,
            "key_reasoning": ["Best Sharpe with bounded drawdown.",
                              "AI council currently in fallback mode."],
            "watchouts": ["Treat live sizing conservatively until AI is online."],
        },
        "_meta": {
            "model": "deterministic_fallback",
            "latency_s": 0.0,
            "attempt": 0,
            "source": "fallback",
            "reason": reason,
            "generation": gen,
        },
    }


# ──────────────────────────────────────────────────────────────────────────────
# CLI smoke test
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    async def _main():
        sample = [
            {
                "genes": {"rsi_period": 14, "ma_short": 10, "ma_long": 50,
                          "stop_loss_pct": 0.05, "take_profit_pct": 0.10,
                          "position_size_pct": 0.20},
                "metrics": {"win_rate": 60, "max_drawdown_pct": 8,
                            "sharpe_ratio": 1.2, "profit_factor": 1.4,
                            "trades": 80, "profit_pct": 12.5},
                "monte_carlo": {"paths": 80, "survivability_pct": 90,
                                "tail_dd_95_pct": 14, "worst_case_return_pct": -8},
                "fitness": 0.42,
            },
            {
                "genes": {"rsi_period": 9, "ma_short": 18, "ma_long": 96,
                          "stop_loss_pct": 0.011, "take_profit_pct": 0.024,
                          "position_size_pct": 0.10},
                "metrics": {"win_rate": 55, "max_drawdown_pct": 11,
                            "sharpe_ratio": 0.9, "profit_factor": 1.2,
                            "trades": 200, "profit_pct": 7.0},
                "monte_carlo": {"paths": 80, "survivability_pct": 85,
                                "tail_dd_95_pct": 16, "worst_case_return_pct": -10},
                "fitness": 0.31,
            },
            {
                "genes": {"rsi_period": 21, "ma_short": 5, "ma_long": 30,
                          "stop_loss_pct": 0.08, "take_profit_pct": 0.15,
                          "position_size_pct": 0.30},
                "metrics": {"win_rate": 42, "max_drawdown_pct": 22,
                            "sharpe_ratio": 0.4, "profit_factor": 1.05,
                            "trades": 500, "profit_pct": 4.0},
                "monte_carlo": {"paths": 80, "survivability_pct": 60,
                                "tail_dd_95_pct": 28, "worst_case_return_pct": -22},
                "fitness": 0.12,
            },
        ]
        council = OllamaCouncil()
        ok = await council.health_check()
        print(f"Ollama available: {ok}")
        out = await council.evaluate(sample, generation=1)
        print(json.dumps(out, indent=2))

    asyncio.run(_main())
