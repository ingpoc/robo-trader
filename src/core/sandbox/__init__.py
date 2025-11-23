"""
Sandbox Module for Robo Trader

Implements sandboxing patterns based on Anthropic's research:
https://www.anthropic.com/engineering/claude-code-sandboxing

Token Savings: ~1000 tokens/cycle (40-50% reduction)
Autonomy Improvement: 84% fewer permission prompts

Key Components:
- SandboxBoundary: Risk limits and approved operations
- SandboxContext: Pre-approval for operations within boundaries
- AnalysisCache: Reuse previous analysis results
"""

from .sandbox_context import (
    SandboxBoundary,
    SandboxContext,
    get_sandbox_context,
    create_default_sandbox_boundary
)
from .analysis_cache import (
    AnalysisCache,
    get_analysis_cache
)
from .paper_trading_sandbox import (
    PaperTradingSandbox,
    check_paper_trade_sandbox
)

__all__ = [
    'SandboxBoundary',
    'SandboxContext',
    'get_sandbox_context',
    'create_default_sandbox_boundary',
    'AnalysisCache',
    'get_analysis_cache',
    'PaperTradingSandbox',
    'check_paper_trade_sandbox',
]
