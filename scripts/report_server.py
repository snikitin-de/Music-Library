"""
Serve the HTML report and handle safe quarantine actions.

The API only moves files that are already listed as duplicates in
reports/duplicates.csv. It never deletes files.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import mimetypes
import os
import unicodedata
import re
import shutil
import subprocess
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PureWindowsPath
from urllib.parse import parse_qs, urlparse

import yaml

from mutagen import File as MutagenFile

from generate_html_report import (
    DISPLAY_TAGS,
    ReportRow,
    build_payload,
    collect_genres_from_tracks,
    collect_years_from_tracks,
    first_tag,
    make_display_tag,
    render_html,
    year_from,
)


ROOT = Path(__file__).resolve().parents[1]
REPORT_HTML = ROOT / "reports" / "duplicates.html"
REPORT_CSV = ROOT / "reports" / "duplicates.csv"
BEETS_CONFIG = ROOT / "beets-config.yaml"
WEB_BEETS_CONFIG = ROOT / "reports" / "beets-web-config.yaml"

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

ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")

_REPORT_CACHE: dict[str, object] = {}
_AUDIO_PATH_CACHE: dict[tuple[tuple[tuple[int, int], tuple[int, int]], str], str | None] = {}


def norm_path(value: str) -> str:
    return str(PureWindowsPath(value)).replace("/", "\\").casefold()


def report_cache_key() -> tuple[tuple[int, int], tuple[int, int]]:
    def file_key(path: Path) -> tuple[int, int]:
        try:
            stat = path.stat()
            return (stat.st_mtime_ns, stat.st_size)
        except OSError:
            return (0, 0)

    return (file_key(REPORT_HTML), file_key(REPORT_CSV))


def report_metadata() -> dict[str, object]:
    key = report_cache_key()
    if _REPORT_CACHE.get("key") == key:
        return _REPORT_CACHE["metadata"]  # type: ignore[return-value]

    paths: list[str] = []
    roots: list[Path] = []

    for row in read_duplicate_rows():
        for item_key in ("kept_file", "moved_file"):
            value = row.get(item_key, "")
            if value:
                paths.append(value)

    try:
        payload = read_payload()
        library = payload.get("library", {}) if isinstance(payload, dict) else {}
        library_root = library.get("path", "")
        if library_root:
            roots.append(Path(library_root))
        for track in library.get("tracks", []):
            value = track.get("path", "")
            if value:
                paths.append(value)
    except Exception:
        pass

    unique_paths: list[str] = []
    seen_paths: set[str] = set()
    by_norm: dict[str, str] = {}
    by_name: dict[str, list[str]] = {}
    by_stem: dict[str, list[str]] = {}

    for value in paths:
        key_norm = norm_path(value)
        if not key_norm or key_norm in seen_paths:
            continue
        unique_paths.append(value)
        seen_paths.add(key_norm)
        by_norm[key_norm] = value

        name = PureWindowsPath(value).name or Path(value).name
        by_name.setdefault(name.casefold(), []).append(value)
        by_stem.setdefault(normalize_audio_name(PureWindowsPath(name).stem), []).append(value)

    unique_roots: list[Path] = []
    seen_roots: set[str] = set()
    for root in roots:
        root_key = norm_path(str(root))
        if root_key not in seen_roots:
            unique_roots.append(root)
            seen_roots.add(root_key)

    metadata: dict[str, object] = {
        "paths": unique_paths,
        "path_set": set(seen_paths),
        "by_norm": by_norm,
        "by_name": by_name,
        "by_stem": by_stem,
        "roots": unique_roots,
    }
    _REPORT_CACHE.clear()
    _REPORT_CACHE.update({"key": key, "metadata": metadata})
    return metadata


def read_payload() -> dict:
    text = REPORT_HTML.read_text(encoding="utf-8")
    match = re.search(
        r'<script id="payload" type="application/json">(.*?)</script>',
        text,
        re.S,
    )
    if not match:
        raise RuntimeError("Embedded report payload was not found")
    return json.loads(html.unescape(match.group(1)))


def library_path() -> str:
    payload = read_payload()
    library = payload.get("library", {}).get("path", "")
    if not library:
        raise RuntimeError("Report does not contain a library path")
    return library


def quarantine_path(library: str) -> str:
    return str(PureWindowsPath(library).parent / "Duplicates_To_Check")


def current_moved_files() -> set[str]:
    if not REPORT_CSV.exists():
        return set()
    with REPORT_CSV.open("r", encoding="utf-8-sig", newline="") as f:
        return {
            row.get("moved_file", "")
            for row in csv.DictReader(f)
            if row.get("moved_file")
        }


def read_duplicate_rows() -> list[dict[str, str]]:
    if not REPORT_CSV.exists():
        return []
    with REPORT_CSV.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_duplicate_rows(rows: list[dict[str, str]]) -> None:
    REPORT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with REPORT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
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


def safe_quarantine_path(original: Path, library: Path, quarantine: Path) -> Path:
    try:
        relative = original.relative_to(library)
    except ValueError:
        relative = Path(original.name)
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


def update_report_without_scan(remaining_rows: list[dict[str, str]], moved_paths: set[str]) -> None:
    payload = read_payload()
    library = payload.get("library", {})
    tracks = [
        track
        for track in library.get("tracks", [])
        if norm_path(track.get("path", "")) not in moved_paths
    ]
    library["tracks"] = tracks
    library["total_files"] = len(tracks)
    library["audio_files"] = sum(
        1
        for track in tracks
        if "статус: не читается" not in " ".join(
            f"{tag.get('label', '')}: {tag.get('value', '')}"
            for tag in track.get("tags", [])
            if isinstance(tag, dict)
        ).lower()
    )

    formats: dict[str, int] = {}
    for track in tracks:
        for tag in track.get("tags", []):
            if isinstance(tag, dict) and tag.get("kind") == "format":
                fmt = str(tag.get("value", "")).upper()
                if fmt:
                    formats[fmt] = formats.get(fmt, 0) + 1
                break
    library["formats"] = dict(sorted(formats.items()))

    report_rows = [
        ReportRow(
            duplicate_group=row.get("duplicate_group", ""),
            kept_file=row.get("kept_file", ""),
            moved_file=row.get("moved_file", ""),
            reason=row.get("reason", ""),
            kept_quality=row.get("kept_quality", ""),
            moved_quality=row.get("moved_quality", ""),
        )
        for row in remaining_rows
    ]
    new_payload = build_payload(report_rows, library)
    REPORT_HTML.write_text(render_html(new_payload), encoding="utf-8")


def move_from_csv(only_file: str | None = None) -> dict:
    library = Path(library_path())
    quarantine = Path(quarantine_path(str(library)))
    rows = read_duplicate_rows()
    wanted = norm_path(only_file) if only_file else None
    remaining = []
    moved = []

    for row in rows:
        moved_file = row.get("moved_file", "")
        if not moved_file:
            remaining.append(row)
            continue
        if wanted is not None and norm_path(moved_file) != wanted:
            remaining.append(row)
            continue

        source = Path(moved_file)
        if not source.exists():
            moved.append({"source": str(source), "status": "already_missing"})
            continue

        destination = safe_quarantine_path(source, library, quarantine)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(destination))
        moved.append({"source": str(source), "destination": str(destination), "status": "moved"})

    if wanted is not None and not moved:
        raise RuntimeError("Selected duplicate was not found in the current CSV report.")

    moved_paths = {norm_path(item["source"]) for item in moved}
    write_duplicate_rows(remaining)
    update_report_without_scan(remaining, moved_paths)
    return {
        "ok": True,
        "quarantine": str(quarantine),
        "moved": moved,
        "remaining_duplicates": len(remaining),
    }


def run_command(args: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            args,
            cwd=ROOT,
            env={
                **dict(os.environ),
                "NO_COLOR": "1",
                "PYTHONIOENCODING": "utf-8",
            },
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=300,
        )
    except OSError as exc:
        raise RuntimeError(str(exc)) from exc


def refresh_report(library: str) -> list[dict[str, object]]:
    commands = [
        [
            sys.executable,
            "scripts/find_duplicates.py",
            "--library",
            library,
            "--dry-run",
            "--report",
            str(REPORT_CSV),
        ],
        [
            sys.executable,
            "scripts/generate_html_report.py",
            "--csv",
            str(REPORT_CSV),
            "--library",
            library,
            "--out",
            str(REPORT_HTML),
        ],
    ]
    results = []
    for command in commands:
        result = run_command(command)
        results.append(
            {
                "command": " ".join(command),
                "returncode": result.returncode,
                "output": result.stdout,
            }
        )
        if result.returncode != 0:
            raise RuntimeError(result.stdout)
    return results


def refresh_html_report(library: str) -> dict[str, object]:
    result = run_command(
        [
            sys.executable,
            "scripts/generate_html_report.py",
            "--csv",
            str(REPORT_CSV),
            "--library",
            library,
            "--out",
            str(REPORT_HTML),
        ]
    )
    if result.returncode != 0:
        raise RuntimeError(result.stdout)
    _REPORT_CACHE.clear()
    _AUDIO_PATH_CACHE.clear()
    return {
        "command": " ".join(result.args),
        "returncode": result.returncode,
        "output": result.stdout,
    }


def track_payload_from_file(path: Path) -> dict:
    track_tags = [
        make_display_tag("формат", path.suffix.lower().lstrip(".").upper(), "format"),
    ]

    try:
        audio = MutagenFile(path, easy=True)
    except Exception:
        audio = None

    if audio is None:
        track_tags.append(make_display_tag("статус", "не распознан", "status"))
    else:
        tags = audio.tags or {}
        info = getattr(audio, "info", None)
        bitrate = int(getattr(info, "bitrate", 0) or 0)
        sample_rate = int(getattr(info, "sample_rate", 0) or 0)
        bit_depth = int(getattr(info, "bits_per_sample", 0) or 0)
        if bitrate > 0:
            track_tags.append(make_display_tag("битрейт", f"{round(bitrate / 1000)} kbps", "bitrate"))
        if bit_depth > 0:
            track_tags.append(make_display_tag("разрядность", f"{bit_depth} бит", "bit_depth"))
        if sample_rate > 0:
            track_tags.append(make_display_tag("частота дискретизации", f"{sample_rate / 1000:g} kHz", "sample_rate"))

        for tag_key, aliases, label, kind in DISPLAY_TAGS:
            value_text = first_tag(tags, aliases)
            if tag_key == "year":
                value_text = year_from(value_text)
            if value_text:
                track_tags.append(make_display_tag(label, value_text, kind))

    return {
        "name": path.name,
        "path": str(path),
        "folder": str(path.parent),
        "tags": track_tags,
    }


def refresh_report_tracks(files: list[str]) -> dict[str, object]:
    payload = read_payload()
    library = payload.get("library", {})
    tracks = list(library.get("tracks", []))
    selected = {norm_path(path) for path in files}
    replaced = 0
    refreshed_tracks: list[dict] = []

    for index, track in enumerate(tracks):
        if norm_path(track.get("path", "")) not in selected:
            continue
        source = resolve_audio_path(track.get("path", ""))
        if source is None:
            continue
        refreshed_track = track_payload_from_file(source)
        tracks[index] = refreshed_track
        refreshed_tracks.append(refreshed_track)
        replaced += 1

    library["tracks"] = tracks
    library["genres"] = collect_genres_from_tracks(tracks)
    library["years"] = collect_years_from_tracks(tracks)

    report_rows = [
        ReportRow(
            duplicate_group=row.get("duplicate_group", ""),
            kept_file=row.get("kept_file", ""),
            moved_file=row.get("moved_file", ""),
            reason=row.get("reason", ""),
            kept_quality=row.get("kept_quality", ""),
            moved_quality=row.get("moved_quality", ""),
        )
        for row in read_duplicate_rows()
    ]
    REPORT_HTML.write_text(render_html(build_payload(report_rows, library)), encoding="utf-8")
    _REPORT_CACHE.clear()
    _AUDIO_PATH_CACHE.clear()
    return {"updated_tracks": replaced, "tracks": refreshed_tracks}


def quarantine_duplicates(only_file: str | None = None) -> dict:
    return move_from_csv(only_file)


def require_quarantine_confirmation(body: dict) -> None:
    if body.get("confirm") != "MOVE_TO_QUARANTINE":
        raise RuntimeError("Quarantine action requires explicit confirmation.")


def report_music_path_set() -> set[str]:
    paths = set()
    try:
        payload = read_payload()
        library = payload.get("library", {}) if isinstance(payload, dict) else {}
        for track in library.get("tracks", []):
            value = track.get("path", "")
            if value:
                paths.add(norm_path(value))
    except Exception:
        pass
    return paths


def validate_music_files(files: object) -> list[str]:
    if not isinstance(files, list):
        raise RuntimeError("Files must be a list.")

    allowed = report_music_path_set()
    selected: list[str] = []
    seen: set[str] = set()

    for value in files:
        raw = str(value or "").strip()
        if not raw:
            continue
        key = norm_path(raw)
        if key in seen:
            continue
        if key not in allowed:
            raise RuntimeError(f"File is not listed in the current music report: {raw}")

        source = resolve_audio_path(raw)
        if source is None or not path_exists(source):
            raise RuntimeError(f"Audio file was not found: {raw}")
        if source.suffix.lower() not in AUDIO_EXTENSIONS:
            raise RuntimeError(f"Unsupported audio file type: {source}")
        if not source_inside_library(source):
            raise RuntimeError(f"File is outside the reported music library: {source}")

        selected.append(str(source))
        seen.add(key)

    if not selected:
        raise RuntimeError("No music files were selected.")
    return selected


def strip_ansi(value: str) -> str:
    return ANSI_RE.sub("", value or "")


def web_beets_config_path(action: str, mode: str) -> Path:
    if not BEETS_CONFIG.exists():
        raise RuntimeError(f"Beets config was not found: {BEETS_CONFIG}")

    with BEETS_CONFIG.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

    # Веб-операции должны работать с текущей библиотекой из отчёта,
    # а не с примерным путём из beets-config.yaml вроде D:\Music\Sorted.
    current_library = library_path()
    config["directory"] = current_library

    import_config = dict(config.get("import") or {})
    import_config.update(
        {
            "write": True,
            "timid": False,
            "resume": False,
            "incremental": False,
            "duplicate_action": "skip",
        }
    )

    if action == "layout" and mode == "real":
        # Именно разложить: переместить исходный файл в структуру paths.
        import_config.update({"copy": False, "move": True})
    else:
        # Для тегов и dry-run ничего физически не перемещаем.
        # tag + real пишет теги в текущий файл, но не раскладывает его.
        import_config.update({"copy": False, "move": False})

    config["import"] = import_config

    WEB_BEETS_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    with WEB_BEETS_CONFIG.open("w", encoding="utf-8") as f:
        yaml.safe_dump(config, f, allow_unicode=True, sort_keys=False)
    return WEB_BEETS_CONFIG


def build_beets_args(action: str, mode: str, files: list[str]) -> list[str]:
    if action not in {"tag", "layout"}:
        raise RuntimeError("Unknown music operation.")
    if mode not in {"dry-run", "real"}:
        raise RuntimeError("Choose dry-run or real processing mode.")
    args = [
        "beet",
        "-c",
        str(web_beets_config_path(action, mode)),
        "import",
        "--quiet",
        "--quiet-fallback=skip",
    ]
    if mode == "dry-run":
        args.append("--pretend")
    if action == "layout":
        args.append("--noautotag")
    args.extend(files)
    return args


def estimated_windows_command_length(args: list[str]) -> int:
    total = 0
    for arg in args:
        total += len(str(arg)) + 3
    return total


def chunk_beets_commands(action: str, mode: str, files: list[str]) -> list[list[str]]:
    # Keep well below Windows' command-line limit because paths can contain
    # spaces and subprocess quoting adds extra characters.
    max_command_length = 24000
    base = build_beets_args(action, mode, [])
    commands: list[list[str]] = []
    current: list[str] = []

    for file_path in files:
        candidate = base + current + [file_path]
        if current and estimated_windows_command_length(candidate) > max_command_length:
            commands.append(base + current)
            current = [file_path]
            continue

        if estimated_windows_command_length(candidate) > max_command_length:
            raise RuntimeError(f"File path is too long for beets command: {file_path}")
        current.append(file_path)

    if current:
        commands.append(base + current)
    return commands


def skipped_count_from_outputs(outputs: list[str]) -> int:
    skipped = 0
    for output in outputs:
        for match in re.finditer(r"Skipped\s+(\d+)\s+paths?", output, re.I):
            skipped += int(match.group(1))
    return skipped




INVALID_FILENAME_CHARS_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]+')


def safe_path_part(value: str, fallback: str) -> str:
    value = str(value or "").strip()
    value = INVALID_FILENAME_CHARS_RE.sub(" ", value)
    value = re.sub(r"\s+", " ", value).strip(" .")
    return value or fallback


def tag_value_for_layout(audio, names: list[str]) -> str:
    if not audio or not getattr(audio, "tags", None):
        return ""
    for name in names:
        value = first_tag(audio.tags, [name])
        if value:
            return str(value).strip()
    return ""


def track_number_for_layout(value: str) -> str:
    value = str(value or "").strip()
    match = re.search(r"\d+", value)
    if not match:
        return ""
    return match.group(0).zfill(2)


def year_for_layout(value: str) -> str:
    value = str(value or "").strip()
    match = re.search(r"\d{4}", value)
    return match.group(0) if match else ""


def unique_destination_path(destination: Path) -> Path:
    if not destination.exists():
        return destination

    stem = destination.stem
    suffix = destination.suffix
    parent = destination.parent

    for index in range(2, 10000):
        candidate = parent / f"{stem} ({index}){suffix}"
        if not candidate.exists():
            return candidate

    raise RuntimeError(f"Could not create a unique destination for: {destination}")


def manual_layout_file(source_raw: str) -> dict[str, str]:
    source = resolve_audio_path(source_raw)
    if source is None or not path_exists(source):
        raise RuntimeError(f"Audio file was not found: {source_raw}")

    if source.suffix.lower() not in AUDIO_EXTENSIONS:
        raise RuntimeError(f"Unsupported audio file type: {source}")

    if not source_inside_library(source):
        raise RuntimeError(f"File is outside the reported music library: {source}")

    audio = MutagenFile(source, easy=True)

    artist = tag_value_for_layout(audio, ["albumartist", "albumartistsort", "artist"])
    album = tag_value_for_layout(audio, ["album"])
    title = tag_value_for_layout(audio, ["title"])

    artist_part = safe_path_part(artist, "Unknown Artist")
    album_part = safe_path_part(album, "Unknown Album")
    title_part = safe_path_part(title, source.stem)

    folder = Path(library_path()) / artist_part / album_part
    file_name = safe_path_part(f"{title_part} - {artist_part}", source.stem) + source.suffix.lower()
    destination = unique_destination_path(folder / file_name)

    if norm_path(str(source)) == norm_path(str(destination)):
        return {
            "source": str(source),
            "destination": str(destination),
            "status": "already_in_place",
        }

    folder.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(destination))

    return {
        "source": str(source),
        "destination": str(destination),
        "status": "moved",
    }


def run_manual_layout(files: list[str], mode: str) -> dict[str, object]:
    planned: list[dict[str, str]] = []

    for file_path in files:
        source = resolve_audio_path(file_path)
        if source is None:
            raise RuntimeError(f"Audio file was not found: {file_path}")

        audio = MutagenFile(source, easy=True)
        artist = tag_value_for_layout(audio, ["albumartist", "albumartistsort", "artist"])
        album = tag_value_for_layout(audio, ["album"])
        title = tag_value_for_layout(audio, ["title"])

        artist_part = safe_path_part(artist, "Unknown Artist")
        album_part = safe_path_part(album, "Unknown Album")
        title_part = safe_path_part(title, source.stem)

        folder = Path(library_path()) / artist_part / album_part
        file_name = safe_path_part(f"{title_part} - {artist_part}", source.stem) + source.suffix.lower()
        destination = unique_destination_path(folder / file_name)

        planned.append({
            "source": str(source),
            "destination": str(destination),
            "status": "planned",
        })

    if mode == "dry-run":
        return {
            "ok": True,
            "moved": 0,
            "planned": len(planned),
            "items": planned,
        }

    moved: list[dict[str, str]] = []
    for file_path in files:
        moved.append(manual_layout_file(file_path))

    return {
        "ok": True,
        "moved": sum(1 for item in moved if item.get("status") == "moved"),
        "planned": len(moved),
        "items": moved,
    }




def apply_path_replacements_to_csv(replacements: dict[str, str]) -> int:
    if not replacements or not REPORT_CSV.exists():
        return 0

    normalized = {norm_path(source): destination for source, destination in replacements.items()}
    rows = read_duplicate_rows()
    changed = 0

    for row in rows:
        for key in ("kept_file", "moved_file"):
            value = row.get(key, "")
            replacement = normalized.get(norm_path(value))
            if replacement:
                row[key] = replacement
                changed += 1

    if changed:
        write_duplicate_rows(rows)

    return changed


def apply_path_replacements_to_payload(replacements: dict[str, str]) -> dict[str, object]:
    payload = read_payload()
    library = payload.get("library", {})
    tracks = list(library.get("tracks", []))
    normalized = {norm_path(source): destination for source, destination in replacements.items()}

    updated_tracks = 0
    changed_tracks: list[dict] = []

    for index, track in enumerate(tracks):
        old_path = str(track.get("path", ""))
        new_path = normalized.get(norm_path(old_path))

        if not new_path:
            continue

        source = resolve_audio_path(new_path)
        if source is not None and path_exists(source):
            tracks[index] = track_payload_from_file(source)
        else:
            track["path"] = new_path
            track["folder"] = str(Path(new_path).parent)
            track["name"] = Path(new_path).name
            tracks[index] = track

        changed_tracks.append(tracks[index])
        updated_tracks += 1

    library["tracks"] = tracks
    library["genres"] = collect_genres_from_tracks(tracks)
    library["years"] = collect_years_from_tracks(tracks)

    return {
        "payload": payload,
        "updated_tracks": updated_tracks,
        "tracks": changed_tracks,
    }


def rebuild_report_html_from_current_data(library: dict) -> None:
    report_rows = [
        ReportRow(
            duplicate_group=row.get("duplicate_group", ""),
            kept_file=row.get("kept_file", ""),
            moved_file=row.get("moved_file", ""),
            reason=row.get("reason", ""),
            kept_quality=row.get("kept_quality", ""),
            moved_quality=row.get("moved_quality", ""),
        )
        for row in read_duplicate_rows()
    ]

    REPORT_HTML.write_text(render_html(build_payload(report_rows, library)), encoding="utf-8")
    _REPORT_CACHE.clear()
    _AUDIO_PATH_CACHE.clear()


def update_report_after_layout(layout_items: list[dict[str, str]]) -> dict[str, object]:
    replacements = {
        item["source"]: item["destination"]
        for item in layout_items
        if item.get("status") == "moved"
        and item.get("source")
        and item.get("destination")
    }

    if not replacements:
        return {
            "updated_tracks": 0,
            "updated_csv_paths": 0,
            "replacements": 0,
            "tracks": [],
        }

    csv_changed = apply_path_replacements_to_csv(replacements)
    payload_result = apply_path_replacements_to_payload(replacements)
    payload = payload_result["payload"]
    library = payload.get("library", {})

    rebuild_report_html_from_current_data(library)

    return {
        "updated_tracks": payload_result["updated_tracks"],
        "updated_csv_paths": csv_changed,
        "replacements": len(replacements),
        "tracks": payload_result.get("tracks", []),
    }


def run_music_operation(body: dict) -> dict:
    action = str(body.get("action", ""))
    mode = str(body.get("mode", "dry-run"))
    scope = str(body.get("scope", "filtered"))

    if action not in {"tag", "layout"}:
        raise RuntimeError("Unknown music operation.")
    if mode not in {"dry-run", "real"}:
        raise RuntimeError("Choose dry-run or real processing mode.")
    if scope not in {"single", "filtered"}:
        raise RuntimeError("Unknown music operation scope.")

    files = validate_music_files(body.get("files", []))

    if scope == "single" and len(files) != 1:
        raise RuntimeError("Single-record operation must contain exactly one file.")

    scope_name = "одной записи" if scope == "single" else "отфильтрованного списка"
    mode_name = "dry run" if mode == "dry-run" else "реальная обработка"

    if action == "layout":
        layout_result = run_manual_layout(files, mode)

        if mode == "real":
            refresh_result = update_report_after_layout(layout_result["items"])
        else:
            refresh_result = None

        if mode == "dry-run":
            sample = layout_result["items"][:3]
            sample_text = "; ".join(f'{item["source"]} -> {item["destination"]}' for item in sample)
            message = f"Раскладка: dry run для {scope_name}. Файлов: {len(files)}. Будет перемещено: {layout_result['planned']}."
            if sample_text:
                message += f" Пример: {sample_text}"
        else:
            message = f"Раскладка: реальная обработка для {scope_name}. Перемещено файлов: {layout_result['moved']} из {len(files)}."
            if refresh_result:
                message += f" Отчёт обновлён: путей в списке музыки — {refresh_result.get('updated_tracks', 0)}, путей в CSV дублей — {refresh_result.get('updated_csv_paths', 0)}."

        return {
            "ok": True,
            "reload": mode == "real",
            "message": message,
            "commands": 0,
            "skipped": 0,
            "output": "",
            "layout": layout_result,
            "refresh": refresh_result,
            "track": (refresh_result or {}).get("tracks", [None])[0] if scope == "single" and refresh_result else None,
        }

    commands = chunk_beets_commands(action, mode, files)
    outputs = []
    for index, command in enumerate(commands, start=1):
        result = run_command(command)
        output = strip_ansi(result.stdout)
        outputs.append(output)
        if result.returncode != 0:
            raise RuntimeError(
                f"beet command failed in batch {index}/{len(commands)}:\n"
                f"{output or 'no output'}"
            )

    refresh_result = None
    if mode == "real":
        refresh_result = refresh_report_tracks(files)

    action_name = "Проставление тегов"
    skipped = skipped_count_from_outputs(outputs)
    message = f"{action_name}: {mode_name} завершена для {scope_name}. Файлов: {len(files)}. Пакетов: {len(commands)}."
    if skipped:
        message += f" Пропущено: {skipped}."

    return {
        "ok": True,
        "reload": mode == "real",
        "message": message,
        "commands": len(commands),
        "skipped": skipped,
        "output": "\n".join(outputs)[-4000:],
        "refresh": refresh_result,
        "track": (refresh_result or {}).get("tracks", [None])[0] if scope == "single" and refresh_result else None,
    }


def normalize_audio_name(value: str) -> str:
    value = unicodedata.normalize("NFKC", value or "")
    value = value.lower().replace("ё", "е")
    value = re.sub(r"\b(feat|ft|featuring)\.?\b", " ", value)
    value = value.replace("&", " and ")
    value = re.sub(r"[^a-zа-я0-9]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def path_exists(path: Path) -> bool:
    try:
        return path.exists() and path.is_file()
    except OSError:
        return False


def report_audio_paths() -> list[str]:
    metadata = report_metadata()
    return list(metadata["paths"])  # type: ignore[arg-type]


def library_roots_from_report() -> list[Path]:
    metadata = report_metadata()
    return list(metadata["roots"])  # type: ignore[arg-type]


def candidates_for_audio_path(requested: str) -> list[Path]:
    requested = (requested or "").strip().strip('"')
    candidates: list[Path] = []

    if not requested:
        return candidates

    raw = requested.replace("/", "\\")
    requested_name = PureWindowsPath(raw).name or Path(requested).name
    requested_stem_norm = normalize_audio_name(PureWindowsPath(requested_name).stem)
    metadata = report_metadata()
    by_norm = metadata["by_norm"]  # type: ignore[assignment]
    by_name = metadata["by_name"]  # type: ignore[assignment]
    by_stem = metadata["by_stem"]  # type: ignore[assignment]

    # 1. Exact candidates.
    candidates.append(Path(requested))
    candidates.append(Path(raw))
    candidates.append(Path(str(PureWindowsPath(raw))))

    # 2. Paths already embedded in report / CSV.
    exact = by_norm.get(norm_path(requested)) or by_norm.get(norm_path(raw))
    if exact:
        candidates.append(Path(exact))

    for value in by_name.get(requested_name.casefold(), []):
        candidates.append(Path(value))

    for value in by_stem.get(requested_stem_norm, []):
        candidates.append(Path(value))

    unique: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        key = str(path).casefold()
        if key not in seen:
            unique.append(path)
            seen.add(key)

    return unique


def search_audio_in_libraries(requested: str) -> Path | None:
    raw = (requested or "").strip().strip('"').replace("/", "\\")
    requested_name = PureWindowsPath(raw).name or Path(requested).name
    requested_stem_norm = normalize_audio_name(PureWindowsPath(requested_name).stem)

    for root in library_roots_from_report():
        try:
            if not root.exists():
                continue

            for path in root.rglob("*"):
                if not path.is_file() or path.suffix.lower() not in AUDIO_EXTENSIONS:
                    continue

                if (
                    path.name.casefold() == requested_name.casefold()
                    or normalize_audio_name(path.stem) == requested_stem_norm
                ):
                    return path
        except Exception:
            continue
    return None


def quarantine_candidate_for_audio_path(requested: str) -> Path | None:
    raw = (requested or "").strip().strip('"').replace("/", "\\")
    requested_path = Path(raw)

    for root in library_roots_from_report():
        try:
            relative = requested_path.relative_to(root)
        except ValueError:
            continue

        candidate = Path(quarantine_path(str(root))) / relative
        if path_exists(candidate):
            return candidate

    return None


def resolve_audio_path(requested: str) -> Path | None:
    cache_key = (report_cache_key(), norm_path(requested))
    if cache_key in _AUDIO_PATH_CACHE:
        cached = _AUDIO_PATH_CACHE[cache_key]
        return Path(cached) if cached else None

    resolved: Path | None = None
    for candidate in candidates_for_audio_path(requested):
        if path_exists(candidate):
            resolved = candidate
            break

    if resolved is None:
        resolved = quarantine_candidate_for_audio_path(requested)

    if resolved is None:
        resolved = search_audio_in_libraries(requested)

    _AUDIO_PATH_CACHE[cache_key] = str(resolved) if resolved else None
    return resolved


def source_inside_library(source: Path) -> bool:
    source_key = norm_path(str(source))
    for root in library_roots_from_report():
        root_key = norm_path(str(root)).rstrip("\\")
        if source_key == root_key or source_key.startswith(root_key + "\\"):
            return True

        quarantine_key = norm_path(quarantine_path(str(root))).rstrip("\\")
        if source_key == quarantine_key or source_key.startswith(quarantine_key + "\\"):
            return True
    return False


def client_closed_connection(exc: OSError) -> bool:
    return isinstance(exc, (BrokenPipeError, ConnectionAbortedError, ConnectionResetError))


def send_audio_file(handler: SimpleHTTPRequestHandler, head_only: bool = False) -> None:
    parsed = urlparse(handler.path)
    params = parse_qs(parsed.query)
    requested = params.get("file", [""])[0]

    if not requested:
        handler.send_error(400, "Missing file")
        return

    source = resolve_audio_path(requested)

    if source is None:
        checked = " | ".join(str(path) for path in candidates_for_audio_path(requested)[:40])
        handler.send_error(404, f"Audio file not found. Requested: {requested}. Checked: {checked}")
        return

    # Allow exact files from report, or resolved files that are inside the report library.
    metadata = report_metadata()
    allowed_exact = norm_path(requested) in metadata["path_set"]  # type: ignore[operator]
    if not allowed_exact and not source_inside_library(source):
        handler.send_error(403, "File is not listed in the current report or library")
        return

    if source.suffix.lower() not in AUDIO_EXTENSIONS:
        handler.send_error(415, "Unsupported audio file type")
        return

    file_size = source.stat().st_size
    content_type = mimetypes.guess_type(str(source))[0] or "application/octet-stream"
    range_header = handler.headers.get("Range")

    if range_header:
        match = re.match(r"bytes=(\d+)-(\d*)", range_header)
        if not match:
            handler.send_error(416, "Invalid range")
            return

        start = int(match.group(1))
        end = int(match.group(2)) if match.group(2) else file_size - 1
        end = min(end, file_size - 1)

        if start >= file_size or start > end:
            handler.send_error(416, "Range not satisfiable")
            return

        length = end - start + 1
        handler.send_response(206)
        handler.send_header("Content-Type", content_type)
        handler.send_header("Accept-Ranges", "bytes")
        handler.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
        handler.send_header("Content-Length", str(length))
        handler.end_headers()
        if head_only:
            return

        try:
            with source.open("rb") as f:
                f.seek(start)
                remaining = length
                while remaining > 0:
                    chunk = f.read(min(1024 * 1024, remaining))
                    if not chunk:
                        break
                    handler.wfile.write(chunk)
                    remaining -= len(chunk)
        except OSError as exc:
            if not client_closed_connection(exc):
                raise
        return

    handler.send_response(200)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Accept-Ranges", "bytes")
    handler.send_header("Content-Length", str(file_size))
    handler.end_headers()
    if head_only:
        return

    try:
        with source.open("rb") as f:
            shutil.copyfileobj(f, handler.wfile)
    except OSError as exc:
        if not client_closed_connection(exc):
            raise


class ReportHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_GET(self) -> None:
        if self.path.startswith("/api/audio"):
            send_audio_file(self)
            return

        if self.path in {"/", ""}:
            self.send_response(302)
            self.send_header("Location", "/reports/duplicates.html")
            self.end_headers()
            return

        super().do_GET()

    def do_HEAD(self) -> None:
        if self.path.startswith("/api/audio"):
            send_audio_file(self, head_only=True)
            return

        super().do_HEAD()

    def do_POST(self) -> None:
        try:
            if self.path == "/api/quarantine-all":
                require_quarantine_confirmation(self.read_json())
                self.send_json(200, quarantine_duplicates())
                return

            if self.path == "/api/quarantine-one":
                body = self.read_json()
                require_quarantine_confirmation(body)
                moved_file = str(body.get("moved_file", ""))
                allowed = {norm_path(path) for path in current_moved_files()}
                if not moved_file or norm_path(moved_file) not in allowed:
                    self.send_json(
                        400,
                        {
                            "ok": False,
                            "error": "File is not listed as a movable duplicate in the current CSV report.",
                        },
                    )
                    return
                self.send_json(200, quarantine_duplicates(moved_file))
                return

            if self.path == "/api/music-operation":
                self.send_json(200, run_music_operation(self.read_json()))
                return

            self.send_json(404, {"ok": False, "error": "Unknown API endpoint"})
        except RuntimeError as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        except Exception as exc:
            self.send_json(500, {"ok": False, "error": str(exc)})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--open", action="store_true", help="Open report in browser")
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), ReportHandler)
    url = f"http://{args.host}:{args.port}/reports/duplicates.html"
    print(f"Report server: {url}")
    if args.open:
        import webbrowser
        webbrowser.open(url)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
