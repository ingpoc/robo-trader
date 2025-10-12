"""
Accuracy Validation Framework for Robo Trader
Implements backtesting capabilities and accuracy measurement tools.
"""

import asyncio
import json
import statistics
from datetime import datetime, timedelta, date
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

from src.config import Config
from src.core.di import DependencyContainer
from src.services.recommendation_service import RecommendationService
from src.agents.recommendation_agent import RecommendationAgent


@dataclass
class BacktestResult:
    """Backtest result data structure."""
    symbol: str
    recommendation_date: date
    recommendation: str  # BUY, HOLD, SELL
    confidence: float
    actual_performance_1d: Optional[float] = None
    actual_performance_7d: Optional[float] = None
    actual_performance_30d: Optional[float] = None
    market_performance_1d: Optional[float] = None
    market_performance_7d: Optional[float] = None
    market_performance_30d: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AccuracyMetrics:
    """Accuracy metrics for recommendations."""
    total_recommendations: int
    buy_recommendations: int
    hold_recommendations: int
    sell_recommendations: int

    # Directional accuracy (did price move in predicted direction)
    directional_accuracy_1d: float
    directional_accuracy_7d: float
    directional_accuracy_30d: float

    # Performance vs market
    avg_outperformance_1d: float
    avg_outperformance_7d: float
    avg_outperformance_30d: float

    # Risk-adjusted metrics
    sharpe_ratio_1d: float
    sharpe_ratio_7d: float
    sharpe_ratio_30d: float

    # Confidence analysis
    high_confidence_accuracy: float
    medium_confidence_accuracy: float
    low_confidence_accuracy: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BacktestingEngine:
    """Engine for backtesting recommendation accuracy."""

    def __init__(self, config: Config, state_manager):
        self.config = config
        self.state_manager = state_manager
        self.historical_data = {}  # Cache for historical price data

    async def load_historical_data(self, symbol: str, start_date: date, end_date: date) -> pd.DataFrame:
        """Load historical price data for backtesting."""
        # In a real implementation, this would fetch from a data provider
        # For now, we'll simulate historical data

        if symbol in self.historical_data:
            return self.historical_data[symbol]

        # Generate synthetic historical data for testing
        date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        np.random.seed(hash(symbol) % 2**32)  # Deterministic seed per symbol

        # Simulate price movements with some volatility
        base_price = 1000 + hash(symbol) % 9000  # Base price between 1000-10000
        prices = [base_price]
        returns = np.random.normal(0.0005, 0.02, len(date_range) - 1)  # Mean return 0.05%, vol 2%

        for ret in returns:
            new_price = prices[-1] * (1 + ret)
            prices.append(new_price)

        df = pd.DataFrame({
            'date': date_range,
            'close': prices,
            'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
            'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
            'volume': [int(np.random.lognormal(15, 1)) for _ in prices]
        })

        df.set_index('date', inplace=True)
        self.historical_data[symbol] = df
        return df

    async def get_price_performance(self, symbol: str, start_date: date, end_date: date) -> float:
        """Calculate price performance between two dates."""
        try:
            data = await self.load_historical_data(symbol, start_date - timedelta(days=30), end_date + timedelta(days=30))
            start_price = data.loc[data.index <= pd.Timestamp(start_date), 'close'].iloc[-1]
            end_price = data.loc[data.index >= pd.Timestamp(end_date), 'close'].iloc[0]
            return (end_price - start_price) / start_price
        except (KeyError, IndexError):
            return 0.0

    async def backtest_recommendation(self, symbol: str, recommendation_date: date,
                                    recommendation: str, confidence: float) -> BacktestResult:
        """Backtest a single recommendation."""
        result = BacktestResult(
            symbol=symbol,
            recommendation_date=recommendation_date,
            recommendation=recommendation,
            confidence=confidence
        )

        # Calculate performance over different time horizons
        for days in [1, 7, 30]:
            end_date = recommendation_date + timedelta(days=days)
            perf = await self.get_price_performance(symbol, recommendation_date, end_date)
            market_perf = await self.get_price_performance('NIFTY50', recommendation_date, end_date)

            if days == 1:
                result.actual_performance_1d = perf
                result.market_performance_1d = market_perf
            elif days == 7:
                result.actual_performance_7d = perf
                result.market_performance_7d = market_perf
            elif days == 30:
                result.actual_performance_30d = perf
                result.market_performance_30d = market_perf

        return result

    def calculate_directional_accuracy(self, results: List[BacktestResult], days: int) -> float:
        """Calculate directional accuracy for given time horizon."""
        correct_predictions = 0
        total_predictions = 0

        for result in results:
            perf = getattr(result, f'actual_performance_{days}d')
            if perf is None:
                continue

            total_predictions += 1

            # Check if prediction direction was correct
            if result.recommendation == 'BUY' and perf > 0:
                correct_predictions += 1
            elif result.recommendation == 'SELL' and perf < 0:
                correct_predictions += 1
            elif result.recommendation == 'HOLD' and abs(perf) < 0.02:  # Within 2%
                correct_predictions += 1

        return correct_predictions / total_predictions if total_predictions > 0 else 0.0


class AccuracyValidationFramework:
    """Framework for validating recommendation accuracy."""

    def __init__(self):
        self.config = None
        self.container = None
        self.state_manager = None
        self.backtesting_engine = None
        self.recommendation_service = None

    async def setup(self):
        """Initialize the validation framework."""
        self.config = Config()
        self.container = DependencyContainer()
        await self.container.initialize(self.config)
        self.state_manager = await self.container.get_state_manager()
        self.backtesting_engine = BacktestingEngine(self.config, self.state_manager)
        self.recommendation_service = RecommendationService(self.config, self.state_manager)

    async def teardown(self):
        """Clean up resources."""
        if self.container:
            await self.container.cleanup()

    async def generate_synthetic_recommendations(self, symbols: List[str], days_back: int = 90) -> List[Dict[str, Any]]:
        """Generate synthetic historical recommendations for testing."""
        recommendations = []
        end_date = date.today()
        start_date = end_date - timedelta(days=days_back)

        for symbol in symbols:
            # Generate 2-3 recommendations per symbol over the period
            rec_dates = pd.date_range(start=start_date, end=end_date, freq='15D')  # Every 15 days

            for rec_date in rec_dates:
                # Simulate recommendation generation
                recommendation_types = ['BUY', 'HOLD', 'SELL']
                weights = [0.4, 0.4, 0.2]  # Bias toward BUY/HOLD

                recommendation = np.random.choice(recommendation_types, p=weights)
                confidence = np.random.beta(2, 2)  # Beta distribution for confidence

                recommendations.append({
                    'symbol': symbol,
                    'date': rec_date.date(),
                    'recommendation': recommendation,
                    'confidence': confidence,
                    'scores': {
                        'fundamental': np.random.beta(2, 2),
                        'valuation': np.random.beta(2, 2),
                        'growth': np.random.beta(2, 2),
                        'risk': np.random.beta(2, 2),
                        'qualitative': np.random.beta(2, 2)
                    }
                })

        return recommendations

    async def run_backtest_analysis(self, symbols: List[str] = None, days_back: int = 90) -> Dict[str, Any]:
        """Run comprehensive backtest analysis."""
        if symbols is None:
            symbols = ['RELIANCE', 'TCS', 'INFY', 'HDFC', 'ICICIBANK', 'BAJFINANCE']

        print(f"🔍 Running backtest analysis for {len(symbols)} symbols over {days_back} days")

        # Generate synthetic historical recommendations
        historical_recs = await self.generate_synthetic_recommendations(symbols, days_back)

        # Run backtests
        backtest_results = []
        for rec in historical_recs:
            result = await self.backtesting_engine.backtest_recommendation(
                rec['symbol'], rec['date'], rec['recommendation'], rec['confidence']
            )
            backtest_results.append(result)

        # Calculate accuracy metrics
        metrics = await self.calculate_accuracy_metrics(backtest_results)

        # Generate detailed report
        report = {
            'timestamp': datetime.now().isoformat(),
            'analysis_period_days': days_back,
            'symbols_analyzed': symbols,
            'total_recommendations': len(backtest_results),
            'metrics': metrics.to_dict(),
            'recommendations_breakdown': self._analyze_recommendation_distribution(backtest_results),
            'confidence_analysis': self._analyze_confidence_performance(backtest_results),
            'symbol_performance': self._analyze_symbol_performance(backtest_results),
            'sample_results': [r.to_dict() for r in backtest_results[:10]]  # First 10 for reference
        }

        return report

    async def calculate_accuracy_metrics(self, results: List[BacktestResult]) -> AccuracyMetrics:
        """Calculate comprehensive accuracy metrics."""
        if not results:
            return AccuracyMetrics(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

        # Basic counts
        buy_recs = sum(1 for r in results if r.recommendation == 'BUY')
        hold_recs = sum(1 for r in results if r.recommendation == 'HOLD')
        sell_recs = sum(1 for r in results if r.recommendation == 'SELL')

        # Directional accuracy
        acc_1d = self.backtesting_engine.calculate_directional_accuracy(results, 1)
        acc_7d = self.backtesting_engine.calculate_directional_accuracy(results, 7)
        acc_30d = self.backtesting_engine.calculate_directional_accuracy(results, 30)

        # Performance vs market
        outperform_1d = self._calculate_average_outperformance(results, 1)
        outperform_7d = self._calculate_average_outperformance(results, 7)
        outperform_30d = self._calculate_average_outperformance(results, 30)

        # Sharpe ratios (simplified)
        sharpe_1d = self._calculate_sharpe_ratio(results, 1)
        sharpe_7d = self._calculate_sharpe_ratio(results, 7)
        sharpe_30d = self._calculate_sharpe_ratio(results, 30)

        # Confidence analysis
        conf_analysis = self._analyze_confidence_performance(results)

        return AccuracyMetrics(
            total_recommendations=len(results),
            buy_recommendations=buy_recs,
            hold_recommendations=hold_recs,
            sell_recommendations=sell_recs,
            directional_accuracy_1d=acc_1d,
            directional_accuracy_7d=acc_7d,
            directional_accuracy_30d=acc_30d,
            avg_outperformance_1d=outperform_1d,
            avg_outperformance_7d=outperform_7d,
            avg_outperformance_30d=outperform_30d,
            sharpe_ratio_1d=sharpe_1d,
            sharpe_ratio_7d=sharpe_7d,
            sharpe_ratio_30d=sharpe_30d,
            high_confidence_accuracy=conf_analysis.get('high', 0),
            medium_confidence_accuracy=conf_analysis.get('medium', 0),
            low_confidence_accuracy=conf_analysis.get('low', 0)
        )

    def _calculate_average_outperformance(self, results: List[BacktestResult], days: int) -> float:
        """Calculate average outperformance vs market."""
        outperformances = []
        for result in results:
            stock_perf = getattr(result, f'actual_performance_{days}d')
            market_perf = getattr(result, f'market_performance_{days}d')

            if stock_perf is not None and market_perf is not None:
                outperformances.append(stock_perf - market_perf)

        return statistics.mean(outperformances) if outperformances else 0.0

    def _calculate_sharpe_ratio(self, results: List[BacktestResult], days: int) -> float:
        """Calculate simplified Sharpe ratio."""
        returns = []
        for result in results:
            stock_perf = getattr(result, f'actual_performance_{days}d')
            market_perf = getattr(result, f'market_performance_{days}d')

            if stock_perf is not None and market_perf is not None:
                excess_return = stock_perf - market_perf
                returns.append(excess_return)

        if not returns:
            return 0.0

        avg_return = statistics.mean(returns)
        if len(returns) > 1:
            std_return = statistics.stdev(returns)
            return avg_return / std_return if std_return > 0 else 0.0
        return 0.0

    def _analyze_recommendation_distribution(self, results: List[BacktestResult]) -> Dict[str, Any]:
        """Analyze distribution of recommendations."""
        rec_counts = {'BUY': 0, 'HOLD': 0, 'SELL': 0}
        for result in results:
            rec_counts[result.recommendation] += 1

        return {
            'counts': rec_counts,
            'percentages': {
                k: v / len(results) * 100 for k, v in rec_counts.items()
            }
        }

    def _analyze_confidence_performance(self, results: List[BacktestResult]) -> Dict[str, float]:
        """Analyze performance by confidence levels."""
        confidence_groups = {'high': [], 'medium': [], 'low': []}

        for result in results:
            if result.confidence >= 0.8:
                group = 'high'
            elif result.confidence >= 0.6:
                group = 'medium'
            else:
                group = 'low'

            # Check if directional prediction was correct (1-day)
            perf = result.actual_performance_1d
            if perf is not None:
                correct = (
                    (result.recommendation == 'BUY' and perf > 0) or
                    (result.recommendation == 'SELL' and perf < 0) or
                    (result.recommendation == 'HOLD' and abs(perf) < 0.02)
                )
                confidence_groups[group].append(1 if correct else 0)

        return {
            group: statistics.mean(scores) if scores else 0.0
            for group, scores in confidence_groups.items()
        }

    def _analyze_symbol_performance(self, results: List[BacktestResult]) -> Dict[str, Any]:
        """Analyze performance by symbol."""
        symbol_stats = {}

        for result in results:
            if result.symbol not in symbol_stats:
                symbol_stats[result.symbol] = {'recommendations': 0, 'correct_1d': 0, 'total_perf': 0}

            symbol_stats[result.symbol]['recommendations'] += 1

            # Check directional accuracy
            perf = result.actual_performance_1d
            if perf is not None:
                correct = (
                    (result.recommendation == 'BUY' and perf > 0) or
                    (result.recommendation == 'SELL' and perf < 0) or
                    (result.recommendation == 'HOLD' and abs(perf) < 0.02)
                )
                if correct:
                    symbol_stats[result.symbol]['correct_1d'] += 1

            # Accumulate performance
            if perf is not None:
                symbol_stats[result.symbol]['total_perf'] += perf

        # Calculate averages
        for symbol, stats in symbol_stats.items():
            stats['accuracy_1d'] = stats['correct_1d'] / stats['recommendations']
            stats['avg_performance'] = stats['total_perf'] / stats['recommendations']

        return symbol_stats

    async def generate_accuracy_report(self, report_data: Dict[str, Any]) -> str:
        """Generate a formatted accuracy report."""
        report = []
        report.append("📊 RECOMMENDATION ACCURACY REPORT")
        report.append("=" * 50)
        report.append(f"Analysis Period: {report_data['analysis_period_days']} days")
        report.append(f"Symbols Analyzed: {', '.join(report_data['symbols_analyzed'])}")
        report.append(f"Total Recommendations: {report_data['total_recommendations']}")
        report.append("")

        metrics = report_data['metrics']
        report.append("🎯 ACCURACY METRICS")
        report.append("-" * 30)
        report.append(f"Directional Accuracy (1-day): {metrics['directional_accuracy_1d']:.1%}")
        report.append(f"Directional Accuracy (7-day): {metrics['directional_accuracy_7d']:.1%}")
        report.append(f"Directional Accuracy (30-day): {metrics['directional_accuracy_30d']:.1%}")
        report.append("")
        report.append(f"Avg Outperformance (1-day): {metrics['avg_outperformance_1d']:.2%}")
        report.append(f"Avg Outperformance (7-day): {metrics['avg_outperformance_7d']:.2%}")
        report.append(f"Avg Outperformance (30-day): {metrics['avg_outperformance_30d']:.2%}")
        report.append("")
        report.append(f"Sharpe Ratio (1-day): {metrics['sharpe_ratio_1d']:.2f}")
        report.append(f"Sharpe Ratio (7-day): {metrics['sharpe_ratio_7d']:.2f}")
        report.append(f"Sharpe Ratio (30-day): {metrics['sharpe_ratio_30d']:.2f}")
        report.append("")

        breakdown = report_data['recommendations_breakdown']
        report.append("📈 RECOMMENDATION DISTRIBUTION")
        report.append("-" * 35)
        for rec_type, count in breakdown['counts'].items():
            pct = breakdown['percentages'][rec_type]
            report.append(f"{rec_type}: {count} ({pct:.1f}%)")
        report.append("")

        conf = report_data['confidence_analysis']
        report.append("🎖️  CONFIDENCE ANALYSIS")
        report.append("-" * 25)
        report.append(f"High Confidence Accuracy: {conf['high']:.1%}")
        report.append(f"Medium Confidence Accuracy: {conf['medium']:.1%}")
        report.append(f"Low Confidence Accuracy: {conf['low']:.1%}")
        report.append("")

        # Symbol performance
        symbol_perf = report_data['symbol_performance']
        report.append("🏆 SYMBOL PERFORMANCE")
        report.append("-" * 25)
        for symbol, stats in sorted(symbol_perf.items(), key=lambda x: x[1]['accuracy_1d'], reverse=True):
            report.append(f"{symbol}: {stats['accuracy_1d']:.1%} accuracy, {stats['avg_performance']:.2%} avg perf")

        return "\n".join(report)

    async def run_full_accuracy_validation(self) -> Dict[str, Any]:
        """Run complete accuracy validation suite."""
        print("🎯 Starting Accuracy Validation Framework")
        print("=" * 60)

        try:
            await self.setup()

            # Run backtest analysis
            report_data = await self.run_backtest_analysis()

            # Generate and display report
            report = await self.generate_accuracy_report(report_data)
            print(report)

            # Save detailed results
            results_file = f"accuracy_validation_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(results_file, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)

            print(f"\n📁 Detailed results saved to: {results_file}")

            return report_data

        finally:
            await self.teardown()


# Standalone execution
if __name__ == "__main__":
    async def main():
        framework = AccuracyValidationFramework()
        await framework.run_full_accuracy_validation()

    asyncio.run(main())