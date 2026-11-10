from __future__ import annotations

import csv
import contextlib
import html
import http.client
import io
import json
import re
import subprocess
import sys
import tempfile
import threading
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import library_source as sources
import report_server as server
from report_server import run_command
from scan_progress import ProgressStore


class LibrarySourceTests(unittest.TestCase):
    def files(self, folder):
        return sources.SourceFiles(folder / "library.html", folder / "duplicates.csv", folder / "duplicates_needs_review.csv", folder / "source.json", folder / "source_actions.csv", folder / "source_backups")

    def test_browser_lists_only_directories_and_preserves_unicode_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "Альбом & песни").mkdir()
            (root / "Beta").mkdir()
            (root / "track.mp3").write_bytes(b"audio")
            result = sources.list_folders(str(root))
            self.assertEqual({entry["name"] for entry in result["folders"]}, {"Альбом & песни", "Beta"})
            self.assertEqual(result["path"], str(root.resolve()))
            self.assertEqual(result["parent"], str(root.resolve().parent))

    def test_invalid_folder_is_rejected(self):
        with self.assertRaises(RuntimeError):
            sources.validate_folder("")
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp) / "file.txt"
            file.write_text("not a folder", encoding="utf-8")
            with self.assertRaises(RuntimeError):
                sources.validate_folder(str(file))

    def test_source_change_requires_confirmation_before_running_a_scan(self):
        with tempfile.TemporaryDirectory() as temp:
            files = self.files(Path(temp))
            files.html.write_text("old report", encoding="utf-8")
            with self.assertRaises(RuntimeError):
                sources.change_source(str(Path(temp)), "", files, lambda args: self.fail("Scan must not start"), "old")
            self.assertEqual(files.html.read_text(encoding="utf-8"), "old report")

    def test_failed_scan_preserves_all_previous_reports(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            library = root / "new library"
            library.mkdir()
            files = self.files(root)
            for file in [files.html, files.csv, files.review, files.settings]:
                file.write_text("old contents", encoding="utf-8")
            failed = lambda args: subprocess.CompletedProcess(args, 1, "scan failed")
            with self.assertRaisesRegex(RuntimeError, "scan failed"):
                sources.change_source(str(library), "CHANGE_LIBRARY_SOURCE", files, failed, "old")
            self.assertTrue(all(file.read_text(encoding="utf-8") == "old contents" for file in [files.html, files.csv, files.review, files.settings]))

    def test_real_scan_switches_report_but_does_not_change_music(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            library = root / "music with spaces"
            library.mkdir()
            audio = library / "sample.wav"
            with wave.open(str(audio), "wb") as out:
                out.setnchannels(1)
                out.setsampwidth(2)
                out.setframerate(8000)
                out.writeframes(b"\0\0" * 800)
            original = audio.read_bytes()
            files = self.files(root)
            files.html.write_text("old report", encoding="utf-8")
            bindings = {"REPORT_HTML": files.html, "REPORT_CSV": files.csv, "REVIEW_CSV": files.review, "SOURCE_SETTINGS": files.settings, "SOURCE_ACTIONS_CSV": files.actions, "SOURCE_BACKUPS": files.backups, "_SOURCE_OVERRIDE": "", "_REPORT_CACHE": {}, "_AUDIO_PATH_CACHE": {}, "_ENRICHMENT_CANDIDATES": {}, "_SOURCE_PROGRESS": ProgressStore()}
            with contextlib.ExitStack() as stack:
                for name, value in bindings.items():
                    stack.enter_context(patch.object(server, name, value))
                stack.enter_context(contextlib.redirect_stderr(io.StringIO()))
                httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.ReportHandler)
                worker = threading.Thread(target=httpd.serve_forever, daemon=True)
                worker.start()
                connection = http.client.HTTPConnection("127.0.0.1", httpd.server_port, timeout=20)
                try:
                    connection.request("POST", "/api/library-source", json.dumps({"path": str(library), "confirm": "CHANGE_LIBRARY_SOURCE"}), {"Content-Type": "application/json", "Origin": "https://unrelated.example"})
                    rejected = connection.getresponse()
                    rejected.read()
                    self.assertEqual(rejected.status, 403)
                    connection.request("POST", "/api/library-source", json.dumps({"path": str(library)}), {"Content-Type": "application/json"})
                    rejected = connection.getresponse()
                    rejected.read()
                    self.assertEqual(rejected.status, 400)
                    self.assertEqual(files.html.read_text(encoding="utf-8"), "old report")
                    scan_id = "12345678-1234-1234-1234-123456789abc"
                    connection.request("POST", "/api/library-source", json.dumps({"path": str(library), "confirm": "CHANGE_LIBRARY_SOURCE", "progress_id": scan_id}), {"Content-Type": "application/json"})
                    response = connection.getresponse()
                    self.assertEqual(response.status, 200)
                    result = json.loads(response.read())
                    connection.request("GET", "/api/library-source/progress?id=" + scan_id)
                    response = connection.getresponse()
                    progress = json.loads(response.read())
                    self.assertEqual(progress["status"], "completed")
                    self.assertEqual(progress["stage"], "completed")
                    connection.request("GET", "/api/library-source")
                    response = connection.getresponse()
                    self.assertEqual(json.loads(response.read())["path"], str(library.resolve()))
                    self.assertEqual(server.library_path(), str(library.resolve()))
                finally:
                    connection.close()
                    httpd.shutdown()
                    worker.join(timeout=5)
                    httpd.server_close()
            self.assertTrue(result["ok"])
            text = files.html.read_text(encoding="utf-8")
            payload = json.loads(html.unescape(re.search(r'<script id="payload" type="application/json">(.*?)</script>', text, re.S)[1]))
            self.assertEqual(payload["library"]["path"], str(library.resolve()))
            self.assertEqual(payload["library"]["total_files"], 1)
            self.assertEqual(audio.read_bytes(), original)
            self.assertEqual(list(library.iterdir()), [audio])
            self.assertEqual(json.loads(files.settings.read_text(encoding="utf-8"))["path"], str(library.resolve()))
            self.assertEqual((Path(result["backup"]) / "library.html").read_text(encoding="utf-8"), "old report")
            with files.actions.open(encoding="utf-8", newline="") as handle:
                self.assertEqual(list(csv.DictReader(handle))[-1]["status"], "completed")

    def test_progress_can_be_read_while_the_source_post_is_still_running(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            library = root / "music"
            library.mkdir()
            with wave.open(str(library / "sample.wav"), "wb") as audio:
                audio.setnchannels(1)
                audio.setsampwidth(2)
                audio.setframerate(8000)
                audio.writeframes(b"\0\0" * 80)
            files = self.files(root)
            files.html.write_text("old report", encoding="utf-8")
            entered, release = threading.Event(), threading.Event()
            result = {}
            def runner(args, progress):
                def received(event):
                    progress(event)
                    if event["stage"] == "tags" and event["processed"] == 0:
                        entered.set()
                        if not release.wait(10):
                            raise RuntimeError("Test did not release scan")
                return run_command(args, received)
            bindings = {"REPORT_HTML":files.html, "REPORT_CSV":files.csv, "REVIEW_CSV":files.review, "SOURCE_SETTINGS":files.settings, "SOURCE_ACTIONS_CSV":files.actions, "SOURCE_BACKUPS":files.backups, "_SOURCE_OVERRIDE":"", "_SOURCE_PROGRESS":ProgressStore(), "_REPORT_CACHE":{}, "_AUDIO_PATH_CACHE":{}, "_ENRICHMENT_CANDIDATES":{}, "run_command":runner}
            with contextlib.ExitStack() as stack:
                for name,value in bindings.items():
                    stack.enter_context(patch.object(server,name,value))
                stack.enter_context(contextlib.redirect_stderr(io.StringIO()))
                httpd = server.ThreadingHTTPServer(("127.0.0.1",0),server.ReportHandler)
                http_worker = threading.Thread(target=httpd.serve_forever,daemon=True)
                http_worker.start()
                scan_id = "abcdefab-1234-1234-1234-123456789abc"
                def post():
                    client = http.client.HTTPConnection("127.0.0.1",httpd.server_port,timeout=20)
                    try:
                        client.request("POST","/api/library-source",json.dumps({"path":str(library),"confirm":"CHANGE_LIBRARY_SOURCE","progress_id":scan_id}),{"Content-Type":"application/json"})
                        response=client.getresponse()
                        result.update(status=response.status,body=json.loads(response.read()))
                    except Exception as error:
                        result["error"]=str(error)
                    finally:
                        client.close()
                post_worker = threading.Thread(target=post,daemon=True)
                post_worker.start()
                client = http.client.HTTPConnection("127.0.0.1",httpd.server_port,timeout=3)
                try:
                    self.assertTrue(entered.wait(10))
                    client.request("GET","/api/library-source/progress?id="+scan_id)
                    response=client.getresponse()
                    state=json.loads(response.read())
                    self.assertEqual(response.status,200)
                    self.assertEqual((state["status"],state["stage"],state["processed"],state["total"]),("running","tags",0,1))
                    self.assertTrue(post_worker.is_alive())
                    self.assertEqual(files.html.read_text(encoding="utf-8"),"old report")
                finally:
                    release.set()
                    post_worker.join(15)
                    client.close()
                    httpd.shutdown()
                    http_worker.join(5)
                    httpd.server_close()
                self.assertEqual(result.get("status"),200,result)

    def test_saved_choice_does_not_override_a_new_report_from_cli(self):
        with tempfile.TemporaryDirectory() as temp:
            settings = Path(temp) / "source.json"
            settings.write_text(json.dumps({"path": str(Path(temp) / "old")}), encoding="utf-8")
            self.assertEqual(sources.saved_source(settings, str(Path(temp) / "new")), "")
            self.assertEqual(sources.saved_source(settings, str(Path(temp) / "old")), str(Path(temp) / "old"))

    def test_publish_failure_restores_reports_already_replaced(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            library = root / "new library"
            library.mkdir()
            files = self.files(root)
            for file in [files.html, files.csv, files.review, files.settings]:
                file.write_text("old contents", encoding="utf-8")
            replace = Path.replace
            def fail_html(source, target):
                if Path(target) == files.html:
                    raise PermissionError("publish failed")
                return replace(source, target)
            with patch.object(Path, "replace", fail_html), self.assertRaisesRegex(RuntimeError, "publish failed"):
                sources.change_source(str(library), "CHANGE_LIBRARY_SOURCE", files, run_command, "old")
            self.assertTrue(all(file.read_text(encoding="utf-8") == "old contents" for file in [files.html, files.csv, files.review, files.settings]))
