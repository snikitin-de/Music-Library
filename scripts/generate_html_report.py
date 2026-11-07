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
from report_assets import ICON_LICENSE_NOTICE


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

GENRE_SPLIT_RE = re.compile(r"\s*(?:,|;|/|\|)\s*")

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
    genres = []
    for item in GENRE_SPLIT_RE.split(value or ""):
        genre = clean_tag_value(item)
        if genre:
            genres.append(genre)
    return genres


def collect_genres_from_tracks(tracks: list[dict]) -> dict[str, int]:
    genres: Counter[str] = Counter()
    display_names: dict[str, str] = {}

    for track in tracks:
        for tag in track.get("tags", []):
            if not isinstance(tag, dict) or tag.get("kind") != "genre":
                continue
            for genre in split_genres(tag.get("value", "")):
                key = normalize(genre)
                if not key:
                    continue
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
        for genre in genre_values:
            key = normalize(genre)
            if not key:
                continue
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


def analyze_library(library: Path | None, identity_report: Path | None = None) -> dict:
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

    for scan_root in scan_roots:
        for path in scan_root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in AUDIO_EXTENSIONS:
                continue

            try:
                first_relative_part = path.relative_to(library).parts[0].casefold()
            except (ValueError, IndexError):
                first_relative_part = ""
            if first_relative_part in MANAGED_STORAGE_FOLDERS:
                continue

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


def safe_int(value: str | None) -> int:
    if not value:
        return 0
    try:
        return int(float(value))
    except ValueError:
        return 0


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


def format_size(value: str | None) -> str:
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


def render_quality(
    quality: dict[str, str],
    has_cover_override: bool | None = None,
    has_lyrics_override: bool | None = None,
) -> str:
    fmt = html.escape(quality.get("format", "—").upper() or "—")
    bit_depth = html.escape(quality.get("bit_depth", "—") or "—")
    tag_score = html.escape(quality.get("tag_score", "—") or "—")
    has_cover = quality.get("cover", "").lower() == "true" if has_cover_override is None else has_cover_override
    cover = "Да" if has_cover else "Нет"
    has_lyrics = quality.get("lyrics", "").lower() == "true" if has_lyrics_override is None else has_lyrics_override
    lyrics = "Да" if has_lyrics else "Нет"

    items = [
        ("Формат", fmt),
        ("Битрейт", html.escape(format_bitrate(quality.get("bitrate")))),
        ("Разрядность", bit_depth),
        ("Частота дискретизации", html.escape(format_sample_rate(quality.get("sample_rate")))),
        ("Теги", f"{tag_score}/5"),
        ("Обложка", cover),
        ("Текст песни", lyrics),
        ("Размер", html.escape(format_size(quality.get("size")))),
    ]

    return '<div class="quality-grid">' + "".join(
        f"<div><span>{label}</span><strong>{value}</strong></div>" for label, value in items
    ) + "</div>"


def audio_player(file_path: str, label: str) -> str:
    if not file_path:
        return ""

    src = f"/api/audio?file={quote(file_path, safe='')}"
    escaped_label = html.escape(label)
    return (
        '<div class="audio-player-wrap">'
        '<div class="custom-audio-player">'
        f'<audio class="audio-player" preload="none" src="{html.escape(src)}">'
        f"{escaped_label}"
        "</audio>"
        f'<button class="audio-play" type="button" aria-label="{escaped_label}">'
        f'{lucide_icon("play", "audio-play-icon")}'
        "</button>"
        '<div class="audio-time audio-current">0:00</div>'
        '<div class="audio-seek-wrap">'
        '<div class="audio-seek-track"><span class="audio-seek-fill"></span></div>'
        '<input class="audio-seek" type="range" min="0" max="1000" value="0" step="1" aria-label="Позиция воспроизведения">'
        "</div>"
        '<button class="audio-mute" type="button" aria-label="Выключить звук">'
        f'{lucide_icon("volume", "audio-volume-icon audio-volume-on")}'
        f'{lucide_icon("volume-x", "audio-volume-icon audio-volume-off")}'
        "</button>"
        "</div>"
        "</div>"
    )


def cover_preview(track: dict) -> str:
    cover_data_uri = str(track.get("cover_data_uri") or "")
    cover_url = str(track.get("cover_url") or "")
    cover_src = cover_data_uri or cover_url
    has_cover = bool(track.get("has_cover")) or bool(cover_src)
    cover_state = "есть" if has_cover else "нет"
    if cover_src:
        return (
            '<div class="music-cover music-cover-has" title="Обложка: есть">'
            f'<img src="{html.escape(cover_src)}" alt="Обложка трека {html.escape(track.get("name", ""))}" loading="lazy">'
            "</div>"
        )
    return (
        '<div class="music-cover music-cover-empty" title="Обложка: нет" aria-label="Обложка: нет">'
        f'{lucide_icon("image-off", "empty-cover-icon")}'
        f'<strong>{cover_state}</strong>'
        "</div>"
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
    return "".join(parts)


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
    return "".join(parts)


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
            and str(tag.get("value", "")).strip()
            for tag in track.get("tags", [])
        )
        if has_genre:
            with_genre += 1
    return with_genre, max(0, total - with_genre)


def render_genre_bars(genres: dict, tracks: list[dict] | None = None) -> str:
    if not genres:
        return '<div class="format-empty">Жанры не определены.</div>'

    def polar_point(radius: float, angle: float) -> tuple[float, float]:
        radians = math.radians(angle)
        return (50 + radius * math.cos(radians), 50 + radius * math.sin(radians))

    def donut_slice_path(start_percent: float, end_percent: float) -> str:
        outer_radius = 46
        inner_radius = 25
        start_angle = -90 + start_percent * 3.6
        end_angle = -90 + end_percent * 3.6
        large_arc = 1 if end_percent - start_percent > 50 else 0
        outer_start = polar_point(outer_radius, start_angle)
        outer_end = polar_point(outer_radius, end_angle)
        inner_end = polar_point(inner_radius, end_angle)
        inner_start = polar_point(inner_radius, start_angle)
        return (
            f"M {outer_start[0]:.3f} {outer_start[1]:.3f} "
            f"A {outer_radius} {outer_radius} 0 {large_arc} 1 {outer_end[0]:.3f} {outer_end[1]:.3f} "
            f"L {inner_end[0]:.3f} {inner_end[1]:.3f} "
            f"A {inner_radius} {inner_radius} 0 {large_arc} 0 {inner_start[0]:.3f} {inner_start[1]:.3f} "
            "Z"
        )

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
            end = start + percent
            svg_segments.append(
                f'<path class="donut-segment" d="{donut_slice_path(start, end)}" fill="{color}" />'
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
            f'Жанры указаны у <strong>{format_number(with_genre)}</strong> из '
            f'<strong>{len(tracks)}</strong> файлов. '
            f'Без жанра: <strong>{format_number(without_genre)}</strong>.'
            '</p>'
        )
    return f"""
    {coverage}
    <div class="donut-layout">
      <div class="donut-chart">
        <svg class="donut-svg" viewBox="0 0 100 100" aria-hidden="true">
          {"".join(svg_segments)}
        </svg>
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

    peak_year, peak_count = max(all_year_items, key=lambda item: item[1])
    return f"""
    <p class="chart-note">
      Самый музыкальный год: <strong>{html.escape(str(peak_year))}</strong>,
      <strong>{format_number(peak_count)}</strong> файлов.
    </p>
    <div class="year-chart" role="img" aria-label="Эпохи по количеству файлов">
      {"".join(bars)}
    </div>
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

    return f"""
    <section class="panel heatmap-panel">
      <div class="heatmap-heading">
        <div>
          <h2>Тепловая карта: эпоха × жанр</h2>
          <p>Количество треков</p>
        </div>
      </div>
      <div class="heatmap-scroll">
        <div class="heatmap-grid" style="--heatmap-columns: {len(columns)};">
          <div class="heatmap-corner"></div>
          {header}
          {"".join(body_rows)}
        </div>
      </div>
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
    if not tracks:
        return '<div class="empty visible">Музыкальные файлы не найдены.</div>'

    duplicate_paths = duplicate_paths or set()
    items = []
    for track in tracks:
        tag_search_values = []
        tag_values_by_kind = defaultdict(list)
        tag_parts = []
        for tag in track.get("tags", []):
            if isinstance(tag, dict):
                label = tag.get("label", "")
                value = tag.get("value", "")
                kind = re.sub(r"[^a-z0-9_-]", "", tag.get("kind", "tag").lower()) or "tag"
                text = f"{label}: {value}" if value else label
                tag_search_values.append(text)
                tag_values_by_kind[kind].append(text)
                tag_parts.append(
                    f'<span class="music-pill music-pill-{html.escape(kind)}">{html.escape(text)}</span>'
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
        tag_attributes = " ".join(
            f'data-tag-{html.escape(kind)}="{html.escape(" ".join(values).lower())}"'
            for kind, values in sorted(tag_values_by_kind.items())
        )
        sort_artist = " ".join(tag_values_by_kind.get("artist", []) or tag_values_by_kind.get("albumartist", [])).lower()
        sort_album = " ".join(tag_values_by_kind.get("album", [])).lower()
        sort_year = " ".join(tag_values_by_kind.get("year", [])).lower()
        sort_format = " ".join(tag_values_by_kind.get("format", [])).lower()
        status_text = " ".join(tag_values_by_kind.get("status", [])).lower()
        card_classes = ["music-card"]
        identity_mismatch = bool(track.get("identity_mismatch"))
        identity = track.get("identity") or {}
        if identity_mismatch:
            card_classes.append("music-card-identity-mismatch")
        if track.get("path", "") in duplicate_paths:
            card_classes.append("music-card-duplicate")
        if "не читается" in status_text or "не распознан" in status_text:
            card_classes.append("music-card-unreadable")
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
        cover_search_disabled = ' disabled aria-disabled="true" title="Обложка уже есть"' if has_cover else ""
        lyrics_search_disabled = ' disabled aria-disabled="true" title="Текст уже есть"' if has_lyrics else ""
        player_html = audio_player(track.get("path", ""), f'Прослушать {track.get("name", "")}')
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
        items.append(
            f"""
            <article class="{html.escape(" ".join(card_classes))}" data-file-path="{html.escape(track.get("path", ""))}" data-layout-status="{layout_status}" data-identity-mismatch="{'yes' if identity_mismatch else 'no'}" data-music-search="{html.escape(search_text)}" data-sort-name="{html.escape(track.get("name", "").lower())}" data-sort-artist="{html.escape(sort_artist)}" data-sort-album="{html.escape(sort_album)}" data-sort-year="{html.escape(sort_year)}" data-sort-format="{html.escape(sort_format)}" {tag_attributes}>
              <button class="music-trash-icon trash-one" type="button" data-file-path="{html.escape(track.get("path", ""))}" title="В корзину" aria-label="В корзину">
                {lucide_icon("trash", "trash-svg")}
              </button>
              <div class="music-card-content">
                {cover_html}
                <div class="music-card-main">
                  <div class="music-title">{html.escape(track.get("name", ""))}</div>
                  <div class="music-path" title="{html.escape(track.get("path", ""))}">{html.escape(track.get("folder", ""))}</div>
                  {player_html}
                  <div class="music-pills">{tags}</div>
                  {identity_warning}
                  <div class="music-actions">
                    <button class="small music-action-single" type="button" data-action="tag" data-file-path="{html.escape(track.get("path", ""))}">Теги через beets</button>
                    <button class="small music-action-single" type="button" data-action="shazam-tag" data-file-path="{html.escape(track.get("path", ""))}">Теги через Shazam</button>
                    <button class="small music-action-single" type="button" data-action="layout" data-file-path="{html.escape(track.get("path", ""))}"{layout_disabled}>Разложить по папкам</button>
                    <button class="small enrichment-button" type="button" data-kind="cover" data-file-path="{html.escape(track.get("path", ""))}"{cover_search_disabled}>Найти обложку</button>
                    <button class="small enrichment-button" type="button" data-kind="lyrics" data-file-path="{html.escape(track.get("path", ""))}"{lyrics_search_disabled}>Найти текст</button>
                    <button class="small lyrics-button" type="button" data-file-path="{html.escape(track.get("path", ""))}" data-track-name="{html.escape(track.get("name", ""))}"{lyrics_disabled}>Текст песни</button>
                  </div>
                  <div class="music-card-status" aria-live="polite">
                    <div class="music-card-status-text"></div>
                    <div class="music-card-progress" aria-hidden="true"><span></span></div>
                  </div>
                </div>
              </div>
            </article>
            """
        )
    return "".join(items)


def render_html(payload: dict) -> str:
    json_payload = json.dumps(payload, ensure_ascii=False)
    summary = payload["summary"]
    library = payload["library"]
    top_artists = library.get("top_artists") or infer_top_artists_from_tracks(library.get("tracks", []))
    genres = library.get("genres") or collect_genres_from_tracks(library.get("tracks", []))
    library["genres"] = genres
    years = library.get("years") or collect_years_from_tracks(library.get("tracks", []))
    library["years"] = years
    library_raw_path = library.get("path", "")
    library_path = html.escape(library_raw_path)
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

    for group in payload["groups"]:
        items_html = []
        for item in group["items"]:
            kept_cover = cover_info_for_path(item["kept_file"], cover_by_path, cover_by_name)
            moved_cover = cover_info_for_path(item["moved_file"], cover_by_path, cover_by_name)
            kept_has_cover = bool(kept_cover.get("has_cover")) if kept_cover else None
            moved_has_cover = bool(moved_cover.get("has_cover")) if moved_cover else None
            kept_has_lyrics = bool(kept_cover.get("has_lyrics")) if kept_cover else None
            moved_has_lyrics = bool(moved_cover.get("has_lyrics")) if moved_cover else None
            review_only = bool(item.get("review_only"))
            kept_label = "Лучший кандидат" if review_only else "Оставлен"
            moved_label = "Кандидат в сравнение" if review_only else "В карантин"
            kept_actions = f"""
                    <div class="track-actions">
                      <button class="small quarantine-one" type="button" data-file="{html.escape(item["kept_file"])}">В карантин</button>
                      <button class="small danger-button trash-one" type="button" data-file-path="{html.escape(item["kept_file"])}">В корзину</button>
                    </div>"""
            moved_actions = f"""
                    <div class="track-actions">
                      <button class="small quarantine-one" type="button" data-file="{html.escape(item["moved_file"])}">В карантин</button>
                      <button class="small danger-button trash-one" type="button" data-file-path="{html.escape(item["moved_file"])}">В корзину</button>
                    </div>"""
            items_html.append(
                f"""
                <div class="comparison" data-kept-file="{html.escape(item["kept_file"])}" data-moved-file="{html.escape(item["moved_file"])}">
                  <div class="track keep" data-file-path="{html.escape(item["kept_file"])}">
                    <div class="track-head">
                      {duplicate_cover_preview(item["kept_file"], item["kept_name"], item["kept_quality"], kept_cover)}
                      <div class="track-meta">
                        <div class="track-label">{kept_label}</div>
                        <div class="track-title">{html.escape(item["kept_name"])}</div>
                        <div class="track-path" title="{html.escape(item["kept_file"])}">{html.escape(item["kept_folder"])}</div>
                      </div>
                    </div>
                    {audio_player(item["kept_file"], f'Прослушать оставленный файл: {item["kept_name"]}')}
                    {render_quality(item["kept_quality"], kept_has_cover, kept_has_lyrics)}
                    {kept_actions}
                  </div>
                  <div class="divider">
                    <div class="arrow" aria-hidden="true"><span></span></div>
                    <div class="reason">{html.escape(translate_reason(item["reason"]))}</div>
                  </div>
                  <div class="track move" data-file-path="{html.escape(item["moved_file"])}">
                    <div class="track-head">
                      {duplicate_cover_preview(item["moved_file"], item["moved_name"], item["moved_quality"], moved_cover)}
                      <div class="track-meta">
                        <div class="track-label">{moved_label}</div>
                        <div class="track-title">{html.escape(item["moved_name"])}</div>
                        <div class="track-path" title="{html.escape(item["moved_file"])}">{html.escape(item["moved_folder"])}</div>
                      </div>
                    </div>
                    {audio_player(item["moved_file"], f'Прослушать файл для карантина: {item["moved_name"]}')}
                    {render_quality(item["moved_quality"], moved_has_cover, moved_has_lyrics)}
                    {moved_actions}
                  </div>
                  <div class="duplicate-card-status" aria-live="polite">
                    <div class="duplicate-card-status-text"></div>
                    <div class="music-card-progress" aria-hidden="true"><span></span></div>
                  </div>
                </div>
                """
            )

        badges = "".join(f'<span class="badge">{html.escape(fmt)}</span>' for fmt in group["formats"])
        group_subtitle = (
            f"Возможных совпадений: {group['duplicates_count']}"
            if group.get("review_only")
            else f"Худших дублей: {group['duplicates_count']}"
        )
        groups_html.append(
            f"""
            <section class="group-card" data-search="{html.escape(group["name"].lower())}" data-count="{group["duplicates_count"]}">
              <button class="group-header" type="button">
                <div>
                  <div class="group-title">{html.escape(group["name"])}</div>
                  <div class="group-subtitle">{group_subtitle}</div>
                </div>
                <div class="badges">{badges}</div>
              </button>
              <div class="group-body">{''.join(items_html)}</div>
            </section>
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
</head>
<body>
  <div class="app-shell">
    <aside class="app-sidebar" aria-label="Навигация по отчёту">
      <a class="app-brand" href="#overview" aria-label="Моя медиатека — к обзору">
        <span class="brand-mark">{lucide_icon("audio-lines", "brand-icon")}</span>
        <span><strong>Моя медиатека</strong><small>Локальная коллекция</small></span>
      </a>
      <p class="nav-caption">Библиотека</p>
      <nav class="side-nav" aria-label="Разделы медиатеки">
        <a href="#overview" class="active">
          {lucide_icon("house", "nav-icon")}
          <span>Обзор</span>
        </a>
        <a href="#insights">
          {lucide_icon("chart", "nav-icon")}
          <span>Аналитика</span>
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
      <div class="sidebar-library">
        <span>Источник музыки</span>
        <p>{lucide_icon("disc")} Ваша коллекция</p>
        <small>{library_path}</small>
      </div>
      <div class="sidebar-note" id="processingModeNote" aria-live="polite">
        <span class="status-dot" aria-hidden="true"></span>
        <div><strong id="processingModeTitle">Режим проверки</strong><small id="processingModeDetail">Изменения и удаление отключены</small></div>
      </div>
    </aside>
    <div class="app-workspace">
      <div class="workspace-bar">
        <a href="#overview" aria-label="К обзору медиатеки">{lucide_icon("house")}</a>
        <span>Медиатека</span><span aria-hidden="true">/</span><strong>Обзор коллекции</strong>
        <span class="workspace-label">Локальная библиотека</span>
      </div>
  <main class="page">
    <section class="header" id="overview">
      <div class="hero-layout">
        <div class="collection-art" aria-hidden="true">{lucide_icon("audio-lines")}</div>
        <div class="hero-copy">
          <div class="hero-kicker">Ваша музыкальная коллекция</div>
          <h1>Моя медиатека</h1>
          <p class="hero-lead">Треки, качество и метаданные вашей библиотеки.</p>
          <div class="library-path"><span>Текущая папка</span>{library_path}</div>
        </div>
      </div>
      <div class="summary">
        <div class="metric metric-primary"><span class="metric-icon">{lucide_icon("files")}</span><span class="metric-label">Всего файлов</span><strong>{format_number(library.get("total_files"))}</strong></div>
        <div class="metric"><span class="metric-icon">{lucide_icon("disc")}</span><span class="metric-label">Альбомов</span><strong>{format_number(library.get("albums"))}</strong></div>
        <div class="metric"><span class="metric-icon">{lucide_icon("users")}</span><span class="metric-label">Исполнителей</span><strong>{format_number(library.get("artists"))}</strong></div>
        <div class="metric"><span class="metric-icon">{lucide_icon("image")}</span><span class="metric-label">С обложкой</span><strong>{format_number(library.get("files_with_cover"))}</strong></div>
        <div class="metric"><span class="metric-icon">{lucide_icon("file-text")}</span><span class="metric-label">С текстом</span><strong>{format_number(library.get("files_with_lyrics"))}</strong></div>
        <div class="metric metric-alert"><span class="metric-icon">{lucide_icon("copy-check")}</span><span class="metric-label">Дублей</span><strong id="duplicateMetric">{format_number(summary["duplicates"])}</strong></div>
        <div class="metric"><span class="metric-icon">{lucide_icon("circle-alert")}</span><span class="metric-label">На проверку</span><strong>{format_number(summary.get("review_groups", 0))}</strong></div>
      </div>
    </section>

    <div class="section-heading" id="insights"><div><span>Обзор библиотеки</span><h2>Ваша коллекция в цифрах</h2></div><p>Форматы, исполнители и метаданные</p></div>
    <div class="analysis-grid">
      <section class="panel summary-panel">
        <h2>Сводка</h2>
        <div class="panel-body note summary-main">
          Групп дублей: <strong id="duplicateGroupsMetric">{format_number(summary["groups"])}</strong><br>
          Файлов, предлагаемых в карантин: <strong id="duplicateFilesMetric">{format_number(summary["duplicates"])}</strong><br>
          Возможных групп на проверку: <strong>{format_number(summary.get("review_groups", 0))}</strong><br>
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

    <section class="music-section collapsed" id="musicSection">
      <div class="duplicates-heading music-heading">
        <h2 class="section-title">Музыка</h2>
      <div class="duplicates-actions">
          <button class="small" id="rescanLibrary" type="button">Пересканировать библиотеку</button>
          <button class="small" id="expandMusic" type="button">Раскрыть всё</button>
          <button class="small" id="collapseMusic" type="button">Свернуть всё</button>
        </div>
      </div>
    <div class="quarantine-panel scan-panel" id="scanPanel">
      <p id="scanStatus">Готово к пересканированию библиотеки. Файлы не перемещаются.</p>
      <span class="copy-status" id="scanCopyStatus"></span>
      <div class="global-progress" id="scanProgress" aria-hidden="true"><span></span></div>
    </div>
    <div class="music-operations music-toolbar">
      <div class="music-operation-groups">
        <section class="music-operation-block">
          <p class="music-operations-title">Тип обработки</p>
          <div class="music-operations-row">
            <label class="mode-choice"><input type="radio" name="processMode" value="dry-run" checked> Проверка</label>
            <label class="mode-choice"><input type="radio" name="processMode" value="real"> Применить изменения</label>
          </div>
        </section>
        <section class="music-operation-block music-operation-actions">
          <p class="music-operations-title">Обработка</p>
          <div class="music-operations-row">
            <button class="small" id="tagVisible" type="button">Теги beets</button>
            <button class="small" id="shazamTagVisible" type="button">Теги Shazam</button>
            <button class="small" id="layoutVisible" type="button">Разложить по папкам</button>
            <button class="small" id="coverVisible" type="button">Найти обложки</button>
            <button class="small" id="lyricsVisible" type="button">Найти тексты</button>
          </div>
        </section>
      </div>
      <div class="operation-status" id="operationStatus">Режим проверки: будет показан план без изменения файлов. Глобальные кнопки работают по отфильтрованному списку, кнопки внутри карточки — только по своей записи.</div>
    </div>
    <div class="toolbar music-toolbar">
      <div class="search-control is-empty">
        <input id="musicSearch" type="search" placeholder=" " aria-label="Поиск по музыке">
        <span class="search-placeholder" aria-hidden="true">Поиск: исполнитель, альбом, трек</span>
      </div>
      <select id="tagFilter" aria-label="Фильтр по тегам">
        <option value="all">Теги: все</option>
        <option value="format">Тег: формат</option>
        <option value="cover">Тег: обложка</option>
        <option value="lyrics">Тег: текст песни</option>
        <option value="bitrate">Тег: битрейт</option>
        <option value="bit_depth">Тег: разрядность</option>
        <option value="sample_rate">Тег: частота дискретизации</option>
        <option value="album">Тег: альбом</option>
        <option value="albumartist">Тег: исполнитель альбома</option>
        <option value="artist">Тег: исполнитель</option>
        <option value="genre">Тег: жанр</option>
        <option value="title">Тег: название</option>
        <option value="year">Тег: год</option>
        <option value="status">Тег: статус</option>
      </select>
      <select id="identityFilter" aria-label="Фильтр по аудиоотпечатку">
        <option value="all">Отпечаток: все</option>
        <option value="mismatch">Отпечаток: не совпадает</option>
        <option value="match">Отпечаток: совпадает</option>
      </select>
      <select id="layoutFilter" aria-label="Фильтр по раскладке">
        <option value="all">Раскладка: все</option>
        <option value="ready">Раскладка: нет</option>
        <option value="done">Раскладка: есть</option>
      </select>
      <div class="sort-control">
        <select id="sort" aria-label="Сортировка музыки">
          <option value="name">Название</option>
          <option value="artist">Исполнитель</option>
          <option value="album">Альбом</option>
          <option value="year">Год</option>
          <option value="format">Формат</option>
        </select>
      </div>
    </div>
    <div class="music-list" id="musicList">{music_html}</div>
    <div class="empty" id="musicEmpty">Ничего не найдено по текущему фильтру музыки.</div>
    </section>

    <section class="music-section duplicates-section" id="duplicates">
    <div class="duplicates-heading">
      <h2 class="section-title">Дубли и возможные совпадения</h2>
      <div class="duplicates-actions">
        <button class="small" id="findDuplicates" type="button">Найти дубли</button>
        <button class="small danger-button" id="quarantineCommand" type="button">Переместить всё в карантин</button>
        <button class="small" id="expandAll" type="button">Раскрыть всё</button>
        <button class="small" id="collapseAll" type="button">Свернуть всё</button>
      </div>
    </div>
    <div class="quarantine-panel scan-panel" id="duplicateScanPanel">
      <p id="duplicateScanStatus">Готово к новому поиску дублей. Файлы не перемещаются.</p>
      <span class="copy-status" id="duplicateScanCopyStatus"></span>
      <div class="global-progress" id="duplicateScanProgress" aria-hidden="true"><span></span></div>
    </div>
    <div class="quarantine-panel" id="quarantinePanel">
      <p id="quarantineStatus">Готово к безопасному переносу дублей в карантин. Файлы не удаляются.</p>
      <span class="copy-status" id="copyStatus"></span>
      <div class="global-progress" id="globalProgress" aria-hidden="true"><span></span></div>
    </div>
    <div id="cards">{''.join(groups_html)}</div>
    <div class="empty" id="empty">Ничего не найдено по текущему фильтру.</div>
    </section>
  </main>
    </div>
  </div>

  <div class="lyrics-modal" id="lyricsModal" aria-hidden="true">
    <div class="lyrics-dialog" role="dialog" aria-modal="true" aria-labelledby="lyricsTitle">
      <div class="lyrics-dialog-head">
        <div>
          <h2 class="lyrics-dialog-title" id="lyricsTitle">Текст песни</h2>
          <div class="lyrics-dialog-path" id="lyricsPath"></div>
          <div class="lyrics-source" id="lyricsSource">Источник: не выбран</div>
        </div>
        <button class="lyrics-close" id="lyricsClose" type="button" aria-label="Закрыть">×</button>
      </div>
      <pre class="lyrics-text" id="lyricsText"></pre>
    </div>
  </div>

  <script id="payload" type="application/json">{html.escape(json_payload)}</script>
  <script>
    let cards = Array.from(document.querySelectorAll('.group-card'));
    const sort = document.getElementById('sort');
    let musicCards = Array.from(document.querySelectorAll('.music-card'));
    const musicList = document.getElementById('musicList');
    const musicSearch = document.getElementById('musicSearch');
    const searchControl = musicSearch.closest('.search-control');
    const tagFilter = document.getElementById('tagFilter');
    const layoutFilter = document.getElementById('layoutFilter');
    const identityFilter = document.getElementById('identityFilter');
    const musicEmpty = document.getElementById('musicEmpty');
    const quarantineButton = document.getElementById('quarantineCommand');
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
    const musicSection = document.getElementById('musicSection');
    const expandMusic = document.getElementById('expandMusic');
    const collapseMusic = document.getElementById('collapseMusic');
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
    const lyricsPath = document.getElementById('lyricsPath');
    const lyricsSource = document.getElementById('lyricsSource');
    const lyricsText = document.getElementById('lyricsText');
    const lyricsClose = document.getElementById('lyricsClose');

    const sideNavLinks = Array.from(document.querySelectorAll('.side-nav a[href^="#"]'));

    function activateSideNav(id) {{
      sideNavLinks.forEach(link => {{
        const isActive = link.getAttribute('href') === '#' + id;
        link.classList.toggle('active', isActive);
        if (isActive) link.setAttribute('aria-current', 'page');
        else link.removeAttribute('aria-current');
      }});
    }}

    sideNavLinks.forEach(link => {{
      link.addEventListener('click', () => activateSideNav(link.getAttribute('href').slice(1)));
    }});
    window.addEventListener('hashchange', () => activateSideNav(window.location.hash.slice(1) || 'overview'));
    activateSideNav(window.location.hash.slice(1) || 'overview');
    function selectedMode() {{
      const selected = document.querySelector('input[name="processMode"]:checked');
      return selected ? selected.value : 'dry-run';
    }}

    function updateOperationStatus() {{
      const mode = selectedMode();
      if (mode === 'real') {{
        if (operationStatus) operationStatus.textContent = 'Изменения включены: каждое действие потребует отдельного подтверждения. Удаление файлов запрещено. Глобальные кнопки работают по отфильтрованному списку, кнопки внутри карточки — только по своей записи.';
        if (processingModeTitle) processingModeTitle.textContent = 'Изменения включены';
        if (processingModeDetail) processingModeDetail.textContent = 'Удаление файлов запрещено';
        if (processingModeNote) processingModeNote.classList.add('mode-real');
      }} else {{
        if (operationStatus) operationStatus.textContent = 'Режим проверки: будет показан план без изменения файлов. Глобальные кнопки работают по отфильтрованному списку, кнопки внутри карточки — только по своей записи.';
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
      lyricsModal.classList.remove('visible');
      lyricsModal.setAttribute('aria-hidden', 'true');
    }}

    async function openLyricsModal(button) {{
      const card = button.closest('.music-card');
      const filePath = button.dataset.filePath || card?.dataset.filePath || '';
      const trackName = button.dataset.trackName || card?.querySelector('.music-title')?.textContent || 'Текст песни';
      if (!filePath || button.disabled) return;

      lyricsTitle.textContent = trackName;
      lyricsPath.textContent = filePath;
      lyricsSource.textContent = 'Источник: загружается...';
      lyricsText.textContent = 'Загружаю текст песни...';
      lyricsText.classList.add('loading');
      lyricsText.classList.remove('error');
      lyricsModal.classList.add('visible');
      lyricsModal.setAttribute('aria-hidden', 'false');

      try {{
        const response = await fetch(`/api/lyrics?file=${{encodeURIComponent(filePath)}}`);
        const result = await response.json();
        if (!response.ok || !result.ok) throw new Error(result.error || 'Текст песни не найден.');
        lyricsText.textContent = result.lyrics || 'Текст песни не найден.';
        lyricsPath.textContent = filePath;
        lyricsSource.textContent = result.source ? `Источник: ${{result.source}}` : 'Источник: не указан';
        lyricsText.classList.remove('loading');
      }} catch (error) {{
        lyricsSource.textContent = 'Источник: текст не найден';
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
      const root = card || document;
      const selector = card ? '.music-action-single' : '.music-action-single, #tagVisible, #shazamTagVisible, #layoutVisible, #coverVisible, #lyricsVisible';
      root.querySelectorAll(selector).forEach(button => {{
        button.disabled = disabled;
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
      document.querySelectorAll('.quarantine-one, .trash-one, #quarantineCommand, #rescanLibrary, #findDuplicates').forEach(button => {{
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
      applyMusicFilters();
    }}

    function refreshGroupAfterComparisonRemoval(group) {{
      if (!group) return;
      const comparisons = Array.from(group.querySelectorAll('.comparison'));
      if (!comparisons.length) {{
        group.remove();
        cards = cards.filter(card => card !== group);
        return;
      }}

      group.dataset.count = String(comparisons.length);
      const subtitle = group.querySelector('.group-subtitle');
      if (subtitle) subtitle.textContent = `Худших дублей: ${{comparisons.length}}`;
    }}

    function removeDuplicateComparisonsByPaths(paths) {{
      const normalized = new Set((paths || []).map(normalizePathForCompare));
      if (!normalized.size) return;
      const groupsToRefresh = new Set();
      document.querySelectorAll('.comparison').forEach(comparison => {{
        const kept = normalizePathForCompare(comparison.dataset.keptFile || '');
        const moved = normalizePathForCompare(comparison.dataset.movedFile || '');
        if (normalized.has(kept) || normalized.has(moved)) {{
          const group = comparison.closest('.group-card');
          groupsToRefresh.add(group);
          comparison.remove();
        }}
      }});
      groupsToRefresh.forEach(refreshGroupAfterComparisonRemoval);
      updateDuplicateSummaryCounts();
      document.getElementById('empty').classList.toggle('visible', cards.filter(card => !card.hidden).length === 0);
    }}

    function updateDuplicateSummaryCounts() {{
      const visibleGroups = cards.length;
      const visibleDuplicates = document.querySelectorAll('.comparison').length;
      const formattedGroups = visibleGroups.toLocaleString('ru-RU').replace(/\u00a0/g, ' ');
      const formattedDuplicates = visibleDuplicates.toLocaleString('ru-RU').replace(/\u00a0/g, ' ');
      const duplicateMetric = document.getElementById('duplicateMetric');
      const duplicateGroupsMetric = document.getElementById('duplicateGroupsMetric');
      const duplicateFilesMetric = document.getElementById('duplicateFilesMetric');
      if (duplicateMetric) duplicateMetric.textContent = formattedDuplicates;
      if (duplicateGroupsMetric) duplicateGroupsMetric.textContent = formattedGroups;
      if (duplicateFilesMetric) duplicateFilesMetric.textContent = formattedDuplicates;
    }}

    function clearTagAttributes(card) {{
      Array.from(card.attributes).forEach(attribute => {{
        if (attribute.name.startsWith('data-tag-')) card.removeAttribute(attribute.name);
      }});
    }}

    function tagText(tag) {{
      if (!tag || typeof tag !== 'object') return String(tag || '');
      const label = tag.label || '';
      const value = tag.value || '';
      return value ? `${{label}}: ${{value}}` : label;
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
        cover.innerHTML = '<span aria-hidden="true">♪</span><strong>нет</strong>';
      }}
    }}

    function updateMusicCardFromTrack(card, track) {{
      if (!card || !track) return;

      const path = track.path || '';
      const folder = track.folder || '';
      const name = track.name || '';
      const tags = Array.isArray(track.tags) ? track.tags : [];
      const tagValuesByKind = {{}};
      const tagSearchValues = [];

      card.dataset.filePath = path;
      card.dataset.sortName = name.toLowerCase();
      clearTagAttributes(card);

      const title = card.querySelector('.music-title');
      const pathNode = card.querySelector('.music-path');
      const audio = card.querySelector('.audio-player');
      const pills = card.querySelector('.music-pills');
      if (title) title.textContent = name;
      if (pathNode) {{
        pathNode.textContent = folder;
        pathNode.title = path;
      }}
      if (audio) {{
        audio.src = `/api/audio?file=${{encodeURIComponent(path)}}`;
        audio.textContent = `Прослушать ${{name}}`;
      }}
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

          const pill = document.createElement('span');
          pill.className = `music-pill music-pill-${{kind}}`;
          pill.textContent = text;
          pills.appendChild(pill);
        }});
      }}

      Object.entries(tagValuesByKind).forEach(([kind, values]) => {{
        card.setAttribute(`data-tag-${{kind}}`, values.join(' ').toLowerCase());
      }});
      card.dataset.sortArtist = (tagValuesByKind.artist || tagValuesByKind.albumartist || []).join(' ').toLowerCase();
      card.dataset.sortAlbum = (tagValuesByKind.album || []).join(' ').toLowerCase();
      card.dataset.sortYear = (tagValuesByKind.year || []).join(' ').toLowerCase();
      card.dataset.sortFormat = (tagValuesByKind.format || []).join(' ').toLowerCase();
      card.dataset.musicSearch = [name, folder, tagSearchValues.join(' ')].join(' ').toLowerCase();
      const layoutButton = card.querySelector('[data-action="layout"]');
      card.dataset.layoutStatus = layoutButton?.disabled ? 'done' : 'ready';
      const lyricsButton = card.querySelector('.lyrics-button');
      const hasLyrics = (tagValuesByKind.lyrics || []).join(' ').toLowerCase().includes('текст песни: есть');
      if (lyricsButton) {{
        lyricsButton.dataset.filePath = path;
        lyricsButton.dataset.trackName = name;
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
      card.querySelectorAll('.music-action-single').forEach(button => {{
        button.dataset.filePath = path;
      }});
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
          if (updatedTrack) updateMusicCardFromTrack(sourceCard, updatedTrack);
          setCardStatus(sourceCard, 'done', result.message || 'Операция завершена.');
          applyMusicFilters();
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
      const sorted = [...musicCards];
      sorted.sort((a, b) => {{
        const key = sort.value || 'name';
        const left = a.getAttribute(`data-sort-${{key}}`) || a.dataset.sortName || '';
        const right = b.getAttribute(`data-sort-${{key}}`) || b.dataset.sortName || '';
        return left.localeCompare(right, 'ru', {{ numeric: true, sensitivity: 'base' }});
      }});
      sorted.forEach(card => musicList.appendChild(card));
    }}

    function updateSearchPlaceholder() {{
      if (!searchControl) return;
      searchControl.classList.toggle('is-empty', musicSearch.value.length === 0);
    }}

    function applyMusicFilters() {{
      updateSearchPlaceholder();
      const value = musicSearch.value.trim().toLowerCase();
      const tagKind = tagFilter.value;
      const layoutKind = layoutFilter.value;
      const identityKind = identityFilter.value;
      let visibleCount = 0;
      musicCards.forEach(card => {{
        const searchArea = tagKind === 'all'
          ? (card.dataset.musicSearch || '')
          : (card.getAttribute(`data-tag-${{tagKind}}`) || '');
        const matchesText = !value || searchArea.includes(value);
        const matchesLayout = layoutKind === 'all' || card.dataset.layoutStatus === layoutKind;
        const mismatch = card.dataset.identityMismatch === 'yes';
        const matchesIdentity = identityKind === 'all' || (identityKind === 'mismatch' ? mismatch : !mismatch);
        const visible = matchesText && matchesLayout && matchesIdentity;
        card.hidden = !visible;
        if (visible) visibleCount += 1;
      }});
      musicEmpty.classList.toggle('visible', visibleCount === 0);
    }}

    document.querySelectorAll('.group-header').forEach(button => {{
      button.addEventListener('click', () => button.closest('.group-card').classList.toggle('open'));
    }});
    function audioPath(player) {{
      try {{
        return new URL(player.currentSrc || player.src, window.location.href).searchParams.get('file') || '';
      }} catch (_error) {{
        return '';
      }}
    }}

    async function releaseAudioStreams(filePath = '') {{
      const wanted = normalizePathForCompare(filePath);
      document.querySelectorAll('.audio-player').forEach(player => {{
        if (wanted && normalizePathForCompare(audioPath(player)) !== wanted) return;
        player.pause();
        player.removeAttribute('src');
        player.load();
      }});
      // Chromium aborts the range request asynchronously; let the server close its handle.
      await new Promise(resolve => setTimeout(resolve, 250));
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
        removeDuplicateComparisonsByPaths(changedPaths);
        removeMusicCardsByPaths(changedPaths);
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

    quarantineButton.addEventListener('click', () => {{
      const confirmed = window.confirm('Перенести все худшие дубли из CSV-отчёта в карантин? Файлы не удаляются.');
      if (!confirmed) return;
      runQuarantine('/api/quarantine-all', {{ confirm: 'MOVE_TO_QUARANTINE' }}, 'Переношу все худшие дубли в карантин...');
    }});

    async function runTrash(filePath, sourceButton) {{
      const sourceMusicCard = sourceButton?.closest?.('.music-card') || null;
      const sourceComparison = sourceButton?.closest?.('.comparison') || null;
      if (!filePath) return;

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
          body: JSON.stringify({{ file: filePath, confirm: 'MOVE_TO_TRASH' }}),
        }});
        const result = await response.json();
        if (!response.ok || !result.ok) throw new Error(result.error || 'Команда не выполнена');
        const changedPaths = result.moved_paths || [result.source || filePath];
        removeDuplicateComparisonsByPaths(changedPaths);
        removeMusicCardsByPaths(changedPaths);
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
      const progress = fromDuplicates ? duplicateScanProgress : scanProgress;
      statusPanel.classList.add('visible');
      statusText.textContent = fromDuplicates ? 'Идёт поиск дублей по всей библиотеке…' : 'Сканирование библиотеки…';
      copyText.textContent = '';
      progress.classList.add('visible');
      setDuplicateActionsDisabled(true);
      try {{
        const response = await fetch('/api/rescan-library', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{ confirm: 'RESCAN_LIBRARY' }}),
        }});
        const result = await response.json();
        if (!response.ok || !result.ok) throw new Error(result.error || 'Команда не выполнена');
        statusText.textContent = 'Готово. CSV дублей и отчёт обновлены, страница перезагружается.';
        setTimeout(() => window.location.reload(), 500);
      }} catch (error) {{
        statusText.textContent = 'Не удалось пересканировать библиотеку.';
        copyText.textContent = error.message || String(error);
      }} finally {{
        progress.classList.remove('visible');
        setDuplicateActionsDisabled(false);
      }}
    }}

    function formatAudioTime(seconds) {{
      if (!Number.isFinite(seconds) || seconds < 0) return '0:00';
      const minutes = Math.floor(seconds / 60);
      const rest = Math.floor(seconds % 60).toString().padStart(2, '0');
      return `${{minutes}}:${{rest}}`;
    }}

    document.querySelectorAll('.custom-audio-player').forEach(wrapper => {{
      const player = wrapper.querySelector('.audio-player');
      const playButton = wrapper.querySelector('.audio-play');
      const muteButton = wrapper.querySelector('.audio-mute');
      const currentTime = wrapper.querySelector('.audio-current');
      const seekWrap = wrapper.querySelector('.audio-seek-wrap');
      const seek = wrapper.querySelector('.audio-seek');

      function updateProgress() {{
        const duration = player.duration || 0;
        const progress = duration ? Math.min(100, Math.max(0, player.currentTime / duration * 100)) : 0;
        seek.value = Math.round(progress * 10);
        seekWrap.style.setProperty('--audio-progress', `${{progress}}%`);
        currentTime.textContent = formatAudioTime(player.currentTime);
      }}

      playButton.addEventListener('click', () => {{
        if (player.paused) {{
          player.play();
        }} else {{
          player.pause();
        }}
      }});

      muteButton.addEventListener('click', () => {{
        player.muted = !player.muted;
      }});

      seek.addEventListener('input', () => {{
        if (!player.duration) return;
        player.currentTime = Number(seek.value) / 1000 * player.duration;
      }});

      player.addEventListener('play', () => {{
        document.querySelectorAll('.audio-player').forEach(other => {{
          if (other !== player) other.pause();
        }});
        playButton.classList.add('playing');
      }});
      player.addEventListener('pause', () => playButton.classList.remove('playing'));
      player.addEventListener('ended', () => playButton.classList.remove('playing'));
      player.addEventListener('volumechange', () => muteButton.classList.toggle('muted', player.muted || player.volume === 0));
      player.addEventListener('loadedmetadata', updateProgress);
      player.addEventListener('timeupdate', updateProgress);
      updateProgress();
    }});

    document.querySelectorAll('.quarantine-one').forEach(button => {{
      button.addEventListener('click', event => {{
        event.stopPropagation();
        const confirmed = window.confirm('Переместить выбранный файл в карантин? Файл не удаляется.');
        if (!confirmed) return;
        runQuarantine(
          '/api/quarantine-one',
          {{ file: button.dataset.file, confirm: 'MOVE_TO_QUARANTINE' }},
          'Переношу выбранный файл в карантин...',
          button
        );
      }});
    }});
    document.querySelectorAll('.music-action-single').forEach(button => {{
      button.addEventListener('click', event => {{
        event.preventDefault();
        event.stopPropagation();
        runMusicOperation(button.dataset.action, [singleMusicPath(button)], 'single', button);
      }});
    }});
    document.querySelectorAll('.trash-one').forEach(button => {{
      button.addEventListener('click', event => {{
        event.preventDefault();
        event.stopPropagation();
        runTrash(button.dataset.filePath, button);
      }});
    }});
    document.querySelectorAll('.lyrics-button').forEach(button => {{
      button.addEventListener('click', event => {{
        event.preventDefault();
        event.stopPropagation();
        openLyricsModal(button);
      }});
    }});
    document.querySelectorAll('.enrichment-button').forEach(button => {{
      button.addEventListener('click', event => {{
        event.preventDefault();
        event.stopPropagation();
        searchAndSaveEnrichment(button);
      }});
    }});
    if (lyricsClose) lyricsClose.addEventListener('click', closeLyricsModal);
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

    document.querySelectorAll('input[name="processMode"]').forEach(input => {{
      input.addEventListener('change', updateOperationStatus);
    }});
    updateOperationStatus();
    document.getElementById('expandAll').addEventListener('click', () => cards.forEach(card => {{ if (!card.hidden) card.classList.add('open'); }}));
    document.getElementById('collapseAll').addEventListener('click', () => cards.forEach(card => card.classList.remove('open')));
    musicSearch.addEventListener('input', () => {{
      updateSearchPlaceholder();
      applyMusicFilters();
    }});
    tagFilter.addEventListener('change', applyMusicFilters);
    layoutFilter.addEventListener('change', applyMusicFilters);
    identityFilter.addEventListener('change', applyMusicFilters);
    sort.addEventListener('change', applySort);
    if (expandMusic) {{
      expandMusic.addEventListener('click', () => musicSection.classList.remove('collapsed'));
    }}
    if (collapseMusic) {{
      collapseMusic.addEventListener('click', () => musicSection.classList.add('collapsed'));
    }}
    applySort();
    applyMusicFilters();
    if (cards.length <= 8) cards.forEach(card => card.classList.add('open'));
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
    library_stats = analyze_library(library_path, identity_report_path)
    payload = build_payload(rows, library_stats, review_rows)
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
