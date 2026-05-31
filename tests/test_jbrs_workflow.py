from __future__ import annotations

import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from jbrs_workflow_common import (
    JBRS_ARTICLE_REFERENCE_TARGETS_PATH,
    JBRS_LOCAL_FILE_MANIFEST_PATH,
    JBRS_OCR_BATCH_PLAN_PATH,
    JBRS_OCR_STATUS_LOG_PATH,
    JBRS_PILOT_SUMMARY_PATH,
    JBRS_REFERENCE_HUNT_RAW_PATH,
    JBRS_REFERENCE_FILE_MATCH_PATH,
    JBRS_TRANSLATION_CANDIDATE_LOG_PATH,
    build_pilot_summary,
    classify_reference_kind,
    classify_translation_candidate,
    is_clean_article_target_row,
    read_tsv,
)


class JBRSWorkflowArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.raw_rows = read_tsv(JBRS_REFERENCE_HUNT_RAW_PATH)
        cls.target_rows = read_tsv(JBRS_ARTICLE_REFERENCE_TARGETS_PATH)
        cls.manifest_rows = read_tsv(JBRS_LOCAL_FILE_MANIFEST_PATH)
        cls.match_rows = read_tsv(JBRS_REFERENCE_FILE_MATCH_PATH)
        cls.batch_rows = read_tsv(JBRS_OCR_BATCH_PLAN_PATH)
        cls.status_rows = read_tsv(JBRS_OCR_STATUS_LOG_PATH)
        cls.candidate_rows = read_tsv(JBRS_TRANSLATION_CANDIDATE_LOG_PATH)
        cls.summary = json.loads(JBRS_PILOT_SUMMARY_PATH.read_text(encoding="utf-8"))

    def test_generated_files_exist(self) -> None:
        for path in [
            JBRS_REFERENCE_HUNT_RAW_PATH,
            JBRS_ARTICLE_REFERENCE_TARGETS_PATH,
            JBRS_LOCAL_FILE_MANIFEST_PATH,
            JBRS_REFERENCE_FILE_MATCH_PATH,
            JBRS_OCR_BATCH_PLAN_PATH,
            JBRS_OCR_STATUS_LOG_PATH,
            JBRS_TRANSLATION_CANDIDATE_LOG_PATH,
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
            self.assertIn(row["local_file_id"], local_ids)

    def test_ready_for_ocr_never_has_blocked_by(self) -> None:
        for row in self.batch_rows:
            if row["status"] == "ready_for_ocr":
                self.assertEqual(row["blocked_by"], "")

    def test_rows_without_runtime_paths_need_runtime_cache(self) -> None:
        pending_rows = [
            row
            for row in self.batch_rows
            if row["status"] not in {"already_text_available", "skipped", "completed", "failed"}
            and row["runtime_path_available"] != "true"
        ]
        self.assertGreater(len(pending_rows), 0)
        for row in pending_rows[:25]:
            self.assertEqual(row["status"], "needs_runtime_path_cache")

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
        )
        self.assertEqual(self.summary, rebuilt)


class JBRSWorkflowLogicTests(unittest.TestCase):
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
            runtime_cache.write_text('{"jbrs-local-0001":"/Volumes/Example/JBRS/vol1.pdf"}', encoding="utf-8")
            self.assertTrue(runtime_cache.exists())
            self.assertNotIn("/data/working/bibliography/jbrs/", str(runtime_cache))


if __name__ == "__main__":
    unittest.main()
