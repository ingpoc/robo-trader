import { test, expect } from '@playwright/test';

test.describe('Agents Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('http://localhost:3000/agents');
  });

  test('should load agents page', async ({ page }) => {
    await expect(page).toHaveTitle(/Robo Trader/);
    await expect(page.locator('h1')).toContainText('AI Agents');
  });

  test('should display agent status dashboard', async ({ page }) => {
    const agentCards = page.locator('[data-testid="agent-card"]');
    await expect(agentCards).toHaveCount.greaterThan(0);
  });

  test('should show Claude agent status', async ({ page }) => {
    const claudeAgent = page.locator('[data-testid="claude-agent"]');
    await expect(claudeAgent).toBeVisible();
    await expect(claudeAgent).toContainText('Claude Agent');
  });

  test('should display task queue status', async ({ page }) => {
    const taskQueue = page.locator('[data-testid="task-queue"]');
    await expect(taskQueue).toBeVisible();
  });

  test('should show recommendation approvals section', async ({ page }) => {
    const approvals = page.locator('[data-testid="recommendations"]');
    await expect(approvals).toBeVisible();
  });

  test('should have agent configuration panel', async ({ page }) => {
    const config = page.locator('[data-testid="agent-config"]');
    await expect(config).toBeVisible();
  });
});