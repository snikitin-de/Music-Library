"""Browser client for the server's local JSON storage."""

REPORT_USER_STORAGE_JS = r"""
class ReportLibraryStorage {
  constructor(libraryKey) {
    this.server = location.protocol === 'http:' || location.protocol === 'https:';
    this.migrationKey = 'music-report-migrated:' + libraryKey;
    this.edits = Promise.resolve();
  }

  async request(change) {
    const body = change ? JSON.stringify(change) : undefined;
    const response = await fetch('/api/player-state', body ? {
      method: 'POST', headers: {'Content-Type': 'application/json'}, body,
      keepalive: new Blob([body]).size < 60000,
    } : {cache: 'no-store'});
    const result = await response.json().catch(() => null);
    if (!response.ok || !result?.ok) {
      const message = result?.error || 'Сервер не смог открыть данные плеера.';
      throw Object.assign(new Error(message), {status: response.status});
    }
    return result;
  }

  async load(legacyBackup) {
    const state = await this.request();
    let migrated = false;
    try { migrated = localStorage.getItem(this.migrationKey) === '1'; } catch {}
    if (migrated || (!legacyBackup.playlists.length && !legacyBackup.history.length)) return state;
    try {
      const imported = await this.request({action: 'import', backup: legacyBackup});
      try { localStorage.setItem(this.migrationKey, '1'); } catch {}
      return {...state, ...imported};
    } catch {
      return {...state, migrationFailed: true};
    }
  }

  editPlaylists(edit) {
    const attempt = this.edits.then(async () => {
      for (let retries = 0; retries < 4; retries++) {
        const current = await this.request();
        const result = edit(current.playlists);
        if (result === null) return {result, playlists: current.playlists};
        try {
          const saved = await this.request({
            action: 'playlists', revision: current.playlistsRevision, playlists: current.playlists,
          });
          return {result, playlists: saved.playlists};
        } catch (error) {
          if (error.status !== 409 || retries === 3) throw error;
        }
      }
    });
    this.edits = attempt.catch(() => {});
    return attempt;
  }
}

class ReportSessionStorage {
  constructor(storage, player, onError) {
    this.storage = storage;
    this.player = player;
    this.onError = onError;
    this.ready = false;
    this.token = '';
    this.signature = '';
    this.timestamp = 0;
    this.lastProgress = 0;
    this.lastPosition = -1;
  }

  now() {
    this.timestamp = Math.max(Date.now(), this.timestamp + 1);
    return this.timestamp;
  }

  enable(restored = null) {
    this.ready = true;
    if (restored) this.timestamp = restored.updatedAt;
    this.signature = restored ? this.snapshotSignature(this.player.snapshot()) : '';
  }

  snapshotSignature(snapshot) {
    const {position, listenRecorded, ...structure} = snapshot;
    return JSON.stringify(structure);
  }

  changed() {
    if (!this.ready) return;
    const snapshot = this.player.snapshot();
    const signature = this.snapshotSignature(snapshot);
    if (signature === this.signature || (!this.signature && !snapshot.track && !snapshot.manualQueue.length)) return;
    this.signature = signature;
    this.token = crypto.randomUUID?.() || Date.now().toString(36) + Math.random().toString(36).slice(2);
    const token = this.token;
    this.lastPosition = snapshot.position;
    this.lastProgress = Date.now();
    this.storage.request({action: 'session', session: {...snapshot, token, updatedAt: this.now()}}).catch(() => {
      if (this.token === token) {
        this.signature = '';
        this.token = '';
        this.onError();
      }
    });
  }

  progress(force = false, claim = false) {
    if (!this.ready || !this.player.track) return;
    const position = this.player.position();
    if (!this.token) {
      if (!claim && this.player.audio.paused) return;
      this.signature = '';
      this.changed();
      return;
    }
    const now = Date.now();
    if (!force && (now - this.lastProgress < 3000 || Math.abs(position - this.lastPosition) < .5)) return;
    this.lastPosition = position;
    this.lastProgress = now;
    this.storage.request({action: 'position', token: this.token, updatedAt: this.now(),
      position, listenRecorded: this.player.listenRecorded}).catch(this.onError);
  }
}

function libraryBackup(playlists, history) {
  return {version: 1, playlists, history};
}

function downloadLibraryBackup(backup) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(backup, null, 2)], {type: 'application/json'}));
  const link = document.createElement('a');
  link.href = url;
  link.download = 'music-library-backup.json';
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
"""
