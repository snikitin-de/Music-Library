"""One embedded stylesheet for the standalone music library report."""

import base64
from pathlib import Path

_FONT_DATA = base64.b64encode((Path(__file__).parent / "assets" / "InterVariable.woff2").read_bytes()).decode("ascii")
_FONT_FACE = '@font-face{font-family:"Library Inter";font-style:normal;font-weight:100 900;font-display:swap;src:url(data:font/woff2;base64,' + _FONT_DATA + ') format("woff2");}\n'

REPORT_CSS = _FONT_FACE + r"""
:root {
  color-scheme: dark;
  --bg: #000; --panel: #181818; --panel-solid: #121212; --soft: #242424;
  --text: #f5f5f5; --muted: #a7a7a7; --line: #303030;
  --good: #2bcf70; --bad: #ff9caa; --accent: #2bcf70;
  --accent-strong: #4cdd8c; --warning: #f0c674; --radius: 8px;
}
* { box-sizing: border-box; }
html { scroll-behavior: auto; scroll-padding-top: 24px; }
body { margin: 0; min-width: 320px; color: var(--text); background: var(--bg); font: 14px/1.5 "Library Inter", Arial, sans-serif; -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; text-rendering: optimizeLegibility; font-kerning: normal; }
::selection { color: #000; background: var(--accent); }
button, input, select { font: inherit; -webkit-font-smoothing: inherit; text-rendering: inherit; background-clip: padding-box; }
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
.app-brand small { color: var(--muted); font-size: 11px; }
.nav-caption { margin: 14px 12px 8px; color: var(--muted); font-size: 11px; font-weight: 600; letter-spacing: 1px; text-transform: uppercase; }
.side-nav { display: grid; gap: 4px; }
.side-nav a { display: flex; align-items: center; gap: 14px; min-height: 46px; padding: 10px 14px; border-radius: 4px; color: var(--muted); font-weight: 600; text-decoration: none; transition: color .15s, background .15s; }
.side-nav a:hover { color: #fff; background: #1c1c1c; }
.side-nav a.active { color: #fff; background: #282828; }
.side-nav a.active .nav-icon { color: var(--accent); }
.sidebar-source { margin: 24px 12px 0; padding-top: 18px; border-top: 1px solid var(--line); }
.sidebar-source>span { color: var(--muted); font-size: 11px; }
.sidebar-source p { margin: 8px 0 0; overflow: hidden; color: #c5c5c5; font-size: 11px; line-height: 1.6; text-overflow: ellipsis; white-space: nowrap; }
.sidebar-note { display: flex; align-items: flex-start; gap: 10px; margin: auto 8px 0; padding: 14px 4px 0; border-top: 1px solid var(--line); }
.status-dot { flex: 0 0 7px; height: 7px; margin-top: 6px; border-radius: 50%; background: var(--accent); }
.sidebar-note div { display: grid; gap: 3px; }
.sidebar-note strong { font-size: 12px; font-weight: 600; }
.sidebar-note small { color: var(--muted); font-size: 11px; }
.sidebar-note.mode-real .status-dot { background: var(--warning); }
.sidebar-note.mode-real strong { color: var(--warning); }
.app-workspace { grid-column: 2; min-width: 0; min-height: calc(100vh - 16px); border-radius: var(--radius); background: var(--panel-solid); }
.page { width: 100%; max-width: 1800px; margin: 0 auto; padding: 0 32px 56px; }
.header { margin: 0 -32px; padding: 32px 32px 24px; border-radius: var(--radius) var(--radius) 0 0; background: linear-gradient(180deg, #27382e 0, #1d2922 48%, #121212 100%); }
.hero-layout { display: flex; align-items: center; gap: 24px; min-width: 0; }
.collection-art { display: grid; place-items: center; flex: 0 0 140px; height: 140px; border-radius: 4px; background: var(--accent); color: #0b301c; box-shadow: 0 8px 24px #0004; }
.collection-art svg { width: 72px; height: 72px; stroke-width: 1.6; }
.hero-copy { min-width: 0; }
.hero-kicker { margin-bottom: 4px; font-size: 12px; font-weight: 600; }
h1 { margin: 0; font-size: clamp(32px, 4.5vw, 64px); font-weight: 700; letter-spacing: -1.4px; line-height: 1.15; }
.hero-lead { margin: 10px 0 0; color: #c7ceca; font-size: 13px; }
.summary { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 8px; margin-top: 28px; }
.metric { position: relative; min-width: 0; padding: 14px 12px; border-radius: 4px; background: #ffffff0a; }
.metric strong { display: block; margin-top: 8px; font-size: 26px; font-weight: 700; letter-spacing: -.6px; line-height: 1; font-variant-numeric: tabular-nums; }
.metric-label { display: block; color: #b3b3b3; font-size: 11px; }
.metric-icon { display: none; }
.metric-primary strong { color: var(--accent); }
.section-heading { display: flex; justify-content: space-between; align-items: end; gap: 16px; margin-top: 22px; }
.section-heading span { color: var(--muted); font-size: 11px; }
.section-heading h2, .section-title { margin: 0; font-size: 24px; font-weight: 700; letter-spacing: -.6px; line-height: 1.3; }
.section-heading p { margin: 0; color: var(--muted); font-size: 12px; }
.analysis-grid { display: grid; grid-template-columns: 1.1fr 1fr 1fr 1fr; gap: 12px; margin-top: 16px; align-items: stretch; }
.panel { min-width: 0; padding: 20px; border-radius: var(--radius); background: var(--panel); }
.panel h2 { margin: 0; font-size: 16px; font-weight: 650; letter-spacing: -.2px; }
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
.format-bar { height: 4px; overflow: hidden; border-radius: 2px; background: #343434; }
.format-bar span { display: block; height: 100%; border-radius: inherit; background: var(--accent); }
.donut-layout { display: grid; justify-items: center; gap: 18px; }
.donut-chart { position: relative; display: grid; place-items: center; width: 140px; aspect-ratio: 1; }
.donut-svg { position: absolute; inset: 0; width: 100%; height: 100%; overflow: visible; shape-rendering: geometricPrecision; }
.donut-segment { stroke-linecap: butt; }
.donut-canvas { position: absolute; inset: 0; display: block; width: 100%; height: 100%; image-rendering: auto; }
.donut-hole { position: relative; display: grid; place-items: center; align-content: center; width: 70px; aspect-ratio: 1; border-radius: 50%; background: var(--panel); text-align: center; }
.donut-hole strong { font-size: 22px; line-height: 1; }
.donut-hole span { max-width: 68px; margin-top: 4px; overflow: hidden; color: var(--muted); font-size: 10px; text-overflow: ellipsis; white-space: nowrap; }
.chart-legend { display: grid; gap: 7px; width: 100%; min-width: 0; max-height: 178px; padding-right: 12px; overflow-y: auto; scrollbar-width: thin; scrollbar-gutter: stable; }
.chart-legend-row { display: grid; grid-template-columns: 7px minmax(0, 1fr) 32px 38px; gap: 6px; align-items: center; font-size: 11px; font-variant-numeric: tabular-nums; }
.chart-dot { width: 7px; height: 7px; border-radius: 50%; }
.chart-label { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.chart-legend-row strong, .chart-legend-row span:last-child { text-align: right; font-weight: 400; }
.chart-legend-row span:last-child { color: var(--muted); }
.chart-note { margin: 0 0 14px; }
.year-chart { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 8px; height: 180px; margin-top: 18px; }
.year-chart-item { display: grid; grid-template-rows: minmax(0, 1fr) 28px; min-width: 0; }
.year-chart-column { display: flex; flex-direction: column; align-items: center; justify-content: flex-end; border-bottom: 1px solid var(--line); }
.year-chart-bar { width: min(28px, 68%); height: max(6px, var(--bar-height)); border-radius: 3px 3px 0 0; background: var(--accent); }
.year-chart-item:hover .year-chart-bar { background: var(--accent-strong); }
.year-chart-label { padding-top: 8px; color: var(--muted); font-size: 10px; text-align: center; white-space: nowrap; }
.year-chart-value { margin-bottom: 6px; font-size: 11px; font-variant-numeric: tabular-nums; }
.heatmap-panel { margin-top: 12px; }
.heatmap-heading { margin-bottom: 16px; }
.heatmap-heading p { margin: 4px 0 0; color: var(--muted); font-size: 12px; }
.heatmap-scroll { max-width: 100%; overflow-x: auto; scrollbar-width: thin; }
.heatmap-grid { display: grid; grid-template-columns: minmax(110px, .88fr) repeat(var(--heatmap-columns), minmax(80px, 1fr)); min-width: 640px; gap: 3px; }
.heatmap-row { display: contents; }
.heatmap-corner, .heatmap-column, .heatmap-genre, .heatmap-cell { display: flex; align-items: center; min-height: 32px; font-size: 12px; }
.heatmap-column { justify-content: center; color: var(--muted); }
.heatmap-genre { overflow: hidden; white-space: nowrap; }
.heatmap-cell { justify-content: center; border-radius: 3px; color: #f5fff8; font-variant-numeric: tabular-nums; }
.heatmap-scale { display: flex; justify-content: flex-end; align-items: center; gap: 10px; margin-top: 12px; color: var(--muted); font-size: 10px; }
.heatmap-scale-bar { width: 140px; height: 6px; border-radius: 3px; background: linear-gradient(90deg, #242424, #224d34, #297442, #2b7c48); }
.music-section { margin-top: 36px; scroll-margin-top: 24px; }
.duplicates-heading { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 14px; margin-bottom: 16px; }
.duplicates-actions { display: flex; flex-wrap: wrap; gap: 8px; }
input, select, button.small { min-width: 0; min-height: 38px; padding: 8px 14px; border: 1px solid #484848; border-radius: 999px; color: var(--text); background: transparent; }
button.small { display: inline-flex; align-items: center; justify-content: center; font-size: 13px; font-weight: 500; line-height: 1.4; }
button.small:hover:not(:disabled) { border-color: #b3b3b3; background: #ffffff0c; }
input, select { width: 100%; height: 42px; background: #242424; }
input:focus, select:focus { outline: 2px solid #fff; outline-offset: 1px; }
input::placeholder { color: transparent; }
select { appearance: none; padding-right: 42px; font-size: 12px; background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%23b3b3b3' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3C/svg%3E"); background-repeat: no-repeat; background-size: 16px 16px; background-position: right 16px center; }
.toolbar { display: grid; grid-template-columns: minmax(220px, 1.5fr) repeat(4, minmax(125px, 1fr)); gap: 8px; align-items: center; }
.search-control { position: relative; min-width: 0; }
.search-control input { height: 44px; padding-left: 16px; font-size: 13px; line-height: 20px; }
.search-placeholder { position: absolute; left: 17px; top: 50%; max-width: calc(100% - 40px); overflow: hidden; transform: translateY(-50%); color: var(--muted); font-size: 13px; line-height: 20px; white-space: nowrap; text-overflow: ellipsis; pointer-events: none; }
.search-control:not(.is-empty) .search-placeholder { display: none; }
.sort-control { min-width: 0; }
.web-select { position: relative; min-width: 0; }
.web-select-trigger { display: grid; grid-template-columns: minmax(0,1fr) 16px; align-items: center; gap: 12px; width: 100%; height: 44px; padding: 0 16px; border: 1px solid #484848; border-radius: 999px; color: var(--text); background: #242424; font-size: 13px; font-weight: 400; line-height: 20px; text-align: left; }
.web-select-trigger:hover { border-color: #888; background: #2b2b2b; }
.web-select-trigger[aria-expanded="true"] { border-color: #999; background: #303030; }
.web-select-label { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.web-select-trigger svg { display: block; width: 16px; height: 16px; fill: none; stroke: #b3b3b3; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }
.web-select-menu { position: fixed; inset: auto; z-index: 100; display: block; margin: 0; padding: 0; overflow: hidden; contain: paint; border: 1px solid #484848; border-radius: 12px; color: var(--text); background: #242424; box-shadow: 0 12px 40px #0009; }
.web-select-options { display: grid; align-content: start; gap: 2px; max-height: calc(var(--menu-height,300px) - 2px); padding: 6px; overflow-y: auto; overscroll-behavior: contain; scrollbar-gutter: stable; }
.web-select-options::-webkit-scrollbar { width: 6px; }
.web-select-options::-webkit-scrollbar-thumb { border-radius: 999px; background: #666; }
.web-select-options::-webkit-scrollbar-track { background: transparent; }
.web-select-options::-webkit-scrollbar-button { display: none; width: 0; height: 0; }
.web-select-option { min-height: 36px; padding: 8px 10px; overflow: hidden; border-radius: 6px; font-size: 13px; line-height: 20px; text-overflow: ellipsis; white-space: nowrap; cursor: pointer; }
.web-select-option.active { background: #3b3b3b; }
.web-select-option[aria-selected="true"] { color: var(--accent-strong); }
.web-select-option[aria-disabled="true"] { color: #777; cursor: not-allowed; }
.music-toolbar { margin: 16px 0; }
.music-operations { padding: 18px 20px; border-radius: var(--radius); background: var(--panel); }
.music-operation-groups { display: flex; flex-wrap: wrap; gap: 16px 32px; }
.music-operation-block { min-width: 0; }
.music-operations-title { margin: 0 0 10px; color: var(--muted); font-size: 11px; }
.music-operations-row { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
.mode-choice { display: inline-flex; align-items: center; gap: 7px; padding: 8px 12px; border: 1px solid #484848; border-radius: 999px; font-size: 12px; cursor: pointer; }
.mode-choice input { width: 13px; height: 13px; min-height: 0; margin: 0; accent-color: var(--accent); }
.mode-choice:has(input:checked) { border-color: var(--accent); color: var(--accent); background: #2bcf700a; }
.operation-status { margin-top: 16px; color: var(--muted); font-size: 11px; line-height: 1.6; overflow-wrap: anywhere; }
.music-section.collapsed .music-toolbar, .music-section.collapsed .music-list, .music-section.collapsed #musicEmpty { display: none; }
.music-list { display: grid; gap: 8px; }
.music-card { position: relative; min-width: 0; padding: 18px 54px 18px 18px; border: 1px solid transparent; border-radius: var(--radius); background: var(--panel); transition: background .15s; }
.music-card:hover { background: #202020; }
.music-card-content { display: grid; grid-template-columns: 112px minmax(0, 1fr); gap: 20px; align-items: start; }
.music-card-main { min-width: 0; }
.music-cover { display: grid; place-items: center; align-content: center; gap: 8px; width: 112px; aspect-ratio: 1; overflow: hidden; border-radius: 4px; background: #2a2a2a; color: var(--muted); }
.music-cover img { width: 100%; height: 100%; object-fit: cover; }
.empty-cover-icon { width: 32px; height: 32px; color: #888; }
.music-cover-empty strong { font-size: 10px; font-weight: 400; }
.music-title { font-size: 15px; font-weight: 600; overflow-wrap: anywhere; }
.music-path, .track-path { margin-top: 4px; color: var(--muted); font-size: 11px; overflow-wrap: anywhere; }
.music-actions { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 14px; }
.music-actions .small { min-height: 34px; padding: 6px 12px; font-size: 12px; }
.music-trash-icon { position: absolute; top: 16px; right: 14px; display: grid; place-items: center; width: 28px; height: 28px; padding: 0; border: 0; border-radius: 50%; color: var(--muted); background: transparent; }
.music-trash-icon:hover { color: var(--bad); background: #ffffff0c; }
.trash-svg { width: 17px; height: 17px; }
.music-card-duplicate { border-left: 3px solid var(--warning); }
.music-card-identity-mismatch { border-left: 3px solid #e8ab55; }
.music-card-unreadable { border-left: 3px solid var(--bad); }
.identity-warning { margin-top: 12px; padding: 10px 12px; border-radius: 4px; color: var(--warning); background: #f0c6740d; font-size: 12px; }
.identity-warning-icon { width: 16px; height: 16px; margin-right: 5px; }
.music-pills { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 12px; }
.music-pill { display: inline-flex; align-items: center; max-width: 100%; padding: 3px 8px; border: 1px solid #ffffff0c; border-radius: 999px; color: #ccc; background: #ffffff08; font-size: 11px; line-height: 1.5; overflow-wrap: anywhere; }
.music-pill-format { color: #f0b9c3; background: #38252b; font-weight: 700; }
.music-pill-bitrate { color: #b5d4fb; background: #223047; }
.music-pill-bit_depth { color: #d4c5f3; background: #30283e; }
.music-pill-sample_rate { color: #a8ded8; background: #1f3533; }
.music-pill-tags { color: #b5d2e5; background: #23333e; }
.music-pill-cover { color: #a5dcb6; background: #21392a; }
.music-pill-lyrics { color: #d8b5ef; background: #35263e; }
.music-pill-album { color: #f1d08c; background: #3a3221; }
.music-pill-albumartist, .music-pill-artist { color: #efbd98; background: #392b23; }
.music-pill-title { color: #b9dce7; background: #24343b; }
.music-pill-genre { color: #e9b7d5; background: #3a2633; }
.music-pill-year { color: #cdd3de; background: #30333b; }
.music-pill-status { color: var(--bad); background: #3c252a; }
.audio-player-wrap { margin-top: 12px; }
.audio-player { display: none; }
.custom-audio-player { display: grid; grid-template-columns: 32px 42px minmax(20px, 1fr) 32px; gap: 10px; align-items: center; width: 100%; min-height: 36px; }
.audio-play, .audio-mute { display: flex; align-items: center; justify-content: center; width: 32px; height: 32px; padding: 0; border: 0; border-radius: 50%; color: var(--text); background: transparent; line-height: 0; }
.audio-play { color: #000; background: #fff; }
.audio-play:hover { background: var(--accent); }
.audio-mute:hover { background: #ffffff16; }
.audio-play-icon { display: block; width: 16px; height: 16px; margin: 0; fill: currentColor; }
.audio-play.playing .audio-play-icon { display: none; }
.audio-play.playing::before { content: ""; width: 9px; height: 11px; background: linear-gradient(currentColor, currentColor) left/3px 11px no-repeat, linear-gradient(currentColor, currentColor) right/3px 11px no-repeat; }
.audio-time { color: var(--muted); font-size: 11px; font-variant-numeric: tabular-nums; }
.audio-seek-wrap { position: relative; display: flex; align-items: center; min-width: 0; height: 20px; }
.audio-seek-track { width: 100%; height: 4px; overflow: hidden; border-radius: 2px; background: #555; pointer-events: none; }
.audio-seek-fill { display: block; width: var(--audio-progress, 0%); height: 100%; background: #fff; }
.audio-seek-wrap:hover .audio-seek-fill { background: var(--accent); }
.audio-seek { position: absolute; inset: 0; width: 100%; height: 100%; min-height: 0; margin: 0; padding: 0; opacity: 0; cursor: pointer; }
.audio-seek-wrap:focus-within { outline: 2px solid #fff; outline-offset: 2px; border-radius: 4px; }
.audio-volume-icon { width: 17px; height: 17px; color: var(--muted); }
.audio-mute .audio-volume-off, .audio-mute.muted .audio-volume-on { display: none; }
.audio-mute.muted .audio-volume-off { display: block; }
.danger-button { color: var(--bad) !important; border-color: #72424b !important; }
.quarantine-one { color: #b9e2c7 !important; border-color: #41634d !important; }
.quarantine-panel { display: none; margin: 12px 0; padding: 16px; border: 1px solid #5b4548; border-radius: var(--radius); background: #241c1e; }
.quarantine-panel.visible { display: block; }
.quarantine-panel p { margin: 0; color: #ded2d5; font-size: 13px; overflow-wrap: anywhere; }
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
.group-card { margin-top: 8px; overflow: hidden; border: 1px solid var(--line); border-radius: var(--radius); background: var(--panel); }
.group-header { display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: center; gap: 16px; width: 100%; padding: 18px 20px; border: 0; color: var(--text); background: transparent; text-align: left; }
.group-header:hover { background: #ffffff08; }
.group-title { font-weight: 600; overflow-wrap: anywhere; }
.group-subtitle { margin-top: 4px; color: var(--muted); font-size: 12px; }
.badges { display: flex; flex-wrap: wrap; gap: 6px; }
.badge { padding: 3px 8px; border: 1px solid #555; border-radius: 3px; color: #ccc; font-size: 10px; font-weight: 600; }
.group-body { display: none; padding: 16px; border-top: 1px solid var(--line); }
.group-card.open .group-body { display: block; }
.comparison { display: grid; grid-template-columns: minmax(0, 1fr) 80px minmax(0, 1fr); gap: 12px; }
.comparison+.comparison { margin-top: 20px; padding-top: 20px; border-top: 1px solid var(--line); }
.track { display: flex; flex-direction: column; min-width: 0; padding: 16px; border: 1px solid #39463d; border-radius: 6px; background: #1c231f; }
.track.move { border-color: #4b383c; background: #241e20; }
.track-head { display: grid; grid-template-columns: 80px minmax(0, 1fr); gap: 14px; }
.music-cover.duplicate-cover { width: 80px; }
.track-meta { min-width: 0; }
.track-label { margin-bottom: 8px; color: #9ad8ae; font-size: 10px; font-weight: 600; }
.move .track-label { color: var(--bad); }
.track-title { font-size: 13px; font-weight: 600; overflow-wrap: anywhere; }
.quality-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; margin-top: 16px; }
.quality-grid div { min-width: 0; padding: 6px 0; border-bottom: 1px solid #ffffff0a; }
.quality-grid span { display: block; color: var(--muted); font-size: 10px; }
.quality-grid strong { display: block; margin-top: 2px; font-size: 12px; font-weight: 500; overflow-wrap: anywhere; }
.track-actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: auto; padding-top: 18px; }
.track-actions .small { flex: 1 1 auto; }
.divider { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px; color: var(--muted); font-size: 11px; text-align: center; }
.arrow span { display: block; width: 20px; height: 2px; background: #aaa; }
.arrow span::after { content: ""; display: block; width: 7px; height: 7px; margin-left: 13px; border-top: 2px solid #aaa; border-right: 2px solid #aaa; transform: translateY(-3px) rotate(45deg); }
.empty { display: none; margin-top: 12px; padding: 32px; border-radius: var(--radius); color: var(--muted); background: var(--panel); text-align: center; }
.empty.visible { display: block; }
.lyrics-modal { position: fixed; inset: 0; z-index: 50; display: none; align-items: center; justify-content: center; padding: 20px; background: #000b; }
.lyrics-modal.visible { display: flex; }
.lyrics-dialog { display: grid; grid-template-rows: auto minmax(0, 1fr); width: min(760px, 100%); max-height: 85vh; overflow: hidden; border: 1px solid #444; border-radius: 8px; background: #202020; box-shadow: 0 24px 80px #0008; }
.lyrics-dialog-head { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 16px; padding: 24px; border-bottom: 1px solid #383838; }
.lyrics-dialog-title { margin: 0; font-size: 20px; overflow-wrap: anywhere; }
.lyrics-dialog-path, .lyrics-source { margin-top: 8px; color: var(--muted); font-size: 11px; overflow-wrap: anywhere; }
.lyrics-close { display: grid; place-items: center; width: 32px; height: 32px; padding: 0; border: 0; border-radius: 50%; color: var(--text); background: #ffffff12; }
.lyrics-close-icon { display: block; width: 18px; height: 18px; }
.lyrics-close:hover { background: #ffffff24; }
.lyrics-text { min-height: 200px; margin: 0; padding: 28px; overflow: auto; color: var(--text); font-family: inherit; font-size: 20px; font-weight: 500; line-height: 1.8; white-space: pre-wrap; }
.lyrics-text.loading, .lyrics-text.error { color: var(--muted); font-size: 14px; }
@media (min-width: 1700px) { .page { padding-inline: 40px; } .header { margin-inline: -40px; padding-inline: 40px; } }
@media (max-width: 1450px) {
  .analysis-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .donut-layout { grid-template-columns: 140px minmax(0, 1fr); align-items: center; }
  .toolbar { grid-template-columns: repeat(4, minmax(0, 1fr)); }
  .search-control { grid-column: 1 / -1; }
  .summary { grid-template-columns: repeat(4, minmax(0, 1fr)); }
}
@media (max-width: 1050px) {
  .app-shell { grid-template-columns: 200px minmax(0, 1fr); }
  .app-sidebar { width: 200px; }
  .page { padding-inline: 24px; } .header { margin-inline: -24px; padding-inline: 24px; }
  .collection-art { flex-basis: 104px; height: 104px; } .collection-art svg { width: 56px; height: 56px; }
  .hero-layout { gap: 18px; } h1 { letter-spacing: -1px; }
  .hero-lead { max-width: 380px; }
  .donut-layout { grid-template-columns: 1fr; }
  .comparison { grid-template-columns: 1fr; } .divider { min-height: 40px; } .arrow { transform: rotate(90deg); }
  .section-heading p { display: none; }
  .toolbar { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 760px) {
  .app-shell { display: block; padding: 0; }
  .app-sidebar { position: relative; top: auto; left: auto; bottom: auto; flex-direction: row; align-items: center; flex-wrap: wrap; gap: 8px; width: auto; height: auto; min-height: 0; padding: 14px 16px 10px; overflow: visible; contain: none; border-radius: 0; }
  .app-brand { padding: 0; gap: 8px; } .app-brand strong { font-size: 14px; } .app-brand small { display: none; }
  .brand-mark { width: 28px; height: 28px; } .brand-icon { width: 19px; height: 19px; }
  .side-nav { display: flex; flex: 1 0 100%; gap: 4px; order: 2; }
  .side-nav a { justify-content: center; flex: 1; gap: 7px; min-height: 38px; padding: 8px 6px; font-size: 11px; }
  .nav-icon { width: 16px; height: 16px; }
  .nav-caption { display: none; }
  .sidebar-note { order: 1; margin: 0 0 0 auto; padding: 0; border: 0; } .sidebar-note small { display: none; } .sidebar-note strong { font-size: 10px; }
  .sidebar-source { order: 3; flex: 1 0 100%; min-width: 0; margin: 6px 0 0; padding-top: 10px; }
  .app-workspace { border-radius: 0; } .header { border-radius: 0; }
  .page { padding: 0 20px 40px; } .header { margin-inline: -20px; padding: 24px 20px 16px; }
  .hero-layout { align-items: start; } .collection-art { flex-basis: 80px; height: 80px; } .collection-art svg { width: 44px; height: 44px; }
  h1 { font-size: 34px; } .hero-lead { font-size: 12px; }
  .metric { padding: 12px 10px; } .metric strong { font-size: 24px; }
  .summary { gap: 6px; margin-top: 20px; }
  .metric-label { font-size: 10px; }
  .music-card-content { grid-template-columns: 80px minmax(0, 1fr); gap: 14px; } .music-cover { width: 80px; }
  .music-card { padding: 14px 40px 14px 14px; } .music-trash-icon { right: 8px; top: 10px; }
  .music-actions .small { min-height: 36px; } .section-title { font-size: 22px; }
}
@media (max-width: 520px) {
  .side-nav { min-width: 0; width: 100%; }
  .side-nav a { flex: 1 1 0; min-width: 0; flex-direction: column; gap: 4px; font-size: 10px; }
  .side-nav a span { white-space: nowrap; }
  .page { padding-inline: 16px; } .header { margin-inline: -16px; padding-inline: 16px; }
  .hero-layout { gap: 12px; } .collection-art { flex-basis: 64px; height: 64px; } .collection-art svg { width: 36px; height: 36px; }
  h1 { font-size: 28px; letter-spacing: -.8px; } .hero-kicker { font-size: 10px; } .hero-lead { font-size: 11px; }
  .summary { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .analysis-grid { grid-template-columns: 1fr; }
  .panel { padding: 18px; } .donut-layout { grid-template-columns: 1fr; gap: 16px; } .donut-chart { width: 140px; }
  .music-operations { padding: 16px; } .music-operation-groups { display: grid; }
  .music-operations-row { gap: 6px; } .mode-choice { padding-inline: 8px; font-size: 11px; }
  .duplicates-actions { gap: 6px; } .duplicates-actions .small { min-height: 36px; padding-inline: 10px; font-size: 11px; }
  .music-card-content { grid-template-columns: 1fr; } .music-cover { width: 104px; }
  .group-header { grid-template-columns: 1fr; gap: 10px; padding: 16px; }
  .group-body { padding: 10px; } .track { padding: 12px; } .track-head { grid-template-columns: 64px minmax(0, 1fr); gap: 10px; } .music-cover.duplicate-cover { width: 64px; }
  .lyrics-dialog-head { padding: 18px; } .lyrics-text { padding: 20px; font-size: 17px; }
}
@media (prefers-reduced-motion: reduce) {
  html { scroll-behavior: auto; } *, *::before, *::after { animation-duration: .01ms !important; animation-iteration-count: 1 !important; transition-duration: .01ms !important; }
}
"""
