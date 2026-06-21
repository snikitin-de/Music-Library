"""Search and safely save missing cover art and lyrics as sidecar files."""

from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


USER_AGENT = "MusicLibraryAgent/1.0 (local music metadata tool)"
MAX_DOWNLOAD_BYTES = 12 * 1024 * 1024
COVER_NAMES = ("cover.jpg", "cover.jpeg", "cover.png", "folder.jpg", "folder.jpeg", "folder.png")


class EnrichmentError(RuntimeError):
    pass


@dataclass(frozen=True)
class TrackMetadata:
    artist: str
    album_artist: str
    album: str
    title: str
    duration: int = 0


def _request_bytes(url: str, *, accept: str, max_bytes: int = MAX_DOWNLOAD_BYTES) -> tuple[bytes, str]:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": accept})
    try:
        with urlopen(request, timeout=12) as response:
            content_type = response.headers.get_content_type()
            declared = int(response.headers.get("Content-Length", "0") or 0)
            if declared > max_bytes:
                raise EnrichmentError("Ответ провайдера слишком большой.")
            data = response.read(max_bytes + 1)
    except HTTPError as exc:
        raise EnrichmentError(f"Провайдер ответил HTTP {exc.code}.") from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise EnrichmentError(f"Не удалось связаться с провайдером: {exc}") from exc
    if len(data) > max_bytes:
        raise EnrichmentError("Ответ провайдера слишком большой.")
    return data, content_type


def _request_json(url: str) -> object:
    data, _ = _request_bytes(url, accept="application/json", max_bytes=2 * 1024 * 1024)
    try:
        return json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EnrichmentError("Провайдер вернул некорректный JSON.") from exc


def _plain_from_lrc(value: str) -> str:
    lines = []
    for line in value.splitlines():
        cleaned = re.sub(r"^(?:\[[^\]]+\])+\s*", "", line).strip()
        if cleaned:
            lines.append(cleaned)
    return "\n".join(lines).strip()


def search_lyrics(metadata: TrackMetadata) -> list[dict[str, object]]:
    if not metadata.artist or not metadata.title:
        raise EnrichmentError("Для поиска текста нужны теги исполнителя и названия.")

    params = {"artist_name": metadata.artist, "track_name": metadata.title}
    if metadata.album:
        params["album_name"] = metadata.album
    result = _request_json("https://lrclib.net/api/search?" + urlencode(params))
    if not isinstance(result, list):
        return []

    candidates: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()
    for item in result[:10]:
        if not isinstance(item, dict):
            continue
        synced = str(item.get("syncedLyrics") or "").strip()
        plain = str(item.get("plainLyrics") or "").strip()
        lyrics = synced or plain
        kind = "synced" if synced else "plain"
        if not lyrics:
            continue
        key = (kind, lyrics)
        if key in seen:
            continue
        seen.add(key)
        candidates.append(
            {
                "provider": "LRCLIB",
                "kind": kind,
                "artist": str(item.get("artistName") or metadata.artist),
                "title": str(item.get("trackName") or metadata.title),
                "album": str(item.get("albumName") or metadata.album),
                "duration": int(float(item.get("duration") or 0)),
                "content": lyrics,
                "preview": _plain_from_lrc(lyrics)[:1200],
            }
        )
    return candidates


def _escape_mb_query(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def search_covers(metadata: TrackMetadata) -> list[dict[str, object]]:
    artist = metadata.album_artist or metadata.artist
    if not artist or not metadata.album:
        raise EnrichmentError("Для поиска обложки нужны теги исполнителя альбома и альбома.")
    query = f'artist:"{_escape_mb_query(artist)}" AND release:"{_escape_mb_query(metadata.album)}"'
    url = "https://musicbrainz.org/ws/2/release/?" + urlencode(
        {"query": query, "fmt": "json", "limit": 8}
    )
    result = _request_json(url)
    releases = result.get("releases", []) if isinstance(result, dict) else []
    candidates: list[dict[str, object]] = []
    for release in releases:
        if not isinstance(release, dict) or not release.get("id"):
            continue
        release_id = str(release["id"])
        artist_credit = release.get("artist-credit") or []
        credited = "".join(str(part.get("name") or "") + str(part.get("joinphrase") or "") for part in artist_credit if isinstance(part, dict)).strip()
        candidates.append(
            {
                "provider": "MusicBrainz / Cover Art Archive",
                "kind": "cover",
                "artist": credited or artist,
                "album": str(release.get("title") or metadata.album),
                "date": str(release.get("date") or ""),
                "country": str(release.get("country") or ""),
                "score": int(release.get("score") or 0),
                "release_id": release_id,
                "preview_url": f"https://coverartarchive.org/release/{release_id}/front-250",
                "download_url": f"https://coverartarchive.org/release/{release_id}/front-500",
            }
        )
    return candidates


def sidecar_cover_path(audio_path: Path) -> Path | None:
    for name in COVER_NAMES:
        candidate = audio_path.parent / name
        if candidate.is_file():
            return candidate
    return None


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, path)
    except Exception:
        try:
            os.unlink(temporary_name)
        except OSError:
            pass
        raise


def save_lyrics(audio_path: Path, candidate: dict[str, object]) -> Path:
    if audio_path.with_suffix(".lrc").exists() or audio_path.with_suffix(".txt").exists():
        raise EnrichmentError("Текст рядом с треком уже существует; перезапись запрещена.")
    content = str(candidate.get("content") or "").strip()
    if not content:
        raise EnrichmentError("Кандидат не содержит текста.")
    suffix = ".lrc" if candidate.get("kind") == "synced" else ".txt"
    destination = audio_path.with_suffix(suffix)
    _atomic_write(destination, (content + "\n").encode("utf-8"))
    return destination


def save_cover(audio_path: Path, candidate: dict[str, object]) -> Path:
    existing = sidecar_cover_path(audio_path)
    if existing is not None:
        raise EnrichmentError(f"Обложка рядом с альбомом уже существует: {existing.name}")
    url = str(candidate.get("download_url") or "")
    if not url.startswith("https://coverartarchive.org/"):
        raise EnrichmentError("Недопустимый адрес обложки.")
    data, content_type = _request_bytes(url, accept="image/jpeg,image/png")
    if content_type not in {"image/jpeg", "image/png"}:
        raise EnrichmentError("Провайдер вернул не изображение.")
    destination = audio_path.parent / ("cover.png" if content_type == "image/png" else "cover.jpg")
    _atomic_write(destination, data)
    return destination
