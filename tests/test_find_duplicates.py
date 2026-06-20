import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.find_duplicates import (  # noqa: E402
    TrackInfo,
    group_duplicates,
    group_review_candidates,
    normalize_artist_credit,
    normalize_text_key,
)


def track(
    name: str,
    *,
    artist: str = "Artist",
    albumartist: str = "Artist",
    album: str = "Album",
    title: str = "Title",
    track_number: str = "1",
    metadata_source: str = "tags",
) -> TrackInfo:
    return TrackInfo(
        path=Path(name),
        artist=artist,
        albumartist=albumartist,
        album=album,
        title=title,
        track=track_number,
        fmt="flac",
        bitrate=1000,
        sample_rate=44100,
        bit_depth=16,
        tag_score=5,
        has_cover=True,
        size=100,
        metadata_source=metadata_source,
    )


class DuplicateDetectionTests(unittest.TestCase):
    def test_album_tracks_need_same_album_and_track_for_auto_duplicate(self) -> None:
        items = [
            track("first.flac", album="Album", title="Song", track_number="1"),
            track("second.flac", album="Other Album", title="Song", track_number="1"),
        ]

        self.assertEqual(group_duplicates(items), {})
        self.assertEqual(len(group_review_candidates(items, {})), 1)

    def test_same_album_track_is_auto_duplicate(self) -> None:
        items = [
            track("first.flac", album="Album", title="Song", track_number="01"),
            track("second.flac", album="Album", title="Song", track_number="1"),
        ]

        groups = group_duplicates(items)

        self.assertEqual(len(groups), 1)
        self.assertIn(("tags", "album_track", "artist", "album", "1", "song"), groups)

    def test_tagged_files_do_not_auto_duplicate_by_filename(self) -> None:
        items = [
            track("Song.flac", album="Album", title="Song", track_number="1"),
            track("Song (2).flac", album="Other Album", title="Different Song", track_number="2"),
        ]

        self.assertEqual(group_duplicates(items), {})

    def test_filename_fallback_can_duplicate_when_tags_are_unusable(self) -> None:
        items = [
            track("Song.flac", title="Song", metadata_source="filename", album="", track_number=""),
            track("Song (2).flac", title="Song", metadata_source="filename", album="", track_number=""),
        ]

        groups = group_duplicates(items)

        self.assertEqual(len(groups), 1)
        self.assertIn(("filename", "song"), groups)

    def test_title_normalization_handles_accents_and_fraction_glyphs(self) -> None:
        self.assertEqual(normalize_text_key("\u00c0 demi pardonn\u00e9e"), "a demi pardonnee")
        self.assertEqual(normalize_text_key("\u00bd Lovesong"), "1 2 lovesong")

    def test_artist_normalization_handles_common_collaboration_separators(self) -> None:
        self.assertEqual(
            normalize_artist_credit("R3HAB x A Touch Of Class"),
            normalize_artist_credit("R3HAB, A Touch Of Class"),
        )
        self.assertEqual(
            normalize_artist_credit("DJ Snake with Lauv"),
            normalize_artist_credit("DJ Snake, LAUV"),
        )


if __name__ == "__main__":
    unittest.main()
