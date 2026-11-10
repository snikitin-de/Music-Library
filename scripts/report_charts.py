"""Offline Plotly assets and figure containers for the standalone report."""

import html
import json
import re
from pathlib import Path

_ASSETS = Path(__file__).parent / "assets"
# Prevent a literal HTML closing tag in vendored JavaScript from ending its script.
PLOTLY_JS = re.sub(r"</script", r"<\\/script", (
    (_ASSETS / "plotly-4.2.0.min.js").read_text(encoding="utf-8") + "\n" +
    (_ASSETS / "plotly-locale-ru-4.2.0.js").read_text(encoding="utf-8")
), flags=re.I)
PLOTLY_LICENSE = (_ASSETS / "Plotly-LICENSE.txt").read_text(encoding="utf-8")


def plotly_chart(data: list[dict], layout: dict, fallback: str, *, height: int, classes: str = "", label: str = "Диаграмма") -> str:
    figure = html.escape(json.dumps({"data": data, "layout": layout}, ensure_ascii=False), quote=True)
    return (
        f'<div class="library-chart {html.escape(classes)}" style="height:{height}px" '
        f'data-plotly="{figure}" role="img" aria-label="{html.escape(label)}">'
        '<div class="plotly-host" aria-hidden="true"></div>'
        f'<div class="plotly-fallback">{fallback}</div></div>'
    )


def horizontal_bars(items: list[tuple], fallback: str, *, height: int, label: str) -> str:
    labels = [html.escape(str(name)) for name, _ in items]
    values = [count for _, count in items]
    return plotly_chart([{
        "type": "bar", "orientation": "h", "x": values, "y": labels,
        "marker": {"color": "#2bcf70", "line": {"width": 0}},
        "text": [str(count) for count in values], "textposition": "outside", "cliponaxis": False,
        "constraintext": "none", "textfont": {"size": 12},
        "hovertemplate": "%{y}: %{x} файлов<extra></extra>",
    }], {
        "margin": {"l": 0, "r": 24, "t": 2, "b": 2}, "bargap": 0.72, "barcornerradius": 0,
        "xaxis": {"visible": False, "fixedrange": True, "range": [0, max(values, default=1) * 1.18]},
        "yaxis": {"autorange": "reversed", "automargin": True, "fixedrange": True, "type": "category", "tickfont": {"size": 12}, "ticks": "", "ticksuffix": "  "},
    }, fallback, height=height, label=label)


REPORT_CHARTS_JS = r"""
(() => {
  if (typeof Plotly === 'undefined') return;
  const config = {displayModeBar: false, displaylogo: false, responsive: true, scrollZoom: false, doubleClick: false, showTips: false, locale: 'ru'};
  const pending = new WeakSet();
  const draw = () => document.querySelectorAll('[data-plotly]').forEach(element => {
    if (element.closest('[hidden]') || pending.has(element)) return;
    const host = element.querySelector('.plotly-host');
    if (element.classList.contains('plotly-ready')) {
      Plotly.Plots.resize(host).catch(error => {
        if (!element.closest('[hidden]')) console.warn('Plotly: не удалось обновить размер графика', error);
      });
      return;
    }
    pending.add(element);
    const figure = JSON.parse(element.dataset.plotly);
    const layout = Object.assign({
      paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
      font: {family: 'Library Nunito, Segoe UI, sans-serif', size: 12, color: '#f5f5f5'},
      hoverlabel: {bgcolor: '#242424', bordercolor: '#484848', font: {family: 'Library Nunito, sans-serif', size: 13}},
      showlegend: false, dragmode: false, separators: ', ',
      margin: {l: 0, r: 0, t: 0, b: 0},
    }, figure.layout);
    Plotly.newPlot(host, figure.data, layout, config).then(() => {
      element.classList.add('plotly-ready');
    }).catch(error => {
      host.replaceChildren();
      console.warn('Plotly: оставлен статический график', error);
    }).finally(() => pending.delete(element));
  });
  window.addEventListener('report-page-change', () => {
    if (document.fonts) document.fonts.ready.then(draw); else draw();
  });
  // Plotly sizes labels with the real embedded font, avoiding fallback-font measurements.
  if (document.fonts) document.fonts.ready.then(draw); else draw();
})();
"""
