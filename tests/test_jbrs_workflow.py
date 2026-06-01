from __future__ import annotations

import json
import re
import sys
import tempfile
import unittest
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import ocr_jbrs_google_vision as ocr
import detect_jbrs_translation_candidates as detect
import jbrs_workflow_common as common
import run_jbrs_production_ocr as production
from corpus_common import write_tsv
from jbrs_workflow_common import (
    JBRS_ARTICLE_REFERENCE_TARGETS_PATH,
    JBRS_ARTICLE_REFERENCE_TARGETS_REVIEW_PATH,
    JBRS_CORPUS_CITATION_PRIORITY_QUEUE_PATH,
    JBRS_EMBEDDED_TRANSLATION_EXCERPT_REVIEW_PATH,
    JBRS_EXTRACTED_SOURCE_TEXT_UNITS_PATH,
    JBRS_EXTRACTED_TRANSLATION_UNITS_PATH,
    JBRS_FOLLOWUP_SOURCE_LEADS_PATH,
    JBRS_LOCAL_FILE_MANIFEST_PATH,
    JBRS_OCR_BATCH_PLAN_PATH,
    JBRS_OCR_QUALITY_REVIEW_PATH,
    JBRS_OCR_STATUS_LOG_PATH,
    JBRS_PILOT_SUMMARY_PATH,
    JBRS_REFERENCE_HUNT_RAW_PATH,
    JBRS_REFERENCE_FILE_MATCH_PATH,
    JBRS_STRUCTURED_EXTRACTION_PLAN_PATH,
    JBRS_TRANSLATION_CANDIDATE_LOG_PATH,
    JBRS_TRANSLATION_CANDIDATE_REVIEW_PATH,
    OCR_BATCH_PLAN_FIELDS,
    OCR_STATUS_LOG_FIELDS,
    build_ocr_batch_plan_rows,
    build_ocr_status_log_rows,
    build_pilot_summary,
    classify_reference_kind,
    classify_translation_candidate,
    is_clean_article_target_row,
    read_tsv,
    tsv_header_and_row_count,
    title_needs_review,
)


class JBRSWorkflowArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.raw_rows = read_tsv(JBRS_REFERENCE_HUNT_RAW_PATH)
        cls.target_rows = read_tsv(JBRS_ARTICLE_REFERENCE_TARGETS_PATH)
        cls.target_review_rows = read_tsv(JBRS_ARTICLE_REFERENCE_TARGETS_REVIEW_PATH)
        cls.manifest_rows = read_tsv(JBRS_LOCAL_FILE_MANIFEST_PATH)
        cls.match_rows = read_tsv(JBRS_REFERENCE_FILE_MATCH_PATH)
        cls.batch_rows = read_tsv(JBRS_OCR_BATCH_PLAN_PATH)
        cls.status_rows = read_tsv(JBRS_OCR_STATUS_LOG_PATH)
        cls.candidate_rows = read_tsv(JBRS_TRANSLATION_CANDIDATE_LOG_PATH)
        cls.candidate_review_rows = read_tsv(JBRS_TRANSLATION_CANDIDATE_REVIEW_PATH)
        cls.excerpt_review_rows = read_tsv(JBRS_EMBEDDED_TRANSLATION_EXCERPT_REVIEW_PATH)
        cls.followup_source_lead_rows = read_tsv(JBRS_FOLLOWUP_SOURCE_LEADS_PATH)
        cls.citation_priority_rows = read_tsv(JBRS_CORPUS_CITATION_PRIORITY_QUEUE_PATH)
        cls.ocr_quality_review_rows = read_tsv(JBRS_OCR_QUALITY_REVIEW_PATH)
        cls.structured_extraction_plan_rows = read_tsv(JBRS_STRUCTURED_EXTRACTION_PLAN_PATH)
        cls.extracted_translation_unit_rows = read_tsv(JBRS_EXTRACTED_TRANSLATION_UNITS_PATH)
        cls.extracted_source_text_unit_rows = read_tsv(JBRS_EXTRACTED_SOURCE_TEXT_UNITS_PATH)
        cls.summary = json.loads(JBRS_PILOT_SUMMARY_PATH.read_text(encoding="utf-8"))

    def test_generated_files_exist(self) -> None:
        for path in [
            JBRS_REFERENCE_HUNT_RAW_PATH,
            JBRS_ARTICLE_REFERENCE_TARGETS_PATH,
            JBRS_ARTICLE_REFERENCE_TARGETS_REVIEW_PATH,
            JBRS_LOCAL_FILE_MANIFEST_PATH,
            JBRS_REFERENCE_FILE_MATCH_PATH,
            JBRS_OCR_BATCH_PLAN_PATH,
            JBRS_OCR_STATUS_LOG_PATH,
            JBRS_TRANSLATION_CANDIDATE_LOG_PATH,
            JBRS_TRANSLATION_CANDIDATE_REVIEW_PATH,
            JBRS_EMBEDDED_TRANSLATION_EXCERPT_REVIEW_PATH,
            JBRS_FOLLOWUP_SOURCE_LEADS_PATH,
            JBRS_CORPUS_CITATION_PRIORITY_QUEUE_PATH,
            JBRS_OCR_QUALITY_REVIEW_PATH,
            JBRS_STRUCTURED_EXTRACTION_PLAN_PATH,
            JBRS_EXTRACTED_TRANSLATION_UNITS_PATH,
            JBRS_EXTRACTED_SOURCE_TEXT_UNITS_PATH,
            JBRS_PILOT_SUMMARY_PATH,
        ]:
            self.assertTrue(path.exists(), path)

    def test_shorttitle_metadata_hit_stays_out_of_clean_targets(self) -> None:
        raw_row = next(row for row in self.raw_rows if row["matched_reference_text_short"] == "shorttitle = {JBRS},")
        self.assertEqual(raw_row["reference_kind"], "metadata_fragment")
        raw_target_links = "|".join(row["raw_reference_ids"] for row in self.target_rows)
        self.assertNotIn(raw_row["reference_id"], raw_target_links)
        self.assertFalse(is_clean_article_target_row(raw_row))

    def test_clean_targets_are_article_like(self) -> None:
        self.assertGreaterEqual(len(self.target_rows), 1)
        for row in self.target_rows:
            self.assertIn(row["reference_kind"], {"article_reference", "unclear"})
            self.assertTrue(
                row["author"] or row["article_title"] or row["page_range"] or row["volume"],
                row["target_reference_id"],
            )

    def test_reference_matches_link_clean_targets(self) -> None:
        target_ids = {row["target_reference_id"] for row in self.target_rows}
        local_ids = {row["local_file_id"] for row in self.manifest_rows}
        for row in self.match_rows:
            self.assertIn(row["reference_id"], target_ids)
            if row["local_file_id"]:
                self.assertIn(row["local_file_id"], local_ids)

    def test_ready_for_ocr_never_has_blocked_by(self) -> None:
        for row in self.batch_rows:
            if row["status"] == "ready_for_ocr":
                self.assertEqual(row["blocked_by"], "")

    def test_drive_scan_now_has_runtime_ready_rows(self) -> None:
        self.assertGreater(sum(row["runtime_path_available"] == "true" for row in self.batch_rows), 0)
        self.assertGreater(sum(row["status"] == "ready_for_ocr" for row in self.batch_rows), 0)

    def test_manifest_excludes_appledouble_sidecars(self) -> None:
        self.assertFalse(any(row["file_name"].startswith("._") for row in self.manifest_rows))

    def test_numeric_filenames_get_cautious_metadata_only(self) -> None:
        numeric_rows = [
            row for row in self.manifest_rows if re.fullmatch(r"\d{6}[A-Za-z]?\.pdf", row["file_name"])
        ]
        self.assertGreater(len(numeric_rows), 0)
        generic_row = next(
            row
            for row in numeric_rows
            if not row["probable_author_from_path"] and not row["probable_title_from_filename"]
        )
        self.assertEqual(generic_row["file_name"], "011015.pdf")
        self.assertIn(generic_row["is_whole_issue_or_volume"], {"", "false"})

    def test_summary_counts_match_generated_files(self) -> None:
        rebuilt = build_pilot_summary(
            self.raw_rows,
            self.target_rows,
            self.manifest_rows,
            self.match_rows,
            self.batch_rows,
            self.status_rows,
            self.candidate_rows,
            self.candidate_review_rows,
            self.excerpt_review_rows,
            self.followup_source_lead_rows,
            self.ocr_quality_review_rows,
            self.citation_priority_rows,
            self.structured_extraction_plan_rows,
            self.extracted_translation_unit_rows,
            self.extracted_source_text_unit_rows,
        )
        self.assertEqual(self.summary, rebuilt)

    def test_batch_and_status_tsvs_have_headers_and_matching_rows(self) -> None:
        batch_header, batch_row_count = tsv_header_and_row_count(JBRS_OCR_BATCH_PLAN_PATH, common.OCR_BATCH_PLAN_FIELDS)
        status_header, status_row_count = tsv_header_and_row_count(JBRS_OCR_STATUS_LOG_PATH, common.OCR_STATUS_LOG_FIELDS)
        self.assertEqual(batch_header, "\t".join(common.OCR_BATCH_PLAN_FIELDS))
        self.assertEqual(status_header, "\t".join(common.OCR_STATUS_LOG_FIELDS))
        self.assertEqual(batch_row_count, len(self.batch_rows))
        self.assertEqual(status_row_count, len(self.status_rows))
        self.assertEqual({row["batch_id"] for row in self.batch_rows}, {row["batch_id"] for row in self.status_rows})

    def test_batch_and_status_tsvs_fit_github_contents_threshold(self) -> None:
        self.assertLessEqual(JBRS_OCR_BATCH_PLAN_PATH.stat().st_size, common.MAX_GITHUB_CONTENTS_SIZE)
        self.assertLessEqual(JBRS_OCR_STATUS_LOG_PATH.stat().st_size, common.MAX_GITHUB_CONTENTS_SIZE)

    def test_malformed_targets_have_review_rows(self) -> None:
        review_by_id = {row["target_reference_id"]: row for row in self.target_review_rows}
        for row in self.target_rows:
            if title_needs_review(row["article_title"]):
                self.assertIn(
                    review_by_id[row["target_reference_id"]]["review_status"],
                    {"needs_manual_bibliographic_review", "parser_artifact", "duplicate_or_alias"},
                )

    def test_parser_artifact_targets_do_not_feed_confident_matching(self) -> None:
        parser_rows = [row for row in self.match_rows if row["target_review_status"] == "parser_artifact"]
        self.assertGreater(len(parser_rows), 0)
        for row in parser_rows:
            self.assertEqual(row["match_status"], "false_positive")

    def test_translation_candidates_require_review_before_promotion(self) -> None:
        review_by_key = {row["candidate_key"]: row for row in self.candidate_review_rows}
        review_by_local_file = {row["local_file_id"]: row for row in self.candidate_review_rows}
        self.assertEqual({row["candidate_key"] for row in self.candidate_rows}, set(review_by_key))
        self.assertFalse(any(row["review_status"] == "verified_translation_coverage" for row in self.candidate_review_rows))
        shwegugyi = review_by_local_file["1920-shwegugyiinscription-luce1920-pdf"]
        self.assertEqual(shwegugyi["is_actual_translation_section"], "true")
        self.assertEqual(shwegugyi["review_status"], "reviewed_manual_follow_up_needed")
        ananda = review_by_local_file["1976-anandainscriptions-tinlwin1976-pdf"]
        self.assertEqual(ananda["is_actual_translation_section"], "true")
        self.assertEqual(ananda["review_status"], "reviewed_manual_follow_up_needed")
        pyu = review_by_local_file["1917-pyuinscriptions-blagden1917-pdf"]
        self.assertEqual(pyu["review_status"], "reviewed_general_discussion_only")
        burma_debt = review_by_local_file["1932-burmadebttopagan-luce1932-pdf"]
        self.assertEqual(burma_debt["is_actual_translation_section"], "false")

    def test_excerpt_and_followup_layers_cover_embedded_lead(self) -> None:
        candidate_by_local_file = {row["local_file_id"]: row for row in self.candidate_rows}
        burma_debt = candidate_by_local_file["1932-burmadebttopagan-luce1932-pdf"]
        excerpt_row = next(row for row in self.excerpt_review_rows if row["local_file_id"] == "1932-burmadebttopagan-luce1932-pdf")
        followup_row = next(row for row in self.followup_source_lead_rows if row["possible_local_file_id"] == "1920-shwegugyiinscription-luce1920-pdf")
        self.assertEqual(excerpt_row["candidate_key"], burma_debt["candidate_key"])
        self.assertEqual(followup_row["trigger_candidate_key"], burma_debt["candidate_key"])

    def test_summary_distinguishes_translation_lead_types_without_verified_coverage(self) -> None:
        self.assertEqual(self.summary["embedded_translation_excerpt_candidate_count"], 1)
        self.assertEqual(self.summary["bibliography_only_translation_hit_count"], 1)
        self.assertEqual(self.summary["standalone_translation_section_count"], 2)
        self.assertEqual(self.summary["fuller_source_followup_lead_count"], 1)
        self.assertEqual(self.summary["citation_priority_queue_count"], 2)
        self.assertEqual(self.summary["mixed_language_extraction_plan_count"], 1)
        self.assertEqual(self.summary["extracted_source_text_unit_count"], 2)
        self.assertEqual(self.summary["extracted_translation_unit_count"], 2)
        self.assertEqual(self.summary["burmese_relevant_extracted_unit_count"], 2)
        self.assertEqual(self.summary["pali_only_extracted_unit_count"], 2)
        self.assertEqual(self.summary["verified_translation_coverage_count"], 0)

    def test_structured_extraction_plan_covers_current_jbrs_leads(self) -> None:
        plan_by_local_file = {row["source_local_file_id"]: row for row in self.structured_extraction_plan_rows}
        self.assertEqual(
            {
                "1920-shwegugyiinscription-luce1920-pdf",
                "1976-anandainscriptions-tinlwin1976-pdf",
                "1932-burmadebttopagan-luce1932-pdf",
            },
            set(plan_by_local_file),
        )
        self.assertEqual(plan_by_local_file["1920-shwegugyiinscription-luce1920-pdf"]["burmese_relevance_status"], "related_non_burmese_pagan_source")
        self.assertEqual(plan_by_local_file["1976-anandainscriptions-tinlwin1976-pdf"]["burmese_relevance_status"], "mixed_burmese_pali_relevance")
        self.assertIn("Pali and Burmese", plan_by_local_file["1976-anandainscriptions-tinlwin1976-pdf"]["source_text_language_or_script"])
        self.assertEqual(plan_by_local_file["1932-burmadebttopagan-luce1932-pdf"]["lead_type"], "embedded_translation_excerpt")

    def test_extraction_dry_run_records_shwegugyi_and_ananda_units(self) -> None:
        translation_by_file = defaultdict(list)
        for row in self.extracted_translation_unit_rows:
            translation_by_file[row["source_local_file_id"]].append(row)
        source_by_file = defaultdict(list)
        for row in self.extracted_source_text_unit_rows:
            source_by_file[row["source_local_file_id"]].append(row)
        self.assertEqual(len(translation_by_file["1920-shwegugyiinscription-luce1920-pdf"]), 1)
        self.assertEqual(len(source_by_file["1920-shwegugyiinscription-luce1920-pdf"]), 1)
        self.assertEqual(len(translation_by_file["1976-anandainscriptions-tinlwin1976-pdf"]), 1)
        self.assertEqual(len(source_by_file["1976-anandainscriptions-tinlwin1976-pdf"]), 1)
        shwegugyi_translation = translation_by_file["1920-shwegugyiinscription-luce1920-pdf"][0]
        ananda_translation = translation_by_file["1976-anandainscriptions-tinlwin1976-pdf"][0]
        ananda_source = source_by_file["1976-anandainscriptions-tinlwin1976-pdf"][0]
        self.assertEqual(shwegugyi_translation["is_burmese_relevant"], "false")
        self.assertEqual(shwegugyi_translation["translation_language"], "English")
        self.assertEqual(shwegugyi_translation["extraction_plan_id"], "jbrs-extract-plan-20260531-001")
        self.assertEqual(ananda_translation["is_burmese_relevant"], "true")
        self.assertEqual(ananda_translation["includes_pali"], "true")
        self.assertEqual(ananda_translation["includes_burmese"], "true")
        self.assertEqual(ananda_translation["source_text_unit_id"], ananda_source["source_text_unit_id"])
        self.assertEqual(ananda_source["source_language"], "Mixed Pali/Burmese witness notes")
        self.assertEqual(ananda_translation["candidate_key"], "jbrs-candidate-key:1976-anandainscriptions-tinlwin1976-pdf:explicit_translation_heading:page-1:e52b351bb422")

    def test_citation_priority_queue_tracks_corpus_derived_jbrs_leads(self) -> None:
        queue_by_file = {row["candidate_local_file_id"]: row for row in self.citation_priority_rows}
        self.assertEqual(queue_by_file["1932-burmadebttopagan-luce1932-pdf"]["translation_evidence_type"], "embedded_translation_excerpt")
        self.assertEqual(queue_by_file["1920-shwegugyiinscription-luce1920-pdf"]["burmese_relevance_status"], "related_non_burmese_pagan_source")
        self.assertIn("jbrs-target-0012", queue_by_file["1920-shwegugyiinscription-luce1920-pdf"]["corpus_source_or_manifest"])


class JBRSWorkflowLogicTests(unittest.TestCase):
    def _sample_batch_row(self, batch_id: str, status: str = "ready_for_ocr") -> dict[str, str]:
        return {
            "batch_id": batch_id,
            "local_file_id": f"{batch_id}-local",
            "file_name": f"{batch_id}.pdf",
            "path_stub": f"JBRS/{batch_id}.pdf",
            "volume": "",
            "issue": "",
            "year": "1933",
            "page_count_estimate": "1",
            "runtime_path_available": "true",
            "ocr_priority": "medium",
            "ocr_priority_reason": "test",
            "ocr_scope": "article_pages_only",
            "ocr_engine": "google_vision",
            "output_basename": batch_id,
            "expected_output_format": "google_vision_json|page_text|article_text|metadata_sidecar",
            "metadata_sidecar_path": f"data_local/ocr/jbrs/manifest/{batch_id}.json",
            "status": status,
            "blocked_by": "",
            "notes": "",
        }

    def test_runtime_cache_changes_needs_runtime_path_cache_to_ready(self) -> None:
        manifest_row = {
            "local_file_id": "sample-local-file",
            "file_name": "sample.pdf",
            "path_stub_or_redacted_path": "JBRS/sample.pdf",
            "probable_author_from_path": "",
            "probable_title_from_filename": "",
            "probable_year_from_filename": "1933",
            "probable_year_from_folder": "",
            "probable_volume_issue_from_filename": "",
            "probable_article_start_page_from_filename": "1",
            "probable_article_end_page_from_filename": "2",
            "folder_context": "JBRS",
            "is_article_split_pdf": "true",
            "is_whole_issue_or_volume": "false",
            "runtime_path_available": "false",
            "ocr_priority_reason": "",
        }
        without_cache = build_ocr_batch_plan_rows([manifest_row], [], {}, [])
        with_cache = build_ocr_batch_plan_rows([manifest_row], [], {"sample-local-file": "/example/jbrs/sample.pdf"}, [])
        self.assertEqual(without_cache[0]["status"], "needs_runtime_path_cache")
        self.assertEqual(with_cache[0]["status"], "ready_for_ocr")

    def test_translation_citation_is_not_explicit_heading(self) -> None:
        row = classify_translation_candidate(
            "See the translation of this inscription by Buhler for the Sanskrit passage.",
        )
        self.assertEqual(row[0], "citation_to_someone_else_translation")

    def test_general_translation_discussion_is_not_explicit_heading(self) -> None:
        row = classify_translation_candidate(
            "The inscriptions were to be edited with facsimile, notes, transcription and translation.",
        )
        self.assertEqual(row[0], "planned_or_general_translation_discussion")

    def test_reference_kind_detects_shorttitle_metadata(self) -> None:
        self.assertEqual(
            classify_reference_kind("data/example.tsv", "shorttitle = {JBRS},"),
            "metadata_fragment",
        )

    def test_reference_kind_detects_article_like_family_rows(self) -> None:
        self.assertEqual(
            classify_reference_kind(
                "data/working/bibliography/bibtex_authority/raw_reference_to_bibtex.tsv",
                "U Hswai, JBRS 48 (2), 1965, p. 67, no. 1",
            ),
            "article_reference",
        )

    def test_ocr_script_no_longer_uses_placeholder_failure(self) -> None:
        script_text = Path("scripts/ocr_jbrs_google_vision.py").read_text(encoding="utf-8")
        self.assertNotIn("live_submission_not_implemented", script_text)

    def test_runtime_path_cache_written_outside_repository_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime_cache = Path(tmpdir) / "jbrs_runtime_path_map.json"
            runtime_cache.write_text('{"jbrs-local-0001":"/example/jbrs/vol1.pdf"}', encoding="utf-8")
            self.assertTrue(runtime_cache.exists())
            self.assertNotIn("/data/working/bibliography/jbrs/", str(runtime_cache))

    def test_preflight_fails_cleanly_when_no_ready_rows_are_selected(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(ocr, "gitignored_data_local", return_value=True), patch.object(ocr, "staged_forbidden_paths", return_value=[]):
                report = ocr.preflight_report(
                    selected_rows=[],
                    runtime_path_cache={},
                    local_output_root=Path(tmpdir),
                    live_mode=False,
                )
        self.assertIn("No ready_for_ocr rows were selected.", report["errors"])

    def test_completed_batch_is_not_selected_by_default(self) -> None:
        batch_rows = [self._sample_batch_row("completed-batch")]
        status_rows = [{"batch_id": "completed-batch", "status": "completed"}]
        selected, skipped = ocr.select_batch_rows(batch_rows, status_rows, [], 0)
        self.assertEqual(selected, [])
        self.assertTrue(any("--force-rerun-completed" in message for message in skipped), skipped)

    def test_failed_batch_is_not_selected_by_default(self) -> None:
        batch_rows = [self._sample_batch_row("failed-batch")]
        status_rows = [{"batch_id": "failed-batch", "status": "failed"}]
        selected, skipped = ocr.select_batch_rows(batch_rows, status_rows, [], 0)
        self.assertEqual(selected, [])
        self.assertTrue(any("--rerun-failed" in message for message in skipped), skipped)

    def test_rerun_failed_allows_failed_batch(self) -> None:
        batch_rows = [self._sample_batch_row("failed-batch")]
        status_rows = [{"batch_id": "failed-batch", "status": "failed"}]
        selected, skipped = ocr.select_batch_rows(batch_rows, status_rows, [], 0, rerun_failed=True)
        self.assertEqual([row["batch_id"] for row in selected], ["failed-batch"])
        self.assertEqual(skipped, [])

    def test_force_rerun_completed_allows_completed_batch(self) -> None:
        batch_rows = [self._sample_batch_row("completed-batch")]
        status_rows = [{"batch_id": "completed-batch", "status": "completed"}]
        selected, skipped = ocr.select_batch_rows(
            batch_rows,
            status_rows,
            [],
            0,
            force_rerun_completed=True,
        )
        self.assertEqual([row["batch_id"] for row in selected], ["completed-batch"])
        self.assertEqual(skipped, [])

    def test_batch_id_respects_completed_guard_without_force(self) -> None:
        batch_rows = [self._sample_batch_row("jbrs-ocr-1227")]
        status_rows = [{"batch_id": "jbrs-ocr-1227", "status": "completed"}]
        selected, skipped = ocr.select_batch_rows(batch_rows, status_rows, ["jbrs-ocr-1227"], 0)
        self.assertEqual(selected, [])
        self.assertTrue(any("jbrs-ocr-1227" in message for message in skipped), skipped)

    def test_build_status_log_rows_preserves_completed_status(self) -> None:
        batch_rows = [self._sample_batch_row("completed-batch")]
        existing_rows = [
            {
                "ocr_job_id": "completed-batch-run",
                "batch_id": "completed-batch",
                "local_file_id": "completed-batch-local",
                "file_name": "completed-batch.pdf",
                "ocr_engine": "google_vision",
                "ocr_scope": "article_pages_only",
                "status": "completed",
                "pages_submitted": "8",
                "pages_completed": "8",
                "output_path_stub": "data_local/ocr/jbrs/article_text/completed-batch.txt",
                "metadata_sidecar_stub": "data_local/ocr/jbrs/manifest/completed-batch.json",
                "error_type": "",
                "error_message_short": "",
                "created_at": "2026-05-31T00:00:00+00:00",
                "updated_at": "2026-05-31T00:10:00+00:00",
                "notes": "done",
            }
        ]
        merged = build_ocr_status_log_rows(batch_rows, existing_rows)
        self.assertEqual(merged[0]["status"], "completed")
        self.assertEqual(merged[0]["pages_completed"], "8")
        self.assertEqual(merged[0]["notes"], "done")

    def test_preflight_passes_with_mocked_ready_row_and_runtime_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_root = Path(tmpdir)
            source = temp_root / "sample.pdf"
            source.write_bytes(b"%PDF-1.4\n")
            batch_row = {"batch_id": "test-batch", "local_file_id": "sample", "status": "ready_for_ocr"}
            with patch.object(ocr, "gitignored_data_local", return_value=True), patch.object(ocr, "staged_forbidden_paths", return_value=[]):
                report = ocr.preflight_report(
                    selected_rows=[batch_row],
                    runtime_path_cache={"sample": str(source)},
                    local_output_root=temp_root / "data_local/ocr/jbrs",
                    live_mode=False,
                )
        self.assertEqual(report["errors"], [])

    def test_live_preflight_reports_quota_project_and_auth_probe_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_root = Path(tmpdir)
            source = temp_root / "sample.pdf"
            source.write_bytes(b"%PDF-1.4\n")
            batch_row = {"batch_id": "test-batch", "local_file_id": "sample", "status": "ready_for_ocr"}
            with (
                patch.object(ocr, "gitignored_data_local", return_value=True),
                patch.object(ocr, "staged_forbidden_paths", return_value=[]),
                patch.object(ocr, "lookup_access_token", return_value=("token", "gcloud auth application-default print-access-token")),
                patch.object(ocr, "resolve_quota_project_id", return_value="project-123"),
                patch.object(ocr, "vision_auth_probe", return_value={"responses": [{}]}),
            ):
                report = ocr.preflight_report(
                       selected_rows=[batch_row],
                       runtime_path_cache={"sample": str(source)},
                       local_output_root=temp_root / "data_local/ocr/jbrs",
                       live_mode=True,
                )
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["credential_source"], "gcloud auth application-default print-access-token")
        self.assertEqual(report["quota_project_id"], "project-123")
        self.assertEqual(report["vision_auth_probe_status"], "ok")

    def test_live_preflight_fails_early_on_adc_quota_project_probe_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_root = Path(tmpdir)
            source = temp_root / "sample.pdf"
            source.write_bytes(b"%PDF-1.4\n")
            batch_row = {"batch_id": "test-batch", "local_file_id": "sample", "status": "ready_for_ocr"}
            with (
                patch.object(ocr, "gitignored_data_local", return_value=True),
                patch.object(ocr, "staged_forbidden_paths", return_value=[]),
                patch.object(ocr, "lookup_access_token", return_value=("token", "gcloud auth application-default print-access-token")),
                patch.object(ocr, "resolve_quota_project_id", return_value=""),
                patch.object(
                       ocr,
                       "vision_auth_probe",
                       side_effect=RuntimeError(
                           "Your application is authenticating by using local Application Default Credentials and no quota project is set."
                       ),
                ),
            ):
                report = ocr.preflight_report(
                       selected_rows=[batch_row],
                       runtime_path_cache={"sample": str(source)},
                       local_output_root=temp_root / "data_local/ocr/jbrs",
                       live_mode=True,
                )
        self.assertEqual(report["vision_auth_probe_status"], "failed")
        self.assertTrue(
            any("Google Vision rejected ADC because no usable quota project was supplied" in error for error in report["errors"]),
            report["errors"],
        )
        self.assertTrue(
            any("ADC token source is active but no quota project is configured" in warning for warning in report["warnings"]),
            report["warnings"],
        )

    def test_live_ocr_can_run_with_mocked_vision_response(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_root = Path(tmpdir)
            source = temp_root / "sample.pdf"
            source.write_bytes(b"%PDF-1.4\nsample")
            image = temp_root / "page-0001.png"
            image.write_bytes(b"fake-image")
            batch_rows = [
                {
                    "batch_id": "test-batch",
                    "local_file_id": "sample-local-file",
                    "file_name": "sample.pdf",
                    "path_stub": "JBRS/sample.pdf",
                    "volume": "",
                    "issue": "",
                    "year": "1933",
                    "page_count_estimate": "1",
                    "runtime_path_available": "true",
                    "ocr_priority": "medium",
                    "ocr_priority_reason": "test",
                    "ocr_scope": "article_pages_only",
                    "ocr_engine": "google_vision",
                    "output_basename": "sample-output",
                    "expected_output_format": "google_vision_json|page_text|article_text|metadata_sidecar",
                    "metadata_sidecar_path": "data_local/ocr/jbrs/manifest/sample-output.json",
                    "status": "ready_for_ocr",
                    "blocked_by": "",
                    "notes": "test row",
                }
            ]
            batch_plan = temp_root / "batch.tsv"
            status_log = temp_root / "status.tsv"
            runtime_cache = temp_root / "runtime.json"
            preflight_report_path = temp_root / "preflight.json"
            write_tsv(batch_plan, batch_rows, OCR_BATCH_PLAN_FIELDS)
            write_tsv(status_log, [], OCR_STATUS_LOG_FIELDS)
            runtime_cache.write_text(json.dumps({"sample-local-file": str(source)}), encoding="utf-8")
            args = SimpleNamespace(
                batch_plan=batch_plan,
                status_log=status_log,
                runtime_path_cache=runtime_cache,
                local_output_root=temp_root / "data_local/ocr/jbrs",
                preflight_report=preflight_report_path,
                batch_id=["test-batch"],
                limit=0,
                dry_run=False,
                execute=True,
                rerun_failed=False,
                force_rerun_completed=False,
            )
            with (
                patch.object(ocr, "gitignored_data_local", return_value=True),
                patch.object(ocr, "staged_forbidden_paths", return_value=[]),
                patch.object(ocr, "lookup_access_token", return_value=("token", "mock")),
                patch.object(ocr, "resolve_quota_project_id", return_value="project-123"),
                patch.object(ocr, "vision_auth_probe", return_value={"responses": [{}]}),
                patch.object(ocr, "source_to_images", return_value=[image]),
                patch.object(ocr, "vision_ocr_image", return_value={"responses": [{"fullTextAnnotation": {"text": "Translation\\nSample text"}}]}),
            ):
                result = ocr.run_selected_batches(args)
            self.assertEqual(result, 0)
            written_status = read_tsv(status_log)
            self.assertEqual(written_status[0]["status"], "completed")
            self.assertTrue((args.local_output_root / "article_text/sample-output.txt").exists())
            self.assertTrue((args.local_output_root / "manifest/sample-output.json").exists())

    def test_live_ocr_failure_preserves_submitted_page_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_root = Path(tmpdir)
            source = temp_root / "sample.pdf"
            source.write_bytes(b"%PDF-1.4\nsample")
            image = temp_root / "page-0001.png"
            image.write_bytes(b"fake-image")
            batch_rows = [
                {
                    "batch_id": "test-batch",
                    "local_file_id": "sample-local-file",
                    "file_name": "sample.pdf",
                    "path_stub": "JBRS/sample.pdf",
                    "volume": "",
                    "issue": "",
                    "year": "1933",
                    "page_count_estimate": "1",
                    "runtime_path_available": "true",
                    "ocr_priority": "medium",
                    "ocr_priority_reason": "test",
                    "ocr_scope": "article_pages_only",
                    "ocr_engine": "google_vision",
                    "output_basename": "sample-output",
                    "expected_output_format": "google_vision_json|page_text|article_text|metadata_sidecar",
                    "metadata_sidecar_path": "data_local/ocr/jbrs/manifest/sample-output.json",
                    "status": "ready_for_ocr",
                    "blocked_by": "",
                    "notes": "test row",
                }
            ]
            batch_plan = temp_root / "batch.tsv"
            status_log = temp_root / "status.tsv"
            runtime_cache = temp_root / "runtime.json"
            preflight_report_path = temp_root / "preflight.json"
            write_tsv(batch_plan, batch_rows, OCR_BATCH_PLAN_FIELDS)
            write_tsv(status_log, [], OCR_STATUS_LOG_FIELDS)
            runtime_cache.write_text(json.dumps({"sample-local-file": str(source)}), encoding="utf-8")
            args = SimpleNamespace(
                batch_plan=batch_plan,
                status_log=status_log,
                runtime_path_cache=runtime_cache,
                local_output_root=temp_root / "data_local/ocr/jbrs",
                preflight_report=preflight_report_path,
                batch_id=["test-batch"],
                limit=0,
                dry_run=False,
                execute=True,
                rerun_failed=False,
                force_rerun_completed=False,
            )
            with (
                patch.object(ocr, "gitignored_data_local", return_value=True),
                patch.object(ocr, "staged_forbidden_paths", return_value=[]),
                patch.object(ocr, "lookup_access_token", return_value=("token", "mock")),
                patch.object(ocr, "resolve_quota_project_id", return_value="project-123"),
                patch.object(ocr, "vision_auth_probe", return_value={"responses": [{}]}),
                patch.object(ocr, "source_to_images", return_value=[image]),
                patch.object(ocr, "vision_ocr_image", side_effect=RuntimeError("quota blocked")),
            ):
                result = ocr.run_selected_batches(args)
            self.assertEqual(result, 0)
            written_status = read_tsv(status_log)
            self.assertEqual(written_status[0]["status"], "failed")
            self.assertEqual(written_status[0]["pages_submitted"], "1")
            self.assertEqual(written_status[0]["pages_completed"], "")

    def test_validator_flags_blank_batch_plan_header(self) -> None:
        original_helper = common.tsv_header_and_row_count

        def fake_header(path: Path, fields: list[str]) -> tuple[str, int]:
            if path == common.JBRS_OCR_BATCH_PLAN_PATH:
                return "", 0
            return original_helper(path, fields)

        with patch.object(common, "tsv_header_and_row_count", side_effect=fake_header):
            errors = common.validate_jbrs_workflow()
        self.assertIn("JBRS OCR batch plan TSV is blank or missing the expected header.", errors)

    def test_validator_flags_summary_without_batch_rows(self) -> None:
        original_read_tsv = common.read_tsv

        def fake_read_tsv(path: Path):
            if path == common.JBRS_OCR_BATCH_PLAN_PATH:
                return []
            return original_read_tsv(path)

        with patch.object(common, "read_tsv", side_effect=fake_read_tsv):
            errors = common.validate_jbrs_workflow()
        self.assertTrue(
            any("pilot summary reports OCR batch rows" in error for error in errors),
            errors,
        )

    def test_narrow_candidate_selection_can_resolve_batch_ids(self) -> None:
        manifest_rows = [
            {"local_file_id": "target-file"},
            {"local_file_id": "other-file"},
        ]
        batch_rows = [
            {"batch_id": "batch-1", "local_file_id": "target-file"},
            {"batch_id": "batch-2", "local_file_id": "other-file"},
        ]
        selected = detect.resolve_selected_local_file_ids(
            manifest_rows,
            batch_rows,
            local_file_ids=[],
            batch_ids=["batch-1"],
        )
        self.assertEqual(selected, {"target-file"})

    def test_narrow_candidate_merge_preserves_existing_candidate_ids_for_matching_candidate_keys(self) -> None:
        existing_rows = [
            {
                "candidate_id": "jbrs-candidate-0007",
                "candidate_key": "target-file:key-a",
                "local_file_id": "target-file",
                "candidate_type": "translation_word_hit",
            },
            {
                "candidate_id": "jbrs-candidate-0008",
                "candidate_key": "other-file:key-a",
                "local_file_id": "other-file",
                "candidate_type": "translation_word_hit",
            },
        ]
        replacement_rows = [
            {
                "candidate_id": "jbrs-candidate-0001",
                "candidate_key": "target-file:key-a",
                "local_file_id": "target-file",
                "candidate_type": "planned_or_general_translation_discussion",
            }
        ]
        merged = detect.merge_candidate_rows(existing_rows, replacement_rows, {"target-file"})
        merged_by_local_file = {row["local_file_id"]: row for row in merged}
        self.assertEqual(merged_by_local_file["target-file"]["candidate_id"], "jbrs-candidate-0007")
        self.assertEqual(merged_by_local_file["other-file"]["candidate_id"], "jbrs-candidate-0008")

    def test_alignment_validator_flags_candidate_review_local_file_and_type_mismatches(self) -> None:
        candidate_rows = [
            {
                "candidate_id": "jbrs-candidate-0001",
                "candidate_key": "key-1",
                "local_file_id": "1920-shwegugyiinscription-luce1920-pdf",
                "candidate_type": "explicit_translation_heading",
            }
        ]
        review_rows = [
            {
                "candidate_id": "jbrs-candidate-0001",
                "candidate_key": "key-1",
                "local_file_id": "1976-anandainscriptions-tinlwin1976-pdf",
                "candidate_type": "translation_word_hit",
                "review_status": "needs_manual_review",
                "manual_assessment": "Ananda translation lead",
                "is_actual_translation_section": "",
                "is_inscription_translation": "",
            }
        ]
        errors = common.validate_translation_candidate_alignment(candidate_rows, review_rows, [], [], [])
        self.assertTrue(any("local_file_id does not match" in error for error in errors), errors)
        self.assertTrue(any("candidate_type does not match" in error for error in errors), errors)

    def test_alignment_validator_flags_named_source_conflicts_and_missing_quality_rows(self) -> None:
        candidate_rows = [
            {
                "candidate_id": "jbrs-candidate-0002",
                "candidate_key": "key-2",
                "local_file_id": "1948-centuryofprogress-luce1948-pdf",
                "candidate_type": "explicit_translation_heading",
            }
        ]
        review_rows = [
            {
                "candidate_id": "jbrs-candidate-0002",
                "candidate_key": "key-2",
                "local_file_id": "1948-centuryofprogress-luce1948-pdf",
                "candidate_type": "explicit_translation_heading",
                "review_status": "reviewed_manual_follow_up_needed",
                "manual_assessment": "The article contains a standalone inscription text-and-translation section with clear Shwegugyi framing and Ananda parallels.",
                "is_actual_translation_section": "true",
                "is_inscription_translation": "true",
            }
        ]
        errors = common.validate_translation_candidate_alignment(candidate_rows, review_rows, [], [], [])
        self.assertTrue(any("conflicts with local_file_id" in error for error in errors), errors)
        self.assertTrue(any("lacks OCR quality review" in error for error in errors), errors)

    def test_validator_flags_pali_only_translation_unit_marked_burmese_relevant(self) -> None:
        original_read_tsv = common.read_tsv

        def fake_read_tsv(path: Path):
            rows = original_read_tsv(path)
            if path == common.JBRS_EXTRACTED_TRANSLATION_UNITS_PATH:
                mutated = [dict(row) for row in rows]
                mutated[0]["is_burmese_relevant"] = "true"
                return mutated
            return rows

        with patch.object(common, "read_tsv", side_effect=fake_read_tsv):
            errors = common.validate_jbrs_workflow()
        self.assertTrue(any("Pali-only extracted translation unit is incorrectly marked Burmese-relevant" in error for error in errors), errors)

    def test_validator_flags_mixed_plan_unit_without_mixed_or_version_specific_scope(self) -> None:
        original_read_tsv = common.read_tsv

        def fake_read_tsv(path: Path):
            rows = original_read_tsv(path)
            if path == common.JBRS_EXTRACTED_SOURCE_TEXT_UNITS_PATH:
                mutated = [dict(row) for row in rows]
                for row in mutated:
                    if row["source_local_file_id"] == "1976-anandainscriptions-tinlwin1976-pdf":
                        row["source_language"] = "Pali"
                        row["notes"] = "Needs manual linkage."
                return mutated
            return rows

        with patch.object(common, "read_tsv", side_effect=fake_read_tsv):
            errors = common.validate_jbrs_workflow()
        self.assertTrue(any("Mixed-language extraction plan lacks mixed or version-specific source-unit scope" in error for error in errors), errors)

    def test_production_selector_skips_weak_numeric_metadata_clues(self) -> None:
        batch_rows = [
            {
                "batch_id": "jbrs-ocr-weak",
                "local_file_id": "weak-row",
                "file_name": "123456.pdf",
                "status": "ready_for_ocr",
                "ocr_priority": "medium",
                "page_count_estimate": "",
            },
            {
                "batch_id": "jbrs-ocr-strong",
                "local_file_id": "strong-row",
                "file_name": "PaliMonPagan1-Luce1976.pdf",
                "status": "ready_for_ocr",
                "ocr_priority": "medium",
                "page_count_estimate": "",
            },
        ]
        status_rows = []
        manifest_rows = [
            {
                "local_file_id": "weak-row",
                "file_name": "123456.pdf",
                "probable_title_from_filename": "",
                "probable_author_from_path": "G. H. Luce",
                "is_article_split_pdf": "true",
                "is_whole_issue_or_volume": "false",
            },
            {
                "local_file_id": "strong-row",
                "file_name": "PaliMonPagan1-Luce1976.pdf",
                "probable_title_from_filename": "Pali Mon Pagan 1",
                "probable_author_from_path": "G. H. Luce",
                "is_article_split_pdf": "true",
                "is_whole_issue_or_volume": "false",
            },
        ]
        selected_rows, _ = production.select_production_batch_rows(
            batch_rows=batch_rows,
            status_rows=status_rows,
            manifest_rows=manifest_rows,
            match_rows=[],
            citation_rows=[],
            limit=10,
        )
        self.assertEqual([row["batch_id"] for row in selected_rows], ["jbrs-ocr-strong"])

    def test_auth_error_helper_detects_token_expiry_responses(self) -> None:
        message = '{ "error": { "code": 401, "message": "Request had invalid authentication credentials." } }'
        self.assertTrue(ocr.is_refreshable_auth_error(message))
        self.assertFalse(ocr.is_refreshable_auth_error("quota project missing"))


if __name__ == "__main__":
    unittest.main()
