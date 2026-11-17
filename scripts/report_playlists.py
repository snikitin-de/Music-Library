"""Playlist controls for the standalone report."""

from report_controls import page_actions_html

PLAYLISTS_SIDEBAR_HTML = """
      <section class="sidebar-playlists" aria-labelledby="playlistSectionTitle">
        <div class="sidebar-playlists-heading">
          <h2 class="nav-caption" id="playlistSectionTitle">Плейлисты</h2>
          <button class="small" id="createPlaylist" type="button">Создать</button>
        </div>
        <div class="playlist-search-row" id="playlistSearchRow">
          <button class="playlist-search-toggle" id="playlistSearchToggle" type="button" aria-expanded="false" aria-controls="playlistSearch" aria-label="Поиск плейлистов" title="Поиск плейлистов">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="6.5"/><path d="m16 16 4 4"/></svg>
          </button>
          <div class="playlist-search-field">
            <input id="playlistSearch" type="search" placeholder="Поиск плейлистов" aria-label="Поиск плейлистов" disabled>
          </div>
          <div class="playlist-sort">
            <svg data-select-icon hidden viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true">
              <path d="M8 6h12M8 12h12M8 18h12M4 6h.01M4 12h.01M4 18h.01"/>
            </svg>
            <select id="playlistSort" data-menu-align="end" aria-label="Сортировка плейлистов">
              <option value="date" data-label="По дате">По дате создания</option>
              <option value="name">По алфавиту</option>
            </select>
          </div>
        </div>
        <nav id="playlistNavigation" aria-label="Плейлисты"></nav>
        <p class="playlist-hint" id="playlistNavigationEmpty" hidden>Плейлисты не найдены.</p>
      </section>
"""

def playlists_page_html(track_search: str, track_table: str) -> str:
    actions = page_actions_html("playlistActions", "Действия с плейлистом", """
          <button id="renamePlaylist" type="button" aria-haspopup="dialog">Переименовать</button>
          <button id="resetPlaylistCover" type="button" disabled>Сбросить фото</button>
          <button id="deletePlaylist" type="button" aria-haspopup="dialog">Удалить плейлист</button>""")
    return f"""
    <section class="report-view music-section" data-page="playlist" aria-labelledby="playlistTitle" hidden>
      <header class="header">
        <div class="hero-layout playlist-hero">
          <button class="playlist-cover-button" id="playlistCoverButton" type="button" aria-label="Выбрать фото плейлиста" title="Выбрать фото плейлиста">
            <span class="playlist-cover-frame" id="playlistCover"></span>
            <span class="playlist-cover-action" aria-hidden="true">Выбрать фото</span>
          </button>
          <input id="playlistCoverInput" type="file" accept="image/*" hidden>
          <div class="hero-copy">
            <span class="playlist-kind">Плейлист</span>
            <h1 id="playlistTitle"></h1>
            <p class="music-summary" id="playlistSummary"></p>
          </div>
        </div>
      </header>
      {track_search}
      {actions}
      {track_table}
      <div class="empty" id="playlistTrackEmpty" role="status">Треки не найдены.</div>
      <div class="list-pagination" id="playlistPagination" hidden>
        <button class="small" type="button">Показать ещё 10 треков</button>
      </div>
    </section>
"""

PLAYLISTS_CONTROLS_HTML = """
  <dialog class="playlist-dialog" id="playlistDialog" aria-labelledby="playlistDialogTitle">
    <form id="playlistForm">
      <h2 id="playlistDialogTitle">Создать плейлист</h2>
      <label for="playlistName">Название</label>
      <input id="playlistName" maxlength="80" required>
      <p class="playlist-hint" id="playlistCreateError" role="status"></p>
      <div class="playlist-dialog-actions">
        <button class="small" id="cancelPlaylist" type="button">Отмена</button>
        <button class="small" id="playlistNameSubmit" type="submit">Создать</button>
      </div>
    </form>
  </dialog>
  <dialog class="playlist-dialog" id="playlistDeleteDialog" aria-labelledby="playlistDeleteTitle">
    <form id="playlistDeleteForm">
      <h2 id="playlistDeleteTitle">Удалить плейлист?</h2>
      <p id="playlistDeleteName"></p>
      <p id="playlistDeleteError" class="playlist-hint" role="status"></p>
      <div class="playlist-dialog-actions">
        <button class="small" id="cancelPlaylistDelete" type="button" autofocus>Отмена</button>
        <button class="small playlist-delete-confirm" type="submit">Удалить</button>
      </div>
    </form>
  </dialog>
  <div class="playlist-track-menu report-menu" id="playlistTrackMenu" role="group" aria-label="Действия с треком" hidden>
    <button id="addTrackToPlaylist" type="button" aria-expanded="false" aria-controls="trackPlaylistPicker">Добавить в плейлист</button>
    <button id="addTrackToQueue" type="button">Добавить в очередь</button>
    <button id="playTrackNext" type="button">Играть следующим</button>
    <button id="removeTrackFromPlaylist" type="button" hidden>Удалить из плейлиста</button>
    <div id="trackPlaylistPicker" hidden>
      <input id="trackPlaylistSearch" type="search" placeholder="Поиск плейлиста" aria-label="Поиск плейлиста для трека">
      <div id="trackPlaylistOptions"></div>
    </div>
  </div>
  <div class="playlist-status" id="playlistStatus" hidden>
    <span id="playlistStatusMessage" role="status"></span>
    <button class="small" id="restorePlaylist" type="button" hidden>Отменить</button>
  </div>
  <template id="playlistArtworkNote">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      <path d="M9 18V5l11-2v13"/><ellipse cx="6" cy="18" rx="3" ry="2.5"/><ellipse cx="17" cy="16" rx="3" ry="2.5"/>
    </svg>
  </template>
  <template id="playlistUnavailableTrack">
    <table><tbody class="playlist-unavailable">
      <tr class="music-track-row">
        <td class="music-track-number"></td>
        <th scope="row">
          <div class="music-track-name">
            <span class="music-cover music-cover-empty" aria-hidden="true">♪</span>
            <div class="music-track-text">
              <div class="music-title"></div>
              <small class="playlist-hint">Файл недоступен в библиотеке</small>
            </div>
          </div>
        </th>
        <td class="music-track-artist"></td>
        <td class="music-track-album"></td>
        <td class="music-track-duration">—</td>
        <td class="music-track-control">
          <div class="music-track-actions">
            <button class="music-track-menu-button" type="button" aria-expanded="false" aria-controls="playlistTrackMenu" aria-label="Действия с треком" title="Действия с треком"><span aria-hidden="true">…</span></button>
          </div>
        </td>
      </tr>
    </tbody></table>
  </template>
"""

PLAYLISTS_JS = r"""
class ReportTrackSelection {
  constructor(pager, normalizePath) {
    this.pager = pager;
    this.normalizePath = normalizePath;
    this.table = pager.container;
    this.bar = this.table.previousElementSibling;
    this.count = this.bar.querySelector('[data-track-selection-count]');
    this.actions = this.bar.querySelector('[data-track-selection-actions]');
    this.rows = [];
    this.selected = new Set();
    this.anchor = null;
    this.bar.querySelector('[data-track-selection-clear]').addEventListener('click', () => this.clear(true));
    this.table.addEventListener('click', event => this.handleClick(event), true);
    this.table.addEventListener('keydown', event => {
      if (event.key.toLowerCase() !== 'a' || !(event.ctrlKey || event.metaKey) ||
          !event.target.closest('.music-track-row')) return;
      event.preventDefault();
      this.replace(new Set(this.rows));
    });
  }

  checkbox(row) {
    return row?.querySelector('.music-track-select');
  }

  setItems(items, reset = true) {
    const key = row => row ? this.normalizePath(row.dataset.filePath) : '';
    const selected = new Set(Array.from(this.selected, key));
    const anchor = key(this.anchor);
    this.rows = items.filter(row => row.classList.contains('music-card'));
    this.anchor = anchor ? this.rows.find(row => key(row) === anchor) : null;
    this.replace(new Set(selected.size ? this.rows.filter(row => selected.has(key(row))) : []));
    this.pager.setItems(items, reset);
  }

  handleClick(event) {
    const row = event.target.closest('.music-track-row')?.parentElement;
    if (!row?.classList.contains('music-card')) return;
    const control = event.target.closest('button, a, input');
    const modified = event.ctrlKey || event.metaKey || event.shiftKey;
    const checkbox = this.checkbox(row);
    if (control && control !== checkbox) {
      if (!modified || !control.matches('.music-play')) return;
      event.preventDefault();
      event.stopPropagation();
    }
    this.select(row, event.shiftKey, event.ctrlKey || event.metaKey || (control === checkbox && !event.shiftKey));
    if (control !== checkbox) checkbox.focus({preventScroll: true});
  }

  select(row, range, toggle) {
    if (range && this.anchor) {
      const first = this.rows.indexOf(this.anchor);
      const last = this.rows.indexOf(row);
      const rows = this.rows.slice(Math.min(first, last), Math.max(first, last) + 1);
      this.replace(new Set(toggle ? [...this.selected, ...rows] : rows));
      return;
    }
    this.anchor = row;
    const selected = toggle ? new Set(this.selected) : new Set();
    if (selected.has(row)) selected.delete(row);
    else selected.add(row);
    this.replace(selected);
  }

  replace(rows) {
    for (const row of this.selected) {
      if (!rows.has(row)) this.checkbox(row).checked = false;
    }
    for (const row of rows) this.checkbox(row).checked = true;
    this.selected = rows;
    this.bar.hidden = rows.size === 0;
    const count = rows.size ? 'Выбрано ' + rows.size.toLocaleString('ru-RU') : '';
    if (this.count.textContent !== count) this.count.textContent = count;
  }

  selectedRows() {
    return this.rows.filter(row => this.selected.has(row));
  }

  clear(restoreFocus = false) {
    if (restoreFocus && this.bar.contains(document.activeElement)) {
      const row = this.table.contains(this.anchor) ? this.anchor : this.selectedRows().find(row => this.table.contains(row));
      (this.checkbox(row) || this.table.querySelector('.music-sort')).focus({preventScroll: true});
    }
    this.anchor = null;
    this.replace(new Set());
  }
}

class ReportPlaylists {
  constructor({libraryPath, reportTitle, musicPager, normalizePath, resolveTrack, trackCard, playTracks, enqueueTracks, storage, onTrackRemoved, onPlaylistRemoved, bindTrack, sortTrackTable, formatTrackSummary}) {
    this.storageKey = 'music-report-playlists:' + (normalizePath(libraryPath) || location.pathname);
    this.sortStorageKey = this.storageKey + ':sort';
    this.reportTitle = reportTitle;
    this.storage = storage;
    this.normalizePath = normalizePath;
    this.resolveTrack = resolveTrack;
    this.trackCard = trackCard;
    this.playTracks = playTracks;
    this.onTrackRemoved = onTrackRemoved;
    this.onPlaylistRemoved = onPlaylistRemoved;
    this.sortTrackTable = sortTrackTable;
    this.formatTrackSummary = formatTrackSummary;
    const ids = ['createPlaylist', 'playlistSearch', 'playlistSearchToggle', 'playlistSearchRow', 'playlistNavigation', 'playlistNavigationEmpty',
      'playlistSort',
      'playlistTitle', 'playlistSummary', 'playlistTrackSearch', 'playlistTracks', 'playlistTrackEmpty', 'playlistPagination', 'playlistDialog',
      'playlistCoverButton', 'playlistCover', 'playlistCoverInput', 'resetPlaylistCover', 'playlistArtworkNote',
      'renamePlaylist', 'deletePlaylist', 'playlistDialogTitle', 'playlistNameSubmit',
      'playlistDeleteDialog', 'playlistDeleteForm', 'playlistDeleteName', 'playlistDeleteError', 'cancelPlaylistDelete',
      'playlistForm', 'playlistName', 'playlistCreateError', 'cancelPlaylist', 'playlistTrackMenu',
      'addTrackToPlaylist', 'playTrackNext', 'addTrackToQueue', 'removeTrackFromPlaylist', 'trackPlaylistPicker', 'trackPlaylistSearch', 'trackPlaylistOptions',
      'playlistStatus', 'playlistStatusMessage', 'restorePlaylist', 'playlistUnavailableTrack'];
    this.ui = Object.fromEntries(ids.map(id => [id, document.getElementById(id)]));
    this.items = [];
    this.navigationSort = 'date';
    this.nameCollator = new Intl.Collator('ru', {sensitivity: 'base', numeric: true});
    this.activeId = '';
    this.sortKey = null;
    this.sortDirection = 1;
    this.rows = [];
    this.menuTracks = [];
    this.menuButton = null;
    this.statusTimer = null;
    this.coverRequest = 0;
    try {
      this.items = this.read();
      this.navigationSort = localStorage.getItem(this.sortStorageKey) === 'name' ? 'name' : 'date';
    } catch {
      if (!this.storage.server) this.notify('Плейлисты недоступны. Проверьте настройки хранения данных браузера.');
    }

    const ui = this.ui;
    ui.playlistSort.value = this.navigationSort;
    ui.playlistSort.dispatchEvent(new Event('change'));
    ui.playlistSort.addEventListener('change', () => {
      this.navigationSort = ui.playlistSort.value;
      this.renderNavigation();
      try {
        localStorage.setItem(this.sortStorageKey, this.navigationSort);
      } catch {
        // Sorting still works for the current page.
      }
    });
    this.pager = new ReportPagedList(ui.playlistTracks, ui.playlistPagination, ui.playlistTracks.closest('[data-page]'), bindTrack);
    this.musicSelection = new ReportTrackSelection(musicPager, normalizePath);
    this.playlistSelection = new ReportTrackSelection(this.pager, normalizePath);
    const selections = [this.musicSelection, this.playlistSelection];
    ui.playlistTrackSearch.addEventListener('input', () => this.filterTracks());
    ui.playlistTracks.querySelectorAll('[data-music-sort]').forEach(button => {
      button.addEventListener('click', () => {
        const key = button.dataset.musicSort;
        this.sortDirection = key === this.sortKey ? -this.sortDirection : 1;
        this.sortKey = key;
        this.sortRows();
      });
    });
    ui.createPlaylist.addEventListener('click', () => this.openNameDialog());
    ui.renamePlaylist.addEventListener('click', () => {
      const playlist = this.items.find(item => item.id === this.activeId);
      if (!playlist) return;
      this.openNameDialog(playlist);
    });
    ui.cancelPlaylist.addEventListener('click', () => ui.playlistDialog.close());
    ui.playlistForm.addEventListener('submit', async event => {
      event.preventDefault();
      if (ui.playlistNameSubmit.disabled) return;
      ui.playlistNameSubmit.disabled = true;
      try { await this.saveName(); } finally { ui.playlistNameSubmit.disabled = false; }
    });
    ui.deletePlaylist.addEventListener('click', () => {
      const playlist = this.items.find(item => item.id === this.activeId);
      if (!playlist) return;
      this.deleteTargetId = playlist.id;
      ui.playlistDeleteName.textContent = '«' + playlist.name + '»';
      ui.playlistDeleteError.textContent = '';
      ui.playlistDeleteDialog.showModal();
    });
    ui.cancelPlaylistDelete.addEventListener('click', () => ui.playlistDeleteDialog.close());
    ui.playlistDeleteForm.addEventListener('submit', async event => {
      event.preventDefault();
      const submit = ui.playlistDeleteForm.querySelector('[type="submit"]');
      if (submit.disabled) return;
      submit.disabled = true;
      try { await this.deletePlaylist(); } finally { submit.disabled = false; }
    });
    ui.restorePlaylist.addEventListener('click', () => this.restorePlaylist());
    ui.playlistSearch.addEventListener('input', () => this.renderNavigation());
    ui.playlistSearchToggle.addEventListener('click', () => this.setSearchOpen(ui.playlistSearch.disabled));
    ui.playlistSearch.addEventListener('keydown', event => {
      if (event.key !== 'Escape') return;
      event.preventDefault();
      this.setSearchOpen(false);
    });
    ui.playlistCoverButton.addEventListener('click', () => {
      this.coverTarget = this.activeId;
      ui.playlistCoverInput.click();
    });
    ui.playlistCoverInput.addEventListener('change', () => {
      const file = ui.playlistCoverInput.files[0];
      ui.playlistCoverInput.value = '';
      if (file && this.coverTarget) this.setCover(file, this.coverTarget);
    });
    ui.resetPlaylistCover.addEventListener('click', () => {
      this.coverRequest++;
      this.saveCover(this.activeId, '');
    });
    ui.addTrackToPlaylist.addEventListener('click', () => {
      const open = ui.trackPlaylistPicker.hidden;
      ui.trackPlaylistPicker.hidden = !open;
      ui.addTrackToPlaylist.setAttribute('aria-expanded', String(open));
      if (open) {
        this.renderPicker();
        ui.trackPlaylistSearch.focus({preventScroll: true});
      }
      this.positionMenu();
    });
    ui.trackPlaylistSearch.addEventListener('input', () => {
      this.renderPicker();
      this.positionMenu();
    });
    for (const [button, next] of [[ui.addTrackToQueue, false], [ui.playTrackNext, true]]) {
      button.addEventListener('click', () => {
        const count = enqueueTracks(this.menuTracks, next);
        if (!count) return;
        this.closeMenu(true);
        this.notify(next ? 'Трек будет играть следующим.' : count === 1 ? 'Трек добавлен в очередь.' : 'В очередь добавлено треков: ' + count.toLocaleString('ru-RU') + '.');
      });
    }
    ui.removeTrackFromPlaylist.addEventListener('click', () => this.remove());
    for (const selection of selections) {
      const table = selection.table;
      selection.actions.addEventListener('click', () => {
        if (this.menuButton === selection.actions) this.closeMenu(true);
        else this.openMenu(selection.actions, selection);
      });
      table.addEventListener('click', event => {
        const button = event.target.closest('.music-track-menu-button');
        if (!button) return;
        if (button === this.menuButton && !ui.playlistTrackMenu.hidden) {
          this.closeMenu(true);
          return;
        }
        this.openMenu(button, selection);
      });
      table.addEventListener('contextmenu', event => {
        const button = event.target.closest('.music-track-row')?.querySelector('.music-track-menu-button');
        if (!button) return;
        event.preventDefault();
        this.openMenu(button, selection, event.clientX, event.clientY);
      });
    }
    document.addEventListener('pointerdown', event => {
      if (!ui.playlistTrackMenu.contains(event.target) && !this.menuButton?.contains(event.target)) this.closeMenu();
    });
    document.addEventListener('keydown', event => {
      if (event.key !== 'Escape' || event.defaultPrevented || event.target.closest('dialog')) return;
      if (!ui.playlistTrackMenu.hidden) this.closeMenu(true);
      else selections.forEach(selection => selection.clear(true));
    });
    document.addEventListener('scroll', event => {
      if (!ui.playlistTrackMenu.contains(event.target)) this.closeMenu();
    }, true);
    window.addEventListener('resize', () => this.closeMenu());
    window.addEventListener('report-page-change', () => {
      this.closeMenu();
      selections.forEach(selection => selection.clear());
    });
    window.addEventListener('storage', event => {
      if (this.storage.server || event.key !== this.storageKey) return;
      try {
        const previous = this.items;
        this.items = this.read();
        this.renderNavigation();
        this.renderPage();
        for (const item of previous) {
          if (!this.items.some(playlist => playlist.id === item.id)) this.onPlaylistRemoved(item.id);
        }
        if (this.activeId && !this.items.some(item => item.id === this.activeId)) location.hash = '#overview';
        if (!ui.trackPlaylistPicker.hidden) this.renderPicker();
      } catch {
        this.notify('Не удалось обновить список плейлистов.');
      }
    });
    this.renderNavigation();
  }

  read() {
    const items = JSON.parse(localStorage.getItem(this.storageKey) || '[]');
    if (!Array.isArray(items)) throw new Error('Invalid playlists');
    return items.filter(item => item && typeof item.id === 'string' && /^[a-z0-9-]+$/.test(item.id)
      && typeof item.name === 'string' && Array.isArray(item.tracks)).map(item => ({
        ...item, tracks: item.tracks.filter(track => typeof track?.path === 'string' && track.path)
      }));
  }

  applyItems(items) {
    this.items = items;
    this.renderNavigation();
    this.renderPage();
    if (!this.ui.trackPlaylistPicker.hidden) this.renderPicker();
  }

  async save(edit) {
    let latest, result;
    try {
      if (this.storage.server) {
        const saved = await this.storage.editPlaylists(edit);
        this.applyItems(saved.playlists);
        return saved.result;
      }
      latest = this.read();
      result = edit(latest);
      if (result === null) return null;
      localStorage.setItem(this.storageKey, JSON.stringify(latest));
    } catch {
      return null;
    }
    this.applyItems(latest);
    return result;
  }

  openNameDialog(playlist = null) {
    const ui = this.ui;
    this.nameTargetId = playlist?.id || '';
    let index = this.items.length + 1;
    while (this.items.some(item => item.name === 'Плейлист ' + index)) index++;
    ui.playlistName.value = playlist?.name || 'Плейлист ' + index;
    ui.playlistDialogTitle.textContent = playlist ? 'Переименовать плейлист' : 'Создать плейлист';
    ui.playlistNameSubmit.textContent = playlist ? 'Сохранить' : 'Создать';
    ui.playlistCreateError.textContent = '';
    ui.playlistDialog.showModal();
    ui.playlistName.select();
  }

  async saveName() {
    const ui = this.ui;
    const name = ui.playlistName.value.trim();
    if (!name) {
      ui.playlistCreateError.textContent = 'Введите название плейлиста.';
      ui.playlistName.focus();
      return;
    }
    if (this.nameTargetId) {
      const id = this.nameTargetId;
      const updated = await this.save(items => {
        const item = items.find(playlist => playlist.id === id);
        if (!item) return null;
        item.name = name;
        return true;
      });
      if (!updated) {
        ui.playlistCreateError.textContent = 'Не удалось сохранить название плейлиста.';
        return;
      }
      ui.playlistDialog.close();
      return;
    }
    const id = globalThis.crypto?.randomUUID?.() || Date.now().toString(36) + '-' + Math.random().toString(36).slice(2);
    const created = await this.save(items => items.push({id, name, createdAt: Date.now(), tracks: []}));
    if (!created) {
      ui.playlistCreateError.textContent = 'Не удалось сохранить плейлист.';
      return;
    }
    ui.playlistSearch.value = '';
    this.renderNavigation();
    ui.playlistDialog.close();
    location.hash = '#playlist-' + id;
  }

  async deletePlaylist() {
    const id = this.deleteTargetId;
    const removed = await this.save(items => {
      const index = items.findIndex(playlist => playlist.id === id);
      if (index < 0) return null;
      return {index, playlist: items.splice(index, 1)[0]};
    });
    if (!removed) {
      this.ui.playlistDeleteError.textContent = 'Не удалось удалить плейлист.';
      return;
    }
    this.ui.playlistDeleteDialog.close();
    this.onPlaylistRemoved(id);
    if (this.activeId === id) location.hash = '#overview';
    this.notify('Плейлист «' + removed.playlist.name + '» удалён.', removed);
  }

  async restorePlaylist() {
    const removed = this.undoDelete;
    if (!removed) return;
    const restored = await this.save(items => {
      if (!items.some(item => item.id === removed.playlist.id)) {
        items.splice(removed.index, 0, removed.playlist);
      }
      return true;
    });
    if (!restored) {
      this.notify('Не удалось восстановить плейлист.', removed);
      return;
    }
    this.notify('Плейлист восстановлен.');
    location.hash = '#playlist-' + removed.playlist.id;
  }

  playlistForPage(page) {
    return this.items.find(item => 'playlist-' + item.id === page);
  }

  show(playlist) {
    const changed = (playlist?.id || '') !== this.activeId;
    this.activeId = playlist?.id || '';
    for (const link of this.ui.playlistNavigation.children) {
      if (link.hash === '#playlist-' + this.activeId) link.setAttribute('aria-current', 'page');
      else link.removeAttribute('aria-current');
    }
    if (changed) {
      this.ui.playlistTrackSearch.value = '';
      this.sortKey = null;
      this.sortDirection = 1;
    }
    if (playlist) this.renderPage(changed);
  }

  search(names, query) {
    const filter = query.trim().toLocaleLowerCase('ru');
    return names.filter(item => item.name.toLocaleLowerCase('ru').includes(filter));
  }

  sortNavigation(items) {
    if (this.navigationSort === 'name') {
      return items.sort((a, b) => this.nameCollator.compare(a.name, b.name));
    }
    const date = item => Number.isFinite(item.createdAt) ? item.createdAt : 0;
    return items.reverse().sort((a, b) => date(b) - date(a));
  }

  setSearchOpen(open, restoreFocus = true) {
    const ui = this.ui;
    if (ui.playlistSearch.disabled === !open) return;
    ui.playlistSearchRow.classList.toggle('is-open', open);
    ui.playlistSearchToggle.setAttribute('aria-expanded', String(open));
    ui.playlistSearch.disabled = !open;
    if (open) {
      ui.playlistSearch.focus({preventScroll: true});
    } else {
      ui.playlistSearch.value = '';
      this.renderNavigation();
      if (restoreFocus) ui.playlistSearchToggle.focus({preventScroll: true});
    }
  }

  isPhoto(value) {
    return typeof value === 'string' && /^data:image\/(?:jpeg|png|webp);base64,/.test(value);
  }

  addArtworkImage(tile, src) {
    const image = document.createElement('img');
    image.alt = '';
    image.decoding = 'async';
    image.loading = 'lazy';
    image.addEventListener('error', () => image.remove(), {once: true});
    image.src = src;
    tile.append(image);
  }

  artworkFor(playlist) {
    const art = document.createElement('span');
    art.className = 'playlist-art';
    art.setAttribute('aria-hidden', 'true');
    const note = this.ui.playlistArtworkNote.content;
    if (this.isPhoto(playlist.cover)) {
      art.append(note.cloneNode(true));
      this.addArtworkImage(art, playlist.cover);
      return art;
    }

    const seen = new Set();
    const tiles = [];
    for (const reference of playlist.tracks) {
      const track = this.resolveTrack(reference.path) || reference;
      const album = track.album?.trim();
      const key = album ? (track.artist + '|' + album).toLocaleLowerCase('ru') : this.normalizePath(reference.path);
      if (seen.has(key)) continue;
      seen.add(key);
      const label = String(album || track.title || track.path).trim();
      const tile = document.createElement('span');
      tile.className = 'playlist-art-tile';
      const hue = Array.from(label).reduce((hash, character) => (hash * 31 + character.codePointAt(0)) % 360, 0);
      tile.style.backgroundColor = 'hsl(' + hue + ' 42% 28%)';
      const initials = label.match(/[\p{L}\p{N}][\p{L}\p{N}]?/u);
      tile.textContent = initials ? initials[0].toLocaleUpperCase('ru') : '♪';
      if (this.isPhoto(track.cover) || (location.protocol !== 'file:' && track.cover?.startsWith('/api/cover?'))) {
        this.addArtworkImage(tile, track.cover);
      }
      tiles.push(tile);
      if (tiles.length === 4) break;
    }
    art.dataset.tiles = String(tiles.length);
    if (tiles.length) art.append(...tiles);
    else art.append(note.cloneNode(true));
    return art;
  }

  photoColor(image) {
    try {
      const canvas = document.createElement('canvas');
      canvas.width = canvas.height = 16;
      const context = canvas.getContext('2d');
      context.drawImage(image, 0, 0, 16, 16);
      const pixels = context.getImageData(0, 0, 16, 16).data;
      const buckets = new Map();
      let dominant;
      for (let i = 0; i < pixels.length; i += 4) {
        if (pixels[i + 3] < 128) continue;
        const [red, green, blue] = pixels.subarray(i, i + 3);
        const key = (red >> 5) * 64 + (green >> 5) * 8 + (blue >> 5);
        const bucket = buckets.get(key) || {red: 0, green: 0, blue: 0, count: 0, score: 0};
        bucket.red += red;
        bucket.green += green;
        bucket.blue += blue;
        bucket.count++;
        bucket.score += 1 + (Math.max(red, green, blue) - Math.min(red, green, blue)) / 64;
        buckets.set(key, bucket);
        if (!dominant || bucket.score > dominant.score) dominant = bucket;
      }
      if (!dominant) return '';
      const rgb = [dominant.red, dominant.green, dominant.blue].map(value => Math.round(value / dominant.count));
      return 'rgb(' + rgb.join(' ') + ')';
    } catch {
      return '';
    }
  }

  updateArtworkColor(art) {
    const frame = this.ui.playlistCover;
    const workspace = frame.closest('.app-workspace');
    const images = Array.from(art.querySelectorAll('img'));
    const update = () => {
      if (frame.firstElementChild !== art) return;
      for (const image of images) {
        if (!image.complete || !image.naturalWidth) continue;
        const sampled = this.photoColor(image);
        if (sampled) {
          workspace.style.setProperty('--playlist-color', 'color-mix(in srgb, ' + sampled + ' 58%, #181818)');
          return;
        }
      }
      const tile = art.querySelector('.playlist-art-tile');
      workspace.style.setProperty('--playlist-color', tile?.style.backgroundColor || '');
    };
    images.forEach(image => image.addEventListener('load', update, {once: true}));
    update();
  }

  async setCover(file, id) {
    const request = ++this.coverRequest;
    const url = URL.createObjectURL(file);
    try {
      const image = new Image();
      image.src = url;
      await image.decode();
      if (request !== this.coverRequest) return;
      const {naturalWidth: width, naturalHeight: height} = image;
      const side = Math.min(width, height);
      const canvas = document.createElement('canvas');
      canvas.width = canvas.height = Math.min(side, 384);
      const context = canvas.getContext('2d');
      context.fillStyle = '#242424';
      context.fillRect(0, 0, canvas.width, canvas.height);
      context.drawImage(image, (width - side) / 2, (height - side) / 2, side, side, 0, 0, canvas.width, canvas.height);
      await this.saveCover(id, canvas.toDataURL('image/webp', 0.82));
    } catch {
      if (request === this.coverRequest) this.notify('Не удалось открыть фото. Выберите другой файл.');
    } finally {
      URL.revokeObjectURL(url);
    }
  }

  async saveCover(id, cover) {
    const updated = await this.save(items => {
      const playlist = items.find(item => item.id === id);
      if (!playlist) return null;
      if (cover) playlist.cover = cover;
      else delete playlist.cover;
      return true;
    });
    if (!updated) this.notify('Не удалось сохранить фото плейлиста.');
  }

  renderNavigation() {
    const ui = this.ui;
    const items = this.sortNavigation(this.search(this.items, ui.playlistSearch.value));
    ui.playlistNavigation.replaceChildren(...items.map(item => {
      const link = document.createElement('a');
      link.href = '#playlist-' + item.id;
      const title = document.createElement('span');
      title.className = 'playlist-nav-title';
      title.textContent = item.name;
      link.append(this.artworkFor(item), title);
      link.title = item.name;
      link.setAttribute('aria-label', item.name);
      if (item.id === this.activeId) link.setAttribute('aria-current', 'page');
      return link;
    }));
    ui.playlistNavigationEmpty.hidden = !this.items.length || Boolean(items.length);
  }

  renderPage(reset = false) {
    const item = this.items.find(playlist => playlist.id === this.activeId);
    if (!item) return;
    const ui = this.ui;
    ui.playlistTitle.textContent = item.name;
    document.title = item.name + ' — ' + this.reportTitle;
    const art = this.artworkFor(item);
    ui.playlistCover.replaceChildren(art);
    this.updateArtworkColor(art);
    const customPhoto = this.isPhoto(item.cover);
    ui.resetPlaylistCover.disabled = !customPhoto;
    ui.resetPlaylistCover.title = customPhoto ? 'Вернуть автоматическую обложку' : 'Уже используется автоматическая обложка';
    this.rows = item.tracks.map((track, index) => this.makeTrackRow(track, index + 1));
    ui.playlistSummary.textContent = this.formatTrackSummary(this.rows);
    this.sortRows(reset);
    this.pager.activate();
  }

  makeTrackRow(track, number) {
    const source = this.trackCard(track.path);
    const row = source ? source.cloneNode(true) : this.ui.playlistUnavailableTrack.content.querySelector('tbody').cloneNode(true);
    if (source) {
      row.querySelector('.music-track-select').checked = false;
      const details = row.querySelector('.music-track-details');
      details.id = 'playlist-details-' + number;
      details.hidden = true;
      const toggle = row.querySelector('.music-details-toggle');
      toggle.setAttribute('aria-controls', details.id);
      toggle.setAttribute('aria-expanded', 'false');
      row.querySelector('.music-track-menu-button').setAttribute('aria-expanded', 'false');
      row.querySelectorAll('.trash-one, .music-action-single, .enrichment-button, .music-card-status').forEach(node => node.remove());
    } else {
      const title = track.title || track.path;
      row.dataset.filePath = track.path;
      row.dataset.sortName = title.toLowerCase();
      row.dataset.sortArtist = (track.artist || '').toLowerCase();
      row.dataset.sortAlbum = (track.album || '').toLowerCase();
      row.dataset.musicSearch = [row.dataset.sortName, row.dataset.sortArtist, row.dataset.sortAlbum].join(' ');
      row.dataset.duration = '0';
      row.querySelector('.music-title').textContent = title;
      row.querySelector('.music-track-artist').textContent = track.artist || '—';
      row.querySelector('.music-track-album').textContent = track.album || '—';
      row.querySelector('.music-track-menu-button').setAttribute('aria-label', 'Действия: ' + title);
    }
    row.hidden = false;
    row.dataset.sortNumber = number;
    row.querySelector(source ? '.music-track-index' : '.music-track-number').textContent = number;
    return row;
  }

  sortRows(reset = true) {
    this.sortTrackTable(this.ui.playlistTracks, this.rows, this.sortKey, this.sortDirection);
    this.filterTracks(reset);
  }

  filterTracks(reset = true) {
    const ui = this.ui;
    const query = ui.playlistTrackSearch.value.trim().toLowerCase();
    const matches = query ? this.rows.filter(row => row.dataset.musicSearch.includes(query)) : this.rows;
    ui.playlistTracks.hidden = matches.length === 0;
    ui.playlistTrackEmpty.classList.toggle('visible', Boolean(query) && matches.length === 0);
    this.playlistSelection.setItems(matches, reset);
  }

  play(path) {
    const track = this.resolveTrack(path);
    if (!track) return;
    const queue = this.rows.map(row => this.resolveTrack(row.dataset.filePath)).filter(Boolean);
    this.playTracks(track, queue, this.activeId);
  }

  openMenu(button, selection, x, y) {
    this.closeMenu();
    const row = button.closest('tbody');
    const rows = row && !selection.selected.has(row) ? [row] : selection.selectedRows();
    const tracks = rows.map(item => this.resolveTrack(item.dataset.filePath)).filter(Boolean);
    const playlistId = row && rows.length === 1 && selection === this.playlistSelection ? this.activeId : '';
    if (!tracks.length && !playlistId) return;
    this.menuTracks = tracks;
    this.menuPlaylistId = playlistId;
    this.menuPath = row?.dataset.filePath;
    this.menuButton = button;
    this.menuPoint = Number.isFinite(x) && (x || y) ? {x, y} : null;
    this.ui.trackPlaylistSearch.value = '';
    this.ui.addTrackToPlaylist.hidden = !tracks.length;
    this.ui.playTrackNext.hidden = tracks.length !== 1;
    this.ui.addTrackToQueue.hidden = !tracks.length;
    this.ui.removeTrackFromPlaylist.hidden = !playlistId;
    this.ui.playlistTrackMenu.hidden = false;
    button.setAttribute('aria-expanded', 'true');
    this.positionMenu();
    const first = tracks.length ? this.ui.addTrackToPlaylist : this.ui.removeTrackFromPlaylist;
    first.focus({preventScroll: true});
  }

  positionMenu() {
    const menu = this.ui.playlistTrackMenu;
    if (!this.menuButton || menu.hidden) return;
    const anchor = this.menuButton.getBoundingClientRect();
    const x = this.menuPoint ? this.menuPoint.x : anchor.right - menu.offsetWidth;
    const y = this.menuPoint ? this.menuPoint.y : anchor.bottom + 4;
    menu.style.left = Math.max(8, Math.min(x, innerWidth - menu.offsetWidth - 8)) + 'px';
    menu.style.top = Math.max(8, Math.min(y, innerHeight - menu.offsetHeight - 8)) + 'px';
  }

  closeMenu(restoreFocus = false) {
    if (this.ui.playlistTrackMenu.hidden) return;
    this.ui.playlistTrackMenu.hidden = true;
    this.ui.trackPlaylistPicker.hidden = true;
    this.ui.addTrackToPlaylist.setAttribute('aria-expanded', 'false');
    this.menuButton?.setAttribute('aria-expanded', 'false');
    if (restoreFocus) this.menuButton?.focus({preventScroll: true});
    this.menuButton = null;
    this.menuTracks = [];
    this.menuPlaylistId = '';
    this.menuPath = '';
  }

  renderPicker() {
    const ui = this.ui;
    const items = this.search(this.items, ui.trackPlaylistSearch.value);
    const current = this.menuTracks.map(track => this.normalizePath(track.path));
    const buttons = items.map(item => {
      const button = document.createElement('button');
      button.type = 'button';
      button.textContent = item.name;
      button.title = item.name;
      const existing = new Set(item.tracks.map(track => this.normalizePath(track.path)));
      if (current.every(path => existing.has(path))) {
        button.disabled = true;
        button.title = item.name + (current.length === 1 ? ' · Трек уже добавлен' : ' · Выбранные треки уже добавлены');
      }
      button.addEventListener('click', () => this.add(item.id));
      return button;
    });
    if (!buttons.length) {
      const hint = document.createElement('p');
      hint.className = 'playlist-hint';
      hint.textContent = this.items.length ? 'Плейлисты не найдены.' : 'Сначала создайте плейлист в левом меню.';
      buttons.push(hint);
    }
    ui.trackPlaylistOptions.replaceChildren(...buttons);
  }

  async add(id) {
    if (!this.menuTracks.length || this.addingToPlaylist) return;
    const tracks = this.menuTracks;
    const menu = this.menuButton;
    this.addingToPlaylist = true;
    let result;
    try {
      result = await this.save(items => {
        const item = items.find(playlist => playlist.id === id);
        if (!item) return null;
        const existing = new Set(item.tracks.map(track => this.normalizePath(track.path)));
        let count = 0;
        for (const {path, title, artist, album} of tracks) {
          const key = this.normalizePath(path);
          if (existing.has(key)) continue;
          item.tracks.push({path, title, artist, album});
          existing.add(key);
          count++;
        }
        return {name: item.name, count};
      });
    } finally {
      this.addingToPlaylist = false;
    }
    if (result === null) {
      this.notify(tracks.length === 1 ? 'Не удалось добавить трек в плейлист.' : 'Не удалось добавить треки в плейлист.');
      return;
    }
    if (this.menuButton === menu && this.menuTracks === tracks) this.closeMenu(true);
    const {name, count} = result;
    if (!count) this.notify(tracks.length === 1 ? 'Трек уже есть в «' + name + '».' : 'Выбранные треки уже есть в «' + name + '».');
    else if (tracks.length === 1) this.notify('Трек добавлен в «' + name + '».');
    else this.notify('В «' + name + '» добавлено треков: ' + count.toLocaleString('ru-RU') + '.');
  }

  async remove() {
    const id = this.menuPlaylistId;
    const path = this.menuPath;
    if (!id || id !== this.activeId || !path) return;
    const table = this.ui.playlistTracks;
    const index = Array.from(table.tBodies).indexOf(this.menuButton.closest('tbody'));
    const key = this.normalizePath(path);
    const menu = this.menuButton;
    const name = await this.save(items => {
      const item = items.find(playlist => playlist.id === id);
      if (!item) return null;
      const remaining = item.tracks.filter(track => this.normalizePath(track.path) !== key);
      if (remaining.length === item.tracks.length) return null;
      item.tracks = remaining;
      return item.name;
    });
    if (name === null) {
      this.notify('Не удалось удалить трек из плейлиста.');
      return;
    }
    if (this.menuButton === menu) this.closeMenu();
    this.onTrackRemoved(id, path);
    const row = table.tBodies[Math.max(0, Math.min(index, table.tBodies.length - 1))];
    if (this.activeId === id) (row?.querySelector('.music-track-menu-button') || this.ui.playlistCoverButton).focus({preventScroll: true});
    this.notify('Трек удалён из «' + name + '».');
  }

  async replacePaths(moves) {
    if (!moves.length || !this.items.length) return;
    const destinations = new Map(moves.map(item => [this.normalizePath(item.source), item.destination]));
    if (!this.items.some(item => item.tracks.some(track => destinations.has(this.normalizePath(track.path))))) return;
    const updated = await this.save(items => {
      for (const item of items) {
        const seen = new Set();
        item.tracks = item.tracks.map(track => {
          const path = destinations.get(this.normalizePath(track.path)) || track.path;
          return {...track, path};
        }).filter(track => {
          const key = this.normalizePath(track.path);
          if (seen.has(key)) return false;
          seen.add(key);
          return true;
        });
      }
      return true;
    });
    if (!updated) this.notify('Не удалось обновить пути треков в плейлистах.');
  }

  notify(message, undo = null) {
    const status = this.ui.playlistStatus;
    this.undoDelete = undo;
    this.ui.playlistStatusMessage.textContent = message;
    this.ui.restorePlaylist.hidden = !undo;
    status.hidden = false;
    clearTimeout(this.statusTimer);
    if (!undo) this.statusTimer = setTimeout(() => { status.hidden = true; }, 3500);
  }
}
"""
