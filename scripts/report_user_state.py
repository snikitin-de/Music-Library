"""Atomic JSON storage for a report server's playlists and player."""

from __future__ import annotations

import json
import math
import re
import tempfile
from pathlib import Path, PureWindowsPath
from threading import Lock


MAX_REQUEST_BYTES = 24 * 1024 * 1024
HISTORY_LIMIT = 200
_LOCK = Lock()
_ID = re.compile(r"[a-z0-9-]{1,100}")
_COVER = re.compile(r"data:image/(?:jpeg|png|webp);base64,[A-Za-z0-9+/=]+")


class StateConflict(RuntimeError):
    pass


def _invalid() -> None:
    raise RuntimeError("Неверный формат данных плеера или резервной копии.")


def _object(value):
    if not isinstance(value, dict):
        _invalid()
    return value


def _list(value):
    if not isinstance(value, list):
        _invalid()
    return value


def _text(value, limit: int, required: bool = False) -> str:
    if not isinstance(value, str) or len(value) > limit or (required and not value.strip()):
        _invalid()
    return value


def _number(value, limit: float):
    if type(value) not in (int, float) or not 0 <= value <= limit or not math.isfinite(value):
        _invalid()
    return value


def _flag(value) -> bool:
    if type(value) is not bool:
        _invalid()
    return value


def _path_key(path: str) -> str:
    return str(PureWindowsPath(path)).lower()


def _track(value) -> dict:
    value = _object(value)
    return {
        "path": _text(value.get("path"), 4096, required=True),
        **{key: _text(value.get(key, ""), 4096) for key in ("title", "artist", "album", "name")},
    }


def _playlists(value) -> list[dict]:
    result = []
    seen = set()
    for item in _list(value):
        item = _object(item)
        item_id = _text(item.get("id"), 100, required=True)
        if not _ID.fullmatch(item_id) or item_id in seen:
            _invalid()
        seen.add(item_id)
        playlist = {
            "id": item_id,
            "name": _text(item.get("name"), 80, required=True),
            "createdAt": _number(item.get("createdAt", 0), 8.64e15),
            "tracks": [_track(track) for track in _list(item.get("tracks"))],
        }
        cover = item.get("cover")
        if cover:
            if not _COVER.fullmatch(_text(cover, 2 * 1024 * 1024)):
                _invalid()
            playlist["cover"] = cover
        result.append(playlist)
    return result


def _listen(value) -> dict:
    value = _object(value)
    return {
        "path": _text(value.get("path"), 4096, required=True),
        "title": _text(value.get("title", ""), 4096),
        "artist": _text(value.get("artist", ""), 4096),
        "playedAt": _number(value.get("playedAt"), 8.64e15),
    }


def _session(value) -> dict:
    value = _object(value)
    return {
        "token": _text(value.get("token"), 100, required=True),
        "updatedAt": _number(value.get("updatedAt"), 8.64e15),
        "position": _number(value.get("position"), 31557600),
        "track": _track(value["track"]) if value.get("track") is not None else None,
        "manualQueue": [_track(track) for track in _list(value.get("manualQueue"))],
        "scope": _text(value.get("scope", ""), 128),
        "anchor": _text(value.get("anchor", ""), 4096),
        **{
            key: [_text(path, 4096, required=True) for path in _list(value.get(key, []))]
            for key in ("source", "shuffleOrder", "shufflePlayed")
        },
        **{
            key: _flag(value.get(key, False))
            for key in ("shuffle", "repeat", "playingQueuedTrack", "listenRecorded")
        },
    }


def _merge_playlists(current: list[dict], incoming: list[dict]) -> None:
    by_id = {item["id"]: item for item in current}
    for playlist in incoming:
        existing = by_id.get(playlist["id"])
        if existing is None:
            current.append(playlist)
            continue
        known = {_path_key(track["path"]) for track in existing["tracks"]}
        for track in playlist["tracks"]:
            key = _path_key(track["path"])
            if key not in known:
                existing["tracks"].append(track)
                known.add(key)


def _merge_history(current: list[dict], incoming: list[dict]) -> list[dict]:
    unique = {}
    for entry in current + incoming:
        unique.setdefault((_path_key(entry["path"]), entry["playedAt"]), entry)
    return sorted(unique.values(), key=lambda entry: entry["playedAt"], reverse=True)[:HISTORY_LIMIT]


def _read(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


def _write(path: Path, data: dict) -> None:
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as target:
            temporary = Path(target.name)
            json.dump(data, target, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
            if target.tell() > MAX_REQUEST_BYTES:
                raise RuntimeError("Не удалось сохранить данные: JSON превышает допустимый размер.")
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


class ReportUserState:
    def __init__(self, directory: Path):
        self.library_file = directory / "player-library.json"
        self.session_file = directory / "player-session.json"

    def _library(self) -> dict:
        return _read(self.library_file, {"version": 1, "playlistsRevision": 0, "playlists": [], "history": []})

    def read(self) -> dict:
        with _LOCK:
            return {**self._library(), "session": _read(self.session_file, None)}

    def update(self, body: dict) -> dict:
        action = _object(body).get("action")
        with _LOCK:
            if action in ("session", "position"):
                self._update_session(action, body)
                return {}
            library = self._library()
            if action == "playlists":
                if _number(body.get("revision"), 1e12) != library["playlistsRevision"]:
                    raise StateConflict("Плейлисты изменились в другой вкладке.")
                library["playlists"] = _playlists(body.get("playlists"))
                library["playlistsRevision"] += 1
                result = {"playlists": library["playlists"], "playlistsRevision": library["playlistsRevision"]}
            elif action == "listen":
                library["history"] = _merge_history(library["history"], [_listen(body.get("entry"))])
                result = {"history": library["history"]}
            elif action == "import":
                backup = _object(body.get("backup"))
                if type(backup.get("version")) is not int or backup["version"] != 1:
                    _invalid()
                playlists = _playlists(backup.get("playlists"))
                entries = [_listen(entry) for entry in _list(backup.get("history"))]
                _merge_playlists(library["playlists"], playlists)
                library["playlistsRevision"] += 1
                library["history"] = _merge_history(library["history"], entries)
                result = library
            else:
                _invalid()
            _write(self.library_file, library)
            return result

    def _update_session(self, action: str, body: dict) -> None:
        current = _read(self.session_file, None)
        if action == "session":
            candidate = _session(body.get("session"))
            if current is None or candidate["updatedAt"] >= current["updatedAt"]:
                _write(self.session_file, candidate)
        else:
            token = _text(body.get("token"), 100, required=True)
            updated_at = _number(body.get("updatedAt"), 8.64e15)
            position = _number(body.get("position"), 31557600)
            listened = _flag(body.get("listenRecorded", False))
            if current and current["token"] == token and updated_at >= current["updatedAt"]:
                _write(self.session_file, {**current, "updatedAt": updated_at, "position": position, "listenRecorded": listened})
