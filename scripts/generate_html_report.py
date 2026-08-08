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
FAVICON_VERSION = "lucide-1.28.0-audio-lines"

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
    '<rect width="24" height="24" rx="7" fill="#8f73e2" stroke="none"/>'
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

    colors = ["#2563eb", "#dc2626", "#f59e0b", "#16a34a", "#9333ea", "#0891b2", "#db2777", "#65a30d", "#b91c1c"]
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
        return "rgb(247, 245, 251)"

    stops = [
        (0.0, (244, 241, 251)),
        (0.24, (234, 228, 249)),
        (0.46, (220, 211, 246)),
        (0.68, (202, 189, 240)),
        (0.84, (184, 167, 234)),
        (1.0, (163, 141, 225)),
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
    return "rgb(163, 141, 225)"


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
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Отчёт по музыкальной библиотеке</title>
  <link rel="icon" type="image/svg+xml" href="{FAVICON_DATA_URI}#v={FAVICON_VERSION}">
  <style>
    :root {{
      --bg: #050816;
      --panel: rgba(13, 18, 32, 0.78);
      --panel-solid: #111827;
      --soft: rgba(255, 255, 255, 0.055);
      --text: #e5e7eb;
      --muted: #9ca3af;
      --line: rgba(148, 163, 184, 0.24);
      --good: #86efac;
      --bad: #fca5a5;
      --accent: #93c5fd;
      --accent-strong: #60a5fa;
      --warning: #fde68a;
      --shadow: 0 24px 80px rgba(0, 0, 0, 0.34);
      --radius: 22px;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      color: var(--text);
      background:
        radial-gradient(circle at 0 0, rgba(59, 130, 246, 0.32), transparent 34rem),
        radial-gradient(circle at 100% 0, rgba(20, 184, 166, 0.18), transparent 30rem),
        radial-gradient(circle at 50% 100%, rgba(244, 114, 182, 0.1), transparent 34rem),
        linear-gradient(135deg, #020617, #0f172a 52%, #111827);
      font-family: Inter, Segoe UI, system-ui, -apple-system, BlinkMacSystemFont, Arial, sans-serif;
    }}
    .page {{ width: min(1240px, calc(100% - 32px)); margin: 0 auto; padding: 40px 0 64px; }}
    .header {{ padding: 28px; border: 1px solid var(--line); border-radius: var(--radius); background: var(--panel); box-shadow: var(--shadow); backdrop-filter: blur(18px); }}
    h1 {{ margin: 0; font-size: clamp(28px, 4vw, 44px); line-height: 1.06; letter-spacing: 0; }}
    .library-path {{ margin-top: 14px; overflow-wrap: anywhere; color: var(--muted); font-size: 13px; line-height: 1.45; }}
    .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin-top: 24px; }}
    .metric {{ padding: 18px; border: 1px solid var(--line); border-radius: 18px; background: var(--soft); }}
    .metric span {{ display: block; color: var(--muted); font-size: 13px; }}
    .metric strong {{ display: block; margin-top: 6px; font-size: 30px; letter-spacing: 0; }}
    .analysis-grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; margin-top: 16px; }}
    .panel {{ padding: 20px; border: 1px solid var(--line); border-radius: 20px; background: rgba(13, 18, 32, 0.68); box-shadow: 0 16px 48px rgba(0, 0, 0, 0.18); backdrop-filter: blur(12px); }}
    .panel h2, .section-title {{ margin: 0; font-size: 22px; }}
    .panel-body {{ margin-top: 14px; }}
    .note {{ color: var(--muted); font-size: 14px; line-height: 1.5; }}
    .note strong {{ color: var(--text); white-space: nowrap; }}
    .summary-panel {{ display: grid; grid-template-rows: auto 1fr; gap: 18px; }}
    .summary-panel .panel-body {{ margin-top: 0; }}
    .summary-main {{ padding-bottom: 18px; border-bottom: 1px solid var(--line); }}
    .summary-subtitle {{ margin: 0 0 14px; color: var(--text); font-size: 16px; font-weight: 800; }}
    .format-row {{ display: grid; grid-template-columns: 60px 1fr 60px; gap: 10px; align-items: center; margin-top: 10px; }}
    .panel-body > .format-row:first-child {{ margin-top: 0; }}
    .artist-row {{ display: grid; grid-template-columns: minmax(88px, 1fr) minmax(72px, 0.75fr) 46px; gap: 10px; align-items: center; margin-top: 10px; }}
    .panel-body > .artist-row:first-child {{ margin-top: 0; }}
    .artist-name {{ min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
    .genre-row {{ display: grid; grid-template-columns: minmax(90px, 150px) 1fr 44px; gap: 10px; align-items: center; margin-top: 10px; }}
    .genre-name {{ min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
    .year-row {{ display: grid; grid-template-columns: 54px 1fr 44px; gap: 10px; align-items: center; margin-top: 10px; }}
    .format-bar {{ height: 10px; border-radius: 999px; background: rgba(148, 163, 184, 0.16); overflow: hidden; }}
    .format-bar span {{ display: block; height: 100%; border-radius: inherit; background: linear-gradient(90deg, rgba(147, 197, 253, 0.62), rgba(45, 212, 191, 0.78)); }}
    .format-count {{ text-align: right; color: var(--muted); }}
    .donut-layout {{ display: grid; grid-template-columns: 1fr; gap: 14px; justify-items: center; }}
    .donut-chart {{ position: relative; isolation: isolate; overflow: hidden; width: 146px; aspect-ratio: 1; border-radius: 50%; display: grid; place-items: center; background: transparent; box-shadow: 0 18px 42px rgba(0, 0, 0, 0.18); }}
    .donut-svg {{ position: absolute; inset: 0; z-index: 0; width: 100%; height: 100%; shape-rendering: geometricPrecision; }}
    .donut-segment {{ vector-effect: non-scaling-stroke; }}
    .donut-hole {{ position: relative; z-index: 2; width: 82px; aspect-ratio: 1; border-radius: 50%; display: grid; place-items: center; align-content: center; padding: 8px; background: #0f172a; text-align: center; box-shadow: 0 0 0 1px var(--line); }}
    .donut-hole strong {{ font-size: 24px; line-height: 1; }}
    .donut-hole span {{ display: block; max-width: 68px; margin-top: 5px; overflow: hidden; color: var(--muted); font-size: 11px; line-height: 1.15; text-overflow: ellipsis; white-space: nowrap; }}
    .chart-legend {{ display: grid; gap: 7px; width: 100%; min-width: 0; max-height: 209px; overflow-y: auto; padding-right: 4px; scrollbar-gutter: stable; scrollbar-width: thin; scrollbar-color: rgba(148, 163, 184, 0.34) transparent; }}
    .chart-legend::-webkit-scrollbar {{ width: 6px; }}
    .chart-legend::-webkit-scrollbar-track {{ background: transparent; }}
    .chart-legend::-webkit-scrollbar-thumb {{ border-radius: 999px; background: rgba(148, 163, 184, 0.28); }}
    .chart-legend-row {{ display: grid; grid-template-columns: 10px minmax(0, 1fr) 42px 44px; gap: 8px; align-items: center; min-width: 0; font-size: 13px; }}
    .chart-dot {{ width: 10px; height: 10px; border-radius: 50%; }}
    .chart-label {{ overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
    .chart-legend-row strong {{ text-align: right; }}
    .chart-legend-row span:last-child {{ color: var(--muted); text-align: right; }}
    .chart-note {{ width: 100%; margin: 0 0 12px; color: var(--muted); font-size: 14px; line-height: 1.5; }}
    .chart-note strong {{ color: var(--text); white-space: nowrap; }}
    .year-chart {{ display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 8px; width: 100%; height: 196px; margin-top: 18px; }}
    .year-chart-item {{ display: grid; grid-template-rows: minmax(0, 1fr) 28px; min-width: 0; }}
    .year-chart-column {{ display: flex; flex-direction: column; align-items: center; justify-content: flex-end; min-height: 0; border-bottom: 1px solid var(--line); }}
    .year-chart-bar {{ display: block; width: min(32px, 68%); height: max(8px, var(--bar-height)); border-radius: 6px 6px 2px 2px; background: #8064dc; transition: background .16s ease, transform .16s ease; transform-origin: bottom; }}
    .year-chart-item:hover .year-chart-bar {{ background: #6749cb; transform: scaleX(1.06); }}
    .year-chart-label {{ display: block; padding-top: 9px; color: var(--muted); font-size: 10px; font-weight: 650; line-height: 1.1; text-align: center; white-space: nowrap; }}
    .year-chart-value {{ display: block; margin-bottom: 6px; color: var(--text); font-size: 11px; font-weight: 750; line-height: 1; text-align: center; font-variant-numeric: tabular-nums; }}
    .heatmap-panel {{
      margin-top: 14px;
      padding: 22px;
      overflow: hidden;
      background:
        linear-gradient(135deg, rgba(12, 21, 38, 0.92), rgba(10, 18, 34, 0.82));
    }}
    .heatmap-heading {{
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 14px;
      margin-bottom: 18px;
    }}
    .heatmap-heading h2 {{ margin: 0; font-size: 24px; line-height: 1.15; }}
    .heatmap-heading p {{ margin: 5px 0 0; color: var(--muted); font-size: 14px; }}
    .heatmap-scroll {{ max-width: 100%; overflow-x: auto; padding-bottom: 4px; scrollbar-width: thin; scrollbar-color: rgba(148, 163, 184, 0.34) transparent; }}
    .heatmap-scroll::-webkit-scrollbar {{ height: 8px; }}
    .heatmap-scroll::-webkit-scrollbar-track {{ background: transparent; }}
    .heatmap-scroll::-webkit-scrollbar-thumb {{ border-radius: 999px; background: rgba(148, 163, 184, 0.28); }}
    .heatmap-grid {{
      display: grid;
      grid-template-columns: minmax(116px, 0.88fr) repeat(var(--heatmap-columns), minmax(92px, 1fr));
      min-width: 720px;
      overflow: hidden;
      border-radius: 8px;
    }}
    .heatmap-row {{ display: contents; }}
    .heatmap-corner, .heatmap-column, .heatmap-genre, .heatmap-cell {{
      min-height: 40px;
      border: 1px solid rgba(2, 6, 23, 0.72);
    }}
    .heatmap-corner, .heatmap-column {{
      display: flex;
      align-items: center;
      justify-content: center;
      border-color: transparent;
      color: #dbe4f0;
      background: transparent;
      font-weight: 750;
    }}
    .heatmap-genre {{
      display: flex;
      align-items: center;
      min-width: 0;
      padding: 0 12px 0 0;
      overflow: hidden;
      border-color: transparent rgba(2, 6, 23, 0.72) transparent transparent;
      color: #eef2f7;
      background: transparent;
      font-weight: 760;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    .heatmap-cell {{
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 0 8px;
      color: #f8fafc;
      font-size: 15px;
      font-variant-numeric: tabular-nums;
      text-align: center;
      text-shadow: 0 1px 10px rgba(0, 0, 0, 0.42);
    }}
    .heatmap-scale {{
      display: grid;
      grid-template-columns: auto minmax(180px, 420px) auto;
      justify-content: center;
      align-items: center;
      gap: 10px;
      margin-top: 18px;
      color: var(--muted);
      font-size: 14px;
    }}
    .heatmap-scale-bar {{
      height: 16px;
      border-radius: 999px;
      background: linear-gradient(90deg, rgb(20, 43, 101), rgb(42, 55, 133), rgb(104, 55, 166), rgb(190, 61, 135), rgb(239, 91, 77), rgb(255, 174, 48));
      box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.08);
    }}
    .toolbar {{ display: grid; grid-template-columns: minmax(220px, 1fr) minmax(190px, 0.66fr) minmax(205px, 0.74fr) minmax(190px, 0.66fr) minmax(190px, 0.6fr); gap: 10px; margin-top: 18px; align-items: center; }}
    input, select, button.small {{
      height: 44px;
      min-height: 44px;
      border: 1px solid var(--line);
      border-radius: 999px;
      background: rgba(15, 23, 42, 0.82);
      color: var(--text);
      padding: 0 16px;
      font: inherit;
      outline: none;
    }}
    input::placeholder {{ color: transparent; }}
    .search-control {{ position: relative; min-width: 0; }}
    .search-control input {{ position: relative; z-index: 1; width: 100%; padding-right: 18px; }}
    .search-placeholder {{
      position: absolute;
      z-index: 2;
      left: 16px;
      top: 50%;
      max-width: calc(100% - 32px);
      overflow: hidden;
      transform: translateY(-50%);
      color: rgba(203, 213, 225, 0.92);
      font: inherit;
      line-height: 1.25;
      padding-bottom: 1px;
      text-overflow: ellipsis;
      white-space: nowrap;
      pointer-events: none;
    }}
    .search-control input:focus + .search-placeholder {{ color: rgba(226, 232, 240, 0.72); }}
    .search-control:not(.is-empty) .search-placeholder {{ display: none; }}
    input:focus, select:focus, button.small:focus-visible {{ border-color: rgba(147, 197, 253, 0.72); box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2); }}
    button.small {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      white-space: nowrap;
      transition: border-color 0.16s ease, background 0.16s ease;
    }}
    button.small:hover:not(:disabled) {{ border-color: rgba(147, 197, 253, 0.5); background: rgba(30, 41, 59, 0.92); }}
    input {{ min-width: 0; }}
    select {{
      width: 100%;
      min-width: 0;
      padding-right: 42px;
      appearance: none;
      background-image:
        linear-gradient(45deg, transparent 50%, #e5e7eb 50%),
        linear-gradient(135deg, #e5e7eb 50%, transparent 50%);
      background-position:
        calc(100% - 21px) 18px,
        calc(100% - 15px) 18px;
      background-size: 6px 6px, 6px 6px;
      background-repeat: no-repeat;
    }}
    .sort-control {{
      position: relative;
      min-width: 0;
    }}
    .sort-control::before {{
      content: "↑";
      position: absolute;
      left: 16px;
      top: 0;
      bottom: 0;
      z-index: 1;
      width: 16px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: var(--accent);
      font-size: 16px;
      line-height: 44px;
      pointer-events: none;
    }}
    .sort-control select {{ padding-left: 34px; }}
    button {{ cursor: pointer; }}
    button:disabled {{
      cursor: not-allowed;
      opacity: 0.55;
    }}
    .section-title {{ margin-top: 28px; letter-spacing: 0; }}
    .music-toolbar {{ margin: 24px 0 12px; }}
    .music-operations {{
      margin-top: 14px;
      padding: 14px;
      border: 1px solid var(--line);
      border-radius: 18px;
      background: rgba(255, 255, 255, 0.045);
    }}
    .music-operation-groups {{ display: grid; grid-template-columns: 1fr; gap: 12px; align-items: stretch; }}
    .music-operation-block {{ min-width: 0; padding: 12px; border: 1px solid var(--line); border-radius: 14px; background: rgba(15, 23, 42, 0.44); }}
    .music-operations-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
    }}
    .music-operations-row > button.small,
    .music-operations-row > .mode-choice {{
      min-width: 0;
      height: 42px;
      justify-content: center;
    }}
    .music-operations-row > button.small {{ flex: 0 1 auto; }}
    .music-operation-actions .music-operations-row {{ flex-wrap: nowrap; width: 100%; }}
    .music-operation-actions .music-operations-row > button.small {{ flex: 1 1 0; min-width: 0; padding-inline: 12px; }}
    .music-operations-title {{ margin: 0 0 10px; font-weight: 750; }}
    .mode-choice {{ display: inline-flex; align-items: center; gap: 6px; min-height: 42px; padding: 0 12px; border: 1px solid var(--line); border-radius: 999px; background: rgba(15, 23, 42, 0.82); }}
    .mode-choice input {{ flex: 0 0 auto; width: auto; height: auto; margin: 0; }}
    .operation-status {{ margin-top: 10px; color: var(--muted); font-size: 13px; line-height: 1.45; overflow-wrap: anywhere; }}
    .duplicates-heading {{ display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-top: 24px; }}
    .duplicates-heading .section-title {{ margin: 0; }}
    .duplicates-actions {{ display: flex; gap: 10px; flex-wrap: wrap; justify-content: flex-end; }}
    .duplicates-actions .small {{ height: 42px; min-height: 42px; }}
    #rescanLibrary,
    #quarantineCommand {{ width: 236px; }}
    #findDuplicates {{ width: 150px; }}
    .danger-button {{
      border-color: rgba(248, 113, 113, 0.32) !important;
      color: #fecaca !important;
      background: rgba(127, 29, 29, 0.16) !important;
    }}
    .danger-button:hover {{
      border-color: rgba(248, 113, 113, 0.48) !important;
      color: #fee2e2 !important;
      background: rgba(127, 29, 29, 0.26) !important;
    }}
    .quarantine-one {{
      border-color: rgba(134, 239, 172, 0.3) !important;
      color: #bbf7d0 !important;
      background: rgba(20, 83, 45, 0.14) !important;
    }}
    .quarantine-one:hover {{
      border-color: rgba(134, 239, 172, 0.44) !important;
      color: #dcfce7 !important;
      background: rgba(20, 83, 45, 0.24) !important;
    }}
    .track-actions {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px;
      margin-top: auto;
      padding-top: 12px;
    }}
    .track-actions .small {{
      width: 100%;
      min-width: 0;
      justify-content: center;
      text-align: center;
    }}
    .quarantine-panel {{
      display: none;
      margin: 12px 0;
      padding: 14px;
      border: 1px solid rgba(252, 165, 165, 0.34);
      border-radius: 18px;
      background: rgba(127, 29, 29, 0.18);
    }}
    .quarantine-panel.visible {{ display: block; }}
    .quarantine-panel p {{ margin: 0 0 10px; color: #fecaca; line-height: 1.45; }}
    .quarantine-panel p:last-child {{ margin-bottom: 0; }}
    .copy-status {{ margin-left: 10px; color: #fecaca; font-size: 13px; }}
    .global-progress {{
      display: none;
      height: 8px;
      margin-top: 10px;
      overflow: hidden;
      border-radius: 999px;
      background: rgba(252, 165, 165, 0.16);
    }}
    .global-progress.visible {{ display: block; }}
    .global-progress span {{
      display: block;
      width: 40%;
      height: 100%;
      border-radius: inherit;
      background: linear-gradient(90deg, #ef4444, #f97316);
      animation: card-progress 1.1s ease-in-out infinite;
    }}
    .music-section.collapsed .music-toolbar,
    .music-section.collapsed .music-list {{
      display: none;
    }}
    .music-section.collapsed #musicEmpty {{
      display: none !important;
    }}
    .music-list {{ display: grid; gap: 10px; }}
    .music-card {{ position: relative; padding: 14px 58px 14px 14px; border: 1px solid var(--line); border-radius: 18px; background: rgba(13, 18, 32, 0.68); box-shadow: 0 10px 28px rgba(0, 0, 0, 0.14); }}
    .music-trash-icon {{ position: absolute; top: 12px; right: 12px; z-index: 3; width: 32px; min-width: 32px; height: 32px; padding: 0; display: grid; place-items: center; border: 1px solid rgba(248, 113, 113, 0.38); border-radius: 7px; color: #fca5a5; background: rgba(69, 10, 10, 0.28); cursor: pointer; }}
    .music-trash-icon:hover {{ color: #fff; border-color: rgba(248, 113, 113, 0.8); background: rgba(127, 29, 29, 0.72); }}
    .trash-svg {{ display: block; width: 18px; height: 18px; flex: 0 0 auto; }}
    .music-card-identity-mismatch {{ border-color: rgba(250, 204, 21, 0.85); background: rgba(113, 63, 18, 0.32); box-shadow: 0 0 0 1px rgba(250, 204, 21, 0.18), 0 10px 28px rgba(0, 0, 0, 0.14); }}
    .identity-warning {{ margin-top: 10px; padding: 10px 12px; border: 1px solid rgba(250, 204, 21, 0.5); border-radius: 12px; color: #fde68a; background: rgba(113, 63, 18, 0.36); }}
    .music-card-duplicate {{ border-color: rgba(245, 158, 11, 0.54); background: rgba(120, 53, 15, 0.2); }}
    .music-card-unreadable {{ border-color: rgba(239, 68, 68, 0.58); background: rgba(127, 29, 29, 0.22); }}
    .music-card[hidden] {{ display: none; }}
    .music-card-content {{ display: grid; grid-template-columns: 112px minmax(0, 1fr); gap: 14px; align-items: start; }}
    .music-card-main {{ min-width: 0; }}
    .music-cover {{
      display: grid;
      place-items: center;
      width: 112px;
      aspect-ratio: 1 / 1;
      overflow: hidden;
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 12px;
      background: rgba(15, 23, 42, 0.88);
      color: var(--muted);
    }}
    .music-cover img {{ width: 100%; height: 100%; object-fit: cover; }}
    .music-cover-empty {{ gap: 3px; text-align: center; }}
    .empty-cover-icon {{ width: 28px; height: 28px; color: rgba(147, 197, 253, 0.78); }}
    .music-cover-empty strong {{ color: var(--muted); font-size: 11px; font-weight: 700; text-transform: uppercase; }}
    .music-title {{ font-weight: 750; overflow-wrap: anywhere; }}
    .music-path {{ margin-top: 5px; color: var(--muted); font-size: 12px; overflow-wrap: anywhere; }}
    .music-actions {{
      display: flex;
      flex-wrap: nowrap;
      gap: 8px;
      width: 100%;
      margin-top: 12px;
    }}
    .music-actions .small {{
      flex: 1 1 0;
      width: auto;
      min-width: 112px;
      padding-inline: 12px;
      text-align: center;
    }}
    .music-actions .music-action-single[data-action="layout"] {{
      padding-inline: 24px;
    }}
    .lyrics-button:not(:disabled) {{
      border-color: rgba(192, 132, 252, 0.34);
      color: #e9d5ff;
      background: rgba(88, 28, 135, 0.16);
    }}
    .lyrics-modal {{
      position: fixed;
      inset: 0;
      z-index: 50;
      display: none;
      align-items: center;
      justify-content: center;
      padding: 22px;
      background: rgba(2, 6, 23, 0.72);
    }}
    .lyrics-modal.visible {{ display: flex; }}
    .lyrics-dialog {{
      width: min(760px, 100%);
      max-height: min(78vh, 760px);
      display: grid;
      grid-template-rows: auto minmax(0, 1fr);
      overflow: hidden;
      border: 1px solid rgba(226, 232, 240, 0.22);
      border-radius: 18px;
      background: rgba(15, 23, 42, 0.98);
      box-shadow: 0 26px 80px rgba(0, 0, 0, 0.42);
    }}
    .lyrics-dialog-head {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 14px;
      align-items: start;
      padding: 18px 20px 14px;
      border-bottom: 1px solid var(--line);
    }}
    .lyrics-dialog-title {{
      margin: 0;
      font-size: 18px;
      line-height: 1.3;
      overflow-wrap: anywhere;
    }}
    .lyrics-dialog-path {{
      margin-top: 5px;
      color: var(--muted);
      font-size: 12px;
      overflow-wrap: anywhere;
    }}
    .lyrics-source {{
      display: inline-flex;
      align-items: center;
      width: fit-content;
      max-width: 100%;
      min-height: 28px;
      margin-top: 10px;
      padding: 5px 9px;
      border: 1px solid rgba(125, 211, 252, 0.34);
      border-radius: 8px;
      color: #bae6fd;
      background: rgba(14, 116, 144, 0.18);
      font-size: 12px;
      font-weight: 750;
      line-height: 1.35;
      overflow-wrap: anywhere;
    }}
    .lyrics-close {{
      display: inline-grid;
      place-items: center;
      width: 32px;
      min-width: 32px;
      height: 32px;
      padding: 0;
      border: 1px solid rgba(248, 113, 113, 0.3);
      border-radius: 7px;
      color: #fecaca;
      background: rgba(127, 29, 29, 0.28);
      font-size: 20px;
      font-weight: 400;
      line-height: 1;
    }}
    .lyrics-close:focus-visible {{
      outline: none;
      box-shadow: 0 0 0 3px rgba(248, 113, 113, 0.18);
    }}
    .lyrics-close:hover {{
      border-color: rgba(248, 113, 113, 0.5);
      color: #fee2e2;
      background: rgba(127, 29, 29, 0.42);
    }}
    .lyrics-text {{
      min-height: 220px;
      margin: 0;
      padding: 18px 20px 22px;
      overflow: auto;
      white-space: pre-wrap;
      color: #e5e7eb;
      font-family: inherit;
      font-size: 15px;
      line-height: 1.65;
    }}
    .lyrics-text.loading,
    .lyrics-text.error {{
      color: var(--muted);
    }}
    .music-card-status {{ display: none; margin-top: 12px; color: var(--muted); font-size: 13px; }}
    .music-card-status.visible {{ display: block; }}
    .music-card-status.done {{ color: var(--good); }}
    .music-card-status.error {{ color: var(--bad); }}
    .music-card-progress {{
      position: relative;
      height: 8px;
      margin-top: 7px;
      overflow: hidden;
      border-radius: 999px;
      background: rgba(148, 163, 184, 0.18);
    }}
    .music-card-progress span {{
      position: absolute;
      inset: 0 auto 0 0;
      width: 42%;
      border-radius: inherit;
      background: linear-gradient(90deg, var(--accent), #2dd4bf);
      transform: translateX(-100%);
    }}
    .music-card-status.running .music-card-progress span {{
      animation: card-progress 1.1s ease-in-out infinite;
    }}
    .music-card-status.done .music-card-progress span {{
      width: 100%;
      transform: none;
      animation: none;
      background: var(--good);
    }}
    .music-card-status.error .music-card-progress span {{
      width: 100%;
      transform: none;
      animation: none;
      background: var(--bad);
    }}
    .duplicate-card-status {{
      display: none;
      grid-column: 1 / -1;
      color: var(--muted);
      font-size: 13px;
    }}
    .duplicate-card-status.visible {{ display: block; }}
    .duplicate-card-status.done {{ color: var(--good); }}
    .duplicate-card-status.error {{ color: var(--bad); }}
    .duplicate-card-status.running .music-card-progress span {{
      animation: card-progress 1.1s ease-in-out infinite;
    }}
    .duplicate-card-status.done .music-card-progress span {{
      width: 100%;
      transform: none;
      animation: none;
      background: var(--good);
    }}
    .duplicate-card-status.error .music-card-progress span {{
      width: 100%;
      transform: none;
      animation: none;
      background: var(--bad);
    }}
    @keyframes card-progress {{
      0% {{ transform: translateX(-100%); }}
      55% {{ transform: translateX(70%); }}
      100% {{ transform: translateX(240%); }}
    }}
    .music-pills {{ display: flex; flex-wrap: wrap; gap: 7px; margin-top: 12px; }}
    .music-pill {{
      display: inline-flex;
      align-items: center;
      max-width: 100%;
      min-height: 24px;
      padding: 3px 8px;
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 999px;
      color: #dbeafe;
      background: rgba(59, 130, 246, 0.16);
      font-size: 12px;
      font-weight: 600;
      line-height: 1.25;
      overflow-wrap: anywhere;
    }}
    .music-pill-format {{ background: rgba(248, 113, 113, 0.16); color: #fecaca; }}
    .music-pill-bitrate {{ background: rgba(96, 165, 250, 0.16); color: #bfdbfe; }}
    .music-pill-bit_depth {{ background: rgba(167, 139, 250, 0.16); color: #ddd6fe; }}
    .music-pill-sample_rate {{ background: rgba(45, 212, 191, 0.16); color: #ccfbf1; }}
    .music-pill-album {{ background: rgba(251, 191, 36, 0.16); color: #fde68a; }}
    .music-pill-albumartist {{ background: rgba(134, 239, 172, 0.14); color: #bbf7d0; }}
    .music-pill-artist {{ background: rgba(251, 146, 60, 0.14); color: #fed7aa; }}
    .music-pill-genre {{ background: rgba(244, 114, 182, 0.14); color: #fbcfe8; }}
    .music-pill-title {{ background: rgba(125, 211, 252, 0.14); color: #bae6fd; }}
    .music-pill-year {{ background: rgba(203, 213, 225, 0.12); color: #e2e8f0; }}
    .music-pill-cover {{ background: rgba(52, 211, 153, 0.14); color: #a7f3d0; }}
    .music-pill-lyrics {{ background: rgba(192, 132, 252, 0.14); color: #e9d5ff; }}
    .music-pill-status {{ background: rgba(248, 113, 113, 0.16); color: #fecaca; }}
    .group-card {{ margin-top: 14px; border: 1px solid var(--line); border-radius: var(--radius); background: rgba(13, 18, 32, 0.68); overflow: hidden; box-shadow: 0 16px 48px rgba(0, 0, 0, 0.2); backdrop-filter: blur(12px); }}
    .group-card[hidden] {{ display: none; }}
    .group-header {{ width: 100%; display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: center; gap: 16px; padding: 20px 22px; border: 0; background: transparent; color: var(--text); text-align: left; }}
    .group-header:hover {{ background: rgba(255, 255, 255, 0.035); }}
    .group-title {{ font-weight: 700; line-height: 1.35; overflow-wrap: anywhere; }}
    .group-subtitle {{ margin-top: 4px; color: var(--muted); font-size: 13px; }}
    .badges {{ display: flex; gap: 6px; flex-wrap: wrap; justify-content: flex-end; align-items: center; min-width: 0; }}
    .badge {{ display: inline-flex; align-items: center; justify-content: center; min-height: 28px; padding: 5px 10px; border: 1px solid rgba(147, 197, 253, 0.28); border-radius: 999px; color: #dbeafe; background: rgba(59, 130, 246, 0.18); font-size: 12px; font-weight: 700; white-space: nowrap; }}
    .group-body {{ display: none; padding: 18px; border-top: 1px solid var(--line); background: rgba(255, 255, 255, 0.035); }}
    .group-card.open .group-body {{ display: block; }}
    .comparison {{ display: grid; grid-template-columns: minmax(0, 1fr) 92px minmax(0, 1fr); align-items: stretch; gap: 14px; padding: 16px; border: 1px solid var(--line); border-radius: 20px; background: rgba(255, 255, 255, 0.045); }}
    .comparison + .comparison {{ margin-top: 12px; }}
    .track {{ display: flex; flex-direction: column; min-width: 0; padding: 16px; border: 1px solid var(--line); border-radius: 18px; }}
    .track-head {{
      display: grid;
      grid-template-columns: 100px minmax(0, 1fr);
      align-items: start;
      min-width: 0;
      min-height: 116px;
      gap: 16px;
    }}
    .track-meta {{ min-width: 0; overflow: hidden; }}
    .music-cover.duplicate-cover {{ width: 100px; border-radius: 10px; }}
    .duplicate-cover .empty-cover-icon {{ width: 25px; height: 25px; }}
    .keep {{ border-color: rgba(134, 239, 172, 0.28); background: rgba(34, 197, 94, 0.08); }}
    .move {{ border-color: rgba(252, 165, 165, 0.28); background: rgba(239, 68, 68, 0.08); }}
    .track-label {{ display: inline-flex; align-items: center; width: fit-content; min-height: 26px; padding: 0 10px; border-radius: 999px; margin-bottom: 10px; font-size: 12px; font-weight: 800; }}
    .keep .track-label {{ color: #bbf7d0; background: rgba(34, 197, 94, 0.16); }}
    .move .track-label {{ color: #fecaca; background: rgba(239, 68, 68, 0.16); }}
    .track-title {{
      display: -webkit-box;
      overflow: hidden;
      font-weight: 700;
      line-height: 1.35;
      overflow-wrap: anywhere;
      -webkit-box-orient: vertical;
      -webkit-line-clamp: 2;
    }}
    .track-path {{
      display: block;
      max-width: 100%;
      margin-top: 6px;
      overflow: hidden;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.35;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    .audio-player-wrap {{ margin-top: 12px; }}
    .audio-player {{ display: none; }}
    .custom-audio-player {{
      display: grid;
      grid-template-columns: 28px 42px minmax(80px, 1fr) 32px;
      align-items: center;
      gap: 6px;
      width: 100%;
      min-height: 36px;
      padding: 0 6px 0 8px;
      border-radius: 999px;
      background: rgba(15, 23, 42, 0.74);
      color: var(--text);
      border: 1px solid rgba(148, 163, 184, 0.18);
      box-sizing: border-box;
    }}
    .audio-play,
    .audio-mute {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 28px;
      height: 28px;
      min-width: 28px;
      padding: 0;
      border: 0;
      border-radius: 999px;
      background: transparent;
      color: var(--text);
      cursor: pointer;
      justify-self: center;
    }}
    .audio-play:hover,
    .audio-mute:hover {{ background: rgba(148, 163, 184, 0.18); }}
    .audio-play-icon {{ width: 15px; height: 15px; margin-left: 1px; }}
    .audio-play.playing .audio-play-icon {{ display: none; }}
    .audio-play.playing::before {{
      content: "";
      width: 10px;
      height: 12px;
      background:
        linear-gradient(currentColor, currentColor) left center / 3px 12px no-repeat,
        linear-gradient(currentColor, currentColor) right center / 3px 12px no-repeat;
    }}
    .audio-time {{
      min-width: 36px;
      font-size: 14px;
      line-height: 1;
      white-space: nowrap;
    }}
    .audio-seek-wrap {{
      position: relative;
      width: 100%;
      min-width: 0;
      height: 16px;
      display: flex;
      align-items: center;
    }}
    .audio-seek-track {{
      position: relative;
      width: 100%;
      height: 4px;
      overflow: hidden;
      border-radius: 999px;
      background: rgba(148, 163, 184, 0.3);
      pointer-events: none;
    }}
    .audio-seek-fill {{
      display: block;
      width: var(--audio-progress, 0%);
      height: 100%;
      border-radius: inherit;
      background: linear-gradient(90deg, var(--accent), #2dd4bf);
    }}
    .audio-seek {{
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
      margin: 0;
      padding: 0;
      opacity: 0;
      cursor: pointer;
      appearance: none;
      -webkit-appearance: none;
      border: 0;
    }}
    .audio-volume-icon {{
      display: block;
      width: 17px;
      height: 17px;
      flex: 0 0 17px;
      color: #cbd5e1;
    }}
    .audio-speaker {{
      fill: currentColor;
    }}
    .audio-volume-mark {{
      fill: none;
      stroke: currentColor;
      stroke-width: 2.4;
      stroke-linecap: round;
      stroke-linejoin: round;
    }}
    .audio-mute .audio-volume-off {{ display: none; }}
    .audio-mute.muted .audio-volume-on {{ display: none; }}
    .audio-mute.muted .audio-volume-off {{ display: block; }}
    .quality-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; margin-top: 12px; }}
    .quality-grid div {{ padding: 9px; border: 1px solid var(--line); border-radius: 14px; background: rgba(255, 255, 255, 0.045); }}
    .quality-grid span {{ display: block; color: var(--muted); font-size: 11px; }}
    .quality-grid strong {{ display: block; margin-top: 3px; font-size: 13px; overflow-wrap: anywhere; }}
    .divider {{ display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; color: var(--muted); font-size: 12px; }}
    .arrow {{ display: grid; place-items: center; width: 42px; height: 42px; margin-bottom: 8px; border-radius: 999px; border: 1px solid rgba(253, 230, 138, 0.2); color: var(--warning); background: rgba(253, 230, 138, 0.12); }}
    .arrow span {{ position: relative; display: block; width: 16px; height: 2px; border-radius: 999px; background: currentColor; }}
    .arrow span::after {{ content: ""; position: absolute; top: 50%; right: 0; width: 7px; height: 7px; border-top: 2px solid currentColor; border-right: 2px solid currentColor; transform: translateY(-50%) rotate(45deg); transform-origin: center; }}
    .empty {{ display: none; margin-top: 12px; padding: 28px; border: 1px dashed var(--line); border-radius: var(--radius); text-align: center; color: var(--muted); background: rgba(255, 255, 255, 0.045); }}
    .empty.visible {{ display: block; }}
    @media (max-width: 900px) {{
      .summary, .analysis-grid {{ grid-template-columns: 1fr 1fr; }}
      .donut-chart {{ width: 132px; }}
      .comparison {{ grid-template-columns: 1fr; }}
      .divider {{ min-height: 48px; }}
      .arrow {{ transform: rotate(90deg); }}
    }}
    @media (max-width: 560px) {{
      .summary, .analysis-grid, .quality-grid {{ grid-template-columns: 1fr; }}
      .toolbar {{ grid-template-columns: 1fr; }}
      input, select, .search-control, .sort-control, .duplicates-actions .small {{ width: 100%; }}
      .music-card-content {{ grid-template-columns: 1fr; }}
      .music-cover {{ width: min(100%, 180px); }}
      .track-head {{ grid-template-columns: 72px minmax(0, 1fr); gap: 12px; }}
      .music-cover.duplicate-cover {{ width: 72px; }}
      .music-actions {{ display: grid; grid-template-columns: 1fr; width: 100%; }}
      .music-actions .small {{ width: 100%; min-width: 0; }}
      .music-operation-groups {{ grid-template-columns: 1fr; }}
      .music-operation-actions .music-operations-row {{ overflow-x: auto; padding-bottom: 4px; }}
      .music-operation-actions .music-operations-row > button.small {{ flex: 0 0 auto; width: auto; }}
      .music-operations-row > button.small,
      .music-operations-row > .mode-choice {{ width: 100%; }}
      .duplicates-heading {{ align-items: stretch; flex-direction: column; }}
      .group-header {{ grid-template-columns: 1fr; }}
      .badges {{ justify-content: flex-start; }}
    }}
    /* Music application theme */
    :root {{
      --bg:#eeecf3;--panel:#fbfaff;--panel-solid:#fff;--soft:#f2f0f6;--text:#2c2837;--muted:#817b8f;
      --line:rgba(59,50,78,.12);--good:#27845f;--bad:#bd4a5a;--accent:#7359d5;--accent-strong:#6247c7;
      --warning:#a96f1b;--shadow:0 18px 55px rgba(48,39,69,.09);--radius:24px;
    }}
    html {{scroll-behavior:smooth;scroll-padding-top:24px}}
    body {{color:var(--text);background:var(--bg);font-family:"Segoe UI Variable Text","Segoe UI Variable","Segoe UI",Inter,system-ui,sans-serif;-webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale;text-rendering:optimizeLegibility}}
    body::before {{content:"";position:fixed;inset:0;z-index:-1;pointer-events:none;background:radial-gradient(circle at 76% 4%,rgba(153,131,225,.14),transparent 28rem),radial-gradient(circle at 42% 100%,rgba(255,255,255,.72),transparent 36rem)}}
    ::selection {{color:#fff;background:var(--accent)}}
    .app-shell {{display:grid;grid-template-columns:224px minmax(0,1fr);min-height:100vh}}
    .app-sidebar {{position:sticky;top:0;z-index:10;display:flex;flex-direction:column;height:100vh;padding:28px 18px 22px;color:#f7f4ff;background:#2d2936;box-shadow:18px 0 45px rgba(45,41,54,.08)}}
    .app-brand {{display:flex;align-items:center;gap:12px;min-width:0;padding:0 10px 28px;color:inherit;text-decoration:none}}
    .app-brand>span:last-child {{display:grid;min-width:0;gap:3px}}
    .app-brand strong {{overflow:hidden;font-size:15px;letter-spacing:.01em;text-overflow:ellipsis;white-space:nowrap}}
    .app-brand small {{color:#aaa3b7;font-size:11px;letter-spacing:.12em;text-transform:uppercase}}
    .brand-mark {{display:flex;align-items:center;justify-content:center;width:36px;height:36px;flex:0 0 auto;border-radius:11px;color:#2d2936;background:#a58fee;box-shadow:0 9px 24px rgba(165,143,238,.24)}}
    .brand-icon {{width:20px;height:20px}}
    .brand-icon,.nav-icon,.metric-icon svg,.trash-svg,.audio-play-icon,.audio-volume-icon,.empty-cover-icon,.identity-warning-icon {{display:block;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round;shape-rendering:geometricPrecision}}
    .side-nav {{display:grid;gap:7px}}
    .side-nav a {{display:flex;align-items:center;gap:12px;min-height:44px;padding:0 13px;border-radius:12px;color:#aaa4b4;font-size:13px;font-weight:650;text-decoration:none;transition:.16s ease}}
    .side-nav a span {{display:grid;place-items:center;width:22px;height:22px;color:#c6bed5;font-size:18px}}
    .side-nav a:hover {{color:#fff;background:rgba(255,255,255,.075);transform:translateX(2px)}}
    .side-nav a.active {{color:#fff;background:#413b4d;box-shadow:inset 3px 0 #a58fee}}
    .side-nav a.active span {{color:#b6a1f5}}
    .sidebar-note {{display:grid;grid-template-columns:auto minmax(0,1fr);gap:10px;align-items:start;margin-top:auto;padding:14px;border:1px solid rgba(255,255,255,.08);border-radius:14px;background:rgba(255,255,255,.045)}}
    .status-dot {{width:8px;height:8px;margin-top:4px;border-radius:50%;background:#71d3a7;box-shadow:0 0 0 4px rgba(113,211,167,.12)}}
    .sidebar-note div {{display:grid;gap:4px}}.sidebar-note strong {{font-size:12px}}.sidebar-note small {{color:#aaa3b7;font-size:10px;line-height:1.35}}
    .app-workspace {{min-width:0}}
    .topbar {{display:flex;align-items:center;justify-content:space-between;gap:20px;min-height:76px;padding:18px 36px;border-bottom:1px solid var(--line);background:rgba(238,236,243,.88)}}
    .topbar-context {{display:flex;align-items:baseline;gap:10px}}.topbar-context span {{color:var(--muted);font-size:12px}}.topbar-context strong {{font-size:14px}}
    .topbar-status {{display:inline-flex;align-items:center;gap:8px;min-height:34px;padding:0 13px;border:1px solid var(--line);border-radius:999px;color:#625c6f;background:rgba(255,255,255,.66);font-size:12px;font-weight:650}}
    .topbar-status span {{width:7px;height:7px;border-radius:50%;background:#6fc49e}}
    .page {{width:min(1480px,calc(100% - 72px));margin:0 auto;padding:28px 0 70px}}
    .header {{position:relative;isolation:isolate;overflow:hidden;padding:34px;border:1px solid rgba(107,86,172,.11);border-radius:28px;background:linear-gradient(118deg,#d6cff0 0%,#e4e0f4 55%,#d9d3ec 100%);box-shadow:0 22px 60px rgba(71,58,104,.12)}}
    .header::after {{content:"";position:absolute;z-index:-1;top:-110px;right:-70px;width:390px;height:390px;border:1px solid rgba(255,255,255,.4);border-radius:50%;box-shadow:0 0 0 38px rgba(255,255,255,.06),0 0 0 78px rgba(255,255,255,.04)}}
    .hero-layout {{display:grid;grid-template-columns:minmax(0,1.4fr) minmax(280px,.72fr);gap:34px;align-items:center;min-height:250px}}
    .hero-copy {{max-width:720px}}.hero-kicker {{margin-bottom:14px;color:#67579b;font-size:11px;font-weight:800;letter-spacing:.16em;text-transform:uppercase}}
    h1 {{max-width:720px;color:#302a3c;font-family:"Segoe UI Variable Display","Segoe UI Variable Text","Segoe UI",sans-serif;font-size:clamp(36px,5vw,64px);font-weight:650;line-height:1.04;letter-spacing:-.032em}}
    .hero-lead {{max-width:640px;margin:18px 0 0;color:#655e72;font-size:15px;line-height:1.62}}
    .library-path {{display:inline-flex;flex-direction:column;gap:3px;max-width:100%;margin-top:22px;padding:10px 14px;border:1px solid rgba(69,56,99,.1);border-radius:12px;color:#554e61;background:rgba(255,255,255,.42);font-size:11px}}
    .library-path span {{color:#7d748b;font-size:9px;font-weight:800;letter-spacing:.11em;text-transform:uppercase}}
    .hero-visual {{position:relative;min-height:220px}}
    .hero-disc {{position:absolute;top:0;right:26px;display:grid;place-items:center;width:188px;aspect-ratio:1;border-radius:50%;background:repeating-radial-gradient(circle,#34303c 0 2px,#25222d 3px 7px);box-shadow:-18px 24px 40px rgba(54,46,72,.24)}}
    .hero-disc::before {{content:"";width:62px;aspect-ratio:1;border-radius:50%;background:#a58fee;box-shadow:0 0 0 7px #ded8ef}}
    .hero-disc span {{position:absolute;width:14px;aspect-ratio:1;border-radius:50%;background:#2d2936}}
    .hero-track {{position:absolute;right:104px;bottom:0;display:grid;gap:4px;min-width:180px;padding:15px 18px;border:1px solid rgba(255,255,255,.58);border-radius:16px;color:#fff;background:rgba(67,58,84,.88);box-shadow:0 14px 35px rgba(53,45,69,.2);backdrop-filter:blur(12px)}}
    .hero-track small {{color:#cfc8dc;font-size:10px}}.hero-track strong {{font-size:15px}}
    .hero-wave {{position:absolute;right:5px;bottom:18px;display:flex;align-items:center;gap:3px;height:38px}}
    .hero-wave i {{width:3px;border-radius:4px;background:#7359d5}}.hero-wave i:nth-child(1),.hero-wave i:nth-child(7) {{height:10px}}
    .hero-wave i:nth-child(2),.hero-wave i:nth-child(6) {{height:19px}}.hero-wave i:nth-child(3),.hero-wave i:nth-child(5) {{height:29px}}.hero-wave i:nth-child(4) {{height:38px}}
    .summary {{grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-top:28px}}
    .metric {{position:relative;min-height:104px;padding:18px;border:1px solid rgba(70,57,100,.1);border-radius:18px;color:#322d3c;background:rgba(255,255,255,.72);box-shadow:none}}
    .metric .metric-icon {{position:absolute;top:15px;right:15px;display:grid;place-items:center;width:34px;height:34px;border-radius:10px;color:#7158c4;background:#eeeafb}}
    .metric-icon svg {{width:20px;height:20px}}.metric-label {{max-width:calc(100% - 44px);color:#797284;font-size:11px;font-weight:650}}.metric strong {{margin-top:14px;color:#312c3a;font-size:28px;line-height:1}}
    .metric-primary {{grid-column:span 2;color:#322d3c;background:rgba(255,255,255,.82)}}.metric-primary .metric-icon {{color:#6749cb;background:#e8e0fb}}
    .metric-primary .metric-label {{color:#706879}}.metric-primary strong {{color:#312c3a;font-size:34px}}.metric-alert .metric-icon {{color:#a85f6d;background:#f6dfe4}}
    .section-heading {{display:flex;align-items:end;justify-content:space-between;gap:24px;margin:38px 0 15px;scroll-margin-top:24px}}
    .section-heading span {{display:block;margin-bottom:6px;color:var(--accent);font-size:10px;font-weight:800;letter-spacing:.14em;text-transform:uppercase}}
    .section-heading h2 {{margin:0;font-size:clamp(24px,3vw,34px);letter-spacing:-.03em}}.section-heading p {{margin:0 0 3px;color:var(--muted);font-size:12px}}
    .analysis-grid {{grid-template-columns:repeat(12,minmax(0,1fr));gap:12px;margin-top:0}}
    .panel {{grid-column:span 2;padding:20px;border:1px solid var(--line);border-radius:20px;color:var(--text);background:rgba(255,255,255,.82);box-shadow:0 12px 38px rgba(46,38,64,.055);backdrop-filter:none}}
    .panel.summary-panel {{grid-column:span 4}}.artist-panel {{grid-column:span 3}}.genre-panel {{grid-column:span 2}}.years-panel {{grid-column:span 3}}.panel h2,.section-title {{color:var(--text);font-size:18px;font-weight:650;letter-spacing:-.012em}}
    .panel-body {{margin-top:17px}}.note,.chart-note,.operation-status {{color:var(--muted)}}.summary-main {{border-color:var(--line);line-height:1.7}}
    .summary-subtitle {{color:var(--text);font-size:13px}}.format-row,.artist-row,.genre-row,.year-row {{color:#5f5869;font-size:12px}}
    .format-bar {{height:7px;background:#ebe8f0}}.format-bar span {{background:linear-gradient(90deg,#7e65d9,#b5a4ee)}}
    .donut-chart {{box-shadow:none}}.donut-hole {{color:var(--text);background:#fff;box-shadow:0 0 0 1px var(--line)}}
    .chart-legend {{scrollbar-color:#c9c3d2 transparent}}.years-panel .panel-body {{margin-top:14px}}.years-panel .chart-note {{margin-bottom:0}}
    .heatmap-panel {{margin-top:12px;padding:24px;border-color:var(--line);background:#34303d;box-shadow:0 18px 48px rgba(44,39,53,.12)}}
    .heatmap-heading h2 {{color:#fff}}.heatmap-heading p {{color:#aaa3b4}}
    .music-section {{margin-top:34px;padding:24px;border:1px solid var(--line);border-radius:24px;background:rgba(255,255,255,.66);box-shadow:var(--shadow);scroll-margin-top:24px}}
    .duplicates-heading {{margin-top:34px}}.music-section .duplicates-heading {{margin-top:0}}.section-title {{margin-top:0;font-size:25px}}
    input,select,button.small {{min-height:42px;height:42px;border-color:var(--line);border-radius:12px;color:#443e4e;background-color:#fff;box-shadow:none}}
    .search-placeholder {{color:#8d8696}}.search-control input:focus+.search-placeholder {{color:#9b94a5}}
    input:focus,select:focus,button.small:focus-visible {{border-color:rgba(115,89,213,.55);box-shadow:0 0 0 3px rgba(115,89,213,.12)}}
    select {{background-image:linear-gradient(45deg,transparent 50%,#746d7e 50%),linear-gradient(135deg,#746d7e 50%,transparent 50%)}}
    .sort-control::before {{color:var(--accent)}}button.small {{font-size:12px;font-weight:700}}
    button.small:hover:not(:disabled) {{border-color:rgba(115,89,213,.32);color:var(--accent-strong);background:#f3f0fb}}
    .music-operations {{padding:12px;border-color:var(--line);border-radius:18px;background:#f1eff5}}
    .music-operation-groups {{grid-template-columns:minmax(250px,.65fr) minmax(0,2fr)}}.music-operation-block {{border-color:transparent;border-radius:14px;background:rgba(255,255,255,.72)}}
    .music-operations-title {{color:#5d5667;font-size:12px}}.mode-choice {{border-color:var(--line);color:#5b5464;background:#fff;font-size:12px}}
    .mode-choice:has(input:checked) {{border-color:rgba(115,89,213,.32);color:#5e47b8;background:#eee9fb}}.operation-status {{padding:3px 4px 0;font-size:11px}}
    .music-operation-actions .music-operations-row {{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));overflow:visible}}.music-operation-actions .music-operations-row>button.small {{width:100%;height:auto;min-height:42px;white-space:normal;line-height:1.2}}
    .toolbar {{grid-template-columns:minmax(190px,1.25fr) repeat(4,minmax(120px,1fr));gap:8px}}.music-list {{gap:10px}}
    .music-card {{padding:15px 52px 15px 15px;border-color:var(--line);border-radius:17px;color:var(--text);background:#fff;box-shadow:0 8px 26px rgba(53,44,72,.045);transition:.16s ease}}
    .music-card:hover {{transform:translateY(-1px);border-color:rgba(115,89,213,.22);box-shadow:0 13px 34px rgba(53,44,72,.075)}}
    .music-card-content {{grid-template-columns:100px minmax(0,1fr);gap:16px}}.music-cover {{width:100px;border-color:var(--line);border-radius:13px;color:var(--muted);background:#efedf3}}
    .empty-cover-icon {{color:var(--accent)}}.music-title {{color:#332e3b;font-size:15px}}.music-path,.track-path {{color:#8b8494}}
    .music-actions {{gap:7px}}.music-actions .small {{color:#625a70;background:#f2f0f6}}.music-trash-icon {{border-color:#ecd2d8;border-radius:9px;color:#b75464;background:#fbf1f3}}
    .music-trash-icon:hover {{border-color:#dca9b3;color:#994455;background:#f6dfe4}}.music-card-identity-mismatch {{border-color:#e6c97e;background:#fffaf0;box-shadow:none}}
    .identity-warning {{border-color:#ead496;color:#815b1c;background:#fff4d8}}.identity-warning-icon {{display:inline-block;width:16px;height:16px;margin-right:5px;vertical-align:-3px}}.music-card-duplicate {{border-color:#e6bd79;background:#fffaf2}}.music-card-unreadable {{border-color:#e5aeb8;background:#fff5f6}}
    .music-pill {{color:#625b70!important;background:#efedf4!important}}.music-pill-format,.music-pill-bitrate,.music-pill-bit_depth,.music-pill-sample_rate {{color:#5c47ad!important;background:#eee9fb!important}}
    .music-pill-cover {{color:#267454!important;background:#e2f4ec!important}}.music-pill-lyrics {{color:#7a4d98!important;background:#f1e5f7!important}}.music-pill-status {{color:#a34b5b!important;background:#fae7ea!important}}
    .quarantine-panel {{border-color:#e8c4cb;color:#8f4654;background:#fff5f6}}.quarantine-panel p,.copy-status {{color:#954c59}}.global-progress {{background:#f3dde1}}
    .global-progress span {{background:linear-gradient(90deg,#c45b6d,#df8f75)}}.danger-button {{border-color:#e9c2c9!important;color:#a74455!important;background:#fff6f7!important}}
    .danger-button:hover {{border-color:#daaab3!important;color:#8e3547!important;background:#fbe9ec!important}}.quarantine-one {{border-color:#bfe3d3!important;color:#267255!important;background:#f0faf6!important}}
    .quarantine-one:hover {{border-color:#9dd4bc!important;color:#1f6048!important;background:#e5f6ee!important}}
    .group-card {{margin-top:10px;border-color:var(--line);border-radius:18px;color:var(--text);background:#fff;box-shadow:0 10px 32px rgba(51,43,67,.055);backdrop-filter:none}}
    .group-header {{color:var(--text)}}.group-header:hover {{background:#f7f5fa}}.group-subtitle {{color:var(--muted)}}.badge {{border-color:#d9d0f2;color:#5c48aa;background:#f0ecfb}}
    .group-body {{border-color:var(--line);background:#f4f2f7}}.comparison {{border-color:var(--line);background:#fff}}.track {{border-color:var(--line)}}
    .keep {{border-color:#c4e2d5;background:#f3faf7}}.move {{border-color:#ebcbd1;background:#fff7f8}}.keep .track-label {{color:#267255;background:#dff3ea}}.move .track-label {{color:#a04555;background:#f8e2e6}}
    .custom-audio-player {{border-color:var(--line);color:var(--text);background:#eeeaf4}}.audio-play:hover,.audio-mute:hover {{background:#ddd7e6}}.audio-volume-icon {{color:#6d6577}}
    .audio-seek-track {{background:#d3ccdc}}.audio-seek-fill {{background:linear-gradient(90deg,#7359d5,#a58fee)}}.quality-grid div {{border-color:var(--line);background:rgba(255,255,255,.72)}}
    .divider {{color:var(--muted)}}.arrow {{border-color:#e7d5b4;color:#9e6b1f;background:#fff6e5}}.empty {{border-color:#cfc9d7;color:var(--muted);background:rgba(255,255,255,.6)}}
    .lyrics-modal {{background:rgba(39,34,48,.62);backdrop-filter:blur(8px)}}.lyrics-dialog {{border-color:var(--line);color:var(--text);background:#fbfaff;box-shadow:0 28px 80px rgba(27,22,35,.28)}}
    .lyrics-dialog-head {{border-color:var(--line)}}.lyrics-dialog-title {{color:var(--text)}}.lyrics-dialog-path,.lyrics-source {{color:var(--muted)}}.lyrics-close {{color:#5e5769;background:#efedf3}}.lyrics-text {{color:#453f4f;background:#fff}}
    @media (max-width:1180px) {{
      .app-shell {{grid-template-columns:82px minmax(0,1fr)}}.app-sidebar {{padding-inline:13px}}.app-brand {{justify-content:center;padding-inline:0}}.app-brand>span:last-child,.sidebar-note div {{display:none}}
      .side-nav a {{justify-content:center;padding:0;font-size:0}}.side-nav a span {{font-size:19px}}.sidebar-note {{grid-template-columns:1fr;place-items:center;padding:14px 8px}}
      .panel,.panel.summary-panel {{grid-column:span 6}}.hero-layout {{grid-template-columns:minmax(0,1fr) 280px}}.toolbar {{grid-template-columns:repeat(2,minmax(0,1fr))}}.search-control {{grid-column:span 2}}
    }}
    @media (max-width:820px) {{
      .app-shell {{display:block}}.app-sidebar {{position:relative;width:100%;height:auto;padding:14px 18px;flex-direction:row;align-items:center;gap:18px}}.app-brand {{padding:0}}.app-brand>span:last-child {{display:grid}}
      .side-nav {{display:flex;margin-left:auto}}.side-nav a {{width:40px;min-height:40px}}.sidebar-note {{display:none}}.topbar {{padding:15px 20px}}.page {{width:min(100% - 32px,760px);padding-top:18px}}
      .header {{padding:25px}}.hero-layout {{grid-template-columns:1fr;min-height:0}}.hero-visual {{display:none}}.summary {{grid-template-columns:repeat(2,minmax(0,1fr))}}.metric-primary {{grid-column:span 2}}
      .section-heading {{align-items:flex-start;flex-direction:column;gap:6px}}.analysis-grid {{grid-template-columns:1fr}}.panel,.panel.summary-panel {{grid-column:auto}}.music-section {{padding:18px}}
      .music-operation-groups {{grid-template-columns:1fr}}.music-operation-actions .music-operations-row {{grid-template-columns:repeat(2,minmax(0,1fr))}}.comparison {{grid-template-columns:1fr}}.divider {{min-height:46px}}.arrow {{transform:rotate(90deg)}}
    }}
    @media (max-width:560px) {{
      .app-sidebar {{overflow-x:auto}}.app-brand>span:last-child {{display:none}}.side-nav {{min-width:max-content}}.topbar-status {{display:none}}.page {{width:min(100% - 20px,540px)}}
      .header {{padding:20px;border-radius:22px}}h1 {{font-size:37px}}.hero-lead {{font-size:13px}}.summary {{grid-template-columns:1fr}}.metric-primary {{grid-column:auto}}.metric {{min-height:92px}}
      .toolbar,.search-control {{grid-template-columns:1fr;grid-column:auto}}.music-operation-actions .music-operations-row {{grid-template-columns:1fr}}.music-card {{padding-right:48px}}.music-card-content {{grid-template-columns:1fr}}.music-cover {{width:min(100%,160px)}}.music-section {{padding:14px}}
    }}
    /* Visual consistency corrections */
    .app-sidebar {{color:#383241;background:#fbfaff;border-right:1px solid var(--line);box-shadow:8px 0 30px rgba(50,42,66,.035)}}
    .app-brand {{color:#302a3a}}.app-brand small {{color:#91899d}}
    .brand-mark {{color:#fff;background:#8f73e2;box-shadow:0 9px 24px rgba(143,115,226,.22)}}
    .side-nav a {{color:#7c7488}}.side-nav a:hover {{color:#5c48ad;background:#f1edf9;transform:none}}
    .side-nav a.active {{color:#5943ae;background:#ebe5fa;box-shadow:none}}
    .side-nav a span {{display:block;width:auto;height:auto;color:inherit;font-size:13px}}
    .nav-icon {{width:20px;height:20px;flex:0 0 auto}}
    .sidebar-note {{border-color:var(--line);color:#4d4657;background:#f2eff7}}.sidebar-note small {{color:#8d8598}}
    .sidebar-note.mode-real {{border-color:#ead3a6;color:#76531d;background:#fff8ea}}
    .sidebar-note.mode-real .status-dot {{background:#d39a3c;box-shadow:0 0 0 4px rgba(211,154,60,.14)}}
    .sidebar-note.mode-real small {{color:#98713a}}
    .page {{padding-top:30px}}.panel {{min-width:0;border-radius:22px;background:#fff}}
    .analysis-grid {{align-items:stretch}}.artist-row {{grid-template-columns:minmax(0,1fr) minmax(42px,.62fr) 30px;gap:6px}}
    .format-count {{min-width:0;color:#817a8d;font-variant-numeric:tabular-nums;text-align:right}}
    .chart-legend {{padding-right:7px;scrollbar-gutter:auto}}.chart-legend-row {{grid-template-columns:9px minmax(0,1fr) 32px 38px;gap:6px;font-size:12px}}
    .chart-legend-row strong,.chart-legend-row span:last-child {{font-variant-numeric:tabular-nums;text-align:right}}
    .donut-hole strong,.metric strong,.note strong,.heatmap-cell {{font-variant-numeric:tabular-nums}}
    .year-chart {{height:196px}}.year-chart-label {{color:#6d6579;font-size:10px;font-weight:650}}
    .year-chart-value {{color:#312a3c;font-size:11px;font-weight:800;font-variant-numeric:tabular-nums}}
    .heatmap-panel {{color:var(--text);background:#fff;box-shadow:0 12px 38px rgba(46,38,64,.055)}}
    .heatmap-heading h2 {{color:var(--text)}}.heatmap-heading p {{color:var(--muted)}}
    .heatmap-grid {{grid-template-columns:minmax(150px,1.15fr) repeat(var(--heatmap-columns),minmax(82px,1fr));gap:1px;padding:1px;border:1px solid #ece8f2;border-radius:16px;background:#ece8f2}}
    .heatmap-corner,.heatmap-column,.heatmap-genre,.heatmap-cell {{border:0;text-shadow:none}}
    .heatmap-corner,.heatmap-column {{color:#5c5567;background:#f7f5fa}}
    .heatmap-genre {{padding-left:12px;color:#4b4555;background:#fbfaff}}
    .heatmap-cell {{color:#40394c;font-weight:700}}
    .heatmap-scale {{color:#8b8495}}.heatmap-scale-bar {{background:linear-gradient(90deg,#f4f1fb,#e5def8,#d1c5f2,#bdaaea,#a38de1);box-shadow:inset 0 0 0 1px rgba(83,65,125,.08)}}
    @media (max-width:1400px) {{
      .analysis-grid {{grid-template-columns:repeat(6,minmax(0,1fr))}}.panel {{grid-column:span 2}}.panel.summary-panel {{grid-column:span 6}}
    }}
    @media (max-width:1180px) {{
      .side-nav a span {{display:none}}.nav-icon {{width:20px;height:20px}}
      .analysis-grid {{grid-template-columns:repeat(2,minmax(0,1fr))}}.panel {{grid-column:auto}}.panel.summary-panel {{grid-column:span 2}}
    }}
    @media (max-width:820px) {{
      .analysis-grid {{grid-template-columns:1fr}}.panel,.panel.summary-panel {{grid-column:auto}}
      .app-sidebar {{border-right:0;border-bottom:1px solid var(--line)}}
    }}
  </style>
</head>
<body>
  <div class="app-shell">
    <aside class="app-sidebar" aria-label="Навигация по отчёту">
      <a class="app-brand" href="#overview" aria-label="Моя медиатека — к обзору">
        <span class="brand-mark">{lucide_icon("audio-lines", "brand-icon")}</span>
        <span><strong>Моя медиатека</strong><small>Music Library</small></span>
      </a>
      <nav class="side-nav">
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
      <div class="sidebar-note" id="processingModeNote" aria-live="polite">
        <span class="status-dot" aria-hidden="true"></span>
        <div><strong id="processingModeTitle">Режим проверки</strong><small id="processingModeDetail">Изменения и удаление отключены</small></div>
      </div>
    </aside>
    <div class="app-workspace">
  <main class="page">
    <section class="header" id="overview">
      <div class="hero-layout">
        <div class="hero-copy">
          <div class="hero-kicker">Ваша коллекция · в одном ритме</div>
          <h1>Музыкальная библиотека</h1>
          <p class="hero-lead">Слушайте, приводите коллекцию в порядок и находите лучшие версии треков в едином пространстве.</p>
          <div class="library-path"><span>Текущая папка</span>{library_path}</div>
        </div>
        <div class="hero-visual" aria-hidden="true">
          <div class="hero-disc"><span></span></div>
          <div class="hero-wave"><i></i><i></i><i></i><i></i><i></i><i></i><i></i></div>
          <div class="hero-track"><small>Сейчас в коллекции</small><strong>{format_number(library.get("total_files"))} треков</strong></div>
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

    <div class="section-heading" id="insights"><div><span>Статистика коллекции</span><h2>Всё важное — с первого взгляда</h2></div><p>Сводка по качеству, исполнителям и метаданным</p></div>
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
