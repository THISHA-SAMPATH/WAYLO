import puppeteer from 'puppeteer';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, '..');
const docsDir = path.join(projectRoot, 'docs');

if (!fs.existsSync(docsDir)) {
  fs.mkdirSync(docsDir, { recursive: true });
}

async function run() {
  console.log('Launching Puppeteer Chrome...');
  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--enable-webgl', '--ignore-gpu-blocklist']
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900, deviceScaleFactor: 1.5 });

  page.on('console', msg => {
    console.log(`[BROWSER CONSOLE ${msg.type()}]:`, msg.text());
  });

  page.on('pageerror', err => {
    console.error('[BROWSER RUNTIME ERROR]:', err);
  });

  console.log('Navigating to http://localhost:8000...');
  await page.goto('http://localhost:8000', { waitUntil: 'networkidle0', timeout: 30000 });

  // 1. Hero Screenshot
  console.log('Waiting for Hero & Stat Strip...');
  await page.waitForSelector('h1', { timeout: 10000 });
  await page.waitForFunction(() => document.body.innerText.includes('2.9%') || document.body.innerText.includes('WAYLO'));

  // Wait extra 2 seconds for Three.js animations / stats to settle
  await new Promise(r => setTimeout(r, 2000));

  const heroPath = path.join(docsDir, 'hero_demo.png');
  await page.screenshot({ path: heroPath, fullPage: false });
  console.log(`Saved hero screenshot to: ${heroPath}`);

  // 2. 3D Live Demo Screenshot
  console.log('Scrolling to 3D Live Demo...');
  const demoSection = await page.$('#demo');
  if (demoSection) {
    await demoSection.scrollIntoView();
    await new Promise(r => setTimeout(r, 2500));
    const demoPath = path.join(docsDir, 'live_3d_demo.png');
    await page.screenshot({ path: demoPath, fullPage: false });
    console.log(`Saved 3D live demo screenshot to: ${demoPath}`);
  }

  // 3. Evidence Page Screenshot
  console.log('Clicking Evidence (N=1000) tab...');
  const buttons = await page.$$('button');
  let evidenceBtn = null;
  for (const btn of buttons) {
    const text = await page.evaluate(el => el.innerText, btn);
    if (text.includes('Evidence (N=1000)')) {
      evidenceBtn = btn;
      break;
    }
  }

  if (evidenceBtn) {
    await evidenceBtn.click();
    await new Promise(r => setTimeout(r, 2000));
    await page.waitForFunction(() => document.body.innerText.includes('Doorway Passage & Collision Table'));
    const evidencePath = path.join(docsDir, 'evidence_page.png');
    await page.screenshot({ path: evidencePath, fullPage: false });
    console.log(`Saved evidence page screenshot to: ${evidencePath}`);
  }

  await browser.close();
  console.log('Screenshot capture process completed successfully!');
}

run().catch(err => {
  console.error('Screenshot capture failed:', err);
  process.exit(1);
});
