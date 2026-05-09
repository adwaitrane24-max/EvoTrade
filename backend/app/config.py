import os
from dotenv import load_dotenv

load_dotenv()

BINANCE_WS_URL = os.getenv("BINANCE_WS_URL", "wss://stream.binance.com:9443/ws/btcusdt@kline_1m")
SQLITE_PATH = os.getenv("SQLITE_PATH", "./evotrade.db")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
DEBUG = os.getenv("DEBUG", "true").lower() == "true"

SYMBOL_YFINANCE = "BTC-USD"
SYMBOL_DISPLAY = "BTC/USDT"
CANDLE_BUFFER_SIZE = 500
HMM_HISTORY_DAYS = 90
HMM_MODEL_PATH = "./models/hmm.pkl"

GA_POPULATION = 10
GA_GENERATIONS = 5
GA_CXPB = 0.7
GA_MUTPB_START = 0.3
GA_MUTPB_DECAY = 0.05

MC_PATHS = 50
MC_STEPS = 100
MC_SURVIVAL_THRESHOLD = 0.70  # portfolio must stay above 70% of initial capital

CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
]
