import { test, expect } from '@playwright/test';

test.describe('Dashboard Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('http://localhost:3000');
  });

  test('should load dashboard page', async ({ page }) => {
    await expect(page).toHaveTitle(/Robo Trader/);
    await expect(page.locator('h1')).toContainText('Dashboard');
  });

  test('should display metric cards', async ({ page }) => {
    // Check for metric cards
    const metricCards = page.locator('[data-testid="metric-card"]');
    await expect(metricCards).toHaveCount(4);
  });

  test('should display portfolio chart', async ({ page }) => {
    const chart = page.locator('[data-testid="portfolio-chart"]');
    await expect(chart).toBeVisible();
  });

  test('should display holdings table', async ({ page }) => {
    const holdingsTable = page.locator('[data-testid="holdings-table"]');
    await expect(holdingsTable).toBeVisible();
  });

  test('should display AI insights panel', async ({ page }) => {
    const aiInsights = page.locator('[data-testid="ai-insights"]');
    await expect(aiInsights).toBeVisible();
  });

  test('should have quick trade form', async ({ page }) => {
    const quickTradeForm = page.locator('[data-testid="quick-trade-form"]');
    await expect(quickTradeForm).toBeVisible();
  });

  test('should navigate to agents page', async ({ page }) => {
    await page.click('text=Agents');
    await expect(page).toHaveURL(/.*agents/);
  });

  test('should navigate to trading page', async ({ page }) => {
    await page.click('text=Trading');
    await expect(page).toHaveURL(/.*trading/);
  });

  test('should navigate to paper trading page', async ({ page }) => {
    await page.click('text=Paper Trading');
    await expect(page).toHaveURL(/.*paper-trading/);
  });
});