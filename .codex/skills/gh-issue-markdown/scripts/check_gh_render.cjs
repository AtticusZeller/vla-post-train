// Check that a GitHub issue, pull request, or comment page renders its math and images.
//
// GitHub renders math in the browser, so only a real page load shows MathJax errors such as
// "Missing \end{cases}" or "macros are not allowed". The math chunk loads lazily and a headless
// load sometimes leaves every formula raw, so a load with raw formulas is retried before failing.
//
// Usage: NODE_PATH=<dir>/node_modules node check_gh_render.cjs <url> [--shots <dir>] [--chrome <path>]
//        [--skip-math]
// <url> may be a file:// preview from `gh api markdown`; pass --skip-math there, since only a real
// GitHub page runs MathJax. Exit code 0 means every formula rendered, every image in the rendered
// Markdown loaded, and no error text was found.

const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright-core');

const ERROR_TEXT = /(Missing [^\n]{0,60}|Undefined control sequence[^\n]{0,60}|macros are not allowed[^\n]{0,60}|Misplaced [^\n]{0,60}|Extra [}\\][^\n]{0,60}|Math input error[^\n]{0,60}|Unable to render[^\n]{0,60})/g;
const CHROME_CANDIDATES = ['/usr/bin/google-chrome', '/opt/pw-browsers/chromium', '/usr/bin/chromium', '/usr/bin/chromium-browser'];

function parseArgs(argv) {
  const args = { url: null, shots: null, chrome: null, attempts: 3, skipMath: false };
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--shots') args.shots = argv[++i];
    else if (argv[i] === '--chrome') args.chrome = argv[++i];
    else if (argv[i] === '--attempts') args.attempts = Number(argv[++i]);
    else if (argv[i] === '--skip-math') args.skipMath = true;
    else args.url = argv[i];
  }
  if (!args.url) throw new Error('usage: check_gh_render.cjs <url> [--shots <dir>] [--chrome <path>]');
  args.chrome = args.chrome || CHROME_CANDIDATES.find(p => fs.existsSync(p));
  if (!args.chrome) throw new Error('no Chrome found; pass --chrome <path>');
  return args;
}

async function inspect(page) {
  return page.evaluate((src) => {
    const re = new RegExp(src, 'g');
    const maths = [...document.querySelectorAll('math-renderer')];
    const raw = maths.filter(e => /^\$/.test(e.textContent.trim()));
    const mermaid = [...document.querySelectorAll('[data-type="mermaid"], .js-render-enrichment-target')];
    const images = [...document.querySelectorAll('.markdown-body img, [data-testid="issue-body"] img, body > img, p img')]
      .filter((e, i, all) => all.indexOf(e) === i && !e.closest('[data-testid="github-avatar"], .avatar'));
    const broken = images.filter(e => !e.complete || e.naturalWidth === 0);
    return {
      math_total: maths.length,
      math_raw: raw.length,
      raw_samples: raw.slice(0, 5).map(e => e.textContent.trim().slice(0, 100)),
      mermaid_blocks: mermaid.length,
      images_total: images.length,
      images_broken: broken.map(e => e.getAttribute('data-canonical-src') || e.src),
      errors: document.body.innerText.match(re) || [],
    };
  }, ERROR_TEXT.source);
}

// Images below the fold load lazily; scroll through the page so each one gets a chance to load.
async function loadLazyContent(page) {
  const height = await page.evaluate(() => document.body.scrollHeight);
  for (let y = 0; y < height; y += 1000) {
    await page.evaluate(top => window.scrollTo(0, top), y);
    await page.waitForTimeout(300);
  }
  await page.evaluate(() => Promise.all([...document.images].map(img => img.decode().catch(() => {}))));
  await page.evaluate(() => window.scrollTo(0, 0));
}

async function screenshotSections(page, dir) {
  fs.mkdirSync(dir, { recursive: true });
  const headings = await page.$$('.markdown-body h2, .markdown-body h3, [data-testid="issue-body"] h2, [data-testid="issue-body"] h3');
  for (let i = 0; i < headings.length; i++) {
    await headings[i].scrollIntoViewIfNeeded();
    await page.waitForTimeout(800);
    await page.screenshot({ path: path.join(dir, `section-${String(i).padStart(2, '0')}.png`) });
  }
  return headings.length;
}

(async () => {
  const args = parseArgs(process.argv.slice(2));
  const browser = await chromium.launch({ executablePath: args.chrome, args: ['--headless=new'] });
  let report = null;
  try {
    for (let attempt = 1; attempt <= args.attempts; attempt++) {
      const page = await browser.newPage({ viewport: { width: 1100, height: 1400 } });
      await page.goto(args.url, { waitUntil: 'load', timeout: 60000 });
      await page.waitForTimeout(12000);
      await loadLazyContent(page);
      report = { attempt, ...(await inspect(page)) };
      if (args.skipMath) { report.math_raw = 0; report.raw_samples = []; report.math_skipped = true; }
      if (report.math_raw === 0 || attempt === args.attempts) {
        if (args.shots) report.screenshots = await screenshotSections(page, args.shots);
        break;
      }
      await page.close();
    }
  } finally {
    await browser.close();
  }
  console.log(JSON.stringify(report, null, 1));
  const ok = report.math_raw === 0 && report.errors.length === 0 && report.images_broken.length === 0;
  process.exit(ok ? 0 : 1);
})().catch(e => { console.error(e.message); process.exit(2); });
