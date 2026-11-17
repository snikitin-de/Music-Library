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
  --scrollbar-size: 6px; --scroll-thumb: #ffffff30; --scroll-thumb-hover: #ffffff70;
}
* { box-sizing: border-box; }
/* A transparent track and a four-pixel visible thumb, without native arrows. */
::-webkit-scrollbar { width: var(--scrollbar-size); height: var(--scrollbar-size); background: transparent; }
::-webkit-scrollbar-track, ::-webkit-scrollbar-corner { background: transparent; }
::-webkit-scrollbar-thumb { min-height: 24px; border: 1px solid transparent; border-radius: 999px; background: var(--scroll-thumb); background-clip: padding-box; }
::-webkit-scrollbar-thumb:hover { background-color: var(--scroll-thumb-hover); }
:where(.app-sidebar, .chart-legend, .web-select-options, .lyrics-text, .heatmap-scroll, .source-folders):hover::-webkit-scrollbar-thumb { background-color: var(--scroll-thumb-hover); }
::-webkit-scrollbar-thumb:active { background-color: #ffffff99; }
::-webkit-scrollbar-button { display: none; width: 0; height: 0; }
:is(.workspace-scroll, .playback-panel-view)::-webkit-scrollbar-thumb { background-color: #454545; }
:is(.workspace-scroll, .playback-panel-view)::-webkit-scrollbar-thumb:hover { background-color: #6c6c6c; }
:is(.workspace-scroll, .playback-panel-view)::-webkit-scrollbar-thumb:active { background-color: #919191; }
:is(.workspace-scroll, .playback-panel-view)::-webkit-scrollbar-button:single-button { display: none; width: 0; height: 0; border: 0; background: transparent; }
/* Firefox uses the standard colours; Chromium keeps the arrow-free custom bar. */
@supports not selector(::-webkit-scrollbar) {
  * { scrollbar-width: thin; scrollbar-color: var(--scroll-thumb) transparent; }
  *:hover { scrollbar-color: var(--scroll-thumb-hover) transparent; }
  :is(.workspace-scroll, .playback-panel-view) { scrollbar-color: #454545 transparent; }
}
html { scroll-behavior: auto; scroll-padding-top: 24px; }
body { margin: 0; min-width: 0; color: var(--text); background: var(--bg); font: 14px/1.55 "Library Nunito", "Segoe UI", Arial, sans-serif; text-rendering: optimizeLegibility; font-kerning: normal; font-synthesis: none; }
::selection { color: #000; background: var(--accent); }
button, input, select { font: inherit; text-rendering: inherit; background-clip: padding-box; }
/* A neutral standard filter paints text with grayscale coverage on Windows too.
   Keep it on controls and text, never on layout ancestors: filters establish a
   containing block for fixed descendants (dropdowns, sidebar and dialogs). */
button, input, select, label, h1, h2, h3, p, pre,
.app-brand strong, .nav-caption, .side-nav a,
.metric, .section-heading>span, .note, .summary-subtitle,
.format-row, .ranking-list, .chart-legend, .donut-hole, .year-chart, .heatmap-grid, .heatmap-scale,
.operation-status, .search-placeholder, .web-select-option,
.music-title, .music-path, .track-title, .track-path, .music-pill, .audio-time,
.identity-warning, .music-card-status, .duplicate-card-status, .copy-status,
.group-title, .group-subtitle, .badges, .track-label, .quality-grid, .divider,
.lyrics-dialog-path, .lyrics-source, .lyrics-artist, .lyrics-line, .lyrics-section,
.lyrics-text.is-raw, .lyrics-text.loading, .lyrics-text.error { filter: opacity(1); }
button { cursor: pointer; }
button:disabled { cursor: not-allowed; opacity: .4; }
.window-close { display: grid; place-items: center; flex: 0 0 32px; width: 32px; height: 32px; padding: 0; border: 0; border-radius: 50%; color: var(--text); background: #2b2b2b; }
.window-close svg { display: block; width: 18px; height: 18px; }
.window-close:hover:not(:disabled) { background: #383838; }
a { color: inherit; }
:focus-visible { outline: 2px solid #fff; outline-offset: 4px; }
[hidden] { display: none !important; }
svg { width: 20px; height: 20px; flex-shrink: 0; vertical-align: middle; shape-rendering: geometricPrecision; }
.app-shell { --sidebar-default-width: 248px; --sidebar-width: var(--sidebar-resized, var(--sidebar-default-width)); --queue-width: var(--queue-resized, clamp(280px, 24vw, 360px)); --panel-gap: 8px; --panel-scroll-inset: 12px; --player-offset: 0px; --topbar-height: 48px; position: relative; display: grid; grid-template-columns: var(--sidebar-width) minmax(0, 1fr); gap: var(--panel-gap); padding: var(--panel-gap); }
.pane-divider { position: absolute; z-index: 22; inset-block: calc(var(--topbar-height) + 2 * var(--panel-gap)) var(--panel-gap); width: var(--panel-gap); cursor: col-resize; touch-action: none; }
.pane-divider-sidebar { left: calc(var(--panel-gap) + var(--sidebar-width)); }
.pane-divider-queue { right: calc(var(--panel-gap) + var(--queue-width)); }
.pane-divider::after { position: absolute; inset-block: 8px; left: 50%; width: 2px; border-radius: 2px; transform: translateX(-50%); content: ""; }
.pane-divider:hover::after { background: #ffffff52; }
.pane-divider:focus-visible { outline: none; }
.pane-divider:is(:focus-visible, .is-dragging)::after { background: var(--accent); }
.app-shell:has(.pane-divider.is-dragging) { cursor: col-resize; user-select: none; }
.app-topbar { position: relative; z-index: 20; display: grid; grid-column: 1 / -1; grid-template-columns: minmax(var(--topbar-height), 1fr) minmax(0, 576px) minmax(var(--topbar-height), 1fr); align-items: center; gap: 8px; }
.topbar-search-area { display: grid; grid-column: 2; grid-template-columns: var(--topbar-height) minmax(0, 1fr) var(--topbar-height); gap: 8px; align-items: center; }
.topbar-round { display: grid; place-items: center; width: var(--topbar-height); height: var(--topbar-height); border-radius: 50%; color: var(--muted); background: #242424; cursor: pointer; }
.topbar-round:hover, .topbar-home.active, .topbar-settings[open] > summary { color: var(--text); background: #303030; }
.topbar-round svg { width: 23px; height: 23px; }
.topbar-settings { position: relative; grid-column: 3; justify-self: end; }
.queue-toggle { border: 0; }
.topbar-settings > summary { list-style: none; }
.topbar-settings > summary::-webkit-details-marker { display: none; }
.topbar-settings-panel { position: absolute; top: calc(100% + 8px); right: 0; width: min(272px, calc(100vw - 24px)); }
.report-menu { padding: 5px; border: 0; border-radius: var(--radius-tile); background: #242424; box-shadow: 0 12px 32px #0008; }
.report-menu button { display: flex; align-items: center; gap: 12px; width: 100%; min-height: 44px; padding: 8px 12px; border: 0; border-radius: var(--radius-small); color: var(--text); background: transparent; text-align: left; }
.report-menu button:hover:not(:disabled), .report-menu button[aria-expanded="true"] { background: #ffffff12; }
.report-menu button:focus-visible { outline-offset: -2px; }
.topbar-settings-panel button > span { min-width: 0; }
.topbar-settings-panel button svg, .topbar-settings-panel small { color: var(--muted); }
.topbar-settings-panel strong { font-weight: inherit; }
.topbar-settings-panel small { display: block; font-size: 12px; line-height: 1.4; }
.topbar-settings-panel .mode-real strong, .topbar-settings:has(.mode-real) > summary { color: var(--warning); }
#librarySourcePath { overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
.app-sidebar { --sidebar-item-inset: 14px; position: fixed; top: calc(var(--topbar-height) + 2 * var(--panel-gap)); left: var(--panel-gap); bottom: calc(var(--panel-gap) + var(--player-offset)); z-index: 10; display: flex; flex-direction: column; width: var(--sidebar-width); padding: 24px 12px 16px; overflow-y: auto; overscroll-behavior: contain; contain: layout paint; border-radius: var(--radius); background: var(--panel-solid); }
.app-sidebar-header { display: flex; align-items: center; justify-content: space-between; gap: 4px; margin-bottom: 28px; }
.app-brand { display: flex; align-items: center; gap: 12px; padding-left: 12px; text-decoration: none; }
.sidebar-toggle { display: grid; place-items: center; flex-shrink: 0; width: 36px; height: 36px; padding: 0; border: 0; border-radius: var(--radius-small); color: var(--muted); background: transparent; }
.sidebar-toggle:hover, .sidebar-toggle:focus-visible { color: var(--text); background: #282828; }
.sidebar-toggle svg { width: 24px; height: 24px; }
.sidebar-toggle[aria-expanded="false"] .sidebar-toggle-chevron { transform-box: fill-box; transform-origin: center; transform: scaleX(-1); }
.brand-mark { display: grid; place-items: center; width: 36px; height: 36px; flex-shrink: 0; border-radius: 50%; color: #000; background: var(--accent); }
.brand-icon { width: 23px; height: 23px; }
.app-brand>span:last-child { display: grid; gap: 1px; }
.app-brand strong { font-size: 16px; letter-spacing: -.4px; }
.app-brand small { color: var(--muted); font-size: 12px; }
.nav-caption { margin: 14px var(--sidebar-item-inset) 8px; color: var(--muted); font-size: 12px; font-weight: 600; letter-spacing: .6px; text-transform: uppercase; }
.side-nav { display: grid; gap: 4px; }
.side-nav a { display: flex; align-items: center; gap: 14px; min-height: 46px; padding: 10px var(--sidebar-item-inset); border-radius: var(--radius-small); color: var(--muted); font-weight: 600; text-decoration: none; transition: color .15s, background .15s; }
.side-nav a:hover { color: #fff; background: #1c1c1c; }
.side-nav a.active { color: #fff; background: #282828; }
.side-nav a.active .nav-icon { color: var(--accent); }
.sidebar-playlists { --playlist-row-outset: 4px; display: grid; flex-shrink: 0; gap: 6px; margin-top: 24px; }
.sidebar-playlists-heading { display: flex; align-items: center; justify-content: space-between; gap: 6px; }
.sidebar-playlists-heading .nav-caption { display: block; margin: 0; margin-inline-start: var(--sidebar-item-inset); }
.sidebar-playlists-heading button.small { min-height: 30px; padding: 4px 10px; font-size: 12px; }
.sidebar-playlists input, .playlist-track-menu input { min-height: 34px; height: 34px; padding: 6px 12px; font-size: 13px; }
.sidebar-playlists input::placeholder, .playlist-track-menu input::placeholder { color: var(--muted); }
.playlist-search-row { display: grid; align-items: center; gap: 6px; padding-inline-start: calc(var(--sidebar-item-inset) - 7px); grid-template-columns: 34px minmax(0, 0fr) auto; transition: grid-template-columns .22s ease; }
.playlist-search-row.is-open { grid-template-columns: 34px minmax(0, 1fr) auto; }
.playlist-search-field { min-width: 0; overflow: clip; opacity: 0; transition: opacity .18s ease; }
.playlist-search-row.is-open .playlist-search-field { opacity: 1; }
.playlist-search-field input:focus, .playlist-track-menu input:focus { outline: none; background: #383838; }
.playlist-search-toggle { display: grid; place-items: center; width: 34px; height: 34px; padding: 0; border: 0; border-radius: 50%; color: var(--muted); background: transparent; }
.playlist-search-toggle:hover, .playlist-search-toggle[aria-expanded="true"] { color: var(--text); background: #252525; }
.playlist-sort { min-width: 0; justify-self: end; }
.playlist-sort .web-select-trigger { display: flex; justify-content: center; gap: 6px; height: 34px; padding: 0 7px; border: 0; border-radius: var(--radius-small); color: var(--muted); background: transparent; font-size: 12px; font-weight: 700; white-space: nowrap; }
.playlist-sort .web-select-trigger svg { width: 17px; height: 17px; stroke: currentColor; }
.playlist-sort .web-select-trigger:hover, .playlist-sort .web-select-trigger[aria-expanded="true"] { color: var(--text); background: #252525; }
.playlist-sort .web-select-trigger:focus-visible { outline-offset: -2px; }
.playlist-search-row.is-open .playlist-sort .web-select-trigger { width: 34px; padding: 0; }
.playlist-search-row.is-open .playlist-sort .web-select-label { display: none; }
#playlistSort-options { min-width: min(180px, calc(100vw - 24px)); }
#playlistSort-options .web-select-option { position: relative; padding-right: 30px; }
#playlistSort-options .web-select-option[aria-selected="true"]::after { position: absolute; right: 10px; content: "✓"; }
@media (prefers-reduced-motion: reduce) {
  .playlist-search-row, .playlist-search-field { transition: none; }
}
#playlistNavigation { display: grid; gap: 4px; margin-inline: calc(-1 * var(--playlist-row-outset)); }
#playlistNavigation a { display: flex; align-items: center; gap: 11px; min-height: 62px; padding: 7px 8px; padding-inline-start: calc(var(--sidebar-item-inset) + var(--playlist-row-outset)); overflow: hidden; border-radius: var(--radius-small); color: var(--text); text-decoration: none; }
#playlistNavigation a:hover { background: #242424; }
#playlistNavigation a:focus-visible { outline-offset: -2px; }
.playlist-nav-title { min-width: 0; overflow: hidden; font-weight: 700; text-overflow: ellipsis; white-space: nowrap; }
#playlistNavigation .playlist-art { flex: 0 0 46px; width: 46px; font-size: 10px; }
.playlist-hint { margin: 0; color: var(--muted); font-size: 13px; overflow-wrap: anywhere; }
.sidebar-playlists .playlist-hint { padding-inline-start: var(--sidebar-item-inset); }
.app-workspace { --page-padding: 32px; grid-column: 2; min-width: 0; min-height: calc(100vh - 16px); border-radius: var(--radius); background: var(--panel-solid); }
.workspace-scroll:focus-visible { outline-offset: -2px; }
.app-workspace:has(.report-view:not([hidden])) {
  --library-gradient-color: #513a9f;
  background: linear-gradient(
    var(--library-gradient-color),
    color-mix(in srgb, var(--library-gradient-color) 72%, var(--panel-solid)) 24%,
    color-mix(in srgb, var(--library-gradient-color) 43%, var(--panel-solid)) 48%,
    color-mix(in srgb, var(--library-gradient-color) 16%, var(--panel-solid)) 75%,
    var(--panel-solid)
  ) left var(--workspace-background-offset, 0px) / 100% 610px no-repeat var(--panel-solid);
}
.app-workspace:has(.report-view[data-page="overview"]:not([hidden])) {
  --library-gradient-color: color-mix(in srgb, var(--accent) 74%, var(--panel-solid));
}
.app-workspace:has(#duplicates:not([hidden])) {
  --library-gradient-color: #266882;
}
.app-workspace:has([data-page="playlist"]:not([hidden])) {
  --library-gradient-color: var(--playlist-color, #494949);
}
.page { width: 100%; max-width: 1800px; margin: 0 auto; padding: 0 var(--page-padding) 56px; }
.report-view[data-page="overview"] { container: overview / inline-size; }
.header { padding-block: 32px 24px; }
.hero-layout { display: flex; align-items: center; gap: 24px; min-width: 0; }
.collection-art { display: grid; place-items: center; flex: 0 0 140px; height: 140px; border-radius: var(--radius-tile); background: var(--accent); color: #0b301c; box-shadow: 0 8px 24px #0004; }
.music-section .collection-art {
  background: color-mix(in srgb, var(--library-gradient-color) 70%, white);
  color: var(--panel-solid);
}
.collection-art svg { width: 72px; height: 72px; stroke-width: 1.6; }
.hero-copy { min-width: 0; }
h1 { margin: 0; font-size: clamp(32px, 4.5vw, 64px); font-weight: 750; letter-spacing: -.8px; line-height: 1.15; }
.summary { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 8px; margin-top: 28px; }
.metric { position: relative; min-width: 0; padding: 14px 12px; border-radius: var(--radius-tile); background: #ffffff0a; }
.metric strong { display: block; margin-top: 8px; font-size: 26px; font-weight: 700; letter-spacing: -.6px; line-height: 1; font-variant-numeric: tabular-nums; }
.metric-label { display: block; color: #b3b3b3; font-size: 12px; }
.metric-icon { display: none; }
.metric-primary strong { color: var(--accent); }
.section-heading { margin-top: 22px; }
.section-heading span { color: var(--muted); font-size: 12px; }
.section-heading h2 { margin: 0; font-size: 24px; font-weight: 750; letter-spacing: -.3px; line-height: 1.3; }
.analysis-grid { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 12px; margin-top: 16px; align-items: stretch; }
.panel { min-width: 0; padding: 20px; border-radius: var(--radius); background: var(--panel); container-type: inline-size; }
.panel h2 { margin: 0; font-size: 16px; font-weight: 700; letter-spacing: 0; }
.panel-body { margin-top: 18px; }
.note, .chart-note, .format-empty { color: var(--muted); font-size: 12px; line-height: 1.8; }
.note strong, .chart-note strong { color: var(--text); font-weight: 500; }
.summary-main { padding-bottom: 16px; border-bottom: 1px solid var(--line); }
.summary-subtitle { margin: 0 0 12px; font-size: 12px; font-weight: 600; }
.format-row, .genre-row, .year-row { display: grid; align-items: center; gap: 8px; margin-top: 10px; font-size: 12px; }
.format-row { grid-template-columns: 45px minmax(0, 1fr) 44px; }
.genre-row { grid-template-columns: minmax(0, 1fr) 1fr 34px; }
.year-row { grid-template-columns: 42px minmax(0, 1fr) 34px; }
.genre-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ranking-list { display: grid; gap: 7px; margin: 0; padding: 0; list-style: none; font-size: 12px; }
.ranking-row { display: grid; grid-template-columns: 2.3ch minmax(0, 1fr) auto; gap: 8px; align-items: baseline; min-height: 22px; line-height: 1.4; }
.ranking-place { color: var(--muted); font-variant-numeric: tabular-nums; }
.ranking-name { overflow-wrap: anywhere; }
.artist-ranking .ranking-row { grid-template-columns: 2.3ch minmax(0, 1fr) minmax(16px, .5fr) minmax(3ch, auto); }
.artist-ranking .format-bar { height: 8px; align-self: center; background: transparent; }
.format-count, .ranking-value { color: var(--muted); text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
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
.year-chart { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 4px; height: 180px; margin-top: 18px; }
.year-chart-item { display: grid; grid-template-rows: minmax(0, 1fr) 38px; min-width: 0; }
.year-chart-column { display: flex; flex-direction: column; align-items: center; justify-content: flex-end; border-bottom: 1px solid var(--line); }
.year-chart-bar { width: min(28px, 68%); height: max(6px, var(--bar-height)); border-radius: 0; background: var(--accent); }
.year-chart-item:hover .year-chart-bar { background: var(--accent-strong); }
.year-chart-label { padding-top: 6px; color: var(--muted); font-size: 12px; line-height: 1.2; text-align: center; }
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
.music-section { scroll-margin-top: 24px; }
.music-summary { margin: 4px 0 0; color: #e2dbf4; font-size: 14px; font-variant-numeric: tabular-nums; }
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
.page-search input { width: 100%; height: 52px; padding: 0 20px 0 50px; border-color: transparent; background: #ffffff17; font-size: 14px; transition: background .15s, border-color .15s; }
.page-search input:hover, .page-search input:focus { background: #ffffff28; }
.page-search input:focus-visible { outline: 2px solid #fff; outline-offset: -2px; }
.track-search input::placeholder { color: var(--muted); }
.page-search .search-placeholder { left: 50px; max-width: calc(100% - 90px); font-size: 14px; }
.search-icon { position: absolute; z-index: 1; left: 18px; top: 50%; width: 20px; height: 20px; transform: translateY(-50%); color: var(--muted); pointer-events: none; }
.page-search:focus-within .search-icon { color: var(--text); }
.topbar-search input { height: var(--topbar-height); padding: 0 16px 0 44px; font-size: 14px; }
.topbar-search input:hover, .topbar-search input:focus { background: #303030; }
.topbar-search input:focus-visible { outline-offset: -2px; }
.topbar-search .search-icon { left: 15px; }
.topbar-search .search-placeholder { left: 44px; max-width: calc(100% - 60px); font-size: 14px; }
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
.operation-status { margin-bottom: 12px; color: var(--muted); font-size: 12px; line-height: 20px; overflow-wrap: anywhere; }
.operation-status:empty { margin-bottom: 0; }
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
#duplicates .music-summary { color: #dceff5; }
:is(#musicSection, #duplicates) :is(.music-genre:not([aria-pressed="true"]), .duplicate-toolbar select, .duplicate-toolbar .web-select-trigger) {
  background-color: #ffffff17;
}
:is(#musicSection, #duplicates) :is(.music-genre:not([aria-pressed="true"]), .duplicate-toolbar select, .duplicate-toolbar .web-select-trigger):hover,
#duplicates .duplicate-toolbar .web-select-trigger[aria-expanded="true"] {
  background-color: #ffffff28;
}
.music-list { width: 100%; border-collapse: separate; border-spacing: 0; table-layout: fixed; }
.music-list th, .music-list td { text-align: left; padding: 7px 12px; }
.music-list thead th { position: relative; padding-block: 9px 18px; color: var(--muted); font-size: 13px; font-weight: 500; }
.music-list thead th::after { position: absolute; inset-inline: 0; bottom: 8px; height: 1px; background: var(--line); content: ""; pointer-events: none; }
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
.music-track-row .music-track-number { position: relative; }
.music-track-select { position: absolute; inset: 50% auto auto 50%; transform: translate(-50%, -50%); width: 16px; height: 16px; min-height: 0; margin: 0; padding: 0; opacity: 0; accent-color: var(--accent); cursor: pointer; }
.music-card > .music-track-row { user-select: none; }
.music-track-row:is(:hover, :has(.music-track-select:is(:focus-visible, :checked))) .music-track-select { opacity: 1; }
.music-track-row:is(:hover, :has(.music-track-select:is(:focus-visible, :checked))) .music-track-index { visibility: hidden; }
@media (hover: none) {
  .music-track-row .music-track-select { opacity: 1; }
  .music-track-row .music-track-index { visibility: hidden; }
}
.track-selection-bar { position: sticky; top: 0; z-index: 3; display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin-bottom: 8px; padding: 8px 12px; border-radius: var(--radius-small); background: var(--panel-solid); }
.track-selection-bar [role="status"] { margin-inline-end: auto; font-size: 13px; font-weight: 700; }
.music-list :is(.music-track-artist, .music-track-album) { width: 23%; color: var(--muted); font-size: 13px; }
.music-list .music-track-duration { width: 78px; text-align: right; color: var(--muted); font-size: 13px; font-variant-numeric: tabular-nums; white-space: nowrap; }
.music-track-duration svg { width: 16px; height: 16px; vertical-align: middle; }
.music-list .music-track-control { width: 82px; text-align: center; padding-inline: 4px; }
.music-track-actions { display: flex; justify-content: flex-end; gap: 2px; }
.music-track-row:hover > *, .music-track-row:focus-within > *, .music-card.is-current-track > .music-track-row > * { background: #ffffff0b; }
.music-track-row > :first-child { border-radius: var(--radius-small) 0 0 var(--radius-small); }
.music-track-row > :last-child { border-radius: 0 var(--radius-small) var(--radius-small) 0; }
.music-card:has(> .music-track-details:not([hidden])) > .music-track-row > * { background: var(--panel); border-bottom-left-radius: 0; border-bottom-right-radius: 0; }
.music-card > .music-track-row:has(.music-track-select:checked) > * { background: #ffffff20; }
.music-track-name { display: flex; align-items: center; gap: 12px; min-width: 0; }
.music-track-text { min-width: 0; }
.music-track-row .music-title, .music-track-artist, .music-track-album, .music-track-artist-mobile, .music-track-album-mobile { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.music-track-artist-mobile, .music-track-album-mobile { display: none; color: var(--muted); font-size: 12px; font-weight: 400; }
.music-play, .music-details-toggle, .music-track-menu-button { display: inline-grid; place-items: center; padding: 0; border: 0; background: transparent; color: var(--muted); }
.music-play { position: relative; flex: 0 0 40px; border-radius: 5px; }
.music-play .music-cover { width: 40px; height: 40px; border-radius: inherit; }
.music-play .empty-cover-icon { width: 18px; height: 18px; }
.music-play-icons { position: absolute; inset: 0; display: grid; place-items: center; border-radius: inherit; background: #0009; color: #fff; opacity: 0; transition: opacity .15s; }
.music-play-icons svg { width: 17px; height: 17px; }
.music-track-row:hover .music-play-icons, .music-play:focus-visible .music-play-icons, .is-playing-track .music-play-icons { opacity: 1; }
.music-play .music-pause-icon, .is-playing-track .music-play .music-play-icon { display: none; }
.is-playing-track .music-play .music-pause-icon { display: block; }
.music-details-toggle, .music-track-menu-button { flex-shrink: 0; width: 36px; height: 36px; border-radius: 50%; }
.music-details-toggle:hover, .music-details-toggle[aria-expanded="true"], .music-track-menu-button:hover, .music-track-menu-button[aria-expanded="true"] { background: #ffffff0e; color: var(--text); }
.music-track-actions button:focus-visible { outline-offset: -2px; }
.music-details-toggle .group-chevron { width: 18px; height: 18px; }
.music-details-toggle[aria-expanded="true"] .group-chevron { transform: rotate(180deg); }
.playlist-unavailable .music-cover { flex: 0 0 40px; width: 40px; height: 40px; border-radius: 5px; }
.hero-layout.playlist-hero { align-items: flex-end; }
.playlist-kind { display: block; margin-bottom: 6px; font-size: 13px; font-weight: 700; }
#playlistTitle { font-size: clamp(30px, 5.4vw, 84px); overflow-wrap: anywhere; }
.playlist-hero .music-summary { margin-top: 12px; color: var(--muted); }
.page-actions { position: relative; z-index: 2; width: max-content; margin-bottom: 12px; }
.page-actions > summary { display: grid; place-items: center; width: 40px; height: 40px; border-radius: 50%; color: var(--muted); list-style: none; cursor: pointer; }
.page-actions > summary::-webkit-details-marker { display: none; }
.page-actions > summary:hover, .page-actions[open] > summary { color: var(--text); background: #ffffff12; }
.page-actions-panel { left: 0; right: auto; width: max-content; min-width: 184px; max-width: calc(100vw - 48px); }
.playlist-cover-button { position: relative; display: block; flex-shrink: 0; width: clamp(112px, 16vw, 224px); aspect-ratio: 1; padding: 0; overflow: hidden; border: 0; border-radius: var(--radius-small); color: var(--text); background: #282828; box-shadow: 0 8px 24px #0005; }
.playlist-cover-frame, .playlist-cover-frame .playlist-art { display: grid; width: 100%; height: 100%; }
.playlist-cover-frame .playlist-art { font-size: clamp(18px, 3.2vw, 52px); }
.playlist-cover-action { position: absolute; inset: 0; display: grid; place-items: center; border-radius: inherit; background: #000a; opacity: 0; font-size: 14px; font-weight: 750; }
.playlist-cover-button:hover .playlist-cover-action, .playlist-cover-button:focus-visible .playlist-cover-action { opacity: 1; }
.playlist-art { position: relative; display: grid; place-items: center; aspect-ratio: 1; overflow: hidden; border-radius: 5px; color: #aaa; background: #282828; }
.playlist-art svg { width: 28%; height: 28%; min-width: 18px; min-height: 18px; }
.playlist-art[data-tiles="2"] { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.playlist-art[data-tiles="3"], .playlist-art[data-tiles="4"] { grid-template: repeat(2, minmax(0, 1fr)) / repeat(2, minmax(0, 1fr)); }
.playlist-art[data-tiles="3"] .playlist-art-tile:first-child { grid-row: span 2; }
.playlist-art-tile { position: relative; display: grid; place-items: center; align-self: stretch; justify-self: stretch; min-width: 0; overflow: hidden; color: #fff; font-weight: 750; }
.playlist-art img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
.playlist-dialog { width: min(400px, calc(100vw - 32px)); padding: 24px; border: 0; border-radius: var(--radius); color: var(--text); background: #202020; box-shadow: 0 24px 80px #0008; }
.playlist-dialog::backdrop { background: #000b; }
.playlist-dialog form { display: grid; gap: 12px; }
.playlist-dialog h2 { margin: 0 0 4px; font-size: 20px; }
.playlist-dialog input { background: #303030; }
.playlist-dialog input:focus-visible { outline: none; background: #414141; }
#playlistCreateError:empty, #playlistDeleteError:empty { display: none; }
#playlistDeleteName { margin: 0; overflow-wrap: anywhere; }
.playlist-dialog-actions { display: flex; justify-content: flex-end; gap: 8px; }
.playlist-dialog-actions button[type="submit"] { color: #0b301c; background: var(--accent); font-weight: 700; }
.playlist-dialog-actions button[type="submit"]:hover { background: var(--accent-strong); }
.playlist-dialog-actions .playlist-delete-confirm[type="submit"] { color: #39111b; background: var(--bad); }
.playlist-dialog-actions .playlist-delete-confirm[type="submit"]:hover { background: #ffb4be; }
.playlist-track-menu { position: fixed; z-index: 100; width: min(270px, calc(100vw - 16px)); max-height: calc(100dvh - 16px); overflow: auto; }
#trackPlaylistPicker { padding: 6px 0 0; }
#trackPlaylistOptions { max-height: min(232px, 40dvh); overflow: auto; padding-top: 3px; }
#trackPlaylistOptions button { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
#trackPlaylistOptions .playlist-hint { padding: 8px; }
.playlist-status { position: fixed; left: 50%; bottom: calc(14px + var(--player-height, 0px)); z-index: 101; display: flex; align-items: center; gap: 12px; width: max-content; max-width: min(460px, calc(100vw - 32px)); margin: 0; padding: 8px 16px; border-radius: var(--radius-tile); transform: translateX(-50%); color: var(--text); background: var(--soft); box-shadow: 0 8px 24px #0008; font-size: 13px; font-weight: 650; overflow-wrap: anywhere; }
.playlist-status button.small { flex-shrink: 0; min-height: 30px; padding: 4px 10px; }
#playerBackupFile::file-selector-button { margin-inline-end: 8px; padding: 4px 10px; border: 0; border-radius: 999px; color: var(--text); background: var(--soft); font: inherit; cursor: pointer; }
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
body.has-player .app-shell { --player-offset: var(--player-height, 88px); }
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
.global-skip, .global-mode { display: grid; place-items: center; width: 28px; height: 28px; padding: 0; border: 0; border-radius: 50%; color: #b3b3b3; background: transparent; }
.global-skip svg { width: 20px; height: 20px; fill: currentColor; }
.global-skip:hover:not(:disabled), .global-mode:hover { color: #fff; }
.global-mode { position: relative; }
.global-mode svg { width: 17px; height: 17px; }
.global-mode[aria-pressed="true"] { color: var(--accent); }
.global-mode[aria-pressed="true"]::after { position: absolute; bottom: -1px; width: 4px; height: 4px; border-radius: 50%; background: currentColor; content: ""; }
.global-timeline { display: grid; grid-template-columns: 38px minmax(0, 1fr) 38px; align-items: center; gap: 8px; width: 100%; }
.global-timeline .audio-time:first-child { text-align: right; }
.global-extras { display: flex; justify-content: flex-end; align-items: center; gap: 8px; }
.global-volume { width: 90px; }
.global-extra-button { display: grid; place-items: center; flex: 0 0 32px; width: 32px; height: 32px; padding: 0; border: 0; border-radius: 50%; color: var(--muted); background: transparent; }
.global-extra-button svg { width: 18px; height: 18px; }
.global-extra-button:hover { color: var(--text); background: #ffffff16; }
.queue-toggle[aria-expanded="true"] { color: var(--accent); }
.global-status { grid-column: 1 / -1; margin: 0; text-align: center; }
.playback-panel { position: fixed; inset: calc(var(--topbar-height) + 2 * var(--panel-gap)) var(--panel-gap) calc(var(--panel-gap) + var(--player-offset)) auto; z-index: 21; display: flex; flex-direction: column; width: min(360px, calc(100% - 2 * var(--panel-gap))); min-height: 0; padding: var(--panel-scroll-inset); border-radius: var(--radius); background: var(--panel-solid); box-shadow: 0 8px 32px #0008; }
.playback-panel-header { display: flex; gap: 4px; justify-content: space-between; align-items: center; padding: 0 4px 8px; }
.playback-tabs { display: flex; gap: 16px; }
.playback-tabs button { padding: 8px 0; border: 0; border-bottom: 2px solid transparent; color: var(--muted); background: transparent; font-size: 13px; font-weight: 750; white-space: nowrap; }
.playback-tabs button:hover, .playback-tabs button[aria-selected="true"] { color: var(--text); }
.playback-tabs button[aria-selected="true"] { border-bottom-color: var(--accent); }
.playback-panel-icon { display: grid; place-items: center; flex: 0 0 28px; width: 28px; height: 28px; padding: 0; border: 0; border-radius: 50%; color: var(--muted); background: transparent; }
.playback-panel-icon svg { width: 16px; height: 16px; }
.playback-panel-icon:hover { color: var(--text); background: #ffffff16; }
.playback-panel-reorder { cursor: grab; flex-basis: 24px; width: 24px; }
.playback-panel-reorder:active { cursor: grabbing; }
.playback-panel-row.queue-drop-target { background: #ffffff14; box-shadow: inset 0 2px var(--accent); }
.playback-panel-view { min-height: 0; padding: 4px 2px 6px; overflow-y: auto; overscroll-behavior: contain; scrollbar-gutter: stable; }
.playback-panel-view section + section { margin-top: 16px; }
.playback-panel-view h2 { margin: 0 0 6px 4px; color: var(--text); font-size: 14px; }
.playback-panel-view ul { display: grid; gap: 2px; margin: 0; padding: 0; list-style: none; }
.playback-panel-row { display: flex; align-items: center; min-width: 0; padding-right: 4px; border-radius: var(--radius-small); }
.playback-panel-row:has(button:not(:disabled):hover), .playback-panel-row:focus-within { background: #ffffff0e; }
.playback-panel-track { display: flex; align-items: center; gap: 10px; flex: 1 1 auto; min-width: 0; padding: 5px 4px; border: 0; border-radius: var(--radius-small); color: var(--text); background: transparent; text-align: left; }
.playback-panel-track:disabled { cursor: default; opacity: 1; }
.playback-panel-track:focus-visible, .playback-panel-view:focus-visible { outline-offset: -2px; }
.playback-panel-art { position: relative; display: grid; place-items: center; flex: 0 0 44px; width: 44px; height: 44px; overflow: hidden; border-radius: 5px; color: var(--muted); background: var(--soft); }
.playback-panel-art svg { width: 16px; height: 16px; }
.playback-panel-art img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
.playback-panel-track-text { display: grid; min-width: 0; gap: 1px; }
.playback-panel-track-text > * { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.playback-panel-track-text strong { font-size: 14px; font-weight: 700; }
.playback-panel-row.is-current strong { color: var(--accent); }
.playback-panel-track-text small, .playback-panel-track-text time, .playback-panel-note { color: var(--muted); font-size: 12px; }
.playback-panel-note { margin: 8px 4px; }
.playback-panel-more.small { margin: 8px 4px 0; font-size: 12px; }
@media (min-width: 1120px) {
  .app-shell:has(.playback-panel:not([hidden])) { grid-template-columns: var(--sidebar-width) minmax(0, 1fr) var(--queue-width); }
  .playback-panel { position: relative; inset: auto; grid-column: 3; grid-row: 2; width: auto; box-shadow: none; }
}
@media (max-width: 760px) {
  .global-player { grid-template-columns: minmax(0, 1fr) auto; gap: 8px 16px; padding: 10px 16px; }
  .global-cover { width: 40px; height: 40px; flex-basis: 40px; }
  .global-controls { display: contents; }
  .global-transport { grid-column: 2; grid-row: 1; gap: 8px; }
  .global-timeline { grid-column: 1 / -1; grid-row: 2; }
  .global-extras { grid-column: 1 / -1; grid-row: 3; }
  .global-extras #globalLyrics { margin-right: auto; }
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
#duplicates .page-search { margin-bottom: 8px; }
.duplicate-toolbar :is(select, .web-select-trigger) { height: 38px; }
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
.lyrics-dialog .window-close { position: absolute; top: 12px; right: 12px; }
.lyrics-toolbar { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; padding: 0 32px 18px; }
.lyrics-toolbar .small { min-height: 32px; padding: 5px 12px; color: #c2c2c2; background: #303030; font-size: 12px; }
.lyrics-toolbar .small[aria-pressed="true"] { color: #c4e5cf; background: #2c4234; }
#lyricsFollow { min-width: 148px; }
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
.lyrics-text.is-synced .lyrics-line:is(.is-current, .is-played) { color: #f5fff8; }
.lyrics-section { margin: 24px 0 12px; color: #a8cab4; font-size: 12px; font-weight: 600; letter-spacing: .03em; }
.lyrics-text > :first-child { margin-top: 0; }
.lyrics-text.is-raw { color: #b9b9b9; font-family: Consolas, "Courier New", monospace; font-size: 14px; font-weight: 400; line-height: 1.65; white-space: pre-wrap; }
.lyrics-text.loading, .lyrics-text.error { color: var(--muted); font-size: 14px; }
.source-dialog { width: min(720px, calc(100vw - 32px)); max-height: calc(100vh - 40px); margin: auto; padding: 0; overflow: auto; border: 0; border-radius: var(--radius); color: var(--text); background: #202020; box-shadow: 0 24px 80px #0008; }
.source-dialog[open] { display: flex; flex-direction: column; overflow: hidden; }
.source-dialog::backdrop { background: #000b; }
.source-dialog-head { display: flex; flex-shrink: 0; align-items: center; justify-content: space-between; gap: 12px; padding: 24px; }
.source-dialog-head h2 { margin: 0; font-size: 20px; }
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
@media (min-width: 1700px) { .app-workspace { --page-padding: 40px; } }
@container overview (max-width: 1140px) {
  .analysis-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}
@container overview (max-width: 820px) {
  .analysis-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .analysis-grid > .summary-panel { grid-column: 1 / -1; }
}
@container overview (max-width: 490px) {
  .analysis-grid { grid-template-columns: 1fr; }
}
@media (max-width: 1450px) {
  .donut-layout { grid-template-columns: 160px minmax(0, 1fr); align-items: center; }
  .toolbar { grid-template-columns: repeat(4, minmax(0, 1fr)); }
  .summary { grid-template-columns: repeat(4, minmax(0, 1fr)); }
}
@media (max-width: 1050px) {
  .app-shell { --sidebar-default-width: 200px; }
  .app-brand { gap: 8px; padding-left: 4px; }
  .app-workspace { --page-padding: 24px; }
  .collection-art { flex-basis: 104px; height: 104px; } .collection-art svg { width: 56px; height: 56px; }
  .hero-layout { gap: 18px; }
  .donut-layout { grid-template-columns: 1fr; }
  .toolbar { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (min-width: 761px) {
  .app-shell { height: calc(100dvh - var(--player-offset)); grid-template-rows: var(--topbar-height) minmax(0, 1fr); }
  .app-workspace { display: grid; grid-row: 2; grid-template-rows: minmax(0, 1fr); min-height: 0; overflow: hidden; }
  .workspace-scroll { min-width: 0; min-height: 0; margin-inline: var(--panel-scroll-inset); overflow: auto; overscroll-behavior-y: contain; scroll-padding-top: 24px; scrollbar-gutter: stable both-edges; }
  .workspace-scroll::-webkit-scrollbar-track { margin-block: clamp(12px, 10vh, 58px) var(--panel-scroll-inset); }
  .workspace-scroll .page { padding-inline: calc(var(--page-padding) - var(--panel-scroll-inset) - var(--scrollbar-size)); }
  .app-shell.is-sidebar-collapsed { --sidebar-width: 72px; }
  .is-sidebar-collapsed .app-sidebar { padding-top: 16px; }
  .is-sidebar-collapsed .app-sidebar-header { margin-bottom: 16px; }
  .is-sidebar-collapsed .sidebar-toggle { width: 100%; height: 44px; }
  .is-sidebar-collapsed :is(.app-brand, .nav-caption, .side-nav a span, .sidebar-playlists-heading, .playlist-search-row, #playlistNavigationEmpty, .playlist-nav-title) { display: none; }
  .is-sidebar-collapsed .side-nav a { justify-content: center; padding-inline: 0; }
  .is-sidebar-collapsed .sidebar-playlists { gap: 0; margin-top: 12px; }
  .is-sidebar-collapsed #playlistNavigation { margin-inline: 0; }
  .is-sidebar-collapsed #playlistNavigation a { justify-content: center; gap: 0; min-height: 46px; padding: 3px 0; }
  .is-sidebar-collapsed #playlistNavigation .playlist-art { flex-basis: 40px; width: 40px; }
}
@media (max-width: 760px) {
  .app-shell { --topbar-height: 44px; display: block; padding: 0; }
  .app-topbar { grid-template-columns: minmax(0, 1fr) auto; padding: 8px 12px 4px; }
  .topbar-search-area { grid-column: 1; }
  .topbar-settings { grid-column: 2; }
  .app-sidebar { position: relative; top: auto; left: auto; bottom: auto; flex-direction: row; align-items: center; flex-wrap: wrap; gap: 8px; width: auto; height: auto; min-height: 0; padding: 14px 16px 10px; overflow: visible; contain: none; border-radius: 0; }
  .app-sidebar-header { margin-bottom: 0; }
  .sidebar-toggle { display: none; }
  .app-brand { padding: 0; gap: 8px; } .app-brand strong { font-size: 14px; } .app-brand small { display: none; }
  .brand-mark { width: 28px; height: 28px; } .brand-icon { width: 19px; height: 19px; }
  .side-nav { display: flex; flex: 1 0 100%; gap: 4px; order: 2; }
  .sidebar-playlists { flex: 1 0 100%; order: 3; margin-top: 4px; }
  #playlistNavigation { max-height: 126px; overflow: auto; }
  .playlist-cover-button { width: clamp(80px, 26vw, 146px); }
  .side-nav a { justify-content: center; flex: 1; gap: 7px; min-height: 38px; padding: 8px 6px; font-size: 12px; }
  .nav-icon { width: 16px; height: 16px; }
  .nav-caption { display: none; }
  .app-workspace { margin-bottom: var(--panel-gap); overflow: clip; border-radius: 0 0 var(--radius) var(--radius); }
  .page { padding: 0 20px 40px; } .header { padding-block: 24px 16px; }
  .hero-layout { align-items: start; } .collection-art { flex-basis: 80px; height: 80px; } .collection-art svg { width: 44px; height: 44px; }
  h1 { font-size: 34px; }
  .metric { padding: 12px 10px; } .metric strong { font-size: 24px; }
  .summary { gap: 6px; margin-top: 20px; }
  .metric-label { font-size: 12px; }
  .music-card-content { grid-template-columns: 80px minmax(0, 1fr); gap: 14px; } .music-cover { width: 80px; }
  .duplicate-track { padding: 14px 40px 14px 14px; } .music-trash-icon { right: 8px; top: 10px; }
  .music-actions .small { min-height: 36px; }
}
@media (max-width: 520px) {
  .side-nav { min-width: 0; width: 100%; }
  .side-nav a { flex: 1 1 0; min-width: 0; flex-direction: column; gap: 4px; font-size: 12px; }
  .side-nav a span { white-space: nowrap; }
  .page { padding-inline: 16px; }
  .hero-layout { gap: 12px; } .collection-art { flex-basis: 64px; height: 64px; } .collection-art svg { width: 36px; height: 36px; }
  h1 { font-size: 28px; letter-spacing: -.4px; }
  .summary { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .panel { padding: 18px; } .donut-layout { grid-template-columns: 1fr; gap: 16px; }
  .music-card-content { grid-template-columns: 1fr; } .music-cover { width: 104px; }
  .group-header { gap: 10px; padding: 12px; }
  .group-status { display: none; }
  .group-body { padding: 12px; }
  .lyrics-dialog-head { padding: 20px 60px 14px 20px; } .lyrics-dialog-title { font-size: 24px; }
  .lyrics-toolbar { padding: 0 20px 14px; }
  .lyrics-text { padding: 4px 12px 16px 20px; font-size: 20px; }
}
@media (max-width: 680px) {
  .app-workspace:has(.report-view:not([hidden])) { background-size: 100% 760px; }
  .toolbar > .web-select, .toolbar > select { flex: 1 1 140px; width: auto; }
  .music-list :is(.music-track-artist, .music-track-album) { display: none; }
  :is(.music-track-artist-mobile, .music-track-album-mobile):not(:empty) { display: block; }
  .music-list th, .music-list td { padding-inline: 6px; }
  .music-list .music-track-number { width: 40px; }
  .music-list .music-track-duration { width: 52px; }
  .music-list .music-track-control { width: 68px; }
  .music-track-actions button { width: 29px; height: 32px; }
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
