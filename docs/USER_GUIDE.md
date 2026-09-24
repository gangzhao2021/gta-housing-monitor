# 本地看板使用指南

当前版本：2026-09-23。页面使用已保存的官方数据及 Rentals.ca / Urbanation 公开报告，打开页面不会自动联网或给出复苏预测。所有命令在项目目录执行。

## 后续展示与私有后台（未实施）

当前仍按下述本地流程使用。用户已要求精简页面分隔线／边框等装饰线，后续先在 Figma 中修改与复核，再落实代码；图表数据曲线不属于这次默认删减范围。同时将完整后台数据／管理功能限制为本人访问；后续拟发布经筛选的只读展示数据，展示受众、下载权限、主机和费用尚未确定。当前“数据与记录”、保存和下载步骤属于本地使用说明，不代表未来展示访客会拥有这些权限。网页已显示的数值不能保证不可复制；具体计划见[实施计划第 7 节](IMPLEMENTATION_ROADMAP.md#7-p4展示端私有后台与交付)。本次没有迁移数据或部署网站。

## 中英文切换 / Language

在页头右侧的 **语言 / Language** 选择 **中文** 或 **EN**。手机端可横向滚动顶部导航查看其他页面。页面、图表、说明与 CSV 表头随语言切换；当前页面、日期筛选和月供输入保留。原始来源名称、单元格与 JSON 观察记录保留原样，方便追溯。语言偏好保留在当前浏览会话中。

Use **语言 / Language** at the top right to choose **中文** or **EN**. On mobile, scroll the top navigation horizontally to reach other pages. Your current page, period filters and mortgage inputs are retained. CSV headings follow the selected language; original source references and JSON observation records remain unchanged.

## 第一次打开

1. 建立本地 Python 环境并安装锁定依赖。当前 Mac 的系统 Python 会被 Xcode 许可拦住，可直接使用 Codex 内置 Python：

   ```bash
   /Users/ryanzhao/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m venv .venv
   .venv/bin/python -m pip install -r requirements.lock
   ```

2. 导入已经保存的原始文件；重复执行不会增加相同观测：

   ```bash
   PYTHONPATH=src .venv/bin/python -m housing.cli boc
   PYTHONPATH=src .venv/bin/python -m housing.cli statcan
   PYTHONPATH=src .venv/bin/python -m housing.cli construction
   PYTHONPATH=src .venv/bin/python -m housing.cli population
   PYTHONPATH=src .venv/bin/python -m housing.cli cmhc-rental
   PYTHONPATH=src .venv/bin/python -m housing.cli trreb
   PYTHONPATH=src .venv/bin/python -m housing.cli status
   ```

3. 首次设置管理密码并启动仅本机可访问的完整管理页：

   ```bash
   .venv/bin/python scripts/setup_owner_password.py
   sh scripts/run_owner_local.sh
   ```

   浏览器打开 `http://127.0.0.1:8501`。密码不写入仓库，验证器保存在仅本机用户可读的 `.streamlit/owner_auth.env`。直接运行 `app.py` 而没有验证器会拒绝访问。

4. 如需演示只读页面，另开终端运行：

   ```bash
   .venv/bin/python scripts/publish_display.py
   .venv/bin/streamlit run viewer_app.py --server.address 127.0.0.1 --server.port 8502
   ```

   打开 `http://127.0.0.1:8502`。展示页只读取 `data/display_snapshot.json` 中获准的最新数值，不连接完整数据库，没有记录、原件及完整下载入口。它覆盖总览、月度／年度租赁及地区对比、经济与人口、月供情景；当前比完整管理页少地图、来源明细和部分分析功能。每次核验入库后需重新生成快照；生成失败保留上一版。正式分享前仍需补齐体验和身份／部署验收。

5. 官方 BoC／StatsCan 来源可手动执行 `.venv/bin/python scripts/run_refresh_cycle.py`。它顺序调用已有安全刷新、核查数据库完整性，然后只在全周期成功时原子发布展示快照，结果写到私有的 `data/run_reports/`。报告类来源仍需各自人工核验，尚未安装本机或远程定时任务；刷新网页不会抓取官网。

## 看数据与保存观察

顶部导航包含五页，各页的期间选择只作用于相应内容：

| 页面 | 如何使用 | 范围 |
| --- | --- | --- |
| 市场总览 | 选择“观察月份”和“趋势范围”，查看成交、库存、供需比与 HPI；下方“各房型基准价”比较所选月份的四类住宅 | TRREB `All TRREB Areas`；总量卡片为全房型，房型图采用 HPI 自己的分类 |
| 租赁市场 | 在“月度挂牌／年度存量／地区对比”切换视图；年度可比较五类房型，地区通过“编辑地区”和“口径与时间”调整 | 月度沿来源市场定义；年度Toronto CMA或源调查区，2022—2025年；各口径分列 |
| 经济与供给 | 利率与融资、就业、住宅建设、人口四节顺序展示；顶部页内导航可跳转。月度主题各自选择月份与趋势范围，人口单独选择“人口估计年份” | 利率为加拿大背景；就业与人口是 CMA 2021 边界；建设是 CMA 2011 边界 |
| 月供情景 | 输入贷款本金、摊还年限、情景年利率及对比年利率；下方历史图只替换已接入月份的按揭利率，可下载情景CSV | 固定本金和摊还期的假设比较，金额为加元；历史线不是当年借款人的实际月供 |
| 数据与记录 | 查看来源新鲜度、指标定义、导入结果；保存或下载月度观察 | 本地保存的资料及版本，不自动联网更新 |

### 理解变化与缺失

- 指标名称旁的 **ⓘ** 可悬停查看影响房价的机制，点击可保持展开／收起，键盘可聚焦后按Enter；手机点击。说明支持中英文，是机制解释，不是确定的涨跌预测。
- 数据来源总表将原表抑制值显示为“来源抑制发布”，同时列出应有所属期；“最近所属期”仍是最近有数值的期间。这与尚未更新或零值不同。

- 卡片严格显示所选月份或年份。该期缺值时显示“暂无数据”，不会用较早值顶替；融资页会另行提示最近较早的值及其所属月份。趋势图在缺期处断开，表格与 CSV 保留空白，不填零。
- 同比对照上年同月或上一年度；缺少该期对照时不计算。利率、失业率及空置率用百分点变化，库存月数用月数变化，其他数量和金额用百分比。变化使用中性颜色，不自动解释为好坏。
- TRREB 总量“较上年同期”由各月原始发布版自算，可能不同于后续修订后的官方同比。MOI、SNLR 是本项目的原始月公式，不等于报告中的 `Trend`。
- “各房型基准价”是标准化住宅的 HPI 基准价，不是平均成交价。展开“房型数值与来源”可看原报告同比、原始分类和页码。该图沿所选观测的 CSV、PDF 来源哈希核对数据，不直接采用后来下载的同月报告；HPI 的 Attached 不替换为成交表的 Semi-Detached。
- 租金为 CMHC 调查的平均月租金，包含现有租约，不是当下 MLS 挂牌或新租客报价。“均值较上年”可能受样本构成影响，不等于官方同样本租金涨幅。全房型均值直接取原表，不把各房型简单平均。租赁年度选择不受市场总览月份影响；condo 空置率只有总体值，不推算房型空置率。当前租赁页范围为公寓，未混入工作簿中的 Townhouse 独立表。
- 住宅建设另有“按住宅类型比较”，分别查看开工、竣工或在建的四类住宅。若原表分项与总数不一致，页面保留原值并提示，不能把“公寓及其他住宅”解释为 condo 预售或待售库存。人口年度值不插值为月度数，也不与不同边界的建设量计算人均比率。

### 下载与记录

- 月度页面展开“查看与下载本节数据”，下载与当前趋势范围一致的 CSV。HPI 房型和建设房型的来源详情内也有独立下载，包含来源文件和哈希。
- 租赁页可“下载房型租金对照”，导出所选调查年度的房型、金额、质量标记和来源单元格；“年度变化与调查口径”内还可下载来源质量明细。
- 在“数据与记录”页的“月度观察记录”选择月份，点“保存本地记录”。记录保存在 `data/observations/`，随后可在“打开既有记录”查看数值表、展开完整凭据或“下载这份记录”。每次保存新文件，不覆盖旧记录。记录含输入观测 ID、版本、原文件哈希、资料所属月份与未更新系列，没有复苏评分。选择历史月份只筛选当前已保存的历史资料，不代表还原当时已知的信息。
- “数据与记录”页的“来源覆盖与更新时间”显示最近所属期、状态和历史缺月；“指标定义与原始来源”可打开官方来源，“最近导入运行”显示成功或失败记录。

### 月供情景

“月供情景”按加拿大名义年利率半年复利换算等效月利率，再计算月付本息。初始利率取数据库中最新的新增非受保固定五年及以上平均值，并显示所属月份。两个利率可分别修改，右侧月供数字及比较图同步变化；当前网页会话中切换导航后保留输入。清空任一参数会提示补齐，零本金则正常显示零月供。结果只包含本金与利息，不含税费、保险、管理费等开支，也不是银行报价或获批额度。

“数据与记录”页的“数据边界与预测验证状态”说明剩余限制。历史首次发布日期、修订版本的公开时点、季节比较规则与样本外验证尚未齐备，页面不生成复苏标签或预测。

## 月度更新

BoC与三张StatsCan表现在可以通过独立入口检查和安全导入，网页浏览本身不会触发下载。入口使用官方URL，下载内容哈希去重；新内容先保存原件、解析，再用SQLite backup API备份数据库后事务入库。网络／解析失败会留下运行记录，不会把缺值填零。一次运行的四个来源分别报告成功、无变化或失败：

```bash
PYTHONPATH=src .venv/bin/python scripts/refresh_official.py --source all
PYTHONPATH=src .venv/bin/python scripts/refresh_official.py --source boc
```

`all`包括BoC（含新增固定按揭）、就业、建设、人口。此刷新入口返回的 `unchanged` 表示响应哈希与已成功导入文件相同；它与下文导入摘要中“同值重复”的计数含义不同，两者均不直接证明官方尚未发布。此入口**尚无定时调度**，也不处理TRREB PDF、Rentals.ca图表或CMHC年度工作簿；这些仍需按下述来源步骤核验。长期运行主机和检查时刻确定后再启用调度，不要把本地电脑休眠时的空档误当作来源没有发布。

先确认官方新一期已经发布；对每个新文件使用新名字，保留原有文件。当前示例的 2026-09 月份尚未完成，不能混入完整月比较。

可以一次下载央行、就业和建设公开快照；人口全表约 22 MB，需显式选择：

```bash
.venv/bin/python scripts/download_public_data.py --end-month 2026-08
.venv/bin/python scripts/download_public_data.py --end-month 2026-08 --include-population
.venv/bin/python scripts/download_public_data.py --end-month 2026-08 --include-rental --rental-year 2025
```

默认截止上一个完整月份。相同文件名已存在时不会覆盖；更正或复核时先手工改用新文件名。下载之后仍需分别导入并检查页面中的运行状态。

- BoC：从 [Valet](https://www.bankofcanada.ca/valet-api-how-to/) 获取 `V39079,BD.CDN.5YR.DQ.YLD,V122667786` 的 JSON，保存到 `data/raw/boc/`。例如新文件 `core-2026-09.json`，再运行：

  ```bash
  PYTHONPATH=src .venv/bin/python -m housing.cli boc --file data/raw/boc/core-2026-09.json --source-url '完整的实际下载 URL'
  ```

- StatsCan：从 [表 14-10-0460-01](https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1410046001) 下载整个英文 CSV ZIP，放在 `data/raw/statcan/` 且不覆盖旧 ZIP，使用 `housing.cli statcan --file 路径 --source-url '实际下载 URL'`。导入器固定筛选 Toronto CMA、2021 边界、Estimate、单月季调三率。
- 建设背景：下载 [表 34-10-0154-01](https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=3410015401) 英文 ZIP，以新文件名保存后运行 `housing.cli construction --file 路径 --source-url '实际下载 URL'`。导入器筛选 Toronto CMA **2011 边界**的实际总单位开工、竣工和在建量；房型比较读取对应观测所引用的原始 ZIP，并核对分项与总数。不可用 SAAR 代替实际量。
- 人口背景：下载 [表 17-10-0148-01](https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1710014801) 英文 ZIP，以新文件名保存后运行 `housing.cli population --file 路径 --source-url '实际下载 URL'`。导入器筛选 Toronto CMA **2021 边界**、总性别、全年龄组的 7 月 1 日估计；不插值成月度值。
- 租赁背景：可用下载脚本 `--include-rental --rental-year YYYY` 保存 CMHC Toronto RMS 工作簿（文件已存在时不覆盖）。运行 `PYTHONPATH=src .venv/bin/python -m housing.cli cmhc-rental`。导入器从 Toronto CMA 总计行提取两期五类租金、专建出租总体及房型空置率、condo 总体空置率；专建出租租金来自表 1.1.2，condo 两期租金来自表 4.1.3。当前已保存2023与2025版工作簿，合计覆盖2022—2025年，保留原表质量与抑制标记，未公开值不填零。将来工作簿版式或表头变更时需先核对；请另存原文件再用 `cmhc-rental --file 路径 --source-url '实际下载 URL'` 导入。页面按年度展示两种调查。
- TRREB：从 [Market Watch 档案](https://trreb.ca/market-data/market-watch/market-watch-archive/) 下载新月官方 PDF；也可运行 `.venv/bin/python scripts/download_trreb.py 2026-09 2026-09`。随后运行 `.venv/bin/python scripts/extract_trreb.py`，核对新 CSV 的目标月份、PDF 页码和五个数字，再运行 `PYTHONPATH=src .venv/bin/python -m housing.cli trreb`。提取器遇到缺页、表头不符或异常数值会报错，不导入未通过的月。
- 每次更新运行 `housing.cli status` 并查看“数据与记录”页“最近导入运行”。`inserted` 是新观测，`unchanged` 是同值重复，`revised` 是同一系列同一期间数值改变。一个来源更新成功不代表所有来源已更新。
- 导入器会在写入前检查系列、期间格式、数值范围及同批次重复期间冲突。整批文件异常时不会写入任何观测；原始文件哈希会保留，失败原因写入导入记录并显示在页面详情中。修正文件后用新文件名重试，旧文件与失败记录继续保留。

## 备份与恢复

备份 `data/housing.sqlite3`、整个 `data/raw/`、`data/manual/`、`data/observations/` 和 `requirements.lock`。这些合起来才能保留原文件、提取版、数值修订与月度记录。恢复时把它们放回相同相对路径，再运行 `housing.cli status`、打开网页并核对一条观察记录的输入版本与值。可运行 `.venv/bin/python scripts/check_restore.py` 在临时目录演练并核对哈希。数据库文件不要与正在写入的导入操作同时复制；先停止网页及更新进程，或使用 SQLite backup API。

如果出现报错，复制终端的完整错误文字及“数据与记录”页“最近导入运行”的对应行。若 SQLite 文件损坏，可先从备份恢复；勿删除原始文件或覆盖唯一备份。

## Rentals.ca 月度挂牌租金

租赁市场默认显示月度挂牌租金；“租金数据口径”可切换到 CMHC 年度存量租金。
月度总体序列已接入2022-07—2026-07（49个月）；一卧、两卧、三卧各有2025-11—2026-07（9个月）。开间历史尚未核验接入，不等于来源从未发布。选择更早月份时不以最新房型报价补缺。

来源为 Rentals.ca / Urbanation 2026 年 8 月报告内的公开 Datawrapper 图表，报告月份与观测月份相差一个月。2026 年 9 月报告页面虽然可在线阅读，但本次没有取得并核验对应原始数据集，因此未写入 8 月观测。当前不是自动联网刷新。

更新步骤：从新一期 Rentals.ca 报告找到同口径图表，保存其公开 HTML 与 `dataset.csv` 为新文件，不覆盖旧版本；逐项核对 Toronto、市况范围和报告期间。然后分别导入总体历史及房型快照：

```bash
PYTHONPATH=src .venv/bin/python -m housing.cli rentals \
  --file data/raw/rentals/2026-08-report-history.csv \
  --chart data/raw/rentals/2026-08-report-history.html \
  --source-url https://rentals.ca/blog/rentals-ca-august-2026-rent-report

PYTHONPATH=src .venv/bin/python -m housing.cli rentals \
  --file data/raw/rentals/2026-08-report-bedrooms.csv \
  --chart data/raw/rentals/2026-08-report-bedrooms.html \
  --source-url https://rentals.ca/blog/rentals-ca-august-2026-rent-report
```

解析器验证标题、发布者、公寓/condo 范围、日期、连续月份、房型列和数值范围；未知格式拒绝导入。两个文件的哈希均登记到 manifest，观测链接到原始 CSV。再次导入相同数据不生成重复观测；数值修订保留版本。不将图表修改时间冒充正式发布日期。每月 15 日为本地新鲜度检查日，不是来源发布承诺。


### 分房型来源注意事项

- 房型历史目前各9个月，房型菜单也可同时比较一至三卧。同比缺上年观测时不计算。
- 2026-04三卧采用图表dvDEZ第2版CSV的3,567；报告正文为3,558，存在来源内部差异，采用已存档图表版本，未以正文覆盖。
- 原始HTML、CSV和版本来源保存在`data/raw/rentals/`。不得混用全部物业与公寓／condo范围。

## 地区租金对比（2026-09-23）

入口：租赁市场 → 地区对比。点击“编辑地区”或地图位置点选择最多三个地区；已选的对比地区可再点一次移除，主要地区从“编辑地区”更换。“口径与时间”内选择月度挂牌或年度CMHC及期间，年度另可选择平均租金／空置率。外部房型菜单选择同一房型。地图点只帮助选区，不代表统计边界；地区控件仅作用本视图。

- 月度保持专建出租公寓＋condo同口径：North York、Scarborough、Markham、Vaughan、Mississauga、Oakville总体各覆盖2025-11—2026-07（9个月）；除Markham外一／两卧各覆盖2026-04—07（4个月）。Markham月度分房型未接入。Toronto总体49个月、房型9个月。
- CMHC 专建出租公寓：2022—2025，五类房型租金及空置率。North York、Scarborough、Mississauga、Oakville、Markham；另有 Richmond Hill/Vaughan/King 和 Aurora/Newmarket/Whitchurch-Stouffville 组合调查区。组合值不能拆给某个城市，部分数据抑制。
- Downtown 无已核定边界和对应数据；Richmond Hill/Aurora 无独立月度数据。选择不可用组合会明确提示，不能借用 Toronto。Oakview 暂按 Oakville 理解。
- 地区定义沿用来源名称；不能把相邻/包含地区相加。挂牌均值也不能把各地区简单平均生成 GTA 均值。

地区月度原件使用以下命令；后续月份保存新文件名并换成相应报告 URL：

```bash
PYTHONPATH=src .venv/bin/python -m housing.cli rentals-regions \
  --file data/raw/rentals/2026-08-report-apts-cities.csv \
  --chart data/raw/rentals/2026-08-report-apts-cities.html \
  --source-url https://rentals.ca/blog/rentals-ca-august-2026-rent-report
```

Markham 采用 `2026-08-report-regions-cities.csv/html`，同一导入命令。季度 MLS 实际成交租金尚未接入，相关公开页面本次读取返回 403；不使用挂牌租金替代。
年度地区复用已存档 CMHC XLSX，用 `cmhc-regions --file ... --source-url ...` 导入；URL 从 manifest 对应原件记录读取。原始质量等级、抑制状态、表名与单元格保留在地区导出中。

### 租金历史长度与来源差异

在“地区覆盖与边界说明”查看自动生成的地区/房型覆盖表；0 个观测表示尚未接入。2026-09-23 回补后，六个地区总体和 Toronto 一至三卧有 2025-11—2026-07 九个月；其他已支持地区的一/两卧仍为四个月。各图显示实际观测数，短于一年不能用来判断全年季节性。地区总体统一使用 Top 25 公寓/condo 图；2026-04 城市表与排名图存在未解释差异，来源选择调整已保留版本和说明。
