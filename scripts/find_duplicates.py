"""
Find duplicate music files and keep the best quality copy.

Safe by default:
- dry-run mode is supported;
- files are moved to quarantine, not deleted;
- CSV report is created.

Example:

    python scripts/find_duplicates.py --library "D:\\Music\\Sorted" --dry-run

    python scripts/find_duplicates.py ^
      --library "D:\\Music\\Sorted" ^
      --quarantine "D:\\Music\\Duplicates" ^
      --report "reports\\duplicates.csv"
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
import shutil
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from mutagen import File as MutagenFile
if __package__:
    from .scan_progress import ProgressWriter, progress_files
else:
    from scan_progress import ProgressWriter, progress_files


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


AUDIO_EXTENSIONS = {
    ".flac",
    ".alac",
    ".wav",
    ".aiff",
    ".aif",
    ".mp3",
    ".m4a",
    ".aac",
    ".ogg",
    ".opus",
    ".wma",
}
MANAGED_LIBRARY_FOLDER = "Library"
MANAGED_STORAGE_FOLDERS = {"duplicates", "trash"}

FORMAT_PRIORITY = {
    "flac": 100,
    "alac": 95,
    "wav": 90,
    "aiff": 88,
    "aif": 88,
    "m4a": 70,
    "aac": 68,
    "mp3": 60,
    "opus": 58,
    "ogg": 55,
    "wma": 40,
}


@dataclass
class ScanStats:
    audio_files: int = 0
    tagged_tracks: int = 0
    filename_fallback_tracks: int = 0
    skipped_tracks: int = 0
    filename_groups: int = 0
    hash_groups: int = 0
    hashed_files: int = 0
    review_groups: int = 0


@dataclass
class TrackInfo:
    path: Path
    artist: str
    albumartist: str
    album: str
    title: str
    track: str
    fmt: str
    bitrate: int
    sample_rate: int
    bit_depth: int
    tag_score: int
    has_cover: bool
    duration: int
    size: int
    metadata_source: str = "tags"

    @property
    def tag_duplicate_key(self) -> tuple[str, ...]:
        return strict_tag_duplicate_key(self)

    @property
    def filename_duplicate_key(self) -> tuple[str, ...]:
        return ("filename", normalize_filename_key(self.path.stem))

    @property
    def filename_preference(self) -> int:
        copy_markers = ("\u043a\u043e\u043f\u0438\u044f", "copy", "duplicate", "\u0434\u0443\u0431\u043b\u0438\u043a\u0430\u0442")
        name = normalize(self.path.stem)
        return 0 if any(marker in name for marker in copy_markers) else 1

    @property
    def quality_tuple(self) -> tuple[int, int, int, int, int, int, int, int]:
        return (
            FORMAT_PRIORITY.get(self.fmt.lower(), 0),
            self.bitrate,
            self.bit_depth,
            self.sample_rate,
            self.tag_score,
            int(self.has_cover),
            self.filename_preference,
            self.size,
        )

    @property
    def quality_text(self) -> str:
        return (
            f"format={self.fmt}; "
            f"bitrate={self.bitrate}; "
            f"bit_depth={self.bit_depth}; "
            f"sample_rate={self.sample_rate}; "
            f"duration={self.duration}; "
            f"tag_score={self.tag_score}; "
            f"cover={self.has_cover}; "
            f"size={self.size}"
        )


def normalize(value: str) -> str:
    value = value or ""
    value = value.lower().replace("\u0451", "\u0435")
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"[\\/_|]+", " ", value)
    value = value.strip()
    return value


def normalize_text_key(value: str) -> str:
    value = normalize(value)
    value = value.replace("\u00bd", "1 2").replace("\u00bc", "1 4").replace("\u00be", "3 4")
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"[^\w\s]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def normalize_track_number(value: str) -> str:
    value = normalize(value)
    if "/" in value:
        value = value.split("/", 1)[0]
    value = value.strip()
    return str(int(value)) if value.isdigit() else normalize_text_key(value)


def normalize_filename_key(value: str) -> str:
    value = normalize(value)
    copy_words = "copy|duplicate|\u043a\u043e\u043f\u0438\u044f|\u0434\u0443\u0431\u043b\u0438\u043a\u0430\u0442"
    value = re.sub(rf"\(({copy_words}|\d+)\)", " ", value)
    value = re.sub(rf"\[({copy_words}|\d+)\]", " ", value)
    value = re.sub(rf"\b({copy_words})\b", " ", value)
    value = re.sub(r"\(\s*\)|\[\s*\]", " ", value)
    return normalize_text_key(value).strip(" -_")


def normalize_artist_credit(value: str) -> str:
    value = normalize(value)
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"\b(feat|featuring|ft|with)\.?\b", ",", value)
    value = re.sub(r"\s+x\s+", ",", value)
    value = value.replace("&", ",").replace(";", ",").replace("/", ",")
    value = re.sub(r"\s+and\s+", ",", value)

    parts = []
    for part in value.split(","):
        part = normalize_text_key(part)
        if part:
            parts.append(part)

    return " + ".join(sorted(set(parts)))


def artist_title_key(track: TrackInfo) -> tuple[str, ...]:
    artist = normalize_artist_credit(track.artist or track.albumartist)
    title = normalize_text_key(track.title)
    if not artist or not title:
        return ()
    return ("artist_title", artist, title)


VERSION_MARKER_RE = re.compile(
    r"\b("
    r"live|remaster(?:ed)?|radio\s+edit|album\s+edit|single\s+version|"
    r"extended|club|mix|remix|acoustic|instrumental|karaoke|clean|explicit"
    r")\b",
    flags=re.IGNORECASE,
)


def has_version_marker(value: str) -> bool:
    return bool(VERSION_MARKER_RE.search(value or ""))


def artist_credit_parts(value: str) -> set[str]:
    normalized = normalize_artist_credit(value)
    return {part.strip() for part in normalized.split("+") if part.strip()}


def compatible_artist_credit(items: list[TrackInfo]) -> str:
    artist_sets = []
    for item in items:
        parts = artist_credit_parts(item.artist or item.albumartist)
        if not parts:
            return ""
        artist_sets.append(parts)

    shared = set.intersection(*artist_sets)
    if shared:
        return " + ".join(sorted(shared))

    first = artist_sets[0]
    if all(artist_set == first for artist_set in artist_sets[1:]):
        return " + ".join(sorted(first))

    return ""


def durations_are_compatible(items: list[TrackInfo], tolerance: int = 4) -> bool:
    durations = [item.duration for item in items if item.duration > 0]
    if len(durations) < 2:
        return True
    return max(durations) - min(durations) <= tolerance

def has_feature_credit_in_title(value: str) -> bool:
    return bool(re.search(r"[\[(]\s*(?:feat(?:uring)?|ft)\.?\s+", value or "", flags=re.IGNORECASE))


def title_without_feature_credit(value: str) -> str:
    value = re.sub(
        r"\s*[\[(]\s*(?:feat(?:uring)?|ft)\.?\s+.*?[\])]\s*",
        " ",
        value or "",
        flags=re.IGNORECASE,
    )
    return normalize_text_key(value)


def missing_track_artist_title_key(track: TrackInfo) -> tuple[str, ...]:
    if track.metadata_source != "tags":
        return ()
    artist = normalize_artist_credit(track.artist or track.albumartist)
    title = title_without_feature_credit(track.title)
    if not artist or not title:
        return ()
    return ("missing_track_artist_title", artist, title)


def cross_release_title_key(track: TrackInfo) -> tuple[str, ...]:
    if track.metadata_source != "tags":
        return ()
    if has_version_marker(track.title):
        return ()

    title = title_without_feature_credit(track.title)
    if not title:
        return ()

    return ("cross_release_title", title)


def strict_tag_duplicate_key(track: TrackInfo) -> tuple[str, ...]:
    if track.metadata_source != "tags":
        return ()

    title = normalize_text_key(track.title)
    if not title:
        return ()

    album = normalize_text_key(track.album)
    if album:
        albumartist = normalize_artist_credit(track.albumartist or track.artist)
        track_number = normalize_track_number(track.track)
        if not albumartist:
            return ()
        if not track_number:
            return ("album_title", albumartist, album, title)
        return ("album_track", albumartist, album, track_number, title)

    artist = normalize_artist_credit(track.artist or track.albumartist)
    if not artist:
        return ()
    return ("single", artist, title)


def first_tag(tags: dict, names: Iterable[str]) -> str:
    for name in names:
        value = tags.get(name)
        if value:
            if isinstance(value, list):
                return str(value[0])
            return str(value)
    return ""


def split_filename_title_artist(stem: str) -> tuple[str, str]:
    normalized = normalize_filename_key(stem)
    if " - " in stem:
        left, right = stem.rsplit(" - ", 1)
        return normalize_filename_key(right), normalize_filename_key(left)
    if " — " in stem:
        left, right = stem.rsplit(" — ", 1)
        return normalize_filename_key(right), normalize_filename_key(left)
    return "", normalized


def track_from_filename(path: Path, reason: str) -> TrackInfo | None:
    artist, title = split_filename_title_artist(path.stem)
    if not title:
        print(f"WARNING: skipped audio file without usable filename: {path}")
        return None

    try:
        size = path.stat().st_size
    except OSError as exc:
        print(f"WARNING: skipped inaccessible audio file: {path} ({exc})")
        return None

    if reason:
        print(f"WARNING: using filename fallback for audio file: {path} ({reason})")

    return TrackInfo(
        path=path,
        artist=artist,
        albumartist=artist,
        album="",
        title=title,
        track="",
        fmt=path.suffix.lower().lstrip("."),
        bitrate=0,
        sample_rate=0,
        bit_depth=0,
        tag_score=0,
        has_cover=False,
        duration=0,
        size=size,
        metadata_source="filename",
    )


def read_track(path: Path) -> TrackInfo | None:
    try:
        audio = MutagenFile(path, easy=True)
    except Exception as exc:
        return track_from_filename(path, str(exc))

    if audio is None:
        return track_from_filename(path, "mutagen returned no audio metadata")

    tags = audio.tags or {}

    artist = first_tag(tags, ["artist", "albumartist", "composer"])
    albumartist = first_tag(tags, ["albumartist", "artist"])
    album = first_tag(tags, ["album"])
    title = first_tag(tags, ["title"])
    track = first_tag(tags, ["tracknumber", "track"])

    if "/" in track:
        track = track.split("/", 1)[0]
    track = track.zfill(2) if track.isdigit() else track

    info = getattr(audio, "info", None)
    bitrate = int(getattr(info, "bitrate", 0) or 0)
    sample_rate = int(getattr(info, "sample_rate", 0) or 0)
    bit_depth = int(getattr(info, "bits_per_sample", 0) or 0)
    duration = int(round(float(getattr(info, "length", 0) or 0)))

    fmt = path.suffix.lower().lstrip(".")
    size = path.stat().st_size

    tag_score = sum(bool(x) for x in [artist, albumartist, album, title, track])

    try:
        audio_full = MutagenFile(path, easy=False)
    except Exception:
        audio_full = None

    has_cover = False
    if audio_full is not None:
        has_cover = bool(getattr(audio_full, "pictures", None))
        if not has_cover and audio_full.tags is not None:
            raw_tags = audio_full.tags
            tag_keys = [str(k).lower() for k in raw_tags.keys()]
            has_cover = any(
                key.startswith("apic")
                or key == "covr"
                or "metadata_block_picture" in key
                for key in tag_keys
            )

    if not title:
        return track_from_filename(path, "missing title tag")

    return TrackInfo(
        path=path,
        artist=artist,
        albumartist=albumartist,
        album=album,
        title=title,
        track=track,
        fmt=fmt,
        bitrate=bitrate,
        sample_rate=sample_rate,
        bit_depth=bit_depth,
        tag_score=tag_score,
        has_cover=has_cover,
        duration=duration,
        size=size,
    )


def scan_roots_for_library(library: Path) -> list[Path]:
    library_folder = library / MANAGED_LIBRARY_FOLDER
    if library_folder.exists() and library_folder.is_dir():
        return [library_folder]
    return [library]


def should_skip_managed_storage(path: Path, library: Path) -> bool:
    try:
        first_relative_part = path.relative_to(library).parts[0].casefold()
    except (ValueError, IndexError):
        return False
    return first_relative_part in MANAGED_STORAGE_FOLDERS


def managed_relative_path(path: Path, library: Path) -> Path:
    for scan_root in scan_roots_for_library(library):
        try:
            return path.relative_to(scan_root)
        except ValueError:
            continue
    return path.relative_to(library)


def scan_library(library: Path) -> list[TrackInfo]:
    tracks: list[TrackInfo] = []

    for scan_root in scan_roots_for_library(library):
        for path in scan_root.rglob("*"):
            if not path.is_file():
                continue

            if path.suffix.lower() not in AUDIO_EXTENSIONS:
                continue

            if should_skip_managed_storage(path, library):
                continue

            track = read_track(path)
            if track is not None:
                tracks.append(track)

    return tracks


def scan_library_with_stats(library: Path, progress=None) -> tuple[list[TrackInfo], ScanStats]:
    tracks: list[TrackInfo] = []
    stats = ScanStats()

    paths = (path for root in scan_roots_for_library(library) for path in root.rglob("*")
             if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS
             and not should_skip_managed_storage(path, library))
    for path in progress_files(paths, progress, "tags"):
        stats.audio_files += 1
        track = read_track(path)
        if track is None:
            stats.skipped_tracks += 1
            continue

        if track.metadata_source == "filename":
            stats.filename_fallback_tracks += 1
        else:
            stats.tagged_tracks += 1

        tracks.append(track)

    return tracks, stats


def duplicate_key(track: TrackInfo) -> tuple[str, ...]:
    tag_key = track.tag_duplicate_key
    if tag_key and all(tag_key):
        return ("tags",) + tag_key

    filename_key = track.filename_duplicate_key
    if track.metadata_source == "filename" and filename_key and all(filename_key):
        return filename_key

    return ()


def group_duplicates(tracks: list[TrackInfo], stats: ScanStats | None = None) -> dict[tuple[str, ...], list[TrackInfo]]:
    groups: dict[tuple[str, ...], list[TrackInfo]] = {}

    for track in tracks:
        key = duplicate_key(track)
        if not key or not all(key):
            if stats is not None:
                stats.skipped_tracks += 1
            continue
        groups.setdefault(key, []).append(track)

    fallback_groups: dict[tuple[str, ...], list[TrackInfo]] = {}
    for track in tracks:
        key = missing_track_artist_title_key(track)
        if key and all(key):
            fallback_groups.setdefault(key, []).append(track)

    for key, items in fallback_groups.items():
        if len(items) < 2 or not any(not normalize_track_number(item.track) for item in items):
            continue

        albums = {normalize_text_key(item.album) for item in items if normalize_text_key(item.album)}
        if len(albums) > 1 and not any(has_feature_credit_in_title(item.title) for item in items):
            continue

        item_paths = {item.path for item in items}
        if any({item.path for item in existing_items} == item_paths for existing_items in groups.values()):
            continue

        overlapping_keys = [
            existing_key
            for existing_key, existing_items in groups.items()
            if item_paths.intersection(existing_item.path for existing_item in existing_items)
        ]
        combined_items = {item.path: item for item in items}
        for existing_key in overlapping_keys:
            combined_items.update({item.path: item for item in groups.pop(existing_key)})
        groups[key] = list(combined_items.values())

    cross_release_groups: dict[tuple[str, ...], list[TrackInfo]] = {}
    for track in tracks:
        key = cross_release_title_key(track)
        if key and all(key):
            cross_release_groups.setdefault(key, []).append(track)

    for key, items in cross_release_groups.items():
        if len(items) < 2:
            continue
        if not durations_are_compatible(items):
            continue
        artist_key = compatible_artist_credit(items)
        if not artist_key:
            continue

        item_paths = {item.path for item in items}
        if any({item.path for item in existing_items} == item_paths for existing_items in groups.values()):
            continue

        overlapping_keys = [
            existing_key
            for existing_key, existing_items in groups.items()
            if item_paths.intersection(existing_item.path for existing_item in existing_items)
        ]
        combined_items = {item.path: item for item in items}
        for existing_key in overlapping_keys:
            combined_items.update({item.path: item for item in groups.pop(existing_key)})
        groups[("cross_release", artist_key, key[1])] = list(combined_items.values())

    duplicate_groups = {key: items for key, items in groups.items() if len(items) > 1}
    if stats is not None:
        stats.filename_groups = sum(1 for key in duplicate_groups if key and key[0] == "filename")
    return duplicate_groups


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def group_content_duplicates(
    tracks: list[TrackInfo],
    duplicate_groups: dict[tuple[str, ...], list[TrackInfo]],
    stats: ScanStats | None = None,
    progress=None,
) -> dict[tuple[str, ...], list[TrackInfo]]:
    exact_group_sets = {frozenset(item.path for item in items) for items in duplicate_groups.values()}
    by_size: dict[int, list[TrackInfo]] = {}
    for track in tracks:
        by_size.setdefault(track.size, []).append(track)

    groups: dict[tuple[str, ...], list[TrackInfo]] = {}
    total = sum(len(items) for size, items in by_size.items() if size > 0 and len(items) > 1)
    processed = 0
    if progress:
        progress({"stage": "hashes", "processed": 0, "total": total, "current": ""})
    for size, same_size_items in by_size.items():
        if size <= 0 or len(same_size_items) < 2:
            continue

        by_hash: dict[str, list[TrackInfo]] = {}
        for track in same_size_items:
            try:
                digest = file_sha256(track.path)
            except OSError as exc:
                print(f"WARNING: skipped hash for inaccessible audio file: {track.path} ({exc})")
                continue
            finally:
                processed += 1
                if progress:
                    progress({"stage": "hashes", "processed": processed, "total": total, "current": track.path.name})

            if stats is not None:
                stats.hashed_files += 1
            by_hash.setdefault(digest, []).append(track)

        for digest, hash_items in by_hash.items():
            if len(hash_items) < 2:
                continue

            group_set = frozenset(item.path for item in hash_items)
            if group_set in exact_group_sets:
                continue

            groups[("sha256", digest)] = hash_items

    if stats is not None:
        stats.hash_groups = len(groups)

    return groups


def merge_duplicate_groups(
    tag_groups: dict[tuple[str, ...], list[TrackInfo]],
    hash_groups: dict[tuple[str, ...], list[TrackInfo]],
) -> dict[tuple[str, ...], list[TrackInfo]]:
    merged = dict(tag_groups)
    merged.update(hash_groups)
    return merged


def group_review_candidates(
    tracks: list[TrackInfo],
    duplicate_groups: dict[tuple[str, ...], list[TrackInfo]],
    stats: ScanStats | None = None,
) -> dict[tuple[str, ...], list[TrackInfo]]:
    exact_group_sets = {frozenset(item.path for item in items) for items in duplicate_groups.values()}
    candidate_groups: dict[tuple[str, ...], list[TrackInfo]] = {}
    seen_group_sets: set[frozenset[Path]] = set()

    for key_builder in (artist_title_key, lambda track: track.filename_duplicate_key):
        groups: dict[tuple[str, ...], list[TrackInfo]] = {}
        for track in tracks:
            key = key_builder(track)
            if not key or not all(key):
                continue
            groups.setdefault(key, []).append(track)

        for key, items in groups.items():
            if len(items) < 2:
                continue

            group_set = frozenset(item.path for item in items)
            if group_set in exact_group_sets or group_set in seen_group_sets:
                continue

            seen_group_sets.add(group_set)
            candidate_groups[key] = items

    if stats is not None:
        stats.review_groups = len(candidate_groups)

    return candidate_groups


def review_reason(key: tuple[str, ...], items: list[TrackInfo]) -> str:
    albums = {normalize(item.album) for item in items if normalize(item.album)}
    tracks = {normalize(item.track) for item in items if normalize(item.track)}

    if key and key[0] == "artist_title":
        if len(albums) > 1 or len(tracks) > 1:
            return "needs_review: same artist/title, different album or track tags"
        return "needs_review: same artist/title, tag key is not identical"

    return "needs_review: same normalized filename, tags are not identical"


def write_review_report(report: Path, groups: dict[tuple[str, ...], list[TrackInfo]]) -> None:
    report.parent.mkdir(parents=True, exist_ok=True)

    with report.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "review_group",
                "file",
                "reason",
                "quality",
                "artist",
                "title",
                "album",
                "track",
            ],
        )
        writer.writeheader()

        for key, items in groups.items():
            group_name = " | ".join(key)
            reason = review_reason(key, items)
            for item in sorted(items, key=lambda track: track.quality_tuple, reverse=True):
                writer.writerow(
                    {
                        "review_group": group_name,
                        "file": str(item.path),
                        "reason": reason,
                        "quality": item.quality_text,
                        "artist": item.artist,
                        "title": item.title,
                        "album": item.album,
                        "track": item.track,
                    }
                )


def safe_quarantine_path(original: Path, library: Path, quarantine: Path) -> Path:
    relative = managed_relative_path(original, library)
    destination = quarantine / relative

    if not destination.exists():
        return destination

    stem = destination.stem
    suffix = destination.suffix
    parent = destination.parent

    index = 1
    while True:
        candidate = parent / f"{stem}__duplicate_{index}{suffix}"
        if not candidate.exists():
            return candidate
        index += 1


def write_report(report: Path, rows: list[dict[str, str]]) -> None:
    report.parent.mkdir(parents=True, exist_ok=True)

    with report.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "duplicate_group",
                "kept_file",
                "moved_file",
                "reason",
                "kept_quality",
                "moved_quality",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--library", required=True, help="Music library folder")
    parser.add_argument("--quarantine", help="Folder for worse duplicates")
    parser.add_argument("--report", default="reports/duplicates.csv", help="CSV report path")
    parser.add_argument("--review-report", help="CSV report for possible duplicates that need manual review")
    parser.add_argument("--dry-run", action="store_true", help="Do not move files")
    parser.add_argument("--only-file", help="Move only this duplicate file when it is found")
    parser.add_argument("--progress", action="store_true", help="Emit live scan counters")
    args = parser.parse_args()

    library = Path(args.library).expanduser().resolve()
    quarantine = Path(args.quarantine).expanduser().resolve() if args.quarantine else None
    report = Path(args.report).expanduser().resolve()
    review_report = (
        Path(args.review_report).expanduser().resolve()
        if args.review_report
        else report.with_name(f"{report.stem}_needs_review{report.suffix}")
    )
    only_file = Path(args.only_file).expanduser().resolve() if args.only_file else None

    if not library.exists():
        raise SystemExit(f"Library folder does not exist: {library}")

    if not args.dry_run and quarantine is None:
        raise SystemExit("Use --quarantine or run with --dry-run")

    progress = ProgressWriter() if args.progress else None
    tracks, stats = scan_library_with_stats(library, progress)
    tag_duplicate_groups = group_duplicates(tracks, stats)
    hash_duplicate_groups = group_content_duplicates(tracks, tag_duplicate_groups, stats, progress)
    duplicate_groups = merge_duplicate_groups(tag_duplicate_groups, hash_duplicate_groups)
    review_groups = group_review_candidates(tracks, duplicate_groups, stats)

    rows: list[dict[str, str]] = []

    print(f"Audio files found: {stats.audio_files}")
    print(f"Scanned tracks: {len(tracks)}")
    print(f"Tracks with readable tags: {stats.tagged_tracks}")
    print(f"Tracks using filename fallback: {stats.filename_fallback_tracks}")
    print(f"Skipped tracks: {stats.skipped_tracks}")
    print(f"Duplicate groups: {len(duplicate_groups)}")
    print(f"Duplicate groups by filename fallback: {stats.filename_groups}")
    print(f"Duplicate groups by exact file hash: {stats.hash_groups}")
    print(f"Files hashed for exact-copy check: {stats.hashed_files}")
    print(f"Needs-review candidate groups: {stats.review_groups}")

    for key, items in duplicate_groups.items():
        sorted_items = sorted(items, key=lambda item: item.quality_tuple, reverse=True)
        kept = sorted_items[0]
        duplicate_group = " | ".join(key)

        print()
        print(f"Duplicate group: {duplicate_group}")
        print(f"KEEP: {kept.path}")

        for duplicate in sorted_items[1:]:
            if only_file is not None and duplicate.path.resolve() != only_file:
                continue

            reason = "exact same file content" if key and key[0] == "sha256" else "lower quality score"
            print(f"MOVE: {duplicate.path} -> {quarantine if quarantine else '[dry-run quarantine]'}")

            rows.append(
                {
                    "duplicate_group": duplicate_group,
                    "kept_file": str(kept.path),
                    "moved_file": str(duplicate.path),
                    "reason": reason,
                    "kept_quality": kept.quality_text,
                    "moved_quality": duplicate.quality_text,
                }
            )

            if not args.dry_run and quarantine is not None:
                destination = safe_quarantine_path(duplicate.path, library, quarantine)
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(duplicate.path), str(destination))

    write_report(report, rows)
    write_review_report(review_report, review_groups)
    print()
    print(f"Report written: {report}")
    print(f"Needs-review report written: {review_report}")

    if args.dry_run:
        print("Dry-run mode: no files were moved.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
