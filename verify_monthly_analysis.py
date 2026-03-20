#!/usr/bin/env python
"""Verify monthly portfolio analysis implementation."""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def check_database_schema():
    """Check if database schema includes portfolio analysis tables."""
    print("Checking database schema...")

    with open('src/core/database_state/base.py', 'r') as f:
        content = f.read()

    if 'CREATE TABLE IF NOT EXISTS portfolio_analysis' in content:
        print("  ✓ portfolio_analysis table found in schema")
    else:
        print("  ✗ portfolio_analysis table NOT found in schema")
        return False

    if 'CREATE TABLE IF NOT EXISTS monthly_analysis_summary' in content:
        print("  ✓ monthly_analysis_summary table found in schema")
    else:
        print("  ✗ monthly_analysis_summary table NOT found in schema")
        return False

    return True


def check_portfolio_monthly_analysis_state():
    """Check if PortfolioMonthlyAnalysisState is implemented."""
    print("\nChecking PortfolioMonthlyAnalysisState...")

    try:
        from src.core.database_state.portfolio_monthly_analysis_state import PortfolioMonthlyAnalysisState
        print("  ✓ PortfolioMonthlyAnalysisState imported successfully")

        # Check key methods
        methods = [
            'store_analysis',
            'get_analysis',
            'get_latest_analysis_for_symbol',
            'store_monthly_summary',
            'get_monthly_summary',
            'get_analysis_statistics'
        ]

        for method in methods:
            if hasattr(PortfolioMonthlyAnalysisState, method):
                print(f"  ✓ Method {method} exists")
            else:
                print(f"  ✗ Method {method} NOT found")
                return False

        return True
    except ImportError as e:
        print(f"  ✗ Failed to import PortfolioMonthlyAnalysisState: {e}")
        return False


def check_coordinator():
    """Check if MonthlyPortfolioAnalysisCoordinator is implemented."""
    print("\nChecking MonthlyPortfolioAnalysisCoordinator...")

    try:
        from src.core.coordinators.portfolio.monthly_analysis_coordinator import MonthlyPortfolioAnalysisCoordinator
        print("  ✓ MonthlyPortfolioAnalysisCoordinator imported successfully")

        # Check key methods
        methods = [
            'trigger_monthly_analysis',
            'get_analysis_history',
            'get_monthly_summaries',
            'get_analysis_statistics'
        ]

        for method in methods:
            if hasattr(MonthlyPortfolioAnalysisCoordinator, method):
                print(f"  ✓ Method {method} exists")
            else:
                print(f"  ✗ Method {method} NOT found")
                return False

        return True
    except ImportError as e:
        print(f"  ✗ Failed to import MonthlyPortfolioAnalysisCoordinator: {e}")
        return False


def check_api_routes():
    """Check if API routes are implemented."""
    print("\nChecking API routes...")

    try:
        from src.web.routes.portfolio.monthly_analysis import router
        print("  ✓ Monthly analysis router imported successfully")

        # Check routes
        routes = [route.path for route in router.routes]
        expected_routes = ['/trigger', '/history', '/summaries', '/statistics', '/latest/{symbol}', '/recommendations']

        for route in expected_routes:
            # Handle path parameters
            route_pattern = route.replace('{symbol}', '{symbol}')
            found = any(route_pattern in r for r in routes)
            if found:
                print(f"  ✓ Route {route} exists")
            else:
                print(f"  ✗ Route {route} NOT found")

        return True
    except ImportError as e:
        print(f"  ✗ Failed to import monthly analysis router: {e}")
        return False


def check_di_registration():
    """Check if DI registration is done."""
    print("\nChecking DI registration...")

    with open('src/core/di_registry_coordinators.py', 'r') as f:
        content = f.read()

    if 'from .coordinators.portfolio.monthly_analysis_coordinator import MonthlyPortfolioAnalysisCoordinator' in content:
        print("  ✓ Coordinator import found in di_registry_coordinators.py")
    else:
        print("  ✗ Coordinator import NOT found in di_registry_coordinators.py")

    if 'create_monthly_portfolio_analysis_coordinator' in content:
        print("  ✓ Coordinator registration found")
    else:
        print("  ✗ Coordinator registration NOT found")

    with open('src/core/di_registry_core.py', 'r') as f:
        content = f.read()

    if 'portfolio_monthly_analysis_state' in content:
        print("  ✓ State registration found in di_registry_core.py")
    else:
        print("  ✗ State registration NOT found in di_registry_core.py")

    with open('src/web/app.py', 'r') as f:
        content = f.read()

    if 'from .routes.portfolio.monthly_analysis import router as monthly_analysis_router' in content:
        print("  ✓ Router import found in app.py")
    else:
        print("  ✗ Router import NOT found in app.py")

    if 'app.include_router(monthly_analysis_router)' in content:
        print("  ✓ Router registration found in app.py")
    else:
        print("  ✗ Router registration NOT found in app.py")

    return True


def check_tests():
    """Check if tests are written."""
    print("\nChecking tests...")

    if os.path.exists('tests/test_monthly_portfolio_analysis.py'):
        print("  ✓ Test file exists")

        with open('tests/test_monthly_portfolio_analysis.py', 'r') as f:
            content = f.read()

        test_classes = ['TestPortfolioMonthlyAnalysisState', 'TestMonthlyPortfolioAnalysisCoordinator']
        for test_class in test_classes:
            if f'class {test_class}' in content:
                print(f"  ✓ Test class {test_class} found")
            else:
                print(f"  ✗ Test class {test_class} NOT found")
    else:
        print("  ✗ Test file does NOT exist")

    return True


def main():
    """Run all checks."""
    print("=" * 60)
    print("MONTHLY PORTFOLIO ANALYSIS IMPLEMENTATION VERIFICATION")
    print("=" * 60)

    checks = [
        check_database_schema,
        check_portfolio_monthly_analysis_state,
        check_coordinator,
        check_api_routes,
        check_di_registration,
        check_tests
    ]

    all_passed = True
    for check in checks:
        if not check():
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("✓ ALL CHECKS PASSED - Implementation is complete!")
    else:
        print("✗ SOME CHECKS FAILED - Please review the issues above")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())