from __future__ import annotations

import html
import base64
import json
import re
import sys
import tempfile
import unittest
import wave
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from generate_html_report import ReportRow, analyze_library, build_payload, cover_api_url, render_html, render_genre_bars, render_year_bars, render_genre_era_heatmap, collect_genres_from_tracks, collect_genre_era_heatmap, genre_coverage


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
    def test_duplicate_statistics_match_overview_and_appear_under_page_title(self):
        rows = [ReportRow('Группа', 'a.flac', path, 'lower quality score', 'format=flac', 'format=mp3')
                for path in ['b.mp3', 'c.mp3']]
        review = [ReportRow('Проверка', 'd.flac', 'e.flac', 'needs_review: same artist/title, tag key is not identical', '', '')]
        document = render_html(build_payload(rows, {'path': 'D:/Music', 'tracks': []}, review))
        duplicates_page = document.split('id="duplicates" hidden>', 1)[1]
        header = duplicates_page.split('</header>', 1)[0]
        summary = re.search(r'<p class="music-summary">(.*?)</p>', header, re.S)
        self.assertIsNotNone(summary)
        self.assertIn('</h1>', header[:summary.start()])
        text = "".join(Elements(summary[1]).texts)
        self.assertEqual(" ".join(text.split()), "Групп дублей: 1 · Дублей: 2 · Возможных дублей: 1")
        for element_id, value in [('duplicateGroupsMetric', '1'), ('duplicateMetric', '2'), ('reviewGroupsMetric', '1')]:
            self.assertIn(f'<strong id="{element_id}">{value}</strong>', document)

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
            "musicSearch",
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

    def test_navigation_keeps_report_sections_and_playlist_page_separate(self):
        parsed = Elements(self.render(tracks=[{"path": "D:/Музыка/a.flac", "name": "Трек", "tags": []}]))
        self.assertEqual(set(parsed.pages), {"overview", "musicSection", "duplicates", "playlist"})
        ids = {page: {a["id"] for _, a in elements if "id" in a} for page, elements in parsed.pages.items()}
        self.assertIn("insights", ids["overview"])
        self.assertNotIn("musicList", ids["overview"])
        self.assertNotIn("cards", ids["overview"])
        self.assertTrue({"musicList", "tagVisible"}.issubset(ids["musicSection"]))
        self.assertTrue({"cards", "findDuplicates"}.issubset(ids["duplicates"]))
        self.assertTrue({"playlistTitle", "playlistTracks"}.issubset(ids["playlist"]))
        playlist_table = parsed.pages["playlist"]
        self.assertTrue(any(tag == "table" and a.get("id") == "playlistTracks" for tag, a in playlist_table))
        self.assertEqual(
            [a["data-music-sort"] for _, a in playlist_table if "data-music-sort" in a],
            [a["data-music-sort"] for _, a in parsed.pages["musicSection"] if "data-music-sort" in a],
        )
        self.assertTrue({"checkExactDuplicates", "exactDuplicatesMetric", "quarantineCommand"}.isdisjoint(ids["duplicates"]))
        targets = [a["href"] for tag, a in parsed.elements if tag == "a" and a.get("href", "").startswith("#")]
        self.assertEqual(set(targets), {"#overview", "#musicSection", "#duplicates"})

    def test_track_search_appears_between_each_page_heading_and_track_table(self):
        pages = Elements(self.render()).pages
        for page, field, table in [
            ("musicSection", "musicPageSearch", "musicList"),
            ("playlist", "playlistTrackSearch", "playlistTracks"),
        ]:
            with self.subTest(page=page):
                elements = pages[page]
                title_index = next(i for i, (tag, _) in enumerate(elements) if tag == "h1")
                table_index = next(i for i, (_, a) in enumerate(elements) if a.get("id") == table)
                searches = [a for tag, a in elements[title_index + 1:table_index]
                            if tag == "input" and a.get("type") == "search"]
                self.assertEqual([(a["id"], a.get("aria-controls")) for a in searches], [(field, table)])

    def test_top_toolbar_contains_home_music_search_and_settings(self):
        document = self.render()
        toolbar = document.split('<header class="app-topbar"', 1)[1].split('</header>', 1)[0]
        controls = {attrs["id"]: (tag, attrs) for tag, attrs in Elements(toolbar).elements if "id" in attrs}
        self.assertEqual(controls["reportHome"][1]["href"], "#overview")
        self.assertEqual(controls["musicSearch"][1]["type"], "search")
        self.assertEqual(controls["reportSettings"][0], "details")
        source_tag, source_control = controls["librarySource"]
        self.assertEqual(source_tag, "button")
        self.assertEqual(source_control["aria-haspopup"], "dialog")
        self.assertEqual(source_control["aria-controls"], "sourceDialog")
        self.assertEqual(controls["processingModeNote"][1]["aria-pressed"], "false")

    def test_window_close_buttons_share_the_same_style_and_icon(self):
        document = self.render()
        icons = []
        for element_id in ["lyricsClose", "sourceClose", "playbackPanelClose"]:
            match = re.search(r'<button\b[^>]*\bid="' + element_id + r'"[^>]*>.*?</button>', document, re.S)
            self.assertIsNotNone(match)
            button = Elements(match[0]).elements[0][1]
            self.assertIn("window-close", button.get("class", "").split())
            self.assertTrue(button.get("aria-label"))
            icon = re.search(r'<svg\b.*?</svg>', match[0], re.S)
            self.assertIsNotNone(icon)
            icons.append(icon[0])
        self.assertEqual(len(set(icons)), 1)

    def test_page_actions_use_collapsed_menus_under_search_with_progress_outside(self):
        document = self.render()
        for page, search, menu_id, actions, status in [
            ("musicSection", "musicPageSearch", "musicActions",
             {"tagVisible", "shazamTagVisible", "layoutVisible", "coverVisible", "lyricsVisible", "rescanLibrary"},
             {"operationStatus", "scanPanel"}),
            ("duplicates", "duplicateSearch", "duplicateActions", {"findDuplicates"}, {"duplicateScanPanel"}),
        ]:
            with self.subTest(page=page):
                section = document.split(f'id="{page}" hidden>', 1)[1]
                menu = re.search(r'<details\b[^>]*\bid="' + menu_id + r'"[^>]*>.*?</details>', section, re.S)
                self.assertIsNotNone(menu)
                self.assertLess(section.index(f'id="{search}"'), menu.start())
                elements = Elements(menu[0]).elements
                self.assertNotIn("open", elements[0][1])
                self.assertEqual({a["id"] for tag, a in elements if tag == "button"}, actions)
                for element_id in status:
                    self.assertGreater(section.index(f'id="{element_id}"'), menu.end())

    def test_playlist_controls_are_available_in_the_sidebar_and_each_track(self):
        track = {"path": "D:/Музыка/a.flac", "name": "Трек.flac", "tags": []}
        document = self.render(tracks=[track, dict(track, path="D:/Музыка/b.flac")])
        sidebar = document.split('<aside class="app-sidebar"', 1)[1].split('</aside>', 1)[0]
        self.assertLess(sidebar.index('class="side-nav"'), sidebar.index('id="playlistSectionTitle"'))
        self.assertIn('id="playlistSearch"', sidebar)
        self.assertRegex(sidebar, r'id="playlistSearchToggle"[^>]+aria-expanded="false"')
        self.assertIn('id="playlistSort"', sidebar)
        self.assertIn('<option value="date" data-label="По дате">По дате создания</option>', sidebar)
        self.assertIn('<option value="name">По алфавиту</option>', sidebar)
        self.assertIn('id="createPlaylist"', sidebar)
        self.assertIn('id="playlistCoverButton"', document)
        self.assertIn('id="playlistCoverInput" type="file"', document)
        self.assertTrue('id="renamePlaylist"' in document)
        self.assertTrue('id="deletePlaylist"' in document and 'id="playlistDeleteDialog"' in document)
        playlist_actions = document.split('id="playlistActions"', 1)[1].split('</details>', 1)[0]
        reset = next(attrs for _, attrs in Elements(playlist_actions).elements if attrs.get("id") == "resetPlaylistCover")
        self.assertNotIn("hidden", reset)
        self.assertIn("disabled", reset)
        elements = Elements(document).pages["musicSection"]
        triggers = [attrs for tag, attrs in elements
                    if tag == "button" and "music-track-menu-button" in attrs.get("class", "").split()]
        self.assertEqual(len(triggers), 2)
        self.assertTrue(all(attrs.get("aria-controls") == "playlistTrackMenu" for attrs in triggers))
        self.assertIn('id="addTrackToPlaylist"', document)
        self.assertIn('id="removeTrackFromPlaylist"', document)
        pagination = document.split('id="playlistPagination"', 1)[1].split('</div>', 1)[0]
        self.assertNotIn('role="status"', pagination)

    def test_queue_toggles_sit_by_search_and_volume_and_empty_tabs_have_no_hints(self):
        document = self.render()
        elements = Elements(document).elements
        buttons = [a for tag, a in elements if tag == "button" and a.get("aria-controls") == "playbackPanel"]
        self.assertEqual([(a["id"], a["aria-expanded"]) for a in buttons],
                         [("queueToggle", "false"), ("globalQueueToggle", "false")])
        search_area = document.split('<div class="topbar-search-area">', 1)[1].split("</div>", 1)[0]
        self.assertLess(search_area.index('id="musicSearch"'), search_area.index('id="queueToggle"'))
        player = document.split('<div class="global-extras">', 1)[1].split('id="globalVolumeWrap"', 1)[0]
        extras = [a["id"] for tag, a in Elements(player).elements if tag == "button"]
        self.assertEqual(extras, ["globalLyrics", "globalQueueToggle", "globalMute"])
        panel = document.split('id="playbackPanel"', 1)[1].split('</aside>', 1)[0]
        self.assertNotIn("Очередь пуста.", panel)
        self.assertNotIn("Здесь появятся прослушанные треки.", panel)
        tabs = [a["aria-controls"] for _, a in Elements(panel).elements if a.get("role") == "tab"]
        self.assertEqual(tabs, ["playbackQueueView", "playbackHistoryView"])

    def test_track_menu_shows_playlist_and_queue_actions_before_play_next(self):
        document = self.render()
        menu = document.split('id="playlistTrackMenu"', 1)[1].split('id="trackPlaylistPicker"', 1)[0]
        actions = [a["id"] for tag, a in Elements(menu).elements if tag == "button"]
        self.assertEqual(actions[:3], ["addTrackToPlaylist", "addTrackToQueue", "playTrackNext"])

    def test_track_tables_have_batch_controls_and_only_playable_rows_can_be_selected(self):
        track = {"path": "D:/Music/a.flac", "title": "Трек"}
        document = self.render(tracks=[track])
        pages = Elements(document).pages
        for page in ("musicSection", "playlist"):
            elements = pages[page]
            actions = [a.get("aria-controls") for _, a in elements if "data-track-selection-actions" in a]
            self.assertEqual(actions, ["playlistTrackMenu"])
            self.assertTrue(any("data-track-selection-clear" in a for _, a in elements))
        playable = document.split('id="musicCardSource"', 1)[1].split('</template>', 1)[0]
        self.assertRegex(playable, r'<input class="music-track-select" type="checkbox"[^>]+aria-label="[^"]+"')
        unavailable = document.split('id="playlistUnavailableTrack"', 1)[1].split('</template>', 1)[0]
        self.assertNotIn('music-track-select', unavailable)

    def test_resizable_panes_have_keyboard_accessible_separators(self):
        elements = Elements(self.render()).elements
        separators = [attrs for _, attrs in elements if attrs.get("role") == "separator"]
        self.assertEqual(
            [(item.get("aria-controls"), item.get("aria-orientation"), item.get("tabindex")) for item in separators],
            [("appSidebar", "vertical", "0"), ("playbackPanel", "vertical", "0")],
        )

    def test_navigation_and_page_headers_share_titles(self):
        document = self.render()
        navigation = document.split('<nav class="side-nav"', 1)[1].split('</nav>', 1)[0]
        expected_titles = ["Моя медиатека", "Музыка", "Дубликаты"]
        self.assertEqual(re.findall(r"<span>(.*?)</span>", navigation), expected_titles)
        headings = re.findall(
            r'<div class="hero-layout">\s*'
            r'<div class="collection-art" aria-hidden="true"><svg\b.*?</svg></div>\s*'
            r'<div class="hero-copy">\s*<h1>(.*?)</h1>',
            document, re.S,
        )
        self.assertEqual(headings, expected_titles)

    def test_sidebar_toggle_controls_the_navigation_panel(self):
        elements = Elements(self.render()).elements
        tag, toggle = next((tag, attrs) for tag, attrs in elements if attrs.get("id") == "sidebarToggle")
        self.assertEqual(tag, "button")
        self.assertEqual(toggle["aria-label"], "Свернуть меню")
        self.assertEqual(toggle["aria-expanded"], "true")
        self.assertTrue(any(tag == "aside" and attrs.get("id") == toggle["aria-controls"]
                            for tag, attrs in elements))
        for target, title in [("#overview", "Моя медиатека"), ("#musicSection", "Музыка"), ("#duplicates", "Дубликаты")]:
            self.assertTrue(any(tag == "a" and attrs.get("href") == target and attrs.get("aria-label") == title
                                for tag, attrs in elements))

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
        self.assertFalse(any(tag == "select" for tag, _ in elements))
        self.assertEqual([a["data-music-sort"] for tag, a in elements
                          if tag == "button" and "data-music-sort" in a], ["number", "name", "artist", "album", "duration"])
        self.assertFalse(any(tag == "th" and "aria-sort" in a for tag, a in elements))
        groups = [a for tag, a in elements if tag == "tbody" and a.get("data-file-path")]
        self.assertEqual([a["data-sort-number"] for a in groups], ["1", "2"])
        self.assertEqual([a["data-sort-name"] for a in groups], ["песня <версия>", "02.flac"])
        self.assertEqual([a["data-sort-artist"] for a in groups], ["исполнитель", ""])
        self.assertEqual([a["title"] for tag, a in elements
                          if tag == "td" and a.get("class") == "music-track-artist"], ["Исполнитель", ""])
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

    def test_library_report_uses_server_urls_for_covers(self):
        with tempfile.TemporaryDirectory() as folder:
            library = Path(folder)
            track = library / "Песня.wav"
            with wave.open(str(track), "wb") as audio:
                audio.setparams((1, 2, 44100, 0, "NONE", "not compressed"))
                audio.writeframes(b"\x00\x00" * 100)
            (library / "cover.png").write_bytes(base64.b64decode(
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGNgYPgPAAEDAQAIicLsAAAAAElFTkSuQmCC"
            ))
            stats = analyze_library(library)

        self.assertTrue(stats["tracks"][0]["has_cover"])
        self.assertEqual(stats["tracks"][0]["cover_data_uri"], "")
        document = render_html(build_payload([], stats))
        images = [a for tag, a in Elements(document).pages["musicSection"] if tag == "img"]
        self.assertEqual([a["src"] for a in images], [cover_api_url(str(track))])

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

    def test_sidebar_omits_settings_controls_and_source_dialog_remains_available(self):
        document = self.render()
        sidebar = document.split('<aside class="app-sidebar"', 1)[1].split('</aside>', 1)[0]
        self.assertNotIn('id="librarySource"', sidebar)
        self.assertNotIn('id="processingModeNote"', sidebar)
        ids = {a.get("id") for _, a in Elements(document).elements}
        self.assertTrue({"sourceDialog", "sourcePath", "sourceFolders", "sourceApply", "sourceCancel"}.issubset(ids))


if __name__ == "__main__":
    unittest.main()
