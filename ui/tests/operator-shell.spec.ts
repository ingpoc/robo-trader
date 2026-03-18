import { expect, test } from '@playwright/test'

test.describe('Operator Shell', () => {
  test('loads the app shell and primary navigation', async ({ page }) => {
    await page.goto('/')

    await expect(page).toHaveTitle(/Robo Trader/i)
    await expect(page.getByRole('navigation', { name: 'Main navigation' })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Overview' })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Paper Trading' })).toBeVisible()
    await expect(page.getByRole('link', { name: 'System Health' })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Configuration' })).toBeVisible()
  })

  test('navigates across the four mission-aligned routes', async ({ page }) => {
    await page.goto('/')

    await page.getByRole('link', { name: 'Paper Trading' }).click()
    await expect(page).toHaveURL(/\/paper-trading$/)
    await expect(page.getByText('Paper Trading')).toBeVisible()

    await page.getByRole('link', { name: 'System Health' }).click()
    await expect(page).toHaveURL(/\/system-health$/)
    await expect(page.getByText('System Health')).toBeVisible()

    await page.getByRole('link', { name: 'Configuration' }).click()
    await expect(page).toHaveURL(/\/configuration$/)
    await expect(page.getByText('Configuration')).toBeVisible()

    await page.getByRole('link', { name: 'Overview' }).click()
    await expect(page).toHaveURL(/\/$/)
    await expect(page.getByText('Overview')).toBeVisible()
  })

  test('does not expose removed top-level routes in the navigation', async ({ page }) => {
    await page.goto('/')

    await expect(page.getByRole('link', { name: 'News & Earnings' })).toHaveCount(0)
    await expect(page.getByRole('link', { name: 'AI Transparency' })).toHaveCount(0)
    await expect(page.getByRole('link', { name: 'Agents' })).toHaveCount(0)
  })
})
