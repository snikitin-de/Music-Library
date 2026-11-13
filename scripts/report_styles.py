"""One embedded stylesheet for the standalone music library report."""

import base64
from pathlib import Path

_FONT_DATA = base64.b64encode((Path(__file__).parent / "assets" / "NunitoVariable.woff2").read_bytes()).decode("ascii")
_FONT_FACE = '@font-face{font-family:"Library Nunito";font-style:normal;font-weight:200 1000;font-display:swap;src:url(data:font/woff2;base64,' + _FONT_DATA + ') format("woff2");}\n'

REPORT_CSS = _FONT_FACE + r"""
:root {
  color-scheme: dark;
  --bg: #000; --panel: #181818; --panel-solid: #121212; --soft: #242424;
  --text: #f5f5f5; --muted: #a7a7a7; --line: #303030;
  --good: #2bcf70; --bad: #ff9caa; --accent: #2bcf70;
  --accent-strong: #4cdd8c; --warning: #f0c674;
  --radius: 16px; --radius-tile: 12px; --radius-small: 8px;
  --scroll-thumb: #ffffff30; --scroll-thumb-hover: #ffffff70;
}
* { box-sizing: border-box; }
/* A transparent track and a four-pixel visible thumb, without native arrows. */
::-webkit-scrollbar { width: 6px; height: 6px; background: transparent; }
::-webkit-scrollbar-track, ::-webkit-scrollbar-corner { background: transparent; }
::-webkit-scrollbar-thumb { min-height: 24px; border: 1px solid transparent; border-radius: 999px; background: var(--scroll-thumb); background-clip: padding-box; }
::-webkit-scrollbar-thumb:hover { background-color: var(--scroll-thumb-hover); }
:where(.app-sidebar, .chart-legend, .web-select-options, .lyrics-text, .heatmap-scroll, .source-folders):hover::-webkit-scrollbar-thumb { background-color: var(--scroll-thumb-hover); }
::-webkit-scrollbar-thumb:active { background-color: #ffffff99; }
::-webkit-scrollbar-button { display: none; width: 0; height: 0; }
/* Firefox uses the standard colours; Chromium keeps the arrow-free custom bar. */
@supports not selector(::-webkit-scrollbar) {
  * { scrollbar-width: thin; scrollbar-color: var(--scroll-thumb) transparent; }
  *:hover { scrollbar-color: var(--scroll-thumb-hover) transparent; }
}
html { scroll-behavior: auto; scroll-padding-top: 24px; }
body { margin: 0; min-width: 0; color: var(--text); background: var(--bg); font: 14px/1.55 "Library Nunito", "Segoe UI", Arial, sans-serif; text-rendering: optimizeLegibility; font-kerning: normal; font-synthesis: none; }
::selection { color: #000; background: var(--accent); }
button, input, select { font: inherit; text-rendering: inherit; background-clip: padding-box; }
/* A neutral standard filter paints text with grayscale coverage on Windows too.
   Keep it on controls and text, never on layout ancestors: filters establish a
   containing block for fixed descendants (dropdowns, sidebar and dialogs). */
button, input, select, label, h1, h2, h3, p, pre,
.app-brand strong, .nav-caption, .side-nav a, .sidebar-source>span, .sidebar-note,
.hero-kicker, .metric, .section-heading>span, .note, .summary-subtitle,
.format-row, .artist-row, .chart-legend, .donut-hole, .year-chart, .heatmap-grid, .heatmap-scale,
.operation-status, .search-placeholder, .web-select-option,
.music-title, .music-path, .track-title, .track-path, .music-pill, .audio-time,
.identity-warning, .music-card-status, .duplicate-card-status, .copy-status,
.group-title, .group-subtitle, .badges, .track-label, .quality-grid, .divider,
.lyrics-dialog-path, .lyrics-source, .lyrics-artist, .lyrics-line, .lyrics-section,
.lyrics-text.is-raw, .lyrics-text.loading, .lyrics-text.error { filter: opacity(1); }
button { cursor: pointer; }
button:disabled { cursor: not-allowed; opacity: .4; }
a { color: inherit; }
:focus-visible { outline: 2px solid #fff; outline-offset: 4px; }
[hidden] { display: none !important; }
svg { width: 20px; height: 20px; flex-shrink: 0; vertical-align: middle; shape-rendering: geometricPrecision; }
.app-shell { display: grid; grid-template-columns: 248px minmax(0, 1fr); gap: 8px; padding: 8px; align-items: start; }
.app-sidebar { position: fixed; top: 8px; left: 8px; bottom: 8px; z-index: 10; display: flex; flex-direction: column; width: 248px; padding: 24px 12px 16px; overflow-y: auto; overscroll-behavior: contain; contain: layout paint; border-radius: var(--radius); background: var(--panel-solid); }
.app-brand { display: flex; align-items: center; gap: 12px; padding: 0 12px 28px; text-decoration: none; }
.brand-mark { display: grid; place-items: center; width: 36px; height: 36px; flex-shrink: 0; border-radius: 50%; color: #000; background: var(--accent); }
.brand-icon { width: 23px; height: 23px; }
.app-brand>span:last-child { display: grid; gap: 1px; }
.app-brand strong { font-size: 16px; letter-spacing: -.4px; }
.app-brand small { color: var(--muted); font-size: 12px; }
.nav-caption { margin: 14px 12px 8px; color: var(--muted); font-size: 12px; font-weight: 600; letter-spacing: .6px; text-transform: uppercase; }
.side-nav { display: grid; gap: 4px; }
.side-nav a { display: flex; align-items: center; gap: 14px; min-height: 46px; padding: 10px 14px; border-radius: var(--radius-small); color: var(--muted); font-weight: 600; text-decoration: none; transition: color .15s, background .15s; }
.side-nav a:hover { color: #fff; background: #1c1c1c; }
.side-nav a.active { color: #fff; background: #282828; }
.side-nav a.active .nav-icon { color: var(--accent); }
.sidebar-footer { display: grid; gap: 16px; margin: auto 8px 0; padding-top: 14px; border-top: 1px solid var(--line); }
.sidebar-source { display: block; width: 100%; min-width: 0; margin: 0; padding: 0; border: 0; color: inherit; background: transparent; font: inherit; text-align: left; }
.sidebar-source, .sidebar-source * { cursor: pointer; user-select: none; -webkit-user-select: none; }
.sidebar-source-label { display: block; color: var(--text); font-size: 12px; font-weight: 600; }
.sidebar-source-path { display: block; margin-top: 6px; overflow: hidden; color: #c5c5c5; font-size: 12px; line-height: 1.6; text-overflow: ellipsis; white-space: nowrap; }
.sidebar-source:hover .sidebar-source-path { color: var(--text); }
.sidebar-note { display: grid; gap: 3px; width: 100%; margin: 0; padding: 0; border: 0; color: var(--text); background: transparent; font: inherit; text-align: left; }
.sidebar-note, .sidebar-note * { cursor: pointer; user-select: none; -webkit-user-select: none; }
.sidebar-note:hover strong { text-decoration: underline; text-underline-offset: 3px; }
.sidebar-note strong { font-size: 12px; font-weight: 600; }
.sidebar-note small { color: var(--muted); font-size: 12px; }
.sidebar-note.mode-real strong { color: var(--warning); }
.app-workspace { grid-column: 2; min-width: 0; min-height: calc(100vh - 16px); border-radius: var(--radius); background: var(--panel-solid); }
.app-workspace:has(#musicSection:not([hidden])) {
  background: linear-gradient(#513a9f, #2a1e51 24%, #21183f 48%, #181622 75%, var(--panel-solid))
    top / 100% 610px no-repeat var(--panel-solid);
}
.page { width: 100%; max-width: 1800px; margin: 0 auto; padding: 0 32px 56px; }
.header { margin: 0 -32px; padding: 32px 32px 24px; border-radius: var(--radius) var(--radius) 0 0; background: linear-gradient(180deg, #27382e 0, #1d2922 48%, #121212 100%); }
.hero-layout { display: flex; align-items: center; gap: 24px; min-width: 0; }
.collection-art { display: grid; place-items: center; flex: 0 0 140px; height: 140px; border-radius: var(--radius-tile); background: var(--accent); color: #0b301c; box-shadow: 0 8px 24px #0004; }
.collection-art svg { width: 72px; height: 72px; stroke-width: 1.6; }
.hero-copy { min-width: 0; }
.hero-kicker { margin-bottom: 4px; font-size: 12px; font-weight: 600; }
h1 { margin: 0; font-size: clamp(32px, 4.5vw, 64px); font-weight: 750; letter-spacing: -.8px; line-height: 1.15; }
.hero-lead { margin: 10px 0 0; color: #c7ceca; font-size: 13px; }
.summary { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 8px; margin-top: 28px; }
.summary.duplicate-summary { grid-template-columns: repeat(3, minmax(0, 1fr)); margin: 0 0 16px; }
.duplicate-summary .metric { display: flex; flex-direction: column; }
.duplicate-summary .metric strong { margin-top: auto; padding-top: 8px; }
.metric { position: relative; min-width: 0; padding: 14px 12px; border-radius: var(--radius-tile); background: #ffffff0a; }
.metric strong { display: block; margin-top: 8px; font-size: 26px; font-weight: 700; letter-spacing: -.6px; line-height: 1; font-variant-numeric: tabular-nums; }
.metric-label { display: block; color: #b3b3b3; font-size: 12px; }
.metric-icon { display: none; }
.metric-primary strong { color: var(--accent); }
.section-heading { display: flex; justify-content: space-between; align-items: end; gap: 16px; margin-top: 22px; }
.section-heading span { color: var(--muted); font-size: 12px; }
.section-heading h2, .section-title { margin: 0; font-size: 24px; font-weight: 750; letter-spacing: -.3px; line-height: 1.3; }
.section-heading p { margin: 0; color: var(--muted); font-size: 12px; }
.analysis-grid { display: grid; grid-template-columns: 1.1fr 1fr 1fr 1fr; gap: 12px; margin-top: 16px; align-items: stretch; }
.panel { min-width: 0; padding: 20px; border-radius: var(--radius); background: var(--panel); container-type: inline-size; }
.panel h2 { margin: 0; font-size: 16px; font-weight: 700; letter-spacing: 0; }
.panel-body { margin-top: 18px; }
.note, .chart-note, .format-empty { color: var(--muted); font-size: 12px; line-height: 1.8; }
.note strong, .chart-note strong { color: var(--text); font-weight: 500; }
.summary-main { padding-bottom: 16px; border-bottom: 1px solid var(--line); }
.summary-subtitle { margin: 0 0 12px; font-size: 12px; font-weight: 600; }
.format-row, .artist-row, .genre-row, .year-row { display: grid; align-items: center; gap: 8px; margin-top: 10px; font-size: 12px; }
.format-row { grid-template-columns: 45px minmax(0, 1fr) 44px; }
.artist-row { grid-template-columns: minmax(0, 1fr) minmax(30px, .6fr) 30px; }
.genre-row { grid-template-columns: minmax(0, 1fr) 1fr 34px; }
.year-row { grid-template-columns: 42px minmax(0, 1fr) 34px; }
.artist-name, .genre-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.format-count { color: var(--muted); text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
.format-bar { height: 4px; overflow: hidden; border-radius: 0; background: #343434; }
.format-bar span { display: block; height: 100%; border-radius: inherit; background: var(--accent); }
.donut-layout { display: grid; justify-items: center; gap: 18px; }
.library-chart { position: relative; min-width: 0; width: 100%; }
.plotly-host { position: absolute; inset: 0; }
.plotly-host svg.main-svg { width: 100%; height: 100%; }
.plotly-fallback { height: 100%; }
.plotly-ready>.plotly-fallback { display: none; }
.donut-chart-wrap { position: relative; width: 160px; height: 160px; }
.donut-chart { width: 160px; aspect-ratio: 1; }
.donut-svg { position: absolute; inset: 0; width: 100%; height: 100%; overflow: visible; shape-rendering: geometricPrecision; }
.donut-segment { stroke-linecap: butt; }
.donut-hole { position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%); display: grid; place-items: center; align-content: center; width: 80px; aspect-ratio: 1; text-align: center; pointer-events: none; }
.donut-hole strong { font-size: 22px; line-height: 1; }
.donut-hole span { max-width: 68px; margin-top: 4px; overflow: hidden; color: var(--muted); font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }
.chart-legend { display: grid; grid-auto-rows: 19px; gap: 7px; width: 100%; min-width: 0; max-height: 175px; padding-right: 12px; overflow-y: auto; scrollbar-gutter: stable; }
.chart-legend-row { display: grid; grid-template-columns: 7px minmax(0, 1fr) 32px 38px; gap: 6px; align-items: center; font-size: 12px; line-height: 19px; font-variant-numeric: tabular-nums; }
.chart-dot { width: 7px; height: 7px; border-radius: 50%; }
.chart-label { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.chart-legend-row strong, .chart-legend-row span:last-child { text-align: right; font-weight: 400; }
.chart-legend-row span:last-child { color: var(--muted); }
.chart-note { margin: 0 0 14px; }
.year-chart { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 8px; height: 180px; margin-top: 18px; }
.year-chart-item { display: grid; grid-template-rows: minmax(0, 1fr) 28px; min-width: 0; }
.year-chart-column { display: flex; flex-direction: column; align-items: center; justify-content: flex-end; border-bottom: 1px solid var(--line); }
.year-chart-bar { width: min(28px, 68%); height: max(6px, var(--bar-height)); border-radius: 0; background: var(--accent); }
.year-chart-item:hover .year-chart-bar { background: var(--accent-strong); }
.year-chart-label { padding-top: 8px; color: var(--muted); font-size: 12px; text-align: center; white-space: nowrap; }
.year-chart-value { margin-bottom: 6px; font-size: 12px; font-variant-numeric: tabular-nums; }
.heatmap-panel { margin-top: 12px; }
.heatmap-heading { margin-bottom: 16px; }
.heatmap-heading p { margin: 4px 0 0; color: var(--muted); font-size: 12px; }
.heatmap-scroll { max-width: 100%; overflow-x: auto; }
.heatmap-grid { display: grid; grid-template-columns: minmax(110px, .88fr) repeat(var(--heatmap-columns), minmax(80px, 1fr)); min-width: 640px; gap: 3px; }
.heatmap-row { display: contents; }
.heatmap-corner, .heatmap-column, .heatmap-genre, .heatmap-cell { display: flex; align-items: center; min-height: 32px; font-size: 12px; }
.heatmap-column { justify-content: center; color: var(--muted); }
.heatmap-genre { overflow: hidden; white-space: nowrap; }
.heatmap-cell { justify-content: center; border-radius: 6px; color: #f5fff8; font-variant-numeric: tabular-nums; }
.heatmap-scale { display: flex; justify-content: flex-end; align-items: center; gap: 10px; margin-top: 12px; color: var(--muted); font-size: 12px; }
.heatmap-scale-bar { width: 140px; height: 6px; border-radius: 3px; background: linear-gradient(90deg, #242424, #224d34, #297442, #2b7c48); }
.music-section { margin-top: 36px; scroll-margin-top: 24px; }
.report-view.music-section { margin-top: 0; padding-top: 28px; }
.duplicates-heading { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 14px; margin-bottom: 16px; }
.music-heading { padding-block: 20px 12px; margin-bottom: 16px; }
.music-heading .section-title { font-size: clamp(36px, 5.5vw, 72px); line-height: 1.05; letter-spacing: -.04em; }
.music-summary { margin: 4px 0 0; color: #e2dbf4; font-size: 14px; font-variant-numeric: tabular-nums; }
.duplicates-actions { display: flex; flex-wrap: wrap; gap: 8px; }
input, select, button.small { min-width: 0; min-height: 38px; padding: 8px 14px; border: 1px solid transparent; border-radius: 999px; color: var(--text); background: #242424; }
button.small { display: inline-flex; align-items: center; justify-content: center; font-size: 14px; font-weight: 500; line-height: 20px; transition: background .15s; }
button.small:hover:not(:disabled) { background: #303030; }
button.small:active:not(:disabled) { background: #383838; }
input, select { width: 100%; height: 42px; background: #242424; }
input:focus, select:focus { outline: none; }
input:focus-visible, select:focus-visible { outline: 2px solid #fff; outline-offset: 1px; }
input::placeholder { color: transparent; }
select { appearance: none; padding-right: 42px; font-size: 12px; background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%23b3b3b3' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3C/svg%3E"); background-repeat: no-repeat; background-size: 16px 16px; background-position: right 16px center; }
.toolbar { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; justify-content: flex-start; }
.toolbar > .web-select, .toolbar > select { flex: 0 1 200px; width: 200px; max-width: 100%; }
.search-control { position: relative; min-width: 0; }
.search-control input { height: 44px; padding-left: 16px; font-size: 13px; line-height: 20px; }
.search-placeholder { position: absolute; left: 17px; top: 50%; max-width: calc(100% - 40px); overflow: hidden; transform: translateY(-50%); color: var(--muted); font-size: 13px; line-height: 20px; white-space: nowrap; text-overflow: ellipsis; pointer-events: none; }
.search-control:not(.is-empty) .search-placeholder { display: none; }
.page-search { width: 100%; margin: 0 0 20px; }
.page-search input { width: 100%; height: 52px; padding: 0 20px 0 50px; border-color: transparent; background: #242424; font-size: 14px; transition: background .15s, border-color .15s; }
.page-search input:hover, .page-search input:focus { background: #303030; }
.page-search input:focus-visible { outline: 2px solid #fff; outline-offset: -2px; }
.page-search .search-placeholder { left: 50px; max-width: calc(100% - 90px); font-size: 14px; }
.search-icon { position: absolute; z-index: 1; left: 18px; top: 50%; width: 20px; height: 20px; transform: translateY(-50%); color: var(--muted); pointer-events: none; }
.page-search:focus-within .search-icon { color: var(--text); }
.web-select { position: relative; min-width: 0; }
.web-select-trigger { display: grid; grid-template-columns: minmax(0,1fr) 16px; align-items: center; gap: 12px; width: 100%; height: 44px; padding: 0 16px; border: 1px solid transparent; border-radius: 999px; color: var(--text); background: #242424; font-size: 13px; font-weight: 400; line-height: 20px; text-align: left; transition: background .15s; }
.web-select-trigger:hover, .web-select-trigger[aria-expanded="true"] { background: #303030; }
.web-select-label { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.web-select-trigger svg, .group-chevron { display: block; width: 16px; height: 16px; fill: none; stroke: #b3b3b3; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }
.web-select-menu { position: fixed; inset: auto; z-index: 100; display: block; margin: 0; padding: 0; overflow: hidden; contain: paint; border: 1px solid transparent; border-radius: var(--radius-tile); color: var(--text); background: #242424; box-shadow: 0 12px 40px #0009; }
.web-select-options { display: grid; align-content: start; gap: 2px; max-height: calc(var(--menu-height,300px) - 2px); padding: 6px; overflow-y: auto; overscroll-behavior: contain; scrollbar-gutter: stable both-edges; }
.web-select-option { min-height: 36px; padding: 8px 10px; overflow: hidden; border-radius: var(--radius-small); font-size: 13px; line-height: 20px; text-overflow: ellipsis; white-space: nowrap; cursor: pointer; }
.web-select-option.active { background: #3b3b3b; }
.web-select-option[aria-selected="true"] { color: var(--accent-strong); }
.web-select-option[aria-disabled="true"] { color: #777; cursor: not-allowed; }
.music-toolbar { margin: 16px 0; }
.music-operations { padding: 18px 20px; border-radius: var(--radius); background: var(--panel); }
.music-operations-title { margin: 0 0 10px; color: #e2dbf4; font-size: 13px; font-weight: 700; }
.music-operations-row { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
.operation-status { margin-top: 16px; color: var(--muted); font-size: 12px; line-height: 20px; overflow-wrap: anywhere; }
.operation-status:empty { margin-top: 0; }
.music-genre-pagination { position: relative; margin-bottom: 6px; }
.music-genre-filters { display: flex; gap: 8px; min-width: 0; padding-block: 2px; overflow-x: auto; scrollbar-width: none; scroll-padding-inline: 40px; }
.music-genre-filters::-webkit-scrollbar { display: none; }
.music-genre-arrow { position: absolute; z-index: 1; inset-inline-start: 0; top: 50%; transform: translateY(-50%); display: grid; place-items: center; width: 32px; height: 32px; padding: 0; border: 0; border-radius: 50%; background: #ffffffe0; color: #181818; }
.music-genre-arrow:last-child { inset-inline: auto 0; }
.music-genre-arrow:hover { background: #fff; }
.music-genre-arrow svg { width: 20px; height: 20px; }
.music-genre { flex: none; max-width: 100%; min-height: 32px; padding: 5px 12px; overflow: hidden; border: 0; border-radius: 999px; background: #2b2b2b; color: var(--text); font-size: 13px; font-weight: 600; white-space: nowrap; text-overflow: ellipsis; }
.music-genre:hover { background: #373737; }
.music-genre[aria-pressed="true"] { background: #f1f1f1; color: #161616; }
.music-genre:focus-visible { outline: 2px solid var(--text); outline-offset: -3px; }
@media (prefers-reduced-motion: no-preference) {
  .music-genre-filters { scroll-behavior: smooth; }
}
#musicSection .music-operations { background: #100c1d50; }
#musicSection :is(.page-search input, .music-operations button.small, .music-genre:not([aria-pressed="true"])) {
  background-color: #ffffff17;
}
#musicSection :is(.page-search input, .music-operations button.small, .music-genre:not([aria-pressed="true"])):hover,
#musicSection .page-search input:focus {
  background-color: #ffffff28;
}
.music-list { width: 100%; border-collapse: separate; border-spacing: 0; table-layout: fixed; }
.music-list th, .music-list td { text-align: left; padding: 7px 12px; }
.music-list thead th { padding-block: 9px; border-bottom: 1px solid var(--line); color: var(--muted); font-size: 13px; font-weight: 500; }
.music-sort { display: flex; align-items: center; gap: 8px; width: 100%; min-height: 22px; padding: 0; border: 0; border-radius: 2px; background: transparent; color: inherit; text-align: inherit; }
.music-track-number .music-sort { justify-content: center; gap: 4px; }
.music-track-duration .music-sort { justify-content: flex-end; }
.music-sort:hover, th[aria-sort] > .music-sort { color: var(--text); }
th[aria-sort] > .music-sort::after {
  content: "";
  border-inline: 5px solid transparent;
  border-bottom: 5px solid var(--accent);
}
th[aria-sort="descending"] > .music-sort::after { transform: rotate(180deg); }
.music-list .music-track-number { width: 48px; padding-inline: 4px; text-align: center; color: var(--muted); font-size: 13px; font-variant-numeric: tabular-nums; }
.music-list :is(.music-track-artist, .music-track-album) { width: 23%; color: var(--muted); font-size: 13px; }
.music-list .music-track-duration { width: 78px; text-align: right; color: var(--muted); font-size: 13px; font-variant-numeric: tabular-nums; white-space: nowrap; }
.music-track-duration svg { width: 16px; height: 16px; vertical-align: middle; }
.music-list .music-track-control { width: 48px; text-align: center; padding-inline: 4px; }
.music-track-row:hover > *, .music-track-row:focus-within > *, .music-card.is-current-track > .music-track-row > * { background: #ffffff0b; }
.music-track-row > :first-child { border-radius: var(--radius-small) 0 0 var(--radius-small); }
.music-track-row > :last-child { border-radius: 0 var(--radius-small) var(--radius-small) 0; }
.music-card:has(> .music-track-details:not([hidden])) > .music-track-row > * { background: var(--panel); border-bottom-left-radius: 0; border-bottom-right-radius: 0; }
.music-track-name { display: flex; align-items: center; gap: 12px; min-width: 0; }
.music-track-text { min-width: 0; }
.music-track-row .music-title, .music-track-artist, .music-track-album, .music-track-artist-mobile, .music-track-album-mobile { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.music-track-artist-mobile, .music-track-album-mobile { display: none; color: var(--muted); font-size: 12px; font-weight: 400; }
.music-play, .music-details-toggle { display: inline-grid; place-items: center; padding: 0; border: 0; background: transparent; color: var(--muted); }
.music-play { position: relative; flex: 0 0 40px; border-radius: 5px; }
.music-play .music-cover { width: 40px; height: 40px; border-radius: inherit; }
.music-play .empty-cover-icon { width: 18px; height: 18px; }
.music-play-icons { position: absolute; inset: 0; display: grid; place-items: center; border-radius: inherit; background: #0009; color: #fff; opacity: 0; transition: opacity .15s; }
.music-play-icons svg { width: 17px; height: 17px; }
.music-track-row:hover .music-play-icons, .music-play:focus-visible .music-play-icons, .is-playing-track .music-play-icons { opacity: 1; }
.music-play .music-pause-icon, .is-playing-track .music-play .music-play-icon { display: none; }
.is-playing-track .music-play .music-pause-icon { display: block; }
.music-details-toggle { width: 36px; height: 36px; border-radius: 50%; }
.music-details-toggle:hover, .music-details-toggle[aria-expanded="true"] { background: #ffffff0e; color: var(--text); }
.music-details-toggle .group-chevron { width: 18px; height: 18px; }
.music-details-toggle[aria-expanded="true"] .group-chevron { transform: rotate(180deg); }
.music-list .music-track-details td { padding: 0 0 6px; }
.music-track-panel { position: relative; padding: 14px 46px 16px 16px; border-radius: 0 0 var(--radius-small) var(--radius-small); background: var(--panel); }
.music-track-panel .music-path { margin-top: 0; }
.music-track-match { margin-top: 8px; color: var(--muted); font-size: 12px; }
.music-track-panel .music-pills:empty { display: none; }
.list-pagination { display: grid; justify-items: center; gap: 8px; padding: 24px 0 8px; color: var(--muted); font-size: 12px; }
.list-pagination p { margin: 0; }
.music-card-content { display: grid; grid-template-columns: 112px minmax(0, 1fr); gap: 20px; align-items: start; }
.music-card-main { min-width: 0; }
.music-cover { display: grid; place-items: center; align-content: center; gap: 8px; width: 112px; aspect-ratio: 1; overflow: hidden; border-radius: var(--radius-tile); background: #2a2a2a; color: var(--muted); }
.music-cover img { width: 100%; height: 100%; object-fit: cover; }
.empty-cover-icon { width: 32px; height: 32px; color: #888; }
.music-cover-empty strong { font-size: 12px; font-weight: 400; }
.music-title { font-size: 15px; font-weight: 600; overflow-wrap: anywhere; }
.music-path, .track-path { margin-top: 4px; color: var(--muted); font-size: 12px; overflow-wrap: anywhere; }
.music-actions { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 14px; }
.music-card .music-pills + .music-actions { margin-top: 20px; }
.music-actions .small { min-height: 34px; padding: 6px 12px; font-size: 13px; }
.music-trash-icon { position: absolute; top: 16px; right: 14px; display: grid; place-items: center; width: 28px; height: 28px; padding: 0; border: 0; border-radius: 50%; color: var(--muted); background: transparent; }
.music-trash-icon:hover { color: var(--bad); background: #ffffff0c; }
.trash-svg { width: 17px; height: 17px; }
.identity-warning { margin-top: 12px; padding: 10px 12px; border-radius: var(--radius-small); color: var(--warning); background: #f0c6740d; font-size: 12px; }
.identity-warning-icon { width: 16px; height: 16px; margin-right: 5px; }
.music-pills { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 12px; }
.music-pill { display: inline-flex; align-items: center; max-width: 100%; padding: 2px 8px; border: 1px solid transparent; border-radius: 6px; color: #abd2b8; background: #243329; font-size: 12px; font-weight: 400; line-height: 1.5; overflow-wrap: anywhere; }
.music-pill-format { font-weight: 600; }
.duplicate-track { cursor: pointer; }
.music-card.is-current-track .music-title, .duplicate-track.is-current-track .music-title { color: var(--accent); }
.audio-playback-status { margin-top: 8px; color: var(--bad); font-size: 12px; }
.audio-player { display: none; }
.global-player[hidden], .global-player [hidden] { display: none; }
.global-player { position: fixed; inset: auto 0 0; z-index: 60; display: grid; grid-template-columns: minmax(0, 1fr) minmax(260px, 2fr) minmax(0, 1fr); align-items: center; gap: 24px; min-height: 88px; padding: 12px 24px; background: #000; box-shadow: 0 -8px 24px #0003; }
body.has-player { padding-bottom: var(--player-height, 88px); }
body.has-player .app-sidebar { bottom: calc(var(--player-height, 88px) + 8px); }
body.has-player .lyrics-modal { bottom: var(--player-height, 88px); }
body.has-player .lyrics-dialog { max-height: min(85vh, calc(100dvh - var(--player-height, 88px) - 40px)); }
.global-track { display: flex; gap: 12px; align-items: center; min-width: 0; }
.global-cover { flex: 0 0 56px; width: 56px; height: 56px; object-fit: cover; border-radius: 6px; }
.global-cover-placeholder { display: grid; place-items: center; color: var(--muted); background: var(--soft); }
.global-cover-placeholder svg { width: 24px; height: 24px; }
.global-track-text { display: grid; min-width: 0; gap: 2px; }
.global-track-text strong, .global-track-text span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.global-track-text strong { font-size: 13px; font-weight: 650; }
.global-track-text span { font-size: 12px; color: var(--muted); }
.global-controls { display: grid; justify-items: center; gap: 5px; width: 100%; max-width: 640px; margin-inline: auto; }
.global-transport { display: flex; gap: 16px; align-items: center; justify-content: center; }
.global-skip { display: grid; place-items: center; width: 28px; height: 28px; padding: 0; border: 0; border-radius: 50%; color: #b3b3b3; background: transparent; }
.global-skip svg { width: 20px; height: 20px; fill: currentColor; }
.global-skip:hover:not(:disabled) { color: #fff; }
.global-timeline { display: grid; grid-template-columns: 38px minmax(0, 1fr) 38px; align-items: center; gap: 8px; width: 100%; }
.global-timeline .audio-time:first-child { text-align: right; }
.global-extras { display: flex; justify-content: flex-end; align-items: center; gap: 8px; }
.global-volume { width: 90px; }
.global-lyrics { display: grid; place-items: center; width: 32px; height: 32px; padding: 0; border: 0; border-radius: 50%; color: var(--muted); background: transparent; }
.global-lyrics svg { width: 18px; height: 18px; }
.global-lyrics:hover { color: var(--text); background: #ffffff16; }
.global-status { grid-column: 1 / -1; margin: 0; text-align: center; }
@media (max-width: 760px) {
  .global-player { grid-template-columns: minmax(0, 1fr) auto; gap: 8px 16px; padding: 10px 16px; }
  .global-cover { width: 40px; height: 40px; flex-basis: 40px; }
  .global-controls { display: contents; }
  .global-transport { grid-column: 2; grid-row: 1; gap: 8px; }
  .global-timeline { grid-column: 1 / -1; grid-row: 2; }
  .global-extras { grid-column: 1 / -1; grid-row: 3; }
  .global-extras .global-lyrics { margin-right: auto; }
  body.has-player .app-sidebar { bottom: auto; }
}
.audio-play, .audio-mute { display: flex; align-items: center; justify-content: center; width: 32px; height: 32px; padding: 0; border: 0; border-radius: 50%; color: var(--text); background: transparent; line-height: 0; }
.audio-play { color: #000; background: #fff; }
.audio-play:hover { background: var(--accent); }
.audio-mute:hover { background: #ffffff16; }
.playback-icon { display: block; fill: currentColor; stroke: none; }
.audio-play-icon, .audio-pause-icon { width: 16px; height: 16px; margin: 0; }
.audio-pause-icon, .audio-play.playing .audio-play-icon { display: none; }
.audio-play.playing .audio-pause-icon { display: block; }
.audio-time { color: var(--muted); font-size: 12px; font-variant-numeric: tabular-nums; }
.audio-seek-wrap { position: relative; display: flex; align-items: center; min-width: 0; height: 20px; }
.audio-seek-track { width: 100%; height: 4px; overflow: hidden; border-radius: 2px; background: #555; pointer-events: none; }
.audio-seek-fill { display: block; width: var(--audio-progress, 0%); height: 100%; background: #fff; }
.audio-seek-wrap:hover .audio-seek-fill, .audio-seek-wrap:focus-within .audio-seek-fill { background: var(--accent); }
.audio-seek { position: absolute; inset: 0; width: 100%; height: 100%; min-height: 0; margin: 0; padding: 0; opacity: 0; cursor: pointer; }
.audio-seek-wrap:focus-within, .audio-seek:focus-visible { outline: none; }
.audio-volume-icon { width: 17px; height: 17px; color: var(--muted); }
.audio-mute .audio-volume-off, .audio-mute.muted .audio-volume-on { display: none; }
.audio-mute.muted .audio-volume-off { display: block; }
.quarantine-one { color: #b9e2c7 !important; }
.quarantine-panel { display: none; margin: 12px 0; padding: 16px; border: 0; border-radius: var(--radius); background: var(--panel); }
.quarantine-panel.visible { display: block; }
.quarantine-panel p { margin: 0; color: var(--muted); font-size: 13px; overflow-wrap: anywhere; }
.copy-status { color: var(--muted); font-size: 12px; }
.global-progress { display: none; height: 4px; margin-top: 12px; overflow: hidden; border-radius: 2px; background: #ffffff16; }
.global-progress.visible { display: block; }
.global-progress span { display: block; width: 40%; height: 100%; background: var(--accent); animation: card-progress 1.1s ease-in-out infinite; }
.music-card-status, .duplicate-card-status { display: none; margin-top: 12px; color: var(--muted); font-size: 12px; overflow-wrap: anywhere; }
.duplicate-card-status { grid-column: 1 / -1; }
.music-card-status.visible, .duplicate-card-status.visible { display: block; }
.music-card-status.done, .duplicate-card-status.done { color: var(--good); }
.music-card-status.error, .duplicate-card-status.error { color: var(--bad); }
.music-card-progress { position: relative; height: 4px; margin-top: 8px; overflow: hidden; border-radius: 2px; background: #ffffff16; }
.music-card-progress span { position: absolute; inset: 0 auto 0 0; width: 42%; background: var(--accent); transform: translateX(-100%); }
.running .music-card-progress span { animation: card-progress 1.1s ease-in-out infinite; }
.done .music-card-progress span, .error .music-card-progress span { width: 100%; transform: none; animation: none; }
.error .music-card-progress span { background: var(--bad); }
@keyframes card-progress { 0% { transform: translateX(-100%); } 55% { transform: translateX(70%); } 100% { transform: translateX(240%); } }
.group-card { margin-top: 8px; min-width: 0; border: 0; border-radius: var(--radius-tile); background: var(--panel); }
.group-card:first-child { margin-top: 8px; }
.group-header { display: flex; align-items: center; gap: 16px; width: 100%; padding: 16px; color: var(--text); text-align: left; cursor: pointer; list-style: none; border-radius: var(--radius-tile); }
.group-header::-webkit-details-marker { display: none; }
.group-header:hover { background: #ffffff04; }
.group-cover { flex-shrink: 0; }
.group-cover .music-cover { width: 48px; height: 48px; border-radius: 8px; }
.group-cover .music-cover strong { display: none; }
.group-cover .empty-cover-icon { width: 22px; height: 22px; }
.group-heading-text { min-width: 0; flex: 1; }
.group-title { margin: 0; font-size: 15px; font-weight: 700; line-height: 1.4; overflow-wrap: anywhere; }
.group-differences { margin-top: 3px; color: #c4c4c4; font-size: 12px; }
.group-meta { display: flex; flex-wrap: wrap; gap: 4px 12px; margin-top: 4px; color: var(--muted); font-size: 11px; }
.group-subtitle { color: var(--muted); font-size: 11px; }
.group-status { flex-shrink: 0; padding: 4px 10px; border-radius: 999px; color: #b9d7c2; background: #25332a; font-size: 11px; }
.group-card[data-review-only="yes"] .group-status { color: var(--warning); background: #393125; }
.group-chevron { flex-shrink: 0; align-self: center; }
.group-card[open] > .group-header .group-chevron { transform: rotate(180deg); }
.group-card[data-review-only="yes"] .group-subtitle, .group-card[data-review-only="yes"] .track-label { color: var(--warning); }
.group-body { display: grid; gap: 16px; padding: 16px; }
.comparison { min-width: 0; }
.duplicate-file-grid { display: grid; grid-template-columns: repeat(var(--compare-files, 2), minmax(280px, 1fr)); gap: 20px 16px; overflow-x: auto; padding-bottom: 6px; }
.comparison-enhanced .duplicate-file-grid { grid-template-rows: auto auto; }
.duplicate-file-column { display: grid; grid-template-rows: subgrid; grid-row: 1 / span 2; gap: 20px; min-width: 0; padding: 16px; border-radius: var(--radius-tile); background: var(--soft); }
.duplicate-track { display: flex; flex-direction: column; min-width: 0; padding: 14px 36px 14px 14px; border: 0; border-radius: var(--radius-small); background: var(--soft); box-shadow: 0 3px 10px #0002; }
.duplicate-track:hover { background: #2b2b2b; }
.duplicate-file-column .duplicate-track { padding: 0 24px 0 0; background: transparent; box-shadow: none; }
.duplicate-file-column .duplicate-track .music-trash-icon { top: 0; right: 0; }
.duplicate-track .music-actions .duplicate-listen { min-width: 100px; background: #414141; }
.duplicate-track .music-actions .duplicate-listen:hover:not(:disabled) { background: #505050; }
.duplicate-track .music-actions .quarantine-one { background: #304738; }
.duplicate-track .music-actions .quarantine-one:hover:not(:disabled) { background: #3b5946; }
.duplicate-track .music-card-content { display: grid; grid-template-columns: 48px minmax(0, 1fr); gap: 12px; flex: 1; align-items: start; }
.duplicate-track .music-card-main { display: flex; flex-direction: column; align-self: stretch; min-width: 0; }
.duplicate-track .music-cover { width: 48px; height: 48px; border-radius: 6px; }
.duplicate-file-number { order: -1; margin-bottom: 3px; color: var(--muted); font-size: 11px; }
.duplicate-track .track-title { margin-top: 5px; font-size: 13px; }
.duplicate-track .track-path { margin-top: 6px; font-size: 11px; overflow-wrap: anywhere; }
.duplicate-track .duplicate-quality { margin-top: 12px; }
.comparison-enhanced .duplicate-track .duplicate-quality { display: none; }
.duplicate-matrix-panel { margin: 0 0 12px; }
.duplicate-matrix-toolbar { display: flex; flex-direction: column; align-items: flex-start; gap: 8px; margin-bottom: 8px; font-size: 12px; }
.duplicate-matrix-toolbar strong { color: #c4c4c4; font-weight: 600; }
.duplicate-matrix-toolbar .small { min-height: 32px; padding: 5px 12px; background: #3b3b3b; font-size: 12px; }
.duplicate-matrix-toolbar .small:hover:not(:disabled) { background: #4a4a4a; }
.duplicate-file-parameters { min-width: 0; }
.duplicate-file-table thead th { color: var(--text); font-weight: 600; }
.duplicate-file-table th:last-child { width: 40%; text-align: right; }
.duplicate-matrix-note { margin: 10px 0 0; color: var(--muted); font-size: 12px; }
.duplicate-toolbar { margin-bottom: 16px; }
.quality-table { width: 100%; border-collapse: collapse; table-layout: fixed; font-size: 12px; }
.quality-table tr { height: 32px; }
.quality-table th, .quality-table td { padding: 6px 0; border-bottom: 1px solid #ffffff0a; overflow-wrap: anywhere; }
.quality-table th { width: 60%; color: var(--muted); font-weight: 400; text-align: left; }
.quality-table td { color: var(--text); font-weight: 500; text-align: right; }
.quality-table td.quality-better { color: var(--good); font-weight: 700; }
.duplicate-track .music-actions { margin-top: auto; padding-top: 12px; }
.duplicate-listen svg { width: 14px; height: 14px; margin-right: 5px; }
.duplicate-listen .duplicate-listen-pause, .duplicate-listen.playing .duplicate-listen-play { display: none; }
.duplicate-listen.playing .duplicate-listen-pause { display: block; }
.duplicate-track-heading { display: flex; flex-wrap: wrap; align-items: baseline; gap: 4px 12px; margin-bottom: 4px; }
.track-label { color: #9ad8ae; font-size: 12px; font-weight: 600; }
.move .track-label { color: var(--bad); }
.duplicate-reason { color: var(--muted); font-size: 12px; overflow-wrap: anywhere; }
.quality-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; margin-top: 16px; }
.quality-grid div { min-width: 0; padding: 6px 0; border-bottom: 1px solid #ffffff0a; }
.quality-grid span { display: block; color: var(--muted); font-size: 12px; }
.quality-grid strong { display: block; margin-top: 2px; font-size: 12px; font-weight: 500; overflow-wrap: anywhere; }
.empty { display: none; margin-top: 12px; padding: 32px; border-radius: var(--radius); color: var(--muted); background: var(--panel); text-align: center; }
.empty.visible { display: block; }
.lyrics-modal { position: fixed; inset: 0; z-index: 50; display: none; align-items: center; justify-content: center; padding: 20px; background: #000b; }
.lyrics-modal.visible { display: flex; }
.lyrics-dialog { position: relative; display: grid; grid-template-rows: auto auto minmax(0, 1fr); width: min(820px, 100%); max-height: 85vh; overflow: hidden; border: 0; border-radius: var(--radius); background: #202020; box-shadow: 0 24px 80px #0008; }
.lyrics-dialog-head { display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: start; gap: 16px; max-height: 40vh; padding: 28px 64px 16px 32px; overflow-y: auto; }
.lyrics-kicker { margin: 0 0 10px; color: #a8cab4; font-size: 11px; font-weight: 600; letter-spacing: .08em; text-transform: uppercase; }
.lyrics-dialog-title { margin: 0; font-size: 28px; font-weight: 750; line-height: 1.2; letter-spacing: -.4px; overflow-wrap: anywhere; }
.lyrics-artist { margin-top: 8px; color: #b7b7b7; font-size: 15px; }
.lyrics-artist:empty { display: none; }
.lyrics-details { margin-top: 12px; color: var(--muted); font-size: 12px; }
.lyrics-details summary { width: fit-content; cursor: pointer; }
.lyrics-details summary:hover { color: var(--text); }
.lyrics-dialog-path, .lyrics-source { margin-top: 8px; color: var(--muted); font-size: 12px; overflow-wrap: anywhere; }
.lyrics-close { position: absolute; top: 12px; right: 12px; display: grid; place-items: center; width: 32px; height: 32px; padding: 0; border: 0; border-radius: 50%; color: var(--text); background: #2b2b2b; }
.lyrics-close-icon { display: block; width: 18px; height: 18px; }
.lyrics-close:hover { background: #383838; }
.lyrics-toolbar { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; padding: 0 32px 18px; }
.lyrics-toolbar .small { min-height: 32px; padding: 5px 12px; color: #c2c2c2; background: #303030; font-size: 12px; }
.lyrics-toolbar .small[aria-pressed="true"] { color: #c4e5cf; background: #2c4234; }
#lyricsFollow { min-width: 148px; }
.lyrics-sync-note { margin-left: auto; color: var(--muted); font-size: 12px; }
.lyrics-toolbar .audio-playback-status { flex-basis: 100%; margin: 0; }
.lyrics-text { min-height: 0; margin: 0 8px 12px 0; padding: 4px 24px 20px 32px; overflow: auto; scrollbar-gutter: stable; color: #e3e7e4; font-family: inherit; font-size: 26px; font-weight: 650; line-height: 1.6; overflow-wrap: anywhere; }
.lyrics-text:focus-visible { outline: none; }
.lyrics-stanza { margin: 0 0 28px; }
.lyrics-stanza:last-child { margin-bottom: 0; }
.lyrics-line { display: block; white-space: pre-wrap; }
.lyric-seek { width: 100%; padding: 0; border: 0; border-radius: 6px; color: inherit; background: transparent; font: inherit; text-align: left; line-height: inherit; user-select: text; transition: color .18s, background .18s; }
.lyrics-text.is-synced .lyrics-line { color: #858e87; }
.lyrics-text.is-synced .lyric-seek:hover, .lyrics-text.is-synced .lyric-seek:focus-visible { color: #d5dfd8; }
.lyric-seek:focus-visible { outline: none; background: #ffffff0b; }
.lyrics-text.is-synced .lyrics-line.is-current { color: #f5fff8; }
.lyrics-section { margin: 24px 0 12px; color: #a8cab4; font-size: 12px; font-weight: 600; letter-spacing: .03em; }
.lyrics-text > :first-child { margin-top: 0; }
.lyrics-text.is-raw { color: #b9b9b9; font-family: Consolas, "Courier New", monospace; font-size: 14px; font-weight: 400; line-height: 1.65; white-space: pre-wrap; }
.lyrics-text.loading, .lyrics-text.error { color: var(--muted); font-size: 14px; }
.source-dialog { width: min(720px, calc(100vw - 32px)); max-height: calc(100vh - 40px); margin: auto; padding: 0; overflow: auto; border: 0; border-radius: var(--radius); color: var(--text); background: #202020; box-shadow: 0 24px 80px #0008; }
.source-dialog[open] { display: flex; flex-direction: column; overflow: hidden; }
.source-dialog::backdrop { background: #000b; }
.source-dialog-head { display: flex; flex-shrink: 0; align-items: center; justify-content: space-between; gap: 12px; padding: 24px; }
.source-dialog-head h2 { margin: 0; font-size: 20px; }
.source-close { display: grid; place-items: center; width: 32px; height: 32px; padding: 0; border: 0; border-radius: 50%; color: var(--text); background: #333; font-size: 24px; line-height: 1; }
.source-close:hover { background: #404040; }
.source-dialog-body { min-height: 0; padding: 20px 24px 8px; overflow-y: auto; }
.source-dialog label { display: block; margin-bottom: 8px; font-size: 13px; }
.source-path-row { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 8px; }
.source-dialog input::placeholder { color: var(--muted); }
.source-dialog input { font-size: 13px; }
.source-dialog input, .source-dialog button.small { background: #333; }
.source-dialog input:hover, .source-dialog button.small:hover:not(:disabled) { background: #404040; }
.source-navigation { display: flex; flex-wrap: wrap; gap: 8px; margin: 14px 0; }
.source-folder-frame { padding: 8px; overflow: hidden; border: 1px solid transparent; border-radius: var(--radius-tile); background: #181818; }
.source-folders { min-height: 180px; max-height: 262px; padding: 0; overflow-y: auto; overscroll-behavior: contain; }
.source-folder { display: block; width: 100%; padding: 10px 12px; overflow: hidden; border: 0; border-radius: var(--radius-small); color: var(--text); background: transparent; font: inherit; text-align: left; text-overflow: ellipsis; white-space: nowrap; }
.source-folder:hover, .source-folder:focus-visible { background: #ffffff12; }
.source-status, .source-hint { margin: 12px 0; overflow-wrap: anywhere; font-size: 12px; line-height: 1.6; }
.source-hint { color: var(--muted); }
.source-progress { margin: 16px 0; }
.source-progress-caption { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 4px 12px; margin-bottom: 8px; font-size: 12px; }
.source-progress-caption span { color: var(--muted); }
.source-progress progress { display: block; width: 100%; height: 6px; overflow: hidden; border: 0; border-radius: 3px; accent-color: var(--accent); background: #363636; }
.source-progress progress::-webkit-progress-bar { background: #363636; }
.source-progress progress::-webkit-progress-value { border-radius: 3px; background: var(--accent); }
.source-progress progress::-moz-progress-bar { border-radius: 3px; background: var(--accent); }
.source-progress-file { min-height: 19px; margin-top: 6px; overflow: hidden; color: var(--muted); font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }
.source-dialog-actions { display: flex; flex-shrink: 0; flex-wrap: wrap; justify-content: flex-end; gap: 8px; padding: 16px 24px 20px; }
.source-apply { color: #b9e2c7 !important; }
@media (min-width: 1700px) { .page { padding-inline: 40px; } .header { margin-inline: -40px; padding-inline: 40px; } }
@media (max-width: 1450px) {
  .analysis-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .donut-layout { grid-template-columns: 160px minmax(0, 1fr); align-items: center; }
  .toolbar { grid-template-columns: repeat(4, minmax(0, 1fr)); }
  .search-control { grid-column: 1 / -1; }
  .summary { grid-template-columns: repeat(4, minmax(0, 1fr)); }
}
@media (max-width: 1050px) {
  .app-shell { grid-template-columns: 200px minmax(0, 1fr); }
  .app-sidebar { width: 200px; }
  .page { padding-inline: 24px; } .header { margin-inline: -24px; padding-inline: 24px; }
  .collection-art { flex-basis: 104px; height: 104px; } .collection-art svg { width: 56px; height: 56px; }
  .hero-layout { gap: 18px; }
  .hero-lead { max-width: 380px; }
  .donut-layout { grid-template-columns: 1fr; }
  .section-heading p { display: none; }
  .toolbar { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 760px) {
  .app-shell { display: block; padding: 0; }
  .app-sidebar { position: relative; top: auto; left: auto; bottom: auto; flex-direction: row; align-items: center; flex-wrap: wrap; gap: 8px; width: auto; height: auto; min-height: 0; padding: 14px 16px 10px; overflow: visible; contain: none; border-radius: 0; }
  .app-brand { padding: 0; gap: 8px; } .app-brand strong { font-size: 14px; } .app-brand small { display: none; }
  .brand-mark { width: 28px; height: 28px; } .brand-icon { width: 19px; height: 19px; }
  .side-nav { display: flex; flex: 1 0 100%; gap: 4px; order: 2; }
  .side-nav a { justify-content: center; flex: 1; gap: 7px; min-height: 38px; padding: 8px 6px; font-size: 12px; }
  .nav-icon { width: 16px; height: 16px; }
  .nav-caption { display: none; }
  .sidebar-note { order: 1; margin: 0 0 0 auto; padding: 0; border: 0; } .sidebar-note small { display: none; } .sidebar-note strong { font-size: 12px; }
  .sidebar-footer { order: 3; flex: 1 0 100%; grid-template-columns: minmax(0, 1fr) auto; align-items: center; width: 100%; margin: 6px 0 0; padding-top: 10px; }
  .app-workspace { border-radius: 0; } .header { border-radius: 0; }
  .page { padding: 0 20px 40px; } .header { margin-inline: -20px; padding: 24px 20px 16px; }
  .hero-layout { align-items: start; } .collection-art { flex-basis: 80px; height: 80px; } .collection-art svg { width: 44px; height: 44px; }
  h1 { font-size: 34px; } .hero-lead { font-size: 12px; }
  .metric { padding: 12px 10px; } .metric strong { font-size: 24px; }
  .summary { gap: 6px; margin-top: 20px; }
  .metric-label { font-size: 12px; }
  .music-card-content { grid-template-columns: 80px minmax(0, 1fr); gap: 14px; } .music-cover { width: 80px; }
  .duplicate-track { padding: 14px 40px 14px 14px; } .music-trash-icon { right: 8px; top: 10px; }
  .music-actions .small { min-height: 36px; } .section-title { font-size: 22px; }
}
@media (max-width: 520px) {
  .summary.duplicate-summary { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .side-nav { min-width: 0; width: 100%; }
  .side-nav a { flex: 1 1 0; min-width: 0; flex-direction: column; gap: 4px; font-size: 12px; }
  .side-nav a span { white-space: nowrap; }
  .page { padding-inline: 16px; } .header { margin-inline: -16px; padding-inline: 16px; }
  .hero-layout { gap: 12px; } .collection-art { flex-basis: 64px; height: 64px; } .collection-art svg { width: 36px; height: 36px; }
  h1 { font-size: 28px; letter-spacing: -.4px; } .hero-kicker { font-size: 12px; } .hero-lead { font-size: 12px; }
  .summary { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .analysis-grid { grid-template-columns: 1fr; }
  .panel { padding: 18px; } .donut-layout { grid-template-columns: 1fr; gap: 16px; }
  .music-operations { padding: 16px; }
  .music-operations-row { gap: 6px; }
  .duplicates-actions { gap: 6px; } .duplicates-actions .small { min-height: 36px; padding-inline: 10px; font-size: 13px; }
  .music-card-content { grid-template-columns: 1fr; } .music-cover { width: 104px; }
  .group-header { gap: 10px; padding: 12px; }
  .group-status { display: none; }
  .group-body { padding: 12px; }
  .lyrics-dialog-head { padding: 20px 60px 14px 20px; } .lyrics-dialog-title { font-size: 24px; }
  .lyrics-toolbar { padding: 0 20px 14px; }
  .lyrics-sync-note { margin-left: 0; }
  .lyrics-text { padding: 4px 12px 16px 20px; font-size: 20px; }
}
@media (max-width: 680px) {
  .app-workspace:has(#musicSection:not([hidden])) { background-size: 100% 760px; }
  .toolbar > .web-select, .toolbar > select { flex: 1 1 140px; width: auto; }
  .music-list :is(.music-track-artist, .music-track-album) { display: none; }
  :is(.music-track-artist-mobile, .music-track-album-mobile):not(:empty) { display: block; }
  .music-list th, .music-list td { padding-inline: 6px; }
  .music-list .music-track-number { width: 40px; }
  .music-list .music-track-duration { width: 52px; }
  .music-list .music-track-control { width: 44px; }
  .music-track-name { gap: 8px; }
}
@media (hover: none) {
  .music-play-icons { opacity: 1; }
}
/* Keep genre names readable when a panel narrows, including at increased zoom. */
@container (max-width: 360px) {
  .donut-layout { grid-template-columns: 1fr; }
}
@media (prefers-reduced-motion: reduce) {
  html { scroll-behavior: auto; } *, *::before, *::after { animation-duration: .01ms !important; animation-iteration-count: 1 !important; transition-duration: .01ms !important; }
}
"""
