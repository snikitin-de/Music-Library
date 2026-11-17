"""The report's queue and browser-local listening history."""


def playback_panel_html(close_icon: str, note_icon: str, grip_icon: str) -> str:
    return f"""
    <aside class="playback-panel" id="playbackPanel" aria-label="Очередь и история прослушивания" hidden>
      <header class="playback-panel-header">
        <div class="playback-tabs" role="tablist" aria-label="Воспроизведение">
          <button id="playbackQueueTab" type="button" role="tab" aria-controls="playbackQueueView" aria-selected="true">Очередь</button>
          <button id="playbackHistoryTab" type="button" role="tab" aria-controls="playbackHistoryView" aria-selected="false" tabindex="-1">Недавно прослушано</button>
        </div>
        <button class="window-close" id="playbackPanelClose" type="button" aria-label="Закрыть панель воспроизведения" title="Закрыть">{close_icon}</button>
      </header>
      <div class="playback-panel-view" id="playbackQueueView" role="tabpanel" aria-labelledby="playbackQueueTab" tabindex="0">
        <section id="playbackCurrentSection" hidden>
          <h2>Сейчас играет</h2>
          <ul id="playbackCurrent"></ul>
        </section>
        <section id="playbackManualSection" hidden>
          <h2>Следующие в очереди</h2>
          <ul id="playbackManual"></ul>
        </section>
        <section id="playbackSourceSection" hidden>
          <h2 id="playbackSourceTitle">Далее по списку</h2>
          <ul id="playbackSource"></ul>
          <button class="small playback-panel-more" id="playbackSourceMore" type="button" hidden>Показать ещё</button>
        </section>
      </div>
      <div class="playback-panel-view" id="playbackHistoryView" role="tabpanel" aria-labelledby="playbackHistoryTab" tabindex="0" hidden>
        <p class="playback-panel-note" id="playbackHistoryStorage" hidden>Не удалось сохранить историю.</p>
        <ul id="playbackHistory"></ul>
      </div>
    </aside>
    <template id="playbackPanelTrack">
      <li class="playback-panel-row">
        <button class="playback-panel-icon playback-panel-reorder" type="button" draggable="true" hidden>{grip_icon}</button>
        <button class="playback-panel-track" type="button">
          <span class="playback-panel-art" aria-hidden="true">{note_icon}</span>
          <span class="playback-panel-track-text"><strong></strong><small></small><time hidden></time></span>
        </button>
        <button class="playback-panel-icon playback-panel-remove" type="button" hidden>{close_icon}</button>
      </li>
    </template>
"""


PLAYBACK_PANEL_JS = r"""
class ReportListeningHistory {
  constructor(key, storage = () => window.localStorage) {
    this.key = key;
    this.storage = storage;
    this.entries = [];
    this.reload();
  }

  reload() {
    try {
      const entries = JSON.parse(this.storage().getItem(this.key) || '[]');
      this.entries = Array.isArray(entries) ? entries.filter(entry =>
        typeof entry?.path === 'string' && entry.path && Number.isFinite(entry.playedAt) &&
        Number.isFinite(new Date(entry.playedAt).getTime())).slice(0, 200) : [];
      this.persistent = true;
    } catch {
      this.persistent = false;
    }
  }

  add(track, playedAt = Date.now()) {
    if (this.persistent) this.reload();
    const {path, title, artist} = track;
    this.entries.unshift({path, title: title || track.name || path, artist: artist || '', playedAt});
    this.entries = this.entries.slice(0, 200);
    try {
      this.storage().setItem(this.key, JSON.stringify(this.entries));
      this.persistent = true;
    } catch {
      this.persistent = false;
    }
  }
}

class ReportPlaybackPanel {
  constructor(player, {libraryKey, storage, resolveTrack, playHistoryTrack, sourceName}) {
    this.player = player;
    this.storage = storage;
    this.resolveTrack = resolveTrack;
    this.playHistoryTrack = playHistoryTrack;
    this.sourceName = sourceName;
    this.history = new ReportListeningHistory('music-report-history:' + libraryKey);
    this.historyWrites = Promise.resolve();
    this.dateFormat = new Intl.DateTimeFormat('ru-RU', {dateStyle: 'medium', timeStyle: 'short'});
    this.sourceLimit = 30;
    const ids = ['queueToggle', 'globalQueueToggle', 'playbackPanel', 'playbackPanelClose', 'playbackQueueTab', 'playbackHistoryTab',
      'playbackQueueView', 'playbackHistoryView', 'playbackCurrentSection', 'playbackCurrent',
      'playbackManualSection', 'playbackManual', 'playbackSourceSection', 'playbackSourceTitle',
      'playbackSource', 'playbackSourceMore', 'playbackHistoryStorage', 'playbackHistory', 'playbackPanelTrack'];
    this.ui = Object.fromEntries(ids.map(id => [id, document.getElementById(id)]));
    const ui = this.ui;
    this.tabs = [ui.playbackQueueTab, ui.playbackHistoryTab];
    this.activeTab = ui.playbackQueueTab;
    this.toggles = [ui.queueToggle, ui.globalQueueToggle];
    this.activeToggle = ui.queueToggle;
    for (const toggle of this.toggles) {
      toggle.addEventListener('click', () => {
        this.activeToggle = toggle;
        this.setOpen(ui.playbackPanel.hidden);
      });
    }
    ui.playbackPanelClose.addEventListener('click', () => this.setOpen(false));
    ui.playbackPanel.addEventListener('keydown', event => {
      if (event.key !== 'Escape') return;
      event.stopPropagation();
      this.setOpen(false);
    });
    for (const tab of this.tabs) {
      tab.addEventListener('click', () => this.selectTab(tab));
      tab.addEventListener('keydown', event => {
        const next = {ArrowLeft: this.tabs.find(other => other !== tab),
          ArrowRight: this.tabs.find(other => other !== tab), Home: this.tabs[0], End: this.tabs[1]}[event.key];
        if (!next) return;
        event.preventDefault();
        this.selectTab(next);
        next.focus({preventScroll: true});
      });
    }
    ui.playbackSourceMore.addEventListener('click', () => {
      this.sourceLimit += 30;
      this.renderQueue();
    });
    window.addEventListener('storage', event => {
      if (this.storage.server || (event.key !== this.history.key && event.key !== null)) return;
      this.history.reload();
      this.refresh();
    });
  }

  setOpen(open) {
    this.ui.playbackPanel.hidden = !open;
    for (const toggle of this.toggles) toggle.setAttribute('aria-expanded', String(open));
    if (open) {
      this.refresh();
      this.activeTab.focus({preventScroll: true});
    } else {
      this.activeToggle.focus({preventScroll: true});
    }
  }

  selectTab(selected) {
    this.activeTab = selected;
    for (const tab of this.tabs) {
      const active = tab === selected;
      tab.setAttribute('aria-selected', String(active));
      tab.tabIndex = active ? 0 : -1;
      document.getElementById(tab.getAttribute('aria-controls')).hidden = !active;
    }
    this.refresh();
  }

  record(track) {
    if (!this.storage.server) {
      this.history.add(track);
      if (this.activeTab === this.ui.playbackHistoryTab) this.refresh();
      return;
    }
    const {path, title, artist} = track;
    const entry = {path, title: title || track.name || path, artist: artist || '', playedAt: Date.now()};
    this.historyWrites = this.historyWrites.then(async () => {
      const result = await this.storage.request({action: 'listen', entry});
      this.applyHistory(result.history);
    }).catch(() => {
      this.history.persistent = false;
      this.refresh();
    });
  }

  applyHistory(entries) {
    this.history.entries = entries;
    this.history.persistent = true;
    if (this.activeTab === this.ui.playbackHistoryTab) this.refresh();
  }

  refresh() {
    if (this.ui.playbackPanel.hidden) return;
    if (this.activeTab === this.ui.playbackQueueTab) this.renderQueue();
    else this.renderHistory();
  }

  renderQueue() {
    const ui = this.ui;
    const {track, manualQueue} = this.player;
    const upcoming = this.player.sourceUpcoming();
    ui.playbackCurrentSection.hidden = !track;
    ui.playbackCurrent.replaceChildren(...(track ? [this.trackRow(track, {current: true, play: () => this.player.toggle()})] : []));
    ui.playbackManualSection.hidden = !manualQueue.length;
    ui.playbackManual.replaceChildren(...manualQueue.map((item, index) => this.trackRow(item, {
      play: () => this.player.playQueued(index),
      remove: () => this.player.removeQueued(index),
      queueIndex: index,
    })));
    ui.playbackSourceSection.hidden = !upcoming.length;
    const name = this.sourceName();
    ui.playbackSourceTitle.textContent = name ? 'Далее из: ' + name : 'Далее по списку';
    ui.playbackSource.replaceChildren(...upcoming.slice(0, this.sourceLimit).map(item =>
      this.trackRow(item, {play: () => this.player.start(item)})));
    ui.playbackSourceMore.hidden = upcoming.length <= this.sourceLimit;
  }

  renderHistory() {
    const ui = this.ui;
    ui.playbackHistory.replaceChildren(...this.history.entries.map(entry => {
      const track = this.resolveTrack(entry.path);
      return this.trackRow({...entry, cover: track?.cover}, {
        play: track ? () => this.playHistoryTrack(track.path) : null,
        playedAt: entry.playedAt,
      });
    }));
    ui.playbackHistoryStorage.hidden = this.history.persistent;
  }

  trackRow(track, {play, remove, current = false, playedAt = null, queueIndex = null} = {}) {
    const row = this.ui.playbackPanelTrack.content.firstElementChild.cloneNode(true);
    row.classList.toggle('is-current', current);
    const button = row.querySelector('.playback-panel-track');
    const title = track.title || track.name || track.path;
    const titleNode = row.querySelector('strong');
    titleNode.textContent = title;
    titleNode.title = title;
    if (queueIndex !== null) this.bindReorder(row, track, queueIndex, title);
    const artist = row.querySelector('small');
    artist.textContent = track.artist || '';
    artist.hidden = !track.artist;
    if (track.cover) {
      const image = document.createElement('img');
      image.alt = '';
      image.loading = 'lazy';
      image.addEventListener('error', () => image.remove(), {once: true});
      image.src = track.cover;
      row.querySelector('.playback-panel-art').append(image);
    }
    if (playedAt !== null) {
      const time = row.querySelector('time');
      time.dateTime = new Date(playedAt).toISOString();
      time.textContent = this.dateFormat.format(playedAt);
      time.hidden = false;
    }
    button.disabled = !play;
    if (play) {
      button.addEventListener('click', () => {
        this.activeTab.focus({preventScroll: true});
        play();
      });
    }
    if (remove) {
      const removeButton = row.querySelector('.playback-panel-remove');
      removeButton.hidden = false;
      removeButton.title = 'Убрать из очереди';
      removeButton.setAttribute('aria-label', 'Убрать из очереди: ' + title);
      removeButton.addEventListener('click', () => {
        this.activeTab.focus({preventScroll: true});
        remove();
      });
    }
    return row;
  }

  bindReorder(row, track, index, title) {
    const handle = row.querySelector('.playback-panel-reorder');
    handle.hidden = false;
    handle.title = 'Переместить в очереди';
    handle.setAttribute('aria-label', 'Переместить в очереди: ' + title);
    handle.addEventListener('keydown', event => {
      if (event.key !== 'ArrowUp' && event.key !== 'ArrowDown') return;
      event.preventDefault();
      const target = index + (event.key === 'ArrowUp' ? -1 : 1);
      if (this.player.moveQueued(index, target)) {
        this.ui.playbackManual.children[target].querySelector('.playback-panel-reorder').focus({preventScroll: true});
      }
    });
    handle.addEventListener('dragstart', event => {
      this.draggedTrack = track;
      event.dataTransfer.effectAllowed = 'move';
      event.dataTransfer.setData('text/plain', String(index + 1));
    });
    handle.addEventListener('dragend', () => {
      this.draggedTrack = null;
      this.ui.playbackManual.querySelector('.queue-drop-target')?.classList.remove('queue-drop-target');
    });
    row.addEventListener('dragover', event => {
      if (!this.draggedTrack || this.draggedTrack === track) return;
      event.preventDefault();
      event.dataTransfer.dropEffect = 'move';
      row.classList.add('queue-drop-target');
    });
    row.addEventListener('dragleave', event => {
      if (!row.contains(event.relatedTarget)) row.classList.remove('queue-drop-target');
    });
    row.addEventListener('drop', event => {
      if (!this.draggedTrack) return;
      event.preventDefault();
      row.classList.remove('queue-drop-target');
      const from = this.player.manualQueue.indexOf(this.draggedTrack);
      this.draggedTrack = null;
      this.player.moveQueued(from, index);
    });
  }
}
"""
