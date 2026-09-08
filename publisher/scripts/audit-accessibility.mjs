// Optional audit tooling: requires playwright and axe-core in the Node environment.
// Does not change the served application or user data.
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const { chromium } = require('playwright');
const base = process.env.PUBLISHER_AUDIT_URL || 'http://127.0.0.1:3010';
if (!['127.0.0.1', 'localhost'].includes(new URL(base).hostname)) throw Error('Local audit only');
const browser = await chromium.launch({ channel: 'chrome', headless: true });
const results = [];
try {
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', error => errors.push(error.name));
  for (const width of [320, 375, 768, 1280]) {
    await page.setViewportSize({ width, height: 900 });
    for (const route of ['/', '/courses/smartphone-basics/week-01', '/readiness', '/legal/privacy', '/legal/terms', '/support']) {
      await page.goto(base + route, { waitUntil: 'networkidle' });
      await page.addScriptTag({ path: require.resolve('axe-core/axe.min.js') });
      const audit = await page.evaluate(async () => {
        const axeResult = await window.axe.run(document, { runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21aa'] } });
        return {
          overflow: document.documentElement.scrollWidth > innerWidth,
          violations: axeResult.violations.map(v => ({ id: v.id, impact: v.impact, count: v.nodes.length })),
          smallTargets: [...document.querySelectorAll('.brand,.card-link,.back-link,.site-footer a')].filter(el => {
            const r = el.getBoundingClientRect(); return r.width < 44 || r.height < 44;
          }).map(el => el.textContent.trim()),
        };
      });
      results.push({ width, route, ...audit });
    }
  }
  await page.goto(base, { waitUntil: 'networkidle' });
  await page.keyboard.press('Tab');
  const firstFocus = await page.locator(':focus').textContent();
  await page.keyboard.press('Enter');
  const skipTarget = await page.evaluate(() => document.activeElement.id);
  console.log(JSON.stringify({ results, keyboard: { firstFocus, skipTarget }, pageErrors: errors }, null, 2));
  if (errors.length || results.some(r => r.overflow || r.violations.length || r.smallTargets.length)) process.exitCode = 1;
} finally { await browser.close(); }
