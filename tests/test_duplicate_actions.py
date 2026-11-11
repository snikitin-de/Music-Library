"""Regression coverage for file moves and rescanning from the duplicate report."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

import report_server as server
from generate_html_report import ReportRow, build_payload, render_html
from scan_progress import ProgressStore


class DuplicateActionsTests(unittest.TestCase):
    def setUp(self):
        temp = self.enterContext(tempfile.TemporaryDirectory())
        root = Path(temp)
        self.library = root / 'Library'
        self.library.mkdir()
        self.quarantine = root / 'Duplicates'
        self.trash = root / 'Trash'
        self.files = [self.library / name for name in ('a.flac', 'b.flac', 'c.flac')]
        for file in self.files:
            file.write_bytes(b'test audio')
        self.enterContext(patch.multiple(
            server, REPORT_HTML=root / 'library.html', REPORT_CSV=root / 'duplicates.csv',
            REVIEW_CSV=root / 'duplicates_needs_review.csv', FILE_ACTIONS_CSV=root / 'file_actions.csv',
            SOURCE_SETTINGS=root / 'source.json', SOURCE_ACTIONS_CSV=root / 'source_actions.csv',
            SOURCE_BACKUPS=root / 'backups', _SOURCE_PROGRESS=ProgressStore(),
            _REPORT_CACHE={}, _AUDIO_PATH_CACHE={}, _ENRICHMENT_CANDIDATES={},
            library_path=Mock(return_value=str(self.library)),
            quarantine_path=Mock(return_value=str(self.quarantine)),
            trash_path=Mock(return_value=str(self.trash)),
        ))
        tracks = [dict(path=str(file), name=file.name, tags=[]) for file in self.files]
        server.REPORT_HTML.write_text(render_html(build_payload([], dict(path=str(self.library), tracks=tracks))), encoding='utf-8')

    def post(self, path, **body):
        handler = Mock(path=path)
        handler.read_json.return_value = body
        server.ReportHandler.handle_post(handler)
        return handler.send_json.call_args.args

    def write_groups(self, review=False):
        quality = ['format=flac; bitrate=' + str(rate) for rate in (900000, 800000, 700000)]
        if review:
            server.write_review_report_rows([
                dict(review_group='review', file=str(file), reason='needs_review: same artist/title, tag key is not identical', quality=values)
                for file, values in zip(self.files, quality)
            ])
        else:
            server.write_duplicate_rows([
                dict(duplicate_group='normal', kept_file=str(self.files[0]), moved_file=str(file),
                     reason='lower quality score', kept_quality=quality[0], moved_quality=values)
                for file, values in zip(self.files[1:], quality[1:])
            ])

    def test_file_moves_require_real_mode_even_with_a_confirmation_token(self):
        self.write_groups()
        for endpoint, token in [('/api/quarantine-one', 'MOVE_TO_QUARANTINE'), ('/api/trash-file', 'MOVE_TO_TRASH')]:
            for mode in ({}, {'mode': 'dry-run'}):
                with self.subTest(endpoint=endpoint, mode=mode):
                    status, result = self.post(endpoint, file=str(self.files[0]), confirm=token, **mode)
                    self.assertEqual(status, 400, result)
        self.assertTrue(all(file.exists() for file in self.files))
        self.assertFalse(server.FILE_ACTIONS_CSV.exists())

    def test_quarantine_promotes_the_highest_ranked_remaining_file(self):
        self.write_groups()
        status, result = self.post('/api/quarantine-one', file=str(self.files[0]), mode='real', confirm='MOVE_TO_QUARANTINE')
        self.assertEqual(status, 200, result)
        self.assertTrue(result['reload'])
        self.assertTrue((self.quarantine / self.files[0].name).exists())
        row, = server.read_duplicate_rows()
        self.assertEqual((row['kept_file'], row['moved_file']), tuple(map(str, self.files[1:])))
        self.assertEqual(row['kept_quality'], 'format=flac; bitrate=800000')
        group, = server.read_payload()['groups']
        self.assertEqual(group['name'], 'normal')

    def test_trash_keeps_the_two_remaining_possible_duplicates(self):
        self.write_groups(review=True)
        status, result = self.post('/api/trash-file', file=str(self.files[0]), mode='real', confirm='MOVE_TO_TRASH')
        self.assertEqual(status, 200, result)
        self.assertTrue(result['reload'])
        self.assertTrue((self.trash / self.files[0].name).exists())
        self.assertEqual([row['file'] for row in server.read_review_report_rows()], list(map(str, self.files[1:])))
        group, = server.read_payload()['groups']
        self.assertTrue(group['review_only'])

    def test_rescan_streams_progress_and_preserves_reports_when_render_fails(self):
        self.write_groups()
        original = server.REPORT_CSV.read_bytes()
        scan_id = 'rescan-regression-1'
        stages = []

        def run(args, progress=None):
            self.assertIn('--progress', args)
            if '--report' in args:
                Path(args[args.index('--report') + 1]).write_bytes(b'new report')
                progress(dict(stage='hashes', processed=2, total=3))
                stages.append(server._SOURCE_PROGRESS.snapshot(scan_id)['stage'])
                return subprocess.CompletedProcess(args, 0, '')
            return subprocess.CompletedProcess(args, 1, 'Test render failure')

        with patch.object(server, 'run_command', side_effect=run):
            status, result = self.post('/api/rescan-library', confirm='RESCAN_LIBRARY', progress_id=scan_id)
        self.assertEqual(status, 400, result)
        self.assertEqual(stages, ['hashes'])
        self.assertEqual(server._SOURCE_PROGRESS.snapshot(scan_id)['status'], 'failed')
        self.assertEqual(server.REPORT_CSV.read_bytes(), original)
