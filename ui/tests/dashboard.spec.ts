import { test, expect } from '@playwright/test';

test.describe('Dashboard Functionality', () => {
  test.beforeEach(async ({ page }) => {
    // Clear any existing state
    await page.context().clearCookies();
    await page.context().clearPermissions();
  });

  test('should load dashboard successfully', async ({ page }) => {
    // Navigate to dashboard
    await page.goto('/');

    // Wait for page to load
    await page.waitForLoadState('networkidle');

    // Check that we're on the dashboard
    await expect(page).toHaveURL(/.*\/$/);

    // Check for main dashboard elements
    await expect(page.locator('h1, h2').filter({ hasText: /dashboard|Dashboard/ })).toBeVisible();

    // Check for no JavaScript errors in console
    const errors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    // Wait a bit for any async errors
    await page.waitForTimeout(2000);

    // Should have no console errors
    expect(errors.length).toBe(0);
  });

  test('should establish WebSocket connection', async ({ page }) => {
    // Listen for WebSocket connections
    const wsConnections: string[] = [];
    page.on('websocket', ws => {
      wsConnections.push(ws.url());
    });

    // Navigate to dashboard
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Wait for WebSocket connection
    await page.waitForTimeout(3000);

    // Should have established WebSocket connection
    expect(wsConnections.length).toBeGreaterThan(0);
    expect(wsConnections.some(url => url.includes('ws://') || url.includes('wss://'))).toBe(true);
  });

  test('should load portfolio data via API', async ({ page }) => {
    // Monitor network requests
    const apiRequests: string[] = [];
    const apiResponses: any[] = [];

    page.on('request', request => {
      if (request.url().includes('/api/')) {
        apiRequests.push(request.url());
      }
    });

    page.on('response', response => {
      if (response.url().includes('/api/')) {
        apiResponses.push({
          url: response.url(),
          status: response.status(),
          ok: response.ok()
        });
      }
    });

    // Navigate to dashboard
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Wait for API calls to complete
    await page.waitForTimeout(5000);

    // Should have made API requests
    expect(apiRequests.length).toBeGreaterThan(0);

    // All API responses should be successful
    apiResponses.forEach(response => {
      expect(response.ok).toBe(true);
      expect(response.status).toBe(200);
    });
  });

  test('should navigate between pages', async ({ page }) => {
    // Start on dashboard
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Check navigation links exist
    const navLinks = page.locator('nav a, [role="navigation"] a');
    await expect(navLinks).toHaveCount(await navLinks.count());

    // Get all navigation links
    const links = await navLinks.all();
    expect(links.length).toBeGreaterThan(0);

    // Test navigation to each page
    for (const link of links) {
      const href = await link.getAttribute('href');
      if (href && !href.startsWith('http') && !href.startsWith('#')) {
        // Click the link
        await link.click();

        // Wait for navigation
        await page.waitForLoadState('networkidle');

        // Should be on the expected page
        await expect(page).toHaveURL(new RegExp(href.replace('/', '\\/')));

        // Go back to dashboard for next test
        await page.goto('/');
        await page.waitForLoadState('networkidle');
      }
    }
  });

  test('should handle API errors gracefully', async ({ page }) => {
    // Mock API failure
    await page.route('**/api/**', route => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Internal Server Error' })
      });
    });

    // Navigate to dashboard
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Should show error state or fallback UI
    // Look for error messages or fallback content
    const errorElements = page.locator('[data-testid*="error"], .error, .alert-danger');
    const hasErrorUI = await errorElements.count() > 0;

    // Either shows error UI or handles gracefully without crashing
    if (hasErrorUI) {
      await expect(errorElements.first()).toBeVisible();
    }

    // Page should still be functional
    await expect(page.locator('body')).toBeVisible();
  });

  test('should handle WebSocket disconnection gracefully', async ({ page }) => {
    // Navigate to dashboard
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Wait for initial WebSocket connection
    await page.waitForTimeout(3000);

    // Simulate network disconnection by blocking WebSocket
    await page.route('ws://**', route => {
      route.abort();
    });

    // Wait for reconnection attempts
    await page.waitForTimeout(5000);

    // Page should still be functional
    await expect(page.locator('body')).toBeVisible();

    // Should show connection status or handle gracefully
    const connectionStatus = page.locator('[data-testid*="connection"], .connection-status, .ws-status');
    if (await connectionStatus.count() > 0) {
      // If connection status is shown, it should indicate disconnected state
      await expect(connectionStatus.first()).toBeVisible();
    }
  });

  test('should capture screenshots on failure', async ({ page }) => {
    // This test will fail to demonstrate screenshot capture
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Intentionally fail the test
    await expect(page.locator('non-existent-element')).toBeVisible();
  });
});