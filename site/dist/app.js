'use strict';
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const TEXT = {
  zh:{market:'市场总览',rent:'租赁市场',economy:'经济与供给',mortgage:'月供情景',snapshot:'只读展示 · 资料快照生成于',fixed:'网站显示已发布快照；本机更新经核验和发布后才在这里生效。',date:'观察月份',year:'调查年份',price:'房价走势',sales:'成交与新增挂牌',supply:'库存月数与成交／新挂牌比',annual:'年度存量',monthly:'月度挂牌',region:'地区对比',room:'房型',regionLabel:'比较地区（最多三个）',mapTitle:'地区选择地图',mapNote:'位置点仅用于选择地区，不代表统计边界或街道租金。灰色表示所选期间无观测；最多比较三个地区。',mapFull:'已选择三个地区，请先取消一个。',rates:'利率与融资',jobs:'就业',construction:'住宅建设',population:'人口',context:'外部背景（研究中）',contextNote:'仅供解释市场背景；油价暂不上图，这些指标尚未用于评分或预测。不同地区、频率与单位不能直接合并。',latest:'最近值',unit:'单位',period:'资料期',geography:'地区',indicator:'指标',sources:'官方来源',impact:'如何影响房价',principal:'贷款本金（加元）',years:'摊还年限',rate:'名义年利率（%）',payment:'每月本息',paymentNote:'仅为固定假设的计算情景，不代表贷款批准、实际家庭负担能力或利率预测。',noData:'所选范围暂无观测',notForecast:'公开数据研究工具 · 非实时行情 · 领先信号尚未验证',total:'全部卧室类型',studio:'开间',one:'一卧',two:'两卧',three:'三卧',threePlus:'三卧及以上',starts:'当月开工与竣工',stock:'月末在建住宅',unemployment:'失业率',employment:'就业率与劳动参与率',sourceNote:'资料来自已发布快照；不同统计边界不计算交叉比率。'},
  en:{market:'Market overview',rent:'Rental market',economy:'Economy & supply',mortgage:'Mortgage scenarios',snapshot:'Read-only display · Snapshot created',fixed:'This site shows a published snapshot. Local updates appear only after validation and publication.',date:'Observation month',year:'Survey year',price:'Home price trend',sales:'Sales and new listings',supply:'Months of inventory and sales-to-new-listings ratio',annual:'Annual stock',monthly:'Monthly asking',region:'Area comparison',room:'Bedroom type',regionLabel:'Compare areas (up to three)',mapTitle:'Select areas on map',mapNote:'Reference points select areas; they are not statistical boundaries or street rents. Grey means no observation for this period. Compare up to three areas.',mapFull:'Three areas are selected. Remove one first.',rates:'Rates & financing',jobs:'Employment',construction:'Housing construction',population:'Population',context:'External context (under research)',contextNote:'For market context only. Oil is not charted yet, and these measures are not used for scores or forecasts. Different geographies, frequencies and units cannot be combined directly.',latest:'Latest value',unit:'Unit',period:'Reference period',geography:'Geography',indicator:'Measure',sources:'Official sources',impact:'How it relates to home prices',principal:'Loan principal (CAD)',years:'Amortization years',rate:'Nominal annual rate (%)',payment:'Monthly principal & interest',paymentNote:'A fixed-assumption scenario, not a loan approval, actual household affordability or rate forecast.',noData:'No observations for this selection',notForecast:'Public-data research tool · Not live market data · Leading signals not validated',total:'All bedroom types',studio:'Studio',one:'1 bedroom',two:'2 bedrooms',three:'3 bedrooms',threePlus:'3+ bedrooms',starts:'Monthly starts and completions',stock:'Homes under construction at month-end',unemployment:'Unemployment rate',employment:'Employment and participation rates',sourceNote:'Values come from a published snapshot; different statistical boundaries are not combined into ratios.'}
};
const PROPERTY_TYPES = {"all_types": ["全部房型", "All property types"], "detached": ["独立屋", "Detached"], "semi_detached": ["半独立屋", "Semi-detached"], "townhouse": ["镇屋", "Townhouse"], "condo_townhouse": ["公寓镇屋", "Condo townhouse"], "condo_apartment": ["公寓", "Condo apartment"], "link": ["连接屋", "Link"], "coop_apartment": ["合作公寓", "Co-op apartment"], "detached_condo": ["独立式公寓", "Detached condo"], "coownership_apartment": ["共同产权公寓", "Co-ownership apartment"]};
const COLORS = ['#2855d9','#007f86','#bf6517','#7952be'];
const ROOM = {total:'total',studio:'studio','1br':'one','2br':'two','3br':'three','3plus':'threePlus'};
const AREAS = {toronto:'Toronto',north_york:'North York',scarborough:'Scarborough',markham:'Markham',vaughan:'Vaughan',mississauga:'Mississauga',oakville:'Oakville',richmond_vaughan_king:'Richmond Hill / Vaughan / King',aurora_newmarket_whit:'Aurora / Newmarket / Whit-St.'};
const MAP_POINTS = {toronto:[-79.3832,43.6532],north_york:[-79.4111,43.7615],scarborough:[-79.2318,43.7764],markham:[-79.3370,43.8561],vaughan:[-79.5083,43.8372],mississauga:[-79.6441,43.5890],oakville:[-79.6877,43.4675],richmond_vaughan_king:[-79.4700,43.8800],aurora_newmarket_whit:[-79.4400,44.0200]};
const state = {lang:'zh',page:'market',rentMode:'monthly',room:'total',annualRoom:'total',regionRoom:'total',regionFrequency:'monthly',regions:['north_york','scarborough'],regionFeedback:'',supplyMetric:'moi_raw',principal:500000,years:25,rate:5,end:{}};
const initialState=JSON.parse(JSON.stringify(state));
function restoreView(){try{const q=JSON.parse(decodeURIComponent(location.hash.slice(1)));for(const key of ['lang','page','rentMode','room','annualRoom','regionRoom','regionFrequency']){const allowed={lang:['zh','en'],page:['market','rent','economy','mortgage'],rentMode:['monthly','annual','region'],room:Object.keys(ROOM),annualRoom:Object.keys(ROOM),regionRoom:Object.keys(ROOM),regionFrequency:['monthly','annual']};if(allowed[key].includes(q[key]))state[key]=q[key]}if(['moi_raw','snlr_raw'].includes(q.supplyMetric))state.supplyMetric=q.supplyMetric;if(Object.hasOwn(PROPERTY_TYPES,q.districtType))state.districtType=q.districtType;if(typeof q.districtRegion==='string'&&/^[A-Za-z0-9 ./'()&-]{1,100}$/.test(q.districtRegion))state.districtRegion=q.districtRegion;if(['average_price','sales','new_listings','active_listings','median_price','avg_ldom'].includes(q.districtMetric))state.districtMetric=q.districtMetric;if(Array.isArray(q.regions))state.regions=q.regions.filter(r=>Object.hasOwn(AREAS,r)).slice(0,3);if(q.end&&typeof q.end==='object')for(const [k,v]of Object.entries(q.end)){if(/^[a-zA-Z0-9_-]{1,100}$/.test(k)&&!['__proto__','constructor','prototype'].includes(k)&&/^\d{4}(-\d{2})?$/.test(v))state.end[k]=v}}catch{}}
function viewLink(){const q={};for(const key of ['lang','page','rentMode','room','annualRoom','regionRoom','regionFrequency','regions','end','districtType','districtRegion','districtMetric','supplyMetric'])q[key]=state[key];return '#'+encodeURIComponent(JSON.stringify(q))}
restoreView();
let payload, observations, monthly;
let chartModels = [];
const t = (key) => TEXT[state.lang][key] || key;
const meta = (field) => payload.series[field] || {zh:field,en:field,unit:'',source:'',url:''};
const name = (field) => meta(field)[state.lang] || meta(field).zh;
const number = (value,digits=0) => value==null ? '—' : Number(value).toLocaleString(state.lang==='zh'?'zh-CN':'en-CA',{maximumFractionDigits:digits,minimumFractionDigits:digits});
const axisNumber = (v) => v===0?'0':Math.abs(v)>=1000000?`${number(v/1000000,2)}M`:Math.abs(v)>=10000?`${number(v/1000,0)}k`:number(v,Math.abs(v)<100?1:0);
const monthLabel = (period) => state.lang==='zh' && /^\d{4}-\d{2}$/.test(period) ? `${period.slice(0,4)}年${Number(period.slice(5))}月` : period;
const quarterLabel = (period) => {const q=Math.floor((Number(period.slice(5))-1)/3)+1;return state.lang==='zh'?`${period.slice(0,4)}年第${q}季度`:`${period.slice(0,4)} Q${q}`};
function prepare() {
  observations = payload.snapshot.observations;
  monthly = {};
  const dailyYields = {};
  for (const [field, periods] of Object.entries(observations)) {
    for (const [period,value] of Object.entries(periods)) {
      if(field==='goc_5y_yield') (dailyYields[period.slice(0,7)] ??= []).push(value);
      else {
        const key=field==='boc_policy_rate'?period.slice(0,7):period;
        (monthly[key] ??= {})[field]=value;
      }
    }
  }
  for(const [period,values] of Object.entries(dailyYields)) (monthly[period] ??= {}).goc_5y_yield=values.reduce((a,b)=>a+b,0)/values.length;
  for(const row of Object.values(monthly)) {
    if(row.trreb_sales && row.trreb_active_listings!=null) row.moi_raw=row.trreb_active_listings/row.trreb_sales;
    if(row.trreb_sales!=null && row.trreb_new_listings) row.snlr_raw=row.trreb_sales/row.trreb_new_listings*100;
  }
}
const allPeriods = (fields, annual=false) => (annual?[...new Set(fields.flatMap(f=>Object.keys(observations[f]||{})))]:Object.keys(monthly)).filter(p=>annual?fields.some(f=>observations[f]?.[p]!=null):(/^\d{4}-\d{2}$/.test(p)&&fields.some(f=>monthly[p]?.[f]!=null))).sort();
const last = (fields,annual=false,key=fields.join('-')) => {const periods=allPeriods(fields,annual);if(!periods.length)return null;if(!periods.includes(state.end[key]))state.end[key]=periods.at(-1);return state.end[key]};
const viewPeriods = (fields,end,annual=false) => allPeriods(fields,annual).filter(p=>p<=end).slice(annual?-5:-25);
function calendarViewPeriods(fields,end,annual=false) {
  if(annual)return viewPeriods(fields,end,true);
  const first=allPeriods(fields).find(p=>p<=end);
  if(!first)return [];
  const periods=[];
  let [year,month]=end.split('-').map(Number);
  for(let i=0;i<36;i++){
    const period=`${year}-${String(month).padStart(2,'0')}`;
    if(period<first)break;
    periods.unshift(period);
    month--;if(month===0){month=12;year--}
  }
  return periods;
}
const value = (field,period,annual=false) => annual? observations[field]?.[period] : monthly[period]?.[field];
function help(field,visible,iconOnly=false) {
  const m=meta(field), h=m.help?.[state.lang];
  if(!h) return esc(visible||name(field));
  const link=m.url?`<a href="${esc(m.url)}" target="_blank" rel="noopener noreferrer">${esc(m.source)} ↗</a>`:'';
  return `<details class="info"><summary aria-label="${esc(name(field))}">${iconOnly?'':esc(visible||name(field))}<span class="help-icon" aria-hidden="true">ⓘ</span></summary><div class="bubble"><strong>${esc(t('impact'))}</strong><p>${esc(h[0])}</p><p>${esc(h[1])}</p>${link}</div></details>`;
}
function shell(body) {
  document.documentElement.lang=state.lang;
  $('#app').classList.toggle('overview',state.page==='market');
  $('#app').innerHTML=`<header class="masthead"><div class="brand">GTA HOUSING MONITOR</div><div class="languages" role="group" aria-label="语言 / Language"><button data-lang="zh" aria-pressed="${state.lang==='zh'}">中文</button><button data-lang="en" aria-pressed="${state.lang==='en'}">EN</button></div></header><nav aria-label="${state.lang==='zh'?'导航':'Navigation'}">${['market','rent','economy','mortgage'].map(p=>`<button data-page="${p}" ${p===state.page?'aria-current="page"':''}>${t(p)}</button>`).join('')}</nav>${state.page==='market'?'':`<h1>${t(state.page)}</h1><p class="caption intro">${t('snapshot')} ${esc(payload.snapshot.created_at)} · ${t('fixed')}</p>`}${body}<footer><div class="view-actions"><button data-reset>${state.lang==='zh'?'重置筛选':'Reset filters'}</button><a href="${esc(viewLink())}">${state.lang==='zh'?'保存视图链接':'Save view link'}</a></div><p>${t('snapshot')} ${esc(payload.snapshot.created_at)}</p><p>${t('notForecast')}</p></footer>`;
  attach();
}
function select(label,key,periods,annual=false,availablePeriods=periods) {
  const current=state.end[key]||periods.at(-1);
  const available=new Set(availablePeriods);
  return `<label class="control">${esc(label)}<select data-end="${esc(key)}">${[...periods].reverse().map(p=>`<option value="${esc(p)}" ${p===current?'selected':''} ${available.has(p)?'':'disabled'}>${annual?p:monthLabel(p)}</option>`).join('')}</select></label>`;
}
function metric(field,period,digits=0) {
  const v=value(field,period), prev=value(field,`${Number(period.slice(0,4))-1}${period.slice(4)}`), delta=(v!=null&&prev)?(v/prev-1)*100:null;
  const shown=field==='trreb_hpi_benchmark'?`$${number(v)}`:number(v,digits);
  return `<div class="metric"><div class="metric-name">${help(field)}</div><div class="metric-value">${shown}</div><div class="metric-delta">${delta==null?'—':`${delta>=0?'+':''}${number(delta,1)}%`} ${state.lang==='zh'?'较上年同期':'year over year'}</div></div>`;
}
function tooltipValue(field,v) {
  if(v==null) return '—';
  const unit=meta(field).unit;
  const shown=number(v,Math.abs(v)<100?2:0);
  if(unit==='CAD') return `$${shown}`;
  if(unit==='CAD/month') return `$${shown}${state.lang==='zh'?'/月':'/month'}`;
  if(unit==='%') return `${shown}%`;
  const units={sales:state.lang==='zh'?'宗':'sales',units:state.lang==='zh'?'套':'units',persons:state.lang==='zh'?'人':'people','月':state.lang==='zh'?'个月':'months'};
  return `${shown}${unit?` ${units[unit]||unit}`:''}`;
}
function hpiAnnotation(periods,x,y,plotH,W,narrow) {
  const i=periods.indexOf('2025-04');
  if(i<0)return '';
  const zh=state.lang==='zh';
  const lines=zh?(narrow?[
    '注：2025-04 综合指数',
    '341.7→320.0（−6.4%）为 TRREB',
    '官方发布原值；同期基准房价',
    '$1,068,500→$1,009,400（−5.5%）。',
    '跨期解读注意口径可能变化。'
  ]:[
    '注：2025-04 综合指数 341.7→320.0（−6.4%）为 TRREB 官方发布原值；',
    '同期基准房价 $1,068,500→$1,009,400（−5.5%）。跨期解读注意口径可能变化。'
  ]):(narrow?[
    'Note: TRREB published the 2025-04',
    'composite index at 320.0, down from',
    '341.7 (−6.4%). The benchmark price',
    'fell from $1,068,500 to $1,009,400',
    '(−5.5%). Compare periods with care;',
    'the methodology may differ.'
  ]:[
    'Note: TRREB published the 2025-04 composite index at 320.0, down from 341.7 (−6.4%).',
    'The benchmark price fell from $1,068,500 to $1,009,400 (−5.5%). Methodology may differ across periods.'
  ]);
  const xx=x(i),yy=y(value('trreb_hpi_benchmark','2025-04'));
  const tx=narrow?12:55,ty=plotH+23;
  return `<g class="hpi-annotation"><title>${esc(lines.join(' '))}</title><line class="hpi-guide" x1="${xx}" x2="${xx}" y1="${yy+6}" y2="${plotH-30}"/><circle class="hpi-marker" cx="${xx}" cy="${yy}" r="5"/>${lines.map((line,index)=>`<text class="hpi-note" x="${tx}" y="${ty+index*16}">${esc(line)}</text>`).join('')}</g>`;
}
function svgChart(fields,periods,{annual=false,zero=false,height=240,labels=null,compact=false,width=null,legend=true,unit=null,hpiNote=false}={}) {
  const narrow=window.innerWidth<=480;
  const W=narrow?Math.max(300,Math.min(440,window.innerWidth-40)):(width||(compact?520:680));
  const noteHeight=hpiNote&&periods.includes('2025-04')?(narrow?122:72):0;
  const H=(narrow?220:height)+noteHeight,plotH=H-noteHeight;
  const pad={l:unit?65:(narrow?47:(compact?47:55)),r:28,t:15,b:30},innerW=W-pad.l-pad.r,innerH=plotH-pad.t-pad.b;
  const vals=fields.flatMap(f=>periods.map(p=>value(f,p,annual))).filter(v=>Number.isFinite(v));
  if(!vals.length) return `<p class="chart-empty">${t('noData')}</p>`;
  let min=zero?0:Math.min(...vals),max=Math.max(...vals);
  if(min===max){min=Math.max(0,min-1);max+=1}
  const margin=(max-min)*.08;max+=margin;if(!zero)min-=margin;
  const x=i=>pad.l+(periods.length===1?innerW/2:i*innerW/(periods.length-1));
  const y=v=>pad.t+(max-v)/(max-min)*innerH;
  const grids=Array.from({length:5},(_,i)=>{const yy=pad.t+i*innerH/4, vv=max-i*(max-min)/4;return `<line class="grid-line" x1="${pad.l}" x2="${W-pad.r}" y1="${yy}" y2="${yy}"/><text class="axis-label" x="${pad.l-9}" y="${yy+4}" text-anchor="end">${axisNumber(vv)}</text>`}).join('');
  const step=Math.max(1,Math.ceil((periods.length-1)/(narrow?2:4)));
  const ticks=periods.map((p,i)=>i===0||i===periods.length-1||i%step===0?`<text class="axis-label" x="${x(i)}" y="${plotH-5}" text-anchor="middle">${annual?p:p.slice(2).replace('-','/')}</text>`:'').join('');
  const lines=fields.map((f,j)=>{let paths=[],part=[];periods.forEach((p,i)=>{const v=value(f,p,annual);if(v==null){if(part.length){paths.push(`<path class="series-line" d="${part.join(' ')}" stroke="${COLORS[j%COLORS.length]}"/>`);part=[]}return}part.push(`${part.length?'L':'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`)});if(part.length)paths.push(`<path class="series-line" d="${part.join(' ')}" stroke="${COLORS[j%COLORS.length]}"/>`);return paths.join('')}).join('');
  const index=chartModels.push({fields,periods,annual,labels,W,H,pad,innerW,innerH,y})-1;
  return `<div class="chart-area">${legend?`<div class="legend">${fields.map((f,i)=>`<span class="legend-item"><span class="legend-line series-color-${i%COLORS.length}"></span>${help(f,labels?.[f])}</span>`).join('')}</div>`:''}<div class="chart-wrap"><svg class="chart" data-chart="${index}" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(fields.map(f=>labels?.[f]||name(f)).join(', '))}">${grids}${ticks}${unit?`<text class="axis-label" transform="translate(12 ${plotH/2}) rotate(-90)" text-anchor="middle">${esc(unit)}</text>`:''}${lines}${hpiNote?hpiAnnotation(periods,x,y,plotH,W,narrow):''}<line class="chart-cursor" data-cursor x1="0" x2="0" y1="${pad.t}" y2="${plotH-pad.b}" visibility="hidden"/><g data-points></g><rect class="chart-hit" x="${pad.l}" y="${pad.t}" width="${innerW}" height="${innerH}" fill="transparent" tabindex="0" role="button" aria-label="${state.lang==='zh'?'图表数据；使用左右方向键查看各期':'Chart values; use left and right arrows to inspect periods'}"/></svg><div class="chart-tooltip" hidden></div></div></div>`;
}
function attachChartTooltips() {
  document.querySelectorAll('[data-chart]').forEach(svg=>{
    const model=chartModels[Number(svg.dataset.chart)];
    const {fields,periods,annual,labels,W,pad,innerW,innerH,y}=model;
    const wrap=svg.parentElement,tooltip=wrap.querySelector('.chart-tooltip');
    const cursor=svg.querySelector('[data-cursor]'),points=svg.querySelector('[data-points]');
    const x=i=>pad.l+(periods.length===1?innerW/2:i*innerW/(periods.length-1));
    let active=periods.length-1;
    function show(i) {
      active=Math.max(0,Math.min(periods.length-1,i));
      const period=periods[active],xx=x(active);
      cursor.setAttribute('x1',xx);cursor.setAttribute('x2',xx);cursor.setAttribute('visibility','visible');
      points.innerHTML=fields.map((f,j)=>{const v=value(f,period,annual);return v==null?'':`<circle class="chart-point" cx="${xx}" cy="${y(v)}" r="4" fill="${COLORS[j%COLORS.length]}"/>`}).join('');
      tooltip.innerHTML=`<strong>${annual?period:monthLabel(period)}</strong>${fields.map((f,j)=>`<div class="tooltip-row"><span class="tooltip-key"><i class="series-color-${j%COLORS.length}"></i>${esc(labels?.[f]||name(f))}</span><b>${esc(tooltipValue(f,value(f,period,annual)))}</b></div>`).join('')}`;
      tooltip.hidden=false;
      const left=Math.max(8,Math.min(wrap.clientWidth-tooltip.offsetWidth-8,xx/W*svg.clientWidth+8));
      tooltip.style.left=`${left}px`;
      svg.querySelector('.chart-hit').setAttribute('aria-label',`${annual?period:monthLabel(period)}；${fields.map(f=>`${labels?.[f]||name(f)} ${tooltipValue(f,value(f,period,annual))}`).join('，')}`);
    }
    function hide(){tooltip.hidden=true;cursor.setAttribute('visibility','hidden');points.innerHTML=''}
    const hit=svg.querySelector('.chart-hit');
    hit.addEventListener('pointermove',event=>{const rect=svg.getBoundingClientRect(),svgX=(event.clientX-rect.left)*W/rect.width;show(periods.length===1?0:Math.round((svgX-pad.l)/innerW*(periods.length-1)))});
    hit.addEventListener('pointerleave',hide);
    hit.addEventListener('pointerdown',event=>{const rect=svg.getBoundingClientRect(),svgX=(event.clientX-rect.left)*W/rect.width;show(periods.length===1?0:Math.round((svgX-pad.l)/innerW*(periods.length-1)))});
    hit.addEventListener('focus',()=>show(active));
    hit.addEventListener('blur',hide);
    hit.addEventListener('keydown',event=>{if(event.key==='ArrowLeft'||event.key==='ArrowRight'){event.preventDefault();show(active+(event.key==='ArrowRight'?1:-1))}else if(event.key==='Escape')hide()});
  });
}
function freshnessLabel(field){const f=payload.snapshot.freshness?.[field];if(!f)return '—';const labels={current:['已更新','Current'],pending:['待发布','Pending release'],overdue:['需核查更新','Update needs checking'],missing:['无观测','Missing'],unknown:['节奏待核验','Cadence unverified'],archived:['归档','Archived']};return (labels[f.status]||labels.unknown)[state.lang==='zh'?0:1]}
function sourceNote(){return `<p class="note">${t('sourceNote')}</p>`}
function marketPage(){
 const fields=['trreb_hpi_benchmark','trreb_sales','moi_raw'];
 const end=last(fields,false,'market');if(!end)return `<p>${t('noData')}</p>`;
 const periods=viewPeriods(fields,end),zh=state.lang==='zh', supply=state.supplyMetric==='snlr_raw'?'snlr_raw':'moi_raw';
 return `<div class="overview-heading"><div><h1>${t('market')}</h1><p class="caption">${zh?'TRREB 全市场 · 全部房型':'All TRREB areas · All home types'}</p></div>${select(t('date'),'market',allPeriods(fields))}</div>
 <div class="metrics overview-metrics">${metric('trreb_hpi_benchmark',end)}${metric('trreb_sales',end)}${metric('moi_raw',end,2)}</div>
 <section class="price-panel"><div class="chart-heading"><h2>${t('price')}</h2><span class="caption">${esc(periods[0])} — ${esc(end)}</span></div>${svgChart(['trreb_hpi_benchmark'],periods,{height:300,width:1280,legend:false,unit:'CAD',hpiNote:true})}<p class="note">${zh?'基准价格，不是成交均价。悬停、触摸或使用左右方向键查看各期数值。':'Benchmark price, not average sale price. Hover, touch or use arrow keys to inspect each period.'}</p></section>
 <div class="split overview-support"><section><h2>${t('sales')}</h2>${svgChart(['trreb_sales','trreb_new_listings'],periods,{height:230,width:616,zero:true,unit:zh?'笔 / 套':'Sales / listings'})}</section><section><h2>${zh?'供需状况':'Market balance'}</h2><div class="supply-options" role="group" aria-label="${zh?'供需指标':'Supply measure'}">${['moi_raw','snlr_raw'].map(f=>`<span><button data-supply="${f}" aria-pressed="${supply===f}">${esc(name(f))}</button>${help(f,null,true)}</span>`).join('')}</div>${svgChart([supply],periods,{height:230,width:616,zero:true,legend:false,unit:supply==='moi_raw'?(zh?'月':'Months'):'%'})}</section></div>
 ${districtSection()}<details class="overview-sources"><summary>${zh?'来源与口径':'Sources and definitions'}</summary>${sourceNote()}<p class="note">${t('fixed')}</p><a href="https://trreb.ca/market-data/market-watch/" target="_blank" rel="noopener noreferrer">TRREB Market Watch ↗</a></details>`;
}
function districtSection(){
 const rows=payload.snapshot.districts||[]; if(!rows.length)return '';
 state.districtType ||= 'all_types';state.districtRegion ||= 'Markham';state.districtMetric ||= 'average_price';
 const types=[...new Set(rows.map(r=>r.house_type))].sort();
 const chosen=rows.filter(r=>r.house_type===state.districtType);
 const areas=[...new Set(chosen.map(r=>r.region))].sort();
 if(!areas.includes(state.districtRegion))state.districtRegion=areas[0];
 const fields={average_price:['均价','Average price','CAD'],sales:['成交','Sales','sales'],new_listings:['新增挂牌','New listings','listings'],active_listings:['在售挂牌','Active listings','listings'],median_price:['中位价','Median price','CAD'],avg_ldom:['挂牌天数','Listing days','days']};
 const field='district_selected',definition=fields[state.districtMetric];
 payload.series[field]={zh:state.districtRegion+' · '+definition[0],en:state.districtRegion+' · '+definition[1],unit:definition[2],source:'TRREB',url:'https://trreb.ca/market-data/market-watch/market-watch-archive/'};
 for(const period of Object.keys(monthly))delete monthly[period][field];
 const selected=chosen.filter(r=>r.region===state.districtRegion);
 for(const row of selected){monthly[row.ym]||={};monthly[row.ym][field]=row[state.districtMetric]}
 const options=(key,items,label)=>`<label class="control">${label}<select data-state="${key}">${items.map(([v,n])=>`<option value="${esc(v)}" ${state[key]===v?'selected':''}>${esc(n)}</option>`).join('')}</select></label>`;
 const periods=selected.map(r=>r.ym).sort(),end=last([field],false,'district');
 const controls=options('districtType',types.map(v=>[v,PROPERTY_TYPES[v]?.[state.lang==='zh'?0:1]||v]),state.lang==='zh'?'转售房型':'Property type')+options('districtRegion',areas.map(v=>[v,v]),t('region'))+options('districtMetric',Object.entries(fields).map(([v,d])=>[v,d[state.lang==='zh'?0:1]]),t('indicator'))+select(t('date'),'district',periods);
 const entries=selected.filter(r=>r.ym<=end).slice(-36);
 return `<details id="district-section"><summary>${state.lang==='zh'?'地区转售明细':'District resale'}</summary><div class="controls">${controls}</div><p class="note">${state.lang==='zh'?'TRREB 报告地区不能与租赁地区互换；均价不是 HPI，受成交构成影响。':'TRREB areas differ from rental-market areas. Average prices are not HPI and depend on the sales mix.'}</p>${svgChart([field],entries.map(r=>r.ym))}<table class="context-table"><thead><tr><th>${t('period')}</th><th>${t('latest')}</th></tr></thead><tbody>${entries.slice(-12).reverse().map(r=>`<tr><td data-label="${t('period')}"><button data-district-month="${r.ym}">${monthLabel(r.ym)}</button></td><td data-label="${t('latest')}">${number(r[state.districtMetric])}</td></tr>`).join('')}</tbody></table></details>`;
}
function tabButtons(key,options,current){return `<div class="tabs" role="tablist">${options.map(([id,label])=>`<button role="tab" data-${key}="${id}" aria-selected="${current===id}">${esc(label)}</button>`).join('')}</div>`}
function roomSelect(key,annual=false){const rooms=annual?['total','studio','1br','2br','3plus']:['total','1br','2br','3br'];const current=state[key];return `<label class="control">${t('room')}<select data-state="${key}">${rooms.map(r=>`<option value="${r}" ${current===r?'selected':''}>${t(ROOM[r])}</option>`).join('')}</select></label>`}
function areaField(region,annual,room){return annual?`regional_cmhc_${region}_pbr_rent_${room}`:region==='toronto'?`toronto_asking_rent_${room}`:`regional_asking_${region}_${room}`}
function toggleRegion(region,choices){
  if(!choices.some(([id])=>id===region))return;
  state.regionFeedback='';
  if(state.regions.includes(region))state.regions=state.regions.filter(id=>id!==region);
  else if(state.regions.length<3)state.regions.push(region);
  else state.regionFeedback=t('mapFull');
  render();
}
function areaMap(choices,annual,period){
  const W=740,H=370,zoom=9,tileSize=256,world=tileSize*2**zoom;
  const viewBox=window.innerWidth<=600?'240 0 310 370':`0 0 ${W} ${H}`;
  const project=(lon,lat)=>[(lon+180)/360*world,(1-Math.asinh(Math.tan(lat*Math.PI/180))/Math.PI)/2*world];
  const [centerX,centerY]=project(-79.45,43.76),left=centerX-W/2,top=centerY-H/2;
  const x=lon=>project(lon,43.76)[0]-left;
  const y=lat=>project(-79.45,lat)[1]-top;
  const tiles=[];
  for(let tx=Math.floor(left/tileSize);tx<=Math.floor((left+W)/tileSize);tx++){
    for(let ty=Math.floor(top/tileSize);ty<=Math.floor((top+H)/tileSize);ty++){
      tiles.push(`<image class="map-tile" x="${(tx*tileSize-left).toFixed(1)}" y="${(ty*tileSize-top).toFixed(1)}" width="256" height="256" href="https://tile.openstreetmap.org/${zoom}/${tx}/${ty}.png"/>`);
    }
  }
  const short={richmond_vaughan_king:'Richmond Hill area',aurora_newmarket_whit:'Aurora area'};
  const labelOffsets={toronto:[16,24,'start'],north_york:[-18,-19,'end'],scarborough:[18,-15,'start'],markham:[18,-15,'start'],vaughan:[-18,-15,'end'],mississauga:[-18,-15,'end'],oakville:[18,-12,'start'],richmond_vaughan_king:[-18,-14,'end'],aurora_newmarket_whit:[18,-12,'start']};
  const points=choices.map(([id,label])=>{
    const [lon,lat]=MAP_POINTS[id],field=areaField(id,annual,state.regionRoom),v=value(field,period,annual),chosen=state.regions.includes(id);
    const xx=x(lon).toFixed(1),yy=y(lat).toFixed(1),status=v==null?t('noData'):tooltipValue(field,v),[dx,dy,anchor]=labelOffsets[id]||[18,-12,'start'];
    const hitX=anchor==='end'?Number(xx)-125:Number(xx)-20;
    return `<g class="map-point ${chosen?'selected':''} ${v==null?'unavailable':''}" data-map-region="${esc(id)}" role="button" tabindex="0" aria-pressed="${chosen}" aria-label="${esc(label)} · ${esc(status)}"><title>${esc(label)} · ${esc(status)}</title><rect class="map-hit" x="${hitX}" y="${Number(yy)-42}" width="145" height="68" fill="transparent"/><circle cx="${xx}" cy="${yy}" r="14"/><circle class="map-core" cx="${xx}" cy="${yy}" r="4"/><text x="${Number(xx)+dx}" y="${Number(yy)+dy}" text-anchor="${anchor}">${esc(short[id]||label)}</text></g>`;
  }).join('');
  return `<section class="area-map" aria-label="${t('mapTitle')}"><h2>${t('mapTitle')}</h2><p class="note">${t('mapNote')}</p><div class="map-surface"><svg viewBox="${viewBox}" role="group" aria-label="${t('mapTitle')}"><rect width="${W}" height="${H}" fill="#e8eef0"/>${tiles.join('')}${points}</svg><a class="map-attribution" href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">© OpenStreetMap contributors</a></div>${state.regionFeedback?`<p class="map-feedback" role="status">${esc(state.regionFeedback)}</p>`:''}</section>`;
}
function rentPage(){
  let out=tabButtons('mode',[['monthly',t('monthly')],['annual',t('annual')],['region',t('region')]],state.rentMode);
  if(state.rentMode==='monthly'){
    const f=`toronto_asking_rent_${state.room}`,periods=allPeriods([f]),end=last([f]);
    out+=`<div class="controls">${roomSelect('room')}${select(t('date'),f,periods)}</div>${end?svgChart([f],viewPeriods([f],end),{height:255}):`<p>${t('noData')}</p>`}<p class="note">${state.lang==='zh'?'挂牌均值涵盖专建出租公寓与 condo；不等于成交租金或全部出租物业。':'Asking averages cover purpose-built apartments and condos; they are not signed rents or all rental property.'}</p>`;
    return out;
  }
  if(state.rentMode==='annual'){
    const fields=[`toronto_pbr_rent_${state.annualRoom}`,`toronto_condo_rent_${state.annualRoom}`],periods=allPeriods(fields,true),end=last(fields,true);
    out+=`<div class="controls">${roomSelect('annualRoom',true)}${select(t('year'),fields.join('-'),periods,true)}</div>${end?svgChart(fields,viewPeriods(fields,end,true),{annual:true,height:255}):`<p>${t('noData')}</p>`}<p class="note">${state.lang==='zh'?'CMHC 年度存量租金与月度挂牌不同；均值变化并非同一套住房租金涨幅。':'CMHC annual stock rent differs from monthly asking rent; average changes are not same-unit rent growth.'}</p>`;
    return out;
  }
  const annual=state.regionFrequency==='annual';
  const choices=Object.entries(AREAS).filter(([id])=>annual?id!=='toronto':!id.includes('richmond')&&!id.includes('aurora'));
  state.regions=state.regions.filter(id=>choices.some(([candidate])=>candidate===id));
  const fields=state.regions.map(r=>areaField(r,annual,state.regionRoom));
  const present=fields.filter(f=>observations[f]);
  const periods=present.length?allPeriods(present,annual):[];
  const end=present.length?last(present,annual):null;
  const chartPeriods=end?(annual?viewPeriods(present,end,true):calendarViewPeriods(present,end)):[];
  const names=Object.fromEntries(state.regions.map((r,i)=>[fields[i],AREAS[r]]));
  out+=`<div class="controls"><label class="control">${t('annual')} / ${t('monthly')}<select data-state="regionFrequency"><option value="monthly" ${!annual?'selected':''}>${t('monthly')}</option><option value="annual" ${annual?'selected':''}>${t('annual')}</option></select></label>${roomSelect('regionRoom',annual)}${chartPeriods.length?select(annual?t('year'):t('date'),present.join('-'),chartPeriods,annual,periods):''}</div>`;
  out+=areaMap(choices,annual,end||periods.at(-1));
  out+=`<div class="region-options" role="group" aria-label="${t('regionLabel')}">${choices.map(([id,label])=>`<label><input type="checkbox" data-region="${id}" ${state.regions.includes(id)?'checked':''}>${esc(label)}</label>`).join('')}</div>`;
  out+=end?svgChart(present,chartPeriods,{annual,height:260,labels:names}):`<p class="chart-empty">${t('noData')}</p>`;
  out+=sourceNote();
  return out;
}
function economicSection(title,fields,key,opts={}){const periods=allPeriods(fields,!!opts.annual),end=last(fields,!!opts.annual,key);return `<section class="economic-panel"><h2>${title}</h2><div class="controls">${select(opts.annual?t('year'):t('date'),key,periods,!!opts.annual)}</div>${end?svgChart(fields,viewPeriods(fields,end,!!opts.annual),opts):`<p>${t('noData')}</p>`}</section>`}
function contextTable(){const data=payload.snapshot.context||{};const fields=Object.keys(data);const rows=fields.map(f=>{const v=data[f],unit=meta(f).unit,period=v?.period||'—';const area=meta(f).geography||'—';const digits=f==='usd_cad_monthly'?4:f==='toronto_residential_construction_cost_index'?1:2;const cells=[[t('latest'),number(v?.value,digits)],[t('unit'),unit],[t('period'),f==='toronto_residential_construction_cost_index'&&v?quarterLabel(period):period],[t('geography'),area],[state.lang==='zh'?'更新状态':'Freshness',freshnessLabel(f)]];return `<tr><th scope="row">${help(f)}</th>${cells.map(([label,val])=>`<td data-label="${esc(label)}">${esc(val)}</td>`).join('')}</tr>`}).join('');return `<h2>${t('context')}</h2><p class="note">${t('contextNote')}</p><table class="context-table"><thead><tr>${['indicator','latest','unit','period','geography',state.lang==='zh'?'更新状态':'Freshness'].map(k=>`<th scope="col">${t(k)}</th>`).join('')}</tr></thead><tbody>${rows}</tbody></table><p class="source-links">${t('sources')}: ${fields.map(f=>`<a href="${esc(meta(f).url)}" target="_blank" rel="noopener noreferrer">${esc(meta(f).source)}</a>`).join('')}</p>`}
function economyPage(){return economicSection(t('rates'),['boc_policy_rate','goc_5y_yield','mortgage_uninsured_fixed_5plus'],'rates',{height:235})+`<h2>${t('jobs')}</h2><div class="split">${economicSection(t('unemployment'),['toronto_unemployment_rate'],'unemployment',{height:250,compact:true})}${economicSection(t('employment'),['toronto_employment_rate','toronto_participation_rate'],'employment',{height:250,compact:true})}</div>`+`<h2>${t('construction')}</h2><div class="split">${economicSection(t('starts'),['toronto_cma_2011_starts','toronto_cma_2011_completions'],'starts',{height:250,zero:true,compact:true})}${economicSection(t('stock'),['toronto_cma_2011_under_construction'],'stock',{height:250,compact:true})}</div>`+economicSection(t('population'),['toronto_cma_2021_population'],'population',{annual:true,height:235})+sourceNote()+contextTable()}
function monthlyPayment(principal,rate,years){if(principal<=0)return 0;const r=Math.pow(1+rate/200,1/6)-1,n=years*12;return r===0?principal/n:principal*r/(1-Math.pow(1+r,-n))}
function mortgagePage(){const {principal,years,rate}=state;return `<div class="controls"><label class="control">${t('principal')}<input data-number="principal" type="number" min="0" step="10000" value="${principal}"></label><label class="control">${t('years')}<input data-number="years" type="number" min="1" max="40" step="1" value="${years}"></label><label class="control">${t('rate')}<input data-number="rate" type="number" min="0" max="30" step="0.1" value="${rate}"></label></div><h2>${t('payment')}</h2><div class="payment-result">$${number(monthlyPayment(principal,rate,years),2)}</div><p class="note">${t('paymentNote')}</p>`}
function render(){chartModels=[];shell(({market:marketPage,rent:rentPage,economy:economyPage,mortgage:mortgagePage})[state.page]());attachChartTooltips()}
function attach(){
  document.querySelectorAll("[data-supply]").forEach(el=>el.onclick=()=>{state.supplyMetric=el.dataset.supply;render();document.querySelector(`[data-supply="${state.supplyMetric}"]`)?.focus()});
  document.querySelector('[data-reset]').onclick=()=>{const lang=state.lang;Object.keys(state).forEach(k=>delete state[k]);Object.assign(state,JSON.parse(JSON.stringify(initialState)),{lang});history.replaceState(null,'',location.pathname);render()};
  document.querySelectorAll('[data-district-month]').forEach(el=>el.onclick=()=>{state.end.district=el.dataset.districtMonth;render();document.querySelector('#district-section')?.setAttribute('open','')});
  document.querySelectorAll('[data-lang]').forEach(el=>el.onclick=()=>{state.lang=el.dataset.lang;render()});
  document.querySelectorAll('[data-page]').forEach(el=>el.onclick=()=>{state.page=el.dataset.page;render()});
  document.querySelectorAll('[data-mode]').forEach(el=>el.onclick=()=>{state.rentMode=el.dataset.mode;render()});
  document.querySelectorAll('[data-state]').forEach(el=>el.onchange=()=>{state[el.dataset.state]=el.value;state.regionFeedback='';render();if(el.dataset.state.startsWith('district'))document.querySelector('#district-section')?.setAttribute('open','')});
  document.querySelectorAll('[data-end]').forEach(el=>el.onchange=()=>{state.end[el.dataset.end]=el.value;render();if(el.dataset.end==='district')document.querySelector('#district-section')?.setAttribute('open','')});
  document.querySelectorAll('[data-region]').forEach(el=>el.onchange=()=>toggleRegion(el.dataset.region,Object.entries(AREAS).filter(([id])=>state.regionFrequency==='annual'?id!=='toronto':!id.includes('richmond')&&!id.includes('aurora'))));
  document.querySelectorAll('[data-map-region]').forEach(el=>{
    el.onclick=()=>toggleRegion(el.dataset.mapRegion,Object.entries(AREAS).filter(([id])=>state.regionFrequency==='annual'?id!=='toronto':!id.includes('richmond')&&!id.includes('aurora')));
    el.onkeydown=event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();el.click()}};
  });
  document.querySelectorAll('[data-number]').forEach(el=>el.oninput=()=>{
    const value=Number(el.value);
    const valid=el.value!==''&&Number.isFinite(value);
    if(valid)state[el.dataset.number]=value;
    const allValid=[...document.querySelectorAll('[data-number]')].every(input=>input.value!==''&&Number.isFinite(Number(input.value)))&&state.years>0;
    document.querySelector('.payment-result').textContent=allValid
      ? `$${number(monthlyPayment(state.principal,state.rate,state.years),2)}` : '—';
  });
}
fetch('data.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error(`HTTP ${r.status}`);return r.json()}).then(data=>{payload=data;prepare();render()}).catch(()=>{$('#app').innerHTML='<p class="message">已发布的资料快照暂时无法读取。 / Published data snapshot could not be loaded.</p>'});

let resizeFrame;window.addEventListener('resize',()=>{cancelAnimationFrame(resizeFrame);resizeFrame=requestAnimationFrame(()=>{if(!payload)return;const open=document.querySelector('#district-section')?.open;render();if(open)document.querySelector('#district-section')?.setAttribute('open','')})});
