"""
Chat onboarding router — 7-question deterministic state machine.
No LLM required for MVP.
"""
import uuid
from fastapi import APIRouter
from app.models.schemas import ChatMessageRequest, ChatMessageResponse, FinalizeRequest, FinalizeResponse
from app.utils.logger import get_logger

log = get_logger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat"])

# In-memory session state (single-user MVP)
_sessions: dict = {}

QUESTIONS = [
    {
        "step": 1,
        "key": "name",
        "bot_message": "Hey! I'm EvoTrade. Before I evolve a strategy for you, I need to understand your trading profile. Let's start simple — what's your name?",
        "quick_replies": None,
    },
    {
        "step": 2,
        "key": "capital",
        "bot_message": "Got it, {name}! How much capital do you want to start with? (e.g. 50000 for ₹50,000 or $50,000)",
        "quick_replies": None,
    },
    {
        "step": 3,
        "key": "risk_level",
        "bot_message": "What's your risk tolerance?",
        "quick_replies": ["Conservative", "Moderate", "Aggressive"],
    },
    {
        "step": 4,
        "key": "experience",
        "bot_message": "How would you describe your trading experience?",
        "quick_replies": ["Beginner", "Intermediate", "Advanced"],
    },
    {
        "step": 5,
        "key": "asset_pref",
        "bot_message": "Which asset class are you interested in? (For MVP, Crypto is fully functional)",
        "quick_replies": ["Crypto", "Indian Equities", "Both"],
    },
    {
        "step": 6,
        "key": "daily_loss_limit",
        "bot_message": "What's your daily loss limit comfort level? (e.g. 5 for 5% of capital)",
        "quick_replies": ["2%", "5%", "10%"],
    },
    {
        "step": 7,
        "key": "strategy_pref",
        "bot_message": "Any specific strategy preference? (optional — type 'none' to skip)",
        "quick_replies": ["Momentum", "Mean Reversion", "None"],
    },
]


def _parse_capital(text: str) -> float:
    import re
    text = text.replace(",", "").replace("₹", "").replace("$", "").strip()
    nums = re.findall(r"\d+(?:\.\d+)?", text)
    if nums:
        val = float(nums[0])
        # Convert shorthand like "50k" → 50000
        if "k" in text.lower():
            val *= 1000
        return val
    return 50000.0


def _parse_loss_limit(text: str) -> float:
    import re
    text = text.replace("%", "").strip()
    nums = re.findall(r"\d+(?:\.\d+)?", text)
    return float(nums[0]) / 100 if nums else 0.05


def _get_or_create_session(user_id: str) -> dict:
    if user_id not in _sessions:
        _sessions[user_id] = {"step": 0, "profile": {}}
    return _sessions[user_id]


def _advance(session: dict, user_text: str) -> ChatMessageResponse:
    step = session["step"]
    profile = session["profile"]

    # Process the answer to the previous question
    if step > 0 and step <= len(QUESTIONS):
        q = QUESTIONS[step - 1]
        key = q["key"]
        if key == "capital":
            profile[key] = _parse_capital(user_text)
        elif key == "daily_loss_limit":
            profile[key] = _parse_loss_limit(user_text)
        elif key == "risk_level":
            mapping = {"conservative": "conservative", "moderate": "moderate", "aggressive": "aggressive"}
            profile[key] = mapping.get(user_text.lower().strip(), user_text.lower().strip())
        elif key == "experience":
            profile[key] = user_text.strip().capitalize()
        elif key == "asset_pref":
            profile[key] = user_text.strip()
        elif key == "strategy_pref":
            profile[key] = user_text.strip() if user_text.lower() not in ("none", "skip", "") else "none"
        else:
            profile[key] = user_text.strip()

    session["step"] += 1
    next_step = session["step"]

    if next_step > len(QUESTIONS):
        # All done — build summary
        cap = profile.get("capital", 50000)
        symbol = "₹" if profile.get("asset_pref", "Crypto") != "Both" else "₹/$"
        summary = (
            f"Perfect! Here's what I'll work with:\n\n"
            f"• **Name:** {profile.get('name', 'Trader')}\n"
            f"• **Capital:** {symbol}{cap:,.0f}\n"
            f"• **Risk:** {profile.get('risk_level', 'Moderate').capitalize()}\n"
            f"• **Asset:** {'BTC/USDT (Crypto)' if 'Crypto' in profile.get('asset_pref','Crypto') else profile.get('asset_pref')}\n"
            f"• **Experience:** {profile.get('experience', 'Beginner')}\n\n"
            f"I'm now going to evolve a custom trading strategy across 5 generations. Each generation spawns 10 candidate strategies. Only the strongest 3 survive. Ready to begin? 🧬"
        )
        return ChatMessageResponse(
            bot_message=summary,
            step=len(QUESTIONS),
            total_steps=len(QUESTIONS),
            profile_so_far=profile,
            is_complete=True,
            quick_replies=None,
        )

    q = QUESTIONS[next_step - 1]
    bot_msg = q["bot_message"].format(**profile)
    return ChatMessageResponse(
        bot_message=bot_msg,
        step=next_step,
        total_steps=len(QUESTIONS),
        profile_so_far=dict(profile),
        is_complete=False,
        quick_replies=q.get("quick_replies"),
    )


@router.post("/message", response_model=ChatMessageResponse)
async def chat_message(req: ChatMessageRequest):
    session = _get_or_create_session(req.user_id)

    if session["step"] == 0:
        # First message triggers first question
        q0 = QUESTIONS[0]
        session["step"] = 1
        return ChatMessageResponse(
            bot_message=q0["bot_message"],
            step=1,
            total_steps=len(QUESTIONS),
            profile_so_far={},
            is_complete=False,
            quick_replies=q0.get("quick_replies"),
        )

    return _advance(session, req.message)


@router.post("/finalize", response_model=FinalizeResponse)
async def finalize(req: FinalizeRequest):
    profile_id = str(uuid.uuid4())
    # Persist to SQLite
    try:
        import aiosqlite
        from app.config import SQLITE_PATH
        async with aiosqlite.connect(SQLITE_PATH) as db:
            p = req.profile
            await db.execute(
                "INSERT OR REPLACE INTO user_profiles (id, name, capital, risk_level, experience, asset_pref, daily_loss_limit, strategy_pref) VALUES (?,?,?,?,?,?,?,?)",
                (profile_id, p.get("name"), p.get("capital"), p.get("risk_level"),
                 p.get("experience"), p.get("asset_pref"), p.get("daily_loss_limit"), p.get("strategy_pref"))
            )
            await db.commit()
    except Exception as e:
        log.warning(f"DB persist error: {e}")
    log.info(f"Profile finalized: {profile_id}")
    return FinalizeResponse(ok=True, profile_id=profile_id)
