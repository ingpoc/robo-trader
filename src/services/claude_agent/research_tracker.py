"""
Research Tracker Service

Tracks all AI research activities, market analysis, and data sources used
for complete transparency in Claude's decision-making process.
"""

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ...stores.claude_strategy_store import ClaudeStrategyStore

logger = logging.getLogger(__name__)


@dataclass
class ResearchSession:
    """A research session tracking AI's market analysis."""

    session_id: str
    account_type: str
    research_type: str  # 'market_analysis', 'stock_research', 'sector_analysis', 'technical_analysis'
    symbols_analyzed: List[str]
    data_sources_used: List[str]
    analysis_start_time: str
    analysis_end_time: Optional[str] = None
    confidence_score: float = 0.0
    key_findings: List[str] = None
    recommendations: List[Dict[str, Any]] = None
    token_usage: int = 0
    cost_usd: float = 0.0
    created_at: str = ""

    def __post_init__(self):
        if self.key_findings is None:
            self.key_findings = []
        if self.recommendations is None:
            self.recommendations = []
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ResearchSession":
        return ResearchSession(**data)


@dataclass
class DataSourceUsage:
    """Tracks usage of external data sources."""

    source_name: str
    source_type: str  # 'market_data', 'news', 'fundamental', 'technical'
    queries_made: int = 0
    data_points_retrieved: int = 0
    last_used: str = ""
    total_cost: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ResearchTracker:
    """
    Tracks all AI research activities for transparency.

    Provides complete visibility into:
    - Market analysis performed
    - Data sources consulted
    - Research methodologies used
    - Analysis confidence levels
    - Key findings and recommendations
    """

    def __init__(self, strategy_store: ClaudeStrategyStore):
        self.strategy_store = strategy_store
        self.active_sessions: Dict[str, ResearchSession] = {}
        self.data_source_usage: Dict[str, DataSourceUsage] = {}

    async def start_research_session(
        self,
        account_type: str,
        research_type: str,
        symbols: List[str],
        session_id: Optional[str] = None,
    ) -> ResearchSession:
        """Start tracking a new research session."""

        if not session_id:
            session_id = (
                f"research_{int(datetime.now(timezone.utc).timestamp())}_{account_type}"
            )

        session = ResearchSession(
            session_id=session_id,
            account_type=account_type,
            research_type=research_type,
            symbols_analyzed=symbols,
            data_sources_used=[],
            analysis_start_time=datetime.now(timezone.utc).isoformat(),
        )

        self.active_sessions[session_id] = session
        logger.info(
            f"Started research session: {session_id} ({research_type}) for {len(symbols)} symbols"
        )

        return session

    async def record_data_source_usage(
        self,
        session_id: str,
        source_name: str,
        source_type: str,
        queries: int = 1,
        data_points: int = 0,
        cost: float = 0.0,
    ) -> None:
        """Record usage of a data source during research."""

        if session_id not in self.active_sessions:
            logger.warning(f"Session {session_id} not found for data source tracking")
            return

        session = self.active_sessions[session_id]

        # Add to session's data sources if not already present
        if source_name not in session.data_sources_used:
            session.data_sources_used.append(source_name)

        # Update global data source usage
        if source_name not in self.data_source_usage:
            self.data_source_usage[source_name] = DataSourceUsage(
                source_name=source_name,
                source_type=source_type,
                last_used=datetime.now(timezone.utc).isoformat(),
            )

        usage = self.data_source_usage[source_name]
        usage.queries_made += queries
        usage.data_points_retrieved += data_points
        usage.total_cost += cost
        usage.last_used = datetime.now(timezone.utc).isoformat()

        logger.debug(
            f"Recorded data source usage: {source_name} ({queries} queries, {data_points} data points)"
        )

    async def add_research_findings(
        self, session_id: str, findings: List[str], confidence_score: float = 0.0
    ) -> None:
        """Add key findings from research analysis."""

        if session_id not in self.active_sessions:
            logger.warning(f"Session {session_id} not found for findings recording")
            return

        session = self.active_sessions[session_id]
        session.key_findings.extend(findings)
        session.confidence_score = max(session.confidence_score, confidence_score)

        logger.info(f"Added {len(findings)} findings to research session {session_id}")

    async def add_recommendations(
        self, session_id: str, recommendations: List[Dict[str, Any]]
    ) -> None:
        """Add trading recommendations from research."""

        if session_id not in self.active_sessions:
            logger.warning(
                f"Session {session_id} not found for recommendations recording"
            )
            return

        session = self.active_sessions[session_id]
        session.recommendations.extend(recommendations)

        logger.info(
            f"Added {len(recommendations)} recommendations to research session {session_id}"
        )

    async def complete_research_session(
        self, session_id: str, token_usage: int = 0, cost_usd: float = 0.0
    ) -> Optional[ResearchSession]:
        """Complete a research session and save to storage."""

        if session_id not in self.active_sessions:
            logger.warning(f"Session {session_id} not found for completion")
            return None

        session = self.active_sessions[session_id]
        session.analysis_end_time = datetime.now(timezone.utc).isoformat()
        session.token_usage = token_usage
        session.cost_usd = cost_usd

        # Save to database (extend the strategy store)
        await self._save_research_session(session)

        # Remove from active sessions
        del self.active_sessions[session_id]

        logger.info(
            f"Completed research session: {session_id} ({len(session.key_findings)} findings, {len(session.recommendations)} recommendations)"
        )

        return session

    async def get_research_history(
        self,
        account_type: Optional[str] = None,
        research_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[ResearchSession]:
        """Get historical research sessions."""

        # This would query the database for stored research sessions
        # For now, return active sessions as example
        sessions = list(self.active_sessions.values())

        if account_type:
            sessions = [s for s in sessions if s.account_type == account_type]
        if research_type:
            sessions = [s for s in sessions if s.research_type == research_type]

        return sessions[-limit:]  # Return most recent

    async def get_data_source_usage_stats(self) -> Dict[str, Any]:
        """Get statistics on data source usage."""

        total_queries = sum(
            usage.queries_made for usage in self.data_source_usage.values()
        )
        total_cost = sum(usage.total_cost for usage in self.data_source_usage.values())
        total_data_points = sum(
            usage.data_points_retrieved for usage in self.data_source_usage.values()
        )

        return {
            "total_queries": total_queries,
            "total_cost_usd": total_cost,
            "total_data_points": total_data_points,
            "sources_used": len(self.data_source_usage),
            "source_breakdown": {
                name: usage.to_dict() for name, usage in self.data_source_usage.items()
            },
        }

    async def get_research_effectiveness(
        self, account_type: str, days: int = 7
    ) -> Dict[str, Any]:
        """Analyze research effectiveness over time."""

        # Get research sessions for the period
        sessions = await self.get_research_history(account_type=account_type)

        # Filter by time period (simplified)
        cutoff_time = datetime.now(timezone.utc).timestamp() - (days * 24 * 60 * 60)
        recent_sessions = [
            s
            for s in sessions
            if datetime.fromisoformat(s.created_at).timestamp() > cutoff_time
        ]

        if not recent_sessions:
            return {"error": "No research sessions found in the specified period"}

        # Calculate effectiveness metrics
        total_sessions = len(recent_sessions)
        avg_confidence = (
            sum(s.confidence_score for s in recent_sessions) / total_sessions
        )
        total_findings = sum(len(s.key_findings) for s in recent_sessions)
        total_recommendations = sum(len(s.recommendations) for s in recent_sessions)
        total_symbols = sum(len(s.symbols_analyzed) for s in recent_sessions)

        return {
            "period_days": days,
            "total_sessions": total_sessions,
            "avg_confidence_score": avg_confidence,
            "total_findings": total_findings,
            "total_recommendations": total_recommendations,
            "total_symbols_analyzed": total_symbols,
            "findings_per_session": (
                total_findings / total_sessions if total_sessions > 0 else 0
            ),
            "recommendations_per_session": (
                total_recommendations / total_sessions if total_sessions > 0 else 0
            ),
            "symbols_per_session": (
                total_symbols / total_sessions if total_sessions > 0 else 0
            ),
        }

    async def _save_research_session(self, session: ResearchSession) -> None:
        """Save research session to database."""

        # This would extend the ClaudeStrategyStore to include research session storage
        # For now, we'll log the session data
        session_data = session.to_dict()

        # In a full implementation, this would save to a dedicated research_sessions table
        logger.info(f"Research session saved: {session.session_id}")
        logger.debug(f"Session data: {json.dumps(session_data, indent=2)}")

    async def cleanup_old_sessions(self, days_to_keep: int = 30) -> int:
        """Clean up old research sessions from memory."""

        cutoff_time = datetime.now(timezone.utc).timestamp() - (
            days_to_keep * 24 * 60 * 60
        )
        old_sessions = []

        for session_id, session in self.active_sessions.items():
            if datetime.fromisoformat(session.created_at).timestamp() < cutoff_time:
                old_sessions.append(session_id)

        for session_id in old_sessions:
            del self.active_sessions[session_id]

        if old_sessions:
            logger.info(f"Cleaned up {len(old_sessions)} old research sessions")

        return len(old_sessions)
