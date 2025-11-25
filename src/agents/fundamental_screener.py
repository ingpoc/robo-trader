"""
Fundamental Screener Agent

Screens universe for investment opportunities based on valuation and quality metrics.
Uses real fundamental data from FundamentalService (Perplexity AI).
"""

import json
from typing import Dict, List, Any, Optional

from claude_agent_sdk import tool
from loguru import logger

from src.config import Config
from ..core.database_state import DatabaseStateManager
from ..services.fundamental_service import FundamentalService


def create_fundamental_screener_tool(
    config: Config,
    state_manager: DatabaseStateManager,
    fundamental_service: Optional[FundamentalService] = None
):
    """Create fundamental screener tool with dependencies via closure."""
    
    @tool("fundamental_screening", "Screen for investment opportunities using real fundamental data", {
        "symbols": List[str]
    })
    async def fundamental_screening_tool(args: Dict[str, Any]) -> Dict[str, Any]:
        """Perform fundamental screening using real fundamental data."""
        try:
            symbols = args.get("symbols", [])
            
            if not fundamental_service:
                return {
                    "content": [{"type": "text", "text": "Error: Fundamental service not available. Please configure Perplexity API keys."}],
                    "is_error": True
                }

            if not symbols:
                # Default to common NSE stocks if no symbols provided
                symbols = ["INFY", "TCS", "HDFCBANK", "ICICIBANK", "RELIANCE", "BAJFINANCE", "MARUTI", "TITAN"]

            # Fetch real fundamental data
            logger.info(f"Fetching fundamental data for {len(symbols)} symbols")
            fundamental_data = await fundamental_service.fetch_fundamentals_batch(
                symbols=symbols,
                force_refresh=False
            )

            # Apply screening filters
            candidates = _apply_screening_filters(fundamental_data, config)

            return {
                "content": [
                    {"type": "text", "text": f"Fundamental screening completed using real data. Found {len(candidates)} candidates matching criteria"},
                    {"type": "text", "text": json.dumps(candidates, indent=2)}
                ]
            }

        except Exception as e:
            logger.error(f"Fundamental screening failed: {e}")
            return {
                "content": [{"type": "text", "text": f"Error: {str(e)}"}],
                "is_error": True
            }
    
    return fundamental_screening_tool


def _apply_screening_filters(
    fundamental_data: Dict[str, Any],
    config: Config
) -> List[Dict[str, Any]]:
    """Apply screening filters to fundamental data."""
    candidates = []

    for symbol, analysis in fundamental_data.items():
        if not analysis:
            continue

        pe_ratio = analysis.pe_ratio
        roe = analysis.roe
        debt_to_equity = analysis.debt_to_equity
        market_cap = analysis.market_cap

        # Apply filters from config
        passes_filter = True
        filter_reasons = []

        if pe_ratio is not None:
            if pe_ratio > config.screening.max_pe_ratio:
                passes_filter = False
                filter_reasons.append(f"PE {pe_ratio:.1f} > {config.screening.max_pe_ratio}")
        else:
            filter_reasons.append("PE ratio unavailable")

        if roe is not None:
            if roe < config.screening.min_roe_percent:
                passes_filter = False
                filter_reasons.append(f"ROE {roe:.1f}% < {config.screening.min_roe_percent}%")
        else:
            filter_reasons.append("ROE unavailable")

        if debt_to_equity is not None:
            if debt_to_equity > config.screening.max_debt_equity:
                passes_filter = False
                filter_reasons.append(f"D/E {debt_to_equity:.2f} > {config.screening.max_debt_equity}")
        else:
            filter_reasons.append("Debt-to-equity unavailable")

        if market_cap is not None:
            market_cap_crores = market_cap / 10000000  # Convert to crores
            min_market_cap_crores = config.screening.min_market_cap / 10000000
            if market_cap_crores < min_market_cap_crores:
                passes_filter = False
                filter_reasons.append(f"Market cap {market_cap_crores:.0f} cr < {min_market_cap_crores:.0f} cr")
        else:
            filter_reasons.append("Market cap unavailable")

        if passes_filter:
            candidates.append({
                "symbol": symbol,
                "metrics": {
                    "pe_ratio": round(pe_ratio, 2) if pe_ratio else None,
                    "roe_percent": round(roe, 2) if roe else None,
                    "debt_equity": round(debt_to_equity, 2) if debt_to_equity else None,
                    "market_cap_crores": round(market_cap / 10000000, 2) if market_cap else None,
                    "overall_score": analysis.overall_score,
                    "recommendation": analysis.recommendation
                },
                "rationale": f"PE {pe_ratio:.1f}, ROE {roe:.1f}%, D/E {debt_to_equity:.2f}, Score: {analysis.overall_score:.1f}" if all([pe_ratio, roe, debt_to_equity, analysis.overall_score]) else "Partial data available"
            })
        else:
            logger.debug(f"{symbol} filtered out: {', '.join(filter_reasons)}")

    return candidates