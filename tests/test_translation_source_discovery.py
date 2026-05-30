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

from corpus_common import write_tsv
from discover_translation_sources import (
    PERIODICAL_ARTICLE_DISCOVERY_FIELDS,
    WITNESS_CANDIDATE_FIELDS,
    WITNESS_CLASSIFICATION_FIELDS,
    classify_candidate_witness,
    match_source_work_to_file,
)
from validate_translation_source_discovery import validate_translation_source_discovery


PLAN_FIELDS = [
    "source_work_key",
    "canonical_title",
    "source_family_ids",
    "work_type",
    "translation_likelihood",
    "edition_likelihood",
    "plate_or_image_likelihood",
    "priority",
    "evidence",
    "next_action",
    "notes",
    "discovery_status",
    "candidate_witness_count",
    "classified_witness_count",
    "confirmed_translation_witness_count",
    "confirmed_edition_witness_count",
    "confirmed_plate_witness_count",
    "next_review_action",
]

SOURCE_WORK_FIELDS = [
    "source_work_key",
    "canonical_title",
    "short_title",
    "authority_level",
    "work_type",
    "authors_editors",
    "date_or_date_range",
    "publisher_or_institution",
    "place",
    "related_source_family_ids",
    "related_acronyms",
    "authority_status",
    "evidence_source",
    "evidence_quote",
    "bibtex_key",
    "needs_human_review",
    "notes",
]


def base_source_row(**overrides: str) -> dict:
    row = {
        "source_work_key": "lucePeMaungTinInscriptionsOfBurma",
        "canonical_title": "Inscriptions of Burma",
        "short_title": "IOB",
        "authority_level": "book",
        "work_type": "book",
        "authors_editors": "G. H. Luce and U Pe Maung Tin",
        "date_or_date_range": "",
        "publisher_or_institution": "",
        "place": "",
        "related_source_family_ids": "sf-iob",
        "related_acronyms": "IOB",
        "authority_status": "confirmed_source_work",
        "evidence_source": "",
        "evidence_quote": "",
        "bibtex_key": "lucePeMaungTinInscriptionsOfBurma",
        "needs_human_review": "false",
        "notes": "",
        "title_tokens": ["inscriptions", "burma"],
        "author_surname": "luce",
        "is_container": False,
        "translation_likelihood": "possible",
        "edition_likelihood": "high",
        "plate_or_image_likelihood": "high",
    }
    row.update(overrides)
    return row


def base_file_record(**overrides: str) -> dict:
    row = {
        "candidate_file_id": "iob-plates",
        "candidate_file_label": "Luce&PeMaungTin_InscriptionsOfBurma(Plates3,4,5)_1960.pdf",
        "candidate_path_or_redacted_path": "data/local/bibliography_sources/iob/Luce&PeMaungTin_InscriptionsOfBurma(Plates3,4,5)_1960.pdf",
        "file_type": "pdf",
        "sha256_if_available": "abc123",
        "local_cache_status": "copied",
        "source_folder_hints": "Burmese",
        "all_original_paths": "OBI_LIBRARY_ROOT:Thematic/Burmese/Luce&PeMaungTin_InscriptionsOfBurma(Plates3,4,5)_1960.pdf",
        "primary_original_path": "",
        "evidence_priority": "high",
        "source_library_rows": [],
        "ocr_manifest_row": None,
        "ocr_snippets": [],
    }
    row["search_blob"] = " || ".join(
        [
            row["candidate_file_label"],
            row["candidate_path_or_redacted_path"],
            row["source_folder_hints"],
            row["all_original_paths"],
        ]
    )
    row.update(overrides)
    return row


class TranslationSourceDiscoveryTests(unittest.TestCase):
    def test_match_source_work_to_file_by_normalized_title(self) -> None:
        source_row = base_source_row()
        file_record = base_file_record()

        match = match_source_work_to_file(source_row, file_record)

        self.assertIsNotNone(match)
        assert match is not None
        self.assertEqual(match["match_type"], "normalized_title_filename")
        self.assertEqual(match["match_confidence"], "medium")

    def test_classify_source_edition_translation_plate_and_container(self) -> None:
        edition_source = base_source_row()
        edition_candidate = {
            "witness_id": "w1",
            "source_work_key": edition_source["source_work_key"],
            "canonical_title": edition_source["canonical_title"],
            "candidate_file_label": "Inscriptions of Burma Volume 1.pdf",
            "candidate_file_id": "iob-vol1",
            "candidate_path_or_redacted_path": "data/local/bibliography_sources/iob/Inscriptions of Burma Volume 1.pdf",
            "file_type": "pdf",
            "match_type": "exact_title_filename",
            "match_confidence": "high",
            "match_reason": "Exact title match",
            "sha256_if_available": "",
            "local_cache_status": "copied",
            "needs_human_review": "false",
            "notes": "",
        }
        edition_file = base_file_record(
            candidate_file_id="iob-vol1",
            candidate_file_label="Inscriptions of Burma Volume 1.pdf",
            all_original_paths="OBI_LIBRARY_ROOT:Inscriptions of Burma Volume 1.pdf",
            source_folder_hints="Burmese",
            ocr_snippets=[],
        )
        edition = classify_candidate_witness(edition_source, edition_candidate, edition_file)
        self.assertEqual(edition["witness_type"], "source_edition")

        translation_source = base_source_row(
            source_work_key="translationArticle",
            canonical_title="Myazedi translation note",
            title_tokens=["myazedi", "translation", "note"],
            author_surname="luce",
            authority_level="article",
            work_type="article",
            translation_likelihood="high",
            edition_likelihood="possible",
            plate_or_image_likelihood="low",
        )
        translation_candidate = {**edition_candidate, "witness_id": "w2", "source_work_key": "translationArticle", "canonical_title": "Myazedi translation note", "candidate_file_label": "Myazedi translation note.pdf"}
        translation_file = base_file_record(
            candidate_file_id="translation-note",
            candidate_file_label="Myazedi translation note.pdf",
            all_original_paths="OBI_LIBRARY_ROOT:Myazedi translation note.pdf",
            ocr_snippets=[{"snippet_text": "English translation with commentary and notes."}],
        )
        translation = classify_candidate_witness(translation_source, translation_candidate, translation_file)
        self.assertEqual(translation["witness_type"], "translation_source")
        self.assertEqual(translation["contains_translation"], "confirmed")

        plate = classify_candidate_witness(base_source_row(), {**edition_candidate, "witness_id": "w3", "candidate_file_label": "IOB plates volume.pdf"}, base_file_record())
        self.assertEqual(plate["witness_type"], "plate_volume")
        self.assertEqual(plate["contains_plate_or_image"], "confirmed")

        container_source = base_source_row(
            source_work_key="journalBurmaResearchSociety",
            canonical_title="Journal of the Burma Research Society",
            short_title="JBRS",
            authority_level="periodical",
            work_type="periodical",
            related_source_family_ids="sf-jbrs",
            related_acronyms="JBRS",
            is_container=True,
            translation_likelihood="unknown",
            edition_likelihood="unknown",
            plate_or_image_likelihood="low",
        )
        container_candidate = {**edition_candidate, "witness_id": "w4", "source_work_key": "journalBurmaResearchSociety", "canonical_title": "Journal of the Burma Research Society", "candidate_file_label": "011015.pdf"}
        container_file = base_file_record(
            candidate_file_id="011015",
            candidate_file_label="011015.pdf",
            all_original_paths="OBI_LIBRARY_ROOT:Thematic/Burmese/Burma JBRS/1911/011015.pdf",
            source_folder_hints="1911 | JBRS Originals",
        )
        container = classify_candidate_witness(container_source, container_candidate, container_file)
        self.assertEqual(container["witness_type"], "periodical_container")
        self.assertEqual(container["contains_translation"], "unknown")

    def test_validator_requires_matching_candidate_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            self._write_validation_fixture(
                tmp,
                classification_rows=[
                    {
                        "witness_id": "missing",
                        "source_work_key": "lucePeMaungTinInscriptionsOfBurma",
                        "canonical_title": "Inscriptions of Burma",
                        "candidate_file_label": "Inscriptions of Burma.pdf",
                        "witness_type": "source_edition",
                        "contains_translation": "possible",
                        "contains_edition_or_transliteration": "possible",
                        "contains_plate_or_image": "possible",
                        "contains_catalogue_metadata": "unknown",
                        "contains_secondary_discussion": "unknown",
                        "coverage_scope": "whole_work",
                        "confidence": "high",
                        "evidence_source": "filename",
                        "evidence_snippet": "Inscriptions of Burma.pdf",
                        "needs_human_review": "false",
                        "next_action": "Inspect file.",
                        "notes": "",
                    }
                ],
                report_overrides={"candidate_witness_count": 0, "classified_witness_count": 1},
            )

            errors = self._run_validation(tmp)

            self.assertTrue(any("no matching witness candidate row" in error for error in errors))

    def test_validator_rejects_confirmed_translation_without_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            candidate_rows = [self._candidate_row()]
            classification_rows = [
                {
                    **self._classification_row(),
                    "contains_translation": "confirmed",
                    "evidence_source": "",
                    "evidence_snippet": "",
                }
            ]
            self._write_validation_fixture(
                tmp,
                candidate_rows=candidate_rows,
                classification_rows=classification_rows,
                report_overrides={"candidate_witness_count": 1, "classified_witness_count": 1},
            )

            errors = self._run_validation(tmp)

            self.assertTrue(any("confirmed translation without evidence" in error for error in errors))

    def test_validator_blocks_periodical_container_translation_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            candidate_rows = [self._candidate_row(source_work_key="journalBurmaResearchSociety", canonical_title="Journal of the Burma Research Society")]
            classification_rows = [
                {
                    **self._classification_row(source_work_key="journalBurmaResearchSociety", canonical_title="Journal of the Burma Research Society"),
                    "witness_type": "periodical_container",
                    "contains_translation": "confirmed",
                }
            ]
            self._write_validation_fixture(
                tmp,
                source_rows=[
                    {
                        **base_source_row(),
                        "source_work_key": "journalBurmaResearchSociety",
                        "canonical_title": "Journal of the Burma Research Society",
                        "short_title": "JBRS",
                        "authority_level": "periodical",
                        "work_type": "periodical",
                        "related_source_family_ids": "sf-jbrs",
                        "related_acronyms": "JBRS",
                    }
                ],
                plan_rows=[
                    self._plan_row(source_work_key="journalBurmaResearchSociety", canonical_title="Journal of the Burma Research Society", discovery_status="needs_article_level_discovery", candidate_witness_count="1", classified_witness_count="1")
                ],
                candidate_rows=candidate_rows,
                classification_rows=classification_rows,
                report_overrides={"candidate_witness_count": 1, "classified_witness_count": 1},
            )

            errors = self._run_validation(tmp)

            self.assertTrue(any("periodical container" in error for error in errors))

    def test_validator_rejects_long_evidence_snippet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            candidate_rows = [self._candidate_row()]
            classification_rows = [
                {
                    **self._classification_row(),
                    "evidence_snippet": "x" * 400,
                }
            ]
            self._write_validation_fixture(
                tmp,
                candidate_rows=candidate_rows,
                classification_rows=classification_rows,
                report_overrides={"candidate_witness_count": 1, "classified_witness_count": 1},
            )

            errors = self._run_validation(tmp)

            self.assertTrue(any("short evidence snippet" in error for error in errors))

    def _plan_row(self, **overrides: str) -> dict:
        row = {
            "source_work_key": "lucePeMaungTinInscriptionsOfBurma",
            "canonical_title": "Inscriptions of Burma",
            "source_family_ids": "sf-iob",
            "work_type": "book",
            "translation_likelihood": "possible",
            "edition_likelihood": "high",
            "plate_or_image_likelihood": "high",
            "priority": "high",
            "evidence": "",
            "next_action": "",
            "notes": "",
            "discovery_status": "classified_provisional",
            "candidate_witness_count": "1",
            "classified_witness_count": "1",
            "confirmed_translation_witness_count": "0",
            "confirmed_edition_witness_count": "0",
            "confirmed_plate_witness_count": "0",
            "next_review_action": "",
        }
        row.update(overrides)
        return row

    def _candidate_row(self, **overrides: str) -> dict:
        row = {
            "witness_id": "w1",
            "source_work_key": "lucePeMaungTinInscriptionsOfBurma",
            "canonical_title": "Inscriptions of Burma",
            "candidate_file_label": "Inscriptions of Burma.pdf",
            "candidate_file_id": "iob",
            "candidate_path_or_redacted_path": "data/local/bibliography_sources/iob/Inscriptions of Burma.pdf",
            "file_type": "pdf",
            "match_type": "exact_title_filename",
            "match_confidence": "high",
            "match_reason": "Exact title match",
            "sha256_if_available": "abc",
            "local_cache_status": "copied",
            "needs_human_review": "false",
            "notes": "",
        }
        row.update(overrides)
        return row

    def _classification_row(self, **overrides: str) -> dict:
        row = {
            "witness_id": "w1",
            "source_work_key": "lucePeMaungTinInscriptionsOfBurma",
            "canonical_title": "Inscriptions of Burma",
            "candidate_file_label": "Inscriptions of Burma.pdf",
            "witness_type": "source_edition",
            "contains_translation": "possible",
            "contains_edition_or_transliteration": "possible",
            "contains_plate_or_image": "possible",
            "contains_catalogue_metadata": "unknown",
            "contains_secondary_discussion": "unknown",
            "coverage_scope": "whole_work",
            "confidence": "high",
            "evidence_source": "filename",
            "evidence_snippet": "Inscriptions of Burma.pdf",
            "needs_human_review": "false",
            "next_action": "Inspect file.",
            "notes": "",
        }
        row.update(overrides)
        return row

    def _write_validation_fixture(
        self,
        root: Path,
        *,
        source_rows: list[dict] | None = None,
        plan_rows: list[dict] | None = None,
        candidate_rows: list[dict] | None = None,
        classification_rows: list[dict] | None = None,
        report_overrides: dict | None = None,
    ) -> None:
        source_rows = source_rows or [base_source_row()]
        plan_rows = plan_rows or [self._plan_row()]
        candidate_rows = candidate_rows or []
        classification_rows = classification_rows or []
        write_tsv(root / "source_work_authority.tsv", source_rows, SOURCE_WORK_FIELDS)
        write_tsv(root / "translation_source_discovery_plan.tsv", plan_rows, PLAN_FIELDS)
        write_tsv(root / "witness_candidates.tsv", candidate_rows, WITNESS_CANDIDATE_FIELDS)
        write_tsv(root / "witness_classification.tsv", classification_rows, WITNESS_CLASSIFICATION_FIELDS)
        periodical_rows = [
            {
                "series_source_work_key": key,
                "series_title": key,
                "source_family_id": "",
                "known_raw_reference_examples": "",
                "likely_article_keys_or_titles": "",
                "local_file_candidates": "",
                "priority": "medium",
                "next_action": "",
                "notes": "",
            }
            for key in [
                "journalBurmaResearchSociety",
                "journalRoyalAsiaticSociety",
                "bulletinBurmaHistoricalCommission",
                "annualReportsArchaeologicalSurveyIndia",
                "epigraphiaBirmanica",
            ]
        ]
        write_tsv(root / "periodical_article_discovery_plan.tsv", periodical_rows, PERIODICAL_ARTICLE_DISCOVERY_FIELDS)
        report = {
            "source_work_count": len(plan_rows),
            "source_works_with_candidate_witnesses": len({row["source_work_key"] for row in candidate_rows}),
            "candidate_witness_count": len(candidate_rows),
            "classified_witness_count": len(classification_rows),
            "confirmed_translation_witness_count": 0,
            "possible_translation_witness_count": sum(row.get("contains_translation") == "possible" for row in classification_rows),
            "confirmed_edition_witness_count": 0,
            "possible_edition_witness_count": sum(row.get("contains_edition_or_transliteration") == "possible" for row in classification_rows),
            "plate_or_image_witness_count": sum(row.get("contains_plate_or_image") in {"possible", "confirmed"} for row in classification_rows),
            "periodical_container_count": sum(row.get("witness_type") == "periodical_container" for row in classification_rows),
            "article_discovery_needed_count": 5,
            "blocked_source_work_count": 0,
            "notes": ["fixture"],
        }
        if report_overrides:
            report.update(report_overrides)
        (root / "translation_source_discovery_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    def _run_validation(self, root: Path) -> list[str]:
        return validate_translation_source_discovery(
            plan_path=root / "translation_source_discovery_plan.tsv",
            source_work_authority_path=root / "source_work_authority.tsv",
            witness_candidates_path=root / "witness_candidates.tsv",
            witness_classification_path=root / "witness_classification.tsv",
            periodical_article_plan_path=root / "periodical_article_discovery_plan.tsv",
            report_path=root / "translation_source_discovery_report.json",
        )


if __name__ == "__main__":
    unittest.main()
