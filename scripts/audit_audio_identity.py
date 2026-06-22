"""Safely compare embedded tags with AcoustID recognition results."""

from __future__ import annotations

import argparse
import json
import os
import re
import time
import unicodedata
from pathlib import Path

import acoustid


AUDIO_EXTENSIONS = {".flac", ".alac", ".wav", ".aiff", ".aif", ".mp3", ".m4a", ".aac", ".ogg", ".opus", ".wma"}
DEFAULT_ACOUSTID_KEY = "1vOwZtEn"  # Public beets client key.
MIN_SCORE = 0.80


def normalized(value: str) -> str:
    value = str(value or "").lower().replace("ё", "е")
    value = "".join(
        char for char in unicodedata.normalize("NFKD", value)
        if not unicodedata.combining(char)
    )
    value = re.sub(r"\([^)]*(?:live|remaster|edit|version|mix)[^)]*\)", " ", value)
    value = re.sub(r"[^\w]+", " ", value, flags=re.UNICODE)
    return re.sub(r"\s+", " ", value).strip()


def comparable(left: str, right: str) -> bool:
    a, b = normalized(left), normalized(right)
    return bool(a and b and (a == b or a in b or b in a))


def tag_value(tags: object, *names: str) -> str:
    for name in names:
        value = getattr(tags, "get", lambda _key: None)(name)
        if value:
            return str(value[0] if isinstance(value, list) else value)
    return ""


def recognize(path: Path, api_key: str) -> dict[str, object]:
    from mutagen import File as MutagenFile

    audio = MutagenFile(path, easy=True)
    tags = audio.tags or {} if audio is not None else {}
    tagged_artist = tag_value(tags, "artist", "albumartist", "composer")
    tagged_title = tag_value(tags, "title")
    last_error = None
    for attempt in range(3):
        try:
            response = acoustid.match(
                api_key, str(path), parse=False, force_fpcalc=True, timeout=30
            )
            break
        except Exception as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(1.5 * (attempt + 1))
    else:
        raise last_error or RuntimeError("AcoustID lookup failed")

    results = response.get("results", []) if isinstance(response, dict) else []
    if not results:
        return {"status": "not_found", "mismatch": False}
    best = max(results, key=lambda item: float(item.get("score", 0) or 0))
    score = float(best.get("score", 0) or 0)
    candidates = []
    seen = set()
    for recording in best.get("recordings", []) or []:
        artist = ", ".join(
            str(item.get("name", "")) for item in recording.get("artists", []) if item.get("name")
        )
        title = str(recording.get("title", "") or "")
        key = (normalized(artist), normalized(title))
        if key in seen:
            continue
        seen.add(key)
        candidates.append({
            "recording_id": recording.get("id", ""),
            "artist": artist,
            "title": title,
        })

    if len(candidates) != 1:
        return {
            "status": "ambiguous",
            "mismatch": False,
            "score": round(score, 4),
            "candidates": candidates,
            "tagged_artist": tagged_artist,
            "tagged_title": tagged_title,
        }

    candidate = candidates[0]
    artist, title = candidate["artist"], candidate["title"]
    confidently_compared = score >= MIN_SCORE and bool(tagged_artist and tagged_title and artist and title)
    mismatch = confidently_compared and not (
        comparable(tagged_artist, artist) and comparable(tagged_title, title)
    )
    return {
        "status": "mismatch" if mismatch else "match" if confidently_compared else "uncertain",
        "mismatch": mismatch,
        "score": round(score, 4),
        "recording_id": candidate["recording_id"],
        "recognized_artist": artist,
        "recognized_title": title,
        "tagged_artist": tagged_artist,
        "tagged_title": tagged_title,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--library", required=True)
    parser.add_argument("--out", default="reports/audio_identity.json")
    parser.add_argument("--api-key", default=os.environ.get("ACOUSTID_API_KEY", DEFAULT_ACOUSTID_KEY))
    parser.add_argument("--only-file", help="Check one file first as a safe sample")
    args = parser.parse_args()

    library = Path(args.library).expanduser().resolve()
    out = Path(args.out).expanduser().resolve()
    old = {}
    if out.exists():
        try:
            old = json.loads(out.read_text(encoding="utf-8")).get("files", {})
        except (OSError, ValueError):
            old = {}

    if not library.is_dir():
        raise SystemExit(f"Music library folder does not exist: {library}")
    scan_root = library / "Library" if (library / "Library").is_dir() else library
    if args.only_file:
        sample = Path(args.only_file).expanduser().resolve()
        try:
            sample.relative_to(scan_root)
        except ValueError as exc:
            raise SystemExit(f"Sample file is outside the music library: {sample}") from exc
        if not sample.is_file() or sample.suffix.lower() not in AUDIO_EXTENSIONS:
            raise SystemExit(f"Sample audio file does not exist or is unsupported: {sample}")
        paths = [sample]
    else:
        paths = [
            path for path in scan_root.rglob("*")
            if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS
        ]
    results = dict(old)
    for index, path in enumerate(paths, 1):
        stat = path.stat()
        key = str(path)
        signature = {"size": stat.st_size, "mtime_ns": stat.st_mtime_ns}
        if (
            results.get(key, {}).get("signature") == signature
            and results.get(key, {}).get("status") != "error"
        ):
            print(f"[{index}/{len(paths)}] cached: {path}")
            continue
        try:
            result = recognize(path, args.api_key)
            print(f"[{index}/{len(paths)}] {result['status']}: {path}")
        except Exception as exc:
            result = {"status": "error", "mismatch": False, "error": str(exc)}
            print(f"[{index}/{len(paths)}] error: {path} ({exc})")
        results[key] = {"signature": signature, **result}

    payload = {"library": str(library), "minimum_score": MIN_SCORE, "files": results}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    mismatches = sum(bool(item.get("mismatch")) for item in results.values())
    print(f"Identity report written: {out}")
    print(f"Tag/audio mismatches: {mismatches}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
