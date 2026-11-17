import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from report_user_state import ReportUserState, StateConflict


class ReportUserStateTests(unittest.TestCase):
    def test_import_merges_backup_without_changing_existing_playlists_or_duplicate_listens(self):
        with tempfile.TemporaryDirectory() as directory:
            state = ReportUserState(Path(directory))
            original = {"id": "one", "name": "Мой плейлист", "tracks": [{"path": "C:/Music/A.flac"}]}
            state.update({"action": "playlists", "revision": 0, "playlists": [original]})
            with self.assertRaises(StateConflict):
                state.update({"action": "playlists", "revision": 0, "playlists": []})
            entry = {"path": "C:/Music/A.flac", "playedAt": 1700000000000, "title": "Трек"}
            backup = {
                "version": 1,
                "playlists": [{"id": "one", "name": "Копия", "tracks": [{"path": "C:/MUSIC/a.flac"}, {"path": "C:/Music/B.flac"}]}],
                "history": [entry],
            }
            state.update({"action": "import", "backup": backup})
            state.update({"action": "import", "backup": backup})
            state.update({"action": "listen", "entry": entry})
            saved = ReportUserState(Path(directory)).read()
            self.assertEqual(saved["playlists"][0]["name"], original["name"])
            self.assertEqual([track["path"] for track in saved["playlists"][0]["tracks"]], ["C:/Music/A.flac", "C:/Music/B.flac"])
            self.assertEqual(len(saved["history"]), 1)
            invalid = {**backup, "history": [{"path": "B.flac", "playedAt": float("nan")}]}
            with self.assertRaises(RuntimeError):
                state.update({"action": "import", "backup": invalid})
            self.assertEqual(state.read(), saved)

    def test_late_progress_does_not_replace_a_newer_session(self):
        with tempfile.TemporaryDirectory() as directory:
            state = ReportUserState(Path(directory))
            old = {"token": "old", "updatedAt": 10, "position": 2, "track": {"path": "A.flac"}, "manualQueue": []}
            new = {**old, "token": "new", "updatedAt": 20, "position": 7, "manualQueue": [{"path": "B.flac"}]}
            state.update({"action": "session", "session": old})
            state.update({"action": "session", "session": new})
            state.update({"action": "position", "token": "old", "updatedAt": 30, "position": 2})
            state.update({"action": "position", "token": "new", "updatedAt": 31, "position": 8})
            state.update({"action": "position", "token": "new", "updatedAt": 21, "position": 1})
            state.update({"action": "session", "session": old})
            saved = json.loads(state.session_file.read_text(encoding="utf-8"))
            self.assertEqual(saved["position"], 8)
            self.assertEqual(saved["manualQueue"][0]["path"], "B.flac")


if __name__ == "__main__":
    unittest.main()
