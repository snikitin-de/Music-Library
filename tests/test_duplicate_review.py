"""Review duplicate groups without hiding differences or implying a completed move."""
import re
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from generate_html_report import ReportRow, build_payload, render_html
from test_report_interface import Elements


class DuplicateReviewTests(unittest.TestCase):
    def test_standalone_main_script_has_valid_javascript_syntax(self):
        script = re.findall(r'<script(?:\s[^>]*)?>(.*?)</script>', self.document(), re.S)[-1]
        result = subprocess.run(['node', '--check'], input=script, text=True, encoding='utf-8', capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def document(self):
        rows = [ReportRow('Группа', 'D:/Music/a.flac', 'D:/Music/b.flac',
                          'lower quality score', 'format=flac; bitrate=956000; lyrics=False',
                          'format=flac; bitrate=953000; lyrics=True')]
        return render_html(build_payload(rows, {'path': 'D:/Music', 'tracks': []}))

    def test_duration_is_displayed_as_a_difference_without_a_quality_advantage(self):
        rows = [ReportRow('Группа', 'D:/Music/a.flac', 'D:/Music/b.flac',
                          'lower quality score', 'format=flac; duration=245',
                          'format=flac; duration=3600')]
        document = render_html(build_payload(rows, {'path': 'D:/Music', 'tracks': []}))
        values = re.findall(r'<th scope="row">Длительность</th><td data-quality="duration"([^>]*)>(.*?)</td>', document)
        self.assertEqual(values, [('', '4:05'), ('', '1:00:00')])

    def test_groups_start_collapsed_and_remain_keyboard_accessible(self):
        elements = Elements(self.document()).elements
        tag, group = next((tag, a) for tag, a in elements if 'group-card' in a.get('class', '').split())
        self.assertEqual(tag, 'details')
        self.assertNotIn('open', group)
        self.assertTrue(any(tag == 'summary' and 'group-header' in a.get('class', '').split()
                            for tag, a in elements))

    def test_unprocessed_files_are_labelled_as_recommendations(self):
        labels = re.findall(r'<span class="track-label">(.*?)</span>', self.document(), re.S)
        self.assertEqual(labels, ['Предлагается оставить', 'Предлагается в карантин'])

    def test_recommendation_names_the_deciding_available_advantage(self):
        reasons = re.findall(r'<span class="duplicate-reason">(.*?)</span>', self.document(), re.S)
        self.assertEqual(reasons, ['', 'У файла 1 выше битрейт'])

    def test_each_file_has_an_explicit_listen_action_and_exact_path(self):
        actions = [a for _, a in Elements(self.document()).elements
                   if 'duplicate-listen' in a.get('class', '').split()]
        self.assertEqual([a['data-file-path'] for a in actions], ['D:/Music/a.flac', 'D:/Music/b.flac'])

    def test_comparison_preserves_unknowns_and_recomputes_for_remaining_candidates(self):
        document = self.document()
        match = re.search(r'<script id="reportDuplicates">(.*?)</script>', document, re.S)
        self.assertIsNotNone(match, 'Standalone reports must embed duplicate review logic')
        script = r'''
const assert = require('node:assert/strict');
''' + match[1] + r'''
const files = [
 {path:'a', rows:[{key:'format',label:'Формат',value:'FLAC'}, {key:'lyrics',label:'Текст песни',value:'—'}, {key:'bitrate',label:'Битрейт',value:'956 kbps',better:true}]},
 {path:'b', rows:[{key:'format',label:'Формат',value:'FLAC'}, {key:'lyrics',label:'Текст песни',value:'Нет'}, {key:'bitrate',label:'Битрейт',value:'953 kbps'}]},
 {path:'c', rows:[{key:'format',label:'Формат',value:'FLAC'}, {key:'lyrics',label:'Текст песни',value:'—'}, {key:'bitrate',label:'Битрейт',value:'956 kbps'}]},
];
let rows = ReportDuplicates.comparisonRows(files);
assert.deepEqual(rows.filter(r=>r.different).map(r=>r.key), ['lyrics','bitrate']);
assert.deepEqual(rows[1].values.map(v=>v.value), ['—','Нет','—']);
assert.deepEqual(rows[2].values.map(v=>v.path), ['a','b','c']);
rows = ReportDuplicates.comparisonRows([files[0],files[2]]);
assert.equal(rows.filter(r=>r.different).length,0,'Removing the differing candidate must clear the differences');
assert.ok(rows.every(r=>r.values.every(v=>!v.better)), 'Equal remaining values lose their old advantage');
assert.deepEqual(ReportDuplicates.comparisonRows([]), []);
'''
        result = subprocess.run(['node', '-'], input=script, text=True, encoding='utf-8', capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_separate_file_parameters_keep_values_with_their_file_and_share_the_filter(self):
        module = re.search(r'<script id="reportDuplicates">(.*?)</script>', self.document(), re.S)[1]
        script = "const assert = require('node:assert/strict');\n" + module + r'''
const files = [
 {path:'a.flac',label:'Файл 1',rows:[{key:'format',label:'Формат',value:'FLAC'}, {key:'lyrics',label:'Текст песни',value:'Нет'}, {key:'bitrate',label:'Битрейт',value:'956 kbps',better:true}]},
 {path:'b.flac',label:'Файл 2',rows:[{key:'format',label:'Формат',value:'FLAC'}, {key:'lyrics',label:'Текст песни',value:'Да',better:true}, {key:'bitrate',label:'Битрейт',value:'953 kbps'}]},
];
let columns = ReportDuplicates.fileParameters(files, false);
assert.deepEqual(columns.map(c=>c.path), ['a.flac','b.flac']);
assert.deepEqual(columns.map(c=>c.rows.map(r=>r.key)), [['lyrics','bitrate'],['lyrics','bitrate']]);
assert.deepEqual(columns.map(c=>c.rows.map(r=>r.value)), [['Нет','956 kbps'],['Да','953 kbps']]);
assert.deepEqual(columns.map(c=>c.rows.map(r=>r.better)), [[false,true],[true,false]]);
columns = ReportDuplicates.fileParameters(files, true);
assert.deepEqual(columns.map(c=>c.rows.map(r=>r.value)), [['FLAC','Нет','956 kbps'],['FLAC','Да','953 kbps']]);
assert.deepEqual(ReportDuplicates.fileParameters([], false), []);
'''
        result = subprocess.run(['node', '-'], input=script, text=True, encoding='utf-8', capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
