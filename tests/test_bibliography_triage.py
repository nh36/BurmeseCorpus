from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from corpus_common import write_tsv
from triage_bibliography import build_bibliography_triage
from validate_bibliography_triage import validate_bibliography_triage


class BibliographyTriageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.addCleanup(self.tempdir.cleanup)
        self.root = Path(self.tempdir.name)

    def sample_inputs(self) -> tuple[list[dict], list[dict], list[dict]]:
        raw_reference_rows = [
            {"raw_reference_string": "RDASB 1958-59", "occurrence_count": "2"},
            {"raw_reference_string": "RDASB 1959-60", "occurrence_count": "1"},
            {"raw_reference_string": "Harvey, History, p. 331", "occurrence_count": "1"},
            {"raw_reference_string": "U Min Hswe, no. 21", "occurrence_count": "1"},
        ]
        occurrence_rows = [
            {"record_id": "obi-1", "source_deposit": "zenodo_4321314", "raw_reference_string": "RDASB 1958-59"},
            {"record_id": "obi-2", "source_deposit": "zenodo_4321314", "raw_reference_string": "RDASB 1958-59"},
            {"record_id": "obi-3", "source_deposit": "zenodo_4321314", "raw_reference_string": "RDASB 1959-60"},
            {"record_id": "obi-4", "source_deposit": "zenodo_4321314", "raw_reference_string": "Harvey, History, p. 331"},
            {"record_id": "obi-5", "source_deposit": "zenodo_4321314", "raw_reference_string": "U Min Hswe, no. 21"},
        ]
        inscription_rows = [
            {"record_id": "obi-1", "references_original": "RDASB 1958-59"},
            {"record_id": "obi-2", "references_original": "RDASB 1958-59"},
            {"record_id": "obi-3", "references_original": "RDASB 1959-60"},
            {"record_id": "obi-4", "references_original": "Harvey, History, p. 331"},
            {"record_id": "obi-5", "references_original": "U Min Hswe, no. 21"},
            {"record_id": "sagaing-1", "references_original": None},
        ]
        return raw_reference_rows, occurrence_rows, inscription_rows

    def test_groups_obvious_related_references_conservatively(self) -> None:
        raw_reference_rows, occurrence_rows, inscription_rows = self.sample_inputs()

        family_rows, member_rows, work_candidates, report = build_bibliography_triage(
            raw_reference_rows,
            occurrence_rows,
            inscription_rows,
        )

        by_family_id = {row["family_id"]: row for row in family_rows}
        self.assertIn("fam-rdasb-publication", by_family_id)
        self.assertEqual(by_family_id["fam-rdasb-publication"]["member_count"], 2)
        self.assertEqual(by_family_id["fam-rdasb-publication"]["occurrence_count"], 3)
        rdasb_members = [row for row in member_rows if row["family_id"] == "fam-rdasb-publication"]
        self.assertEqual({row["raw_reference_string"] for row in rdasb_members}, {"RDASB 1958-59", "RDASB 1959-60"})
        self.assertEqual(report["records_without_references"], 1)
        self.assertEqual(len(work_candidates), len(family_rows))

    def test_leaves_unrelated_references_unclustered(self) -> None:
        raw_reference_rows, occurrence_rows, inscription_rows = self.sample_inputs()

        family_rows, _member_rows, _work_candidates, _report = build_bibliography_triage(
            raw_reference_rows,
            occurrence_rows,
            inscription_rows,
        )

        by_label = {row["family_label"]: row["family_id"] for row in family_rows}
        self.assertNotEqual(by_label["Harvey, History references"], by_label["U Min Hswe references"])

    def test_validation_detects_missing_member_family(self) -> None:
        bibliography_dir = self.root / "bibliography"
        bibliography_dir.mkdir(parents=True, exist_ok=True)
        write_tsv(
            bibliography_dir / "reference_families.tsv",
            [
                {
                    "family_id": "fam-one",
                    "family_label": "One",
                    "family_type": "unclear",
                    "member_count": 1,
                    "occurrence_count": 1,
                    "sample_raw_references": "One",
                    "likely_contains_translation": "unknown",
                    "review_status": "unreviewed",
                    "notes": "",
                }
            ],
            [
                "family_id",
                "family_label",
                "family_type",
                "member_count",
                "occurrence_count",
                "sample_raw_references",
                "likely_contains_translation",
                "review_status",
                "notes",
            ],
        )
        write_tsv(
            bibliography_dir / "reference_family_members.tsv",
            [
                {
                    "family_id": "fam-missing",
                    "raw_reference_string": "One",
                    "occurrence_count": 1,
                    "example_record_ids": "obi-1",
                    "notes": "",
                }
            ],
            ["family_id", "raw_reference_string", "occurrence_count", "example_record_ids", "notes"],
        )
        write_tsv(
            bibliography_dir / "bibliographic_work_candidates.tsv",
            [
                {
                    "work_candidate_id": "work-one",
                    "family_id": "fam-one",
                    "provisional_short_label": "One",
                    "author_original": "",
                    "author_normalized": "",
                    "year": "",
                    "title_original": "",
                    "title_normalized": "",
                    "publication_details": "",
                    "language": "",
                    "script": "latin",
                    "translation_relevance": "unknown",
                    "evidence_raw_references": "One",
                    "review_status": "unreviewed",
                    "notes": "",
                }
            ],
            [
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
            ],
        )
        (bibliography_dir / "bibliography_triage_report.json").write_text(
            json.dumps({"family_count": 1}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        result = validate_bibliography_triage(bibliography_dir)

        self.assertFalse(result["ok"])
        self.assertTrue(any("unknown family_id" in error for error in result["errors"]))

    def test_validation_detects_invalid_review_status_and_translation_relevance(self) -> None:
        bibliography_dir = self.root / "bibliography"
        bibliography_dir.mkdir(parents=True, exist_ok=True)
        write_tsv(
            bibliography_dir / "reference_families.tsv",
            [
                {
                    "family_id": "fam-one",
                    "family_label": "One",
                    "family_type": "unclear",
                    "member_count": 1,
                    "occurrence_count": 1,
                    "sample_raw_references": "One",
                    "likely_contains_translation": "unknown",
                    "review_status": "bad-status",
                    "notes": "",
                }
            ],
            [
                "family_id",
                "family_label",
                "family_type",
                "member_count",
                "occurrence_count",
                "sample_raw_references",
                "likely_contains_translation",
                "review_status",
                "notes",
            ],
        )
        write_tsv(
            bibliography_dir / "reference_family_members.tsv",
            [
                {
                    "family_id": "fam-one",
                    "raw_reference_string": "One",
                    "occurrence_count": 1,
                    "example_record_ids": "obi-1",
                    "notes": "",
                }
            ],
            ["family_id", "raw_reference_string", "occurrence_count", "example_record_ids", "notes"],
        )
        write_tsv(
            bibliography_dir / "bibliographic_work_candidates.tsv",
            [
                {
                    "work_candidate_id": "work-one",
                    "family_id": "fam-one",
                    "provisional_short_label": "One",
                    "author_original": "",
                    "author_normalized": "",
                    "year": "",
                    "title_original": "",
                    "title_normalized": "",
                    "publication_details": "",
                    "language": "",
                    "script": "latin",
                    "translation_relevance": "bad-value",
                    "evidence_raw_references": "One",
                    "review_status": "also-bad",
                    "notes": "",
                }
            ],
            [
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
            ],
        )
        (bibliography_dir / "bibliography_triage_report.json").write_text(
            json.dumps({"family_count": 1}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        result = validate_bibliography_triage(bibliography_dir)

        self.assertFalse(result["ok"])
        self.assertTrue(any("invalid review_status" in error for error in result["errors"]))
        self.assertTrue(any("invalid translation_relevance" in error for error in result["errors"]))

    def test_validation_passes_for_minimal_valid_fixture(self) -> None:
        bibliography_dir = self.root / "bibliography"
        bibliography_dir.mkdir(parents=True, exist_ok=True)
        write_tsv(
            bibliography_dir / "reference_families.tsv",
            [
                {
                    "family_id": "fam-rdasb-publication",
                    "family_label": "RDASB references",
                    "family_type": "publication",
                    "member_count": 1,
                    "occurrence_count": 2,
                    "sample_raw_references": "RDASB 1958-59",
                    "likely_contains_translation": "unknown",
                    "review_status": "unreviewed",
                    "notes": "",
                }
            ],
            [
                "family_id",
                "family_label",
                "family_type",
                "member_count",
                "occurrence_count",
                "sample_raw_references",
                "likely_contains_translation",
                "review_status",
                "notes",
            ],
        )
        write_tsv(
            bibliography_dir / "reference_family_members.tsv",
            [
                {
                    "family_id": "fam-rdasb-publication",
                    "raw_reference_string": "RDASB 1958-59",
                    "occurrence_count": 2,
                    "example_record_ids": "obi-1 | obi-2",
                    "notes": "",
                }
            ],
            ["family_id", "raw_reference_string", "occurrence_count", "example_record_ids", "notes"],
        )
        write_tsv(
            bibliography_dir / "bibliographic_work_candidates.tsv",
            [
                {
                    "work_candidate_id": "work-rdasb-publication",
                    "family_id": "fam-rdasb-publication",
                    "provisional_short_label": "RDASB references",
                    "author_original": "",
                    "author_normalized": "",
                    "year": "",
                    "title_original": "",
                    "title_normalized": "",
                    "publication_details": "",
                    "language": "",
                    "script": "latin",
                    "translation_relevance": "unknown",
                    "evidence_raw_references": "RDASB 1958-59",
                    "review_status": "unreviewed",
                    "notes": "",
                }
            ],
            [
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
            ],
        )
        (bibliography_dir / "bibliography_triage_report.json").write_text(
            json.dumps(
                {
                    "raw_reference_count": 1,
                    "reference_occurrence_count": 2,
                    "family_count": 1,
                    "work_candidate_count": 1,
                    "unclustered_reference_count": 1,
                    "families_by_type": {"publication": 1},
                    "translation_relevance_counts": {"unknown": 1},
                    "records_with_references": 2,
                    "records_without_references": 1,
                    "notes": ["Sagaing records currently have no raw references in the release input."],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        result = validate_bibliography_triage(bibliography_dir)

        self.assertTrue(result["ok"])


if __name__ == "__main__":
    unittest.main()
