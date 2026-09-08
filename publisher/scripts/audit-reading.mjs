// Optional, local-only reading stress test. Not a native screen-reader test.
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const { chromium } = require('playwright');
const browser = await chromium.launch({ channel: 'chrome', headless: true });
const routes = ['/', '/courses/smartphone-basics/week-01', '/readiness', '/legal/privacy', '/legal/terms', '/support'];
const results = [];
try {
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  const cdp = await page.context().newCDPSession(page);
  await cdp.send('Accessibility.enable');
  for (const route of routes) {
    await page.goto('http://127.0.0.1:3010' + route, { waitUntil: 'networkidle' });
    const ax = await cdp.send('Accessibility.getFullAXTree');
    const exposed = ax.nodes.filter(n => !n.ignored);
    const headings = exposed.filter(n => n.role?.value === 'heading');
    const links = exposed.filter(n => n.role?.value === 'link');
    const mainCount = exposed.filter(n => n.role?.value === 'main').length;
    const language = await page.locator('html').getAttribute('lang');
    // Snapshot all computed sizes before changing anything: prevents cascading multiplication.
    const enlarged = await page.evaluate(() => {
      const sizes = [...document.querySelectorAll('body, body *')].map(el => [el, parseFloat(getComputedStyle(el).fontSize)]);
      const before = document.body.innerText;
      for (const [el, px] of sizes) el.style.fontSize = `${px * 2}px`;
      return { textPreserved: before === document.body.innerText, overflow: document.documentElement.scrollWidth > innerWidth };
    });
    results.push({ route, language, mainCount, headingCount: headings.length,
      unnamedLinks: links.filter(n => !n.name?.value?.trim()).length,
      text200: enlarged });
  }
  console.log(JSON.stringify({ method: 'computed font-size doubled at 1280 CSS px; Chrome AX tree', results }, null, 2));
  if (results.some(r => r.language !== 'ko' || r.mainCount !== 1 || r.unnamedLinks || r.text200.overflow || !r.text200.textPreserved)) process.exitCode = 1;
} finally { await browser.close(); }
