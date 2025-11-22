import { chromium } from 'playwright';

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();

  try {
    console.log('🔍 Navigating to http://localhost:3000...');
    await page.goto('http://localhost:3000');

    console.log('⏳ Waiting for app to load (3 seconds)...');
    await page.waitForTimeout(3000);

    console.log('\n📸 Taking screenshot of dashboard...');
    await page.screenshot({ path: '/tmp/01_dashboard.png', fullPage: true });

    // Look for Claude icon
    console.log('\n🔎 Looking for Claude images on page...');
    const allImages = await page.locator('img').all();
    console.log(`  Total images found: ${allImages.length}`);

    let claudeIconFound = false;
    for (let i = 0; i < allImages.length; i++) {
      const img = allImages[i];
      const src = await img.getAttribute('src');
      const alt = await img.getAttribute('alt');
      const cls = await img.getAttribute('class');

      if (alt && (alt.includes('Claude') || alt.toLowerCase().includes('claude'))) {
        console.log(`\n  ✓ Found Claude-related image:`);
        console.log(`    alt: "${alt}"`);
        console.log(`    class: "${cls}"`);
        console.log(`    Has animate-pulse: ${cls && cls.includes('animate-pulse') ? '✅ YES' : '❌ NO'}`);
        claudeIconFound = true;
      }
    }

    if (!claudeIconFound) {
      console.log('\n  ❌ No Claude-related images found!');
    }

    // Check for any animate-pulse elements
    console.log('\n🎬 Checking for animate-pulse animations...');
    const pulseElements = await page.locator('[class*="animate-pulse"]').all();
    console.log(`  Found ${pulseElements.length} elements with animate-pulse`);

    if (pulseElements.length > 0) {
      for (let i = 0; i < Math.min(3, pulseElements.length); i++) {
        const elem = pulseElements[i];
        const tagName = await elem.evaluate(e => e.tagName);
        const cls = await elem.getAttribute('class');
        console.log(`    [${i+1}] <${tagName}> class="${cls}"`);
      }
    }

    // Check page HTML for Claude status
    console.log('\n📊 Checking page content...');
    const html = await page.content();
    const hasAnalyzing = html.includes('analyzing');
    const hasClaudeIcon = html.includes('Claude_online');
    console.log(`  Contains "analyzing": ${hasAnalyzing ? '✅' : '❌'}`);
    console.log(`  Contains "Claude_online": ${hasClaudeIcon ? '✅' : '❌'}`);

    // Try to locate the sidebar where Claude icon should be
    console.log('\n🔍 Looking in sidebar for Claude icon...');
    const sidebar = await page.locator('aside').first();
    const sidebarExists = await sidebar.isVisible().catch(() => false);
    console.log(`  Sidebar found: ${sidebarExists ? '✅' : '❌'}`);

    if (sidebarExists) {
      const sidebarImages = await sidebar.locator('img').all();
      console.log(`  Images in sidebar: ${sidebarImages.length}`);

      for (let img of sidebarImages) {
        const alt = await img.getAttribute('alt');
        const cls = await img.getAttribute('class');
        if (alt && alt.includes('Claude')) {
          console.log(`    ✓ Claude icon found in sidebar!`);
          console.log(`      class: "${cls}"`);
          console.log(`      animate-pulse: ${cls && cls.includes('animate-pulse') ? '✅' : '❌'}`);
        }
      }
    }

    console.log('\n✅ Test complete! Screenshot saved to /tmp/01_dashboard.png');

  } catch (error) {
    console.error('❌ Error during test:', error.message);
  } finally {
    await browser.close();
  }
})();
