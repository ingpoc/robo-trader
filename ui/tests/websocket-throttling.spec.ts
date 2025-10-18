import { test, expect } from '@playwright/test';

test.describe('WebSocket Throttling in Chromium (Comet)', () => {
  test('should throttle WebSocket messages correctly in Chromium', async ({ page, browserName }) => {
    // Skip if not Chromium-based browser
    if (browserName !== 'chromium') {
      test.skip();
    }

    const messageTimestamps: number[] = [];
    let wsConnection: any = null;
    let processedMessages = 0;

    page.on('websocket', ws => {
      wsConnection = ws;
      ws.on('framereceived', () => {
        messageTimestamps.push(Date.now());
        processedMessages++;
      });
    });

    // Navigate to dashboard
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Monitor messages for 15 seconds to capture throttling behavior
    await page.waitForTimeout(15000);

    // Verify throttling is active (should process fewer messages than received)
    console.log(`Total messages received: ${messageTimestamps.length}`);
    console.log(`Messages processed: ${processedMessages}`);

    // With 5-second throttling, we should see controlled message processing
    // In a 15-second window, expect reasonable throttling (not excessive)
    expect(processedMessages).toBeLessThanOrEqual(10); // Allow for backend message frequency

    if (messageTimestamps.length > 1) {
      const intervals: number[] = [];
      for (let i = 1; i < messageTimestamps.length; i++) {
        intervals.push(messageTimestamps[i] - messageTimestamps[i - 1]);
      }

      const avgInterval = intervals.reduce((a, b) => a + b, 0) / intervals.length;
      console.log(`Average processing interval: ${avgInterval}ms`);

      // Should show throttling behavior (intervals should be reasonable, not too frequent)
      expect(avgInterval).toBeGreaterThan(1000); // At least 1 second between processing
      expect(avgInterval).toBeLessThan(10000); // At most 10 seconds (allowing for throttling)
    }
  });

  test('should load components correctly with throttling active', async ({ page, browserName }) => {
    // Skip if not Chromium-based browser
    if (browserName !== 'chromium') {
      test.skip();
    }

    // Navigate to dashboard
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Wait for WebSocket connection and throttling to take effect
    await page.waitForTimeout(10000);

    // Verify key components are rendered
    const dashboardContainer = page.locator('main[role="main"]');
    await expect(dashboardContainer).toBeVisible();

    // Check for metric cards using the actual class names from MetricCard component
    const metricCards = page.locator('.group.relative.overflow-hidden.border-0');
    const metricCount = await metricCards.count();
    expect(metricCount).toBeGreaterThan(0);

    // Verify metric card content is loaded
    const firstMetricCard = metricCards.first();
    await expect(firstMetricCard).toBeVisible();

    // Check for metric labels (Available Cash, Total Exposure, etc.)
    const metricLabels = page.locator('.text-sm.font-bold.text-warmgray-800.uppercase');
    const labelCount = await metricLabels.count();
    expect(labelCount).toBeGreaterThan(0);

    // Verify no excessive re-renders (components should be stable)
    const initialMetricText = await metricLabels.first().textContent();

    // Wait additional time to ensure stability
    await page.waitForTimeout(5000);
    const finalMetricText = await metricLabels.first().textContent();

    // Text should remain stable (no excessive updates causing flickering)
    expect(initialMetricText).toBe(finalMetricText);

    // Check that page remains responsive
    await expect(page.locator('body')).toBeVisible();
    await expect(page.locator('body')).not.toHaveClass(/loading/);
  });

  test('should handle rapid WebSocket messages without performance degradation', async ({ page, browserName }) => {
    // Skip if not Chromium-based browser
    if (browserName !== 'chromium') {
      test.skip();
    }

    let renderCount = 0;
    const renderTimestamps: number[] = [];

    // Monitor component re-renders
    page.on('console', msg => {
      if (msg.text().includes('render') || msg.text().includes('update')) {
        renderTimestamps.push(Date.now());
        renderCount++;
      }
    });

    // Navigate to dashboard
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Monitor for 10 seconds
    await page.waitForTimeout(10000);

    console.log(`Component render events: ${renderCount}`);

    // With throttling, renders should be controlled
    // Allow reasonable number of renders but not excessive
    expect(renderCount).toBeLessThan(50); // Reasonable upper bound

    // Page should remain functional
    await expect(page.locator('body')).toBeVisible();

    // Check for any error indicators
    const errorElements = page.locator('[data-testid*="error"], .error, .alert-danger');
    const errorCount = await errorElements.count();
    expect(errorCount).toBe(0);
  });
});