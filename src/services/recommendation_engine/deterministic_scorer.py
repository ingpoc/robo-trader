"""
Deterministic Scorer

Converts structured ResearchLedgerEntry features into an auditable score.
Every rule is explicit and testable. The LLM never determines buy/sell —
this scorer does, from extracted features only.

Scoring philosophy:
- Positive scores = accumulating evidence for a position
- Negative scores = red flags that should prevent entry
- Confidence = % of features successfully extracted (not an LLM opinion)
"""

import logging
from typing import Dict, Any, Optional

from src.models.research_ledger import ResearchLedgerEntry

logger = logging.getLogger(__name__)


# --- Scoring Rules (named constants with rationale) ---

# Management signals
GUIDANCE_RAISED_SCORE = 15        # Forward-looking positive signal
GUIDANCE_LOWERED_SCORE = -20      # Strongest negative management signal
DILUTION_SCORE = -15              # Equity dilution hurts existing shareholders
PLEDGE_INCREASE_PER_5PCT = -10    # Promoter pledge increase = distress signal
INSIDER_BUYING_SCORE = 10         # Insider buying = skin in the game
CEO_CFO_CHANGE_SCORE = -5         # Leadership transition risk
AUDITOR_FLAGS_SCORE = -20         # Governance red flag — serious

# Financial signals
REVENUE_GROWTH_HIGH_SCORE = 20    # Revenue growth > 15% YoY
REVENUE_GROWTH_MOD_SCORE = 10     # Revenue growth 5-15% YoY
EPS_GROWTH_HIGH_SCORE = 15        # EPS growth > 15% YoY
EPS_GROWTH_MOD_SCORE = 8          # EPS growth 5-15% YoY
FCF_NEGATIVE_SCORE = -20          # Negative FCF = cash burn
MARGIN_EXPANDING_SCORE = 10       # Operating leverage
MARGIN_CONTRACTING_SCORE = -10    # Margin pressure
HIGH_DEBT_EQUITY_SCORE = -15      # D/E > 1.0 is elevated for most sectors
EARNINGS_BEAT_SCORE = 10          # Positive earnings surprise
EARNINGS_MISS_SCORE = -10         # Negative earnings surprise

# Catalyst signals
RESULTS_IN_WINDOW_SCORE = 10      # Upcoming catalyst
ORDER_WIN_SCORE = 15              # Concrete business win
REGULATORY_APPROVAL_SCORE = 12    # Positive regulatory event
SECTOR_TAILWIND_SCORE = 8         # Macro/policy support
STORY_CROWDED_SCORE = -12         # Priced in — reduces edge
RESTRUCTURING_SCORE = 10          # Value unlock potential

# Market signals
RS_POSITIVE_SCORE = 10            # Outperforming benchmark
RS_NEGATIVE_SCORE = -5            # Underperforming benchmark
SECTOR_EXPANDING_SCORE = 8        # Sector momentum support
SECTOR_CONTRACTING_SCORE = -8     # Sector headwind
INSTITUTIONAL_BUYING_SCORE = 8    # Smart money accumulation
HIGH_DELIVERY_SCORE = 5           # Genuine buying (not just speculative)
BASE_BREAKOUT_SCORE = 15          # Technical setup confirmation
VOLUME_EXPANSION_SCORE = 8        # Volume confirms price action

# Thresholds
BUY_THRESHOLD = 40                # Score > 40 = BUY
AVOID_THRESHOLD = 0               # Score < 0 = AVOID
# Score 0-40 = HOLD

# Minimum confidence to act
MIN_CONFIDENCE_FOR_BUY = 0.40     # Need at least 40% features extracted to BUY


class DeterministicScorer:
    """
    Scores a ResearchLedgerEntry using explicit, auditable rules.

    Every scoring rule is a named constant. No LLM opinions influence the final action.
    Confidence is the % of features successfully extracted.
    """

    def score(self, entry: ResearchLedgerEntry) -> ResearchLedgerEntry:
        """
        Score a research ledger entry and set score, action, and confidence.

        Returns the same entry with score/action/confidence fields populated.
        """
        total_score = 0.0
        breakdown: Dict[str, float] = {}

        # --- Management scoring ---
        mgmt = entry.management
        if mgmt.guidance_raised is True:
            total_score += GUIDANCE_RAISED_SCORE
            breakdown["guidance_raised"] = GUIDANCE_RAISED_SCORE
        if mgmt.guidance_lowered is True:
            total_score += GUIDANCE_LOWERED_SCORE
            breakdown["guidance_lowered"] = GUIDANCE_LOWERED_SCORE
        if mgmt.dilution_signal is True:
            total_score += DILUTION_SCORE
            breakdown["dilution_signal"] = DILUTION_SCORE
        if mgmt.promoter_pledge_change_pct is not None and mgmt.promoter_pledge_change_pct > 0:
            pledge_penalty = int(mgmt.promoter_pledge_change_pct / 5) * PLEDGE_INCREASE_PER_5PCT
            total_score += pledge_penalty
            breakdown["promoter_pledge"] = pledge_penalty
        if mgmt.insider_buying_net_90d is not None and mgmt.insider_buying_net_90d > 0:
            total_score += INSIDER_BUYING_SCORE
            breakdown["insider_buying"] = INSIDER_BUYING_SCORE
        if mgmt.ceo_cfo_change_recent is True:
            total_score += CEO_CFO_CHANGE_SCORE
            breakdown["ceo_cfo_change"] = CEO_CFO_CHANGE_SCORE
        if mgmt.auditor_flags is True:
            total_score += AUDITOR_FLAGS_SCORE
            breakdown["auditor_flags"] = AUDITOR_FLAGS_SCORE

        # --- Financial scoring ---
        fin = entry.financial
        if fin.revenue_growth_yoy_pct is not None:
            if fin.revenue_growth_yoy_pct > 15:
                total_score += REVENUE_GROWTH_HIGH_SCORE
                breakdown["revenue_growth"] = REVENUE_GROWTH_HIGH_SCORE
            elif fin.revenue_growth_yoy_pct > 5:
                total_score += REVENUE_GROWTH_MOD_SCORE
                breakdown["revenue_growth"] = REVENUE_GROWTH_MOD_SCORE
        if fin.eps_growth_yoy_pct is not None:
            if fin.eps_growth_yoy_pct > 15:
                total_score += EPS_GROWTH_HIGH_SCORE
                breakdown["eps_growth"] = EPS_GROWTH_HIGH_SCORE
            elif fin.eps_growth_yoy_pct > 5:
                total_score += EPS_GROWTH_MOD_SCORE
                breakdown["eps_growth"] = EPS_GROWTH_MOD_SCORE
        if fin.free_cash_flow_positive is False:
            total_score += FCF_NEGATIVE_SCORE
            breakdown["fcf_negative"] = FCF_NEGATIVE_SCORE
        if fin.operating_margin_trend == "expanding":
            total_score += MARGIN_EXPANDING_SCORE
            breakdown["margin_trend"] = MARGIN_EXPANDING_SCORE
        elif fin.operating_margin_trend == "contracting":
            total_score += MARGIN_CONTRACTING_SCORE
            breakdown["margin_trend"] = MARGIN_CONTRACTING_SCORE
        if fin.debt_equity_ratio is not None and fin.debt_equity_ratio > 1.0:
            total_score += HIGH_DEBT_EQUITY_SCORE
            breakdown["high_debt"] = HIGH_DEBT_EQUITY_SCORE
        if fin.eps_surprise_pct is not None:
            if fin.eps_surprise_pct > 5:
                total_score += EARNINGS_BEAT_SCORE
                breakdown["earnings_surprise"] = EARNINGS_BEAT_SCORE
            elif fin.eps_surprise_pct < -5:
                total_score += EARNINGS_MISS_SCORE
                breakdown["earnings_surprise"] = EARNINGS_MISS_SCORE

        # --- Catalyst scoring ---
        cat = entry.catalyst
        if cat.results_date_in_window is True:
            total_score += RESULTS_IN_WINDOW_SCORE
            breakdown["results_window"] = RESULTS_IN_WINDOW_SCORE
        if cat.order_book_win is True:
            total_score += ORDER_WIN_SCORE
            breakdown["order_win"] = ORDER_WIN_SCORE
        if cat.regulatory_approval is True:
            total_score += REGULATORY_APPROVAL_SCORE
            breakdown["regulatory"] = REGULATORY_APPROVAL_SCORE
        if cat.sector_tailwind is True:
            total_score += SECTOR_TAILWIND_SCORE
            breakdown["sector_tailwind"] = SECTOR_TAILWIND_SCORE
        if cat.story_crowded is True:
            total_score += STORY_CROWDED_SCORE
            breakdown["story_crowded"] = STORY_CROWDED_SCORE
        if cat.demerger_or_restructuring is True:
            total_score += RESTRUCTURING_SCORE
            breakdown["restructuring"] = RESTRUCTURING_SCORE

        # --- Market scoring ---
        mkt = entry.market
        if mkt.relative_strength_vs_nifty_90d is not None:
            if mkt.relative_strength_vs_nifty_90d > 0:
                total_score += RS_POSITIVE_SCORE
                breakdown["relative_strength"] = RS_POSITIVE_SCORE
            elif mkt.relative_strength_vs_nifty_90d < -10:
                total_score += RS_NEGATIVE_SCORE
                breakdown["relative_strength"] = RS_NEGATIVE_SCORE
        if mkt.sector_momentum == "expanding":
            total_score += SECTOR_EXPANDING_SCORE
            breakdown["sector_momentum"] = SECTOR_EXPANDING_SCORE
        elif mkt.sector_momentum == "contracting":
            total_score += SECTOR_CONTRACTING_SCORE
            breakdown["sector_momentum"] = SECTOR_CONTRACTING_SCORE
        if mkt.institutional_holding_change_pct is not None and mkt.institutional_holding_change_pct > 0.5:
            total_score += INSTITUTIONAL_BUYING_SCORE
            breakdown["institutional_buying"] = INSTITUTIONAL_BUYING_SCORE
        if mkt.delivery_pct_avg_20d is not None and mkt.delivery_pct_avg_20d > 50:
            total_score += HIGH_DELIVERY_SCORE
            breakdown["high_delivery"] = HIGH_DELIVERY_SCORE
        if mkt.base_breakout_setup is True:
            total_score += BASE_BREAKOUT_SCORE
            breakdown["base_breakout"] = BASE_BREAKOUT_SCORE
        if mkt.volume_expansion is True:
            total_score += VOLUME_EXPANSION_SCORE
            breakdown["volume_expansion"] = VOLUME_EXPANSION_SCORE

        # --- Calculate confidence ---
        extracted, total = entry.count_extracted_features()
        confidence = extracted / total if total > 0 else 0.0

        # --- Determine action ---
        if total_score > BUY_THRESHOLD and confidence >= MIN_CONFIDENCE_FOR_BUY:
            action = "BUY"
        elif total_score < AVOID_THRESHOLD:
            action = "AVOID"
        else:
            action = "HOLD"

        # Populate entry
        entry.score = round(total_score, 2)
        entry.action = action
        entry.feature_confidence = round(confidence, 4)

        logger.info(
            f"Scored {entry.symbol}: score={entry.score}, action={entry.action}, "
            f"confidence={entry.feature_confidence:.0%} ({extracted}/{total} features), "
            f"breakdown={breakdown}"
        )

        return entry
