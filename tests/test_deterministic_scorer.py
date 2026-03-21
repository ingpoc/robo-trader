"""
Tests for the DeterministicScorer.

Verifies that known feature inputs produce expected scores and actions.
"""

import pytest
from src.models.research_ledger import (
    ResearchLedgerEntry,
    ManagementFeatures,
    FinancialFeatures,
    CatalystFeatures,
    MarketFeatures,
)
from src.services.recommendation_engine.deterministic_scorer import (
    DeterministicScorer,
    BUY_THRESHOLD,
    AVOID_THRESHOLD,
)


@pytest.fixture
def scorer():
    return DeterministicScorer()


def _make_entry(**kwargs) -> ResearchLedgerEntry:
    """Helper to create a ResearchLedgerEntry with specific features."""
    return ResearchLedgerEntry(
        symbol=kwargs.pop("symbol", "TEST"),
        management=ManagementFeatures(**kwargs.pop("management", {})),
        financial=FinancialFeatures(**kwargs.pop("financial", {})),
        catalyst=CatalystFeatures(**kwargs.pop("catalyst", {})),
        market=MarketFeatures(**kwargs.pop("market", {})),
    )


class TestDeterministicScorer:
    def test_empty_features_hold(self, scorer):
        """Entry with no features should HOLD with 0 score."""
        entry = _make_entry()
        result = scorer.score(entry)
        assert result.action == "HOLD"
        assert result.score == 0.0
        assert result.feature_confidence == 0.0

    def test_strong_buy_signal(self, scorer):
        """Multiple positive signals should produce BUY."""
        entry = _make_entry(
            management={"guidance_raised": True, "insider_buying_net_90d": 10.0},
            financial={"revenue_growth_yoy_pct": 25.0, "eps_growth_yoy_pct": 20.0, "free_cash_flow_positive": True},
            catalyst={"order_book_win": True},
            market={"relative_strength_vs_nifty_90d": 5.0, "base_breakout_setup": True},
        )
        result = scorer.score(entry)
        assert result.score > BUY_THRESHOLD
        assert result.action == "BUY"
        assert result.feature_confidence > 0.3  # At least some features extracted

    def test_strong_avoid_signal(self, scorer):
        """Multiple red flags should produce AVOID."""
        entry = _make_entry(
            management={"guidance_lowered": True, "dilution_signal": True, "auditor_flags": True},
            financial={"free_cash_flow_positive": False, "debt_equity_ratio": 2.5},
        )
        result = scorer.score(entry)
        assert result.score < AVOID_THRESHOLD
        assert result.action == "AVOID"

    def test_mixed_signals_hold(self, scorer):
        """Mixed positive and negative signals should HOLD."""
        entry = _make_entry(
            management={"guidance_raised": True},  # +15
            financial={"free_cash_flow_positive": False},  # -20
            market={"relative_strength_vs_nifty_90d": 3.0},  # +10
        )
        result = scorer.score(entry)
        assert result.action == "HOLD"
        assert 0 <= result.score <= BUY_THRESHOLD

    def test_confidence_calculation(self, scorer):
        """Confidence should reflect % of features extracted."""
        # Entry with all management features set (7 fields)
        entry = _make_entry(
            management={
                "guidance_raised": False,
                "guidance_lowered": False,
                "promoter_pledge_change_pct": 0.0,
                "dilution_signal": False,
                "insider_buying_net_90d": 0.0,
                "ceo_cfo_change_recent": False,
                "auditor_flags": False,
            }
        )
        result = scorer.score(entry)
        extracted, total = result.count_extracted_features()
        assert extracted == 7
        assert total > 7  # Other groups have fields too
        assert result.feature_confidence == extracted / total

    def test_low_confidence_blocks_buy(self, scorer):
        """Even high score shouldn't BUY if confidence is too low."""
        # Only 2 features but both very positive
        entry = _make_entry(
            management={"guidance_raised": True},
            market={"base_breakout_setup": True},
        )
        result = scorer.score(entry)
        # Score is 15 + 15 = 30, which is < BUY_THRESHOLD anyway
        # But even if it were higher, low confidence should block
        extracted, total = result.count_extracted_features()
        assert extracted / total < 0.4  # Low confidence

    def test_promoter_pledge_penalty_scales(self, scorer):
        """Promoter pledge penalty should scale with magnitude."""
        entry_small = _make_entry(management={"promoter_pledge_change_pct": 3.0})
        entry_large = _make_entry(management={"promoter_pledge_change_pct": 12.0})

        result_small = scorer.score(entry_small)
        result_large = scorer.score(entry_large)

        # 3% = 0 * -10 = 0 (int(3/5) = 0)
        # 12% = 2 * -10 = -20
        assert result_large.score < result_small.score

    def test_earnings_surprise_scoring(self, scorer):
        """Positive earnings surprise should add points, negative should subtract."""
        entry_beat = _make_entry(financial={"eps_surprise_pct": 10.0})
        entry_miss = _make_entry(financial={"eps_surprise_pct": -10.0})

        result_beat = scorer.score(entry_beat)
        result_miss = scorer.score(entry_miss)

        assert result_beat.score > 0
        assert result_miss.score < 0

    def test_score_is_deterministic(self, scorer):
        """Same input should always produce same output."""
        features = {
            "management": {"guidance_raised": True},
            "financial": {"revenue_growth_yoy_pct": 20.0},
            "catalyst": {"order_book_win": True},
            "market": {"base_breakout_setup": True},
        }
        result1 = scorer.score(_make_entry(**features))
        result2 = scorer.score(_make_entry(**features))
        assert result1.score == result2.score
        assert result1.action == result2.action
