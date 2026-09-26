# 已接入系列字典

> 2026-09-26 增补：本次新增六条独立系列（含一条停更历史表），全库 131 个系列、5,944 条含版本观测。最新口径与验证见文末“2026-09-26”小节；下列更早日期的计数保留为历史记录。

核对日期：2026-09-24；本轮实际刷新四个外部背景来源并核对本地数据库、系列目录和解析器。原始文件与哈希见 `data/raw/manifest.csv`。所有 `value` 都保留来源单位，没有将百分数除以 100。当前全部观测的 `published_at`、`availability_evidence` 均为空；抓取时间不得替代发布日期。

当前登记 **125 个系列**，其中 **123 个有数值观测**；两个 Markham 开间年度系列由来源持续抑制，登记定义但没有数值。数据库有 **5,566 条含版本观测、5,561 个不同系列／期间、112 份登记原件**。数值计数不包含抑制单元格，也不包含从原件即时解析的房型分项。

| 系列族 | 登记数 | 当前覆盖 |
| --- | ---: | --- |
| 外部背景 | 4 | WTI、BoC 能源商品指数、USD/CAD 月均汇率、Toronto 住宅建筑造价指数；私有库保留历史，展示快照仅含每项最近值，不进入预测 |
| 融资、就业、转售、建设、人口 | 15 | 逐系列定义见下表；覆盖期见[来源覆盖](SOURCE_COVERAGE.md) |
| Toronto CMA 年度公寓租赁 | 16 | 两类市场、2022—2025，每系列 4 年，共 64 个数值 |
| Toronto 月度公寓挂牌租金 | 4 | 总体 2022-07—2026-08；一／两／三卧 2025-11—2026-08 |
| 其他地区月度公寓挂牌租金 | 16 | 六地区总体 2025-11—2026-08；除 Markham 外一／两卧 2026-04—2026-08 |
| CMHC 地区年度专建出租公寓 | 70 | 七个原始调查区 × 租金／空置率 × 五房型；2022—2025 的 280 个目标单元格中 252 个数值、28 个抑制 |

### 基础系列与 Toronto CMA 年度系列

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
| `toronto_pbr_rent_studio` | CMHC Rental Market Survey，表 1.1.2 | CAD/月，年 | Toronto CMA 2021 边界；私人专建出租公寓（3 套及以上）；Studio／开间平均租金 | 10 月调查，2022–2025；原表平均值，非新租约挂牌价 |
| `toronto_pbr_rent_1br` | CMHC Rental Market Survey，表 1.1.2 | CAD/月，年 | Toronto CMA 2021 边界；私人专建出租公寓（3 套及以上）；一卧平均租金 | 10 月调查，2022–2025；原表平均值，非新租约挂牌价 |
| `toronto_pbr_rent_2br` | CMHC Rental Market Survey，表 1.1.2 | CAD/月，年 | Toronto CMA 2021 边界；私人专建出租公寓（3 套及以上）；两卧平均租金 | 10 月调查，2022–2025；原表平均值，非新租约挂牌价 |
| `toronto_pbr_rent_3plus` | CMHC Rental Market Survey，表 1.1.2 | CAD/月，年 | Toronto CMA 2021 边界；私人专建出租公寓（3 套及以上）；三卧及以上平均租金 | 10 月调查，2022–2025；原表平均值，非新租约挂牌价 |
| `toronto_pbr_rent_total` | CMHC Rental Market Survey，表 1.1.2 | CAD/月，年 | Toronto CMA 2021 边界；私人专建出租公寓（3 套及以上）；全部房型平均租金 | 10 月调查，2022–2025；原表平均值，非新租约挂牌价 |
| `toronto_condo_rent_studio` | CMHC Rental Market Survey，表 4.1.3 | CAD/月，年 | Toronto CMA 2021 边界；出租公寓产权房（次级出租市场）；Studio／开间平均租金 | 10 月调查，2022–2025；原表平均值，非新租约挂牌价 |
| `toronto_condo_rent_1br` | CMHC Rental Market Survey，表 4.1.3 | CAD/月，年 | Toronto CMA 2021 边界；出租公寓产权房（次级出租市场）；一卧平均租金 | 10 月调查，2022–2025；原表平均值，非新租约挂牌价 |
| `toronto_condo_rent_2br` | CMHC Rental Market Survey，表 4.1.3 | CAD/月，年 | Toronto CMA 2021 边界；出租公寓产权房（次级出租市场）；两卧平均租金 | 10 月调查，2022–2025；原表平均值，非新租约挂牌价 |
| `toronto_condo_rent_3plus` | CMHC Rental Market Survey，表 4.1.3 | CAD/月，年 | Toronto CMA 2021 边界；出租公寓产权房（次级出租市场）；三卧及以上平均租金 | 10 月调查，2022–2025；原表平均值，非新租约挂牌价 |
| `toronto_condo_rent_total` | CMHC Rental Market Survey，表 4.1.3 | CAD/月，年 | Toronto CMA 2021 边界；出租公寓产权房（次级出租市场）；全部房型平均租金 | 10 月调查，2022–2025；原表平均值，非新租约挂牌价 |
| `toronto_pbr_vacancy_studio` | 同调查，表 1.1.1 | %，年 | Toronto CMA 2021 边界；私人专建出租公寓（3 套及以上）；Studio／开间 | 10 月调查，2022–2025 |
| `toronto_pbr_vacancy_1br` | 同调查，表 1.1.1 | %，年 | Toronto CMA 2021 边界；私人专建出租公寓（3 套及以上）；一卧 | 10 月调查，2022–2025 |
| `toronto_pbr_vacancy_2br` | 同调查，表 1.1.1 | %，年 | Toronto CMA 2021 边界；私人专建出租公寓（3 套及以上）；两卧 | 10 月调查，2022–2025 |
| `toronto_pbr_vacancy_3plus` | 同调查，表 1.1.1 | %，年 | Toronto CMA 2021 边界；私人专建出租公寓（3 套及以上）；三卧及以上 | 10 月调查，2022–2025 |
| `toronto_pbr_vacancy_rate` | 同调查，表 1.1.1 | %，年 | Toronto CMA 2021 边界；私人专建出租公寓（3 套及以上）；全部房型 | 10 月调查，2022–2025 |
| `toronto_condo_vacancy_rate` | 同调查，表 4.1.1 | %，年 | Toronto CMA 2021 边界；出租公寓产权房；全部房型 | 10 月调查，2022–2025；没有按卧室数的独立空置率 |

### 外部背景系列（2026-09-24 实际接入）

| 数据库 ID | 来源系列／原件 | 单位、频率、地区 | 数值覆盖与限制 |
| --- | --- | --- | --- |
| `wti_cushing_spot_price` | EIA WTI Cushing 月度现货价 `RWTC` | USD／桶，月；美国国际基准 | 2022-09—2026-08，共 48 期；不是 Ontario 零售油价或建材到场成本 |
| `boc_energy_price_index` | BoC `BCPI_MONTHLY` 的 `M.ENER` | 商品指数，月；加拿大 | 2022-09—2026-08，共 48 期；不是 WTI、家庭能源账单或单独材料价格 |
| `usd_cad_monthly` | BoC `FX_RATES_MONTHLY` 的 `FXMUSDCAD` | CAD／USD，月；加拿大 | 2022-09—2026-08，共 48 期；1 USD 兑换 CAD 的月均值，方向不可反写 |
| `toronto_residential_construction_cost_index` | StatsCan 表 18-10-0289-01，`v1617912612`；Residential buildings、Division composite | 指数（2023=100），季；Toronto CMA 2021 | 2017Q1—2026Q2，共 38 期；季度以首月存储，不是转售房价或包含土地的完整开发成本 |

四项在管理端“数据与记录”和只读展示端“经济与供给”均列示最近一期；完整历史保留在私有库，当前页面没有历史趋势。它们没有作为房价涨跌标签或预测特征。当前原件保存的是本次取得的历史快照，不含逐期首次发布和修订时点；全部 `published_at`／`availability_evidence` 仍为空，不能用于严格当时信息集回测。

派生字段：`moi_raw = active_listings / sales`，单位月；`snlr_raw = sales / new_listings × 100`，单位 %。零分母返回缺失。两者都只组合相同地区、房型、月份的这三个固定 TRREB 系列。TRREB 报告的 `SNLR Trend` 和 `Mos Inv (Trend)` 使用趋势／移动平均口径，**不是**这里的原始月度比率。数量及 HPI 自算同比为 `(本期 / 上年同月 − 1) × 100`，以百分数数值展示；当前依据各月原始发布版，不是 TRREB 最新修订历史版，页面会显式提醒。


### 租赁房型和质量字段

Toronto CMA 年度租赁目前包含 16 个系列、64 个观测（2022—2025）。历史上 2026-09-23 只核对 2025 工作簿时为 16 个系列、32 个年度观测，当时全库为 31 个系列、4,905 个观测；这些是历史计数，不能代替当前基线。此前只导入两卧是实现范围遗漏，不能据此说来源没有其他房型。Condo 租金改用表 4.1.3，补回其 2024 年比较值；表 4.1.2 仍是有效的 2025 年跨市场比较表，但不再用作 Condo 历史主表。

- `total` 是 CMHC 直接公布的全部房型均值，不能把四种卧室类别作算术平均替代。
- 本页“均值较上年”计算 `(同一系列本年／上年 − 1) × 100`，单位 %，受样本与住房构成影响。表 1.1.5 的同样本租金变化是不同指标，尚未入库。例如专建两卧均值 $2,046／$1,974 对应约 3.65%，官方同样本涨幅是 3.4%。
- 专建出租和 Condo 出租的调查总体不同；不合并为一个“Toronto 平均租金”。页面只覆盖公寓，原表中的私人 Townhouse、空置／已住单位租金、同样本涨幅仍是独立类别，不混入本表。
- `parse_cmhc_rental_details` 从保留工作簿提供 `series_id`、`period`、`value`、`status`、`quality`、`significance`、`sheet`、`cell`。这些来源单元格证据可在租赁页面详情查看和导出；数值观测继续引用文件 SHA-256。
- 质量 `a` 为 Excellent、`b` 为 Very Good、`c` 为 Good、`d` 为 Poor（谨慎使用）。2025 Condo Studio 为 c，三卧及以上为 b，其余租金类别为 a；专建出租各房型租金均为 a。
- 原表 `↑`／`↓` 表示同比差异统计显著，`-`／`–` 表示有效样本不足以把变化解释为统计显著。标记为空表示该单元格未提供判断，不能解释为“不显著”。2025 Condo 租金五类均标 `-`。
- `status=suppressed` 对应原表 `**`，`not_available` 对应空白或不可用标记；两者均不转换为零。未知文本、缺少数值质量等级、异常表头及年份不一致会使解析失败。当前两个工作簿的 Toronto CMA 64 个目标单元格均有可用值。地区调查区另有抑制，不能把 Toronto CMA 的完整性推广到所有地区。


边界说明：人口使用 2021 CMA 边界，建设表的 Toronto DGUID 是 2011S0503535。两组各自可看历史变化，不能当成同一边界数据拼接或计算建设／人口比率。

原始来源：[BoC Valet API](https://www.bankofcanada.ca/valet-api-how-to/)、[BoC 按揭定义与发布说明](https://www.bankofcanada.ca/rates/banking-and-financial-statistics/interest-rates-for-new-and-existing-lending-by-chartered-banks/)、[Statistics Canada 表 14-10-0460-01](https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1410046001)、[表 34-10-0154-01](https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=3410015401)、[表 17-10-0148-01](https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1710014801)、[CMHC Rental Market Survey Data Tables](https://www.cmhc-schl.gc.ca/professionals/housing-markets-data-and-research/housing-data/data-tables/rental-market/rental-market-report-data-tables)、[TRREB Market Watch 档案](https://trreb.ca/market-data/market-watch/market-watch-archive/)。

### 月度挂牌租金系列

所有这些系列均为 Rentals.ca／Urbanation 的专建出租公寓与 condo 挂牌样本均值，单位 `CAD/month`、月频、未季调。`total` 为来源总体均值，不能由房型均值合成；`3br` 只指三卧，不等于 CMHC 的 `3plus`。地区为来源市场名称，没有已验证的行政区边界等价关系。均值受挂牌构成影响，不是实际签约租金。

| ID 模式／地区代码 | 已登记后缀 | 当前数值范围与主来源 |
| --- | --- | --- |
| `toronto_asking_rent_{room}` | `total`、`1br`、`2br`、`3br` | 总体 50 月，分房型各 10 月；历史总体图、六大城市公寓表及 Toronto 房型图 |
| `regional_asking_{region}_{room}`；`region` 为 `north_york`、`scarborough`、`vaughan`、`mississauga`、`oakville` | `total`、`1br`、`2br` | 总体各 10 月，统一采用 Top 25 公寓／condo 排名图；一／两卧各 5 月，采用公寓城市表 |
| `regional_asking_markham_total` | 只有 `total` | 10 月，Top 25 公寓／condo 排名图；没有已接入的一／两／三卧系列 |

完整地区／房型月度计数见[月度覆盖审计](RENTAL_COVERAGE_AUDIT.csv)。无观测组合不是零，也不证明来源永远没有该资料；Downtown、Richmond Hill、Aurora 独立月度序列仍未核验。Top 25 图缺席不代表没有出租房；不把口径不同的旧全物业表接到公寓序列。2026-04 五个地区总体的来源选择变更保留了旧数值版本，原因及原图见[来源覆盖](SOURCE_COVERAGE.md)。

### CMHC 地区年度系列

ID 为 `regional_cmhc_{region}_pbr_{measure}_{suffix}`；`measure=rent` 时后缀为 `studio`、`1br`、`2br`、`3plus`、`total`，`measure=vacancy` 时总体后缀为 `rate`、其余相同。每区登记 10 个系列。租金单位为 `CAD/month`，空置率为 `%`；均为年度 10 月、私人专建出租公寓调查，采用表 1.1.2／1.1.1。地区表没有另行接入 condo 房型系列。

| `region` | 原始调查区（2021 分区） |
| --- | --- |
| `north_york` | North York (Zones 13-17) |
| `scarborough` | Scarborough (Zones 10-12) |
| `mississauga` | Mississauga City (Zones 18-20) |
| `oakville` | Zone 23 - Oakville |
| `markham` | Zone 27 - Markham |
| `richmond_vaughan_king` | Zone 25 - Richmond Hill/Vaughan/King |
| `aurora_newmarket_whit` | Zone 26 - Aurora, Newmkt, Whit-St. |

2023 和 2025 工作簿各提供相邻两年，合计 2022—2025；组合调查区不能拆为单城或与月度同名地区无条件拼接。Markham 开间租金和开间空置率四年均被抑制，其他地区／房型也有个别年份抑制。2025 年七区 70 个目标单元格中有 59 个数值、11 个抑制；以原件单元格状态判断，不用最后有数值的年份冒充最新年度。

### 原件解析与派生字段（不计入 125 个登记系列）

- TRREB HPI 房型分项由对应月份已存档 PDF 即时解析：综合、独立式、附连式、镇屋、公寓分别给指数、基准房价、原报告同比。原报告同比可能使用修订后的上年值，与跨原发布版自算同比分开。
- 建设分项由已存档 StatsCan ZIP 即时解析：开工／竣工／在建 × 总体、独立屋、半独立屋、排屋、公寓及其他。保留原表状态、分项合计差异和源文件哈希；不强改分项使其等于总数。HPI 房型和建设房型不可视为同一分类。
- MOI、SNLR、同比、三月均线、共同基期累计变化、共同起止期地区变化及月供情景由应用计算，没有独立持久化的 `derived_observations` 表。月供采用加拿大名义年利率半年复利换算月率，只含本息；历史月供固定本金及摊还期，并非历史实际贷款账单。

### 当前存储字段和版本边界

| 实体 | 已有字段及含义 | 当前限制 |
| --- | --- | --- |
| `series` | `id`、`label`、`source`、`source_series`、`geography`、`unit`、`frequency`、`seasonal_adjustment`、`smoothing`、`definition` | 房型、边界、用途主要编码在 ID／描述中；没有独立倍率、房型和边界版本字段；来源链接另由目录及 `raw_files` 提供 |
| `raw_files` | `sha256`、`path`、`source`、`source_url`、`retrieved_at`、`reference_period`、`method` | `retrieved_at` 由本地文件修改时间转 UTC，不能证明官方下载发生时间或正式发布时点；按内容哈希登记，不是每次请求的不可变事件日志 |
| `observations` | `id`、`series_id`、`period`、`value`、`version`、`raw_sha256`、`first_seen_at`、`published_at`、`availability_evidence` | `period` 为日／月／季／年字符串；季度用该季首月的 `YYYY-MM`；`first_seen_at` 是本地插入时间；`version` 是本地数值变化顺序，不是官方版本号；暂无独立 `available_at`、质量／抑制列及元数据审计表 |
| `ingestion_runs` | 来源、开始时间、成功／失败、原件哈希、新增／未变／修订行数、错误摘要 | 记录导入批次，不能单独证明每个值在历史判断时点已可获得 |

同值再次导入返回 `unchanged`，不新建观测或替换该观测的原件引用；批次与原件登记可留下本次来源，但没有逐观测采集证据关系。数值变化保留旧行并新增本地版本；同值的官方版本、质量、可用时间或定义变更还没有完整独立审计机制。质量、显著性与抑制状态由 CMHC 原件在运行时解析，不存为 `observations.value`；原件缺失时不能只靠数值库重建完整质量解释。

`research.as_known_at` 目前只是保守筛选原型：要求 `published_at` 和 `availability_evidence` 非 NULL、发布日期含时区且不晚于判断时点，再取符合条件的最高本地版本。它没有验证证据内容、独立可用时间或官方版本顺序；审计脚本的字段完整率不等于严格回测已具备全部条件。正式研究仍须按[项目规格](PROJECT_SPEC.md)补齐版本级证据、实际可用时点与研究验收。

schema 2 展示快照包含原有 121 个白名单展示系列每个期间的最新数值，以及四项获选外部背景各自的最近一期 `{period, value}` 摘要和快照生成时间；不包含四项背景完整历史，旧 schema 1 可兼容读取但无摘要。快照尚未经受众专属内容审定；不含原件路径、哈希、观测版本、质量或抑制证据。生成时间不是来源发布时间；展示端当前只有一般缺值提示，不能宣称与管理端具有同等来源解释和新鲜度能力。


### 2026-09-23 首次接入记录（历史，已被后续回补覆盖）

- 来源：Rentals.ca / Urbanation，2026 年 8 月报告内的公开图表 CSV；商业挂牌样本统计，非政府调查或 MLS 实际成交租金。
- `toronto_asking_rent_total`：2022-07—2026-07，49 个月，CAD/month；专建出租公寓与 condo 合并，全房型原始总体均值。
- `toronto_asking_rent_1br/2br/3br`：2026-07 单月快照。三卧不等于三卧及以上，未提供开间。
- 地区：Toronto (Rentals.ca market definition)，不声明与 Toronto CMA、City of Toronto 或 All TRREB Areas 边界完全一致。
- 历史图表：<https://datawrapper.dwcdn.net/cTPkd/1/>；房型图表：<https://datawrapper.dwcdn.net/o6p6T/1/>。原始 HTML 和 CSV 均保存到 `data/raw/rentals`。
- 2026-07 总体 2,577，一卧 2,242、两卧 2,956、三卧 3,655 加元/月。总体均值不是房型均值的简单平均；样本结构变化可能影响均值。
- 当时 2026-08 尚未接入，不补值；也不把报告标题中的 8 月当成观测月份。当时数据与记录页显示新鲜度不足。后续已扩展到本页顶部所列当前范围；过程及原图链接见[来源覆盖](SOURCE_COVERAGE.md)。


### 2026-09-26 新增背景系列字典（增补，优先于页首旧计数）

| 数据库 ID | 原系列与表 | 单位、频率 | 定义与限制 |
| --- | --- | --- | --- |
| `boc_prime_rate` | `V80691311` | %，月；Canada | 每月最后有效周三报价；不是央行政策利率；未季调 |
| `boc_conventional_mortgage_5y` | `V80691335` | %，月；Canada | 每月最后有效周三报价；不是新增贷款金额加权实际利率；未季调 |
| `toronto_nhpi_total` | `111955499`；18100205 | index, 2016=100，月；Toronto CMA 2011 boundary | 新建住宅房屋与土地综合指数；非转售 HPI，非全部 condo 市场；未季调 |
| `ontario_cpi_shelter` | `41691952`；18100004 | index, 2002=100，月；Ontario | 居住消费成本指数，包含租金和自有住房成本；不是房价指数；未季调 |
| `toronto_permits_units_34100066` | `122233956`；34100066 | units，月；Toronto CMA 2011 boundary | 住宅总体、全部工作类型、新增住宅单位；表于 2023-10 停更，独立保存不拼接；未季调 |
| `toronto_permits_units` | `1675206466`；34100292 | units，月；Toronto CMA 2011 boundary | 现行后继表 34-10-0292；住宅总体、全部工作类型、新增住宅单位；不是许可证张数、净增量、开工或竣工；未季调 |

以上六条是描述性背景，未纳入预测、展示快照或访客下载。覆盖与运行入口见[2026-09-26 来源增补](SOURCE_COVERAGE.md#2026-09-26-新增背景系列)。银行两序列保存的是月内最后有效周报价，不能称为实际贷款成交利率或日历月最后一天报价；JSON 保留原周值。NHPI 的房屋＋土地综合值由官方直接提供，不能把分项指数相加。Shelter CPI 是居住服务消费成本，含房市与利率的反馈，不是独立于房价的外生成本冲击。许可单位为新增住宅单位，`Types of work, total` 含新建与改造等，不能与住宅开工做一比一对应或相加。

新 CSV 的 `source_sha256` 指向同批官方 JSON 内容哈希，`source_url` 是可访问的官方系列／表入口；WDS 请求方法、vector 和返回元数据由提取器及 JSON 保存。`period` 为所属月，不是获取月或发布时间；质量、修订、保密标记保留在 JSON，数值表不伪造缺失值，遇未支持的数值质量状态会失败。旧表与现行许可表有不同数据库 ID；重叠期间不去重合并，因为可能存在修订与方法差异。

本次核验全库 131 个系列（129 个有值），5,944 条含版本观测、5,939 个不同系列／期间、166 份登记文件；前文较早基线保留为历史。


### TRREB 地区／房型独立 CSV（2026-09-26）

文件 `data/manual/trreb-districts-<起月>-to-<止月>-<内容哈希>.csv`；不是既有 `trreb-extracted-*.csv` 格式，不计入数据库系列与观测数。

| 字段 | 含义与单位 |
| --- | --- |
| `ym`, `house_type`, `region` | 所属月 YYYY-MM、房型代码、原报告地区标签；三者共同唯一 |
| `sales`, `dollar_volume` | 当月成交笔数、成交总金额 CAD；不是交割量 |
| `average_price`, `median_price` | 平均价、中位价，CAD；保留原报告整数 |
| `new_listings`, `active_listings` | 当月新增挂牌、月末在售挂牌数 |
| `snlr_trend`, `moi_trend` | 原报告趋势口径，分别为百分数和月；不能当自算原始 SNLR／MOI |
| `avg_sp_lp` | 平均成交价／挂牌价百分数，保留百分数数值，不除以 100 |
| `avg_ldom`, `avg_pdom` | 平均挂牌天数、平均物业上市天数，日；两种口径不混用 |
| `source_pdf`, `source_pdf_sha256` | 原 PDF 文件名与完整 SHA256 |

房型代码：`all_types`, `detached`, `semi_detached`, `townhouse`, `condo_townhouse`, `condo_apartment`, `link`, `coop_apartment`, `detached_condo`, `coownership_apartment`。不同房型页未提供的趋势／PDOM 列保持空白；零成交行不臆造均价、中位价或成交额。地区包含父级、子级和 Toronto district，不能把全部行相加。全房型 All TRREB Areas 才与首页全市场销量比较；单房型总计分别保留。

## 地区转售版本表与展示契约（2026-09-26）

`district_observations` 以 `(ym, house_type, region, version)` 为主键；`values_json` 保存提取 CSV 的 11 个数值字段，`raw_sha256` 绑定不可变 CSV，`pdf_sha256` 绑定该期官方 PDF。重复相同值不新增版本，已见旧原件不能覆盖新版本。该表独立于总市场 `observations`，不改变总表历史值。

展示快照可选字段 `districts` 只含年月、房型、地区与上述数值；不含文件路径、哈希或导入记录。`freshness` 只发布来源节奏对应的状态、最新／预期期间、落后期数及缺期列表。`unknown` 表示节奏未核验；`pending` 只是本地发布规则尚未到期，不证明官网一定未发布。
