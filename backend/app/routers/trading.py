"""Trading router — start/pause/stop paper trading, portfolio snapshot."""
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.models.schemas import TradingStartRequest, TradingStartResponse, PortfolioResponse
from app.utils.logger import get_logger

log = get_logger(__name__)
router = APIRouter(prefix="/api/trading", tags=["trading"])

# In-memory alpha gene store (keyed by alpha_gene_id)
_alpha_genes: dict = {}


def register_alpha_gene(alpha_gene_id: str, gene: dict, profile: dict):
    """Called from evolution router when user confirms an alpha gene."""
    _alpha_genes[alpha_gene_id] = {"gene": gene, "profile": profile}


@router.post("/start", response_model=TradingStartResponse)
async def start_trading(req: TradingStartRequest):
    from app.services.paper_trader import paper_trader
    from app.services.market_data import market_data_service
    from app.services.event_bus import event_bus

    session_id = str(uuid.uuid4())

    # Look up gene — frontend stores the full gene in the request body (for MVP simplicity)
    # The alpha_gene_id is passed; we look it up from the evolution result stored in memory
    alpha_entry = _alpha_genes.get(req.alpha_gene_id)
    if not alpha_entry:
        # Fallback: use a default gene for demo resilience
        log.warning(f"Alpha gene {req.alpha_gene_id} not found — using defaults")
        alpha_gene = {
            "rsi_oversold": 30.0, "rsi_overbought": 70.0,
            "ma_short": 9, "ma_long": 21,
            "stop_loss_pct": 0.02, "take_profit_pct": 0.04,
            "position_size_pct": 0.20, "sentiment_weight": 0.5,
        }
        capital = 50000.0
    else:
        alpha_gene = alpha_entry["gene"]
        capital = float(alpha_entry["profile"].get("capital", 50000))

    paper_trader.start(
        alpha_gene=alpha_gene,
        capital=capital,
        session_id=session_id,
        event_bus=event_bus,
        market_service=market_data_service,
    )
    log.info(f"Paper trading started — session {session_id}")
    return TradingStartResponse(ok=True, trading_session_id=session_id)


@router.post("/pause")
async def pause_trading():
    from app.services.paper_trader import paper_trader
    paper_trader.pause()
    return {"ok": True}


@router.post("/resume")
async def resume_trading():
    from app.services.paper_trader import paper_trader
    paper_trader.resume()
    return {"ok": True}


@router.post("/emergency-stop")
async def emergency_stop():
    from app.services.paper_trader import paper_trader
    await paper_trader.emergency_stop()
    return {"ok": True}


@router.get("/portfolio", response_model=PortfolioResponse)
async def get_portfolio():
    from app.services.paper_trader import paper_trader
    return PortfolioResponse(**paper_trader.get_portfolio())


def store_alpha_gene(alpha_gene_id: str, gene: dict, profile: dict):
    _alpha_genes[alpha_gene_id] = {"gene": gene, "profile": profile}


class StoreAlphaRequest(BaseModel):
    alpha_gene_id: str
    gene: dict
    profile: dict = {}

@router.post("/store-alpha")
async def store_alpha(req: StoreAlphaRequest):
    _alpha_genes[req.alpha_gene_id] = {"gene": req.gene, "profile": req.profile}
    return {"ok": True}
