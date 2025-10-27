#!/usr/bin/env python3
"""
Test script to verify portfolio loading and News & Earnings functionality.
Includes console logging monitoring.
"""

from playwright.sync_api import sync_playwright
import time

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Use headless=False for better debugging
        page = browser.new_page()

        # Set up console logging
        console_messages = []

        def handle_console(msg):
            console_messages.append({
                'type': msg.type,
                'text': msg.text,
                'location': msg.location,
                'timestamp': time.time()
            })
            print(f"[{msg.type.upper()}] {msg.text}")

        page.on('console', handle_console)

        # Navigate to application
        print("🚀 Navigating to application...")
        page.goto('http://localhost:3000')
        page.wait_for_load_state('networkidle')

        # Check Dashboard first (portfolio should be loaded)
        print("\n📊 Testing Dashboard - Portfolio Loading...")
        page.wait_for_selector('text=Overview', timeout=10000)
        page.click('text=Overview')
        page.wait_for_load_state('networkidle')

        # Wait for dashboard to load completely
        time.sleep(3)

        # Take screenshot of dashboard
        page.screenshot(path='dashboard_state.png', full_page=True)
        print("✅ Dashboard loaded - Screenshot saved as dashboard_state.png")

        # Navigate to News & Earnings page
        print("\n📰 Testing News & Earnings Page...")
        page.click('text=News & Earnings')
        page.wait_for_load_state('networkidle')

        # Wait for page to load
        time.sleep(3)

        # Test the refresh functionality (this should trigger our fixed API)
        print("🔄 Testing News & Earnings refresh (should call /api/news-earnings/)...")
        refresh_button = page.locator('button:has-text("Refresh")')
        if refresh_button.is_visible():
            refresh_button.click()
            page.wait_for_load_state('networkidle')
            time.sleep(5)  # Give time for API calls to complete
            print("✅ Refresh button clicked - API should have been called")
        else:
            print("⚠️ Refresh button not found")

        # Take screenshot of News & Earnings page
        page.screenshot(path='news_earnings_state.png', full_page=True)
        print("✅ News & Earnings page loaded - Screenshot saved as news_earnings_state.png")

        # Check for any error messages in console
        error_messages = [msg for msg in console_messages if msg['type'] == 'error']
        warning_messages = [msg for msg in console_messages if msg['type'] == 'warning']

        print(f"\n📊 Console Summary:")
        print(f"  - Total console messages: {len(console_messages)}")
        print(f"  - Errors: {len(error_messages)}")
        print(f"  - Warnings: {len(warning_messages)}")

        if error_messages:
            print("\n❌ Error Messages Found:")
            for error in error_messages:
                print(f"   - {error['text']}")

        if warning_messages:
            print("\n⚠️ Warning Messages:")
            for warning in warning_messages[:5]:  # Show first 5 warnings
                print(f"   - {warning['text']}")
            if len(warning_messages) > 5:
                print(f"   ... and {len(warning_messages) - 5} more")

        # Test Paper Trading page to check holdings display
        print("\n💰 Testing Paper Trading - Holdings Display...")
        page.click('text=Paper Trading')
        page.wait_for_load_state('networkidle')
        time.sleep(3)

        # Look for holdings information
        holdings_text = page.locator('text=₹').first()
        if holdings_text.is_visible():
            print("✅ Portfolio balance visible in Paper Trading")
        else:
            print("⚠️ Portfolio balance not immediately visible")

        page.screenshot(path='paper_trading_state.png', full_page=True)
        print("✅ Paper Trading page loaded - Screenshot saved as paper_trading_state.png")

        # Final check - navigate to Agents page to test dropdown issues
        print("\n🤖 Testing Agents Page - Dropdown Functionality...")
        page.click('text=Agents')
        page.wait_for_load_state('networkidle')
        page.click('text=Configuration')
        page.wait_for_load_state('networkidle')
        time.sleep(2)

        # Try to interact with a dropdown
        try:
            first_dropdown = page.locator('select').first()
            if first_dropdown.is_visible():
                print("✅ Found dropdown element in Agents Configuration")
                # Check if it's clickable
                if first_dropdown.is_enabled():
                    print("✅ Dropdown is enabled")
                else:
                    print("⚠️ Dropdown is disabled - CSS pointer-events issue confirmed")
            else:
                print("⚠️ No dropdown elements found")
        except Exception as e:
            print(f"⚠️ Error checking dropdowns: {e}")

        page.screenshot(path='agents_config_state.png', full_page=True)
        print("✅ Agents Configuration page loaded - Screenshot saved as agents_config_state.png")

        print("\n🎯 Test Complete!")
        print("Screenshots saved:")
        print("  - dashboard_state.png")
        print("  - news_earnings_state.png")
        print("  - paper_trading_state.png")
        print("  - agents_config_state.png")

        browser.close()

if __name__ == "__main__":
    main()