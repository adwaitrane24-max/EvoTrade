"""
news_fetcher.py — Fetches crypto-related headlines from NewsAPI for sentiment analysis.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

from newsapi import NewsApiClient

logger = logging.getLogger(__name__)


class NewsFetcher:
    """
    Retrieves recent news headlines relevant to a given asset.

    Attributes:
        api_key: NewsAPI key loaded from environment.
        max_articles: Maximum articles to return per fetch.
    """

    _QUERY_MAP: dict[str, str] = {
        "BTC/USDT": "bitcoin OR BTC cryptocurrency",
        "ETH/USDT": "ethereum OR ETH cryptocurrency",
        "SOL/USDT": "solana OR SOL cryptocurrency",
        "BNB/USDT": "binance coin OR BNB cryptocurrency",
    }

    def __init__(self, api_key: str, max_articles: int = 20) -> None:
        """
        Args:
            api_key: NewsAPI authentication key.
            max_articles: Cap on returned articles.
        """
        self._client = NewsApiClient(api_key=api_key)
        self.max_articles = max_articles

    def fetch_headlines(
        self,
        symbol: str,
        lookback_hours: int = 24,
    ) -> list[dict]:
        """
        Pull recent headlines for the given trading symbol.

        Args:
            symbol: Trading pair, e.g. "BTC/USDT".
            lookback_hours: How many hours back to search.

        Returns:
            List of dicts with keys: title, description, source, publishedAt, url.
        """
        query = self._QUERY_MAP.get(symbol, symbol.split("/")[0] + " cryptocurrency")
        from_date = (datetime.utcnow() - timedelta(hours=lookback_hours)).strftime(
            "%Y-%m-%dT%H:%M:%S"
        )

        try:
            response = self._client.get_everything(
                q=query,
                from_param=from_date,
                language="en",
                sort_by="publishedAt",
                page_size=min(self.max_articles, 100),
            )
        except Exception as exc:
            logger.error("NewsAPI request failed: %s", exc)
            return []

        articles = response.get("articles", [])
        cleaned = [
            {
                "title": a.get("title", ""),
                "description": a.get("description", ""),
                "source": a.get("source", {}).get("name", ""),
                "published_at": a.get("publishedAt", ""),
                "url": a.get("url", ""),
            }
            for a in articles
            if a.get("title")
        ]
        logger.info("Fetched %d headlines for %s", len(cleaned), symbol)
        return cleaned

    def get_headline_texts(self, symbol: str, lookback_hours: int = 24) -> list[str]:
        """Return just the headline strings for LLM consumption."""
        articles = self.fetch_headlines(symbol, lookback_hours)
        return [f"{a['title']} — {a['description']}" for a in articles if a["title"]]


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    logging.basicConfig(level=logging.INFO)
    load_dotenv()

    key = os.getenv("NEWS_API_KEY", "")
    if not key:
        print("NEWS_API_KEY not set — skipping demo.")
    else:
        fetcher = NewsFetcher(api_key=key)
        headlines = fetcher.get_headline_texts("BTC/USDT")
        for h in headlines[:5]:
            print(h)
