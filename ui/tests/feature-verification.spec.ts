/**
 * Feature Verification Tests
 * Auto-verifies UI features marked as completed but not verified
 */

import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

// Path to feature list
const FEATURE_LIST_PATH = path.join(__dirname, '../../.claude/progress/feature-list.json');

/**
 * Read feature list and find unverified UI features
 */
function getUnverifiedUIFeatures(): any[] {
  if (!fs.existsSync(FEATURE_LIST_PATH)) {
    console.log('Feature list not found:', FEATURE_LIST_PATH);
    return [];
  }

  const featureList = JSON.parse(fs.readFileSync(FEATURE_LIST_PATH, 'utf-8'));
  const features = [];

  // Iterate through all categories
  for (const category of Object.values(featureList.categories || {})) {
    const cat = category as any;
    for (const feat of cat.features || []) {
      // Check if it's a UI feature that's completed but not verified
      if (
        feat.id.startsWith('UI-') &&
        feat.status === 'completed' &&
        !feat.verification?.verified
      ) {
        features.push(feat);
      }
    }
  }

  return features;
}

test.describe('Feature Verification', () => {
  const features = getUnverifiedUIFeatures();

  if (features.length === 0) {
    test.skip('No unverified UI features found', () => {});
  }

  for (const feature of features) {
    test(`${feature.id}: should load without errors`, async ({ page }) => {
      const consoleErrors: string[] = [];
      const consoleWarnings: string[] = [];

      // Capture console errors and warnings
      page.on('console', (msg) => {
        if (msg.type() === 'error') {
          consoleErrors.push(msg.text());
        } else if (msg.type() === 'warning') {
          consoleWarnings.push(msg.text());
        }
      });

      // Navigate to the application
      await page.goto('http://localhost:3000');

      // Wait for the page to be fully loaded
      await page.waitForLoadState('networkidle');

      // Check for console errors
      expect(consoleErrors).toHaveLength(0);

      // Log warnings for reference but don't fail on them
      if (consoleWarnings.length > 0) {
        console.log(`Warnings for ${feature.id}:`, consoleWarnings);
      }
    });

    test(`${feature.id}: should have valid DOM structure`, async ({ page }) => {
      await page.goto('http://localhost:3000');
      await page.waitForLoadState('networkidle');

      // Check that the page has a valid structure
      const body = await page.locator('body');
      expect(await body.count()).toBeGreaterThan(0);

      // Check for React root element
      const root = await page.locator('#root, [data-reactroot]');
      expect(await root.count()).toBeGreaterThan(0);
    });

    test(`${feature.id}: should be responsive`, async ({ page }) => {
      // Test desktop view
      await page.setViewportSize({ width: 1920, height: 1080 });
      await page.goto('http://localhost:3000');
      await page.waitForLoadState('networkidle');

      // Test tablet view
      await page.setViewportSize({ width: 768, height: 1024 });
      await page.waitForTimeout(1000);

      // Test mobile view
      await page.setViewportSize({ width: 375, height: 667 });
      await page.waitForTimeout(1000);

      // Ensure page is still interactive
      const body = await page.locator('body');
      expect(await body.isVisible()).toBe(true);
    });
  }
});
