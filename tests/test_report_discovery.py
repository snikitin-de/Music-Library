"""Search whole duplicate groups and display each file only once."""
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from generate_html_report import ReportRow, build_payload, render_html
from test_report_interface import Elements


class ReportDiscoveryTests(unittest.TestCase):
    def document(self):
        rows = [ReportRow('raw group', 'D:/Music/best.flac', path, 'lower quality score',
                          'format=flac; bitrate=900000', 'format=mp3; bitrate=320000')
                for path in ['D:/Music/other.mp3', 'D:/Music/third.mp3']]
        tracks = [{'path': 'D:/Music/third.mp3', 'name': 'third.mp3', 'tags': [
            {'kind': 'artist', 'value': 'Ёлка'}, {'kind': 'album', 'value': 'Редкий <альбом>'}]}]
        return render_html(build_payload(rows, {'path': 'D:/Music', 'tracks': tracks, 'total_files': 3}))

    def test_multi_file_group_shows_one_reference_and_every_candidate(self):
        elements = Elements(self.document()).elements
        files = [a for _, a in elements if 'duplicate-track' in a.get('class', '').split()]
        self.assertEqual([a['data-file-path'] for a in files],
                         ['D:/Music/best.flac', 'D:/Music/other.mp3', 'D:/Music/third.mp3'])
        self.assertEqual(sum('keep' in a['class'].split() for a in files), 1)
        actions = [a['data-file'] for _, a in elements if 'quarantine-one' in a.get('class', '').split()]
        self.assertEqual(actions, ['D:/Music/best.flac', 'D:/Music/other.mp3', 'D:/Music/third.mp3'])

    def test_search_indexes_metadata_from_every_candidate_and_has_separate_inputs(self):
        elements = Elements(self.document()).elements
        group = next(a for _, a in elements if 'group-card' in a.get('class', '').split())
        self.assertIn('ёлка', group['data-search'])
        self.assertIn('редкий <альбом>', group['data-search'])
        ids = [a.get('id') for _, a in elements]
        self.assertEqual(ids.count('duplicateSearch'), 1)
        self.assertEqual(ids.count('musicSearch'), 1)

    def test_duplicate_search_includes_unmounted_groups_resets_paging_and_can_clear(self):
        source = (Path(__file__).resolve().parents[1] / 'scripts/generate_html_report.py').read_text(encoding='utf-8')
        start = source.index('    function applyDuplicateFilters(')
        end = source.index('    function audioPath(', start)
        function = source[start:end].replace('{{', '{').replace('}}', '}')
        script = r'''
const assert = require('node:assert/strict');
const cards = Array.from({length:25}, (_,i)=>({hidden:false,dataset:{search:i===24?'ёлка редкий альбом':'другой трек'}}));
const duplicateSearch={value:'  ЁЛКА  ',closest:()=>({classList:{toggle(){}}})};
const empty={classList:{toggle(_,v){this.visible=v;}}};
const document={getElementById:()=>empty};
let matches;
const playbackContext='duplicates';let queueGroups;
function updatePlaybackQueue(){queueGroups=cards.filter(card=>!card.hidden);}
const duplicatePager={setItems(items){matches=items;}};
function updateSearchPlaceholder(){}
''' + function + r'''
applyDuplicateFilters();
assert.deepEqual(matches,[cards[24]],'Unloaded groups must be searchable');
assert.deepEqual(queueGroups,[cards[24]],'The playback queue follows the current search');
assert.equal(cards[0].hidden,true); assert.equal(cards[24].hidden,false);
duplicateSearch.value='no match'; applyDuplicateFilters();
assert.equal(matches.length,0); assert.equal(empty.classList.visible,true);
duplicateSearch.value=''; applyDuplicateFilters();
assert.equal(matches.length,25); assert.equal(empty.classList.visible,false);
'''
        result = subprocess.run(['node', '-'], input=script, text=True, encoding='utf-8', capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_removing_one_candidate_keeps_reference_and_remaining_candidates(self):
        source = self.document()
        functions = source[source.index('    function refreshGroupAfterComparisonRemoval('):source.index('    function clearTagAttributes(')]
        normalize = source[source.index('    function normalizePathForCompare('):source.index('    function setDuplicateStatus(')]
        filtering = source[source.index('    function applyDuplicateFilters('):source.index('    function audioPath(')]
        script = r'''
const assert=require('node:assert/strict');
const fields={};
const document={getElementById(id){return fields[id] ||= {textContent:'',classList:{toggle(){}}};}};
const duplicateSearch={value:''};
function updateSearchPlaceholder(){}
let pageItems;
const playbackContext='duplicates';
function updatePlaybackQueue(){}
const duplicatePager={setItems(items){pageItems=items;}};
let candidates=['D:/Music/a.mp3','D:/Music/b.mp3'].map((path,i)=>({dataset:{filePath:path,search:i===0?'removed album':'remaining album',referenceBetter:i===0?'bitrate':''},remove(){candidates=candidates.filter(c=>c!==this);}}));
const reference={dataset:{search:'best track'}};
const cell={dataset:{quality:'bitrate'},classList:{toggle(_,on){this.green=on;}}};
let comparisonPresent=true;
const comparison={dataset:{keptFile:'D:/Music/best.flac'},
 querySelectorAll(selector){return selector==='.keep td[data-quality]'?[cell]:candidates;},querySelector(){return candidates[0];},
 closest(){return group;},remove(){comparisonPresent=false;}};
const subtitle={textContent:''};
const group={dataset:{reviewOnly:'no',search:'track removed album',searchBase:'track'},hidden:false,
 querySelectorAll(selector){return selector==='.comparison'?(comparisonPresent?[comparison]:[]):(comparisonPresent?(selector==='.duplicate-track'?[reference,...candidates]:candidates):[]);},
 querySelector(){return subtitle;},remove(){this.removed=true;}};
let cards=[group];
''' + normalize + functions + filtering + r'''
removeDuplicateComparisonsByPaths([String.raw`d:\Music\a.mp3`]);
assert.equal(comparisonPresent,true,'Keep the reference while other candidates remain');
assert.equal(cards.length,1); assert.deepEqual(candidates.map(c=>c.dataset.filePath),['D:/Music/b.mp3']);
assert.equal(group.dataset.count,'1'); assert.equal(fields.duplicateFilesMetric.textContent,'1');
assert.ok(!group.dataset.search.includes('removed album'),'Drop removed candidate metadata from search');
assert.equal(cell.classList.green,false,'Equal remaining values must lose their old advantage');
assert.deepEqual(pageItems,[group]);
removeDuplicateComparisonsByPaths(['D:/Music/b.mp3']);
assert.equal(cards.length,0,'Remove empty groups after their last candidate');
assert.equal(fields.duplicateFilesMetric.textContent,'0');
'''
        result = subprocess.run(['node', '-'], input=script, text=True, encoding='utf-8', capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
