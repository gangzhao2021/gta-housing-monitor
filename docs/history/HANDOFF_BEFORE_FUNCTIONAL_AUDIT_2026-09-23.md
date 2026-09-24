# 工作交接

最新复核：2026-09-23。此次按用户反馈重做 dashboard 并检查两卧之外的同类覆盖问题。完整证据见 [验收状态](docs/PROJECT_ACCEPTANCE.md)。

## 最新检查点：地区租金对比（2026-09-23）

- 新增第三租赁视图“地区租金对比”。最多三个地区、同房型比较；月度 Rentals.ca 公寓/condo，年度 CMHC 专建出租租金/空置率；中英文与同范围来源导出。
- 月度5个外围地区 ×3系列 ×4个月，加 Markham 总体2个月；年度7个源调查区 ×5房型 ×2指标，覆盖2022—2025（抑制单元格不造值）。具体覆盖与不可用原因见 USER_GUIDE/SOURCE_COVERAGE。
- Downtown未接入；Richmond Hill/Aurora独立月度未接入，年度仅组合调查区；MLS成交租金未接入（公开页面403）。不把组合区称为单个城市。
- 39项测试通过；数据库121系列、5,318条观测、82份原件。恢复验证通过；原数值未修改。此前统计均为历史检查点。
- 新代码：regions.py映射、regional_ingest.py解析、regional_view.py地区视图；CLI增加rentals-regions/cmhc-regions。原CMHC解析器可指定地区行和前缀，默认行为保持Toronto CMA。

## 最新检查点：月度挂牌租金接入（2026-09-23）

- 用户授权接入更细频率租金来源。新增 Rentals.ca / Urbanation 公开图表解析、CLI 导入、四个系列、新鲜度规则；页面默认月度，可切换 CMHC 年度视图。
- 总体 49 个月（2022-07—2026-07），房型三条（2026-07）。新导入 52 条，原有值未修改。数据库共 35 系列、4,989 条观测、60 份原文件。
- 中英文月度走势、同比/环比、房型报价、期间控制、来源与版本 CSV；缺历史房型不挪用当期快照。
- 全套 34 项测试通过，包括原始来源数值、重复导入、非法批次、期间与导出、中英文及原有 CMHC 视图回归。
- 下载与导入仍需逐期运行，未设置自动更新任务。2026-09 报告存在，但其对应原始数据集未核验，当前没有 2026-08 观测。
- 下方较早统计为历史检查点；本节为最新状态。更新命令见 USER_GUIDE。领先信号、发布时点回测及其他原有外部缺口未因租金接入而完成。

## 当前状态

- 应用：`app.py`，五页导航；可复用展示在 `src/housing/dashboard.py`，日历范围/比较在 `presentation.py`。
- 租赁：两类公寓市场 × 五类房型 × 2024/2025；16 租赁系列、32 个观测，质量与来源保留。旧版两卧和 condo 单年份是实现遗漏，现已修正。
- HPI 与建设：`breakdowns.py` 提供原始房型细分与来源；HPI 必须用 `trreb_hpi_for_observation`，避免关联未被观测采用的后来报告。
- 数据库 31 系列、4,905 条观测。新增 25 个租赁观测，已有 7 个未变，无数值修订；导入前 SQLite 备份在 `/tmp/housing-before-bedroom-expansion.sqlite3`（临时备份，不能当长期归档）。
- 28 项测试通过；恢复核对 4,905 条、55 个原文件、1 个既有观察记录。五页与四主题经过 AppTest；实际浏览器检查 1440/390/320px。
- 具体已修正：筛选不作用年度数据的误导、旧月份顶替卡片、非连续年同比、百分点表达、缺月连线/UTC 月坐标、月供输入重置、快照提前引用年度数据和日频误判过期、CSV 丢缺失组合、元数据关联错误。

## 继续工作的约束

### 2026-09-23 租赁历史与图表补充

- 新增 `data/raw/cmhc/rmr-toronto-2023-en.xlsx` 官方原件，菜单现为 2022—2025。16 个 CMHC 系列共有 64 条观测；数据库总计 4,937，56 份原件。原有数据未修订；导入前临时备份 `/tmp/housing-before-rental-history.sqlite3`。
- 解析器兼容历史 Bachelor=Studio，仍逐表验证 2021 census 地区定义。新历史通过原有导入接口记录来源与哈希；恢复验证已包含新文件。
- 租金年度双线图（房型选择、截止年、来源和质量 CSV）放到租赁页主区域；总空置率趋势常显；市场总览新增年月成交热力图。年度点位不插值，最早年也能显示单点。
- 全套 31 项测试通过，恢复核验成功。此前本文件的观测数和测试数为历史检查点，以本节为准。

### 2026-09-23 视觉修订

- 中英文切换：侧栏 `语言 / Language`，默认中文；五页导航、指标、图表、说明、数据表及 CSV 本地化。`src/housing/i18n.py` 为显示边界，`en.json` 为英文词表。指标 ID、选择值、数值、来源工作表/单元格和原始 JSON 记录保持原样。选择状态单独保存，避免翻译控件标签后重置筛选或月供输入。
- 中英文页面集成共 8 项通过：五页/四主题、英文图表字段与实际数据绑定、租金数值、切换后期间与月供保留、CSV 数值一致。实际浏览器切换英文，检查 1440px 桌面与 390px 手机租赁图表/表格。原始来源名称可保留源语言；本次未重新运行数据管道测试。

- 用户随后要求更活泼的色彩：白底与平面布局保留，房价蓝、成交青绿、供应暖橙、库存月数紫；指标和曲线由 `series_color` 保持一致，组合/单系列切换不换色。租赁图表与表头使用青绿/蓝对应两类市场，导航和提示区增加浅色点缀。涨跌保持中性文字，多系列线型保留。实际复核桌面总览与租赁页；此轮纯配色调整未重跑业务测试。

- 后续布局复核：房价移为首张全宽 380px 主图，摘要房价优先；成交图独占一行，库存趋势直接展开。HPI 指数保留在数据表，取消重复摘要。利率默认三线对照，保留单指标选择；经济趋势图 340px，多系列采用纵向图例与不同线型。租赁全宽图表及月供双情景布局保留。
- 此次布局调整后 6 项页面测试通过，筛选与首张房价图/成交图/CSV 一致性已核对；实际浏览器检查 1440px 房价主图及 320px 主图、利率图例与缺期展示。

- 按用户指定，实读并运行 BOP-RMS 的 `.local/make-v29-review` Figma 导出界面作为参考，对照 `docs/spec/design/bop-rms-figma-make-brief.md`。参考项目未修改。
- 看板改为白底、近黑正文、灰色辅助文字、细线分区、196px 窄侧栏；指标使用平面分栏，图表统一黑灰配色，控件保留 4px 小圆角。样式集中于 `src/housing/dashboard.css`。
- 本次重新运行 6 项页面集成测试并通过；浏览器实际检查 1280px 桌面、390px 和 320px 手机租赁图表/表格，以及 320px 导航切换与指标布局。320px 页面宽度未横向溢出。已恢复默认预览尺寸。
- 此轮为视觉修订，未重新运行前述全套 28 项测试；数据范围和预测有效性限制仍适用。

1. 来源没有变化时不需反复追取；新数据按 [使用指南](docs/USER_GUIDE.md) 保留原文件后导入。
2. 公开数据还有地区与其他细分，不能将“未接入”写成“官方没有”。目前租赁明确是公寓范围。
3. CMHC 租金均值变化不是同样本租金涨幅；质量/显著性提示和导出不可去掉。
4. 按揭保存数据仍到 2026-06；必须显示准确所属期。近期空缺由数据来源提供后才能补齐。
5. 预测与领先信号未验证。逐期公布日、历史修订可用时点、季节比较方法、样本外检验尚待完成，不能将看板修正称作整个预测项目完成。
6. 原始建设在建分项 1982-01、1988-01 与总量不一致；源表质量提示已保留。
7. 本目录没有 Git 仓库。没有部署、远端推送、外部通知或付费来源操作。

## 启动与验证

```bash
.venv/bin/streamlit run app.py
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/check_restore.py
```

`.streamlit/config.toml` 定义浅色主题与保存后重载。本轮已重启服务、干净加载并复核新版租赁页。用户无需提供额外数据即可查看这次补齐的房型。


### 2026-09-23 分房型月度历史补充（取代前述单月覆盖限制）

- 从 2026 年 3—7 月报告的公开房型图表补入 2026-02—2026-06，一/二/三卧现各有 2026-02—2026-07 六个月连续观测，共 18 条。
- 月度页新增全房型、一卧、两卧、三卧、房型对比选项。按所选系列限制月份范围，使用独立颜色及可见点位，导出同期间各房型来源记录；同比缺上年观测时不计算。
- 全房型历史仍为 2022-07—2026-07。分房型更早历史、开间及 2026-08 尚未接入，不代表来源没有发布。报告正文出现过开间数据，但本次公开图表 CSV 只有一/二/三卧。
- 4 月三卧采用图表 dvDEZ 第 2 版 CSV 的 3,567；5 月报告正文为 3,558，存在来源内部差异，采用已存档图表版本，不以正文覆盖。记录于原件与 CSV 版本来源。
- 新增 15 条，数据库共 5,004 条观测，70 份原文件。原始 HTML/CSV 保存于 data/raw/rentals，后续更新沿用 rentals CLI。

### Markham 短历史提示修正

用户发现月度 Markham 仅为向下直线。核对确为两条已接入观测：2026-06 2250、2026-07 2211。地区图上方新增所选期间实际观测数；1—2点时明确提示不足以判断长期趋势。已在用户当前 Markham 页面确认中文提示生效，未修改任何数据；历史仍未补齐。

## 2026-09-23 Markham 与同类历史缺口回补完成

取代上一节“两点尚未补齐”状态：六个地区总体、Toronto 一/二/三卧现各有 2025-11—2026-07 九个月。41 条新增、5 条总体来源调整保留版本，现 5,364 条含版本观测、102 原件。地区总体统一 Top 25 图，禁止城市表再次覆盖；2026-04 来源内部差异详见 SOURCE_COVERAGE 最新节。其他地区房型仍仅 4 个月，未冒用全部物业表。覆盖表自动计算，新增 RENTAL_COVERAGE_AUDIT.csv 快照。42 测试与恢复校验通过，浏览器当前 Markham 九点曲线确认。最新月缺口、未接入地区/房型仍明确显示，不宣称全项目验收完成。

## 2026-09-23 无数据房型交互修正

完成月度 7 地区×4 房型和年度 7 分区的可用性复核。地区房型选项按当前地区标记无数据/部分缺失；提示区分月图未提供与 CMHC 抑制。Markham 月度一/两卧可显式切换同房型年度存量租金，回调保留地区/房型并取消无关对比。43 测试通过。未新增月度分房型数值，源图未提供的组合仍缺失。

## 2026-09-23 UI 信息层级整理

延续浅色极简与系列配色：浅灰画布、白色指标卡、细彩色顶边、圆角控件。地区筛选统一面板，年度指标/观察期并排，手机保留双列且主地区全宽。房型缺失标签缩短为“暂无数据/部分可用”；来源详细说明、覆盖表和季节性限制移入数据展开区，断点/短序列与缺失提醒保留。地区图高 420px。桌面 1440 与窄屏 390 实际截图检查；43 项全套测试及最终年度面板调整后的 14 项 UI 测试通过。未改数据。

## 2026-09-23 按用户截图精简控件

用户具体指出巨型下拉框、筛选区套框和来源说明栏厚重。租赁一级选择改横向页签（内部值不变，rental-view 现为 radio）；地区筛选去外框并改为下划线样式，桌面为四项工具栏+三地区一行，来源标题简化。全局展开说明改细分隔线、透明背景、小字号，保留键盘与原生展开交互。14 项 UI 回归通过；独立浏览器预览验证页签、地区图和来源展开/收起，未改变用户当前页面。

## 2026-09-23 回归白底极简风格

按用户确认的 SSENSE/Apple 方向收敛样式：删除浅蓝灰画布、圆角指标卡和彩色顶边的覆盖规则，恢复白底、细分隔线和无框指标排版。保留彩色数字/曲线、蓝色页签与键盘焦点；地区工具栏和细线说明展开行保持。只改 CSS，浏览器检查桌面与 390px 手机总览，数字完整显示，临时预览已关闭、尺寸已恢复。本次未重跑业务测试。

## 2026-09-23 Figma visual redesign draft

User approved using yashirq's team. Created https://www.figma.com/design/xKNAErf19Uep7K3z5Lqvco with two desktop frames (3:156 overview, 3:234 regional rentals), two mobile frames (3:320, 3:385) and unavailable-bedroom state (6:29). Actual SQLite observations used for editable vector charts. Desktop/mobile screenshots reviewed; auto-layout sizing fixed, mobile rental controls compacted. Draft uses white editorial layout, dominant chart, saturated series colours, left contextual rail on desktop, compact mobile selections. Imported SDS button instances; Inter/Noto Sans SC. Not implemented in running app; not a fully wired prototype. Details and source snapshot in design/FIGMA_REDESIGN_BRIEF.md and design/figma-data-snapshot.json. No publication/sharing changes.

## 2026-09-23 Approved Figma design applied to the live dashboard

Supersedes the draft-only status above. Implemented the approved editorial direction in all five live Streamlit pages: horizontal masthead/navigation, white canvas, thin dividers, saturated series colours, and desktop context rail beside the dominant chart. Overview price moved beside the hero chart with supporting market metrics below. Monthly, annual and regional rental views, economy/supply, mortgage scenarios and data/records now use the shared system. Regional selections moved into an Edit regions popover; source/period controls are in a disclosure. Original widget keys, source exports, history gaps, missing-bedroom alternatives and calculator persistence retained.

Mortgage comparison now includes a calculated two-bar view; missing input is explicitly distinct from zero. Fixed duplicate default/session-state warning, added popover localization and a chart/input regression. Full suite: 44 tests passed; isolated database tests do not write real records. Browser reviewed at 1440×1000 and 390×844: all five pages, rental variants, regional editor, language switch and native controls. Server restart caused temporary connection errors; subsequent page navigation/rendering succeeded. Local Streamlit restarted on 127.0.0.1:8501. No observations imported or replaced in this UI change.

Figma reference frames remain visual specifications; no new Figma frames or publication/sharing changes made. Native accessible Streamlit controls substitute for SDS button mockups; dynamic Altair charts use actual database rows, not exported chart SVGs. This UI delivery does not close the pre-existing data freshness / leading-signal validation limitations.

## 2026-09-23 Indicator impact explanations

Added bilingual qualitative explanations to shared metric-card labels, with a discreet ⓘ trigger. Desktop pointer hover previews the bubble; native details support click/touch and keyboard Enter toggling. Coverage includes policy/bond/mortgage rates, resale activity/inventory ratios, labour market, construction, population, HPI, rents and vacancy metrics rendered through cards. Each explanation separates a potential price channel from its limitations and links to Bank of Canada background. These are explanatory mechanisms, not estimated effects or forecasts; observations/calculations unchanged. Verified actual policy-rate bubble, closed-disclosure hover preview, 390px width and language labels; 15 dashboard regressions passed.
