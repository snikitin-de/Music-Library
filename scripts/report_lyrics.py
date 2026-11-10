"""Offline reading view for lyrics, retaining the original text for inspection."""

REPORT_LYRICS_JS = r"""
const ReportLyrics = (() => {
  function parse(raw) {
    const result = {title: '', artist: '', blocks: [], cues: []};
    let stanza = [];
    let lineIndex = 0;
    let offset = 0;
    const flush = () => {
      if (stanza.length) result.blocks.push({type: 'stanza', lines: stanza});
      stanza = [];
    };
    const metadata = /^(?:\s*\[(?:ti|ar|al|by|offset|re|ve|length|au|la|id|language):[^\]]*\])+\s*$/i;
    const timestamps = /^(?:\s*\[\d{1,3}:[0-5]\d(?:[.:]\d{1,3})?\])+\s*/;
    for (const original of String(raw || '').replace(/^\uFEFF/, '').replace(/\r\n?/g, '\n').split('\n')) {
      let line = original.trim();
      if (metadata.test(line)) {
        for (const match of line.matchAll(/\[(ti|ar|offset):([^\]]*)\]/gi)) {
          const value = match[2].trim();
          if (match[1].toLowerCase() === 'offset') {
            if (/^[+-]?\d+$/.test(value) && Number.isFinite(Number(value))) offset = Number(value);
          } else if (value) result[match[1].toLowerCase() === 'ti' ? 'title' : 'artist'] = value;
        }
        continue;
      }
      const prefix = line.match(timestamps);
      const times = prefix ? Array.from(prefix[0].matchAll(/\[(\d{1,3}):([0-5]\d)(?:[.:](\d{1,3}))?\]/g),
        match => Number(match[1]) * 60 + Number(match[2]) + Number('0.' + (match[3] || '0'))) : [];
      if (prefix) {
        line = line.replace(timestamps, '').replace(/<\d{1,3}:[0-5]\d(?:[.:]\d{1,3})?>/g, '').trim();
        line = line.replace(/^v\d+\s*:\s*/i, '');
      }
      if (!line) {
        times.forEach(time => result.cues.push({time, line: null}));
        flush();
        continue;
      }
      const section = line.match(/^\[([^\[\]:]+)\]$/);
      if (section) {
        flush();
        times.forEach(time => result.cues.push({time, line: null}));
        result.blocks.push({type: 'section', text: section[1].trim()});
      } else {
        times.forEach(time => result.cues.push({time, line: lineIndex}));
        lineIndex += 1;
        stanza.push(line);
      }
    }
    flush();
    // Some lyric providers wrap plain text in an LRC with 00:00 on every line.
    // Those placeholders cannot locate a line in the audio timeline.
    const timedLines = new Set(result.cues.filter(cue => cue.line !== null).map(cue => cue.line));
    if (timedLines.size > 1 && result.cues.every(cue => cue.time === 0)) {
      result.cues = [];
      result.timingIssue = 'zero-timestamps';
    }
    result.cues = result.cues.map(cue => ({time: cue.time - offset / 1000, line: cue.line})).sort((a, b) => a.time - b.time);
    return result;
  }

  function activeLines(model, time) {
    const cues = model.cues || [];
    if (!Number.isFinite(time)) return [];
    let low = 0, high = cues.length;
    while (low < high) {
      const middle = (low + high) >>> 1;
      if (cues[middle].time <= time) low = middle + 1;
      else high = middle;
    }
    if (!low) return [];
    const currentTime = cues[low - 1].time;
    const lines = new Set();
    for (let i = low - 1; i >= 0 && cues[i].time === currentTime; i--) {
      if (cues[i].line !== null) lines.add(cues[i].line);
    }
    return [...lines].sort((a, b) => a - b);
  }

  function seekTime(model, index, currentTime = 0) {
    const times = (model.cues || []).filter(cue => cue.line === index).map(cue => cue.time);
    if (!times.length) return null;
    const now = Number.isFinite(currentTime) ? currentTime : 0;
    return times.reduce((best, time) => Math.abs(time - now) < Math.abs(best - now) ? time : best);
  }

  function render(container, model, original = null) {
    container.replaceChildren();
    container.classList.toggle('is-raw', original !== null);
    if (original !== null) {
      container.textContent = original;
      return;
    }
    if (!model.blocks.length) {
      container.textContent = 'Текст песни не найден.';
      return;
    }
    const timed = new Set((model.cues || []).filter(cue => cue.line !== null).map(cue => cue.line));
    let index = 0;
    for (const block of model.blocks) {
      const element = document.createElement(block.type === 'section' ? 'div' : 'p');
      element.className = block.type === 'section' ? 'lyrics-section' : 'lyrics-stanza';
      if (block.type === 'section') {
        element.textContent = block.text;
      } else {
        for (const text of block.lines) {
          const isTimed = timed.has(index);
          const line = document.createElement(isTimed ? 'button' : 'span');
          line.className = isTimed ? 'lyrics-line lyric-seek' : 'lyrics-line';
          line.dataset.lyricIndex = String(index++);
          if (isTimed) {
            line.type = 'button';
            line.title = 'Перейти к этому месту песни';
          }
          line.textContent = text;
          element.append(line);
        }
      }
      container.append(element);
    }
  }

  class Sync {
    constructor(container, {onSeek = () => {}, onState = () => {}} = {}) {
      this.container = container;
      this.onSeek = onSeek;
      this.onState = onState;
      this.player = null;
      this.lines = [];
      this.frame = null;
      this.follow = true;
      this.enabled = true;
      this.hasTiming = false;
      this.currentKey = '';
      this.events = ['timeupdate', 'seeking', 'seeked', 'loadedmetadata', 'durationchange', 'play', 'pause', 'ended', 'error', 'emptied'];
      this.handleMedia = event => {
        this.update(['play', 'seeking', 'seeked'].includes(event.type));
        if (event.type === 'play') this.startFrame();
        else if (['pause', 'ended', 'error', 'emptied'].includes(event.type)) this.stopFrame();
        this.onState();
      };
      const manual = () => { if (this.enabled && this.hasTiming && this.follow) this.setFollow(false); };
      container.addEventListener('wheel', manual, {passive: true});
      container.addEventListener('touchstart', manual, {passive: true});
      container.addEventListener('pointerdown', manual, {passive: true});
      container.addEventListener('mousedown', manual, {passive: true});
      container.addEventListener('keydown', event => {
        if (['ArrowUp', 'ArrowDown', 'PageUp', 'PageDown', 'Home', 'End'].includes(event.key)
          || (event.target === container && event.key === ' ')) manual();
      });
      container.addEventListener('click', event => {
        const line = event.target.closest?.('.lyric-seek');
        if (!line || !container.contains(line) || !this.enabled) return;
        const selection = window.getSelection?.();
        if (selection && !selection.isCollapsed && container.contains(selection.anchorNode)) return;
        const index = Number(line.dataset.lyricIndex);
        const time = seekTime(this.model, index, this.player?.currentTime || 0);
        if (time !== null) this.onSeek(index, Math.max(0, time));
      });
    }

    bind(model, player, enabled = true) {
      this.dispose();
      this.model = model;
      this.player = player;
      this.enabled = enabled;
      this.follow = true;
      this.hasTiming = (model.cues || []).some(cue => cue.line !== null);
      this.lines = Array.from(this.container.querySelectorAll('.lyrics-line'));
      this.container.classList.toggle('is-synced', enabled && this.hasTiming && Boolean(player));
      if (player) this.events.forEach(event => player.addEventListener(event, this.handleMedia));
      this.update(true);
      this.startFrame();
      this.onState();
    }

    update(forceScroll = false) {
      const active = this.player && this.enabled && this.hasTiming && !this.player.ended && !this.player.error
        ? activeLines(this.model, this.player.currentTime) : [];
      const key = active.join(',');
      const changed = key !== this.currentKey;
      if (changed) {
        this.currentKey = key;
        const indices = new Set(active);
        this.lines.forEach((line, index) => {
          const current = indices.has(index);
          line.classList.toggle('is-current', current);
          if (current) line.setAttribute('aria-current', 'true');
          else line.removeAttribute('aria-current');
        });
      }
      if (this.follow && active.length && (changed || forceScroll)) {
        const line = this.lines[active[0]];
        if (!line) return;
        const rect = line.getBoundingClientRect();
        const top = this.container.scrollTop + rect.top - this.container.getBoundingClientRect().top
          - (this.container.clientHeight - rect.height) * .45;
        const reduced = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
        this.container.scrollTo({top: Math.max(0, top), behavior: reduced ? 'auto' : 'smooth'});
      }
    }

    setFollow(enabled) {
      this.follow = enabled;
      if (!enabled) this.container.scrollTo({top: this.container.scrollTop, behavior: 'auto'});
      else this.update(true);
      this.onState();
    }

    startFrame() {
      if (this.frame !== null || !this.player || this.player.paused || this.player.ended || this.player.error || !this.enabled || !this.hasTiming) return;
      this.frame = requestAnimationFrame(() => {
        this.frame = null;
        this.update();
        this.startFrame();
      });
    }

    stopFrame() {
      if (this.frame !== null) cancelAnimationFrame(this.frame);
      this.frame = null;
    }

    dispose() {
      this.stopFrame();
      if (this.player) this.events.forEach(event => this.player.removeEventListener(event, this.handleMedia));
      this.player = null;
      this.hasTiming = false;
      this.currentKey = '';
      this.lines.forEach(line => { line.classList.toggle('is-current', false); line.removeAttribute('aria-current'); });
      this.container.classList.toggle('is-synced', false);
    }
  }
  return {parse, render, activeLines, seekTime, Sync};
})();
"""
