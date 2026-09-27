/* Browser regression for the published static viewer. Run with Playwright installed
   and site/dist/data.json generated from the reviewed display snapshot. */
const assert = require('node:assert/strict');
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require('playwright');

const dist = path.resolve(__dirname, '../site/dist');
const mime = {'.html':'text/html', '.js':'text/javascript', '.css':'text/css', '.json':'application/json', '.svg':'image/svg+xml'};
async function main() {
  assert.ok(fs.existsSync(path.join(dist, 'data.json')), 'Generate site/dist/data.json before browser testing');
  const server = http.createServer((req, res) => {
    const filename = req.url === '/' ? 'index.html' : req.url.slice(1);
    if (!['index.html','app.js','styles.css','data.json','favicon.svg'].includes(filename)) {
      res.writeHead(404).end(); return;
    }
    res.setHeader('Content-Type', mime[path.extname(filename)]);
    fs.createReadStream(path.join(dist, filename)).pipe(res);
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  let browser;
  try {
    browser = await chromium.launch({headless:true});
    const page = await browser.newPage({viewport:{width:1440,height:900}});
    const errors=[];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(`http://127.0.0.1:${server.address().port}`);
    await page.locator('.price-panel > .chart-area .chart').waitFor();
    assert.equal(await page.locator('.metric-asof').count(), 3, 'overview metrics need their own data period');
    assert.equal(await page.locator('.supply-stat').count(), 4, 'supply panel should keep four measures together');
    assert.match(await page.locator('.editorial').textContent(), /尚无人工审核/);
    await page.locator('.price-comparison > summary').click();
    const dual=page.locator('.price-comparison .chart');
    assert.equal(await dual.locator('.series-line').count(), 2, 'dual-axis study needs two observed series');
    assert.equal(await dual.locator('.secondary-axis').count(), 6, 'secondary axis needs its own unit and ticks');
    await dual.locator('.chart-hit').focus();
    await page.keyboard.press('ArrowLeft');
    assert.equal(await page.locator('.price-comparison .chart-tooltip').isVisible(), true);
    assert.match(await page.locator('.price-comparison .chart-tooltip').textContent(), /成交均价/);

    for (const width of [1440,390,320]) {
      await page.setViewportSize({width,height:900});
      for (const lang of ['zh','en']) {
        await page.locator(`[data-lang="${lang}"]`).click();
        const note = page.locator('.price-panel svg .hpi-annotation');
        assert.equal(await note.count(), 1, `${width}px ${lang}: HPI mark missing`);
        const copy = await note.locator('text').allTextContents();
        assert.ok(copy.join(' ').includes('341.7'));
        assert.ok(copy.join(' ').includes('320.0'));
        assert.ok(copy.join(' ').includes('6.4%'));
        assert.ok(copy.join(' ').includes('5.5%'));
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, `${width}px ${lang}: overflow`);
        const clipped=await note.locator('text').evaluateAll(nodes => nodes.some(node => {
          const box=node.getBBox(),svg=node.ownerSVGElement.viewBox.baseVal;
          return box.x<0||box.x+box.width>svg.width||box.y+box.height>svg.height;
        }));
        assert.equal(clipped,false,`${width}px ${lang}: annotation clipped`);
        if(process.env.HOUSING_SCREENSHOT_DIR&&width===390){
          await page.screenshot({path:path.join(process.env.HOUSING_SCREENSHOT_DIR,`housing-hpi-${lang}.png`),fullPage:true});
        }
      }
    }
    await page.setViewportSize({width:1440,height:900});
    await page.locator('[data-lang="zh"]').click();
    await page.locator('[data-end="market"]').selectOption('2025-03');
    assert.equal(await page.locator('.price-panel .hpi-annotation').count(), 0, 'future HPI annotation shown in earlier window');
    await page.locator('[data-end="market"]').selectOption('2026-08');
    await page.locator('.price-panel > .chart-area .chart-hit').focus();
    await page.keyboard.press('ArrowLeft');
    assert.equal(await page.locator('.price-panel > .chart-area .chart-tooltip').isVisible(), true);
    await page.locator('[data-market-view="mom"]').click();
    assert.equal(await page.locator('.price-panel > .chart-area .hpi-annotation').count(), 0, 'level annotation must not use a transformed axis');
    assert.equal(await page.evaluate(() => comparisonValue('trreb_hpi_benchmark','2025-04','mom')), null, 'HPI break must not become a growth number');
    assert.equal(await page.evaluate(() => comparisonValue('trreb_sales','2026-08','mom')), await page.evaluate(() => (value('trreb_sales','2026-08')/value('trreb_sales','2026-07')-1)*100));
    await page.locator('[data-market-view="yoy"]').click();
    assert.equal(await page.evaluate(() => comparisonValue('trreb_hpi_benchmark','2026-03','yoy')), null, 'yearly HPI base crosses the break');
    await page.locator('[data-market-view="level"]').click();
    await page.locator('#district-section > summary').click();
    assert.equal(await page.locator('#district-section .sparkline').count(), 12, 'each district row needs a six-month mini-chart');
    assert.match(await page.locator('#district-section .sparkline').first().getAttribute('aria-label'), /2026-08/);
    assert.equal(await page.locator('.municipal-shape').count(), 8, 'only verified municipality boundaries should be coloured');
    assert.equal(await page.locator('.municipal-table tbody tr').count(), 8);
    assert.equal(await page.locator('.municipal-shape[fill="#d6dce0"]').count(), 0, 'latest month has eight consecutive observations');
    await page.locator('[data-end="market"]').selectOption('2022-09');
    assert.equal(await page.locator('.municipal-shape[fill="#d6dce0"]').count(), 8, 'missing prior month must remain uncoloured');
    await page.locator('[data-end="market"]').selectOption('2026-08');
    const markham=page.locator('[data-map-csd="Markham"]');
    assert.match(await markham.getAttribute('aria-label'), /Markham.*%/);
    await markham.focus();
    await page.keyboard.press('Enter');
    assert.equal(await page.locator('#district-section').getAttribute('open'), '');
    assert.equal(await page.locator('[data-state="districtRegion"]').inputValue(), 'Markham');

    await page.locator('[data-page="mortgage"]').click();
    const principal=page.locator('[data-number="principal"]');
    await principal.fill('600000');
    assert.equal(await principal.evaluate(el => document.activeElement === el), true, 'input lost focus');
    const payment=await page.locator('.payment-result').textContent();
    const expected=await page.evaluate(() => `$${number(monthlyPayment(600000,5,25),2)}`);
    assert.equal(payment, expected, 'monthly payment did not update on input');
    await page.locator('[data-number="years"]').fill('');
    assert.equal(await page.locator('.payment-result').textContent(), '—', 'incomplete input should not show a misleading payment');
    await page.locator('[data-number="years"]').fill('30');
    await page.locator('[data-number="rate"]').fill('4');
    assert.equal(await page.locator('.payment-result').textContent(), await page.evaluate(() => `$${number(monthlyPayment(600000,4,30),2)}`));

    await page.locator('[data-page="rent"]').click();
    await page.locator('[data-mode="region"]').click();
    assert.deepEqual(await page.locator('[data-region]:checked').evaluateAll(nodes => nodes.map(n => n.dataset.region)), ['north_york','scarborough','markham']);
    const comparison=await page.evaluate(() => {
      const select=document.querySelector('select[data-end]');
      const chart=document.querySelector('[data-chart]');
      const model=chartModels[Number(chart.dataset.chart)];
      return {
        options:[...select.options].map(o => ({value:o.value,disabled:o.disabled})).reverse(),
        periods:model.periods,
        fields:model.fields,
        gapValues:model.fields.map(f => value(f,'2024-09')),
        pathCount:chart.querySelectorAll('.series-line').length,
      };
    });
    assert.deepEqual(comparison.options.map(o => o.value), comparison.periods, 'dropdown and chart calendar differ');
    assert.equal(comparison.options.find(o => o.value === '2024-09')?.disabled, true, 'missing month must be disabled');
    assert.ok(comparison.gapValues.every(v => v == null), 'gap was filled with data');
    assert.ok(comparison.pathCount > comparison.fields.length, 'lines should break at missing months');
    assert.deepEqual(errors, [], 'browser errors');
    console.log('PASS: HPI annotations, responsive languages, mortgage input, rental month parity and gaps');
  } finally {
    await browser?.close();
    await new Promise(resolve => server.close(resolve));
  }
}
main().catch(error => {console.error(error); process.exitCode=1;});
