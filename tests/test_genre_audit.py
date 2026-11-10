import copy
import csv
import html
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from audit_genres import audit_tracks


class GenreAuditTests(unittest.TestCase):
    def test_audit_covers_all_values_and_only_unverified_cases_need_review(self):
        tracks=[
            {'path':'Песня 1.flac','tags':[{'kind':'genre','value':'Pop; International Pop'},{'kind':'genre','value':'Pop; International Pop'}]},
            {'path':'Песня 2.flac','tags':[{'kind':'genre','value':'Pop; International Pop'}]},
            {'path':'Песня 3.flac','tags':[{'kind':'genre','value':'Compilation'}]},
            {'path':'Песня 4.flac','tags':[{'kind':'genre','value':'Pop; Unknown 123'}]},
        ]
        original=copy.deepcopy(tracks)
        rows,review=audit_tracks(tracks)
        self.assertEqual(len(rows),3)
        self.assertEqual(rows[0]['files'],2)
        self.assertEqual(rows[0]['normalized_genres'],'Pop')
        self.assertEqual([row['file'] for row in review],['Песня 4.flac'])
        self.assertEqual(tracks,original)

    def test_cli_writes_complete_utf8_reports_without_changing_the_input(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder=Path(temporary)
            source=folder/'library.html'
            payload={'library':{'tracks':[{'path':'D:/Музыка/Песня.flac','tags':[{'kind':'genre','value':'Рок; Unknown 123'}]}]}}
            document='<script id="payload" type="application/json">'+html.escape(json.dumps(payload,ensure_ascii=False))+'</script>'
            source.write_text(document,encoding='utf-8')
            output=folder/'audit.csv'
            result=subprocess.run([sys.executable,str(ROOT/'scripts/audit_genres.py'),'--html',str(source),'--out',str(output)],capture_output=True,text=True,encoding='utf-8')
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(result.stdout)['review_rows'],1)
            with output.open(encoding='utf-8-sig',newline='') as stream:
                rows=list(csv.DictReader(stream))
            self.assertEqual(rows[0]['normalized_genres'],'Rock')
            self.assertEqual(rows[0]['example_file'],'D:/Музыка/Песня.flac')
            self.assertEqual(json.loads(output.with_suffix('.json').read_text(encoding='utf-8'))['review_rows'],1)
            self.assertEqual(source.read_text(encoding='utf-8'),document)
