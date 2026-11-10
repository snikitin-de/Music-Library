from __future__ import annotations

import json
import sys
import tempfile
import unittest
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from scan_progress import ProgressStore, progress_files, run_streaming
from find_duplicates import scan_library_with_stats, group_content_duplicates
from generate_html_report import analyze_library


class ScanProgressTests(unittest.TestCase):
    def test_file_counts_are_reported_after_each_file_is_processed(self):
        events = []
        files = progress_files(iter([Path('a.wav'), Path('b.wav')]), events.append, 'tags')
        self.assertEqual(next(files), Path('a.wav'))
        self.assertEqual(events[-1], {'stage':'tags', 'processed':0, 'total':2, 'current':''})
        self.assertEqual(next(files), Path('b.wav'))
        self.assertEqual(events[-1]['processed'], 1)
        self.assertEqual(list(files), [])
        self.assertEqual(events[-1]['processed'], 2)

    def test_scanner_and_report_analysis_emit_real_totals(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in ['a.wav', 'b.wav']:
                with wave.open(str(root / name), 'wb') as audio:
                    audio.setnchannels(1)
                    audio.setsampwidth(2)
                    audio.setframerate(8000)
                    audio.writeframes(b'\0\0' * 80)
            events = []
            tracks, stats = scan_library_with_stats(root, events.append)
            group_content_duplicates(tracks, {}, stats, events.append)
            report = analyze_library(root, progress=events.append)
            for stage in ['tags', 'hashes', 'analysis']:
                final = [event for event in events if event['stage'] == stage][-1]
                self.assertEqual((final['processed'], final['total']), (2, 2))
            self.assertEqual(report['total_files'], 2)

    def test_subprocess_delivers_progress_before_it_exits(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            marker = root / 'observed'
            code = "import json,time,sys; from pathlib import Path; print('@@SCAN_PROGRESS '+json.dumps({'stage':'tags','processed':1,'total':2,'current':'песня.wav'}),flush=True); marker=Path(sys.argv[1]); deadline=time.monotonic()+3\nwhile not marker.exists() and time.monotonic()<deadline: time.sleep(.01)\nprint('finished'); sys.exit(0 if marker.exists() else 3)"
            events = []
            def received(event):
                events.append(event)
                marker.write_text('seen', encoding='utf-8')
            result = run_streaming([sys.executable, '-u', '-c', code, str(marker)], root, received, timeout=5)
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertEqual(events[0]['current'], 'песня.wav')
            self.assertIn('finished', result.stdout)

    def test_store_separates_scans_and_does_not_report_false_completion(self):
        store = ProgressStore()
        update = store.start('12345678-1234-1234-1234-123456789abc')
        self.assertEqual(store.snapshot('12345678-1234-1234-1234-123456789abc')['status'], 'running')
        update({'stage':'tags','processed':3,'total':9,'current':'a.wav'})
        snapshot = store.snapshot('12345678-1234-1234-1234-123456789abc')
        self.assertEqual((snapshot['processed'],snapshot['total']), (3,9))
        with self.assertRaises(RuntimeError):
            store.start('12345678-1234-1234-1234-123456789abc')
        self.assertIsNone(store.snapshot('unknown'))
        update({'stage':'failed','status':'failed','error':'scan failed'})
        self.assertEqual(store.snapshot('12345678-1234-1234-1234-123456789abc')['status'], 'failed')

    def test_empty_library_finishes_counted_phases_without_dividing_by_zero(self):
        events = []
        self.assertEqual(list(progress_files(iter([]), events.append, 'tags')), [])
        self.assertEqual((events[-1]['processed'],events[-1]['total']), (0,0))
