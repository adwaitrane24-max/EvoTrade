"""
config.py — Environment variable loader and application-wide settings.
All secrets are sourced exclusively from .env; nothing is hardcoded here.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Resolve .env relative to this file's directory
_ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH)


def _require(key: str) -> str:
    """Return env var or raise a descriptive error if missing."""
    value = os.getenv(key)
    if not value:
        raise EnvironmentError(
            f"Required environment variable '{key}' is not set. "
            f"Copy backend/.env.example to backend/.env and fill in your credentials."
        )
    return value


def _optional(key: str, default: str) -> str:
    return os.getenv(key, default)


class Config:
    """Central configuration object. Instantiated once at import time."""

    # --- API Keys (all optional — paper trading works without any of these) ---
    ANTHROPIC_API_KEY: str = _optional("ANTHROPIC_API_KEY", "")
    BINANCE_API_KEY: str = _optional("BINANCE_API_KEY", "")
    BINANCE_API_SECRET: str = _optional("BINANCE_API_SECRET", "")
    NEWS_API_KEY: str = _optional("NEWS_API_KEY", "")

    # --- Trading Defaults ---
    DEFAULT_SYMBOL: str = _optional("DEFAULT_SYMBOL", "BTC/USDT")
    DEFAULT_RISK_PROFILE: str = _optional("DEFAULT_RISK_PROFILE", "medium")

    # --- Genetic Algorithm Defaults ---
    GA_POPULATION_SIZE: int = 10
    GA_MAX_GENERATIONS: int = 50
    GA_CONVERGENCE_WINDOW: int = 5

    # --- Monte Carlo ---
    MONTE_CARLO_PATHS: int = 1000
    MONTE_CARLO_HORIZON_DAYS: int = 30

    # --- Safety ---
    MAX_DAILY_LOSS_PCT: float = 0.05   # 5 % of account
    MAX_POSITION_SIZE_PCT: float = 0.20  # 20 % of account

    # --- WebSocket ---
    WS_HOST: str = _optional("WS_HOST", "0.0.0.0")
    WS_PORT: int = int(_optional("WS_PORT", "8000"))


config = Config()


if __name__ == "__main__":
    print("Config loaded successfully.")
    print(f"  Symbol          : {config.DEFAULT_SYMBOL}")
    print(f"  Risk profile    : {config.DEFAULT_RISK_PROFILE}")
    print(f"  Population size : {config.GA_POPULATION_SIZE}")
