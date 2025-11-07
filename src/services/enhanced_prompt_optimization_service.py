"""
Enhanced Prompt Optimization Service.

Manages prompt templates, optimization, and performance tracking for
Claude Agent SDK interactions across different workflow contexts.
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import hashlib
import re

from loguru import logger
from src.core.event_bus import EventBus, Event, EventType
from src.core.errors import TradingError, ErrorCategory, ErrorSeverity
from src.models.scheduler import TaskType

logger = logging.getLogger(__name__)


class PromptType(Enum):
    """Types of prompts supported by the optimization system."""
    MARKET_RESEARCH = "market_research"
    PORTFOLIO_ANALYSIS = "portfolio_analysis"
    TRADE_EXECUTION = "trade_execution"
    RISK_ASSESSMENT = "risk_assessment"
    STRATEGY_OPTIMIZATION = "strategy_optimization"
    NEWS_ANALYSIS = "news_analysis"
    EARNINGS_ANALYSIS = "earnings_analysis"
    GENERAL_QUERY = "general_query"


class OptimizationStatus(Enum):
    """Status of prompt optimization."""
    ACTIVE = "active"
    TESTING = "testing"
    DEPRECATED = "deprecated"
    FAILED = "failed"


@dataclass
class PromptTemplate:
    """Represents a prompt template with metadata."""
    id: str
    name: str
    prompt_type: PromptType
    template: str
    variables: List[str]
    context_requirements: List[str]
    performance_metrics: Dict[str, float]
    usage_count: int
    success_rate: float
    avg_response_time_ms: float
    token_efficiency_score: float
    created_at: datetime
    last_used: datetime
    status: OptimizationStatus
    version: int
    parent_template_id: Optional[str] = None


@dataclass
class PromptPerformance:
    """Performance metrics for a prompt."""
    template_id: str
    usage_count: int
    success_count: int
    error_count: int
    total_response_time_ms: float
    total_tokens_used: int
    avg_response_quality_score: float
    last_updated: datetime


@dataclass
class OptimizationExperiment:
    """A/B testing experiment for prompt optimization."""
    id: str
    name: str
    control_template_id: str
    variant_template_ids: List[str]
    traffic_split: Dict[str, float]  # template_id -> percentage (0-1)
    start_time: datetime
    end_time: Optional[datetime]
    sample_size_per_variant: int
    statistical_significance: float
    winning_template_id: Optional[str]
    status: str


class EnhancedPromptOptimizationService:
    """
    Enhanced service for managing prompt templates and optimization.

    Handles:
    - Prompt template management and versioning
    - A/B testing for prompt optimization
    - Performance tracking and analytics
    - Contextual prompt selection
    - Token efficiency optimization
    """

    def __init__(self, container):
        """Initialize enhanced prompt optimization service."""
        self.container = container
        self.event_bus: Optional[EventBus] = None
        self._initialized = False

        # Storage
        self._templates: Dict[str, PromptTemplate] = {}
        self._performance_data: Dict[str, PromptPerformance] = {}
        self._active_experiments: Dict[str, OptimizationExperiment] = {}

        # File paths
        self.templates_dir = Path("state/prompt_templates")
        self.templates_file = self.templates_dir / "templates.json"
        self.performance_file = self.templates_dir / "performance.json"
        self.experiments_file = self.templates_dir / "experiments.json"

        # Optimization settings
        self.min_sample_size = 20  # Minimum samples for statistical significance
        self.significance_threshold = 0.05  # p-value threshold
        self.performance_update_interval = 3600  # Update every hour

        # Background tasks
        self._performance_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None

    async def initialize(self) -> None:
        """Initialize enhanced prompt optimization service."""
        if self._initialized:
            return

        try:
            # Get dependencies
            self.event_bus = await self.container.get("event_bus")

            # Create directories
            self.templates_dir.mkdir(parents=True, exist_ok=True)

            # Load existing data
            await self._load_templates()
            await self._load_performance_data()
            await self._load_experiments()

            # Subscribe to events
            self.event_bus.subscribe(EventType.CLAUDE_REQUEST_COMPLETED, self)
            self.event_bus.subscribe(EventType.CLAUDE_REQUEST_FAILED, self)

            # Start background tasks
            self._performance_task = asyncio.create_task(self._performance_update_loop())
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

            # Create default templates if none exist
            if not self._templates:
                await self._create_default_templates()

            self._initialized = True
            logger.info("Enhanced Prompt Optimization Service initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Enhanced Prompt Optimization Service: {e}")
            raise TradingError(
                f"Enhanced Prompt Optimization Service initialization failed: {e}",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.CRITICAL,
                recoverable=False
            )

    async def handle_event(self, event: Event) -> None:
        """Handle events for performance tracking."""
        try:
            if event.type == EventType.CLAUDE_REQUEST_COMPLETED:
                await self._handle_claude_request_completed(event)
            elif event.type == EventType.CLAUDE_REQUEST_FAILED:
                await self._handle_claude_request_failed(event)

        except Exception as e:
            logger.error(f"Error handling prompt optimization event {event.type}: {e}")

    async def _handle_claude_request_completed(self, event: Event) -> None:
        """Handle successful Claude request for performance tracking."""
        data = event.data
        template_id = data.get("template_id")
        if not template_id:
            return

        # Update performance metrics
        if template_id not in self._performance_data:
            self._performance_data[template_id] = PromptPerformance(
                template_id=template_id,
                usage_count=0,
                success_count=0,
                error_count=0,
                total_response_time_ms=0.0,
                total_tokens_used=0,
                avg_response_quality_score=0.0,
                last_updated=datetime.now(timezone.utc)
            )

        perf = self._performance_data[template_id]
        perf.usage_count += 1
        perf.success_count += 1
        perf.total_response_time_ms += data.get("response_time_ms", 0)
        perf.total_tokens_used += data.get("tokens_used", 0)

        # Update quality score if provided
        quality_score = data.get("quality_score")
        if quality_score is not None:
            if perf.avg_response_quality_score == 0:
                perf.avg_response_quality_score = quality_score
            else:
                # Exponential moving average
                alpha = 0.3
                perf.avg_response_quality_score = (
                    alpha * quality_score +
                    (1 - alpha) * perf.avg_response_quality_score
                )

        perf.last_updated = datetime.now(timezone.utc)

        # Update template metrics
        if template_id in self._templates:
            template = self._templates[template_id]
            template.usage_count += 1
            template.success_rate = perf.success_count / perf.usage_count
            template.avg_response_time_ms = perf.total_response_time_ms / perf.usage_count
            template.last_used = datetime.now(timezone.utc)

    async def _handle_claude_request_failed(self, event: Event) -> None:
        """Handle failed Claude request for performance tracking."""
        data = event.data
        template_id = data.get("template_id")
        if not template_id:
            return

        # Update performance metrics
        if template_id not in self._performance_data:
            self._performance_data[template_id] = PromptPerformance(
                template_id=template_id,
                usage_count=0,
                success_count=0,
                error_count=0,
                total_response_time_ms=0.0,
                total_tokens_used=0,
                avg_response_quality_score=0.0,
                last_updated=datetime.now(timezone.utc)
            )

        perf = self._performance_data[template_id]
        perf.usage_count += 1
        perf.error_count += 1
        perf.last_updated = datetime.now(timezone.utc)

        # Update template metrics
        if template_id in self._templates:
            template = self._templates[template_id]
            template.usage_count += 1
            template.success_rate = perf.success_count / perf.usage_count

    async def get_optimal_prompt(
        self,
        prompt_type: PromptType,
        context: Dict[str, Any],
        variables: Dict[str, Any]
    ) -> Tuple[PromptTemplate, str]:
        """
        Get the optimal prompt template for the given context.

        Returns tuple of (template, rendered_prompt).
        """
        try:
            # Check for active experiments
            experiment = await self._get_active_experiment(prompt_type)
            if experiment:
                template_id = await self._select_experiment_template(experiment)
            else:
                template_id = await self._select_best_template(prompt_type, context)

            if not template_id or template_id not in self._templates:
                # Fallback to default template
                template_id = await self._get_default_template_id(prompt_type)

            template = self._templates[template_id]
            rendered_prompt = await self._render_template(template, variables)

            # Track usage
            template.last_used = datetime.now(timezone.utc)

            return template, rendered_prompt

        except Exception as e:
            logger.error(f"Error getting optimal prompt: {e}")
            # Return fallback template
            fallback_template = await self._get_fallback_template(prompt_type)
            return fallback_template, await self._render_template(fallback_template, variables)

    async def create_template(
        self,
        name: str,
        prompt_type: PromptType,
        template: str,
        variables: List[str],
        context_requirements: List[str],
        parent_template_id: Optional[str] = None
    ) -> str:
        """Create a new prompt template."""
        try:
            template_id = self._generate_template_id(name, template)

            # Determine version
            version = 1
            if parent_template_id and parent_template_id in self._templates:
                version = self._templates[parent_template_id].version + 1

            prompt_template = PromptTemplate(
                id=template_id,
                name=name,
                prompt_type=prompt_type,
                template=template,
                variables=variables,
                context_requirements=context_requirements,
                performance_metrics={},
                usage_count=0,
                success_rate=0.0,
                avg_response_time_ms=0.0,
                token_efficiency_score=0.0,
                created_at=datetime.now(timezone.utc),
                last_used=datetime.now(timezone.utc),
                status=OptimizationStatus.TESTING,
                version=version,
                parent_template_id=parent_template_id
            )

            self._templates[template_id] = prompt_template

            # Initialize performance tracking
            self._performance_data[template_id] = PromptPerformance(
                template_id=template_id,
                usage_count=0,
                success_count=0,
                error_count=0,
                total_response_time_ms=0.0,
                total_tokens_used=0,
                avg_response_quality_score=0.0,
                last_updated=datetime.now(timezone.utc)
            )

            # Save to file
            await self._save_templates()

            # Emit event
            await self._emit_template_created_event(template_id, prompt_type)

            logger.info(f"Created prompt template: {template_id}")
            return template_id

        except Exception as e:
            logger.error(f"Error creating prompt template: {e}")
            raise TradingError(
                f"Failed to create prompt template: {e}",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.MEDIUM,
                recoverable=True
            )

    async def create_experiment(
        self,
        name: str,
        control_template_id: str,
        variant_template_ids: List[str],
        sample_size: int = 100,
        duration_days: int = 7
    ) -> str:
        """Create an A/B testing experiment for prompt optimization."""
        try:
            experiment_id = self._generate_experiment_id(name)

            # Even traffic split initially
            total_templates = len(variant_template_ids) + 1  # +1 for control
            traffic_split = {control_template_id: 1.0 / total_templates}
            for variant_id in variant_template_ids:
                traffic_split[variant_id] = 1.0 / total_templates

            experiment = OptimizationExperiment(
                id=experiment_id,
                name=name,
                control_template_id=control_template_id,
                variant_template_ids=variant_template_ids,
                traffic_split=traffic_split,
                start_time=datetime.now(timezone.utc),
                end_time=None,
                sample_size_per_variant=sample_size,
                statistical_significance=0.0,
                winning_template_id=None,
                status="active"
            )

            self._active_experiments[experiment_id] = experiment

            # Save experiments
            await self._save_experiments()

            logger.info(f"Created A/B experiment: {experiment_id}")
            return experiment_id

        except Exception as e:
            logger.error(f"Error creating experiment: {e}")
            raise TradingError(
                f"Failed to create experiment: {e}",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.MEDIUM,
                recoverable=True
            )

    async def get_template_analytics(self, template_id: str) -> Dict[str, Any]:
        """Get analytics for a specific template."""
        if template_id not in self._templates:
            return {"error": "Template not found"}

        template = self._templates[template_id]
        performance = self._performance_data.get(template_id)

        analytics = {
            "template": asdict(template),
            "performance": asdict(performance) if performance else None,
            "comparison": await self._compare_with_peers(template_id),
            "recommendations": await self._generate_template_recommendations(template_id)
        }

        return analytics

    async def get_optimization_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive optimization dashboard data."""
        return {
            "templates": {
                prompt_type.value: await self._get_templates_by_type(prompt_type)
                for prompt_type in PromptType
            },
            "active_experiments": [
                asdict(exp) for exp in self._active_experiments.values()
                if exp.status == "active"
            ],
            "performance_summary": await self._get_performance_summary(),
            "optimization_opportunities": await self._identify_optimization_opportunities(),
            "recent_improvements": await self._get_recent_improvements()
        }

    async def _select_best_template(
        self,
        prompt_type: PromptType,
        context: Dict[str, Any]
    ) -> Optional[str]:
        """Select the best performing template for the given type and context."""
        candidates = [
            template for template in self._templates.values()
            if (template.prompt_type == prompt_type and
                template.status == OptimizationStatus.ACTIVE and
                self._check_context_requirements(template, context))
        ]

        if not candidates:
            return None

        # Sort by composite score (success_rate, response_time, token_efficiency)
        def calculate_score(template: PromptTemplate) -> float:
            perf = self._performance_data.get(template.id)
            if not perf or perf.usage_count < self.min_sample_size:
                return 0.0

            # Weighted score: 40% success rate, 30% speed, 30% token efficiency
            success_score = template.success_rate
            speed_score = 1.0 / (1.0 + template.avg_response_time_ms / 1000.0)  # Normalize to 0-1
            token_score = template.token_efficiency_score

            return 0.4 * success_score + 0.3 * speed_score + 0.3 * token_score

        best_template = max(candidates, key=calculate_score)
        return best_template.id

    async def _render_template(self, template: PromptTemplate, variables: Dict[str, Any]) -> str:
        """Render a template with provided variables."""
        rendered = template.template

        # Replace variables using {{variable}} syntax
        for var_name, var_value in variables.items():
            if var_name in template.variables:
                placeholder = f"{{{{{var_name}}}}}"
                rendered = rendered.replace(placeholder, str(var_value))

        return rendered

    async def _create_default_templates(self) -> None:
        """Create default prompt templates for each type."""
        default_templates = [
            {
                "name": "Market Research Default",
                "prompt_type": PromptType.MARKET_RESEARCH,
                "template": """Analyze the market data for {{symbols}} with focus on:
1. Recent price movements and trends
2. Volume analysis and trading patterns
3. Key support and resistance levels
4. Market sentiment indicators
5. Relevant news and catalysts

Please provide a comprehensive analysis with specific recommendations.""",
                "variables": ["symbols"],
                "context_requirements": ["market_data"]
            },
            {
                "name": "Portfolio Analysis Default",
                "prompt_type": PromptType.PORTFOLIO_ANALYSIS,
                "template": """Analyze the following portfolio:
- Holdings: {{holdings}}
- Cash position: {{cash}}
- Risk tolerance: {{risk_tolerance}}

Provide recommendations for:
1. Portfolio optimization
2. Risk management
3. Rebalancing opportunities
4. Performance improvement""",
                "variables": ["holdings", "cash", "risk_tolerance"],
                "context_requirements": ["portfolio_data"]
            },
            {
                "name": "Trade Execution Default",
                "prompt_type": PromptType.TRADE_EXECUTION,
                "template": """Evaluate this trade opportunity:
- Symbol: {{symbol}}
- Action: {{action}}
- Quantity: {{quantity}}
- Reason: {{reason}}
- Risk level: {{risk_level}}

Provide execution strategy including:
1. Optimal entry/exit points
2. Position sizing recommendations
3. Risk management measures
4. Stop-loss and target levels""",
                "variables": ["symbol", "action", "quantity", "reason", "risk_level"],
                "context_requirements": ["market_data", "portfolio_data"]
            }
        ]

        for template_data in default_templates:
            await self.create_template(**template_data)

    def _generate_template_id(self, name: str, template: str) -> str:
        """Generate unique template ID."""
        content = f"{name}_{template}_{datetime.now().isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:16]

    def _generate_experiment_id(self, name: str) -> str:
        """Generate unique experiment ID."""
        content = f"exp_{name}_{datetime.now().isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:16]

    def _check_context_requirements(self, template: PromptTemplate, context: Dict[str, Any]) -> bool:
        """Check if context meets template requirements."""
        return all(req in context for req in template.context_requirements)

    async def _get_active_experiment(self, prompt_type: PromptType) -> Optional[OptimizationExperiment]:
        """Get active experiment for prompt type."""
        for experiment in self._active_experiments.values():
            if experiment.status == "active":
                control_template = self._templates.get(experiment.control_template_id)
                if control_template and control_template.prompt_type == prompt_type:
                    return experiment
        return None

    async def _select_experiment_template(self, experiment: OptimizationExperiment) -> str:
        """Select template based on experiment traffic split."""
        import random
        templates = list(experiment.traffic_split.keys())
        weights = list(experiment.traffic_split.values())
        return random.choices(templates, weights=weights)[0]

    async def _get_default_template_id(self, prompt_type: PromptType) -> Optional[str]:
        """Get default template ID for prompt type."""
        for template in self._templates.values():
            if (template.prompt_type == prompt_type and
                "default" in template.name.lower() and
                template.status == OptimizationStatus.ACTIVE):
                return template.id
        return None

    async def _get_fallback_template(self, prompt_type: PromptType) -> PromptTemplate:
        """Get fallback template when no suitable template found."""
        return PromptTemplate(
            id="fallback",
            name="Fallback Template",
            prompt_type=prompt_type,
            template="Please analyze the following data: {{data}}",
            variables=["data"],
            context_requirements=[],
            performance_metrics={},
            usage_count=0,
            success_rate=0.0,
            avg_response_time_ms=0.0,
            token_efficiency_score=0.0,
            created_at=datetime.now(timezone.utc),
            last_used=datetime.now(timezone.utc),
            status=OptimizationStatus.ACTIVE,
            version=1
        )

    async def _compare_with_peers(self, template_id: str) -> Dict[str, Any]:
        """Compare template performance with peers of same type."""
        template = self._templates.get(template_id)
        if not template:
            return {}

        peers = [
            t for t in self._templates.values()
            if (t.prompt_type == template.prompt_type and
                t.id != template_id and
                t.usage_count > 0)
        ]

        if not peers:
            return {"message": "No peer templates for comparison"}

        avg_success_rate = sum(p.success_rate for p in peers) / len(peers)
        avg_response_time = sum(p.avg_response_time_ms for p in peers) / len(peers)

        return {
            "peer_count": len(peers),
            "avg_success_rate": avg_success_rate,
            "avg_response_time_ms": avg_response_time,
            "relative_performance": {
                "success_rate_diff": template.success_rate - avg_success_rate,
                "response_time_diff": template.avg_response_time_ms - avg_response_time
            }
        }

    async def _generate_template_recommendations(self, template_id: str) -> List[str]:
        """Generate optimization recommendations for a template."""
        template = self._templates.get(template_id)
        performance = self._performance_data.get(template_id)

        if not template or not performance:
            return ["Insufficient data for recommendations"]

        recommendations = []

        # Success rate recommendations
        if template.success_rate < 0.8:
            recommendations.append("Consider refining prompt structure to improve success rate")

        # Response time recommendations
        if template.avg_response_time_ms > 30000:  # 30 seconds
            recommendations.append("Prompt may be too complex, consider simplifying")

        # Usage recommendations
        if performance.usage_count < 10:
            recommendations.append("Template needs more usage data for reliable analysis")

        # Token efficiency recommendations
        if template.token_efficiency_score < 0.5:
            recommendations.append("Optimize template for better token efficiency")

        return recommendations

    async def _get_templates_by_type(self, prompt_type: PromptType) -> List[Dict[str, Any]]:
        """Get all templates of a specific type."""
        return [
            {
                "id": t.id,
                "name": t.name,
                "usage_count": t.usage_count,
                "success_rate": t.success_rate,
                "avg_response_time_ms": t.avg_response_time_ms,
                "status": t.status.value,
                "version": t.version
            }
            for t in self._templates.values()
            if t.prompt_type == prompt_type
        ]

    async def _get_performance_summary(self) -> Dict[str, Any]:
        """Get overall performance summary."""
        if not self._performance_data:
            return {}

        total_usage = sum(p.usage_count for p in self._performance_data.values())
        total_success = sum(p.success_count for p in self._performance_data.values())
        total_errors = sum(p.error_count for p in self._performance_data.values())

        return {
            "total_templates": len(self._templates),
            "active_experiments": len([e for e in self._active_experiments.values() if e.status == "active"]),
            "total_usage": total_usage,
            "overall_success_rate": total_success / max(1, total_usage),
            "total_errors": total_errors,
            "avg_response_time_ms": sum(
                p.total_response_time_ms / max(1, p.usage_count)
                for p in self._performance_data.values()
            ) / max(1, len(self._performance_data))
        }

    async def _identify_optimization_opportunities(self) -> List[Dict[str, Any]]:
        """Identify templates that need optimization."""
        opportunities = []

        for template in self._templates.values():
            if template.status != OptimizationStatus.ACTIVE:
                continue

            if template.success_rate < 0.7:
                opportunities.append({
                    "template_id": template.id,
                    "template_name": template.name,
                    "issue": "Low success rate",
                    "current_value": template.success_rate,
                    "recommended_action": "Create A/B test with improved prompt"
                })

            if template.avg_response_time_ms > 45000:  # 45 seconds
                opportunities.append({
                    "template_id": template.id,
                    "template_name": template.name,
                    "issue": "High response time",
                    "current_value": template.avg_response_time_ms,
                    "recommended_action": "Simplify prompt structure"
                })

        return opportunities

    async def _get_recent_improvements(self) -> List[Dict[str, Any]]:
        """Get recently improved templates."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)

        improvements = []
        for template in self._templates.values():
            if (template.created_at > cutoff and
                template.status == OptimizationStatus.ACTIVE and
                template.usage_count > 5):
                improvements.append({
                    "template_id": template.id,
                    "template_name": template.name,
                    "success_rate": template.success_rate,
                    "usage_count": template.usage_count,
                    "created_at": template.created_at.isoformat()
                })

        return sorted(improvements, key=lambda x: x["success_rate"], reverse=True)

    async def _performance_update_loop(self) -> None:
        """Background loop to update performance metrics."""
        while self._initialized:
            try:
                # Update token efficiency scores
                await self._update_token_efficiency_scores()

                # Check for experiment completion
                await self._check_experiment_completion()

                # Save data periodically
                await self._save_performance_data()

                await asyncio.sleep(self.performance_update_interval)

            except Exception as e:
                logger.error(f"Error in performance update loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error

    async def _cleanup_loop(self) -> None:
        """Background loop for cleanup tasks."""
        while self._initialized:
            try:
                # Cleanup old experiments
                await self._cleanup_old_experiments()

                # Archive unused templates
                await self._archive_unused_templates()

                await asyncio.sleep(86400)  # Run daily

            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(3600)  # Wait 1 hour on error

    async def _update_token_efficiency_scores(self) -> None:
        """Update token efficiency scores for all templates."""
        for template_id, performance in self._performance_data.items():
            if performance.usage_count == 0:
                continue

            template = self._templates.get(template_id)
            if not template:
                continue

            # Calculate tokens per successful response
            if performance.success_count > 0:
                tokens_per_success = performance.total_tokens_used / performance.success_count
                # Normalize to 0-1 score (lower is better)
                template.token_efficiency_score = max(0, 1 - tokens_per_success / 10000)

    async def _check_experiment_completion(self) -> None:
        """Check if any experiments have sufficient data for completion."""
        for experiment in list(self._active_experiments.values()):
            if experiment.status != "active":
                continue

            # Check sample size
            ready_for_analysis = True
            for template_id in [experiment.control_template_id] + experiment.variant_template_ids:
                perf = self._performance_data.get(template_id)
                if not perf or perf.usage_count < experiment.sample_size_per_variant:
                    ready_for_analysis = False
                    break

            if ready_for_analysis:
                await self._analyze_experiment_results(experiment.id)

    async def _analyze_experiment_results(self, experiment_id: str) -> None:
        """Analyze experiment results and determine winner."""
        experiment = self._active_experiments.get(experiment_id)
        if not experiment:
            return

        # Simple success rate comparison
        best_template_id = experiment.control_template_id
        best_success_rate = 0.0

        for template_id in [experiment.control_template_id] + experiment.variant_template_ids:
            perf = self._performance_data.get(template_id)
            if perf and perf.usage_count > 0:
                success_rate = perf.success_count / perf.usage_count
                if success_rate > best_success_rate:
                    best_success_rate = success_rate
                    best_template_id = template_id

        # Update experiment
        experiment.winning_template_id = best_template_id
        experiment.status = "completed"
        experiment.end_time = datetime.now(timezone.utc)

        # Promote winning template
        if best_template_id != experiment.control_template_id:
            winning_template = self._templates.get(best_template_id)
            if winning_template:
                winning_template.status = OptimizationStatus.ACTIVE

        # Save results
        await self._save_experiments()

        logger.info(f"Experiment {experiment_id} completed. Winner: {best_template_id}")

    async def _cleanup_old_experiments(self) -> None:
        """Clean up old completed experiments."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)

        experiments_to_remove = [
            exp_id for exp_id, exp in self._active_experiments.items()
            if (exp.status in ["completed", "failed"] and
                exp.end_time and exp.end_time < cutoff)
        ]

        for exp_id in experiments_to_remove:
            del self._active_experiments[exp_id]

        if experiments_to_remove:
            await self._save_experiments()
            logger.info(f"Cleaned up {len(experiments_to_remove)} old experiments")

    async def _archive_unused_templates(self) -> None:
        """Archive templates that haven't been used recently."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=90)

        for template in list(self._templates.values()):
            if (template.status == OptimizationStatus.ACTIVE and
                template.last_used < cutoff and
                template.usage_count < 5):
                template.status = OptimizationStatus.DEPRECATED

        await self._save_templates()

    async def _emit_template_created_event(self, template_id: str, prompt_type: PromptType) -> None:
        """Emit event when template is created."""
        if not self.event_bus:
            return

        event = Event(
            id=f"template_created_{datetime.now().timestamp()}",
            type=EventType.PROMPT_TEMPLATE_CREATED,
            source="enhanced_prompt_optimization_service",
            data={
                "template_id": template_id,
                "prompt_type": prompt_type.value,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        await self.event_bus.publish(event)

    async def _load_templates(self) -> None:
        """Load templates from file."""
        try:
            if self.templates_file.exists():
                async with aiofiles.open(self.templates_file, 'r') as f:
                    content = await f.read()
                    data = json.loads(content)

                    for template_data in data:
                        template = PromptTemplate(**template_data)
                        # Convert string timestamps back to datetime
                        template.created_at = datetime.fromisoformat(template.created_at)
                        template.last_used = datetime.fromisoformat(template.last_used)
                        template.status = OptimizationStatus(template.status)
                        template.prompt_type = PromptType(template.prompt_type)

                        self._templates[template.id] = template

        except Exception as e:
            logger.warning(f"Error loading templates: {e}")

    async def _save_templates(self) -> None:
        """Save templates to file."""
        try:
            data = []
            for template in self._templates.values():
                template_dict = asdict(template)
                # Convert datetime to string for JSON serialization
                template_dict["created_at"] = template.created_at.isoformat()
                template_dict["last_used"] = template.last_used.isoformat()
                template_dict["status"] = template.status.value
                template_dict["prompt_type"] = template.prompt_type.value
                data.append(template_dict)

            self.templates_file.parent.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(self.templates_file, 'w') as f:
                await f.write(json.dumps(data, indent=2))

        except Exception as e:
            logger.error(f"Error saving templates: {e}")

    async def _load_performance_data(self) -> None:
        """Load performance data from file."""
        try:
            if self.performance_file.exists():
                async with aiofiles.open(self.performance_file, 'r') as f:
                    content = await f.read()
                    data = json.loads(content)

                    for perf_data in data:
                        performance = PromptPerformance(**perf_data)
                        performance.last_updated = datetime.fromisoformat(performance.last_updated)

                        self._performance_data[performance.template_id] = performance

        except Exception as e:
            logger.warning(f"Error loading performance data: {e}")

    async def _save_performance_data(self) -> None:
        """Save performance data to file."""
        try:
            data = []
            for performance in self._performance_data.values():
                perf_dict = asdict(performance)
                perf_dict["last_updated"] = performance.last_updated.isoformat()
                data.append(perf_dict)

            self.performance_file.parent.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(self.performance_file, 'w') as f:
                await f.write(json.dumps(data, indent=2))

        except Exception as e:
            logger.error(f"Error saving performance data: {e}")

    async def _load_experiments(self) -> None:
        """Load experiments from file."""
        try:
            if self.experiments_file.exists():
                async with aiofiles.open(self.experiments_file, 'r') as f:
                    content = await f.read()
                    data = json.loads(content)

                    for exp_data in data:
                        experiment = OptimizationExperiment(**exp_data)
                        experiment.start_time = datetime.fromisoformat(experiment.start_time)
                        if experiment.end_time:
                            experiment.end_time = datetime.fromisoformat(experiment.end_time)

                        self._active_experiments[experiment.id] = experiment

        except Exception as e:
            logger.warning(f"Error loading experiments: {e}")

    async def _save_experiments(self) -> None:
        """Save experiments to file."""
        try:
            data = []
            for experiment in self._active_experiments.values():
                exp_dict = asdict(experiment)
                exp_dict["start_time"] = experiment.start_time.isoformat()
                if experiment.end_time:
                    exp_dict["end_time"] = experiment.end_time.isoformat()
                data.append(exp_dict)

            self.experiments_file.parent.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(self.experiments_file, 'w') as f:
                await f.write(json.dumps(data, indent=2))

        except Exception as e:
            logger.error(f"Error saving experiments: {e}")

    async def cleanup(self) -> None:
        """Cleanup service resources."""
        if not self._initialized:
            return

        try:
            # Cancel background tasks
            if self._performance_task:
                self._performance_task.cancel()
            if self._cleanup_task:
                self._cleanup_task.cancel()

            # Save final data
            await self._save_templates()
            await self._save_performance_data()
            await self._save_experiments()

            # Unsubscribe from events
            if self.event_bus:
                self.event_bus.unsubscribe(EventType.CLAUDE_REQUEST_COMPLETED, self)
                self.event_bus.unsubscribe(EventType.CLAUDE_REQUEST_FAILED, self)

            self._initialized = False
            logger.info("Enhanced Prompt Optimization Service cleaned up successfully")

        except Exception as e:
            logger.error(f"Error during enhanced prompt optimization cleanup: {e}")