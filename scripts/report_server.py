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
import unicodedata
import re
import shutil
import subprocess
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PureWindowsPath
from urllib.parse import parse_qs, urlparse

from generate_html_report import ReportRow, build_payload, render_html


ROOT = Path(__file__).resolve().parents[1]
REPORT_HTML = ROOT / "reports" / "duplicates.html"
REPORT_CSV = ROOT / "reports" / "duplicates.csv"

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
    return subprocess.run(
        args,
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=300,
    )


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


def quarantine_duplicates(only_file: str | None = None) -> dict:
    return move_from_csv(only_file)


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

        with source.open("rb") as f:
            f.seek(start)
            remaining = length
            while remaining > 0:
                chunk = f.read(min(1024 * 1024, remaining))
                if not chunk:
                    break
                handler.wfile.write(chunk)
                remaining -= len(chunk)
        return

    handler.send_response(200)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Accept-Ranges", "bytes")
    handler.send_header("Content-Length", str(file_size))
    handler.end_headers()
    if head_only:
        return

    with source.open("rb") as f:
        shutil.copyfileobj(f, handler.wfile)


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
                self.send_json(200, quarantine_duplicates())
                return

            if self.path == "/api/quarantine-one":
                body = self.read_json()
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

            self.send_json(404, {"ok": False, "error": "Unknown API endpoint"})
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
