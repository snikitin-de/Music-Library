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
from generate_html_report import ReportRow, build_payload, render_html, render_genre_bars, render_year_bars, render_genre_era_heatmap, collect_genres_from_tracks, collect_genre_era_heatmap, genre_coverage


class Elements(HTMLParser):
    def __init__(self, document: str):
        super().__init__()
        self.elements = []
        self.texts = []
        self.pages = {}
        self.stack = []
        self.feed(document)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.elements.append((tag, attrs))
        page = attrs.get("data-page") or (self.stack[-1][1] if self.stack else None)
        if page:
            self.pages.setdefault(page, []).append((tag, attrs))
        if tag not in {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}:
            self.stack.append((tag, page))

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        self.texts.append(data)


class ReportInterfaceTests(unittest.TestCase):
    def test_duplicate_statistics_match_overview_and_appear_above_search(self):
        rows = [ReportRow('Группа', 'a.flac', path, 'lower quality score', 'format=flac', 'format=mp3')
                for path in ['b.mp3', 'c.mp3']]
        review = [ReportRow('Проверка', 'd.flac', 'e.flac', 'needs_review: same artist/title, tag key is not identical', '', '')]
        document = render_html(build_payload(rows, {'path': 'D:/Music', 'tracks': []}, review))
        for ids, value in [(('duplicateGroupsMetric','duplicatePageGroupsMetric'),'1'),
                           (('duplicateMetric','duplicatePageFilesMetric'),'2'),
                           (('reviewGroupsMetric','duplicatePageReviewMetric'),'1')]:
            for element_id in ids:
                match = re.search(r'<strong id="' + element_id + r'">(.*?)</strong>', document)
                self.assertIsNotNone(match, element_id)
                self.assertEqual(match[1], value, element_id)
        elements = Elements(document).pages['duplicates']
        stats = next(i for i, (_, a) in enumerate(elements) if 'duplicate-summary' in a.get('class', '').split())
        search = next(i for i, (_, a) in enumerate(elements) if a.get('id') == 'duplicateSearch')
        self.assertLess(stats, search)

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
            "musicList", "musicEmpty",
            "tagVisible", "shazamTagVisible", "layoutVisible", "coverVisible",
            "lyricsVisible", "operationStatus", "rescanLibrary", "findDuplicates",
            "cards", "empty",
            "lyricsModal", "lyricsClose", "processingModeNote",
        }
        self.assertTrue(required.issubset(ids))
        mode_tag, mode = next((tag,attrs) for tag,attrs in elements if attrs.get("id") == "processingModeNote")
        self.assertEqual(mode_tag,"button")
        self.assertEqual(mode.get("data-mode"),"dry-run")
        self.assertEqual(mode.get("aria-pressed"),"false")
        self.assertFalse(any(tag=="input" and attrs.get("name")=="processMode" for tag,attrs in elements))
        self.assertIn("Музыкальные файлы не найдены", self.render())

    def test_navigation_has_three_separate_pages_with_their_own_content(self):
        parsed = Elements(self.render(tracks=[{"path": "D:/Музыка/a.flac", "name": "Трек", "tags": []}]))
        self.assertEqual(set(parsed.pages), {"overview", "musicSection", "duplicates"})
        ids = {page: {a["id"] for _, a in elements if "id" in a} for page, elements in parsed.pages.items()}
        self.assertIn("insights", ids["overview"])
        self.assertNotIn("musicList", ids["overview"])
        self.assertNotIn("cards", ids["overview"])
        self.assertTrue({"musicList", "musicSearch", "tagVisible"}.issubset(ids["musicSection"]))
        self.assertTrue({"cards", "findDuplicates"}.issubset(ids["duplicates"]))
        self.assertTrue({"checkExactDuplicates", "exactDuplicatesMetric", "quarantineCommand"}.isdisjoint(ids["duplicates"]))
        targets = [a["href"] for tag, a in parsed.elements if tag == "a" and a.get("href", "").startswith("#")]
        self.assertEqual(set(targets), {"#overview", "#musicSection", "#duplicates"})

    def test_duplicate_groups_can_be_opened_individually(self):
        parsed = Elements(self.render(rows=[ReportRow("Группа", "D:/Музыка/a.flac", "D:/Музыка/a.mp3", "quality", "format=flac", "format=mp3")]))
        removed = {"expandMusic", "collapseMusic", "expandAll", "collapseAll"}
        self.assertFalse(removed.intersection(a.get("id") for _, a in parsed.elements))
        headers = [(tag, a) for tag, a in parsed.elements if "group-header" in a.get("class", "").split()]
        self.assertEqual(len(headers), 1)
        self.assertEqual(headers[0][0], "summary")
        music = next(a for _, a in parsed.elements if a.get("id") == "musicSection")
        self.assertNotIn("collapsed", music.get("class", "").split())

    def test_music_table_keeps_details_collapsed_and_uses_track_tags(self):
        tracks = [
            {"path": "D:/Музыка/01.flac", "name": "01.flac", "duration": 204, "tags": [
                {"kind": "title", "label": "название", "value": "Песня <версия>"},
                {"kind": "artist", "label": "исполнитель", "value": "Исполнитель"},
                {"kind": "album", "label": "альбом", "value": "Альбом"},
                {"kind": "genre", "label": "жанр", "value": "Синти-поп"},
            ]},
            {"path": "D:/Музыка/02.flac", "name": "02.flac", "tags": []},
        ]
        parsed = Elements(self.render(tracks=tracks))
        elements = parsed.pages["musicSection"]
        self.assertEqual(next(tag for tag, a in elements if a.get("id") == "musicList"), "table")
        groups = [a for tag, a in elements if tag == "tbody" and a.get("data-file-path")]
        self.assertEqual([a["data-sort-name"] for a in groups], ["песня <версия>", "02.flac"])
        self.assertIn("синти-поп", groups[0]["data-music-search"])
        self.assertIn("3:24", parsed.texts)
        self.assertIn("—", parsed.texts)
        self.assertIn("Песня <версия>", parsed.texts)
        toggles = [a for tag, a in elements if tag == "button" and a.get("class") == "music-details-toggle"]
        self.assertEqual(len(toggles), 2)
        for toggle in toggles:
            self.assertEqual(toggle.get("aria-expanded"), "false")
            tag, panel = next((tag, a) for tag, a in elements if a.get("id") == toggle["aria-controls"])
            self.assertEqual(tag, "tr")
            self.assertIn("hidden", panel)
        self.assertNotEqual(toggles[0]["aria-controls"], toggles[1]["aria-controls"])

    def test_empty_duplicates_page_shows_an_empty_state(self):
        parsed = Elements(self.render())
        empty = next(a for _, a in parsed.pages["duplicates"] if a.get("id") == "empty")
        self.assertIn("visible", empty["class"].split())

    def test_large_lists_are_inert_until_their_page_loads_a_batch(self):
        tracks = [{"path": f"D:/Музыка/{index}.flac", "name": f"Трек {index}", "tags": []} for index in range(25)]
        rows = [ReportRow(f"Группа {index}", f"D:/Музыка/{index}.flac", f"D:/Музыка/{index}.mp3", "quality", "format=flac", "format=mp3") for index in range(15)]
        document = self.render(tracks=tracks, rows=rows)
        class ActiveCards(HTMLParser):
            def __init__(self):
                super().__init__()
                self.inert = 0
                self.active = []
                self.stored = []
            def handle_starttag(self, tag, attrs):
                if tag == 'template': self.inert += 1
                classes = dict(attrs).get('class', '').split()
                if 'music-card' in classes or 'group-card' in classes:
                    (self.stored if self.inert else self.active).append(classes)
            def handle_endtag(self, tag):
                if tag == 'template': self.inert -= 1
        parsed = ActiveCards()
        parsed.feed(document)
        self.assertEqual(len(parsed.active), 0, 'Full lists must not enter the active DOM before pagination')
        self.assertEqual(sum('music-card' in classes for classes in parsed.stored), 25)
        self.assertEqual(sum('group-card' in classes for classes in parsed.stored), 15)

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
        self.assertIn("Предлагается оставить", document)
        self.assertIn("В карантин", document)
        self.assertEqual(len([a for _, a in elements if "quarantine-one" in a.get("class", "").split()]), 2)
        self.assertFalse(any(tag == "script" and "src" in a for tag, a in elements))
        self.assertFalse(any(tag == "link" and a.get("rel") == "stylesheet" for tag, a in elements))

    def test_duplicates_use_readable_groups_and_music_style_cards(self):
        path='D:/Музыка/a.flac'
        document=self.render(tracks=[{'path':path,'name':'a.flac','tags':[{'kind':'title','value':'Песня <тест>'},{'kind':'artist','value':'Исполнитель'}]}],rows=[ReportRow('cross_release | raw technical key',path,'D:/Музыка/a.mp3','lower quality score','format=flac; bitrate=900000','format=mp3; bitrate=320000')])
        parsed=Elements(document)
        self.assertTrue('Дубли и возможные совпадения' not in document,'Use the short duplicates page title')
        title=re.search(r'<h3 class="group-title">(.*?)</h3>',document,re.S)
        self.assertIsNotNone(title)
        self.assertEqual(html.unescape(title[1]),'Песня <тест> — Исполнитель')
        rows=[a for tag,a in parsed.elements if 'duplicate-track' in a.get('class','').split()]
        self.assertEqual([row['data-file-path'] for row in rows],[path,'D:/Музыка/a.mp3'])
        self.assertEqual(len([a for _,a in parsed.elements if 'duplicate-quality' in a.get('class','').split()]),2)
        self.assertFalse(any('quality-grid' in a.get('class','').split() for _,a in parsed.elements))
        trash=[a for _,a in parsed.elements if 'trash-one' in a.get('class','').split() and 'music-trash-icon' in a.get('class','').split()]
        self.assertTrue({path,'D:/Музыка/a.mp3'}.issubset(a['data-file-path'] for a in trash))

    def test_review_only_comparisons_keep_their_uncertain_status(self):
        document=self.render(rows=[ReportRow('review | raw', 'D:/Музыка/a.flac','D:/Музыка/b.flac','needs_review: same artist/title, tag key is not identical','format=flac','format=flac')])
        subtitles=re.findall(r'<div class="group-subtitle">(.*?)</div>',document,re.S)
        self.assertEqual(subtitles,['Возможный дубль · сравнений: 1'])
        labels=re.findall(r'<span class="track-label">(.*?)</span>',document,re.S)
        self.assertEqual(labels,['Лучший кандидат','Для сравнения'])

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

    def test_plotly_genres_preserve_counts_and_include_small_genres(self):
        genres = dict(zip(["Pop", "Rock", "Dance", "Electronic", "Electro", "House", "Techno", "Folk", "Metal", "Country", "Blues", "Jazz"], range(20, 8, -1)))
        charts = [a for _, a in Elements(render_genre_bars(genres)).elements if "data-plotly" in a]
        self.assertEqual(len(charts), 1)
        trace = json.loads(charts[0]["data-plotly"])["data"][0]
        self.assertEqual(trace["type"], "pie")
        self.assertEqual(trace["values"], [20, 19, 18, 17, 16, 15, 14, 13, 12, 30])
        self.assertEqual(trace["labels"][-1], "Прочие")
        self.assertFalse(trace["sort"])

    def test_singer_songwriter_category_is_excluded_from_genre_analytics_only(self):
        tracks = [
            {"tags": [{"kind": "genre", "value": "Pop; Singer & Songwriter"}, {"kind": "year", "value": "2018"}]},
            {"tags": [{"kind": "genre", "value": "singer   & songwriter"}]},
            {"tags": [{"kind": "genre", "value": "R&B; Singer-songwriter"}]},
        ]
        self.assertEqual(collect_genres_from_tracks(tracks), {"Pop": 1, "R&B": 1, "Singer-songwriter": 1})
        self.assertEqual(genre_coverage(tracks), (2, 1))
        heatmap = collect_genre_era_heatmap(tracks)
        self.assertEqual({row["genre"] for row in heatmap["rows"]}, {"Pop", "R&B", "Singer-songwriter"})
        self.assertEqual(tracks[0]["tags"][0]["value"], "Pop; Singer & Songwriter")

    def test_cached_genre_counts_cannot_reintroduce_excluded_category(self):
        document = render_genre_bars({"Singer & Songwriter": 20, "Pop": 8})
        chart = next(a for _, a in Elements(document).elements if "data-plotly" in a)
        trace = json.loads(chart["data-plotly"])["data"][0]
        self.assertEqual(trace["labels"], ["Pop"])
        self.assertEqual(trace["values"], [8])
        self.assertNotIn("Singer &amp; Songwriter", document)
        self.assertIn("Жанры не определены", render_genre_bars({"Singer & Songwriter": 20}))

    def test_plotly_years_keep_counts_in_the_right_eras(self):
        charts = [a for _, a in Elements(render_year_bars({"1970": 2, "1981": 3, "2018": 5, "2019": 7})).elements if "data-plotly" in a]
        self.assertEqual(len(charts), 1)
        trace = json.loads(charts[0]["data-plotly"])["data"][0]
        self.assertEqual(trace["type"], "bar")
        self.assertEqual(trace["x"], ["до 80-х", "80-е", "10-е"])
        self.assertEqual(trace["y"], [2, 3, 12])

    def test_plotly_heatmap_keeps_raw_counts_separate_from_colour_scale(self):
        tracks = [{"tags": [{"kind": "genre", "value": "Рок"}, {"kind": "year", "value": year}]} for year in ["2018", "2019", "2021"]]
        charts = [a for _, a in Elements(render_genre_era_heatmap(tracks)).elements if "data-plotly" in a]
        self.assertEqual(len(charts), 1)
        trace = json.loads(charts[0]["data-plotly"])["data"][0]
        self.assertEqual(trace["type"], "heatmap")
        self.assertEqual(trace["y"], ["Rock"])
        self.assertEqual(trace["customdata"], [[0, 0, 0, 2, 1, 0]])

    def test_plotly_heatmap_single_occurrence_uses_full_colour_range(self):
        tracks = [{"tags": [{"kind": "genre", "value": "Рок"}, {"kind": "year", "value": "2021"}]}]
        chart = next(a for _, a in Elements(render_genre_era_heatmap(tracks)).elements if "data-plotly" in a)
        trace = json.loads(chart["data-plotly"])["data"][0]
        self.assertAlmostEqual(trace["zmax"], 0.6931471805599453)

    def test_genre_ring_segments_cover_whole_circle_including_other_genres(self):
        genres = dict(zip(["Pop", "Rock", "Dance", "Electronic", "Electro", "House", "Techno", "Folk", "Metal", "Country", "Blues", "Jazz"], range(20, 8, -1)))
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
        self.assertIn("The Nunito Project Authors", html.unescape(license_text[1]))

    def test_library_source_preserves_full_path_in_hover_hint(self):
        elements = Elements(self.render()).elements
        paths = [a for tag, a in elements if a.get("id") == "librarySourcePath"]
        self.assertEqual(len(paths), 1)
        self.assertEqual(paths[0].get("title"), "D:/Музыка/Library")

    def test_source_is_a_dialog_button_in_the_bottom_sidebar_block(self):
        elements = Elements(self.render()).elements
        source_index = next(i for i, (_, a) in enumerate(elements) if a.get("id") == "librarySource")
        footer_index = next((i for i, (_, a) in enumerate(elements) if "sidebar-footer" in a.get("class", "").split()), -1)
        mode_index = next(i for i, (_, a) in enumerate(elements) if a.get("id") == "processingModeNote")
        self.assertGreaterEqual(footer_index, 0)
        self.assertLess(footer_index, source_index)
        self.assertLess(source_index, mode_index)
        tag, button = elements[source_index]
        self.assertEqual(tag, "button")
        self.assertEqual(button.get("aria-haspopup"), "dialog")
        self.assertEqual(button.get("aria-controls"), "sourceDialog")
        ids = {a.get("id") for _, a in elements}
        self.assertTrue({"sourceDialog", "sourcePath", "sourceFolders", "sourceApply", "sourceCancel"}.issubset(ids))


if __name__ == "__main__":
    unittest.main()
