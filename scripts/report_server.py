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
import re
import shutil
import subprocess
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PureWindowsPath

from generate_html_report import ReportRow, build_payload, render_html


ROOT = Path(__file__).resolve().parents[1]
REPORT_HTML = ROOT / "reports" / "duplicates.html"
REPORT_CSV = ROOT / "reports" / "duplicates.csv"


def norm_path(value: str) -> str:
    return str(PureWindowsPath(value)).replace("/", "\\").casefold()


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
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), ReportHandler)
    print(f"Report server: http://{args.host}:{args.port}/reports/duplicates.html")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
