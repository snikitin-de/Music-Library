"""Timing, media lifecycle, and user control of synchronized lyrics."""
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from report_lyrics import REPORT_LYRICS_JS


DOM = r'''
const assert=require('node:assert/strict');
class Element extends EventTarget {
 constructor(tag='div'){super();this.tag=tag;this.children=[];this.dataset={};this.attrs={};this.className='';this.scrollTop=0;this.clientHeight=120;this.scrollCalls=[];
  this.classList={contains:name=>this.className.split(' ').includes(name),toggle:(name,on)=>{const set=new Set(this.className.split(' ').filter(Boolean));if(on)set.add(name);else set.delete(name);this.className=[...set].join(' ');},remove:(name)=>this.classList.toggle(name,false)};
 }
 append(child){child.parent=this;this.children.push(child);}
 replaceChildren(){this.children=[];this.textContent='';}
 setAttribute(name,value){this.attrs[name]=value;}
 removeAttribute(name){delete this.attrs[name];}
 getAttribute(name){return this.attrs[name]??null;}
 contains(node){return node===this||this.children.some(child=>child.contains(node));}
 closest(selector){return this.classList.contains(selector.slice(1))?this:this.parent?.closest(selector);}
 querySelectorAll(selector){return this.children.flatMap(child=>[...(child.classList.contains(selector.slice(1))?[child]:[]),...child.querySelectorAll(selector)]);}
 getBoundingClientRect(){const root=this.closest('.lyrics-text');const top=this.dataset.lyricIndex===undefined?0:Number(this.dataset.lyricIndex)*40-(root?.scrollTop||0);return{top,bottom:top+40,height:40};}
 scrollTo(options){this.scrollCalls.push(options);this.scrollTop=Math.max(0,options.top);}
}
class Player extends EventTarget {constructor(){super();this.currentTime=0;this.paused=true;this.ended=false;}}
const frames=new Map();let frameId=0;
global.requestAnimationFrame=callback=>{frames.set(++frameId,callback);return frameId;};
global.cancelAnimationFrame=id=>frames.delete(id);
global.window={getSelection:()=>({isCollapsed:true}),matchMedia:()=>({matches:true})};
global.document={createElement:tag=>new Element(tag)};
const container=new Element();container.className='lyrics-text';
function fire(target,type,actualTarget=target){const event=new Event(type);if(actualTarget!==target)Object.defineProperty(event,'target',{value:actualTarget});target.dispatchEvent(event);}
'''


class LyricsSyncTests(unittest.TestCase):
    def run_js(self, script):
        result = subprocess.run(['node', '-'], input=REPORT_LYRICS_JS + '\n' + script,
                                text=True, encoding='utf-8', capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_timeline_handles_boundaries_empty_cues_offset_and_repeated_lines(self):
        self.run_js(r'''
const assert=require('node:assert/strict');
const model=ReportLyrics.parse('[offset:+1000]\n[00:05.00]Первая\n[00:10.00]\n[00:12.50]Вторая\n[00:12.50]Другой голос');
assert.deepEqual(model.cues,[{time:4,line:0},{time:9,line:null},{time:11.5,line:1},{time:11.5,line:2}]);
assert.deepEqual(ReportLyrics.activeLines(model,3.99),[]);
assert.deepEqual(ReportLyrics.activeLines(model,4),[0]);
assert.deepEqual(ReportLyrics.activeLines(model,9),[]);
assert.deepEqual(ReportLyrics.activeLines(model,11.5),[1,2]);
assert.deepEqual(ReportLyrics.activeLines(model,4.5),[0],'Seeking backwards must reset the active line');
assert.deepEqual(ReportLyrics.activeLines(model,NaN),[]);
const repeats=ReportLyrics.parse('[00:20.00][00:05.00]Припев\n[offset:-500]');
assert.deepEqual(repeats.cues,[{time:5.5,line:0},{time:20.5,line:0}]);
assert.equal(ReportLyrics.seekTime(repeats,0,18),20.5);
assert.equal(ReportLyrics.seekTime(repeats,0,0),5.5);
assert.equal(ReportLyrics.seekTime(repeats,99,0),null);
assert.deepEqual(ReportLyrics.activeLines(ReportLyrics.parse('Без таймкода'),10),[]);
''')

    def test_zero_placeholders_are_readable_but_cannot_highlight_every_line(self):
        self.run_js(DOM + r'''
const raw='[ti:Песня]\n[offset:300]\n[00:00.00]Первая\n[00:00.00]Вторая\n[00:00.00]Третья';
const model=ReportLyrics.parse(raw);
assert.equal(model.timingIssue,'zero-timestamps','Repeated zero placeholders do not contain synchronization');
assert.deepEqual(model.cues,[]);
assert.deepEqual(model.blocks,[{type:'stanza',lines:['Первая','Вторая','Третья']}]);
ReportLyrics.render(container,model);
const player=new Player();player.currentTime=5;
const sync=new ReportLyrics.Sync(container);sync.bind(model,player);
assert.equal(sync.hasTiming,false);assert.equal(container.querySelectorAll('.is-current').length,0);
assert.equal(container.querySelectorAll('.lyric-seek').length,0);
assert.equal(ReportLyrics.seekTime(model,1,5),null);
const real=ReportLyrics.parse('[00:00.00]Начало\n[00:03.00]Продолжение');
assert.deepEqual(ReportLyrics.activeLines(real,0),[0]);
assert.deepEqual(ReportLyrics.activeLines(real,3),[1]);
assert.equal(real.timingIssue,undefined);
const duet=ReportLyrics.parse('[00:00]Голос 1\n[00:00]Голос 2\n[00:05]');
assert.deepEqual(ReportLyrics.activeLines(duet,1),[0,1],'A real closing cue preserves simultaneous opening lines');
sync.dispose();
''')

    def test_highlight_follows_media_but_manual_scroll_has_priority(self):
        self.run_js(DOM + r'''
const model=ReportLyrics.parse('[00:05]Первая\n[00:10]\n[00:12]Вторая\n[00:12]Третья\n[00:15]Последняя');
ReportLyrics.render(container,model);
const player=new Player();let updates=0;
const sync=new ReportLyrics.Sync(container,{onState:()=>updates++});
sync.bind(model,player);
const lines=container.querySelectorAll('.lyrics-line');
assert.equal(container.classList.contains('is-synced'),true);
player.currentTime=5;fire(player,'timeupdate');
assert.equal(lines[0].getAttribute('aria-current'),'true');
player.currentTime=10;fire(player,'seeked');assert.equal(lines[0].getAttribute('aria-current'),null);
player.currentTime=12;fire(player,'seeked');
assert.equal(lines[1].getAttribute('aria-current'),'true');assert.equal(lines[2].getAttribute('aria-current'),'true');
fire(container,'wheel');assert.equal(sync.follow,false);
const scrolls=container.scrollCalls.length;
player.currentTime=15;fire(player,'timeupdate');
assert.equal(lines[3].getAttribute('aria-current'),'true');assert.equal(container.scrollCalls.length,scrolls);
sync.setFollow(true);assert.ok(container.scrollCalls.length>scrolls);
player.paused=false;fire(player,'play');assert.equal(frames.size,1);
player.paused=true;fire(player,'pause');assert.equal(frames.size,0);
assert.equal(lines[3].getAttribute('aria-current'),'true','Pause keeps the current line');
player.ended=true;fire(player,'ended');assert.equal(lines[3].getAttribute('aria-current'),null);assert.equal(frames.size,0);
sync.bind(model,player,false);assert.equal(container.classList.contains('is-synced'),false);
sync.dispose();const previous=updates;fire(player,'timeupdate');assert.equal(updates,previous,'Dispose must detach media listeners');
''')

    def test_only_timed_lines_seek_and_selecting_text_does_not_start_playback(self):
        self.run_js(DOM + r'''
const model=ReportLyrics.parse('Пояснение\n[00:05][00:20]Припев');
ReportLyrics.render(container,model);
const lines=container.querySelectorAll('.lyrics-line');
assert.equal(lines[0].tag,'span');assert.equal(lines[1].tag,'button');
const player=new Player();player.currentTime=18;
let selected=[];
const sync=new ReportLyrics.Sync(container,{onSeek:(index,time)=>selected.push([index,time])});
sync.bind(model,player);
fire(container,'click',lines[1]);assert.deepEqual(selected,[[1,20]]);
window.getSelection=()=>({isCollapsed:false,anchorNode:lines[1]});
fire(container,'click',lines[1]);assert.equal(selected.length,1);
sync.bind(model,player,false);window.getSelection=()=>({isCollapsed:true});
fire(container,'click',lines[1]);assert.equal(selected.length,1,'Raw view does not seek');
sync.bind(model,null,true);
fire(container,'click',lines[1]);assert.deepEqual(selected.at(-1),[1,5],'A lyric can select the shared player before its first song');
sync.dispose();
''')

    def test_scrollbar_drag_and_navigation_keys_inside_lines_stop_following(self):
        self.run_js(DOM + r'''
const model=ReportLyrics.parse('[00:01]Первая\n[00:02]Вторая');
ReportLyrics.render(container,model);
const player=new Player();const sync=new ReportLyrics.Sync(container);sync.bind(model,player);
fire(container,'pointerdown');assert.equal(sync.follow,false,'Dragging the scrollbar must take control');
sync.setFollow(true);
const line=container.querySelectorAll('.lyrics-line')[0];
const key=new Event('keydown');Object.defineProperties(key,{target:{value:line},key:{value:'PageDown'}});container.dispatchEvent(key);
assert.equal(sync.follow,false,'Scroll keys work when a lyric line has keyboard focus');
sync.setFollow(true);
const activate=new Event('keydown');Object.defineProperties(activate,{target:{value:line},key:{value:' '}});container.dispatchEvent(activate);
assert.equal(sync.follow,true,'Space on a line is activation, not manual scrolling');
sync.dispose();
''')


if __name__ == '__main__':
    unittest.main()
