import aiosqlite
from app.config import SQLITE_PATH
from app.utils.logger import get_logger

log = get_logger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS user_profiles (
    id TEXT PRIMARY KEY,
    name TEXT,
    capital REAL,
    risk_level TEXT,
    experience TEXT,
    asset_pref TEXT,
    daily_loss_limit REAL,
    strategy_pref TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS evolution_runs (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    status TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chromosomes (
    id TEXT PRIMARY KEY,
    evolution_id TEXT,
    generation INTEGER,
    genes TEXT,
    fitness REAL,
    survived BOOLEAN,
    is_alpha BOOLEAN
);

CREATE TABLE IF NOT EXISTS trades (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    timestamp TIMESTAMP,
    side TEXT,
    qty REAL,
    price REAL,
    pnl REAL,
    reason TEXT
);
"""

async def init_db():
    async with aiosqlite.connect(SQLITE_PATH) as db:
        await db.executescript(SCHEMA)
        await db.commit()
    log.info(f"SQLite database initialised at {SQLITE_PATH}")

async def get_db():
    return aiosqlite.connect(SQLITE_PATH)
