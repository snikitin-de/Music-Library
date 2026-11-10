import sys
import unittest
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from generate_html_report import better_quality_fields, render_quality


class QualityComparisonTests(unittest.TestCase):
    def quality(self,**changes):
        return {'format':'flac','bitrate':'1000000','bit_depth':'24','sample_rate':'44100','tag_score':'5','cover':'True','lyrics':'False','size':'20000000',**changes}

    def test_advantages_are_independent_for_each_file_and_ties_are_plain(self):
        left,right=self.quality(),self.quality(bitrate='700000',bit_depth='16',lyrics='True',size='18000000')
        self.assertEqual(better_quality_fields(left,right),({'bitrate','bit_depth'},{'lyrics'}))
        self.assertEqual(better_quality_fields(left,left),(set(),set()))

    def test_format_priority_is_used_without_comparing_bitrate_across_codecs(self):
        self.assertEqual(better_quality_fields(self.quality(format='flac',bitrate='200000'),self.quality(format='mp3',bitrate='320000')),({'format'},set()))

    def test_presence_overrides_are_shared_by_rendering_and_comparison(self):
        left,right=self.quality(),self.quality()
        self.assertEqual(better_quality_fields(left,right,left_cover=False,right_cover=True,left_lyrics=True,right_lyrics=False),({'lyrics'},{'cover'}))

    def test_unknown_values_are_not_treated_as_lower_quality(self):
        self.assertEqual(better_quality_fields({},self.quality()),(set(),set()))
        self.assertEqual(better_quality_fields(self.quality(bit_depth='unknown'),self.quality(bit_depth='16')),(set(),set()))

    def test_size_is_only_a_tie_breaker_and_identically_displayed_values_stay_plain(self):
        self.assertEqual(better_quality_fields(self.quality(size='22000000'),self.quality()),({'size'},set()))
        self.assertEqual(better_quality_fields(self.quality(bitrate='1000001',size='20000001'),self.quality()),(set(),set()))

    def test_table_highlights_only_requested_values(self):
        class Cells(HTMLParser):
            def __init__(self):super().__init__();self.cells=[];self.tables=0
            def handle_starttag(self,tag,attrs):
                if tag=='table':self.tables+=1
                if tag=='td':self.cells.append(dict(attrs))
        document=render_quality(self.quality(),better_fields={'bitrate','lyrics'})
        parsed=Cells();parsed.feed(document)
        self.assertEqual(parsed.tables,1)
        self.assertEqual(len(parsed.cells),8)
        self.assertEqual({cell['data-quality'] for cell in parsed.cells if 'quality-better' in cell.get('class','').split()},{'bitrate','lyrics'})
        self.assertTrue('music-pill' not in document)
