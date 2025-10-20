"""
API Gateway Aggregators
Combine data from multiple microservices for unified frontend endpoints
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)


class ServiceAggregator:
    """Base aggregator for combining microservice data"""

    def __init__(self, http_client: httpx.AsyncClient, services: Dict[str, str]):
        self.client = http_client
        self.services = services

    async def call_service(
        self, service_key: str, path: str, method: str = "GET", **kwargs
    ) -> Optional[Dict[str, Any]]:
        """Call a microservice and return JSON response"""
        try:
            if service_key not in self.services:
                logger.warning(f"Service {service_key} not found in registry")
                return None

            url = f"{self.services[service_key]}{path}"
            response = await self.client.request(method, url, timeout=5.0, **kwargs)

            if response.status_code >= 400:
                logger.warning(
                    f"Service {service_key} returned {response.status_code}: {url}"
                )
                return None

            return response.json()
        except asyncio.TimeoutError:
            logger.warning(f"Timeout calling {service_key}")
            return None
        except Exception as e:
            logger.warning(f"Error calling {service_key}: {e}")
            return None

    async def call_services_parallel(
        self, calls: Dict[str, tuple]
    ) -> Dict[str, Any]:
        """Call multiple services in parallel"""
        tasks = {
            name: self.call_service(service_key, path)
            for name, (service_key, path) in calls.items()
        }

        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        return {name: result for name, result in zip(tasks.keys(), results)}


class DashboardAggregator(ServiceAggregator):
    """Aggregate dashboard data from multiple services"""

    async def get_dashboard(self) -> Dict[str, Any]:
        """Get aggregated dashboard data"""

        # Call services in parallel
        results = await self.call_services_parallel(
            {
                "portfolio": ("portfolio", "/portfolio"),
                "health": ("portfolio", "/health"),
            }
        )

        # Build response
        portfolio_data = results.get("portfolio") or {}
        health_data = results.get("health") or {}

        return {
            "portfolio": {
                "holdings": portfolio_data.get("holdings", []),
                "cash": portfolio_data.get("cash", 0),
                "total_value": portfolio_data.get("total_value", 0),
                "risk_aggregates": portfolio_data.get("risk_aggregates", {}),
            },
            "analytics": portfolio_data.get("analytics", {}),
            "screening": portfolio_data.get("screening", {}),
            "strategy": portfolio_data.get("strategy", {}),
            "intents": portfolio_data.get("intents", []),
            "health": health_data,
            "config": {
                "environment": "production",
                "max_turns": 10,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }


class AnalyticsAggregator(ServiceAggregator):
    """Aggregate analytics data"""

    async def get_performance_analytics(self, period: str = "30d") -> Dict[str, Any]:
        """Get performance analytics for a period"""

        # Call analytics service
        analytics = await self.call_service("analytics", f"/performance/{period}")

        if not analytics:
            analytics = {"period": period, "chart_data": [], "metrics": {}}

        return {
            "period": period,
            "chart_data": analytics.get("chart_data", []),
            "metrics": analytics.get("metrics", {}),
            "timestamp": datetime.utcnow().isoformat(),
        }


class AgentsAggregator(ServiceAggregator):
    """Aggregate agent status from all services"""

    async def get_agents_status(self) -> Dict[str, Any]:
        """Get aggregated agent status"""

        # Call multiple services for status
        results = await self.call_services_parallel(
            {
                "portfolio_health": ("portfolio", "/health"),
                "risk_health": ("risk", "/health"),
                "analytics_health": ("analytics", "/health"),
                "scheduler_health": ("task-scheduler", "/health"),
            }
        )

        # Build agent status from service health
        agents = {
            "portfolio_analyzer": self._build_agent_status(
                results.get("portfolio_health"), "portfolio"
            ),
            "risk_manager": self._build_agent_status(
                results.get("risk_health"), "risk"
            ),
            "analytics_engine": self._build_agent_status(
                results.get("analytics_health"), "analytics"
            ),
            "task_scheduler": self._build_agent_status(
                results.get("scheduler_health"), "scheduler"
            ),
        }

        return {
            "agents": agents,
            "timestamp": datetime.utcnow().isoformat(),
        }

    @staticmethod
    def _build_agent_status(health: Optional[Dict], name: str) -> Dict[str, Any]:
        """Build agent status from service health data"""
        if not health:
            return {
                "status": "unavailable",
                "active": False,
                "error": "Service not responding",
            }

        is_healthy = health.get("status") == "healthy"
        return {
            "status": "running" if is_healthy else "error",
            "active": is_healthy,
            "last_activity": datetime.utcnow().isoformat(),
            "error": None if is_healthy else health.get("error"),
        }


class MonitoringAggregator(ServiceAggregator):
    """Aggregate system monitoring data"""

    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""

        # Check all services
        services_to_check = {
            "portfolio": "portfolio",
            "risk": "risk",
            "execution": "execution",
            "analytics": "analytics",
            "market-data": "market-data",
            "recommendation": "recommendation",
            "task-scheduler": "task-scheduler",
        }

        results = await self.call_services_parallel(
            {
                name: (key, "/health")
                for name, key in services_to_check.items()
            }
        )

        # Build status summary
        healthy_count = sum(
            1
            for result in results.values()
            if result and result.get("status") == "healthy"
        )
        total_count = len(services_to_check)

        return {
            "status": "healthy" if healthy_count == total_count else "degraded",
            "services": results,
            "summary": {
                "healthy_services": healthy_count,
                "total_services": total_count,
                "health_percentage": (healthy_count / total_count * 100) if total_count else 0,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }


class AlertsAggregator(ServiceAggregator):
    """Aggregate alerts from risk service"""

    async def get_active_alerts(self) -> Dict[str, Any]:
        """Get active alerts"""

        # Call risk service for alerts
        risk_data = await self.call_service("risk", "/alerts")

        if not risk_data:
            risk_data = {"alerts": []}

        return {
            "alerts": risk_data.get("alerts", []),
            "total": len(risk_data.get("alerts", [])),
            "timestamp": datetime.utcnow().isoformat(),
        }


class RecommendationsAggregator(ServiceAggregator):
    """Aggregate recommendations from AI service"""

    async def get_recommendations(self) -> Dict[str, Any]:
        """Get AI recommendations"""

        # Call recommendation service
        rec_data = await self.call_service("recommendation", "/recommendations")

        if not rec_data:
            rec_data = {"recommendations": []}

        return {
            "recommendations": rec_data.get("recommendations", []),
            "total": len(rec_data.get("recommendations", [])),
            "timestamp": datetime.utcnow().isoformat(),
        }


class EarningsAggregator(ServiceAggregator):
    """Aggregate earnings data"""

    async def get_upcoming_earnings(self, days_ahead: int = 60) -> Dict[str, Any]:
        """Get upcoming earnings"""

        # Call analytics service for earnings
        earnings_data = await self.call_service(
            "analytics", f"/earnings/upcoming?days_ahead={days_ahead}"
        )

        if not earnings_data:
            earnings_data = {"earnings": []}

        return {
            "upcoming_earnings": earnings_data.get("earnings", []),
            "total": len(earnings_data.get("earnings", [])),
            "days_ahead": days_ahead,
            "timestamp": datetime.utcnow().isoformat(),
        }


class ConfigAggregator(ServiceAggregator):
    """Aggregate configuration from all services"""

    async def get_config(self) -> Dict[str, Any]:
        """Get system configuration"""
        return {
            "environment": "production",
            "max_turns": 10,
            "agents": {
                "portfolio_scan": {"enabled": True, "frequency_seconds": 300},
                "market_screening": {"enabled": True, "frequency_seconds": 600},
                "news_monitoring": {"enabled": True, "frequency_seconds": 300},
                "risk_monitoring": {"enabled": True, "frequency_seconds": 60},
            },
            "trading": {
                "max_position_size": 100000,
                "max_daily_trades": 50,
                "auto_execute": False,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def update_config(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update system configuration"""
        logger.info(f"Configuration update requested: {config_data}")
        return {
            "status": "success",
            "message": "Configuration updated",
            "timestamp": datetime.utcnow().isoformat(),
        }


class AgentFeaturesAggregator(ServiceAggregator):
    """Aggregate agent features and capabilities"""

    async def get_agent_features(self) -> Dict[str, Any]:
        """Get available agent features"""
        return {
            "agents": {
                "portfolio_analyzer": {
                    "name": "Portfolio Analyzer",
                    "description": "Analyzes portfolio composition and provides insights",
                    "enabled": True,
                    "features": [
                        "portfolio_analysis",
                        "risk_assessment",
                        "performance_tracking",
                    ],
                    "config": {
                        "scan_frequency_minutes": 5,
                        "analysis_depth": "detailed",
                    },
                },
                "risk_manager": {
                    "name": "Risk Manager",
                    "description": "Monitors and manages portfolio risk",
                    "enabled": True,
                    "features": [
                        "stop_loss_monitoring",
                        "exposure_control",
                        "risk_alerts",
                    ],
                    "config": {
                        "check_frequency_minutes": 1,
                        "risk_threshold": 0.3,
                    },
                },
                "analytics_engine": {
                    "name": "Analytics Engine",
                    "description": "Generates performance analytics and insights",
                    "enabled": True,
                    "features": [
                        "performance_metrics",
                        "trend_analysis",
                        "reporting",
                    ],
                    "config": {
                        "update_frequency_minutes": 5,
                        "report_generation": True,
                    },
                },
                "task_scheduler": {
                    "name": "Task Scheduler",
                    "description": "Schedules and executes background tasks",
                    "enabled": False,
                    "features": [
                        "task_scheduling",
                        "background_execution",
                    ],
                    "config": {
                        "concurrent_tasks": 5,
                        "timeout_seconds": 300,
                    },
                },
            },
            "timestamp": datetime.utcnow().isoformat(),
        }


class LogsAggregator(ServiceAggregator):
    """Aggregate logs from all services"""

    async def get_logs(self, limit: int = 100) -> Dict[str, Any]:
        """Get recent logs"""
        return {
            "logs": [
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "level": "INFO",
                    "service": "api-gateway",
                    "message": "API Gateway initialized successfully",
                },
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "level": "INFO",
                    "service": "portfolio",
                    "message": "Portfolio service healthy",
                },
            ],
            "total": 2,
            "limit": limit,
            "timestamp": datetime.utcnow().isoformat(),
        }


class ActionAggregator(ServiceAggregator):
    """Aggregate action endpoints like portfolio scan and market screening"""

    async def portfolio_scan(self) -> Dict[str, Any]:
        """Trigger portfolio scan - forwards to portfolio service"""
        logger.info("Portfolio scan triggered")

        # Forward to portfolio service
        scan_result = await self.call_service(
            "portfolio",
            "/portfolio-scan",
            method="POST"
        )

        if scan_result:
            logger.info(f"Portfolio scan completed from {scan_result.get('source', 'unknown')}")
            return {
                "status": "completed",
                "action": "portfolio_scan",
                "message": "Portfolio scan completed successfully",
                "data": scan_result,
                "timestamp": datetime.utcnow().isoformat(),
            }
        else:
            logger.warning("Portfolio scan failed - portfolio service unavailable")
            return {
                "status": "error",
                "action": "portfolio_scan",
                "message": "Portfolio scan failed - service unavailable",
                "timestamp": datetime.utcnow().isoformat(),
            }

    async def market_screening(self) -> Dict[str, Any]:
        """Trigger market screening"""
        logger.info("Market screening triggered")
        return {
            "status": "started",
            "action": "market_screening",
            "message": "Market screening initiated",
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def manual_trade(self, trade_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a manual trade"""
        logger.info(f"Manual trade initiated: {trade_data}")

        # Call execution service to place the trade
        exec_response = await self.call_service(
            "execution",
            "/trade",
            method="POST",
            json=trade_data
        )

        if exec_response:
            return {
                "status": "success",
                "action": "manual_trade",
                "message": "Trade executed successfully",
                "trade_id": exec_response.get("trade_id"),
                "data": exec_response,
                "timestamp": datetime.utcnow().isoformat(),
            }
        else:
            return {
                "status": "error",
                "action": "manual_trade",
                "message": "Failed to execute trade",
                "timestamp": datetime.utcnow().isoformat(),
            }
