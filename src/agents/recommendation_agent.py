"""
Recommendation Agent

Provides AI-powered investment recommendations through Claude Agent SDK tools.
Generates comprehensive BUY/SELL/HOLD recommendations with detailed analysis.
"""

import json
from typing import Dict, List, Any
from datetime import datetime, timezone

from claude_agent_sdk import tool
from loguru import logger

from src.config import Config
from ..core.database_state import DatabaseStateManager
from ..services.recommendation_service import RecommendationEngine
from ..services.fundamental_service import FundamentalService
from ..services.risk_service import RiskService


def create_recommendation_tools(
    config: Config,
    state_manager: DatabaseStateManager,
    fundamental_service: FundamentalService,
    risk_service: RiskService
) -> List:
    """Create recommendation tools with dependencies via closure."""

    # Initialize recommendation engine
    reco_engine = RecommendationEngine(
        config=config,
        state_manager=state_manager,
        fundamental_service=fundamental_service,
        risk_service=risk_service
    )

    @tool("generate_recommendation", "Generate AI-powered investment recommendation for a stock symbol", {
        "symbol": str,
        "force_refresh": bool
    })
    async def generate_recommendation_tool(args: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive investment recommendation for a stock."""
        try:
            symbol = args["symbol"].upper()
            force_refresh = args.get("force_refresh", False)

            logger.info(f"Generating recommendation for {symbol}")

            # Generate recommendation
            result = await reco_engine.generate_recommendation(symbol, force_refresh)

            if not result:
                return {
                    "content": [{"type": "text", "text": f"Unable to generate recommendation for {symbol} - insufficient data"}],
                    "is_error": True
                }

            # Store recommendation
            recommendation_id = await reco_engine.store_recommendation(result)

            # Format response
            response_data = {
                "symbol": result.symbol,
                "recommendation": result.recommendation_type,
                "confidence": result.confidence_level,
                "overall_score": result.overall_score,
                "target_price": result.target_price,
                "stop_loss": result.stop_loss,
                "time_horizon": result.time_horizon,
                "risk_level": result.risk_level,
                "reasoning": result.reasoning,
                "factors": result.factors.to_dict(),
                "recommendation_id": recommendation_id,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }

            return {
                "content": [
                    {"type": "text", "text": f"Generated {result.recommendation_type} recommendation for {symbol}"},
                    {"type": "text", "text": json.dumps(response_data, indent=2)}
                ]
            }

        except Exception as e:
            logger.error(f"Recommendation generation failed for {args.get('symbol', 'unknown')}: {e}")
            return {
                "content": [{"type": "text", "text": f"Error generating recommendation: {str(e)}"}],
                "is_error": True
            }

    @tool("generate_bulk_recommendations", "Generate recommendations for multiple stock symbols", {
        "symbols": List[str],
        "force_refresh": bool
    })
    async def generate_bulk_recommendations_tool(args: Dict[str, Any]) -> Dict[str, Any]:
        """Generate recommendations for multiple symbols."""
        try:
            symbols = [s.upper() for s in args["symbols"]]
            force_refresh = args.get("force_refresh", False)

            logger.info(f"Generating bulk recommendations for {len(symbols)} symbols")

            # Generate bulk recommendations
            recommendations = await reco_engine.generate_bulk_recommendations(symbols, force_refresh)

            # Store recommendations and collect results
            results = []
            stored_count = 0

            for symbol, result in recommendations.items():
                try:
                    # Store recommendation
                    recommendation_id = await reco_engine.store_recommendation(result)
                    if recommendation_id:
                        stored_count += 1

                    results.append({
                        "symbol": result.symbol,
                        "recommendation": result.recommendation_type,
                        "confidence": result.confidence_level,
                        "score": result.overall_score,
                        "target_price": result.target_price,
                        "stop_loss": result.stop_loss,
                        "recommendation_id": recommendation_id
                    })

                except Exception as e:
                    logger.error(f"Error storing recommendation for {symbol}: {e}")
                    results.append({
                        "symbol": symbol,
                        "error": str(e)
                    })

            summary = {
                "total_symbols": len(symbols),
                "successful_recommendations": len(results),
                "stored_recommendations": stored_count,
                "recommendations": results
            }

            return {
                "content": [
                    {"type": "text", "text": f"Generated recommendations for {len(results)}/{len(symbols)} symbols"},
                    {"type": "text", "text": json.dumps(summary, indent=2)}
                ]
            }

        except Exception as e:
            logger.error(f"Bulk recommendation generation failed: {e}")
            return {
                "content": [{"type": "text", "text": f"Error generating bulk recommendations: {str(e)}"}],
                "is_error": True
            }

    @tool("get_recommendation_history", "Get historical recommendations for a stock symbol", {
        "symbol": str,
        "limit": int
    })
    async def get_recommendation_history_tool(args: Dict[str, Any]) -> Dict[str, Any]:
        """Get recommendation history for a symbol."""
        try:
            symbol = args["symbol"].upper()
            limit = args.get("limit", 10)

            logger.info(f"Getting recommendation history for {symbol} (limit: {limit})")

            # Get recommendation history
            recommendations = await reco_engine.get_recommendation_history(symbol, limit)

            # Format recommendations
            history = []
            for rec in recommendations:
                history.append({
                    "recommendation_id": rec.recommendation_id,
                    "symbol": rec.symbol,
                    "recommendation_type": rec.recommendation_type,
                    "confidence_score": rec.confidence_score,
                    "target_price": rec.target_price,
                    "stop_loss": rec.stop_loss,
                    "reasoning": rec.reasoning,
                    "analysis_type": rec.analysis_type,
                    "time_horizon": rec.time_horizon,
                    "risk_level": rec.risk_level,
                    "executed_at": rec.executed_at,
                    "outcome": rec.outcome,
                    "actual_return": rec.actual_return
                })

            return {
                "content": [
                    {"type": "text", "text": f"Found {len(history)} historical recommendations for {symbol}"},
                    {"type": "text", "text": json.dumps(history, indent=2)}
                ]
            }

        except Exception as e:
            logger.error(f"Failed to get recommendation history for {args.get('symbol', 'unknown')}: {e}")
            return {
                "content": [{"type": "text", "text": f"Error getting recommendation history: {str(e)}"}],
                "is_error": True
            }

    @tool("analyze_portfolio_recommendations", "Analyze current portfolio and generate recommendations", {})
    async def analyze_portfolio_recommendations_tool(args: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze current portfolio holdings and generate recommendations."""
        try:
            logger.info("Analyzing portfolio recommendations")

            # Get current portfolio
            portfolio = await state_manager.get_portfolio()
            if not portfolio or not portfolio.holdings:
                return {
                    "content": [{"type": "text", "text": "No portfolio holdings found to analyze"}],
                    "is_error": True
                }

            # Extract symbols from portfolio
            symbols = [holding.get('tradingsymbol', '') for holding in portfolio.holdings if holding.get('tradingsymbol')]
            if not symbols:
                return {
                    "content": [{"type": "text", "text": "No valid symbols found in portfolio"}],
                    "is_error": True
                }

            # Generate recommendations for portfolio symbols
            recommendations = await reco_engine.generate_bulk_recommendations(symbols)

            # Analyze portfolio composition and recommendations
            analysis = {
                "portfolio_summary": {
                    "total_holdings": len(portfolio.holdings),
                    "symbols_analyzed": len(symbols),
                    "recommendations_generated": len(recommendations)
                },
                "recommendation_breakdown": {},
                "high_confidence_opportunities": [],
                "risk_concerns": []
            }

            # Count recommendation types
            reco_counts = {}
            for symbol, result in recommendations.items():
                reco_type = result.recommendation_type
                reco_counts[reco_type] = reco_counts.get(reco_type, 0) + 1

                # Track high confidence opportunities
                if result.confidence_level == "HIGH":
                    if result.recommendation_type == "BUY":
                        analysis["high_confidence_opportunities"].append({
                            "symbol": symbol,
                            "recommendation": result.recommendation_type,
                            "confidence": result.confidence_level,
                            "target_price": result.target_price,
                            "potential_upsite": f"{((result.target_price - await reco_engine._get_current_price(symbol)) / await reco_engine._get_current_price(symbol) * 100):.1f}%" if result.target_price else None
                        })
                    elif result.recommendation_type == "SELL":
                        analysis["risk_concerns"].append({
                            "symbol": symbol,
                            "recommendation": result.recommendation_type,
                            "confidence": result.confidence_level,
                            "stop_loss": result.stop_loss
                        })

            analysis["recommendation_breakdown"] = reco_counts

            # Store recommendations
            stored_count = 0
            for result in recommendations.values():
                try:
                    recommendation_id = await reco_engine.store_recommendation(result)
                    if recommendation_id:
                        stored_count += 1
                except Exception as e:
                    logger.error(f"Error storing recommendation for {result.symbol}: {e}")

            analysis["stored_recommendations"] = stored_count

            return {
                "content": [
                    {"type": "text", "text": f"Portfolio analysis complete: {len(recommendations)} recommendations generated"},
                    {"type": "text", "text": json.dumps(analysis, indent=2)}
                ]
            }

        except Exception as e:
            logger.error(f"Portfolio recommendation analysis failed: {e}")
            return {
                "content": [{"type": "text", "text": f"Error analyzing portfolio recommendations: {str(e)}"}],
                "is_error": True
            }

    @tool("get_recommendation_stats", "Get recommendation engine statistics and performance", {})
    async def get_recommendation_stats_tool(args: Dict[str, Any]) -> Dict[str, Any]:
        """Get recommendation engine statistics."""
        try:
            logger.info("Getting recommendation statistics")

            # Get stats from recommendation engine
            stats = await reco_engine.get_recommendation_stats()

            # Add additional computed stats
            try:
                # Get recent recommendations for analysis
                all_recommendations = await state_manager.get_all_recommendations(limit=1000)

                if all_recommendations:
                    # Calculate success rates, average returns, etc.
                    completed_recommendations = [r for r in all_recommendations if r.outcome]

                    if completed_recommendations:
                        successful_trades = sum(1 for r in completed_recommendations if r.actual_return and r.actual_return > 0)
                        success_rate = successful_trades / len(completed_recommendations) * 100

                        avg_return = sum(r.actual_return for r in completed_recommendations if r.actual_return) / len([r for r in completed_recommendations if r.actual_return])

                        stats.update({
                            "total_completed_recommendations": len(completed_recommendations),
                            "success_rate_percent": round(success_rate, 2),
                            "average_return_percent": round(avg_return, 2),
                            "total_tracked_recommendations": len(all_recommendations)
                        })
                    else:
                        stats["total_tracked_recommendations"] = len(all_recommendations)
                        stats["note"] = "No completed recommendations with outcome data yet"

            except Exception as e:
                logger.warning(f"Could not compute additional stats: {e}")

            return {
                "content": [
                    {"type": "text", "text": "Recommendation Engine Statistics"},
                    {"type": "text", "text": json.dumps(stats, indent=2)}
                ]
            }

        except Exception as e:
            logger.error(f"Failed to get recommendation stats: {e}")
            return {
                "content": [{"type": "text", "text": f"Error getting recommendation statistics: {str(e)}"}],
                "is_error": True
            }

    return [
        generate_recommendation_tool,
        generate_bulk_recommendations_tool,
        get_recommendation_history_tool,
        analyze_portfolio_recommendations_tool,
        get_recommendation_stats_tool
    ]