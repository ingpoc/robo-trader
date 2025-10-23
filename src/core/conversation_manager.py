"""
Conversation Manager for Robo Trader

Manages conversational interactions with Claude, maintaining context,
handling multi-turn conversations, and providing natural language
trading partnership capabilities.
"""

import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

from loguru import logger
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

from src.config import Config
from ..core.database_state import DatabaseStateManager


class ConversationMessage:
    """Represents a single message in the conversation."""

    def __init__(self, role: str, content: str, timestamp: Optional[str] = None):
        self.role = role  # "user" or "assistant"
        self.content = content
        self.timestamp = timestamp or datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationMessage":
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=data.get("timestamp")
        )


class ConversationSession:
    """Represents a conversation session with context and history."""

    def __init__(self, session_id: str, user_id: Optional[str] = None):
        self.session_id = session_id
        self.user_id = user_id or "default"
        self.messages: List[ConversationMessage] = []
        self.context: Dict[str, Any] = {}
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.last_activity = self.created_at
        self.metadata: Dict[str, Any] = {}

    def add_message(self, role: str, content: str) -> None:
        """Add a message to the conversation."""
        message = ConversationMessage(role, content)
        self.messages.append(message)
        self.last_activity = message.timestamp

        # Keep only last 50 messages to manage context window
        if len(self.messages) > 50:
            self.messages = self.messages[-50:]

    def get_recent_messages(self, limit: int = 20) -> List[ConversationMessage]:
        """Get recent messages for context."""
        return self.messages[-limit:]

    def update_context(self, key: str, value: Any) -> None:
        """Update conversation context."""
        self.context[key] = value
        self.context["last_updated"] = datetime.now(timezone.utc).isoformat()

    def get_context(self) -> Dict[str, Any]:
        """Get current conversation context."""
        return self.context.copy()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "messages": [msg.to_dict() for msg in self.messages],
            "context": self.context,
            "created_at": self.created_at,
            "last_activity": self.last_activity,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationSession":
        session = cls(data["session_id"], data.get("user_id"))
        session.messages = [ConversationMessage.from_dict(msg) for msg in data.get("messages", [])]
        session.context = data.get("context", {})
        session.created_at = data.get("created_at", session.created_at)
        session.last_activity = data.get("last_activity", session.last_activity)
        session.metadata = data.get("metadata", {})
        return session


class ConversationManager:
    """
    Manages conversational interactions with Claude for natural language trading.

    Key features:
    - Multi-turn conversation support
    - Context preservation across sessions
    - Portfolio-aware responses
    - Trading intent extraction
    - Educational explanations
    """

    def __init__(self, config: Config, state_manager: DatabaseStateManager):
        self.config = config
        self.state_manager = state_manager
        self.client: Optional[ClaudeSDKClient] = None
        self._client_initialized = False
        self.active_sessions: Dict[str, ConversationSession] = {}

        # Conversation settings
        self.max_context_messages = 20
        self.session_timeout_hours = 24
        self.context_refresh_interval = 300  # 5 minutes

    async def initialize(self) -> None:
        """Initialize the conversation manager."""
        logger.info("Initializing Conversation Manager")

        # Load existing sessions
        await self._load_active_sessions()

        logger.info("Conversation Manager initialized successfully (Claude client will initialize on demand)")

    async def _ensure_client(self) -> None:
        """Lazy initialization of Claude SDK client."""
        if self.client is None:
            options = ClaudeAgentOptions(
                allowed_tools=[],
                system_prompt=self._get_conversation_prompt(),
                max_turns=50
            )
            self.client = ClaudeSDKClient(options=options)
            await self.client.__aenter__()
            self._client_initialized = True
            logger.info("Conversation Manager Claude client initialized")

    async def cleanup(self) -> None:
        """Cleanup conversation manager resources."""
        if self.client and self._client_initialized:
            try:
                await self.client.__aexit__(None, None, None)
                logger.info("Conversation Manager client cleaned up")
            except Exception as e:
                logger.warning(f"Error cleaning up Conversation Manager client: {e}")
            finally:
                self.client = None
                self._client_initialized = False

    async def start_conversation(self, user_id: Optional[str] = None) -> str:
        """Start a new conversation session."""
        session_id = f"conv_{int(datetime.now(timezone.utc).timestamp() * 1000)}"
        session = ConversationSession(session_id, user_id)
        self.active_sessions[session_id] = session

        # Initialize with portfolio context
        await self._initialize_session_context(session)

        logger.info(f"Started conversation session {session_id} for user {user_id}")
        return session_id

    async def send_message(self, session_id: str, message: str) -> Dict[str, Any]:
        """
        Send a message to Claude and get a response.

        Returns structured response with content, intent detection, and actions.
        """
        if session_id not in self.active_sessions:
            raise ValueError(f"Conversation session {session_id} not found")

        session = self.active_sessions[session_id]

        # Add user message to session
        session.add_message("user", message)

        # Update context if needed
        await self._refresh_session_context(session)

        # Build conversation prompt with context
        conversation_prompt = self._build_conversation_prompt(session, message)

        response_content = ""
        detected_intents = []
        suggested_actions = []

        if self.client is None:
            await self._ensure_client()

        if self.client:
            try:
                await asyncio.wait_for(self.client.query(conversation_prompt), timeout=30.0)

                async for response_msg in self.client.receive_response():
                    if hasattr(response_msg, 'content'):
                        for block in response_msg.content:
                            if hasattr(block, 'text'):
                                response_content += block.text

                                # Try to extract structured data from response
                                try:
                                    # Look for JSON-like structures in the response
                                    if "{" in block.text and "}" in block.text:
                                        json_start = block.text.find("{")
                                        json_end = block.text.rfind("}") + 1
                                        json_str = block.text[json_start:json_end]

                                        parsed = json.loads(json_str)
                                        if "intents" in parsed:
                                            detected_intents = parsed["intents"]
                                        if "actions" in parsed:
                                            suggested_actions = parsed["actions"]
                                except (json.JSONDecodeError, KeyError):
                                    pass  # Not structured data, continue

            except asyncio.TimeoutError:
                logger.error(f"Conversation query timed out: {message[:100]}...")
                response_content = "I apologize, but my response is taking longer than expected. Please try again."
            except Exception as e:
                logger.error(f"Error in Claude conversation: {e}", exc_info=True)
                response_content = "I apologize, but I'm having trouble processing your request right now. Please try again."
        else:
            # Fallback response when Claude is unavailable
            response_content = self._generate_fallback_response(message, session)

        # Add AI response to session
        session.add_message("assistant", response_content)

        # Save session
        await self._save_session(session)

        return {
            "response": response_content,
            "intents": detected_intents,
            "actions": suggested_actions,
            "session_id": session_id
        }

    async def get_conversation_history(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get conversation history for a session."""
        if session_id not in self.active_sessions:
            return []

        session = self.active_sessions[session_id]
        messages = session.get_recent_messages(limit)
        return [msg.to_dict() for msg in messages]

    async def end_conversation(self, session_id: str) -> None:
        """End a conversation session."""
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            await self._save_session(session)
            del self.active_sessions[session_id]
            logger.info(f"Ended conversation session {session_id}")

    async def get_active_sessions(self) -> List[Dict[str, Any]]:
        """Get information about active conversation sessions."""
        sessions_info = []
        for session in self.active_sessions.values():
            sessions_info.append({
                "session_id": session.session_id,
                "user_id": session.user_id,
                "message_count": len(session.messages),
                "last_activity": session.last_activity,
                "created_at": session.created_at
            })
        return sessions_info

    def _get_conversation_prompt(self) -> str:
        """Get the system prompt for conversational interactions."""
        return """
You are Claude, an expert AI trading assistant for Robo Trader.

Your role is to provide natural, conversational trading assistance while being:
- Helpful and informative
- Conservative and risk-aware
- Educational about trading concepts
- Context-aware of the user's portfolio and situation

Always maintain a professional, friendly tone. Explain trading concepts clearly.
When discussing trades or recommendations, always include risk considerations.

If you detect trading intents in user messages, structure your response to include:
- Clear analysis or recommendation
- Risk assessment
- Reasoning for your position
- Alternative perspectives

Response Format:
Provide natural conversational responses. If you want to include structured data for the system to process, include it at the end in JSON format like:

INTENTS: {"intents": ["portfolio_analysis", "trade_recommendation"]}
ACTIONS: {"actions": ["analyze_portfolio", "check_risk"]}
"""

    def _build_conversation_prompt(self, session: ConversationSession, current_message: str) -> str:
        """Build a conversation prompt with context."""

        # Get recent conversation history
        recent_messages = session.get_recent_messages(self.max_context_messages)

        # Build conversation context
        conversation_history = ""
        for msg in recent_messages[-10:]:  # Last 10 messages for context
            role = "User" if msg.role == "user" else "Assistant"
            conversation_history += f"{role}: {msg.content}\n"

        # Get portfolio context
        portfolio_context = self._get_portfolio_context(session.context)

        prompt = f"""
Current Conversation:
{conversation_history}

Portfolio Context:
{portfolio_context}

User's Latest Message: {current_message}

Please respond naturally and helpfully. Remember to be conservative with trading advice and always consider risk.
"""

        return prompt

    def _get_portfolio_context(self, session_context: Dict[str, Any]) -> str:
        """Get portfolio information for conversation context."""
        try:
            # This would integrate with the state manager to get current portfolio info
            # For now, return basic context
            return "Portfolio information will be loaded here (holdings, P&L, risk metrics)"
        except Exception:
            return "Portfolio information temporarily unavailable"

    async def _initialize_session_context(self, session: ConversationSession) -> None:
        """Initialize conversation session with portfolio and user context."""
        try:
            # Get current portfolio state
            portfolio = await self.state_manager.get_portfolio()
            if portfolio:
                session.update_context("portfolio_holdings", len(portfolio.holdings))
                session.update_context("portfolio_value", portfolio.exposure_total)

            # Get recent recommendations
            pending_recommendations = await self.state_manager.get_pending_approvals()
            session.update_context("pending_recommendations", len(pending_recommendations))

        except Exception as e:
            logger.error(f"Failed to initialize session context: {e}")

    async def _refresh_session_context(self, session: ConversationSession) -> None:
        """Refresh session context periodically."""
        # Check if context needs refreshing (every 5 minutes)
        last_update = session.context.get("last_updated")
        if last_update:
            last_update_time = datetime.fromisoformat(last_update)
            if datetime.now(timezone.utc) - last_update_time < timedelta(seconds=self.context_refresh_interval):
                return  # Context is still fresh

        # Refresh context
        await self._initialize_session_context(session)

    def _generate_fallback_response(self, message: str, session: ConversationSession) -> str:
        """Generate fallback response when Claude is unavailable."""
        message_lower = message.lower()

        if "portfolio" in message_lower:
            return "I'd be happy to help you analyze your portfolio. While I'm currently operating in limited mode, I can tell you that portfolio analysis includes reviewing your holdings, risk metrics, and performance. Please try again when the full AI system is available."

        elif "buy" in message_lower or "sell" in message_lower:
            return "I understand you're interested in trading decisions. When the full system is available, I can provide detailed analysis including technical indicators, fundamental metrics, and risk assessment. Please hold off on trades until I can give you proper guidance."

        elif "risk" in message_lower:
            return "Risk management is crucial in trading. Key considerations include position sizing, stop losses, diversification, and market conditions. The system will provide comprehensive risk analysis when fully operational."

        else:
            return "I'm currently operating in a limited capacity. I can help you with basic trading concepts and will provide full conversational trading assistance once the AI system is fully initialized. Please try your request again later."

    async def _load_active_sessions(self) -> None:
        """Load active conversation sessions from storage."""
        try:
            # This would load sessions from persistent storage
            # For now, sessions are in-memory only
            pass
        except Exception as e:
            logger.error(f"Failed to load active sessions: {e}")

    async def _save_session(self, session: ConversationSession) -> None:
        """Save conversation session to persistent storage."""
        try:
            # This would save sessions to persistent storage
            # For now, sessions are in-memory only
            pass
        except Exception as e:
            logger.error(f"Failed to save session {session.session_id}: {e}")

    async def cleanup_expired_sessions(self) -> None:
        """Clean up expired conversation sessions."""
        current_time = datetime.now(timezone.utc)
        expired_sessions = []

        for session_id, session in self.active_sessions.items():
            last_activity = datetime.fromisoformat(session.last_activity)
            if current_time - last_activity > timedelta(hours=self.session_timeout_hours):
                expired_sessions.append(session_id)

        for session_id in expired_sessions:
            await self.end_conversation(session_id)

        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired conversation sessions")