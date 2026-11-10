"""Real scan counters and streaming progress for the local report server."""

from __future__ import annotations

import json
import os
import re
import subprocess
import threading
import time

PREFIX = "@@SCAN_PROGRESS "


def progress_files(paths, progress, stage):
    if progress is None:
        yield from paths
        return
    files = []
    progress({"stage": "discover", "processed": 0, "total": None, "current": ""})
    for path in paths:
        files.append(path)
        progress({"stage": "discover", "processed": len(files), "total": None, "current": path.name})
    progress({"stage": stage, "processed": 0, "total": len(files), "current": ""})
    for index, path in enumerate(files, 1):
        yield path
        progress({"stage": stage, "processed": index, "total": len(files), "current": path.name})


class ProgressWriter:
    def __init__(self):
        self.stage = None
        self.last = 0.0

    def __call__(self, event):
        now = time.monotonic()
        if event["stage"] != self.stage or event.get("processed") == event.get("total") or now - self.last >= .2:
            print(PREFIX + json.dumps(event, ensure_ascii=False), flush=True)
            self.last, self.stage = now, event["stage"]


class ProgressStore:
    def __init__(self):
        self.lock = threading.Lock()
        self.scans = {}

    def start(self, scan_id):
        if not isinstance(scan_id, str) or not re.fullmatch(r"[a-zA-Z0-9-]{16,64}", scan_id):
            raise RuntimeError("Некорректный идентификатор сканирования.")
        with self.lock:
            if scan_id in self.scans:
                raise RuntimeError("Такое сканирование уже запускалось.")
            for key in list(self.scans):
                if len(self.scans) < 32:
                    break
                if self.scans[key]["status"] != "running":
                    del self.scans[key]
            self.scans[scan_id] = {"ok": True, "status": "running", "stage": "starting", "processed": 0, "total": None, "current": ""}

        def update(event):
            with self.lock:
                state = self.scans[scan_id]
                if event.get("stage") != state["stage"]:
                    state.update(processed=0, total=None, current="")
                state.update(event)
        return update

    def snapshot(self, scan_id):
        with self.lock:
            value = self.scans.get(scan_id)
            return dict(value) if value else None


def run_streaming(args, cwd, progress, timeout=300):
    output, failures = [], []
    with subprocess.Popen(args, cwd=cwd, env={**os.environ, "NO_COLOR": "1", "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"}, text=True, encoding="utf-8", errors="replace", stdout=subprocess.PIPE, stderr=subprocess.STDOUT) as process:
        def read():
            try:
                for line in process.stdout:
                    if line.startswith(PREFIX):
                        progress(json.loads(line[len(PREFIX):]))
                    else:
                        output.append(line)
            except Exception as error:
                failures.append(error)
                process.kill()
        reader = threading.Thread(target=read, daemon=True)
        reader.start()
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            raise
        finally:
            reader.join()
        if failures:
            raise failures[0]
        return subprocess.CompletedProcess(args, process.returncode, "".join(output))
