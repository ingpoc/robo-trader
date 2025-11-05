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
from typing import Dict, List, Any

from src.core.errors import TradingError, ErrorCategory, ErrorSeverity

logger = logging.getLogger(__name__)


class PortfolioAnalysisExecutor:
    """Executes Claude analysis for portfolio intelligence."""

    def __init__(self, client_manager, analysis_logger):
        self.client_manager = client_manager
        self.analysis_logger = analysis_logger

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

        print(f"DEBUG: _execute_claude_analysis() called with {len(stocks_data)} stocks, analysis_id={analysis_id}")
        logger.info(f"DEBUG: _execute_claude_analysis() called with {len(stocks_data)} stocks, analysis_id={analysis_id}")

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

            # Create Claude SDK client with MCP server
            from claude_agent_sdk import ClaudeAgentOptions
            options = ClaudeAgentOptions(
                system_prompt=system_prompt,
                mcp_servers={"portfolio_intelligence": mcp_server},
                allowed_tools=tool_names,
                max_turns=15
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

            user_prompt = f"""Analyze the following stocks and their data:

STOCKS SUMMARY:
{json.dumps(stocks_summary, indent=2)}

CURRENT PROMPTS USED FOR DATA FETCHING:
{json.dumps(prompts, indent=2)}

TASK:
1. Assess data quality and freshness for each stock
2. Review current prompts using the read_prompt tool
3. Optimize prompts if needed using the update_prompt tool
4. Provide investment recommendations for each stock
5. Use log_analysis_step to document your thinking process

Begin your analysis now."""

            # Execute query with streaming and real-time progress monitoring
            print(f"DEBUG: Starting Claude analysis with streaming (analysis_id={analysis_id})")
            logger.info(f"DEBUG: Starting Claude analysis with streaming for {len(stocks_data)} stocks")

            # Send query and monitor responses in real-time
            await client.query(user_prompt)

            response_chunks = []
            last_activity = time.time()
            message_timeout = 120.0  # Timeout if no message for 2 minutes (indicates hung state)

            print(f"DEBUG: Entering receive_messages() loop to monitor Claude progress")

            async for message in client.receive_messages():
                # Check for message timeout (indicates hung state)
                time_since_activity = time.time() - last_activity
                if time_since_activity > message_timeout:
                    error_msg = f"No activity from Claude for {int(time_since_activity)} seconds - analysis may be hung"
                    logger.error(error_msg)
                    print(f"DEBUG: {error_msg}")
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
                                print(f"DEBUG: Claude using tool: {block.name}")
                                logger.info(f"Claude executing tool: {block.name}")

                            elif isinstance(block, TextBlock):
                                # Claude is responding - RUNNING
                                response_chunks.append(block.text)
                                print(f"DEBUG: Received text chunk ({len(block.text)} chars, {len(response_chunks)} total chunks)")
                                logger.info(f"Claude text response ({len(response_chunks)} chunks total)")

                    elif isinstance(message, ToolResultBlock):
                        # Tool completed - STILL RUNNING
                        print(f"DEBUG: Tool result received")
                        logger.info("Tool execution result received")

                    elif isinstance(message, ResultMessage):
                        # Analysis complete - READY
                        print(f"DEBUG: Claude analysis complete (ResultMessage received)")
                        logger.info("Claude analysis completed - ResultMessage received")
                        break

                except Exception as e:
                    logger.warning(f"Error processing message type: {e}")
                    # Continue processing - don't fail on message type issues
                    pass

            print(f"DEBUG: Exit receive_messages() loop - received {len(response_chunks)} text chunks")
            logger.info(f"Claude analysis streaming complete: {len(response_chunks)} response chunks collected")

            # Assemble final response from chunks
            response = "\n".join(response_chunks) if response_chunks else ""
            execution_time_ms = int((time.time() - start_time) * 1000)

            print(f"DEBUG: Final response length: {len(response)} chars, execution time: {execution_time_ms}ms")

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
            print(f"DEBUG: Claude response type: {type(response)}")
            print(f"DEBUG: Claude response length: {len(response)}")
            print(f"DEBUG: Claude response (first 500 chars): {response[:500]}")
            logger.info(f"DEBUG: Claude response type: {type(response)}, length: {len(response)}")

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
                "execution_time_ms": execution_time_ms
            }

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
