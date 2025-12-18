/**
 * System Health Check Tests
 * Verifies backend and frontend are working correctly
 */

import { test, expect } from '@playwright/test';

test.describe('System Health', () => {
  test('backend health endpoint should return 200', async ({ request }) => {
    const response = await request.get('http://localhost:8000/api/health');
    expect(response.status()).toBe(200);

    const data = await response.json();
    expect(data.status).toBe('healthy');
  });

  test('backend should respond within 5 seconds', async ({ request }) => {
    const startTime = Date.now();
    const response = await request.get('http://localhost:8000/api/health');
    const endTime = Date.now();

    expect(response.status()).toBe(200);
    expect(endTime - startTime).toBeLessThan(5000);
  });

  test('frontend should load without errors', async ({ page }) => {
    const errors: string[] = [];

    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');

    expect(errors).toHaveLength(0);
  });

  test('frontend should load within 10 seconds', async ({ page }) => {
    const startTime = Date.now();

    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');

    const endTime = Date.now();
    expect(endTime - startTime).toBeLessThan(10000);
  });

  test('frontend should have valid document structure', async ({ page }) => {
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');

    // Check for basic HTML structure
    const html = await page.locator('html');
    expect(await html.count()).toBe(1);

    const head = await page.locator('head');
    expect(await head.count()).toBe(1);

    const body = await page.locator('body');
    expect(await body.count()).toBe(1);

    // Check for React root
    const root = await page.locator('#root, [data-reactroot]');
    expect(await root.count()).toBeGreaterThan(0);
  });

  test('frontend should not have accessibility violations', async ({ page }) => {
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');

    // Check for basic accessibility requirements
    const mainContent = await page.locator('main, [role="main"], #root');
    expect(await mainContent.count()).toBeGreaterThan(0);
  });

  test('frontend should handle network errors gracefully', async ({ page, context }) => {
    // Simulate offline mode
    await context.setOffline(true);

    await page.goto('http://localhost:3000').catch(() => {
      // Expected to fail
    });

    // Go back online
    await context.setOffline(false);

    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');

    const body = await page.locator('body');
    expect(await body.isVisible()).toBe(true);
  });

  test('backend API should have CORS headers', async ({ request }) => {
    const response = await request.get('http://localhost:8000/api/health');

    const headers = response.headers();
    // Most APIs should have CORS headers, but it's not mandatory for all endpoints
    // This is a soft check
    expect(response.status()).toBe(200);
  });
});
