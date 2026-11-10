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
        music=next(a for tag,a in elements if 'music-card' in a.get('class','').split())
        self.assertEqual(music.get('tabindex'),'0','Track selection must support the keyboard')

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


if __name__ == '__main__':unittest.main()
