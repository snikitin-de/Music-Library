"""One shared audio source for the standalone report, independent of mounted cards."""

REPORT_PLAYER_JS = r"""
class ReportPlayer {
  constructor(audio, {normalizePath, play, seek, onChange = () => {}, onUpdate = () => {}, onQueueChange = () => {}, onListen = () => {}}) {
    this.audio = audio;
    this.normalizePath = normalizePath;
    this.play = play;
    this.seekPlayback = seek;
    this.onChange = onChange;
    this.onUpdate = onUpdate;
    this.onQueueChange = onQueueChange;
    this.track = null;
    this.pending = null;
    this.queue = [];
    this.queueByPath = new Map();
    this.queueScope = '';
    this.sourceTrackKey = '';
    this.manualQueue = [];
    this.playingQueuedTrack = false;
    this.listenRecorded = false;
    this.resumePosition = null;
    this.shuffle = false;
    this.shufflePlayed = new Set();
    this.shuffleQueue = [];
    audio.addEventListener('loadedmetadata', () => this.applyResumePosition());
    for (const event of ['play', 'pause', 'ended', 'timeupdate', 'durationchange', 'loadedmetadata', 'volumechange', 'error', 'emptied']) {
      audio.addEventListener(event, () => this.onUpdate());
    }
    audio.addEventListener('ended', () => {
      if (!this.repeat) void this.step(1);
    });
    audio.addEventListener('playing', () => {
      if (!this.track || audio.paused || audio.ended || this.listenRecorded) return;
      this.listenRecorded = true;
      onListen(this.track);
    });
  }
  matches(path) { return Boolean(this.track && this.normalizePath(this.track.path) === this.normalizePath(path)); }
  setQueue(tracks, scope = this.queueScope) {
    const byPath = new Map();
    for (const track of tracks) {
      const key = this.normalizePath(track.path || '');
      if (key && !byPath.has(key)) byPath.set(key, track);
    }
    this.queueByPath = byPath;
    this.queue = Array.from(byPath.values());
    if (scope !== this.queueScope) {
      this.queueScope = scope;
      this.sourceTrackKey = '';
      this.shufflePlayed.clear();
    }
    if (this.shuffle) this.prepareShuffle();
    this.onUpdate();
    this.onQueueChange();
  }
  prepareShuffle() {
    this.shuffleQueue = this.queue.filter(track => !this.shufflePlayed.has(this.normalizePath(track.path)));
    for (let i = this.shuffleQueue.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [this.shuffleQueue[i], this.shuffleQueue[j]] = [this.shuffleQueue[j], this.shuffleQueue[i]];
    }
  }
  setShuffle(enabled) {
    if (this.shuffle === enabled) return;
    this.shuffle = enabled;
    this.shufflePlayed.clear();
    if (enabled && this.sourceTrackKey) this.shufflePlayed.add(this.sourceTrackKey);
    if (enabled && this.track) this.shufflePlayed.add(this.normalizePath(this.track.path));
    if (enabled) this.prepareShuffle();
    else this.shuffleQueue = [];
    this.onUpdate();
    this.onQueueChange();
  }
  get repeat() { return this.audio.loop === true; }
  setRepeat(enabled) {
    this.audio.loop = enabled;
    this.onUpdate();
    this.onQueueChange();
  }
  enqueue(track, next = false) {
    return this.enqueueTracks([track], next) > 0;
  }
  enqueueTracks(tracks, next = false) {
    const queued = tracks.filter(track => track?.path).map(track => ({...track}));
    if (!queued.length) return 0;
    this.manualQueue = next ? queued.concat(this.manualQueue) : this.manualQueue.concat(queued);
    this.onUpdate();
    this.onQueueChange();
    return queued.length;
  }
  moveQueued(from, to) {
    if (!Number.isInteger(to) || to < 0 || to >= this.manualQueue.length || from === to) return false;
    const track = this.takeQueued(from);
    if (!track) return false;
    this.manualQueue.splice(to, 0, track);
    this.onUpdate();
    this.onQueueChange();
    return true;
  }
  position() {
    return this.resumePosition ?? (Number.isFinite(this.audio.currentTime) ? this.audio.currentTime : 0);
  }
  applyResumePosition() {
    if (this.resumePosition === null || !this.audio.readyState) return;
    const duration = this.audio.duration;
    this.audio.currentTime = Number.isFinite(duration) ? Math.min(duration, this.resumePosition) : this.resumePosition;
    this.resumePosition = null;
  }
  snapshot() {
    const trackData = ({path, title, artist, album, name}) => ({path, title, artist, album, name});
    return {
      track: this.track ? trackData(this.track) : null,
      manualQueue: this.manualQueue.map(trackData),
      position: this.position(),
      scope: this.queueScope,
      anchor: this.sourceTrackKey,
      source: this.sourceTrackKey ? this.queue.map(track => track.path) : [],
      shuffleOrder: this.sourceTrackKey ? this.shuffleQueue.map(track => track.path) : [],
      shufflePlayed: [...this.shufflePlayed],
      shuffle: this.shuffle,
      repeat: this.repeat,
      playingQueuedTrack: this.playingQueuedTrack,
      listenRecorded: this.listenRecorded,
    };
  }
  restore(state, resolveTrack) {
    this.setQueue(state.source.map(path => resolveTrack({path})).filter(Boolean), state.scope);
    this.manualQueue = state.manualQueue.map(resolveTrack).filter(Boolean);
    const track = state.track && resolveTrack(state.track);
    if (track) {
      this.audio.preload = 'metadata';
      this.select(track, !state.playingQueuedTrack);
      this.resumePosition = state.position;
      this.applyResumePosition();
      this.listenRecorded = state.listenRecorded;
    }
    this.sourceTrackKey = this.normalizePath(state.anchor);
    this.shuffle = state.shuffle;
    this.audio.loop = state.repeat;
    this.shufflePlayed = new Set(state.shufflePlayed.map(this.normalizePath));
    this.shuffleQueue = state.shuffleOrder.map(path => this.queueByPath.get(this.normalizePath(path))).filter(Boolean);
    this.onUpdate();
    this.onQueueChange();
  }
  takeQueued(index) {
    if (!Number.isInteger(index) || index < 0 || index >= this.manualQueue.length) return null;
    return this.manualQueue.splice(index, 1)[0];
  }
  removeQueued(index) {
    if (!this.takeQueued(index)) return;
    this.onUpdate();
    this.onQueueChange();
  }
  updateQueuedTracks(changes) {
    let updated = false;
    const queue = this.manualQueue.flatMap(track => {
      const path = this.normalizePath(track.path);
      if (!changes.has(path)) return [track];
      updated = true;
      const replacement = changes.get(path);
      return replacement ? [{...replacement}] : [];
    });
    if (!updated) return;
    this.manualQueue = queue;
    this.onUpdate();
    this.onQueueChange();
  }
  async playQueued(index) {
    const track = this.takeQueued(index);
    if (track) await this.start(track, false);
  }
  sourceUpcoming() {
    if (!this.sourceTrackKey) return [];
    if (this.shuffle) {
      return this.shuffleQueue.filter(track => !this.shufflePlayed.has(this.normalizePath(track.path)));
    }
    const index = this.queue.indexOf(this.queueByPath.get(this.sourceTrackKey));
    return index < 0 ? [] : this.queue.slice(index + 1);
  }
  neighbour(direction) {
    if (direction === 1 && this.manualQueue.length) return this.manualQueue[0];
    if (!this.sourceTrackKey) return null;
    const anchor = this.queueByPath.get(this.sourceTrackKey);
    if (direction === -1 && this.playingQueuedTrack) return anchor || null;
    if (this.shuffle) {
      if (direction === 1) {
        return this.shuffleQueue.find(track => !this.shufflePlayed.has(this.normalizePath(track.path))) || null;
      }
      const history = Array.from(this.shufflePlayed);
      const index = history.indexOf(this.sourceTrackKey);
      for (let i = index - 1; i >= 0; i--) {
        const previous = this.queueByPath.get(history[i]);
        if (previous) return previous;
      }
      return null;
    }
    const index = this.queue.indexOf(anchor);
    return index >= 0 ? this.queue[index + direction] : null;
  }
  canStep(direction) { return Boolean(this.neighbour(direction)); }
  async step(direction) {
    if (direction === 1 && this.manualQueue.length) {
      await this.playQueued(0);
      return;
    }
    const track = this.neighbour(direction);
    if (track) await this.start(track);
  }
  async start(track, fromSource = true) {
    if (!track?.path) return;
    if (!this.select(track, fromSource)) {
      this.cancel();
      this.audio.pause();
      this.resumePosition = null;
      this.audio.currentTime = 0;
      this.listenRecorded = false;
    }
    await this.run(signal => this.play(this.audio, signal));
  }
  cancel() { this.pending?.abort(); this.pending = null; }
  select(track, fromSource = true) {
    if (!track?.path) return false;
    const key = this.normalizePath(track.path);
    if (fromSource) this.sourceTrackKey = key;
    this.playingQueuedTrack = !fromSource;
    if (this.shuffle) this.shufflePlayed.add(key);
    if (this.matches(track.path)) {
      this.onQueueChange();
      return false;
    }
    this.cancel();
    this.audio.pause();
    this.track = {...track};
    this.resumePosition = null;
    this.listenRecorded = false;
    this.audio.src = '/api/audio?file=' + encodeURIComponent(track.path);
    this.audio.load();
    this.onChange(this.track);
    this.onUpdate();
    this.onQueueChange();
    return true;
  }
  refresh(track) {
    if (!this.matches(track.path)) return;
    this.track = {...track};
    this.onChange(this.track);
    this.onQueueChange();
  }
  async run(action) {
    this.cancel();
    const request = new AbortController();
    this.pending = request;
    this.onUpdate();
    try { await action(request.signal); }
    finally {
      if (this.pending === request) { this.pending = null; this.onUpdate(); }
    }
  }
  async toggle(track) {
    const changed = track ? this.select(track) : false;
    track ||= this.track;
    if (!track?.path) return;
    if (!changed && ((!this.audio.paused && !this.audio.ended) || this.pending)) {
      this.cancel();
      this.audio.pause();
      this.onUpdate();
      return;
    }
    if (this.audio.ended) {
      await this.start(track, !this.playingQueuedTrack);
      return;
    }
    await this.run(signal => this.play(this.audio, signal));
  }
  async seek(track, seconds) {
    if (!track?.path || !Number.isFinite(seconds)) return;
    if (!this.matches(track.path)) this.select(track);
    this.resumePosition = null;
    await this.run(signal => this.seekPlayback(this.audio, seconds, signal));
  }
  clear() {
    this.cancel();
    this.audio.pause();
    this.track = null;
    this.resumePosition = null;
    this.sourceTrackKey = '';
    this.playingQueuedTrack = false;
    this.listenRecorded = false;
    this.shufflePlayed.clear();
    if (this.shuffle) this.prepareShuffle();
    this.audio.removeAttribute('src');
    this.audio.load();
    this.onChange(null);
    this.onUpdate();
    this.onQueueChange();
  }
}
"""
