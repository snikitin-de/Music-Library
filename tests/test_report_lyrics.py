"""Reading view for LRC and plain lyrics without changing their source."""
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from report_lyrics import REPORT_LYRICS_JS
from generate_html_report import build_payload, render_html
from test_report_interface import Elements


class ReportLyricsTests(unittest.TestCase):
    def report(self, tracks=None):
        return render_html(build_payload([], {'tracks': tracks or [], 'path': 'D:/Music'}))

    def run_js(self, script):
        result = subprocess.run(['node', '-'], input=REPORT_LYRICS_JS + '\n' + script,
                                text=True, encoding='utf-8', capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_lrc_headers_timestamps_and_empty_timed_lines(self):
        self.run_js(r'''
const assert=require('node:assert/strict');
const raw='\uFEFF[ti:Песня]\r\n[ar:Исполнитель]\r\n[by:Программа]\r\n[offset:100]\r\n\r\n[00:01.25]Первая строка\r\n[00:03.50]Вторая строка\r\n[00:06.00]\r\n[00:08.00]Новая строфа';
assert.deepEqual(ReportLyrics.parse(raw),{
 title:'Песня',artist:'Исполнитель',blocks:[
  {type:'stanza',lines:['Первая строка','Вторая строка']},
  {type:'stanza',lines:['Новая строфа']}
 ],cues:[{time:1.15,line:0},{time:3.4,line:1},{time:5.9,line:null},{time:7.9,line:2}]});
assert.deepEqual(ReportLyrics.parse('[ti:Только заголовок]\n[by:Автор]'),{title:'Только заголовок',artist:'',blocks:[],cues:[]});
''')

    def test_plain_stanzas_sections_multiple_and_word_timestamps(self):
        self.run_js(r'''
const assert=require('node:assert/strict');
assert.deepEqual(ReportLyrics.parse('Строка\nЕщё строка\n\n[Припев]\nПовтор\n[custom: сохранить]'),{
 title:'',artist:'',blocks:[
  {type:'stanza',lines:['Строка','Ещё строка']},
  {type:'section',text:'Припев'},
  {type:'stanza',lines:['Повтор','[custom: сохранить]']}
 ],cues:[]});
assert.deepEqual(ReportLyrics.parse('[01:02.3][02:05.90]<01:02.3>Одна <01:02.8>строка').blocks,[{type:'stanza',lines:['Одна строка']}]);
assert.equal(ReportLyrics.parse('Обычный текст <01:02.3>').blocks[0].lines[0],'Обычный текст <01:02.3>');
''')

    def test_reading_is_safe_and_original_view_preserves_exact_text(self):
        self.run_js(r'''
const assert=require('node:assert/strict');
function node(tag){return {tag,children:[],textContent:'',className:'',dataset:{},
 classList:{toggle(name,on){this[name]=on;}},
 replaceChildren(){this.children=[];this.textContent='';},
 append(child){this.children.push(child);},
 set innerHTML(value){throw new Error('Lyrics must be inserted as text');}};}
global.document={createElement:node};
const container=node('div');
const raw='[ti:Тест]\r\n[00:01.00]v1:<img src=x onerror=alert(1)>\r\n\r\n[Припев]\r\nВторая строка';
const parsed=ReportLyrics.parse(raw);
ReportLyrics.render(container,parsed);
assert.equal(container.children[0].children[0].textContent,'<img src=x onerror=alert(1)>');
assert.equal(container.children[1].textContent,'Припев');
assert.equal(container.children[2].children[0].textContent,'Вторая строка');
ReportLyrics.render(container,parsed,raw);
assert.equal(container.textContent,raw); assert.equal(container.classList['is-raw'],true);
ReportLyrics.render(container,parsed);
assert.equal(container.classList['is-raw'],false); assert.equal(container.children.length,3);
''')

    def test_timed_voice_markers_are_hidden_but_plain_text_is_preserved(self):
        self.run_js(r'''
const assert=require('node:assert/strict');
const raw='[00:01.00]v1:Первый\n[00:02.00]v2: Второй\n[00:03.00]v1:\n[00:04.00] V3: <00:04.10>Вместе';
assert.deepEqual(ReportLyrics.parse(raw).blocks,[
 {type:'stanza',lines:['Первый','Второй']},
 {type:'stanza',lines:['Вместе']}
]);
assert.equal(ReportLyrics.parse('v1: Это обычный текст').blocks[0].lines[0],'v1: Это обычный текст');
''')

    def test_plain_lyrics_can_use_clean_card_metadata_and_both_view_controls(self):
        report = self.report([{'path':'D:/Music/01 - file.opus','name':'01 - file.opus','tags':[
            {'kind':'title','value':'Песня <тест>'},{'kind':'artist','value':'Первый & Второй'},
            {'kind':'artist','value':'Третий'},{'kind':'lyrics','label':'текст песни','value':'есть'}]}])
        elements = Elements(report).elements
        button = next(a for _, a in elements if 'lyrics-button' in a.get('class','').split())
        self.assertEqual(button['data-lyrics-title'], 'Песня <тест>')
        self.assertEqual(button['data-lyrics-artist'], 'Первый & Второй · Третий')
        ids = [a.get('id') for _, a in elements]
        for expected in ['lyricsReading','lyricsOriginal','lyricsDetails','lyricsArtist']:
            self.assertEqual(ids.count(expected), 1)

    def test_slow_previous_request_cannot_overwrite_a_new_song(self):
        report = self.report()
        start = report.index('    async function openLyricsModal(')
        function = report[start:report.index('    async function searchAndSaveEnrichment(', start)]
        self.run_js(function + r'''
const assert=require('node:assert/strict');
const field=()=>({textContent:'',disabled:false,open:false,
 classList:{add(){},remove(){}},setAttribute(){}});
const lyricsTitle=field(),lyricsArtist=field(),lyricsDetails=field(),lyricsPath=field(),
 lyricsSource=field(),lyricsText=field(),lyricsReading=field(),lyricsOriginal=field(),lyricsModal=field(),
 lyricsPlay=field(),lyricsClock=field(),lyricsFollow=field(),lyricsSyncNote=field(),lyricsPlaybackError=field();
let lyricsRequestId=0,lyricsRawText='',lyricsDocument=null,lyricsAudio=null,rendered;
const lyricsSync={dispose(){}};
function cancelLyricsSeek(){}
function formatAudioTime(){return '0:00';}
function setLyricsView(){rendered=lyricsDocument;}
const pending=[];
global.fetch=()=>new Promise(resolve=>pending.push(resolve));
const button=(path,title)=>({disabled:false,dataset:{filePath:path,lyricsTitle:title,lyricsArtist:'Исполнитель '+title},closest:()=>null});
(async()=>{
 const old=openLyricsModal(button('old.flac','Старая'));
 const current=openLyricsModal(button('new.flac','Новая'));
 pending[1]({ok:true,json:async()=>({ok:true,lyrics:'[00:01.00]Новая строка',source:'Встроенные теги'})});
 await current;
 assert.equal(lyricsTitle.textContent,'Новая');
 assert.equal(lyricsArtist.textContent,'Исполнитель Новая');
 pending[0]({ok:true,json:async()=>({ok:true,lyrics:'[ti:Старая]\n[00:01.00]Старая строка'})});
 await old;
 assert.equal(lyricsTitle.textContent,'Новая'); assert.equal(lyricsPath.textContent,'new.flac');
 assert.deepEqual(rendered.blocks,[{type:'stanza',lines:['Новая строка']}]);
 assert.equal(lyricsOriginal.disabled,false);
})().catch(error=>{console.error(error);process.exitCode=1;});
''')


if __name__ == '__main__':
    unittest.main()
