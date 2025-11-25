"""
Context Analyzer for Robo-Trader MCP Tools.

Implements Anthropic's progressive disclosure pattern with context awareness
to dynamically show relevant tools based on conversation context and user intent.
"""

from typing import Dict, List, Any, Optional, Set, Tuple
from enum import Enum
import re
import json
from dataclasses import dataclass
from datetime import datetime, timedelta


class IntentCategory(Enum):
    """Defined user intent categories for tool relevance."""
    DEBUGGING = "debugging"        # Error analysis, troubleshooting
    MONITORING = "monitoring"      # Health checks, status monitoring
    ANALYSIS = "analysis"          # Data analysis, insights generation
    DEVELOPMENT = "development"    # Development workflows, testing
    PRODUCTION = "production"      # Production operations, maintenance
    OPTIMIZATION = "optimization"  # Performance optimization, efficiency
    EXPLORATION = "exploration"    # Discovery, learning, general inquiry


@dataclass
class ToolRelevanceScore:
    """Relevance score for a tool in specific context."""
    tool_name: str
    relevance_score: float  # 0.0 to 1.0
    relevance_reasons: List[str]
    context_match: bool
    priority_boost: float = 0.0


@dataclass
class ContextAnalysis:
    """Result of context analysis."""
    detected_intents: List[IntentCategory]
    confidence_scores: Dict[IntentCategory, float]
    keyword_matches: Dict[str, List[str]]
    tool_relevance: List[ToolRelevanceScore]
    conversation_summary: str
    session_context: Dict[str, Any]


class ContextAnalyzer:
    """Analyzes conversation context and determines tool relevance."""

    def __init__(self):
        self.intent_keywords = self._initialize_intent_keywords()
        self.tool_intent_mappings = self._initialize_tool_mappings()
        self.context_history: List[Dict[str, Any]] = []
        self.max_history_size = 10

    def _initialize_intent_keywords(self) -> Dict[IntentCategory, List[str]]:
        """Define keyword patterns for each intent category."""
        return {
            IntentCategory.DEBUGGING: [
                "error", "issue", "problem", "debug", "troubleshoot", "fix", "broken",
                "crash", "exception", "fail", "timeout", "lock", "stuck", "wrong",
                "diagnose", "investigate", "check why", "not working", "incorrect"
            ],

            IntentCategory.MONITORING: [
                "health", "status", "check", "monitor", "performance", "metrics",
                "uptime", "running", "active", "current state", "overview", "dashboard",
                "watch", "observe", "track", "measure", "evaluate", "assess"
            ],

            IntentCategory.ANALYSIS: [
                "analyze", "analysis", "insights", "report", "summary", "findings",
                "data", "patterns", "trends", "statistics", "correlation", "examine",
                "review", "study", "investigate", "explore", "understand", "breakdown"
            ],

            IntentCategory.DEVELOPMENT: [
                "develop", "implement", "build", "create", "add", "modify", "change",
                "update", "upgrade", "refactor", "test", "validate", "prototype",
                "experiment", "demo", "example", "tutorial", "learn", "understand how"
            ],

            IntentCategory.PRODUCTION: [
                "deploy", "production", "live", "real", "operational", "maintenance",
                "backup", "restore", "scale", "configure", "setup", "administer",
                "manage", "operate", "run", "execute", "schedule", "automate"
            ],

            IntentCategory.OPTIMIZATION: [
                "optimize", "improve", "enhance", "speed", "performance", "efficiency",
                "reduce", "minimize", "maximize", "better", "faster", "optimize",
                "tune", "adjust", "fine-tune", "streamline", "optimize for"
            ],

            IntentCategory.EXPLORATION: [
                "what", "how", "where", "find", "search", "discover", "explore",
                "list", "show", "available", "options", "choices", "browse",
                "navigate", "overview", "introduction", "getting started"
            ]
        }

    def _initialize_tool_mappings(self) -> Dict[str, List[IntentCategory]]:
        """Map tools to their relevant intent categories."""
        return {
            # System Health Tools
            "check_system_health": [IntentCategory.MONITORING, IntentCategory.PRODUCTION],
            "queue_status": [IntentCategory.MONITORING, IntentCategory.DEBUGGING],
            "coordinator_status": [IntentCategory.MONITORING, IntentCategory.DEBUGGING],
            "real_time_performance_monitor": [IntentCategory.MONITORING, IntentCategory.OPTIMIZATION],

            # Analysis Tools
            "analyze_logs": [IntentCategory.DEBUGGING, IntentCategory.ANALYSIS],
            "query_portfolio": [IntentCategory.ANALYSIS, IntentCategory.MONITORING],
            "context_aware_summarize": [IntentCategory.ANALYSIS, IntentCategory.OPTIMIZATION],
            "smart_file_read": [IntentCategory.ANALYSIS, IntentCategory.DEVELOPMENT],
            "execute_analysis": [IntentCategory.ANALYSIS, IntentCategory.OPTIMIZATION],

            # Database Tools
            "diagnose_database_locks": [IntentCategory.DEBUGGING, IntentCategory.PRODUCTION],
            "verify_configuration_integrity": [IntentCategory.MONITORING, IntentCategory.PRODUCTION],

            # Search and Discovery Tools
            "search_tools": [IntentCategory.EXPLORATION, IntentCategory.DEVELOPMENT],
            "list_directories": [IntentCategory.EXPLORATION, IntentCategory.DEVELOPMENT],
            "read_file": [IntentCategory.EXPLORATION, IntentCategory.DEVELOPMENT],
            "find_related_files": [IntentCategory.DEVELOPMENT, IntentCategory.ANALYSIS],

            # Optimization Tools
            "smart_cache": [IntentCategory.OPTIMIZATION, IntentCategory.DEVELOPMENT],
            "workflow_orchestrator": [IntentCategory.OPTIMIZATION, IntentCategory.PRODUCTION],
            "enhanced_differential_analysis": [IntentCategory.ANALYSIS, IntentCategory.OPTIMIZATION],
            "differential_analysis": [IntentCategory.ANALYSIS, IntentCategory.OPTIMIZATION],

            # Performance Tools
            "task_execution_metrics": [IntentCategory.MONITORING, IntentCategory.OPTIMIZATION],
            "token_metrics_collector": [IntentCategory.MONITORING, IntentCategory.OPTIMIZATION],

            # Execution Tools
            "execute_python": [IntentCategory.DEVELOPMENT, IntentCategory.PRODUCTION],
            "session_context_injection": [IntentCategory.DEVELOPMENT, IntentCategory.OPTIMIZATION],

            # Knowledge Tools
            "knowledge_query": [IntentCategory.EXPLORATION, IntentCategory.ANALYSIS],
            "suggest_fix": [IntentCategory.DEBUGGING, IntentCategory.DEVELOPMENT]
        }

    def analyze_context(self, conversation_history: List[str], current_message: str) -> ContextAnalysis:
        """
        Analyze conversation context to determine user intent and tool relevance.

        Args:
            conversation_history: Recent conversation messages
            current_message: The current user message

        Returns:
            ContextAnalysis with detected intents and tool relevance scores
        """
        # Combine conversation history with current message
        full_context = " ".join(conversation_history[-5:] + [current_message])  # Last 5 messages + current
        full_context_lower = full_context.lower()

        # Detect intents based on keyword matching
        detected_intents = self._detect_intents(full_context_lower)
        confidence_scores = self._calculate_confidence_scores(full_context_lower, detected_intents)
        keyword_matches = self._extract_keyword_matches(full_context_lower, detected_intents)

        # Calculate tool relevance scores
        tool_relevance = self._calculate_tool_relevance(detected_intents, confidence_scores)

        # Create conversation summary
        conversation_summary = self._create_conversation_summary(current_message, detected_intents)

        # Create session context
        session_context = {
            "timestamp": datetime.now().isoformat(),
            "message_count": len(conversation_history),
            "detected_intents": [intent.value for intent in detected_intents],
            "confidence_scores": {intent.value: score for intent, score in confidence_scores.items()},
            "primary_intent": detected_intents[0].value if detected_intents else "exploration"
        }

        return ContextAnalysis(
            detected_intents=detected_intents,
            confidence_scores=confidence_scores,
            keyword_matches=keyword_matches,
            tool_relevance=tool_relevance,
            conversation_summary=conversation_summary,
            session_context=session_context
        )

    def _detect_intents(self, context: str) -> List[IntentCategory]:
        """Detect user intents based on keyword presence in context."""
        intent_scores = {}

        for intent, keywords in self.intent_keywords.items():
            score = 0
            matched_keywords = []

            for keyword in keywords:
                # Count keyword occurrences (word boundaries)
                pattern = r'\b' + re.escape(keyword) + r'\b'
                matches = len(re.findall(pattern, context, re.IGNORECASE))
                if matches > 0:
                    score += matches
                    matched_keywords.append(keyword)

            if score > 0:
                intent_scores[intent] = {
                    "score": score,
                    "matches": matched_keywords
                }

        # Sort intents by score and return top 3
        sorted_intents = sorted(intent_scores.items(), key=lambda x: x[1]["score"], reverse=True)
        return [intent for intent, _ in sorted_intents[:3]]

    def _calculate_confidence_scores(self, context: str, detected_intents: List[IntentCategory]) -> Dict[IntentCategory, float]:
        """Calculate confidence scores for detected intents."""
        confidence_scores = {}
        total_keyword_matches = 0

        # Count total matches for normalization
        for intent in detected_intents:
            keywords = self.intent_keywords[intent]
            for keyword in keywords:
                pattern = r'\b' + re.escape(keyword) + r'\b'
                matches = len(re.findall(pattern, context, re.IGNORECASE))
                total_keyword_matches += matches

        if total_keyword_matches == 0:
            return {intent: 0.0 for intent in detected_intents}

        # Calculate normalized confidence scores
        for intent in detected_intents:
            keywords = self.intent_keywords[intent]
            intent_matches = 0

            for keyword in keywords:
                pattern = r'\b' + re.escape(keyword) + r'\b'
                matches = len(re.findall(pattern, context, re.IGNORECASE))
                intent_matches += matches

            confidence_scores[intent] = intent_matches / total_keyword_matches

        return confidence_scores

    def _extract_keyword_matches(self, context: str, detected_intents: List[IntentCategory]) -> Dict[str, List[str]]:
        """Extract specific keyword matches for each intent."""
        keyword_matches = {}

        for intent in detected_intents:
            keywords = self.intent_keywords[intent]
            matched_keywords = []

            for keyword in keywords:
                pattern = r'\b' + re.escape(keyword) + r'\b'
                if re.search(pattern, context, re.IGNORECASE):
                    matched_keywords.append(keyword)

            if matched_keywords:
                keyword_matches[intent.value] = matched_keywords

        return keyword_matches

    def _calculate_tool_relevance(self, detected_intents: List[IntentCategory], confidence_scores: Dict[IntentCategory, float]) -> List[ToolRelevanceScore]:
        """Calculate relevance scores for all tools based on detected intents."""
        tool_relevance = []

        for tool_name, relevant_intents in self.tool_intent_mappings.items():
            relevance_score = 0.0
            relevance_reasons = []
            context_match = False

            # Calculate base relevance from intent matching
            for intent in detected_intents:
                if intent in relevant_intents:
                    confidence = confidence_scores.get(intent, 0.0)
                    relevance_score += confidence * 0.7  # Base weight
                    relevance_reasons.append(f"Matches {intent.value} intent")
                    context_match = True

            # Apply priority boosts for specific patterns
            priority_boost = self._calculate_priority_boost(tool_name, detected_intents)
            relevance_score += priority_boost

            # Normalize score to 0.0-1.0 range
            relevance_score = min(relevance_score, 1.0)

            # Add minimum threshold for context-matched tools
            if context_match and relevance_score < 0.3:
                relevance_score = 0.3

            tool_relevance.append(ToolRelevanceScore(
                tool_name=tool_name,
                relevance_score=relevance_score,
                relevance_reasons=relevance_reasons,
                context_match=context_match,
                priority_boost=priority_boost
            ))

        # Sort by relevance score (descending)
        tool_relevance.sort(key=lambda x: x.relevance_score, reverse=True)
        return tool_relevance

    def _calculate_priority_boost(self, tool_name: str, detected_intents: List[IntentCategory]) -> float:
        """Calculate priority boosts for specific tool-intent combinations."""
        priority_boosts = {
            # Debugging tools get boost in debugging context
            ("analyze_logs", IntentCategory.DEBUGGING): 0.3,
            ("diagnose_database_locks", IntentCategory.DEBUGGING): 0.4,
            ("suggest_fix", IntentCategory.DEBUGGING): 0.3,

            # Monitoring tools get boost in monitoring context
            ("check_system_health", IntentCategory.MONITORING): 0.3,
            ("queue_status", IntentCategory.MONITORING): 0.2,
            ("real_time_performance_monitor", IntentCategory.MONITORING): 0.3,

            # Exploration tools get boost in exploration context
            ("search_tools", IntentCategory.EXPLORATION): 0.4,
            ("list_directories", IntentCategory.EXPLORATION): 0.3,
            ("knowledge_query", IntentCategory.EXPLORATION): 0.2,

            # Analysis tools get boost in analysis context
            ("query_portfolio", IntentCategory.ANALYSIS): 0.3,
            ("context_aware_summarize", IntentCategory.ANALYSIS): 0.3,
            ("execute_analysis", IntentCategory.ANALYSIS): 0.2
        }

        boost = 0.0
        for intent in detected_intents:
            boost += priority_boosts.get((tool_name, intent), 0.0)

        return boost

    def _create_conversation_summary(self, current_message: str, detected_intents: List[IntentCategory]) -> str:
        """Create a summary of the conversation context."""
        primary_intent = detected_intents[0].value if detected_intents else "exploration"

        # Extract key themes from the message
        themes = []
        if "error" in current_message.lower() or "problem" in current_message.lower():
            themes.append("troubleshooting")
        if "check" in current_message.lower() or "status" in current_message.lower():
            themes.append("status verification")
        if "analyze" in current_message.lower() or "understand" in current_message.lower():
            themes.append("data investigation")
        if "how" in current_message.lower() or "what" in current_message.lower():
            themes.append("information seeking")

        theme_str = f" (themes: {', '.join(themes)})" if themes else ""

        return f"Primary intent: {primary_intent}{theme_str}"

    def update_context_history(self, analysis: ContextAnalysis) -> None:
        """Update the context history with new analysis."""
        self.context_history.append({
            "timestamp": datetime.now().isoformat(),
            "session_context": analysis.session_context,
            "conversation_summary": analysis.conversation_summary,
            "tool_relevance": analysis.tool_relevance[:5]  # Top 5 tools
        })

        # Maintain history size
        if len(self.context_history) > self.max_history_size:
            self.context_history = self.context_history[-self.max_history_size:]

    def get_contextual_tool_priority(self, tool_name: str) -> Tuple[float, List[str]]:
        """Get contextual priority score and reasons for a specific tool."""
        if not self.context_history:
            return 0.5, ["No context history available"]

        # Get the most recent context analysis
        recent_analysis = self.context_history[-1]

        for tool_relevance in recent_analysis["tool_relevance"]:
            if tool_relevance["tool_name"] == tool_name:
                return tool_relevance["relevance_score"], tool_relevance["relevance_reasons"]

        return 0.1, ["Tool not relevant to current context"]


# Global context analyzer instance
context_analyzer = ContextAnalyzer()