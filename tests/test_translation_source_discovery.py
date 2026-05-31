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
from verify_translation_witnesses import (
    ACQUISITION_ACTION_QUEUE_FIELDS,
    ACQUISITION_REVIEW_GAP_TYPES,
    CORE_DIRECT_WITNESS_SEARCH_FIELDS,
    DIRECT_WITNESS_ACQUISITION_PLAN_FIELDS,
    DIRECT_WITNESS_ACQUISITION_STATUS_FIELDS,
    DIRECT_WITNESS_ACQUISITION_SOURCE_KEYS,
    DIRECT_WITNESS_SEARCH_FIELDS,
    EB_FASCICLE_CONTENT_INSPECTION_FIELDS,
    EPIGRAPHIA_BIRMANICA_FASCICLE_COVERAGE_FIELDS,
    EPIGRAPHIA_BIRMANICA_REVIEW_FIELDS,
    EXTERNAL_CATALOGUE_CANDIDATE_TRIAGE_FIELDS,
    EXTERNAL_CATALOGUE_SEARCH_LOG_FIELDS,
    HUMAN_ACQUISITION_CHECKLIST_FIELDS,
    INSCRIPTIONS_OF_BURMA_TEXT_SEARCH_FIELDS,
    INSCRIPTIONS_OF_BURMA_TEXT_VOLUME_HUNT_FIELDS,
    MANUAL_REVIEW_QUEUE_FIELDS,
    MISSING_DIRECT_SEARCH_FIELDS,
    MISSING_CORE_WITNESS_HUNT_QUERIES,
    MISSING_CORE_WITNESS_HUNT_FIELDS,
    OPEN_DIRECT_WITNESS_GAP_TYPES,
    PLAUSIBLE_HUNT_TRIAGE_STATUSES,
    RESCUE_CANDIDATE_REVIEW_FIELDS,
    RULED_OUT_WITNESS_CANDIDATE_FIELDS,
    SIP_WITNESS_ID,
    SIP_WITNESS_INSPECTION_FIELDS,
    SOURCE_WITNESS_CONTENT_PROFILE_FIELDS,
    SNIPPET_FIELDS,
    SOURCE_WORK_GAP_FIELDS,
    VERIFICATION_FIELDS,
    WITNESS_HUNT_CANDIDATE_TRIAGE_FIELDS,
)


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
    "verified_direct_witness_count",
    "verified_translation_witness_count",
    "verified_edition_witness_count",
    "verified_plate_witness_count",
    "weak_false_positive_count",
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

    def test_validator_rejects_uem_inheriting_sip_direct_witness(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            self._write_validation_fixture(
                tmp,
                source_rows=[
                    {
                        **base_source_row(),
                        "source_work_key": "uemSelectionsPagan",
                        "canonical_title": "Selections from the Inscriptions of Pagan",
                        "short_title": "UEM",
                        "authors_editors": "U E Maung (ed.)",
                        "related_source_family_ids": "sf-uem",
                        "related_acronyms": "UEM",
                    }
                ],
                plan_rows=[self._plan_row(source_work_key="uemSelectionsPagan", canonical_title="Selections from the Inscriptions of Pagan", discovery_status="verified_direct_witness_found", verified_direct_witness_count="1", verified_edition_witness_count="1")],
                candidate_rows=[self._candidate_row(source_work_key="uemSelectionsPagan", canonical_title="Selections from the Inscriptions of Pagan", candidate_file_label="Luce&PeMaungTin 1928 inscriptions of Pagan.pdf")],
                classification_rows=[self._classification_row(source_work_key="uemSelectionsPagan", canonical_title="Selections from the Inscriptions of Pagan")],
                verification_rows=[
                    self._verification_row(
                        source_work_key="uemSelectionsPagan",
                        canonical_title="Selections from the Inscriptions of Pagan",
                        candidate_file_label="Luce&PeMaungTin 1928 inscriptions of Pagan.pdf",
                    )
                ],
                report_overrides={"candidate_witness_count": 1, "classified_witness_count": 1},
            )

            errors = self._run_validation(tmp)

            self.assertTrue(any("UEM incorrectly has a verified direct witness" in error for error in errors))

    def test_validator_requires_gap_row_for_needs_direct_witness_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            self._write_validation_fixture(
                tmp,
                source_rows=[{**base_source_row(), "source_work_key": "uemSelectionsPagan", "canonical_title": "Selections from the Inscriptions of Pagan", "short_title": "UEM", "authors_editors": "U E Maung (ed.)", "related_source_family_ids": "sf-uem", "related_acronyms": "UEM"}],
                plan_rows=[self._plan_row(source_work_key="uemSelectionsPagan", canonical_title="Selections from the Inscriptions of Pagan", discovery_status="needs_direct_witness_search")],
                gap_rows=[],
            )

            errors = self._run_validation(tmp)

            self.assertTrue(any("needs a matching source_work_witness_gaps.tsv row" in error for error in errors))

    def test_validator_requires_acquisition_plan_row_for_open_gap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            self._write_validation_fixture(
                tmp,
                source_rows=[{**base_source_row(), "source_work_key": "uemSelectionsPagan", "canonical_title": "Selections from the Inscriptions of Pagan", "short_title": "UEM", "authors_editors": "U E Maung (ed.)", "related_source_family_ids": "sf-uem", "related_acronyms": "UEM"}],
                plan_rows=[self._plan_row(source_work_key="uemSelectionsPagan", canonical_title="Selections from the Inscriptions of Pagan", discovery_status="needs_direct_witness_search")],
                gap_rows=[self._gap_row(source_work_key="uemSelectionsPagan", canonical_title="Selections from the Inscriptions of Pagan", gap_type="needs_direct_witness", current_status="needs_direct_witness")],
                direct_witness_acquisition_plan_rows=[],
            )

            errors = self._run_validation(tmp)

            self.assertTrue(any("missing a direct_witness_acquisition_plan.tsv row" in error for error in errors))

    def test_validator_requires_manual_review_queue_for_unconfirmed_sip_and_eb(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            self._write_validation_fixture(
                tmp,
                source_rows=[
                    base_source_row(source_work_key="sipSelectionsPagan", canonical_title="Selections from the Inscriptions of Pagan", short_title="SIP", authors_editors="Pe Maung Tin and G. H. Luce", related_source_family_ids="sf-sip", related_acronyms="SIP"),
                    base_source_row(source_work_key="epigraphiaBirmanica", canonical_title="Epigraphia Birmanica", short_title="EB", authors_editors="Charles Duroiselle", related_source_family_ids="sf-eb", related_acronyms="EB"),
                ],
                source_witness_content_profile_rows=[
                    {
                        "source_work_key": "sipSelectionsPagan",
                        "witness_id": SIP_WITNESS_ID,
                        "file_label": "Selections from the Inscriptions of Pagan.pdf",
                        "verified_witness_type": "source_edition",
                        "content_profile_status": "confirmed",
                        "title_page_status": "confirmed",
                        "contents_status": "unknown",
                        "sample_entry_status": "attempted_no_recoverable_text",
                        "translation_status": "unknown",
                        "edition_status": "confirmed",
                        "notes_commentary_status": "unknown",
                        "plate_image_status": "not_applicable",
                        "catalogue_metadata_status": "unknown",
                        "coverage_scope": "whole_work",
                        "confidence": "high",
                        "next_action": "Retry targeted sample-entry OCR.",
                        "notes": "",
                    },
                    {
                        "source_work_key": "epigraphiaBirmanica",
                        "witness_id": "eb-vol1",
                        "file_label": "Duroiselle - Epigraphia Birmanica Volume 1.pdf",
                        "verified_witness_type": "source_edition",
                        "content_profile_status": "confirmed",
                        "title_page_status": "confirmed",
                        "contents_status": "unknown",
                        "sample_entry_status": "unknown",
                        "translation_status": "unknown",
                        "edition_status": "confirmed",
                        "notes_commentary_status": "unknown",
                        "plate_image_status": "unknown",
                        "catalogue_metadata_status": "unknown",
                        "coverage_scope": "whole_work",
                        "confidence": "high",
                        "next_action": "Inspect contents.",
                        "notes": "",
                    },
                ],
                manual_review_queue_rows=[],
            )

            errors = self._run_validation(tmp)

            self.assertTrue(any("Selections from the Inscriptions of Pagan.pdf needs a matching manual_review_queue.tsv row" in error for error in errors))
            self.assertTrue(any("Duroiselle - Epigraphia Birmanica Volume 1.pdf needs a matching manual_review_queue.tsv row" in error for error in errors))

    def test_validator_requires_external_catalogue_log_for_acquisition_row(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            self._write_validation_fixture(
                tmp,
                source_rows=[{**base_source_row(), "source_work_key": "uemSelectionsPagan", "canonical_title": "Selections from the Inscriptions of Pagan", "short_title": "UEM", "authors_editors": "U E Maung (ed.)", "date_or_date_range": "1958", "related_source_family_ids": "sf-uem", "related_acronyms": "UEM"}],
                plan_rows=[self._plan_row(source_work_key="uemSelectionsPagan", canonical_title="Selections from the Inscriptions of Pagan", discovery_status="needs_direct_witness_search")],
                gap_rows=[self._gap_row(source_work_key="uemSelectionsPagan", canonical_title="Selections from the Inscriptions of Pagan", gap_type="needs_direct_witness", current_status="needs_direct_witness")],
                direct_witness_acquisition_plan_rows=[self._acquisition_plan_row(source_work_key="uemSelectionsPagan", canonical_title="Selections from the Inscriptions of Pagan", source_family_or_acronym="UEM", known_or_expected_author_editor="U E Maung (ed.)", known_or_expected_year="1958", known_or_expected_publisher_or_series="unknown")],
                external_catalogue_search_log_rows=[],
            )

            errors = self._run_validation(tmp)

            self.assertTrue(any("missing external catalogue search-log coverage" in error for error in errors))

    def test_validator_does_not_allow_ambiguous_catalogue_hit_to_close_gap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            self._write_validation_fixture(
                tmp,
                gap_rows=[
                    self._gap_row(
                        source_work_key="lucePeMaungTinInscriptionsOfBurma",
                        canonical_title="Inscriptions of Burma",
                        gap_type="has_authoritative_catalogue_record_needs_acquisition",
                        current_status="authoritative_catalogue_record_found",
                        notes="Ambiguous catalogue hit only; local corpus still lacks the companion text witness.",
                    )
                ],
                direct_witness_acquisition_plan_rows=[
                    self._acquisition_plan_row(
                        local_search_status="authoritative_catalogue_record_found",
                        known_or_expected_year="1933-1956",
                        known_or_expected_publisher_or_series="Oxford University Press, H. Milford",
                    )
                ],
                manual_review_queue_rows=[self._manual_review_queue_row()],
                external_catalogue_search_log_rows=[
                    self._external_catalogue_search_log_row(
                        result_status="ambiguous_match",
                        match_assessment="needs_human_review",
                        evidence_snippet="Portfolio-format overlap remains ambiguous.",
                    )
                ],
                external_catalogue_candidate_triage_rows=[
                    self._external_catalogue_candidate_triage_row(
                        triage_status="needs_human_review",
                        triage_reason="Ambiguous catalogue overlap only.",
                        is_authoritative_record="false",
                    )
                ],
            )

            errors = self._run_validation(tmp)

            self.assertTrue(any("cannot close from catalogue evidence" in error for error in errors))

    def test_validator_allows_authoritative_catalogue_record_without_local_witness(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            self._write_validation_fixture(
                tmp,
                plan_rows=[self._plan_row(discovery_status="verification_in_progress")],
                gap_rows=[
                    self._gap_row(
                        source_work_key="lucePeMaungTinInscriptionsOfBurma",
                        canonical_title="Inscriptions of Burma",
                        gap_type="has_authoritative_catalogue_record_needs_acquisition",
                        current_status="authoritative_catalogue_record_found",
                        notes="UC Berkeley Library | Inscriptions of Burma. | 1934- identifies the IOB text volume, but the local corpus still lacks the companion text witness.",
                    )
                ],
                direct_witness_acquisition_plan_rows=[
                    self._acquisition_plan_row(
                        local_search_status="authoritative_catalogue_record_found",
                        known_or_expected_year="1933-1956",
                        known_or_expected_publisher_or_series="Oxford University Press, H. Milford",
                    )
                ],
                manual_review_queue_rows=[self._manual_review_queue_row()],
                external_catalogue_search_log_rows=[self._external_catalogue_search_log_row()],
                external_catalogue_candidate_triage_rows=[self._external_catalogue_candidate_triage_row()],
            )

            errors = self._run_validation(tmp)

            self.assertFalse(any("cannot close from catalogue evidence" in error for error in errors))
            self.assertFalse(any("cannot leave acquisition review states" in error for error in errors))
            self.assertFalse(any("should use authoritative_catalogue_record_found" in error for error in errors))

    def test_validator_requires_iob_acquisition_status_and_berkeley_action_queue(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            self._write_validation_fixture(
                tmp,
                plan_rows=[self._plan_row(discovery_status="verification_in_progress")],
                gap_rows=[
                    self._gap_row(
                        source_work_key="lucePeMaungTinInscriptionsOfBurma",
                        canonical_title="Inscriptions of Burma",
                        gap_type="has_authoritative_catalogue_record_needs_acquisition",
                        current_status="authoritative_catalogue_record_found",
                        notes="UC Berkeley Library | Inscriptions of Burma. | 1934- identifies the IOB text volume, but the local corpus still lacks the companion text witness.",
                    )
                ],
                direct_witness_acquisition_plan_rows=[
                    self._acquisition_plan_row(
                        local_search_status="authoritative_catalogue_record_found",
                        known_or_expected_year="1933-1956",
                        known_or_expected_publisher_or_series="Oxford University Press, H. Milford",
                    )
                ],
                direct_witness_acquisition_status_rows=[
                    self._acquisition_status_row(
                        local_direct_witness_status="local_plate_witness_only",
                        external_catalogue_status="authoritative_catalogue_record_found",
                        acquisition_status="needs_local_copy_or_scan",
                    )
                ],
                manual_review_queue_rows=[self._manual_review_queue_row()],
                acquisition_action_queue_rows=[],
                external_catalogue_search_log_rows=[self._external_catalogue_search_log_row()],
                external_catalogue_candidate_triage_rows=[self._external_catalogue_candidate_triage_row()],
            )

            errors = self._run_validation(tmp)

            self.assertTrue(any("requires a matching acquisition_action_queue.tsv row" in error for error in errors))
            self.assertTrue(any("Berkeley-specific acquire_local_copy_or_scan action row" in error for error in errors))

    def test_validator_rejects_uem_acquisition_status_pretending_to_be_resolved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            self._write_validation_fixture(
                tmp,
                source_rows=[{**base_source_row(), "source_work_key": "uemSelectionsPagan", "canonical_title": "Selections from the Inscriptions of Pagan", "short_title": "UEM", "authors_editors": "U E Maung (ed.)", "date_or_date_range": "1958", "related_source_family_ids": "sf-uem", "related_acronyms": "UEM"}],
                plan_rows=[self._plan_row(source_work_key="uemSelectionsPagan", canonical_title="Selections from the Inscriptions of Pagan", discovery_status="needs_direct_witness_search")],
                gap_rows=[self._gap_row(source_work_key="uemSelectionsPagan", canonical_title="Selections from the Inscriptions of Pagan", gap_type="needs_direct_witness", current_status="needs_direct_witness", notes="No direct U E Maung witness found yet.")],
                direct_witness_acquisition_plan_rows=[self._acquisition_plan_row(source_work_key="uemSelectionsPagan", canonical_title="Selections from the Inscriptions of Pagan", source_family_or_acronym="UEM", known_or_expected_author_editor="U E Maung (ed.)", known_or_expected_year="1958", known_or_expected_publisher_or_series="unknown")],
                direct_witness_acquisition_status_rows=[
                    self._acquisition_status_row(
                        source_work_key="uemSelectionsPagan",
                        canonical_title="Selections from the Inscriptions of Pagan",
                        local_direct_witness_status="local_direct_witness_verified",
                        external_catalogue_status="bibliographic_clue_only",
                        acquisition_status="local_witness_available",
                        translation_coverage_status="unconfirmed",
                        edition_or_text_status="Incorrectly treated as resolved",
                        current_blocker="",
                        next_action="",
                        notes="",
                    )
                ],
                external_catalogue_search_log_rows=[
                    self._external_catalogue_search_log_row(
                        catalogue_log_row_id="uem-no-match",
                        source_work_key="uemSelectionsPagan",
                        search_target="Selections from the Inscriptions of Pagan",
                        catalogue_or_repository="WorldCat",
                        query="U E Maung Selections from the Inscriptions of Pagan",
                        query_type="title-search",
                        result_status="bibliographic_clue_only",
                        candidate_title="Selections from the Inscriptions of Pagan",
                        candidate_author_editor="U E Maung",
                        candidate_year="1958",
                        candidate_publisher_or_series="Rangoon",
                        candidate_url_or_identifier="",
                        evidence_snippet="Short clue only.",
                        match_assessment="needs_human_review",
                        next_action="Continue targeted catalogue search.",
                    )
                ],
                external_catalogue_candidate_triage_rows=[
                    self._external_catalogue_candidate_triage_row(
                        source_work_key="uemSelectionsPagan",
                        catalogue_log_row_id_or_query="uem-no-match",
                        candidate_title="Selections from the Inscriptions of Pagan",
                        candidate_author_editor="U E Maung",
                        candidate_year="1958",
                        catalogue_or_repository="WorldCat",
                        triage_status="bibliographic_clue_only",
                        triage_reason="Short title clue only.",
                        is_authoritative_record="false",
                    )
                ],
                acquisition_action_queue_rows=[],
            )

            errors = self._run_validation(tmp)

            self.assertTrue(any("should remain no_local_direct_witness" in error for error in errors))
            self.assertTrue(any("should remain in needs_authoritative_catalogue_record" in error for error in errors))

    def test_validator_requires_checklist_row_for_each_acquisition_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            self._write_validation_fixture(
                tmp,
                source_rows=[
                    {**base_source_row(), "source_work_key": "sipSelectionsPagan", "canonical_title": "Selections from the Inscriptions of Pagan", "short_title": "SIP", "authors_editors": "Pe Maung Tin and G. H. Luce"},
                    {**base_source_row(), "source_work_key": "epigraphiaBirmanica", "canonical_title": "Epigraphia Birmanica", "short_title": "EB", "authors_editors": "Charles Duroiselle"},
                ],
                direct_witness_acquisition_plan_rows=[
                    self._acquisition_plan_row(source_work_key="sipSelectionsPagan", canonical_title="Selections from the Inscriptions of Pagan", local_search_status="verified_direct_witness_translation_unconfirmed", priority="medium"),
                    self._acquisition_plan_row(source_work_key="epigraphiaBirmanica", canonical_title="Epigraphia Birmanica", local_search_status="verified_direct_witness_translation_unconfirmed", priority="medium"),
                ],
                direct_witness_acquisition_status_rows=[
                    self._acquisition_status_row(source_work_key="sipSelectionsPagan", canonical_title="Selections from the Inscriptions of Pagan", local_direct_witness_status="local_direct_witness_needs_content_review", external_catalogue_status="not_needed_for_current_step", acquisition_status="needs_manual_content_review", translation_coverage_status="needs_manual_review", priority="medium"),
                    self._acquisition_status_row(source_work_key="epigraphiaBirmanica", canonical_title="Epigraphia Birmanica", local_direct_witness_status="local_direct_witness_needs_content_review", external_catalogue_status="not_needed_for_current_step", acquisition_status="needs_manual_content_review", translation_coverage_status="needs_manual_review", priority="medium"),
                ],
                human_acquisition_checklist_rows=[
                    self._human_acquisition_checklist_row(
                        checklist_id="sip-manual-content-review",
                        source_work_key="sipSelectionsPagan",
                        task_type="manual_content_review",
                        task="Inspect SIP contents.",
                        success_condition="Reviewed.",
                        failure_condition="Still unconfirmed.",
                        priority="medium",
                    )
                ],
            )

            errors = self._run_validation(tmp)

            self.assertTrue(any("requires at least one human_acquisition_checklist.tsv row" in error for error in errors))

    def test_validator_requires_iob_checklist_to_keep_berkeley_local_copy_distinction(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            self._write_validation_fixture(
                tmp,
                human_acquisition_checklist_rows=[
                    self._human_acquisition_checklist_row(
                        task="Use the catalogue record to review the text volume.",
                        evidence_to_use="Catalogue metadata only.",
                        failure_condition="No local witness yet.",
                        notes="",
                    )
                ],
            )

            errors = self._run_validation(tmp)

            self.assertTrue(any("Berkeley acquisition lead and local-copy distinction" in error for error in errors))

    def test_validator_requires_manual_content_review_tasks_for_sip_and_eb(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            self._write_validation_fixture(
                tmp,
                source_rows=[
                    {**base_source_row(), "source_work_key": "sipSelectionsPagan", "canonical_title": "Selections from the Inscriptions of Pagan", "short_title": "SIP", "authors_editors": "Pe Maung Tin and G. H. Luce"},
                    {**base_source_row(), "source_work_key": "epigraphiaBirmanica", "canonical_title": "Epigraphia Birmanica", "short_title": "EB", "authors_editors": "Charles Duroiselle"},
                ],
                direct_witness_acquisition_plan_rows=[
                    self._acquisition_plan_row(source_work_key="sipSelectionsPagan", canonical_title="Selections from the Inscriptions of Pagan", local_search_status="verified_direct_witness_translation_unconfirmed", priority="medium"),
                    self._acquisition_plan_row(source_work_key="epigraphiaBirmanica", canonical_title="Epigraphia Birmanica", local_search_status="verified_direct_witness_translation_unconfirmed", priority="medium"),
                ],
                direct_witness_acquisition_status_rows=[
                    self._acquisition_status_row(source_work_key="sipSelectionsPagan", canonical_title="Selections from the Inscriptions of Pagan", local_direct_witness_status="local_direct_witness_needs_content_review", external_catalogue_status="not_needed_for_current_step", acquisition_status="needs_manual_content_review", translation_coverage_status="needs_manual_review", priority="medium"),
                    self._acquisition_status_row(source_work_key="epigraphiaBirmanica", canonical_title="Epigraphia Birmanica", local_direct_witness_status="local_direct_witness_needs_content_review", external_catalogue_status="not_needed_for_current_step", acquisition_status="needs_manual_content_review", translation_coverage_status="needs_manual_review", priority="medium"),
                ],
                human_acquisition_checklist_rows=[
                    self._human_acquisition_checklist_row(checklist_id="sip-bad", source_work_key="sipSelectionsPagan", task_type="locate_authoritative_catalogue_record", task="Wrong task type", success_condition="x", failure_condition="y", priority="medium"),
                    self._human_acquisition_checklist_row(checklist_id="eb-bad", source_work_key="epigraphiaBirmanica", task_type="locate_authoritative_catalogue_record", task="Wrong task type", success_condition="x", failure_condition="y", priority="medium"),
                ],
            )

            errors = self._run_validation(tmp)

            self.assertTrue(any("sipSelectionsPagan checklist rows must be manual content-review tasks" in error for error in errors))
            self.assertTrue(any("epigraphiaBirmanica checklist rows must be manual content-review tasks" in error for error in errors))

    def test_validator_requires_catalogue_or_identity_tasks_for_open_catalogue_targets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            self._write_validation_fixture(
                tmp,
                source_rows=[
                    {**base_source_row(), "source_work_key": "uemSelectionsPagan", "canonical_title": "Selections from the Inscriptions of Pagan", "short_title": "UEM", "authors_editors": "U E Maung"},
                    {**base_source_row(), "source_work_key": "tnInscriptionsPaganPinyaAva", "canonical_title": "Inscriptions of Pagan, Pinya and Ava", "short_title": "TN", "authors_editors": "U Tun Nyein"},
                    {**base_source_row(), "source_work_key": "ppaCatalogue", "canonical_title": "Inscriptions of Pagan, Pinya and Ava", "short_title": "PPA", "authors_editors": ""},
                    {**base_source_row(), "source_work_key": "ubSourceFamily", "canonical_title": "Inscriptions Collected in Upper Burma", "short_title": "UB", "authors_editors": ""},
                ],
                direct_witness_acquisition_plan_rows=[
                    self._acquisition_plan_row(source_work_key="uemSelectionsPagan", canonical_title="Selections from the Inscriptions of Pagan", source_family_or_acronym="UEM", known_or_expected_year="1958", known_or_expected_publisher_or_series="unknown"),
                    self._acquisition_plan_row(source_work_key="tnInscriptionsPaganPinyaAva", canonical_title="Inscriptions of Pagan, Pinya and Ava", source_family_or_acronym="TN", known_or_expected_year="1897", known_or_expected_publisher_or_series="Government Printing, Burma"),
                    self._acquisition_plan_row(source_work_key="ppaCatalogue", canonical_title="Inscriptions of Pagan, Pinya and Ava", source_family_or_acronym="PPA", known_or_expected_year="unknown", known_or_expected_publisher_or_series="Archaeological Survey of Burma"),
                    self._acquisition_plan_row(source_work_key="ubSourceFamily", canonical_title="Inscriptions Collected in Upper Burma", source_family_or_acronym="UB", known_or_expected_year="unknown", known_or_expected_publisher_or_series="Archaeological Survey of Burma"),
                ],
                direct_witness_acquisition_status_rows=[
                    self._acquisition_status_row(source_work_key="uemSelectionsPagan", canonical_title="Selections from the Inscriptions of Pagan", local_direct_witness_status="no_local_direct_witness", external_catalogue_status="bibliographic_clue_only", acquisition_status="needs_authoritative_catalogue_record", translation_coverage_status="unconfirmed"),
                    self._acquisition_status_row(source_work_key="tnInscriptionsPaganPinyaAva", canonical_title="Inscriptions of Pagan, Pinya and Ava", local_direct_witness_status="no_local_direct_witness", external_catalogue_status="ambiguous_or_cross_source_hits_only", acquisition_status="needs_authoritative_catalogue_record", translation_coverage_status="unconfirmed"),
                    self._acquisition_status_row(source_work_key="ppaCatalogue", canonical_title="Inscriptions of Pagan, Pinya and Ava", local_direct_witness_status="no_local_direct_witness", external_catalogue_status="ambiguous_or_cross_source_hits_only", acquisition_status="needs_authoritative_catalogue_record", translation_coverage_status="unconfirmed"),
                    self._acquisition_status_row(source_work_key="ubSourceFamily", canonical_title="Inscriptions Collected in Upper Burma", local_direct_witness_status="no_local_direct_witness", external_catalogue_status="bibliographic_clue_only", acquisition_status="needs_authoritative_catalogue_record", translation_coverage_status="unconfirmed"),
                ],
                human_acquisition_checklist_rows=[
                    self._human_acquisition_checklist_row(checklist_id="uem-wrong", source_work_key="uemSelectionsPagan", task_type="manual_content_review", task="Wrong", success_condition="x", failure_condition="y", priority="high"),
                    self._human_acquisition_checklist_row(checklist_id="tn-wrong", source_work_key="tnInscriptionsPaganPinyaAva", task_type="locate_authoritative_catalogue_record", task="Wrong", success_condition="x", failure_condition="y", priority="high"),
                    self._human_acquisition_checklist_row(checklist_id="ppa-wrong", source_work_key="ppaCatalogue", task_type="locate_authoritative_catalogue_record", task="Wrong", success_condition="x", failure_condition="y", priority="high"),
                    self._human_acquisition_checklist_row(checklist_id="ub-wrong", source_work_key="ubSourceFamily", task_type="manual_content_review", task="Wrong", success_condition="x", failure_condition="y", priority="high"),
                ],
            )

            errors = self._run_validation(tmp)

            self.assertTrue(any("uemSelectionsPagan checklist rows must require catalogue-acquisition work" in error for error in errors))
            self.assertTrue(any("tnInscriptionsPaganPinyaAva checklist rows must require source-identity resolution" in error for error in errors))
            self.assertTrue(any("ppaCatalogue checklist rows must require source-identity resolution" in error for error in errors))
            self.assertTrue(any("ubSourceFamily checklist rows must require catalogue-acquisition work" in error for error in errors))

    def test_validator_requires_phase_summary_guardrail_language(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            self._write_validation_fixture(
                tmp,
                phase_summary_text="# Translation source discovery phase summary\n\nShort summary without guardrails.\n",
            )

            errors = self._run_validation(tmp)

            self.assertTrue(any("phase_summary.md is missing required guardrail language" in error or "translation_source_discovery_phase_summary.md is missing required guardrail language" in error for error in errors))

    def test_validator_rejects_failed_sip_ocr_counting_as_sample_entry_inspection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            self._write_validation_fixture(
                tmp,
                source_rows=[base_source_row(source_work_key="sipSelectionsPagan", canonical_title="Selections from the Inscriptions of Pagan", short_title="SIP", authors_editors="Pe Maung Tin and G. H. Luce", related_source_family_ids="sf-sip", related_acronyms="SIP")],
                plan_rows=[self._plan_row(source_work_key="sipSelectionsPagan", canonical_title="Selections from the Inscriptions of Pagan", discovery_status="verified_direct_witness_found", verified_direct_witness_count="1", verified_edition_witness_count="1")],
                candidate_rows=[self._candidate_row(witness_id=SIP_WITNESS_ID, source_work_key="sipSelectionsPagan", canonical_title="Selections from the Inscriptions of Pagan", candidate_file_label="Selections from the Inscriptions of Pagan.pdf", candidate_file_id="sip-pdf")],
                classification_rows=[self._classification_row(witness_id=SIP_WITNESS_ID, source_work_key="sipSelectionsPagan", canonical_title="Selections from the Inscriptions of Pagan", candidate_file_label="Selections from the Inscriptions of Pagan.pdf")],
                verification_rows=[self._verification_row(witness_id=SIP_WITNESS_ID, source_work_key="sipSelectionsPagan", canonical_title="Selections from the Inscriptions of Pagan", candidate_file_label="Selections from the Inscriptions of Pagan.pdf", contains_translation_verified="unknown", contains_edition_verified="confirmed")],
                sip_inspection_rows=[
                    {
                        "witness_id": SIP_WITNESS_ID,
                        "file_label": "Selections from the Inscriptions of Pagan.pdf",
                        "inspection_area": "sample_entry",
                        "inspection_method": "ocr",
                        "evidence_snippet": "",
                        "contains_translation": "unknown",
                        "contains_edition_or_transliteration": "unknown",
                        "contains_notes_or_commentary": "unknown",
                        "inspection_status": "attempted_no_recoverable_text",
                        "next_action": "Retry targeted OCR.",
                        "notes": "No recoverable sample-entry OCR was isolated.",
                    }
                ],
                source_witness_content_profile_rows=[
                    {
                        "source_work_key": "sipSelectionsPagan",
                        "witness_id": SIP_WITNESS_ID,
                        "file_label": "Selections from the Inscriptions of Pagan.pdf",
                        "verified_witness_type": "source_edition",
                        "content_profile_status": "confirmed",
                        "title_page_status": "confirmed",
                        "contents_status": "unknown",
                        "sample_entry_status": "attempted_no_recoverable_text",
                        "translation_status": "unknown",
                        "edition_status": "confirmed",
                        "notes_commentary_status": "unknown",
                        "plate_image_status": "not_applicable",
                        "catalogue_metadata_status": "unknown",
                        "coverage_scope": "whole_work",
                        "confidence": "high",
                        "next_action": "Retry targeted sample-entry OCR.",
                        "notes": "",
                    }
                ],
                report_overrides={"sip_sample_entry_inspected": True, "sip_sample_entry_ocr_attempted": True, "sip_translation_status": "unconfirmed", "sip_contains_translation_status": "unconfirmed"},
            )

            errors = self._run_validation(tmp)

            self.assertTrue(any("sip_sample_entry_inspected cannot be true" in error for error in errors))

    def test_validator_rejects_iob_plate_as_text_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            self._write_validation_fixture(
                tmp,
                iob_text_search_rows=[
                    {
                        "query": "Inscriptions of Burma text",
                        "matched_file_label": "Luce&PeMaungTin_InscriptionsOfBurma(Plates3,4,5)_1960.pdf",
                        "matched_file_id": "iob-plates",
                        "match_type": "filename",
                        "match_confidence": "medium",
                        "short_evidence": "Matched plate PDF filename.",
                        "searched_sources": "local_file_manifest",
                        "search_scope": "filename search",
                        "search_date_or_run_id": "fixture",
                        "search_result_status": "candidate_found",
                        "recommended_action": "Keep searching for text volume.",
                        "notes": "",
                        "is_text_witness_candidate": "true",
                        "is_plate_witness_candidate": "true",
                        "false_positive_for_text": "false",
                        "reason_not_text_witness": "",
                    }
                ],
            )

            errors = self._run_validation(tmp)

            self.assertTrue(any("must not be marked as a text witness candidate" in error for error in errors))

    def test_validator_rejects_iob_volume_hunt_plate_with_promotable_action(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            self._write_validation_fixture(
                tmp,
                iob_text_volume_hunt_rows=[
                    {
                        "query": "Inscriptions of Burma 1960 text",
                        "matched_file_label": "Luce&PeMaungTin_InscriptionsOfBurma(Plates3,4,5)_1960.pdf",
                        "matched_file_id": "iob-plates",
                        "match_type": "filename",
                        "match_confidence": "medium",
                        "short_evidence": "Matched plate PDF filename.",
                        "searched_sources": "local_file_manifest",
                        "search_scope": "filename search",
                        "search_date_or_run_id": "fixture",
                        "search_result_status": "candidate_found",
                        "recommended_action": "Inspect title page before promoting this as a direct witness.",
                        "notes": "",
                        "is_text_witness_candidate": "false",
                        "is_plate_witness_candidate": "true",
                        "false_positive_for_text": "true",
                        "reason_not_text_witness": "plate/facsimile volume, not companion text volume",
                    }
                ],
                witness_hunt_candidate_triage_rows=[
                    {
                        "hunt_table": "inscriptions_of_burma_text_volume_hunt",
                        "source_work_key": "lucePeMaungTinInscriptionsOfBurma",
                        "query": "Inscriptions of Burma 1960 text",
                        "matched_file_label": "Luce&PeMaungTin_InscriptionsOfBurma(Plates3,4,5)_1960.pdf",
                        "matched_file_id": "iob-plates",
                        "initial_match_type": "filename",
                        "initial_search_result_status": "candidate_found",
                        "triage_status": "known_false_positive",
                        "triage_reason": "plate/facsimile volume, not companion text volume",
                        "is_cross_source_match": "false",
                        "is_secondary_or_unrelated": "false",
                        "is_known_false_positive": "true",
                        "recommended_action": "Retain as a plate witness; continue searching for the companion text volume.",
                        "notes": "",
                    }
                ],
            )

            errors = self._run_validation(tmp)

            self.assertTrue(any("still uses a promotable direct-witness action" in error for error in errors))

    def test_validator_rejects_iob_plate_profile_with_sample_entry_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            self._write_validation_fixture(
                tmp,
                source_witness_content_profile_rows=[
                    {
                        "source_work_key": "lucePeMaungTinInscriptionsOfBurma",
                        "witness_id": "iob-plates",
                        "file_label": "Luce&PeMaungTin_InscriptionsOfBurma(Plates3,4,5)_1960.pdf",
                        "verified_witness_type": "plate_volume",
                        "content_profile_status": "confirmed",
                        "title_page_status": "confirmed",
                        "contents_status": "not_applicable",
                        "sample_entry_status": "possible",
                        "translation_status": "not_applicable",
                        "edition_status": "not_applicable",
                        "notes_commentary_status": "unknown",
                        "plate_image_status": "confirmed",
                        "catalogue_metadata_status": "unknown",
                        "coverage_scope": "plate/facsimile witness",
                        "confidence": "high",
                        "next_action": "Retain as a plate/facsimile witness and continue hunting the companion text volume.",
                        "notes": "",
                    }
                ],
            )

            errors = self._run_validation(tmp)

            self.assertTrue(any("sample_entry_status=not_applicable" in error for error in errors))

    def test_validator_requires_full_missing_core_hunt_query_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            self._write_validation_fixture(
                tmp,
                missing_core_witness_hunt_rows=[
                    {
                        "source_work_key": "uemSelectionsPagan",
                        "query": "U E Maung",
                        "variant_type": "author_name",
                        "matched_file_label": "",
                        "matched_file_id": "",
                        "match_type": "not_found",
                        "match_confidence": "low",
                        "short_evidence": "",
                        "searched_sources": "local_file_manifest;source_library_manifest;ocr_text_index;raw_reference_to_bibtex",
                        "search_scope": "targeted author/title/abbreviation search",
                        "search_date_or_run_id": "fixture",
                        "search_result_status": "not_found",
                        "is_known_false_positive": "false",
                        "false_positive_reason": "",
                        "recommended_action": "Continue targeted local/direct-witness search.",
                        "notes": "",
                    }
                ],
            )

            errors = self._run_validation(tmp)

            self.assertTrue(any("missing expected queries" in error for error in errors))

    def test_validator_rejects_promotable_uem_sip_false_positive_hunt_row(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            self._write_validation_fixture(
                tmp,
                source_rows=[base_source_row(source_work_key="sipSelectionsPagan", canonical_title="Selections from the Inscriptions of Pagan", short_title="SIP", authors_editors="Pe Maung Tin and G. H. Luce", related_source_family_ids="sf-sip", related_acronyms="SIP")],
                candidate_rows=[self._candidate_row(witness_id=SIP_WITNESS_ID, source_work_key="sipSelectionsPagan", canonical_title="Selections from the Inscriptions of Pagan", candidate_file_label="Luce 1928 inscriptions of Pagan.pdf", candidate_file_id="sip-pdf")],
                verification_rows=[
                    self._verification_row(
                        witness_id="uem-fp",
                        source_work_key="uemSelectionsPagan",
                        canonical_title="Selections from the Inscriptions of Pagan",
                        candidate_file_label="Luce 1928 inscriptions of Pagan.pdf",
                        verification_status="weak_false_positive",
                        directness="weak_related_match",
                    )
                ],
                missing_core_witness_hunt_rows=[
                    {
                        "source_work_key": source_work_key,
                        "query": query,
                        "variant_type": variant_type,
                        "matched_file_label": ("Luce 1928 inscriptions of Pagan.pdf" if query == "Selections from the Inscriptions of Pagan U E Maung" else ""),
                        "matched_file_id": ("sip-pdf" if query == "Selections from the Inscriptions of Pagan U E Maung" else ""),
                        "match_type": ("normalized_title_filename" if query == "Selections from the Inscriptions of Pagan U E Maung" else "not_found"),
                        "match_confidence": ("medium" if query == "Selections from the Inscriptions of Pagan U E Maung" else "low"),
                        "short_evidence": "",
                        "searched_sources": "local_file_manifest;source_library_manifest;ocr_text_index;raw_reference_to_bibtex",
                        "search_scope": "targeted author/title/abbreviation search across local manifests, source-library paths, author-folder path hints, OCR index, and bibliography crosswalk",
                        "search_date_or_run_id": "fixture",
                        "search_result_status": ("candidate_found" if query == "Selections from the Inscriptions of Pagan U E Maung" else "not_found"),
                        "is_known_false_positive": ("false" if query == "Selections from the Inscriptions of Pagan U E Maung" else "false"),
                        "false_positive_reason": "",
                        "recommended_action": ("Inspect title page before promoting this as a direct witness." if query == "Selections from the Inscriptions of Pagan U E Maung" else "Continue targeted local/direct-witness search."),
                        "notes": "",
                    }
                    for source_work_key, query_rows in MISSING_CORE_WITNESS_HUNT_QUERIES.items()
                    for query, variant_type in query_rows
                ],
                witness_hunt_candidate_triage_rows=[
                    {
                        "hunt_table": "missing_core_witness_hunt",
                        "source_work_key": "uemSelectionsPagan",
                        "query": "Selections from the Inscriptions of Pagan U E Maung",
                        "matched_file_label": "Luce 1928 inscriptions of Pagan.pdf",
                        "matched_file_id": "sip-pdf",
                        "initial_match_type": "normalized_title_filename",
                        "initial_search_result_status": "candidate_found",
                        "triage_status": "known_false_positive",
                        "triage_reason": "known SIP/UEM false positive",
                        "is_cross_source_match": "false",
                        "is_secondary_or_unrelated": "false",
                        "is_known_false_positive": "true",
                        "recommended_action": "Inspect title page before promoting this as a direct witness.",
                        "notes": "",
                    }
                ],
            )

            errors = self._run_validation(tmp)

            self.assertTrue(any("cannot be surfaced as promotable" in error for error in errors))

    def test_validator_rejects_missing_triage_for_candidate_hunt_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            self._write_validation_fixture(
                tmp,
                iob_text_volume_hunt_rows=[
                    {
                        "query": "Inscriptions of Burma text volume",
                        "matched_file_label": "a_list_of_inscriptions_found_in_burma_part_i.pdf",
                        "matched_file_id": "list-pdf",
                        "match_type": "normalized_title_filename",
                        "match_confidence": "medium",
                        "short_evidence": "Matched A List of Inscriptions Found in Burma Part I.pdf",
                        "searched_sources": "local_file_manifest",
                        "search_scope": "filename search",
                        "search_date_or_run_id": "fixture",
                        "search_result_status": "candidate_found",
                        "recommended_action": "Inspect title page before promoting this as a direct witness.",
                        "notes": "",
                        "is_text_witness_candidate": "false",
                        "is_plate_witness_candidate": "false",
                        "false_positive_for_text": "false",
                        "reason_not_text_witness": "separate List source work, not the Luce/Pe Maung Tin companion text volume",
                    }
                ],
            )

            errors = self._run_validation(tmp)

            self.assertTrue(any("missing coverage for inscriptions_of_burma_text_volume_hunt" in error for error in errors))

    def test_validator_rejects_iob_list_candidate_as_text_witness(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            self._write_validation_fixture(
                tmp,
                gap_rows=[
                    {
                        "source_work_key": "lucePeMaungTinInscriptionsOfBurma",
                        "canonical_title": "Inscriptions of Burma",
                        "current_status": "verification_in_progress",
                        "verified_direct_witness_count": "0",
                        "verified_translation_witness_count": "0",
                        "verified_edition_witness_count": "0",
                        "verified_plate_witness_count": "2",
                        "candidate_count": "0",
                        "best_candidate_witness_id": "",
                        "best_candidate_file_label": "",
                        "gap_type": "has_verified_plate_but_needs_text",
                        "priority": "high",
                        "next_action": "Find the companion text volume before treating Inscriptions of Burma as text-covered.",
                        "notes": "Verified plate/facsimile witnesses exist, but the current text-volume hunt only yields cross-source leads, secondary/article matches, bibliographic clues, or false positives.",
                    }
                ],
                iob_text_volume_hunt_rows=[
                    {
                        "query": "Inscriptions of Burma text volume",
                        "matched_file_label": "a_list_of_inscriptions_found_in_burma_part_i.pdf",
                        "matched_file_id": "list-pdf",
                        "match_type": "normalized_title_filename",
                        "match_confidence": "medium",
                        "short_evidence": "Matched A List of Inscriptions Found in Burma Part I.pdf",
                        "searched_sources": "local_file_manifest",
                        "search_scope": "filename search",
                        "search_date_or_run_id": "fixture",
                        "search_result_status": "candidate_found",
                        "recommended_action": "Inspect title page before promoting this as a direct witness.",
                        "notes": "",
                        "is_text_witness_candidate": "true",
                        "is_plate_witness_candidate": "false",
                        "false_positive_for_text": "false",
                        "reason_not_text_witness": "",
                    }
                ],
                witness_hunt_candidate_triage_rows=[
                    {
                        "hunt_table": "inscriptions_of_burma_text_volume_hunt",
                        "source_work_key": "lucePeMaungTinInscriptionsOfBurma",
                        "query": "Inscriptions of Burma text volume",
                        "matched_file_label": "a_list_of_inscriptions_found_in_burma_part_i.pdf",
                        "matched_file_id": "list-pdf",
                        "initial_match_type": "normalized_title_filename",
                        "initial_search_result_status": "candidate_found",
                        "triage_status": "cross_source_witness",
                        "triage_reason": "Matched the separate List of Inscriptions source work, not the Luce/Pe Maung Tin companion text volume.",
                        "is_cross_source_match": "true",
                        "is_secondary_or_unrelated": "false",
                        "is_known_false_positive": "false",
                        "recommended_action": "Retain only as a reviewed cross-source List witness; continue searching for the Luce/Pe Maung Tin companion text volume.",
                        "notes": "",
                    }
                ],
            )

            errors = self._run_validation(tmp)

            self.assertTrue(any("a_list_of_inscriptions_found_in_burma_part_i.pdf cannot count as an IOB text witness candidate" in error for error in errors))

    def test_validator_rejects_iob_111029_candidate_as_secondary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            self._write_validation_fixture(
                tmp,
                gap_rows=[
                    {
                        "source_work_key": "lucePeMaungTinInscriptionsOfBurma",
                        "canonical_title": "Inscriptions of Burma",
                        "current_status": "verification_in_progress",
                        "verified_direct_witness_count": "0",
                        "verified_translation_witness_count": "0",
                        "verified_edition_witness_count": "0",
                        "verified_plate_witness_count": "2",
                        "candidate_count": "0",
                        "best_candidate_witness_id": "",
                        "best_candidate_file_label": "",
                        "gap_type": "has_verified_plate_but_needs_text",
                        "priority": "high",
                        "next_action": "Find the companion text volume before treating Inscriptions of Burma as text-covered.",
                        "notes": "Verified plate/facsimile witnesses exist, but the current text-volume hunt only yields cross-source leads, secondary/article matches, bibliographic clues, or false positives.",
                    }
                ],
                iob_text_volume_hunt_rows=[
                    {
                        "query": "Luce Pe Maung Tin Portfolio I",
                        "matched_file_label": "111029.pdf",
                        "matched_file_id": "111029.pdf",
                        "match_type": "source_family_match",
                        "match_confidence": "medium",
                        "short_evidence": "OBI_LIBRARY_ROOT:ChroniclleTagaung_PeMaungTinLuce1921.pdf",
                        "searched_sources": "local_file_manifest",
                        "search_scope": "filename search",
                        "search_date_or_run_id": "fixture",
                        "search_result_status": "candidate_found",
                        "recommended_action": "Inspect title page before promoting this as a direct witness.",
                        "notes": "",
                        "is_text_witness_candidate": "true",
                        "is_plate_witness_candidate": "false",
                        "false_positive_for_text": "false",
                        "reason_not_text_witness": "",
                    }
                ],
                witness_hunt_candidate_triage_rows=[
                    {
                        "hunt_table": "inscriptions_of_burma_text_volume_hunt",
                        "source_work_key": "lucePeMaungTinInscriptionsOfBurma",
                        "query": "Luce Pe Maung Tin Portfolio I",
                        "matched_file_label": "111029.pdf",
                        "matched_file_id": "111029.pdf",
                        "initial_match_type": "source_family_match",
                        "initial_search_result_status": "candidate_found",
                        "triage_status": "secondary_or_unrelated",
                        "triage_reason": "Matched a Luce/Pe Maung Tin chronicle/article lead rather than the companion Inscriptions of Burma text volume.",
                        "is_cross_source_match": "false",
                        "is_secondary_or_unrelated": "true",
                        "is_known_false_positive": "false",
                        "recommended_action": "Retain only as a reviewed secondary/cross-source lead; continue searching for the Luce/Pe Maung Tin companion text volume.",
                        "notes": "",
                    }
                ],
            )

            errors = self._run_validation(tmp)

            self.assertTrue(any("111029.pdf cannot count as an IOB text witness candidate" in error for error in errors))

    def test_validator_rejects_eb_translation_confirmation_without_explicit_signal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            self._write_validation_fixture(
                tmp,
                source_witness_content_profile_rows=[
                    {
                        "source_work_key": "epigraphiaBirmanica",
                        "witness_id": "eb1",
                        "file_label": "Duroiselle - Epigraphica Birmanica Talaing Plaques on Ananda Plates.pdf",
                        "verified_witness_type": "source_edition",
                        "content_profile_status": "confirmed",
                        "title_page_status": "confirmed",
                        "contents_status": "confirmed",
                        "sample_entry_status": "confirmed",
                        "translation_status": "confirmed",
                        "edition_status": "confirmed",
                        "notes_commentary_status": "possible",
                        "plate_image_status": "confirmed",
                        "catalogue_metadata_status": "unknown",
                        "coverage_scope": "Talaing fascicle",
                        "confidence": "high",
                        "next_action": "Inspect further.",
                        "notes": "",
                    }
                ],
                eb_fascicle_content_inspection_rows=[
                    {
                        "witness_id": "eb1",
                        "file_label": "Duroiselle - Epigraphica Birmanica Talaing Plaques on Ananda Plates.pdf",
                        "inspection_area": "sample_entry",
                        "short_snippet": "He converses with the king and they have a long conversation.",
                        "contains_translation": "confirmed",
                        "contains_edition_or_transliteration": "possible",
                        "contains_notes_or_commentary": "possible",
                        "contains_plate_or_image": "confirmed",
                        "confidence": "medium",
                        "inspection_status": "confirmed",
                        "next_action": "Inspect more.",
                        "notes": "English prose appears on the sampled page.",
                    }
                ],
            )

            errors = self._run_validation(tmp)

            self.assertTrue(any("translation confirmed content profiles require explicit snippet evidence" in error for error in errors))

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
            "verified_direct_witness_count": "0",
            "verified_translation_witness_count": "0",
            "verified_edition_witness_count": "0",
            "verified_plate_witness_count": "0",
            "weak_false_positive_count": "0",
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

    def _verification_row(self, **overrides: str) -> dict:
        row = {
            "witness_id": "w1",
            "source_work_key": "lucePeMaungTinInscriptionsOfBurma",
            "canonical_title": "Inscriptions of Burma",
            "candidate_file_label": "Inscriptions of Burma.pdf",
            "current_witness_type": "source_edition",
            "verified_witness_type": "source_edition",
            "verification_status": "verified_direct_witness",
            "directness": "direct_source",
            "contains_translation_verified": "unknown",
            "contains_edition_verified": "confirmed",
            "contains_plate_or_image_verified": "unknown",
            "contains_catalogue_metadata_verified": "unknown",
            "contains_secondary_discussion_verified": "unknown",
            "title_page_evidence": "Inscriptions of Burma",
            "toc_evidence": "",
            "ocr_or_text_snippet": "",
            "evidence_quality": "strong",
            "confidence": "high",
            "recommended_action": "Use verified direct witness.",
            "notes": "",
        }
        row.update(overrides)
        return row

    def _gap_row(self, **overrides: str) -> dict:
        row = {field: "" for field in SOURCE_WORK_GAP_FIELDS}
        row.update(
            {
                "source_work_key": "uemSelectionsPagan",
                "canonical_title": "Selections from the Inscriptions of Pagan",
                "source_family_ids": "sf-uem",
                "gap_type": "needs_direct_witness",
                "current_status": "needs_direct_witness",
                "recommended_next_action": "Continue targeted local/direct-witness search.",
                "notes": "",
            }
        )
        row.update(overrides)
        return row

    def _acquisition_plan_row(self, **overrides: str) -> dict:
        row = {
            "source_work_key": "lucePeMaungTinInscriptionsOfBurma",
            "canonical_title": "Inscriptions of Burma",
            "source_family_or_acronym": "IOB",
            "target_witness_needed": "Companion text volume for Inscriptions of Burma",
            "known_or_expected_author_editor": "G. H. Luce and U Pe Maung Tin",
            "known_or_expected_year": "",
            "known_or_expected_publisher_or_series": "",
            "known_variant_titles": "Inscriptions of Burma",
            "local_search_status": "verified_plate_witness_only",
            "local_candidates_ruled_out": "",
            "bibliographic_clues": "",
            "likely_external_catalogues_or_repositories": "WorldCat",
            "priority": "high",
            "recommended_next_action": "Search external catalogues for a direct witness.",
            "notes": "",
        }
        row.update(overrides)
        return row

    def _acquisition_status_row(self, **overrides: str) -> dict:
        row = {
            "source_work_key": "lucePeMaungTinInscriptionsOfBurma",
            "canonical_title": "Inscriptions of Burma",
            "local_direct_witness_status": "local_plate_witness_only",
            "external_catalogue_status": "authoritative_catalogue_record_found",
            "acquisition_status": "needs_local_copy_or_scan",
            "translation_coverage_status": "unconfirmed",
            "edition_or_text_status": "Verified plate portfolios only; companion text witness not yet acquired",
            "current_blocker": "Authoritative catalogue lead exists, but no local companion text witness has been acquired",
            "next_action": "Use the Berkeley catalogue lead to locate a local copy, legally usable scan, or holding location for the companion text volume.",
            "priority": "high",
            "notes": "Do not conflate this with the verified plate portfolios.",
        }
        row.update(overrides)
        return row

    def _acquisition_action_queue_row(self, **overrides: str) -> dict:
        row = {
            "action_id": "iob-berkeley-acquire-local-copy",
            "source_work_key": "lucePeMaungTinInscriptionsOfBurma",
            "action_type": "acquire_local_copy_or_scan",
            "target_record_or_work": "UC Berkeley Library record for Inscriptions of Burma",
            "authority_evidence": "https://digicoll.lib.berkeley.edu/record/289404; Type: Text; issued in portfolio.",
            "what_to_do_next": "Use the Berkeley catalogue lead to locate a local copy, legally usable scan, or holding location for the companion text volume.",
            "success_condition": "A local text witness is acquired or a legally usable scan/location is identified.",
            "blocked_by": "Authoritative catalogue lead exists, but no local companion text witness has been acquired",
            "priority": "high",
            "notes": "Do not conflate this acquisition target with the already verified plate portfolios.",
        }
        row.update(overrides)
        return row

    def _human_acquisition_checklist_row(self, **overrides: str) -> dict:
        row = {
            "checklist_id": "iob-berkeley-local-copy",
            "source_work_key": "lucePeMaungTinInscriptionsOfBurma",
            "task_type": "acquire_local_copy_or_scan",
            "task": "Use the Berkeley record to locate or acquire a local companion text witness, or identify a legally usable scan/location.",
            "evidence_to_use": "UC Berkeley Library record for Inscriptions of Burma; Type: Text; issued in portfolio.",
            "success_condition": "A local text witness is acquired or a legally usable scan/location is identified.",
            "failure_condition": "Only plate portfolios or catalogue metadata are available; do not promote the Berkeley record to a verified local text witness.",
            "priority": "high",
            "notes": "Keep the Berkeley catalogue lead separate from the already verified plate portfolios.",
        }
        row.update(overrides)
        return row

    def _manual_review_queue_row(self, **overrides: str) -> dict:
        row = {
            "review_id": "fixture-review",
            "source_work_key": "lucePeMaungTinInscriptionsOfBurma",
            "review_type": "external_acquisition",
            "target_file_or_work": "Inscriptions of Burma",
            "reason_for_review": "Need a direct witness or authoritative catalogue record.",
            "evidence_available": "",
            "what_to_check": "Search external catalogues.",
            "expected_outcome": "Acquire a direct witness or catalogue record.",
            "priority": "high",
            "notes": "",
        }
        row.update(overrides)
        return row

    def _ruled_out_candidate_row(self, **overrides: str) -> dict:
        row = {
            "source_work_key": "lucePeMaungTinInscriptionsOfBurma",
            "candidate_label": "111029.pdf",
            "candidate_id": "111029.pdf",
            "evidence_sources": "rescue_candidate_review",
            "ruled_out_category": "secondary_article",
            "reason_ruled_out": "Reviewed as a secondary article.",
            "recommended_guardrail": "Do not promote as a direct witness.",
            "related_queries_or_context": "fixture",
            "notes": "",
        }
        row.update(overrides)
        return row

    def _external_catalogue_search_log_row(self, **overrides: str) -> dict:
        row = {
            "catalogue_log_row_id": "iob-berkeley-text-record",
            "source_work_key": "lucePeMaungTinInscriptionsOfBurma",
            "search_target": "IOB companion text volume",
            "catalogue_or_repository": "UC Berkeley Library",
            "query": "\"Inscriptions of Burma\" text",
            "query_type": "title-author-text-volume",
            "result_status": "exact_catalogue_match",
            "candidate_title": "Inscriptions of Burma.",
            "candidate_author_editor": "G. H. Luce; Pe Maung Tin",
            "candidate_year": "1934-",
            "candidate_publisher_or_series": "Oxford University Press, H. Milford",
            "candidate_url_or_identifier": "https://digicoll.lib.berkeley.edu/record/289404",
            "evidence_snippet": "Type: Text; issued in portfolio.",
            "match_assessment": "authoritative_catalogue_record",
            "next_action": "Use the catalogue record as an acquisition lead.",
            "notes": "",
        }
        row.update(overrides)
        return row

    def _external_catalogue_candidate_triage_row(self, **overrides: str) -> dict:
        row = {
            "source_work_key": "lucePeMaungTinInscriptionsOfBurma",
            "catalogue_log_row_id_or_query": "iob-berkeley-text-record",
            "candidate_title": "Inscriptions of Burma.",
            "candidate_author_editor": "G. H. Luce; Pe Maung Tin",
            "candidate_year": "1934-",
            "catalogue_or_repository": "UC Berkeley Library",
            "triage_status": "authoritative_catalogue_record",
            "triage_reason": "Catalogue metadata clearly identifies the companion text volume.",
            "is_direct_witness_candidate": "false",
            "is_authoritative_record": "true",
            "is_cross_source_or_secondary": "false",
            "recommended_action": "Use the catalogue record as an acquisition lead.",
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
        verification_rows: list[dict] | None = None,
        snippet_rows: list[dict] | None = None,
        missing_search_rows: list[dict] | None = None,
        gap_rows: list[dict] | None = None,
        sip_inspection_rows: list[dict] | None = None,
        source_witness_content_profile_rows: list[dict] | None = None,
        eb_fascicle_content_inspection_rows: list[dict] | None = None,
        uem_search_rows: list[dict] | None = None,
        core_search_rows: list[dict] | None = None,
        iob_text_search_rows: list[dict] | None = None,
        iob_text_volume_hunt_rows: list[dict] | None = None,
        missing_core_witness_hunt_rows: list[dict] | None = None,
        witness_hunt_candidate_triage_rows: list[dict] | None = None,
        direct_witness_acquisition_plan_rows: list[dict] | None = None,
        direct_witness_acquisition_status_rows: list[dict] | None = None,
        manual_review_queue_rows: list[dict] | None = None,
        acquisition_action_queue_rows: list[dict] | None = None,
        human_acquisition_checklist_rows: list[dict] | None = None,
        ruled_out_witness_candidate_rows: list[dict] | None = None,
        external_catalogue_search_log_rows: list[dict] | None = None,
        external_catalogue_candidate_triage_rows: list[dict] | None = None,
        rescue_review_rows: list[dict] | None = None,
        epigraphia_review_rows: list[dict] | None = None,
        epigraphia_fascicle_coverage_rows: list[dict] | None = None,
        phase_summary_text: str | None = None,
        report_overrides: dict | None = None,
    ) -> None:
        source_rows = source_rows or [base_source_row()]
        plan_rows = plan_rows or [self._plan_row()]
        candidate_rows = candidate_rows or []
        classification_rows = classification_rows or []
        verification_rows = verification_rows or []
        snippet_rows = snippet_rows or []
        missing_search_rows = missing_search_rows or []
        gap_rows = gap_rows or []
        sip_inspection_rows = sip_inspection_rows or []
        source_witness_content_profile_rows = source_witness_content_profile_rows or [
            {
                "source_work_key": "lucePeMaungTinInscriptionsOfBurma",
                "witness_id": "w1",
                "file_label": "Inscriptions of Burma.pdf",
                "verified_witness_type": "source_edition",
                "content_profile_status": "confirmed",
                "title_page_status": "confirmed",
                "contents_status": "unknown",
                "sample_entry_status": "unknown",
                "translation_status": "unknown",
                "edition_status": "confirmed",
                "notes_commentary_status": "unknown",
                "plate_image_status": "unknown",
                "catalogue_metadata_status": "unknown",
                "coverage_scope": "whole_work",
                "confidence": "high",
                "next_action": "Continue targeted inspection.",
                "notes": "",
            }
        ]
        eb_fascicle_content_inspection_rows = eb_fascicle_content_inspection_rows or [
            {
                "witness_id": "eb-fixture",
                "file_label": "Epigraphia Birmanica fixture.pdf",
                "inspection_area": "title_page",
                "short_snippet": "Epigraphia Birmanica",
                "contains_translation": "unknown",
                "contains_edition_or_transliteration": "confirmed",
                "contains_notes_or_commentary": "unknown",
                "contains_plate_or_image": "unknown",
                "confidence": "medium",
                "inspection_status": "confirmed",
                "next_action": "Inspect contents.",
                "notes": "",
            }
        ]
        uem_search_rows = uem_search_rows or []
        core_search_rows = core_search_rows or []
        iob_text_search_rows = iob_text_search_rows or []
        iob_text_volume_hunt_rows = iob_text_volume_hunt_rows or [
            {
                "query": "Inscriptions of Burma text",
                "matched_file_label": "",
                "matched_file_id": "",
                "match_type": "",
                "match_confidence": "",
                "short_evidence": "Checked local file manifest and OCR index; no text volume surfaced.",
                "searched_sources": "local_file_manifest;source_library_manifest;ocr_text_index",
                "search_scope": "local manifest plus OCR index",
                "search_date_or_run_id": "fixture",
                "search_result_status": "not_found",
                "recommended_action": "Continue targeted portfolio/text hunt.",
                "notes": "",
                "is_text_witness_candidate": "false",
                "is_plate_witness_candidate": "false",
                "false_positive_for_text": "false",
                "reason_not_text_witness": "",
            }
        ]
        missing_core_witness_hunt_rows = missing_core_witness_hunt_rows or [
            {
                "source_work_key": source_work_key,
                "query": query,
                "variant_type": variant_type,
                "matched_file_label": "",
                "matched_file_id": "",
                "match_type": "not_found",
                "match_confidence": "low",
                "short_evidence": "",
                "searched_sources": "local_file_manifest;source_library_manifest;ocr_text_index;raw_reference_to_bibtex",
                "search_scope": "targeted author/title/abbreviation search across local manifests, source-library paths, author-folder path hints, OCR index, and bibliography crosswalk",
                "search_date_or_run_id": "fixture",
                "search_result_status": "not_found",
                "is_known_false_positive": "false",
                "false_positive_reason": "",
                "recommended_action": "Continue targeted local/direct-witness search.",
                "notes": "Checked local manifest and OCR index.",
            }
            for source_work_key, query_rows in MISSING_CORE_WITNESS_HUNT_QUERIES.items()
            for query, variant_type in query_rows
        ]
        witness_hunt_candidate_triage_rows = witness_hunt_candidate_triage_rows or []
        rescue_review_rows = rescue_review_rows or [
            {
                "candidate_file_id": "111029.pdf",
                "candidate_file_label": "111029.pdf",
                "matched_query": "Luce Pe Maung Tin Selections",
                "possible_source_work_keys": "sipSelectionsPagan;uemSelectionsPagan",
                "title_page_snippet": "ChroniclleTagaung_PeMaungTinLuce1921.pdf",
                "contents_snippet": "",
                "classification": "secondary_article",
                "confidence": "high",
                "recommended_mapping": "Do not promote as a direct witness.",
                "notes": "",
            },
            {
                "candidate_file_id": "taw-sein-ko",
                "candidate_file_label": "Taw Sein Ko 1899 Inscriptions of Pagan.pdf",
                "matched_query": "Taw Sein Ko 1899 Inscriptions of Pagan",
                "possible_source_work_keys": "tnInscriptionsPaganPinyaAva;ppaCatalogue;epigraphiaBirmanica",
                "title_page_snippet": "Inscriptions of Pagan",
                "contents_snippet": "",
                "classification": "needs_title_page_review",
                "confidence": "medium",
                "recommended_mapping": "Review title page before mapping.",
                "notes": "",
            },
        ]
        if direct_witness_acquisition_plan_rows is None:
            direct_witness_acquisition_plan_rows = []
            source_by_key = {row["source_work_key"]: row for row in source_rows}
            for row in gap_rows:
                source_key = row.get("source_work_key", "")
                if source_key in source_by_key and row.get("gap_type") in OPEN_DIRECT_WITNESS_GAP_TYPES:
                    direct_witness_acquisition_plan_rows.append(
                        self._acquisition_plan_row(
                            source_work_key=source_key,
                            canonical_title=row.get("canonical_title", source_by_key[source_key].get("canonical_title", "")),
                            source_family_or_acronym=source_by_key[source_key].get("short_title", ""),
                            known_or_expected_author_editor=source_by_key[source_key].get("authors_editors", ""),
                            known_or_expected_year="1958" if source_key == "uemSelectionsPagan" else "1897" if source_key == "tnInscriptionsPaganPinyaAva" else "unknown" if source_key in {"ppaCatalogue", "ubSourceFamily"} else "1933-1956" if source_key == "lucePeMaungTinInscriptionsOfBurma" else "",
                            known_or_expected_publisher_or_series="Government Printing, Burma" if source_key == "tnInscriptionsPaganPinyaAva" else "Archaeological Survey of Burma" if source_key in {"ppaCatalogue", "ubSourceFamily"} else "Oxford University Press, H. Milford" if source_key == "lucePeMaungTinInscriptionsOfBurma" else "unknown" if source_key == "uemSelectionsPagan" else "",
                            recommended_next_action=row.get("next_action", "Search external catalogues."),
                            notes=row.get("notes", ""),
                        )
                    )
            for source_key in {"sipSelectionsPagan", "epigraphiaBirmanica"}:
                if source_key in source_by_key:
                    direct_witness_acquisition_plan_rows.append(
                        self._acquisition_plan_row(
                            source_work_key=source_key,
                            canonical_title=source_by_key[source_key].get("canonical_title", ""),
                            source_family_or_acronym=source_by_key[source_key].get("short_title", ""),
                            known_or_expected_author_editor=source_by_key[source_key].get("authors_editors", ""),
                            local_search_status="verified_direct_witness_translation_unconfirmed",
                            priority="medium",
                            target_witness_needed="Manual review of verified local witness content",
                            recommended_next_action="Review the verified local witness without inferring translation from generic English prose.",
                        )
                    )
        if direct_witness_acquisition_status_rows is None:
            direct_witness_acquisition_status_rows = []
            source_by_key = {row["source_work_key"]: row for row in source_rows}
            for row in direct_witness_acquisition_plan_rows:
                source_key = row.get("source_work_key", "")
                canonical_title = row.get("canonical_title", "")
                short_title = source_by_key.get(source_key, {}).get("short_title", "")
                if source_key == "lucePeMaungTinInscriptionsOfBurma":
                    direct_witness_acquisition_status_rows.append(
                        self._acquisition_status_row(
                            source_work_key=source_key,
                            canonical_title=canonical_title,
                        )
                    )
                elif source_key in {"sipSelectionsPagan", "epigraphiaBirmanica"}:
                    direct_witness_acquisition_status_rows.append(
                        self._acquisition_status_row(
                            source_work_key=source_key,
                            canonical_title=canonical_title,
                            local_direct_witness_status="local_direct_witness_needs_content_review",
                            external_catalogue_status="not_needed_for_current_step",
                            acquisition_status="needs_manual_content_review",
                            translation_coverage_status="needs_manual_review",
                            edition_or_text_status="Verified local witness; translation review pending",
                            current_blocker="Local witness is present, but explicit translation evidence has not been confirmed",
                            next_action="Review the verified local witness without inferring translation from generic English prose.",
                            priority="medium",
                            notes=short_title,
                        )
                    )
                else:
                    direct_witness_acquisition_status_rows.append(
                        self._acquisition_status_row(
                            source_work_key=source_key,
                            canonical_title=canonical_title,
                            local_direct_witness_status="no_local_direct_witness",
                            external_catalogue_status="no_external_match_found",
                            acquisition_status="needs_authoritative_catalogue_record",
                            translation_coverage_status="unconfirmed",
                            edition_or_text_status="No verified local edition/text witness",
                            current_blocker="Authoritative catalogue record still needed",
                            next_action=row.get("recommended_next_action", ""),
                            priority=row.get("priority", "high"),
                            notes=short_title,
                        )
                    )
        if manual_review_queue_rows is None:
            manual_review_queue_rows = []
            for row in source_witness_content_profile_rows:
                source_key = row.get("source_work_key", "")
                if source_key in {"sipSelectionsPagan", "epigraphiaBirmanica"} and row.get("translation_status") != "confirmed":
                    manual_review_queue_rows.append(
                        self._manual_review_queue_row(
                            review_id=f"{source_key}-{row.get('file_label', 'review')}",
                            source_work_key=source_key,
                            review_type="content_review",
                            target_file_or_work=row.get("file_label", ""),
                            priority="medium",
                        )
                    )
                if source_key == "lucePeMaungTinInscriptionsOfBurma" and row.get("plate_image_status") == "confirmed":
                    manual_review_queue_rows.append(
                        self._manual_review_queue_row(
                            review_id=f"{row.get('file_label', 'iob')}-plate-guardrail",
                            source_work_key=source_key,
                            review_type="plate_guardrail",
                            target_file_or_work=row.get("file_label", ""),
                            priority="low",
                            reason_for_review="Keep verified plate witnesses out of the text-volume gap closure.",
                            expected_outcome="Retain as a plate witness only.",
                        )
                    )
            for row in gap_rows:
                if row.get("gap_type") in OPEN_DIRECT_WITNESS_GAP_TYPES:
                    manual_review_queue_rows.append(
                        self._manual_review_queue_row(
                            review_id=f"{row.get('source_work_key', '')}-external-acquisition",
                            source_work_key=row.get("source_work_key", ""),
                            review_type="external_acquisition",
                            target_file_or_work=row.get("canonical_title", ""),
                            evidence_available=row.get("notes", ""),
                            notes=row.get("next_action", ""),
                        )
                    )
                elif row.get("gap_type") in ACQUISITION_REVIEW_GAP_TYPES:
                    manual_review_queue_rows.append(
                        self._manual_review_queue_row(
                            review_id=f"{row.get('source_work_key', '')}-external-acquisition",
                            source_work_key=row.get("source_work_key", ""),
                            review_type="external_acquisition",
                            target_file_or_work=row.get("canonical_title", ""),
                            evidence_available=row.get("notes", ""),
                            notes=row.get("next_action", ""),
                        )
                    )
        if acquisition_action_queue_rows is None:
            acquisition_action_queue_rows = []
            for row in direct_witness_acquisition_status_rows:
                source_key = row.get("source_work_key", "")
                if source_key not in DIRECT_WITNESS_ACQUISITION_SOURCE_KEYS:
                    continue
                if row.get("acquisition_status") == "needs_local_copy_or_scan":
                    acquisition_action_queue_rows.append(self._acquisition_action_queue_row())
                elif row.get("acquisition_status") == "needs_authoritative_catalogue_record":
                    acquisition_action_queue_rows.append(
                        self._acquisition_action_queue_row(
                            action_id=f"{source_key}-locate-authoritative-record",
                            source_work_key=source_key,
                            action_type="locate_authoritative_catalogue_record",
                            target_record_or_work=row.get("canonical_title", ""),
                            authority_evidence=row.get("current_blocker", ""),
                            what_to_do_next=row.get("next_action", ""),
                            success_condition="A catalogue record names the expected source work clearly enough to distinguish it from known false positives or cross-source records.",
                            blocked_by=row.get("current_blocker", ""),
                            priority=row.get("priority", "high"),
                            notes="",
                        )
                    )
        if human_acquisition_checklist_rows is None:
            human_acquisition_checklist_rows = []
            for row in direct_witness_acquisition_status_rows:
                source_key = row.get("source_work_key", "")
                if source_key == "lucePeMaungTinInscriptionsOfBurma":
                    human_acquisition_checklist_rows.append(self._human_acquisition_checklist_row())
                elif source_key == "sipSelectionsPagan":
                    human_acquisition_checklist_rows.append(
                        self._human_acquisition_checklist_row(
                            checklist_id="sip-manual-content-review",
                            source_work_key=source_key,
                            task_type="manual_content_review",
                            task="Inspect a recoverable SIP sample entry or contents page and keep translation status unconfirmed unless explicit translation evidence appears.",
                            evidence_to_use="Local witness is present, but translation-bearing content remains unreviewed.",
                            success_condition="A sample entry or contents page is reviewed and the translation status stays evidence-based.",
                            failure_condition="No explicit translation heading appears, so SIP remains a verified edition witness with translation unconfirmed.",
                            priority="medium",
                            notes="The reviewed SIP/UEM false positive must not be recycled as UEM evidence.",
                        )
                    )
                elif source_key == "epigraphiaBirmanica":
                    human_acquisition_checklist_rows.append(
                        self._human_acquisition_checklist_row(
                            checklist_id="eb-manual-content-review",
                            source_work_key=source_key,
                            task_type="manual_content_review",
                            task="Inspect explicit translation headings or sections in the verified Epigraphia Birmanica fascicles.",
                            evidence_to_use="Local fascicles are verified, but explicit translation evidence has not been confirmed.",
                            success_condition="Explicit translation-bearing sections are confirmed or ruled out from the verified fascicles.",
                            failure_condition="Only captions or generic English prose appear, so translation coverage remains unconfirmed.",
                            priority="medium",
                            notes="EB is a content-review problem, not a direct-witness acquisition problem.",
                        )
                    )
                elif source_key == "tnInscriptionsPaganPinyaAva":
                    human_acquisition_checklist_rows.append(
                        self._human_acquisition_checklist_row(
                            checklist_id="tn-source-identity-resolution",
                            source_work_key=source_key,
                            task_type="resolve_source_identity",
                            task="Resolve whether the U Tun Nyein 1897 target is genuinely distinct from the Forchhammer/Taw Sein Ko 1899 record.",
                            evidence_to_use=row.get("current_blocker", ""),
                            success_condition="Catalogue metadata distinguishes a U Tun Nyein / 1897 witness or confirms the identity relationship explicitly.",
                            failure_condition="Only ambiguous Gazette Press / Government Printing clues remain, so the gap stays open.",
                            priority="high",
                            notes="",
                        )
                    )
                elif source_key == "ppaCatalogue":
                    human_acquisition_checklist_rows.append(
                        self._human_acquisition_checklist_row(
                            checklist_id="ppa-source-identity-resolution",
                            source_work_key=source_key,
                            task_type="resolve_source_identity",
                            task="Resolve whether PPA/IPPA is a separate catalogue family or a shorthand for the 1899 Inscriptions of Pagan, Pinya and Ava record.",
                            evidence_to_use=row.get("current_blocker", ""),
                            success_condition="A catalogue record names PPA/IPPA clearly enough to confirm whether it is separate or an alias.",
                            failure_condition="Only overlapping title-family clues remain, so the gap stays open.",
                            priority="high",
                            notes="",
                        )
                    )
                else:
                    human_acquisition_checklist_rows.append(
                        self._human_acquisition_checklist_row(
                            checklist_id=f"{source_key}-catalogue-search",
                            source_work_key=source_key,
                            task_type="locate_authoritative_catalogue_record",
                            task="Use targeted catalogue/source-identity searches to distinguish the expected direct witness from known false positives and cross-source records.",
                            evidence_to_use=row.get("current_blocker", ""),
                            success_condition="A catalogue record or title-page witness identifies the target source work clearly enough for acquisition planning.",
                            failure_condition="Only ambiguous or cross-source hits remain, so the direct-witness gap stays open.",
                            priority=row.get("priority", "high"),
                            notes="",
                        )
                    )
        if ruled_out_witness_candidate_rows is None:
            ruled_out_witness_candidate_rows = []
            for row in witness_hunt_candidate_triage_rows:
                if row.get("triage_status") in {"known_false_positive", "cross_source_witness", "secondary_or_unrelated", "too_broad_query_noise"}:
                    ruled_out_witness_candidate_rows.append(
                        self._ruled_out_candidate_row(
                            source_work_key=row.get("source_work_key", ""),
                            candidate_label=row.get("matched_file_label", ""),
                            candidate_id=row.get("matched_file_id", ""),
                            evidence_sources=f"{row.get('hunt_table', '')};witness_hunt_candidate_triage",
                            ruled_out_category=row.get("triage_status", ""),
                            reason_ruled_out=row.get("triage_reason", ""),
                            recommended_guardrail=row.get("recommended_action", ""),
                            related_queries_or_context=row.get("query", ""),
                            notes=row.get("notes", ""),
                        )
                    )
        if external_catalogue_search_log_rows is None:
            external_catalogue_search_log_rows = []
            for row in direct_witness_acquisition_plan_rows:
                source_key = row.get("source_work_key", "")
                if source_key not in DIRECT_WITNESS_ACQUISITION_SOURCE_KEYS:
                    continue
                if source_key == "lucePeMaungTinInscriptionsOfBurma":
                    external_catalogue_search_log_rows.append(self._external_catalogue_search_log_row())
                else:
                    external_catalogue_search_log_rows.append(
                        self._external_catalogue_search_log_row(
                            catalogue_log_row_id=f"{source_key}-no-match",
                            source_work_key=source_key,
                            search_target=row.get("canonical_title", ""),
                            catalogue_or_repository="WorldCat",
                            query=row.get("canonical_title", ""),
                            query_type="title-search",
                            result_status="no_match",
                            candidate_title="",
                            candidate_author_editor="",
                            candidate_year="",
                            candidate_publisher_or_series="",
                            candidate_url_or_identifier="",
                            evidence_snippet="No precise external catalogue record surfaced in the fixture search log.",
                            match_assessment="",
                            next_action="Continue targeted catalogue searching.",
                        )
                    )
        if external_catalogue_candidate_triage_rows is None:
            external_catalogue_candidate_triage_rows = []
            for row in external_catalogue_search_log_rows:
                if row.get("result_status") in {"no_match", "blocked_or_unavailable"} and not row.get("candidate_title"):
                    continue
                if row.get("match_assessment") == "authoritative_catalogue_record":
                    external_catalogue_candidate_triage_rows.append(self._external_catalogue_candidate_triage_row())
                else:
                    external_catalogue_candidate_triage_rows.append(
                        self._external_catalogue_candidate_triage_row(
                            source_work_key=row.get("source_work_key", ""),
                            catalogue_log_row_id_or_query=row.get("catalogue_log_row_id", "") or row.get("query", ""),
                            candidate_title=row.get("candidate_title", ""),
                            candidate_author_editor=row.get("candidate_author_editor", ""),
                            candidate_year=row.get("candidate_year", ""),
                            catalogue_or_repository=row.get("catalogue_or_repository", ""),
                            triage_status="needs_human_review" if row.get("result_status") != "bibliographic_clue_only" else "bibliographic_clue_only",
                            triage_reason="Fixture catalogue hit remains ambiguous." if row.get("result_status") != "bibliographic_clue_only" else "Fixture clue does not yet identify a standalone record.",
                            is_direct_witness_candidate="false",
                            is_authoritative_record="false",
                            is_cross_source_or_secondary="false",
                            recommended_action=row.get("next_action", ""),
                        )
                    )
            for row in rescue_review_rows:
                if row.get("classification") == "secondary_article":
                    ruled_out_witness_candidate_rows.append(
                        self._ruled_out_candidate_row(
                            source_work_key=row.get("possible_source_work_keys", ""),
                            candidate_label=row.get("candidate_file_label", ""),
                            candidate_id=row.get("candidate_file_id", ""),
                            evidence_sources="rescue_candidate_review",
                            ruled_out_category=row.get("classification", ""),
                            reason_ruled_out=row.get("notes", "") or "Reviewed as a secondary article.",
                            recommended_guardrail=row.get("recommended_mapping", ""),
                            related_queries_or_context=row.get("matched_query", ""),
                        )
                    )
            for row in verification_rows:
                if row.get("verification_status") == "weak_false_positive":
                    ruled_out_witness_candidate_rows.append(
                        self._ruled_out_candidate_row(
                            source_work_key=row.get("source_work_key", ""),
                            candidate_label=row.get("candidate_file_label", ""),
                            candidate_id=row.get("witness_id", ""),
                            evidence_sources="witness_verification",
                            ruled_out_category="weak_false_positive",
                            reason_ruled_out=row.get("notes", "") or "Reviewed weak false positive.",
                            recommended_guardrail=row.get("recommended_action", ""),
                            related_queries_or_context=row.get("candidate_file_label", ""),
                        )
                    )
            for row in iob_text_search_rows + iob_text_volume_hunt_rows:
                if row.get("false_positive_for_text") == "true":
                    ruled_out_witness_candidate_rows.append(
                        self._ruled_out_candidate_row(
                            source_work_key=row.get("source_work_key", "lucePeMaungTinInscriptionsOfBurma"),
                            candidate_label=row.get("matched_file_label", ""),
                            candidate_id=row.get("matched_file_id", ""),
                            evidence_sources="inscriptions_of_burma_text_false_positive",
                            ruled_out_category="known_false_positive",
                            reason_ruled_out=row.get("reason_not_text_witness", ""),
                            recommended_guardrail=row.get("recommended_action", ""),
                            related_queries_or_context=row.get("query", ""),
                            notes=row.get("notes", ""),
                        )
                    )
        epigraphia_review_rows = epigraphia_review_rows or [
            {
                "witness_id": "epigraphiaBirmanica--011041",
                "file_label": "011041.pdf",
                "source_work_key": "epigraphiaBirmanica",
                "probable_volume_or_fascicle": "",
                "title_page_snippet": "ElementaryLahooAkaWa_Antisdel-1911.pdf",
                "contents_snippet": "",
                "contains_translation": "false",
                "contains_edition_or_transliteration": "false",
                "contains_plate_or_image": "false",
                "classification": "unrelated_numbered_pdf",
                "confidence": "medium",
                "next_action": "Keep out unless a title page proves otherwise.",
                "notes": "",
            }
        ]
        epigraphia_fascicle_coverage_rows = epigraphia_fascicle_coverage_rows or []
        phase_summary_text = phase_summary_text or (
            "# Translation source discovery phase summary\n\n"
            "## Current overall state\n"
            "- Broad fuzzy hunts yielded zero plausible direct candidates.\n\n"
            "## Verified local witnesses\n"
            "- SIP remains a verified local edition witness with translation unconfirmed.\n"
            "- EB remains a verified local fascicle witness with translation unconfirmed.\n\n"
            "## Verified plate-only witnesses\n"
            "- IOB plate portfolios remain verified plate witnesses only.\n\n"
            "## What must not be promoted automatically\n"
            "- The Berkeley IOB catalogue record is not a verified local witness.\n"
            "- Verified IOB plate portfolios do not satisfy the missing text witness.\n"
            "- The SIP/UEM false positive remains ruled out as a false positive.\n"
        )
        write_tsv(root / "source_work_authority.tsv", source_rows, SOURCE_WORK_FIELDS)
        write_tsv(root / "translation_source_discovery_plan.tsv", plan_rows, PLAN_FIELDS)
        write_tsv(root / "witness_candidates.tsv", candidate_rows, WITNESS_CANDIDATE_FIELDS)
        write_tsv(root / "witness_classification.tsv", classification_rows, WITNESS_CLASSIFICATION_FIELDS)
        write_tsv(root / "witness_verification.tsv", verification_rows, VERIFICATION_FIELDS)
        write_tsv(root / "witness_titlepage_toc_snippets.tsv", snippet_rows, SNIPPET_FIELDS)
        write_tsv(root / "missing_direct_witness_search.tsv", missing_search_rows, MISSING_DIRECT_SEARCH_FIELDS)
        write_tsv(root / "source_work_witness_gaps.tsv", gap_rows, SOURCE_WORK_GAP_FIELDS)
        write_tsv(root / "sip_witness_inspection.tsv", sip_inspection_rows, SIP_WITNESS_INSPECTION_FIELDS)
        write_tsv(root / "source_witness_content_profile.tsv", source_witness_content_profile_rows, SOURCE_WITNESS_CONTENT_PROFILE_FIELDS)
        write_tsv(root / "eb_fascicle_content_inspection.tsv", eb_fascicle_content_inspection_rows, EB_FASCICLE_CONTENT_INSPECTION_FIELDS)
        write_tsv(root / "uem_direct_witness_search.tsv", uem_search_rows, DIRECT_WITNESS_SEARCH_FIELDS)
        write_tsv(root / "core_source_direct_witness_search.tsv", core_search_rows, CORE_DIRECT_WITNESS_SEARCH_FIELDS)
        write_tsv(root / "inscriptions_of_burma_text_witness_search.tsv", iob_text_search_rows, INSCRIPTIONS_OF_BURMA_TEXT_SEARCH_FIELDS)
        write_tsv(root / "inscriptions_of_burma_text_volume_hunt.tsv", iob_text_volume_hunt_rows, INSCRIPTIONS_OF_BURMA_TEXT_VOLUME_HUNT_FIELDS)
        write_tsv(root / "missing_core_witness_hunt.tsv", missing_core_witness_hunt_rows, MISSING_CORE_WITNESS_HUNT_FIELDS)
        write_tsv(root / "witness_hunt_candidate_triage.tsv", witness_hunt_candidate_triage_rows, WITNESS_HUNT_CANDIDATE_TRIAGE_FIELDS)
        write_tsv(root / "direct_witness_acquisition_plan.tsv", direct_witness_acquisition_plan_rows, DIRECT_WITNESS_ACQUISITION_PLAN_FIELDS)
        write_tsv(root / "direct_witness_acquisition_status.tsv", direct_witness_acquisition_status_rows, DIRECT_WITNESS_ACQUISITION_STATUS_FIELDS)
        write_tsv(root / "manual_review_queue.tsv", manual_review_queue_rows, MANUAL_REVIEW_QUEUE_FIELDS)
        write_tsv(root / "acquisition_action_queue.tsv", acquisition_action_queue_rows, ACQUISITION_ACTION_QUEUE_FIELDS)
        write_tsv(root / "human_acquisition_checklist.tsv", human_acquisition_checklist_rows, HUMAN_ACQUISITION_CHECKLIST_FIELDS)
        write_tsv(root / "ruled_out_witness_candidates.tsv", ruled_out_witness_candidate_rows, RULED_OUT_WITNESS_CANDIDATE_FIELDS)
        write_tsv(root / "external_catalogue_search_log.tsv", external_catalogue_search_log_rows, EXTERNAL_CATALOGUE_SEARCH_LOG_FIELDS)
        write_tsv(root / "external_catalogue_candidate_triage.tsv", external_catalogue_candidate_triage_rows, EXTERNAL_CATALOGUE_CANDIDATE_TRIAGE_FIELDS)
        write_tsv(root / "rescue_candidate_review.tsv", rescue_review_rows, RESCUE_CANDIDATE_REVIEW_FIELDS)
        write_tsv(root / "epigraphia_birmanica_witness_review.tsv", epigraphia_review_rows, EPIGRAPHIA_BIRMANICA_REVIEW_FIELDS)
        write_tsv(root / "epigraphia_birmanica_fascicle_coverage.tsv", epigraphia_fascicle_coverage_rows, EPIGRAPHIA_BIRMANICA_FASCICLE_COVERAGE_FIELDS)
        (root / "translation_source_discovery_phase_summary.md").write_text(phase_summary_text, encoding="utf-8")
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
                "article_candidate_count": "0",
                "high_priority_article_count": "0",
                "needs_article_title_normalization": "false",
                "needs_local_file_search": "true",
            }
            for key in [
                "journalBurmaResearchSociety",
                "journalRoyalAsiaticSociety",
                "bulletinBurmaHistoricalCommission",
                "annualReportsArchaeologicalSurveyIndia",
                "epigraphiaBirmanica",
            ]
        ]
        write_tsv(
            root / "periodical_article_discovery_plan.tsv",
            periodical_rows,
            PERIODICAL_ARTICLE_DISCOVERY_FIELDS
            + [
                "article_candidate_count",
                "high_priority_article_count",
                "needs_article_title_normalization",
                "needs_local_file_search",
            ],
        )
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
            "verified_witness_count": len(verification_rows),
            "verified_direct_witness_count": sum(row.get("verification_status") in {"verified_direct_witness", "verified_catalogue_witness"} for row in verification_rows),
            "verified_translation_witness_count": sum(row.get("contains_translation_verified") == "confirmed" for row in verification_rows),
            "verified_edition_witness_count": sum(row.get("contains_edition_verified") == "confirmed" for row in verification_rows),
            "verified_plate_witness_count": sum(row.get("verification_status") == "verified_plate_witness" for row in verification_rows),
            "verified_catalogue_witness_count": sum(row.get("verification_status") == "verified_catalogue_witness" for row in verification_rows),
            "verified_secondary_work_count": sum(row.get("verification_status") == "verified_secondary_work" for row in verification_rows),
            "weak_false_positive_count": sum(row.get("verification_status") == "weak_false_positive" for row in verification_rows),
            "missing_direct_witness_search_count": sum(bool(row.get("matched_file_label")) for row in missing_search_rows),
            "titlepage_toc_snippet_count": len(snippet_rows),
            "source_works_needing_direct_witness_count": sum(row.get("discovery_status") == "needs_direct_witness_search" for row in plan_rows),
            "source_work_witness_gap_count": len(gap_rows),
            "source_works_with_verified_direct_witness": len({row["source_work_key"] for row in verification_rows if row.get("verification_status") in {"verified_direct_witness", "verified_catalogue_witness"}}),
            "source_works_still_needing_direct_witness": sum(row.get("local_direct_witness_status") == "no_local_direct_witness" for row in direct_witness_acquisition_status_rows),
            "sip_inspection_completed": bool(sip_inspection_rows),
            "sip_title_page_inspected": any(row.get("inspection_area") == "title_page" and row.get("inspection_status") == "confirmed" for row in sip_inspection_rows),
            "sip_contents_inspected": any(row.get("inspection_area") == "contents" and row.get("inspection_status") == "confirmed" for row in sip_inspection_rows),
            "sip_sample_entry_ocr_attempted": any(row.get("inspection_area") == "sample_entry" for row in sip_inspection_rows),
            "sip_sample_entry_inspected": any(row.get("inspection_area") == "sample_entry" and row.get("inspection_status") == "confirmed" for row in sip_inspection_rows),
            "sip_translation_status": "confirmed" if any(row.get("witness_id") == SIP_WITNESS_ID and row.get("translation_status") == "confirmed" for row in source_witness_content_profile_rows) else "unconfirmed",
            "sip_edition_status": "confirmed" if any(row.get("witness_id") == SIP_WITNESS_ID and row.get("edition_status") == "confirmed" for row in source_witness_content_profile_rows) else "unconfirmed",
            "sip_needs_sample_entry_review": any(row.get("inspection_area") == "sample_entry" for row in sip_inspection_rows) and not any(row.get("inspection_area") == "sample_entry" and row.get("inspection_status") == "confirmed" for row in sip_inspection_rows),
            "sip_contains_translation_status": "confirmed" if any(row.get("witness_id") == SIP_WITNESS_ID and row.get("translation_status") == "confirmed" for row in source_witness_content_profile_rows) else "unconfirmed",
            "uem_direct_search_count": sum(bool(row.get("matched_file_label")) for row in uem_search_rows),
            "core_source_direct_search_count": sum(bool(row.get("matched_file_label")) for row in core_search_rows),
            "inscriptions_of_burma_text_witness_search_count": len(iob_text_search_rows),
            "inscriptions_of_burma_text_witness_found": sum(row.get("is_text_witness_candidate") == "true" and row.get("search_result_status") == "direct_witness_found" for row in iob_text_search_rows),
            "inscriptions_of_burma_plate_false_positive_count": len({row.get("matched_file_id", "") or row.get("matched_file_label", "") for row in (iob_text_search_rows + iob_text_volume_hunt_rows) if row.get("false_positive_for_text") == "true"}),
            "inscriptions_of_burma_text_volume_hunt_count": len(iob_text_volume_hunt_rows),
            "missing_core_witness_hunt_count": len(missing_core_witness_hunt_rows),
            "witness_hunt_candidate_triage_count": len(witness_hunt_candidate_triage_rows),
            "direct_witness_acquisition_plan_count": len(direct_witness_acquisition_plan_rows),
            "manual_review_queue_count": len(manual_review_queue_rows),
            "ruled_out_witness_candidate_count": len(ruled_out_witness_candidate_rows),
            "external_catalogue_search_log_count": len(external_catalogue_search_log_rows),
            "external_catalogue_candidate_triage_count": len(external_catalogue_candidate_triage_rows),
            "acquisition_status_count": len(direct_witness_acquisition_status_rows),
            "acquisition_action_queue_count": len(acquisition_action_queue_rows),
            "authoritative_catalogue_record_count": sum(row.get("is_authoritative_record") == "true" for row in external_catalogue_candidate_triage_rows),
            "source_works_needing_authoritative_catalogue_record_count": sum(row.get("acquisition_status") == "needs_authoritative_catalogue_record" for row in direct_witness_acquisition_status_rows),
            "source_works_with_authoritative_catalogue_record_needing_local_copy_count": sum(row.get("acquisition_status") == "needs_local_copy_or_scan" for row in direct_witness_acquisition_status_rows),
            "source_works_needing_manual_content_review_count": sum(row.get("acquisition_status") == "needs_manual_content_review" for row in direct_witness_acquisition_status_rows),
            "source_works_with_local_direct_witness_but_translation_unconfirmed_count": sum(row.get("local_direct_witness_status") in {"local_direct_witness_verified", "local_direct_witness_needs_content_review"} and row.get("translation_coverage_status") in {"unconfirmed", "needs_manual_review"} for row in direct_witness_acquisition_status_rows),
            "plausible_direct_candidate_count": sum(row.get("triage_status") in PLAUSIBLE_HUNT_TRIAGE_STATUSES for row in witness_hunt_candidate_triage_rows),
            "known_false_positive_hunt_count": sum(row.get("triage_status") == "known_false_positive" for row in witness_hunt_candidate_triage_rows),
            "cross_source_or_secondary_hunt_count": sum(row.get("triage_status") in {"cross_source_witness", "secondary_or_unrelated", "too_broad_query_noise"} for row in witness_hunt_candidate_triage_rows),
            "rescue_candidate_review_count": len(rescue_review_rows),
            "epigraphia_birmanica_review_count": len(epigraphia_review_rows),
            "eb_verified_fascicle_count": len(epigraphia_fascicle_coverage_rows),
            "eb_fascicle_coverage_count": len(epigraphia_fascicle_coverage_rows),
            "eb_content_profile_count": sum(row.get("source_work_key") == "epigraphiaBirmanica" for row in source_witness_content_profile_rows),
            "eb_translation_confirmed_count": sum(row.get("source_work_key") == "epigraphiaBirmanica" and row.get("translation_status") == "confirmed" for row in source_witness_content_profile_rows),
            "eb_translation_unconfirmed_count": sum(row.get("source_work_key") == "epigraphiaBirmanica" and row.get("translation_status") != "confirmed" for row in source_witness_content_profile_rows),
            "eb_fascicle_content_inspection_count": len(eb_fascicle_content_inspection_rows),
            "direct_witness_search_result_counts": {
                "direct_witness_found": sum(row.get("search_result_status") == "direct_witness_found" for row in (uem_search_rows + core_search_rows + iob_text_search_rows)),
                "candidate_found": sum(row.get("search_result_status") == "candidate_found" for row in (uem_search_rows + core_search_rows + iob_text_search_rows)),
                "bibliographic_clue_found": sum(row.get("search_result_status") == "bibliographic_clue_found" for row in (uem_search_rows + core_search_rows + iob_text_search_rows)),
                "not_found": sum(row.get("search_result_status") == "not_found" for row in (uem_search_rows + core_search_rows + iob_text_search_rows)),
                "blocked_by_missing_local_index": sum(row.get("search_result_status") == "blocked_by_missing_local_index" for row in (uem_search_rows + core_search_rows + iob_text_search_rows)),
            },
            "verified_translation_after_inspection_count": sum(row.get("contains_translation_verified") == "confirmed" for row in verification_rows),
            "verified_edition_after_inspection_count": sum(row.get("contains_edition_verified") == "confirmed" for row in verification_rows),
            "notes": ["fixture"],
        }
        if report_overrides:
            report.update(report_overrides)
        (root / "translation_source_discovery_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        verification_report = {
            "verified_witness_count": len(verification_rows),
            "verified_direct_witness_count": sum(row.get("verification_status") in {"verified_direct_witness", "verified_catalogue_witness"} for row in verification_rows),
            "verified_translation_witness_count": sum(row.get("contains_translation_verified") == "confirmed" for row in verification_rows),
            "verified_edition_witness_count": sum(row.get("contains_edition_verified") == "confirmed" for row in verification_rows),
            "verified_plate_witness_count": sum(row.get("verification_status") == "verified_plate_witness" for row in verification_rows),
            "verified_catalogue_witness_count": sum(row.get("verification_status") == "verified_catalogue_witness" for row in verification_rows),
            "verified_secondary_work_count": sum(row.get("verification_status") == "verified_secondary_work" for row in verification_rows),
            "weak_false_positive_count": sum(row.get("verification_status") == "weak_false_positive" for row in verification_rows),
            "missing_direct_witness_search_count": sum(bool(row.get("matched_file_label")) for row in missing_search_rows),
            "titlepage_toc_snippet_count": len(snippet_rows),
            "source_works_needing_direct_witness_count": sum(row.get("discovery_status") == "needs_direct_witness_search" for row in plan_rows),
            "source_work_witness_gap_count": len(gap_rows),
            "source_works_with_verified_direct_witness": len({row["source_work_key"] for row in verification_rows if row.get("verification_status") in {"verified_direct_witness", "verified_catalogue_witness"}}),
            "source_works_still_needing_direct_witness": sum(row.get("local_direct_witness_status") == "no_local_direct_witness" for row in direct_witness_acquisition_status_rows),
            "sip_inspection_completed": bool(sip_inspection_rows),
            "sip_title_page_inspected": any(row.get("inspection_area") == "title_page" and row.get("inspection_status") == "confirmed" for row in sip_inspection_rows),
            "sip_contents_inspected": any(row.get("inspection_area") == "contents" and row.get("inspection_status") == "confirmed" for row in sip_inspection_rows),
            "sip_sample_entry_ocr_attempted": any(row.get("inspection_area") == "sample_entry" for row in sip_inspection_rows),
            "sip_sample_entry_inspected": any(row.get("inspection_area") == "sample_entry" and row.get("inspection_status") == "confirmed" for row in sip_inspection_rows),
            "sip_translation_status": "confirmed" if any(row.get("witness_id") == SIP_WITNESS_ID and row.get("translation_status") == "confirmed" for row in source_witness_content_profile_rows) else "unconfirmed",
            "sip_edition_status": "confirmed" if any(row.get("witness_id") == SIP_WITNESS_ID and row.get("edition_status") == "confirmed" for row in source_witness_content_profile_rows) else "unconfirmed",
            "sip_needs_sample_entry_review": any(row.get("inspection_area") == "sample_entry" for row in sip_inspection_rows) and not any(row.get("inspection_area") == "sample_entry" and row.get("inspection_status") == "confirmed" for row in sip_inspection_rows),
            "sip_contains_translation_status": "confirmed" if any(row.get("witness_id") == SIP_WITNESS_ID and row.get("translation_status") == "confirmed" for row in source_witness_content_profile_rows) else "unconfirmed",
            "uem_direct_search_count": sum(bool(row.get("matched_file_label")) for row in uem_search_rows),
            "core_source_direct_search_count": sum(bool(row.get("matched_file_label")) for row in core_search_rows),
            "inscriptions_of_burma_text_witness_search_count": len(iob_text_search_rows),
            "inscriptions_of_burma_text_witness_found": sum(row.get("is_text_witness_candidate") == "true" and row.get("search_result_status") == "direct_witness_found" for row in iob_text_search_rows),
            "inscriptions_of_burma_plate_false_positive_count": len({row.get("matched_file_id", "") or row.get("matched_file_label", "") for row in (iob_text_search_rows + iob_text_volume_hunt_rows) if row.get("false_positive_for_text") == "true"}),
            "inscriptions_of_burma_text_volume_hunt_count": len(iob_text_volume_hunt_rows),
            "missing_core_witness_hunt_count": len(missing_core_witness_hunt_rows),
            "witness_hunt_candidate_triage_count": len(witness_hunt_candidate_triage_rows),
            "direct_witness_acquisition_plan_count": len(direct_witness_acquisition_plan_rows),
            "manual_review_queue_count": len(manual_review_queue_rows),
            "ruled_out_witness_candidate_count": len(ruled_out_witness_candidate_rows),
            "external_catalogue_search_log_count": len(external_catalogue_search_log_rows),
            "external_catalogue_candidate_triage_count": len(external_catalogue_candidate_triage_rows),
            "acquisition_status_count": len(direct_witness_acquisition_status_rows),
            "acquisition_action_queue_count": len(acquisition_action_queue_rows),
            "authoritative_catalogue_record_count": sum(row.get("is_authoritative_record") == "true" for row in external_catalogue_candidate_triage_rows),
            "source_works_needing_authoritative_catalogue_record_count": sum(row.get("acquisition_status") == "needs_authoritative_catalogue_record" for row in direct_witness_acquisition_status_rows),
            "source_works_with_authoritative_catalogue_record_needing_local_copy_count": sum(row.get("acquisition_status") == "needs_local_copy_or_scan" for row in direct_witness_acquisition_status_rows),
            "source_works_needing_manual_content_review_count": sum(row.get("acquisition_status") == "needs_manual_content_review" for row in direct_witness_acquisition_status_rows),
            "source_works_with_local_direct_witness_but_translation_unconfirmed_count": sum(row.get("local_direct_witness_status") in {"local_direct_witness_verified", "local_direct_witness_needs_content_review"} and row.get("translation_coverage_status") in {"unconfirmed", "needs_manual_review"} for row in direct_witness_acquisition_status_rows),
            "plausible_direct_candidate_count": sum(row.get("triage_status") in PLAUSIBLE_HUNT_TRIAGE_STATUSES for row in witness_hunt_candidate_triage_rows),
            "known_false_positive_hunt_count": sum(row.get("triage_status") == "known_false_positive" for row in witness_hunt_candidate_triage_rows),
            "cross_source_or_secondary_hunt_count": sum(row.get("triage_status") in {"cross_source_witness", "secondary_or_unrelated", "too_broad_query_noise"} for row in witness_hunt_candidate_triage_rows),
            "rescue_candidate_review_count": len(rescue_review_rows),
            "epigraphia_birmanica_review_count": len(epigraphia_review_rows),
            "eb_verified_fascicle_count": len(epigraphia_fascicle_coverage_rows),
            "eb_fascicle_coverage_count": len(epigraphia_fascicle_coverage_rows),
            "eb_content_profile_count": sum(row.get("source_work_key") == "epigraphiaBirmanica" for row in source_witness_content_profile_rows),
            "eb_translation_confirmed_count": sum(row.get("source_work_key") == "epigraphiaBirmanica" and row.get("translation_status") == "confirmed" for row in source_witness_content_profile_rows),
            "eb_translation_unconfirmed_count": sum(row.get("source_work_key") == "epigraphiaBirmanica" and row.get("translation_status") != "confirmed" for row in source_witness_content_profile_rows),
            "eb_fascicle_content_inspection_count": len(eb_fascicle_content_inspection_rows),
            "direct_witness_search_result_counts": {
                "direct_witness_found": sum(row.get("search_result_status") == "direct_witness_found" for row in (uem_search_rows + core_search_rows + iob_text_search_rows)),
                "candidate_found": sum(row.get("search_result_status") == "candidate_found" for row in (uem_search_rows + core_search_rows + iob_text_search_rows)),
                "bibliographic_clue_found": sum(row.get("search_result_status") == "bibliographic_clue_found" for row in (uem_search_rows + core_search_rows + iob_text_search_rows)),
                "not_found": sum(row.get("search_result_status") == "not_found" for row in (uem_search_rows + core_search_rows + iob_text_search_rows)),
                "blocked_by_missing_local_index": sum(row.get("search_result_status") == "blocked_by_missing_local_index" for row in (uem_search_rows + core_search_rows + iob_text_search_rows)),
            },
            "verified_translation_after_inspection_count": sum(row.get("contains_translation_verified") == "confirmed" for row in verification_rows),
            "verified_edition_after_inspection_count": sum(row.get("contains_edition_verified") == "confirmed" for row in verification_rows),
            "notes": ["fixture"],
        }
        (root / "witness_verification_report.json").write_text(json.dumps(verification_report, indent=2) + "\n", encoding="utf-8")

    def _run_validation(self, root: Path) -> list[str]:
        return validate_translation_source_discovery(
            plan_path=root / "translation_source_discovery_plan.tsv",
            source_work_authority_path=root / "source_work_authority.tsv",
            witness_candidates_path=root / "witness_candidates.tsv",
            witness_classification_path=root / "witness_classification.tsv",
            witness_verification_path=root / "witness_verification.tsv",
            witness_snippets_path=root / "witness_titlepage_toc_snippets.tsv",
            missing_direct_search_path=root / "missing_direct_witness_search.tsv",
            source_work_gaps_path=root / "source_work_witness_gaps.tsv",
            sip_witness_inspection_path=root / "sip_witness_inspection.tsv",
            source_witness_content_profile_path=root / "source_witness_content_profile.tsv",
            eb_fascicle_content_inspection_path=root / "eb_fascicle_content_inspection.tsv",
            uem_direct_search_path=root / "uem_direct_witness_search.tsv",
            core_source_direct_search_path=root / "core_source_direct_witness_search.tsv",
            inscriptions_of_burma_text_search_path=root / "inscriptions_of_burma_text_witness_search.tsv",
            inscriptions_of_burma_text_volume_hunt_path=root / "inscriptions_of_burma_text_volume_hunt.tsv",
            missing_core_witness_hunt_path=root / "missing_core_witness_hunt.tsv",
            witness_hunt_candidate_triage_path=root / "witness_hunt_candidate_triage.tsv",
            direct_witness_acquisition_plan_path=root / "direct_witness_acquisition_plan.tsv",
            direct_witness_acquisition_status_path=root / "direct_witness_acquisition_status.tsv",
            manual_review_queue_path=root / "manual_review_queue.tsv",
            acquisition_action_queue_path=root / "acquisition_action_queue.tsv",
            translation_source_discovery_phase_summary_path=root / "translation_source_discovery_phase_summary.md",
            human_acquisition_checklist_path=root / "human_acquisition_checklist.tsv",
            ruled_out_witness_candidates_path=root / "ruled_out_witness_candidates.tsv",
            external_catalogue_search_log_path=root / "external_catalogue_search_log.tsv",
            external_catalogue_candidate_triage_path=root / "external_catalogue_candidate_triage.tsv",
            rescue_candidate_review_path=root / "rescue_candidate_review.tsv",
            epigraphia_birmanica_review_path=root / "epigraphia_birmanica_witness_review.tsv",
            epigraphia_birmanica_fascicle_coverage_path=root / "epigraphia_birmanica_fascicle_coverage.tsv",
            periodical_article_plan_path=root / "periodical_article_discovery_plan.tsv",
            report_path=root / "translation_source_discovery_report.json",
            witness_verification_report_path=root / "witness_verification_report.json",
        )


if __name__ == "__main__":
    unittest.main()
