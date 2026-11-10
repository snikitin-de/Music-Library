"""Playback must select a source after a card leaves the inert template."""
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from generate_html_report import build_payload, render_html


class ReportAudioTests(unittest.TestCase):
    def test_seeking_loads_metadata_can_cancel_and_does_not_autoplay_after_cancel(self):
        report = render_html(build_payload([], {'tracks': [], 'path': 'D:/Music'}))
        start = report.index('    async function seekAudioPlayback(')
        function = report[start:report.index('    function bindCardControls(', start)]
        script = r'''
import assert from 'node:assert/strict';
class Player extends EventTarget {
 constructor(){super();this.readyState=0;this.currentTime=0;this.duration=100;this.error=null;this.paused=true;this.calls=[];}
 load(){this.calls.push('load');queueMicrotask(()=>{this.readyState=1;this.dispatchEvent(new Event('loadedmetadata'));});}
 async play(){this.calls.push('play');this.paused=false;}
 pause(){this.calls.push('pause');this.paused=true;}
}
const status={hidden:true,textContent:''};
const first=new Player();
assert.equal(await seekAudioPlayback(first,25,status),true);
assert.deepEqual(first.calls,['load','play']);assert.equal(first.preload,'metadata');assert.equal(first.currentTime,25);
first.calls=[];await seekAudioPlayback(first,500,status);
assert.deepEqual(first.calls,['play']);assert.ok(first.currentTime<100&&first.currentTime>99);
const pending=new Player();pending.load=function(){this.calls.push('load');};
const abort=new AbortController();const request=seekAudioPlayback(pending,30,status,abort.signal);abort.abort();
assert.equal(await request,false);pending.dispatchEvent(new Event('loadedmetadata'));
assert.deepEqual(pending.calls,['load']);assert.equal(status.hidden,true);
const broken=new Player();broken.load=function(){queueMicrotask(()=>this.dispatchEvent(new Event('error')));};
assert.equal(await seekAudioPlayback(broken,10,status),false);assert.equal(status.hidden,false);assert.match(status.textContent,/Не удалось/);
const stopped=new AbortController();stopped.abort();const untouched=new Player();
assert.equal(await seekAudioPlayback(untouched,10,status,stopped.signal),false);assert.deepEqual(untouched.calls,[]);
const waitingPlay=new Player();waitingPlay.readyState=1;
let rejectPlay;waitingPlay.play=function(){return new Promise((_,reject)=>{rejectPlay=reject;});};
waitingPlay.pause=function(){this.calls.push('pause');rejectPlay(Object.assign(new Error('Stopped'),{name:'AbortError'}));};
const cancelPlay=new AbortController();const playing=seekAudioPlayback(waitingPlay,20,status,cancelPlay.signal);cancelPlay.abort();
assert.equal(await playing,false);assert.deepEqual(waitingPlay.calls,['pause']);assert.equal(status.hidden,true);
'''
        result = subprocess.run(['node', '--input-type=module', '-'], input=function + script,
                                text=True, encoding='utf-8', capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_initialization_resume_pause_retry_and_visible_failure(self):
        report = render_html(build_payload([], {'tracks': [], 'path': 'D:/Music'}))
        start = report.index('    async function toggleAudioPlayback(')
        function = report[start:report.index('    function bindCardControls(', start)]
        script = r'''
import assert from 'node:assert/strict';
const button={classList:{remove(){}}};
const status={hidden:true,textContent:''};
let calls=[];
const player={paused:true,currentSrc:'',error:null,currentTime:0,
 load(){calls.push('load');this.currentSrc='track.flac';this.error=null;},
 async play(){calls.push('play');if(!this.currentSrc)throw new Error('No supported sources');this.paused=false;},
 pause(){calls.push('pause');this.paused=true;}};
await toggleAudioPlayback(player,button,status);
assert.deepEqual(calls,['load','play']); assert.equal(player.paused,false);
player.currentTime=12; calls=[];
await toggleAudioPlayback(player,button,status);
assert.deepEqual(calls,['pause']); assert.equal(player.currentTime,12);
calls=[]; await toggleAudioPlayback(player,button,status);
assert.deepEqual(calls,['play'],'Resume must not reload or reset a track');
player.paused=true; player.error={code:4}; calls=[];
await toggleAudioPlayback(player,button,status);
assert.deepEqual(calls,['load','play'],'Retry a previously failed source');
player.paused=true; player.play=async()=>{throw new Error('Network failure');};
await toggleAudioPlayback(player,button,status);
assert.equal(status.hidden,false); assert.match(status.textContent,/Не удалось/);
player.play=async()=>{player.paused=false;};
await toggleAudioPlayback(player,button,status);
assert.equal(status.hidden,true); assert.equal(status.textContent,'');
player.paused=true; player.play=async()=>{throw Object.assign(new Error('paused'),{name:'AbortError'});};
await toggleAudioPlayback(player,button,status);
assert.equal(status.hidden,true,'Stopping a pending play request is not a playback failure');
'''
        result = subprocess.run(['node', '--input-type=module', '-'], input=function + script,
                                text=True, encoding='utf-8', capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
