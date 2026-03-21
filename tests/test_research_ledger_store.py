"""
Tests for the ResearchLedgerStore.

Verifies CRUD operations, concurrent access, and data integrity.
"""

import asyncio
import pytest
import aiosqlite

from src.stores.research_ledger_store import ResearchLedgerStore


@pytest.fixture
async def store():
    """Create an in-memory store for testing."""
    conn = await aiosqlite.connect(":memory:")
    s = ResearchLedgerStore(conn)
    await s.initialize()
    yield s
    await conn.close()


def _sample_entry(symbol="RELIANCE", score=45.0, action="BUY"):
    return {
        "id": f"test_{symbol}_{score}",
        "symbol": symbol,
        "timestamp": "2026-03-20T10:00:00Z",
        "features_json": '{"mgmt_guidance_raised": true}',
        "score": score,
        "action": action,
        "feature_confidence": 0.65,
        "sources": ["perplexity_news"],
        "extraction_model": "claude-sonnet-4-20250514",
        "extraction_duration_ms": 1500,
    }


class TestResearchLedgerStore:
    @pytest.mark.asyncio
    async def test_store_and_retrieve(self, store):
        """Basic store and retrieve."""
        entry = _sample_entry()
        assert await store.store_entry(entry)

        result = await store.get_latest("RELIANCE")
        assert result is not None
        assert result["symbol"] == "RELIANCE"
        assert result["score"] == 45.0
        assert result["action"] == "BUY"

    @pytest.mark.asyncio
    async def test_get_latest_returns_newest(self, store):
        """get_latest should return the most recent entry."""
        await store.store_entry({
            **_sample_entry(score=30.0),
            "id": "old",
            "timestamp": "2026-03-19T10:00:00Z",
        })
        await store.store_entry({
            **_sample_entry(score=50.0),
            "id": "new",
            "timestamp": "2026-03-20T10:00:00Z",
        })

        result = await store.get_latest("RELIANCE")
        assert result["score"] == 50.0

    @pytest.mark.asyncio
    async def test_get_history(self, store):
        """get_history should return multiple entries ordered by timestamp."""
        for i in range(5):
            await store.store_entry({
                **_sample_entry(score=float(i * 10)),
                "id": f"entry_{i}",
                "timestamp": f"2026-03-{15+i}T10:00:00Z",
            })

        history = await store.get_history("RELIANCE", limit=3)
        assert len(history) == 3
        # Should be newest first
        assert history[0]["score"] > history[1]["score"]

    @pytest.mark.asyncio
    async def test_get_all_latest(self, store):
        """get_all_latest should return one entry per symbol."""
        await store.store_entry(_sample_entry("RELIANCE", 45.0))
        await store.store_entry(_sample_entry("TCS", 60.0, "BUY"))
        await store.store_entry(_sample_entry("INFY", 20.0, "HOLD"))

        results = await store.get_all_latest()
        symbols = {r["symbol"] for r in results}
        assert "RELIANCE" in symbols
        assert "TCS" in symbols
        assert "INFY" in symbols

    @pytest.mark.asyncio
    async def test_get_buy_candidates(self, store):
        """get_buy_candidates should only return BUY entries."""
        await store.store_entry(_sample_entry("RELIANCE", 45.0, "BUY"))
        await store.store_entry(_sample_entry("TCS", 60.0, "BUY"))
        await store.store_entry(_sample_entry("INFY", 20.0, "HOLD"))

        results = await store.get_buy_candidates()
        assert all(r["action"] == "BUY" for r in results)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_nonexistent_symbol(self, store):
        """Querying a non-existent symbol should return None/empty."""
        assert await store.get_latest("NOSYMBOL") is None
        assert await store.get_history("NOSYMBOL") == []

    @pytest.mark.asyncio
    async def test_upsert_behavior(self, store):
        """Storing with same ID should replace."""
        entry = _sample_entry()
        await store.store_entry(entry)

        # Update score
        entry["score"] = 99.0
        await store.store_entry(entry)

        result = await store.get_latest("RELIANCE")
        assert result["score"] == 99.0
