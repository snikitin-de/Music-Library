"""
Generate a standalone HTML report from duplicate CSV report
and optional full music library analysis.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath

from mutagen import File as MutagenFile


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

MAX_DISPLAY_TAG_LENGTH = 120

DISPLAY_TAGS = [
    ("album", ["album"], "альбом", "album"),
    ("albumartist", ["albumartist"], "исполнитель альбома", "albumartist"),
    ("artist", ["artist"], "исполнитель", "artist"),
    ("genre", ["genre"], "жанр", "genre"),
    ("title", ["title"], "название", "title"),
    ("year", ["year", "date"], "год", "year"),
]

GENRE_SPLIT_RE = re.compile(r"\s*(?:,|;|/|\|)\s*")


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


def analyze_library(library: Path | None) -> dict:
    if library is None:
        return {
            "enabled": False,
            "path": "",
            "total_files": "—",
            "audio_files": "—",
            "albums": "—",
            "artists": "—",
            "formats": {},
            "genres": {},
            "years": {},
            "unreadable_files": "—",
            "tracks": [],
        }

    if not library.exists():
        raise SystemExit(f"Music library folder does not exist: {library}")

    total_files = 0
    audio_files = 0
    unreadable_files = 0
    albums: set[str] = set()
    artists: set[str] = set()
    formats: Counter[str] = Counter()
    tracks: list[dict] = []

    for path in library.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in AUDIO_EXTENSIONS:
            continue

        total_files += 1
        formats[path.suffix.lower().lstrip(".").upper()] += 1

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
                        make_display_tag("статус", "не читается", "status"),
                    ],
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
                        make_display_tag("статус", "не распознан", "status"),
                    ],
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
        if track_artist:
            artists.add(normalize(track_artist))
        if album:
            albums.add(f"{normalize(artist)} | {normalize(album)}")

        track_tags = [
            make_display_tag("формат", path.suffix.lower().lstrip(".").upper(), "format"),
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
        "genres": collect_genres_from_tracks(tracks),
        "years": collect_years_from_tracks(tracks),
        "unreadable_files": unreadable_files,
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


def build_payload(rows: list[ReportRow], library_stats: dict) -> dict:
    groups: dict[str, list[dict]] = defaultdict(list)

    for row in rows:
        kept_q = parse_quality(row.kept_quality)
        moved_q = parse_quality(row.moved_quality)
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
            }
        )

    return {
        "summary": {
            "groups": len(groups),
            "duplicates": len(rows),
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
    }
    return mapping.get((reason or "").strip().lower(), reason or "ниже оценка качества")


def render_quality(quality: dict[str, str]) -> str:
    fmt = html.escape(quality.get("format", "—").upper() or "—")
    bit_depth = html.escape(quality.get("bit_depth", "—") or "—")
    tag_score = html.escape(quality.get("tag_score", "—") or "—")
    cover = "Да" if quality.get("cover", "").lower() == "true" else "Нет"

    items = [
        ("Формат", fmt),
        ("Битрейт", html.escape(format_bitrate(quality.get("bitrate")))),
        ("Разрядность", bit_depth),
        ("Частота дискретизации", html.escape(format_sample_rate(quality.get("sample_rate")))),
        ("Теги", f"{tag_score}/5"),
        ("Обложка", cover),
        ("Размер", html.escape(format_size(quality.get("size")))),
    ]

    return '<div class="quality-grid">' + "".join(
        f"<div><span>{label}</span><strong>{value}</strong></div>" for label, value in items
    ) + "</div>"


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


def render_genre_bars(genres: dict) -> str:
    if not genres:
        return '<div class="format-empty">Жанры не определены.</div>'

    max_count = max(genres.values()) if genres else 1
    parts = []
    for genre, count in list(genres.items())[:12]:
        width = max(4, round(count / max_count * 100))
        parts.append(
            f"""
            <div class="genre-row">
              <div class="genre-name" title="{html.escape(genre)}">{html.escape(genre)}</div>
              <div class="format-bar"><span style="width:{width}%"></span></div>
              <div class="format-count">{format_number(count)}</div>
            </div>
            """
        )
    return "".join(parts)


def render_year_bars(years: dict) -> str:
    if not years:
        return '<div class="format-empty">Годы не определены.</div>'

    max_count = max(years.values()) if years else 1
    parts = []
    for year, count in years.items():
        width = max(4, round(count / max_count * 100))
        parts.append(
            f"""
            <div class="year-row">
              <div class="year-name">{html.escape(year)}</div>
              <div class="format-bar"><span style="width:{width}%"></span></div>
              <div class="format-count">{format_number(count)}</div>
            </div>
            """
        )
    return "".join(parts)


def render_music_list(tracks: list[dict], duplicate_paths: set[str] | None = None) -> str:
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
        if track.get("path", "") in duplicate_paths:
            card_classes.append("music-card-duplicate")
        if "не читается" in status_text or "не распознан" in status_text:
            card_classes.append("music-card-unreadable")
        items.append(
            f"""
            <article class="{html.escape(" ".join(card_classes))}" data-music-search="{html.escape(search_text)}" data-sort-name="{html.escape(track.get("name", "").lower())}" data-sort-artist="{html.escape(sort_artist)}" data-sort-album="{html.escape(sort_album)}" data-sort-year="{html.escape(sort_year)}" data-sort-format="{html.escape(sort_format)}" {tag_attributes}>
              <div class="music-title">{html.escape(track.get("name", ""))}</div>
              <div class="music-path" title="{html.escape(track.get("path", ""))}">{html.escape(track.get("folder", ""))}</div>
              <div class="music-pills">{tags}</div>
            </article>
            """
        )
    return "".join(items)


def render_html(payload: dict) -> str:
    json_payload = json.dumps(payload, ensure_ascii=False)
    summary = payload["summary"]
    library = payload["library"]
    genres = library.get("genres") or collect_genres_from_tracks(library.get("tracks", []))
    library["genres"] = genres
    years = library.get("years") or collect_years_from_tracks(library.get("tracks", []))
    library["years"] = years
    library_raw_path = library.get("path", "")
    library_path = html.escape(library_raw_path)
    quarantine_path = ""
    if library_raw_path:
        quarantine_path = str(PureWindowsPath(library_raw_path).parent / "Duplicates_To_Check")
    quarantine_command = (
        f'python scripts\\find_duplicates.py --library "{library_raw_path}" '
        f'--quarantine "{quarantine_path}" --report reports\\duplicates.csv'
    )
    duplicate_paths = {
        path
        for group in payload.get("groups", [])
        for item in group.get("items", [])
        for path in (item.get("kept_file", ""), item.get("moved_file", ""))
        if path
    }
    music_html = render_music_list(library.get("tracks", []), duplicate_paths)
    groups_html = []

    for group in payload["groups"]:
        items_html = []
        for item in group["items"]:
            items_html.append(
                f"""
                <div class="comparison">
                  <div class="track keep">
                    <div class="track-label">Оставлен</div>
                    <div class="track-title">{html.escape(item["kept_name"])}</div>
                    <div class="track-path" title="{html.escape(item["kept_file"])}">{html.escape(item["kept_folder"])}</div>
                    {render_quality(item["kept_quality"])}
                  </div>
                  <div class="divider">
                    <div class="arrow">→</div>
                    <div class="reason">{html.escape(translate_reason(item["reason"]))}</div>
                  </div>
                  <div class="track move">
                    <div class="track-label">В карантин</div>
                    <div class="track-title">{html.escape(item["moved_name"])}</div>
                    <div class="track-path" title="{html.escape(item["moved_file"])}">{html.escape(item["moved_folder"])}</div>
                    {render_quality(item["moved_quality"])}
                    <button class="small danger-button quarantine-one" type="button" data-moved-file="{html.escape(item["moved_file"])}">Переместить этот файл</button>
                  </div>
                </div>
                """
            )

        badges = "".join(f'<span class="badge">{html.escape(fmt)}</span>' for fmt in group["formats"])
        groups_html.append(
            f"""
            <section class="group-card" data-search="{html.escape(group["name"].lower())}" data-count="{group["duplicates_count"]}">
              <button class="group-header" type="button">
                <div>
                  <div class="group-title">{html.escape(group["name"])}</div>
                  <div class="group-subtitle">Худших дублей: {group["duplicates_count"]}</div>
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
  <style>
    :root {{
      --bg: #111827;
      --panel: #ffffff;
      --soft: #f3f4f6;
      --text: #111827;
      --muted: #6b7280;
      --line: #d1d5db;
      --good: #0f766e;
      --bad: #b91c1c;
      --accent: #2563eb;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--text);
      background: #eef2f7;
      font-family: Segoe UI, Arial, sans-serif;
    }}
    .page {{ width: min(1240px, calc(100% - 32px)); margin: 0 auto; padding: 32px 0 56px; }}
    .header {{ padding: 24px; border: 1px solid var(--line); border-radius: 8px; background: var(--panel); }}
    h1 {{ margin: 0; font-size: 32px; line-height: 1.15; }}
    .lead {{ margin: 10px 0 0; color: var(--muted); line-height: 1.5; }}
    .library-path {{ margin-top: 12px; overflow-wrap: anywhere; color: var(--muted); font-size: 13px; }}
    .summary {{ display: grid; grid-template-columns: repeat(4, minmax(140px, 1fr)); gap: 12px; margin-top: 18px; }}
    .metric {{ padding: 16px; border: 1px solid var(--line); border-radius: 8px; background: var(--soft); }}
    .metric span {{ display: block; color: var(--muted); font-size: 13px; }}
    .metric strong {{ display: block; margin-top: 6px; font-size: 28px; }}
    .analysis-grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; margin-top: 14px; }}
    .panel {{ padding: 18px; border: 1px solid var(--line); border-radius: 8px; background: var(--panel); }}
    .panel h2, .section-title {{ margin: 0 0 12px; font-size: 20px; }}
    .note {{ color: var(--muted); line-height: 1.55; }}
    .format-row {{ display: grid; grid-template-columns: 60px 1fr 60px; gap: 10px; align-items: center; margin-top: 10px; }}
    .genre-row {{ display: grid; grid-template-columns: minmax(90px, 150px) 1fr 44px; gap: 10px; align-items: center; margin-top: 10px; }}
    .genre-name {{ min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
    .year-row {{ display: grid; grid-template-columns: 54px 1fr 44px; gap: 10px; align-items: center; margin-top: 10px; }}
    .format-bar {{ height: 10px; border-radius: 999px; background: #e5e7eb; overflow: hidden; }}
    .format-bar span {{ display: block; height: 100%; background: var(--accent); }}
    .format-count {{ text-align: right; color: var(--muted); }}
    .toolbar {{ display: flex; gap: 10px; flex-wrap: wrap; margin-top: 16px; }}
    input, select, button.small {{
      height: 42px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      color: var(--text);
      padding: 0 12px;
      font: inherit;
    }}
    input {{ flex: 1 1 300px; }}
    select {{
      flex: 0 0 250px;
      padding-right: 42px;
      appearance: none;
      background-image:
        linear-gradient(45deg, transparent 50%, #111827 50%),
        linear-gradient(135deg, #111827 50%, transparent 50%);
      background-position:
        calc(100% - 19px) 17px,
        calc(100% - 13px) 17px;
      background-size: 6px 6px, 6px 6px;
      background-repeat: no-repeat;
    }}
    button {{ cursor: pointer; }}
    .section-title {{ margin-top: 24px; }}
    .music-toolbar {{ margin: 24px 0 12px; }}
    .duplicates-heading {{ display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-top: 24px; }}
    .duplicates-heading .section-title {{ margin: 0; }}
    .duplicates-actions {{ display: flex; gap: 10px; flex-wrap: wrap; justify-content: flex-end; }}
    .danger-button {{ border-color: #dc2626 !important; color: #fff !important; background: #dc2626 !important; }}
    .danger-button:hover {{ background: #b91c1c !important; }}
    .quarantine-one {{ margin-top: 12px; width: 100%; }}
    .quarantine-panel {{
      display: none;
      margin: 12px 0;
      padding: 14px;
      border: 1px solid #fecaca;
      border-radius: 8px;
      background: #fff7f7;
    }}
    .quarantine-panel.visible {{ display: block; }}
    .quarantine-panel p {{ margin: 0 0 10px; color: #991b1b; line-height: 1.45; }}
    .quarantine-panel p:last-child {{ margin-bottom: 0; }}
    .quarantine-command {{ display: block; padding: 10px; border: 1px solid #fecaca; border-radius: 6px; background: #fff; overflow-x: auto; white-space: pre; }}
    .copy-status {{ margin-left: 10px; color: #991b1b; font-size: 13px; }}
    .music-list {{ display: grid; gap: 10px; }}
    .music-card {{ padding: 14px; border: 1px solid var(--line); border-radius: 8px; background: var(--panel); }}
    .music-card-duplicate {{ border-color: #f59e0b; background: #fffbeb; }}
    .music-card-unreadable {{ border-color: #ef4444; background: #fef2f2; }}
    .music-card[hidden] {{ display: none; }}
    .music-title {{ font-weight: 750; overflow-wrap: anywhere; }}
    .music-path {{ margin-top: 5px; color: var(--muted); font-size: 12px; overflow-wrap: anywhere; }}
    .music-pills {{ display: flex; flex-wrap: wrap; gap: 7px; margin-top: 12px; }}
    .music-pill {{
      display: inline-flex;
      align-items: center;
      max-width: 100%;
      min-height: 24px;
      padding: 3px 8px;
      border: 0;
      border-radius: 4px;
      color: #1f2937;
      background: #eef2ff;
      font-size: 12px;
      font-weight: 600;
      line-height: 1.25;
      overflow-wrap: anywhere;
    }}
    .music-pill-format {{ background: #fee2e2; color: #7f1d1d; }}
    .music-pill-bitrate {{ background: #dbeafe; color: #1e3a8a; }}
    .music-pill-bit_depth {{ background: #ede9fe; color: #4c1d95; }}
    .music-pill-sample_rate {{ background: #ccfbf1; color: #134e4a; }}
    .music-pill-album {{ background: #fef3c7; color: #78350f; }}
    .music-pill-albumartist {{ background: #dcfce7; color: #14532d; }}
    .music-pill-artist {{ background: #ffedd5; color: #7c2d12; }}
    .music-pill-genre {{ background: #fce7f3; color: #831843; }}
    .music-pill-title {{ background: #e0f2fe; color: #075985; }}
    .music-pill-year {{ background: #e5e7eb; color: #374151; }}
    .music-pill-status {{ background: #fee2e2; color: #991b1b; }}
    .group-card {{ margin-top: 12px; border: 1px solid var(--line); border-radius: 8px; background: var(--panel); overflow: hidden; }}
    .group-card[hidden] {{ display: none; }}
    .group-header {{ width: 100%; display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: center; gap: 16px; padding: 18px; border: 0; background: transparent; color: var(--text); text-align: left; }}
    .group-title {{ font-weight: 700; line-height: 1.35; overflow-wrap: anywhere; }}
    .group-subtitle {{ margin-top: 4px; color: var(--muted); font-size: 13px; }}
    .badges {{ display: flex; gap: 6px; flex-wrap: wrap; justify-content: flex-end; align-items: center; min-width: 0; }}
    .badge {{ display: inline-flex; align-items: center; justify-content: center; min-height: 26px; padding: 5px 9px; border-radius: 4px; color: #1e3a8a; background: #dbeafe; font-size: 12px; font-weight: 700; white-space: nowrap; }}
    .group-body {{ display: none; padding: 16px; border-top: 1px solid var(--line); background: #fafafa; }}
    .group-card.open .group-body {{ display: block; }}
    .comparison {{ display: grid; grid-template-columns: minmax(0, 1fr) 92px minmax(0, 1fr); gap: 14px; padding: 14px; border: 1px solid var(--line); border-radius: 8px; background: #fff; }}
    .comparison + .comparison {{ margin-top: 12px; }}
    .track {{ min-width: 0; padding: 14px; border: 1px solid var(--line); border-radius: 8px; }}
    .keep {{ border-color: #99f6e4; background: #f0fdfa; }}
    .move {{ border-color: #fecaca; background: #fef2f2; }}
    .track-label {{ display: inline-block; margin-bottom: 10px; font-size: 12px; font-weight: 800; }}
    .keep .track-label {{ color: var(--good); }}
    .move .track-label {{ color: var(--bad); }}
    .track-title {{ font-weight: 700; overflow-wrap: anywhere; }}
    .track-path {{ margin-top: 6px; color: var(--muted); font-size: 12px; overflow-wrap: anywhere; }}
    .quality-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; margin-top: 12px; }}
    .quality-grid div {{ padding: 8px; border: 1px solid var(--line); border-radius: 8px; background: rgba(255, 255, 255, 0.7); }}
    .quality-grid span {{ display: block; color: var(--muted); font-size: 11px; }}
    .quality-grid strong {{ display: block; margin-top: 3px; font-size: 13px; overflow-wrap: anywhere; }}
    .divider {{ display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; color: var(--muted); font-size: 12px; }}
    .arrow {{ font-size: 24px; color: var(--accent); }}
    .empty {{ display: none; margin-top: 12px; padding: 24px; border: 1px dashed var(--line); border-radius: 8px; text-align: center; color: var(--muted); background: #fff; }}
    .empty.visible {{ display: block; }}
    .footer {{ margin-top: 18px; color: var(--muted); text-align: center; font-size: 12px; }}
    @media (max-width: 900px) {{
      .summary, .analysis-grid {{ grid-template-columns: 1fr 1fr; }}
      .comparison {{ grid-template-columns: 1fr; }}
      .divider {{ min-height: 48px; }}
      .arrow {{ transform: rotate(90deg); }}
    }}
    @media (max-width: 560px) {{
      .summary, .analysis-grid, .quality-grid {{ grid-template-columns: 1fr; }}
      input, select, .duplicates-actions .small {{ flex-basis: 100%; width: 100%; }}
      .duplicates-heading {{ align-items: stretch; flex-direction: column; }}
      .group-header {{ grid-template-columns: 1fr; }}
      .badges {{ justify-content: flex-start; }}
    }}
  </style>
</head>
<body>
  <main class="page">
    <section class="header">
      <h1>Отчёт по музыкальной библиотеке</h1>
      <p class="lead">Безопасный отчёт: файлы не удалялись, теги не менялись, перенос в карантин не выполнялся.</p>
      <div class="library-path">{library_path}</div>
      <div class="summary">
        <div class="metric"><span>Всего файлов</span><strong>{format_number(library.get("total_files"))}</strong></div>
        <div class="metric"><span>Альбомов</span><strong>{format_number(library.get("albums"))}</strong></div>
        <div class="metric"><span>Исполнителей</span><strong>{format_number(library.get("artists"))}</strong></div>
        <div class="metric"><span>Дублей</span><strong>{format_number(summary["duplicates"])}</strong></div>
      </div>
    </section>

    <div class="analysis-grid">
      <section class="panel">
        <h2>Сводка</h2>
        <div class="note">
          Групп дублей: <strong>{format_number(summary["groups"])}</strong><br>
          Файлов, предлагаемых в карантин: <strong>{format_number(summary["duplicates"])}</strong><br>
          Нечитаемых аудиофайлов: <strong>{format_number(library.get("unreadable_files"))}</strong>
        </div>
      </section>
      <section class="panel">
        <h2>Форматы файлов</h2>
        {render_format_bars(library.get("formats", {}))}
      </section>
      <section class="panel">
        <h2>Жанры</h2>
        {render_genre_bars(genres)}
      </section>
      <section class="panel">
        <h2>Годы</h2>
        {render_year_bars(years)}
      </section>
    </div>

    <h2 class="section-title">Музыка</h2>
    <div class="toolbar music-toolbar">
      <input id="musicSearch" type="search" placeholder="Поиск по исполнителю, альбому или названию">
      <select id="tagFilter">
        <option value="all">Искать во всех тегах</option>
        <option value="format">Тег: формат</option>
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
      <select id="sort">
        <option value="name">Сортировка: по названию</option>
        <option value="artist">Сортировка: по исполнителю</option>
        <option value="album">Сортировка: по альбому</option>
        <option value="year">Сортировка: по году</option>
        <option value="format">Сортировка: по формату</option>
      </select>
    </div>
    <div class="music-list" id="musicList">{music_html}</div>
    <div class="empty" id="musicEmpty">Ничего не найдено по текущему фильтру музыки.</div>

    <div class="duplicates-heading">
      <h2 class="section-title">Дубли</h2>
      <div class="duplicates-actions">
        <button class="small danger-button" id="quarantineCommand" type="button">Переместить в карантин</button>
        <button class="small" id="expandAll" type="button">Раскрыть всё</button>
        <button class="small" id="collapseAll" type="button">Свернуть всё</button>
      </div>
    </div>
    <div class="quarantine-panel" id="quarantinePanel">
      <p id="quarantineStatus">Готово к безопасному переносу дублей в карантин. Файлы не удаляются.</p>
      <code class="quarantine-command" id="quarantineCommandText">{html.escape(quarantine_command)}</code>
      <span class="copy-status" id="copyStatus"></span>
    </div>
    <div id="cards">{''.join(groups_html)}</div>
    <div class="empty" id="empty">Ничего не найдено по текущему фильтру.</div>
    <div class="footer">Сгенерировано локально. Отчёт не содержит действий удаления файлов.</div>
  </main>

  <script id="payload" type="application/json">{html.escape(json_payload)}</script>
  <script>
    const cards = Array.from(document.querySelectorAll('.group-card'));
    const sort = document.getElementById('sort');
    const musicCards = Array.from(document.querySelectorAll('.music-card'));
    const musicList = document.getElementById('musicList');
    const musicSearch = document.getElementById('musicSearch');
    const tagFilter = document.getElementById('tagFilter');
    const musicEmpty = document.getElementById('musicEmpty');
    const quarantineButton = document.getElementById('quarantineCommand');
    const quarantinePanel = document.getElementById('quarantinePanel');
    const quarantineCommandText = document.getElementById('quarantineCommandText');
    const copyStatus = document.getElementById('copyStatus');
    const quarantineStatus = document.getElementById('quarantineStatus');

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

    function applyMusicFilters() {{
      const value = musicSearch.value.trim().toLowerCase();
      const tagKind = tagFilter.value;
      let visibleCount = 0;
      musicCards.forEach(card => {{
        const searchArea = tagKind === 'all'
          ? (card.dataset.musicSearch || '')
          : (card.getAttribute(`data-tag-${{tagKind}}`) || '');
        const visible = !value || searchArea.includes(value);
        card.hidden = !visible;
        if (visible) visibleCount += 1;
      }});
      musicEmpty.classList.toggle('visible', visibleCount === 0);
    }}

    document.querySelectorAll('.group-header').forEach(button => {{
      button.addEventListener('click', () => button.closest('.group-card').classList.toggle('open'));
    }});
    async function runQuarantine(url, body, message) {{
      quarantinePanel.classList.add('visible');
      quarantineStatus.textContent = message;
      copyStatus.textContent = '';
      try {{
        const response = await fetch(url, {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: body ? JSON.stringify(body) : null,
        }});
        const result = await response.json();
        if (!response.ok || !result.ok) throw new Error(result.error || 'Команда не выполнена');
        quarantineStatus.textContent = 'Готово. Файлы перенесены в карантин, отчёт обновляется.';
        setTimeout(() => window.location.reload(), 900);
      }} catch (error) {{
        quarantineStatus.textContent = 'Не удалось выполнить перенос автоматически.';
        copyStatus.textContent = error.message || String(error);
      }}
    }}

    quarantineButton.addEventListener('click', () => {{
      runQuarantine('/api/quarantine-all', null, 'Переношу все худшие дубли в карантин...');
    }});

    document.querySelectorAll('.quarantine-one').forEach(button => {{
      button.addEventListener('click', event => {{
        event.stopPropagation();
        runQuarantine(
          '/api/quarantine-one',
          {{ moved_file: button.dataset.movedFile }},
          'Переношу выбранный дубль в карантин...'
        );
      }});
    }});
    document.getElementById('expandAll').addEventListener('click', () => cards.forEach(card => {{ if (!card.hidden) card.classList.add('open'); }}));
    document.getElementById('collapseAll').addEventListener('click', () => cards.forEach(card => card.classList.remove('open')));
    musicSearch.addEventListener('input', applyMusicFilters);
    tagFilter.addEventListener('change', applyMusicFilters);
    sort.addEventListener('change', applySort);
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
    parser.add_argument("--library", help="Music library folder for full analysis")
    parser.add_argument("--out", default="reports/duplicates.html", help="Output HTML file")
    args = parser.parse_args()

    csv_path = Path(args.csv).expanduser().resolve()
    library_path = Path(args.library).expanduser().resolve() if args.library else None
    out_path = Path(args.out).expanduser().resolve()

    if not csv_path.exists():
        raise SystemExit(f"CSV report does not exist: {csv_path}")

    rows = read_rows(csv_path)
    library_stats = analyze_library(library_path)
    payload = build_payload(rows, library_stats)
    html_doc = render_html(payload)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html_doc, encoding="utf-8")

    print(f"HTML report written: {out_path}")
    print(f"Total files: {library_stats['total_files']}")
    print(f"Albums: {library_stats['albums']}")
    print(f"Artists: {library_stats['artists']}")
    print(f"Duplicate groups: {payload['summary']['groups']}")
    print(f"Duplicate files: {payload['summary']['duplicates']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
