import pytest
import os
import tempfile
from datetime import datetime
from src.services.claude_agent.trade_decision_logger import TradeDecisionLogger

@pytest.fixture
def temp_data_file():
    """Create a temporary data file for testing."""
    fd, path = tempfile.mkstemp(suffix='.jsonl')
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)

@pytest.mark.asyncio
async def test_log_trade_decision(temp_data_file):
    """Test logging a trade decision."""
    logger = TradeDecisionLogger(data_file=temp_data_file)
    await logger.initialize()
    decision = {
        "trade_id": "trade_001",
        "symbol": "HDFC",
        "action": "BUY",
        "quantity": 10,
        "entry_price": 2750,
        "reasoning": "Momentum breakout",
        "confidence": 0.85,
        "stop_loss": 2650,
        "target": 2900,
        "research_sources": ["news", "technical"],
        "decision_timestamp": datetime.now().isoformat()
    }
    result = await logger.log_decision(decision)
    assert result["trade_id"] == "trade_001"
    assert result["symbol"] == "HDFC"
    assert "logged_at" in result
    history = await logger.get_recent_decisions(limit=1)
    assert len(history) > 0
    assert history[0]["trade_id"] == "trade_001"

@pytest.mark.asyncio
async def test_get_decision_stats(temp_data_file):
    """Test getting decision statistics."""
    logger = TradeDecisionLogger(data_file=temp_data_file)
    await logger.initialize()
    decision = {
        "trade_id": "trade_stat",
        "symbol": "INFY",
        "action": "SELL",
        "quantity": 5,
        "entry_price": 3000,
        "reasoning": "Profit taking",
        "confidence": 0.7
    }
    await logger.log_decision(decision)
    stats = await logger.get_decision_stats()
    assert stats["total_decisions"] >= 1
    assert "buy_decisions" in stats
    assert "sell_decisions" in stats
    assert "avg_confidence" in stats
    assert stats["sell_decisions"] >= 1

@pytest.mark.asyncio
async def test_filter_by_symbol(temp_data_file):
    """Test filtering decisions by symbol."""
    logger = TradeDecisionLogger(data_file=temp_data_file)
    await logger.initialize()

    await logger.log_decision({
        "trade_id": "trade_hdfc_1",
        "symbol": "HDFC",
        "action": "BUY",
        "quantity": 10,
        "confidence": 0.8
    })

    await logger.log_decision({
        "trade_id": "trade_infy_1",
        "symbol": "INFY",
        "action": "BUY",
        "quantity": 5,
        "confidence": 0.75
    })

    await logger.log_decision({
        "trade_id": "trade_hdfc_2",
        "symbol": "HDFC",
        "action": "SELL",
        "quantity": 10,
        "confidence": 0.85
    })

    hdfc_decisions = await logger.get_recent_decisions(symbol="HDFC")
    assert len(hdfc_decisions) == 2
    assert all(d["symbol"] == "HDFC" for d in hdfc_decisions)

    infy_decisions = await logger.get_recent_decisions(symbol="INFY")
    assert len(infy_decisions) == 1
    assert infy_decisions[0]["symbol"] == "INFY"

@pytest.mark.asyncio
async def test_persistence(temp_data_file):
    """Test that decisions persist across logger instances."""
    logger1 = TradeDecisionLogger(data_file=temp_data_file)
    await logger1.initialize()

    await logger1.log_decision({
        "trade_id": "persist_test",
        "symbol": "TCS",
        "action": "BUY",
        "quantity": 15,
        "confidence": 0.9
    })

    await logger1.cleanup()

    logger2 = TradeDecisionLogger(data_file=temp_data_file)
    await logger2.initialize()

    decisions = await logger2.get_recent_decisions()
    assert len(decisions) >= 1
    assert any(d["trade_id"] == "persist_test" for d in decisions)

@pytest.mark.asyncio
async def test_recent_decisions_order(temp_data_file):
    """Test that recent decisions are returned in reverse chronological order."""
    logger = TradeDecisionLogger(data_file=temp_data_file)
    await logger.initialize()

    for i in range(5):
        await logger.log_decision({
            "trade_id": f"trade_{i}",
            "symbol": "TEST",
            "action": "BUY",
            "quantity": i + 1,
            "confidence": 0.8
        })

    recent = await logger.get_recent_decisions(limit=3)
    assert len(recent) == 3
    assert recent[0]["trade_id"] == "trade_4"
    assert recent[1]["trade_id"] == "trade_3"
    assert recent[2]["trade_id"] == "trade_2"

@pytest.mark.asyncio
async def test_avg_confidence_calculation(temp_data_file):
    """Test average confidence calculation."""
    logger = TradeDecisionLogger(data_file=temp_data_file)
    await logger.initialize()

    await logger.log_decision({
        "trade_id": "conf_1",
        "symbol": "TEST",
        "action": "BUY",
        "quantity": 10,
        "confidence": 0.8
    })

    await logger.log_decision({
        "trade_id": "conf_2",
        "symbol": "TEST",
        "action": "SELL",
        "quantity": 10,
        "confidence": 0.6
    })

    stats = await logger.get_decision_stats()
    assert stats["avg_confidence"] == 0.7
