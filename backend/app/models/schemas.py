from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from datetime import datetime


class ChatMessageRequest(BaseModel):
    user_id: str
    message: str

class ChatMessageResponse(BaseModel):
    bot_message: str
    step: int
    total_steps: int = 7
    profile_so_far: Dict[str, Any] = {}
    is_complete: bool = False
    quick_replies: Optional[List[str]] = None

class FinalizeRequest(BaseModel):
    user_id: str
    profile: Dict[str, Any]

class FinalizeResponse(BaseModel):
    ok: bool = True
    profile_id: str


class EvolutionStartRequest(BaseModel):
    user_id: str
    profile_id: str

class EvolutionStartResponse(BaseModel):
    evolution_id: str
    status: str = "running"

class EvolutionStatusResponse(BaseModel):
    status: str
    current_generation: int
    completed_generations: int
    top_3: Optional[List[Dict[str, Any]]] = None
    alpha_gene: Optional[Dict[str, Any]] = None


class TradingStartRequest(BaseModel):
    user_id: str
    alpha_gene_id: str

class TradingStartResponse(BaseModel):
    ok: bool = True
    trading_session_id: str

class TradeRecord(BaseModel):
    id: str
    timestamp: str
    side: str
    qty: float
    price: float
    pnl: Optional[float] = None
    reason: str

class PortfolioResponse(BaseModel):
    cash: float
    position: Optional[Dict[str, Any]] = None
    trades: List[Dict[str, Any]] = []
    equity_curve: List[float] = []
    total_pnl: float = 0.0
    daily_pnl: float = 0.0
    win_rate: float = 0.0
    wins: int = 0
    total_closed: int = 0

class GeneVector(BaseModel):
    rsi_oversold: float = Field(..., ge=15, le=45)
    rsi_overbought: float = Field(..., ge=55, le=85)
    ma_short: int = Field(..., ge=5, le=30)
    ma_long: int = Field(..., ge=30, le=200)
    stop_loss_pct: float = Field(..., ge=0.005, le=0.05)
    take_profit_pct: float = Field(..., ge=0.005, le=0.10)
    position_size_pct: float = Field(..., ge=0.05, le=0.40)
    sentiment_weight: float = Field(..., ge=0.0, le=1.0)
