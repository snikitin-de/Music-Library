"""
Generate a standalone HTML report from duplicate CSV report
and optional full music library analysis.
"""

from __future__ import annotations

import argparse
import base64
import csv
import html
import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from urllib.parse import quote

from mutagen import File as MutagenFile
from mutagen.flac import Picture
from mutagen.mp4 import MP4Cover

from report_styles import REPORT_CSS
from report_assets import ICON_LICENSE_NOTICE, FONT_LICENSE_NOTICE
from report_controls import REPORT_CONTROLS_JS
from report_source import SOURCE_DIALOG_HTML, SOURCE_DIALOG_JS
from report_pagination import REPORT_PAGINATION_JS
from report_lyrics import REPORT_LYRICS_JS
from report_player import REPORT_PLAYER_JS
from report_duplicates import REPORT_DUPLICATES_JS
from genre_rules import normalized_genres, normalize_genre_counts
from scan_progress import ProgressWriter, progress_files
from find_duplicates import FORMAT_PRIORITY
from report_charts import PLOTLY_JS, PLOTLY_LICENSE, REPORT_CHARTS_JS, plotly_chart, horizontal_bars


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

MAX_DISPLAY_TAG_LENGTH = 120
LYRICS_FILE_EXTENSIONS = (".lrc", ".txt")
COVER_FILE_NAMES = ("cover.jpg", "cover.jpeg", "cover.png", "folder.jpg", "folder.jpeg", "folder.png")
FAVICON_VERSION = "library-green-3"

# Ready-made SVG paths from Lucide 1.28.0 (ISC):
# https://cdn.jsdelivr.net/npm/lucide-static@1.28.0/icons/
LUCIDE_ICON_NODES = {
    "chevron-down": '<path d="m6 9 6 6 6-6"/>',
    "chevron-left": '<path d="m15 18-6-6 6-6"/>',
    "chevron-right": '<path d="m9 18 6-6-6-6"/>',
    "clock": '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
    "pause": '<path d="M6 4h4v16H6zM14 4h4v16h-4z"/>',
    "search": '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
    "audio-lines": '<path d="M2 10v3"/><path d="M6 6v11"/><path d="M10 3v18"/><path d="M14 8v7"/><path d="M18 5v13"/><path d="M22 10v3"/>',
    "house": '<path d="M15 21v-8a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v8"/><path d="M3 10a2 2 0 0 1 .709-1.528l7-6a2 2 0 0 1 2.582 0l7 6A2 2 0 0 1 21 10v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
    "chart": '<path d="M5 21v-6"/><path d="M12 21V9"/><path d="M19 21V3"/>',
    "music": '<circle cx="8" cy="18" r="4"/><path d="M12 18V2l7 4"/>',
    "copy": '<rect width="14" height="14" x="8" y="8" rx="2" ry="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/>',
    "files": '<path d="M15 2h-4a2 2 0 0 0-2 2v11a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V8"/><path d="M16.706 2.706A2.4 2.4 0 0 0 15 2v5a1 1 0 0 0 1 1h5a2.4 2.4 0 0 0-.706-1.706z"/><path d="M5 7a2 2 0 0 0-2 2v11a2 2 0 0 0 2 2h8a2 2 0 0 0 1.732-1"/>',
    "disc": '<circle cx="12" cy="12" r="10"/><path d="M6 12c0-1.7.7-3.2 1.8-4.2"/><circle cx="12" cy="12" r="2"/><path d="M18 12c0 1.7-.7 3.2-1.8 4.2"/>',
    "users": '<path d="M18 21a8 8 0 0 0-16 0"/><circle cx="10" cy="8" r="5"/><path d="M22 20c0-3.37-2-6.5-4-8a5 5 0 0 0-.45-8.3"/>',
    "image": '<rect width="18" height="18" x="3" y="3" rx="2" ry="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21"/>',
    "image-off": '<line x1="2" x2="22" y1="2" y2="22"/><path d="M10.41 10.41a2 2 0 1 1-2.83-2.83"/><line x1="13.5" x2="6" y1="13.5" y2="21"/><line x1="18" x2="21" y1="12" y2="15"/><path d="M3.59 3.59A1.99 1.99 0 0 0 3 5v14a2 2 0 0 0 2 2h14c.55 0 1.052-.22 1.41-.59"/><path d="M21 15V5a2 2 0 0 0-2-2H9"/>',
    "file-text": '<path d="M6 22a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.704.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2z"/><path d="M14 2v5a1 1 0 0 0 1 1h5"/><path d="M10 9H8"/><path d="M16 13H8"/><path d="M16 17H8"/>',
    "copy-check": '<path d="m12 15 2 2 4-4"/><rect width="14" height="14" x="8" y="8" rx="2" ry="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/>',
    "circle-alert": '<circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="8" y2="12"/><line x1="12" x2="12.01" y1="16" y2="16"/>',
    "triangle-alert": '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
    "trash": '<path d="M10 11v6"/><path d="M14 11v6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/><path d="M3 6h18"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>',
    "play": '<path d="M5 5a2 2 0 0 1 3.008-1.728l11.997 6.998a2 2 0 0 1 .003 3.458l-12 7A2 2 0 0 1 5 19z"/>',
    "x": '<path d="m18 6-12 12M6 6l12 12"/>',
    "volume": '<path d="M11 4.702a.705.705 0 0 0-1.203-.498L6.413 7.587A1.4 1.4 0 0 1 5.416 8H3a1 1 0 0 0-1 1v6a1 1 0 0 0 1 1h2.416a1.4 1.4 0 0 1 .997.413l3.383 3.384A.705.705 0 0 0 11 19.298z"/><path d="M16 9a5 5 0 0 1 0 6"/>',
    "volume-x": '<path d="M11 4.702a.705.705 0 0 0-1.203-.498L6.413 7.587A1.4 1.4 0 0 1 5.416 8H3a1 1 0 0 0-1 1v6a1 1 0 0 0 1 1h2.416a1.4 1.4 0 0 1 .997.413l3.383 3.384A.705.705 0 0 0 11 19.298z"/><line x1="22" x2="16" y1="9" y2="15"/><line x1="16" x2="22" y1="9" y2="15"/>',
}


def lucide_icon(name: str, class_name: str = "app-icon") -> str:
    return (
        f'<svg class="{html.escape(class_name)}" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        f'stroke-linejoin="round" aria-hidden="true">{LUCIDE_ICON_NODES[name]}</svg>'
    )


FAVICON_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
    'stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    '<rect width="24" height="24" rx="12" fill="#28b969" stroke="none"/>'
    f'{LUCIDE_ICON_NODES["audio-lines"]}</svg>'
)
FAVICON_DATA_URI = "data:image/svg+xml," + quote(FAVICON_SVG, safe="")

DISPLAY_TAGS = [
    ("album", ["album"], "альбом", "album"),
    ("albumartist", ["albumartist"], "исполнитель альбома", "albumartist"),
    ("artist", ["artist"], "исполнитель", "artist"),
    ("genre", ["genre"], "жанр", "genre"),
    ("title", ["title"], "название", "title"),
    ("year", ["year", "date"], "год", "year"),
]


HEATMAP_ERAS = [
    ("80-е", 1980, 1989),
    ("90-е", 1990, 1999),
    ("00-е", 2000, 2009),
    ("10-е", 2010, 2019),
    ("20-е", 2020, 2029),
    ("Без года", None, None),
]

EXCLUDED_TOP_ARTISTS = {"various artists", "varios artists"}


@dataclass
class ReportRow:
    duplicate_group: str
    kept_file: str
    moved_file: str
    reason: str
    kept_quality: str
    moved_quality: str


def normalize(value: str) -> str:
    value = value or ""
    value = value.lower().replace("ё", "е")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def is_excluded_top_artist(value: str) -> bool:
    return normalize(value) in EXCLUDED_TOP_ARTISTS


def first_tag(tags: dict, names: list[str]) -> str:
    for name in names:
        value = tags.get(name)
        if value:
            if isinstance(value, list):
                return str(value[0])
            return str(value)
    return ""


def clean_tag_value(value: str) -> str:
    value = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(value) > MAX_DISPLAY_TAG_LENGTH:
        value = value[: MAX_DISPLAY_TAG_LENGTH - 1].rstrip() + "…"
    return value


def make_display_tag(label: str, value: str, kind: str) -> dict[str, str]:
    return {"label": label, "value": clean_tag_value(value), "kind": kind}


def image_data_uri(data: bytes, mime: str | None) -> str:
    if not data:
        return ""
    safe_mime = mime if mime and mime.startswith("image/") else "image/jpeg"
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:{safe_mime};base64,{encoded}"


def embedded_cover_bytes(path: Path) -> tuple[bool, bytes, str]:
    try:
        audio = MutagenFile(path, easy=False)
    except Exception:
        return False, b"", ""

    if audio is None:
        return sidecar_cover_bytes(path)

    for picture in getattr(audio, "pictures", []) or []:
        data = getattr(picture, "data", b"")
        mime = getattr(picture, "mime", "image/jpeg")
        if data:
            return True, data, mime

    tags = audio.tags
    if tags is None:
        return sidecar_cover_bytes(path)

    has_cover = False
    for key, value in tags.items():
        key_text = str(key).lower()
        values = value if isinstance(value, list) else [value]

        if key_text.startswith("apic"):
            has_cover = True
            for item in values:
                data = getattr(item, "data", b"")
                mime = getattr(item, "mime", "image/jpeg")
                if data:
                    return True, data, mime

        if key_text == "covr":
            has_cover = True
            for item in values:
                image_format = getattr(item, "imageformat", None)
                mime = "image/png" if image_format == MP4Cover.FORMAT_PNG else "image/jpeg"
                data = bytes(item)
                if data:
                    return True, data, mime

        if "metadata_block_picture" in key_text:
            has_cover = True
            for item in values:
                try:
                    raw = base64.b64decode(str(item))
                    picture = Picture(raw)
                except Exception:
                    continue
                if picture.data:
                    return True, picture.data, picture.mime

    if has_cover:
        return True, b"", ""
    return sidecar_cover_bytes(path)


def sidecar_cover_bytes(path: Path) -> tuple[bool, bytes, str]:
    for name in COVER_FILE_NAMES:
        candidate = path.parent / name
        if not candidate.is_file():
            continue
        try:
            data = candidate.read_bytes()
        except OSError:
            continue
        if data:
            mime = "image/png" if candidate.suffix.lower() == ".png" else "image/jpeg"
            return True, data, mime
    return False, b"", ""


def embedded_cover(path: Path, include_data_uri: bool = False) -> tuple[bool, str]:
    has_cover, data, mime = embedded_cover_bytes(path)
    if include_data_uri and data:
        return has_cover, image_data_uri(data, mime)
    return has_cover, ""


def has_tag_text(value: object) -> bool:
    return bool(lyrics_text_from_tag_value(value))


def lyrics_text_from_tag_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="ignore").strip()
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (list, tuple, set)):
        parts = [lyrics_text_from_tag_value(item) for item in value]
        return "\n".join(part for part in parts if part).strip()
    for attr in ("text", "lyrics"):
        if hasattr(value, attr):
            text = lyrics_text_from_tag_value(getattr(value, attr))
            if text:
                return text

    return str(value).strip()


def is_lyrics_tag_key(key: object) -> bool:
    key_text = str(key).lower().strip()
    if "lyricist" in key_text:
        return False
    return (
        key_text in {"lyrics", "unsyncedlyrics", "syncedlyrics", "lyr", "\xa9lyr", "©lyr"}
        or key_text.startswith(("uslt", "sylt"))
        or "lyrics" in key_text
    )


def has_embedded_lyrics(path: Path) -> bool:
    return bool(lyrics_for_track(path))


def embedded_lyrics(path: Path) -> str:
    try:
        audio = MutagenFile(path, easy=False)
    except Exception:
        return ""

    if audio is None or audio.tags is None:
        return ""

    lyrics = [
        lyrics_text_from_tag_value(value)
        for key, value in audio.tags.items()
        if is_lyrics_tag_key(key)
    ]
    return "\n\n".join(text for text in lyrics if text).strip()


def sidecar_lyrics_path(path: Path) -> Path | None:
    for extension in LYRICS_FILE_EXTENSIONS:
        candidate = path.with_suffix(extension)
        if candidate.is_file():
            return candidate

    normalized_stem = normalize(path.stem)
    try:
        candidates = list(path.parent.iterdir())
    except OSError:
        return None

    for candidate in candidates:
        if not candidate.is_file() or candidate.suffix.lower() not in LYRICS_FILE_EXTENSIONS:
            continue
        if normalize(candidate.stem) == normalized_stem:
            return candidate
    return None


def lyrics_for_track(path: Path) -> str:
    lyrics, _source = lyrics_for_track_with_source(path)
    return lyrics


def lyrics_for_track_with_source(path: Path) -> tuple[str, str]:
    embedded = embedded_lyrics(path)
    if embedded:
        return embedded, "встроенные теги"

    sidecar = sidecar_lyrics_path(path)
    if sidecar is None:
        return "", ""

    for encoding in ("utf-8-sig", "utf-8", "cp1251"):
        try:
            text = sidecar.read_text(encoding=encoding).strip()
        except UnicodeDecodeError:
            continue
        except OSError:
            return "", ""
        if text:
            return text, sidecar.name
    return "", ""


def cover_api_url(file_path: str) -> str:
    if not file_path:
        return ""
    return f"/api/cover?file={quote(file_path, safe='')}"


def path_lookup_key(value: str) -> str:
    return str(PureWindowsPath(value or "")).replace("/", "\\").casefold()


def build_cover_lookup(tracks: list[dict]) -> tuple[dict[str, dict[str, object]], dict[str, list[dict[str, object]]]]:
    by_path: dict[str, dict[str, object]] = {}
    by_name: dict[str, list[dict[str, object]]] = defaultdict(list)

    for track in tracks:
        path = str(track.get("path") or "")
        name = str(track.get("name") or file_name(path))
        tags = track.get("tags") or []
        info = {
            "has_cover": bool(track.get("has_cover") or track.get("cover_url") or track.get("cover_data_uri")),
            "cover_url": str(track.get("cover_url") or ""),
            "has_lyrics": any(
                tag.get("kind") == "lyrics" and normalize(str(tag.get("value") or "")) == "есть"
                for tag in tags
            ),
        }
        if path:
            by_path[path_lookup_key(path)] = info
        if name:
            by_name[name.casefold()].append(info)

    return by_path, by_name


def cover_info_for_path(
    file_path: str,
    by_path: dict[str, dict[str, object]],
    by_name: dict[str, list[dict[str, object]]],
) -> dict[str, object] | None:
    exact = by_path.get(path_lookup_key(file_path))
    if exact:
        return exact

    candidates = by_name.get(file_name(file_path).casefold(), [])
    with_cover = [candidate for candidate in candidates if candidate.get("has_cover")]
    if with_cover and len(with_cover) == len(candidates):
        return with_cover[0]
    if len(with_cover) == 1:
        return with_cover[0]
    if len(candidates) == 1:
        return candidates[0]

    path = Path(file_path)
    if path.is_file():
        has_cover, _cover_data_uri = embedded_cover(path)
        return {
            "has_cover": has_cover,
            "cover_url": cover_api_url(file_path) if has_cover else "",
            "has_lyrics": has_embedded_lyrics(path),
        }
    return None


def year_from(value: str) -> str:
    match = re.search(r"\d{4}", value or "")
    return match.group(0) if match else clean_tag_value(value)


def split_genres(value: str) -> list[str]:
    return normalized_genres(value)


def track_genres(track: dict) -> list[str]:
    return [genre for value in tag_values(track, "genre") for genre in split_genres(value)]


def collect_genres_from_tracks(tracks: list[dict]) -> dict[str, int]:
    genres: Counter[str] = Counter()
    display_names: dict[str, str] = {}

    for track in tracks:
        seen = set()
        for genre in track_genres(track):
            key = normalize(genre)
            if not key or key in seen:
                continue
            seen.add(key)
            display_names.setdefault(key, genre)
            genres[key] += 1

    return {
        display_names[key]: count
        for key, count in sorted(
            genres.items(),
            key=lambda item: (-item[1], display_names.get(item[0], item[0]).lower()),
        )
    }


def collect_years_from_tracks(tracks: list[dict]) -> dict[str, int]:
    years: Counter[str] = Counter()
    for track in tracks:
        for tag in track.get("tags", []):
            if not isinstance(tag, dict) or tag.get("kind") != "year":
                continue
            match = re.search(r"\d{4}", str(tag.get("value", "")))
            if match:
                years[match.group(0)] += 1

    return {
        year: count
        for year, count in sorted(years.items(), key=lambda item: item[0], reverse=True)
    }


def tag_values(track: dict, kind: str) -> list[str]:
    values = []
    for tag in track.get("tags", []):
        if not isinstance(tag, dict) or tag.get("kind") != kind:
            continue
        value = str(tag.get("value", "")).strip()
        if value:
            values.append(value)
    return values


def heatmap_era_from_year(value: str) -> str:
    match = re.search(r"\d{4}", value or "")
    if not match:
        return "Без года"

    year = int(match.group(0))
    for label, start_year, end_year in HEATMAP_ERAS:
        if start_year is not None and end_year is not None and start_year <= year <= end_year:
            return label
    return "Без года"


def collect_genre_era_heatmap(tracks: list[dict], limit: int = 10) -> dict[str, object]:
    matrix: dict[str, Counter[str]] = defaultdict(Counter)
    display_names: dict[str, str] = {}
    totals: Counter[str] = Counter()
    columns = [label for label, _, _ in HEATMAP_ERAS]

    for track in tracks:
        genre_values = []
        for value in tag_values(track, "genre"):
            genre_values.extend(split_genres(value))
        if not genre_values:
            continue

        era = heatmap_era_from_year(" ".join(tag_values(track, "year")))
        seen = set()
        for genre in genre_values:
            key = normalize(genre)
            if not key or key in seen:
                continue
            seen.add(key)
            display_names.setdefault(key, genre)
            matrix[key][era] += 1
            totals[key] += 1

    ordered_keys = sorted(
        totals,
        key=lambda key: (-totals[key], display_names.get(key, key).lower()),
    )[:limit]
    rows = [
        {
            "genre": display_names[key],
            "values": {column: matrix[key].get(column, 0) for column in columns},
            "total": totals[key],
        }
        for key in ordered_keys
    ]
    max_value = max((count for row in rows for count in row["values"].values()), default=0)
    return {"columns": columns, "rows": rows, "max": max_value}


def read_audio_identity_report(path: Path | None) -> dict[str, dict]:
    if path is None or not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"WARNING: audio identity report could not be read: {path} ({exc})")
        return {}
    return payload.get("files", {}) if isinstance(payload, dict) else {}


def analyze_library(library: Path | None, identity_report: Path | None = None, progress=None) -> dict:
    identity_by_path = read_audio_identity_report(identity_report)
    if library is None:
        return {
            "enabled": False,
            "path": "",
            "total_files": "—",
            "audio_files": "—",
            "albums": "—",
            "artists": "—",
            "formats": {},
            "top_artists": [],
            "genres": {},
            "years": {},
            "unreadable_files": "—",
            "files_with_cover": "—",
            "files_with_lyrics": "—",
            "tracks": [],
        }

    if not library.exists():
        raise SystemExit(f"Music library folder does not exist: {library}")

    library_folder = library / MANAGED_LIBRARY_FOLDER
    scan_roots = [library_folder] if library_folder.exists() and library_folder.is_dir() else [library]

    total_files = 0
    audio_files = 0
    unreadable_files = 0
    albums: set[str] = set()
    artists: set[str] = set()
    artist_counts: Counter[str] = Counter()
    formats: Counter[str] = Counter()
    files_with_cover = 0
    files_with_lyrics = 0
    identity_mismatches = 0
    tracks: list[dict] = []

    paths = (path for root in scan_roots for path in root.rglob("*")
             if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS
             and path.relative_to(library).parts[0].casefold() not in MANAGED_STORAGE_FOLDERS)
    for path in progress_files(paths, progress, "analysis"):
        total_files += 1
        identity = identity_by_path.get(str(path), {})
        identity_mismatch = bool(identity.get("mismatch"))
        if identity_mismatch:
            identity_mismatches += 1
        formats[path.suffix.lower().lstrip(".").upper()] += 1
        has_cover, cover_data_uri = embedded_cover(path)
        has_lyrics = has_embedded_lyrics(path)
        if has_cover:
            files_with_cover += 1
        if has_lyrics:
            files_with_lyrics += 1
        cover_url = cover_api_url(str(path)) if has_cover else ""
        cover_tag = make_display_tag("обложка", "есть" if has_cover else "нет", "cover")
        lyrics_tag = make_display_tag("текст песни", "есть" if has_lyrics else "нет", "lyrics")
        size_tag = music_file_size_tag(path)

        try:
            audio = MutagenFile(path, easy=True)
        except Exception as exc:
            print(f"WARNING: skipped unreadable audio file: {path} ({exc})")
            unreadable_files += 1
            tracks.append(
                {
                    "name": path.name,
                    "path": str(path),
                    "folder": str(path.parent),
                    "tags": [
                        make_display_tag("формат", path.suffix.lower().lstrip(".").upper(), "format"),
                        cover_tag,
                        lyrics_tag,
                        size_tag,
                        make_display_tag("статус", "не читается", "status"),
                    ],
                    "has_cover": has_cover,
                    "cover_data_uri": cover_data_uri,
                    "cover_url": cover_url,
                    "identity": identity,
                    "identity_mismatch": identity_mismatch,
                }
            )
            continue

        if audio is None:
            unreadable_files += 1
            tracks.append(
                {
                    "name": path.name,
                    "path": str(path),
                    "folder": str(path.parent),
                    "tags": [
                        make_display_tag("формат", path.suffix.lower().lstrip(".").upper(), "format"),
                        cover_tag,
                        lyrics_tag,
                        size_tag,
                        make_display_tag("статус", "не распознан", "status"),
                    ],
                    "has_cover": has_cover,
                    "cover_data_uri": cover_data_uri,
                    "cover_url": cover_url,
                    "identity": identity,
                    "identity_mismatch": identity_mismatch,
                }
            )
            continue

        audio_files += 1
        tags = audio.tags or {}
        artist = first_tag(tags, ["albumartist", "artist", "composer"])
        track_artist = first_tag(tags, ["artist", "albumartist", "composer"])
        album = first_tag(tags, ["album"])

        if artist:
            artists.add(normalize(artist))
            if not is_excluded_top_artist(artist):
                artist_counts[artist.strip()] += 1
        if track_artist:
            artists.add(normalize(track_artist))
        if album:
            albums.add(f"{normalize(artist)} | {normalize(album)}")

        track_tags = [
            make_display_tag("формат", path.suffix.lower().lstrip(".").upper(), "format"),
            cover_tag,
            lyrics_tag,
            size_tag,
        ]
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

        tracks.append(
            {
                "name": path.name,
                "path": str(path),
                "folder": str(path.parent),
                "tags": track_tags,
                "duration": duration_seconds(getattr(info, "length", None)),
                "has_cover": has_cover,
                "cover_data_uri": cover_data_uri,
                "cover_url": cover_url,
                "identity": identity,
                "identity_mismatch": identity_mismatch,
            }
        )

    return {
        "enabled": True,
        "path": str(library),
        "total_files": total_files,
        "audio_files": audio_files,
        "albums": len(albums),
        "artists": len(artists),
        "formats": dict(sorted(formats.items())),
        "top_artists": artist_counts.most_common(10),
        "genres": collect_genres_from_tracks(tracks),
        "years": collect_years_from_tracks(tracks),
        "unreadable_files": unreadable_files,
        "files_with_cover": files_with_cover,
        "files_with_lyrics": files_with_lyrics,
        "identity_mismatches": identity_mismatches,
        "tracks": sorted(tracks, key=lambda item: item["name"].lower()),
    }

def parse_quality(value: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for part in value.split(";"):
        if "=" not in part:
            continue
        key, val = part.split("=", 1)
        result[key.strip()] = val.strip()
    return result


def safe_int(value: str | int | float | None) -> int:
    if not value:
        return 0
    try:
        return int(float(value))
    except (ValueError, OverflowError):
        return 0


def duration_seconds(value: str | int | float | None) -> float:
    try:
        seconds = float(value or 0)
    except (TypeError, ValueError, OverflowError):
        return 0
    return seconds if math.isfinite(seconds) and seconds > 0 else 0


def format_number(value) -> str:
    if isinstance(value, int):
        return f"{value:,}".replace(",", " ")
    return str(value)


def format_bitrate(value: str | None) -> str:
    bitrate = safe_int(value)
    return "—" if bitrate <= 0 else f"{round(bitrate / 1000)} kbps"


def format_sample_rate(value: str | None) -> str:
    sample_rate = safe_int(value)
    return "—" if sample_rate <= 0 else f"{sample_rate / 1000:g} kHz"


def format_duration(value: str | int | float | None) -> str:
    seconds = safe_int(value)
    if seconds <= 0:
        return "—"
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}:{minutes:02}:{seconds:02}" if hours else f"{minutes}:{seconds:02}"


def format_size(value: str | int | None) -> str:
    size = safe_int(value)
    if size <= 0:
        return "—"

    units = ["B", "KB", "MB", "GB", "TB"]
    n = float(size)
    idx = 0
    while n >= 1024 and idx < len(units) - 1:
        n /= 1024
        idx += 1
    return f"{int(n)} {units[idx]}" if idx == 0 else f"{n:.1f} {units[idx]}"


def music_file_size_tag(path: Path) -> dict[str, str]:
    try:
        size = path.stat().st_size
    except OSError:
        size = 0
    return make_display_tag("размер", format_size(size), "size")


def file_name(path: str) -> str:
    return Path(path).name


def parent_folder(path: str) -> str:
    return str(Path(path).parent)


def read_rows(csv_path: Path) -> list[ReportRow]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = []
        for row in csv.DictReader(f):
            rows.append(
                ReportRow(
                    duplicate_group=row.get("duplicate_group", ""),
                    kept_file=row.get("kept_file", ""),
                    moved_file=row.get("moved_file", ""),
                    reason=row.get("reason", ""),
                    kept_quality=row.get("kept_quality", ""),
                    moved_quality=row.get("moved_quality", ""),
                )
            )
        return rows


def read_review_rows(csv_path: Path) -> list[ReportRow]:
    if not csv_path.exists():
        return []

    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            grouped[row.get("review_group", "")].append(row)

    rows: list[ReportRow] = []
    for group_name, items in grouped.items():
        if len(items) < 2:
            continue
        kept = items[0]
        for candidate in items[1:]:
            rows.append(
                ReportRow(
                    duplicate_group=f"На проверку | {group_name}",
                    kept_file=kept.get("file", ""),
                    moved_file=candidate.get("file", ""),
                    reason=candidate.get("reason", "") or kept.get("reason", ""),
                    kept_quality=kept.get("quality", ""),
                    moved_quality=candidate.get("quality", ""),
                )
            )
    return rows


def build_payload(
    rows: list[ReportRow],
    library_stats: dict,
    review_rows: list[ReportRow] | None = None,
) -> dict:
    review_rows = review_rows or []
    all_rows = rows + review_rows
    groups: dict[str, list[dict]] = defaultdict(list)

    for row in all_rows:
        kept_q = parse_quality(row.kept_quality)
        moved_q = parse_quality(row.moved_quality)
        review_only = row.reason.startswith("needs_review:")
        groups[row.duplicate_group].append(
            {
                "duplicate_group": row.duplicate_group,
                "kept_file": row.kept_file,
                "kept_name": file_name(row.kept_file),
                "kept_folder": parent_folder(row.kept_file),
                "moved_file": row.moved_file,
                "moved_name": file_name(row.moved_file),
                "moved_folder": parent_folder(row.moved_file),
                "reason": row.reason,
                "kept_quality": kept_q,
                "moved_quality": moved_q,
                "review_only": review_only,
            }
        )

    group_items = []
    for group_name, items in groups.items():
        formats = sorted(
            {
                item["kept_quality"].get("format", "").upper()
                for item in items
            }
            | {
                item["moved_quality"].get("format", "").upper()
                for item in items
            }
            - {""}
        )
        group_items.append(
            {
                "name": group_name,
                "items": items,
                "duplicates_count": len(items),
                "formats": formats,
                "review_only": all(item.get("review_only") for item in items),
            }
        )

    return {
        "summary": {
            "groups": len({row.duplicate_group for row in rows}),
            "duplicates": len(rows),
            "review_groups": len({row.duplicate_group for row in review_rows}),
            "review_files": len(review_rows),
        },
        "library": library_stats,
        "groups": sorted(group_items, key=lambda item: item["name"].lower()),
    }


def translate_reason(reason: str) -> str:
    mapping = {
        "lower quality score": "ниже оценка качества",
        "lower bitrate": "ниже битрейт",
        "lower format priority": "хуже формат",
        "missing cover": "нет встроенной обложки",
        "less complete tags": "менее полные теги",
        "needs_review: same artist/title, different album or track tags": "одинаковые исполнитель и название, но отличаются альбом или номер трека",
        "needs_review: same artist/title, tag key is not identical": "похожие теги исполнителя и названия требуют проверки",
        "needs_review: same normalized filename, tags are not identical": "похожие имена файлов, но теги отличаются",
    }
    return mapping.get((reason or "").strip().lower(), reason or "ниже оценка качества")


def _quality_presence(quality: dict, key: str, override: bool | None = None) -> bool | None:
    if override is not None:
        return override
    return {"true": True, "false": False, "1": True, "0": False}.get(str(quality.get(key, "")).strip().lower())


def _quality_number(quality: dict, key: str) -> float | None:
    try:
        value = float(quality[key])
        return value if math.isfinite(value) and value >= 0 else None
    except (KeyError, TypeError, ValueError):
        return None


def better_quality_fields(left: dict, right: dict, *, left_cover=None, right_cover=None, left_lyrics=None, right_lyrics=None) -> tuple[set[str], set[str]]:
    better = (set(), set())
    def mark(key, first, second, positive=False):
        if first is None or second is None or (positive and min(first, second) <= 0):
            return
        if first > second:
            better[0].add(key)
        elif second > first:
            better[1].add(key)
    formats = [str(quality.get("format", "")).lower() for quality in (left, right)]
    ranks = [FORMAT_PRIORITY.get(fmt) for fmt in formats]
    mark("format", *ranks)
    if formats[0] == formats[1] and ranks[0] is not None and format_bitrate(left.get("bitrate")) != format_bitrate(right.get("bitrate")):
        mark("bitrate", _quality_number(left, "bitrate"), _quality_number(right, "bitrate"), positive=True)
    for key in ("bit_depth", "sample_rate", "tag_score"):
        mark(key, _quality_number(left, key), _quality_number(right, key), positive=key != "tag_score")
    covers = (_quality_presence(left, "cover", left_cover), _quality_presence(right, "cover", right_cover))
    lyrics = (_quality_presence(left, "lyrics", left_lyrics), _quality_presence(right, "lyrics", right_lyrics))
    mark("cover", *covers)
    mark("lyrics", *lyrics)
    # Highlight the larger displayed size; file selection keeps its own quality ranking.
    if format_size(left.get("size")) != format_size(right.get("size")):
        mark("size", _quality_number(left, "size"), _quality_number(right, "size"), positive=True)
    return better


def render_quality(
    quality: dict[str, str],
    has_cover_override: bool | None = None,
    has_lyrics_override: bool | None = None,
    better_fields: set[str] | None = None,
) -> str:
    fmt = html.escape(quality.get("format", "—").upper() or "—")
    bit_depth = html.escape(quality.get("bit_depth", "—") or "—")
    tag_score = html.escape(quality.get("tag_score", "—") or "—")
    has_cover = _quality_presence(quality, "cover", has_cover_override)
    cover = "—" if has_cover is None else ("Да" if has_cover else "Нет")
    has_lyrics = _quality_presence(quality, "lyrics", has_lyrics_override)
    lyrics = "—" if has_lyrics is None else ("Да" if has_lyrics else "Нет")

    items = [
        ("Формат", fmt),
        ("Длительность", format_duration(quality.get("duration"))),
        ("Битрейт", html.escape(format_bitrate(quality.get("bitrate")))),
        ("Разрядность", f"{bit_depth} бит" if safe_int(quality.get("bit_depth")) > 0 else "—"),
        ("Частота дискретизации", html.escape(format_sample_rate(quality.get("sample_rate")))),
        ("Теги", f"{tag_score}/5" if _quality_number(quality, "tag_score") is not None else "—"),
        ("Обложка", cover),
        ("Текст песни", lyrics),
        ("Размер", html.escape(format_size(quality.get("size")))),
    ]

    kinds = ["format", "duration", "bitrate", "bit_depth", "sample_rate", "tag_score", "cover", "lyrics", "size"]
    rows = []
    for (label, value), key in zip(items, kinds):
        emphasis = ' class="quality-better" title="Преимущество при сравнении с дублями"' if key in (better_fields or set()) else ""
        rows.append(f'<tr><th scope="row">{label}</th><td data-quality="{key}"{emphasis}>{value}</td></tr>')
    return '<table class="duplicate-quality quality-table" aria-label="Характеристики файла"><tbody>' + ''.join(rows) + '</tbody></table>'


def shared_player() -> str:
    return f'''<section class="global-player" id="globalPlayer" aria-label="Общий плеер" hidden>
      <audio class="audio-player" id="globalAudio" preload="none"></audio>
      <div class="global-track">
        <img id="globalCover" class="global-cover" alt="" hidden>
        <div class="global-cover global-cover-placeholder" id="globalCoverPlaceholder">{lucide_icon("music")}</div>
        <div class="global-track-text"><strong id="globalTitle"></strong><span id="globalArtist"></span></div>
      </div>
      <div class="global-controls">
        <div class="global-transport">
          <button class="global-skip" id="globalPrevious" type="button" aria-label="Предыдущий трек" title="Предыдущий трек" disabled><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 5h2v14H5zm14 0v14L8 12z"/></svg></button>
          <button class="audio-play" id="globalPlay" type="button" aria-label="Воспроизвести" aria-pressed="false">{lucide_icon("play", "audio-play-icon playback-icon")}{lucide_icon("pause", "audio-pause-icon playback-icon")}</button>
          <button class="global-skip" id="globalNext" type="button" aria-label="Следующий трек" title="Следующий трек" disabled><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M17 5h2v14h-2zM5 5l11 7-11 7z"/></svg></button>
        </div>
        <div class="global-timeline">
          <span class="audio-time" id="globalCurrent">0:00</span>
          <div class="audio-seek-wrap" id="globalSeekWrap"><div class="audio-seek-track"><span class="audio-seek-fill"></span></div>
            <input class="audio-seek" id="globalSeek" type="range" min="0" max="1000" value="0" step="1" aria-label="Позиция воспроизведения">
          </div><span class="audio-time" id="globalDuration">0:00</span>
        </div>
      </div>
      <div class="global-extras">
        <button class="global-lyrics" id="globalLyrics" type="button" aria-label="Текст текущей песни" title="Текст песни">{lucide_icon("file-text")}</button>
        <button class="audio-mute" id="globalMute" type="button" aria-label="Выключить звук">{lucide_icon("volume", "audio-volume-icon audio-volume-on")}{lucide_icon("volume-x", "audio-volume-icon audio-volume-off")}</button>
        <div class="audio-seek-wrap global-volume" id="globalVolumeWrap"><div class="audio-seek-track"><span class="audio-seek-fill"></span></div>
          <input class="audio-seek" id="globalVolume" type="range" min="0" max="100" value="100" step="1" aria-label="Громкость">
        </div>
      </div>
      <div class="audio-playback-status global-status" id="globalPlaybackError" role="status" aria-live="polite" hidden></div>
    </section>'''


def cover_preview(track: dict) -> str:
    cover_data_uri = str(track.get("cover_data_uri") or "")
    cover_url = str(track.get("cover_url") or "")
    cover_src = cover_data_uri or cover_url
    if cover_src:
        return (
            '<span class="music-cover music-cover-has">'
            f'<img src="{html.escape(cover_src)}" alt="Обложка трека {html.escape(track.get("name", ""))}" loading="lazy">'
            "</span>"
        )
    return (
        '<span class="music-cover music-cover-empty" aria-label="Обложка: нет">'
        f'{lucide_icon("image-off", "empty-cover-icon")}'
        "</span>"
    )


def duplicate_cover_preview(
    file_path: str,
    name: str,
    quality: dict[str, str],
    cover_info: dict[str, object] | None = None,
) -> str:
    has_cover = bool(cover_info.get("has_cover")) if cover_info else quality.get("cover", "").lower() == "true"
    cover_src = str(cover_info.get("cover_url") or "") if cover_info else ""
    if has_cover and not cover_src:
        cover_src = cover_api_url(file_path)
    if cover_src:
        return (
            '<div class="music-cover duplicate-cover music-cover-has" title="Обложка: есть">'
            f'<img src="{html.escape(cover_src)}" alt="Обложка трека {html.escape(name)}" loading="lazy">'
            "</div>"
        )
    return (
        '<div class="music-cover duplicate-cover music-cover-empty" title="Обложка: нет" aria-label="Обложка: нет">'
        f'{lucide_icon("image-off", "empty-cover-icon")}'
        "<strong>нет</strong>"
        "</div>"
    )


def render_format_bars(formats: dict) -> str:
    if not formats:
        return '<div class="format-empty">Форматы не определены.</div>'

    max_count = max(formats.values()) if formats else 1
    parts = []
    for fmt, count in formats.items():
        width = max(4, round(count / max_count * 100))
        parts.append(
            f"""
            <div class="format-row">
              <div class="format-name">{html.escape(fmt)}</div>
              <div class="format-bar"><span style="width:{width}%"></span></div>
              <div class="format-count">{format_number(count)}</div>
            </div>
            """
        )
    return horizontal_bars(list(formats.items()), "".join(parts), height=max(60, len(formats) * 29), label="Количество файлов по форматам")


def render_artist_bars(artists: list) -> str:
    if not artists:
        return '<div class="format-empty">Исполнители не определены.</div>'

    artists = [(artist, count) for artist, count in artists if not is_excluded_top_artist(str(artist))]
    if not artists:
        return '<div class="format-empty">Исполнители не определены.</div>'

    max_count = max((count for _, count in artists), default=1)
    parts = []
    for artist, count in artists[:10]:
        width = max(4, round(count / max_count * 100))
        parts.append(
            f"""
            <div class="artist-row">
              <div class="artist-name" title="{html.escape(str(artist))}">{html.escape(str(artist))}</div>
              <div class="format-bar"><span style="width:{width}%"></span></div>
              <div class="format-count">{format_number(count)}</div>
            </div>
            """
        )
    return horizontal_bars(artists[:10], "".join(parts), height=max(60, min(10, len(artists)) * 29), label="Количество файлов по исполнителям")


def infer_top_artists_from_tracks(tracks: list[dict]) -> list[tuple[str, int]]:
    counts: Counter[str] = Counter()
    display_names: dict[str, str] = {}
    for track in tracks:
        tags = track.get("tags", [])
        artist = ""
        for preferred_kind in ("albumartist", "artist", "composer"):
            artist = next(
                (
                    str(tag.get("value", "")).strip()
                    for tag in tags
                    if isinstance(tag, dict) and tag.get("kind") == preferred_kind
                ),
                "",
            )
            if artist:
                break
        if not artist or is_excluded_top_artist(artist):
            continue

        key = normalize(artist)
        if not key:
            continue
        display_names.setdefault(key, artist)
        counts[key] += 1

    return [(display_names[key], count) for key, count in counts.most_common(10)]


def genre_coverage(tracks: list[dict]) -> tuple[int, int]:
    total = len(tracks)
    with_genre = 0
    for track in tracks:
        has_genre = any(
            isinstance(tag, dict)
            and tag.get("kind") == "genre"
            and split_genres(str(tag.get("value", "")))
            for tag in track.get("tags", [])
        )
        if has_genre:
            with_genre += 1
    return with_genre, max(0, total - with_genre)


def render_genre_bars(genres: dict, tracks: list[dict] | None = None) -> str:
    # Existing standalone reports can still contain the old cached aggregates.
    genres = normalize_genre_counts(genres)
    if not genres:
        return '<div class="format-empty">Жанры не определены.</div>'

    colors = ["#2bcf70", "#82b7a5", "#e0b56b", "#7ba1c4", "#b599c6", "#b4cb7e", "#cb8f88", "#71b8bd", "#aeaeae"]
    total = sum(genres.values())
    legend_items = list(genres.items())
    top_items = legend_items[:9]
    other_count = total - sum(count for _, count in top_items)
    chart_items = top_items + ([("Прочие", other_count)] if other_count else [])
    start = 0.0
    svg_segments = []
    parts = []
    for index, (genre, count) in enumerate(chart_items):
        color = "#9ca3af" if genre == "Прочие" else colors[index % len(colors)]
        percent = count / total * 100
        if percent > 0:
            svg_segments.append(
                '<circle class="donut-segment" cx="50" cy="50" r="35.5" '
                f'fill="none" stroke="{color}" stroke-width="21" pathLength="100" '
                f'stroke-dasharray="{percent:.6f} {100 - percent:.6f}" '
                f'stroke-dashoffset="{-start:.6f}" transform="rotate(-90 50 50)" />'
            )
        start += percent

    for index, (genre, count) in enumerate(legend_items):
        color = colors[index] if index < len(colors) else "#9ca3af"
        percent = count / total * 100
        parts.append(
            f"""
            <div class="chart-legend-row">
              <span class="chart-dot" style="background:{color}"></span>
              <span class="chart-label" title="{html.escape(genre)}">{html.escape(genre)}</span>
              <strong>{percent:.0f}%</strong>
              <span>{format_number(count)}</span>
            </div>
            """
        )

    top_genre, top_count = legend_items[0]
    top_percent = round(top_count / total * 100)
    coverage = ""
    if tracks is not None:
        with_genre, without_genre = genre_coverage(tracks)
        coverage = (
            '<p class="chart-note">'
            f'Проверенные жанры определены у <strong>{format_number(with_genre)}</strong> из '
            f'<strong>{len(tracks)}</strong> файлов. '
            f'Не определён: <strong>{format_number(without_genre)}</strong>.'
            '</p>'
        )
    ring = plotly_chart([{
        "type": "pie", "values": [count for _, count in chart_items],
        "labels": [html.escape(str(genre)) for genre, _ in chart_items],
        "hole": 0.54, "sort": False, "direction": "clockwise", "textinfo": "none",
        "marker": {"colors": ["#9ca3af" if genre == "Прочие" else colors[index % len(colors)] for index, (genre, _) in enumerate(chart_items)], "line": {"width": 0}},
        "hovertemplate": "%{label}: %{value} файлов (%{percent})<extra></extra>",
    }], {}, '<svg class="donut-svg" viewBox="0 0 100 100" aria-hidden="true">' + "".join(svg_segments) + '</svg>',
        height=160, classes="donut-chart", label="Распределение файлов по жанрам")
    return f"""
    {coverage}
    <div class="donut-layout">
      <div class="donut-chart-wrap">
        {ring}
        <div class="donut-hole">
          <strong>{top_percent}%</strong>
          <span>{html.escape(top_genre)}</span>
        </div>
      </div>
      <div class="chart-legend">
        {"".join(parts)}
      </div>
    </div>
    """


def render_year_bars(years: dict) -> str:
    if not years:
        return '<div class="format-empty">Годы не определены.</div>'

    all_year_items = sorted(
        ((int(year), count) for year, count in years.items() if str(year).isdigit()),
        key=lambda item: item[0],
    )
    if not all_year_items:
        return '<div class="format-empty">Годы не определены.</div>'

    era_definitions = [
        ("до 80-х", None, 1979),
        ("80-е", 1980, 1989),
        ("90-е", 1990, 1999),
        ("00-е", 2000, 2009),
        ("10-е", 2010, 2019),
        ("20-е", 2020, 2029),
    ]
    era_items = []
    for label, start_year, end_year in era_definitions:
        count = sum(
            year_count
            for year, year_count in all_year_items
            if (start_year is None or year >= start_year) and year <= end_year
        )
        if not count:
            continue

        if start_year is None:
            title = f"{label}: до {end_year + 1}, {format_number(count)} файлов"
        else:
            title = f"{label}: {start_year}-{end_year}, {format_number(count)} файлов"
        era_items.append((label, count, title))

    max_count = max(count for _, count, _ in era_items)
    bars = []
    for label, count, title in era_items:
        ratio = max(4.0, count / max_count * 100)
        bars.append(
            f"""
            <div class="year-chart-item" title="{html.escape(title)}">
              <div class="year-chart-column">
                <span class="year-chart-value">{format_number(count)}</span>
                <span class="year-chart-bar" style="--bar-height:{ratio:.2f}%"></span>
              </div>
              <span class="year-chart-label">{html.escape(label)}</span>
            </div>
            """
        )

    plot = plotly_chart([{
        "type": "bar", "x": [label for label, _, _ in era_items], "y": [count for _, count, _ in era_items],
        "customdata": [title for _, _, title in era_items],
        "marker": {"color": "#2bcf70", "line": {"width": 0}},
        "text": [str(count) for _, count, _ in era_items], "textposition": "outside", "cliponaxis": False,
        "hovertemplate": "%{customdata}<extra></extra>",
    }], {
        "margin": {"l": 4, "r": 4, "t": 24, "b": 28}, "bargap": 0.55, "barcornerradius": 0,
        "xaxis": {"fixedrange": True, "showgrid": False, "showline": True, "linecolor": "#303030", "tickfont": {"size": 12}},
        "yaxis": {"visible": False, "fixedrange": True, "range": [0, max_count * 1.22]},
    }, '<div class="year-chart">' + "".join(bars) + '</div>', height=200, label="Эпохи по количеству файлов")
    peak_year, peak_count = max(all_year_items, key=lambda item: item[1])
    return f"""
    <p class="chart-note">
      Самый музыкальный год: <strong>{html.escape(str(peak_year))}</strong>,
      <strong>{format_number(peak_count)}</strong> файлов.
    </p>
    {plot}
    """


def heatmap_color(value: int, max_value: int) -> str:
    if value <= 0 or max_value <= 0:
        return "rgb(36, 36, 36)"

    stops = [
        (0.0, (30, 43, 35)),
        (0.24, (32, 58, 42)),
        (0.46, (34, 77, 52)),
        (0.68, (37, 96, 60)),
        (0.84, (41, 116, 66)),
        (1.0, (43, 124, 72)),
    ]
    ratio = min(1.0, max(0.0, math.log1p(value) / math.log1p(max_value)))
    for index in range(len(stops) - 1):
        left_pos, left_rgb = stops[index]
        right_pos, right_rgb = stops[index + 1]
        if ratio <= right_pos:
            span = right_pos - left_pos or 1
            local_ratio = (ratio - left_pos) / span
            rgb = tuple(
                round(left + (right - left) * local_ratio)
                for left, right in zip(left_rgb, right_rgb)
            )
            return f"rgb({rgb[0]}, {rgb[1]}, {rgb[2]})"
    return "rgb(43, 124, 72)"


def render_genre_era_heatmap(tracks: list[dict]) -> str:
    heatmap = collect_genre_era_heatmap(tracks)
    columns = heatmap["columns"]
    rows = heatmap["rows"]
    max_value = int(heatmap["max"] or 0)

    if not rows:
        return """
        <section class="panel heatmap-panel">
          <div class="heatmap-heading">
            <div>
              <h2>Тепловая карта: эпоха × жанр</h2>
              <p>Количество треков</p>
            </div>
          </div>
          <div class="format-empty">Недостаточно жанров и годов для тепловой карты.</div>
        </section>
        """

    header = "".join(f'<div class="heatmap-column">{html.escape(column)}</div>' for column in columns)
    body_rows = []
    for row in rows:
        cells = []
        for column in columns:
            count = int(row["values"].get(column, 0))
            title = f'{row["genre"]}, {column}: {format_number(count)} треков'
            cells.append(
                f"""
                <div class="heatmap-cell" style="background:{heatmap_color(count, max_value)}" title="{html.escape(title)}">
                  {format_number(count)}
                </div>
                """
            )
        body_rows.append(
            f"""
            <div class="heatmap-row">
              <div class="heatmap-genre" title="{html.escape(row["genre"])}">{html.escape(row["genre"])}</div>
              {"".join(cells)}
            </div>
            """
        )

    raw_counts = [[int(row["values"].get(column, 0)) for column in columns] for row in rows]
    fallback = (
        f'<div class="heatmap-scroll"><div class="heatmap-grid" style="--heatmap-columns:{len(columns)}">'
        '<div class="heatmap-corner"></div>' + header + "".join(body_rows) + '</div></div>'
    )
    plot = plotly_chart([{
        "type": "heatmap", "x": columns, "y": [html.escape(row["genre"]) for row in rows],
        "z": [[math.log1p(count) for count in row] for row in raw_counts], "zmin": 0, "zmax": math.log1p(max_value) or 1,
        "customdata": raw_counts, "text": raw_counts, "texttemplate": "%{text}", "textfont": {"size": 12},
        "colorscale": [[0, "#242424"], [0.000001, "#1e2b23"], [0.24, "#203a2a"], [0.46, "#224d34"], [0.68, "#25603c"], [0.84, "#297442"], [1, "#2b7c48"]],
        "showscale": False, "xgap": 3, "ygap": 3, "zsmooth": False,
        "hovertemplate": "%{y}<br>%{x}: %{customdata} треков<extra></extra>",
    }], {
        "margin": {"l": 0, "r": 4, "t": 30, "b": 4},
        "xaxis": {"side": "top", "fixedrange": True, "showgrid": False, "tickfont": {"size": 12}, "ticks": "", "zeroline": False},
        "yaxis": {"autorange": "reversed", "automargin": True, "fixedrange": True, "showgrid": False, "tickfont": {"size": 12}, "ticks": "", "ticksuffix": "  ", "zeroline": False},
    }, fallback, height=max(130, len(rows) * 35 + 40), label="Количество треков по эпохам и жанрам")
    return f"""
    <section class="panel heatmap-panel">
      <div class="heatmap-heading">
        <div>
          <h2>Тепловая карта: эпоха × жанр</h2>
          <p>Количество треков</p>
        </div>
      </div>
      {plot}
      <div class="heatmap-scale">
        <span>Меньше</span>
        <div class="heatmap-scale-bar"></div>
        <span>Больше</span>
      </div>
    </section>
    """


def report_safe_path_part(value: str, fallback: str) -> str:
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', " ", str(value or "").strip())
    value = re.sub(r"\s+", " ", value).strip(" .")
    return value or fallback


def already_layouted(track: dict, library_path: str) -> bool:
    track_path = str(track.get("path", ""))
    if not track_path or not library_path:
        return False
    artist_values = tag_values(track, "albumartist") or tag_values(track, "artist")
    album_values = tag_values(track, "album")
    title_values = tag_values(track, "title")
    if not artist_values or not album_values or not title_values:
        return False
    artist = report_safe_path_part(artist_values[0], "Unknown Artist")
    album = report_safe_path_part(album_values[0], "Unknown Album")
    title = report_safe_path_part(title_values[0], PureWindowsPath(track_path).stem)
    source = PureWindowsPath(track_path)
    library = PureWindowsPath(library_path)
    try:
        relative = source.relative_to(library)
        base = library / MANAGED_LIBRARY_FOLDER if relative.parts and relative.parts[0].casefold() == MANAGED_LIBRARY_FOLDER.casefold() else library
    except ValueError:
        base = library
    expected_parent = base / artist / album
    expected_stem = report_safe_path_part(f"{title} - {artist}", source.stem)
    if path_lookup_key(str(source.parent)) != path_lookup_key(str(expected_parent)):
        return False
    return source.stem == expected_stem or bool(re.fullmatch(re.escape(expected_stem) + r" \(\d+\)", source.stem))


def render_music_list(tracks: list[dict], duplicate_paths: set[str] | None = None, library_path: str = "") -> str:
    duplicate_paths = duplicate_paths or set()
    items = []
    for index, track in enumerate(tracks, start=1):
        tag_search_values = []
        tag_values_by_kind = defaultdict(list)
        tag_parts = []
        for tag in track.get("tags", []):
            if isinstance(tag, dict):
                label = tag.get("label", "")
                value = tag.get("value", "")
                kind = re.sub(r"[^a-z0-9_-]", "", tag.get("kind", "tag").lower()) or "tag"
                text = f"{label}: {value}" if label and value else label or value
                tag_search_values.append(text)
                tag_values_by_kind[kind].append(text)
                if kind in {"title", "artist", "album"}:
                    continue
                presence = f' data-present="{"yes" if str(value).strip().lower() == "есть" else "no"}"' if kind in {"cover", "lyrics"} else ""
                tag_parts.append(
                    f'<span class="music-pill music-pill-{html.escape(kind)}"{presence}>{html.escape(text)}</span>'
                )
            else:
                tag_search_values.append(str(tag))
                tag_values_by_kind["tag"].append(str(tag))
                tag_parts.append(f'<span class="music-pill">{html.escape(str(tag))}</span>')
        tags = "".join(tag_parts)
        search_text = " ".join(
            [
                track.get("name", ""),
                track.get("folder", ""),
                " ".join(tag_search_values),
            ]
        ).lower()
        identity_mismatch = bool(track.get("identity_mismatch"))
        identity = track.get("identity") or {}
        duplicate_note = (
            '<div class="music-track-match">Есть совпадения в разделе «Дубли»</div>'
            if track.get("path", "") in duplicate_paths
            else ""
        )
        is_layouted = already_layouted(track, library_path)
        layout_status = "done" if is_layouted else "ready"
        layout_disabled = (
            ' disabled aria-disabled="true" title="Файл уже находится в папках исполнителя и альбома"'
            if is_layouted
            else ""
        )
        has_lyrics = "текст песни: есть" in " ".join(tag_values_by_kind.get("lyrics", [])).lower()
        has_cover = bool(track.get("has_cover"))
        lyrics_disabled = "" if has_lyrics else ' disabled aria-disabled="true" title="Текст песни не найден"'
        lyrics_title = " · ".join(tag_values(track, "title"))
        lyrics_artist = " · ".join(tag_values(track, "artist") or tag_values(track, "albumartist"))
        title = lyrics_title or track.get("name", "")
        album = " · ".join(tag_values(track, "album"))
        details_id = f"music-details-{index}"
        cover_search_disabled = ' disabled aria-disabled="true" title="Обложка уже есть"' if has_cover else ""
        lyrics_search_disabled = ' disabled aria-disabled="true" title="Текст уже есть"' if has_lyrics else ""
        identity_warning = ""
        if identity_mismatch:
            recognized_parts = [
                str(identity.get(key, "")).strip()
                for key in ("recognized_artist", "recognized_title")
                if str(identity.get(key, "")).strip()
            ]
            recognized = " — ".join(recognized_parts) or "не определено"
            confidence = round(float(identity.get("score", 0) or 0) * 100)
            if identity.get("source") == "user":
                source_label = "подтверждено пользователем"
            elif identity.get("source") == "shazamio":
                source_label = "распознано Shazam"
            else:
                source_label = f"уверенность {confidence}%"
            identity_warning = (
                f'<div class="identity-warning">{lucide_icon("triangle-alert", "identity-warning-icon")} По аудиоотпечатку: '
                f'<strong>{html.escape(recognized)}</strong> ({source_label}). '
                'Исполнитель или название не совпадают с тегами.</div>'
            )
        cover_html = cover_preview(track)
        duration = duration_seconds(track.get("duration"))
        genres_attr = html.escape(json.dumps(track_genres(track), ensure_ascii=False))
        items.append(
            f"""
            <tbody class="music-card" data-file-path="{html.escape(track.get("path", ""))}" data-layout-status="{layout_status}" data-music-search="{html.escape(search_text)}" data-music-genres="{genres_attr}" data-duration="{duration}" data-sort-number="{index}" data-sort-name="{html.escape(title.lower())}" data-sort-artist="{html.escape(lyrics_artist.lower())}" data-sort-album="{html.escape(album.lower())}">
              <tr class="music-track-row">
                <td class="music-track-number">{index}</td>
                <th scope="row">
                  <div class="music-track-name">
                    <button class="music-play" type="button" title="Слушать" aria-label="Слушать: {html.escape(title)}" aria-pressed="false">
                      {cover_html}
                      <span class="music-play-icons">
                        {lucide_icon("play", "music-play-icon playback-icon")}
                        {lucide_icon("pause", "music-pause-icon playback-icon")}
                      </span>
                    </button>
                    <div class="music-track-text">
                      <div class="music-title" title="{html.escape(title)}">{html.escape(title)}</div>
                      <div class="music-track-artist-mobile" title="{html.escape(lyrics_artist)}">{html.escape(lyrics_artist)}</div>
                      <div class="music-track-album-mobile" title="{html.escape(album)}">{html.escape(album)}</div>
                    </div>
                  </div>
                </th>
                <td class="music-track-artist" title="{html.escape(lyrics_artist)}">{html.escape(lyrics_artist or "—")}</td>
                <td class="music-track-album" title="{html.escape(album)}">{html.escape(album or "—")}</td>
                <td class="music-track-duration">{format_duration(duration)}</td>
                <td class="music-track-control">
                  <button class="music-details-toggle" type="button" aria-expanded="false" aria-controls="{details_id}" aria-label="Подробности: {html.escape(title)}" title="Подробности">
                    {lucide_icon("chevron-down", "group-chevron")}
                  </button>
                </td>
              </tr>
              <tr class="music-track-details" id="{details_id}" hidden>
                <td colspan="6"><div class="music-track-panel">
                  <button class="music-trash-icon trash-one" type="button" data-file-path="{html.escape(track.get("path", ""))}" title="В корзину" aria-label="В корзину">
                    {lucide_icon("trash", "trash-svg")}
                  </button>
                  <div class="music-path">{html.escape(track.get("path") or track.get("folder", ""))}</div>
                  {duplicate_note}
                  <div class="music-pills">{tags}</div>
                  {identity_warning}
                  <div class="music-actions">
                    <button class="small music-action-single" type="button" data-action="tag" data-file-path="{html.escape(track.get("path", ""))}">Теги через beets</button>
                    <button class="small music-action-single" type="button" data-action="shazam-tag" data-file-path="{html.escape(track.get("path", ""))}">Теги через Shazam</button>
                    <button class="small music-action-single" type="button" data-action="layout" data-file-path="{html.escape(track.get("path", ""))}"{layout_disabled}>Разложить по папкам</button>
                    <button class="small enrichment-button" type="button" data-kind="cover" data-file-path="{html.escape(track.get("path", ""))}"{cover_search_disabled}>Найти обложку</button>
                    <button class="small enrichment-button" type="button" data-kind="lyrics" data-file-path="{html.escape(track.get("path", ""))}"{lyrics_search_disabled}>Найти текст</button>
                    <button class="small lyrics-button" type="button" data-file-path="{html.escape(track.get("path", ""))}" data-track-name="{html.escape(track.get("name", ""))}" data-lyrics-title="{html.escape(lyrics_title)}" data-lyrics-artist="{html.escape(lyrics_artist)}"{lyrics_disabled}>Текст песни</button>
                  </div>
                  <div class="music-card-status" aria-live="polite">
                    <div class="music-card-status-text"></div>
                    <div class="music-card-progress" aria-hidden="true"><span></span></div>
                  </div>
                </div></td>
              </tr>
            </tbody>
            """
        )
    return "".join(items)


def duplicate_group_title(group: dict, tracks_by_path: dict) -> str:
    items = group.get("items", [])
    if not items:
        return "Группа файлов"
    path = items[0].get("kept_file", "")
    track = tracks_by_path.get(path_lookup_key(path), {})
    titles = tag_values(track, "title")
    artists = tag_values(track, "artist") or tag_values(track, "albumartist")
    title = titles[0] if titles else file_name(path).rsplit(".", 1)[0]
    return f"{title} — {artists[0]}" if titles and artists else title


def duplicate_search_text(path: str, tracks_by_path: dict) -> str:
    track = tracks_by_path.get(path_lookup_key(path), {})
    values = [path, str(track.get("name", ""))]
    values.extend(str(tag.get("value", "")) for tag in track.get("tags", []) if isinstance(tag, dict))
    return " ".join(values).lower()


def render_duplicate_track(item: dict, side: str, cover_info: dict | None, review_only: bool, better_fields: set[str], search_text: str = "", reference_better: set[str] | None = None) -> str:
    prefix = "kept" if side == "keep" else "moved"
    path, name = item[f"{prefix}_file"], item[f"{prefix}_name"]
    quality = item[f"{prefix}_quality"]
    label = ("Лучший кандидат" if side == "keep" else "Для сравнения") if review_only else ("Предлагается оставить" if side == "keep" else "Предлагается в карантин")
    reason = translate_reason(item["reason"]) if side != "keep" else ""
    if side != "keep" and not review_only and item["reason"] == "lower quality score":
        explanations = {
            "format": "У файла 1 выше приоритет формата",
            "bitrate": "У файла 1 выше битрейт",
            "bit_depth": "У файла 1 выше разрядность",
            "sample_rate": "У файла 1 выше частота дискретизации",
            "tag_score": "У файла 1 полнее теги",
            "cover": "У файла 1 есть обложка",
            "size": "У файла 1 больше размер",
        }
        reason = next((text for key, text in explanations.items() if key in (reference_better or set())), "Выбор по рейтингу файла")
    reason = html.escape(reason)
    has_cover = bool(cover_info.get("has_cover")) if cover_info else None
    has_lyrics = bool(cover_info.get("has_lyrics")) if cover_info else None
    return f'''
      <article class="track {side} duplicate-track" tabindex="0" aria-label="Музыкальная запись: {html.escape(name)}" data-file-path="{html.escape(path)}" data-search="{html.escape(search_text)}" data-reference-better="{' '.join(sorted(reference_better or []))}">
        <button class="music-trash-icon trash-one" type="button" data-file-path="{html.escape(path)}" title="В корзину" aria-label="В корзину">
          {lucide_icon("trash", "trash-svg")}
        </button>
        <div class="music-card-content">
          {duplicate_cover_preview(path, name, quality, cover_info)}
          <div class="music-card-main">
            <div class="duplicate-track-heading"><span class="track-label">{label}</span><span class="duplicate-reason">{reason}</span></div>
            <span class="duplicate-file-number"></span>
            <div class="music-title track-title" title="{html.escape(name)}">{html.escape(name)}</div>
            <div class="music-path track-path" title="{html.escape(path)}">{html.escape(item[f"{prefix}_folder"])}</div>
            {render_quality(quality, has_cover, has_lyrics, better_fields=better_fields)}
            <div class="music-actions">
              <button class="small duplicate-listen" type="button" data-file-path="{html.escape(path)}" aria-label="Слушать" aria-pressed="false">{lucide_icon("play", "duplicate-listen-play playback-icon")}{lucide_icon("pause", "duplicate-listen-pause playback-icon")}<span class="duplicate-listen-label">Слушать</span></button>
              <button class="small quarantine-one" type="button" data-file="{html.escape(path)}">В карантин</button>
            </div>
          </div>
        </div>
      </article>'''


def scan_progress_panel(panel_id: str) -> str:
    return f'''<div class="source-progress" id="{panel_id}" hidden>
        <div class="source-progress-caption"><strong data-scan-stage role="status"></strong><span data-scan-details></span></div>
        <progress max="1" aria-label="Прогресс текущего этапа сканирования"></progress>
        <div class="source-progress-file" data-scan-file></div>
      </div>'''


def render_html(payload: dict) -> str:
    summary = payload["summary"]
    library = payload["library"]
    top_artists = library.get("top_artists") or infer_top_artists_from_tracks(library.get("tracks", []))
    genres = collect_genres_from_tracks(library["tracks"]) if "tracks" in library else normalize_genre_counts(library.get("genres", {}))
    library["genres"] = genres
    years = library.get("years") or collect_years_from_tracks(library.get("tracks", []))
    library["years"] = years
    json_payload = json.dumps(payload, ensure_ascii=False)
    library_raw_path = library.get("path", "")
    source_html = (
        '<button class="sidebar-source" id="librarySource" type="button" aria-haspopup="dialog" '
        'aria-controls="sourceDialog" aria-label="Изменить источник музыки"><span class="sidebar-source-label">Источник</span>'
        f'<span class="sidebar-source-path" id="librarySourcePath" data-path="{html.escape(library_raw_path)}" '
        f'title="{html.escape(library_raw_path)}">{html.escape(library_raw_path) if library_raw_path else "Выбрать папку"}</span></button>'
    )
    duplicate_paths = {
        path
        for group in payload.get("groups", [])
        for item in group.get("items", [])
        for path in (item.get("kept_file", ""), item.get("moved_file", ""))
        if path
    }
    tracks = library.get("tracks", [])
    cover_by_path, cover_by_name = build_cover_lookup(tracks)
    music_html = render_music_list(tracks, duplicate_paths, library_raw_path)
    groups_html = []
    tracks_by_path = {path_lookup_key(track.get("path", "")): track for track in tracks}

    for group in payload["groups"]:
        items_html = []
        references = defaultdict(list)
        for item in group["items"]:
            references[path_lookup_key(item["kept_file"])].append(item)
        for reference_items in references.values():
            reference = reference_items[0]
            kept_cover = cover_info_for_path(reference["kept_file"], cover_by_path, cover_by_name)
            left_advantages = set()
            candidates = []
            seen = {path_lookup_key(reference["kept_file"])}
            for item in reference_items:
                candidate_key = path_lookup_key(item["moved_file"])
                if candidate_key in seen:
                    continue
                seen.add(candidate_key)
                moved_cover = cover_info_for_path(item["moved_file"], cover_by_path, cover_by_name)
                left_better, right_better = better_quality_fields(
                    reference["kept_quality"], item["moved_quality"],
                    left_cover=kept_cover.get("has_cover") if kept_cover else None,
                    right_cover=moved_cover.get("has_cover") if moved_cover else None,
                    left_lyrics=kept_cover.get("has_lyrics") if kept_cover else None,
                    right_lyrics=moved_cover.get("has_lyrics") if moved_cover else None,
                )
                left_advantages.update(left_better)
                candidates.append(render_duplicate_track(item, "move", moved_cover, bool(item.get("review_only")), right_better,
                    duplicate_search_text(item["moved_file"], tracks_by_path), left_better))
            kept_html = render_duplicate_track(reference, "keep", kept_cover, bool(reference.get("review_only")), left_advantages,
                duplicate_search_text(reference["kept_file"], tracks_by_path))
            multiple = len(candidates) > 1
            candidate_html = "".join(candidates)
            items_html.append(f'''
                <div class="comparison{' comparison-multiple' if multiple else ''}" data-kept-file="{html.escape(reference["kept_file"])}">
                  <div class="duplicate-file-grid" style="--compare-files: {len(candidates) + 1}">
                    {kept_html}
                    {candidate_html}
                  </div>
                  <div class="duplicate-card-status" aria-live="polite">
                    <div class="duplicate-card-status-text"></div>
                    <div class="music-card-progress" aria-hidden="true"><span></span></div>
                  </div>
                </div>''')

        search_values = [group["name"], duplicate_group_title(group, tracks_by_path)]
        for item in group["items"]:
            for prefix in ("kept", "moved"):
                path = item[f"{prefix}_file"]
                search_values.append(duplicate_search_text(path, tracks_by_path))

        group_subtitle = (
            f"Возможный дубль · сравнений: {group['duplicates_count']}"
            if group.get("review_only")
            else f"Дублей: {group['duplicates_count']}"
        )
        groups_html.append(
            f"""
            <details class="group-card" data-group-name="{html.escape(group['name'])}" data-search="{html.escape(' '.join(search_values).lower())}" data-search-base="{html.escape((group['name'] + ' ' + duplicate_group_title(group, tracks_by_path)).lower())}" data-count="{group["duplicates_count"]}" data-review-only="{'yes' if group.get('review_only') else 'no'}">
              <summary class="group-header">
                <span class="group-cover">{duplicate_cover_preview(group['items'][0]['kept_file'], group['items'][0]['kept_name'], group['items'][0]['kept_quality'], cover_info_for_path(group['items'][0]['kept_file'], cover_by_path, cover_by_name))}</span>
                <div class="group-heading-text">
                  <h3 class="group-title">{html.escape(duplicate_group_title(group, tracks_by_path))}</h3>
                  <div class="group-differences">{html.escape(' · '.join(group.get('formats', [])))}</div>
                  <div class="group-meta"><span class="group-file-count"></span><div class="group-subtitle">{group_subtitle}</div></div>
                </div>
                <span class="group-status">{'Возможный дубль' if group.get('review_only') else 'К разбору'}</span>
                {lucide_icon("chevron-down", "group-chevron")}
              </summary>
              <div class="group-body">{''.join(items_html)}</div>
            </details>
            """
        )

    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <!--
{ICON_LICENSE_NOTICE}
  -->
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Отчёт по музыкальной библиотеке</title>
  <link rel="icon" type="image/svg+xml" href="{FAVICON_DATA_URI}#v={FAVICON_VERSION}">
  <style>{REPORT_CSS}</style>
  <noscript><style>.report-view[hidden] {{ display: block !important; }}</style></noscript>
</head>
<body>
  <div class="app-shell">
    <aside class="app-sidebar" aria-label="Навигация по отчёту">
      <a class="app-brand" href="#overview" aria-label="Моя медиатека — к обзору">
        <span class="brand-mark">{lucide_icon("audio-lines", "brand-icon")}</span>
        <span><strong>Моя медиатека</strong></span>
      </a>
      <p class="nav-caption">Библиотека</p>
      <nav class="side-nav" aria-label="Разделы медиатеки">
        <a href="#overview" class="active">
          {lucide_icon("house", "nav-icon")}
          <span>Обзор</span>
        </a>
        <a href="#musicSection">
          {lucide_icon("music", "nav-icon")}
          <span>Моя музыка</span>
        </a>
        <a href="#duplicates">
          {lucide_icon("copy", "nav-icon")}
          <span>Дубли</span>
        </a>
      </nav>
      <div class="sidebar-footer">
      {source_html}
      <button class="sidebar-note" id="processingModeNote" type="button" data-mode="dry-run" aria-pressed="false" aria-live="polite" title="Переключить на применение изменений">
        <strong id="processingModeTitle">Режим проверки</strong><small id="processingModeDetail">Изменения и удаление отключены</small>
      </button>
      </div>
    </aside>
    <div class="app-workspace">
  <main class="page">
    <div class="report-view" data-page="overview">
    <section class="header" id="overview">
      <div class="hero-layout">
        <div class="collection-art" aria-hidden="true">{lucide_icon("audio-lines")}</div>
        <div class="hero-copy">
          <div class="hero-kicker">Ваша музыкальная коллекция</div>
          <h1>Моя медиатека</h1>
          <p class="hero-lead">Треки, качество и метаданные вашей библиотеки.</p>
        </div>
      </div>
      <div class="summary">
        <div class="metric metric-primary"><span class="metric-icon">{lucide_icon("files")}</span><span class="metric-label">Всего файлов</span><strong>{format_number(library.get("total_files"))}</strong></div>
        <div class="metric"><span class="metric-icon">{lucide_icon("disc")}</span><span class="metric-label">Альбомов</span><strong>{format_number(library.get("albums"))}</strong></div>
        <div class="metric"><span class="metric-icon">{lucide_icon("users")}</span><span class="metric-label">Исполнителей</span><strong>{format_number(library.get("artists"))}</strong></div>
        <div class="metric"><span class="metric-icon">{lucide_icon("image")}</span><span class="metric-label">С обложкой</span><strong>{format_number(library.get("files_with_cover"))}</strong></div>
        <div class="metric"><span class="metric-icon">{lucide_icon("file-text")}</span><span class="metric-label">С текстом</span><strong>{format_number(library.get("files_with_lyrics"))}</strong></div>
        <div class="metric metric-alert"><span class="metric-icon">{lucide_icon("copy-check")}</span><span class="metric-label">Дублей</span><strong id="duplicateMetric">{format_number(summary["duplicates"])}</strong></div>
        <div class="metric"><span class="metric-icon">{lucide_icon("circle-alert")}</span><span class="metric-label">Возможные дубли</span><strong id="reviewGroupsMetric">{format_number(summary.get("review_groups", 0))}</strong></div>
      </div>
    </section>

    <div class="section-heading" id="insights"><div><span>Обзор библиотеки</span><h2>Ваша коллекция в цифрах</h2></div><p>Форматы, исполнители и метаданные</p></div>
    <div class="analysis-grid">
      <section class="panel summary-panel">
        <h2>Сводка</h2>
        <div class="panel-body note summary-main">
          Групп дублей: <strong id="duplicateGroupsMetric">{format_number(summary["groups"])}</strong><br>
          Файлов, предлагаемых в карантин: <strong id="duplicateFilesMetric">{format_number(summary["duplicates"])}</strong><br>
          Групп возможных дублей: <strong id="reviewGroupsSummaryMetric">{format_number(summary.get("review_groups", 0))}</strong><br>
          Файлов с обложкой: <strong>{format_number(library.get("files_with_cover"))}</strong><br>
          Файлов с текстом песни: <strong>{format_number(library.get("files_with_lyrics"))}</strong><br>
          Не совпадает с аудиоотпечатком: <strong>{format_number(library.get("identity_mismatches", 0))}</strong><br>
          Нечитаемых аудиофайлов: <strong>{format_number(library.get("unreadable_files"))}</strong>
        </div>
        <div class="panel-body">
          <p class="summary-subtitle">Форматы файлов</p>
          {render_format_bars(library.get("formats", {}))}
        </div>
      </section>
      <section class="panel artist-panel">
        <h2>ТОП 10 исполнителей</h2>
        <div class="panel-body">
          {render_artist_bars(top_artists)}
        </div>
      </section>
      <section class="panel genre-panel">
        <h2>Жанры</h2>
        <div class="panel-body">
          {render_genre_bars(genres, library.get("tracks", []))}
        </div>
      </section>
      <section class="panel years-panel">
        <h2>Годы</h2>
        <div class="panel-body">
          {render_year_bars(years)}
        </div>
      </section>
    </div>

    {render_genre_era_heatmap(library.get("tracks", []))}
    </div>

    <section class="report-view music-section" data-page="musicSection" id="musicSection" hidden>
      <header class="music-heading">
        <h2 class="section-title">Моя музыка</h2>
        <p class="music-summary" id="musicSummary"></p>
      </header>
    <div class="search-control page-search is-empty">
      {lucide_icon("search", "search-icon")}
      <input id="musicSearch" type="search" placeholder=" " aria-label="Поиск по музыке">
      <span class="search-placeholder" aria-hidden="true">Поиск: исполнитель, альбом, трек</span>
    </div>
    <section class="music-operations music-toolbar" aria-labelledby="musicActionsTitle">
      <h3 class="music-operations-title" id="musicActionsTitle">Действия</h3>
      <div class="music-operations-row">
        <button class="small" id="tagVisible" type="button">Теги beets</button>
        <button class="small" id="shazamTagVisible" type="button">Теги Shazam</button>
        <button class="small" id="layoutVisible" type="button">Разложить по папкам</button>
        <button class="small" id="coverVisible" type="button">Найти обложки</button>
        <button class="small" id="lyricsVisible" type="button">Найти тексты</button>
        <button class="small" id="rescanLibrary" type="button">Пересканировать библиотеку</button>
      </div>
      <div class="operation-status" id="operationStatus" role="status"></div>
      <div class="quarantine-panel scan-panel" id="scanPanel">
        <p id="scanStatus" role="status"></p>
        <span class="copy-status" id="scanCopyStatus"></span>
        {scan_progress_panel("scanProgress")}
      </div>
    </section>
    <div class="music-genre-pagination" id="musicGenrePagination" role="group" aria-label="Фильтр по жанрам" hidden>
      <button class="music-genre-arrow" id="musicGenrePrevious" type="button" aria-label="Предыдущие жанры" aria-controls="musicGenreFilters" hidden>{lucide_icon("chevron-left")}</button>
      <div class="music-genre-filters" id="musicGenreFilters"></div>
      <button class="music-genre-arrow" id="musicGenreNext" type="button" aria-label="Следующие жанры" aria-controls="musicGenreFilters" hidden>{lucide_icon("chevron-right")}</button>
    </div>
    <table class="music-list" id="musicList" aria-label="Моя музыка" hidden>
      <thead>
        <tr>
          <th class="music-track-number" scope="col"><button class="music-sort" type="button" data-music-sort="number" aria-label="Номер" title="Номер">#</button></th>
          <th scope="col" aria-sort="ascending"><button class="music-sort" type="button" data-music-sort="name">Название</button></th>
          <th class="music-track-artist" scope="col"><button class="music-sort" type="button" data-music-sort="artist">Исполнитель</button></th>
          <th class="music-track-album" scope="col"><button class="music-sort" type="button" data-music-sort="album">Альбом</button></th>
          <th class="music-track-duration" scope="col"><button class="music-sort" type="button" data-music-sort="duration" aria-label="Длительность" title="Длительность">{lucide_icon("clock")}</button></th>
          <th class="music-track-control" scope="col" aria-label="Подробности"></th>
        </tr>
      </thead>
    </table>
    <template id="musicCardSource"><table>{music_html}</table></template>
    <div class="list-pagination" id="musicPagination" hidden><p role="status" aria-live="polite"></p><button class="small" type="button">Показать ещё 10 треков</button></div>
    <div class="empty" id="musicEmpty">{'Ничего не найдено по текущему фильтру музыки.' if tracks else 'Музыкальные файлы не найдены.'}</div>
    </section>

    <section class="report-view music-section duplicates-section" data-page="duplicates" id="duplicates" hidden>
    <div class="duplicates-heading">
      <h2 class="section-title">Дубли</h2>
      <div class="duplicates-actions">
        <button class="small" id="findDuplicates" type="button">Найти дубли</button>
      </div>
    </div>
    <div class="summary duplicate-summary" role="group" aria-label="Статистика дублей">
      <div class="metric"><span class="metric-icon">{lucide_icon("copy")}</span><span class="metric-label">Групп дублей</span><strong id="duplicatePageGroupsMetric">{format_number(summary["groups"])}</strong></div>
      <div class="metric metric-alert"><span class="metric-icon">{lucide_icon("copy-check")}</span><span class="metric-label">Дублей</span><strong id="duplicatePageFilesMetric">{format_number(summary["duplicates"])}</strong></div>
      <div class="metric"><span class="metric-icon">{lucide_icon("circle-alert")}</span><span class="metric-label">Возможные дубли</span><strong id="duplicatePageReviewMetric">{format_number(summary.get("review_groups", 0))}</strong></div>
    </div>
    <div class="search-control page-search is-empty">
      {lucide_icon("search", "search-icon")}
      <input id="duplicateSearch" type="search" placeholder=" " aria-label="Поиск по дублям">
      <span class="search-placeholder" aria-hidden="true">Поиск: исполнитель, альбом, трек</span>
    </div>
    <div class="quarantine-panel scan-panel" id="duplicateScanPanel">
      <p id="duplicateScanStatus">Готово к новому поиску дублей. Файлы не перемещаются.</p>
      <span class="copy-status" id="duplicateScanCopyStatus"></span>
      {scan_progress_panel("duplicateScanProgress")}
    </div>
    <div class="quarantine-panel" id="quarantinePanel">
      <p id="quarantineStatus">Готово к безопасному переносу дублей в карантин. Файлы не удаляются.</p>
      <span class="copy-status" id="copyStatus"></span>
      <div class="global-progress" id="globalProgress" aria-hidden="true"><span></span></div>
    </div>
    <div class="toolbar duplicate-toolbar">
      <select id="duplicateFilter" aria-label="Фильтр групп дублей">
        <option value="all">Все группы</option>
        <option value="duplicates">Дубли</option>
        <option value="review">Возможные дубли</option>
      </select>
    </div>
    <div id="cards"></div>
    <template id="duplicateCardSource">{''.join(groups_html)}</template>
    <div class="list-pagination" id="duplicatePagination" hidden><p role="status" aria-live="polite"></p><button class="small" type="button">Показать ещё 10 групп</button></div>
    <div class="empty{' visible' if not groups_html else ''}" id="empty">Дубли не найдены.</div>
    </section>
  </main>
    </div>
  </div>

  {shared_player()}
  <div class="lyrics-modal" id="lyricsModal" aria-hidden="true">
    <div class="lyrics-dialog" role="dialog" aria-modal="true" aria-labelledby="lyricsTitle">
      <div class="lyrics-dialog-head">
        <div>
          <p class="lyrics-kicker">Текст песни</p>
          <h2 class="lyrics-dialog-title" id="lyricsTitle">Текст песни</h2>
          <div class="lyrics-artist" id="lyricsArtist"></div>
          <details class="lyrics-details" id="lyricsDetails">
            <summary>О тексте</summary>
            <div class="lyrics-source" id="lyricsSource">Источник: не выбран</div>
            <div class="lyrics-dialog-path" id="lyricsPath"></div>
          </details>
        </div>
        <button class="lyrics-close" id="lyricsClose" type="button" aria-label="Закрыть">{lucide_icon("x", "lyrics-close-icon")}</button>
      </div>
      <div class="lyrics-toolbar" role="group" aria-label="Управление текстом и воспроизведением">
        <button class="small" id="lyricsReading" type="button" aria-pressed="true">Для чтения</button>
        <button class="small" id="lyricsOriginal" type="button" aria-pressed="false">Исходный</button>
        <button class="small" id="lyricsFollow" type="button" aria-pressed="true" hidden>Следить за музыкой</button>
        <span class="lyrics-sync-note" id="lyricsSyncNote"></span>
      </div>
      <div class="lyrics-text" id="lyricsText" tabindex="0" aria-label="Текст песни"></div>
    </div>
  </div>

  <script id="payload" type="application/json">{html.escape(json_payload)}</script>
  {SOURCE_DIALOG_HTML}
  <script id="fontLicense" type="text/plain">{html.escape(FONT_LICENSE_NOTICE)}</script>
  <script id="chartLicense" type="text/plain">{html.escape(PLOTLY_LICENSE)}</script>
  <script id="plotlyLibrary">{PLOTLY_JS}</script>
  <script id="reportControls">{REPORT_CONTROLS_JS}</script>
  <script id="reportSource">{SOURCE_DIALOG_JS}</script>
  <script id="reportCharts">{REPORT_CHARTS_JS}</script>
  <script id="reportPagination">{REPORT_PAGINATION_JS}</script>
  <script id="reportLyrics">{REPORT_LYRICS_JS}</script>
  <script id="reportPlayer">{REPORT_PLAYER_JS}</script>
  <script id="reportDuplicates">{REPORT_DUPLICATES_JS}</script>
  <script>
    let cards = Array.from(document.getElementById('duplicateCardSource').content.querySelectorAll('.group-card'));
    let musicCards = Array.from(document.getElementById('musicCardSource').content.querySelectorAll('.music-card'));
    const musicList = document.getElementById('musicList');
    const musicSortButtons = musicList.querySelectorAll('[data-music-sort]');
    let musicSortKey = 'name';
    let musicSortDirection = 1;
    const musicSummary = document.getElementById('musicSummary');
    const musicGenrePagination = document.getElementById('musicGenrePagination');
    const musicGenreFilters = document.getElementById('musicGenreFilters');
    const musicGenrePrevious = document.getElementById('musicGenrePrevious');
    const musicGenreNext = document.getElementById('musicGenreNext');
    const musicNumber = new Intl.NumberFormat('ru');
    const musicPlural = new Intl.PluralRules('ru');
    let musicGenre = '';
    const musicSearch = document.getElementById('musicSearch');
    const duplicateSearch = document.getElementById('duplicateSearch');
    const duplicateFilter = document.getElementById('duplicateFilter');
    const musicEmpty = document.getElementById('musicEmpty');
    const quarantinePanel = document.getElementById('quarantinePanel');
    const copyStatus = document.getElementById('copyStatus');
    const quarantineStatus = document.getElementById('quarantineStatus');
    const globalProgress = document.getElementById('globalProgress');
    const rescanLibrary = document.getElementById('rescanLibrary');
    const findDuplicates = document.getElementById('findDuplicates');
    const scanPanel = document.getElementById('scanPanel');
    const scanStatus = document.getElementById('scanStatus');
    const scanCopyStatus = document.getElementById('scanCopyStatus');
    const scanProgress = document.getElementById('scanProgress');
    const duplicateScanPanel = document.getElementById('duplicateScanPanel');
    const duplicateScanStatus = document.getElementById('duplicateScanStatus');
    const duplicateScanCopyStatus = document.getElementById('duplicateScanCopyStatus');
    const duplicateScanProgress = document.getElementById('duplicateScanProgress');
    const operationStatus = document.getElementById('operationStatus');
    const processingModeNote = document.getElementById('processingModeNote');
    const processingModeTitle = document.getElementById('processingModeTitle');
    const processingModeDetail = document.getElementById('processingModeDetail');
    const tagVisible = document.getElementById('tagVisible');
    const shazamTagVisible = document.getElementById('shazamTagVisible');
    const layoutVisible = document.getElementById('layoutVisible');
    const coverVisible = document.getElementById('coverVisible');
    const lyricsVisible = document.getElementById('lyricsVisible');
    const lyricsModal = document.getElementById('lyricsModal');
    const lyricsTitle = document.getElementById('lyricsTitle');
    const lyricsArtist = document.getElementById('lyricsArtist');
    const lyricsDetails = document.getElementById('lyricsDetails');
    const lyricsReading = document.getElementById('lyricsReading');
    const lyricsOriginal = document.getElementById('lyricsOriginal');
    const lyricsFollow = document.getElementById('lyricsFollow');
    const lyricsSyncNote = document.getElementById('lyricsSyncNote');
    const lyricsPath = document.getElementById('lyricsPath');
    const lyricsSource = document.getElementById('lyricsSource');
    const lyricsText = document.getElementById('lyricsText');
    const lyricsClose = document.getElementById('lyricsClose');
    let lyricsRawText = '';
    let lyricsDocument = null;
    let lyricsRequestId = 0;
    let lyricsAudio = null;

    const lyricsSync = new ReportLyrics.Sync(lyricsText, {{onSeek: seekLyricsLine, onState: updateLyricsPlaybackUI}});
    let lyricsSeekRequest = null;
    const sharedUI = Object.fromEntries(['globalPlayer', 'globalAudio', 'globalPlay', 'globalPrevious', 'globalNext', 'globalCover', 'globalCoverPlaceholder', 'globalTitle', 'globalArtist', 'globalCurrent', 'globalDuration', 'globalSeek', 'globalSeekWrap', 'globalMute', 'globalVolume', 'globalVolumeWrap', 'globalLyrics', 'globalPlaybackError'].map(id => [id, document.getElementById(id)]));
    let cardPlaybackKey = '';
    let playbackContext = 'music';
    const musicCardByPath = new Map(musicCards.map(card => [normalizePathForCompare(card.dataset.filePath), card]));
    const playback = new ReportPlayer(sharedUI.globalAudio, {{
      normalizePath: normalizePathForCompare,
      play: (audio, signal) => toggleAudioPlayback(audio, sharedUI.globalPlay, sharedUI.globalPlaybackError, signal),
      seek: (audio, seconds, signal) => seekAudioPlayback(audio, seconds, sharedUI.globalPlaybackError, signal),
      onChange: updateGlobalTrack,
      onUpdate: updateGlobalPlayer,
    }});

    function trackForPath(path, source = null) {{
      const card = musicCardByPath.get(normalizePathForCompare(path))
        || source?.closest('.duplicate-track');
      const lyrics = card?.querySelector('.lyrics-button');
      const name = card?.querySelector('.music-title')?.textContent || path.split(/[\\\\/]/).pop();
      return {{path, name, title: lyrics?.dataset.lyricsTitle || name.replace(/\\.[^.]+$/, ''),
        artist: lyrics?.dataset.lyricsArtist || '', cover: card?.querySelector('.music-cover img')?.getAttribute('src') || ''}};
    }}

    function updatePlaybackQueue() {{
      const tracks = playbackContext === 'music'
        ? musicCards.filter(card => !card.hidden)
        : cards.filter(card => !card.hidden).flatMap(card => Array.from(card.querySelectorAll('.duplicate-track')));
      playback.setQueue(tracks.map(card => trackForPath(card.dataset.filePath, card)));
    }}

    function syncOpenLyricsPlayer() {{
      if (!lyricsDocument || !lyricsModal.classList.contains('visible')) return;
      const audio = getLyricsPlayer();
      if (lyricsSync.player !== audio) {{
        lyricsAudio = audio;
        lyricsSync.bind(lyricsDocument, audio, !lyricsText.classList.contains('is-raw'));
      }}
    }}

    function updateGlobalTrack(track) {{
      sharedUI.globalPlayer.hidden = !track;
      document.body.classList.toggle('has-player', Boolean(track));
      document.documentElement.style.setProperty('--player-height', track ? sharedUI.globalPlayer.offsetHeight + 'px' : '0px');
      sharedUI.globalPlaybackError.hidden = true;
      sharedUI.globalPlaybackError.textContent = '';
      sharedUI.globalTitle.textContent = track?.title || '';
      sharedUI.globalTitle.title = track?.title || '';
      sharedUI.globalArtist.textContent = track?.artist || '';
      sharedUI.globalCover.hidden = !track?.cover;
      sharedUI.globalCoverPlaceholder.hidden = Boolean(track?.cover);
      if (track?.cover) sharedUI.globalCover.src = track.cover;
      else sharedUI.globalCover.removeAttribute('src');
      syncOpenLyricsPlayer();
    }}

    function updatePlayingCard(card) {{
      const audio = sharedUI.globalAudio;
      const current = playback.matches(card.dataset.filePath);
      const active = current && !audio.paused && !audio.ended;
      card.classList.toggle('is-current-track', current);
      card.classList.toggle('is-playing-track', active);
      const button = card.querySelector('.music-play, .duplicate-listen');
      if (button) {{
        const label = active ? 'Пауза' : 'Слушать';
        const duplicateLabel = button.querySelector('.duplicate-listen-label');
        if (duplicateLabel) {{
          duplicateLabel.textContent = label;
          button.classList.toggle('playing', active);
          button.setAttribute('aria-label', label);
        }} else {{
          button.title = label;
          button.setAttribute('aria-label', label + ': ' + card.querySelector('.music-title').textContent);
        }}
        button.setAttribute('aria-pressed', String(active));
      }}
      if (current) card.setAttribute('aria-current', 'true');
      else card.removeAttribute('aria-current');
    }}

    function updatePlayingCards() {{
      const audio = sharedUI.globalAudio;
      const playing = !audio.paused && !audio.ended;
      const key = (playback.track?.path || '') + ':' + playing;
      if (key === cardPlaybackKey) return;
      cardPlaybackKey = key;
      document.querySelectorAll('.music-card, .duplicate-track').forEach(updatePlayingCard);
    }}

    function updateGlobalPlayer() {{
      const audio = sharedUI.globalAudio;
      const playing = !audio.paused && !audio.ended;
      sharedUI.globalPlay.classList.toggle('playing', playing);
      sharedUI.globalPlay.setAttribute('aria-pressed', String(playing));
      sharedUI.globalPlay.setAttribute('aria-label', playing ? 'Пауза' : 'Воспроизвести');
      sharedUI.globalPlay.setAttribute('aria-busy', String(Boolean(playback.pending)));
      sharedUI.globalPrevious.disabled = !playback.canStep(-1);
      sharedUI.globalNext.disabled = !playback.canStep(1);
      sharedUI.globalCurrent.textContent = formatAudioTime(audio.currentTime);
      sharedUI.globalDuration.textContent = formatAudioTime(audio.duration);
      const progress = Number.isFinite(audio.duration) && audio.duration > 0 ? Math.min(100, audio.currentTime / audio.duration * 100) : 0;
      sharedUI.globalSeek.value = Math.round(progress * 10);
      sharedUI.globalSeek.disabled = !(Number.isFinite(audio.duration) && audio.duration > 0);
      sharedUI.globalSeekWrap.style.setProperty('--audio-progress', progress + '%');
      const muted = audio.muted || audio.volume === 0;
      sharedUI.globalMute.classList.toggle('muted', muted);
      sharedUI.globalMute.setAttribute('aria-label', muted ? 'Включить звук' : 'Выключить звук');
      sharedUI.globalVolume.value = Math.round(audio.volume * 100);
      sharedUI.globalVolumeWrap.style.setProperty('--audio-progress', (muted ? 0 : audio.volume * 100) + '%');
      updatePlayingCards();
    }}

    sharedUI.globalPlay.addEventListener('click', () => playback.toggle());
    sharedUI.globalPrevious.addEventListener('click', () => playback.step(-1));
    sharedUI.globalNext.addEventListener('click', () => playback.step(1));
    sharedUI.globalSeek.addEventListener('input', () => {{
      if (Number.isFinite(playback.audio.duration) && playback.audio.duration > 0) playback.audio.currentTime = Number(sharedUI.globalSeek.value) / 1000 * playback.audio.duration;
    }});
    sharedUI.globalMute.addEventListener('click', () => {{
      const muted = playback.audio.muted || playback.audio.volume === 0;
      if (playback.audio.volume === 0) playback.audio.volume = .5;
      playback.audio.muted = !muted;
    }});
    sharedUI.globalVolume.addEventListener('input', () => {{ playback.audio.volume = Number(sharedUI.globalVolume.value) / 100; playback.audio.muted = false; }});
    sharedUI.globalLyrics.addEventListener('click', () => {{
      if (!playback.track) return;
      const track = playback.track;
      openLyricsModal({{dataset: {{filePath: track.path, trackName: track.name, lyricsTitle: track.title, lyricsArtist: track.artist}}, closest: () => null}});
    }});
    new ResizeObserver(() => document.documentElement.style.setProperty('--player-height', sharedUI.globalPlayer.hidden ? '0px' : sharedUI.globalPlayer.offsetHeight + 'px')).observe(sharedUI.globalPlayer);

    const sideNavLinks = Array.from(document.querySelectorAll('.side-nav a[href^="#"]'));
    const reportPages = Array.from(document.querySelectorAll('.report-view[data-page]'));
    const pageTitles = {{overview: 'Обзор', musicSection: 'Моя музыка', duplicates: 'Дубли'}};
    const boundCards = new WeakSet();
    const musicPager = new ReportPagedList(musicList, document.getElementById('musicPagination'), document.getElementById('musicSection'), bindCardControls);
    const duplicatePager = new ReportPagedList(document.getElementById('cards'), document.getElementById('duplicatePagination'), document.getElementById('duplicates'), bindCardControls);
    const musicCollator = new Intl.Collator('ru', {{ numeric: true, sensitivity: 'base' }});
    duplicatePager.setItems(cards);


    function activatePage(requestedId) {{
      const id = ['overview', 'musicSection', 'duplicates'].includes(requestedId) ? requestedId : 'overview';
      reportPages.forEach(page => {{ page.hidden = page.dataset.page !== id; }});
      sideNavLinks.forEach(link => {{
        const isActive = link.getAttribute('href') === '#' + id;
        link.classList.toggle('active', isActive);
        if (isActive) link.setAttribute('aria-current', 'page');
        else link.removeAttribute('aria-current');
      }});
      document.title = pageTitles[id] + ' — Моя медиатека';
      if (requestedId !== id) history.replaceState(null, '', '#overview');
      closeLyricsModal();
      window.scrollTo(0, 0);
      if (id === 'musicSection') musicPager.activate();
      if (id === 'duplicates') duplicatePager.activate();
      window.dispatchEvent(new Event('report-page-change'));
    }}

    window.addEventListener('hashchange', () => activatePage(window.location.hash.slice(1) || 'overview'));
    function selectedMode() {{
      return processingModeNote.dataset.mode === 'real' ? 'real' : 'dry-run';
    }}

    function toggleProcessingMode() {{
      processingModeNote.dataset.mode = selectedMode() === 'dry-run' ? 'real' : 'dry-run';
      updateOperationStatus();
    }}

    function updateOperationStatus() {{
      const mode = selectedMode();
      processingModeNote.setAttribute('aria-pressed', mode === 'real' ? 'true' : 'false');
      processingModeNote.title = mode === 'real' ? 'Переключить на режим проверки' : 'Переключить на применение изменений';
      if (mode === 'real') {{
        if (processingModeTitle) processingModeTitle.textContent = 'Применить изменения';
        if (processingModeDetail) processingModeDetail.textContent = 'Каждое действие требует подтверждения';
        if (processingModeNote) processingModeNote.classList.add('mode-real');
      }} else {{
        if (processingModeTitle) processingModeTitle.textContent = 'Режим проверки';
        if (processingModeDetail) processingModeDetail.textContent = 'Изменения и удаление отключены';
        if (processingModeNote) processingModeNote.classList.remove('mode-real');
      }}
    }}

    function visibleMusicPaths() {{
      return musicCards
        .filter(card => !card.hidden)
        .map(card => card.dataset.filePath || '')
        .filter(Boolean);
    }}

    function singleMusicPath(button) {{
      const card = button.closest('.music-card');
      return button.dataset.filePath || card?.dataset.filePath || '';
    }}

    function closeLyricsModal() {{
      if (!lyricsModal) return;
      lyricsRequestId += 1;
      cancelLyricsSeek();
      lyricsSync.dispose();
      lyricsAudio = null;
      lyricsModal.classList.remove('visible');
      lyricsModal.setAttribute('aria-hidden', 'true');
    }}

    function setLyricsView(original) {{
      if (!lyricsDocument) return;
      lyricsReading.setAttribute('aria-pressed', String(!original));
      lyricsOriginal.setAttribute('aria-pressed', String(original));
      ReportLyrics.render(lyricsText, lyricsDocument, original ? lyricsRawText : null);
      lyricsText.scrollTop = 0;
      lyricsAudio = getLyricsPlayer();
      lyricsSync.bind(lyricsDocument, lyricsAudio, !original);
    }}

    function getLyricsPlayer() {{
      return playback.matches(lyricsPath.textContent) ? playback.audio : null;
    }}

    function updateLyricsPlaybackUI() {{
      lyricsFollow.hidden = !lyricsSync.hasTiming || !lyricsSync.enabled || !lyricsAudio;
      lyricsFollow.setAttribute('aria-pressed', String(lyricsSync.follow));
      lyricsFollow.textContent = lyricsSync.follow ? 'Следить за музыкой' : 'К текущей строке';
      const zeroTimes = lyricsDocument?.timingIssue === 'zero-timestamps';
      lyricsSyncNote.textContent = lyricsSync.enabled ? (zeroTimes ? 'Все таймкоды — 00:00' : (lyricsSync.hasTiming ? 'По строкам' : 'Без таймкодов')) : 'Исходный текст';
      lyricsSyncNote.title = zeroTimes ? 'У всех строк указано нулевое время. Для синхронизации нужен текст с настоящими таймкодами.' : '';
    }}

    function cancelLyricsSeek() {{
      if (lyricsSeekRequest && playback.pending === lyricsSeekRequest) playback.cancel();
      lyricsSeekRequest = null;
    }}

    async function seekLyricsLine(index) {{
      if (!lyricsDocument) return;
      const track = trackForPath(lyricsPath.textContent);
      const time = ReportLyrics.seekTime(lyricsDocument, index, getLyricsPlayer()?.currentTime || 0);
      if (time === null) return;
      if (!playback.queue.some(item => normalizePathForCompare(item.path) === normalizePathForCompare(track.path))) {{
        playbackContext = 'music';
        updatePlaybackQueue();
      }}
      const request = playback.seek(track, Math.max(0, time));
      const token = playback.pending;
      lyricsSeekRequest = token;
      await request;
      if (lyricsSeekRequest !== token) return;
      if (lyricsModal.classList.contains('visible') && playback.matches(lyricsPath.textContent)) lyricsSync.setFollow(true);
      lyricsSeekRequest = null;
    }}

    async function openLyricsModal(button) {{
      const card = button.closest('.music-card');
      const filePath = button.dataset.filePath || card?.dataset.filePath || '';
      const trackName = button.dataset.trackName || card?.querySelector('.music-title')?.textContent || 'Текст песни';
      if (!filePath || button.disabled) return;
      const requestId = ++lyricsRequestId;
      cancelLyricsSeek();
      lyricsSync.dispose();
      lyricsAudio = null;
      const fallbackTitle = button.dataset.lyricsTitle || trackName.replace(/\\.[^.]+$/, '');
      const fallbackArtist = button.dataset.lyricsArtist || '';

      lyricsTitle.textContent = fallbackTitle;
      lyricsArtist.textContent = fallbackArtist;
      lyricsDetails.open = false;
      lyricsPath.textContent = filePath;
      lyricsSource.textContent = 'Источник: загружается...';
      lyricsDocument = null;
      lyricsRawText = '';
      lyricsReading.disabled = true;
      lyricsOriginal.disabled = true;
      lyricsFollow.hidden = true;
      lyricsSyncNote.textContent = '';
      lyricsReading.setAttribute('aria-pressed', 'true');
      lyricsOriginal.setAttribute('aria-pressed', 'false');
      lyricsText.textContent = 'Загружаю текст песни...';
      lyricsText.classList.add('loading');
      lyricsText.classList.remove('error', 'is-raw');
      lyricsText.scrollTop = 0;
      lyricsModal.classList.add('visible');
      lyricsModal.setAttribute('aria-hidden', 'false');

      try {{
        const serverError = 'Сервер отчёта недоступен. Запустите его и откройте отчёт через сервер.';
        const response = await fetch(`/api/lyrics?file=${{encodeURIComponent(filePath)}}`)
          .catch(() => {{ throw new Error(serverError); }});
        const result = await response.json().catch(() => {{ throw new Error(serverError); }});
        if (requestId !== lyricsRequestId) return;
        if (!response.ok || !result.ok) throw new Error(result.error || 'Текст песни не найден.');
        lyricsRawText = result.lyrics || '';
        lyricsDocument = ReportLyrics.parse(lyricsRawText);
        lyricsTitle.textContent = lyricsDocument.title || fallbackTitle;
        lyricsArtist.textContent = lyricsDocument.artist || fallbackArtist;
        lyricsPath.textContent = filePath;
        lyricsSource.textContent = result.source ? `Источник: ${{result.source}}` : 'Источник: не указан';
        lyricsText.classList.remove('loading');
        lyricsReading.disabled = !lyricsRawText.trim();
        lyricsOriginal.disabled = !lyricsRawText.trim();
        setLyricsView(false);
      }} catch (error) {{
        if (requestId !== lyricsRequestId) return;
        lyricsSource.textContent = 'Источник: не определён';
        lyricsText.textContent = error.message || String(error);
        lyricsText.classList.remove('loading');
        lyricsText.classList.add('error');
      }}
    }}

    async function searchAndSaveEnrichment(button) {{
      const card = button.closest('.music-card');
      const filePath = button.dataset.filePath || card?.dataset.filePath || '';
      const kind = button.dataset.kind || '';
      if (!filePath || !kind || button.disabled) return;
      const label = kind === 'cover' ? 'обложки' : 'текста песни';
      button.disabled = true;
      let saved = false;
      setCardStatus(card, 'running', `Ищу варианты ${{label}}...`);
      try {{
        const searchResponse = await fetch('/api/enrichment/search', {{
          method: 'POST', headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{ file: filePath, kind }})
        }});
        const searchResult = await searchResponse.json();
        if (!searchResponse.ok || !searchResult.ok) throw new Error(searchResult.error || 'Поиск не выполнен.');
        const candidates = searchResult.candidates || [];
        if (!candidates.length) throw new Error('Подходящие варианты не найдены.');
        const choices = candidates.map((item, index) => {{
          const details = kind === 'cover'
            ? `${{item.artist || '—'}} — ${{item.album || '—'}} (${{item.date || item.country || 'год не указан'}}, совпадение ${{item.score || 0}}%)`
            : `${{item.artist || '—'}} — ${{item.title || '—'}} [${{item.kind === 'synced' ? 'LRC' : 'обычный текст'}}]`;
          return `${{index + 1}}. ${{details}}`;
        }}).join('\\n');
        const answer = window.prompt(`Найдены варианты ${{label}}:\n\n${{choices}}\n\nВведите номер кандидата:`, '1');
        if (answer === null) {{ setCardStatus(card, '', 'Сохранение отменено.'); return; }}
        const index = Number.parseInt(answer, 10) - 1;
        if (!Number.isInteger(index) || !candidates[index]) throw new Error('Выбран неверный номер кандидата.');
        const selected = candidates[index];
        if (kind === 'cover' && selected.preview_url) window.open(selected.preview_url, '_blank', 'noopener');
        const preview = kind === 'lyrics' && selected.preview ? `\n\n${{selected.preview.slice(0, 700)}}` : '';
        if (!window.confirm(`Сохранить выбранный вариант рядом с аудиофайлом? Аудиофайл изменён не будет.${{preview}}`)) {{
          setCardStatus(card, '', 'Сохранение отменено.'); return;
        }}
        const saveResponse = await fetch('/api/enrichment/save', {{
          method: 'POST', headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{ file: filePath, candidate_id: selected.id, confirm: 'SAVE_ENRICHMENT' }})
        }});
        const saveResult = await saveResponse.json();
        if (!saveResponse.ok || !saveResult.ok) throw new Error(saveResult.error || 'Не удалось сохранить файл.');
        saved = true;
        const refreshedTracks = saveResult.refresh?.tracks || [];
        refreshedTracks.forEach(track => {{
          const refreshedCard = musicCards.find(item =>
            normalizePathForCompare(item.dataset.filePath || '') === normalizePathForCompare(track.path || '')
          );
          if (refreshedCard) updateMusicCardFromTrack(refreshedCard, track);
        }});
        if (refreshedTracks.length) {{
          refreshMusicOverview();
          applySort();
        }}
        setCardStatus(card, 'done', saveResult.message || 'Сохранено.');
      }} catch (error) {{
        setCardStatus(card, 'error', error.message || String(error));
      }} finally {{
        if (!saved) button.disabled = false;
      }}
    }}

    async function runVisibleEnrichment(kind) {{
      const buttons = musicCards
        .filter(card => !card.hidden)
        .map(card => card.querySelector(`.enrichment-button[data-kind="${{kind}}"]`))
        .filter(button => button && !button.disabled);
      const label = kind === 'cover' ? '???????' : '???????';
      if (!buttons.length) {{
        operationStatus.textContent = `??? ?????? ${{label}} ??? ?????????? ?????? ? ??????? ???????.`;
        return;
      }}
      if (!window.confirm(`????????? ???????????????? ????? ${{label}} ??? ??????????????? ??????: ${{buttons.length}}? ??? ??????? ?????????? ???????? ??????????? ?????????????.`)) return;
      coverVisible.disabled = true;
      lyricsVisible.disabled = true;
      operationStatus.textContent = `??? ???????? ${{label}}. ??????: ${{buttons.length}}...`;
      try {{
        for (let index = 0; index < buttons.length; index += 1) {{
          operationStatus.textContent = `????? ${{label}}: ${{index + 1}} ?? ${{buttons.length}}.`;
          await searchAndSaveEnrichment(buttons[index]);
        }}
        operationStatus.textContent = `????? ${{label}} ????????. ?????????? ??????: ${{buttons.length}}.`;
      }} finally {{
        coverVisible.disabled = false;
        lyricsVisible.disabled = false;
      }}
    }}

    function setMusicActionDisabled(disabled, card = null) {{
      const buttons = card ? Array.from(card.querySelectorAll('.music-action-single')) : [
        ...musicCards.flatMap(item => Array.from(item.querySelectorAll('.music-action-single'))),
        tagVisible, shazamTagVisible, layoutVisible, coverVisible, lyricsVisible,
      ];
      buttons.forEach(button => {{
        const alreadyLayouted = button.dataset.action === 'layout' && button.closest('.music-card')?.dataset.layoutStatus === 'done';
        button.disabled = disabled || alreadyLayouted;
      }});
    }}

    function setCardStatus(card, state, message) {{
      if (!card) return;
      const status = card.querySelector('.music-card-status');
      const text = card.querySelector('.music-card-status-text');
      if (!status || !text) return;

      status.classList.remove('running', 'done', 'error');
      status.classList.add('visible');
      if (state) status.classList.add(state);
      text.textContent = message || '';
    }}

    function normalizePathForCompare(path) {{
      return String(path || '').replace(/\\//g, '\\\\').toLowerCase();
    }}

    function setDuplicateStatus(node, state, message) {{
      const comparison = node?.closest?.('.comparison') || node;
      if (!comparison) return;
      const status = comparison.querySelector('.duplicate-card-status');
      const text = comparison.querySelector('.duplicate-card-status-text');
      if (!status || !text) return;

      status.classList.remove('running', 'done', 'error');
      status.classList.add('visible');
      if (state) status.classList.add(state);
      text.textContent = message || '';
    }}

    function setDuplicateActionsDisabled(disabled) {{
      [...cards, ...musicCards].flatMap(card => Array.from(card.querySelectorAll('.quarantine-one, .trash-one'))).concat([rescanLibrary, findDuplicates]).filter(Boolean).forEach(button => {{
        button.disabled = disabled;
      }});
    }}

    function removeMusicCardsByPaths(paths) {{
      const normalized = new Set((paths || []).map(normalizePathForCompare));
      if (!normalized.size) return;
      musicCards = musicCards.filter(card => {{
        const remove = normalized.has(normalizePathForCompare(card.dataset.filePath || ''));
        if (remove) card.remove();
        return !remove;
      }});
      refreshMusicOverview();
      applyMusicFilters();
    }}

    function refreshGroupAfterComparisonRemoval(group) {{
      if (!group) return;
      const duplicates = Array.from(group.querySelectorAll('.duplicate-track.move'));
      if (!duplicates.length) {{
        group.remove();
        cards = cards.filter(card => card !== group);
        return;
      }}

      group.dataset.count = String(duplicates.length);
      group.dataset.search = [group.dataset.searchBase || '', ...Array.from(group.querySelectorAll('.duplicate-track'), track => track.dataset.search || '')].join(' ');
      group.querySelectorAll('.comparison').forEach(comparison => {{
        const advantages = new Set(Array.from(comparison.querySelectorAll('.duplicate-track.move')).flatMap(track => (track.dataset.referenceBetter || '').split(' ')));
        comparison.querySelectorAll('.keep td[data-quality]').forEach(cell => cell.classList.toggle('quality-better', advantages.has(cell.dataset.quality)));
      }});
      const subtitle = group.querySelector('.group-subtitle');
      if (subtitle) subtitle.textContent = group.dataset.reviewOnly === 'yes' ? `Возможный дубль · сравнений: ${{duplicates.length}}` : `Дублей: ${{duplicates.length}}`;
      ReportDuplicates.refresh(group);
    }}

    function removeDuplicateComparisonsByPaths(paths) {{
      const normalized = new Set((paths || []).map(normalizePathForCompare));
      if (!normalized.size) return;
      const groupsToRefresh = new Set();
      cards.flatMap(card => Array.from(card.querySelectorAll('.comparison'))).forEach(comparison => {{
        const kept = normalizePathForCompare(comparison.dataset.keptFile || '');
        const group = comparison.closest('.group-card');
        if (normalized.has(kept)) {{
          comparison.remove();
          groupsToRefresh.add(group);
        }} else {{
          comparison.querySelectorAll('.duplicate-track.move').forEach(track => {{
            if (normalized.has(normalizePathForCompare(track.dataset.filePath))) {{
              track.remove();
              groupsToRefresh.add(group);
            }}
          }});
          if (!comparison.querySelector('.duplicate-track.move')) comparison.remove();
        }}
      }});
      groupsToRefresh.forEach(refreshGroupAfterComparisonRemoval);
      applyDuplicateFilters(false);
      updateDuplicateSummaryCounts();
      document.getElementById('empty').classList.toggle('visible', cards.filter(card => !card.hidden).length === 0);
    }}

    function updateDuplicateSummaryCounts() {{
      const duplicateGroups = cards.filter(card => card.dataset.reviewOnly !== 'yes');
      const duplicates = duplicateGroups.reduce((count, card) => count + card.querySelectorAll('.duplicate-track.move').length, 0);
      const metrics = [
        [['duplicateMetric', 'duplicateFilesMetric', 'duplicatePageFilesMetric'], duplicates],
        [['duplicateGroupsMetric', 'duplicatePageGroupsMetric'], duplicateGroups.length],
        [['reviewGroupsMetric', 'reviewGroupsSummaryMetric', 'duplicatePageReviewMetric'], cards.length - duplicateGroups.length],
      ];
      metrics.forEach(([ids, count]) => {{
        const formatted = count.toLocaleString('ru-RU').replace(/\u00a0/g, ' ');
        ids.forEach(id => {{
          const target = document.getElementById(id);
          if (target) target.textContent = formatted;
        }});
      }});
    }}

    function tagText(tag) {{
      if (!tag || typeof tag !== 'object') return String(tag || '');
      const label = tag.label || '';
      const value = tag.value || '';
      return label && value ? `${{label}}: ${{value}}` : label || value;
    }}

    function updateCoverPreview(card, track) {{
      const cover = card.querySelector('.music-cover');
      if (!cover) return;

      const name = track.name || '';
      const coverDataUri = track.cover_data_uri || '';
      const coverUrl = track.cover_url || '';
      const coverSrc = coverDataUri || coverUrl;
      const hasCover = Boolean(track.has_cover || coverSrc);
      cover.classList.toggle('music-cover-has', hasCover);
      cover.classList.toggle('music-cover-empty', !coverSrc);
      cover.title = `Обложка: ${{hasCover ? 'есть' : 'нет'}}`;
      cover.setAttribute('aria-label', `Обложка: ${{hasCover ? 'есть' : 'нет'}}`);

      if (coverSrc) {{
        cover.innerHTML = '';
        const img = document.createElement('img');
        img.src = coverSrc;
        img.alt = `Обложка трека ${{name}}`;
        img.loading = 'lazy';
        cover.appendChild(img);
      }} else {{
        cover.innerHTML = '{lucide_icon("image-off", "empty-cover-icon")}';
      }}
    }}

    function updateMusicCardFromTrack(card, track) {{
      if (!card || !track) return;

      const previousPath = card.dataset.filePath;
      const path = track.path || '';
      const folder = track.folder || '';
      const name = track.name || '';
      const tags = Array.isArray(track.tags) ? track.tags : [];
      const values = kind => tags.filter(tag => tag && typeof tag === 'object' && tag.kind === kind)
        .map(tag => String(tag.value || '').trim()).filter(Boolean);
      const lyricsTitle = values('title').join(' · ');
      const lyricsArtist = (values('artist').length ? values('artist') : values('albumartist')).join(' · ');
      const trackTitle = lyricsTitle || name;
      const album = values('album').join(' · ');
      const tagValuesByKind = {{}};
      const tagSearchValues = [];

      card.dataset.filePath = path;
      card.dataset.sortName = trackTitle.toLowerCase();

      const title = card.querySelector('.music-title');
      const pathNode = card.querySelector('.music-path');
      musicCardByPath.delete(normalizePathForCompare(previousPath));
      musicCardByPath.set(normalizePathForCompare(path), card);
      const pills = card.querySelector('.music-pills');
      title.textContent = title.title = trackTitle;
      card.querySelectorAll('.music-track-artist, .music-track-artist-mobile').forEach(node => {{
        node.title = lyricsArtist;
        node.textContent = lyricsArtist || (node.classList.contains('music-track-artist') ? '—' : '');
      }});
      card.querySelectorAll('.music-track-album, .music-track-album-mobile').forEach(node => {{
        node.title = album;
        node.textContent = album || (node.classList.contains('music-track-album') ? '—' : '');
      }});
      const seconds = Number(track.duration);
      card.dataset.duration = seconds > 0 && Number.isFinite(seconds) ? seconds : 0;
      card.querySelector('.music-track-duration').textContent = seconds > 0 && Number.isFinite(seconds)
        ? formatAudioTime(seconds) : '—';
      if (Array.isArray(track.genres)) card.dataset.musicGenres = JSON.stringify(track.genres);
      const play = card.querySelector('.music-play');
      play.setAttribute('aria-label', play.title + ': ' + trackTitle);
      card.querySelector('.music-details-toggle').setAttribute('aria-label', 'Подробности: ' + trackTitle);
      pathNode.textContent = path || folder;
      updateCoverPreview(card, track);

      if (pills) {{
        pills.textContent = '';
        tags.forEach(tag => {{
          const kind = (tag && typeof tag === 'object' ? (tag.kind || 'tag') : 'tag')
            .toLowerCase()
            .replace(/[^a-z0-9_-]/g, '') || 'tag';
          const text = tagText(tag);
          tagSearchValues.push(text);
          if (!tagValuesByKind[kind]) tagValuesByKind[kind] = [];
          tagValuesByKind[kind].push(text);
          if (['title', 'artist', 'album'].includes(kind)) return;

          const pill = document.createElement('span');
          pill.className = `music-pill music-pill-${{kind}}`;
          if (kind === 'cover' || kind === 'lyrics') {{
            pill.dataset.present = String(tag?.value || '').trim().toLowerCase() === 'есть' ? 'yes' : 'no';
          }}
          pill.textContent = text;
          pills.appendChild(pill);
        }});
      }}

      card.dataset.sortArtist = lyricsArtist.toLowerCase();
      card.dataset.sortAlbum = album.toLowerCase();
      card.dataset.musicSearch = [name, folder, tagSearchValues.join(' ')].join(' ').toLowerCase();
      const layoutButton = card.querySelector('[data-action="layout"]');
      card.dataset.layoutStatus = layoutButton?.disabled ? 'done' : 'ready';
      const lyricsButton = card.querySelector('.lyrics-button');
      const hasLyrics = (tagValuesByKind.lyrics || []).join(' ').toLowerCase().includes('текст песни: есть');
      if (lyricsButton) {{
        lyricsButton.dataset.filePath = path;
        lyricsButton.dataset.trackName = name;
        lyricsButton.dataset.lyricsTitle = lyricsTitle;
        lyricsButton.dataset.lyricsArtist = lyricsArtist;
        lyricsButton.disabled = !hasLyrics;
        lyricsButton.setAttribute('aria-disabled', hasLyrics ? 'false' : 'true');
        lyricsButton.title = hasLyrics ? '' : 'Текст песни не найден';
      }}
      card.querySelectorAll('.enrichment-button').forEach(enrichmentButton => {{
        const enrichmentKind = enrichmentButton.dataset.kind || '';
        const alreadyPresent = enrichmentKind === 'cover' ? Boolean(track.has_cover) : hasLyrics;
        enrichmentButton.dataset.filePath = path;
        enrichmentButton.disabled = alreadyPresent;
        enrichmentButton.setAttribute('aria-disabled', alreadyPresent ? 'true' : 'false');
        enrichmentButton.title = alreadyPresent
          ? (enrichmentKind === 'cover' ? 'Обложка уже есть' : 'Текст уже есть')
          : '';
      }});
      card.querySelectorAll('.music-action-single, .trash-one').forEach(button => {{
        button.dataset.filePath = path;
      }});
      if (playback.matches(previousPath)) {{
        const current = trackForPath(path, card);
        if (normalizePathForCompare(previousPath) === normalizePathForCompare(path)) playback.refresh(current);
        else playback.select(current);
      }}
    }}

    async function runMusicOperation(action, files, scope, sourceButton = null) {{
      const mode = selectedMode();
      const uniqueFiles = Array.from(new Set((files || []).filter(Boolean)));
      const sourceCard = sourceButton?.closest('.music-card') || null;
      const useCardStatus = scope === 'single' && sourceCard;

      if (!uniqueFiles.length) {{
        const message = scope === 'single'
          ? 'Не удалось определить файл этой записи.'
          : 'Нет файлов для обработки по текущему фильтру.';
        if (useCardStatus) setCardStatus(sourceCard, 'error', message);
        else operationStatus.textContent = message;
        return;
      }}

      if (scope === 'single' && uniqueFiles.length !== 1) {{
        operationStatus.textContent = 'Ошибка: операция одной карточки получила больше одного файла.';
        return;
      }}

      let confirmationToken = '';
      if (action === 'shazam-tag') {{
        const approved = window.confirm('Для распознавания будет отправлен аудиоотпечаток в неофициальный Shazam. Продолжить?');
        if (!approved) return;
        confirmationToken = 'ALLOW_SHAZAM_LOOKUP';
      }}
      if (mode === 'real') {{
        const targetText = scope === 'single' ? 'одну выбранную запись' : `отфильтрованные записи: ${{uniqueFiles.length}}`;
        const question = action === 'shazam-tag'
          ? `Записать теги Shazam в: ${{targetText}}? Старые теги будут сохранены в журнале.`
          : `Запустить реальную обработку для: ${{targetText}}?`;
        if (!window.confirm(question)) return;
        if (action === 'shazam-tag') confirmationToken = 'APPLY_SHAZAM_TAGS';
        if (action === 'identity-correction') confirmationToken = 'APPLY_IDENTITY_CORRECTION';
      }}

      setMusicActionDisabled(true, useCardStatus ? sourceCard : null);
      if (useCardStatus) {{
        setCardStatus(sourceCard, 'running', `${{mode === 'dry-run' ? 'Проверяю' : 'Обрабатываю'}} файлов: ${{uniqueFiles.length}}...`);
      }} else {{
      operationStatus.textContent = `${{mode === 'dry-run' ? 'Проверяю' : 'Обрабатываю'}} файлов: ${{uniqueFiles.length}}...`;

      }}

      try {{
        const response = await fetch('/api/music-operation', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{ action, mode, scope, files: uniqueFiles, confirm: confirmationToken }}),
        }});

        const result = await response.json();
        const handleInCard = useCardStatus;
        if (response.ok && result.ok && handleInCard) {{
          const updatedTrack = result.track || result.refresh?.tracks?.[0] || null;
          if (updatedTrack) {{
            updateMusicCardFromTrack(sourceCard, updatedTrack);
            refreshMusicOverview();
          }}
          setCardStatus(sourceCard, 'done', result.message || 'Операция завершена.');
          applySort();
        }}
        if (!response.ok || !result.ok) throw new Error(result.error || 'Команда не выполнена');

        operationStatus.textContent = result.message || 'Операция завершена.';
        if (mode === 'real' && result.reload) setTimeout(() => window.location.reload(), 900);
      }} catch (error) {{
        if (useCardStatus) setCardStatus(sourceCard, 'error', error.message || String(error));
        operationStatus.textContent = error.message || String(error);
      }} finally {{
        setMusicActionDisabled(false, useCardStatus ? sourceCard : null);
      }}
    }}

    function applySort() {{
      const numeric = musicSortKey === 'number' || musicSortKey === 'duration';
      const sortValue = card => {{
        if (musicSortKey === 'duration') return Number(card.dataset.duration);
        const value = card.getAttribute(`data-sort-${{musicSortKey}}`);
        return numeric ? Number(value) : value;
      }};
      musicCards.sort((a, b) => {{
        const left = sortValue(a);
        const right = sortValue(b);
        if (Boolean(left) !== Boolean(right)) return left ? -1 : 1;
        const comparison = numeric ? left - right : musicCollator.compare(left, right);
        return comparison * musicSortDirection || musicCollator.compare(a.dataset.sortName, b.dataset.sortName);
      }});
      musicSortButtons.forEach(button => {{
        const header = button.closest('th');
        if (button.dataset.musicSort === musicSortKey) {{
          header.setAttribute('aria-sort', musicSortDirection === 1 ? 'ascending' : 'descending');
        }} else {{
          header.removeAttribute('aria-sort');
        }}
      }});
      applyMusicFilters();
    }}

    function updateSearchPlaceholder(input = musicSearch) {{
      const searchControl = input.closest('.search-control');
      if (!searchControl) return;
      searchControl.classList.toggle('is-empty', input.value.length === 0);
    }}

    function musicGenreKey(genre) {{
      return genre.toLowerCase().replaceAll('ё', 'е').trim().replace(/\\s+/g, ' ');
    }}

    function musicGenresForCard(card) {{
      return new Map(JSON.parse(card.dataset.musicGenres).map(genre => [musicGenreKey(genre), genre]));
    }}

    function updateMusicGenreArrows() {{
      const {{ scrollLeft, scrollWidth, clientWidth }} = musicGenreFilters;
      const focused = document.activeElement;
      musicGenrePrevious.hidden = scrollLeft <= 1;
      musicGenreNext.hidden = scrollWidth - clientWidth - scrollLeft <= 1;
      if (focused === musicGenrePrevious && musicGenrePrevious.hidden && !musicGenreNext.hidden) {{
        musicGenreNext.focus();
      }} else if (focused === musicGenreNext && musicGenreNext.hidden && !musicGenrePrevious.hidden) {{
        musicGenrePrevious.focus();
      }}
    }}

    function turnMusicGenrePage(direction) {{
      const rail = musicGenreFilters;
      const edgeSpace = parseFloat(getComputedStyle(rail).scrollPaddingInlineStart);
      const pageWidth = Math.max(1, rail.clientWidth - 2 * edgeSpace);
      rail.scrollBy({{ left: direction * pageWidth }});
    }}

    function refreshMusicOverview() {{
      const genres = new Map();
      let seconds = 0;
      let withDuration = 0;
      musicCards.forEach(card => {{
        const duration = Number(card.dataset.duration);
        if (duration > 0) {{
          seconds += duration;
          withDuration += 1;
        }}
        musicGenresForCard(card).forEach((label, key) => {{
          if (!genres.has(key)) genres.set(key, {{ label, count: 0 }});
          genres.get(key).count += 1;
        }});
      }});

      const total = musicCards.length;
      const units = {{ one: 'трек', few: 'трека', many: 'треков', other: 'треков' }};
      let summary = `${{musicNumber.format(total)}} ${{units[musicPlural.select(total)]}}`;
      if (withDuration) {{
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor(seconds / 60) % 60;
        const time = hours ? `${{musicNumber.format(hours)}} ч. ${{minutes}} мин.`
          : minutes ? `${{minutes}} мин. ${{Math.floor(seconds % 60)}} сек.`
          : `${{Math.floor(seconds)}} сек.`;
        summary += ` · ${{time}}`;
        if (withDuration < total) summary += ` (для ${{musicNumber.format(withDuration)}} из ${{musicNumber.format(total)}})`;
      }} else if (total) {{
        summary += ' · длительность неизвестна';
      }}
      musicSummary.textContent = summary;

      if (!genres.has(musicGenre)) musicGenre = '';
      const sortedGenres = [...genres.entries()].sort(([, a], [, b]) =>
        b.count - a.count || musicCollator.compare(a.label, b.label));
      musicGenrePagination.hidden = !sortedGenres.length;
      musicGenreFilters.replaceChildren(...[['', {{ label: 'Все жанры' }}], ...sortedGenres].map(([key, genre]) => {{
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'music-genre';
        button.dataset.musicGenre = key;
        button.textContent = genre.label;
        button.setAttribute('aria-pressed', String(key === musicGenre));
        return button;
      }}));
      updateMusicGenreArrows();
    }}

    function applyMusicFilters() {{
      updateSearchPlaceholder();
      const value = musicSearch.value.trim().toLowerCase();
      let visibleCount = 0;
      musicCards.forEach(card => {{
        const matchesText = !value || card.dataset.musicSearch.includes(value);
        const matchesGenre = !musicGenre || musicGenresForCard(card).has(musicGenre);
        const visible = matchesText && matchesGenre;
        card.hidden = !visible;
        if (visible) visibleCount += 1;
      }});
      musicEmpty.classList.toggle('visible', visibleCount === 0);
      musicList.hidden = visibleCount === 0;
      musicPager.setItems(musicCards.filter(card => !card.hidden));
      if (playbackContext === 'music') updatePlaybackQueue();
    }}

    function applyDuplicateFilters(reset = true) {{
      updateSearchPlaceholder(duplicateSearch);
      const value = duplicateSearch.value.trim().toLowerCase();
      cards.forEach(card => {{
        const review = card.dataset.reviewOnly === 'yes';
        const statusMatches = duplicateFilter.value === 'all' || (duplicateFilter.value === 'review' ? review : !review);
        card.hidden = !statusMatches || (!!value && !(card.dataset.search || '').includes(value));
      }});
      const matches = cards.filter(card => !card.hidden);
      document.getElementById('empty').classList.toggle('visible', matches.length === 0);
      document.getElementById('empty').textContent = cards.length ? 'Нет групп по текущему поиску и фильтру.' : 'Дубли не найдены.';
      duplicatePager.setItems(matches, reset);
      if (playbackContext === 'duplicates') updatePlaybackQueue();
    }}

    function audioPath(player) {{
      try {{
        return new URL(player.currentSrc || player.src, window.location.href).searchParams.get('file') || '';
      }} catch (_error) {{
        return '';
      }}
    }}

    async function releaseAudioStreams(filePath = '') {{
      const wanted = normalizePathForCompare(filePath);
      if (!wanted || playback.matches(filePath)) playback.clear();
      // Chromium aborts the range request asynchronously; let the server close its handle.
      await new Promise(resolve => setTimeout(resolve, 250));
    }}

    function canMoveFile(button) {{
      if (selectedMode() === 'real') return true;
      const message = 'Включите «Применить изменения», чтобы переместить файл.';
      const musicCard = button.closest('.music-card');
      if (musicCard) setCardStatus(musicCard, 'error', message);
      else setDuplicateStatus(button, 'error', message);
      return false;
    }}

    function refreshAfterFileMove(result, paths) {{
      if (result.reload) {{
        try {{
          sessionStorage.setItem('duplicateViewAfterMove', JSON.stringify({{
            query: duplicateSearch.value,
            filter: duplicateFilter.value,
            limit: duplicatePager.limit,
            open: cards.filter(card => card.open).map(card => card.dataset.groupName),
          }}));
        }} catch (error) {{
          // The updated report can still be loaded when session storage is unavailable.
        }}
        window.location.reload();
        return;
      }}
      removeDuplicateComparisonsByPaths(paths);
      removeMusicCardsByPaths(paths);
    }}

    function restoreDuplicateViewAfterMove() {{
      try {{
        const state = JSON.parse(sessionStorage.getItem('duplicateViewAfterMove') || 'null');
        if (!state) return;
        sessionStorage.removeItem('duplicateViewAfterMove');
        duplicateSearch.value = state.query;
        duplicateFilter.value = state.filter;
        duplicatePager.limit = state.limit;
        const expanded = new Set(state.open);
        cards.forEach(card => {{ card.open = expanded.has(card.dataset.groupName); }});
        applyDuplicateFilters(false);
      }} catch (error) {{
        // The report can be opened from disk without session storage.
      }}
    }}

    async function runQuarantine(url, body, message, sourceButton = null) {{
      const sourceComparison = sourceButton?.closest?.('.comparison') || null;
      quarantinePanel.classList.add('visible');
      quarantineStatus.textContent = message;
      copyStatus.textContent = '';
      globalProgress.classList.add('visible');
      setDuplicateActionsDisabled(true);
      if (sourceComparison) setDuplicateStatus(sourceComparison, 'running', message);
      try {{
        await releaseAudioStreams(body?.file || '');
        const response = await fetch(url, {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: body ? JSON.stringify(body) : null,
        }});
        const result = await response.json();
        if (!response.ok || !result.ok) throw new Error(result.error || 'Команда не выполнена');
        const changedPaths = result.moved_paths || (result.moved ? result.moved.map(item => item.source) : []);
        refreshAfterFileMove(result, changedPaths);
        quarantineStatus.textContent = 'Готово. Файлы перенесены в карантин, отчёт обновлён.';
        if (sourceComparison && sourceComparison.isConnected) setDuplicateStatus(sourceComparison, 'done', 'Файл перенесён в карантин.');
      }} catch (error) {{
        quarantineStatus.textContent = 'Не удалось выполнить перенос автоматически.';
        copyStatus.textContent = error.message || String(error);
        if (sourceComparison) setDuplicateStatus(sourceComparison, 'error', error.message || String(error));
      }} finally {{
        globalProgress.classList.remove('visible');
        setDuplicateActionsDisabled(false);
      }}
    }}

    async function runTrash(filePath, sourceButton) {{
      const sourceMusicCard = sourceButton?.closest?.('.music-card') || null;
      const sourceComparison = sourceButton?.closest?.('.comparison') || null;
      if (!filePath || !canMoveFile(sourceButton)) return;

      const confirmed = window.confirm('Переместить выбранный файл в корзину Trash? Файл не будет удалён безвозвратно.');
      if (!confirmed) return;

      quarantinePanel.classList.add('visible');
      quarantineStatus.textContent = 'Перемещаю выбранный файл в корзину...';
      copyStatus.textContent = '';
      globalProgress.classList.add('visible');
      setDuplicateActionsDisabled(true);
      if (sourceMusicCard) {{
        setMusicActionDisabled(true, sourceMusicCard);
        setCardStatus(sourceMusicCard, 'running', 'Перемещаю файл в корзину...');
      }}
      if (sourceComparison) setDuplicateStatus(sourceComparison, 'running', 'Перемещаю файл в корзину...');

      try {{
        await releaseAudioStreams(filePath);
        const response = await fetch('/api/trash-file', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{ file: filePath, mode: 'real', confirm: 'MOVE_TO_TRASH' }}),
        }});
        const result = await response.json();
        if (!response.ok || !result.ok) throw new Error(result.error || 'Команда не выполнена');
        const changedPaths = result.moved_paths || [result.source || filePath];
        refreshAfterFileMove(result, changedPaths);
        quarantineStatus.textContent = 'Готово. Файл перенесён в корзину Trash, отчёт обновлён.';
        if (sourceMusicCard && sourceMusicCard.isConnected) setCardStatus(sourceMusicCard, 'done', 'Файл перенесён в корзину.');
        if (sourceComparison && sourceComparison.isConnected) setDuplicateStatus(sourceComparison, 'done', 'Файл перенесён в корзину.');
      }} catch (error) {{
        quarantineStatus.textContent = 'Не удалось переместить файл в корзину.';
        copyStatus.textContent = error.message || String(error);
        if (sourceMusicCard) setCardStatus(sourceMusicCard, 'error', error.message || String(error));
        if (sourceComparison) setDuplicateStatus(sourceComparison, 'error', error.message || String(error));
      }} finally {{
        globalProgress.classList.remove('visible');
        setDuplicateActionsDisabled(false);
        if (sourceMusicCard) setMusicActionDisabled(false, sourceMusicCard);
      }}
    }}

    async function rescanCurrentLibrary(source = 'library') {{
      const confirmed = window.confirm('Пересканировать библиотеку и заново собрать отчёт по дублям? Файлы не будут перемещаться.');
      if (!confirmed) return;

      const fromDuplicates = source === 'duplicates';
      const statusPanel = fromDuplicates ? duplicateScanPanel : scanPanel;
      const statusText = fromDuplicates ? duplicateScanStatus : scanStatus;
      const copyText = fromDuplicates ? duplicateScanCopyStatus : scanCopyStatus;
      const progressPanel = fromDuplicates ? duplicateScanProgress : scanProgress;
      const progress = ReportScanProgress.create(progressPanel);
      const progressId = ReportScanProgress.newId();
      statusPanel.classList.add('visible');
      statusText.textContent = fromDuplicates ? 'Идёт поиск дублей по всей библиотеке…' : 'Сканирование библиотеки…';
      copyText.textContent = '';
      progressPanel.hidden = false;
      progress.show({{stage: 'starting'}});
      setDuplicateActionsDisabled(true);
      const stopProgress = progress.watch('/api/rescan-library/progress', progressId);
      try {{
        const response = await fetch('/api/rescan-library', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{confirm: 'RESCAN_LIBRARY', progress_id: progressId}}),
        }});
        const result = await response.json();
        if (!response.ok || !result.ok) throw new Error(result.error || 'Команда не выполнена');
        stopProgress();
        progress.show({{stage: 'completed', processed: 1, total: 1}});
        statusText.textContent = 'Отчёт обновлён. Открываю результаты…';
        setTimeout(() => window.location.reload(), 500);
      }} catch (error) {{
        stopProgress();
        progress.show({{stage: 'failed'}});
        statusText.textContent = 'Не удалось пересканировать библиотеку.';
        copyText.textContent = error.message || String(error);
        setDuplicateActionsDisabled(false);
      }}
    }}

    function formatAudioTime(seconds) {{
      if (!Number.isFinite(seconds) || seconds < 0) return '0:00';
      const minutes = Math.floor(seconds / 60);
      const rest = Math.floor(seconds % 60).toString().padStart(2, '0');
      if (minutes >= 60) return `${{Math.floor(minutes / 60)}}:${{String(minutes % 60).padStart(2, '0')}}:${{rest}}`;
      return `${{minutes}}:${{rest}}`;
    }}

    async function toggleAudioPlayback(player, playButton, status, signal) {{
      if (signal?.aborted) return;
      status.hidden = true;
      status.textContent = '';
      if (!player.paused) {{
        player.pause();
        return;
      }}
      try {{
        // Cards start in an inert template. Select the source in the active
        // document before first play, or retry after a previous load error.
        if (!player.currentSrc || player.error) player.load();
        const cancelPlay = () => player.pause();
        signal?.addEventListener('abort', cancelPlay, {{once: true}});
        try {{ await player.play(); }}
        finally {{ signal?.removeEventListener('abort', cancelPlay); }}
      }} catch (error) {{
        if (signal?.aborted || error.name === 'AbortError') return;
        playButton.classList.remove('playing');
        status.textContent = 'Не удалось воспроизвести трек. Попробуйте ещё раз.';
        status.hidden = false;
      }}
    }}

    async function seekAudioPlayback(player, seconds, status, signal) {{
      if (signal?.aborted || !Number.isFinite(seconds)) return false;
      status.hidden = true;
      status.textContent = '';
      try {{
        if (player.readyState < 1 || player.error) {{
          await new Promise((resolve, reject) => {{
            let timer;
            const cleanup = () => {{
              clearTimeout(timer);
              player.removeEventListener('loadedmetadata', ready);
              player.removeEventListener('error', failed);
              signal?.removeEventListener('abort', cancelled);
            }};
            const ready = () => {{ cleanup(); resolve(); }};
            const failed = () => {{ cleanup(); reject(new Error('Audio metadata unavailable')); }};
            const cancelled = () => {{ cleanup(); reject(Object.assign(new Error('Cancelled'), {{name: 'AbortError'}})); }};
            player.addEventListener('loadedmetadata', ready, {{once: true}});
            player.addEventListener('error', failed, {{once: true}});
            signal?.addEventListener('abort', cancelled, {{once: true}});
            timer = setTimeout(failed, 15000);
            try {{
              player.preload = 'metadata';
              player.load();
            }} catch (error) {{ cleanup(); reject(error); }}
          }});
        }}
        if (signal?.aborted) return false;
        const limit = Number.isFinite(player.duration) ? Math.max(0, player.duration - .01) : seconds;
        player.currentTime = Math.max(0, Math.min(seconds, limit));
        const cancelPlay = () => player.pause();
        signal?.addEventListener('abort', cancelPlay, {{once: true}});
        try {{ await player.play(); }}
        finally {{ signal?.removeEventListener('abort', cancelPlay); }}
        return !signal?.aborted;
      }} catch (error) {{
        if (signal?.aborted || error.name === 'AbortError') return false;
        status.textContent = 'Не удалось перейти к строке песни. Попробуйте ещё раз.';
        status.hidden = false;
        return false;
      }}
    }}

    function bindCardControls(root) {{
      const alreadyBound = boundCards.has(root);
      if (!alreadyBound && root.matches('.group-card')) ReportDuplicates.refresh(root);
      const playable = root.matches('.music-card, .duplicate-track') ? [root] : Array.from(root.querySelectorAll('.duplicate-track'));
      playable.forEach(updatePlayingCard);
      if (alreadyBound) return;
      boundCards.add(root);
    playable.forEach(card => {{
      const activate = () => {{
        playbackContext = card.matches('.duplicate-track') ? 'duplicates' : 'music';
        updatePlaybackQueue();
        playback.toggle(trackForPath(card.dataset.filePath, card));
      }};
      const musicPlay = card.querySelector('.music-play');
      if (musicPlay) {{
        musicPlay.addEventListener('click', activate);
        const toggle = card.querySelector('.music-details-toggle');
        const details = card.querySelector('.music-track-details');
        toggle.addEventListener('click', () => {{
          details.hidden = !details.hidden;
          toggle.setAttribute('aria-expanded', String(!details.hidden));
        }});
        return;
      }}
      card.addEventListener('click', event => {{
        if (event.target.closest('button, a, input, select, textarea, summary, [contenteditable="true"]')) return;
        const selection = window.getSelection();
        if (selection && !selection.isCollapsed) return;
        activate();
      }});
      card.addEventListener('keydown', event => {{
        if (event.target !== card || !['Enter', ' '].includes(event.key)) return;
        event.preventDefault();
        activate();
      }});
      card.querySelector('.duplicate-listen')?.addEventListener('click', activate);
    }});

    root.querySelectorAll('.quarantine-one').forEach(button => {{
      button.addEventListener('click', event => {{
        event.stopPropagation();
        if (!canMoveFile(button)) return;
        const confirmed = window.confirm('Переместить выбранный файл в карантин? Файл не удаляется.');
        if (!confirmed) return;
        runQuarantine(
          '/api/quarantine-one',
          {{ file: button.dataset.file, mode: 'real', confirm: 'MOVE_TO_QUARANTINE' }},
          'Переношу выбранный файл в карантин...',
          button
        );
      }});
    }});
    root.querySelectorAll('.music-action-single').forEach(button => {{
      button.addEventListener('click', event => {{
        event.preventDefault();
        event.stopPropagation();
        runMusicOperation(button.dataset.action, [singleMusicPath(button)], 'single', button);
      }});
    }});
    root.querySelectorAll('.trash-one').forEach(button => {{
      button.addEventListener('click', event => {{
        event.preventDefault();
        event.stopPropagation();
        runTrash(button.dataset.filePath, button);
      }});
    }});
    root.querySelectorAll('.lyrics-button').forEach(button => {{
      button.addEventListener('click', event => {{
        event.preventDefault();
        event.stopPropagation();
        openLyricsModal(button);
      }});
    }});
    root.querySelectorAll('.enrichment-button').forEach(button => {{
      button.addEventListener('click', event => {{
        event.preventDefault();
        event.stopPropagation();
        searchAndSaveEnrichment(button);
      }});
    }});
    }}
    if (lyricsClose) lyricsClose.addEventListener('click', closeLyricsModal);
    lyricsReading.addEventListener('click', () => setLyricsView(false));
    lyricsOriginal.addEventListener('click', () => setLyricsView(true));
    lyricsFollow.addEventListener('click', () => lyricsSync.setFollow(!lyricsSync.follow));
    if (lyricsModal) {{
      lyricsModal.addEventListener('click', event => {{
        if (event.target === lyricsModal) closeLyricsModal();
      }});
    }}
    document.addEventListener('keydown', event => {{
      if (event.key === 'Escape') closeLyricsModal();
    }});

    tagVisible.addEventListener('click', () => runMusicOperation('tag', visibleMusicPaths(), 'filtered'));
    shazamTagVisible.addEventListener('click', () => runMusicOperation('shazam-tag', visibleMusicPaths(), 'filtered'));
    layoutVisible.addEventListener('click', () => runMusicOperation('layout', visibleMusicPaths(), 'filtered'));
    coverVisible.addEventListener('click', () => runVisibleEnrichment('cover'));
    lyricsVisible.addEventListener('click', () => runVisibleEnrichment('lyrics'));
    if (rescanLibrary) {{
      rescanLibrary.addEventListener('click', () => rescanCurrentLibrary('library'));
    }}
    if (findDuplicates) {{
      findDuplicates.addEventListener('click', () => rescanCurrentLibrary('duplicates'));
    }}

    processingModeNote.addEventListener('click', toggleProcessingMode);
    updateOperationStatus();
    musicSearch.addEventListener('input', () => {{
      updateSearchPlaceholder();
      applyMusicFilters();
    }});
    musicGenreFilters.addEventListener('click', event => {{
      const button = event.target.closest('.music-genre');
      if (!button) return;
      const key = button.dataset.musicGenre;
      musicGenre = key === musicGenre ? '' : key;
      for (const chip of musicGenreFilters.children) {{
        chip.setAttribute('aria-pressed', String(chip.dataset.musicGenre === musicGenre));
      }}
      applyMusicFilters();
    }});
    musicGenrePrevious.addEventListener('click', () => turnMusicGenrePage(-1));
    musicGenreNext.addEventListener('click', () => turnMusicGenrePage(1));
    musicGenreFilters.addEventListener('scroll', updateMusicGenreArrows, {{ passive: true }});
    new ResizeObserver(updateMusicGenreArrows).observe(musicGenreFilters);
    duplicateSearch.addEventListener('input', () => applyDuplicateFilters());
    duplicateFilter.addEventListener('change', () => applyDuplicateFilters());
    musicSortButtons.forEach(button => {{
      button.addEventListener('click', () => {{
        const key = button.dataset.musicSort;
        musicSortDirection = key === musicSortKey ? -musicSortDirection : 1;
        musicSortKey = key;
        applySort();
      }});
    }});
    refreshMusicOverview();
    applySort();
    restoreDuplicateViewAfterMove();
    activatePage(window.location.hash.slice(1) || 'overview');
  </script>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True, help="Duplicate CSV report")
    parser.add_argument("--review-csv", help="CSV with possible duplicates that require review")
    parser.add_argument("--library", help="Music library folder for full analysis")
    parser.add_argument("--identity-report", default="reports/audio_identity.json", help="Cached AcoustID comparison JSON")
    parser.add_argument("--out", default="reports/library.html", help="Output HTML file")
    parser.add_argument("--progress", action="store_true", help="Emit live scan counters")
    args = parser.parse_args()

    csv_path = Path(args.csv).expanduser().resolve()
    review_csv_path = (
        Path(args.review_csv).expanduser().resolve()
        if args.review_csv
        else csv_path.with_name(f"{csv_path.stem}_needs_review{csv_path.suffix}")
    )
    library_path = Path(args.library).expanduser().resolve() if args.library else None
    out_path = Path(args.out).expanduser().resolve()

    if not csv_path.exists():
        raise SystemExit(f"CSV report does not exist: {csv_path}")

    rows = read_rows(csv_path)
    review_rows = read_review_rows(review_csv_path)
    identity_report_path = Path(args.identity_report).expanduser().resolve() if args.identity_report else None
    progress = ProgressWriter() if args.progress else None
    library_stats = analyze_library(library_path, identity_report_path, progress)
    payload = build_payload(rows, library_stats, review_rows)
    if progress:
        progress({"stage": "render", "processed": 0, "total": None, "current": ""})
    html_doc = render_html(payload)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html_doc, encoding="utf-8")

    print(f"HTML report written: {out_path}")
    print(f"Total files: {library_stats['total_files']}")
    print(f"Albums: {library_stats['albums']}")
    print(f"Artists: {library_stats['artists']}")
    print(f"Duplicate groups: {payload['summary']['groups']}")
    print(f"Duplicate files: {payload['summary']['duplicates']}")
    print(f"Needs-review groups: {payload['summary']['review_groups']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
