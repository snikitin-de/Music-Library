from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import media_enrichment as enrichment


class MediaEnrichmentTests(unittest.TestCase):
    def test_lrclib_prefers_synced_lyrics(self) -> None:
        metadata = enrichment.TrackMetadata("Artist", "Artist", "Album", "Song", 180)
        response = [
            {
                "artistName": "Artist",
                "trackName": "Song",
                "albumName": "Album",
                "duration": 180,
                "syncedLyrics": "[00:01.00]First line",
                "plainLyrics": "First line",
            }
        ]
        with patch.object(enrichment, "_request_json", return_value=response):
            candidates = enrichment.search_lyrics(metadata)
        self.assertEqual(candidates[0]["kind"], "synced")
        self.assertEqual(candidates[0]["preview"], "First line")

    def test_cover_search_builds_archive_candidate(self) -> None:
        metadata = enrichment.TrackMetadata("Artist", "Artist", "Album", "Song")
        response = {
            "releases": [
                {
                    "id": "release-id",
                    "title": "Album",
                    "date": "2024",
                    "score": 100,
                    "artist-credit": [{"name": "Artist", "joinphrase": ""}],
                }
            ]
        }
        with patch.object(enrichment, "_request_json", return_value=response):
            candidates = enrichment.search_covers(metadata)
        self.assertEqual(candidates[0]["release_id"], "release-id")
        self.assertTrue(str(candidates[0]["download_url"]).startswith("https://coverartarchive.org/"))

    def test_sidecars_are_created_without_changing_audio(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            audio = Path(directory) / "song.flac"
            audio.write_bytes(b"audio stays untouched")
            before = audio.read_bytes()
            lyrics = enrichment.save_lyrics(audio, {"kind": "synced", "content": "[00:01.00]Line"})
            with patch.object(enrichment, "_request_bytes", return_value=(b"jpeg-data", "image/jpeg")):
                cover = enrichment.save_cover(audio, {"download_url": "https://coverartarchive.org/release/id/front-500"})
            self.assertEqual(lyrics.name, "song.lrc")
            self.assertEqual(cover.name, "cover.jpg")
            self.assertEqual(audio.read_bytes(), before)

    def test_existing_sidecar_is_never_overwritten(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            audio = Path(directory) / "song.mp3"
            audio.write_bytes(b"audio")
            existing = audio.with_suffix(".txt")
            existing.write_text("old", encoding="utf-8")
            with self.assertRaises(enrichment.EnrichmentError):
                enrichment.save_lyrics(audio, {"kind": "plain", "content": "new"})
            self.assertEqual(existing.read_text(encoding="utf-8"), "old")


if __name__ == "__main__":
    unittest.main()
