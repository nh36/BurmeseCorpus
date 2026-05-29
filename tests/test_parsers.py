from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from corpus_common import parse_structured_corpus_text
from parse_recently_found import parse_recently_found_entries
from parse_sagaing import parse_sagaing_block, split_blocks


FIXTURES = Path(__file__).resolve().parent / "fixtures"


class StructuredCorpusParserTests(unittest.TestCase):
    def test_structured_corpus_parser_extracts_record_and_lines(self) -> None:
        sample = """OBI CORPUS REF: OBI vol1 n°100 ob p167
INFORMATION SOURCE: Sample source
VOLUME: 1
PART: A
INSCRIPTION NUMBER: 100
PAGE NUMBER: 167
NUMBER OF FACES: 2
FACE: obverse
LANGUAGE:
INSCRIPTION SOURCE:
PLACE OF ORIGIN: Sample origin
CURRENT LOCATION: Sample location
REFERENCE NUMBER:
REFERENCES: Ref 1
TITLE: သင်ကြီး အို့သီသင် ကျောက်စာ ¤ saṅʻkrīḥ ʔuiɂsīsaṅʻ inscription
DATE: CS 586 = CE 1224
DONOR:
SUBJECT:
LENGTH:
NOTES:
FOOTNOTES:
INSCRIPTION:
၁\t။ သကရစ် ၅၈၆ ခူဆုန်
¤ 1\t|| sakaracʻ 586 khūchunʻ
<pg>၁၆၈</pg> ¤ <pg>168</pg>
၂\tလပ္လည် ဗုတ်တာဟူနိ
¤ 2\tlaplaññʻ butʻtāhūni
FULL TRANSLITERATION:
|| sakaracʻ 586 khūchunʻ laplaññʻ butʻtāhūni
"""
        parsed = parse_structured_corpus_text(
            sample,
            source_file="OBI_Corpus_Vol1/OBI_Vol1_No100__ob_p167.txt",
            created_by_script="test",
        )
        self.assertEqual(parsed.inscription["record_id"], "obi-v01-n0100-ob-p0167")
        self.assertEqual(parsed.inscription["title_original"], "သင်ကြီး အို့သီသင် ကျောက်စာ")
        self.assertEqual(parsed.inscription["date_normalized"]["ce_year"], 1224)
        self.assertEqual(len(parsed.lines), 2)
        self.assertEqual(parsed.lines[1]["page_break_before"], "168")
        self.assertEqual(parsed.lines[0]["transliteration"], "|| sakaracʻ 586 khūchunʻ")


class RecentlyFoundParserTests(unittest.TestCase):
    def test_recently_found_parser_finds_entries_and_pages(self) -> None:
        sample = (FIXTURES / "recently_found_sample.txt").read_text(encoding="utf-8")
        entries = parse_recently_found_entries(sample)
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["source_entry_number"], 10)
        self.assertEqual(entries[0]["source_page"], 26)
        self.assertEqual(entries[0]["source_title"], "ကန်ကျက်ကလိည်သူကြီးကျောက်စာ")
        self.assertEqual(entries[0]["face_markers"], ["မျက်နှာဘက်"])
        self.assertEqual(entries[1]["source_page"], 31)


class SagaingParserTests(unittest.TestCase):
    def test_sagaing_parser_builds_record_lines_and_structured_text(self) -> None:
        sample = (FIXTURES / "sagaing_sample.txt").read_text(encoding="utf-8")
        blocks = split_blocks(sample)
        self.assertEqual(len(blocks), 1)
        record, lines, structured_txt = parse_sagaing_block(blocks[0][0], blocks[0][1], 1)
        self.assertEqual(record["record_id"], "sagaing-z1203709-b0001-ob-p0007")
        self.assertEqual(record["title_original"], "မင်္ဂလာစေတီကျောက်စာ (က)")
        self.assertEqual(record["number_of_faces"], "2")
        self.assertEqual(record["continuous_text_original"] is not None, True)
        self.assertEqual(len(lines), 2)
        self.assertIn("FULL TRANSCRIPTION:", structured_txt)


if __name__ == "__main__":
    unittest.main()
