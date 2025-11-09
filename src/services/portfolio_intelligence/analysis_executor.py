"""
Analysis Executor for Portfolio Intelligence

Handles:
- Claude analysis execution
- Streaming response processing
- Result parsing
"""

import logging
import time
import json
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

from src.core.errors import TradingError, ErrorCategory, ErrorSeverity

logger = logging.getLogger(__name__)


class PortfolioAnalysisExecutor:
    """Executes Claude analysis for portfolio intelligence."""

    def __init__(self, client_manager, analysis_logger, config):
        self.client_manager = client_manager
        self.analysis_logger = analysis_logger
        self.config = config
        self._hook_events = []  # Store hook events for logging

    async def _hook_pre_tool_use(self, tool_name: str, tool_input: Dict[str, Any]) -> None:
        """Hook called before Claude uses a tool."""
        event = {
            "event_type": "PreToolUse",
            "tool_name": tool_name,
            "tool_input": tool_input,
            "timestamp": time.time()
        }
        self._hook_events.append(event)
        logger.debug(f"PreToolUse hook: Claude about to use tool '{tool_name}' with input: {tool_input}")

    async def _hook_post_tool_use(self, tool_name: str, tool_output: Any, error: Optional[str] = None) -> None:
        """Hook called after Claude uses a tool."""
        event = {
            "event_type": "PostToolUse",
            "tool_name": tool_name,
            "tool_output": str(tool_output)[:500] if tool_output else None,  # Limit size
            "error": error,
            "timestamp": time.time()
        }
        self._hook_events.append(event)
        logger.debug(f"PostToolUse hook: Tool '{tool_name}' completed. Error: {error}")

    async def _hook_stop(self, reason: str) -> None:
        """Hook called when analysis session stops."""
        event = {
            "event_type": "Stop",
            "reason": reason,
            "total_events": len(self._hook_events),
            "timestamp": time.time()
        }
        self._hook_events.append(event)
        logger.debug(f"Stop hook: Analysis session stopped. Reason: {reason}. Total events: {len(self._hook_events)}")

    async def execute_claude_analysis(
        self,
        system_prompt: str,
        stocks_data: Dict[str, Dict[str, Any]],
        prompts: Dict[str, str],
        analysis_id: str,
        mcp_server: Any,
        tool_names: List[str]
    ) -> Dict[str, Any]:
        """Execute Claude analysis with provided tools."""

        start_time = time.time()

        logger.debug(f"_execute_claude_analysis() called with {len(stocks_data)} stocks, analysis_id={analysis_id}")

        try:
            # Initialize analysis logging for portfolio analysis (not a single trade)
            # Create a generic decision log for portfolio analysis
            from src.services.claude_agent.analysis_logger import TradeDecisionLog
            decision_log = TradeDecisionLog(
                decision_id=analysis_id,
                session_id=f"portfolio_{int(time.time())}",
                symbol="PORTFOLIO",  # Generic symbol for portfolio analysis
                action="ANALYZE"  # Portfolio analysis action
            )
            self.analysis_logger.active_decisions[analysis_id] = decision_log

            # Log Claude analysis start
            await self.analysis_logger.log_analysis_step(
                decision_id=analysis_id,
                step_type="ai_analysis",
                description="Starting Claude AI analysis of portfolio stocks",
                input_data={"stocks_count": len(stocks_data), "prompts_count": len(prompts)},
                reasoning="Using Claude AI to analyze data quality, optimize prompts, and provide recommendations",
                confidence_score=0.0,
                duration_ms=0
            )

            # Create Claude SDK client with MCP server and environment-specific permission mode
            from claude_agent_sdk import ClaudeAgentOptions
            options = ClaudeAgentOptions(
                system_prompt=system_prompt,
                mcp_servers={"portfolio_intelligence": mcp_server},
                allowed_tools=tool_names,
                max_turns=10,  # Reduced from 15 - optimized prompts need fewer turns
                permission_mode=self.config.permission_mode  # Use environment-based permission mode
            )

            client = await self.client_manager.get_client("portfolio_analysis", options)

            # Create user prompt with data summary (limit size to avoid token limits)
            stocks_summary = {
                symbol: {
                    "data_summary": data.get("data_summary", {}),
                    "last_checks": {
                        "news": data.get("last_news_check"),
                        "earnings": data.get("last_earnings_check"),
                        "fundamentals": data.get("last_fundamentals_check")
                    },
                    "earnings_count": len(data.get("earnings", [])),
                    "news_count": len(data.get("news", [])),
                    "fundamental_count": len(data.get("fundamental_analysis", []))
                }
                for symbol, data in stocks_data.items()
            }

            user_prompt = f"""Analyze the following stocks and their data. ALL information is provided below - complete your analysis in ONE comprehensive response.

═══════════════════════════════════════════════════════════════
STOCKS SUMMARY (with available data):
═══════════════════════════════════════════════════════════════
{json.dumps(stocks_summary, indent=2)}

═══════════════════════════════════════════════════════════════
CURRENT PROMPTS USED FOR DATA FETCHING (from database):
═══════════════════════════════════════════════════════════════
{json.dumps(prompts, indent=2)}

═══════════════════════════════════════════════════════════════
YOUR ANALYSIS TASK (complete in ONE response):
═══════════════════════════════════════════════════════════════

For EACH stock, provide:

**1. DATA QUALITY ASSESSMENT** (is data sufficient and current?)
   - Earnings: Recent? Complete? Quality score (0-100)
   - News: Fresh? Relevant? Quality score (0-100)
   - Fundamentals: Comprehensive? Quality score (0-100)
   - Overall data quality: SUFFICIENT | NEEDS_UPDATE | INSUFFICIENT

**2. PROMPT OPTIMIZATION** (if data quality is poor)
   - Which prompt needs updating? (earnings_processor/news_processor/deep_fundamental_processor)
   - Why is current prompt insufficient?
   - Optimized prompt (if needed - use update_prompt tool)

**3. INVESTMENT RECOMMENDATION**
   - Action: BUY | HOLD | SELL | WAIT_FOR_DATA
   - Confidence: 0-100%
   - Key reasons: (3-5 bullet points)
   - Risk factors: (2-3 key risks)
   - Price target (if applicable)

**FORMAT YOUR RESPONSE AS:**
```
STOCK: [Symbol]
---
DATA QUALITY:
- Earnings: [score/100] - [current/outdated] - [comment]
- News: [score/100] - [fresh/stale] - [comment]
- Fundamentals: [score/100] - [comprehensive/lacking] - [comment]
- OVERALL: [SUFFICIENT|NEEDS_UPDATE|INSUFFICIENT]

RECOMMENDATION:
- ACTION: [BUY|HOLD|SELL|WAIT_FOR_DATA]
- CONFIDENCE: [X]%
- REASONING:
  * [reason 1]
  * [reason 2]
  * [reason 3]
- RISKS:
  * [risk 1]
  * [risk 2]
- PRICE_TARGET: $[XX] (if applicable)

[Repeat for each stock]
```

**IMPORTANT:**
- Provide analysis for ALL {len(stocks_summary)} stocks in ONE response
- Be concise but actionable (2-3 sentences per section maximum)
- Only use update_prompt tool if data quality is truly insufficient
- If data is outdated but present, still provide conditional recommendations
- Focus on the most critical insights - avoid generic advice

Begin your comprehensive analysis now (all stocks, one response)."""

            # Execute query with streaming and real-time progress monitoring
            logger.info(f"Starting Claude analysis with streaming for {len(stocks_data)} stocks")

            # Send query and monitor responses in real-time
            await client.query(user_prompt)

            response_chunks = []
            last_activity = time.time()
            message_timeout = 120.0  # Timeout if no message for 2 minutes (indicates hung state)

            logger.debug("Entering receive_messages() loop to monitor Claude progress")

            async for message in client.receive_messages():
                # Check for message timeout (indicates hung state)
                time_since_activity = time.time() - last_activity
                if time_since_activity > message_timeout:
                    error_msg = f"No activity from Claude for {int(time_since_activity)} seconds - analysis may be hung"
                    logger.error(error_msg)
                    raise TradingError(
                        error_msg,
                        category=ErrorCategory.SYSTEM,
                        severity=ErrorSeverity.HIGH,
                        recoverable=False
                    )

                last_activity = time.time()

                # Process message based on type for real-time progress tracking
                try:
                    from claude_agent_sdk import AssistantMessage, ToolUseBlock, TextBlock, ResultMessage, ToolResultBlock

                    if isinstance(message, AssistantMessage):
                        for block in message.content:
                            if isinstance(block, ToolUseBlock):
                                # Claude is ACTIVELY using a tool - RUNNING
                                logger.debug(f"Claude using tool: {block.name}")
                                # Log PreToolUse hook event
                                await self._hook_pre_tool_use(
                                    tool_name=block.name,
                                    tool_input=getattr(block, 'input', {})
                                )

                            elif isinstance(block, TextBlock):
                                # Claude is responding - RUNNING
                                response_chunks.append(block.text)
                                logger.debug(f"Received text chunk ({len(block.text)} chars, {len(response_chunks)} total chunks)")

                    elif isinstance(message, ToolResultBlock):
                        # Tool completed - STILL RUNNING
                        logger.debug("Tool result received")
                        # Log PostToolUse hook event
                        tool_name = getattr(message, 'tool_use_id', 'unknown')
                        tool_output = getattr(message, 'content', None)
                        error = getattr(message, 'error', None) if hasattr(message, 'error') else None
                        await self._hook_post_tool_use(
                            tool_name=tool_name,
                            tool_output=tool_output,
                            error=error
                        )

                    elif isinstance(message, ResultMessage):
                        # Analysis complete - READY
                        logger.debug("Claude analysis complete (ResultMessage received)")
                        # Log Stop hook event
                        await self._hook_stop(reason="analysis_complete")
                        break

                except Exception as e:
                    logger.warning(f"Error processing message type: {e}")
                    # Continue processing - don't fail on message type issues
                    pass

            logger.debug(f"Exit receive_messages() loop - received {len(response_chunks)} text chunks")

            # Assemble final response from chunks
            response = "\n".join(response_chunks) if response_chunks else ""
            execution_time_ms = int((time.time() - start_time) * 1000)

            logger.debug(f"Final response length: {len(response)} chars, execution time: {execution_time_ms}ms")

            # Log Claude analysis completion
            await self.analysis_logger.log_analysis_step(
                decision_id=analysis_id,
                step_type="ai_analysis",
                description="Completed Claude AI analysis",
                input_data={"response_length": len(str(response))},
                reasoning=f"Claude analyzed {len(stocks_data)} stocks and provided recommendations",
                confidence_score=0.0,
                duration_ms=execution_time_ms
            )

            # Parse response (Claude SDK returns structured response)
            # Extract recommendations and prompt updates from response

            # DEBUG: Log Claude's actual response
            logger.debug(f"Claude response type: {type(response)}")
            logger.debug(f"Claude response length: {len(response)}")
            logger.debug(f"Claude response (first 500 chars): {response[:500]}")

            # Parse Claude's response to extract structured recommendations and updates
            recommendations = []
            prompt_updates = []
            data_assessment = {}

            # Extract Claude's actual thinking content
            response_text = response

            analysis_result = {
                "recommendations": recommendations,
                "prompt_updates": prompt_updates,
                "data_assessment": data_assessment,
                "claude_response": response_text,
                "execution_time_ms": execution_time_ms,
                "hook_events": self._hook_events  # Include hook events for transparency
            }

            # Log hook events summary
            if self._hook_events:
                pre_tool_count = sum(1 for e in self._hook_events if e["event_type"] == "PreToolUse")
                post_tool_count = sum(1 for e in self._hook_events if e["event_type"] == "PostToolUse")
                logger.info(f"Hook events captured: {pre_tool_count} PreToolUse, {post_tool_count} PostToolUse, {len(self._hook_events)} total")

            return analysis_result

        except Exception as e:
            logger.error(f"Error executing Claude analysis: {e}", exc_info=True)
            # Log error to transparency
            await self.analysis_logger.log_analysis_step(
                decision_id=analysis_id,
                step_type="error",
                description=f"Claude analysis failed: {str(e)}",
                input_data={},
                reasoning="Error occurred during Claude AI analysis",
                confidence_score=0.0,
                duration_ms=int((time.time() - start_time) * 1000)
            )
            raise
