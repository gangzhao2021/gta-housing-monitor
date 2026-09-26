// Historical first-pass construction script, NOT a replay of the final design.
// Final alignment and legend corrections were applied in Figma; see README.md.
// Do not rerun: this creates duplicate frames. __DATA__ was populated from data.json.
const DATA=__DATA__;
await Promise.all(['Regular','Medium','Bold'].map(style=>figma.loadFontAsync({family:'Noto Sans SC',style})));
await Promise.all(['Regular','Medium','Semi Bold'].map(style=>figma.loadFontAsync({family:'Inter',style})));
const baseButton=await figma.getNodeByIdAsync('3:178');
const ids=[];const remember=n=>(ids.push(n.id),n);
const C={ink:'#171717',muted:'#666666',blue:'#2855d9',teal:'#007f86',grid:'#ededed'};
const rgb=h=>({r:parseInt(h.slice(1,3),16)/255,g:parseInt(h.slice(3,5),16)/255,b:parseInt(h.slice(5,7),16)/255});
const fill=h=>[{type:'SOLID',color:rgb(h)}];
function box(name,w,dir='VERTICAL',gap=0){const n=remember(figma.createAutoLayout(dir));n.name=name;n.fills=[];n.resize(w,10);n.primaryAxisSizingMode='AUTO';n.counterAxisSizingMode='FIXED';n.itemSpacing=gap;n.clipsContent=false;return n}
function txt(parent,label,size=14,color=C.ink,width=null,weight='Regular'){const n=remember(figma.createText());n.fontName={family:/[\u3400-\u9fff]/.test(label)?'Noto Sans SC':'Inter',style:weight};n.characters=label;n.fontSize=size;n.lineHeight={unit:'PERCENT',value:150};n.fills=fill(color);n.name=label;parent.appendChild(n);if(width){n.textAutoResize='HEIGHT';n.resize(width,n.height)}return n}
function button(parent,label,w){const n=remember(baseButton.clone());for(const c of n.findAll(()=>true))ids.push(c.id);n.setProperties({'Label#2:0':label});parent.appendChild(n);n.resize(w,44);n.fills=[];n.strokes=[];return n}
function chart(parent,series,w,h,unit){
 const colors=[C.blue,C.teal],pad={l:55,r:18,t:16,b:34};let min=unit==='CAD'?900000:0,max=unit==='CAD'?1100000:unit==='月'?8:25000;
 const x=i=>pad.l+i/(DATA.periods.length-1)*(w-pad.l-pad.r),y=v=>pad.t+(max-v)/(max-min)*(h-pad.t-pad.b);
 let svg=`<svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" xmlns="http://www.w3.org/2000/svg">`;
 for(let i=0;i<5;i++){let v=min+(max-min)*i/4,py=y(v),label=unit==='CAD'?(v/1000000).toFixed(2)+'M':unit==='月'?v.toFixed(0):(v/1000).toFixed(1)+'k';svg+=`<line x1="55" x2="${w-18}" y1="${py}" y2="${py}" stroke="${C.grid}"/><text x="44" y="${py+4}" text-anchor="end" font-family="Inter" font-size="11" fill="#666">${label}</text>`}
 for(const i of (w<500?[0,12,24]:[0,6,12,18,24]))svg+=`<text x="${x(i)}" y="${h-8}" text-anchor="middle" font-family="Inter" font-size="11" fill="#666">${DATA.periods[i].slice(2).replace('-','/')}</text>`;
 svg+=`<text transform="translate(12 ${h/2}) rotate(-90)" text-anchor="middle" font-family="Inter" font-size="11" fill="#666">${unit}</text>`;
 series.forEach((a,j)=>{svg+=`<path d="${a.map((v,i)=>(i?'L':'M')+x(i).toFixed(2)+' '+y(v).toFixed(2)).join(' ')}" fill="none" stroke="${colors[j]}" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>`});
 svg+='</svg>';const n=remember(figma.createNodeFromSvg(svg));n.name='可编辑曲线 · 真实快照 2024-08 至 2026-08';parent.appendChild(n);for(const c of n.findAll(()=>true))ids.push(c.id);return n;
}
function build(mobile){
 const W=mobile?390:1440,P=mobile?24:80,w=W-2*P;
 const root=box(mobile?'07 · 市场总览评审 / Mobile 390':'06 · 市场总览评审 / Desktop 1440',W,'VERTICAL',mobile?28:40);
 root.x=mobile?4800:3240;root.y=80;root.paddingLeft=P;root.paddingRight=P;root.paddingTop=mobile?24:40;root.paddingBottom=40;root.fills=fill('#ffffff');
 const head=box('品牌与语言',w,'HORIZONTAL',12);root.appendChild(head);head.primaryAxisAlignItems='SPACE_BETWEEN';head.counterAxisAlignItems='CENTER';txt(head,'大多伦多房市观察',mobile?16:20,C.ink,null,'Medium');
 const lang=box('无底色语言切换 · 44px 触控区',96,'HORIZONTAL',4);head.appendChild(lang);button(lang,'中文',46);button(lang,'EN',46);
 const nav=box('仅展示导航',w,'HORIZONTAL',mobile?18:40);root.appendChild(nav);for(const [i,t]of ['市场总览','租赁市场','经济与供给','月供情景'].entries())txt(nav,t,mobile?12:14,i?C.muted:C.blue,null,i?'Regular':'Medium');
 const title=box('页面标题与统一时间',w,mobile?'VERTICAL':'HORIZONTAL',mobile?12:32);root.appendChild(title);if(!mobile)title.primaryAxisAlignItems='SPACE_BETWEEN';
 const heading=box('标题',mobile?w:750,'VERTICAL',6);title.appendChild(heading);txt(heading,'市场总览',mobile?28:36,C.ink,null,'Medium');txt(heading,'TRREB 全市场 · 全部房型',13,C.muted);const controls=box('月份',mobile?w:210,'VERTICAL',2);title.appendChild(controls);txt(controls,'观察月份',12,C.muted);button(controls,'2026 年 8 月  ▾',mobile?180:210);
 const hero=box('核心数据',w,mobile?'VERTICAL':'HORIZONTAL',mobile?24:64);root.appendChild(hero);
 const price=box('HPI 基准房价',mobile?w:520,'VERTICAL',4);hero.appendChild(price);txt(price,'HPI 综合基准房价  ⓘ',14,C.muted);txt(price,'$925,900',mobile?48:64,C.ink,null,'Medium');txt(price,'同比 −4.5%   ·   基准价格，不是成交均价',mobile?12:13,C.muted,mobile?w:null);
 const others=box('成交与供需摘要',mobile?w:616,'HORIZONTAL',mobile?28:56);hero.appendChild(others);if(!mobile)others.paddingTop=24;
 const a=box('成交量',mobile?150:245,'VERTICAL',6);others.appendChild(a);txt(a,'当月成交  ⓘ',13,C.muted);txt(a,'5,057',mobile?28:36);txt(a,'同比 −3.0%',12,C.muted);
 const b=box('库存月数',mobile?150:245,'VERTICAL',6);others.appendChild(b);txt(b,'库存月数  ⓘ',13,C.muted);txt(b,'4.84',mobile?28:36);txt(b,'有效挂牌 ÷ 当月成交',12,C.muted,mobile?150:245);
 const trend=box('主图 · 房价走势',w,'VERTICAL',12);root.appendChild(trend);const th=box('走势标题与范围',w,'HORIZONTAL',12);trend.appendChild(th);th.primaryAxisAlignItems='SPACE_BETWEEN';txt(th,'房价走势',18,C.ink,null,'Medium');txt(th,mobile?'近 25 个月':'2024.08 — 2026.08',12,C.muted);chart(trend,[DATA.hpi],w,mobile?250:300,'CAD');
 txt(trend,'标准化住宅价格变化。悬停或使用方向键查看各期数值。',12,C.muted,w);
 const support=box('成交与供需',w,mobile?'VERTICAL':'HORIZONTAL',mobile?28:48);root.appendChild(support);const cw=mobile?w:Math.floor((w-48)/2);
 const sales=box('成交与新增挂牌',cw,'VERTICAL',10);support.appendChild(sales);txt(sales,'成交与新增挂牌',18,C.ink,null,'Medium');txt(sales,'━ 成交量     ━ 新增挂牌',12,C.muted);chart(sales,[DATA.sales,DATA.listings],cw,mobile?210:230,'笔 / 套');
 const supply=box('供需指标',cw,'VERTICAL',10);support.appendChild(supply);txt(supply,'供需状况',18,C.ink,null,'Medium');txt(supply,'库存月数     /     成交／新挂牌比',12,C.blue);chart(supply,[DATA.moi],cw,mobile?200:230,'月');
 const regional=box('地区转售 · 默认收起',w,'VERTICAL',8);root.appendChild(regional);const rr=box('展开地区转售',w,'HORIZONTAL',12);regional.appendChild(rr);rr.primaryAxisAlignItems='SPACE_BETWEEN';txt(rr,'地区转售明细',20,C.ink,null,'Medium');txt(rr,'＋',24,C.blue);txt(regional,'按地区、房型比较均价、成交与挂牌。',13,C.muted,w);
 const foot=box('来源与数据状态',w,'VERTICAL',6);root.appendChild(foot);txt(foot,'来源与口径  ↗     重置筛选     保存视图链接',12,C.muted,w);txt(foot,'TRREB Market Watch · 快照发布于 2026.09.26',11,C.muted,w);txt(foot,'历史数据可能修订；领先信号尚未验证。',11,C.muted,w);
 return root;
}
const desktop=build(false),mobile=build(true);
const textFonts=[...new Set([desktop,mobile].flatMap(n=>n.findAllWithCriteria({types:['TEXT']}).map(t=>t.fontName.family)))];
if(textFonts.some(f=>!['Inter','Noto Sans SC'].includes(f)))throw Error('Unexpected font');
return {createdNodeIds:ids,frames:[desktop,mobile].map(n=>({id:n.id,name:n.name,width:n.width,height:n.height})),fonts:textFonts,dataSnapshot:DATA.created_at};
