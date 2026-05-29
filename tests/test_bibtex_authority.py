from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from bibtex_common import parse_bibtex_text
from build_bibtex_authority import build_authority, parse_locator
from corpus_common import write_tsv
from import_external_bibtex import import_external_bibtex
from validate_bibtex_authority import validate_bibtex_authority


FAMILY_FIELDS = [
    "family_id",
    "family_label",
    "family_type",
    "member_count",
    "occurrence_count",
    "sample_raw_references",
    "likely_contains_translation",
    "review_status",
    "notes",
]

MEMBER_FIELDS = [
    "family_id",
    "raw_reference_string",
    "occurrence_count",
    "example_record_ids",
    "notes",
]

CANDIDATE_FIELDS = [
    "work_candidate_id",
    "family_id",
    "provisional_short_label",
    "author_original",
    "author_normalized",
    "year",
    "title_original",
    "title_normalized",
    "publication_details",
    "language",
    "script",
    "translation_relevance",
    "evidence_raw_references",
    "review_status",
    "notes",
]

SEED_FIELDS = [
    "abbreviation",
    "family_id",
    "provisional_label",
    "probable_bibtex_key",
    "source_type",
    "confidence",
    "evidence",
    "needs_human_review",
    "notes",
]


class BibtexAuthorityTests(unittest.TestCase):
    def test_import_external_bibtex_preserves_entries_and_warnings(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_path = temp_path / "sample.bib"
            input_path.write_text(
                "@book{harvey1925,\n"
                "  author = {Harvey, G. E.},\n"
                "  title = {History of Burma},\n"
                "  year = {1925}\n"
                "}\n\n"
                "{brokenKey,\n"
                "  title = {Broken but preserved}\n"
                "}\n",
                encoding="utf-8",
            )
            output_dir = temp_path / "external"
            report = import_external_bibtex(input_path, "sample.bib", output_dir)
            entries_path = output_dir / "sample_entries.tsv"
            report_path = output_dir / "sample_import_report.json"

            self.assertEqual(report["entry_count"], 2)
            self.assertTrue(report["parse_warnings"])
            self.assertTrue(entries_path.exists())
            self.assertTrue(report_path.exists())

            rows = entries_path.read_text(encoding="utf-8")
            self.assertIn("harvey1925", rows)
            self.assertIn("brokenKey", rows)
            self.assertIn("raw_entry_hash", rows)

    def test_parser_salvages_raw_bibtex_without_type(self) -> None:
        entries, warnings = parse_bibtex_text("{brokenKey,\n  title = {Broken}\n}\n", source_label="test")
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["entry_type"], "unknown")
        self.assertTrue(any("salvaged malformed entry" in warning for warning in warnings))

    def test_locator_parsing_examples(self) -> None:
        self.assertEqual(parse_locator("OBI 3, p. 2", "fam-obi-internal", "OBI"), ("3, p. 2", "volume_page"))
        self.assertEqual(parse_locator("Pl. II 198", "fam-plate-references", "Pl."), ("II 198", "plate"))
        self.assertEqual(parse_locator("List 90", "fam-list-catalogue", "List"), ("90", "catalogue_number"))
        self.assertEqual(parse_locator("RDASB 1971", "fam-rdasb-publication", "RDASB"), ("1971", "volume_page"))

    def write_fixture_tables(self, base: Path) -> tuple[Path, Path, Path, Path, Path]:
        families_path = base / "reference_families.tsv"
        members_path = base / "reference_family_members.tsv"
        candidates_path = base / "bibliographic_work_candidates.tsv"
        seeds_path = base / "source_abbreviation_seeds.tsv"
        external_entries_path = base / "asia_2_entries.tsv"

        write_tsv(
            families_path,
            [
                {
                    "family_id": "fam-obi-internal",
                    "family_label": "OBI",
                    "family_type": "source_catalogue",
                    "member_count": "1",
                    "occurrence_count": "1",
                    "sample_raw_references": "OBI 3, p. 2",
                    "likely_contains_translation": "no",
                    "review_status": "reviewed_provisional",
                    "notes": "",
                },
                {
                    "family_id": "fam-plate-references",
                    "family_label": "Pl.",
                    "family_type": "internal_reference",
                    "member_count": "1",
                    "occurrence_count": "1",
                    "sample_raw_references": "Pl. II 198",
                    "likely_contains_translation": "no",
                    "review_status": "needs_human_review",
                    "notes": "",
                },
                {
                    "family_id": "fam-list-catalogue",
                    "family_label": "List",
                    "family_type": "source_catalogue",
                    "member_count": "1",
                    "occurrence_count": "1",
                    "sample_raw_references": "List 90",
                    "likely_contains_translation": "no",
                    "review_status": "needs_human_review",
                    "notes": "",
                },
                {
                    "family_id": "fam-rdasb-publication",
                    "family_label": "RDASB",
                    "family_type": "publication",
                    "member_count": "1",
                    "occurrence_count": "1",
                    "sample_raw_references": "RDASB 1971",
                    "likely_contains_translation": "possible",
                    "review_status": "reviewed_provisional",
                    "notes": "",
                },
                {
                    "family_id": "fam-harvey-history",
                    "family_label": "Harvey, History",
                    "family_type": "book",
                    "member_count": "1",
                    "occurrence_count": "1",
                    "sample_raw_references": "Harvey, History, p. 10",
                    "likely_contains_translation": "possible",
                    "review_status": "reviewed_provisional",
                    "notes": "",
                },
                {
                    "family_id": "fam-unresolved",
                    "family_label": "Mystery Source",
                    "family_type": "unclear",
                    "member_count": "1",
                    "occurrence_count": "1",
                    "sample_raw_references": "Mystery Source 12",
                    "likely_contains_translation": "unknown",
                    "review_status": "unreviewed",
                    "notes": "",
                },
            ],
            FAMILY_FIELDS,
        )
        write_tsv(
            members_path,
            [
                {"family_id": "fam-obi-internal", "raw_reference_string": "OBI 3, p. 2", "occurrence_count": "2", "example_record_ids": "obi-1", "notes": ""},
                {"family_id": "fam-plate-references", "raw_reference_string": "Pl. II 198", "occurrence_count": "1", "example_record_ids": "obi-2", "notes": ""},
                {"family_id": "fam-list-catalogue", "raw_reference_string": "List 90", "occurrence_count": "3", "example_record_ids": "obi-3", "notes": ""},
                {"family_id": "fam-rdasb-publication", "raw_reference_string": "RDASB 1971", "occurrence_count": "2", "example_record_ids": "obi-4", "notes": ""},
                {"family_id": "fam-harvey-history", "raw_reference_string": "Harvey, History, p. 10", "occurrence_count": "1", "example_record_ids": "obi-5", "notes": ""},
                {"family_id": "fam-unresolved", "raw_reference_string": "Mystery Source 12", "occurrence_count": "1", "example_record_ids": "obi-6", "notes": ""},
            ],
            MEMBER_FIELDS,
        )
        write_tsv(
            candidates_path,
            [
                {
                    "work_candidate_id": "wc-obi",
                    "family_id": "fam-obi-internal",
                    "provisional_short_label": "OBI",
                    "author_original": "",
                    "author_normalized": "",
                    "year": "",
                    "title_original": "Old Burmese Inscriptions Corpus",
                    "title_normalized": "old burmese inscriptions corpus",
                    "publication_details": "",
                    "language": "my",
                    "script": "Mymr",
                    "translation_relevance": "unlikely_translation",
                    "evidence_raw_references": "OBI 3, p. 2",
                    "review_status": "reviewed_provisional",
                    "notes": "",
                },
                {
                    "work_candidate_id": "wc-list",
                    "family_id": "fam-list-catalogue",
                    "provisional_short_label": "List",
                    "author_original": "",
                    "author_normalized": "",
                    "year": "",
                    "title_original": "List catalogue reference",
                    "title_normalized": "list catalogue reference",
                    "publication_details": "",
                    "language": "",
                    "script": "",
                    "translation_relevance": "unknown",
                    "evidence_raw_references": "List 90",
                    "review_status": "needs_human_review",
                    "notes": "",
                },
                {
                    "work_candidate_id": "wc-rdasb",
                    "family_id": "fam-rdasb-publication",
                    "provisional_short_label": "RDASB",
                    "author_original": "",
                    "author_normalized": "",
                    "year": "",
                    "title_original": "Report of the Director, Archaeological Survey of Burma",
                    "title_normalized": "report of the director archaeological survey of burma",
                    "publication_details": "",
                    "language": "",
                    "script": "",
                    "translation_relevance": "possible_translation",
                    "evidence_raw_references": "RDASB 1971",
                    "review_status": "reviewed_provisional",
                    "notes": "",
                },
                {
                    "work_candidate_id": "wc-harvey",
                    "family_id": "fam-harvey-history",
                    "provisional_short_label": "Harvey, History",
                    "author_original": "Harvey",
                    "author_normalized": "harvey",
                    "year": "1925",
                    "title_original": "History of Burma",
                    "title_normalized": "history of burma",
                    "publication_details": "",
                    "language": "",
                    "script": "",
                    "translation_relevance": "possible_translation",
                    "evidence_raw_references": "Harvey, History, p. 10",
                    "review_status": "reviewed_provisional",
                    "notes": "",
                },
                {
                    "work_candidate_id": "wc-unresolved",
                    "family_id": "fam-unresolved",
                    "provisional_short_label": "Mystery Source",
                    "author_original": "",
                    "author_normalized": "",
                    "year": "",
                    "title_original": "",
                    "title_normalized": "",
                    "publication_details": "",
                    "language": "",
                    "script": "",
                    "translation_relevance": "unknown",
                    "evidence_raw_references": "Mystery Source 12",
                    "review_status": "unreviewed",
                    "notes": "",
                },
            ],
            CANDIDATE_FIELDS,
        )
        write_tsv(
            seeds_path,
            [
                {
                    "abbreviation": "List",
                    "family_id": "fam-list-catalogue",
                    "provisional_label": "List catalogue",
                    "probable_bibtex_key": "listCatalogueUnresolved",
                    "source_type": "source_catalogue",
                    "confidence": "medium",
                    "evidence": "triage seed",
                    "needs_human_review": "true",
                    "notes": "",
                }
            ],
            SEED_FIELDS,
        )
        write_tsv(
            external_entries_path,
            [
                {
                    "bibtex_key": "harveyExt",
                    "entry_type": "book",
                    "author": "Harvey, G. E.",
                    "editor": "",
                    "year": "1925",
                    "title": "History of Burma",
                    "booktitle": "",
                    "journal": "",
                    "publisher": "Longmans",
                    "address": "London",
                    "doi": "",
                    "url": "",
                    "isbn": "",
                    "raw_entry_hash": "abc",
                    "source_label": "asia 2.bib",
                    "notes": "",
                }
            ],
            [
                "bibtex_key",
                "entry_type",
                "author",
                "editor",
                "year",
                "title",
                "booktitle",
                "journal",
                "publisher",
                "address",
                "doi",
                "url",
                "isbn",
                "raw_entry_hash",
                "source_label",
                "notes",
            ],
        )
        return families_path, members_path, candidates_path, seeds_path, external_entries_path

    def test_build_authority_matches_external_and_generates_stub(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            families_path, members_path, candidates_path, seeds_path, external_entries_path = self.write_fixture_tables(temp_path)
            output_dir = temp_path / "authority"

            report = build_authority(
                reference_families_path=families_path,
                reference_members_path=members_path,
                work_candidates_path=candidates_path,
                seed_path=seeds_path,
                external_entries_path=external_entries_path,
                output_dir=output_dir,
            )

            authority_bib = (output_dir / "bibliography_authority.bib").read_text(encoding="utf-8")
            candidates_bib = (output_dir / "bibliography_candidates.bib").read_text(encoding="utf-8")
            authority_tsv = (output_dir / "bibtex_authority.tsv").read_text(encoding="utf-8")
            crosswalk_tsv = (output_dir / "raw_reference_to_bibtex.tsv").read_text(encoding="utf-8")

            self.assertIn("harvey1925history", authority_bib)
            self.assertIn("matchedexternalkey = {harveyExt}", authority_bib)
            self.assertIn("Provisional entry generated from corpus reference triage; requires human review", candidates_bib)
            self.assertIn("obiCorpusSource", crosswalk_tsv)
            self.assertIn("abbreviation_catalogue_match", crosswalk_tsv)
            self.assertIn("harvey1925history", crosswalk_tsv)
            self.assertIn("@misc{mystery,", candidates_bib)
            self.assertGreater(report["authority_entry_count"], 0)
            self.assertGreater(report["candidate_entry_count"], 0)
            self.assertIn("matched_external_key", authority_tsv)

    def test_validate_bibtex_authority_passes_for_valid_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            families_path, members_path, candidates_path, seeds_path, external_entries_path = self.write_fixture_tables(temp_path)
            output_dir = temp_path / "authority"
            build_authority(
                reference_families_path=families_path,
                reference_members_path=members_path,
                work_candidates_path=candidates_path,
                seed_path=seeds_path,
                external_entries_path=external_entries_path,
                output_dir=output_dir,
            )
            result = validate_bibtex_authority(
                authority_bib_path=output_dir / "bibliography_authority.bib",
                candidates_bib_path=output_dir / "bibliography_candidates.bib",
                authority_tsv_path=output_dir / "bibtex_authority.tsv",
                crosswalk_path=output_dir / "raw_reference_to_bibtex.tsv",
                families_path=families_path,
                external_entries_path=external_entries_path,
            )
            self.assertTrue(result["ok"], result["errors"])

    def test_validate_bibtex_authority_detects_duplicate_key(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            families_path = temp_path / "reference_families.tsv"
            crosswalk_path = temp_path / "raw_reference_to_bibtex.tsv"
            authority_tsv_path = temp_path / "bibtex_authority.tsv"
            authority_bib_path = temp_path / "bibliography_authority.bib"
            candidate_bib_path = temp_path / "bibliography_candidates.bib"
            external_entries_path = temp_path / "external.tsv"

            write_tsv(families_path, [{"family_id": "fam-1", "family_label": "OBI", "family_type": "source_catalogue", "member_count": "1", "occurrence_count": "1", "sample_raw_references": "OBI 1", "likely_contains_translation": "no", "review_status": "unreviewed", "notes": ""}], FAMILY_FIELDS)
            write_tsv(
                authority_tsv_path,
                [
                    {
                        "bibtex_key": "dupKey",
                        "entry_type": "misc",
                        "authority_status": "machine_stub",
                        "source_of_authority": "corpus_reference",
                        "matched_external_key": "",
                        "family_id": "fam-1",
                        "family_label": "OBI",
                        "family_type": "source_catalogue",
                        "author": "",
                        "editor": "",
                        "year": "",
                        "title": "OBI",
                        "shorttitle": "OBI",
                        "journal": "",
                        "booktitle": "",
                        "publisher": "",
                        "address": "",
                        "volume": "",
                        "number": "",
                        "pages": "",
                        "doi": "",
                        "url": "",
                        "isbn": "",
                        "language": "",
                        "script": "",
                        "translation_relevance": "unknown",
                        "review_status": "unreviewed",
                        "evidence": "test",
                        "notes": "test",
                    }
                ],
                [
                    "bibtex_key",
                    "entry_type",
                    "authority_status",
                    "source_of_authority",
                    "matched_external_key",
                    "family_id",
                    "family_label",
                    "family_type",
                    "author",
                    "editor",
                    "year",
                    "title",
                    "shorttitle",
                    "journal",
                    "booktitle",
                    "publisher",
                    "address",
                    "volume",
                    "number",
                    "pages",
                    "doi",
                    "url",
                    "isbn",
                    "language",
                    "script",
                    "translation_relevance",
                    "review_status",
                    "evidence",
                    "notes",
                ],
            )
            write_tsv(crosswalk_path, [{"raw_reference_string": "OBI 1", "family_id": "fam-1", "work_candidate_id": "wc-1", "bibtex_key": "dupKey", "match_type": "machine_stub_match", "match_confidence": "low", "locator": "1", "locator_type": "number", "evidence": "test", "needs_human_review": "true", "notes": ""}], ["raw_reference_string", "family_id", "work_candidate_id", "bibtex_key", "match_type", "match_confidence", "locator", "locator_type", "evidence", "needs_human_review", "notes"])
            write_tsv(external_entries_path, [], ["bibtex_key"])
            authority_bib_path.write_text("@misc{dupKey,\n  title = {One},\n}\n", encoding="utf-8")
            candidate_bib_path.write_text("@misc{dupKey,\n  title = {Two},\n}\n", encoding="utf-8")

            result = validate_bibtex_authority(
                authority_bib_path=authority_bib_path,
                candidates_bib_path=candidate_bib_path,
                authority_tsv_path=authority_tsv_path,
                crosswalk_path=crosswalk_path,
                families_path=families_path,
                external_entries_path=external_entries_path,
            )
            self.assertFalse(result["ok"])
            self.assertTrue(any("duplicate BibTeX keys" in error for error in result["errors"]))


if __name__ == "__main__":
    unittest.main()
