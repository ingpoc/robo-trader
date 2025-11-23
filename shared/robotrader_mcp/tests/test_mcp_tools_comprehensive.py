#!/usr/bin/env python3
"""
Comprehensive MCP Tools Test Suite

Tests all MCP tools with real application data to ensure they:
1. Don't crash on schema changes
2. Handle missing tables gracefully
3. Provide accurate results
4. Work with actual robo-trader database
"""

import sys
import os
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
import pytest


# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tools.system.check_health import check_system_health
from tools.database.query_portfolio import query_portfolio
from tools.system.queue_status import get_queue_status
from tools.system.coordinator_status import get_coordinator_status


class TestMCPTools:
    """Test suite for MCP tools."""

    @classmethod
    def setup_class(cls):
        """Setup test environment."""
        cls.db_path = os.environ.get(
            'ROBO_TRADER_DB',
            Path(__file__).parent.parent.parent.parent.parent / 'state' / 'robo_trader.db'
        )
        cls.api_base = os.environ.get('ROBO_TRADER_API', 'http://localhost:8000')

    def test_database_exists(self):
        """Test that database exists."""
        assert Path(self.db_path).exists(), f"Database not found at {self.db_path}"

    def test_database_readable(self):
        """Test that database is readable."""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            conn.close()
            assert True
        except sqlite3.Error as e:
            pytest.fail(f"Database not readable: {e}")

    # ================== Test check_system_health ==================

    def test_check_system_health_no_params(self):
        """Test check_system_health with no parameters."""
        result = check_system_health()
        assert result['success'] is True
        assert 'overall_status' in result
        assert result['overall_status'] in ['HEALTHY', 'DEGRADED', 'CRITICAL']
        print(f"✓ check_system_health (no params): {result['overall_status']}")

    def test_check_system_health_with_components(self):
        """Test check_system_health with specific components."""
        result = check_system_health(components=['database', 'disk_space'])
        assert result['success'] is True
        assert 'database' in result.get('health_results', {}) or 'disk_space' in result
        print(f"✓ check_system_health (with components): Success")

    def test_check_system_health_with_all_params(self):
        """Test check_system_health with all parameters."""
        result = check_system_health(
            components=['database', 'queues'],
            verbose=True,
            include_recommendations=True,
            timeout_seconds=5,
            use_cache=False
        )
        assert result['success'] is True
        print(f"✓ check_system_health (all params): Success")

    def test_check_system_health_no_invalid_params(self):
        """Test that check_system_health doesn't fail with unexpected params."""
        # This should not raise an exception
        try:
            result = check_system_health(verbose=True, include_recommendations=True)
            assert result['success'] is True
            print(f"✓ check_system_health (handles recommended params): Success")
        except TypeError as e:
            pytest.fail(f"check_system_health rejected valid parameter: {e}")

    # ================== Test query_portfolio ==================

    def test_query_portfolio_no_params(self):
        """Test query_portfolio with no filters."""
        result = query_portfolio()
        assert result['success'] is True
        assert 'portfolio_stats' in result
        print(f"✓ query_portfolio (no params): Success")

    def test_query_portfolio_with_filters(self):
        """Test query_portfolio with filters."""
        result = query_portfolio(filters=['stale_analysis'])
        assert result['success'] is True
        assert 'analysis' in result
        print(f"✓ query_portfolio (with filters): Success")

    def test_query_portfolio_with_all_params(self):
        """Test query_portfolio with all parameters."""
        result = query_portfolio(
            filters=[],
            limit=10,
            aggregation_only=True,
            include_recommendations=True,
            timeout_seconds=5,
            use_cache=False
        )
        assert result['success'] is True
        print(f"✓ query_portfolio (all params): Success")

    def test_query_portfolio_schema_detection(self):
        """Test that query_portfolio detects schema dynamically."""
        result = query_portfolio()
        if result['success']:
            assert 'schema_detected' in result
            assert 'tables_found' in result['schema_detected']
            print(f"✓ query_portfolio (schema detection): {result['schema_detected']['tables_found']}")

    def test_query_portfolio_handles_missing_columns(self):
        """Test that query_portfolio handles missing columns gracefully."""
        result = query_portfolio(filters=['nonexistent_filter'])
        # Should still succeed, just with empty results
        assert result['success'] is True
        print(f"✓ query_portfolio (missing columns): Handled gracefully")

    # ================== Test get_queue_status ==================

    def test_get_queue_status_with_filter(self):
        """Test get_queue_status with queue filter."""
        result = get_queue_status(queue_filter='')  # Empty filter = all queues
        assert isinstance(result, dict)
        print(f"✓ get_queue_status: Success")

    def test_get_queue_status_with_analysis(self):
        """Test get_queue_status with backlog analysis."""
        result = get_queue_status(
            queue_filter='',
            include_backlog_analysis=True,
            include_details=False
        )
        assert isinstance(result, dict)
        print(f"✓ get_queue_status (with analysis): Success")

    # ================== Test get_coordinator_status ==================

    def test_get_coordinator_status(self):
        """Test get_coordinator_status."""
        result = get_coordinator_status()
        assert isinstance(result, dict)
        print(f"✓ get_coordinator_status: Success")

    def test_get_coordinator_status_with_error_details(self):
        """Test get_coordinator_status with include_error_details."""
        # Check what parameters the function actually accepts
        result = get_coordinator_status(include_error_details=True)
        assert isinstance(result, dict)
        print(f"✓ get_coordinator_status (error details): Success")

    # ================== Database Integrity Tests ==================

    def test_portfolio_table_exists(self):
        """Test that portfolio table exists and is readable."""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM portfolio")
            count = cursor.fetchone()[0]
            conn.close()
            print(f"✓ portfolio table exists with {count} records")
        except sqlite3.Error:
            pytest.fail("portfolio table not found or not readable")

    def test_analysis_history_table_exists(self):
        """Test that analysis_history table exists."""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM analysis_history")
            count = cursor.fetchone()[0]
            conn.close()
            print(f"✓ analysis_history table exists with {count} records")
        except sqlite3.Error:
            pytest.fail("analysis_history table not found or not readable")

    def test_queue_tasks_table_schema(self):
        """Test queue_tasks table has expected columns."""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(queue_tasks)")
            columns = {row[1] for row in cursor.fetchall()}
            conn.close()

            expected = {'task_id', 'queue_name', 'status', 'task_type', 'payload'}
            assert expected.issubset(columns), f"Missing columns: {expected - columns}"
            print(f"✓ queue_tasks table has expected schema")
        except sqlite3.Error:
            pytest.fail("queue_tasks table schema check failed")

    # ================== Integration Tests ==================

    def test_tools_no_exceptions(self):
        """Test that all tools complete without exceptions."""
        tools_to_test = [
            ('check_system_health', check_system_health, {}),
            ('query_portfolio', query_portfolio, {}),
            ('get_queue_status', get_queue_status, {'queue_filter': ''}),
            ('get_coordinator_status', get_coordinator_status, {}),
        ]

        for tool_name, tool_func, params in tools_to_test:
            try:
                result = tool_func(**params)
                assert isinstance(result, dict)
                print(f"✓ {tool_name}: No exceptions")
            except Exception as e:
                pytest.fail(f"{tool_name} raised exception: {e}")

    def test_tools_response_format(self):
        """Test that tools return properly formatted responses."""
        result = check_system_health()
        assert 'success' in result or 'overall_status' in result
        print(f"✓ Tools return proper response format")

    # ================== Performance Tests ==================

    def test_query_portfolio_performance(self):
        """Test query_portfolio completes in reasonable time."""
        import time
        start = time.time()
        result = query_portfolio(limit=100)
        elapsed = time.time() - start
        assert elapsed < 5.0, f"query_portfolio took {elapsed}s (expected < 5s)"
        print(f"✓ query_portfolio completed in {elapsed:.2f}s")

    def test_check_system_health_performance(self):
        """Test check_system_health completes in reasonable time."""
        import time
        start = time.time()
        result = check_system_health(timeout_seconds=5)
        elapsed = time.time() - start
        assert elapsed < 30.0, f"check_system_health took {elapsed}s (expected < 30s)"
        print(f"✓ check_system_health completed in {elapsed:.2f}s")


if __name__ == '__main__':
    # Run tests with pytest
    pytest.main([__file__, '-v', '-s'])
