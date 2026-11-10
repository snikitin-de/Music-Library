import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1] / 'scripts'))
from genre_rules import classify_genres, normalized_genres
from generate_html_report import collect_genres_from_tracks, collect_genre_era_heatmap


class GenreRulesTests(unittest.TestCase):
    def test_compound_styles_and_translations_are_normalized_without_duplicates(self):
        self.assertEqual(normalized_genres('Pop/Rock; Pop; International Pop; Mezinárodní pop'), ['Pop Rock','Pop'])
        self.assertEqual(normalized_genres('Rap/Hip Hop; Hip-Hop; Rap'), ['Hip Hop'])
        self.assertEqual(normalized_genres('Taneční hudba; Dance; Рок; Klassik'), ['Dance','Rock','Classical'])

    def test_parenthesized_lists_do_not_create_broken_genre_names(self):
        self.assertEqual(normalized_genres('Dance & Electronic (Dance, Disco)'), ['Dance','Electronic','Disco'])
        self.assertEqual(normalized_genres('Rock (unsupported annotation)'), ['Rock'])

    def test_artist_language_and_release_categories_are_not_accepted_as_genres(self):
        result = classify_genres('Limp Bizkit; Chuukese; Music; Compilation; Filme/Videospiele; Pop')
        self.assertEqual(result['genres'], ['Pop'])
        self.assertEqual(len(result['issues']),5)
        self.assertEqual(result['status'],'partial')

    def test_unverified_label_is_reported_for_review_instead_of_guessed(self):
        result = classify_genres('Unverified New Style 987')
        self.assertEqual(result['genres'],[])
        self.assertEqual(result['status'],'unverified')
        self.assertEqual(result['issues'][0]['value'],'Unverified New Style 987')

    def test_each_track_is_counted_once_per_canonical_genre_in_both_charts(self):
        tracks=[{'tags':[{'kind':'genre','value':'Pop; International Pop; Pop/Rock'}, {'kind':'genre','value':'Pop'}, {'kind':'year','value':'2018'}]}]
        before=copy.deepcopy(tracks)
        self.assertEqual(collect_genres_from_tracks(tracks), {'Pop':1,'Pop Rock':1})
        rows=collect_genre_era_heatmap(tracks)['rows']
        self.assertEqual({row['genre']:row['total'] for row in rows},{'Pop':1,'Pop Rock':1})
        self.assertEqual(tracks,before)

    def test_verified_rare_styles_and_user_exclusion_remain_distinct(self):
        self.assertEqual(normalized_genres('Singer & Songwriter; Singer-songwriter; Psy-Trance; Indie Dance; Vgm'),['Singer-songwriter','Psytrance','Indie Dance','Video Game Music'])
