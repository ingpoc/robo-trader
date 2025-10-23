"""
Fundamental Screener Agent

Screens universe for investment opportunities based on valuation and quality metrics.
"""

import json
from typing import Dict, List, Any
import random

from claude_agent_sdk import tool
from loguru import logger

from src.config import Config
from ..core.database_state import DatabaseStateManager
from ..core.state_models import Signal


def create_fundamental_screener_tool(config: Config, state_manager: DatabaseStateManager):
    """Create fundamental screener tool with dependencies via closure."""
    
    @tool("fundamental_screening", "Screen for investment opportunities", {})
    async def fundamental_screening_tool(args: Dict[str, Any]) -> Dict[str, Any]:
        """Perform fundamental screening."""
        try:
            # Simulate screening results
            candidates = _simulate_screening(config)

            return {
                "content": [
                    {"type": "text", "text": f"Fundamental screening completed. Found {len(candidates)} candidates"},
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


def _simulate_screening(config: Config) -> List[Dict[str, Any]]:
    """Simulate fundamental screening results."""
    symbols = ["INFY", "TCS", "HDFC", "ICICI", "RELIANCE", "BAJAJ", "MARUTI", "TITAN"]
    candidates = []

    for symbol in symbols:
        # Random metrics within reasonable ranges
        pe_ratio = random.uniform(15, 35)
        roe = random.uniform(8, 25)
        debt_equity = random.uniform(0.1, 1.5)
        market_cap = random.uniform(50000, 500000)  # crores

        # Apply filters
        if (pe_ratio <= config.screening.max_pe_ratio and
            roe >= config.screening.min_roe_percent and
            debt_equity <= config.screening.max_debt_equity and
            market_cap >= config.screening.min_market_cap / 10000000):  # Convert to crores

            candidates.append({
                "symbol": symbol,
                "metrics": {
                    "pe_ratio": round(pe_ratio, 2),
                    "roe_percent": round(roe, 2),
                    "debt_equity": round(debt_equity, 2),
                    "market_cap_crores": round(market_cap, 2)
                },
                "rationale": f"PE {pe_ratio:.1f}, ROE {roe:.1f}%, D/E {debt_equity:.2f}"
            })

    return candidates