"""Recognize one audio file through the unofficial Shazam client.

The caller must obtain explicit user approval before invoking this helper.
It prints a compact JSON object and never modifies the audio file.
"""

from __future__ import annotations

import argparse
import asyncio
import io
import json
import subprocess
import wave
from pathlib import Path

import imageio_ffmpeg
from shazamio import Shazam


def decode_to_wav_bytes(path: Path) -> bytes:
    raw = subprocess.run(
        [
            imageio_ffmpeg.get_ffmpeg_exe(),
            "-v", "error", "-i", str(path),
            "-f", "s16le", "-acodec", "pcm_s16le",
            "-ac", "1", "-ar", "44100", "pipe:1",
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout
    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(44100)
        wav.writeframes(raw)
    return output.getvalue()


def metadata_value(track: dict, title: str) -> str:
    for section in track.get("sections", []) or []:
        if section.get("type") != "SONG":
            continue
        for item in section.get("metadata", []) or []:
            if str(item.get("title", "")).casefold() == title.casefold():
                return str(item.get("text", "") or "").strip()
    return ""


async def recognize(path: Path) -> dict[str, object]:
    result = await Shazam().recognize(decode_to_wav_bytes(path))
    track = result.get("track") or {}
    if not track:
        return {"ok": False, "error": "Shazam did not recognize the file."}
    return {
        "ok": True,
        "artist": str(track.get("subtitle", "") or "").strip(),
        "title": str(track.get("title", "") or "").strip(),
        "album": metadata_value(track, "Album"),
        "year": metadata_value(track, "Released"),
        "genre": str((track.get("genres") or {}).get("primary", "") or "").strip(),
        "track_id": str(track.get("key", "") or ""),
        "url": str(track.get("url", "") or ""),
        "matches": len(result.get("matches", []) or []),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    args = parser.parse_args()
    path = Path(args.file)
    if not path.is_file():
        raise SystemExit(f"Audio file does not exist: {path}")
    print(json.dumps(asyncio.run(recognize(path)), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
