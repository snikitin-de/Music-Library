import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SharedPlayerTests(unittest.TestCase):
    def run_js(self, body):
        source = ROOT / 'scripts/report_player.py'
        self.assertTrue(source.exists(), 'Shared player controller is missing')
        namespace = {}
        exec(source.read_text(encoding='utf-8'), namespace)
        result = subprocess.run([shutil.which('node'), '-'], input=namespace['REPORT_PLAYER_JS'] + body,
                                capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_queue_batch_appends_in_order_and_notifies_once(self):
        self.run_js(r'''
const assert = require('node:assert/strict');
let updates = 0;
const player = new ReportPlayer({addEventListener() {}}, {
  normalizePath: path => path,
  onQueueChange: () => updates++,
});
assert.equal(player.enqueue({path: 'existing'}), true);
assert.equal(player.enqueueTracks([{path: 'first'}, {path: 'second'}]), 2);
assert.deepEqual(player.snapshot().manualQueue.map(track => track.path), ['existing', 'first', 'second']);
assert.equal(updates, 2);
''')

    def test_track_buttons_follow_play_pause_switch_and_end(self):
        import sys
        sys.path.insert(0, str(ROOT / 'scripts'))
        from generate_html_report import render_html, build_payload
        report = render_html(build_payload([], {'tracks': [], 'path': 'D:/Music'}))
        start = report.index('    function updatePlayingCard(')
        function = report[start:report.index('    function updateGlobalPlayer(', start)]
        self.run_js(function + r'''
const assert=require('node:assert/strict');
function classes(){return {toggle(name,on){this[name]=on;}};}
function card(path,music=false){
 const label={textContent:'Слушать'};
 const button={classList:classes(),attrs:{},setAttribute(k,v){this.attrs[k]=v;},querySelector(){return music ? null : label;}};
 return {dataset:{filePath:path},classList:classes(),label,button,
  setAttribute(){},removeAttribute(){},querySelector(selector){
    if(selector==='.music-title') return {textContent:'Песня'};
    return selector.split(', ').includes(music ? '.music-play' : '.duplicate-listen') ? button : null;
  }};
}
const cards=[card('a.flac'),card('b.flac'),card('A.FLAC')];
const musicCard=card('a.flac',true);
const document={querySelectorAll(){return [...cards,musicCard];}};
class Audio extends EventTarget {
 constructor(){super();this.paused=true;this.ended=false;}
 pause(){this.paused=true;this.dispatchEvent(new Event('pause'));}
 load(){} removeAttribute(){this.src='';}
}
const audio=new Audio(), sharedUI={globalAudio:audio};let cardPlaybackKey='';
const playback=new ReportPlayer(audio,{
 normalizePath:p=>p.toLowerCase(),onUpdate:updatePlayingCards,
 play:async a=>{a.paused=false;a.ended=false;a.dispatchEvent(new Event('play'));},seek:async()=>{}
});
const labels=()=>cards.map(c=>c.label.textContent);
(async()=>{
 await playback.toggle({path:'a.flac'});
 assert.deepEqual(labels(),['Пауза','Слушать','Пауза'],'Playing state must reach every card for the active path');
 assert.equal(cards[0].button.attrs['aria-label'],'Пауза');
 assert.equal(musicCard.button.attrs['aria-label'],'Пауза: Песня');
 assert.equal(musicCard.button.attrs['aria-pressed'],'true');
 assert.equal(cards[0].button.classList.playing,true,'Pause icon must follow playback');
 await playback.toggle();
 assert.deepEqual(labels(),['Слушать','Слушать','Слушать'],'Pausing from the shared player must reset card buttons');
 assert.equal(cards[0].button.classList.playing,false);
 assert.equal(musicCard.button.attrs['aria-pressed'],'false');
 await playback.toggle({path:'b.flac'});
 assert.deepEqual(labels(),['Слушать','Пауза','Слушать'],'Switching files must reset the previous button');
 cards.push(card('b.flac'));updatePlayingCard(cards[3]);
 assert.equal(cards[3].label.textContent,'Пауза','Newly mounted cards must receive the active state');
 audio.ended=true;audio.dispatchEvent(new Event('ended'));
 assert.deepEqual(labels(),['Слушать','Слушать','Слушать','Слушать'],'Ending must reset labels even before paused changes');
 playback.clear();
 assert.ok(cards.every(c=>c.button.attrs['aria-label']==='Слушать'));
})().catch(e=>{console.error(e);process.exitCode=1;});
''')

    def test_one_source_survives_reselection_and_tracks_switch_cancels_pending_work(self):
        self.run_js(r'''
const assert=require('node:assert/strict');
class Audio extends EventTarget {
 constructor(){super();this.paused=true;this.currentTime=0;this.calls=[];}
 pause(){this.paused=true;this.calls.push('pause');this.dispatchEvent(new Event('pause'));}
 load(){this.calls.push('load');}
 removeAttribute(){this.src='';}
}
const audio=new Audio(),changes=[],signals=[];
const player=new ReportPlayer(audio,{
 normalizePath:p=>p.toLowerCase(),
 onChange:track=>changes.push(track?.path || null),onUpdate(){},
 play:async(a,signal)=>{signals.push(signal);a.paused=false;},
 seek:async(a,time,signal)=>{signals.push(signal);a.currentTime=time;a.paused=false;}
});
(async()=>{
 await player.toggle({path:'A.flac',title:'A'});
 assert.match(audio.src,/A.flac/);assert.equal(audio.paused,false);
 audio.currentTime=42;const loads=audio.calls.filter(x=>x==='load').length;
 await player.toggle({path:'a.FLAC',title:'A'});
 assert.equal(audio.paused,true);assert.equal(audio.currentTime,42);
 await player.toggle();assert.equal(audio.paused,false);
 assert.equal(audio.calls.filter(x=>x==='load').length,loads);
 await player.seek({path:'B.flac',title:'B'},13);
 assert.equal(player.track.path,'B.flac');assert.equal(audio.currentTime,13);
 player.refresh({path:'B.flac',title:'New title'});
 assert.equal(audio.currentTime,13);assert.equal(player.track.title,'New title');
 player.clear();assert.equal(player.track,null);assert.equal(audio.paused,true);assert.equal(audio.src,'');
 assert.equal(changes.at(-1),null);
 let complete;
 player.play=(_a,signal)=>new Promise(resolve=>{signals.push(signal);complete=resolve;});
 const pending=player.toggle({path:'Slow.flac'});const firstSignal=signals.at(-1);
 player.select({path:'Other.flac'});
 assert.equal(firstSignal.aborted,true);complete();await pending;
 assert.equal(player.track.path,'Other.flac');
})().catch(e=>{console.error(e);process.exitCode=1;});
''')

    def test_cards_have_no_player_and_document_has_exactly_one_audio(self):
        import sys
        sys.path.insert(0, str(ROOT / 'scripts'))
        from generate_html_report import render_html, build_payload
        from html.parser import HTMLParser
        class Elements(HTMLParser):
            def __init__(self, text):
                super().__init__(); self.tags=[];self.feed(text)
            def handle_starttag(self, tag, attrs):self.tags.append((tag,dict(attrs)))
        report=render_html(build_payload([], {'tracks':[{'path':'D:/Music/A.flac','name':'A.flac','tags':[]}], 'path':'D:/Music'}))
        elements=Elements(report).tags
        self.assertEqual(sum(tag=='audio' for tag,_ in elements),1)
        ids=[a.get('id') for _,a in elements]
        self.assertIn('globalPlayer',ids)
        self.assertNotIn('lyricsPlay',ids)
        self.assertNotIn('lyricsClock',ids)
        self.assertFalse(any('card-play' in a.get('class','').split() for _,a in elements))
        play=next((a for tag,a in elements if tag=='button' and 'music-play' in a.get('class','').split()), None)
        self.assertIsNotNone(play,'Track playback needs a keyboard-accessible button')
        self.assertEqual(play.get('aria-pressed'),'false')

    def test_older_lyric_seek_completion_cannot_drop_latest_cancellation(self):
        import sys
        sys.path.insert(0, str(ROOT / 'scripts'))
        from generate_html_report import render_html, build_payload
        report=render_html(build_payload([], {'tracks':[], 'path':'D:/Music'}))
        start=report.index('    function cancelLyricsSeek(')
        functions=report[start:report.index('    async function openLyricsModal(',start)]
        self.run_js(functions+r'''
const assert=require('node:assert/strict');
let lyricsSeekRequest=null;const lyricsDocument={};const lyricsPath={textContent:'A.flac'};
const lyricsModal={classList:{contains:()=>true}};const lyricsSync={setFollow(){}};
const ReportLyrics={seekTime:()=>10};function getLyricsPlayer(){return null;}
function trackForPath(path){return {path};}function updatePlaybackQueue(){}
function normalizePathForCompare(path){return path;}
const audio=new EventTarget();audio.pause=()=>{};audio.load=()=>{};
const pending=[];const playback=new ReportPlayer(audio,{normalizePath:p=>p,play:async()=>{},seek:(_audio,_time,signal)=>new Promise(resolve=>pending.push({signal,resolve}))});
playback.setQueue([{path:'A.flac'}]);
(async()=>{
 const first=seekLyricsLine(0);const second=seekLyricsLine(1);const token=playback.pending;
 pending[0].resolve();await first;
 assert.equal(lyricsSeekRequest,token,'Older completion must preserve the latest seek token');
 cancelLyricsSeek();assert.equal(pending[1].signal.aborted,true,'Closing cancels the latest seek');
 pending[1].resolve();await second;
})().catch(e=>{console.error(e);process.exitCode=1;});
''')

    def test_navigation_uses_whole_ordered_queue_and_starts_neighbours(self):
        self.run_js(r'''
const assert=require('node:assert/strict');
class Audio extends EventTarget {constructor(){super();this.paused=true;}pause(){this.paused=true;}load(){} }
const audio=new Audio();const player=new ReportPlayer(audio,{normalizePath:p=>p.toLowerCase(),play:async a=>{a.paused=false;},seek:async()=>{}});
(async()=>{
 assert.equal(typeof player.setQueue,'function','Navigation needs an ordered queue');
 player.setQueue(Array.from({length:12},(_,i)=>({path:`${i}.flac`})).concat({path:'0.FLAC'}));
 await player.toggle({path:'9.flac'});await player.step(1);
 assert.equal(player.track.path,'10.flac');assert.equal(audio.paused,false,'Next starts beyond first mounted page');
 await player.step(-1);assert.equal(player.track.path,'9.flac');
 player.setQueue([{path:'9.flac'},{path:'1.flac'}]);
 assert.equal(player.canStep(-1),false);await player.step(1);assert.equal(player.track.path,'1.flac');
 assert.equal(player.canStep(1),false);await player.step(1);assert.equal(player.track.path,'1.flac');
 player.setQueue([{path:'other.flac'}]);assert.equal(player.canStep(-1),false);assert.equal(player.canStep(1),false);
})().catch(e=>{console.error(e);process.exitCode=1;});
''')

    def test_shuffle_advances_without_replaying_tracks_and_repeat_takes_priority(self):
        self.run_js(r'''
const assert = require('node:assert/strict');
class Audio extends EventTarget {
  constructor(){super(); this.paused=true; this.loop=false;}
  pause(){this.paused=true;}
  load(){}
}
const audio=new Audio();
const played=[];
const player=new ReportPlayer(audio,{
  normalizePath:path=>path.toLowerCase(),
  play:async element=>{element.paused=false; played.push(player.track.path);},
  seek:async()=>{},
});
const tracks=['A','B','C','D'].map(path=>({path}));
const end=async()=>{
  audio.paused=true;
  audio.dispatchEvent(new Event('ended'));
  await new Promise(resolve=>setImmediate(resolve));
};
(async()=>{
  player.setQueue(tracks,'music');
  await player.toggle(tracks[0]);
  player.setShuffle(true);
  player.setRepeat(true);
  assert.equal(audio.loop,true);
  await end();
  assert.deepEqual(played,['A'],'Repeat must keep the current track even when shuffle is on');
  player.setRepeat(false);
  assert.equal(audio.loop,false);
  await end();
  player.setQueue([...tracks].reverse(),'music');
  await end();
  await end();
  await end();
  assert.equal(played.length,4);
  assert.deepEqual([...new Set(played)].sort(),['A','B','C','D']);
  assert.equal(player.canStep(1),false);
  assert.equal(player.canStep(-1),true);
  player.setQueue(tracks,'playlist:one');
  await player.toggle(tracks[0]);
  assert.equal(player.canStep(1),true,'A different playlist starts its own shuffle');
  player.setShuffle(false);
  assert.equal(player.neighbour(1).path,'B','Turning shuffle off restores the list order');
  await end();
  assert.equal(player.track.path,'B');
})().catch(error=>{console.error(error);process.exitCode=1;});
''')

    def test_manual_queue_has_priority_and_resumes_the_ordered_source(self):
        self.run_js(r'''
const assert = require('node:assert/strict');
class Audio extends EventTarget {
  constructor(){super(); this.paused=true; this.ended=false; this.currentTime=0;}
  pause(){this.paused=true;}
  load(){this.currentTime=0; this.ended=false;}
}
const audio = new Audio();
const listened = [];
const player = new ReportPlayer(audio, {
  normalizePath: path=>path.toLowerCase(),
  play: async element=>{element.paused=false; element.ended=false; element.dispatchEvent(new Event('playing'));},
  seek: async()=>{},
  onListen: track=>listened.push(track.path),
});
const end = async()=>{
  audio.paused=true;
  audio.ended=true;
  audio.dispatchEvent(new Event('ended'));
  await new Promise(resolve=>setImmediate(resolve));
};
const [a,b,c,x] = ['A','B','C','X'].map(path=>({path}));
(async()=>{
  player.setQueue([a,b,c], 'music');
  await player.toggle(a);
  await player.toggle();
  await player.toggle();
  assert.deepEqual(listened, ['A'], 'Resuming is the same listening event');
  player.enqueue(x);
  player.enqueue(x);
  player.enqueue(c);
  player.removeQueued(2);
  assert.deepEqual(player.manualQueue.map(track=>track.path), ['X','X']);
  player.setRepeat(true);
  await end();
  assert.equal(player.track.path,'A');
  assert.equal(player.manualQueue.length,2);
  player.setRepeat(false);
  await end();
  assert.equal(player.track.path,'X');
  await player.seek(x, 12);
  assert.deepEqual(player.sourceUpcoming().map(track=>track.path), ['B','C']);
  await player.step(1);
  assert.equal(audio.currentTime,0);
  assert.equal(audio.paused,false);
  await end();
  await end();
  await end();
  assert.deepEqual(listened, ['A','X','X','B','C']);
  assert.equal(player.canStep(1),false);
})().catch(error=>{console.error(error);process.exitCode=1;});
''')

    def test_idle_queue_starts_only_after_selecting_an_item(self):
        self.run_js(r'''
const assert = require('node:assert/strict');
const audio = new EventTarget();
audio.paused = true;
audio.pause = () => {};
audio.load = () => {};
const player = new ReportPlayer(audio, {
  normalizePath: path=>path,
  play: async element=>{element.paused=false;},
  seek: async()=>{},
});
(async()=>{
  player.setQueue([{path:'Library track'}], 'music');
  player.enqueue({path:'First'});
  player.enqueue({path:'Was moved'});
  player.enqueue({path:'Quarantined'});
  player.updateQueuedTracks(new Map([['Was moved', {path:'Second'}], ['Quarantined', null]]));
  assert.equal(player.track,null);
  await player.playQueued(1);
  assert.equal(player.track.path,'Second');
  assert.deepEqual(player.manualQueue.map(track=>track.path),['First']);
  await player.step(1);
  assert.equal(player.track.path,'First');
  assert.equal(player.canStep(1),false);
})().catch(error=>{console.error(error);process.exitCode=1;});
''')

    def test_restored_session_preserves_position_order_and_stays_paused(self):
        self.run_js(r'''
const assert = require('node:assert/strict');
class Audio extends EventTarget {
  constructor() { super(); this.paused=true; this.currentTime=0; this.readyState=0; this.duration=90; }
  pause() { this.paused=true; }
  load() { this.currentTime=0; }
}
const [a,b,c] = ['A','B','C'].map(path=>({path}));
const create = audio => new ReportPlayer(audio, {
  normalizePath: path=>path.toLowerCase(),
  play: async element=>{element.paused=false;},
  seek: async()=>{},
});
const original = create(new Audio());
original.setQueue([a,b,c], 'playlist:one');
original.select(a);
original.audio.currentTime=37;
original.enqueue(b);
original.enqueue(c, true);
assert.deepEqual(original.manualQueue.map(track=>track.path), ['C','B']);
original.moveQueued(1,0);
assert.deepEqual(original.manualQueue.map(track=>track.path), ['B','C']);
original.setShuffle(true);
original.setRepeat(true);
const snapshot=JSON.parse(JSON.stringify(original.snapshot()));
const audio=new Audio();
const player=create(audio);
player.restore(snapshot, track=>track);
assert.equal(player.position(),37);
assert.equal(audio.paused,true);
assert.equal(player.track.path,'A');
assert.equal(player.queueScope,'playlist:one');
assert.equal(player.repeat,true);
assert.equal(player.shuffle,true);
assert.deepEqual(player.sourceUpcoming().map(track=>track.path), original.sourceUpcoming().map(track=>track.path));
assert.deepEqual(player.manualQueue.map(track=>track.path), ['B','C']);
audio.readyState=1;audio.dispatchEvent(new Event('loadedmetadata'));
assert.equal(audio.currentTime,37);
assert.equal(audio.paused,true);
''')

    def test_recent_listens_keep_timestamps_across_reload_and_work_without_storage(self):
        import sys
        sys.path.insert(0, str(ROOT / 'scripts'))
        from report_playback_panel import PLAYBACK_PANEL_JS

        self.run_js(PLAYBACK_PANEL_JS + r'''
const assert = require('node:assert/strict');
const values = new Map();
const storage = () => ({
  getItem: key=>values.get(key),
  setItem: (key,value)=>values.set(key,value),
});
const history = new ReportListeningHistory('library:A', storage);
history.add({path:'A.flac', title:'Первый', artist:'Исполнитель', cover:'large artwork'}, 1700000000000);
const secondTab = new ReportListeningHistory('library:A', storage);
secondTab.add({path:'B.flac', title:'Второй', artist:''}, 1700000060000);
history.add({path:'A.flac', title:'Первый', artist:'Исполнитель'}, 1700000120000);
assert.deepEqual(new ReportListeningHistory('library:A', storage).entries, [
  {path:'A.flac', title:'Первый', artist:'Исполнитель', playedAt:1700000120000},
  {path:'B.flac', title:'Второй', artist:'', playedAt:1700000060000},
  {path:'A.flac', title:'Первый', artist:'Исполнитель', playedAt:1700000000000},
]);
assert.deepEqual(new ReportListeningHistory('library:B', storage).entries, []);
const limited = new ReportListeningHistory('blocked', () => { throw new Error('Storage unavailable'); });
limited.add({path:'A.flac', title:'Первый'}, 1700000000000);
assert.equal(limited.entries[0].playedAt, 1700000000000);
assert.equal(limited.persistent, false);
''')


if __name__ == '__main__':unittest.main()
