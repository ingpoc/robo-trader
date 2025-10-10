"""
Chat API for Robo Trader Conversational Interface

Provides REST endpoints for natural language trading conversations with Claude.
"""

import asyncio
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from loguru import logger

from ..core.orchestrator import get_orchestrator
from ..core.conversation_manager import ConversationManager


# Create router for chat endpoints
router = APIRouter(prefix="/api/chat", tags=["chat"])

# Global conversation manager instance
conversation_manager: Optional[ConversationManager] = None


class ChatRequest(BaseModel):
    """Request model for chat messages."""
    query: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Response model for chat messages."""
    response: str
    session_id: str
    intents: List[str] = []
    actions: List[str] = []


class ApprovalRequest(BaseModel):
    """Request model for recommendation approval."""
    recommendation_id: str
    action: str  # "approve", "reject", "modify"
    modifications: Optional[Dict[str, Any]] = None


async def initialize_chat_manager():
    """Initialize the global conversation manager."""
    global conversation_manager
    if conversation_manager is None:
        orchestrator = get_orchestrator()
        if orchestrator:
            conversation_manager = ConversationManager(
                orchestrator.config,
                orchestrator.state_manager
            )
            await conversation_manager.initialize()
            logger.info("Chat API conversation manager initialized")


@router.post("/query", response_model=ChatResponse)
async def chat_query(request: ChatRequest, background_tasks: BackgroundTasks):
    """
    Process a natural language query and return AI response.

    This endpoint handles conversational trading queries, maintaining context
    across multiple turns and providing intelligent trading assistance.
    """
    global conversation_manager

    if not conversation_manager:
        await initialize_chat_manager()

    if not conversation_manager:
        raise HTTPException(status_code=500, detail="Chat system not initialized")

    try:
        # Get or create session
        session_id = request.session_id
        if not session_id:
            session_id = await conversation_manager.start_conversation(request.user_id)

        # Send message and get response
        result = await conversation_manager.send_message(session_id, request.query)

        # Process any detected intents/actions in background
        if result.get("intents") or result.get("actions"):
            background_tasks.add_task(
                process_detected_intents,
                session_id,
                result.get("intents", []),
                result.get("actions", [])
            )

        return ChatResponse(
            response=result["response"],
            session_id=session_id,
            intents=result.get("intents", []),
            actions=result.get("actions", [])
        )

    except Exception as e:
        logger.error(f"Chat query error: {e}")
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")


@router.get("/history")
async def get_chat_history(session_id: str, limit: int = 50):
    """
    Get conversation history for a session.

    Returns the message history to restore conversation context in the UI.
    """
    global conversation_manager

    if not conversation_manager:
        await initialize_chat_manager()

    if not conversation_manager:
        raise HTTPException(status_code=500, detail="Chat system not initialized")

    try:
        history = await conversation_manager.get_conversation_history(session_id, limit)
        return {"history": history, "session_id": session_id}

    except Exception as e:
        logger.error(f"Chat history error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve chat history: {str(e)}")


@router.post("/approve-recommendation")
async def approve_recommendation(request: ApprovalRequest):
    """
    Approve or reject AI-generated recommendations.

    Handles user decisions on trading recommendations generated through chat.
    """
    global conversation_manager

    if not conversation_manager:
        await initialize_chat_manager()

    orchestrator = get_orchestrator()
    if not orchestrator:
        raise HTTPException(status_code=500, detail="System not initialized")

    try:
        # Update approval status in state manager
        success = await orchestrator.state_manager.update_approval_status(
            request.recommendation_id,
            request.action,
            request.modifications
        )

        if not success:
            raise HTTPException(status_code=404, detail="Recommendation not found")

        # If approved, execute the recommendation
        if request.action == "approve":
            # Get the recommendation details
            pending_approvals = await orchestrator.state_manager.get_pending_approvals()
            recommendation = next(
                (r for r in pending_approvals if r["id"] == request.recommendation_id),
                None
            )

            if recommendation and "recommendation" in recommendation:
                # Execute the approved recommendation
                await execute_recommendation(orchestrator, recommendation["recommendation"])

        return {
            "status": "success",
            "action": request.action,
            "recommendation_id": request.recommendation_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Recommendation approval error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process approval: {str(e)}")


@router.get("/sessions")
async def get_active_sessions():
    """
    Get information about active conversation sessions.

    Useful for debugging and session management.
    """
    global conversation_manager

    if not conversation_manager:
        await initialize_chat_manager()

    if not conversation_manager:
        raise HTTPException(status_code=500, detail="Chat system not initialized")

    try:
        sessions = await conversation_manager.get_active_sessions()
        return {"sessions": sessions}

    except Exception as e:
        logger.error(f"Get sessions error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get sessions: {str(e)}")


@router.delete("/session/{session_id}")
async def end_conversation_session(session_id: str):
    """
    End a conversation session and clean up resources.
    """
    global conversation_manager

    if not conversation_manager:
        await initialize_chat_manager()

    if not conversation_manager:
        raise HTTPException(status_code=500, detail="Chat system not initialized")

    try:
        await conversation_manager.end_conversation(session_id)
        return {"status": "success", "session_id": session_id}

    except Exception as e:
        logger.error(f"End session error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to end session: {str(e)}")


@router.post("/cleanup")
async def cleanup_expired_sessions():
    """
    Clean up expired conversation sessions.

    Should be called periodically to free up resources.
    """
    global conversation_manager

    if not conversation_manager:
        await initialize_chat_manager()

    if not conversation_manager:
        raise HTTPException(status_code=500, detail="Chat system not initialized")

    try:
        await conversation_manager.cleanup_expired_sessions()
        return {"status": "success", "message": "Expired sessions cleaned up"}

    except Exception as e:
        logger.error(f"Cleanup error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cleanup sessions: {str(e)}")


async def process_detected_intents(session_id: str, intents: List[str], actions: List[str]):
    """
    Process intents and actions detected in chat messages.

    This function runs in the background to handle detected trading intents
    without blocking the chat response.
    """
    try:
        orchestrator = get_orchestrator()
        if not orchestrator:
            return

        # Process intents
        for intent in intents:
            if intent == "portfolio_analysis":
                # Trigger portfolio scan
                asyncio.create_task(orchestrator.run_portfolio_scan())

            elif intent == "market_screening":
                # Trigger market screening
                asyncio.create_task(orchestrator.run_market_screening())

            elif intent == "strategy_review":
                # Trigger strategy analysis
                asyncio.create_task(orchestrator.run_strategy_review())

        # Process actions (these would trigger specific agent actions)
        for action in actions:
            logger.info(f"Processing detected action: {action}")
            # Additional action processing would go here

    except Exception as e:
        logger.error(f"Error processing detected intents: {e}")


async def execute_recommendation(orchestrator, recommendation: Dict[str, Any]):
    """
    Execute an approved recommendation.

    Translates recommendation into actual trading actions.
    """
    try:
        action = recommendation.get("action", "").upper()
        symbol = recommendation.get("symbol", "")
        quantity = recommendation.get("quantity")

        if not symbol:
            logger.error("Recommendation missing symbol")
            return

        # Create trading intent
        intent = await orchestrator.state_manager.create_intent(symbol, source="chat")

        # Create order command based on recommendation
        from ..core.state import OrderCommand, Signal

        if action in ["BUY", "SELL"]:
            # Create signal
            signal = Signal(
                symbol=symbol,
                timeframe="chat_recommendation",
                confidence=recommendation.get("confidence", 0.5),
                rationale=recommendation.get("reasoning", "Chat-based recommendation")
            )
            intent.signal = signal

            # Create order command
            order_cmd = OrderCommand(
                type="place",
                side=action,
                symbol=symbol,
                qty=quantity or 1,  # Default to 1 if not specified
                order_type="MARKET"
            )
            intent.order_commands = [order_cmd]

            # Run risk assessment
            from ..agents.risk_manager import risk_assessment_tool
            await risk_assessment_tool({"intent_id": intent.id})

            # If risk approved, execute
            if intent.risk_decision and intent.risk_decision.decision == "approve":
                from ..agents.execution_agent import execute_trade_tool
                await execute_trade_tool({"intent_id": intent.id})
                logger.info(f"Executed chat recommendation: {action} {quantity} {symbol}")
            else:
                logger.warning(f"Chat recommendation rejected by risk manager: {action} {symbol}")

        else:
            logger.info(f"Non-trading recommendation: {action} for {symbol}")

    except Exception as e:
        logger.error(f"Failed to execute recommendation: {e}")


# Export the router for inclusion in main app
__all__ = ["router", "initialize_chat_manager"]