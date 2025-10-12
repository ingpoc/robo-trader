"""
Comprehensive Test Runner for Robo Trader Phase 4
Combines performance testing, accuracy validation, and system health checks.
"""

import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

from test_performance import PerformanceTestSuite
from test_accuracy import AccuracyValidationFramework


class ComprehensiveTestRunner:
    """Comprehensive test runner for Phase 4 validation."""

    def __init__(self):
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'phase': 'Phase 4: Testing & Optimization',
            'tests': {},
            'summary': {}
        }

    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all comprehensive tests."""
        print("🚀 Starting Comprehensive Phase 4 Test Suite")
        print("=" * 70)

        start_time = time.time()

        try:
            # 1. Performance Testing
            print("\n📊 Running Performance Tests...")
            perf_suite = PerformanceTestSuite()
            await perf_suite.run_full_performance_test()
            self.results['tests']['performance'] = 'completed'

        except Exception as e:
            print(f"❌ Performance tests failed: {e}")
            self.results['tests']['performance'] = f'failed: {str(e)}'

        try:
            # 2. Accuracy Validation
            print("\n🎯 Running Accuracy Validation...")
            accuracy_framework = AccuracyValidationFramework()
            accuracy_results = await accuracy_framework.run_full_accuracy_validation()
            self.results['tests']['accuracy'] = 'completed'
            self.results['accuracy_summary'] = accuracy_results.get('metrics', {})

        except Exception as e:
            print(f"❌ Accuracy validation failed: {e}")
            self.results['tests']['accuracy'] = f'failed: {str(e)}'

        try:
            # 3. System Health Check
            print("\n🏥 Running System Health Checks...")
            health_results = await self.run_health_checks()
            self.results['tests']['health'] = 'completed'
            self.results['health_status'] = health_results

        except Exception as e:
            print(f"❌ Health checks failed: {e}")
            self.results['tests']['health'] = f'failed: {str(e)}'

        # Calculate overall results
        total_time = time.time() - start_time
        self.results['total_duration_seconds'] = round(total_time, 2)

        # Generate summary
        self._generate_summary()

        # Save results
        self._save_results()

        print(f"\n✅ All tests completed in {total_time:.2f} seconds")
        print("📁 Results saved to: comprehensive_test_results.json")

        return self.results

    async def run_health_checks(self) -> Dict[str, Any]:
        """Run comprehensive health checks."""
        try:
            # Import here to avoid circular imports
            from src.config import Config
            from src.core.di import DependencyContainer

            config = Config()
            container = DependencyContainer()
            await container.initialize(config)

            health_status = {
                'database': False,
                'orchestrator': False,
                'scheduler': False,
                'agents': 0,
                'recommendations': 0,
                'alerts': 0
            }

            # Test database
            try:
                state_manager = await container.get_state_manager()
                portfolio = await state_manager.get_portfolio()
                health_status['database'] = True
            except:
                pass

            # Test orchestrator
            try:
                orchestrator = await container.get_orchestrator()
                if orchestrator:
                    health_status['orchestrator'] = True

                    # Check scheduler
                    if hasattr(orchestrator, 'background_scheduler') and orchestrator.background_scheduler:
                        health_status['scheduler'] = True

                    # Check agents
                    try:
                        agents = await orchestrator.get_agents_status()
                        health_status['agents'] = len([a for a in agents.values() if isinstance(a, dict) and a.get('status') == 'running'])
                    except:
                        pass

                    # Check recommendations
                    try:
                        recs = await orchestrator.state_manager.get_pending_approvals()
                        health_status['recommendations'] = len(recs)
                    except:
                        pass

                    # Check alerts
                    try:
                        alerts = await orchestrator.state_manager.alert_manager.get_active_alerts()
                        health_status['alerts'] = len(alerts)
                    except:
                        pass

            except:
                pass

            await container.cleanup()
            return health_status

        except Exception as e:
            return {'error': str(e)}

    def _generate_summary(self):
        """Generate test summary."""
        tests_run = len(self.results['tests'])
        tests_passed = sum(1 for result in self.results['tests'].values() if result == 'completed')
        tests_failed = tests_run - tests_passed

        self.results['summary'] = {
            'tests_run': tests_run,
            'tests_passed': tests_passed,
            'tests_failed': tests_failed,
            'success_rate': round(tests_passed / tests_run * 100, 1) if tests_run > 0 else 0,
            'total_duration_seconds': self.results['total_duration_seconds']
        }

        # Add performance insights if available
        if 'accuracy_summary' in self.results:
            acc = self.results['accuracy_summary']
            self.results['summary']['directional_accuracy_1d'] = acc.get('directional_accuracy_1d', 0)
            self.results['summary']['avg_outperformance_1d'] = acc.get('avg_outperformance_1d', 0)

    def _save_results(self):
        """Save test results to file."""
        results_file = f"comprehensive_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)

    def print_summary_report(self):
        """Print a formatted summary report."""
        print("\n" + "=" * 70)
        print("📋 COMPREHENSIVE TEST SUMMARY REPORT")
        print("=" * 70)

        summary = self.results.get('summary', {})

        print(f"Phase: {self.results['phase']}")
        print(f"Timestamp: {self.results['timestamp']}")
        print(f"Total Duration: {summary.get('total_duration_seconds', 0):.2f} seconds")
        print()

        print("TEST RESULTS:")
        for test_name, result in self.results['tests'].items():
            status = "✅ PASSED" if result == 'completed' else "❌ FAILED"
            print(f"  {test_name.upper()}: {status}")
            if result != 'completed':
                print(f"    Error: {result}")

        print()
        print("OVERALL STATISTICS:")
        print(f"  Tests Run: {summary.get('tests_run', 0)}")
        print(f"  Tests Passed: {summary.get('tests_passed', 0)}")
        print(f"  Tests Failed: {summary.get('tests_failed', 0)}")
        print(f"  Success Rate: {summary.get('success_rate', 0)}%")

        if 'accuracy_summary' in self.results:
            print()
            print("ACCURACY METRICS:")
            acc = self.results['accuracy_summary']
            print(f"  Directional Accuracy (1-day): {acc.get('directional_accuracy_1d', 0):.1%}")
            print(f"  Directional Accuracy (7-day): {acc.get('directional_accuracy_7d', 0):.1%}")
            print(f"  Directional Accuracy (30-day): {acc.get('directional_accuracy_30d', 0):.1%}")
            print(f"  Average Outperformance (1-day): {acc.get('avg_outperformance_1d', 0):.2%}")

        if 'health_status' in self.results:
            print()
            print("SYSTEM HEALTH:")
            health = self.results['health_status']
            if 'error' not in health:
                print(f"  Database: {'✅' if health.get('database') else '❌'}")
                print(f"  Orchestrator: {'✅' if health.get('orchestrator') else '❌'}")
                print(f"  Scheduler: {'✅' if health.get('scheduler') else '❌'}")
                print(f"  Active Agents: {health.get('agents', 0)}")
                print(f"  Pending Recommendations: {health.get('recommendations', 0)}")
                print(f"  Active Alerts: {health.get('alerts', 0)}")


async def main():
    """Main test runner entry point."""
    runner = ComprehensiveTestRunner()

    try:
        results = await runner.run_all_tests()
        runner.print_summary_report()

        # Exit with appropriate code
        success_rate = results.get('summary', {}).get('success_rate', 0)
        sys.exit(0 if success_rate >= 80 else 1)  # 80% success threshold

    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test runner failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())