#!/usr/bin/env python3
"""
End-to-End Test Script for Robo Trader Stock Monitoring System

This script performs a complete end-to-end test of the stock monitoring system by:
1. Running news monitoring for 5 major Indian stocks
2. Running earnings scheduler for fundamentals data
3. Executing the AI-powered recommendation engine
4. Displaying comprehensive analysis results

Stocks tested: RELIANCE, TCS, HDFC, INFY, BAJFINANCE
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, List, Any

from src.config import Config, load_config
from src.core.di import DependencyContainer
from src.core.background_scheduler import BackgroundScheduler
from src.services.recommendation_service import RecommendationEngine


class EndToEndTester:
    """Comprehensive end-to-end testing class for the stock monitoring system."""

    def __init__(self):
        self.config = None
        self.container = None
        self.state_manager = None
        self.scheduler = None
        self.recommendation_engine = None

        # Test stocks
        self.test_stocks = ['RELIANCE', 'TCS', 'HDFC', 'INFY', 'BAJFINANCE']

        # Results storage
        self.results = {
            'news_data': {},
            'earnings_data': {},
            'recommendations': {},
            'summary': {}
        }

    async def initialize_system(self) -> None:
        """Initialize the complete system with all dependencies."""
        print("🚀 Initializing Robo Trader System...")

        try:
            # Load configuration
            self.config = load_config()
            print("✅ Configuration loaded")

            # Initialize dependency container
            self.container = DependencyContainer()
            await self.container.initialize(self.config)
            print("✅ Dependency container initialized")

            # Get state manager
            self.state_manager = await self.container.get_state_manager()
            print("✅ State manager ready")

            # Create scheduler
            self.scheduler = BackgroundScheduler(self.config, self.state_manager)
            print("✅ Background scheduler created")

            # Initialize recommendation engine
            from src.services.fundamental_service import FundamentalService
            fundamental_service = FundamentalService(self.config, self.state_manager)
            risk_service = await self.container.get_risk_service()

            self.recommendation_engine = RecommendationEngine(
                config=self.config,
                state_manager=self.state_manager,
                fundamental_service=fundamental_service,
                risk_service=risk_service
            )
            print("✅ Recommendation engine initialized")

            print("🎯 System initialization complete!\n")

        except Exception as e:
            print(f"❌ System initialization failed: {e}")
            raise

    async def run_news_monitoring(self) -> None:
        """Execute enhanced news monitoring for all test stocks."""
        print("📰 Running News Monitoring...")

        try:
            # Create a mock portfolio with just our test stocks
            mock_portfolio = {
                'holdings': [
                    {'symbol': symbol, 'tradingsymbol': symbol, 'quantity': 100, 'average_price': 1000.0, 'last_price': 1000.0}
                    for symbol in self.test_stocks
                ]
            }

            # Mock the get_portfolio method temporarily
            original_get_portfolio = self.state_manager.get_portfolio
            async def mock_get_portfolio():
                return mock_portfolio
            self.state_manager.get_portfolio = mock_get_portfolio

            try:
                # Manually trigger news monitoring
                print("   Triggering enhanced news monitoring...")
                await self.scheduler._execute_news_monitoring({})

                # Collect results for each stock
                for symbol in self.test_stocks:
                    news_items = await self.state_manager.get_news_for_symbol(symbol, 10)
                    earnings_reports = await self.state_manager.get_earnings_for_symbol(symbol, 5)

                    self.results['news_data'][symbol] = {
                        'news_count': len(news_items),
                        'earnings_count': len(earnings_reports),
                        'latest_news': [
                            {
                                'title': item.get('title', 'N/A'),
                                'sentiment': item.get('sentiment', 'neutral'),
                                'date': item.get('created_at', 'N/A')
                            } for item in news_items[:3]  # Latest 3 items
                        ],
                        'earnings_summary': [
                            {
                                'fiscal_period': report.get('fiscal_period', 'N/A'),
                                'eps_actual': report.get('eps_actual'),
                                'revenue_actual': report.get('revenue_actual'),
                                'surprise_pct': report.get('surprise_pct')
                            } for report in earnings_reports[:2]  # Latest 2 reports
                        ]
                    }

            finally:
                # Restore original method
                self.state_manager.get_portfolio = original_get_portfolio

            print(f"✅ News monitoring completed for {len(self.test_stocks)} stocks")

            # Display summary
            total_news = sum(data['news_count'] for data in self.results['news_data'].values())
            total_earnings = sum(data['earnings_count'] for data in self.results['news_data'].values())
            print(f"   📊 Collected {total_news} news items and {total_earnings} earnings reports\n")

        except Exception as e:
            print(f"❌ News monitoring failed: {e}")
            raise

    async def run_earnings_scheduler(self) -> None:
        """Execute earnings scheduler for comprehensive fundamentals data."""
        print("📈 Running Earnings Scheduler...")

        try:
            # Create a mock portfolio with just our test stocks for earnings scheduler
            mock_portfolio = {
                'holdings': [
                    {'tradingsymbol': symbol, 'symbol': symbol, 'quantity': 100, 'average_price': 1000.0, 'last_price': 1000.0}
                    for symbol in self.test_stocks
                ]
            }

            # Mock the get_portfolio method temporarily
            original_get_portfolio = self.state_manager.get_portfolio
            async def mock_get_portfolio():
                return mock_portfolio
            self.state_manager.get_portfolio = mock_get_portfolio

            try:
                # Trigger earnings scheduler
                print("   Fetching earnings calendar and fundamentals...")
                await self.scheduler._execute_earnings_scheduler({})

                # Get comprehensive fundamental data using the fundamental service we created
                comprehensive_data = await self.recommendation_engine.fundamental_service.fetch_comprehensive_data(self.test_stocks)

                # Store earnings data results
                for symbol in self.test_stocks:
                    if symbol in comprehensive_data:
                        data = comprehensive_data[symbol]
                        self.results['earnings_data'][symbol] = {
                            'fundamentals_available': 'fundamentals' in data,
                            'earnings_count': len(data.get('earnings', [])),
                            'news_count': len(data.get('news', [])),
                            'fundamental_score': data['fundamentals'].overall_score if 'fundamentals' in data else None,
                            'pe_ratio': data['fundamentals'].pe_ratio if 'fundamentals' in data else None,
                            'pb_ratio': data['fundamentals'].pb_ratio if 'fundamentals' in data else None,
                            'roe': data['fundamentals'].roe if 'fundamentals' in data else None
                        }
                    else:
                        self.results['earnings_data'][symbol] = {
                            'fundamentals_available': False,
                            'earnings_count': 0,
                            'news_count': 0,
                            'fundamental_score': None,
                            'pe_ratio': None,
                            'pb_ratio': None,
                            'roe': None
                        }

            finally:
                # Restore original method
                self.state_manager.get_portfolio = original_get_portfolio

            print(f"✅ Earnings scheduler completed for {len(self.test_stocks)} stocks")

            # Display summary
            fundamentals_count = sum(1 for data in self.results['earnings_data'].values() if data['fundamentals_available'])
            earnings_count = sum(data['earnings_count'] for data in self.results['earnings_data'].values())
            print(f"   📊 Retrieved fundamentals for {fundamentals_count} stocks, {earnings_count} earnings reports\n")

        except Exception as e:
            print(f"❌ Earnings scheduler failed: {e}")
            raise

    async def run_recommendation_engine(self) -> None:
        """Execute AI-powered recommendation engine for all test stocks."""
        print("🤖 Running Recommendation Engine...")

        try:
            # Generate bulk recommendations
            print("   Generating AI-powered recommendations...")
            recommendations = await self.recommendation_engine.generate_bulk_recommendations(self.test_stocks)

            # Store and display results
            for symbol, result in recommendations.items():
                if result:
                    self.results['recommendations'][symbol] = {
                        'recommendation': result.recommendation_type,
                        'confidence': result.confidence_level,
                        'overall_score': result.overall_score,
                        'target_price': result.target_price,
                        'stop_loss': result.stop_loss,
                        'risk_level': result.risk_level,
                        'time_horizon': result.time_horizon,
                        'reasoning': result.reasoning,
                        'factors': {
                            'fundamental_score': result.factors.fundamental_score,
                            'valuation_score': result.factors.valuation_score,
                            'growth_score': result.factors.growth_score,
                            'risk_score': result.factors.risk_score,
                            'qualitative_score': result.factors.qualitative_score
                        }
                    }

                    # Store recommendation in database
                    await self.recommendation_engine.store_recommendation(result)

                else:
                    self.results['recommendations'][symbol] = {
                        'recommendation': 'N/A',
                        'confidence': 'N/A',
                        'overall_score': None,
                        'error': 'Insufficient data for recommendation'
                    }

            print(f"✅ Recommendation engine completed for {len(self.test_stocks)} stocks")

            # Display summary
            buy_count = sum(1 for r in self.results['recommendations'].values() if r.get('recommendation') == 'BUY')
            sell_count = sum(1 for r in self.results['recommendations'].values() if r.get('recommendation') == 'SELL')
            hold_count = sum(1 for r in self.results['recommendations'].values() if r.get('recommendation') == 'HOLD')
            print(f"   📊 Generated {buy_count} BUY, {sell_count} SELL, {hold_count} HOLD recommendations\n")

        except Exception as e:
            print(f"❌ Recommendation engine failed: {e}")
            raise

    def display_comprehensive_results(self) -> None:
        """Display comprehensive analysis results."""
        print("📊 COMPREHENSIVE ANALYSIS RESULTS")
        print("=" * 80)

        for symbol in self.test_stocks:
            print(f"\n🏢 {symbol}")
            print("-" * 40)

            # News Data
            news_data = self.results['news_data'].get(symbol, {})
            print(f"📰 News Items: {news_data.get('news_count', 0)}")
            print(f"📈 Earnings Reports: {news_data.get('earnings_count', 0)}")

            if news_data.get('latest_news'):
                print("   Recent News:")
                for news in news_data['latest_news'][:2]:
                    sentiment_emoji = {'positive': '🟢', 'negative': '🔴', 'neutral': '🟡'}.get(news['sentiment'], '🟡')
                    print(f"   {sentiment_emoji} {news['title'][:60]}...")

            # Earnings Data
            earnings_data = self.results['earnings_data'].get(symbol, {})
            if earnings_data.get('fundamentals_available'):
                print(f"📊 Fundamentals: Available (Score: {earnings_data.get('fundamental_score', 'N/A')})")
                if earnings_data.get('pe_ratio'):
                    print(f"   P/E Ratio: {earnings_data['pe_ratio']:.2f}")
                if earnings_data.get('pb_ratio'):
                    print(f"   P/B Ratio: {earnings_data['pb_ratio']:.2f}")
                if earnings_data.get('roe'):
                    print(f"   ROE: {earnings_data['roe']:.2f}%")
            else:
                print("📊 Fundamentals: Not Available")

            # Recommendation
            reco_data = self.results['recommendations'].get(symbol, {})
            recommendation = reco_data.get('recommendation', 'N/A')
            confidence = reco_data.get('confidence', 'N/A')
            score = reco_data.get('overall_score', 'N/A')

            emoji_map = {'BUY': '🟢 BUY', 'SELL': '🔴 SELL', 'HOLD': '🟡 HOLD'}
            reco_emoji = emoji_map.get(recommendation, f'⚪ {recommendation}')

            print(f"🎯 Recommendation: {reco_emoji} (Confidence: {confidence}, Score: {score})")

            if reco_data.get('target_price'):
                print(f"   Target Price: ₹{reco_data['target_price']:.2f}")
            if reco_data.get('stop_loss'):
                print(f"   Stop Loss: ₹{reco_data['stop_loss']:.2f}")

            if reco_data.get('reasoning'):
                print(f"   Reasoning: {reco_data['reasoning'][:100]}...")

        print("\n" + "=" * 80)
        print("📈 SUMMARY STATISTICS")
        print("=" * 80)

        # Calculate summary statistics
        total_news = sum(data.get('news_count', 0) for data in self.results['news_data'].values())
        total_earnings = sum(data.get('earnings_count', 0) for data in self.results['news_data'].values())
        fundamentals_available = sum(1 for data in self.results['earnings_data'].values() if data.get('fundamentals_available'))

        buy_recos = sum(1 for r in self.results['recommendations'].values() if r.get('recommendation') == 'BUY')
        sell_recos = sum(1 for r in self.results['recommendations'].values() if r.get('recommendation') == 'SELL')
        hold_recos = sum(1 for r in self.results['recommendations'].values() if r.get('recommendation') == 'HOLD')

        print(f"📰 Total News Items Collected: {total_news}")
        print(f"📈 Total Earnings Reports: {total_earnings}")
        print(f"📊 Stocks with Fundamentals: {fundamentals_available}/{len(self.test_stocks)}")
        print(f"🎯 Recommendations Generated: {buy_recos} BUY, {sell_recos} SELL, {hold_recos} HOLD")

        # Success criteria check
        print(f"\n✅ SUCCESS CRITERIA VERIFICATION:")
        success_criteria = [
            (total_news > 0, f"News data collected: {total_news} items"),
            (total_earnings > 0, f"Earnings data collected: {total_earnings} reports"),
            (fundamentals_available >= 3, f"Fundamentals available for {fundamentals_available}/{len(self.test_stocks)} stocks"),
            (len(self.results['recommendations']) == len(self.test_stocks), f"Recommendations for all {len(self.test_stocks)} stocks"),
            (buy_recos + sell_recos + hold_recos == len(self.test_stocks), "All recommendations are valid (BUY/SELL/HOLD)")
        ]

        all_passed = True
        for passed, description in success_criteria:
            status = "✅" if passed else "❌"
            print(f"   {status} {description}")
            if not passed:
                all_passed = False

        print(f"\n🎉 OVERALL RESULT: {'SUCCESS' if all_passed else 'PARTIAL SUCCESS'}")
        print(f"Test completed at: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")

    async def run_complete_test(self) -> None:
        """Run the complete end-to-end test suite."""
        print("🧪 STARTING END-TO-END TEST SUITE")
        print("=" * 80)
        print(f"Testing stocks: {', '.join(self.test_stocks)}")
        print("=" * 80)

        try:
            # Step 1: Initialize system
            await self.initialize_system()

            # Step 2: Run news monitoring
            await self.run_news_monitoring()

            # Step 3: Run earnings scheduler
            await self.run_earnings_scheduler()

            # Step 4: Run recommendation engine
            await self.run_recommendation_engine()

            # Step 5: Display results
            self.display_comprehensive_results()

        except Exception as e:
            print(f"❌ Test suite failed: {e}")
            raise

        finally:
            # Cleanup
            if self.container:
                await self.container.cleanup()
                print("\n🧹 System cleanup completed")

    async def save_results_to_file(self, filename: str = "end_to_end_test_results.json") -> None:
        """Save test results to JSON file."""
        try:
            # Add metadata
            self.results['metadata'] = {
                'test_timestamp': datetime.now(timezone.utc).isoformat(),
                'test_stocks': self.test_stocks,
                'system_version': 'v1.0',
                'test_duration_seconds': None  # Could be calculated if needed
            }

            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, indent=2, ensure_ascii=False, default=str)

            print(f"💾 Results saved to {filename}")

        except Exception as e:
            print(f"❌ Failed to save results: {e}")


async def main():
    """Main entry point for the end-to-end test."""
    tester = EndToEndTester()

    try:
        await tester.run_complete_test()
        await tester.save_results_to_file()

    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())