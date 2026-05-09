"""Evolution router — starts GA pipeline, exposes status endpoint."""
import asyncio
import uuid
from typing import Dict, Any
from fastapi import APIRouter, HTTPException
from app.models.schemas import EvolutionStartRequest, EvolutionStartResponse, EvolutionStatusResponse
from app.utils.logger import get_logger

log = get_logger(__name__)
router = APIRouter(prefix="/api/evolution", tags=["evolution"])

# In-memory evolution state (single-session MVP)
_evolutions: Dict[str, Dict[str, Any]] = {}


@router.post("/start", response_model=EvolutionStartResponse)
async def start_evolution(req: EvolutionStartRequest):
    from app.services.evolution_engine import run_evolution
    from app.services.market_data import market_data_service
    from app.services.hmm_regime import hmm_detector
    from app.services.event_bus import event_bus

    evolution_id = str(uuid.uuid4())
    _evolutions[evolution_id] = {
        "status": "running",
        "current_generation": 0,
        "completed_generations": 0,
        "top_3": None,
        "alpha_gene": None,
        "profile_id": req.profile_id,
    }

    # Fetch user profile from DB
    profile: Dict[str, Any] = {}
    try:
        import aiosqlite
        from app.config import SQLITE_PATH
        async with aiosqlite.connect(SQLITE_PATH) as db:
            async with db.execute(
                "SELECT name, capital, risk_level, experience, asset_pref, daily_loss_limit, strategy_pref FROM user_profiles WHERE id=?",
                (req.profile_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    profile = {
                        "name": row[0], "capital": row[1], "risk_level": row[2],
                        "experience": row[3], "asset_pref": row[4],
                        "daily_loss_limit": row[5], "strategy_pref": row[6],
                    }
    except Exception as e:
        log.warning(f"Profile fetch error: {e}")
        profile = {"capital": 50000.0, "risk_level": "moderate"}

    historical_df = market_data_service.load_historical_df(days=90)
    regime = hmm_detector.current_regime
    initial_price = market_data_service.get_last_price() or 60000.0

    async def track_and_run():
        state = _evolutions[evolution_id]
        try:
            async def publish_with_tracking(event_type: str, data: Dict[str, Any]):
                if event_type == "GEN_STARTED":
                    state["current_generation"] = data.get("generation", 0)
                elif event_type == "GEN_COMPLETED":
                    state["completed_generations"] = data.get("generation", 0)
                elif event_type == "EVOLUTION_COMPLETE":
                    state["status"] = "complete"
                    state["top_3"] = data.get("final_top_3")
                    state["alpha_gene"] = data.get("best_alpha_gene")
                await event_bus.publish(event_type, data)

            result = await run_evolution(
                evolution_id=evolution_id,
                profile=profile,
                historical_df=historical_df,
                regime=regime,
                publish=publish_with_tracking,
                initial_price=initial_price,
            )
            state["top_3"] = result["final_top_3"]
            state["alpha_gene"] = result["best_alpha_gene"]
            state["status"] = "complete"
        except Exception as e:
            log.error(f"Evolution error: {e}", exc_info=True)
            state["status"] = "error"

    asyncio.create_task(track_and_run())
    log.info(f"Evolution {evolution_id} started")
    return EvolutionStartResponse(evolution_id=evolution_id, status="running")


@router.get("/{evolution_id}/status", response_model=EvolutionStatusResponse)
async def evolution_status(evolution_id: str):
    state = _evolutions.get(evolution_id)
    if not state:
        raise HTTPException(status_code=404, detail="Evolution not found")
    return EvolutionStatusResponse(
        status=state["status"],
        current_generation=state["current_generation"],
        completed_generations=state["completed_generations"],
        top_3=state.get("top_3"),
        alpha_gene=state.get("alpha_gene"),
    )
