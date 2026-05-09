"""
Mock AI Council — three deterministic agent roles for MVP.
# TODO: Replace with Claude API calls in production (claude-opus-4-7 recommended)
PAPER TRADING ONLY.
"""
from typing import Dict, Any
from app.utils.logger import get_logger

log = get_logger(__name__)


def evaluate(
    genes: Dict[str, float],
    backtest: Dict[str, Any],
    mc_results: Dict[str, Any],
    regime: str,
) -> Dict[str, Any]:
    n_trades = backtest.get("n_trades", 0)
    max_dd = backtest.get("max_drawdown", 0.15)
    survival_rate = mc_results.get("survival_rate", 0.5)

    # Agent 1: Backtesting Critic — penalises overfitting via trade sparsity
    if n_trades >= 20:
        overfit_risk = "low"
        critic_score = 0.90
    elif n_trades >= 10:
        overfit_risk = "medium"
        critic_score = 0.60
    else:
        overfit_risk = "high"
        critic_score = 0.30

    # Agent 2: Risk Guardian — based on drawdown vs position size
    guardian_score = max(0.0, 1.0 - (max_dd / 0.30))
    guardian_verdict = "acceptable" if guardian_score > 0.6 else "concerning"

    # Agent 3: Sentiment Forecaster — regime compatibility
    regime_fit_map = {
        "BULL": 0.85,
        "SIDEWAYS": 0.65,
        "BEAR": 0.55,
        "CRASH": 0.40,
    }
    regime_fit = regime_fit_map.get(regime, 0.70)
    regime_suitability = "well-suited" if regime_fit > 0.70 else "sub-optimal"

    composite = 0.40 * critic_score + 0.35 * guardian_score + 0.25 * regime_fit

    return {
        "critic": {
            "score": critic_score,
            "verdict": overfit_risk,
            "note": f"Strategy made {n_trades} trades — {overfit_risk} overfit risk.",
        },
        "guardian": {
            "score": guardian_score,
            "note": f"Max drawdown {max_dd * 100:.1f}% — {guardian_verdict}.",
        },
        "forecaster": {
            "score": regime_fit,
            "note": f"In current {regime} regime, this strategy is {regime_suitability}.",
        },
        "composite_score": composite,
    }
