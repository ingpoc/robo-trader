"""
Tests for sandboxed code execution tools.

Tests execution isolation, security boundaries, and token efficiency.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.tools.execution.execute_python import execute_python
from src.tools.execution.execute_analysis import execute_analysis
from src.sandbox.manager import SandboxManager, SandboxConfig
from src.sandbox.isolation import IsolationLevel, IsolationPolicy


class TestExecutePython:
    """Tests for execute_python tool."""

    def test_simple_calculation(self):
        """Test basic code execution and result capture."""
        code = """
x = 10
y = 20
result = {"sum": x + y, "product": x * y}
"""
        response = execute_python(code)

        assert response["success"] is True
        assert response["result"]["sum"] == 30
        assert response["result"]["product"] == 200
        assert response["execution_time_ms"] > 0
        assert "token_efficiency" in response

    def test_context_injection(self):
        """Test variable injection via context."""
        code = """
values = [x * 2 for x in data]
result = {"original": data, "doubled": values}
"""
        response = execute_python(code, context={"data": [1, 2, 3, 4, 5]})

        assert response["success"] is True
        assert response["result"]["original"] == [1, 2, 3, 4, 5]
        assert response["result"]["doubled"] == [2, 4, 6, 8, 10]

    def test_json_serialization(self):
        """Test that results are JSON-serializable."""
        code = """
result = {
    "numbers": [1, 2, 3],
    "text": "hello",
    "nested": {"key": "value"},
    "bool": True,
    "none": None
}
"""
        response = execute_python(code)

        assert response["success"] is True
        assert response["result"]["numbers"] == [1, 2, 3]
        assert response["result"]["text"] == "hello"
        assert response["result"]["nested"]["key"] == "value"
        assert response["result"]["bool"] is True
        assert response["result"]["none"] is None

    def test_import_allowlist_math(self):
        """Test allowed imports work (math module)."""
        code = """
import math
result = {
    "pi": math.pi,
    "sqrt_16": math.sqrt(16),
    "factorial_5": math.factorial(5)
}
"""
        response = execute_python(code)

        assert response["success"] is True
        assert abs(response["result"]["pi"] - 3.14159) < 0.0001
        assert response["result"]["sqrt_16"] == 4.0
        assert response["result"]["factorial_5"] == 120

    def test_import_allowlist_statistics(self):
        """Test statistics module is allowed."""
        code = """
import statistics
data = [1, 2, 3, 4, 5, 10]
result = {
    "mean": statistics.mean(data),
    "median": statistics.median(data),
    "stdev": statistics.stdev(data)
}
"""
        response = execute_python(code)

        assert response["success"] is True
        assert response["result"]["mean"] == 4.166666666666667
        assert response["result"]["median"] == 3.5
        assert response["result"]["stdev"] > 0

    def test_import_restriction_os(self):
        """Test that restricted imports are blocked."""
        code = """
import os
result = {"home": os.environ.get("HOME")}
"""
        response = execute_python(code)

        assert response["success"] is False
        assert "not allowed" in response["error"].lower() or "os" in response["error"].lower()

    def test_import_restriction_subprocess(self):
        """Test subprocess import is blocked."""
        code = """
import subprocess
result = {"test": "should fail"}
"""
        response = execute_python(code)

        assert response["success"] is False
        assert "not allowed" in response["error"].lower()

    def test_dangerous_pattern_eval(self):
        """Test that eval() is blocked by code validation."""
        code = """
result = eval("1 + 1")
"""
        response = execute_python(code)

        # Should fail at validation or execution
        assert response["success"] is False

    def test_dangerous_pattern_exec(self):
        """Test that exec() is blocked by code validation."""
        code = """
exec("result = 123")
"""
        response = execute_python(code)

        assert response["success"] is False

    def test_timeout_protection(self):
        """Test that infinite loops timeout."""
        code = """
while True:
    pass
"""
        response = execute_python(code, timeout_seconds=2)

        assert response["success"] is False
        assert "timeout" in response["error"].lower()
        assert response["execution_time_ms"] >= 2000

    def test_code_validation_required(self):
        """Test that non-empty code is required."""
        response = execute_python("")

        assert response["success"] is False
        assert "code" in response["error"].lower()

    def test_timeout_range_validation(self):
        """Test timeout parameter bounds."""
        code = "result = {'test': 1}"

        # Too low
        response = execute_python(code, timeout_seconds=0)
        assert response["success"] is False

        # Too high
        response = execute_python(code, timeout_seconds=150)
        assert response["success"] is False

        # Valid
        response = execute_python(code, timeout_seconds=30)
        assert response["success"] is True

    def test_isolation_level_production(self):
        """Test production isolation level."""
        code = """
result = {
    "level": "production",
    "data": [1, 2, 3]
}
"""
        response = execute_python(code, isolation_level="production")
        assert response["success"] is True
        assert response["result"]["level"] == "production"

    def test_isolation_level_hardened(self):
        """Test hardened isolation level."""
        code = """
result = {
    "level": "hardened",
    "data": [1, 2, 3]
}
"""
        response = execute_python(code, isolation_level="hardened")
        assert response["success"] is True
        assert response["result"]["level"] == "hardened"

    def test_complex_data_analysis(self):
        """Test complex data analysis workflow."""
        code = """
import statistics
import json

data = {
    "stocks": [
        {"symbol": "AAPL", "price": 150, "volume": 1000000},
        {"symbol": "GOOGL", "price": 140, "volume": 800000},
        {"symbol": "MSFT", "price": 380, "volume": 500000},
    ]
}

prices = [s["price"] for s in data["stocks"]]
volumes = [s["volume"] for s in data["stocks"]]

result = {
    "count": len(data["stocks"]),
    "avg_price": statistics.mean(prices),
    "median_price": statistics.median(prices),
    "total_volume": sum(volumes),
    "price_range": {"min": min(prices), "max": max(prices)},
    "symbols": [s["symbol"] for s in data["stocks"]]
}
"""
        response = execute_python(code)

        assert response["success"] is True
        assert response["result"]["count"] == 3
        assert response["result"]["avg_price"] == 223.33333333333334
        assert response["result"]["median_price"] == 150
        assert response["result"]["total_volume"] == 2300000
        assert response["result"]["price_range"]["min"] == 140
        assert response["result"]["price_range"]["max"] == 380
        assert response["result"]["symbols"] == ["AAPL", "GOOGL", "MSFT"]


class TestExecuteAnalysis:
    """Tests for execute_analysis tool."""

    def test_filter_simple_condition(self):
        """Test simple data filtering."""
        response = execute_analysis(
            analysis_type="filter",
            data={
                "stocks": [
                    {"symbol": "AAPL", "price": 150},
                    {"symbol": "GOOGL", "price": 140},
                    {"symbol": "MSFT", "price": 380},
                ]
            },
            parameters={
                "data_field": "stocks",
                "conditions": [
                    {"field": "price", "operator": ">", "value": 150}
                ]
            }
        )

        assert response["success"] is True
        assert response["result"]["filtered_count"] == 1
        assert response["result"]["data"][0]["symbol"] == "MSFT"

    def test_filter_multiple_conditions_and(self):
        """Test filtering with multiple AND conditions."""
        response = execute_analysis(
            analysis_type="filter",
            data={
                "items": [
                    {"id": 1, "status": "active", "value": 100},
                    {"id": 2, "status": "active", "value": 50},
                    {"id": 3, "status": "inactive", "value": 100},
                ]
            },
            parameters={
                "data_field": "items",
                "conditions": [
                    {"field": "status", "operator": "==", "value": "active"},
                    {"field": "value", "operator": ">", "value": 75}
                ],
                "logic": "AND"
            }
        )

        assert response["success"] is True
        assert response["result"]["filtered_count"] == 1
        assert response["result"]["data"][0]["id"] == 1

    def test_filter_multiple_conditions_or(self):
        """Test filtering with multiple OR conditions."""
        response = execute_analysis(
            analysis_type="filter",
            data={
                "items": [
                    {"id": 1, "category": "A", "score": 50},
                    {"id": 2, "category": "B", "score": 75},
                    {"id": 3, "category": "C", "score": 100},
                ]
            },
            parameters={
                "data_field": "items",
                "conditions": [
                    {"field": "category", "operator": "==", "value": "A"},
                    {"field": "score", "operator": ">", "value": 90}
                ],
                "logic": "OR"
            }
        )

        assert response["success"] is True
        assert response["result"]["filtered_count"] == 2  # A and score > 90

    def test_aggregate_group_by(self):
        """Test aggregation with grouping."""
        response = execute_analysis(
            analysis_type="aggregate",
            data={
                "sales": [
                    {"region": "North", "amount": 1000},
                    {"region": "North", "amount": 1500},
                    {"region": "South", "amount": 2000},
                    {"region": "South", "amount": 1800},
                ]
            },
            parameters={
                "data_field": "sales",
                "group_by": "region"
            }
        )

        assert response["success"] is True
        assert response["result"]["success"] is True
        assert response["result"]["group_count"] == 2
        assert response["result"]["total_items"] == 4

    def test_transform_select_fields(self):
        """Test data transformation with field selection."""
        response = execute_analysis(
            analysis_type="transform",
            data={
                "users": [
                    {"id": 1, "name": "Alice", "email": "alice@example.com", "phone": "555-0001"},
                    {"id": 2, "name": "Bob", "email": "bob@example.com", "phone": "555-0002"},
                ]
            },
            parameters={
                "data_field": "users",
                "output_fields": ["id", "name", "email"]
            }
        )

        assert response["success"] is True
        assert response["result"]["count"] == 2
        assert "phone" not in response["result"]["data"][0]
        assert response["result"]["data"][0]["name"] == "Alice"

    def test_transform_rename_fields(self):
        """Test data transformation with field renaming."""
        response = execute_analysis(
            analysis_type="transform",
            data={
                "items": [
                    {"id": 1, "value": 100},
                    {"id": 2, "value": 200},
                ]
            },
            parameters={
                "data_field": "items",
                "output_fields": ["id", "value"],
                "rename": {"value": "amount"}
            }
        )

        assert response["success"] is True
        assert response["result"]["count"] == 2
        assert "amount" in response["result"]["data"][0]
        assert "value" not in response["result"]["data"][0]
        assert response["result"]["data"][0]["amount"] == 100

    def test_validate_required_field(self):
        """Test data validation with required field checks."""
        response = execute_analysis(
            analysis_type="validate",
            data={
                "records": [
                    {"id": 1, "name": "Alice", "email": "alice@example.com"},
                    {"id": 2, "name": "Bob"},  # Missing email
                ]
            },
            parameters={
                "data_field": "records",
                "validations": [
                    {"field": "id", "type": "numeric", "required": True},
                    {"field": "name", "type": "string", "required": True},
                    {"field": "email", "type": "string", "required": True}
                ]
            }
        )

        assert response["success"] is True
        # Second record should have validation issues
        issues = response["result"]["issues"]
        assert len(issues) > 0
        assert response["result"]["valid_count"] == 1

    def test_validate_type_checking(self):
        """Test data validation with type checking."""
        response = execute_analysis(
            analysis_type="validate",
            data={
                "values": [
                    {"id": 1, "price": 99.99},
                    {"id": 2, "price": "invalid"},  # Not numeric
                ]
            },
            parameters={
                "data_field": "values",
                "validations": [
                    {"field": "id", "type": "numeric", "required": True},
                    {"field": "price", "type": "numeric", "required": True}
                ]
            }
        )

        assert response["success"] is True
        assert response["result"]["invalid_count"] == 1
        assert len(response["result"]["issues"]) > 0

    def test_invalid_analysis_type(self):
        """Test error handling for invalid analysis type."""
        response = execute_analysis(
            analysis_type="invalid",
            data={"items": []},
            parameters={}
        )

        assert response["success"] is False
        assert "Unknown analysis type" in response["error"]

    def test_missing_data_field_parameter(self):
        """Test handling of missing data_field parameter."""
        response = execute_analysis(
            analysis_type="aggregate",
            data={"items": [1, 2, 3]},
            parameters={
                "group_by": "status"
                # Missing data_field
            }
        )

        # Should still work, defaults to "data"
        assert isinstance(response, dict)

    def test_complex_filter_portfolio(self):
        """Test complex portfolio filtering scenario."""
        portfolio = {
            "holdings": [
                {"symbol": "AAPL", "sector": "Tech", "roi": 15.5, "volatility": 25},
                {"symbol": "JNJ", "sector": "Healthcare", "roi": 8.2, "volatility": 15},
                {"symbol": "GOOGL", "sector": "Tech", "roi": 12.3, "volatility": 28},
                {"symbol": "XOM", "sector": "Energy", "roi": 5.1, "volatility": 35},
                {"symbol": "MSFT", "sector": "Tech", "roi": 18.7, "volatility": 22},
            ]
        }

        response = execute_analysis(
            analysis_type="filter",
            data=portfolio,
            parameters={
                "data_field": "holdings",
                "conditions": [
                    {"field": "sector", "operator": "==", "value": "Tech"},
                    {"field": "roi", "operator": ">", "value": 10},
                    {"field": "volatility", "operator": "<", "value": 30}
                ],
                "logic": "AND"
            }
        )

        assert response["success"] is True
        # Should match: AAPL, MSFT (not GOOGL due to volatility)
        assert response["result"]["filtered_count"] == 2
        symbols = [s["symbol"] for s in response["result"]["data"]]
        assert set(symbols) == {"AAPL", "MSFT"}


class TestSandboxIsolation:
    """Tests for sandbox isolation and security."""

    def test_no_file_system_access(self):
        """Test that file system access is prevented."""
        code = """
try:
    with open("/etc/passwd", "r") as f:
        result = {"success": True, "content": f.read()}
except Exception as e:
    result = {"success": False, "error": str(e)}
"""
        response = execute_python(code)

        # Should fail regardless
        assert response["success"] is False or \
               (response["success"] is True and response["result"]["success"] is False)

    def test_no_network_access(self):
        """Test that network access is prevented."""
        code = """
import socket
try:
    socket.create_connection(("8.8.8.8", 53), timeout=1)
    result = {"success": True}
except Exception as e:
    result = {"success": False, "error": str(e)}
"""
        response = execute_python(code)

        # Should fail - socket not in allowlist
        assert response["success"] is False

    def test_no_environment_variable_leakage(self):
        """Test that sensitive environment variables are not accessible."""
        code = """
import os
result = {
    "aws_key": os.environ.get("AWS_ACCESS_KEY_ID"),
    "api_secret": os.environ.get("ZERODHA_API_SECRET"),
    "home": os.environ.get("HOME", "not_leaked")
}
"""
        response = execute_python(code)

        assert response["success"] is True
        # AWS and API keys should be None/not accessible
        assert response["result"]["aws_key"] is None
        assert response["result"]["api_secret"] is None


class TestTokenEfficiency:
    """Tests for token efficiency claims."""

    def test_execution_output_structure(self):
        """Test that execution output includes token efficiency information."""
        response = execute_python("result = {'data': [1, 2, 3]}")

        assert "token_efficiency" in response
        assert "compression_ratio" in response["token_efficiency"]
        assert "98%" in response["token_efficiency"]["compression_ratio"]
        assert "estimated_traditional_tokens" in response["token_efficiency"]
        assert "estimated_sandbox_tokens" in response["token_efficiency"]

    def test_analysis_output_structure(self):
        """Test that analysis output includes token efficiency information."""
        response = execute_analysis(
            analysis_type="filter",
            data={"items": [1, 2, 3]},
            parameters={"data_field": "items"}
        )

        assert "token_efficiency" in response["result"]
        assert "99%" in response["result"]["token_efficiency"]["compression_ratio"]


if __name__ == "__main__":
    # Run tests manually for pytest-free execution
    test_python = TestExecutePython()
    test_analysis = TestExecuteAnalysis()
    test_isolation = TestSandboxIsolation()
    test_efficiency = TestTokenEfficiency()

    passed = 0
    failed = 0

    for test_class in [test_python, test_analysis, test_isolation, test_efficiency]:
        for method_name in dir(test_class):
            if method_name.startswith("test_"):
                try:
                    method = getattr(test_class, method_name)
                    method()
                    print(f"✓ {test_class.__class__.__name__}::{method_name}")
                    passed += 1
                except AssertionError as e:
                    print(f"✗ {test_class.__class__.__name__}::{method_name}: {e}")
                    failed += 1
                except Exception as e:
                    print(f"✗ {test_class.__class__.__name__}::{method_name}: {type(e).__name__}: {e}")
                    failed += 1

    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed")
    print(f"{'='*60}")
