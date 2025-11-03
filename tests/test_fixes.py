#!/usr/bin/env python3
"""
Test script to verify the critical issues have been fixed.

This script tests:
1. Portfolio data loading from CSV
2. News & earnings API responses
3. Portfolio scan functionality
"""

import asyncio
import json
import httpx
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"
TIMEOUT = 30.0

async def test_portfolio_scan():
    """Test portfolio scan functionality."""
    print("🔍 Testing portfolio scan...")

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(f"{BASE_URL}/api/portfolio-scan")

            if response.status_code == 200:
                data = response.json()
                print(f"✅ Portfolio scan successful: {data.get('message', 'No message')}")
                print(f"   Holdings loaded: {data.get('holdings_count', 0)}")
                print(f"   Data source: {data.get('source', 'unknown')}")
                return True
            else:
                print(f"❌ Portfolio scan failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False

    except Exception as e:
        print(f"❌ Portfolio scan error: {e}")
        return False

async def test_portfolio_data():
    """Test portfolio data retrieval."""
    print("\n📊 Testing portfolio data retrieval...")

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(f"{BASE_URL}/api/portfolio")

            if response.status_code == 200:
                data = response.json()
                holdings = data.get('holdings', [])
                print(f"✅ Portfolio data retrieved successfully")
                print(f"   Holdings count: {len(holdings)}")

                if holdings:
                    print(f"   Sample holding: {holdings[0].get('symbol', 'Unknown')}")
                    print(f"   Total P&L: {data.get('risk_aggregates', {}).get('portfolio', {}).get('total_pnl', 0):.2f}")

                return True
            else:
                print(f"❌ Portfolio data retrieval failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False

    except Exception as e:
        print(f"❌ Portfolio data error: {e}")
        return False

async def test_news_earnings():
    """Test news & earnings API endpoints."""
    print("\n📰 Testing news & earnings endpoints...")

    endpoints = [
        "/api/news-earnings/",
        "/api/earnings/upcoming",
        "/api/ai/recommendations"
    ]

    all_success = True

    for endpoint in endpoints:
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                response = await client.get(f"{BASE_URL}{endpoint}")

                if response.status_code == 200:
                    data = response.json()
                    if 'news' in data:
                        print(f"✅ {endpoint}: {len(data['news'])} news items")
                    if 'earnings' in data:
                        print(f"✅ {endpoint}: {len(data['earnings'])} earnings items")
                    if 'recommendations' in data:
                        print(f"✅ {endpoint}: {len(data['recommendations'])} recommendations")
                else:
                    print(f"❌ {endpoint}: {response.status_code}")
                    all_success = False

        except Exception as e:
            print(f"❌ {endpoint}: {e}")
            all_success = False

    return all_success

async def test_dashboard():
    """Test dashboard endpoint."""
    print("\n🏠 Testing dashboard endpoint...")

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(f"{BASE_URL}/api/dashboard")

            if response.status_code == 200:
                data = response.json()
                portfolio = data.get('portfolio', {})
                holdings = portfolio.get('holdings', [])

                print(f"✅ Dashboard data retrieved successfully")
                print(f"   Portfolio holdings: {len(holdings)}")
                print(f"   Initialization status: {data.get('initialization_status', {}).get('orchestrator_initialized', False)}")

                return True
            else:
                print(f"❌ Dashboard retrieval failed: {response.status_code}")
                return False

    except Exception as e:
        print(f"❌ Dashboard error: {e}")
        return False

async def main():
    """Run all tests."""
    print("🚀 Testing Robo Trader Critical Issues Fixes")
    print("=" * 50)
    print(f"Testing against: {BASE_URL}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 50)

    tests = [
        ("Portfolio Scan", test_portfolio_scan),
        ("Portfolio Data", test_portfolio_data),
        ("News & Earnings", test_news_earnings),
        ("Dashboard", test_dashboard),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 50)
    print("📋 TEST RESULTS SUMMARY")
    print("=" * 50)

    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
        if result:
            passed += 1

    print(f"\nOverall: {passed}/{len(results)} tests passed")

    if passed == len(results):
        print("🎉 All critical issues have been fixed!")
    else:
        print("⚠️  Some issues still need attention")

if __name__ == "__main__":
    asyncio.run(main())