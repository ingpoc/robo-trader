"""
AI Planning Engine for Robo Trader

Creates and optimizes work plans for intelligent trading operations.
Manages API budget allocation, sector rotation, and event-driven task insertion.
"""

import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass, asdict

from loguru import logger
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

from ..config import Config
from ..core.state import StateManager
from ..auth.claude_auth import validate_claude_api


@dataclass
class DailyTask:
    """Individual task in daily plan."""
    id: str
    symbol: str
    task_type: str  # "deep_analysis", "quick_check", "earnings_review", "event_response"
    priority: str  # "CRITICAL", "HIGH", "MEDIUM", "LOW"
    estimated_api_calls: int
    reason: str
    scheduled_time: str
    status: str = "pending"  # "pending", "in_progress", "completed", "failed"

    @classmethod
    def from_dict(cls, data: Dict) -> "DailyTask":
        return cls(**data)

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class DailyPlan:
    """Complete daily work plan."""
    date: str
    total_api_budget: int
    used_api_calls: int = 0
    tasks: List[DailyTask] = None
    sector_focus: List[str] = None
    events_to_monitor: List[str] = None
    created_at: str = ""
    status: str = "active"  # "active", "completed", "cancelled"

    def __post_init__(self):
        if self.tasks is None:
            self.tasks = []
        if self.sector_focus is None:
            self.sector_focus = []
        if self.events_to_monitor is None:
            self.events_to_monitor = []
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    @classmethod
    def from_dict(cls, data: Dict) -> "DailyPlan":
        if 'tasks' in data:
            data['tasks'] = [DailyTask.from_dict(task) for task in data['tasks']]
        return cls(**data)

    def to_dict(self) -> Dict:
        data = asdict(self)
        data['tasks'] = [task.to_dict() for task in self.tasks]
        return data


@dataclass
class WeeklyPlan:
    """Strategic weekly work distribution."""
    week_start: str
    sector_rotation: Dict[str, List[str]]  # day -> sectors
    api_budget_allocation: Dict[str, int]  # day -> api calls
    priority_stocks: List[str]
    events_calendar: Dict[str, List[str]]  # date -> events
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    @classmethod
    def from_dict(cls, data: Dict) -> "WeeklyPlan":
        return cls(**data)

    def to_dict(self) -> Dict:
        return asdict(self)


class AIPlanner:
    """
    AI creates and optimizes work plans for intelligent trading operations.

    Key responsibilities:
    - Generate daily work plans within API limits
    - Optimize weekly sector rotation
    - Handle urgent event-driven tasks
    - Learn from planning outcomes
    - Track API usage and budget
    """

    def __init__(self, config: Config, state_manager: StateManager):
        self.config = config
        self.state_manager = state_manager
        self.client: Optional[ClaudeSDKClient] = None

        # API budget management
        self.daily_api_limit = 25  # Claude Pro limit
        self.reserve_budget = 5    # Keep for emergencies

    async def initialize(self) -> None:
        """Initialize the AI planner."""
        logger.info("Initializing AI Planner")

        # Validate Claude access for planning
        auth_status = await validate_claude_api(self.config.integration.anthropic_api_key)
        if not auth_status.is_valid:
            logger.warning("Claude API not available for planning - using fallback logic")
            return

        # Create Claude client for planning operations
        options = ClaudeAgentOptions(
            allowed_tools=[],  # Planning doesn't need external tools
            system_prompt=self._get_planning_prompt(),
            max_turns=10
        )

        self.client = ClaudeSDKClient(options=options)
        await self.client.__aenter__()

        logger.info("AI Planner initialized successfully")

    async def create_daily_plan(self) -> Optional[DailyPlan]:
        """
        Generate optimal work plan for today using AI analysis.

        Analyzes:
        - Current portfolio state
        - Pending events (earnings, news)
        - API budget availability
        - Historical performance
        - Market conditions
        """
        try:
            today = datetime.now(timezone.utc).date().isoformat()

            # Get current context
            portfolio = await self.state_manager.get_portfolio()
            priority_items = await self.state_manager.get_priority_items()
            weekly_plan = await self._load_weekly_plan()

            # Build planning query
            planning_query = self._build_daily_planning_query(
                today, portfolio, priority_items, weekly_plan
            )

            if not self.client:
                # Fallback planning without Claude
                return await self._create_fallback_daily_plan(today, priority_items)

            # Use Claude for intelligent planning
            await self.client.query(planning_query)

            plan_data = None
            async for message in self.client.receive_response():
                if hasattr(message, 'content'):
                    for block in message.content:
                        if hasattr(block, 'text'):
                            try:
                                # Try to parse JSON plan from response
                                plan_data = json.loads(block.text)
                                break
                            except json.JSONDecodeError:
                                continue
                    if plan_data:
                        break

            if not plan_data:
                logger.warning("Failed to get structured plan from Claude, using fallback")
                return await self._create_fallback_daily_plan(today, priority_items)

            # Create and validate plan
            plan = DailyPlan.from_dict(plan_data)
            plan = await self._validate_and_adjust_plan(plan)

            # Save plan
            await self.state_manager.save_daily_plan(plan.to_dict())

            logger.info(f"Created daily plan for {today} with {len(plan.tasks)} tasks")
            return plan

        except Exception as e:
            logger.error(f"Failed to create daily plan: {e}")
            return None

    async def optimize_weekly_distribution(self) -> Optional[WeeklyPlan]:
        """
        Balance work across the week within API limits.

        Creates sector rotation schedule:
        - Monday: Banking sector deep analysis
        - Tuesday: IT sector deep analysis
        - Wednesday: Energy & Industrials
        - Thursday: Consumer & Healthcare
        - Friday: Remaining + opportunity scan
        """
        try:
            week_start = self._get_week_start().isoformat()

            # Get portfolio composition for sector analysis
            portfolio = await self.state_manager.get_portfolio()
            sector_weights = self._analyze_portfolio_sectors(portfolio)

            # Build weekly planning query
            planning_query = self._build_weekly_planning_query(sector_weights)

            if not self.client:
                return await self._create_fallback_weekly_plan(sector_weights)

            # Use Claude for strategic planning
            await self.client.query(planning_query)

            plan_data = None
            async for message in self.client.receive_response():
                if hasattr(message, 'content'):
                    for block in message.content:
                        if hasattr(block, 'text'):
                            try:
                                plan_data = json.loads(block.text)
                                break
                            except json.JSONDecodeError:
                                continue
                    if plan_data:
                        break

            if not plan_data:
                logger.warning("Failed to get structured weekly plan from Claude")
                return await self._create_fallback_weekly_plan(sector_weights)

            # Create weekly plan
            weekly_plan = WeeklyPlan.from_dict(plan_data)

            # Save plan
            await self.state_manager.save_weekly_plan(weekly_plan.to_dict())

            logger.info(f"Created weekly plan starting {week_start}")
            return weekly_plan

        except Exception as e:
            logger.error(f"Failed to create weekly plan: {e}")
            return None

    async def handle_urgent_events(self, symbol: str, event_type: str, data: Dict) -> None:
        """
        Insert urgent tasks into existing plan.

        Handles:
        - Earnings announcements
        - Stop loss triggers
        - Major news events
        - Technical breakouts
        """
        try:
            today = datetime.now(timezone.utc).date().isoformat()
            current_plan = await self.state_manager.load_daily_plan(today)

            if not current_plan:
                logger.info(f"No current plan for {today}, creating urgent task directly")
                await self.state_manager.add_priority_item(symbol, f"{event_type}: {data}", "CRITICAL")
                return

            # Create urgent task
            urgent_task = DailyTask(
                id=f"urgent_{int(datetime.now(timezone.utc).timestamp())}_{symbol}",
                symbol=symbol,
                task_type="event_response",
                priority="CRITICAL",
                estimated_api_calls=3,  # Urgent events get priority API allocation
                reason=f"Urgent {event_type}: {data.get('headline', 'Event triggered')}",
                scheduled_time=datetime.now(timezone.utc).isoformat(),
                status="pending"
            )

            # Insert at beginning of task list
            current_plan.tasks.insert(0, urgent_task)

            # Rebalance API budget if needed
            current_plan = await self._rebalance_api_budget(current_plan)

            # Save updated plan
            await self.state_manager.save_daily_plan(current_plan.to_dict())

            logger.info(f"Added urgent task for {symbol} due to {event_type}")

        except Exception as e:
            logger.error(f"Failed to handle urgent event for {symbol}: {e}")

    async def learn_from_outcomes(self) -> None:
        """
        Improve planning based on recommendation outcomes.

        Analyzes:
        - Which recommendations were profitable
        - Which sectors/strategies worked best
        - API usage efficiency
        - Planning accuracy
        """
        try:
            # Get recent outcomes
            recent_outcomes = await self._get_recent_recommendation_outcomes()

            if not recent_outcomes:
                logger.info("No recent outcomes to learn from")
                return

            # Build learning query
            learning_query = self._build_learning_query(recent_outcomes)

            if not self.client:
                logger.warning("Cannot learn without Claude client")
                return

            # Use Claude for analysis and learning
            await self.client.query(learning_query)

            insights = []
            async for message in self.client.receive_response():
                if hasattr(message, 'content'):
                    for block in message.content:
                        if hasattr(block, 'text'):
                            insights.append(block.text)

            if insights:
                # Store learning insights
                await self.state_manager.save_learning_insights({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "outcomes_analyzed": len(recent_outcomes),
                    "insights": insights,
                    "recommendations": self._extract_planning_recommendations(insights)
                })

                logger.info("Updated planning heuristics based on recent outcomes")

        except Exception as e:
            logger.error(f"Failed to learn from outcomes: {e}")

    async def get_current_task_status(self) -> Dict[str, Any]:
        """Get current AI activity status for UI display."""
        try:
            today = datetime.now(timezone.utc).date().isoformat()
            current_plan = await self.state_manager.load_daily_plan(today)

            if not current_plan:
                return {
                    "current_task": None,
                    "api_budget_used": 0,
                    "next_planned_task": None,
                    "active_analyses": 0,
                    "portfolio_health": "No data available",
                    "daily_api_limit": self.daily_api_limit
                }

            current_task = None
            next_task = None
            active_count = 0

            for task in current_plan.tasks:
                if task.status == "in_progress":
                    current_task = f"{task.task_type} on {task.symbol}"
                    active_count += 1
                elif task.status == "pending" and next_task is None:
                    next_task = f"{task.task_type} on {task.symbol}"

            portfolio = await self.state_manager.get_portfolio()
            portfolio_health = "Analyzing..."
            if portfolio:
                risk_score = portfolio.risk_aggregates.get("portfolio", {}).get("concentration_risk", 0) if portfolio.risk_aggregates else 0
                if risk_score < 20:
                    portfolio_health = "Healthy - Low concentration risk"
                elif risk_score < 35:
                    portfolio_health = "Moderate - Some concentration"
                else:
                    portfolio_health = "High risk - Diversification needed"

            return {
                "current_task": current_task,
                "api_budget_used": current_plan.used_api_calls,
                "next_planned_task": next_task,
                "active_analyses": active_count,
                "portfolio_health": portfolio_health,
                "daily_api_limit": self.daily_api_limit
            }

        except Exception as e:
            logger.error(f"Failed to get task status: {e}")
            return {
                "current_task": None,
                "api_budget_used": 0,
                "next_planned_task": None,
                "active_analyses": 0,
                "portfolio_health": "Error loading status",
                "daily_api_limit": self.daily_api_limit
            }

    def _get_planning_prompt(self) -> str:
        """Get the system prompt for AI planning."""
        return """
You are an expert financial planning AI for an autonomous trading system.

Your role is to create optimal work plans that maximize trading performance within API constraints.

Key constraints:
- Daily API limit: 25 calls (keep 5 in reserve for emergencies)
- Focus on high-conviction opportunities
- Balance sector coverage
- Prioritize urgent events (earnings, stop losses)
- Learn from past performance

Always respond with valid JSON structures for plans.
"""

    def _build_daily_planning_query(self, date: str, portfolio: Any, priority_items: List[Dict],
                                   weekly_plan: Optional[WeeklyPlan]) -> str:
        """Build Claude query for daily planning."""

        # Get sector focus for today
        sector_focus = []
        if weekly_plan and weekly_plan.sector_rotation:
            day_name = datetime.fromisoformat(date).strftime('%A').lower()
            sector_focus = weekly_plan.sector_rotation.get(day_name, [])

        query = f"""
Create an optimal daily trading plan for {date}.

Current Context:
- API Budget: {self.daily_api_limit} calls/day (reserve {self.reserve_budget} for emergencies)
- Portfolio: {len(portfolio.holdings) if portfolio else 0} holdings
- Priority Items: {len(priority_items)} urgent items
- Sector Focus: {', '.join(sector_focus) if sector_focus else 'General coverage'}

Priority Items:
{json.dumps(priority_items, indent=2)}

Create a DailyPlan JSON with this structure:
{{
  "date": "{date}",
  "total_api_budget": {self.daily_api_limit - self.reserve_budget},
  "tasks": [
    {{
      "id": "task_1",
      "symbol": "STOCK_SYMBOL",
      "task_type": "deep_analysis|quick_check|earnings_review|event_response",
      "priority": "CRITICAL|HIGH|MEDIUM|LOW",
      "estimated_api_calls": 1-4,
      "reason": "Brief explanation",
      "scheduled_time": "HH:MM format"
    }}
  ],
  "sector_focus": {json.dumps(sector_focus)},
  "events_to_monitor": ["earnings", "news", "technical_levels"]
}}

Guidelines:
1. Total estimated_api_calls should not exceed {self.daily_api_limit - self.reserve_budget}
2. Prioritize CRITICAL priority items first
3. Balance deep analysis (3-4 calls) vs quick checks (1 call)
4. Include time-based scheduling for market hours
5. Focus on high-conviction opportunities
"""

        return query

    def _build_weekly_planning_query(self, sector_weights: Dict[str, float]) -> str:
        """Build Claude query for weekly planning."""

        query = f"""
Create an optimal weekly trading plan balancing sector coverage and API efficiency.

Portfolio Sector Weights:
{json.dumps(sector_weights, indent=2)}

Create a WeeklyPlan JSON with this structure:
{{
  "week_start": "{self._get_week_start().isoformat()}",
  "sector_rotation": {{
    "monday": ["Banking", "Financial Services"],
    "tuesday": ["Information Technology"],
    "wednesday": ["Energy", "Industrials"],
    "thursday": ["Consumer Goods", "Healthcare"],
    "friday": ["Remaining Sectors", "Opportunity Scan"]
  }},
  "api_budget_allocation": {{
    "monday": 20,
    "tuesday": 20,
    "wednesday": 18,
    "thursday": 18,
    "friday": 15
  }},
  "priority_stocks": ["List of high-conviction stocks"],
  "events_calendar": {{
    "2024-10-08": ["Company X earnings"],
    "2024-10-09": ["Sector Y news"]
  }}
}}

Guidelines:
1. Distribute ~100 API calls across the week
2. Focus on sectors with highest portfolio weights
3. Include known earnings and events
4. Reserve Friday for catch-up and new opportunities
5. Balance deep analysis with monitoring
"""

        return query

    async def _create_fallback_daily_plan(self, date: str, priority_items: List[Dict]) -> DailyPlan:
        """Create basic daily plan when Claude is unavailable."""
        logger.info("Using fallback daily planning logic")

        plan = DailyPlan(
            date=date,
            total_api_budget=self.daily_api_limit - self.reserve_budget,
            sector_focus=["General"],
            events_to_monitor=["earnings", "stop_losses"]
        )

        # Add priority items as critical tasks
        for i, item in enumerate(priority_items[:3]):  # Limit to 3 urgent items
            task = DailyTask(
                id=f"priority_{i+1}",
                symbol=item["symbol"],
                task_type="event_response",
                priority="CRITICAL",
                estimated_api_calls=3,
                reason=item["reason"],
                scheduled_time="09:30"
            )
            plan.tasks.append(task)

        # Add basic portfolio monitoring
        if len(plan.tasks) < 5:  # Add up to 5 more tasks
            basic_stocks = ["RELIANCE", "TCS", "HDFC", "INFY", "ITC"]  # Common stocks
            for stock in basic_stocks[:5-len(plan.tasks)]:
                task = DailyTask(
                    id=f"monitor_{stock}",
                    symbol=stock,
                    task_type="quick_check",
                    priority="MEDIUM",
                    estimated_api_calls=1,
                    reason="Regular portfolio monitoring",
                    scheduled_time="14:30"
                )
                plan.tasks.append(task)

        return plan

    async def _create_fallback_weekly_plan(self, sector_weights: Dict[str, float]) -> WeeklyPlan:
        """Create basic weekly plan when Claude is unavailable."""
        logger.info("Using fallback weekly planning logic")

        week_start = self._get_week_start().isoformat()

        # Basic sector rotation
        sector_rotation = {
            "monday": ["Banking", "Financial Services"],
            "tuesday": ["Information Technology"],
            "wednesday": ["Energy", "Industrials"],
            "thursday": ["Consumer Goods", "Healthcare"],
            "friday": ["General", "Opportunity Scan"]
        }

        # Basic API allocation
        api_budget = {
            "monday": 20,
            "tuesday": 20,
            "wednesday": 18,
            "thursday": 18,
            "friday": 15
        }

        return WeeklyPlan(
            week_start=week_start,
            sector_rotation=sector_rotation,
            api_budget_allocation=api_budget,
            priority_stocks=list(sector_weights.keys())[:10],  # Top 10 sectors
            events_calendar={}
        )

    async def _validate_and_adjust_plan(self, plan: DailyPlan) -> DailyPlan:
        """Validate plan and adjust for API budget constraints."""
        total_estimated = sum(task.estimated_api_calls for task in plan.tasks)

        if total_estimated > plan.total_api_budget:
            logger.warning(f"Plan exceeds budget: {total_estimated} > {plan.total_api_budget}")

            # Sort tasks by priority and trim
            priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
            plan.tasks.sort(key=lambda t: priority_order.get(t.priority, 99))

            # Keep only tasks that fit budget
            kept_tasks = []
            used_budget = 0

            for task in plan.tasks:
                if used_budget + task.estimated_api_calls <= plan.total_api_budget:
                    kept_tasks.append(task)
                    used_budget += task.estimated_api_calls
                else:
                    break

            plan.tasks = kept_tasks
            logger.info(f"Trimmed plan to {len(kept_tasks)} tasks using {used_budget} API calls")

        return plan

    async def _rebalance_api_budget(self, plan: DailyPlan) -> DailyPlan:
        """Rebalance API budget when urgent tasks are added."""
        total_estimated = sum(task.estimated_api_calls for task in plan.tasks)

        if total_estimated > plan.total_api_budget:
            # Remove lowest priority tasks to make room
            priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
            plan.tasks.sort(key=lambda t: priority_order.get(t.priority, 99))

            # Keep critical tasks, trim others
            critical_tasks = [t for t in plan.tasks if t.priority == "CRITICAL"]
            other_tasks = [t for t in plan.tasks if t.priority != "CRITICAL"]

            # Calculate remaining budget after critical tasks
            critical_budget = sum(t.estimated_api_calls for t in critical_tasks)
            remaining_budget = plan.total_api_budget - critical_budget

            # Keep highest priority non-critical tasks that fit
            kept_other = []
            for task in other_tasks:
                if remaining_budget - task.estimated_api_calls >= 0:
                    kept_other.append(task)
                    remaining_budget -= task.estimated_api_calls

            plan.tasks = critical_tasks + kept_other

        return plan

    def _analyze_portfolio_sectors(self, portfolio: Any) -> Dict[str, float]:
        """Analyze portfolio sector composition."""
        if not portfolio or not portfolio.holdings:
            return {"General": 1.0}

        # Simple sector analysis (would be more sophisticated in real implementation)
        sectors = {}
        total_value = sum(h.get("market_value", 0) for h in portfolio.holdings)

        # Mock sector assignment (real implementation would use stock data)
        sector_map = {
            "RELIANCE": "Energy",
            "TCS": "Technology",
            "HDFC": "Banking",
            "INFY": "Technology",
            "ITC": "Consumer",
            "HINDUNILVR": "Consumer",
            "ICICIBANK": "Banking",
            "KOTAKBANK": "Banking"
        }

        for holding in portfolio.holdings:
            symbol = holding.get("symbol", "")
            value = holding.get("market_value", 0)
            sector = sector_map.get(symbol, "General")

            sectors[sector] = sectors.get(sector, 0) + value

        # Convert to weights
        if total_value > 0:
            sectors = {k: v/total_value for k, v in sectors.items()}

        return sectors

    def _get_week_start(self) -> datetime:
        """Get the start of current week (Monday)."""
        today = datetime.now(timezone.utc).date()
        week_start = today - timedelta(days=today.weekday())  # Monday
        return datetime.combine(week_start, datetime.min.time(), tzinfo=timezone.utc)

    async def _load_weekly_plan(self) -> Optional[WeeklyPlan]:
        """Load current weekly plan."""
        try:
            return await self.state_manager.load_weekly_plan()
        except Exception:
            return None

    async def _get_recent_recommendation_outcomes(self) -> List[Dict]:
        """Get recent recommendation outcomes for learning."""
        try:
            # This would query the state manager for recent trades and their outcomes
            # Simplified implementation
            return []
        except Exception:
            return []

    def _build_learning_query(self, outcomes: List[Dict]) -> str:
        """Build query for learning from outcomes."""
        return f"""
Analyze these recent trading outcomes to improve future planning:

Outcomes:
{json.dumps(outcomes, indent=2)}

Provide insights on:
1. Which types of recommendations were most profitable
2. Which sectors or strategies worked best
3. What patterns indicate higher success rates
4. How to adjust planning priorities
5. API usage efficiency observations

Respond with specific recommendations for improving the planning algorithm.
"""

    def _extract_planning_recommendations(self, insights: List[str]) -> List[str]:
        """Extract actionable planning recommendations from insights."""
        # Simple extraction - real implementation would be more sophisticated
        recommendations = []
        for insight in insights:
            if "recommend" in insight.lower() or "suggest" in insight.lower():
                recommendations.append(insight)
        return recommendations