import { test, expect } from '@playwright/test';

test.describe('Page Refresh and Error Detection', () => {
  test('should refresh page and capture any errors', async ({ page }) => {
    // Collect console errors and warnings
    const consoleMessages: string[] = [];
    const errors: string[] = [];
    const warnings: string[] = [];

    page.on('console', msg => {
      const text = msg.text();
      consoleMessages.push(`[${msg.type()}] ${text}`);

      if (msg.type() === 'error') {
        errors.push(text);
      } else if (msg.type() === 'warning') {
        warnings.push(text);
      }
    });

    // Collect page errors (JavaScript errors)
    const pageErrors: string[] = [];
    page.on('pageerror', error => {
      pageErrors.push(error.message);
    });

    // Collect failed requests
    const failedRequests: any[] = [];
    page.on('response', response => {
      if (!response.ok() && response.status() >= 400) {
        failedRequests.push({
          url: response.url(),
          status: response.status(),
          statusText: response.statusText()
        });
      }
    });

    // Navigate to the application
    console.log('Navigating to http://localhost:3000');
    await page.goto('http://localhost:3000');

    // Wait for initial load
    await page.waitForLoadState('networkidle');
    console.log('Initial page load complete');

    // Wait a bit for any initial errors to appear
    await page.waitForTimeout(3000);

    // Perform page refresh
    console.log('Refreshing the page...');
    await page.reload();

    // Wait for reload to complete
    await page.waitForLoadState('networkidle');
    console.log('Page refresh complete');

    // Wait additional time for any post-refresh errors
    await page.waitForTimeout(3000);

    // Check if page is still functional after refresh
    const bodyVisible = await page.locator('body').isVisible();
    expect(bodyVisible).toBe(true);

    // Log all collected information
    console.log('\n=== CONSOLE MESSAGES ===');
    consoleMessages.forEach(msg => console.log(msg));

    console.log('\n=== PAGE ERRORS ===');
    pageErrors.forEach(error => console.log(error));

    console.log('\n=== FAILED REQUESTS ===');
    failedRequests.forEach(req => console.log(`${req.status} ${req.statusText}: ${req.url}`));

    console.log('\n=== WARNINGS ===');
    warnings.forEach(warning => console.log(warning));

    // Report findings
    const issues = [];

    if (errors.length > 0) {
      issues.push(`${errors.length} console errors detected`);
    }

    if (pageErrors.length > 0) {
      issues.push(`${pageErrors.length} JavaScript errors detected`);
    }

    if (failedRequests.length > 0) {
      issues.push(`${failedRequests.length} failed HTTP requests detected`);
    }

    if (warnings.length > 0) {
      issues.push(`${warnings.length} console warnings detected`);
    }

    if (issues.length === 0) {
      console.log('\n✅ No issues detected during page refresh');
    } else {
      console.log(`\n❌ Issues found: ${issues.join(', ')}`);
    }

    // Assertions - fail the test if there are critical errors
    expect(pageErrors.length).toBe(0); // JavaScript errors are critical
    expect(failedRequests.filter(req => req.status >= 500).length).toBe(0); // Server errors are critical
  });

  test('should check WebSocket connection after refresh', async ({ page }) => {
    const wsConnections: string[] = [];
    const wsErrors: string[] = [];

    page.on('websocket', ws => {
      wsConnections.push(ws.url());
      ws.on('framereceived', event => {
        // WebSocket frame received
      });
      ws.on('framesent', event => {
        // WebSocket frame sent
      });
      ws.on('close', () => {
        // WebSocket closed
      });
    });

    // Navigate and refresh
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    await page.reload();
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);

    console.log(`WebSocket connections established: ${wsConnections.length}`);
    wsConnections.forEach(url => console.log(`- ${url}`));

    // Should have at least one WebSocket connection
    expect(wsConnections.length).toBeGreaterThan(0);
  });
});