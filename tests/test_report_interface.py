from __future__ import annotations

import html
import base64
import json
import re
import sys
import unittest
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from generate_html_report import ReportRow, build_payload, render_html, render_genre_bars


class Elements(HTMLParser):
    def __init__(self, document: str):
        super().__init__()
        self.elements = []
        self.texts = []
        self.feed(document)

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))

    def handle_data(self, data):
        self.texts.append(data)


class ReportInterfaceTests(unittest.TestCase):
    def render(self, tracks=None, rows=None):
        tracks = tracks or []
        return render_html(build_payload(rows or [], {
            "path": "D:/Музыка/Library", "tracks": tracks,
            "total_files": len(tracks), "albums": 1 if tracks else 0,
            "artists": 1 if tracks else 0,
        }))

    def test_existing_controls_have_unique_targets_and_safe_default(self):
        elements = Elements(self.render()).elements
        ids = [attrs["id"] for _, attrs in elements if "id" in attrs]
        self.assertEqual(len(ids), len(set(ids)))
        required = {
            "musicSearch", "tagFilter", "identityFilter", "layoutFilter", "sort",
            "musicList", "musicEmpty", "expandMusic", "collapseMusic",
            "tagVisible", "shazamTagVisible", "layoutVisible", "coverVisible",
            "lyricsVisible", "operationStatus", "rescanLibrary", "findDuplicates",
            "quarantineCommand", "expandAll", "collapseAll", "cards", "empty",
            "lyricsModal", "lyricsClose", "processingModeNote",
        }
        self.assertTrue(required.issubset(ids))
        modes = [attrs for tag, attrs in elements if tag == "input" and attrs.get("name") == "processMode"]
        self.assertEqual([m["value"] for m in modes if "checked" in m], ["dry-run"])
        self.assertIn("Музыкальные файлы не найдены", self.render())

    def test_card_actions_keep_exact_file_and_escape_untrusted_metadata(self):
        path = 'D:/Музыка/Library/Трек & "версия".flac'
        name = '<script>alert("название")</script>'
        document = self.render([{"path": path, "name": name, "folder": "Альбом", "tags": []}])
        elements = Elements(document).elements
        actions = [attrs for _, attrs in elements if "music-action-single" in attrs.get("class", "").split()]
        self.assertEqual([a["data-action"] for a in actions], ["tag", "shazam-tag", "layout"])
        self.assertTrue(all(a["data-file-path"] == path for a in actions))
        self.assertNotIn(name, document)
        self.assertIn(html.escape(name), document)
        payload = re.search(r'<script id="payload" type="application/json">(.*?)</script>', document, re.S)
        self.assertEqual(json.loads(html.unescape(payload[1]))["library"]["tracks"][0]["path"], path)

    def test_duplicate_comparison_and_standalone_assets_remain_available(self):
        document = self.render(rows=[ReportRow("Группа", "D:/Музыка/a.flac", "D:/Музыка/a.mp3", "quality", "format=flac", "format=mp3")])
        elements = Elements(document).elements
        self.assertIn("Оставлен", document)
        self.assertIn("В карантин", document)
        self.assertEqual(len([a for _, a in elements if "quarantine-one" in a.get("class", "").split()]), 2)
        self.assertFalse(any(tag == "script" and "src" in a for tag, a in elements))
        self.assertFalse(any(tag == "link" and a.get("rel") == "stylesheet" for tag, a in elements))

    def test_standalone_report_preserves_icon_license_notices(self):
        document = self.render()
        comments = re.findall(r"<!--(.*?)-->", document, re.S)
        notices = "\n".join(comments)
        self.assertIn("Lucide Icons and Contributors", notices)
        self.assertIn("ISC License", notices)
        self.assertIn("this permission notice appear in all copies", notices)
        self.assertIn("Copyright (c) 2013-present Cole Bemis", notices)
        self.assertIn("The MIT License (MIT)", notices)
        self.assertIn("THE SOFTWARE IS PROVIDED", notices)

    def test_standalone_utf8_declaration_precedes_large_embedded_notices(self):
        document = self.render().encode("utf-8")
        declaration = b'<meta charset="utf-8">'
        self.assertLessEqual(document.index(declaration) + len(declaration), 1024)

    def test_library_source_appears_once_in_menu_and_remains_in_payload(self):
        document = self.render()
        visible_markup = document.split('<script id="payload"')[0]
        self.assertEqual(Elements(visible_markup).texts.count("D:/Музыка/Library"), 1)
        self.assertIn('id="librarySource"', visible_markup)
        self.assertNotIn("Текущая папка", visible_markup)
        self.assertNotIn("Локальная", visible_markup)
        payload = re.search(r'<script id="payload" type="application/json">(.*?)</script>', document, re.S)
        self.assertEqual(json.loads(html.unescape(payload[1]))["library"]["path"], "D:/Музыка/Library")

    def test_single_genre_draws_a_complete_ring(self):
        elements = Elements(render_genre_bars({"Рок": 10})).elements
        rings = [attrs for tag, attrs in elements if tag == "circle" and attrs.get("class") == "donut-segment"]
        self.assertEqual(len(rings), 1)
        self.assertEqual(float(rings[0]["pathlength"]), 100)
        self.assertEqual([float(x) for x in rings[0]["stroke-dasharray"].split()], [100, 0])
        self.assertEqual(rings[0]["fill"], "none")

    def test_genre_ring_segments_cover_whole_circle_including_other_genres(self):
        genres = {f"Жанр {i}": 20 - i for i in range(12)}
        elements = Elements(render_genre_bars(genres)).elements
        rings = [attrs for tag, attrs in elements if tag == "circle" and attrs.get("class") == "donut-segment"]
        self.assertEqual(len(rings), 10)
        lengths = [float(r["stroke-dasharray"].split()[0]) for r in rings]
        self.assertAlmostEqual(sum(lengths), 100, places=4)
        self.assertTrue(all(length > 0 for length in lengths))

    def test_standalone_report_embeds_real_font_and_its_distribution_license(self):
        document = self.render()
        font = re.search(r'data:font/woff2;base64,([A-Za-z0-9+/=]+)', document)
        self.assertIsNotNone(font, "The offline report must contain its font")
        self.assertEqual(base64.b64decode(font[1])[:4], b'wOF2')
        license_text = re.search(r'<script id="fontLicense" type="text/plain">(.*?)</script>', document, re.S)
        self.assertIsNotNone(license_text, "The embedded font must retain its license")
        self.assertIn("SIL OPEN FONT LICENSE", html.unescape(license_text[1]))
        self.assertIn("The Inter Project Authors", html.unescape(license_text[1]))

    def test_library_source_preserves_full_path_in_hover_hint(self):
        elements = Elements(self.render()).elements
        paths = [a for tag, a in elements if a.get("id") == "librarySourcePath"]
        self.assertEqual(len(paths), 1)
        self.assertEqual(paths[0].get("title"), "D:/Музыка/Library")


if __name__ == "__main__":
    unittest.main()
