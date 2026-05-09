"""
secure_exec.py — TEE-inspired Secure Execution Layer (PRD §8).

This module is the ONLY component permitted to:
  • decrypt broker API credentials (in memory only, zeroized after use)
  • place orders against a broker
  • enforce hard risk limits (PRD §8.6)
  • write tamper-evident audit logs (PRD §18.2 / §26.2)
  • honor the emergency kill switch (PRD §8.7)

Design rules:
  • AI never imports this module.
  • UI never touches this module directly — only via the FastAPI orchestrator.
  • The encryption key MUST live in env / vault. Never in code.
  • Plaintext secrets MUST never be logged.
  • Every order intent gets an audit_id; every audit row carries a hash chain.

For MVP: AES-256-GCM via `cryptography`. The broker call defaults to the local
PaperBroker; pass any object with `.place_order(intent) -> dict` to swap it.
"""

from __future__ import annotations

import asyncio
import base64
import contextlib
import ctypes
import hashlib
import json
import logging
import os
import secrets
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Audit log (append-only, tamper-evident hash chain)
# ──────────────────────────────────────────────────────────────────────────────

_AUDIT_PATH = Path(__file__).parent.parent.parent / "outputs" / "audit_log.jsonl"


@dataclass
class AuditRecord:
    audit_id: str
    ts: str
    event_type: str
    payload: dict
    prev_hash: str
    hash: str = ""

    def serialized_for_hash(self) -> bytes:
        return json.dumps(
            {"audit_id": self.audit_id, "ts": self.ts,
             "event_type": self.event_type, "payload": self.payload,
             "prev_hash": self.prev_hash},
            sort_keys=True, separators=(",", ":"),
        ).encode("utf-8")

    def to_jsonl(self) -> str:
        return json.dumps(asdict(self), sort_keys=True) + "\n"


class AuditLog:
    """
    Append-only JSONL audit log with a tamper-evident SHA-256 hash chain.
    Each row's `hash` covers the row's serialized contents AND the previous
    row's `hash`, so any after-the-fact edit invalidates everything that
    follows it.
    """

    def __init__(self, path: Path = _AUDIT_PATH) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()
        self._last_hash = self._tail_hash()

    def _tail_hash(self) -> str:
        if not self.path.exists():
            return "0" * 64
        last_hash = "0" * 64
        try:
            with self.path.open("r", encoding="utf-8") as f:
                for line in f:
                    try:
                        row = json.loads(line)
                        last_hash = row.get("hash", last_hash)
                    except Exception:
                        pass
        except Exception as exc:
            logger.warning("AuditLog tail read failed: %s", exc)
        return last_hash

    async def append(self, event_type: str, payload: dict) -> AuditRecord:
        async with self._lock:
            audit_id = str(uuid.uuid4())
            ts = datetime.now(timezone.utc).isoformat()
            record = AuditRecord(audit_id=audit_id, ts=ts,
                                 event_type=event_type,
                                 payload=_redact(payload),
                                 prev_hash=self._last_hash)
            digest = hashlib.sha256(record.serialized_for_hash()).hexdigest()
            record.hash = digest
            with self.path.open("a", encoding="utf-8") as f:
                f.write(record.to_jsonl())
            self._last_hash = digest

            # Mirror to Supabase (best-effort; never blocks the write)
            try:
                from persistence.supabase_client import supabase
                asyncio.create_task(supabase().insert_audit_log(
                    audit_id=audit_id, event_type=event_type,
                    payload=record.payload, prev_hash=record.prev_hash,
                    hash=digest,
                ))
            except Exception:
                pass
            return record


def _redact(payload: dict) -> dict:
    """Strip well-known sensitive keys before they ever hit disk (PRD §24.3)."""
    REDACT = {
        "api_key", "api_secret", "secret", "password", "token",
        "private_key", "wallet_seed", "mnemonic", "binance_api_key",
        "binance_api_secret", "anthropic_api_key", "ollama_api_key",
        "credentials", "creds",
    }
    if not isinstance(payload, dict):
        return payload  # type: ignore[return-value]
    out = {}
    for k, v in payload.items():
        if k.lower() in REDACT:
            out[k] = "<redacted>"
        elif isinstance(v, dict):
            out[k] = _redact(v)
        else:
            out[k] = v
    return out


# ──────────────────────────────────────────────────────────────────────────────
# Secret vault (AES-256-GCM)
# ──────────────────────────────────────────────────────────────────────────────

class SecretVault:
    """
    Encrypts and decrypts broker credentials using AES-256-GCM.

    The encryption key (32 bytes) MUST be supplied via the environment variable
    `EVOTRADE_VAULT_KEY` (base64) or passed explicitly. NEVER hard-code the key.
    The vault never logs plaintext.
    """

    KEY_ENV = "EVOTRADE_VAULT_KEY"
    NONCE_LEN = 12  # GCM standard

    def __init__(self, key: Optional[bytes] = None) -> None:
        self._key = key or self._load_key_from_env()
        if len(self._key) != 32:
            raise ValueError("Vault key must be exactly 32 bytes (256 bits).")
        self._aead = AESGCM(self._key)

    @classmethod
    def _load_key_from_env(cls) -> bytes:
        b64 = os.getenv(cls.KEY_ENV)
        if not b64:
            # Generate a one-shot ephemeral key. Useful for dev only — warn loud.
            ephemeral = AESGCM.generate_key(bit_length=256)
            logger.warning(
                "Using EPHEMERAL vault key — set EVOTRADE_VAULT_KEY for persistence."
            )
            return ephemeral
        try:
            return base64.b64decode(b64)
        except Exception as exc:
            raise ValueError(f"Invalid {cls.KEY_ENV}: {exc}") from None

    @classmethod
    def generate_new_key(cls) -> str:
        """Helper: create a new base64-encoded 256-bit key for env."""
        return base64.b64encode(AESGCM.generate_key(bit_length=256)).decode()

    def encrypt(self, plaintext: str, *, aad: Optional[str] = None) -> dict:
        """Encrypt a UTF-8 plaintext string. Returns ciphertext envelope."""
        nonce = secrets.token_bytes(self.NONCE_LEN)
        aad_bytes = aad.encode() if aad else None
        ct = self._aead.encrypt(nonce, plaintext.encode("utf-8"), aad_bytes)
        return {
            "v": 1,
            "alg": "AES-256-GCM",
            "nonce": base64.b64encode(nonce).decode(),
            "ct":    base64.b64encode(ct).decode(),
            "aad":   aad,
        }

    def decrypt(self, envelope: dict) -> str:
        """Decrypt — caller is responsible for using the plaintext briefly."""
        nonce = base64.b64decode(envelope["nonce"])
        ct = base64.b64decode(envelope["ct"])
        aad_bytes = envelope.get("aad").encode() if envelope.get("aad") else None
        plaintext = self._aead.decrypt(nonce, ct, aad_bytes)
        try:
            return plaintext.decode("utf-8")
        finally:
            # Best-effort buffer wipe — Python strings are immutable so this
            # is more about hygiene than guarantees.
            with contextlib.suppress(Exception):
                ctypes.memset(id(plaintext) + 32, 0, len(plaintext))

    @contextlib.contextmanager
    def borrow_decrypted(self, envelope: dict):
        """Context manager: auto-discard plaintext when block exits."""
        plaintext = self.decrypt(envelope)
        try:
            yield plaintext
        finally:
            del plaintext


# ──────────────────────────────────────────────────────────────────────────────
# Risk limits (hard guards — PRD §8.6)
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class RiskLimits:
    max_daily_loss_pct: float = 5.0          # halt new orders if daily PnL ≤ -5%
    max_position_size_pct: float = 0.30      # 30% of capital per single position
    max_open_positions: int = 5
    max_orders_per_minute: int = 30
    max_slippage_bps: int = 50               # caller can request lower
    max_leverage: float = 1.0                # spot only for MVP


@dataclass
class RiskState:
    daily_pnl_pct: float = 0.0
    open_positions: int = 0
    orders_this_minute: int = 0
    last_minute_window: float = 0.0
    breached_reason: Optional[str] = None


# ──────────────────────────────────────────────────────────────────────────────
# Order intent (PRD §8.4)
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class OrderIntent:
    user_id: str
    symbol: str
    side: str                # "BUY" | "SELL"
    type: str                # "MARKET" | "LIMIT"
    qty: float
    risk: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)

    def sanitized(self) -> dict:
        d = asdict(self)
        d["risk"] = dict(self.risk)
        d["metadata"] = dict(self.metadata)
        return d


# ──────────────────────────────────────────────────────────────────────────────
# Secure Execution Layer
# ──────────────────────────────────────────────────────────────────────────────

BrokerCallable = Callable[[OrderIntent], Awaitable[dict]]


class SecureExecutionLayer:
    """
    The single trust boundary between intent and execution.

    Public surface — anything that places orders MUST go through `place_order`.
    """

    def __init__(
        self,
        vault: Optional[SecretVault] = None,
        broker: Optional[BrokerCallable] = None,
        limits: Optional[RiskLimits] = None,
        audit_log: Optional[AuditLog] = None,
    ) -> None:
        self.vault = vault or SecretVault()
        self.audit = audit_log or AuditLog()
        self.limits = limits or RiskLimits()
        self.state = RiskState()
        self._broker: Optional[BrokerCallable] = broker
        self._kill_switch: bool = False
        self._initial_capital: float = 10_000.0

    # ── credential management ────────────────────────────────────────────────

    def store_credentials(self, *, user_id: str, api_key: str,
                          api_secret: str) -> dict:
        """Encrypt + return ciphertext envelope. Plaintext is never persisted."""
        bundle = json.dumps({"k": api_key, "s": api_secret})
        envelope = self.vault.encrypt(bundle, aad=user_id)
        envelope["user_id"] = user_id
        return envelope

    @contextlib.contextmanager
    def _with_credentials(self, envelope: dict, user_id: str):
        """Decrypt creds in-memory, expose to broker, then drop."""
        with self.vault.borrow_decrypted(envelope) as plaintext:
            try:
                creds = json.loads(plaintext)
            except Exception:
                raise RuntimeError("Corrupt credential envelope")
            yield creds
            # creds dict goes out of scope here

    # ── kill switch ──────────────────────────────────────────────────────────

    async def trigger_kill_switch(self, reason: str = "user_initiated") -> None:
        self._kill_switch = True
        await self.audit.append("kill_switch.triggered", {"reason": reason})
        logger.critical("KILL SWITCH TRIGGERED: %s", reason)

    async def clear_kill_switch(self, reason: str = "manual_clear") -> None:
        self._kill_switch = False
        await self.audit.append("kill_switch.cleared", {"reason": reason})

    @property
    def kill_switch_active(self) -> bool:
        return self._kill_switch

    # ── pre-trade risk check ─────────────────────────────────────────────────

    def _check_risk(self, intent: OrderIntent) -> Optional[str]:
        """Return error string on rejection, None on pass."""
        if self._kill_switch:
            return "kill_switch_active"

        # Rate limit
        now = time.time()
        if now - self.state.last_minute_window > 60:
            self.state.last_minute_window = now
            self.state.orders_this_minute = 0
        if self.state.orders_this_minute >= self.limits.max_orders_per_minute:
            return "max_orders_per_minute_exceeded"

        # Daily loss
        if self.state.daily_pnl_pct <= -self.limits.max_daily_loss_pct:
            return f"daily_loss_limit_{self.limits.max_daily_loss_pct}pct"

        # Open positions
        if self.state.open_positions >= self.limits.max_open_positions:
            return "max_open_positions"

        # Slippage cap requested
        slip_req = intent.risk.get("max_slippage_bps", 0)
        if slip_req > self.limits.max_slippage_bps:
            return "slippage_cap_exceeded"

        # Position-size guard (qty as fraction of capital, requires price metadata)
        price = intent.metadata.get("price")
        if price and self._initial_capital > 0:
            notional = intent.qty * price
            if notional > self._initial_capital * self.limits.max_position_size_pct:
                return "position_size_cap"

        return None

    # ── public order entry point ─────────────────────────────────────────────

    def set_broker(self, broker: BrokerCallable) -> None:
        self._broker = broker

    def set_initial_capital(self, capital: float) -> None:
        self._initial_capital = float(capital)

    async def place_order(self, intent: OrderIntent) -> dict:
        """
        Validate → audit (intent) → broker call → audit (result) → return.
        """
        await self.audit.append("order.intent_received", intent.sanitized())

        # Risk check
        rejection = self._check_risk(intent)
        if rejection:
            await self.audit.append("order.risk_rejected",
                                     {"reason": rejection, "intent": intent.sanitized()})
            return {"status": "rejected", "reason": rejection,
                    "intent": intent.sanitized()}

        # Broker call
        if self._broker is None:
            await self.audit.append("order.broker_unconfigured", {})
            return {"status": "error", "reason": "broker_not_configured"}

        try:
            self.state.orders_this_minute += 1
            result = await self._broker(intent)
        except Exception as exc:
            await self.audit.append("order.broker_error",
                                     {"error": str(exc),
                                      "intent": intent.sanitized()})
            return {"status": "error", "reason": "broker_exception",
                    "detail": str(exc)}

        # Audit fill / acceptance
        await self.audit.append("order.broker_response",
                                 {"intent": intent.sanitized(), "result": result})
        return result

    async def update_pnl(self, current_capital: float) -> None:
        """Called by execution loop to keep daily-loss state fresh."""
        if self._initial_capital <= 0:
            return
        self.state.daily_pnl_pct = (
            (current_capital - self._initial_capital) / self._initial_capital * 100.0
        )
        if self.state.daily_pnl_pct <= -self.limits.max_daily_loss_pct:
            self.state.breached_reason = "daily_loss_limit"
            if not self._kill_switch:
                await self.trigger_kill_switch("daily_loss_limit")


# ──────────────────────────────────────────────────────────────────────────────
# CLI smoke
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    async def _demo():
        sx = SecureExecutionLayer()
        envelope = sx.store_credentials(user_id="user-1",
                                         api_key="DUMMY-KEY",
                                         api_secret="DUMMY-SECRET")
        print("Encrypted envelope:", {k: v for k, v in envelope.items() if k != "ct"})

        with sx._with_credentials(envelope, "user-1") as creds:
            print("Decrypted only inside with-block. has_keys=", "k" in creds)

        async def fake_broker(intent: OrderIntent) -> dict:
            return {"status": "filled", "broker_id": "broker-123",
                    "qty": intent.qty, "price": intent.metadata.get("price")}
        sx.set_broker(fake_broker)
        sx.set_initial_capital(10_000.0)

        intent = OrderIntent(
            user_id="user-1", symbol="BTCUSDT", side="BUY", type="MARKET",
            qty=0.001, risk={"max_slippage_bps": 15},
            metadata={"price": 50_000, "strategy_id": "abc",
                      "regime": "bull", "confidence": 0.83},
        )
        result = await sx.place_order(intent)
        print("Order result:", result)

        await sx.trigger_kill_switch("demo")
        result2 = await sx.place_order(intent)
        print("Post-kill result:", result2)

    asyncio.run(_demo())
