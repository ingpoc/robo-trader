"""
MCP Tools for Claude's Real-Time Prompt Optimization

These tools allow Claude to:
1. Analyze data quality from Perplexity responses
2. Improve prompts based on quality analysis
3. Save optimized prompts for future use
4. Track prompt performance over time
"""

from typing import Any, Dict, List

from loguru import logger


class PromptOptimizationTools:
    """MCP tools for Claude to optimize prompts in real-time."""

    def __init__(self, prompt_service):
        self.prompt_service = prompt_service

    def get_tools(self) -> List[Dict[str, Any]]:
        """Return list of available prompt optimization tools."""
        return [
            {
                "name": "analyze_data_quality",
                "description": "Analyze the quality of data received from Perplexity for trading decisions",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "data_type": {
                            "type": "string",
                            "enum": ["earnings", "news", "fundamentals", "metrics"],
                            "description": "Type of data received",
                        },
                        "data": {
                            "type": "string",
                            "description": "The actual data received from Perplexity",
                        },
                        "prompt_used": {
                            "type": "string",
                            "description": "The prompt that was used to get this data",
                        },
                    },
                    "required": ["data_type", "data", "prompt_used"],
                },
            },
            {
                "name": "improve_prompt",
                "description": "Improve a Perplexity prompt based on data quality analysis",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "data_type": {
                            "type": "string",
                            "enum": ["earnings", "news", "fundamentals", "metrics"],
                            "description": "Type of data being fetched",
                        },
                        "current_prompt": {
                            "type": "string",
                            "description": "Current prompt that needs improvement",
                        },
                        "missing_elements": {
                            "type": "array",
                            "items": {"type": "object"},
                            "description": "Elements that are missing from the data",
                        },
                        "redundant_elements": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Elements that are redundant or unnecessary",
                        },
                        "quality_feedback": {
                            "type": "string",
                            "description": "Claude's feedback on current data quality",
                        },
                    },
                    "required": [
                        "data_type",
                        "current_prompt",
                        "missing_elements",
                        "redundant_elements",
                        "quality_feedback",
                    ],
                },
            },
            {
                "name": "save_optimized_prompt",
                "description": "Save an optimized prompt for future use",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "data_type": {
                            "type": "string",
                            "enum": ["earnings", "news", "fundamentals", "metrics"],
                            "description": "Type of data this prompt fetches",
                        },
                        "original_prompt": {
                            "type": "string",
                            "description": "Original prompt before optimization",
                        },
                        "optimized_prompt": {
                            "type": "string",
                            "description": "Claude's optimized version of the prompt",
                        },
                        "quality_score": {
                            "type": "number",
                            "minimum": 1,
                            "maximum": 10,
                            "description": "Claude's satisfaction with data quality (1-10)",
                        },
                        "optimization_notes": {
                            "type": "string",
                            "description": "Claude's notes on why this version is better",
                        },
                    },
                    "required": [
                        "data_type",
                        "original_prompt",
                        "optimized_prompt",
                        "quality_score",
                    ],
                },
            },
            {
                "name": "get_prompt_suggestions",
                "description": "Get suggestions for improving prompt based on historical performance",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "data_type": {
                            "type": "string",
                            "enum": ["earnings", "news", "fundamentals", "metrics"],
                            "description": "Type of data to fetch",
                        },
                        "current_issues": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Current issues with data quality",
                        },
                    },
                    "required": ["data_type"],
                },
            },
        ]

    async def analyze_data_quality(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Tool for Claude to analyze data quality."""

        data_type = args["data_type"]
        data = args["data"]
        prompt_used = args["prompt_used"]

        # Domain-specific quality criteria
        quality_criteria = self._get_quality_criteria(data_type)

        # Claude analyzes the data
        quality_score = 0.0
        missing_elements = []
        redundant_elements = []
        strengths = []

        # Check each quality criterion
        for criterion, description in quality_criteria.items():
            has_quality = self._check_data_quality(data, criterion, data_type)
            if has_quality:
                quality_score += 2.0  # Each criterion worth 2 points (max 10)
                strengths.append(description)
            else:
                missing_elements.append(
                    {
                        "criterion": criterion,
                        "description": description,
                        "why_important": self._explain_importance(criterion, data_type),
                    }
                )

        # Check for redundant content
        redundant_elements = self._find_redundant_content(data, data_type)

        # Generate feedback
        feedback = f"Data quality {quality_score}/10 for {data_type}. "
        if missing_elements:
            feedback += (
                f"Missing: {', '.join([m['criterion'] for m in missing_elements])}. "
            )
        if redundant_elements:
            feedback += f"Redundant: {', '.join(redundant_elements)}."
        if strengths:
            feedback += f" Strengths: {', '.join(strengths)}."

        return {
            "quality_score": quality_score,
            "missing_elements": missing_elements,
            "redundant_elements": redundant_elements,
            "feedback": feedback,
            "strengths": strengths,
            "data_type": data_type,
            "analysis_complete": True,
            "recommendations": self._generate_recommendations(
                data_type, missing_elements, redundant_elements
            ),
        }

    async def improve_prompt(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Tool for Claude to improve prompts."""

        data_type = args["data_type"]
        current_prompt = args["current_prompt"]
        missing_elements = args["missing_elements"]
        redundant_elements = args["redundant_elements"]
        quality_feedback = args["quality_feedback"]

        # Data-type-specific improvement templates
        improvement_template = self._get_improvement_template(data_type)

        # Claude constructs improved prompt
        improvements_needed = [elem["criterion"] for elem in missing_elements]

        improved_prompt = f"""
{current_prompt}

ENHANCEMENTS FOR BETTER TRADING ANALYSIS:
{improvement_template}

SPECIFIC FOCUS AREAS (based on current data quality):
{chr(10).join([f"- Add {elem['criterion']}: {elem['description']}" for elem in missing_elements])}

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
            "focus_areas": self._get_focus_areas(data_type, missing_elements),
            "expected_improvement": f"Should improve {data_type} data quality from current feedback",
            "quality_enhancements": self._get_quality_enhancements(
                data_type, missing_elements
            ),
        }

    async def save_optimized_prompt(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Tool for Claude to save optimized prompts."""

        try:
            # This would trigger the service to save the prompt
            prompt_id = await self.prompt_service._save_optimized_prompt(
                data_type=args["data_type"],
                original_prompt=args["original_prompt"],
                optimized_prompt=args["optimized_prompt"],
                quality_score=args["quality_score"],
                session_id="current_session",  # Would get from context
                optimization_attempts=[],  # Would be populated from context
            )

            return {
                "status": "saved",
                "prompt_id": prompt_id,
                "data_type": args["data_type"],
                "quality_score": args["quality_score"],
                "message": f"Optimized {args['data_type']} prompt saved successfully",
                "optimization_notes": args.get("optimization_notes", ""),
            }

        except Exception as e:
            logger.error(f"Failed to save optimized prompt: {e}")
            return {
                "status": "error",
                "error": str(e),
                "message": "Failed to save optimized prompt",
            }

    async def get_prompt_suggestions(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get suggestions for improving prompts based on historical performance."""

        data_type = args["data_type"]
        current_issues = args.get("current_issues", [])

        # Get historical performance data
        history = await self.prompt_service.get_prompt_history(data_type, days=30)
        trends = await self.prompt_service.get_quality_trends(days=30)

        # Analyze what worked well in the past
        successful_patterns = self._analyze_successful_patterns(history)
        common_issues = self._identify_common_issues(history, current_issues)

        # Generate specific suggestions
        suggestions = self._generate_data_type_suggestions(
            data_type, successful_patterns, common_issues
        )

        return {
            "data_type": data_type,
            "suggestions": suggestions,
            "successful_patterns": successful_patterns,
            "common_issues": common_issues,
            "historical_performance": {
                "avg_quality": (
                    sum(h["quality_score"] for h in history) / len(history)
                    if history
                    else 0
                ),
                "total_optimizations": len(history),
                "recent_trend": self._calculate_recent_trend(trends.get(data_type, [])),
            },
            "recommended_focus": self._get_recommended_focus(data_type, current_issues),
        }

    def _get_quality_criteria(self, data_type: str) -> Dict[str, str]:
        """Get quality criteria for different data types."""

        criteria = {
            "earnings": {
                "eps_vs_estimated": "Actual EPS vs Estimated with exact numbers and surprise percentage",
                "revenue_growth": "Revenue growth rates (YoY and QoQ) with specific percentages",
                "management_guidance": "Management guidance with specific forward-looking statements",
                "profit_margins": "Gross, operating, and net profit margins with trend analysis",
                "earnings_surprise": "Detailed earnings surprise analysis and market reaction",
            },
            "news": {
                "sentiment_analysis": "Clear sentiment classification (positive/negative/neutral) with impact levels",
                "news_categorization": "News categorized by type (earnings, M&A, product, regulatory, etc.)",
                "market_relevance": "Assessment of direct/indirect impact on stock price",
                "source_quality": "Reliable sources with publication timestamps",
                "trading_signals": "Clear indicators of how this news affects trading decisions",
            },
            "fundamentals": {
                "valuation_metrics": "P/E, P/S, P/B ratios with industry comparisons",
                "profitability_analysis": "ROE, ROA, margins with trend analysis",
                "financial_health": "Debt ratios, liquidity metrics, cash flow analysis",
                "growth_sustainability": "Assessment of whether current growth is sustainable",
                "competitive_advantage": "Company's competitive position and market share",
            },
            "metrics": {
                "technical_signals": "Specific technical indicators with clear buy/sell signals",
                "volume_analysis": "Volume patterns confirming price movements",
                "price_levels": "Key support/resistance levels and breakout points",
                "momentum_indicators": "Momentum strength and trend analysis",
                "risk_metrics": "Volatility measures and risk assessment",
            },
        }

        return criteria.get(data_type, {})

    def _check_data_quality(self, data: str, criterion: str, data_type: str) -> bool:
        """Check if data meets quality criterion."""

        # Use NLP/keyword matching to check for specific content
        keywords = {
            "eps_vs_estimated": [
                "eps",
                "estimated",
                "actual",
                "surprise",
                "beat",
                "miss",
            ],
            "revenue_growth": [
                "revenue",
                "growth",
                "%",
                "yoy",
                "qoq",
                "year-over-year",
            ],
            "sentiment_analysis": [
                "sentiment",
                "positive",
                "negative",
                "neutral",
                "impact",
                "bullish",
                "bearish",
            ],
            "valuation_metrics": ["p/e", "p/s", "p/b", "ratio", "industry", "multiple"],
            "technical_signals": [
                "rsi",
                "macd",
                "signal",
                "oversold",
                "overbought",
                "crossover",
                "divergence",
            ],
        }

        criterion_keywords = keywords.get(criterion, [criterion])
        data_lower = data.lower()

        # Check if enough keywords are present
        matches = sum(1 for keyword in criterion_keywords if keyword in data_lower)
        return matches >= max(
            1, len(criterion_keywords) * 0.3
        )  # At least 30% of keywords present

    def _explain_importance(self, criterion: str, data_type: str) -> str:
        """Explain why a quality criterion is important for trading."""

        importance_map = {
            "eps_vs_estimated": "Earnings surprises often cause immediate price movements and gap-ups/downs",
            "revenue_growth": "Revenue growth indicates business expansion and future profitability potential",
            "sentiment_analysis": "News sentiment drives short-term price action and trading volume",
            "valuation_metrics": "Valuation determines if stock is over/undervalued relative to peers and market",
            "technical_signals": "Technical indicators provide entry/exit timing signals and trend confirmation",
        }

        return importance_map.get(
            criterion, f"Important for {data_type} analysis and trading decisions"
        )

    def _find_redundant_content(self, data: str, data_type: str) -> List[str]:
        """Find redundant or unnecessary content in data."""

        redundant_patterns = {
            "earnings": [
                "company overview",
                "business description",
                "general information",
                "about the company",
            ],
            "news": [
                "background information",
                "company history",
                "general market overview",
                "disclaimer",
            ],
            "fundamentals": [
                "basic company information",
                "general industry overview",
                "company profile",
            ],
            "metrics": [
                "general market conditions",
                "basic stock information",
                "trading disclaimer",
            ],
        }

        redundant = []
        for pattern in redundant_patterns.get(data_type, []):
            if pattern in data.lower():
                redundant.append(pattern)

        return redundant

    def _generate_recommendations(
        self,
        data_type: str,
        missing_elements: List[Dict],
        redundant_elements: List[str],
    ) -> List[str]:
        """Generate specific recommendations for improvement."""

        recommendations = []

        for element in missing_elements:
            recommendations.append(
                f"Add {element['description']} - {element['why_important']}"
            )

        if redundant_elements:
            recommendations.append(
                f"Remove redundant content: {', '.join(redundant_elements[:3])}"
            )

        # Add data-type specific recommendations
        if data_type == "earnings":
            recommendations.append(
                "Ensure all financial data includes exact numbers and percentages"
            )
        elif data_type == "news":
            recommendations.append(
                "Categorize news by trading relevance and impact level"
            )
        elif data_type == "fundamentals":
            recommendations.append("Include industry benchmarks for comparison")
        elif data_type == "metrics":
            recommendations.append(
                "Provide clear technical signals with specific trigger levels"
            )

        return recommendations

    def _get_improvement_template(self, data_type: str) -> str:
        """Get improvement template for data type."""

        templates = {
            "earnings": """
FOCUS ON TRADING-RELEVANT EARNINGS DATA:
- Exact EPS numbers vs estimates with surprise percentages
- Revenue growth rates with specific YoY and QoQ figures
- Management guidance with specific numbers and timelines
- Profit margin trends with exact percentage changes
- Any forward-looking statements that could impact stock price
            """,
            "news": """
FOCUS ON TRADING-Impactful NEWS:
- Clear sentiment classification with HIGH/MEDIUM/LOW impact levels
- News categorized by trading relevance (earnings, M&A, product, regulatory)
- Specific assessment of how this news affects stock price
- Reliable sources with exact publication times
- Any insider activity or institutional trading related to news
            """,
            "fundamentals": """
FOCUS ON INVESTMENT DECISION FUNDAMENTALS:
- Exact valuation metrics with industry average comparisons
- Profitability trends with specific percentage changes
- Financial health metrics with debt/equity ratios and liquidity
- Growth sustainability analysis with supporting evidence
- Competitive position with market share and advantages
            """,
            "metrics": """
FOCUS ON TRADING SIGNALS AND TIMING:
- Specific technical indicator levels with clear signals
- Volume analysis confirming price movements
- Key support/resistance levels with breakout potential
- Momentum strength with trend continuation probability
- Risk metrics with volatility assessments and stop-loss levels
            """,
        }

        return templates.get(data_type, "")

    def _get_focus_areas(
        self, data_type: str, missing_elements: List[Dict]
    ) -> List[str]:
        """Get focus areas for improvement based on missing elements."""

        focus_map = {
            "eps_vs_estimated": "Enhance earnings surprise analysis with exact numbers",
            "sentiment_analysis": "Add sentiment impact assessment for trading",
            "valuation_metrics": "Include industry comparison for context",
            "technical_signals": "Add specific entry/exit signal levels",
        }

        focus_areas = []
        for element in missing_elements:
            criterion = element.get("criterion", "")
            if criterion in focus_map:
                focus_areas.append(focus_map[criterion])

        return focus_areas

    def _get_quality_enhancements(
        self, data_type: str, missing_elements: List[Dict]
    ) -> List[str]:
        """Get specific quality enhancements for data type."""

        enhancements = {
            "earnings": [
                "Request exact EPS figures with decimal precision",
                "Ask for revenue growth rates with specific percentages",
                "Include management confidence levels in guidance",
                "Request earnings calendar and next reporting date",
            ],
            "news": [
                "Categorize news by market impact level",
                "Request source credibility scores",
                "Ask for historical price reaction patterns",
                "Include insider trading activity related to news",
            ],
            "fundamentals": [
                "Request industry P/E averages for comparison",
                "Ask for competitive positioning metrics",
                "Include sustainability analysis of growth rates",
                "Request management quality assessment",
            ],
            "metrics": [
                "Specify exact technical indicator levels",
                "Request volume confirmation patterns",
                "Ask for volatility measurements and ranges",
                "Include correlation with broader market indices",
            ],
        }

        return enhancements.get(data_type, [])

    def _analyze_successful_patterns(self, history: List[Dict]) -> List[str]:
        """Analyze successful patterns from historical data."""

        if not history:
            return []

        # Find highest quality prompts
        high_quality_prompts = [p for p in history if p["quality_score"] >= 8.0]

        if not high_quality_prompts:
            return []

        # Extract common patterns from successful prompts
        patterns = []

        # Look for common feedback themes
        feedback_themes = []
        for prompt in high_quality_prompts:
            if prompt.get("claude_feedback"):
                feedback_themes.append(prompt["claude_feedback"])

        # Analyze feedback for common themes
        if feedback_themes:
            patterns.append("High-quality prompts focus on specific, actionable data")
            patterns.append("Successful prompts avoid redundant general information")
            patterns.append("Clear structure and JSON formatting improves quality")

        return patterns

    def _identify_common_issues(
        self, history: List[Dict], current_issues: List[str]
    ) -> List[str]:
        """Identify common issues from historical performance."""

        if not history:
            return current_issues

        # Find low quality prompts and their issues
        low_quality_prompts = [p for p in history if p["quality_score"] < 6.0]

        common_issues = set(current_issues)

        for prompt in low_quality_prompts:
            feedback = prompt.get("claude_feedback", "")
            if "missing" in feedback.lower():
                common_issues.add("Missing critical data elements")
            if "redundant" in feedback.lower():
                common_issues.add("Too much redundant information")
            if "general" in feedback.lower():
                common_issues.add("Lacks specific trading-relevant details")

        return list(common_issues)

    def _generate_data_type_suggestions(
        self, data_type: str, successful_patterns: List[str], common_issues: List[str]
    ) -> List[str]:
        """Generate specific suggestions for data type."""

        suggestions = []

        # Base suggestions on successful patterns
        for pattern in successful_patterns:
            suggestions.append(f"Leverage pattern: {pattern}")

        # Address common issues
        for issue in common_issues:
            suggestions.append(f"Address issue: {issue}")

        # Add data-type specific suggestions
        if data_type == "earnings":
            suggestions.extend(
                [
                    "Focus on surprise percentages and market reaction",
                    "Include guidance confidence levels",
                    "Add competitive earnings comparison",
                ]
            )
        elif data_type == "news":
            suggestions.extend(
                [
                    "Prioritize news by trading impact",
                    "Include sentiment analysis with confidence",
                    "Add historical price reaction patterns",
                ]
            )
        elif data_type == "fundamentals":
            suggestions.extend(
                [
                    "Include industry benchmark comparisons",
                    "Focus on sustainable competitive advantages",
                    "Add financial strength metrics",
                ]
            )
        elif data_type == "metrics":
            suggestions.extend(
                [
                    "Provide clear technical signal levels",
                    "Include volume confirmation analysis",
                    "Add volatility and risk assessments",
                ]
            )

        return suggestions[:8]  # Limit to top 8 suggestions

    def _calculate_recent_trend(self, trend_data: List[Dict]) -> str:
        """Calculate recent trend from data."""

        if len(trend_data) < 2:
            return "insufficient_data"

        recent = trend_data[0]["avg_quality"]
        previous = trend_data[1]["avg_quality"]

        if recent > previous + 0.5:
            return "improving"
        elif recent < previous - 0.5:
            return "declining"
        else:
            return "stable"

    def _get_recommended_focus(
        self, data_type: str, current_issues: List[str]
    ) -> List[str]:
        """Get recommended focus areas for improvement."""

        focus_areas = {
            "earnings": [
                "Enhance earnings surprise analysis",
                "Improve revenue growth detail",
                "Add management guidance quality assessment",
            ],
            "news": [
                "Improve sentiment classification accuracy",
                "Enhance news impact assessment",
                "Add source credibility evaluation",
            ],
            "fundamentals": [
                "Improve industry comparison metrics",
                "Enhance competitive positioning analysis",
                "Add financial strength assessment",
            ],
            "metrics": [
                "Improve technical signal clarity",
                "Enhance volume analysis integration",
                "Add risk metric completeness",
            ],
        }

        return focus_areas.get(data_type, ["General quality improvement"])
