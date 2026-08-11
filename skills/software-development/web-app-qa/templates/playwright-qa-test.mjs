/**
 * Playwright QA Test Template
 * 
 * Usage:
 *   1. Copy this file into your project
 *   2. Set BASE to your target URL
 *   3. Define ROUTES to test
 *   4. Customize form fillers for login/auth flows
 *   5. Run: node playwright-qa-test.mjs
 * 
 * Requires: npm install playwright (or pip install playwright && playwright install chromium)
 */

import { chromium } from 'playwright';

const BASE = 'http://localhost:3099';
const ROUTES = [
  '/',
  '/login',
  '/dashboard/admin',
  '/dashboard/admin/settings',
  '/dashboard/client',
  '/dashboard/contractor',
  '/contact',
  '/careers',
];

async function run() {
  console.log('=== QA TEST ===\n');
  let pass = 0, fail = 0;

  const browser = await chromium.launch({ headless: true });

  // ── Test: Page Loads ──
  console.log('--- Page Load Tests ---');
  for (const route of ROUTES) {
    const page = await browser.newPage();
    const errors = [];
    page.on('pageerror', err => errors.push(err.message));
    page.on('requestfailed', req => errors.push(
      `Fetch: ${req.url()} - ${req.failure()?.errorText || 'unknown'}`
    ));
    page.on('console', msg => {
      if (msg.type() === 'error') errors.push(msg.text());
    });

    try {
      await page.goto(`${BASE}${route}`, { waitUntil: 'networkidle', timeout: 15000 });
      await page.waitForTimeout(2000);

      const title = await page.title();
      const status = errors.length === 0 ? '✅' : '❌';
      console.log(` ${status} ${route} — ${title}`);
      if (errors.length > 0) {
        errors.slice(0, 5).forEach(e => console.log(`    • ${e.slice(0, 200)}`));
        fail++;
      } else {
        pass++;
      }
    } catch (e) {
      console.log(` ❌ ${route} — ${e.message}`);
      fail++;
    }
    await page.close();
  }

  // ── Test: Login Flow ──
  console.log('\n--- Login Flow Tests ---');

  const LOGIN_TESTS = [
    { email: 'admin@demo.com', role: 'admin', label: 'Admin login' },
    { email: 'client@demo.com', role: 'client', label: 'Client login' },
    { email: 'contractor@demo.com', role: 'contractor', label: 'Contractor login' },
  ];

  for (const test of LOGIN_TESTS) {
    const ctx = await browser.newContext();
    const page = await ctx.newPage();
    const errors = [];
    page.on('pageerror', err => errors.push(err.message));
    page.on('requestfailed', req => errors.push(
      `Fetch: ${req.url()} - ${req.failure()?.errorText}`
    ));

    try {
      await page.goto(`${BASE}/login`, { waitUntil: 'networkidle', timeout: 15000 });
      await page.waitForTimeout(1000);

      await page.fill('input[type="email"]', test.email);
      await page.fill('input[type="password"]', 'demo123');
      await page.click('button[type="submit"]');
      await page.waitForTimeout(3000);

      const currentUrl = page.url();
      const redirected = currentUrl.includes(`/dashboard/${test.role}`);
      const ok = redirected && errors.length === 0;
      console.log(` ${ok ? '✅' : '❌'} ${test.label} — ${currentUrl}`);
      if (!ok) {
        errors.slice(0, 5).forEach(e => console.log(`    • ${e.slice(0, 200)}`));
        fail++;
      } else {
        pass++;
      }
    } catch (e) {
      console.log(` ❌ ${test.label} — ${e.message}`);
      fail++;
    }
    await ctx.close();
  }

  // ── Summary ──
  console.log(`\n========================================`);
  console.log(`RESULTS: ${pass}/${pass+fail} passed, ${fail} failed`);
  await browser.close();
  process.exit(fail > 0 ? 1 : 0);
}

run().catch(err => {
  console.error('QA test crashed:', err);
  process.exit(1);
});
