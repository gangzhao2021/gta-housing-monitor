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
    for (const marketView of ['level','mom','yoy']) for (const priceRange of ['recent','long']) for (const tempView of ['line','heat'])
      out.push({lang, page:'market', marketView, priceRange, tempView});
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
    assert.equal(await page.locator('.long-run').count(), 0, 'long-run view sits behind the price switch');
    await page.locator('[data-pick="priceRange"][data-value="long"]').click();
    assert.ok(await page.locator('.price-panel .long-run .series-line').count() >= 1, 'long-run chart missing');
    assert.match(await page.locator('.long-run-stats').textContent(), /高点.*%/);
    assert.equal(await page.locator('[data-pick="marketView"]').count(), 0, 'values/MoM/YoY only apply to the HPI view');
    await page.locator('[data-pick="priceRange"][data-value="recent"]').click();
    // In-page section nav: one button per section, each jumps to an existing block.
    const jumps = await page.locator('.section-nav [data-jump]').evaluateAll(els => els.map(e => e.dataset.jump));
    assert.equal(jumps.length, 5, 'prices, temperature, supply, price bands, areas');
    for (const id of jumps) assert.equal(await page.locator(`#${id}`).count(), 1, `section ${id} missing`);
    await page.locator('.section-nav [data-jump="sec-mix"]').click();
    await page.waitForTimeout(700);
    assert.equal(await page.locator('.section-nav [aria-current="true"]').getAttribute('data-jump'), 'sec-mix', 'scroll spy marks the section in view');
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
    // Linked charts: heatmap and price-band columns set the observation month; legend focuses one band.
    assert.equal(await page.locator('.heat-cell').count(), 0, 'heatmap sits behind the temperature switch');
    await page.locator('[data-pick="tempView"][data-value="heat"]').click();
    const heatCells = page.locator('.heat-cell.pickable');
    assert.ok(await heatCells.count() >= 24, 'cells from September 2022 on are selectable');
    const target = await page.evaluate(() => allPeriods(['trreb_hpi_benchmark','trreb_sales','moi_raw']).at(-13));
    await page.locator(`.heat-cell[data-pick-month="${target}"]`).click();
    assert.equal(await page.evaluate(() => state.end.market), target, 'heatmap click sets the month');
    assert.equal(await page.locator('[data-end="market"]').inputValue(), target);
    assert.equal(await page.locator(`.band-mix .band-col[data-pick-month="${target}"]`).count(), 1, 'price-band chart shows the same month');
    await page.locator(`.heat-cell[data-pick-month="${target}"]`).hover();
    assert.equal(await page.locator('.viz-tip').isVisible(), true, 'hover shows the month and reading');
    const latestMonth = await page.evaluate(() => allPeriods(['trreb_hpi_benchmark','trreb_sales','moi_raw']).at(-1));
    await page.locator(`.band-col[data-pick-month="${latestMonth}"]`).click();
    assert.equal(await page.evaluate(() => state.end.market), latestMonth, 'column click sets the month');
    await page.locator('.band-legend').first().click();
    assert.ok(await page.locator('.band-focus-label').count() >= 2, 'focused band shows its shares');
    await page.locator('.band-legend.active').click();
    assert.equal(await page.locator('.band-focus-label').count(), 0);
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
    // Dumbbell: four unit types; asking rents have no studio, so that point is a hollow marker.
    assert.equal(await page.locator('.db-row').count(), 4, 'one row per unit type');
    assert.equal(await page.locator('.db-missing').count(), 1, 'asking rents have no studio category');
    const dots = await page.locator('.db-dot').count();
    assert.equal(dots, await page.evaluate(() => ['studio','1br','2br','3br'].flatMap(r => RENT_MEASURES.apartment.map(m => m[1](r))).filter(f => f && latestObservation(f)).length));
    await page.locator('[data-pick-room="3br"]').click();
    assert.equal(await page.locator('.db-row.selected').getAttribute('data-pick-room'), '3br');
    assert.equal(await page.evaluate(() => state.room), '3br', 'row click switches the trend below');
    assert.match(await page.locator('.rent-measures .note').textContent(), /三卧及以上/, 'CMHC 3+ must be labelled');
    await page.locator('[data-pick="measureType"][data-value="townhouse"]').click();
    assert.equal(await page.locator('.db-row').count(), 4);
    assert.equal(await page.locator('.db-row[data-pick-room="3br"] .db-dot').count(), 2, 'three-bedroom townhouses have both measures');
    await page.locator('[data-pick="measureType"][data-value="apartment"]').click();
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
    assert.match(await page.locator('.amort h3').textContent(), /5\.00%/);
    assert.equal(await page.locator('.amort-bar').count(), await page.evaluate(() => Number(state.years)));
    await page.locator('[data-amort-step="2"]').click();
    assert.match(await page.locator('.amort h3').textContent(), /7\.00%/, 'rate column switches the chart');
    assert.equal(await page.locator('.sens-col.chosen').getAttribute('data-amort-step'), '2');
    await page.locator('[data-number="rate"]').fill('4');
    assert.match(await page.locator('.amort h3').textContent(), /6\.00%/, 'chart follows the rate input, keeping the chosen offset');
    const bg = await page.locator('.amort .legend-item i').first().evaluate(el => getComputedStyle(el).backgroundColor);
    assert.notEqual(bg, 'rgba(0, 0, 0, 0)', 'swatches keep their colour after redraw');

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

    // 8. Dark mode follows the system setting and the host's data-theme, and keeps text readable.
    await page.emulateMedia({colorScheme:'dark'});
    await open(page, 'market');
    const dark = await page.evaluate(() => ({bg:getComputedStyle(document.body).backgroundColor, ink:getComputedStyle(document.querySelector('h1')).color, line:COLORS[0]}));
    assert.equal(dark.bg, 'rgb(18, 20, 24)');
    assert.notEqual(dark.ink, 'rgb(23, 23, 23)', 'text turns light on a dark page');
    assert.notEqual(dark.line, '#2855d9', 'chart colours follow the dark palette');
    await page.evaluate(() => document.documentElement.setAttribute('data-theme','light'));
    await page.waitForTimeout(100);
    assert.equal(await page.evaluate(() => getComputedStyle(document.body).backgroundColor), 'rgb(255, 255, 255)', 'an explicit light theme wins over a dark system');
    await page.evaluate(() => document.documentElement.removeAttribute('data-theme'));
    await page.emulateMedia({colorScheme:'light'});
    // Manual choice in the header overrides the system and is remembered.
    await page.locator('[data-theme-choice="dark"]').click();
    assert.equal(await page.evaluate(() => getComputedStyle(document.body).backgroundColor), 'rgb(18, 20, 24)', 'dark choice applies on a light system');
    await page.reload();
    await page.locator('#app nav').waitFor();
    assert.equal(await page.evaluate(() => document.documentElement.dataset.theme), 'dark', 'choice survives a reload');
    await page.locator('[data-theme-choice="auto"]').click();
    assert.equal(await page.evaluate(() => document.documentElement.dataset.theme), undefined, 'auto hands control back to the system');

    assert.deepEqual(errors, [], 'browser errors');
    console.log(`PASS: ${COMBOS.length} page combinations, no sideways scroll at 1440/390/320 px, overview, rent, economy and mortgage checks`);
  } finally {
    await browser?.close();
    await new Promise(resolve => server.close(resolve));
  }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
