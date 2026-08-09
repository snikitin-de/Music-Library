from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path, PureWindowsPath

ROOT = Path(__file__).resolve().parents[1]
REPORT_SERVER = ROOT / "scripts" / "report_server.py"
sys.path.insert(0, str(ROOT / "scripts"))

from report_server import quarantine_path, trash_path


def norm_path(value: str) -> str:
    return str(PureWindowsPath(value)).replace("/", "\\").casefold()


def posix_path_inside(path: str, root: str) -> bool:
    path_key = path.replace("\\", "/").rstrip("/").casefold()
    root_key = root.replace("\\", "/").rstrip("/").casefold()
    return path_key == root_key or path_key.startswith(root_key + "/")


def path_parts_for_mapping(value: str) -> list[str]:
    raw = (value or "").strip().strip('"')
    if not raw:
        return []
    parts = list(PureWindowsPath(raw.replace("/", "\\")).parts)
    cleaned: list[str] = []
    for part in parts:
        if not part or part in {"\\", "/"} or part.endswith("\\") or re.match(r"^[A-Za-z]:\\?$", part):
            continue
        cleaned.append(part)
    return cleaned


def relative_tail_candidates(value: str) -> list[Path]:
    parts = path_parts_for_mapping(value)
    tails: list[Path] = []

    for index, part in enumerate(parts):
        if part.casefold() == "library" and index + 1 < len(parts):
            tails.append(Path(*parts[index + 1 :]))
            tails.append(Path(*parts[index:]))

    for index in range(max(0, len(parts) - 4), len(parts)):
        tail = parts[index:]
        if tail:
            tails.append(Path(*tail))

    unique: list[Path] = []
    seen: set[str] = set()
    for tail in tails:
        key = norm_path(str(tail))
        if key and key not in seen:
            unique.append(tail)
            seen.add(key)
    return unique


class ReportServerPathSourceTests(unittest.TestCase):
    def test_report_server_prefers_configured_library_path(self) -> None:
        source = REPORT_SERVER.read_text(encoding="utf-8-sig")
        self.assertIn('LIBRARY_ENV_VARS = ("MUSIC_LIBRARY_PATH", "MUSIC_LIBRARY_ROOT", "LIBRARY_PATH")', source)
        self.assertIn('configured = configured_library_paths()', source)
        self.assertIn('return str(existing)', source)

    def test_posix_storage_paths_are_expected_by_report_server(self) -> None:
        self.assertEqual(quarantine_path("/music/Library"), "/music/Duplicates")
        self.assertEqual(trash_path("/music/Library"), "/music/Trash")

    def test_unc_storage_folders_are_siblings_of_library(self) -> None:
        library = r"\\TRUENAS\vault_storage\music\Library"
        self.assertEqual(
            quarantine_path(library),
            r"\\TRUENAS\vault_storage\music\Duplicates",
        )
        self.assertEqual(
            trash_path(library),
            r"\\TRUENAS\vault_storage\music\Trash",
        )

    def test_storage_root_remains_compatible_with_parent_report_path(self) -> None:
        self.assertEqual(quarantine_path("/music"), "/music/Duplicates")
        self.assertEqual(trash_path("/music"), "/music/Trash")

    def test_posix_path_inside_uses_posix_boundaries(self) -> None:
        self.assertTrue(posix_path_inside("/music/Aiko/Pedestal.flac", "/music"))
        self.assertTrue(posix_path_inside("/music", "/music"))
        self.assertFalse(posix_path_inside("/music2/Aiko/Pedestal.flac", "/music"))

    def test_old_unc_library_path_keeps_useful_tails(self) -> None:
        tails = {str(path) for path in relative_tail_candidates(r"\\TRUENAS\vault_storage\music\Library\Aiko\Pedestal.flac")}
        self.assertIn(str(Path("Aiko") / "Pedestal.flac"), tails)
        self.assertIn(str(Path("Library") / "Aiko" / "Pedestal.flac"), tails)


if __name__ == "__main__":
    unittest.main()
