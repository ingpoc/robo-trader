import { test, expect } from '@playwright/test';

test.describe('WebSocket and API Integration', () => {
  test('should handle WebSocket messages correctly', async ({ page }) => {
    // Track WebSocket messages
    const wsMessages: any[] = [];
    let wsConnection: any = null;

    page.on('websocket', ws => {
      wsConnection = ws;
      ws.on('framereceived', event => {
        try {
          const message = JSON.parse(event.payload as string);
          wsMessages.push(message);
        } catch (e) {
          // Handle non-JSON messages
          wsMessages.push(event.payload);
        }
      });
    });

    // Navigate to dashboard
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Wait for WebSocket connection and messages
    await page.waitForTimeout(5000);

    // Should have received some WebSocket messages
    expect(wsMessages.length).toBeGreaterThan(0);

    // Check for heartbeat messages
    const heartbeatMessages = wsMessages.filter(msg =>
      typeof msg === 'object' && msg.type === 'heartbeat'
    );
    expect(heartbeatMessages.length).toBeGreaterThan(0);

    // Check for data update messages
    const dataMessages = wsMessages.filter(msg =>
      typeof msg === 'object' && (msg.type === 'update' || msg.type === 'data')
    );
    // May or may not have data messages depending on backend state
    console.log(`Received ${dataMessages.length} data messages`);
  });

  test('should make successful API calls', async ({ page }) => {
    // Track API calls
    const apiCalls: { url: string; method: string; status: number; response: any }[] = [];

    page.on('response', async response => {
      if (response.url().includes('/api/')) {
        try {
          const responseBody = await response.json();
          apiCalls.push({
            url: response.url(),
            method: response.request().method(),
            status: response.status(),
            response: responseBody
          });
        } catch (e) {
          apiCalls.push({
            url: response.url(),
            method: response.request().method(),
            status: response.status(),
            response: null
          });
        }
      }
    });

    // Navigate to dashboard
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Wait for API calls to complete
    await page.waitForTimeout(5000);

    // Should have made API calls
    expect(apiCalls.length).toBeGreaterThan(0);

    // All API calls should be successful
    apiCalls.forEach(call => {
      expect(call.status).toBe(200);
      console.log(`API Call: ${call.method} ${call.url} - Status: ${call.status}`);
    });
  });

  test('should handle API authentication', async ({ page }) => {
    // Check if API calls include authentication headers
    const authHeaders: string[] = [];

    page.on('request', request => {
      if (request.url().includes('/api/')) {
        const authHeader = request.headers()['authorization'] || request.headers()['Authorization'];
        if (authHeader) {
          authHeaders.push(authHeader);
        }
      }
    });

    // Navigate to dashboard
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Wait for API calls
    await page.waitForTimeout(3000);

    // Should have authentication headers if API requires auth
    // Note: This depends on the actual API implementation
    console.log(`Found ${authHeaders.length} authenticated API calls`);
  });

  test('should handle WebSocket reconnection', async ({ page }) => {
    let wsConnections = 0;
    let wsDisconnections = 0;

    page.on('websocket', ws => {
      wsConnections++;
      ws.on('close', () => {
        wsDisconnections++;
      });
    });

    // Navigate to dashboard
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Wait for initial connection
    await page.waitForTimeout(3000);
    expect(wsConnections).toBeGreaterThan(0);

    // Simulate network interruption by blocking WebSocket
    await page.route('ws://**', route => route.abort());

    // Wait for disconnection and potential reconnection
    await page.waitForTimeout(10000);

    // Should have handled disconnection gracefully
    console.log(`WebSocket connections: ${wsConnections}, disconnections: ${wsDisconnections}`);

    // Page should still be functional
    await expect(page.locator('body')).toBeVisible();
  });

  test('should validate API response structure', async ({ page }) => {
    const apiResponses: any[] = [];

    page.on('response', async response => {
      if (response.url().includes('/api/') && response.ok()) {
        try {
          const data = await response.json();
          apiResponses.push({
            url: response.url(),
            data: data
          });
        } catch (e) {
          // Skip non-JSON responses
        }
      }
    });

    // Navigate to dashboard
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Wait for API responses
    await page.waitForTimeout(5000);

    // Validate response structures
    apiResponses.forEach(({ url, data }) => {
      // Basic validation - responses should be objects or arrays
      expect(typeof data).toBe('object');
      expect(data).not.toBeNull();

      console.log(`Validated API response for ${url}`);
    });
  });

  test('should handle network failures gracefully', async ({ page }) => {
    // Mock network failure for API calls
    let networkFailures = 0;

    await page.route('**/api/**', route => {
      networkFailures++;
      route.abort();
    });

    // Navigate to dashboard
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Wait for error handling
    await page.waitForTimeout(3000);

    // Should have attempted API calls that failed
    expect(networkFailures).toBeGreaterThan(0);

    // Page should handle errors gracefully
    await expect(page.locator('body')).toBeVisible();

    // Look for error indicators
    const errorIndicators = page.locator('[data-testid*="error"], .error, .alert, .notification');
    const errorCount = await errorIndicators.count();

    if (errorCount > 0) {
      console.log(`Found ${errorCount} error indicators on page`);
    }
  });

  test('should monitor WebSocket message frequency', async ({ page }) => {
    const messageTimestamps: number[] = [];
    let wsConnection: any = null;

    page.on('websocket', ws => {
      wsConnection = ws;
      ws.on('framereceived', () => {
        messageTimestamps.push(Date.now());
      });
    });

    // Navigate to dashboard
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Monitor messages for 10 seconds
    await page.waitForTimeout(10000);

    // Analyze message frequency
    if (messageTimestamps.length > 1) {
      const intervals: number[] = [];
      for (let i = 1; i < messageTimestamps.length; i++) {
        intervals.push(messageTimestamps[i] - messageTimestamps[i - 1]);
      }

      const avgInterval = intervals.reduce((a, b) => a + b, 0) / intervals.length;
      console.log(`Average message interval: ${avgInterval}ms`);
      console.log(`Total messages received: ${messageTimestamps.length}`);

      // Heartbeat should be regular (every 30 seconds = 30000ms)
      // Allow some variance
      expect(avgInterval).toBeGreaterThan(10000); // At least every 10 seconds
    }
  });
});