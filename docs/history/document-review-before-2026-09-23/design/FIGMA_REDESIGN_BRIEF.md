# Toronto Housing Monitor — Figma redesign brief

Status: approved Figma direction implemented in the live Streamlit dashboard across all five pages on 2026-09-23. Team: yashirq's team. Figma frames remain the reference specification; live controls and charts are data driven.

## Reference

BOP-RMS `docs/spec/design/bop-rms-figma-make-brief.md` lines 114 onward: strict SSENSE grid, Apple hierarchy/spacing, white #FFFFFF, ink #171717, secondary #666666, divider #E5E5E5. Its Make file is a reference only; do not modify it. Source app uses system UI / Helvetica / PingFang; confirm available Figma fonts before creating text. No Code Connect files found in this project.

## Deliverables

Two editable desktop screens, plus matching mobile compositions and explicit empty-state treatment:

1. Market overview: concise masthead/navigation, large price figure and period, dominant HPI chart, compact supporting sales/inventory metrics, secondary supply-demand section, unobtrusive source disclosure.
2. Regional rental comparison: same shell, compact geographic selection, inline bedroom/frequency controls, dominant rent chart and direct series labels, coverage/source disclosure. Markham monthly total has nine actual points; monthly bedrooms unavailable. Annual alternatives clearly distinguish occupied-stock rents from asking rents.

## Art direction

Recompose the page rather than translate the existing form grid. Fewer simultaneous controls, deliberate type hierarchy, consistent baseline/alignment, white canvas, no large rounded cards, no decorative coloured borders. Use blue/teal/orange/purple meaningfully for data series and active state. Preserve visible keyboard focus, readable labels, and touch targets. Chinese default with English counterpart planned; source geography/period definitions remain explicit.

## Evidence

`figma-data-snapshot.json` contains currently stored real values and periods for the design charts. Price coverage ends August 2026; regional rent coverage ends July 2026. These are design-time snapshots, not a live Figma integration. Never fabricate monthly bedroom values, missing months, or real-time/leading-prediction claims.

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

QA: desktop screenshots inspected after correcting horizontal auto-layout cross-axis sizing. Both mobile frames inspected; no text overflow found in the checked text bounds. Mobile rental selectors were compacted and recaptured. Unavailable state separately inspected. UI labels/actions are design representations, not a fully wired interactive prototype. English screen variants and production implementation remain future work. No publishing or sharing-setting changes.

The JS files retain construction evidence; they contain node references from this creation session and should not be rerun blindly in the existing file.

## Implementation acceptance

- Shared CSS and native Streamlit controls implement the editorial shell, colour system, context rails, dominant plots and lightweight source disclosures.
- Overview, monthly/annual/regional rentals, economy/supply, mortgage and records all retain their existing data scope and exports.
- Regional edit popover, bilingual labels and narrow-screen stacking were visually checked.
- Mortgage chart uses computed payments; blank inputs prompt for completion, while zero principal remains a valid zero-payment scenario.
- 44 regression tests passed; desktop 1440px and mobile 390px browser review completed. No new source data or externally published deployment.
