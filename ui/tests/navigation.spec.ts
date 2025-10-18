import { test, expect } from '@playwright/test';

const pages = [
  { name: 'Dashboard', path: '/', title: /dashboard|Dashboard/i },
  { name: 'News & Earnings', path: '/news-earnings', title: /news|earnings|News|Earnings/i },
  { name: 'Agents', path: '/agents', title: /agents|Agents/i },
  { name: 'Trading', path: '/trading', title: /trading|Trading/i },
  { name: 'Config', path: '/config', title: /config|Config/i },
  { name: 'Agent Config', path: '/agent-config', title: /agent.*config|Agent.*Config/i },
  { name: 'Logs', path: '/logs', title: /logs|Logs/i }
];

test.describe('Page Navigation and Component Loading', () => {
  test.beforeEach(async ({ page }) => {
    // Clear any existing state
    await page.context().clearCookies();
    await page.context().clearPermissions();
  });

  pages.forEach(pageConfig => {
    test(`should load ${pageConfig.name} page correctly`, async ({ page }) => {
      const errors: string[] = [];
      const warnings: string[] = [];

      // Listen for console messages
      page.on('console', msg => {
        if (msg.type() === 'error') {
          errors.push(msg.text());
        } else if (msg.type() === 'warning') {
          warnings.push(msg.text());
        }
      });

      // Listen for page errors
      page.on('pageerror', error => {
        errors.push(`Page error: ${error.message}`);
      });

      try {
        // Navigate to the page
        await page.goto(pageConfig.path);
        await page.waitForLoadState('networkidle');

        // Check URL
        await expect(page).toHaveURL(new RegExp(pageConfig.path.replace('/', '\\/') + '$'));

        // Check for page title or main heading
        const titleElement = page.locator('h1, h2, h3').filter({ hasText: pageConfig.title });
        await expect(titleElement.first()).toBeVisible();

        // Check for main content area
        const mainContent = page.locator('main, [role="main"], .main-content, #main');
        if (await mainContent.count() > 0) {
          await expect(mainContent.first()).toBeVisible();
        }

        // Check for common components that should be present (but may be hidden on mobile)
        // Note: Some pages may not have all common components, so we don't enforce strict requirements
        const commonComponents = [
          'nav, [role="navigation"]', // Navigation
          'header, [role="banner"]', // Header
          'footer, [role="contentinfo"]' // Footer
        ];

        let foundComponents = 0;
        for (const selector of commonComponents) {
          const elements = page.locator(selector);
          if (await elements.count() > 0) {
            foundComponents++;
          }
        }

        // At least one common component should exist (navigation is most essential)
        expect(foundComponents).toBeGreaterThan(0);

        // Wait for any async content to load
        await page.waitForTimeout(2000);

        // Check for loading states or skeleton loaders
        const loadingElements = page.locator('[data-testid*="loading"], .loading, .skeleton, [aria-busy="true"]');
        if (await loadingElements.count() > 0) {
          // If loading elements are present, they should eventually disappear
          await expect(loadingElements.first()).toBeHidden({ timeout: 10000 });
        }

        // Check for error boundaries or error messages
        const errorElements = page.locator('[data-testid*="error"], .error, .alert, [role="alert"]');
        if (await errorElements.count() > 0) {
          // Log errors but don't fail the test - errors might be expected in some cases
          console.log(`${pageConfig.name} page has error elements:`, await errorElements.allTextContents());
        }

        // Verify no critical rendering issues (page should not be blank)
        const bodyContent = await page.locator('body').textContent();
        expect(bodyContent?.trim()).not.toBe('');

        // Check for WebSocket connection if applicable
        const wsConnections: string[] = [];
        page.on('websocket', ws => {
          wsConnections.push(ws.url());
        });
        await page.waitForTimeout(1000); // Brief wait for WS connection

        // Summary for this page
        console.log(`${pageConfig.name} Page Summary:`);
        console.log(`- URL: ${page.url()}`);
        console.log(`- Console Errors: ${errors.length}`);
        console.log(`- Console Warnings: ${warnings.length}`);
        console.log(`- WebSocket Connections: ${wsConnections.length}`);
        console.log(`- Has Error Elements: ${await errorElements.count() > 0}`);
        console.log(`- Has Loading Elements: ${await loadingElements.count() > 0}`);

        // Log console errors but don't fail test for warnings (which are acceptable)
        // Only fail on actual JavaScript errors, not React warnings
        const actualErrors = errors.filter(error =>
          !error.includes('Warning:') &&
          !error.includes('Each child in a list should have a unique "key" prop')
        );

        if (actualErrors.length > 0) {
          console.log('Actual Console Errors:', actualErrors);
          expect(actualErrors.length).toBe(0);
        }

      } catch (error) {
        console.error(`Error testing ${pageConfig.name} page:`, error);
        throw error;
      }
    });
  });
});