"""Compare parameters in separate file columns in the standalone report."""

REPORT_DUPLICATES_JS = r"""
globalThis.ReportDuplicates = (() => {
  function comparisonRows(files) {
    const fields = new Map(files.flatMap(file => file.rows.map(row => [row.key, row.label])));
    return Array.from(fields, ([key, label]) => {
      const values = files.map(file => {
        const row = file.rows.find(row => row.key === key);
        return {path: file.path, value: row?.value || '—', better: !!row?.better};
      });
      const different = new Set(values.map(cell => cell.value)).size > 1;
      if (!different) values.forEach(cell => { cell.better = false; });
      return {key, label, values, different};
    });
  }

  function fileParameters(files, all) {
    const rows = comparisonRows(files).filter(row => all || row.different);
    return files.map((file, index) => ({
      path: file.path,
      label: file.label,
      rows: rows.map(row => ({key: row.key, label: row.label, ...row.values[index]})),
    }));
  }

  function readFiles(comparison) {
    return Array.from(comparison.querySelectorAll('.duplicate-track'), (track, index) => ({
      path: track.dataset.filePath,
      name: track.querySelector('.track-title').textContent,
      label: 'Файл ' + (index + 1),
      rows: Array.from(track.querySelectorAll('td[data-quality]'), cell => ({
        key: cell.dataset.quality,
        label: cell.parentElement.querySelector('th').textContent,
        value: cell.textContent,
        better: cell.classList.contains('quality-better'),
      })),
    }));
  }

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function fileTable(file) {
    const section = element('div', 'duplicate-file-parameters');
    section.dataset.filePath = file.path;
    const table = element('table', 'quality-table duplicate-file-table');
    table.setAttribute('aria-label', 'Характеристики: ' + file.label);
    const head = element('thead');
    const header = element('tr');
    ['Параметр', file.label].forEach(text => {
      const th = element('th', '', text);
      th.scope = 'col';
      header.append(th);
    });
    head.append(header);
    const body = element('tbody');
    file.rows.forEach(row => {
      const tr = element('tr');
      tr.dataset.quality = row.key;
      const label = element('th', '', row.label);
      label.scope = 'row';
      const value = element('td', row.better ? 'quality-better' : '', row.value);
      tr.append(label, value);
      body.append(tr);
    });
    table.append(head, body);
    section.append(table);
    return section;
  }

  function refreshComparison(comparison) {
    const files = readFiles(comparison);
    const grid = comparison.querySelector('.duplicate-file-grid');
    grid.style.setProperty('--compare-files', files.length);
    grid.querySelectorAll('.duplicate-file-column').forEach(column => {
      if (!column.querySelector('.duplicate-track')) column.remove();
    });
    const rows = comparisonRows(files);
    let panel = comparison.querySelector('.duplicate-matrix-panel');
    if (!panel) {
      panel = element('div', 'duplicate-matrix-panel');
      comparison.prepend(panel);
    }
    const all = comparison.dataset.showAll === 'yes';
    const toolbar = element('div', 'duplicate-matrix-toolbar');
    const heading = element('strong', '', 'Все параметры');
    const toggle = element('button', 'small duplicate-compare-toggle', all ? 'Показать только различия' : 'Показать все параметры');
    toggle.type = 'button';
    toggle.setAttribute('aria-pressed', String(all));
    toggle.addEventListener('click', () => {
      comparison.dataset.showAll = all ? 'no' : 'yes';
      refreshComparison(comparison);
      comparison.querySelector('.duplicate-compare-toggle').focus();
    });
    toolbar.append(heading, toggle);
    const tracks = Array.from(grid.querySelectorAll('.duplicate-track'));
    fileParameters(files, all).forEach((file, index) => {
      const track = tracks[index];
      let column = track.parentElement;
      if (!column.classList.contains('duplicate-file-column')) {
        column = element('div', 'duplicate-file-column');
        grid.insertBefore(column, track);
        column.append(track);
      }
      column.dataset.filePath = file.path;
      column.querySelector('.duplicate-file-parameters')?.remove();
      column.append(fileTable(file));
    });
    const note = element('p', 'duplicate-matrix-note', 'Отображаемые параметры совпадают. Это не подтверждает совпадение содержимого файлов.');
    note.hidden = all || rows.some(row => row.different);
    panel.replaceChildren(toolbar, note);
    comparison.classList.add('comparison-enhanced');
    return rows.filter(row => row.different).map(row => row.label.toLowerCase());
  }

  function refresh(group) {
    const differences = new Set();
    group.querySelectorAll('.comparison').forEach(comparison => {
      refreshComparison(comparison).forEach(label => differences.add(label));
      comparison.querySelectorAll('.duplicate-track').forEach((track, index) => {
        const number = track.querySelector('.duplicate-file-number');
        if (number) number.textContent = 'Файл ' + (index + 1);
      });
    });
    const summary = group.querySelector('.group-differences');
    if (summary) {
      const labels = Array.from(differences);
      summary.textContent = labels.length ? 'Различия: ' + labels.slice(0, 3).join(', ') + (labels.length > 3 ? ' и ещё ' + (labels.length - 3) : '') : 'Отображаемые параметры совпадают';
    }
    const count = group.querySelector('.group-file-count');
    if (count) count.textContent = 'Файлов: ' + group.querySelectorAll('.duplicate-track').length;
  }

  return {comparisonRows, fileParameters, refresh};
})();
"""
