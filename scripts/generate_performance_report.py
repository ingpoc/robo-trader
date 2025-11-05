"""
Performance Report Generator for Robo Trader
Generates comprehensive performance reports from test results.
"""

import json
import glob
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List
import statistics
import matplotlib.pyplot as plt
import pandas as pd


class PerformanceReportGenerator:
    """Generate comprehensive performance reports."""

    def __init__(self):
        self.reports_dir = Path("reports")
        self.reports_dir.mkdir(exist_ok=True)

    def generate_comprehensive_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report from all available test results."""
        print("📊 Generating Comprehensive Performance Report")

        # Find all test result files
        result_files = []
        result_files.extend(glob.glob("performance_test_results_*.json"))
        result_files.extend(glob.glob("accuracy_validation_results_*.json"))
        result_files.extend(glob.glob("comprehensive_test_results_*.json"))

        if not result_files:
            print("⚠️ No test result files found")
            return {}

        # Load and analyze results
        all_results = []
        for file_path in result_files:
            try:
                with open(file_path) as f:
                    data = json.load(f)
                    all_results.append(data)
            except Exception as e:
                print(f"⚠️ Failed to load {file_path}: {e}")

        if not all_results:
            print("⚠️ No valid test results found")
            return {}

        # Generate comprehensive report
        report = {
            'generated_at': datetime.now().isoformat(),
            'report_type': 'comprehensive_performance_analysis',
            'data_sources': len(all_results),
            'analysis_period': self._calculate_analysis_period(all_results),
            'performance_metrics': self._analyze_performance_metrics(all_results),
            'accuracy_metrics': self._analyze_accuracy_metrics(all_results),
            'system_health': self._analyze_system_health(all_results),
            'recommendations': self._generate_recommendations(all_results),
            'trends': self._analyze_trends(all_results)
        }

        # Save report
        report_file = self.reports_dir / f"comprehensive_performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        print(f"✅ Report saved to: {report_file}")
        return report

    def _calculate_analysis_period(self, results: List[Dict]) -> Dict[str, Any]:
        """Calculate the analysis period from results."""
        timestamps = []
        for result in results:
            if 'timestamp' in result:
                try:
                    timestamps.append(datetime.fromisoformat(result['timestamp']))
                except:
                    pass

        if not timestamps:
            return {'start': None, 'end': None, 'duration_days': 0}

        start_date = min(timestamps)
        end_date = max(timestamps)
        duration = (end_date - start_date).total_seconds() / (24 * 3600)

        return {
            'start': start_date.isoformat(),
            'end': end_date.isoformat(),
            'duration_days': round(duration, 1)
        }

    def _analyze_performance_metrics(self, results: List[Dict]) -> Dict[str, Any]:
        """Analyze performance metrics across all results."""
        perf_metrics = {
            'response_times': [],
            'throughput': [],
            'memory_usage': [],
            'cpu_usage': [],
            'error_rates': []
        }

        for result in results:
            # Extract performance metrics
            if 'summary' in result:
                summary = result['summary']
                if 'response_time_avg_ms' in summary:
                    perf_metrics['response_times'].append(summary['response_time_avg_ms'])
                if 'throughput_requests_per_second' in summary:
                    perf_metrics['throughput'].append(summary['throughput_requests_per_second'])

            # Extract system metrics
            if 'memory_avg_mb' in result.get('summary', {}):
                perf_metrics['memory_usage'].append(result['summary']['memory_avg_mb'])
            if 'cpu_avg_percent' in result.get('summary', {}):
                perf_metrics['cpu_usage'].append(result['summary']['cpu_avg_percent'])

        # Calculate aggregates
        analysis = {}
        for metric_name, values in perf_metrics.items():
            if values:
                analysis[f"{metric_name}_avg"] = round(statistics.mean(values), 2)
                analysis[f"{metric_name}_min"] = round(min(values), 2)
                analysis[f"{metric_name}_max"] = round(max(values), 2)
                if len(values) > 1:
                    analysis[f"{metric_name}_std"] = round(statistics.stdev(values), 2)

        return analysis

    def _analyze_accuracy_metrics(self, results: List[Dict]) -> Dict[str, Any]:
        """Analyze accuracy metrics across all results."""
        accuracy_data = []

        for result in results:
            if 'metrics' in result:
                metrics = result['metrics']
                if 'directional_accuracy_1d' in metrics:
                    accuracy_data.append({
                        'accuracy_1d': metrics.get('directional_accuracy_1d', 0),
                        'accuracy_7d': metrics.get('directional_accuracy_7d', 0),
                        'accuracy_30d': metrics.get('directional_accuracy_30d', 0),
                        'outperformance_1d': metrics.get('avg_outperformance_1d', 0),
                        'sharpe_1d': metrics.get('sharpe_ratio_1d', 0)
                    })

        if not accuracy_data:
            return {}

        # Calculate averages
        df = pd.DataFrame(accuracy_data)
        analysis = {}
        for col in df.columns:
            analysis[f"{col}_avg"] = round(df[col].mean(), 4)
            analysis[f"{col}_std"] = round(df[col].std(), 4) if len(df) > 1 else 0

        return analysis

    def _analyze_system_health(self, results: List[Dict]) -> Dict[str, Any]:
        """Analyze system health across all results."""
        health_data = []

        for result in results:
            if 'health_status' in result:
                health = result['health_status']
                if 'error' not in health:
                    health_data.append({
                        'database': health.get('database', False),
                        'orchestrator': health.get('orchestrator', False),
                        'scheduler': health.get('scheduler', False),
                        'agents': health.get('agents', 0),
                        'recommendations': health.get('recommendations', 0),
                        'alerts': health.get('alerts', 0)
                    })

        if not health_data:
            return {'status': 'no_health_data'}

        df = pd.DataFrame(health_data)

        # Calculate health percentages
        health_analysis = {}
        for col in ['database', 'orchestrator', 'scheduler']:
            if col in df.columns:
                success_rate = df[col].mean()
                health_analysis[f"{col}_uptime"] = round(success_rate * 100, 1)

        # Calculate averages for counts
        for col in ['agents', 'recommendations', 'alerts']:
            if col in df.columns:
                health_analysis[f"{col}_avg"] = round(df[col].mean(), 1)

        return health_analysis

    def _generate_recommendations(self, results: List[Dict]) -> List[str]:
        """Generate performance recommendations based on results."""
        recommendations = []

        # Analyze performance metrics
        perf_analysis = self._analyze_performance_metrics(results)

        if perf_analysis.get('response_times_avg', 0) > 500:  # > 500ms average
            recommendations.append("⚡ High response times detected. Consider optimizing database queries and API calls.")

        if perf_analysis.get('memory_usage_avg', 0) > 500:  # > 500MB average
            recommendations.append("🧠 High memory usage detected. Implement memory optimization and monitoring.")

        if perf_analysis.get('cpu_usage_avg', 0) > 80:  # > 80% CPU
            recommendations.append("🔥 High CPU usage detected. Consider scaling resources or optimizing compute-intensive operations.")

        # Analyze accuracy metrics
        acc_analysis = self._analyze_accuracy_metrics(results)

        if acc_analysis.get('accuracy_1d_avg', 0) < 0.55:  # < 55% accuracy
            recommendations.append("🎯 Low directional accuracy detected. Review and refine recommendation algorithms.")

        if acc_analysis.get('outperformance_1d_avg', 0) < 0:  # Negative outperformance
            recommendations.append("📉 Negative market outperformance. Re-evaluate investment strategy and risk management.")

        # Analyze system health
        health_analysis = self._analyze_system_health(results)

        if health_analysis.get('database_uptime', 100) < 95:
            recommendations.append("🗄️ Database reliability issues detected. Implement connection pooling and retry logic.")

        if health_analysis.get('orchestrator_uptime', 100) < 95:
            recommendations.append("🤖 Orchestrator stability issues detected. Review error handling and recovery mechanisms.")

        # General recommendations
        recommendations.extend([
            "📊 Implement continuous performance monitoring with alerting",
            "🔄 Schedule regular performance testing and optimization reviews",
            "📈 Set up automated performance regression testing",
            "🎛️ Configure production-ready logging and tracing",
            "🛡️ Implement comprehensive error handling and recovery"
        ])

        return recommendations

    def _analyze_trends(self, results: List[Dict]) -> Dict[str, Any]:
        """Analyze performance trends over time."""
        # Sort results by timestamp
        sorted_results = sorted(results, key=lambda x: x.get('timestamp', ''))

        trends = {
            'performance_trend': 'stable',
            'accuracy_trend': 'stable',
            'health_trend': 'stable'
        }

        if len(sorted_results) < 2:
            return trends

        # Analyze performance trends
        response_times = []
        for result in sorted_results:
            if 'summary' in result and 'response_time_avg_ms' in result['summary']:
                response_times.append(result['summary']['response_time_avg_ms'])

        if len(response_times) >= 2:
            if response_times[-1] > response_times[0] * 1.2:  # 20% degradation
                trends['performance_trend'] = 'degrading'
            elif response_times[-1] < response_times[0] * 0.8:  # 20% improvement
                trends['performance_trend'] = 'improving'

        return trends

    def print_report_summary(self, report: Dict[str, Any]):
        """Print a formatted report summary."""
        print("\n" + "=" * 80)
        print("📊 COMPREHENSIVE PERFORMANCE REPORT")
        print("=" * 80)

        period = report.get('analysis_period', {})
        if period.get('start'):
            print(f"Analysis Period: {period['start']} to {period['end']} ({period['duration_days']} days)")
        print(f"Data Sources: {report.get('data_sources', 0)} test runs")
        print(f"Generated: {report['generated_at']}")
        print()

        # Performance Metrics
        perf = report.get('performance_metrics', {})
        if perf:
            print("⚡ PERFORMANCE METRICS:")
            if 'response_times_avg' in perf:
                print(f"  Response Time: {perf['response_times_avg']:.1f}ms avg ({perf.get('response_times_min', 0):.1f}ms - {perf.get('response_times_max', 0):.1f}ms)")
            if 'throughput_avg' in perf:
                print(f"  Throughput: {perf['throughput_avg']:.1f} req/s")
            if 'memory_usage_avg' in perf:
                print(f"  Memory Usage: {perf['memory_usage_avg']:.1f}MB avg")
            if 'cpu_usage_avg' in perf:
                print(f"  CPU Usage: {perf['cpu_usage_avg']:.1f}% avg")
            print()

        # Accuracy Metrics
        acc = report.get('accuracy_metrics', {})
        if acc:
            print("🎯 ACCURACY METRICS:")
            if 'accuracy_1d_avg' in acc:
                print(f"  Directional Accuracy (1-day): {acc['accuracy_1d_avg']:.1%}")
            if 'outperformance_1d_avg' in acc:
                print(f"  Market Outperformance (1-day): {acc['outperformance_1d_avg']:.2%}")
            if 'sharpe_1d_avg' in acc:
                print(f"  Sharpe Ratio (1-day): {acc['sharpe_1d_avg']:.2f}")
            print()

        # System Health
        health = report.get('system_health', {})
        if health and health.get('status') != 'no_health_data':
            print("🏥 SYSTEM HEALTH:")
            for key, value in health.items():
                if key.endswith('_uptime'):
                    print(f"  {key.replace('_', ' ').title()}: {value}%")
                elif key.endswith('_avg'):
                    print(f"  {key.replace('_', ' ').title()}: {value}")
            print()

        # Recommendations
        recommendations = report.get('recommendations', [])
        if recommendations:
            print("💡 RECOMMENDATIONS:")
            for i, rec in enumerate(recommendations[:5], 1):  # Show top 5
                print(f"  {i}. {rec}")
            if len(recommendations) > 5:
                print(f"  ... and {len(recommendations) - 5} more recommendations")
            print()

        # Trends
        trends = report.get('trends', {})
        if trends:
            print("📈 PERFORMANCE TRENDS:")
            for trend_name, trend_status in trends.items():
                icon = {'improving': '📈', 'degrading': '📉', 'stable': '➡️'}.get(trend_status, '❓')
                print(f"  {trend_name.replace('_', ' ').title()}: {icon} {trend_status}")


def main():
    """Main report generation entry point."""
    generator = PerformanceReportGenerator()

    try:
        report = generator.generate_comprehensive_report()
        if report:
            generator.print_report_summary(report)
        else:
            print("❌ Failed to generate report - no data available")

    except Exception as e:
        print(f"💥 Report generation failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()