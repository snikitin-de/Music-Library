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
from urllib.parse import quote

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
        '<span class="audio-play-icon" aria-hidden="true"></span>'
        "</button>"
        '<div class="audio-time audio-current">0:00</div>'
        '<div class="audio-seek-wrap">'
        '<div class="audio-seek-track"><span class="audio-seek-fill"></span></div>'
        '<input class="audio-seek" type="range" min="0" max="1000" value="0" step="1" aria-label="Позиция воспроизведения">'
        "</div>"
        '<button class="audio-mute" type="button" aria-label="Выключить звук">'
        '<svg class="audio-volume-icon audio-volume-on" viewBox="0 0 24 24" aria-hidden="true">'
        '<path class="audio-speaker" d="M4 9v6h4l5 4V5L8 9H4z"></path>'
        '<path class="audio-volume-mark" d="M16 9.5c1.2 1.2 1.2 3.8 0 5"></path>'
        "</svg>"
        '<svg class="audio-volume-icon audio-volume-off" viewBox="0 0 24 24" aria-hidden="true">'
        '<path class="audio-speaker" d="M3.5 9v6h4l5 4V5l-5 4h-4z"></path>'
        '<path class="audio-volume-mark" d="M15.5 9l5 6m0-6l-5 6"></path>'
        "</svg>"
        "</button>"
        "</div>"
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

    colors = ["#2563eb", "#dc2626", "#f59e0b", "#16a34a", "#9333ea", "#0891b2", "#db2777", "#65a30d", "#b91c1c"]
    total = sum(genres.values())
    top_items = list(genres.items())[:7]
    other_count = sum(genres.values()) - sum(count for _, count in top_items)
    chart_items = top_items + ([("Прочие", other_count)] if other_count else [])
    start = 0.0
    segments = []
    parts = []
    for index, (genre, count) in enumerate(chart_items):
        color = colors[index % len(colors)]
        end = start + (count / total * 100)
        segments.append(f"{color} {start:.2f}% {end:.2f}%")
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
        start = end

    top_genre, top_count = top_items[0]
    top_percent = round(top_count / total * 100)
    gradient = ", ".join(segments)
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
      <div class="donut-chart" style="background: conic-gradient({gradient});">
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

    year_items = sorted(all_year_items, key=lambda item: (-item[1], -item[0]))[:12]
    year_items = sorted(year_items, key=lambda item: item[0])
    max_count = max(count for _, count in year_items)
    bar_width = 16
    gap = 10
    left = 16
    top = 16
    chart_height = 116
    label_y = top + chart_height + 20
    width = 300
    height = 188
    inner_width = width - left - 14
    gap = max(6, (inner_width - len(year_items) * bar_width) / max(1, len(year_items) - 1))
    bars = []
    for index, (year, count) in enumerate(year_items):
        bar_height = max(3, round(count / max_count * chart_height))
        x = left + index * (bar_width + gap)
        y = top + chart_height - bar_height
        year_label = str(year) if index in {0, 4, 8, len(year_items) - 1} else ""
        bars.append(
            f"""
            <g>
              <title>{year}: {format_number(count)}</title>
              <rect class="year-chart-bar" x="{x}" y="{y}" width="{bar_width}" height="{bar_height}" rx="4"></rect>
              <text class="year-chart-label" x="{x + bar_width / 2}" y="{label_y}" text-anchor="middle">{html.escape(year_label)}</text>
            </g>
            """
        )

    peak_year, peak_count = max(all_year_items, key=lambda item: item[1])
    return f"""
    <p class="chart-note">
      Самый плотный год: <strong>{html.escape(str(peak_year))}</strong>,
      <strong>{format_number(peak_count)}</strong> файлов.
    </p>
    <div class="year-chart-scroll" aria-label="Топ годов по количеству файлов">
      <svg class="year-chart" viewBox="0 0 {width} {height}" role="img">
        <line class="year-chart-axis" x1="{left - 8}" y1="{top + chart_height}" x2="{width - 8}" y2="{top + chart_height}"></line>
        {"".join(bars)}
      </svg>
    </div>
    """


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
        player_html = audio_player(track.get("path", ""), f'Прослушать {track.get("name", "")}')
        items.append(
            f"""
            <article class="{html.escape(" ".join(card_classes))}" data-file-path="{html.escape(track.get("path", ""))}" data-music-search="{html.escape(search_text)}" data-sort-name="{html.escape(track.get("name", "").lower())}" data-sort-artist="{html.escape(sort_artist)}" data-sort-album="{html.escape(sort_album)}" data-sort-year="{html.escape(sort_year)}" data-sort-format="{html.escape(sort_format)}" {tag_attributes}>
              <div class="music-title">{html.escape(track.get("name", ""))}</div>
              <div class="music-path" title="{html.escape(track.get("path", ""))}">{html.escape(track.get("folder", ""))}</div>
              {player_html}
              <div class="music-pills">{tags}</div>
              <div class="music-actions">
                <button class="small music-action-single" type="button" data-action="tag" data-file-path="{html.escape(track.get("path", ""))}">Проставить теги этой записи</button>
                <button class="small music-action-single" type="button" data-action="layout" data-file-path="{html.escape(track.get("path", ""))}">Разложить эту запись</button>
              </div>
              <div class="music-card-status" aria-live="polite">
                <div class="music-card-status-text"></div>
                <div class="music-card-progress" aria-hidden="true"><span></span></div>
              </div>
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
                    {audio_player(item["kept_file"], f'Прослушать оставленный файл: {item["kept_name"]}')}
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
                    {audio_player(item["moved_file"], f'Прослушать файл для карантина: {item["moved_name"]}')}
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
    .library-path {{ margin-top: 12px; overflow-wrap: anywhere; color: var(--muted); font-size: 13px; }}
    .summary {{ display: grid; grid-template-columns: repeat(4, minmax(140px, 1fr)); gap: 12px; margin-top: 18px; }}
    .metric {{ padding: 16px; border: 1px solid var(--line); border-radius: 8px; background: var(--soft); }}
    .metric span {{ display: block; color: var(--muted); font-size: 13px; }}
    .metric strong {{ display: block; margin-top: 6px; font-size: 28px; }}
    .analysis-grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; margin-top: 14px; }}
    .panel {{ padding: 18px; border: 1px solid var(--line); border-radius: 8px; background: var(--panel); }}
    .panel h2, .section-title {{ margin: 0; font-size: 20px; }}
    .panel-body {{ margin-top: 14px; }}
    .note {{ color: var(--muted); line-height: 1.55; }}
    .format-row {{ display: grid; grid-template-columns: 60px 1fr 60px; gap: 10px; align-items: center; margin-top: 10px; }}
    .panel-body > .format-row:first-child {{ margin-top: 0; }}
    .genre-row {{ display: grid; grid-template-columns: minmax(90px, 150px) 1fr 44px; gap: 10px; align-items: center; margin-top: 10px; }}
    .genre-name {{ min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
    .year-row {{ display: grid; grid-template-columns: 54px 1fr 44px; gap: 10px; align-items: center; margin-top: 10px; }}
    .format-bar {{ height: 10px; border-radius: 999px; background: #e5e7eb; overflow: hidden; }}
    .format-bar span {{ display: block; height: 100%; background: var(--accent); }}
    .format-count {{ text-align: right; color: var(--muted); }}
    .donut-layout {{ display: grid; grid-template-columns: 1fr; gap: 14px; justify-items: center; }}
    .donut-chart {{ width: 146px; aspect-ratio: 1; border-radius: 50%; display: grid; place-items: center; box-shadow: inset 0 0 0 1px rgba(17, 24, 39, 0.08); }}
    .donut-hole {{ width: 82px; aspect-ratio: 1; border-radius: 50%; display: grid; place-items: center; align-content: center; padding: 8px; background: var(--panel); text-align: center; box-shadow: 0 0 0 1px var(--line); }}
    .donut-hole strong {{ font-size: 24px; line-height: 1; }}
    .donut-hole span {{ display: block; max-width: 68px; margin-top: 5px; overflow: hidden; color: var(--muted); font-size: 11px; line-height: 1.15; text-overflow: ellipsis; white-space: nowrap; }}
    .chart-legend {{ display: grid; gap: 7px; width: 100%; min-width: 0; }}
    .chart-legend-row {{ display: grid; grid-template-columns: 10px minmax(0, 1fr) 42px 44px; gap: 8px; align-items: center; min-width: 0; font-size: 13px; }}
    .chart-dot {{ width: 10px; height: 10px; border-radius: 50%; }}
    .chart-label {{ overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
    .chart-legend-row strong {{ text-align: right; }}
    .chart-legend-row span:last-child {{ color: var(--muted); text-align: right; }}
    .chart-note {{ width: 100%; margin: 0 0 12px; color: var(--muted); font-size: 13px; line-height: 1.4; }}
    .chart-note strong {{ color: var(--text); }}
    .year-chart-scroll {{ max-width: 100%; overflow: hidden; padding-bottom: 2px; }}
    .year-chart {{ display: block; width: 100%; height: 188px; }}
    .year-chart-axis {{ stroke: #d1d5db; stroke-width: 1; }}
    .year-chart-bar {{ fill: var(--accent); }}
    .year-chart-bar:hover {{ fill: #1d4ed8; }}
    .year-chart-label {{ fill: var(--muted); font-size: 11px; }}
    .year-chart-value {{ fill: var(--text); font-size: 11px; font-weight: 700; }}
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
    .music-operations {{
      margin-top: 14px;
      padding: 14px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #f8fafc;
    }}
    .music-operations-row {{ display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }}
    .music-operations-title {{ margin: 0 0 10px; font-weight: 750; }}
    .mode-choice {{ display: inline-flex; align-items: center; gap: 6px; min-height: 42px; padding: 0 10px; border: 1px solid var(--line); border-radius: 8px; background: #fff; }}
    .mode-choice input {{ flex: 0 0 auto; width: auto; }}
    .operation-status {{ margin-top: 10px; color: var(--muted); font-size: 13px; line-height: 1.45; overflow-wrap: anywhere; }}
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
    .music-section.collapsed .music-toolbar,
    .music-section.collapsed .music-list {{
      display: none;
    }}
    .music-section.collapsed #musicEmpty {{
      display: none !important;
    }}
    .music-list {{ display: grid; gap: 10px; }}
    .music-card {{ padding: 14px; border: 1px solid var(--line); border-radius: 8px; background: var(--panel); }}
    .music-card-duplicate {{ border-color: #f59e0b; background: #fffbeb; }}
    .music-card-unreadable {{ border-color: #ef4444; background: #fef2f2; }}
    .music-card[hidden] {{ display: none; }}
    .music-title {{ font-weight: 750; overflow-wrap: anywhere; }}
    .music-path {{ margin-top: 5px; color: var(--muted); font-size: 12px; overflow-wrap: anywhere; }}
    .music-actions {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }}
    .music-card-status {{ display: none; margin-top: 12px; color: var(--muted); font-size: 13px; }}
    .music-card-status.visible {{ display: block; }}
    .music-card-status.done {{ color: var(--good); }}
    .music-card-status.error {{ color: var(--bad); }}
    .music-card-progress {{
      position: relative;
      height: 8px;
      margin-top: 7px;
      overflow: hidden;
      border-radius: 4px;
      background: #e5e7eb;
    }}
    .music-card-progress span {{
      position: absolute;
      inset: 0 auto 0 0;
      width: 42%;
      border-radius: inherit;
      background: var(--accent);
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
    .audio-player-wrap {{ margin-top: 10px; }}
    .audio-player {{ display: none; }}
    .custom-audio-player {{
      display: grid;
      grid-template-columns: 30px auto minmax(80px, 1fr) 30px;
      align-items: center;
      gap: 8px;
      width: 100%;
      min-height: 36px;
      padding: 0 10px;
      border-radius: 999px;
      background: #f1f3f5;
      color: #111827;
      box-sizing: border-box;
    }}
    .audio-play,
    .audio-mute {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 24px;
      height: 24px;
      padding: 0;
      border: 0;
      border-radius: 999px;
      background: transparent;
      color: #111827;
      cursor: pointer;
    }}
    .audio-play:hover,
    .audio-mute:hover {{ background: #e5e7eb; }}
    .audio-play-icon {{
      width: 0;
      height: 0;
      margin-left: 2px;
      border-top: 6px solid transparent;
      border-bottom: 6px solid transparent;
      border-left: 9px solid currentColor;
    }}
    .audio-play.playing .audio-play-icon {{
      width: 10px;
      height: 12px;
      margin-left: 0;
      border: 0;
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
      background: #c7c9cc;
      pointer-events: none;
    }}
    .audio-seek-fill {{
      display: block;
      width: var(--audio-progress, 0%);
      height: 100%;
      border-radius: inherit;
      background: #9ca3af;
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
      width: 21px;
      height: 21px;
      color: #4b5563;
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
    .audio-volume-off {{ display: none; }}
    .audio-mute.muted .audio-volume-on {{ display: none; }}
    .audio-mute.muted .audio-volume-off {{ display: block; }}
    .quality-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; margin-top: 12px; }}
    .quality-grid div {{ padding: 8px; border: 1px solid var(--line); border-radius: 8px; background: rgba(255, 255, 255, 0.7); }}
    .quality-grid span {{ display: block; color: var(--muted); font-size: 11px; }}
    .quality-grid strong {{ display: block; margin-top: 3px; font-size: 13px; overflow-wrap: anywhere; }}
    .divider {{ display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; color: var(--muted); font-size: 12px; }}
    .arrow {{ font-size: 24px; color: var(--accent); }}
    .empty {{ display: none; margin-top: 12px; padding: 24px; border: 1px dashed var(--line); border-radius: 8px; text-align: center; color: var(--muted); background: #fff; }}
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
        <div class="panel-body note">
          Групп дублей: <strong>{format_number(summary["groups"])}</strong><br>
          Файлов, предлагаемых в карантин: <strong>{format_number(summary["duplicates"])}</strong><br>
          Нечитаемых аудиофайлов: <strong>{format_number(library.get("unreadable_files"))}</strong>
        </div>
      </section>
      <section class="panel">
        <h2>Форматы файлов</h2>
        <div class="panel-body">
          {render_format_bars(library.get("formats", {}))}
        </div>
      </section>
      <section class="panel">
        <h2>Жанры</h2>
        <div class="panel-body">
          {render_genre_bars(genres, library.get("tracks", []))}
        </div>
      </section>
      <section class="panel">
        <h2>Годы</h2>
        <div class="panel-body">
          {render_year_bars(years)}
        </div>
      </section>
    </div>

    <section class="music-section collapsed" id="musicSection">
      <div class="duplicates-heading music-heading">
        <h2 class="section-title">Музыка</h2>
        <div class="duplicates-actions">
          <button class="small" id="expandMusic" type="button">Развернуть список музыки</button>
          <button class="small" id="collapseMusic" type="button">Свернуть список музыки</button>
        </div>
      </div>
    <div class="music-operations music-toolbar">
      <p class="music-operations-title">Обработка музыки</p>
      <div class="music-operations-row">
        <label class="mode-choice"><input type="radio" name="processMode" value="dry-run" checked> Dry run</label>
        <label class="mode-choice"><input type="radio" name="processMode" value="real"> Реальная обработка</label>
        <button class="small" id="tagVisible" type="button">Проставить теги для отфильтрованных</button>
        <button class="small" id="layoutVisible" type="button">Разложить отфильтрованные по папкам</button>
      </div>
      <div class="operation-status" id="operationStatus">Выбран безопасный режим dry run. Глобальные кнопки работают по отфильтрованному списку, кнопки внутри карточки — только по своей записи.</div>
    </div>
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
    </section>

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
    const musicSection = document.getElementById('musicSection');
    const expandMusic = document.getElementById('expandMusic');
    const collapseMusic = document.getElementById('collapseMusic');
    const operationStatus = document.getElementById('operationStatus');
    const tagVisible = document.getElementById('tagVisible');
    const layoutVisible = document.getElementById('layoutVisible');

    function selectedMode() {{
      const selected = document.querySelector('input[name="processMode"]:checked');
      return selected ? selected.value : 'dry-run';
    }}

    function updateOperationStatus() {{
      const mode = selectedMode();
      if (!operationStatus) return;

      if (mode === 'real') {{
        operationStatus.textContent = 'Выбрана реальная обработка. «Разложить» будет перемещать файлы в папки текущей библиотеки по исполнителю и альбому. Глобальные кнопки работают по отфильтрованному списку, кнопки внутри карточки — только по своей записи.';
      }} else {{
        operationStatus.textContent = 'Выбран безопасный режим dry run. Глобальные кнопки работают по отфильтрованному списку, кнопки внутри карточки — только по своей записи.';
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

    function setMusicActionDisabled(disabled, card = null) {{
      const root = card || document;
      const selector = card ? '.music-action-single' : '.music-action-single, #tagVisible, #layoutVisible';
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

      if (mode === 'real') {{
        const targetText = scope === 'single'
          ? 'одну выбранную запись'
          : `отфильтрованные записи: ${{uniqueFiles.length}}`;
        const confirmed = window.confirm(`Запустить реальную обработку через beets для: ${{targetText}}?`);
        if (!confirmed) return;
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
          body: JSON.stringify({{ action, mode, scope, files: uniqueFiles }}),
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
        if (!handleInCard && mode === 'real' && result.reload) setTimeout(() => window.location.reload(), 900);
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
      const confirmed = window.confirm('Перенести все худшие дубли из CSV-отчёта в карантин? Файлы не удаляются.');
      if (!confirmed) return;
      runQuarantine('/api/quarantine-all', {{ confirm: 'MOVE_TO_QUARANTINE' }}, 'Переношу все худшие дубли в карантин...');
    }});

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
        runQuarantine(
          '/api/quarantine-one',
          {{ moved_file: button.dataset.movedFile, confirm: 'MOVE_TO_QUARANTINE' }},
          'Переношу выбранный дубль в карантин...'
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

    tagVisible.addEventListener('click', () => runMusicOperation('tag', visibleMusicPaths(), 'filtered'));
    layoutVisible.addEventListener('click', () => runMusicOperation('layout', visibleMusicPaths(), 'filtered'));

    document.querySelectorAll('input[name="processMode"]').forEach(input => {{
      input.addEventListener('change', updateOperationStatus);
    }});
    updateOperationStatus();
    document.getElementById('expandAll').addEventListener('click', () => cards.forEach(card => {{ if (!card.hidden) card.classList.add('open'); }}));
    document.getElementById('collapseAll').addEventListener('click', () => cards.forEach(card => card.classList.remove('open')));
    musicSearch.addEventListener('input', applyMusicFilters);
    tagFilter.addEventListener('change', applyMusicFilters);
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
