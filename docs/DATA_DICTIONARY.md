# 已接入系列字典

核对日期：2026-09-23。下表描述当前实际入库系列；原始文件与哈希见 `data/raw/manifest.csv`。所有 `value` 都保留来源单位，没有将百分数除以 100。发布时点未有逐观测可靠证据，因此数据库 `published_at` 留空；抓取时间不得替代发布日期。

| 数据库 ID | 原系列／报告列 | 单位、频率 | 范围与口径 | 月图公式／来源 |
| --- | --- | --- | --- | --- |
| `boc_policy_rate` | BoC `V39079` | %，工作日 | 加拿大；隔夜目标利率，非 Bank Rate；未季调 | 月末最后有效观测。BoC Valet API |
| `goc_5y_yield` | BoC `BD.CDN.5YR.DQ.YLD` | %，交易日 | 加拿大；五年基准政府债收益率，未季调 | 当月有效交易日均值；原日值保留。BoC Valet API；旧 lookup 的 `V39053` 不是 Valet ID |
| `mortgage_uninsured_fixed_5plus` | BoC `V122667786` | %，月 | 加拿大；特许银行新增放款、非受保、固定、**五年及以上** | 官方月值；金额加权，含续贷／再融资，不等于个人报价 |
| `toronto_unemployment_rate` | StatsCan 表 14-10-0460-01，`v1642720028` | %，月 | Toronto CMA，2021 边界；Estimate、Seasonally adjusted、单月 | 官方值；未额外平滑 |
| `toronto_employment_rate` | 同表 `v1642720044` | %，月 | 同上 | 官方值 |
| `toronto_participation_rate` | 同表 `v1642720036` | %，月 | 同上 | 官方值 |
| `trreb_sales` | Market Watch 第 3 页 Sales | 成交笔数，月 | All TRREB Areas、All Home Types；未经季调；2022-09 至 2026-08 各月原始发布版 | 原报告总市场行；不是交割量 |
| `trreb_new_listings` | 第 3 页 New Listings | 挂牌条目，月 | 同上 | 当月新增；未去重成房屋数 |
| `trreb_active_listings` | 第 3 页 Active Listings | 挂牌条目，月末 | 同上 | 月末存量，不跨月求和 |
| `trreb_hpi_composite` | 第 25 页 Composite Index | 指数，月 | 同上；MLS HPI 综合指数 | 原报告值，不等于平均房价 |
| `trreb_hpi_benchmark` | 第 25 页 Composite Benchmark | CAD，月 | 同上；MLS HPI 综合基准房价 | 原报告值，与指数分开 |
| `toronto_cma_2011_starts` | StatsCan / CMHC 表 34-10-0154-01，Housing starts / Total units | 套，月 | Toronto CMA **2011 边界**；实际开工，不是 SAAR | 2026-09-23 下载全表，覆盖 1972-01 至 2026-08 |
| `toronto_cma_2011_completions` | 同表，Housing completions / Total units | 套，月 | 同上；竣工流量 | 不与开工混为一谈 |
| `toronto_cma_2011_under_construction` | 同表，Housing under construction / Total units | 套，月末存量 | 同上；在建单位存量 | 不能累加为当期新增供应 |
| `toronto_cma_2021_population` | StatsCan 表 17-10-0148-01，Total gender / All ages | 人，年 | Toronto CMA **2021 边界**；7 月 1 日人口估计 | 2001–2025；年度值不插值为月度 |
| `toronto_pbr_rent_studio` | CMHC Rental Market Survey，表 1.1.2 | CAD/月，年 | Toronto CMA 2021 边界；私人专建出租公寓（3 套及以上）；Studio／开间平均租金 | 10 月调查，2024–2025；原表平均值，非新租约挂牌价 |
| `toronto_pbr_rent_1br` | CMHC Rental Market Survey，表 1.1.2 | CAD/月，年 | Toronto CMA 2021 边界；私人专建出租公寓（3 套及以上）；一卧平均租金 | 10 月调查，2024–2025；原表平均值，非新租约挂牌价 |
| `toronto_pbr_rent_2br` | CMHC Rental Market Survey，表 1.1.2 | CAD/月，年 | Toronto CMA 2021 边界；私人专建出租公寓（3 套及以上）；两卧平均租金 | 10 月调查，2024–2025；原表平均值，非新租约挂牌价 |
| `toronto_pbr_rent_3plus` | CMHC Rental Market Survey，表 1.1.2 | CAD/月，年 | Toronto CMA 2021 边界；私人专建出租公寓（3 套及以上）；三卧及以上平均租金 | 10 月调查，2024–2025；原表平均值，非新租约挂牌价 |
| `toronto_pbr_rent_total` | CMHC Rental Market Survey，表 1.1.2 | CAD/月，年 | Toronto CMA 2021 边界；私人专建出租公寓（3 套及以上）；全部房型平均租金 | 10 月调查，2024–2025；原表平均值，非新租约挂牌价 |
| `toronto_condo_rent_studio` | CMHC Rental Market Survey，表 4.1.3 | CAD/月，年 | Toronto CMA 2021 边界；出租公寓产权房（次级出租市场）；Studio／开间平均租金 | 10 月调查，2024–2025；原表平均值，非新租约挂牌价 |
| `toronto_condo_rent_1br` | CMHC Rental Market Survey，表 4.1.3 | CAD/月，年 | Toronto CMA 2021 边界；出租公寓产权房（次级出租市场）；一卧平均租金 | 10 月调查，2024–2025；原表平均值，非新租约挂牌价 |
| `toronto_condo_rent_2br` | CMHC Rental Market Survey，表 4.1.3 | CAD/月，年 | Toronto CMA 2021 边界；出租公寓产权房（次级出租市场）；两卧平均租金 | 10 月调查，2024–2025；原表平均值，非新租约挂牌价 |
| `toronto_condo_rent_3plus` | CMHC Rental Market Survey，表 4.1.3 | CAD/月，年 | Toronto CMA 2021 边界；出租公寓产权房（次级出租市场）；三卧及以上平均租金 | 10 月调查，2024–2025；原表平均值，非新租约挂牌价 |
| `toronto_condo_rent_total` | CMHC Rental Market Survey，表 4.1.3 | CAD/月，年 | Toronto CMA 2021 边界；出租公寓产权房（次级出租市场）；全部房型平均租金 | 10 月调查，2024–2025；原表平均值，非新租约挂牌价 |
| `toronto_pbr_vacancy_studio` | 同调查，表 1.1.1 | %，年 | Toronto CMA 2021 边界；私人专建出租公寓（3 套及以上）；Studio／开间 | 10 月调查，2024–2025 |
| `toronto_pbr_vacancy_1br` | 同调查，表 1.1.1 | %，年 | Toronto CMA 2021 边界；私人专建出租公寓（3 套及以上）；一卧 | 10 月调查，2024–2025 |
| `toronto_pbr_vacancy_2br` | 同调查，表 1.1.1 | %，年 | Toronto CMA 2021 边界；私人专建出租公寓（3 套及以上）；两卧 | 10 月调查，2024–2025 |
| `toronto_pbr_vacancy_3plus` | 同调查，表 1.1.1 | %，年 | Toronto CMA 2021 边界；私人专建出租公寓（3 套及以上）；三卧及以上 | 10 月调查，2024–2025 |
| `toronto_pbr_vacancy_rate` | 同调查，表 1.1.1 | %，年 | Toronto CMA 2021 边界；私人专建出租公寓（3 套及以上）；全部房型 | 10 月调查，2024–2025 |
| `toronto_condo_vacancy_rate` | 同调查，表 4.1.1 | %，年 | Toronto CMA 2021 边界；出租公寓产权房；全部房型 | 10 月调查，2024–2025；没有按卧室数的独立空置率 |

派生字段：`moi_raw = active_listings / sales`，单位月；`snlr_raw = sales / new_listings × 100`，单位 %。零分母返回缺失。两者都只组合相同地区、房型、月份的这三个固定 TRREB 系列。TRREB 报告的 `SNLR Trend` 和 `Mos Inv (Trend)` 使用趋势／移动平均口径，**不是**这里的原始月度比率。数量及 HPI 同比为本期 / 上年同月 − 1；当前依据各月原始发布版，不是 TRREB 最新修订历史版，页面会显式提醒。


### 租赁房型和质量字段

当前租赁部分包含 16 个系列、32 个年度观测；全库为 31 个系列、4,905 个观测（2026-09-23 核对）。此前只导入两卧是实现范围遗漏，不能据此说来源没有其他房型。Condo 租金改用表 4.1.3，补回其 2024 年比较值；表 4.1.2 仍是有效的 2025 年跨市场比较表，但不再用作 Condo 历史主表。

- `total` 是 CMHC 直接公布的全部房型均值，不能把四种卧室类别作算术平均替代。
- 本页“均值较上年”计算同一系列本年／上年 − 1，受样本与住房构成影响。表 1.1.5 的同样本租金变化是不同指标，尚未入库。例如专建两卧均值 $2,046／$1,974 对应约 3.65%，官方同样本涨幅是 3.4%。
- 专建出租和 Condo 出租的调查总体不同；不合并为一个“Toronto 平均租金”。页面只覆盖公寓，原表中的私人 Townhouse、空置／已住单位租金、同样本涨幅仍是独立类别，不混入本表。
- `parse_cmhc_rental_details` 从保留工作簿提供 `series_id`、`period`、`value`、`status`、`quality`、`significance`、`sheet`、`cell`。这些来源单元格证据可在租赁页面详情查看和导出；数值观测继续引用文件 SHA-256。
- 质量 `a` 为 Excellent、`b` 为 Very Good、`c` 为 Good、`d` 为 Poor（谨慎使用）。2025 Condo Studio 为 c，三卧及以上为 b，其余租金类别为 a；专建出租各房型租金均为 a。
- 原表 `↑`／`↓` 表示同比差异统计显著，`-`／`–` 表示有效样本不足以把变化解释为统计显著。标记为空表示该单元格未提供判断，不能解释为“不显著”。2025 Condo 租金五类均标 `-`。
- `status=suppressed` 对应原表 `**`，`not_available` 对应空白或不可用标记；两者均不转换为零。未知文本、缺少数值质量等级、异常表头及年份不一致会使解析失败。当前 Toronto CMA 选取的 32 个单元格均有可用值。


边界说明：人口使用 2021 CMA 边界，建设表的 Toronto DGUID 是 2011S0503535。两组各自可看历史变化，不能当成同一边界数据拼接或计算建设／人口比率。

原始来源：[BoC Valet API](https://www.bankofcanada.ca/valet-api-how-to/)、[BoC 按揭定义与发布说明](https://www.bankofcanada.ca/rates/banking-and-financial-statistics/interest-rates-for-new-and-existing-lending-by-chartered-banks/)、[Statistics Canada 表 14-10-0460-01](https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1410046001)、[表 34-10-0154-01](https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=3410015401)、[表 17-10-0148-01](https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1710014801)、[CMHC Rental Market Survey Data Tables](https://www.cmhc-schl.gc.ca/professionals/housing-markets-data-and-research/housing-data/data-tables/rental-market/rental-market-report-data-tables)、[TRREB Market Watch 档案](https://trreb.ca/market-data/market-watch/market-watch-archive/)。


### 2026-09-23 新增月度挂牌租金

- 来源：Rentals.ca / Urbanation，2026 年 8 月报告内的公开图表 CSV；商业挂牌样本统计，非政府调查或 MLS 实际成交租金。
- `toronto_asking_rent_total`：2022-07—2026-07，49 个月，CAD/month；专建出租公寓与 condo 合并，全房型原始总体均值。
- `toronto_asking_rent_1br/2br/3br`：2026-07 单月快照。三卧不等于三卧及以上，未提供开间。
- 地区：Toronto (Rentals.ca market definition)，不声明与 Toronto CMA、City of Toronto 或 All TRREB Areas 边界完全一致。
- 历史图表：<https://datawrapper.dwcdn.net/cTPkd/1/>；房型图表：<https://datawrapper.dwcdn.net/o6p6T/1/>。原始 HTML 和 CSV 均保存到 `data/raw/rentals`。
- 2026-07 总体 2,577，一卧 2,242、两卧 2,956、三卧 3,655 加元/月。总体均值不是房型均值的简单平均；样本结构变化可能影响均值。
- 2026-08 尚未接入，不补值；也不把报告标题中的 8 月当成观测月份。数据与记录页显示新鲜度不足。
