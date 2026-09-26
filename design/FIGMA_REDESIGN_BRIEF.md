# Toronto Housing Monitor — Figma redesign brief

Status: the approved visual direction was applied to the five-page management dashboard on 2026-09-23; the Figma file itself contains overview/regional desktop and mobile compositions plus an unavailable state, not complete designs for every page. Team: yashirq's team. The 2026-09-24 separator refinement and local viewer are described below. Full interaction, keyboard and display/management parity acceptance remains open.

## Reference

BOP-RMS `docs/spec/design/bop-rms-figma-make-brief.md` lines 114 onward: strict SSENSE grid, Apple hierarchy/spacing, white #FFFFFF, ink #171717, secondary #666666, divider #E5E5E5. Its Make file is a reference only; do not modify it. Source app uses system UI / Helvetica / PingFang; confirm available Figma fonts before creating text. No Code Connect files found in this project.

## Deliverables

Two editable desktop screens, plus matching mobile compositions and explicit empty-state treatment:

1. Market overview: concise masthead/navigation, large price figure and period, dominant HPI chart, compact supporting sales/inventory metrics, secondary supply-demand section, unobtrusive source disclosure.
2. Regional rental comparison: same shell, compact geographic selection, inline bedroom/frequency controls, dominant rent chart and direct series labels, coverage/source disclosure. The original design snapshot had nine Markham monthly total points; current coverage belongs to the source-coverage document. Monthly bedrooms remain unavailable. Annual alternatives clearly distinguish occupied-stock rents from asking rents.

## Art direction

Recompose the page rather than translate the existing form grid. Fewer simultaneous controls, deliberate type hierarchy, consistent baseline/alignment, white canvas, no large rounded cards, no decorative coloured borders. Use blue/teal/orange/purple meaningfully for data series and active state. Preserve visible keyboard focus, readable labels, and touch targets. Chinese default with English counterpart planned; source geography/period definitions remain explicit.

## Evidence

`figma-data-snapshot.json` retains the original design-time values: price coverage ends August 2026 and regional rents end July 2026. The running data was later extended; this file is historical design evidence, not the current database or a live Figma integration. Never fabricate monthly bedroom values, missing months, or real-time/leading-prediction claims.

## Review gate

Inspect complete frame screenshots, confirm chart prominence, sensible whitespace, readable Chinese type, no clipped control labels, and clear unsupported data states before presenting the design for review. The running dashboard is not replaced by this design step.


## Created Figma draft

File: https://www.figma.com/design/xKNAErf19Uep7K3z5Lqvco

- 01 Market overview desktop: 3:156 (1440px)
- 02 Regional rental desktop: 3:234 (1440px)
- 03 Market overview mobile: 3:320 (390px)
- 04 Regional rental mobile: 3:385 (390px)
- 05 Markham one-bedroom unavailable state: 6:29 (390px)

Design-system discovery: no Code Connect or existing screens in the new file; no subscribed team library. Simple Design System button components and border variable were imported. Select search failed; compact source/room controls are represented with imported button instances in this visual draft. Custom charts are editable vectors built from the saved real observations, not screenshots. Verified rendered fonts: Inter and Noto Sans SC (fallback for unavailable local system UI fonts). Frames use auto layout; charts use plot coordinates.

Historical draft QA: desktop screenshots inspected after correcting horizontal auto-layout cross-axis sizing. Both mobile frames inspected; no text overflow found in the checked text bounds. Mobile rental selectors were compacted and recaptured. Unavailable state separately inspected. UI labels/actions are design representations, not a fully wired interactive prototype. Dedicated English Figma variants were not created; the subsequent local implementation has bilingual controls. No publishing or sharing-setting changes.

The JS files retain construction evidence; they contain node references from this creation session and should not be rerun blindly in the existing file.

## Historical implementation checks (2026-09-23)

- Shared CSS and native Streamlit controls implement the editorial shell, colour system, context rails, dominant plots and lightweight source disclosures.
- Overview, monthly/annual/regional rentals, economy/supply, mortgage and records all retain their existing data scope and exports.
- Regional edit popover, bilingual labels and narrow-screen stacking were visually checked.
- Mortgage chart uses computed payments; blank inputs prompt for completion, while zero principal remains a valid zero-payment scenario.
- 44 regression tests passed; desktop 1440px and mobile 390px browser review completed. No new source data or externally published deployment.


## Page-style simplification and private backend work (2026-09-24)

The user clarified that the distracting lines are the dashboard's own separators, borders and control underlines, not primarily the data curves. Remove or soften redundant decoration where helpful; use whitespace, alignment and heading hierarchy within the approved white design direction. Preserve selected states, keyboard focus, control affordances, warning signals and table readability. Do not reduce data series or remove charts by default in response to this request.

The existing Figma file was edited first: six redundant `Divider` rectangles (`3:224`, `3:264`, `3:309`, `3:375`, `3:455`, `6:52`) were hidden. Desktop overview/rental and mobile overview/rental screenshots were inspected after the change. These separators repeated nearby headings or metric grouping; selected navigation indicators and chart marks/gridlines remain. The matching CSS removes metric top/bottom lines, metric top lines, expander top lines, jump-nav bottom line and economic topic bottom lines. Input underlines and table rows remain for affordance/readability. The BOP-RMS reference and Figma sharing/publishing were unchanged. Full live browser/keyboard acceptance is still open.

The dashboard is intended for display, with full data and administration restricted to the owner. `viewer_app.py` reads a path-free numerical snapshot of the latest version for every stored period; the current series allowlist covers the entire registered catalog. The user has since selected owner-only local demonstration for both entries, which now have local password gates and loopback launchers. The processes still share the local account; storage access is not isolated by service identity. Remote sharing, export policy, identity provider and a long-running host would require separate decisions if remote use is pursued. Earlier QA counts describe historical rounds only; subsequent implementation evidence and its limits are in `docs/PROJECT_ACCEPTANCE.md`.

## Masthead and economy-chart refinement (2026-09-24)

The five existing artboards now use the live `GTA HOUSING MONITOR` product name. The name stays in English in both language modes; content labels translate. User review rejected the added grey track: the language control is again two 44×44 choices with a 4px gap and no outer fill. The selected choice retains a light-blue fill and the radio implementation retains keyboard focus. The live Streamlit label's default 8px inner left padding is explicitly removed so each text label is centered. The mobile masthead render was inspected after editing. The former Figma wordmark differed from the live page; this change brings the reference into alignment without publishing the file or changing its sharing settings.

The economy page has no existing Figma artboard. Its chart repair changes data presentation rather than the masthead visual system: unemployment is separated from employment/participation rates; monthly starts/completions are separated from month-end construction stock. The paired charts share each section's selected period and use independent vertical scales. The existing file still needs an economy artboard if that full page is redesigned visually.

The subsequent line-chart legend correction is made in the data-driven Altair chart rather than Figma. User review exposed that the earlier solid/dashed/dotted assignment was positional, not a meaningful data distinction, and could imply forecast or different evidence status. Standard indicator comparisons now use solid lines with stable series colours and a longer colour-key sample. The raw SNLR and three-month rolling mean also use solid lines with separate names and colours. Missing observations still interrupt the plotted line. The two economy chart splits remain purposeful: unemployment has a different denominator and much smaller percentage range than employment/participation; monthly construction flows cannot share a meaningful raw-value scale with month-end stock. Rates stay together because all three are comparable percentages. A Figma economy artboard would be useful for a broader page-layout redesign, but it would not control the live Altair legend.

## Later user feedback retained for future changes (2026-09-24)

The user rejected the axis-unit experiments and requested the original presentation again. Keep units in the original y-axis title; do not append Chinese unit words to every tick or move them beside the chart heading. If another approach is proposed, change one example for review before applying it broadly. Existing employment and construction splits are implementation choices with the reasons above, not blanket user approval to split other charts.

Metric explanations must remain available when charts replace cards or use an external legend. The display page currently uses the shared bilingual disclosure for its economy/supply charts and market sales/listings and inventory-ratio charts. Preserve meaningful series names, colours and help access during future visual changes. This documentation follow-up did not edit Figma or rerun browser/accessibility acceptance.

## Remaining design coverage

Future implementation should extend this same file for missing approved display flows: filter summary/reset, table-row selection and clearing, loading/error/stale-data states, source/quality disclosure, and responsive economy/mortgage views. Specify selected, focus, empty, unavailable and keyboard-equivalent states before changing those interactions. Keep private record and administration actions outside display compositions. Record the frame IDs, screenshots, source-data date and which live route was compared; a Figma render alone does not verify the Streamlit interaction.

## 2026-09-26 单页评审稿（尚未实施）

按用户同意的先做单页方案，在原文件新增市场总览桌面画板 `26:35` 与手机画板 `26:160`，保留旧画板和线上版本。主图突出 HPI，成交与供需作为次级图；保持白底无图框、同色实线图例、原纵轴单位和帮助入口。地区转售入口默认收起是本次提案，尚未视为用户接受。详细链接、截图、快照时间和实施边界见 [评审说明](review-2026-09-26/README.md)。本次没有修改代码或发布网站，也未验证提案交互。

2026-09-26 后续：用户已同意上述单页稿，已实现到 `site/dist/` 的市场总览并完成中英文响应式及交互检查。Streamlit 和其余业务页未套用该单页布局；Sites 发布记录以当前部署状态为准。
