"""
base_agent.py — Abstract base class for all Claude-powered specialist agents.
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Base class for specialist agents that call Claude via LangChain.

    Each subclass defines its system prompt and implements `analyze()`.

    Attributes:
        model_name: Claude model ID used for inference.
        max_tokens: Maximum tokens allowed in the response.
        temperature: Sampling temperature (0 = deterministic).
    """

    def __init__(
        self,
        api_key: str,
        model_name: str = "claude-sonnet-4-6",
        max_tokens: int = 1024,
        temperature: float = 0.1,
    ) -> None:
        self.api_key = api_key
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.temperature = temperature

        self._llm = ChatAnthropic(
            model=model_name,
            api_key=api_key,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Return the agent's role-defining system prompt."""

    @abstractmethod
    async def analyze(self, context: dict[str, Any]) -> dict[str, Any]:
        """
        Perform specialist analysis on the given context dict.

        Args:
            context: Relevant data for this agent's domain.

        Returns:
            Structured analysis result dict.
        """

    async def _call(self, user_message: str) -> str:
        """
        Send a message to Claude and return the text response.

        Args:
            user_message: The human-turn prompt content.

        Returns:
            Raw string response from Claude.
        """
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=user_message),
        ]
        try:
            response = await self._llm.ainvoke(messages)
            return str(response.content)
        except Exception as exc:
            logger.error("[%s] Claude call failed: %s", self.__class__.__name__, exc)
            raise

    def _parse_json(self, text: str, fallback: dict) -> dict:
        """
        Extract JSON from a Claude response.  Returns fallback on parse failure.
        """
        try:
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(text[start:end])
        except (json.JSONDecodeError, ValueError):
            pass
        logger.warning("[%s] Could not parse JSON from response; using fallback.", self.__class__.__name__)
        return fallback
