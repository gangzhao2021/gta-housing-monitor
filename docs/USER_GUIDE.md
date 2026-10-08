# 本地看板使用指南

当前版本：2026-10-07。页面使用已保存的官方数据及 Rentals.ca / Urbanation 公开报告，打开页面不会自动抓取来源更新或给出复苏预测；地图底图等外部资源仍可能联网加载。所有命令在项目目录执行。以下操作按现有脚本说明，本轮新增外部背景数据已实际导入并完成恢复检查；以下启动与改密步骤未再次执行。

## 本地展示与私有后台（部分实施）

四项外部背景的管理入口是 `http://127.0.0.1:8501/` → “数据与记录” → “外部因素背景（研究中）”；本人演示入口是 `http://127.0.0.1:8502/` → 登录 → “经济与供给” → “外部背景（研究中）”。展示端表格列出每项最近值、单位、所属期和地区；点名称旁的 ⓘ 可查看可能的影响路径、不能直接推断房价的限制及该项官方来源，表格下方也保留直接来源链接。展示端不提供这四项的摘要复制／下载控件；首页另有入口提示。需运行发布脚本或成功完成更新周期，才会把后台新值写入展示快照；仅刷新网页不会抓取官网。[页面验收证据](PROJECT_ACCEPTANCE.md)记录了本机实际结果。

本机两端仅供本人演示。页面装饰线已先在 Figma 精简、再落实代码；图表数据曲线保留。管理端和本机只读展示端都设本机密码门禁并仅监听 `127.0.0.1`；展示页读取经筛选快照，不能访问管理页“数据与记录”、保存和完整下载功能。两个本机进程仍使用同一本机账户；另有发布为私有 Claude Artifact 的静态网页版，未迁移后台。具体计划见[实施计划第 7 节](IMPLEMENTATION_ROADMAP.md#7-p4展示端私有后台与交付)。

## 网页版（私有 Claude Artifact）

打开 [GTA Housing Monitor](https://claude.ai/artifact/6kMnQMgJdnwbPuiMC4taXK)，默认只有本人可见；如需给他人看，在页面的分享菜单设置，并先确认 TRREB 与 Teranet 数据的使用条款（Teranet 仅限非商业个人用途）。网页版提供市场、租赁、经济与供给、月供四页，含中英文、市场温度、长期房价、价格段分布与指标说明。市镇环比地图用随数据打包的统计局市镇边界绘制，不依赖外部地图服务。网页版不提供“保存视图链接”：Artifact 链接不保留筛选状态。它是 `site/dist` 静态文件，不运行 Streamlit：来源明细表、私人记录、后台管理和完整导出不在网页版。

**自动更新**：本机每天 09:00 与 14:00 更新数据并导出 `site/dist/data.json`；Claude 定时任务 `republish-gta-housing-artifact` 在 09:20 与 14:20 检查，只有当天周期成功且网站文件变化时才重新发布到同一链接。任务需要 Claude 应用开着，关闭时会在下次打开补跑。首次使用请在侧边栏“定时任务”点“立即运行”批准权限。手动检查：`.venv/bin/python scripts/artifact_publish_state.py --check`。

**原 Codex Sites 版**已于 2026-10-07 停止更新（`~/.codex/automations/automation/automation.toml` 设为 PAUSED，原文件已备份），站点本身需在 Codex 中删除。

## 中英文切换 / Language

在页头右侧的 **语言 / Language** 选择 **中文** 或 **EN**。`GTA HOUSING MONITOR` 是固定产品名称，不随语言切换；导航、图表、说明与 CSV 表头随语言切换。手机端可横向滚动顶部导航查看其他页面。当前页面、日期筛选和月供输入保留。原始来源名称、单元格与 JSON 观察记录保留原样，方便追溯。语言偏好保留在当前浏览会话中。

Use **语言 / Language** at the top right to choose **中文** or **EN**. `GTA HOUSING MONITOR` remains the product name in both languages. On mobile, scroll the top navigation horizontally to reach other pages. Your current page, period filters and mortgage inputs are retained. CSV headings follow the selected language; original source references and JSON observation records remain unchanged.

## 第一次打开

1. 已有可用 `.venv` 时无需重建；本次核对其 Python 为 3.12.14。新环境按对应 Python 安装锁定依赖，当前锁文件不等于所有系统均已安装验证。下列第一行是本机已有 Codex Python 路径示例，其他机器换成已安装的 Python。系统 Python 曾遇到 Xcode 许可问题，不能据旧记录断言当前仍然如此：

   ```bash
   /Users/ryanzhao/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m venv .venv
   .venv/bin/python -m pip install -r requirements.lock
   ```

2. 明确数据来自哪里。当前已有 `data/housing.sqlite3` 时不要为了启动而重跑历史导入。Git 排除了整个 `data/`：新电脑应先按下文从完整私有备份恢复，或按来源逐项采集重建。没有原件时下面的无参 CLI 默认文件并不存在；默认文件也不能补齐全部租金与地区历史。

   在新建或恢复数据前，限制当前账户生成文件的默认权限：

   ```bash
   umask 077
   mkdir -p data
   chmod 700 data
   PYTHONPATH=src .venv/bin/python -m housing.cli status
   ```

   `status` 是管理 CLI，会初始化／同步系列目录；它不是数据库完整性或新鲜度验收。采集重建需逐一选择已核验的文件，显式传 `--file`、`--source-url`，Rentals 另传 `--chart`，TRREB 另核对 `--pdf`。无参入口固定引用历史文件，不能作为自动选择最新版本的机制。导入时若输入原件不在私有 `data/raw` 或 `data/manual`，会按哈希复制到 `data/raw/imported` 以供完整备份；导入器拒绝同一原件曾入库旧值的重放，不同原件的官方修订先后仍需核验。

3. 首次设置管理密码并启动仅本机可访问的完整管理页：

   ```bash
   .venv/bin/python scripts/setup_owner_password.py
   sh scripts/run_owner_local.sh
   ```

   浏览器打开 `http://127.0.0.1:8501`。默认密码至少 16 字符；用户已选择仅本人本机演示，若要使用 6 字符密码，设置时运行 `.venv/bin/python scripts/setup_owner_password.py --local-demo`。两次输入须一致；明文不写入文件，验证器保存在仅本机用户可读的 `.streamlit/owner_auth.env` 并被 Git 忽略。两个启动脚本都只监听 `127.0.0.1`；6 字符密码不适用于将来远程访问，届时应先换强密码并重新验收。已有验证器时后续只运行启动脚本；设置脚本会拒绝覆盖已有文件。直接启动且未配置验证器时，默认门禁拒绝访问。

4. 如需演示只读页面，另开终端运行：

   ```bash
   .venv/bin/python scripts/publish_display.py
   sh scripts/run_viewer_local.sh
   ```

   打开 `http://127.0.0.1:8502` 并输入与管理端相同的本机密码；未配置验证器时默认拒绝访问。展示页在代码中只读取 `data/display_snapshot.json`，没有记录、原件及完整下载入口。schema 2 快照保存原有展示系列各历史期间的最新版本（有数值的才输出），并额外保存四项外部背景各自的最近一期摘要；不发布这些背景的完整历史，也没有按受众配置的期间白名单。旧 schema 1 快照仍可读取，但没有背景摘要。`created_at` 是快照生成时间，不是资料所属期、正式发布日期或新鲜度证明。成功的官方来源刷新周期会在核心数据核验后发布一次，并在背景四源刷新及核验成功后再次发布；人工入库后需自行重发并刷新展示页面。正式分享前仍需确定内容范围并验收身份与服务权限。

5. 官方 BoC／StatsCan 来源可手动执行 `.venv/bin/python scripts/run_refresh_cycle.py`。它顺序调用安全刷新、核查数据库／manifest／全部原件／记录引用，并在核心四源成功及核验通过后原子发布展示快照，随后刷新背景四源并再次核验，结果写到私有的 `data/run_reports/`。本机 LaunchAgent 已安装，每天系统本地时间 09:00 检查四个核心来源和四个外部背景来源；电脑关闭时不会运行，睡眠期间的日历触发会在唤醒后合并执行。报告类来源仍需各自人工核验；刷新网页不会抓取官网。

6. 私有完整备份已保存于 `~/Library/Application Support/TorontoHousing/backups/`。新建备份可运行 `.venv/bin/python scripts/backup_private.py --output-parent "$HOME/Library/Application Support/TorontoHousing/backups"`，随后用 `.venv/bin/python scripts/check_restore.py --backup-dir "备份目录绝对路径"` 复验；备份包含数据库、原件、manifest、记录和恢复所需代码，不含密码验证器。该路径与项目同机，不能抵御整机或磁盘故障。恢复到新目录后先运行上述校验，再单独设置本机密码。

   每次成功重发展示快照前，当前有效版本会按 SHA-256 保存到私有 `data/display_history/`。可运行 `.venv/bin/python scripts/rollback_display.py --list` 查看旧版哈希和生成时间；确认要回退的完整哈希后，运行 `.venv/bin/python scripts/rollback_display.py --restore 完整64位哈希`。回退只替换展示快照，不倒退数据库；下次成功刷新会再次按当前库重发，故需同时处理导致回退的数据问题。

   定时任务每天 09:00 运行，14:00 再跑一次以补救上午的网络失败（来源未变时不产生新版本）；运行未完全成功时会弹出 macOS 通知。当前数据量可用 `.venv/bin/python scripts/status_summary.py` 生成。定时任务可用 `.venv/bin/python scripts/local_schedule.py --show` 查看定义、`launchctl print gui/$(id -u)/local.toronto-housing.official-refresh` 查看状态；手动补跑用 `.venv/bin/python scripts/run_refresh_cycle.py`，卸载用 `.venv/bin/python scripts/local_schedule.py --uninstall`。任务结果以 `data/run_reports/official-*.json` 为准，`snapshot_published` 为 `true` 才表示本轮发布成功。当前没有失败通知；需定期查看报告。

## 退出、停止与重设管理密码

- 点击相应页面的“退出管理端”或“退出展示端”退出当前会话；服务仍运行。终端 `Ctrl+C` 停止对应服务，管理端和展示端分别停止。
- 会话从登录起一小时有效，在下次交互／脚本执行时检查；不是后台计时器自动清空已经显示的页面。关闭标签也不应代替显式退出。
- 忘记密码或需要轮换时，先停止管理服务；把 `.streamlit/owner_auth.env` 移到仅本人可读的临时备份位置，使原路径空出；重新运行设置脚本，再用启动脚本启动。确认新密码成功后删除旧验证器备份。启动脚本仅在启动时加载验证器，单改文件而不重启不会更新运行中的验证器。
- 当前无账号白名单、多因素认证或失败限速；本地启动脚本强制开启门禁。`HOUSING_REQUIRE_OWNER_AUTH=0` 是隔离测试旁路，不能用于展示或部署启动。两个程序在同一本机账户下运行，不构成独立服务账号的存储隔离。

## 管理端与展示端能力对照

| 功能 | 完整管理端 `app.py` | 只读展示端 `viewer_app.py` |
| --- | --- | --- |
| 导航 | 五页，含数据与记录 | 四个分析主题 |
| 市场分析 | 时间窗口、季节图、HPI 房型及来源等 | 主要价格／成交／供需趋势，窗口较简化 |
| 租赁／地区 | 底图点选、共同期间变化、覆盖和来源表、导出 | 月度／年度及地区趋势、可联动的位置示意点；无来源细目 |
| 经济与供给 | 四主题、建设三面板／房型、页内跳转 | 四主题基本图；就业按量级分两图，建设按当月流量／月末存量分两图，无房型分项 |
| 月供 | 从房价出发的情景（与网页版相同），另有固定条件历史月供 | 从房价出发的情景：月供、压力测试、约需收入、利率敏感度 |
| 记录与数据 | 来源新鲜度、保存记录、完整导出 | 不提供私人记录或完整导出；图表显示数值仍可读取 |

以下详细使用步骤对应完整管理端。展示端对照上表使用，不能把管理端功能或历史验证结论直接套到展示端。

## 看数据与保存观察

顶部导航包含五页，各页的期间选择只作用于相应内容：

| 页面 | 如何使用 | 范围 |
| --- | --- | --- |
| 市场总览 | 选择“观察月份”和“趋势范围”，查看成交、库存、供需比与 HPI；下方“各房型基准价”比较所选月份的四类住宅 | TRREB `All TRREB Areas`；总量卡片为全房型，房型图采用 HPI 自己的分类 |
| 租赁市场 | 在“月度挂牌／年度存量／地区对比”切换视图；年度可比较五类房型，地区通过“编辑地区”和“口径与时间”调整 | 月度沿来源市场定义；年度Toronto CMA或源调查区，2022—2025年；各口径分列 |
| 经济与供给 | 利率与融资、就业、住宅建设、人口四节顺序展示；顶部页内导航可跳转。月度主题各自选择月份与趋势范围，人口单独选择“人口估计年份” | 利率为加拿大背景；就业与人口是 CMA 2021 边界；建设是 CMA 2011 边界 |
| 月供情景 | 输入房价（默认最新 HPI 基准价）、首付比例、摊还年限和年利率；下方历史图用由此得出的贷款额，只替换已接入月份的按揭利率，可下载情景CSV | 金额为加元；历史线不是当年借款人的实际月供 |
| 数据与记录 | 查看来源新鲜度、指标定义、导入结果；保存或下载月度观察 | 本地保存的资料及版本，不自动联网更新 |

### 理解变化与缺失

- 指标名称旁的 **ⓘ** 可悬停查看影响房价的机制，点击可保持展开／收起，键盘可聚焦后按Enter；手机点击。展示页的经济与供给图例、总览的成交／挂牌及库存比图例也保留这些说明。说明支持中英文，是机制解释，不是确定的涨跌预测。
- 数据来源总表将原表抑制值显示为“来源抑制发布”，同时列出应有所属期；“最近所属期”仍是最近有数值的期间。这与尚未更新或零值不同。

- 卡片严格显示所选月份或年份。该期缺值时显示“暂无数据”，不会用较早值顶替；融资页会另行提示最近较早的值及其所属月份。趋势图在缺期处断开，表格与 CSV 保留空白，不填零。
- 趋势图中不同颜色只用于区分指标，不表示预测、数据质量或先后等级；普通指标曲线统一为实线。图例保留指标全名。就业页把不同分母和数值范围的失业率单列，建设页把当月开工／竣工与月末在建存量分列；两组各自共用观察期，但纵轴不能直接比较或相加。
- 按用户最后反馈，单位恢复原有纵轴标题方式；不在每个刻度后追加“人／套”，也不另放到图表标题旁。后续如再调整，先改一张图供用户查看，再决定是否推广。
- 同比对照上年同月或上一年度；缺少该期对照时不计算。利率、失业率及空置率用百分点变化，库存月数用月数变化，其他数量和金额用百分比。变化使用中性颜色，不自动解释为好坏。
- TRREB 总量“较上年同期”由各月原始发布版自算，可能不同于后续修订后的官方同比。MOI、SNLR 是本项目的原始月公式，不等于报告中的 `Trend`。
- “各房型基准价”是标准化住宅的 HPI 基准价，不是平均成交价。展开“房型数值与来源”可看原报告同比、原始分类和页码。该图沿所选观测的 CSV、PDF 来源哈希核对数据，不直接采用后来下载的同月报告；HPI 的 Attached 不替换为成交表的 Semi-Detached。
- 年度存量视图中的租金为 CMHC 调查平均月租金，包含现有租约，不是当下 MLS 挂牌或新租客报价。“均值较上年”可能受样本构成影响，不等于官方同样本租金涨幅。全房型均值直接取原表，不把各房型简单平均。租赁年度选择不受市场总览月份影响；condo 空置率只有总体值，不推算房型空置率。当前租赁页范围为公寓，未混入工作簿中的 Townhouse 独立表。
- 住宅建设另有“按住宅类型比较”，分别查看开工、竣工或在建的四类住宅。若原表分项与总数不一致，页面保留原值并提示，不能把“公寓及其他住宅”解释为 condo 预售或待售库存。人口年度值不插值为月度数，也不与不同边界的建设量计算人均比率。

### 下载与记录

- 市场总览及经济月度节展开“查看与下载本节数据”后，勾选来源表一行左侧的选择框，将观察月份切到该月；本节卡片、趋势、房型／建设详情表及导出按现有月份和窗口重算。再次勾选另一行可切换，直接使用上方月份控件可覆盖该次选择；选择仅限当前节，年度或跨来源数据不隐式跟随。下载与当前趋势范围一致的 CSV。HPI 房型和建设房型的来源详情内也有独立下载，包含来源文件和哈希。
- 租赁页可“下载房型租金对照”，导出所选调查年度的房型、金额、质量标记和来源单元格；“年度变化与调查口径”内还可下载来源质量明细。
- 在“数据与记录”页的“月度观察记录”选择月份，点“保存本地记录”。记录保存在 `data/observations/`，随后可在“打开既有记录”查看数值表、展开完整凭据或“下载这份记录”。每次保存新文件，不覆盖旧记录。记录含输入观测 ID、版本、原文件哈希、资料所属月份与未更新系列，没有复苏评分。选择历史月份只筛选当前已保存的历史资料，不代表还原当时已知的信息。
- “数据与记录”页的“来源覆盖与更新时间”显示最近所属期、状态和历史缺月；“指标定义与原始来源”可打开官方来源，“最近导入运行”显示成功或失败记录。

### 月供情景

“月供情景”按加拿大名义年利率半年复利换算等效月利率，再计算月付本息。房价默认取最新 TRREB HPI 综合基准价，利率默认取最新的新增非受保固定五年及以上平均值，均显示所属月份。贷款额 = 房价 × (1 − 首付比例)。结果包括：每月本息与全期利息；压力测试月供（合同利率 +2 个百分点与 5.25% 取较高者）；大约需要的家庭年收入（压力测试月供不超过收入 39%，未含物业税、取暖和 condo 管理费，实际要求更高）；利率低 1、高 1、高 2 个百分点时的月供。首付低于 20% 时提示需另付按揭保险费（未计入）、房价超过 150 万须至少 20% 首付、30 年摊还仅限首次购房或新房。切换导航后保留输入；清空参数会提示补齐。结果不是银行报价或获批额度。

“数据与记录”页的“数据边界与预测验证状态”说明剩余限制。历史首次发布日期、修订版本的公开时点、季节比较规则与样本外验证尚未齐备，页面不生成复苏标签或预测。

## 月度更新

BoC、StatsCan 与 EIA 的八项已选官方来源可以通过独立入口检查和安全导入，网页浏览本身不会触发下载。入口使用官方URL，下载内容哈希去重；新内容先保存原件、解析，再用SQLite backup API备份数据库后事务入库。网络／解析失败会留下运行记录，不会把缺值填零。一次运行的每个来源分别报告成功、无变化或失败：

需要手动补跑官方检查并更新只读展示快照时，运行 `PYTHONPATH=src .venv/bin/python scripts/run_refresh_cycle.py`。它会加锁、核验恢复所需文件并在 `data/run_reports/` 留私有报告；核心刷新或验证失败时保留上一版展示快照；背景刷新在核心快照发布后运行，背景失败会使周期退出非零，但不撤回已发布的核心快照。相同周期入口也由已安装的本机 LaunchAgent 每日 09:00 调用，不处理报告类来源。

```bash
PYTHONPATH=src .venv/bin/python scripts/refresh_official.py --source all
PYTHONPATH=src .venv/bin/python scripts/refresh_official.py --source boc
```

`all` 包括核心四源（BoC 含新增固定按揭、就业、建设、人口）及背景四源（WTI、BoC 能源／汇率、Toronto 住宅建筑造价）；只运行原四源用 `--source core`，只运行背景四源用 `--source factors`。此刷新入口返回的 `unchanged` 表示响应哈希与已成功导入文件相同；它与下文导入摘要中“同值重复”的计数含义不同，两者均不直接证明官方尚未发布。直接调用本脚本不会自动发布展示快照；应优先使用上面的周期入口。定时任务覆盖该周期的八个已选官方来源，不处理TRREB PDF、Rentals.ca图表或CMHC年度工作簿；这些仍需按下述来源步骤核验。本地电脑关机或长期不登录可能漏检，应查看最近运行报告。

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
- 租赁背景：可用下载脚本 `--include-rental --rental-year YYYY` 保存 CMHC Toronto RMS 工作簿（`YYYY` 换成已发布年份，文件存在时不覆盖）。核对下载后的真实文件名和 URL，再运行 `PYTHONPATH=src .venv/bin/python -m housing.cli cmhc-rental --file 新XLSX路径 --source-url '实际下载 URL'`；无参命令固定读 2025 原件，不用于导入未来新版。导入器从 Toronto CMA 总计行提取两期五类租金、专建出租总体及房型空置率、condo 总体空置率；专建出租租金来自表 1.1.2，condo 两期租金来自表 4.1.3。当前 2023／2025 版已入库、覆盖 2022—2025，不需常规重放。新版本先核对表头、年份、质量／抑制状态，地区年度另走 `cmhc-regions` 入口。
- TRREB：从 [Market Watch 档案](https://trreb.ca/market-data/market-watch/market-watch-archive/) 下载已发布完整月的官方 PDF；下载命令为 `.venv/bin/python scripts/download_trreb.py YYYY-MM YYYY-MM`（依次换成起月、末月）。随后运行 `.venv/bin/python scripts/extract_trreb.py`，核对输出 CSV 的目标月份、PDF 页码和五个数字，再显式执行 `PYTHONPATH=src .venv/bin/python -m housing.cli trreb --file 新CSV路径 --pdf data/raw/trreb --source-url https://trreb.ca/market-data/market-watch/market-watch-archive/`。不要依赖无参入口按文件名排序挑选。提取器目前只扫描 2022–2026 年文件，2027 年以后需先改进年份发现与测试；缺页、表头不符或异常数值时不导入。
- 每次更新运行 `housing.cli status` 并查看“数据与记录”页“最近导入运行”。`inserted` 是新观测，`unchanged` 是同值重复，`revised` 是同一系列同一期间数值改变。一个来源更新成功不代表所有来源已更新。
- 通用导入器在观测写入前检查系列、期间格式、数值范围及同批冲突，异常批次不写观测。部分 CLI 与官方刷新入口会登记解析失败；Rentals 两入口直接调用解析器，早期解析失败可能只有终端报错、没有原件登记或导入记录，此留痕缺口仍待修复。遇到任何失败先保留文件和终端错误，核对实际登记，再另存修正文件重试，不能假设网页日志包含所有失败。

## 备份与恢复

当前没有一键完整备份／恢复工具，也未登记独立设备上的完整备份位置。`data/backups/` 的更新前 SQLite 文件只覆盖数据库；Git 只保护代码和文档，均不能替代原件和观察记录的独立备份。

1. 先停止管理页、展示页和所有导入／刷新进程，保留静止现场；不要一边写库一边直接复制 SQLite 文件。
2. 将整个 `data/` 复制到本人控制的私有备份目录，保留相对路径与权限；包括数据库、原件与 `manifest.csv`、人工提取文件、观察记录、运行报告和展示快照。另保存对应代码提交号、代码副本、`requirements.lock` 与 `.streamlit/config.toml`。验证器单独私密备份或在恢复后重设，不放进可分享的包。
3. 记录备份时间、代码提交、数据库／原件哈希与备份位置。先确认 manifest 与数据库 `raw_files` 一致；当前刷新脚本不会重新导出 manifest，见下文已知缺口。备份与原件同盘不能覆盖设备丢失场景。
4. 恢复时先把故障现场另存，再把备份恢复到新目录验证；不要直接覆盖唯一现场或唯一备份。恢复对应代码与依赖，重新设置目录权限（`chmod -R go-rwx data`），配置管理密码。
5. 以只读方式检查 `PRAGMA integrity_check` 和 `PRAGMA foreign_key_check`，核对 manifest 哈希、版本引用及记录。记录应与其引用的观测版本对照，不能强求等于之后修订的最新值。再启动管理页核对已知期间，重新发布快照并检查展示页。

`.venv/bin/python scripts/check_restore.py` 只是把**当前现场**复制到临时目录演练，结束后删除；它不创建持久备份、不读取指定备份，也不执行真实恢复。脚本检查原件哈希和观测引用，但只深入核对最后一份观察记录，且其中成交值与当前最新版本比较。其通过不能证明任意旧记录、独立备份或未来所有更新批次均可恢复；脚本也未运行外键检查。

已知更新缺口：`refresh_official.py`／`run_refresh_cycle.py` 新原件入库后不更新 `data/raw/manifest.csv`，恢复检查可能因此失败。补齐 manifest 发布和恢复验收前，不把周期成功当成完整备份链通过。失败时保留文件及错误，核对库与 manifest，勿靠重导旧文件“修复”。另单次周期失败不会回滚已成功来源的数据库写入，但保留旧展示快照；中断、锁冲突或部分异常也可能没有周期 JSON 报告。

如果出现报错，记录命令、发生时间、退出码和对应“最近导入运行”行；周期任务另查 `data/run_reports/`。若没有报告，保留终端错误。向他人提供错误摘要前去掉本机私人路径或凭据。

## Rentals.ca 月度挂牌租金

租赁市场默认显示月度挂牌租金；“租金数据口径”可切换到 CMHC 年度存量租金。
截至 2026-10-08，月度总体序列为 2022-07—2026-09；一卧、两卧自 2024-01、三卧自 2024-03 起（2025-11 以前由报告图片转录，缺 2024-02 与 2025-01，审计表见 `docs/RENTAL_BEDROOM_ARCHIVE.csv`）。Rentals.ca 多伦多月度数据没有开间。选择更早月份时不以最新房型报价补缺。

来源为 Rentals.ca / Urbanation 各期公开 Datawrapper 图表，当前最新导入为 2026 年 9 月报告中的 8 月观测；该次报告月份与资料月份相差一个月，每期仍需核对元数据。图表 ID／版本与来源冲突说明见[来源覆盖](SOURCE_COVERAGE.md)。当前不是自动联网刷新，后续报告入口内容变化不改写已保存原件。

更新步骤：从新一期 Rentals.ca 报告找到同口径图表，保存公开 HTML 与 `dataset.csv` 为新文件，不覆盖旧版本；逐项核对市场范围、资料期和数值。以下是已入库原件的命令格式示例，常规启动无需再次执行；新一期必须改为新原件及相应报告 URL：

```bash
PYTHONPATH=src .venv/bin/python -m housing.cli rentals \
  --file data/raw/rentals/2026-09-report-bedrooms.csv \
  --chart data/raw/rentals/2026-09-report-bedrooms.html \
  --source-url https://rentals.ca/national-rent-report
```

解析器按支持的图表格式检查标题、发布者、公寓／condo 范围、日期、房型列和数值；历史序列另查连续月份，未知格式拒绝导入。HTML 和 CSV 的哈希均登记到 manifest，观测链接到 CSV。与当前最新值相同才不新增版本，旧文件不可任意重放；数值修订保留版本。不将图表修改时间冒充正式发布日期。每月 15 日为本地新鲜度检查日，不是来源发布承诺。


### 分房型来源注意事项

- 房型历史截至本次核对各 10 个月，管理页菜单也可同时比较一至三卧。同比缺上年观测时不计算。
- 2026-04三卧采用图表dvDEZ第2版CSV的3,567；报告正文为3,558，存在来源内部差异，采用已存档图表版本，未以正文覆盖。
- 原始HTML、CSV和版本来源保存在`data/raw/rentals/`。不得混用全部物业与公寓／condo范围。

## 地区租金对比（2026-09-24 核对）

入口：租赁市场 → 地区对比。网页版：已选地区显示为带颜色的标签，点 × 移除，用“添加地区”下拉加入，最多三个；某地区缺所选房型时显示提示，不用总体代替。管理端：点击“编辑地区”或地图位置点选择最多三个地区；已选的对比地区可再点一次移除，主要地区从“编辑地区”更换。“口径与时间”内选择月度挂牌或年度CMHC及期间，年度另可选择平均租金／空置率。外部房型菜单选择同一房型。地图点只帮助选区，不代表统计边界；地区控件仅作用本视图。

- 月度保持专建出租公寓＋condo同口径：North York、Scarborough、Markham、Vaughan、Mississauga、Oakville 总体已核验 2024-01—2026-08，其中五地区各 31 个观测、Markham 30 个；2024-09 和 Markham 2024-07 留缺口；除 Markham 外一／两卧各覆盖 2026-04—08（5 个月）。Markham 月度分房型未接入。Toronto 总体 50 个月、房型 10 个月。明细见[地区覆盖审计](RENTAL_COVERAGE_AUDIT.csv)。
- CMHC 专建出租公寓：2022—2025，五类房型租金及空置率。North York、Scarborough、Mississauga、Oakville、Markham；另有 Richmond Hill/Vaughan/King 和 Aurora/Newmarket/Whitchurch-Stouffville 组合调查区。组合值不能拆给某个城市，部分数据抑制。
- Downtown 无已核定边界和对应数据；Richmond Hill/Aurora 无独立月度数据。选择不可用组合会明确提示，不能借用 Toronto。Oakview 暂按 Oakville 理解。
- 地区定义沿用来源名称；不能把相邻/包含地区相加。挂牌均值也不能把各地区简单平均生成 GTA 均值。

地区月度原件使用以下命令；后续月份保存新文件名并换成相应报告 URL：

```bash
PYTHONPATH=src .venv/bin/python -m housing.cli rentals-regions \
  --file data/raw/rentals/2026-09-report-regions-cities.csv \
  --chart data/raw/rentals/2026-09-report-regions-cities.html \
  --source-url https://rentals.ca/national-rent-report

PYTHONPATH=src .venv/bin/python -m housing.cli rentals-regions \
  --file data/raw/rentals/2026-09-report-top25.csv \
  --chart data/raw/rentals/2026-09-report-top25.html \
  --source-url https://rentals.ca/national-rent-report
```

城市图导入 Toronto 总体和可用地区卧室分项；六地区总体采用 Top25 公寓／condo 排名图，不能把城市表总体覆盖到地区主系列。季度 MLS 实际成交租金尚未接入；此前页面检查曾返回 403，本次文档复核未重试，不能据此断言当前不可访问。
年度地区复用已存档 CMHC XLSX，用 `cmhc-regions --file ... --source-url ...` 导入；URL 从 manifest 对应原件记录读取。原始质量等级、抑制状态、表名与单元格保留在地区导出中。

### 租金历史长度与来源差异

在“地区覆盖与边界说明”查看自动生成的月度地区／房型覆盖表；无观测组合不以总体替代，年度 CMHC 还需区分来源抑制。当前历史长度见上表和审计 CSV，短于一年不能判断全年季节性。地区总体统一使用 Top25 公寓／condo 图；2026-04 城市表与排名图存在未解释差异，来源选择调整已保留版本和说明。

## 地区转售与新增背景（2026-09-26）

“市场总览”底部打开“地区转售明细”，选择房型、TRREB 地区、指标（含成交价／挂牌价比、挂牌天数）及观察月。网页版明细表点击月份会更新曲线截止期；曲线支持键盘左右键逐月查看。这里是实际转售统计，不能与挂牌租金系列合并，父子统计地区不可相加。

“经济与供给”底部现有九项外部背景摘要，名称旁 ⓘ 提供说明。更新状态按各自发布节奏判断，待发布不等于零；传统五年按揭公布利率不是实际新增贷款加权利率。网页版背景指标按“新房与建设、房价（其他来源）、利率与通胀、人口流动、外部因素”分组收起，更新状态只在需要核查时标出；签约租金不在此重复。

本机每日 09:00／14:00 更新，09:20／14:20 由 Claude 定时任务按需重新发布网页版；电脑或 Claude 应用未运行时无法保证准点，网页仍显示最近一次成功发布的数据时间。

## 市场温度

“市场总览”首屏的温度刻度卡与下方“市场温度走势”：近三个月成交／新挂牌比与过去各年同月平均的差，高于 10 个百分点为偏热、低于 10 个百分点为偏冷。表格列出 2012 年以来各温度之后 12 个月 HPI 的平均变化与上涨比例。依据见 [研究 v4](LEADING_STUDY_V4.md)；只描述供需，不是预测。计算需要本机研究存档 `data/research/trreb-history.csv`（由 `scripts/build_trreb_history.py` 从 `data/raw/trreb_history/` 生成）。

## 每月人工步骤

- **Rentals.ca 月报**（约每月中旬）：网站拦截自动下载，按“导入”一节处理。
- **Teranet 指数**（约每月下旬）：在 housepriceindex.ca 填表下载 `House_Price_Index.csv`，运行 `.venv/bin/python scripts/import_teranet.py ~/Downloads/House_Price_Index.csv`，然后请 Claude 重新发布网页版（Teranet 不在自动周期内）。

## 备份

更新时只在有新数据写入前备份数据库到 `data/backups/`（未变化不备份）。旧备份可只保留每类最新一份。完整私有备份：`.venv/bin/python scripts/backup_private.py --output-parent ~/Library/Application\ Support/TorontoHousing/backups`；同机备份不能防硬盘损坏，请另存外部硬盘或云盘，并包括 `data/raw/trreb_history/`、`data/research/` 与 `data/raw/teranet/`。
