"""
Prompt Builder for Portfolio Intelligence

Handles:
- System prompt creation
- Claude tools creation
- Prompt retrieval from database
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict

from claude_agent_sdk import tool

logger = logging.getLogger(__name__)


class PortfolioPromptBuilder:
    """Builds prompts and tools for portfolio intelligence analysis."""

    def __init__(self, config_state):
        self.config_state = config_state

    def create_system_prompt(self, stocks_data: Dict[str, Dict[str, Any]]) -> str:
        """Create system prompt explaining the analysis task to Claude."""

        symbols_list = "\n".join(
            [
                f"- {symbol}: {data.get('data_summary', {})}"
                for symbol, data in stocks_data.items()
            ]
        )

        system_prompt = f"""You are an expert financial analyst with access to comprehensive portfolio data analysis capabilities.

YOUR TASK:
Analyze the following stocks and their available data (earnings, news, fundamentals) to:
1. Evaluate if the available data is sufficient and current enough for making investment recommendations
2. Determine if any data is outdated or missing critical information
3. Review the prompts currently used to fetch data from Perplexity API
4. Optimize these prompts if they are not extracting sufficient or quality data
5. Provide investment recommendations based on the analysis

STOCKS TO ANALYZE:
{symbols_list}

AVAILABLE DATA FOR EACH STOCK:
- Earnings reports (EPS, revenue, guidance, dates)
- News items (headlines, sentiment, relevance scores, dates)
- Fundamental analysis (valuation, profitability, growth metrics, dates)
- Last update timestamps for each data type

YOUR PROCESS:

STEP 1: DATA QUALITY ASSESSMENT
For each stock, evaluate:
- Is the earnings data current (within last quarter)?
- Is the news data recent (within last week for major news)?
- Is the fundamental analysis comprehensive?
- Are there gaps in critical information?

STEP 2: PROMPT REVIEW AND OPTIMIZATION
- Review the current prompts used for fetching data from Perplexity:
  * earnings_processor: Used to fetch earnings and fundamental metrics
  * news_processor: Used to fetch market news and updates
  * deep_fundamental_processor: Used for comprehensive fundamental analysis

- For each prompt, evaluate:
  * Is it extracting all necessary data?
  * Is it requesting data in the right format?
  * Could it be improved to get better/more comprehensive data?

- If a prompt needs improvement:
  * Provide an optimized version
  * Explain why the change is needed
  * Ensure the optimized prompt maintains JSON structure compatibility

STEP 3: RECOMMENDATIONS
Based on your analysis, provide:
- Investment recommendations (BUY/HOLD/SELL) for each stock
- Confidence level (0-100%) for each recommendation
- Key reasons supporting each recommendation
- Risk factors to consider
- Suggested action if data is insufficient

IMPORTANT INSTRUCTIONS:
- Use the provided tools to read and update prompts in the database
- All your analysis and thinking should be transparent and logged
- If data is outdated, recommend fetching fresh data before making decisions
- Be conservative in recommendations if data quality is uncertain
- Focus on actionable insights, not generic advice

TOOLS AVAILABLE:
- read_prompt(prompt_name): Read current prompt from database
- update_prompt(prompt_name, new_content, description): Update prompt in database
- log_analysis_step(step_type, description, reasoning): Log your analysis steps
- log_recommendation(symbol, action, confidence, reasoning): Log investment recommendations

Begin your analysis now. Be thorough, transparent, and actionable."""

        return system_prompt

    def create_claude_tools(self) -> tuple:
        """Create tools and MCP server for Claude to interact with prompts and logging."""

        @tool(
            "read_prompt",
            "Read a prompt from the database by name",
            {"prompt_name": str},
        )
        async def read_prompt_tool(args: Dict[str, Any]) -> Dict[str, Any]:
            """Read prompt from database."""
            try:
                prompt_name = args.get("prompt_name")
                prompt_config = await self.config_state.get_prompt_config(prompt_name)

                return {
                    "content": [
                        {"type": "text", "text": json.dumps(prompt_config, indent=2)}
                    ]
                }
            except Exception as e:
                return {
                    "content": [
                        {"type": "text", "text": f"Error reading prompt: {str(e)}"}
                    ],
                    "is_error": True,
                }

        @tool(
            "update_prompt",
            "Update a prompt in the database",
            {"prompt_name": str, "new_content": str, "description": str},
        )
        async def update_prompt_tool(args: Dict[str, Any]) -> Dict[str, Any]:
            """Update prompt in database."""
            try:
                prompt_name = args.get("prompt_name")
                new_content = args.get("new_content")
                description = args.get(
                    "description",
                    f"Optimized by Claude AI at {datetime.now(timezone.utc).isoformat()}",
                )

                success = await self.config_state.update_prompt_config(
                    prompt_name=prompt_name,
                    prompt_content=new_content,
                    description=description,
                )

                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Successfully updated prompt: {prompt_name}",
                        }
                    ]
                }
            except Exception as e:
                return {
                    "content": [
                        {"type": "text", "text": f"Error updating prompt: {str(e)}"}
                    ],
                    "is_error": True,
                }

        @tool(
            "log_analysis_step",
            "Log an analysis step for transparency",
            {"step_type": str, "description": str, "reasoning": str},
        )
        async def log_analysis_step_tool(args: Dict[str, Any]) -> Dict[str, Any]:
            """Log analysis step."""
            try:
                logger.info(
                    f"Analysis step: {args.get('step_type')} - {args.get('description')}"
                )
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": "Analysis step will be logged to AI Transparency",
                        }
                    ]
                }
            except Exception as e:
                return {
                    "content": [
                        {"type": "text", "text": f"Error logging step: {str(e)}"}
                    ],
                    "is_error": True,
                }

        @tool(
            "log_recommendation",
            "Log an investment recommendation",
            {"symbol": str, "action": str, "confidence": float, "reasoning": str},
        )
        async def log_recommendation_tool(args: Dict[str, Any]) -> Dict[str, Any]:
            """Log recommendation."""
            try:
                logger.info(
                    f"Recommendation: {args.get('symbol')} - {args.get('action')} (confidence: {args.get('confidence')})"
                )
                return {
                    "content": [
                        {"type": "text", "text": "Recommendation will be logged"}
                    ]
                }
            except Exception as e:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Error logging recommendation: {str(e)}",
                        }
                    ],
                    "is_error": True,
                }

        # Create MCP server with tools
        from claude_agent_sdk import create_sdk_mcp_server

        mcp_server = create_sdk_mcp_server(
            name="portfolio_intelligence",
            version="1.0.0",
            tools=[
                read_prompt_tool,
                update_prompt_tool,
                log_analysis_step_tool,
                log_recommendation_tool,
            ],
        )

        # Return MCP server and tool names for allowed_tools
        tool_names = [
            "mcp__portfolio_intelligence__read_prompt",
            "mcp__portfolio_intelligence__update_prompt",
            "mcp__portfolio_intelligence__log_analysis_step",
            "mcp__portfolio_intelligence__log_recommendation",
        ]

        return mcp_server, tool_names

    async def get_current_prompts(self) -> Dict[str, str]:
        """Get current prompts from database."""
        prompts = {}
        prompt_names = [
            "earnings_processor",
            "news_processor",
            "deep_fundamental_processor",
        ]

        for prompt_name in prompt_names:
            try:
                prompt_config = await self.config_state.get_prompt_config(prompt_name)
                prompts[prompt_name] = prompt_config.get("content", "Prompt not found")
            except Exception as e:
                logger.warning(f"Could not get prompt {prompt_name}: {e}")
                prompts[prompt_name] = "Prompt not found"

        return prompts
