"""Browse folders and publish a source change without modifying audio files."""

from __future__ import annotations

import csv
import json
import os
import shutil
import sys
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class SourceFiles:
    html: Path
    csv: Path
    review: Path
    settings: Path
    actions: Path
    backups: Path


def validate_folder(value: str) -> Path:
    raw = str(value or "").strip().strip('"')
    if not raw:
        raise RuntimeError("Укажите путь к папке.")
    try:
        path = Path(raw).expanduser()
        if not path.is_absolute():
            raise RuntimeError("Укажите полный путь к папке.")
        path = path.resolve()
        if not path.is_dir():
            raise RuntimeError("Папка не найдена или недоступна.")
        return path
    except (OSError, ValueError) as error:
        raise RuntimeError("Не удалось открыть папку: " + str(error)) from error


def folder_roots() -> list[dict[str, str]]:
    if os.name == "nt":
        import ctypes
        mask = ctypes.windll.kernel32.GetLogicalDrives()
        paths = [f"{chr(65 + index)}:\\" for index in range(26) if mask & (1 << index)]
    else:
        paths = ["/"]
    return [{"name": path, "path": path} for path in paths]


def list_folders(value: str = "") -> dict:
    if not str(value or "").strip():
        return {"ok": True, "path": "", "parent": None, "folders": folder_roots()}
    path = validate_folder(value)
    try:
        folders = []
        with os.scandir(path) as entries:
            for entry in entries:
                try:
                    if entry.is_dir():
                        folders.append({"name": entry.name, "path": str(path / entry.name)})
                except OSError:
                    continue
    except OSError as error:
        raise RuntimeError("Нет доступа к содержимому папки: " + str(error)) from error
    folders.sort(key=lambda entry: entry["name"].casefold())
    return {"ok": True, "path": str(path), "parent": str(path.parent) if path.parent != path else None, "folders": folders}


def saved_source(settings: Path, report_source: str) -> str:
    try:
        selected = str(json.loads(settings.read_text(encoding="utf-8"))["path"])
    except (OSError, ValueError, KeyError, TypeError):
        return ""
    # A newly generated --library report takes precedence over an older UI choice.
    key = lambda path: os.path.normcase(os.path.normpath(path))
    return selected if selected and report_source and key(selected) == key(report_source) else ""


def _log(files: SourceFiles, previous: str, selected: str, status: str, backup: str = "", detail: str = "") -> None:
    files.actions.parent.mkdir(parents=True, exist_ok=True)
    header = not files.actions.exists() or files.actions.stat().st_size == 0
    with files.actions.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        if header:
            writer.writerow(["timestamp", "previous_source", "selected_source", "status", "backup", "detail"])
        writer.writerow([datetime.now().isoformat(timespec="seconds"), previous, selected, status, backup, detail])
    print(f"Library source: {status}: {previous} -> {selected}", flush=True)


def change_source(value: str, confirmation: str, files: SourceFiles, run_command, previous: str, progress=None) -> dict:
    if confirmation != "CHANGE_LIBRARY_SOURCE":
        raise RuntimeError("Смена источника и пересканирование требуют подтверждения.")
    library = validate_folder(value)
    files.html.parent.mkdir(parents=True, exist_ok=True)
    scripts = Path(__file__).resolve().parent
    results = []
    backup = files.backups / (datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:8])
    try:
        with tempfile.TemporaryDirectory(prefix=".source-change-", dir=files.html.parent) as temp:
            stage = Path(temp).resolve()
            if stage.parent != files.html.parent.resolve():
                raise RuntimeError("Некорректная временная папка отчёта.")
            staged = {target: stage / name for target, name in [
                (files.csv, "duplicates.csv"), (files.review, "duplicates_needs_review.csv"),
                (files.html, "library.html"), (files.settings, "source.json"),
            ]}
            commands = [
                [sys.executable, str(scripts / "find_duplicates.py"), "--library", str(library), "--dry-run", "--report", str(staged[files.csv]), "--review-report", str(staged[files.review])],
                [sys.executable, str(scripts / "generate_html_report.py"), "--library", str(library), "--csv", str(staged[files.csv]), "--review-csv", str(staged[files.review]), "--out", str(staged[files.html])],
            ]
            for command in commands:
                if progress:
                    command.append("--progress")
                    result = run_command(command, progress)
                else:
                    result = run_command(command)
                results.append({"command": command, "returncode": result.returncode, "output": result.stdout})
                if result.returncode:
                    raise RuntimeError(result.stdout or "Не удалось пересканировать папку.")
            staged[files.settings].write_text(json.dumps({"path": str(library)}, ensure_ascii=False, indent=2), encoding="utf-8")
            if not all(source.is_file() for source in staged.values()):
                raise RuntimeError("Не все файлы нового отчёта созданы; источник не изменён.")
            backup.mkdir(parents=True)
            if progress:
                progress({"stage": "publish", "processed": 0, "total": None, "current": ""})
            existing = {target: target.exists() for target in staged}
            for target, exists in existing.items():
                if exists:
                    shutil.copyfile(target, backup / target.name)
            published = []
            try:
                for target, source in staged.items():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    source.replace(target)
                    published.append(target)
                _log(files, previous, str(library), "completed", str(backup))
            except Exception:
                for target in reversed(published):
                    if existing[target]:
                        shutil.copyfile(backup / target.name, target)
                    else:
                        target.unlink(missing_ok=True)
                raise
    except Exception as error:
        _log(files, previous, str(library), "failed", str(backup) if backup.exists() else "", str(error))
        raise RuntimeError(str(error)) from error
    return {"ok": True, "path": str(library), "backup": str(backup), "commands": results, "reload": True}
