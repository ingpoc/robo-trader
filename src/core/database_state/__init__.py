"""
Database state management - modularized architecture.

Original monolithic database_state.py (1,412 lines, 62 methods) refactored into:
- base.py: Database connection and schema management
- portfolio_state.py: Portfolio CRUD operations
- intent_state.py: Trading intent tracking
- approval_state.py: Approval workflow management
- news_earnings_state.py: News and earnings data
- analysis_state.py: Analysis and recommendations
- database_state.py: Facade coordinating all managers

Backward compatible exports maintain existing imports:
    from src.core.database_state.database_state import DatabaseStateManager
"""

from .database_state import DatabaseStateManager
from .base import DatabaseConnection
from .portfolio_state import PortfolioStateManager
from .intent_state import IntentStateManager
from .approval_state import ApprovalStateManager
from .news_earnings_state import NewsEarningsStateManager
from .analysis_state import AnalysisStateManager

__all__ = [
    "DatabaseStateManager",  # Main facade - backward compatible
    "DatabaseConnection",
    "PortfolioStateManager",
    "IntentStateManager",
    "ApprovalStateManager",
    "NewsEarningsStateManager",
    "AnalysisStateManager",
]
