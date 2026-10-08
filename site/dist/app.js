'use strict';
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const TEXT = {
  zh:{market:'市场总览',rent:'租赁市场',economy:'经济与供给',mortgage:'月供情景',snapshot:'数据更新于',fixed:'网站显示已发布快照；本机更新经核验和发布后才在这里生效。',date:'观察月份',year:'调查年份',price:'房价走势',sales:'成交与新增挂牌',supply:'库存月数与成交／新挂牌比',annual:'年度调查',monthly:'挂牌租金',lease:'签约租金',monthlySource:'月度挂牌租金',annualSource:'年度调查租金',dataSource:'数据',region:'地区对比',room:'房型',regionLabel:'比较地区（最多三个）',mapTitle:'地区选择地图',mapNote:'点选地区加入对比，最多三个；灰色表示该期无数据。',mapFull:'已选择三个地区，请先取消一个。',rates:'利率与融资',jobs:'就业',construction:'住宅建设',population:'人口',context:'背景指标',contextNote:'各项的地区、频率与单位不同，不能直接相加或比较。',latest:'最近值',unit:'单位',period:'资料期',geography:'地区',indicator:'指标',sources:'官方来源',impact:'与房价的关系',principal:'贷款本金（加元）',years:'摊还年限',rate:'名义年利率（%）',payment:'每月本息',paymentNote:'按固定假设计算，不代表贷款批准或利率预测。',noData:'所选范围暂无观测',notForecast:'公开数据研究工具 · 非实时行情 · 不构成投资建议',total:'全部卧室类型',studio:'开间',one:'一卧',two:'两卧',three:'三卧',threePlus:'三卧及以上',starts:'当月开工与竣工',stock:'月末在建住宅',unemployment:'失业率',employment:'就业率与劳动参与率',sourceNote:'资料来自已发布快照；不同统计边界不计算交叉比率。'},
  en:{market:'Market overview',rent:'Rental market',economy:'Economy & supply',mortgage:'Mortgage scenarios',snapshot:'Data updated',fixed:'This site shows a published snapshot. Local updates appear only after validation and publication.',date:'Observation month',year:'Survey year',price:'Home price trend',sales:'Sales and new listings',supply:'Months of inventory and sales-to-new-listings ratio',annual:'Annual survey',monthly:'Asking rents',lease:'Signed leases',monthlySource:'Monthly asking rents',annualSource:'Annual survey rents',dataSource:'Data',region:'Area comparison',room:'Bedroom type',regionLabel:'Compare areas (up to three)',mapTitle:'Select areas on map',mapNote:'Select up to three areas to compare; grey means no data for this period.',mapFull:'Three areas are selected. Remove one first.',rates:'Rates & financing',jobs:'Employment',construction:'Housing construction',population:'Population',context:'Context indicators',contextNote:'Geographies, frequencies and units differ; do not add or compare them directly.',latest:'Latest value',unit:'Unit',period:'Reference period',geography:'Geography',indicator:'Measure',sources:'Official sources',impact:'How it relates to home prices',principal:'Loan principal (CAD)',years:'Amortization years',rate:'Nominal annual rate (%)',payment:'Monthly principal & interest',paymentNote:'A fixed-assumption scenario, not a loan approval, actual household affordability or rate forecast.',noData:'No observations for this selection',notForecast:'Public-data research tool · Not live market data · Not investment advice',total:'All bedroom types',studio:'Studio',one:'1 bedroom',two:'2 bedrooms',three:'3 bedrooms',threePlus:'3+ bedrooms',starts:'Monthly starts and completions',stock:'Homes under construction at month-end',unemployment:'Unemployment rate',employment:'Employment and participation rates',sourceNote:'Values come from a published snapshot; different statistical boundaries are not combined into ratios.'}
};
const PROPERTY_TYPES = {"all_types": ["全部房型", "All property types"], "detached": ["独立屋", "Detached"], "semi_detached": ["半独立屋", "Semi-detached"], "townhouse": ["镇屋", "Townhouse"], "condo_townhouse": ["公寓镇屋", "Condo townhouse"], "condo_apartment": ["公寓", "Condo apartment"], "link": ["连接屋", "Link"], "coop_apartment": ["合作公寓", "Co-op apartment"], "detached_condo": ["独立式公寓", "Detached condo"], "coownership_apartment": ["共同产权公寓", "Co-ownership apartment"]};
let COLORS = ['#2855d9','#007f86','#bf6517','#7952be'];
// Chart colours follow the light/dark tokens in styles.css; read once per render.
function isDark(){const t=document.documentElement.dataset.theme;return t==='dark'||(t!=='light'&&matchMedia('(prefers-color-scheme: dark)').matches)}
function themeColors(){const css=getComputedStyle(document.documentElement);COLORS=['--blue','--teal','--orange','--purple'].map((v,i)=>css.getPropertyValue(v).trim()||COLORS[i])}
const ROOM = {total:'total',studio:'studio','1br':'one','2br':'two','3br':'three','3plus':'threePlus'};
const AREAS = {toronto:'Toronto',north_york:'North York',scarborough:'Scarborough',markham:'Markham',vaughan:'Vaughan',mississauga:'Mississauga',oakville:'Oakville',richmond_vaughan_king:'Richmond Hill / Vaughan / King',aurora_newmarket_whit:'Aurora / Newmarket / Whit-St.'};
const state = {lang:'zh',page:'market',rentMode:'monthly',room:'total',annualRoom:'total',regionRoom:'total',regionFrequency:'monthly',measureRoom:'1br',measureType:'apartment',bandFocus:'all',amortStep:0,priceRange:'recent',tempView:'line',leaseType:'condo',regions:['north_york','markham','scarborough'],regionFeedback:'',marketView:'level',price:1000000,down:'20',years:'25',rate:5,econRange:'2',end:{}};
const initialState=JSON.parse(JSON.stringify(state));
let payload, observations, monthly;
let chartModels = [];
const t = (key) => TEXT[state.lang][key] || key;
const meta = (field) => payload.series[field] || {zh:field,en:field,unit:'',source:'',url:''};
const name = (field) => meta(field)[state.lang] || meta(field).zh;
const number = (value,digits=0) => value==null ? '—' : Number(value).toLocaleString(state.lang==='zh'?'zh-CN':'en-CA',{maximumFractionDigits:digits,minimumFractionDigits:digits});
const axisNumber = (v) => v===0?'0':Math.abs(v)>=1000000?`${number(v/1000000,2)}M`:Math.abs(v)>=10000?`${number(v/1000,0)}k`:number(v,Math.abs(v)<100?1:0);
const monthLabel = (period) => state.lang==='zh' && /^\d{4}-\d{2}$/.test(period) ? `${period.slice(0,4)}年${Number(period.slice(5))}月` : period;
const snapshotTime = () => {const d=new Date(payload.snapshot.created_at);return isNaN(d)?payload.snapshot.created_at:d.toLocaleString(state.lang==='zh'?'zh-CN':'en-CA',{timeZone:'America/Toronto',year:'numeric',month:state.lang==='zh'?'numeric':'short',day:'numeric',hour:'2-digit',minute:'2-digit'})+(state.lang==='zh'?'（多伦多时间）':' Toronto time')};
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
  // Mortgage scenario starts from the latest observed new fixed mortgage rate.
  const mortgage=Object.keys(monthly).filter(p=>monthly[p].mortgage_uninsured_fixed_5plus!=null).sort().at(-1);
  if(mortgage){initialState.rate=monthly[mortgage].mortgage_uninsured_fixed_5plus;initialState.rateSource=mortgage;if(state.rate===5&&!state.rateSource){state.rate=initialState.rate;state.rateSource=mortgage}}
  const hpi=Object.keys(monthly).filter(p=>monthly[p].trreb_hpi_benchmark!=null).sort().at(-1);
  if(hpi){initialState.price=monthly[hpi].trreb_hpi_benchmark;initialState.priceSource=hpi;if(!state.priceSource){state.price=initialState.price;state.priceSource=hpi}}
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
  return `<details class="info"><summary aria-label="${esc(name(field))}">${iconOnly?'':esc(visible||name(field))}<span class="help-icon" aria-hidden="true">ⓘ</span></summary><div class="bubble"><strong class="bubble-title">${esc(name(field))}</strong>${m.what?`<p class="bubble-what">${esc(m.what[state.lang])}</p>`:''}<span class="bubble-label">${esc(t('impact'))}</span><p>${esc(h[0])}</p><p class="help-caveat">${esc(h[1])}</p>${link}</div></details>`;
}
// Page and rent tab live in a plain #token (the only hash form Artifact links keep), so reload and
// the back button return to the same view. Language is a per-viewer convenience in localStorage.
const PAGES=['market','rent','economy','mortgage'],RENT_MODES=['monthly','lease','annual','region'];
function routeToken(){return state.page==='rent'&&state.rentMode!=='monthly'?`rent-${state.rentMode}`:state.page}
function readRoute(){const [page,mode]=location.hash.slice(1).split('-');if(!PAGES.includes(page))return false;state.page=page;if(page==='rent')state.rentMode=RENT_MODES.includes(mode)?mode:'monthly';return true}
function go(changes){const before=state.page;Object.assign(state,changes);const token=routeToken();if(location.hash.slice(1)!==token)history.pushState(null,'',`#${token}`);render();if(state.page!==before)window.scrollTo(0,0)}
try{const saved=localStorage.getItem('gta-housing-lang');if(saved==='zh'||saved==='en')state.lang=saved}catch{}
let themeChoice='auto',hostTheme=document.documentElement.dataset.theme||null;
try{const saved=localStorage.getItem('gta-housing-theme');if(saved==='light'||saved==='dark')themeChoice=saved}catch{}
function applyTheme(){const root=document.documentElement;settingTheme=true;if(themeChoice==='auto'){if(hostTheme)root.dataset.theme=hostTheme;else delete root.dataset.theme}else root.dataset.theme=themeChoice;settingTheme=false}
let settingTheme=false;applyTheme();
readRoute();
window.addEventListener('popstate',()=>{if(!payload)return;if(!readRoute())state.page='market';render()});
// One icon button, styled like the language buttons; each click cycles auto -> light -> dark.
const THEME_ICONS={auto:'<circle cx="8" cy="8" r="6.25" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M8 1.75a6.25 6.25 0 0 1 0 12.5z" fill="currentColor"/>',
 light:'<circle cx="8" cy="8" r="3" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M8 1v1.6M8 13.4V15M1 8h1.6M13.4 8H15M3.05 3.05l1.13 1.13M11.82 11.82l1.13 1.13M3.05 12.95l1.13-1.13M11.82 4.18l1.13-1.13" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>',
 dark:'<path d="M13.5 9.6A5.75 5.75 0 0 1 6.4 2.5a5.75 5.75 0 1 0 7.1 7.1z" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>'};
function themeButton(){const zh=state.lang==='zh',names={auto:zh?'自动（跟随系统）':'Auto (system)',light:zh?'浅色':'Light',dark:zh?'深色':'Dark'},next={auto:'light',light:'dark',dark:'auto'}[themeChoice];
 const label=zh?`外观：${names[themeChoice]}。点击切换为${names[next]}`:`Appearance: ${names[themeChoice]}. Switch to ${names[next]}`;
 return `<span class="masthead-divider" aria-hidden="true"></span><button class="theme-toggle${themeChoice==='auto'?'':' set'}" data-theme-toggle title="${esc(label)}" aria-label="${esc(label)}"><svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true">${THEME_ICONS[themeChoice]}</svg></button>`}
function shell(body) {
  document.documentElement.lang=state.lang;
  document.title=`${state.page==='market'?'':t(state.page)+' · '}GTA Housing Monitor`;
  $('#app').classList.add('overview');  // every page shares the same width, header and chart sizing
  $('#app').innerHTML=`<header class="masthead"><div class="brand">GTA HOUSING MONITOR</div><div class="masthead-controls"><div class="languages" role="group" aria-label="语言 / Language"><button data-lang="zh" aria-pressed="${state.lang==='zh'}">中文</button><button data-lang="en" aria-pressed="${state.lang==='en'}">EN</button></div>${themeButton()}</div></header><nav aria-label="${state.lang==='zh'?'导航':'Navigation'}">${['market','rent','economy','mortgage'].map(p=>`<button data-page="${p}" ${p===state.page?'aria-current="page"':''}>${t(p)}</button>`).join('')}</nav>${state.page==='market'?'':`<h1>${t(state.page)}</h1>`}${body}<footer><div class="view-actions"><button data-reset>${state.lang==='zh'?'重置筛选':'Reset filters'}</button></div><p>${t('snapshot')} ${esc(snapshotTime())}</p><p>${t('notForecast')}</p></footer>`;
  attach();
}
function select(label,key,periods,annual=false,availablePeriods=periods) {
  const current=state.end[key]||periods.at(-1);
  const available=new Set(availablePeriods);
  return `<label class="control">${esc(label)}<select data-end="${esc(key)}">${[...periods].reverse().map(p=>`<option value="${esc(p)}" ${p===current?'selected':''} ${available.has(p)?'':'disabled'}>${annual?p:monthLabel(p)}</option>`).join('')}</select></label>`;
}
// TRREB's published YoY divides by a revised prior-year figure; it is preferred where printed.
const PUBLISHED_YOY={trreb_hpi_benchmark:'trreb_hpi_benchmark_yoy_published',trreb_sales:'trreb_sales_yoy_published',trreb_new_listings:'trreb_new_listings_yoy_published',trreb_active_listings:'trreb_active_listings_yoy_published'};
function metric(field,period,digits=0) {
  const v=value(field,period), prev=value(field,`${Number(period.slice(0,4))-1}${period.slice(4)}`), computed=(v!=null&&prev)?(v/prev-1)*100:null;
  const published=PUBLISHED_YOY[field]?value(PUBLISHED_YOY[field],period):null, delta=published??computed, zh=state.lang==='zh';
  const shown=field==='trreb_hpi_benchmark'?`$${number(v)}`:number(v,digits);
  const pct=delta==null?'—':`${delta>0?'▲':delta<0?'▼':''} ${number(Math.abs(delta),published!=null&&field==='trreb_hpi_benchmark'?2:1)}%`;
  const source=published!=null?(zh?'TRREB 公布':'TRREB published'):(zh?'自算':'computed');
  const detail=field==='moi_raw'?(zh?'有效挂牌 ÷ 当月成交':'active listings ÷ sales'):field==='trreb_hpi_benchmark'?`${source} · ${zh?'标准化住宅价格，不是成交均价':'standardized home, not the average sale price'}`:'';
  return `<div class="metric"><div class="metric-name">${help(field)}</div><div class="metric-value">${shown}</div><div class="metric-delta">${field==='moi_raw'?'':`<span class="delta" title="${esc(source)}">${zh?'同比':'YoY'} ${pct}</span>`}${detail?` <span>${detail}</span>`:''}</div>${v==null?`<div class="metric-asof">${zh?'本月暂无数据':'No data this month'}</div>`:''}</div>`;
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
function hpiAnnotation(periods,x,y,plotH){
  const i=periods.indexOf('2025-04');
  if(i<0)return '';
  const zh=state.lang==='zh',label=zh?'2025-04 TRREB 重设基期':'Apr 2025 TRREB rebase';
  const xx=x(i),yy=y(value('trreb_hpi_benchmark','2025-04'));
  return `<g class="hpi-annotation"><title>${esc(hpiRebaseNote())}</title><line class="hpi-guide" x1="${xx}" x2="${xx}" y1="16" y2="${plotH-30}"/><circle class="hpi-marker" cx="${xx}" cy="${yy}" r="5"/><text class="hpi-tag" x="${xx+8}" y="28">${esc(label)}</text></g>`;
}
function hpiRebaseNote(){return state.lang==='zh'?'2025 年 4 月 TRREB 发布的基准房价由 $1,068,500 变为 $1,009,400（综合指数 341.7→320.0），口径可能有变化，跨期比较需谨慎。':'In April 2025 TRREB’s published benchmark moved from $1,068,500 to $1,009,400 (composite index 341.7→320.0); the methodology may differ, so compare across that month with care.'}
function comparisonValue(field,period,mode,annual=false){
 const current=value(field,period,annual);
 if(mode==='level'||annual)return current;
 if(mode==='yoy'&&PUBLISHED_YOY[field]){const published=value(PUBLISHED_YOY[field],period);if(published!=null)return published}
 const basePeriod=previousMonth(period,mode==='mom'?1:12);
 if(field==='trreb_hpi_benchmark'&&basePeriod<'2025-04'&&period>='2025-04')return null;
 const base=value(field,basePeriod);
 if(current==null||base==null)return null;
 if(meta(field).unit==='%')return current-base;
 return base===0?null:(current/base-1)*100;
}
// Draw at the width the chart will occupy, so 11px labels stay 11px on screen.
function chartWidth(width,compact){
  const vw=Math.min(window.innerWidth,1440),pad=window.innerWidth<=760?24:80,inner=vw-2*pad-(window.innerWidth>vw?0:16);
  const split=(compact||width===616)&&window.innerWidth>760;
  return Math.round(Math.max(300,split?(inner-48)/2:inner));
}
function niceScale(min,max,count=4){
  const span=max-min||Math.abs(max)||1,raw=span/count,mag=10**Math.floor(Math.log10(raw));
  const step=[1,2,2.5,5,10].map(m=>m*mag).find(v=>v>=raw);
  return {min:Math.floor(min/step)*step,max:Math.ceil(max/step)*step,step};
}
function svgChart(fields,periods,{annual=false,zero=false,height=240,labels=null,compact=false,width=null,legend=true,unit=null,hpiNote=false,secondaryField=null,comparison='level'}={}) {
  const narrow=window.innerWidth<=480;
  const W=narrow?Math.max(300,Math.min(440,window.innerWidth-40)):chartWidth(width,compact);
  const noteHeight=0;
  const H=(narrow?220:height)+noteHeight,plotH=H-noteHeight;
  const pad={l:unit?65:(narrow?47:(compact?47:55)),r:secondaryField?65:28,t:15,b:30},innerW=W-pad.l-pad.r,innerH=plotH-pad.t-pad.b;
  const shown=(f,p)=>comparisonValue(f,p,comparison,annual);
  const vals=fields.filter(f=>f!==secondaryField).flatMap(f=>periods.map(p=>shown(f,p))).filter(v=>Number.isFinite(v));
  if(!vals.length) return `<p class="chart-empty">${t('noData')}</p>`;
  let min=zero?Math.min(0,...vals):Math.min(...vals),max=Math.max(...vals);
  if(min===max){min-=1;max+=1}
  const scale=niceScale(min,max);min=scale.min;max=scale.max;
  const tickCount=Math.round((max-min)/scale.step);
  const x=i=>pad.l+(periods.length===1?innerW/2:i*innerW/(periods.length-1));
  const y=v=>pad.t+(max-v)/(max-min)*innerH;
  const secondaryValues=secondaryField?periods.map(p=>shown(secondaryField,p)).filter(v=>Number.isFinite(v)):[];
  let secondaryMin=Math.min(...secondaryValues),secondaryMax=Math.max(...secondaryValues);
  if(secondaryMin===secondaryMax){secondaryMin-=1;secondaryMax+=1}
  const secondaryMargin=(secondaryMax-secondaryMin)*.08;
  secondaryMin-=secondaryMargin;secondaryMax+=secondaryMargin;
  const yFor=(f,v)=>f===secondaryField?pad.t+(secondaryMax-v)/(secondaryMax-secondaryMin)*innerH:y(v);
  const grids=Array.from({length:tickCount+1},(_,i)=>{const yy=pad.t+i*innerH/tickCount, vv=max-i*scale.step;return `<line class="grid-line" x1="${pad.l}" x2="${W-pad.r}" y1="${yy}" y2="${yy}"/><text class="axis-label" x="${pad.l-9}" y="${yy+4}" text-anchor="end">${axisNumber(vv)}</text>${secondaryField?`<text class="axis-label secondary-axis" x="${W-pad.r+8}" y="${yy+4}" text-anchor="start">${axisNumber(secondaryMax-i*(secondaryMax-secondaryMin)/tickCount)}</text>`:''}`}).join('');
  const step=Math.max(1,Math.ceil((periods.length-1)/(narrow?2:4)));
  const ticks=periods.map((p,i)=>i===0||i===periods.length-1||i%step===0?`<text class="axis-label" x="${x(i)}" y="${plotH-5}" text-anchor="middle">${annual?p:p.slice(2).replace('-','/')}</text>`:'').join('');
  let bridged=false;
  const lines=fields.map((f,j)=>{let paths=[],part=[],lastIndex=null;periods.forEach((p,i)=>{const v=shown(f,p);if(v==null){if(part.length){paths.push(`<path class="series-line" d="${part.join(' ')}" stroke="${COLORS[j%COLORS.length]}"/>`);part=[]}return}
    // A short source gap is bridged with a faint dashed line; no value is drawn or reported for missing periods.
    if(lastIndex!=null&&i-lastIndex>1&&i-lastIndex<=3&&!part.length){bridged=true;paths.push(`<path class="gap-bridge" d="M${x(lastIndex).toFixed(1)},${yFor(f,shown(f,periods[lastIndex])).toFixed(1)}L${x(i).toFixed(1)},${yFor(f,v).toFixed(1)}" stroke="${COLORS[j%COLORS.length]}"/>`)}
    part.push(`${part.length?'L':'M'}${x(i).toFixed(1)},${yFor(f,v).toFixed(1)}`);lastIndex=i});if(part.length)paths.push(`<path class="series-line" d="${part.join(' ')}" stroke="${COLORS[j%COLORS.length]}"/>`);return paths.join('')}).join('');
  const index=chartModels.push({fields,periods,annual,labels,W,H,pad,innerW,innerH,yFor,shown,comparison})-1;
  return `<div class="chart-area">${legend?`<div class="legend">${fields.map((f,i)=>`<span class="legend-item"><span class="legend-line series-color-${i%COLORS.length}"></span>${help(f,labels?.[f])}</span>`).join('')}</div>`:''}<div class="chart-wrap"><svg class="chart" data-chart="${index}" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(fields.map(f=>labels?.[f]||name(f)).join(', '))}">${grids}${ticks}${unit?`<text class="axis-label" transform="translate(12 ${plotH/2}) rotate(-90)" text-anchor="middle">${esc(unit)}</text>`:''}${secondaryField?`<text class="axis-label secondary-axis" transform="translate(${W-12} ${plotH/2}) rotate(90)" text-anchor="middle">CAD</text>`:''}${lines}${hpiNote?hpiAnnotation(periods,x,y,plotH):''}<line class="chart-cursor" data-cursor x1="0" x2="0" y1="${pad.t}" y2="${plotH-pad.b}" visibility="hidden"/><g data-points></g><rect class="chart-hit" x="${pad.l}" y="${pad.t}" width="${innerW}" height="${innerH}" fill="transparent" tabindex="0" role="button" aria-label="${state.lang==='zh'?'图表数据；使用左右方向键查看各期':'Chart values; use left and right arrows to inspect periods'}"/></svg><div class="chart-tooltip" hidden></div></div>${bridged?`<p class="gap-note">${state.lang==='zh'?'虚线跨过来源未发布的月份，只作连接，不代表该月数值。':'Dashed segments span months the source did not publish; they are not values for those months.'}</p>`:''}</div>`;
}
function attachChartTooltips() {
  document.querySelectorAll('[data-chart]').forEach(svg=>{
    const model=chartModels[Number(svg.dataset.chart)];
    const {fields,periods,annual,labels,W,pad,innerW,innerH,yFor,shown,comparison}=model;
    const wrap=svg.parentElement,tooltip=wrap.querySelector('.chart-tooltip');
    const cursor=svg.querySelector('[data-cursor]'),points=svg.querySelector('[data-points]');
    const x=i=>pad.l+(periods.length===1?innerW/2:i*innerW/(periods.length-1));
    let active=periods.length-1;
    function show(i) {
      active=Math.max(0,Math.min(periods.length-1,i));
      const period=periods[active],xx=x(active);
      cursor.setAttribute('x1',xx);cursor.setAttribute('x2',xx);cursor.setAttribute('visibility','visible');
      points.innerHTML=fields.map((f,j)=>{const v=shown(f,period);return v==null?'':`<circle class="chart-point" cx="${xx}" cy="${yFor(f,v)}" r="4" fill="${COLORS[j%COLORS.length]}"/>`}).join('');
      const displayed=(f)=>comparison==='level'?tooltipValue(f,shown(f,period)):shown(f,period)==null?'—':`${number(shown(f,period),1)} ${meta(f).unit==='%'?'pp':'%'}`;
      tooltip.innerHTML=`<strong>${annual?period:monthLabel(period)}</strong>${fields.map((f,j)=>`<div class="tooltip-row"><span class="tooltip-key"><i class="series-color-${j%COLORS.length}"></i>${esc(labels?.[f]||name(f))}</span><b>${esc(displayed(f))}</b></div>`).join('')}`;
      tooltip.hidden=false;
      const left=Math.max(8,Math.min(wrap.clientWidth-tooltip.offsetWidth-8,xx/W*svg.clientWidth+8));
      tooltip.style.left=`${left}px`;
      svg.querySelector('.chart-hit').setAttribute('aria-label',`${annual?period:monthLabel(period)}；${fields.map(f=>`${labels?.[f]||name(f)} ${displayed(f)}`).join('，')}`);
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
function sourceNote(){return ''}
function supplyStat(field,end,digits=0,suffix=''){
 const v=value(field,end);
 return `<div class="supply-stat"><span>${help(field)}</span><strong>${v==null?'—':number(v,digits)+suffix}</strong></div>`;
}
function editorialNote(end){
 const item=payload.editorial?.[end],valid=item&&typeof item.zh==='string'&&typeof item.en==='string'&&typeof item.author==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(item.reviewed_at||'');
 if(!valid)return '';
 return `<aside class="editorial"><h2>${state.lang==='zh'?'每月解读':'Monthly commentary'}</h2>${valid?`<p>${esc(item[state.lang])}</p><small>${esc(item.author)} · ${esc(item.reviewed_at)} · ${monthLabel(end)}</small>`:`<p class="note">${state.lang==='zh'?'本月尚无人工审核的解读。':'No manually reviewed commentary for this month.'}</p>`}</aside>`;
}
function municipalMap(period){
 const features=payload.municipal_boundaries||[];
 if(!features.length)return '';
 const zh=state.lang==='zh',previous=previousMonth(period,1),rows=payload.snapshot.districts||[];
 const byKey=new Map(rows.filter(r=>r.house_type==='all_types').map(r=>[`${r.region}|${r.ym}`,r]));
 const W=860,H=480,pad=20,bounds=[-79.91,43.36,-79.10,44.05];
 const x=lon=>pad+(lon-bounds[0])/(bounds[2]-bounds[0])*(W-2*pad);
 const y=lat=>H-pad-(lat-bounds[1])/(bounds[3]-bounds[1])*(H-2*pad);
 const ringPath=ring=>ring.map(([lon,lat],i)=>`${i?'L':'M'}${x(lon).toFixed(1)},${y(lat).toFixed(1)}`).join('')+'Z';
 const geometryPath=geometry=>(geometry.type==='Polygon'?[geometry.coordinates]:geometry.coordinates).flatMap(polygon=>polygon.map(ringPath)).join(' ');
 const colors=['#b6583d','#e2a38f','#eee9e1','#92c1ba','#187d77'];
 const color=change=>change==null?'#d6dce0':change<=-5?colors[0]:change<=-2?colors[1]:change<2?colors[2]:change<5?colors[3]:colors[4];
 const rendered=features.map(feature=>{
   const name=feature.properties.CSDNAME,region=name==='Toronto'?'City of Toronto':name;
   const current=byKey.get(`${region}|${period}`),prior=byKey.get(`${region}|${previous}`);
   const change=current?.average_price>0&&prior?.average_price>0?(current.average_price/prior.average_price-1)*100:null;
   const status=change==null?(zh?'无连续两月数据':'No consecutive observations'):`${change>=0?'+':''}${number(change,1)}%`;
   return {name,region,change,current,prior,status,path:geometryPath(feature.geometry)};
 });
 const chosen=rendered.some(item=>item.region===state.districtRegion)?state.districtRegion:'City of Toronto';
 // Draw the chosen shape last so its outline is not covered by neighbours.
 rendered.sort((a,b)=>(a.region===chosen)-(b.region===chosen));
 const shapes=rendered.map(item=>`<path class="municipal-shape" d="${item.path}" fill="${color(item.change)}" fill-rule="evenodd" data-map-csd="${esc(item.region)}" role="button" tabindex="0" aria-pressed="${item.region===chosen}" aria-label="${esc(item.name+' · '+item.status)}"><title>${esc(item.name+' · '+item.status)}</title></path>`).join('');
 const centers={Toronto:[-79.36,43.69],Markham:[-79.29,43.88],Vaughan:[-79.56,43.84],Mississauga:[-79.68,43.61],Oakville:[-79.73,43.46],'Richmond Hill':[-79.44,43.90],Aurora:[-79.45,43.99],Brampton:[-79.76,43.73]};
 const labels=rendered.map(item=>{const [lon,lat]=centers[item.name];return `<text class="municipal-label" x="${x(lon).toFixed(1)}" y="${y(lat).toFixed(1)}" text-anchor="middle">${esc(item.name)}</text>`}).join('');
 const legend=colors.map((fill,i)=>`<span><i data-bg="${fill}"></i>${['≤ −5%','−5 to −2%','−2 to +2%','+2 to +5%','≥ +5%'][i]}</span>`).join('')+`<span><i data-bg="#d6dce0"></i>${zh?'无数据':'No data'}</span>`;
 return `<section class="municipal-map"><div class="chart-heading"><h2>${zh?'市镇成交均价环比地图':'Municipal average sale price change'}</h2><span class="caption">${monthLabel(previous)} → ${monthLabel(period)}</span></div><p class="note">${zh?'全部房型成交均价的环比，不是 HPI。点选市镇查看该市镇本月数字。':'Month-over-month change in average sale price, all home types; not HPI. Select an area to see its figures.'}</p><div class="map-layout"><svg viewBox="0 0 ${W} ${H}" role="group" aria-label="${zh?'市镇环比涨跌地图':'Municipal month-over-month map'}">${shapes}${labels}</svg>${mapDetail(rendered.find(item=>item.region===chosen),period,previous)}</div><div class="map-legend" aria-label="${zh?'环比涨跌图例':'Month-over-month legend'}">${legend}</div><p class="map-credit">${zh?'边界：Statistics Canada 2021；数值：TRREB。':'Boundaries: Statistics Canada 2021; values: TRREB.'} <a href="https://geo.statcan.gc.ca/geo_wa/rest/services/2021/Cartographic_boundary_files/MapServer/9" target="_blank" rel="noopener noreferrer">${zh?'边界来源':'Boundary source'} ↗</a></p><table class="context-table municipal-table"><thead><tr><th>${zh?'市镇':'Municipality'}</th><th>${zh?'环比':'Monthly change'}</th><th>${zh?'当月均价':'Current average'}</th><th>${zh?'成交':'Sales'}</th></tr></thead><tbody>${rendered.map(item=>`<tr><th scope="row">${esc(item.name)}</th><td data-label="${zh?'环比':'Monthly change'}">${item.status}</td><td data-label="${zh?'当月均价':'Current average'}">${item.current?.average_price>0?'$'+number(item.current.average_price):'—'}</td><td data-label="${zh?'成交':'Sales'}">${item.current?.sales>0?number(item.current.sales):'—'}</td></tr>`).join('')}</tbody></table></section>`;
}
function mapDetail(item,period,previous){
 if(!item)return '';
 const zh=state.lang==='zh',c=item.current,pr=item.prior,money=v=>v==null?'—':'$'+number(v,0),count=v=>v==null?'—':number(v,0);
 const dir=item.change==null?'':item.change>=0?' up':' down';
 const rows=[[zh?'成交均价':'Average price',money(c?.average_price),pr?.average_price?`${zh?'上月':'Prior'} ${money(pr.average_price)}`:''],
  [zh?'中位价':'Median price',money(c?.median_price),''],
  [zh?'成交':'Sales',count(c?.sales),pr?.sales!=null?`${zh?'上月':'Prior'} ${count(pr.sales)}`:''],
  [zh?'新增挂牌':'New listings',count(c?.new_listings),''],
  [zh?'在售挂牌':'Active listings',count(c?.active_listings),''],
  [zh?'成交价／挂牌价':'Sale-to-list',c?.avg_sp_lp==null?'—':number(c.avg_sp_lp,0)+'%',''],
  [zh?'平均挂牌天数':'Avg. listing days',count(c?.avg_ldom),'']];
 return `<aside class="map-detail" aria-live="polite"><h3>${esc(item.name)}</h3><p class="caption">${zh?'全部房型':'All home types'} · ${monthLabel(period)}</p>
 <p class="map-change${dir}"><b>${esc(item.status)}</b><span>${zh?`均价环比（对比 ${monthLabel(previous)}）`:`average price vs ${monthLabel(previous)}`}</span></p>
 <dl>${rows.map(([k,v,sub])=>`<div><dt>${k}</dt><dd>${v}${sub?`<small>${sub}</small>`:''}</dd></div>`).join('')}</dl>
 ${c&&pr&&c.sales<50?`<p class="note">${zh?'成交不足 50 宗，均价易受个别大额成交影响。':'Fewer than 50 sales; one large sale can move the average.'}</p>`:''}
 <button class="map-more" data-jump-district>${zh?'看这个市镇的 36 个月走势 ↓':'See its 36-month trend ↓'}</button></aside>`;
}
function segmented(key,options,current,label){return `<div class="segmented" role="group" aria-label="${esc(label)}">${options.map(([id,text])=>`<button data-pick="${esc(key)}" data-value="${esc(id)}" aria-pressed="${current===id}">${esc(text)}</button>`).join('')}</div>`}
function marketPage(){
 const fields=['trreb_hpi_benchmark','trreb_sales','moi_raw'];
 const end=last(fields,false,'market');if(!end)return `<p>${t('noData')}</p>`;
 const periods=viewPeriods(fields,end),zh=state.lang==='zh',comparison=state.marketView;
 const views=[['level',zh?'原值':'Values'],['mom',zh?'环比':'MoM'],['yoy',zh?'同比':'YoY']];
 return `<div class="overview-heading"><div><h1>${t('market')}</h1><p class="caption">${zh?'TRREB 全市场 · 全部房型':'All TRREB areas · All home types'}</p></div>${select(t('date'),'market',allPeriods(fields))}</div>
 ${sectionNav()}
 <div class="overview-hero">${metric('trreb_hpi_benchmark',end)}${temperatureCard(end)}</div>
 <div class="kpi-strip">${metric('trreb_sales',end)}${metric('trreb_new_listings',end)}${metric('trreb_active_listings',end)}${metric('moi_raw',end,2)}</div>
${pricePanel(end,periods,comparison,views)}
 ${temperatureSection(end)}
 <section class="supply-dashboard" id="sec-supply"><div class="split overview-support"><div><h2>${t('sales')}</h2>${svgChart(['trreb_sales','trreb_new_listings'],periods,{height:230,width:616,zero:comparison==='level',unit:comparison==='level'?(zh?'笔 / 套':'Sales / listings'):'%',comparison})}</div><div><h2>${help('moi_raw')}</h2>${svgChart(['moi_raw'],periods,{height:230,width:616,zero:comparison==='level',legend:false,unit:comparison==='level'?(zh?'月':'Months'):'%',comparison})}</div></div></section>
 ${priceBands(end)}${regionsPanel(end)}${editorialNote(end)}<details class="overview-sources"><summary>${zh?'来源与口径':'Sources and definitions'}</summary>${sourceNote()}<p class="note">${t('fixed')}</p><a href="https://trreb.ca/market-data/market-watch/" target="_blank" rel="noopener noreferrer">TRREB Market Watch ↗</a></details>`;
}
const SECTIONS=[['sec-price',['价格','Prices']],['sec-temp',['温度','Temperature']],['sec-supply',['供需','Supply']],['sec-mix',['价格段','Price bands']],['regions-panel',['地区','Areas']]];
function sectionNav(){const L=state.lang==='zh'?0:1;return `<div class="section-nav" role="navigation" aria-label="${L?'On this page':'本页内容'}">${SECTIONS.map(([id,label])=>`<button data-jump="${id}">${label[L]}</button>`).join('')}</div>`}
function pricePanel(end,periods,comparison,views){
 const zh=state.lang==='zh',range=state.priceRange==='long'&&observations.teranet_toronto_index_sa?'long':'recent';
 const ranges=[['recent',zh?'近 2 年 · HPI':'2 years · HPI'],['long',zh?'1998 年起 · Teranet':'Since 1998 · Teranet']];
 return `<section class="price-panel" id="sec-price"><div class="chart-heading"><h2>${t('price')}</h2><div class="heading-controls">${segmented('priceRange',ranges,range,zh?'时间跨度':'Time span')}${range==='long'?'':segmented('marketView',views,comparison,zh?'价格及供需图表显示方式':'Price and supply chart mode')}</div></div>${range==='long'?longRunBody():`${comparison==='level'?'':`<p class="note comparison-note">${(comparison==='yoy'?(zh?'房价、成交与新增挂牌的同比使用 TRREB 公布值（以修订后的上年同月为分母）；其余同比按原发布值自算，前期缺失时留空。':'Price, sales and new-listing YoY use TRREB published figures, which divide by revised prior-year values. Other YoY values are computed from original releases and stay blank without a base.'):(zh?'前期缺失、分母为零或 HPI 跨 2025-04 口径断点时留空；百分比指标显示百分点差，其余显示百分比变化。':'Missing bases, zero denominators and HPI comparisons across April 2025 stay blank. Rate measures show percentage-point differences; others show percent changes.'))}</p>`}${svgChart(['trreb_hpi_benchmark'],periods,{height:300,width:1280,legend:false,unit:comparison==='level'?'CAD':'%',hpiNote:comparison==='level',comparison})}<p class="note">${zh?'基准价格是标准化住宅的价格，不是成交均价。':'The benchmark is the price of a standardized home, not the average sale price.'} ${periods.includes('2025-04')?esc(hpiRebaseNote()):''}</p>`}</section>`;
}
function longRunBody(){
 const f='teranet_toronto_index_sa',series=observations[f];if(!series)return '';
 const zh=state.lang==='zh',periods=Object.keys(series).sort(),last=periods.at(-1),peakPeriod=periods.reduce((a,p)=>series[p]>series[a]?p:a,periods[0]);
 const fromPeak=(series[last]/series[peakPeriod]-1)*100,tenYear=series[previousMonth(last,120)],decade=tenYear?(series[last]/tenYear-1)*100:null;
 const pct=v=>`${v>0?'+':v<0?'−':''}${number(Math.abs(v),1)}%`;
 return `<div class="long-run"><p class="long-run-stats"><span>${monthLabel(periods[0])} — ${monthLabel(last)}</span><span>${zh?`较 ${monthLabel(peakPeriod)} 高点 <b>${pct(fromPeak)}</b>`:`<b>${pct(fromPeak)}</b> from the ${peakPeriod} peak`}</span>${decade==null?'':`<span>${zh?`十年 <b>${pct(decade)}</b>`:`<b>${pct(decade)}</b> over ten years`}</span>`}</p>${svgChart([f],periods,{height:240,width:1280,legend:false,unit:zh?'指数':'Index'})}<p class="note">${zh?'Teranet–National Bank 多伦多重复交易指数（季调，2005 年 6 月 = 100）：按产权登记（交割）日期，比 MLS 签约晚 1–3 个月，独立屋占比较高；与「近 2 年 · HPI」视图的口径不同，不能直接对比数值。':'Teranet–National Bank Toronto repeat-sales index (seasonally adjusted, June 2005 = 100): dated at registration (closing), 1–3 months after the MLS sale, with a heavier detached weighting. A different measure from the 2-year HPI view; do not compare levels.'}</p></div>`;
}
function regionsPanel(end){
 const map=municipalMap(end),district=districtSection();
 if(!map&&!district)return '';
 const zh=state.lang==='zh';
 return `<details id="regions-panel" class="sec-anchor" data-sec="sec-areas"><summary><span><strong>${zh?'地区与市镇':'Areas and municipalities'}</strong><small>${zh?'市镇地图，按地区和房型比较均价、成交与挂牌':'Municipal map; compare prices, sales and listings by area and home type'}</small></span></summary>${map}${district}</details>`;
}
const TEMPERATURE_LABELS={cool:['偏冷','Cool'],balanced:['平衡','Balanced'],hot:['偏热','Hot']};
const TEMPERATURE_NOTE={cool:['买方议价空间较大','buyers have more leverage'],balanced:['供需大致平衡','supply and demand roughly balanced'],hot:['卖方占优','sellers have the upper hand']};
function temperatureReading(end){
 const t=payload.market_temperature;if(!t)return null;
 const period=Object.keys(t.months).filter(p=>p<=end).sort().at(-1);
 return period?{t,period,r:t.months[period]}:null;
}
function temperatureCard(end){
 const reading=temperatureReading(end);if(!reading)return '<div></div>';
 const {t,period,r}=reading,zh=state.lang==='zh',L=zh?0:1,band=t.band_pp;
 const lim=Math.max(30,Math.ceil(Math.abs(r.gap)/10)*10),pos=(Math.max(-lim,Math.min(lim,r.gap))+lim)/(2*lim)*100;
 const side=(lim-band)/(2*lim)*100,mid=band/lim*100;
 const gapText=`${r.gap>0?'+':r.gap<0?'−':''}${number(Math.abs(r.gap),1)}`;
 const zones=[['cool',side],['balanced',mid],['hot',side]];
 return `<section class="temp-card" aria-label="${zh?'市场温度':'Market temperature'}"><div class="temp-card-head"><h2>${zh?'市场温度':'Market temperature'}</h2><span class="temperature-chip ${r.state}">${TEMPERATURE_LABELS[r.state][L]}</span><span class="caption">${monthLabel(period)} · ${zh?'近三个月':'last three months'}</span></div>
 <div class="gauge" role="img" aria-label="${esc((zh?'与同月常态相差 ':'Gap to seasonal norm ')+gapText+(zh?' 个百分点':' pp'))}"><span class="gauge-marker" data-left="${pos.toFixed(1)}"><b>${gapText}</b></span><div class="gauge-track">${zones.map(([k,w])=>`<span class="zone ${k}" data-width="${w.toFixed(2)}"></span>`).join('')}</div><div class="gauge-labels">${zones.map(([k,w])=>`<span class="${k===r.state?'current':''}" data-width="${w.toFixed(2)}">${TEMPERATURE_LABELS[k][L]}</span>`).join('')}</div></div>
 <p>${zh?`近三个月成交／新挂牌比 ${number(r.snlr3,1)}%，比同期历史常态 ${number(r.snlr_norm,1)}% ${r.gap<0?'低':'高'} ${number(Math.abs(r.gap),1)} 个百分点：${TEMPERATURE_NOTE[r.state][0]}。近三个月库存月数 ${number(r.moi3,1)}（同期常态 ${number(r.moi_norm,1)}）。`:`Three-month sales-to-new-listings ratio ${number(r.snlr3,1)}%, ${number(Math.abs(r.gap),1)} pp ${r.gap<0?'below':'above'} its seasonal norm of ${number(r.snlr_norm,1)}%: ${TEMPERATURE_NOTE[r.state][1]}. Three-month months of inventory ${number(r.moi3,1)} (norm ${number(r.moi_norm,1)}).`}</p></section>`;
}
function temperatureChart(months,periods,band,W){
 const H=230,pad={l:40,r:12,t:10,b:24},iw=W-pad.l-pad.r,ih=H-pad.t-pad.b;
 const values=periods.map(p=>months[p]?.gap??null),finite=values.filter(v=>v!=null);
 const lim=Math.max(30,Math.ceil(Math.max(...finite.map(Math.abs))/10)*10);
 const x=i=>pad.l+(periods.length===1?iw/2:i*iw/(periods.length-1)),y=v=>pad.t+(lim-v)/(2*lim)*ih;
 const ticks=[-lim,-band,0,band,lim].map(v=>`<line class="${v===0?'zero-line':'grid-line'}" x1="${pad.l}" x2="${W-pad.r}" y1="${y(v)}" y2="${y(v)}"/><text class="axis-label" x="${pad.l-8}" y="${y(v)+4}" text-anchor="end">${v>0?'+':v<0?'−':''}${Math.abs(v)}</text>`).join('');
 let d='',open=false;values.forEach((v,i)=>{if(v==null){open=false;return}d+=`${open?'L':'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`;open=true});
 const step=Math.max(1,Math.ceil((periods.length-1)/(W<500?2:3)));
 const xt=periods.map((p,i)=>i===0||i===periods.length-1||(i%step===0&&periods.length-1-i>=step/2)?`<text class="axis-label" x="${x(i)}" y="${H-6}" text-anchor="${i===0?'start':i===periods.length-1?'end':'middle'}">${p.slice(2).replace('-','/')}</text>`:'').join('');
 const last=values.length-1;
 tempGuide={periods,xs:periods.map((_,i)=>x(i))};
 return `<svg class="chart temperature-chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="${state.lang==='zh'?'成交／新挂牌比与同月常态之差':'Sales-to-new-listings ratio minus seasonal norm'}"><rect class="temp-hot" x="${pad.l}" y="${y(lim)}" width="${iw}" height="${y(band)-y(lim)}"/><rect class="temp-cool" x="${pad.l}" y="${y(-band)}" width="${iw}" height="${y(-lim)-y(-band)}"/><text class="temp-label" x="${W-pad.r-6}" y="${y(lim)+14}" text-anchor="end">${TEMPERATURE_LABELS.hot[state.lang==='zh'?0:1]}</text><text class="temp-label" x="${W-pad.r-6}" y="${y(-lim)-6}" text-anchor="end">${TEMPERATURE_LABELS.cool[state.lang==='zh'?0:1]}</text>${ticks}${xt}<path class="series-line" d="${d}" stroke="${COLORS[0]}"/>${values[last]!=null?`<circle class="chart-point" cx="${x(last)}" cy="${y(values[last])}" r="4" fill="${COLORS[0]}"/>`:''}<line class="temp-guide" data-temp-guide x1="0" x2="0" y1="${pad.t}" y2="${H-pad.b}" visibility="hidden"/></svg>`;
}
function temperatureSection(end){
 const reading=temperatureReading(end);if(!reading)return '';
 const {t,period,r}=reading,zh=state.lang==='zh',L=zh?0:1;
 const periods=Object.keys(t.months).filter(p=>p<=period).sort().slice(-36);
 const full=chartWidth(1280,false),W=window.innerWidth>900?Math.round(full*0.62):full,view=state.tempView==='heat'?'heat':'line';
 const rows=['cool','balanced','hot'].map(k=>{const o=t.outcomes_12m[k],change=o.mean_change==null?'—':`${o.mean_change>0?'+':o.mean_change<0?'−':''}${number(Math.abs(o.mean_change),1)}%`;return `<div class="outcome-row${k===r.state?' current':''}"><span class="outcome-name">${TEMPERATURE_LABELS[k][L]}${k===r.state?`<small>${zh?'当前':'now'}</small>`:''}</span><b>${change}</b><span class="outcome-meta">${o.share_up==null?'—':number(o.share_up*100,0)+'%'} ${zh?'上涨':'rose'} · ${o.n} ${zh?'个月':'months'}</span></div>`}).join('');
 const views=[['line',zh?'近 3 年走势':'3-year trend'],['heat',zh?'逐月热力图':'Monthly heatmap']];
 const left=view==='heat'?seasonHeatmap(end):`${temperatureChart(t.months,periods,t.band_pp,W)}<p class="note">${zh?`高于常态 ${t.band_pp} 个百分点以上为偏热，低于 ${t.band_pp} 个百分点以上为偏冷。`:`Hot when ${t.band_pp} pp or more above the norm, cool when ${t.band_pp} pp or more below.`}</p>`;
 return `<section class="temperature" id="sec-temp"><div class="chart-heading"><div><h2>${zh?'市场温度':'Market temperature'}</h2><p class="caption">${zh?'成交／新挂牌比 − 同月常态 · 个百分点':'Sales-to-new-listings ratio minus seasonal norm · pp'}</p></div>${segmented('tempView',views,view,zh?'显示方式':'View')}</div>
 <div class="temperature-grid"><div>${left}</div>
 <div class="outcomes"><h3>${zh?'历史上，各温度之后 12 个月的 HPI':'HPI over the following 12 months, by reading'}</h3><div role="table" aria-label="${zh?'各温度之后 12 个月 HPI 平均变化':'Average HPI change 12 months after each reading'}">${rows}</div><p class="note">${zh?'2012 年以来 TRREB HPI 统计。描述供需，不是预测；样本外研究显示对 6–12 个月方向有参考意义。':'TRREB HPI since 2012. Describes market balance, not a forecast; out-of-sample research found it informative about direction 6–12 months ahead.'}</p></div></div></section>`;
}
// ---- Linked charts (Figma 12): heatmap and price-band mix share the observation month,
// the dumbbell row picks the rent bedroom type, and the rate table drives the amortization bars.
let tempGuide=null;
const COOL_RGB=[40,85,217],HOT_RGB=[191,101,23];
function gapColor(v){const base=isDark()?[44,48,55]:[243,243,243],k=Math.min(1,Math.abs(v)/30),to=v<0?COOL_RGB:HOT_RGB;return `rgb(${base.map((c,i)=>Math.round(c+(to[i]-c)*k)).join(',')})`}
const signed=(v,d=1)=>`${v>0?'+':v<0?'−':''}${number(Math.abs(v),d)}`;
function seasonHeatmap(end){
 const t=payload.market_temperature;if(!t)return '';
 const zh=state.lang==='zh',L=zh?0:1,months=t.months,keys=Object.keys(months).sort();
 const lastYear=Number(keys.at(-1).slice(0,4)),firstYear=Math.max(2012,Number(keys[0].slice(0,4)));
 const years=[];for(let y=firstYear;y<=lastYear;y++)years.push(y);
 const selectable=new Set(allPeriods(['trreb_hpi_benchmark','trreb_sales','moi_raw']));
 const selected=keys.filter(p=>p<=end).at(-1);
 const full=chartWidth(1280,false),W=window.innerWidth>900?Math.round(full*0.62):full,narrow=W<560;
 const lw=narrow?34:42,cw=(W-lw)/12,ch=narrow?17:22,top=20,H=top+years.length*ch;
 const head=Array.from({length:12},(_,m)=>narrow&&m%3?'':`<text class="axis-label" x="${(lw+m*cw+cw/2).toFixed(1)}" y="12" text-anchor="middle">${zh?`${m+1}月`:['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][m]}</text>`).join('');
 let cells='',labels='',sel='';
 years.forEach((y,r)=>{labels+=`<text class="axis-label" x="0" y="${(top+r*ch+ch*0.68).toFixed(1)}">${narrow?String(y).slice(2):y}</text>`;
  for(let m=0;m<12;m++){const p=`${y}-${String(m+1).padStart(2,'0')}`,v=months[p];if(!v)continue;
   const x=(lw+m*cw).toFixed(1),yy=(top+r*ch).toFixed(1),tip=`${monthLabel(p)} · ${signed(v.gap)} ${zh?'个百分点':'pp'} · ${TEMPERATURE_LABELS[v.state][L]}`,pick=selectable.has(p);
   cells+=`<rect class="heat-cell${pick?' pickable':''}" x="${x}" y="${yy}" width="${(cw-2).toFixed(1)}" height="${ch-2}" rx="2" fill="${gapColor(v.gap)}" data-tip="${esc(tip)}" data-heat="${p}"${pick?` data-pick-month="${p}" tabindex="0" role="button" aria-label="${esc(tip)}"`:''}/>`;
   if(p===selected)sel=`<rect class="heat-selected" x="${(lw+m*cw-1.5).toFixed(1)}" y="${(top+r*ch-1.5).toFixed(1)}" width="${(cw+1).toFixed(1)}" height="${ch+1}" rx="3"/>`}});
 // A plain-language reading: the current run of same-temperature months and the last hot spell.
 let run=0;for(let i=keys.indexOf(selected);i>=0&&months[keys[i]].state===months[selected].state;i--)run++;
 const lastHot=keys.filter(p=>p<=selected&&months[p].state==='hot').at(-1);
 const ramp=[-30,-20,-10,0,10,20,30].map(v=>`<i data-bg="${gapColor(v)}"></i>`).join('');
 return `<div class="heatmap-block"><svg class="chart heatmap" viewBox="0 0 ${W} ${H}" role="group" aria-label="${zh?'市场温度逐月热力图':'Market temperature heatmap'}">${head}${labels}${cells}${sel}</svg>
 <div class="heat-legend"><div class="heat-ramp">${ramp}</div><div class="heat-ramp-labels"><span>${zh?'偏冷':'Cool'} −30</span><span>0</span><span>+30 ${zh?'偏热':'Hot'}</span></div></div>
 <p class="heat-reading">${zh?`${monthLabel(selected)} 为${TEMPERATURE_LABELS[months[selected].state][0]}，已连续 ${run} 个月${TEMPERATURE_LABELS[months[selected].state][0]}${lastHot?`；上一次偏热是 ${monthLabel(lastHot)}`:''}。`:`${selected} reads ${TEMPERATURE_LABELS[months[selected].state][1].toLowerCase()}, ${run} month${run>1?'s':''} in a row${lastHot?`; the last hot month was ${lastHot}`:''}.`}</p>
 <p class="note">${zh?`一行一年（${firstYear}—${lastYear}）。点 2022 年 9 月以后的格子：整页切到该月。`:`One row per year (${firstYear}–${lastYear}). Select a cell from September 2022 on to move the whole page to that month.`}</p></div>`;
}
const BAND_LIGHT=['#9ad0d3','#4fb0b6','#007f86','#2855d9','#1b3a99','#0f1f55'],BAND_DARK=['#bfe6e8','#74c6cb','#2fb3a7','#6f8ff5','#4a63d1','#3a4aa8'];
let BAND_COLORS=BAND_LIGHT;
function bandShares(period){const counts=PRICE_BANDS.map(f=>value(f,period));if(counts.some(v=>v==null))return null;const total=counts.reduce((a,b)=>a+b,0);return total?counts.map(v=>v/total*100):null}
const bandName=i=>name(PRICE_BANDS[i]).replace(/^成交价\s*/,'').replace(/^Sold\s+/,'');
function priceBands(end){
 const zh=state.lang==='zh',all=allPeriods(PRICE_BANDS).filter(p=>bandShares(p));
 if(!all.length||!bandShares(end))return '';
 const latest=all.at(-1),stop=end<all.at(-25)?end:latest,periods=all.filter(p=>p<=stop).slice(-25),shares=periods.map(bandShares);
 const focus=/^[0-5]$/.test(String(state.bandFocus))?Number(state.bandFocus):null;
 const full=chartWidth(1280,false),W=window.innerWidth>900?Math.round(full*0.62):full,narrow=W<560;
 const L=36,H=240,top=8,step=(W-L)/periods.length,bw=Math.max(4,step*0.78);
 const y=v=>top+H-v/100*H;
 const grid=[0,25,50,75,100].map(v=>`<line class="grid-line" x1="${L}" x2="${W}" y1="${y(v)}" y2="${y(v)}"/><text class="axis-label" x="${L-6}" y="${y(v)+4}" text-anchor="end">${v}%</text>`).join('');
 const lab=Math.max(1,Math.ceil(periods.length/(narrow?3:5)));
 const cols=periods.map((p,i)=>{let acc=0;const x=L+i*step+(step-bw)/2;
  const segs=shares[i].map((v,k)=>{const yy=y(acc+v),h=v/100*H;acc+=v;return `<rect class="band-seg" x="${x.toFixed(1)}" y="${yy.toFixed(1)}" width="${bw.toFixed(1)}" height="${Math.max(0,h-0.6).toFixed(1)}" fill="${BAND_COLORS[k]}"${focus!=null&&focus!==k?' opacity="0.22"':''}/>`}).join('');
  const label=focus!=null&&(i===0||i===periods.length-1||p===end)?`<text class="band-focus-label" x="${(x+bw/2).toFixed(1)}" y="${(y(shares[i].slice(0,focus+1).reduce((a,b)=>a+b,0))-4).toFixed(1)}" text-anchor="middle">${number(shares[i][focus],1)}%</text>`:'';
  const tip=`${monthLabel(p)} · `+shares[i].map((v,k)=>`${bandName(k)} ${number(v,1)}%`).join(' · ');
  const tick=i%lab===0||i===periods.length-1?`<text class="axis-label" x="${(x+bw/2).toFixed(1)}" y="${top+H+16}" text-anchor="middle">${p.slice(2).replace('-','/')}</text>`:'';
  return `<g class="band-col" data-pick-month="${p}" data-tip="${esc(tip)}" tabindex="0" role="button" aria-label="${esc(tip)}"><rect class="band-hit" x="${(L+i*step).toFixed(1)}" y="${top}" width="${step.toFixed(1)}" height="${H}"/>${segs}${label}</g>${tick}`}).join('');
 const si=periods.indexOf(end),sel=si<0?'':`<rect class="heat-selected" x="${(L+si*step+(step-bw)/2-2.5).toFixed(1)}" y="${top-2.5}" width="${(bw+5).toFixed(1)}" height="${H+5}" rx="3"/>`;
 const legend=PRICE_BANDS.map((_,k)=>`<button class="band-legend${focus===k?' active':''}" data-pick="bandFocus" data-value="${focus===k?'all':k}" aria-pressed="${focus===k}"><i data-bg="${BAND_COLORS[k]}"></i>${esc(bandName(k))}</button>`).join('');
 const now=bandShares(end),before=bandShares(previousMonth(end,12));
 const rows=PRICE_BANDS.map((_,k)=>`<div class="mix-row"><span><i data-bg="${BAND_COLORS[k]}"></i>${esc(bandName(k))}</span><b>${number(now[k],1)}%</b><small>${before?signed(now[k]-before[k]):'—'}</small></div>`).join('');
 const change=shares.at(-1).map((v,k)=>v-shares[0][k]),up=change.indexOf(Math.max(...change)),down=change.indexOf(Math.min(...change));
 const insight=zh?`${monthLabel(periods[0])} 到 ${monthLabel(periods.at(-1))}，${bandName(up)}的占比从 ${number(shares[0][up],1)}% 变为 ${number(shares.at(-1)[up],1)}%，${bandName(down)}从 ${number(shares[0][down],1)}% 变为 ${number(shares.at(-1)[down],1)}%。`:`From ${periods[0]} to ${periods.at(-1)}, ${bandName(up)} moved from ${number(shares[0][up],1)}% to ${number(shares.at(-1)[up],1)}% of sales, and ${bandName(down)} from ${number(shares[0][down],1)}% to ${number(shares.at(-1)[down],1)}%.`;
 return `<section class="price-bands" id="sec-mix"><div class="chart-heading"><h2>${zh?'成交价格段构成':'Sales by price band'}</h2><span class="caption">${zh?'各价格段占当月成交的比例':'Share of each month’s sales'}</span></div><div class="band-legends" role="group" aria-label="${zh?'只看某一价格段':'Focus on one band'}">${legend}</div>
 <div class="temperature-grid"><svg class="chart band-mix" viewBox="0 0 ${W} ${top+H+24}" role="group" aria-label="${zh?'价格段构成，近 25 个月':'Price-band mix, last 25 months'}">${grid}${cols}${sel}</svg>
 <div class="mix-side"><p>${insight}</p><div class="mix-detail"><strong>${monthLabel(end)}${zh?' · 较上年同月（个百分点）':' · change vs a year earlier (pp)'}</strong>${rows}</div><p class="note">${zh?'点柱子切换观察月份；点图例只看一个价格段。反映成交构成，不是房价指数。':'Select a column to change the month; select a legend item to focus on one band. Reflects the sales mix, not a price index.'}</p></div></div></section>`;
}
function rentDumbbell(){
 const zh=state.lang==='zh',L=zh?0:1,type=state.measureType==='townhouse'?'townhouse':'apartment',measures=RENT_MEASURES[type];
 const selectedRoom=['studio','1br','2br','3br'].includes(state.measureRoom)?state.measureRoom:'1br';
 const rooms=[['studio',t('studio')],['1br',t('one')],['2br',t('two')],['3br',t('three')+(zh?'*':'*')]];
 const data=rooms.map(([room])=>measures.map(([id,field,annual,color,label,source])=>{const f=field(room),o=f&&latestObservation(f);if(!o)return {missing:true,reason:f?(zh?'样本太少，不显示':'too few units'):(zh?'该来源没有这一房型':'no such category'),label,color,source};
  const when=annual?(zh?`${o.period} 年 10 月`:`Oct ${o.period}`):id==='lease'?quarterLabel(o.period):monthLabel(o.period);return {value:o.value,label,color,source,when}}));
 const values=data.flat().filter(d=>!d.missing).map(d=>d.value);if(!values.length)return '';
 const lo=Math.floor((Math.min(...values)-100)/500)*500,hi=Math.ceil((Math.max(...values)+100)/500)*500;
 const W=chartWidth(980,false),lw=56,rw=78,rh=44,top=4,H=top+rooms.length*rh+26,pw=W-lw-rw;
 const X=v=>lw+(v-lo)/(hi-lo)*pw;
 let ticks='';for(let v=lo;v<=hi;v+=500){if(W<520&&(v-lo)%1000)continue;ticks+=`<line class="grid-line" x1="${X(v).toFixed(1)}" x2="${X(v).toFixed(1)}" y1="${top}" y2="${top+rooms.length*rh}"/><text class="axis-label" x="${X(v).toFixed(1)}" y="${H-6}" text-anchor="middle">$${number(v)}</text>`}
 const rowsSvg=rooms.map(([room,label],i)=>{const y=top+i*rh+rh/2,pts=data[i],vals=pts.filter(d=>!d.missing).map(d=>d.value),sel=room===selectedRoom;
  const lineEl=vals.length>1?`<line class="db-line" x1="${X(Math.min(...vals)).toFixed(1)}" x2="${X(Math.max(...vals)).toFixed(1)}" y1="${y}" y2="${y}"/>`:'';
  const dots=pts.map(d=>d.missing?`<circle class="db-missing" cx="${lw-12}" cy="${y}" r="5" data-tip="${esc(`${label} · ${d.label[L]} · ${d.reason}`)}"/>`:`<circle class="db-dot" cx="${X(d.value).toFixed(1)}" cy="${y}" r="6.5" fill="${d.color}" data-tip="${esc(`${label} · ${d.label[L]} · $${number(d.value)} · ${d.when} · ${d.source}`)}"/>`).join('');
  const gap=vals.length>1?`<text class="axis-label" x="${(X(Math.max(...vals))+12).toFixed(1)}" y="${y+4}">${zh?'差':'gap'} $${number(Math.max(...vals)-Math.min(...vals))}</text>`:'';
  return `<g class="db-row${sel?' selected':''}" data-pick-room="${room}" tabindex="0" role="button" aria-pressed="${sel}" aria-label="${esc(label)}"><rect class="db-hit" x="0" y="${top+i*rh+3}" width="${W}" height="${rh-6}" rx="6"/><text class="db-label" x="0" y="${y+4}">${esc(label)}</text>${lineEl}${dots}${gap}</g>`}).join('');
 const legend=measures.map(([id,field,annual,color,label,source,meaning])=>{const o=latestObservation(field('1br'))||latestObservation(field('2br'));const when=o?(annual?(zh?`${o.period} 年 10 月`:`Oct ${o.period}`):id==='lease'?quarterLabel(o.period):monthLabel(o.period)):'';return `<div class="db-legend-item"><i data-bg="${color}"></i><span><b>${esc(label[L])}</b> <small>${source} · ${esc(when)}</small><br><small class="db-meaning">${esc(meaning[L])}</small></span></div>`}).join('');
 return `<section class="rent-measures"><div class="chart-heading"><div><h2>${zh?'同一房型，不同口径的租金':'One unit type, different rent measures'}</h2><p class="caption">${zh?'点一行，下方走势切到该房型；悬停看来源与时间':'Select a row to show that unit type below; hover for source and date'}</p></div>${segmented('measureType',[['apartment',zh?'公寓':'Apartment'],['townhouse',zh?'镇屋':'Townhouse']],type,zh?'物业类型':'Property type')}</div>
 <div class="db-legend">${legend}</div><svg class="chart dumbbell" viewBox="0 0 ${W} ${H}" role="group" aria-label="${zh?'各房型不同口径租金':'Rent measures by unit type'}">${ticks}${rowsSvg}</svg>
 <p class="note">${zh?'* CMHC 为三卧及以上；空心虚线点表示该口径没有这一房型。独立屋、半独立屋和单间合租暂无可靠公开数据。':'* CMHC figures are 3+ bedrooms; a hollow dashed dot means that measure has no such unit type. Detached and semi-detached houses and shared rooms have no reliable public series.'}</p></section>`;
}
function amortization(loan,rate,years){const r=Math.pow(1+rate/200,1/6)-1,pay=monthlyPayment(loan,rate,years);let bal=loan;const out=[];for(let y=1;y<=years;y++){let p=0,i=0;for(let k=0;k<12;k++){const int=bal*r,pr=Math.min(bal,pay-int);i+=int;p+=pr;bal-=pr}out.push({year:y,principal:p,interest:i,balance:Math.max(0,bal)})}return out}
function amortChart(m,rate){
 const zh=state.lang==='zh',rows=amortization(m.loan,rate,m.years);if(!rows.length||m.loan<=0)return '';
 // Drawn at the results column's width (page width minus the 400px inputs and the 64px gap) so labels stay 11px.
 const full=chartWidth(1280,false),W=window.innerWidth>900?Math.max(420,full-464):full,H=210,L=48,top=10,max=Math.max(...rows.map(r=>r.principal+r.interest)),scale=niceScale(0,max,4);
 const y=v=>top+H-v/scale.max*H,step=(W-L)/rows.length,bw=step*0.74;
 let grid='';for(let v=0;v<=scale.max+1e-9;v+=scale.step)grid+=`<line class="grid-line" x1="${L}" x2="${W}" y1="${y(v).toFixed(1)}" y2="${y(v).toFixed(1)}"/><text class="axis-label" x="${L-6}" y="${(y(v)+4).toFixed(1)}" text-anchor="end">${v?'$'+axisNumber(v):'0'}</text>`;
 const bars=rows.map((r,i)=>{const x=L+i*step+(step-bw)/2,tip=zh?`第 ${r.year} 年：本金 ${money(r.principal)} · 利息 ${money(r.interest)} · 年末剩余 ${money(r.balance)}`:`Year ${r.year}: principal ${money(r.principal)} · interest ${money(r.interest)} · balance ${money(r.balance)}`;
  const edge=r.year===rows.length?'end':r.year===1?'start':'middle',tx=edge==='end'?x+bw:edge==='start'?x:x+bw/2;
  const tick=r.year===1||r.year%5===0?`<text class="axis-label" x="${tx.toFixed(1)}" y="${top+H+16}" text-anchor="${edge}">${zh?`第${r.year}年`:`Y${r.year}`}</text>`:'';
  return `<g class="amort-bar" data-tip="${esc(tip)}" tabindex="0" aria-label="${esc(tip)}"><rect x="${x.toFixed(1)}" y="${y(r.principal).toFixed(1)}" width="${bw.toFixed(1)}" height="${(H+top-y(r.principal)).toFixed(1)}" fill="#007f86"/><rect x="${x.toFixed(1)}" y="${y(r.principal+r.interest).toFixed(1)}" width="${bw.toFixed(1)}" height="${Math.max(0,y(r.principal)-y(r.principal+r.interest)-0.6).toFixed(1)}" fill="#bf6517"/></g>${tick}`}).join('');
 const cross=rows.find(r=>r.principal>r.interest),cx=cross?L+(cross.year-1)*step+step/2:null;
 const crossEl=cross?`<line class="amort-cross" x1="${cx.toFixed(1)}" x2="${cx.toFixed(1)}" y1="${top}" y2="${top+H}"/><text class="amort-cross-label" x="${(cx+6).toFixed(1)}" y="${top+12}">${zh?`第 ${cross.year} 年起本金超过利息`:`Principal exceeds interest from year ${cross.year}`}</text>`:'';
 const five=rows.slice(0,5),paid5=five.reduce((a,r)=>a+r.principal+r.interest,0),int5=five.reduce((a,r)=>a+r.interest,0),total=rows.reduce((a,r)=>a+r.interest,0);
 const facts=[[zh?'前 5 年共还':'Paid in the first 5 years',money(Math.round(paid5/100)*100)],[zh?'其中利息':'of which interest',`${money(Math.round(int5/100)*100)}（${number(int5/paid5*100,0)}%）`],[zh?`${m.years} 年利息合计`:`Interest over ${m.years} years`,money(Math.round(total/100)*100)]];
 if(rows[9])facts.push([zh?'第 10 年末剩余本金':'Balance after year 10',money(Math.round(rows[9].balance/100)*100)]);
 return `<div class="amort"><div class="chart-heading"><h3>${zh?`每年还的钱：本金与利息（${number(rate,2)}%）`:`Each year’s payments: principal and interest (${number(rate,2)}%)`}</h3><span class="legend"><span class="legend-item"><i data-bg="#007f86"></i>${zh?'本金':'Principal'}</span><span class="legend-item"><i data-bg="#bf6517"></i>${zh?'利息':'Interest'}</span></span></div>
 <svg class="chart amort-chart" viewBox="0 0 ${W} ${top+H+24}" role="group" aria-label="${zh?'逐年本金与利息':'Principal and interest by year'}">${grid}${bars}${crossEl}</svg>
 <div class="amort-facts">${facts.map(([a,b])=>`<div><span>${a}</span><b>${b}</b></div>`).join('')}</div></div>`;
}
const PRICE_BANDS=['trreb_sales_band_under_500k','trreb_sales_band_500k_800k','trreb_sales_band_800k_1m','trreb_sales_band_1m_1_5m','trreb_sales_band_1_5m_2m','trreb_sales_band_2m_plus'];
function previousMonth(period,offset){
 const date=new Date(Date.UTC(Number(period.slice(0,4)),Number(period.slice(5))-1-offset,1));
 return `${date.getUTCFullYear()}-${String(date.getUTCMonth()+1).padStart(2,'0')}`;
}
function districtSparkline(rows,period,field,unit){
 const byMonth=new Map(rows.map(r=>[r.ym,r[field]]));
 const periods=Array.from({length:6},(_,i)=>previousMonth(period,5-i));
 const values=periods.map(p=>byMonth.get(p));
 const valid=values.filter(v=>Number.isFinite(v));
 if(valid.length<2)return `<span class="sparkline-empty">—</span>`;
 let low=Math.min(...valid),high=Math.max(...valid);if(low===high){low-=1;high+=1}
 const x=i=>5+i*20,y=v=>23-(v-low)/(high-low)*18;
 const segments=[];let points=[];
 values.forEach((v,i)=>{if(!Number.isFinite(v)){if(points.length>1)segments.push(points.join(' '));points=[]}else points.push(`${x(i)},${y(v).toFixed(1)}`)});
 if(points.length>1)segments.push(points.join(' '));
 const description=periods.map((p,i)=>`${p}: ${values[i]==null?'—':number(values[i],unit==='CAD'?0:1)}`).join('; ');
 return `<svg class="sparkline" viewBox="0 0 110 30" role="img" tabindex="0" aria-label="${esc(description)}"><title>${esc(description)}</title>${segments.map(s=>`<polyline points="${s}"/>`).join('')}</svg>`;
}
function districtSection(){
 const rows=payload.snapshot.districts||[]; if(!rows.length)return '';
 state.districtType ||= 'all_types';state.districtRegion ||= 'Markham';state.districtMetric ||= 'average_price';
 const types=[...new Set(rows.map(r=>r.house_type))].sort();
 const chosen=rows.filter(r=>r.house_type===state.districtType);
 const areas=[...new Set(chosen.map(r=>r.region))].sort();
 if(!areas.includes(state.districtRegion))state.districtRegion=areas[0];
 const fields={average_price:['均价','Average price','CAD'],sales:['成交','Sales','sales'],new_listings:['新增挂牌','New listings','listings'],active_listings:['在售挂牌','Active listings','listings'],median_price:['中位价','Median price','CAD'],avg_ldom:['挂牌天数','Listing days','days'],avg_pdom:['物业在市天数','Property days on market','days'],avg_sp_lp:['成交价／挂牌价','Sale-to-list price ratio','%']};
 const field='district_selected',definition=fields[state.districtMetric];
 payload.series[field]={zh:state.districtRegion+' · '+definition[0],en:state.districtRegion+' · '+definition[1],unit:definition[2],source:'TRREB',url:'https://trreb.ca/market-data/market-watch/market-watch-archive/'};
 for(const period of Object.keys(monthly))delete monthly[period][field];
 const selected=chosen.filter(r=>r.region===state.districtRegion);
 for(const row of selected){monthly[row.ym]||={};monthly[row.ym][field]=row[state.districtMetric]}
 const options=(key,items,label)=>`<label class="control">${label}<select data-state="${key}">${items.map(([v,n])=>`<option value="${esc(v)}" ${state[key]===v?'selected':''}>${esc(n)}</option>`).join('')}</select></label>`;
 const periods=selected.map(r=>r.ym).sort(),end=last([field],false,'district');
 const controls=options('districtType',types.map(v=>[v,PROPERTY_TYPES[v]?.[state.lang==='zh'?0:1]||v]),state.lang==='zh'?'转售房型':'Property type')+options('districtRegion',areas.map(v=>[v,v]),t('region'))+options('districtMetric',Object.entries(fields).map(([v,d])=>[v,d[state.lang==='zh'?0:1]]),t('indicator'))+select(t('date'),'district',periods);
 const entries=selected.filter(r=>r.ym<=end).slice(-36);
 return `<section id="district-section"><h2>${state.lang==='zh'?'地区转售明细':'District resale'}</h2><div class="controls">${controls}</div><p class="note">${state.lang==='zh'?'均价受成交构成影响，不是 HPI；每行小图各自缩放。':'Average prices depend on the sales mix and are not HPI; each mini-chart scales independently.'}</p>${svgChart([field],entries.map(r=>r.ym))}<table class="context-table"><thead><tr><th>${t('period')}</th><th>${t('latest')}</th><th>${state.lang==='zh'?'近六个月':'Six-month trend'}</th></tr></thead><tbody>${entries.slice(-12).reverse().map(r=>`<tr><td data-label="${t('period')}"><button data-district-month="${r.ym}">${monthLabel(r.ym)}</button></td><td data-label="${t('latest')}">${number(r[state.districtMetric])}</td><td data-label="${state.lang==='zh'?'近六个月':'Six-month trend'}">${districtSparkline(selected,r.ym,state.districtMetric,definition[2])}</td></tr>`).join('')}</tbody></table></section>`;
}
function tabButtons(key,options,current){return `<div class="tabs" role="tablist">${options.map(([id,label])=>`<button role="tab" data-${key}="${id}" aria-selected="${current===id}">${esc(label)}</button>`).join('')}</div>`}
function areaField(region,annual,room){return annual?`regional_cmhc_${region}_pbr_rent_${room}`:region==='toronto'?`toronto_asking_rent_${room}`:`regional_asking_${region}_${room}`}
function toggleRegion(region,choices){
  if(!choices.some(([id])=>id===region))return;
  state.regionFeedback='';
  if(state.regions.includes(region))state.regions=state.regions.filter(id=>id!==region);
  else if(state.regions.length<3)state.regions.push(region);
  else state.regionFeedback=t('mapFull');
  render();
}
// Each source names bedroom types differently; a null field means the source has no such category.
const plus=r=>r==='3br'?'3plus':r;
const RENT_MEASURES={
 apartment:[
  ['asking',r=>r==='studio'?null:`toronto_asking_rent_${r}`,false,'#2855d9',['挂牌租金','Asking rent'],'Rentals.ca',['房东开价。最快反映新租约行情，但不是成交价。','What landlords ask. Fastest read on new leases, but not a signed rent.']],
  ['lease',r=>`gta_condo_lease_rent_${r==='studio'?'bachelor':r}`,false,'#007f86',['签约租金 · condo','Signed lease · condo'],'TRREB',['经 MLS 实际租出的 condo 平均月租。季度更新。','Average rent on condos actually leased through the MLS. Quarterly.']],
  ['condo',r=>`toronto_condo_rent_${plus(r)}`,true,'#bf6517',['年度调查 · condo','Annual survey · condo'],'CMHC',['含已住租客的平均实租。每年一次，变化最慢。','Average rent actually paid, including sitting tenants. Yearly; moves slowest.']],
  ['pbr',r=>`toronto_pbr_rent_${plus(r)}`,true,'#7952be',['年度调查 · 专建出租','Annual survey · purpose-built'],'CMHC',['专门建来出租的公寓，多为长期租客。','Buildings built as rentals; mostly long-term tenants.']]],
 townhouse:[
  ['lease',r=>`gta_townhouse_lease_rent_${r==='studio'?'bachelor':r}`,false,'#007f86',['签约租金 · 镇屋','Signed lease · townhouse'],'TRREB',['经 MLS 实际租出的镇屋平均月租。季度更新。','Average rent on townhouses actually leased through the MLS. Quarterly.']],
  ['row',r=>`toronto_row_rent_${plus(r)}`,true,'#7952be',['年度调查 · 专建出租镇屋','Annual survey · purpose-built townhouses'],'CMHC',['专门建来出租的联排镇屋，含已住租客。','Townhouse rentals built as such, including sitting tenants.']]]};
function latestObservation(field){const periods=Object.keys(observations[field]||{}).sort();const period=periods.at(-1);return period?{period,value:observations[field][period]}:null}
function roomPicker(key,rooms){if(!rooms.includes(state[key]))state[key]='total';return segmented(key,rooms.map(r=>[r,r==='total'&&state.lang==='zh'?'全部':r==='total'?'All':t(ROOM[r])]),state[key],t('room'))}
function rentPage(){
  const zh=state.lang==='zh';
  let out=rentDumbbell()+tabButtons('mode',[['monthly',t('monthly')],['lease',t('lease')],['annual',t('annual')],['region',t('region')]],state.rentMode);
  if(state.rentMode==='monthly'){
    const room=state.room,fields=room==='total'?['toronto_asking_rent_total','toronto_asking_rent_1br','toronto_asking_rent_2br'].filter(f=>observations[f]):[`toronto_asking_rent_${room}`];
    const key=fields[0],periods=allPeriods([key]),end=last([key]);
    const labels=room==='total'?{toronto_asking_rent_total:zh?'全部':'All',toronto_asking_rent_1br:t('one'),toronto_asking_rent_2br:t('two')}:null;
    out+=`<div class="chart-heading rent-heading"><h2>${zh?'挂牌租金走势':'Asking rent trend'}</h2><div class="heading-controls">${roomPicker('room',['total','1br','2br','3br'])}${select(t('date'),key,periods)}</div></div>${end?svgChart(fields,viewPeriods([key],end),{height:280,labels}):`<p>${t('noData')}</p>`}<p class="note">${zh?`Rentals.ca / Urbanation 月度挂牌报价，涵盖专建出租公寓与 condo，未季调；不等于签约租金。${room==='total'?'分房型数据自 2025 年 11 月起。':''}`:`Rentals.ca / Urbanation monthly asking rents for purpose-built apartments and condos, not seasonally adjusted; not signed rents.${room==='total'?' Bedroom-level data start in November 2025.':''}`}</p>`;
    return out;
  }
  if(state.rentMode==='lease'){
    const town=state.leaseType==='townhouse',prefix=town?'gta_townhouse_lease_rent_':'gta_condo_lease_rent_';
    const rooms=(town?[]:[['bachelor',zh?'开间':'Studio']]).concat([['1br',t('one')],['2br',t('two')],['3br',t('three')]]);
    const fields=rooms.map(([r])=>prefix+r).filter(f=>observations[f]),periods=allPeriods(fields);
    const picker=segmented('leaseType',[['condo',zh?'condo 公寓':'Condo apartments'],['townhouse',zh?'镇屋':'Townhouses']],town?'townhouse':'condo',zh?'物业类型':'Property type');
    if(!periods.length)return out+picker+`<p>${t('noData')}</p>`;
    const labels=Object.fromEntries(rooms.map(([r,l])=>[prefix+r,l]));
    const latest=periods.at(-1),prior=previousMonth(latest,12);
    const cards=rooms.filter(([r])=>observations[prefix+r]).map(([r,l])=>{const f=prefix+r,v=value(f,latest),b=value(f,prior),d=v!=null&&b?(v/b-1)*100:null;return `<div class="supply-stat"><span>${l}</span><strong>$${number(v)}</strong><small>${d==null?'—':`${d>0?'+':d<0?'−':''}${number(Math.abs(d),1)}%`} ${zh?'较上年同季':'vs a year earlier'}</small></div>`}).join('');
    out+=`<div class="chart-heading rent-heading"><div><h2>${town?(zh?'镇屋平均签约租金':'Average signed townhouse rent'):(zh?'condo 公寓平均签约租金':'Average signed condo rent')}</h2><p class="caption">${quarterLabel(latest)}</p></div>${picker}</div><div class="supply-stats">${cards}</div>${svgChart(fields,periods,{height:255,labels,unit:zh?'加元/月':'CAD/month'})}<p class="note">${town?(zh?'经 TRREB MLS 租出的镇屋，按季度统计的实际签约月租；开间镇屋每季只有个位数成交，不显示。不含独立屋和半独立屋。':'Townhouses leased through TRREB’s MLS; quarterly averages of signed rent. Studio townhouses (single-digit leases a quarter) are not shown. Detached and semi-detached houses are not covered.'):(zh?'经 TRREB MLS 租出的 condo 公寓，按季度统计的实际签约月租。':'Condo apartments leased through TRREB’s MLS; quarterly averages of signed monthly rent.')}</p>`;
    return out;
  }
  if(state.rentMode==='annual'){
    roomPicker('annualRoom',['total','studio','1br','2br','3plus']);
    const fields=[`toronto_pbr_rent_${state.annualRoom}`,`toronto_condo_rent_${state.annualRoom}`,`toronto_row_rent_${state.annualRoom}`].filter(f=>observations[f]),periods=allPeriods(fields,true),end=last(fields,true);
    out+=`<div class="chart-heading rent-heading"><h2>${zh?'CMHC 年度租金调查':'CMHC annual rent survey'}</h2><div class="heading-controls">${roomPicker('annualRoom',['total','studio','1br','2br','3plus'])}${select(t('year'),fields.join('-'),periods,true)}</div></div>${end?svgChart(fields,viewPeriods(fields,end,true),{annual:true,height:255}):`<p>${t('noData')}</p>`}<p class="note">${zh?'每年 10 月调查，含已住租客；均值变化并非同一套住房的租金涨幅。':'Surveyed each October, including sitting tenants; changes in averages are not same-unit rent growth.'}</p>`;
    return out;
  }
  const annual=state.regionFrequency==='annual';
  const choices=Object.entries(AREAS).filter(([id])=>annual?id!=='toronto':!id.includes('richmond')&&!id.includes('aurora'));
  state.regions=state.regions.filter(id=>choices.some(([candidate])=>candidate===id));
  const rooms=annual?['total','studio','1br','2br','3plus']:['total','1br','2br','3br'];
  const picker=roomPicker('regionRoom',rooms);
  const fields=state.regions.map(r=>areaField(r,annual,state.regionRoom));
  const present=fields.filter(f=>observations[f]);
  const missing=state.regions.filter((r,i)=>!observations[fields[i]]).map(r=>AREAS[r]);
  const periods=present.length?allPeriods(present,annual):[];
  const end=present.length?last(present,annual):null;
  const chartPeriods=end?(annual?viewPeriods(present,end,true):calendarViewPeriods(present,end)):[];
  const names=Object.fromEntries(state.regions.map((r,i)=>[fields[i],AREAS[r]]));
  const chips=state.regions.map((r,i)=>{const at=present.indexOf(fields[i]);return `<span class="region-chip${at<0?' unavailable':''}"><i data-bg="${at<0?'#c4c4c4':COLORS[at%COLORS.length]}"></i>${esc(AREAS[r])}<button data-remove-region="${esc(r)}" aria-label="${esc((zh?'移除 ':'Remove ')+AREAS[r])}">×</button></span>`}).join('');
  const remaining=choices.filter(([id])=>!state.regions.includes(id));
  const add=state.regions.length<3?`<select class="add-region" data-add-region aria-label="${zh?'添加地区':'Add area'}"><option value="">${zh?'＋ 添加地区':'＋ Add area'}</option>${remaining.map(([id,label])=>`<option value="${esc(id)}">${esc(label)}</option>`).join('')}</select>`:`<span class="add-region full">${zh?'已选三个地区':'Three areas selected'}</span>`;
  out+=`<div class="chart-heading rent-heading"><div><h2>${t('region')}</h2><p class="caption">${zh?'最多三个地区；用“添加地区”加入':'Up to three areas; add them from the list'}</p></div>${segmented('regionFrequency',[['monthly',t('monthlySource')],['annual',t('annualSource')]],state.regionFrequency,t('dataSource'))}</div>`;
  out+=`<div class="region-controls"><div class="region-chips" role="group" aria-label="${t('regionLabel')}">${chips}${add}</div><div class="heading-controls"><span class="control-label">${t('room')}</span>${picker}${chartPeriods.length?select(annual?t('year'):t('date'),present.join('-'),chartPeriods,annual,periods):''}</div></div>`;
  if(missing.length)out+=`<p class="message">${esc(missing.join(zh?'、':', '))}${zh?' 未提供该房型的数据，图中不显示，也不用总体代替。':' has no data for this unit type; it is left out rather than replaced with the overall average.'}</p>`;
  out+=end?svgChart(present,chartPeriods,{annual,height:260,labels:names}):`<p class="chart-empty">${t('noData')}</p>`;
  return out;
}
const ECON_RANGES={'1':13,'2':25,'5':61,all:null};
function rangePeriods(fields,annual=false){const all=allPeriods(fields,annual),n=ECON_RANGES[state.econRange];return n?all.slice(-n):all}
function economicChart(title,fields,opts={},caption=''){const periods=rangePeriods(fields,!!opts.annual);return `<section class="economic-panel"><div class="chart-heading"><h2>${title}</h2>${opts.unitLabel?`<span class="caption">${esc(opts.unitLabel)}</span>`:''}</div>${periods.length?svgChart(fields,periods,opts):`<p>${t('noData')}</p>`}${caption?`<p class="note">${caption}</p>`:''}</section>`}
function latestRaw(field){const keys=Object.keys(observations[field]||{}).sort();const period=keys.at(-1);return period?{period,value:observations[field][period]}:null}
function yearAgoRaw(field,period){const keys=Object.keys(observations[field]||{}).sort();const target=`${Number(period.slice(0,4))-1}${period.slice(4)}`;const key=keys.filter(k=>k<=target).at(-1);return key&&key.slice(0,7)===target.slice(0,7)?observations[field][key]:null}
function econMetric(field,digits=2){
 const zh=state.lang==='zh',latest=latestRaw(field);if(!latest)return '';
 const before=yearAgoRaw(field,latest.period),when=latest.period.length>7?latest.period:monthLabel(latest.period);
 return `<div class="metric"><div class="metric-name">${help(field)}</div><div class="metric-value">${number(latest.value,digits)}%</div><div class="metric-delta">${esc(when)}${before==null?'':` · ${zh?'一年前':'a year earlier'} ${number(before,digits)}%`}</div></div>`;
}
const CONTEXT_GROUPS=[[['新房与建设','New homes & construction'],['toronto_starts_','toronto_cmhc_','toronto_permits_','toronto_nhpi','toronto_residential_construction']],[['房价（其他来源）','Prices (other sources)'],['teranet_']],[['利率与通胀','Rates & inflation'],['boc_conventional','boc_prime','ontario_cpi']],[['人口流动','Migration'],['ontario_net_']],[['外部因素','External factors'],['usd_cad','wti_','boc_energy','canada_policy']]];
const UNIT_ZH={units:'套','CAD/month':'加元/月',persons:'人','%':'%','USD/barrel':'美元/桶','CAD/USD':'加元/美元'};
const CONTEXT_ORDER=['toronto_nhpi_total','toronto_starts_condo','toronto_starts_rental','toronto_starts_homeowner','toronto_cmhc_absorptions','toronto_cmhc_unabsorbed_inventory','toronto_permits_units','toronto_residential_construction_cost_index'];
function contextTable(){
 const data=payload.snapshot.context||{},zh=state.lang==='zh',L=zh?0:1;
 const order=f=>{const i=CONTEXT_ORDER.indexOf(f);return i<0?50:i};
 const row=f=>{const v=data[f],rawUnit=meta(f).unit,unit=zh&&UNIT_ZH[rawUnit]?UNIT_ZH[rawUnit]:rawUnit;const quarterly=f==='toronto_residential_construction_cost_index'||f.startsWith('ontario_net_');const digits=f==='usd_cad_monthly'?4:f==='toronto_residential_construction_cost_index'||f==='toronto_nhpi_total'||f.startsWith('teranet_')?1:f.startsWith('ontario_net_')||rawUnit==='units'?0:2;const shown=`${number(v?.value,digits)}${unit==='%'?'%':unit&&!/index/i.test(unit)?' '+unit:''}`;const status=payload.snapshot.freshness?.[f]?.status;const flag=['overdue','missing','unknown'].includes(status)?`<span class="stale-flag">${esc(freshnessLabel(f))}</span>`:'';return `<tr><th scope="row">${help(f)}${flag}</th><td>${esc(shown)}</td><td>${esc(quarterly&&v?quarterLabel(v.period):v?monthLabel(v.period):'—')}</td></tr>`};
 const groups=CONTEXT_GROUPS.map(([label,prefixes],i)=>{const fields=Object.keys(data).filter(f=>prefixes.some(p=>f.startsWith(p))).sort((a,b)=>order(a)-order(b)||name(a).localeCompare(name(b)));if(!fields.length)return '';return `<details class="context-group" ${i===0?'open':''}><summary><span><strong>${label[L]}</strong><small>${fields.length} ${zh?'项':fields.length===1?'measure':'measures'}</small></span></summary><table class="context-table compact"><tbody>${fields.map(row).join('')}</tbody></table><p class="source-links">${[...new Map(fields.map(f=>[meta(f).url,meta(f).source])).entries()].map(([url,source])=>`<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">${esc(source)} ↗</a>`).join('')}</p></details>`}).join('');
 return `<section class="context-section"><h2>${t('context')}</h2><p class="note">${t('contextNote')}</p>${groups}<p class="note">${zh?'签约租金已在「租赁市场」展示，不在此重复；更新状态只在需要核查时标出。':'Signed rents appear on the rental page and are not repeated here; update status is flagged only when it needs checking.'}</p></section>`;
}
function populationStat(){
 const zh=state.lang==='zh',f='toronto_cma_2021_population',latest=latestRaw(f);if(!latest)return '';
 const prior=observations[f][String(Number(latest.period)-1)],d=prior!=null?latest.value-prior:null;
 const change=d==null?'':`${zh?'较上年':'vs prior year'} ${d>0?'+':d<0?'−':''}${number(Math.abs(d))} ${zh?'人':'people'}${zh?'（':' ('}${d>0?'+':d<0?'−':''}${number(Math.abs(d/prior*100),2)}%${zh?'）':')'}`;
 return `<section class="population-stat"><div><div class="metric-name">${help(f)}</div><strong>${number(latest.value)}</strong></div><p>${zh?`${latest.period} 年 7 月 1 日 · ${change}。每年只有一个估计值，用数字而不是曲线展示。`:`July 1, ${latest.period} · ${change}. One estimate a year, shown as a number rather than a line.`}</p></section>`;
}
function economyPage(){
 const zh=state.lang==='zh',l=f=>latestRaw(f);
 const emp=l('toronto_employment_rate'),part=l('toronto_participation_rate'),stock=l('toronto_cma_2011_under_construction');
 const ranges=[['1',zh?'1 年':'1 yr'],['2',zh?'2 年':'2 yrs'],['5',zh?'5 年':'5 yrs'],['all',zh?'全部':'All']];
 const rateFields=['boc_policy_rate','goc_5y_yield','mortgage_uninsured_fixed_5plus'];
 return `<div class="page-intro"><p class="caption">${zh?'利率、就业和住宅建设：影响房价的背景条件':'Rates, jobs and construction: background conditions for home prices'}</p><div class="range-control"><span class="control-label">${zh?'时间范围（全页）':'Time range (whole page)'}</span>${segmented('econRange',ranges,state.econRange,zh?'时间范围':'Time range')}</div></div>
 <div class="kpi-strip econ-kpis">${econMetric('boc_policy_rate')}${econMetric('mortgage_uninsured_fixed_5plus')}${econMetric('toronto_unemployment_rate',1)}${econMetric('ontario_mortgage_arrears_rate')}</div>
 ${economicChart(t('rates'),rateFields,{height:240,labels:{goc_5y_yield:zh?'5 年期国债收益率（月均）':'5-year GoC yield (monthly average)'},unitLabel:'%'},zh?'按揭利率由银行每月报送，比央行利率和国债收益率晚约两个月公布。':'Banks report mortgage rates monthly, about two months after policy rates and bond yields.')}
 <div class="split econ-split">${economicChart(t('unemployment'),['toronto_unemployment_rate'],{height:230,compact:true,unitLabel:'%'},emp&&part?(zh?`就业率 ${number(emp.value,1)}% · 劳动参与率 ${number(part.value,1)}%（${monthLabel(emp.period)}）`:`Employment rate ${number(emp.value,1)}% · participation ${number(part.value,1)}% (${emp.period})`):'')}${economicChart(t('starts'),['toronto_cma_2011_starts','toronto_cma_2011_completions'],{height:230,zero:true,compact:true,unitLabel:zh?'套 / 月':'units / month'},stock?(zh?`月末在建 ${number(stock.value)} 套（${monthLabel(stock.period)}）· 多伦多 CMA`:`${number(stock.value)} units under construction at month-end (${stock.period}) · Toronto CMA`):'')}</div>
 ${populationStat()}${contextTable()}`;
}
function monthlyPayment(principal,rate,years){if(principal<=0)return 0;const r=Math.pow(1+rate/200,1/6)-1,n=years*12;return r===0?principal/n:principal*r/(1-Math.pow(1+r,-n))}
function mortgageModel(){
 const price=Math.max(0,Number(state.price)||0),down=Number(state.down),years=Number(state.years),rate=Number(state.rate);
 const loan=price*(1-down/100),pay=monthlyPayment(loan,rate,years),qualifying=Math.max(rate+2,5.25),stress=monthlyPayment(loan,qualifying,years);
 return {price,down,years,rate,loan,pay,qualifying,stress,income:stress*12/0.39,interest:pay*years*12-loan,valid:Number.isFinite(rate)&&rate>=0&&years>0};
}
const money=(v,d=0)=>`$${number(v,d)}`;
function mortgageResults(){
 const m=mortgageModel(),zh=state.lang==='zh';if(!m.valid)return `<p class="chart-empty">${zh?'请输入有效的利率。':'Enter a valid rate.'}</p>`;
 const steps=[-1,0,1,2].map(d=>m.rate+d).filter(r=>r>=0);
 const offset=[-1,0,1,2].includes(Number(state.amortStep))&&m.rate+Number(state.amortStep)>=0?Number(state.amortStep):0,chartRate=m.rate+offset;
 const sens=steps.map(r=>{const p=monthlyPayment(m.loan,r,m.years),diff=p-m.pay,cur=Math.abs(r-m.rate)<1e-9,chosen=Math.abs(r-chartRate)<1e-9;return `<div class="sens-col${cur?' current':''}${chosen?' chosen':''}" data-amort-step="${Math.round(r-m.rate)}" tabindex="0" role="button" aria-pressed="${chosen}"><span>${number(r,2)}%</span><strong>${money(p)}</strong><small>${cur?(zh?'当前假设':'current'):`${diff>0?'+':'−'}${money(Math.abs(diff))}`}</small></div>`}).join('');
 return `<div class="payment-main"><span class="metric-name">${t('payment')}</span><div><span class="payment-result">${money(m.pay,2)}</span><span class="per">${zh?'/ 月':'/ month'}</span></div><p class="caption">${zh?`${m.years} 年共付利息约 ${money(Math.round(m.interest/100)*100)}`:`About ${money(Math.round(m.interest/100)*100)} of interest over ${m.years} years`}</p></div>
 <div class="mortgage-cards"><div class="mortgage-card"><strong>${zh?'压力测试月供':'Stress-test payment'}</strong><span>${money(m.stress,2)}</span><p>${zh?`按 ${number(m.qualifying,2)}% 计算：合同利率 +2 个百分点与 5.25% 取较高者，银行用它审核贷款。`:`At ${number(m.qualifying,2)}%: the higher of the contract rate + 2 points and 5.25%, which lenders use to qualify borrowers.`}</p></div><div class="mortgage-card"><strong>${zh?'大约需要的家庭年收入':'Approximate household income needed'}</strong><span>${money(Math.round(m.income/1000)*1000)}</span><p>${zh?'按压力测试月供不超过收入 39% 估算；未含物业税、取暖和 condo 管理费，实际要求更高。':'Stress-test payment at no more than 39% of income; excludes property tax, heating and condo fees, so the real requirement is higher.'}</p></div></div>
 <div class="sensitivity"><h3>${zh?'如果利率变化':'If the rate changes'}</h3><div class="sens-row">${sens}</div><p class="note">${zh?'点任一列，下图切到该利率。':'Select a column to show that rate below.'}</p></div>
 ${amortChart(m,chartRate)}
 <p class="note">${t('paymentNote')}</p>`;
}
function mortgageHints(){
 const m=mortgageModel(),zh=state.lang==='zh',notes=[];
 if(m.down<20)notes.push(zh?'首付低于 20% 需另付按揭保险费，此处未计入。':'Below 20% down, mortgage insurance is required; its premium is not included.');
 if(m.down<20&&m.price>1500000)notes.push(zh?'房价超过 150 万加元须至少 20% 首付。':'Homes over $1.5 million need at least 20% down.');
 if(m.down<20&&m.years===30)notes.push(zh?'首付不足 20% 时，30 年摊还仅限首次购房或新建住宅。':'With under 20% down, 30-year amortization is limited to first-time buyers or new builds.');
 return notes.map(n=>`<p class="message">${esc(n)}</p>`).join('');
}
function mortgagePage(){
 const zh=state.lang==='zh',m=mortgageModel();
 const hpi=state.priceSource?(zh?`默认：${monthLabel(state.priceSource)} TRREB HPI 综合基准房价`:`Default: TRREB HPI composite benchmark, ${state.priceSource}`):'';
 const rateHint=state.rateSource?(zh?`默认：${monthLabel(state.rateSource)} 银行新发 5 年以上固定按揭平均利率`:`Default: banks’ average new 5-year-plus fixed rate, ${state.rateSource}`):'';
 return `<p class="caption page-sub">${zh?'从房价出发估算每月本息 · 加元 · 半年复利（加拿大惯例）':'Monthly principal and interest from a home price · CAD · compounded semi-annually (Canadian convention)'}</p>
 <div class="mortgage-layout"><div class="mortgage-inputs">
 <label class="field"><span class="control-label">${zh?'房价':'Home price'}</span><input class="money-input" data-money="price" inputmode="numeric" autocomplete="off" value="${esc(money(m.price))}"><small>${esc(hpi)}</small></label>
 <div class="field"><span class="control-label">${zh?'首付比例':'Down payment'}</span>${segmented('down',[['10','10%'],['20','20%'],['35','35%']],String(state.down),zh?'首付比例':'Down payment')}<small data-down-amount>${zh?'首付':'Down payment'} ${money(m.price*m.down/100)}</small></div>
 <div class="field"><span class="control-label">${zh?'贷款金额':'Loan amount'}</span><output class="loan-output" data-loan>${money(m.loan)}</output><small>${zh?'= 房价 − 首付':'= price − down payment'}</small></div>
 <div class="field"><span class="control-label">${t('years')}</span>${segmented('years',[['25',zh?'25 年':'25 years'],['30',zh?'30 年':'30 years']],String(state.years),t('years'))}</div>
 <label class="field"><span class="control-label">${t('rate')}</span><input data-number="rate" type="number" min="0" max="30" step="0.01" value="${Number.isFinite(Number(state.rate))?esc(state.rate):''}"><small>${esc(rateHint)}</small></label>
 <div data-mortgage-hints>${mortgageHints()}</div>
 </div><div class="mortgage-results" aria-live="polite">${mortgageResults()}</div></div>`;
}
function render(){themeColors();BAND_COLORS=isDark()?BAND_DARK:BAND_LIGHT;chartModels=[];shell(({market:marketPage,rent:rentPage,economy:economyPage,mortgage:mortgagePage})[state.page]());attachChartTooltips()}
function attach(){
 rovingSetup();
 document.querySelectorAll('[data-jump-district]').forEach(el=>el.onclick=()=>document.getElementById('district-section')?.scrollIntoView({behavior:'smooth',block:'start'}));
  const navEl=document.querySelector('#app nav');if(navEl)document.documentElement.style.setProperty('--nav-h',`${navEl.offsetHeight}px`);
  document.querySelectorAll('[data-jump]').forEach(el=>el.onclick=()=>{jumpTarget=el.dataset.jump;document.getElementById(el.dataset.jump)?.scrollIntoView({behavior:'smooth',block:'start'});spySections()});
  spySections();
  // Widths are set through CSSOM because the page's CSP disallows inline style attributes.
  document.querySelectorAll('[data-width]').forEach(el=>{el.style.width=`${el.dataset.width}%`});
  document.querySelectorAll('[data-bg]').forEach(el=>{el.style.background=el.dataset.bg});
  document.querySelectorAll('[data-left]').forEach(el=>{el.style.left=`${el.dataset.left}%`});
  document.querySelectorAll('[data-pick]').forEach(el=>el.onclick=()=>{const key=el.dataset.pick,value=el.dataset.value;state[key]=value;state.regionFeedback='';render();document.querySelector(`[data-pick="${key}"][data-value="${value}"]`)?.focus()});
  document.querySelectorAll('[data-map-csd]').forEach(el=>{const activate=()=>{const r=el.dataset.mapCsd,keep=scrollY;state.districtRegion=r;state.districtType='all_types';render();document.querySelector('#regions-panel')?.setAttribute('open','');document.querySelector(`[data-map-csd="${CSS.escape(r)}"]`)?.focus({preventScroll:true});scrollTo(0,keep);
   // On narrow screens the card sits under the map; bring it into view.
   const card=document.querySelector('.map-detail');if(card&&innerWidth<=900&&card.getBoundingClientRect().top>innerHeight-120)card.scrollIntoView({behavior:'smooth',block:'nearest'})};el.onclick=activate;el.onkeydown=event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();activate()}}});
  document.querySelector('[data-reset]').onclick=()=>{const lang=state.lang;Object.keys(state).forEach(k=>delete state[k]);Object.assign(state,JSON.parse(JSON.stringify(initialState)),{lang});history.replaceState(null,'',location.pathname);render();window.scrollTo(0,0)};
  document.querySelectorAll('[data-district-month]').forEach(el=>el.onclick=()=>{state.end.district=el.dataset.districtMonth;render();document.querySelector('#regions-panel')?.setAttribute('open','')});
  document.querySelectorAll('[data-theme-toggle]').forEach(el=>el.onclick=()=>{themeChoice={auto:'light',light:'dark',dark:'auto'}[themeChoice];try{localStorage.setItem('gta-housing-theme',themeChoice)}catch{}applyTheme();render();document.querySelector('[data-theme-toggle]')?.focus()});
  document.querySelectorAll('[data-lang]').forEach(el=>el.onclick=()=>{state.lang=el.dataset.lang;try{localStorage.setItem('gta-housing-lang',state.lang)}catch{}render()});
  document.querySelectorAll('[data-page]').forEach(el=>el.onclick=()=>go({page:el.dataset.page}));
  document.querySelectorAll('[data-mode]').forEach(el=>el.onclick=()=>go({rentMode:el.dataset.mode}));
  document.querySelectorAll('[data-state]').forEach(el=>el.onchange=()=>{state[el.dataset.state]=el.value;state.regionFeedback='';render();if(el.dataset.state.startsWith('district'))document.querySelector('#regions-panel')?.setAttribute('open','')});
  document.querySelectorAll('[data-end]').forEach(el=>el.onchange=()=>{state.end[el.dataset.end]=el.value;render();if(el.dataset.end==='district')document.querySelector('#regions-panel')?.setAttribute('open','')});
  const regionChoices=()=>Object.entries(AREAS).filter(([id])=>state.regionFrequency==='annual'?id!=='toronto':!id.includes('richmond')&&!id.includes('aurora'));
  document.querySelectorAll('[data-remove-region]').forEach(el=>el.onclick=()=>{toggleRegion(el.dataset.removeRegion,regionChoices());document.querySelector('[data-add-region]')?.focus()});
  document.querySelectorAll('[data-add-region]').forEach(el=>el.onchange=()=>{if(el.value)toggleRegion(el.value,regionChoices())});
  document.querySelectorAll('[data-border]').forEach(el=>{el.style.borderLeftColor=el.dataset.border});
  const refreshMortgage=()=>{const m=mortgageModel(),zh=state.lang==='zh';document.querySelector('.mortgage-results').innerHTML=mortgageResults();rovingSetup();document.querySelectorAll('.mortgage-results [data-bg]').forEach(el=>{el.style.background=el.dataset.bg});document.querySelector('[data-loan]').textContent=money(m.loan);document.querySelector('[data-down-amount]').textContent=`${zh?'首付':'Down payment'} ${money(m.price*m.down/100)}`;document.querySelector('[data-mortgage-hints]').innerHTML=mortgageHints()};
  document.querySelectorAll('[data-number]').forEach(el=>el.oninput=()=>{const v=Number(el.value);state[el.dataset.number]=el.value!==''&&Number.isFinite(v)?v:NaN;refreshMortgage()});
  document.querySelectorAll('[data-money]').forEach(el=>{el.oninput=()=>{const digits=el.value.replace(/[^0-9]/g,'');state[el.dataset.money]=digits?Number(digits):0;refreshMortgage()};el.onblur=()=>{el.value=money(state[el.dataset.money])}});
}
fetch('data.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error(`HTTP ${r.status}`);return r.json()}).then(data=>{payload=data;prepare();render()}).catch(()=>{$('#app').innerHTML='<p class="message">已发布的资料快照暂时无法读取。 / Published data snapshot could not be loaded.</p>'});

// Help bubbles close on an outside click or Escape, and only one stays open at a time.
document.addEventListener('click',event=>{document.querySelectorAll('details.info[open]').forEach(d=>{if(!d.contains(event.target))d.open=false})});
document.addEventListener('keydown',event=>{if(event.key!=='Escape')return;const open=document.querySelector('details.info[open]');if(open){open.open=false;open.querySelector('summary')?.focus()}});
document.addEventListener('toggle',event=>{const d=event.target;if(d.matches?.('details.info')&&d.open)document.querySelectorAll('details.info[open]').forEach(o=>{if(o!==d)o.open=false})},true);
// One tooltip and delegated handlers serve the custom SVG charts, including ones redrawn on input.
const vizTip=document.createElement('div');vizTip.className='viz-tip';vizTip.hidden=true;vizTip.setAttribute('role','status');document.body.appendChild(vizTip);
function placeTip(text,x,y){vizTip.textContent=text;vizTip.hidden=false;const w=vizTip.offsetWidth,h=vizTip.offsetHeight;vizTip.style.left=`${Math.min(innerWidth-w-8,Math.max(8,x+14))}px`;vizTip.style.top=`${y-h-14<8?y+18:y-h-14}px`}
function heatGuide(el){const line=document.querySelector('[data-temp-guide]');if(!line||!tempGuide)return;const i=el?tempGuide.periods.indexOf(el.dataset.heat):-1;if(i<0){line.setAttribute('visibility','hidden');return}line.setAttribute('x1',tempGuide.xs[i]);line.setAttribute('x2',tempGuide.xs[i]);line.setAttribute('visibility','visible')}
document.addEventListener('pointerover',e=>{const el=e.target.closest?.('[data-tip]');if(!el)return;placeTip(el.dataset.tip,e.clientX,e.clientY);heatGuide(el.closest('[data-heat]'))});
document.addEventListener('pointermove',e=>{const el=e.target.closest?.('[data-tip]');if(el)placeTip(el.dataset.tip,e.clientX,e.clientY)});
document.addEventListener('pointerout',e=>{if(e.target.closest?.('[data-tip]')&&!e.relatedTarget?.closest?.('[data-tip]')){vizTip.hidden=true;heatGuide(null)}});
document.addEventListener('focusin',e=>{const el=e.target.closest?.('[data-tip]');if(!el)return;const r=el.getBoundingClientRect();placeTip(el.dataset.tip,r.left+r.width/2,r.top);heatGuide(el.closest('[data-heat]'))});
document.addEventListener('focusout',e=>{if(e.target.closest?.('[data-tip]')){vizTip.hidden=true;heatGuide(null)}});
function vizAction(target){
 const month=target.closest('[data-pick-month]');if(month){state.end.market=month.dataset.pickMonth;vizTip.hidden=true;render();document.querySelector(`[data-pick-month="${month.dataset.pickMonth}"]`)?.focus({preventScroll:true});return true}
 const room=target.closest('[data-pick-room]');if(room){const r=room.dataset.pickRoom;state.measureRoom=r;if(['1br','2br','3br'].includes(r))state.room=r;state.annualRoom=r==='3br'?'3plus':r;state.leaseType=state.measureType==='townhouse'?'townhouse':'condo';vizTip.hidden=true;render();document.querySelector(`[data-pick-room="${r}"]`)?.focus({preventScroll:true});return true}
 const step=target.closest('[data-amort-step]');if(step){state.amortStep=Number(step.dataset.amortStep);const box=document.querySelector('.mortgage-results');if(box)box.innerHTML=mortgageResults();attach();document.querySelector(`[data-amort-step="${state.amortStep}"]`)?.focus({preventScroll:true});return true}
 return false;
}
document.addEventListener('click',e=>{if(e.target.closest)vizAction(e.target)});
// Dense SVG charts take one Tab stop each; arrow keys move within (heatmap rows are years, so up/down is +/-12 months).
const ROVING=[['.heat-cell[data-pick-month]',true],['.band-col',false],['.amort-bar',false]];
function shiftMonth(p,k){const [y,m]=p.split('-').map(Number),t=y*12+m-1+k;return `${Math.floor(t/12)}-${String(t%12+1).padStart(2,'0')}`}
function rovingSetup(){for(const [sel] of ROVING){const items=[...document.querySelectorAll(sel)];if(!items.length)continue;
 const cur=items.find(el=>el.dataset.pickMonth&&el.dataset.pickMonth===state.end.market)||items.find(el=>el.matches(':focus'))||(sel==='.amort-bar'?items[0]:items.at(-1));
 items.forEach(el=>el.setAttribute('tabindex',el===cur?'0':'-1'))}}
document.addEventListener('keydown',e=>{for(const [sel,grid] of ROVING){const el=e.target.closest?.(sel);if(!el)continue;
 const items=[...document.querySelectorAll(sel)],i=items.indexOf(el);let n;
 if(e.key==='ArrowRight')n=i+1;else if(e.key==='ArrowLeft')n=i-1;else if(e.key==='Home')n=0;else if(e.key==='End')n=items.length-1;
 else if(grid&&(e.key==='ArrowDown'||e.key==='ArrowUp')){const want=shiftMonth(el.dataset.pickMonth,e.key==='ArrowDown'?12:-12);n=items.findIndex(x=>x.dataset.pickMonth===want);if(n<0)n=i}
 else return;
 e.preventDefault();n=Math.max(0,Math.min(items.length-1,n));items.forEach(x=>x.setAttribute('tabindex','-1'));items[n].setAttribute('tabindex','0');items[n].focus();return}});
document.addEventListener('keydown',e=>{if((e.key==='Enter'||e.key===' ')&&e.target.closest?.('[data-pick-month],[data-pick-room],[data-amort-step]')){e.preventDefault();vizAction(e.target)}});
// Highlight the in-page section currently under the sticky navigation.
let jumpTarget=null;
function spySections(){const buttons=[...document.querySelectorAll('[data-jump]')];if(!buttons.length)return;const bar=document.querySelector('.section-nav'),offset=(parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--nav-h'))||52)+(bar?bar.offsetHeight:44)+40;let current=buttons[0].dataset.jump;for(const b of buttons){const el=document.getElementById(b.dataset.jump);if(el&&el.getBoundingClientRect().top-offset<=0)current=b.dataset.jump}
 // Sections near the end cannot reach the top, so a clicked target stays marked until the reader scrolls.
 if(jumpTarget&&document.getElementById(jumpTarget))current=jumpTarget;buttons.forEach(b=>b.setAttribute('aria-current',b.dataset.jump===current?'true':'false'))}
for(const type of ['wheel','touchstart','keydown'])window.addEventListener(type,()=>{if(jumpTarget){jumpTarget=null;spySections()}},{passive:true});
let spyFrame;window.addEventListener('scroll',()=>{cancelAnimationFrame(spyFrame);spyFrame=requestAnimationFrame(spySections)},{passive:true});
matchMedia('(prefers-color-scheme: dark)').addEventListener?.('change',()=>{if(payload)render()});
new MutationObserver(()=>{if(settingTheme)return;const root=document.documentElement;if(themeChoice==='auto')hostTheme=root.dataset.theme||null;else if(root.dataset.theme!==themeChoice){hostTheme=root.dataset.theme||null;applyTheme()}if(payload)render()}).observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']});
let resizeFrame;window.addEventListener('resize',()=>{cancelAnimationFrame(resizeFrame);resizeFrame=requestAnimationFrame(()=>{if(!payload)return;const open=document.querySelector('#regions-panel')?.open;render();if(open)document.querySelector('#regions-panel')?.setAttribute('open','')})});
