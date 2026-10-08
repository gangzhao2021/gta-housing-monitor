/* Browser regression for the published static site (site/dist).
   Run: npm run test:site   (needs `npm install` and `npx playwright install chromium`).
   Expected values are derived from data.json, so monthly refreshes do not break the test. */
const assert = require('node:assert/strict');
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require('playwright');

const dist = path.resolve(__dirname, '../site/dist');
const mime = {'.html':'text/html', '.js':'text/javascript', '.css':'text/css', '.json':'application/json', '.svg':'image/svg+xml'};

function serve() {
  const server = http.createServer((req, res) => {
    const filename = req.url === '/' ? 'index.html' : req.url.slice(1).split('?')[0];
    if (!['index.html','app.js','styles.css','data.json','favicon.svg'].includes(filename)) { res.writeHead(404).end(); return; }
    res.setHeader('Content-Type', mime[path.extname(filename)]);
    fs.createReadStream(path.join(dist, filename)).pipe(res);
  });
  return new Promise(resolve => server.listen(0, '127.0.0.1', () => resolve(server)));
}

// Every page, tab and option the site offers; rendering each must not throw.
const COMBOS = (() => {
  const out = [];
  for (const lang of ['zh','en']) {
    for (const marketView of ['level','mom','yoy']) out.push({lang, page:'market', marketView});
    for (const rentMode of ['monthly','lease','annual','region'])
      for (const regionFrequency of ['monthly','annual'])
        for (const measureType of ['apartment','townhouse'])
          for (const measureRoom of ['studio','1br','2br','3br'])
            for (const leaseType of ['condo','townhouse'])
              out.push({lang, page:'rent', rentMode, regionFrequency, measureType, measureRoom, leaseType});
    for (const econRange of ['1','2','5','all']) out.push({lang, page:'economy', econRange});
    for (const down of ['10','20','35']) for (const years of ['25','30']) out.push({lang, page:'mortgage', down, years});
  }
  return out;
})();

async function open(page, name) {
  await page.locator(`[data-page="${name}"]`).click();
}

async function main() {
  assert.ok(fs.existsSync(path.join(dist, 'data.json')), 'Generate site/dist/data.json before browser testing');
  const server = await serve();
  let browser;
  try {
    browser = await chromium.launch({headless:true});
    const page = await browser.newPage({viewport:{width:1440,height:900}});
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
    await page.goto(`http://127.0.0.1:${server.address().port}`);
    await page.locator('.price-panel .chart').waitFor();

    // 1. Every combination renders.
    const failures = await page.evaluate(combos => {
      const bad = [];
      for (const combo of combos) {
        Object.assign(state, combo);
        try { render(); } catch (error) { bad.push(`${JSON.stringify(combo)} ${error}`); }
      }
      Object.assign(state, JSON.parse(JSON.stringify(initialState)), {lang:'zh'});
      render();
      return bad;
    }, COMBOS);
    assert.deepEqual(failures, [], 'page combinations failed to render');

    // 2. No horizontal page scroll on any page, in either language, at desktop and phone widths.
    for (const width of [1440, 390, 320]) {
      await page.setViewportSize({width, height:900});
      for (const lang of ['zh','en']) {
        await page.locator(`[data-lang="${lang}"]`).click();
        for (const name of ['market','rent','economy','mortgage']) {
          await open(page, name);
          const overflow = await page.evaluate(() => document.documentElement.scrollWidth - innerWidth);
          assert.ok(overflow <= 0, `${width}px ${lang} ${name}: page scrolls sideways by ${overflow}px`);
          if (width === 320) {  // an open help bubble must stay on screen too
            const info = page.locator('details.info').first();
            if (await info.count()) {
              await info.evaluate(el => { el.open = true; });
              const bubble = await page.evaluate(() => document.querySelector('details.info[open] .bubble').getBoundingClientRect().right - innerWidth);
              assert.ok(bubble <= 0, `${lang} ${name}: help bubble runs ${bubble}px off screen`);
              await info.evaluate(el => { el.open = false; });
            }
          }
        }
      }
    }
    await page.setViewportSize({width:1440, height:900});
    await page.locator('[data-lang="zh"]').click();

    // 3. Overview.
    await open(page, 'market');
    assert.equal(await page.locator('.overview-hero .metric').count(), 1);
    assert.equal(await page.locator('.kpi-strip .metric').count(), 4, 'sales, new listings, active listings, months of inventory');
    const marker = Number(await page.locator('.gauge-marker').getAttribute('data-left'));
    assert.ok(marker >= 0 && marker <= 100, 'gauge marker off the scale');
    assert.match(await page.locator('.temp-card p').textContent(), /近三个月/, 'temperature figures must say they are three-month values');
    assert.equal(await page.locator('.price-panel .hpi-annotation').count(), 1, 'HPI rebase tag missing');
    assert.match(await page.locator('.price-panel .note').textContent(), /341\.7.*320\.0/);
    assert.equal(await page.locator('.price-comparison').count(), 0, 'dual-axis study was removed');
    assert.equal(await page.locator('[data-supply]').count(), 0, 'monthly SNLR chart was removed');
    assert.equal(await page.locator('.long-run .series-line').count() >= 1, true, 'long-run chart missing');
    assert.match(await page.locator('.long-run-stats').textContent(), /高点.*%/);
    await page.locator('[data-pick="marketView"][data-value="mom"]').click();
    assert.equal(await page.locator('.price-panel .hpi-annotation').count(), 0, 'level annotation must not use a transformed axis');
    assert.equal(await page.evaluate(() => comparisonValue('trreb_hpi_benchmark','2025-04','mom')), null, 'HPI break must not become a growth number');
    await page.locator('[data-pick="marketView"][data-value="yoy"]').click();
    assert.equal(await page.evaluate(() => comparisonValue('trreb_hpi_benchmark','2026-03','yoy') === value('trreb_hpi_benchmark_yoy_published','2026-03')), true,
      'YoY must use the TRREB published figure');
    await page.locator('[data-pick="marketView"][data-value="level"]').click();
    await page.locator('.price-panel .chart-hit').focus();
    await page.keyboard.press('ArrowLeft');
    assert.equal(await page.locator('.price-panel .chart-tooltip').isVisible(), true, 'keyboard tooltip');
    const outcomes = await page.locator('.outcome-row').count();
    assert.equal(outcomes, 3);
    assert.equal(await page.locator('.outcome-row.current').count(), 1);
    // Help bubbles: one open at a time; an outside click or Escape closes them.
    const infos = page.locator('details.info > summary');
    await infos.nth(0).click();
    assert.equal(await page.locator('details.info[open]').count(), 1);
    await page.locator('.kpi-strip details.info > summary').last().click();  // not covered by the first bubble
    assert.equal(await page.locator('details.info[open]').count(), 1, 'opening a bubble closes the other');
    await page.locator('h1').click();
    assert.equal(await page.locator('details.info[open]').count(), 0, 'outside click closes the bubble');
    await infos.nth(0).click();
    await page.keyboard.press('Escape');
    assert.equal(await page.locator('details.info[open]').count(), 0, 'Escape closes the bubble');
    // Regions panel: collapsed by default, map opens the district detail.
    assert.equal(await page.locator('#regions-panel').getAttribute('open'), null);
    await page.locator('#regions-panel > summary').click();
    const shapes = await page.locator('.municipal-shape').count();
    assert.ok(shapes >= 1, 'municipal map missing');
    assert.equal(await page.locator('.municipal-table tbody tr').count(), shapes);
    const markham = page.locator('[data-map-csd="Markham"]');
    await markham.focus();
    await page.keyboard.press('Enter');
    assert.equal(await page.locator('#regions-panel').getAttribute('open'), '');
    assert.equal(await page.locator('[data-state="districtRegion"]').inputValue(), 'Markham');

    // 4. Rental market.
    await open(page, 'rent');
    assert.equal(await page.locator('.measure').count(), 4, 'apartment measures');
    await page.locator('[data-pick="measureRoom"][data-value="studio"]').click();
    assert.match(await page.locator('.measure').first().textContent(), /没有这一房型/, 'asking rents have no studio category');
    await page.locator('[data-pick="measureRoom"][data-value="3br"]').click();
    assert.match(await page.locator('.measure').nth(2).textContent(), /三卧及以上/, 'CMHC 3+ must be labelled');
    await page.locator('[data-pick="measureType"][data-value="townhouse"]').click();
    assert.equal(await page.locator('.measure').count(), 2, 'townhouse measures');
    assert.equal(await page.locator('.measure.missing').count(), 0, 'three-bedroom townhouses have both measures');
    await page.locator('[data-mode="lease"]').click();
    await page.locator('[data-pick="leaseType"][data-value="townhouse"]').click();
    assert.equal(await page.locator('.supply-stat').count(), 3, 'townhouse leases: one to three bedrooms');
    await page.locator('[data-mode="annual"]').click();
    await page.locator('[data-pick="annualRoom"][data-value="2br"]').click();
    assert.deepEqual(await page.evaluate(() => chartModels[0].fields),
      ['toronto_pbr_rent_2br','toronto_condo_rent_2br','toronto_row_rent_2br']);
    await page.locator('[data-mode="region"]').click();
    assert.equal(await page.locator('.area-map').count(), 0, 'area map was removed');
    assert.equal(await page.locator('.region-chip').count(), 3);
    await page.locator('[data-remove-region="markham"]').click();
    assert.equal(await page.locator('.region-chip').count(), 2);
    await page.locator('[data-add-region]').selectOption('vaughan');
    assert.equal(await page.locator('.region-chip').count(), 3);
    assert.equal(await page.locator('[data-add-region]').count(), 0, 'add list hidden at three areas');
    // Month list and chart calendar agree; missing months stay blank and are disabled.
    const calendar = await page.evaluate(() => {
      const select = document.querySelector('select[data-end]'), chart = document.querySelector('[data-chart]');
      const model = chartModels[Number(chart.dataset.chart)];
      const options = [...select.options].map(o => ({value:o.value, disabled:o.disabled})).reverse();
      return {options, periods:model.periods,
        blankEnabled:options.filter(o => !o.disabled && model.fields.every(f => value(f,o.value) == null)).map(o => o.value)};
    });
    assert.deepEqual(calendar.options.map(o => o.value), calendar.periods, 'dropdown and chart calendar differ');
    assert.deepEqual(calendar.blankEnabled, [], 'months without data must be disabled');

    // 5. Economy & supply.
    await open(page, 'economy');
    assert.equal(await page.locator('.econ-kpis .metric').count(), 4);
    assert.match(await page.locator('.econ-kpis').textContent(), /一年前/);
    await page.locator('[data-pick="econRange"][data-value="all"]').click();
    const rates = await page.evaluate(() => ({first:chartModels[0].periods[0], all:allPeriods(['boc_policy_rate','goc_5y_yield','mortgage_uninsured_fixed_5plus'])[0]}));
    assert.equal(rates.first, rates.all, '"All" must start at the first observation');
    await page.locator('[data-pick="econRange"][data-value="1"]').click();
    assert.equal(await page.evaluate(() => chartModels[0].periods.length), 13);
    assert.equal(await page.locator('.population-stat').count(), 1);
    assert.ok(await page.locator('.context-group').count() >= 4, 'context indicators grouped');
    assert.equal(await page.locator('.context-group[open]').count(), 1, 'only the first group starts open');
    const migration = page.locator('.context-table tbody tr').filter({hasText:'Ontario 省际净迁移'});
    if (await migration.count()) assert.match(await migration.textContent(), /\d{4}年第\d季度/, 'quarterly label');

    // 6. Mortgage scenarios.
    await open(page, 'mortgage');
    const model = await page.evaluate(() => mortgageModel());
    assert.equal(model.down, 20);
    assert.equal(await page.locator('.payment-result').textContent(), await page.evaluate(m => `$${number(m.pay,2)}`, model));
    assert.equal(model.qualifying, Math.max(model.rate + 2, 5.25));
    const price = page.locator('[data-money="price"]');
    await price.fill('800000');
    assert.equal(await price.evaluate(el => document.activeElement === el), true, 'price input lost focus');
    assert.equal(await page.locator('[data-loan]').textContent(), '$640,000');
    assert.equal(await page.locator('.payment-result').textContent(), await page.evaluate(() => `$${number(monthlyPayment(640000,state.rate,25),2)}`));
    await page.locator('[data-pick="down"][data-value="10"]').click();
    assert.ok(await page.locator('[data-mortgage-hints] .message').count() >= 1, 'insurance reminder below 20% down');
    await page.locator('[data-number="rate"]').fill('');
    assert.match(await page.locator('.mortgage-results').textContent(), /有效的利率/, 'blank rate must not show a payment');
    await page.locator('[data-number="rate"]').fill('5');
    assert.equal(await page.locator('.sens-col').count(), 4);

    // 7. Navigation: plain #tokens survive reload, back returns, a new page starts at the top, language is remembered.
    await open(page, 'market');
    await page.evaluate(() => window.scrollTo(0, 2000));
    await open(page, 'rent');
    assert.match(await page.evaluate(() => location.hash), /^#rent(-[a-z]+)?$/, 'rent reopens on its last tab');
    assert.equal(await page.evaluate(() => scrollY), 0, 'new page starts at the top');
    await page.locator('[data-mode="monthly"]').click();
    assert.equal(await page.evaluate(() => location.hash), '#rent');
    await page.locator('[data-mode="lease"]').click();
    assert.equal(await page.evaluate(() => location.hash), '#rent-lease');
    await page.locator('[data-lang="en"]').click();
    await page.reload();
    await page.locator('#app nav').waitFor();
    assert.equal(await page.locator('[data-mode="lease"]').getAttribute('aria-selected'), 'true', 'reload keeps the tab');
    assert.equal(await page.evaluate(() => document.documentElement.lang), 'en', 'language remembered');
    await page.goBack();
    assert.equal(await page.locator('[data-mode="monthly"]').getAttribute('aria-selected'), 'true', 'back returns to the previous tab');
    assert.match(await page.title(), /^Rental market · /);
    await page.locator('[data-lang="zh"]').click();

    assert.deepEqual(errors, [], 'browser errors');
    console.log(`PASS: ${COMBOS.length} page combinations, no sideways scroll at 1440/390/320 px, overview, rent, economy and mortgage checks`);
  } finally {
    await browser?.close();
    await new Promise(resolve => server.close(resolve));
  }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
