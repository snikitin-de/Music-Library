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
      --quarantine "D:\\Music\\Duplicates_To_Check" ^
      --report "reports\\duplicates.csv"
"""

from __future__ import annotations

import argparse
import csv
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from mutagen import File as MutagenFile


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
    size: int

    @property
    def duplicate_key(self) -> tuple[str, ...]:
        if self.album and self.track:
            return (
                normalize(self.albumartist or self.artist),
                normalize(self.album),
                normalize(self.track),
                normalize(self.title),
            )

        return (
            normalize(self.artist),
            normalize(self.title),
        )

    @property
    def filename_preference(self) -> int:
        copy_markers = ("копия", "copy", "duplicate", "дубликат")
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
            self.size,
            self.filename_preference,
        )

    @property
    def quality_text(self) -> str:
        return (
            f"format={self.fmt}; "
            f"bitrate={self.bitrate}; "
            f"bit_depth={self.bit_depth}; "
            f"sample_rate={self.sample_rate}; "
            f"tag_score={self.tag_score}; "
            f"cover={self.has_cover}; "
            f"size={self.size}"
        )


def normalize(value: str) -> str:
    value = value or ""
    value = value.lower().replace("ё", "е")
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"[\\/_|]+", " ", value)
    value = value.strip()
    return value


def first_tag(tags: dict, names: Iterable[str]) -> str:
    for name in names:
        value = tags.get(name)
        if value:
            if isinstance(value, list):
                return str(value[0])
            return str(value)
    return ""


def read_track(path: Path) -> TrackInfo | None:
    try:
        audio = MutagenFile(path, easy=True)
        audio_full = MutagenFile(path, easy=False)
    except Exception as exc:
        print(f"WARNING: skipped unreadable audio file: {path} ({exc})")
        return None

    if audio is None:
        return None

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

    fmt = path.suffix.lower().lstrip(".")
    size = path.stat().st_size

    tag_score = sum(bool(x) for x in [artist, albumartist, album, title, track])

    has_cover = False
    if audio_full is not None and audio_full.tags is not None:
        raw_tags = audio_full.tags
        tag_keys = [str(k).lower() for k in raw_tags.keys()]
        has_cover = any(
            key.startswith("apic")
            or key == "covr"
            or "metadata_block_picture" in key
            for key in tag_keys
        )

    if not title:
        return None

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
        size=size,
    )


def scan_library(library: Path) -> list[TrackInfo]:
    tracks: list[TrackInfo] = []

    for path in library.rglob("*"):
        if not path.is_file():
            continue

        if path.suffix.lower() not in AUDIO_EXTENSIONS:
            continue

        track = read_track(path)
        if track is not None:
            tracks.append(track)

    return tracks


def group_duplicates(tracks: list[TrackInfo]) -> dict[tuple[str, ...], list[TrackInfo]]:
    groups: dict[tuple[str, ...], list[TrackInfo]] = {}

    for track in tracks:
        key = track.duplicate_key
        if not all(key):
            continue
        groups.setdefault(key, []).append(track)

    return {key: items for key, items in groups.items() if len(items) > 1}


def safe_quarantine_path(original: Path, library: Path, quarantine: Path) -> Path:
    relative = original.relative_to(library)
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
    parser.add_argument("--dry-run", action="store_true", help="Do not move files")
    parser.add_argument("--only-file", help="Move only this duplicate file when it is found")
    args = parser.parse_args()

    library = Path(args.library).expanduser().resolve()
    quarantine = Path(args.quarantine).expanduser().resolve() if args.quarantine else None
    report = Path(args.report).expanduser().resolve()
    only_file = Path(args.only_file).expanduser().resolve() if args.only_file else None

    if not library.exists():
        raise SystemExit(f"Library folder does not exist: {library}")

    if not args.dry_run and quarantine is None:
        raise SystemExit("Use --quarantine or run with --dry-run")

    tracks = scan_library(library)
    duplicate_groups = group_duplicates(tracks)

    rows: list[dict[str, str]] = []

    print(f"Scanned tracks: {len(tracks)}")
    print(f"Duplicate groups: {len(duplicate_groups)}")

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

            reason = "lower quality score"
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
    print()
    print(f"Report written: {report}")

    if args.dry_run:
        print("Dry-run mode: no files were moved.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
