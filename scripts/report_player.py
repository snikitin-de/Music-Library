"""One shared audio source for the standalone report, independent of mounted cards."""

REPORT_PLAYER_JS = r"""
class ReportPlayer {
  constructor(audio, {normalizePath, play, seek, onChange = () => {}, onUpdate = () => {}}) {
    this.audio = audio;
    this.normalizePath = normalizePath;
    this.play = play;
    this.seekPlayback = seek;
    this.onChange = onChange;
    this.onUpdate = onUpdate;
    this.track = null;
    this.pending = null;
    this.queue = [];
    for (const event of ['play', 'pause', 'ended', 'timeupdate', 'durationchange', 'loadedmetadata', 'volumechange', 'error', 'emptied']) {
      audio.addEventListener(event, () => this.onUpdate());
    }
  }
  matches(path) { return Boolean(this.track && this.normalizePath(this.track.path) === this.normalizePath(path)); }
  setQueue(tracks) {
    const seen = new Set();
    this.queue = tracks.filter(track => {
      const key = this.normalizePath(track.path || '');
      if (!key || seen.has(key)) return false;
      seen.add(key);
      return true;
    });
    this.onUpdate();
  }
  neighbour(direction) {
    const index = this.queue.findIndex(track => this.matches(track.path));
    return index >= 0 ? this.queue[index + direction] : null;
  }
  canStep(direction) { return Boolean(this.neighbour(direction)); }
  async step(direction) {
    const track = this.neighbour(direction);
    if (track) await this.toggle(track);
  }
  cancel() { this.pending?.abort(); this.pending = null; }
  select(track) {
    if (!track?.path || this.matches(track.path)) return false;
    this.cancel();
    this.audio.pause();
    this.track = {...track};
    this.audio.src = '/api/audio?file=' + encodeURIComponent(track.path);
    this.audio.load();
    this.onChange(this.track);
    this.onUpdate();
    return true;
  }
  refresh(track) {
    if (!this.matches(track.path)) return;
    this.track = {...track};
    this.onChange(this.track);
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
  async toggle(track = this.track) {
    if (!track?.path) return;
    const changed = this.select(track);
    if (!changed && (!this.audio.paused || this.pending)) {
      this.cancel();
      this.audio.pause();
      this.onUpdate();
      return;
    }
    await this.run(signal => this.play(this.audio, signal));
  }
  async seek(track, seconds) {
    if (!track?.path || !Number.isFinite(seconds)) return;
    this.select(track);
    await this.run(signal => this.seekPlayback(this.audio, seconds, signal));
  }
  clear() {
    this.cancel();
    this.audio.pause();
    this.track = null;
    this.audio.removeAttribute('src');
    this.audio.load();
    this.onChange(null);
    this.onUpdate();
  }
}
"""
