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

The dashboard is intended for display, with full data and administration restricted to the owner. `viewer_app.py` reads a path-free numerical snapshot of the latest version for every stored period; the current series allowlist covers the entire registered catalog, pending audience-specific review. The full `app.py` defaults to an owner password gate and the local launcher binds it to loopback. The processes still share the local account; storage access is not isolated by service identity. The audience, export policy, identity provider and host remain undecided. Earlier QA counts describe historical rounds only; the later 62-test evidence and its limits are in `docs/PROJECT_ACCEPTANCE.md`.

## Remaining design coverage

Future implementation should extend this same file for missing approved display flows: filter summary/reset, table-row selection and clearing, loading/error/stale-data states, source/quality disclosure, and responsive economy/mortgage views. Specify selected, focus, empty, unavailable and keyboard-equivalent states before changing those interactions. Keep private record and administration actions outside display compositions. Record the frame IDs, screenshots, source-data date and which live route was compared; a Figma render alone does not verify the Streamlit interaction.
