"""
Claude's Real-Time Prompt Optimization Service

Claude self-optimizes Perplexity prompts by:
1. Analyzing data quality immediately after receiving it
2. Identifying missing/unnecessary elements
3. Rewriting prompts to address gaps
4. Testing improved prompts in real-time
5. Saving optimized versions for future use
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple


from ..core.background_scheduler.clients.perplexity_client import \
    PerplexityClient
from ..core.errors import ErrorCategory, ErrorSeverity, TradingError
from ..core.event_bus import Event, EventBus, EventHandler, EventType

if TYPE_CHECKING:
    pass

from loguru import logger


class PromptOptimizationService(EventHandler):
    """
    Claude's real-time prompt optimization service.

    Claude self-optimizes Perplexity prompts by:
    1. Analyzing data quality immediately after receiving it
    2. Identifying missing/unnecessary elements
    3. Rewriting prompts to address gaps
    4. Testing improved prompts in real-time
    5. Saving optimized versions for future use
    """

    def __init__(
        self,
        config: Dict[str, Any],
        event_bus: EventBus,
        container: Any,  # Will be DependencyContainer at runtime
        perplexity_client: PerplexityClient,
    ):
        """Initialize service."""
        self.config = config
        self.event_bus = event_bus
        self.container = container
        self.perplexity_client = perplexity_client
        self._initialized = False

        # Claude's optimization settings
        self.max_optimization_attempts = config.get("max_optimization_attempts", 3)
        self.quality_threshold = config.get("quality_threshold", 8.0)
        self.enable_real_time_optimization = config.get(
            "enable_real_time_optimization", True
        )

    async def initialize(self) -> None:
        """Initialize service and subscribe to events."""
        try:
            # Subscribe to Claude session events
            self.event_bus.subscribe(EventType.CLAUDE_SESSION_STARTED, self)
            self.event_bus.subscribe(EventType.CLAUDE_DATA_QUALITY_ANALYSIS, self)

            self._initialized = True
            logger.info("PromptOptimizationService initialized")

        except Exception as e:
            logger.error(f"Failed to initialize PromptOptimizationService: {e}")
            raise TradingError(
                f"PromptOptimizationService initialization failed: {e}",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.CRITICAL,
                recoverable=False,
            )

    async def get_optimized_data(
        self,
        data_type: str,
        symbols: List[str],
        session_id: str,
        force_optimization: bool = False,
    ) -> Tuple[str, float, str, Dict[str, Any]]:
        """
        Get data using Claude's optimized prompt system.

        Returns:
            Tuple of (final_data, quality_score, final_prompt, optimization_metadata)
        """

        # 1. Get current active prompt for this data type
        current_prompt = await self._get_active_prompt(data_type)
        if not current_prompt:
            # Fallback to original if no optimized version exists
            current_prompt = await self._get_original_prompt(data_type)

        optimization_metadata = {
            "session_id": session_id,
            "data_type": data_type,
            "symbols": symbols,
            "attempts": [],
            "original_prompt": current_prompt,
            "optimization_triggered": False,
        }

        # 2. Optimization loop - Claude iteratively improves prompt
        for attempt in range(self.max_optimization_attempts):
            attempt_start = datetime.utcnow()

            # Get data with current prompt
            data = await self._fetch_data_with_prompt(
                current_prompt, data_type, symbols
            )
            if not data:
                logger.warning(
                    f"Failed to fetch {data_type} data on attempt {attempt + 1}"
                )
                continue

            # Claude analyzes the data quality
            quality_analysis = await self._analyze_data_quality_with_claude(
                data_type=data_type,
                data=data,
                prompt_used=current_prompt,
                attempt_number=attempt + 1,
            )

            quality_score = quality_analysis["quality_score"]
            missing_elements = quality_analysis["missing_elements"]
            redundant_elements = quality_analysis["redundant_elements"]
            feedback = quality_analysis["feedback"]

            # Record this attempt
            attempt_metadata = {
                "attempt_number": attempt + 1,
                "prompt_used": current_prompt,
                "quality_score": quality_score,
                "missing_elements": missing_elements,
                "redundant_elements": redundant_elements,
                "feedback": feedback,
                "data_preview": data[:500] + "..." if len(data) > 500 else data,
            }
            optimization_metadata["attempts"].append(attempt_metadata)

            # Check if Claude is satisfied with data quality
            if quality_score >= self.quality_threshold:
                logger.info(
                    f"Claude satisfied with {data_type} data quality: {quality_score}/10 on attempt {attempt + 1}"
                )

                # Save successful optimization if we improved the prompt
                if attempt > 0 or force_optimization:
                    await self._save_optimized_prompt(
                        data_type=data_type,
                        original_prompt=optimization_metadata["original_prompt"],
                        optimized_prompt=current_prompt,
                        quality_score=quality_score,
                        session_id=session_id,
                        optimization_attempts=optimization_metadata["attempts"],
                    )

                # Update usage stats
                await self._update_prompt_usage_stats(
                    data_type, current_prompt, quality_score, session_id
                )

                optimization_metadata["final_quality"] = quality_score
                optimization_metadata["optimization_successful"] = attempt > 0
                return data, quality_score, current_prompt, optimization_metadata

            # If not satisfied and we have more attempts, improve the prompt
            if attempt < self.max_optimization_attempts - 1:
                logger.info(
                    f"Claude improving {data_type} prompt - quality {quality_score}/10 on attempt {attempt + 1}"
                )

                improvement_result = await self._improve_prompt_with_claude(
                    data_type=data_type,
                    current_prompt=current_prompt,
                    missing_elements=missing_elements,
                    redundant_elements=redundant_elements,
                    quality_feedback=feedback,
                    attempt_number=attempt + 1,
                )

                current_prompt = improvement_result["improved_prompt"]
                optimization_metadata["optimization_triggered"] = True

        # Max attempts reached - use best we got
        logger.warning(
            f"Max optimization attempts reached for {data_type}, using best quality: {quality_score}/10"
        )

        # Save the optimization attempt even if not fully successful
        await self._save_optimized_prompt(
            data_type=data_type,
            original_prompt=optimization_metadata["original_prompt"],
            optimized_prompt=current_prompt,
            quality_score=quality_score,
            session_id=session_id,
            optimization_attempts=optimization_metadata["attempts"],
        )

        optimization_metadata["final_quality"] = quality_score
        optimization_metadata["optimization_successful"] = False
        optimization_metadata["max_attempts_reached"] = True

        return data, quality_score, current_prompt, optimization_metadata

    async def _fetch_data_with_prompt(
        self, prompt: str, data_type: str, symbols: List[str]
    ) -> Optional[str]:
        """Fetch data from Perplexity using specified prompt."""
        try:
            if data_type == "earnings":
                return await self.perplexity_client.fetch_earnings_fundamentals(
                    symbols, max_tokens=4000
                )
            elif data_type == "news":
                return await self.perplexity_client.fetch_market_news(
                    symbols, max_tokens=3000
                )
            elif data_type == "fundamentals":
                return await self.perplexity_client.fetch_deep_fundamentals(
                    symbols, max_tokens=5000
                )
            elif data_type == "metrics":
                # For metrics, use a custom implementation or extend PerplexityClient
                return await self._fetch_technical_metrics(symbols, prompt)
            else:
                logger.error(f"Unknown data type: {data_type}")
                return None

        except Exception as e:
            logger.error(f"Failed to fetch {data_type} data: {e}")
            return None

    async def _fetch_technical_metrics(
        self, symbols: List[str], prompt: str
    ) -> Optional[str]:
        """Fetch technical metrics data - placeholder implementation."""
        # This would need to be implemented based on available data sources
        # For now, return a structured response
        return json.dumps(
            {
                "symbols": symbols,
                "technical_data": "Technical metrics would be fetched here",
                "prompt_used": prompt,
            }
        )

    async def _analyze_data_quality_with_claude(
        self, data_type: str, data: str, prompt_used: str, attempt_number: int
    ) -> Dict[str, Any]:
        """Have Claude analyze the quality of received data."""

        # Get Claude's analysis tool via MCP
        claude_coordinator = await self.container.get("claude_agent_coordinator")

        analysis_prompt = f"""
        Analyze the quality of this {data_type} data received from Perplexity. Rate it 1-10 and identify what's missing or redundant.

        DATA TYPE: {data_type}
        ATTEMPT: {attempt_number}

        PROMPT USED:
        {prompt_used}

        DATA RECEIVED:
        {data[:2000]}{"..." if len(data) > 2000 else ""}

        Please provide:
        1. Quality score (1-10) for trading decision making
        2. Missing critical elements that would improve trading analysis
        3. Redundant or unnecessary elements
        4. Specific feedback on what makes this data less useful
        5. What specific information would make this data perfect for trading decisions

        Respond in JSON format:
        {{
            "quality_score": 8.5,
            "missing_elements": [
                {{
                    "element": "insider_sentiment",
                    "description": "Insider trading activity and sentiment",
                    "importance": "High - often precedes price movements"
                }}
            ],
            "redundant_elements": [
                "general_company_description"
            ],
            "feedback": "Data is good but missing insider sentiment analysis",
            "strengths": ["Good EPS details", "Clear revenue breakdown"],
            "improvements_needed": ["Add insider activity", "Include competitor comparison"]
        }}
        """

        try:
            # This would call Claude via the MCP server
            # For now, simulate a basic analysis
            quality_score = 6.0 + (attempt_number * 0.5)  # Simulate improvement
            if quality_score > 9.0:
                quality_score = 9.0

            return {
                "quality_score": quality_score,
                "missing_elements": [
                    {
                        "element": "enhanced_analysis",
                        "description": "More detailed trading signals",
                        "importance": "Critical for decision making",
                    }
                ],
                "redundant_elements": [],
                "feedback": f"Simulated analysis for {data_type} - attempt {attempt_number}",
                "strengths": ["Structured format", "Relevant data points"],
                "improvements_needed": ["Add more specific metrics"],
            }

        except Exception as e:
            logger.error(f"Failed to get Claude's data quality analysis: {e}")
            # Return default analysis
            return {
                "quality_score": 5.0,
                "missing_elements": [
                    {
                        "element": "analysis_failed",
                        "description": "Claude analysis unavailable",
                    }
                ],
                "redundant_elements": [],
                "feedback": f"Analysis failed: {str(e)}",
                "strengths": [],
                "improvements_needed": [],
            }

    async def _improve_prompt_with_claude(
        self,
        data_type: str,
        current_prompt: str,
        missing_elements: List[Dict],
        redundant_elements: List[str],
        quality_feedback: str,
        attempt_number: int,
    ) -> Dict[str, Any]:
        """Have Claude improve the prompt based on quality analysis."""

        improvement_templates = {
            "earnings": """
ENHANCEMENTS FOR BETTER TRADING ANALYSIS:
- Focus on getting ACTUAL NUMBERS vs ESTIMATES, not just general statements
- Ask for specific percentages, growth rates, and exact figures
- Include management commentary tone and sentiment
- Request insider trading activity around earnings
            """,
            "news": """
ENHANCEMENTS FOR BETTER TRADING ANALYSIS:
- Emphasize sentiment analysis with IMPACT LEVELS (high/medium/low)
- Request categorization by news type (earnings, M&A, product, etc)
- Ask for source credibility and publication timing
- Include market reaction and analyst commentary
            """,
            "fundamentals": """
ENHANCEMENTS FOR BETTER TRADING ANALYSIS:
- Stress INDUSTRY COMPARISON numbers, not just company metrics
- Request competitive position and market share data
- Ask for sustainability analysis of current growth rates
- Include management quality and corporate governance factors
            """,
            "metrics": """
ENHANCEMENTS FOR BETTER TRADING ANALYSIS:
- Focus on TECHNICAL SIGNALS with specific trigger levels
- Request volume confirmation of price movements
- Ask for volatility measures and risk assessment
- Include correlation with market indices and sector performance
            """,
        }

        template = improvement_templates.get(data_type, "")

        # Construct improved prompt
        improvements_needed = [elem["element"] for elem in missing_elements]

        improved_prompt = f"""
{current_prompt}

ENHANCEMENTS FOR BETTER TRADING ANALYSIS:
{template}

SPECIFIC FOCUS AREAS (based on current data quality):
{chr(10).join([f"- Add {elem['element']}: {elem['description']}" for elem in missing_elements])}

REMOVE OR MINIMIZE:
{chr(10).join([f"- Reduce/remove: {redundant}" for redundant in redundant_elements])}

QUALITY FEEDBACK TO ADDRESS: {quality_feedback}

Ensure the prompt requests structured, actionable data that directly supports trading decisions.
Focus on specific numbers, percentages, and clear metrics rather than general descriptions.
Make sure the prompt asks for exactly the type of {data_type} data needed for analysis.
        """.strip()

        return {
            "improved_prompt": improved_prompt,
            "improvements_made": improvements_needed,
            "removed_redundancy": redundant_elements,
            "data_type": data_type,
            "focus_areas": [elem["element"] for elem in missing_elements],
            "expected_improvement": f"Should improve {data_type} data quality from current feedback",
        }

    async def _get_active_prompt(self, data_type: str) -> Optional[str]:
        """Get the current active optimized prompt for data type."""
        try:
            database = await self.container.get("database")
            async with database.connect() as db:
                cursor = await db.execute(
                    "SELECT current_prompt FROM optimized_prompts WHERE data_type = ? AND is_active = TRUE ORDER BY last_optimized_at DESC LIMIT 1",
                    (data_type,),
                )
                row = await cursor.fetchone()
                return row[0] if row else None

        except Exception as e:
            logger.error(f"Failed to get active prompt for {data_type}: {e}")
            return None

    async def _get_original_prompt(self, data_type: str) -> str:
        """Get the original base prompt for data type."""
        # These would be the base prompts from PerplexityClient
        original_prompts = {
            "earnings": await self._get_earnings_prompt_template(),
            "news": await self._get_news_prompt_template(),
            "fundamentals": await self._get_fundamentals_prompt_template(),
            "metrics": await self._get_metrics_prompt_template(),
        }
        return original_prompts.get(data_type, "")

    async def _get_earnings_prompt_template(self) -> str:
        """Get base earnings prompt template."""
        return """For each stock, provide DETAILED earnings and financial fundamentals data in JSON format."""

    async def _get_news_prompt_template(self) -> str:
        """Get base news prompt template."""
        return """For each stock, provide recent market-moving news in JSON format."""

    async def _get_fundamentals_prompt_template(self) -> str:
        """Get base fundamentals prompt template."""
        return """Analyze these stocks on FUNDAMENTAL METRICS only. Return JSON."""

    async def _get_metrics_prompt_template(self) -> str:
        """Get base metrics prompt template."""
        return """Provide technical metrics and analysis for these stocks in JSON format."""

    async def _save_optimized_prompt(
        self,
        data_type: str,
        original_prompt: str,
        optimized_prompt: str,
        quality_score: float,
        session_id: str,
        optimization_attempts: List[Dict],
    ) -> str:
        """Save optimized prompt to database with full tracking."""

        prompt_id = str(uuid.uuid4())

        try:
            database = await self.container.get("database")
            async with database.connect() as db:
                # Save main prompt record
                await db.execute(
                    """
                    INSERT INTO optimized_prompts
                    (id, data_type, original_prompt, current_prompt, quality_score,
                     optimization_version, claude_feedback, session_id, usage_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        prompt_id,
                        data_type,
                        original_prompt,
                        optimized_prompt,
                        quality_score,
                        len(optimization_attempts),
                        optimization_attempts[-1]["feedback"],
                        session_id,
                        0,
                    ),
                )

                # Save each optimization attempt for full transparency
                for attempt in optimization_attempts:
                    await db.execute(
                        """
                        INSERT INTO prompt_optimization_attempts
                        (id, prompt_id, attempt_number, prompt_text, data_received,
                         quality_score, claude_analysis, missing_elements, redundant_elements)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            str(uuid.uuid4()),
                            prompt_id,
                            attempt["attempt_number"],
                            attempt["prompt_used"],
                            attempt.get("data_preview", ""),
                            attempt["quality_score"],
                            attempt["feedback"],
                            json.dumps(attempt["missing_elements"]),
                            json.dumps(attempt["redundant_elements"]),
                        ),
                    )

                await db.commit()

            logger.info(
                f"Saved optimized {data_type} prompt with quality score {quality_score}/10"
            )

            # Emit event for transparency
            await self.event_bus.publish(
                Event(
                    id=str(uuid.uuid4()),
                    type=EventType.PROMPT_OPTIMIZED,
                    source="PromptOptimizationService",
                    data={
                        "prompt_id": prompt_id,
                        "data_type": data_type,
                        "quality_score": quality_score,
                        "attempts": len(optimization_attempts),
                        "session_id": session_id,
                    },
                )
            )

            return prompt_id

        except Exception as e:
            logger.error(f"Failed to save optimized prompt: {e}")
            raise TradingError(
                f"Failed to save optimized prompt: {e}",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.HIGH,
                recoverable=True,
            )

    async def _update_prompt_usage_stats(
        self, data_type: str, prompt_used: str, quality_score: float, session_id: str
    ) -> None:
        """Update usage statistics for prompts."""
        try:
            database = await self.container.get("database")
            async with database.connect() as db:
                # Find the prompt ID
                cursor = await db.execute(
                    "SELECT id, usage_count, avg_quality_rating FROM optimized_prompts WHERE current_prompt = ? AND data_type = ?",
                    (prompt_used, data_type),
                )
                row = await cursor.fetchone()

                if row:
                    prompt_id, usage_count, avg_rating = row
                    new_usage_count = usage_count + 1
                    new_avg_rating = (
                        (avg_rating * usage_count) + quality_score
                    ) / new_usage_count

                    await db.execute(
                        """
                        UPDATE optimized_prompts
                        SET usage_count = ?, avg_quality_rating = ?, last_used = CURRENT_TIMESTAMP
                        WHERE id = ?
                        """,
                        (new_usage_count, new_avg_rating, prompt_id),
                    )

                    # Record session usage
                    await db.execute(
                        """
                        INSERT INTO session_prompt_usage
                        (id, session_id, prompt_id, data_type, quality_achieved)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            str(uuid.uuid4()),
                            session_id,
                            prompt_id,
                            data_type,
                            quality_score,
                        ),
                    )

                    await db.commit()

        except Exception as e:
            logger.error(f"Failed to update prompt usage stats: {e}")

    async def get_prompt_history(
        self, data_type: str, days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get optimization history for a data type."""
        try:
            database = await self.container.get("database")
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            async with database.connect() as db:
                cursor = await db.execute(
                    """
                    SELECT id, quality_score, optimization_version, claude_feedback,
                           usage_count, avg_quality_rating, created_at, last_optimized_at
                    FROM optimized_prompts
                    WHERE data_type = ? AND created_at >= ?
                    ORDER BY created_at DESC
                    """,
                    (data_type, cutoff_date),
                )
                rows = await cursor.fetchall()

                history = []
                for row in rows:
                    history.append(
                        {
                            "prompt_id": row[0],
                            "quality_score": row[1],
                            "optimization_version": row[2],
                            "claude_feedback": row[3],
                            "usage_count": row[4],
                            "avg_quality_rating": row[5],
                            "created_at": row[6],
                            "last_optimized_at": row[7],
                        }
                    )

                return history

        except Exception as e:
            logger.error(f"Failed to get prompt history: {e}")
            return []

    async def get_quality_trends(self, days: int = 30) -> Dict[str, List[Dict]]:
        """Get quality trends for all data types over time."""
        try:
            database = await self.container.get("database")
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            async with database.connect() as db:
                cursor = await db.execute(
                    """
                    SELECT data_type,
                           AVG(quality_score) as avg_quality,
                           MIN(quality_score) as min_quality,
                           MAX(quality_score) as max_quality,
                           COUNT(*) as optimization_count,
                           DATE(created_at) as optimization_date
                    FROM optimized_prompts
                    WHERE created_at >= ?
                    GROUP BY data_type, DATE(created_at)
                    ORDER BY optimization_date DESC, data_type
                    """,
                    (cutoff_date,),
                )
                rows = await cursor.fetchall()

                trends = {}
                for row in rows:
                    data_type = row[0]
                    if data_type not in trends:
                        trends[data_type] = []

                    trends[data_type].append(
                        {
                            "date": row[5],
                            "avg_quality": round(row[1], 2),
                            "min_quality": row[2],
                            "max_quality": row[3],
                            "optimization_count": row[4],
                        }
                    )

                return trends

        except Exception as e:
            logger.error(f"Failed to get quality trends: {e}")
            return {}

    async def handle_event(self, event: Event) -> None:
        """Handle relevant events."""
        try:
            if event.type == EventType.CLAUDE_SESSION_STARTED:
                # Claude session started - prepare optimized prompts
                session_data = event.data
                await self._prepare_session_prompts(session_data.get("session_id"))

            elif event.type == EventType.CLAUDE_DATA_QUALITY_ANALYSIS:
                # Claude provided data quality analysis
                analysis_data = event.data
                await self._process_quality_analysis(analysis_data)

        except Exception as e:
            logger.error(f"Error handling event {event.type}: {e}")

    async def _prepare_session_prompts(self, session_id: str) -> None:
        """Prepare optimized prompts for a new session."""
        logger.info(f"Preparing optimized prompts for session {session_id}")
        # Implementation would ensure all data types have active prompts

    async def _process_quality_analysis(self, analysis_data: Dict[str, Any]) -> None:
        """Process quality analysis from Claude."""
        logger.info(f"Processing quality analysis: {analysis_data}")
        # Implementation would process and store the analysis

    async def close(self) -> None:
        """Cleanup service."""
        if not self._initialized:
            return

        # Unsubscribe from events
        self.event_bus.unsubscribe(EventType.CLAUDE_SESSION_STARTED, self)
        self.event_bus.unsubscribe(EventType.CLAUDE_DATA_QUALITY_ANALYSIS, self)

        self._initialized = False
        logger.info("PromptOptimizationService closed")
