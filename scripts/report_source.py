"""Folder selection dialog for a report served by report_server.py."""

SOURCE_DIALOG_HTML = r"""
  <dialog class="source-dialog" id="sourceDialog" aria-labelledby="sourceTitle">
    <div class="source-dialog-head">
      <h2 id="sourceTitle">Источник музыки</h2>
      <button class="source-close" id="sourceClose" type="button" aria-label="Закрыть выбор источника">×</button>
    </div>
    <div class="source-dialog-body">
      <form id="sourceBrowseForm">
        <label for="sourcePath">Путь к папке</label>
        <div class="source-path-row">
          <input id="sourcePath" type="text" autocomplete="off" spellcheck="false" autofocus placeholder="Диск, папка или сетевой путь UNC">
          <button class="small" type="submit" id="sourceGo">Открыть</button>
        </div>
      </form>
      <div class="source-navigation">
        <button class="small" id="sourceRoots" type="button">Диски</button>
        <button class="small" id="sourceParent" type="button" disabled>На уровень выше</button>
      </div>
      <div class="source-folder-frame"><div class="source-folders" id="sourceFolders" role="group" aria-label="Папки"></div></div>
      <p class="source-status" id="sourceStatus" role="status" aria-live="polite"></p>
      <div class="source-progress" id="sourceProgressPanel" hidden>
        <div class="source-progress-caption"><strong id="sourceProgressStage">Подготовка сканирования</strong><span id="sourceProgressDetails"></span></div>
        <progress id="sourceProgress" max="1" aria-label="Прогресс текущего этапа сканирования"></progress>
        <div class="source-progress-file" id="sourceProgressFile"></div>
      </div>
      <p class="source-hint">Здесь показаны папки компьютера, на котором запущена программа. После подтверждения обновятся источник, список музыки и отчёт дублей. Музыкальные файлы останутся на месте, теги не изменятся.</p>
    </div>
    <div class="source-dialog-actions">
      <button class="small" id="sourceCancel" type="button">Отмена</button>
      <button class="small source-apply" id="sourceApply" type="button" disabled>Выбрать и пересканировать</button>
    </div>
  </dialog>
"""

SOURCE_DIALOG_JS = r"""
(() => {
  const source = document.getElementById('librarySource');
  const dialog = document.getElementById('sourceDialog');
  const path = document.getElementById('sourcePath');
  const folders = document.getElementById('sourceFolders');
  const status = document.getElementById('sourceStatus');
  const apply = document.getElementById('sourceApply');
  const parent = document.getElementById('sourceParent');
  const close = document.getElementById('sourceClose');
  const cancel = document.getElementById('sourceCancel');
  const progressPanel = document.getElementById('sourceProgressPanel');
  const progressBar = document.getElementById('sourceProgress');
  const progressStage = document.getElementById('sourceProgressStage');
  const progressDetails = document.getElementById('sourceProgressDetails');
  const progressFile = document.getElementById('sourceProgressFile');
  let selected = '';
  let parentPath = null;
  let controller = null;
  let busy = false;
  let opening = 0;

  function showProgress(state) {
    const stages = {starting:'Подготовка сканирования', discover:'Поиск аудиофайлов', tags:'Чтение тегов', hashes:'Проверка точных копий', analysis:'Анализ музыки и обложек', render:'Сборка отчёта', publish:'Сохранение отчётов', completed:'Сканирование завершено', failed:'Сканирование не завершено'};
    progressStage.textContent = stages[state.stage] || 'Сканирование';
    const count = Number(state.processed) || 0;
    const total = state.total;
    if (state.status === 'failed' || state.stage === 'failed') {
      progressBar.max = 1;
      progressBar.value = 0;
      progressDetails.textContent = '';
    } else if (Number.isFinite(total) && total > 0) {
      progressBar.max = total;
      progressBar.value = count;
      progressDetails.textContent = count.toLocaleString('ru-RU') + ' из ' + total.toLocaleString('ru-RU') + ' · ' + Math.floor(count / total * 100) + '%';
    } else if (total === 0) {
      progressBar.max = 1;
      progressBar.value = 1;
      progressDetails.textContent = 'Нет файлов для этого этапа';
    } else {
      progressBar.removeAttribute('value');
      progressDetails.textContent = state.stage === 'discover' ? 'Найдено: ' + count.toLocaleString('ru-RU') : '';
    }
    progressFile.textContent = state.current || '';
    progressFile.title = state.current || '';
  }

  function watchProgress(id) {
    let stopped = false;
    let timer;
    const request = new AbortController();
    async function poll() {
      try {
        const response = await fetch('/api/library-source/progress?id=' + encodeURIComponent(id), {signal: request.signal, cache:'no-store'});
        const state = await response.json();
        if (!stopped && response.ok && state.ok) showProgress(state);
      } catch (error) {
        // The POST still determines success; temporary polling failures are retried.
      } finally {
        if (!stopped) timer = setTimeout(poll, 500);
      }
    }
    poll();
    return () => { stopped = true; clearTimeout(timer); request.abort(); };
  }

  async function readJson(url, options) {
    const response = await fetch(url, options);
    const result = await response.json();
    if (!response.ok || !result.ok) throw new Error(result.error || 'Не удалось выполнить запрос.');
    return result;
  }

  async function browse(value) {
    if (busy) return;
    if (controller) controller.abort();
    const current = new AbortController();
    controller = current;
    selected = '';
    apply.disabled = true;
    parent.disabled = true;
    path.value = value;
    folders.replaceChildren();
    status.textContent = 'Открываю папку...';
    try {
      const result = await readJson('/api/folders?path=' + encodeURIComponent(value), {signal: current.signal});
      if (controller !== current || !dialog.open) return;
      selected = result.path;
      parentPath = result.parent;
      path.value = selected;
      parent.disabled = !parentPath;
      result.folders.forEach(folder => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'source-folder';
        button.textContent = folder.name;
        button.title = folder.path;
        button.setAttribute('aria-label', 'Открыть папку ' + folder.name);
        button.addEventListener('click', () => browse(folder.path));
        folders.append(button);
      });
      status.textContent = result.folders.length ? 'Выберите вложенную папку или используйте текущую.' : 'В этой папке нет вложенных папок. Можно выбрать её источником.';
      apply.disabled = !selected;
    } catch (error) {
      if (error.name !== 'AbortError' && controller === current && dialog.open) {
        status.textContent = 'Не удалось открыть папку: ' + (error.message || 'папка недоступна.');
      }
    }
  }

  function dismiss() { if (!busy) dialog.close(); }
  close.addEventListener('click', dismiss);
  cancel.addEventListener('click', dismiss);
  dialog.addEventListener('cancel', event => { if (busy) event.preventDefault(); });
  dialog.addEventListener('close', () => { opening++; if (controller) controller.abort(); });
  document.getElementById('sourceBrowseForm').addEventListener('submit', event => { event.preventDefault(); browse(path.value); });
  document.getElementById('sourceRoots').addEventListener('click', () => browse(''));
  parent.addEventListener('click', () => { if (parentPath) browse(parentPath); });
  path.addEventListener('input', () => {
    opening++;
    if (controller) controller.abort();
    controller = null;
    selected = '';
    apply.disabled = true;
    parent.disabled = true;
    status.textContent = 'Нажмите «Открыть», чтобы проверить путь.';
  });

  source.addEventListener('click', async () => {
    const attempt = ++opening;
    dialog.showModal();
    progressPanel.hidden = true;
    folders.replaceChildren();
    apply.disabled = true;
    path.value = document.getElementById('librarySourcePath').dataset.path || '';
    if (!['http:', 'https:'].includes(location.protocol)) {
      status.textContent = 'Для выбора папки откройте отчёт через локальный сервер.';
      return;
    }
    status.textContent = 'Загружаю источник...';
    try {
      const info = await readJson('/api/library-source');
      if (attempt === opening && dialog.open) browse(info.path);
    } catch (error) {
      if (attempt === opening && dialog.open) status.textContent = 'Не удалось получить источник: ' + (error.message || 'сервер недоступен.');
    }
  });

  apply.addEventListener('click', async () => {
    if (busy || !selected) return;
    busy = true;
    const progressId = crypto.randomUUID ? crypto.randomUUID() : Date.now().toString(36) + '-' + Math.random().toString(36).slice(2);
    const chosen = selected;
    if (controller) controller.abort();
    dialog.querySelectorAll('button,input').forEach(control => { control.disabled = true; });
    document.querySelectorAll('audio').forEach(audio => audio.pause());
    status.textContent = 'Пересканирую выбранную папку. Музыкальные файлы не изменяются. Дождитесь завершения.';
    progressPanel.hidden = false;
    showProgress({stage:'starting',processed:0,total:null});
    const stopProgress = watchProgress(progressId);
    apply.textContent = 'Сканирование...';
    try {
      await readJson('/api/library-source', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({path: chosen, confirm: 'CHANGE_LIBRARY_SOURCE', progress_id: progressId}),
      });
      showProgress({stage:'completed',processed:1,total:1});
      status.textContent = 'Источник изменён. Открываю обновлённый отчёт...';
      location.hash = '#overview';
      location.reload();
    } catch (error) {
      showProgress({stage:'failed',processed:0,total:null});
      status.textContent = 'Источник не изменён: ' + (error.message || 'ошибка сканирования.');
    } finally {
      stopProgress();
      busy = false;
      dialog.querySelectorAll('button,input').forEach(control => { control.disabled = false; });
      parent.disabled = !parentPath;
      apply.disabled = !selected;
      apply.textContent = 'Выбрать и пересканировать';
    }
  });
})();
"""
