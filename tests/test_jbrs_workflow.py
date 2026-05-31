from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from corpus_common import read_tsv
from jbrs_workflow_common import (
    ABSOLUTE_PATH_PATTERN,
    JBRS_LOCAL_FILE_MANIFEST_PATH,
    JBRS_OCR_BATCH_PLAN_PATH,
    JBRS_OCR_STATUS_LOG_PATH,
    JBRS_README_PATH,
    JBRS_REFERENCE_FILE_MATCH_PATH,
    JBRS_REFERENCE_HUNT_PATH,
    JBRS_TRANSLATION_CANDIDATE_LOG_PATH,
    SHORT_SNIPPET_LIMIT,
    validate_jbrs_workflow,
)


class JBRSWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.reference_rows = read_tsv(JBRS_REFERENCE_HUNT_PATH)
        cls.manifest_rows = read_tsv(JBRS_LOCAL_FILE_MANIFEST_PATH)
        cls.match_rows = read_tsv(JBRS_REFERENCE_FILE_MATCH_PATH)
        cls.batch_rows = read_tsv(JBRS_OCR_BATCH_PLAN_PATH)
        cls.status_rows = read_tsv(JBRS_OCR_STATUS_LOG_PATH)
        cls.candidate_rows = read_tsv(JBRS_TRANSLATION_CANDIDATE_LOG_PATH)
        cls.readme_text = JBRS_README_PATH.read_text(encoding="utf-8")

    def test_reference_hunt_rows_store_required_fields(self) -> None:
        self.assertTrue(self.reference_rows)
        for row in self.reference_rows:
            self.assertTrue(row["reference_id"])
            self.assertTrue(row["source_file"])
            self.assertEqual(row["normalized_journal_title"], "Journal of the Burma Research Society")
            self.assertLessEqual(len(row["matched_reference_text_short"]), SHORT_SNIPPET_LIMIT)

    def test_local_manifest_redacts_absolute_paths(self) -> None:
        self.assertTrue(self.manifest_rows)
        for row in self.manifest_rows:
            self.assertFalse(ABSOLUTE_PATH_PATTERN.search(row["path_stub_or_redacted_path"]))

    def test_reference_file_matches_link_valid_rows(self) -> None:
        reference_ids = {row["reference_id"] for row in self.reference_rows}
        local_file_ids = {row["local_file_id"] for row in self.manifest_rows}
        for row in self.match_rows:
            self.assertIn(row["reference_id"], reference_ids)
            if row["local_file_id"]:
                self.assertIn(row["local_file_id"], local_file_ids)

    def test_ocr_batch_and_status_rows_link_valid_ids(self) -> None:
        local_file_ids = {row["local_file_id"] for row in self.manifest_rows}
        batch_ids = {row["batch_id"] for row in self.batch_rows}
        for row in self.batch_rows:
            self.assertIn(row["local_file_id"], local_file_ids)
        for row in self.status_rows:
            self.assertIn(row["batch_id"], batch_ids)

    def test_translation_candidates_keep_short_evidence_and_markers(self) -> None:
        for row in self.candidate_rows:
            self.assertLessEqual(len(row["short_evidence_snippet"]), SHORT_SNIPPET_LIMIT)
            if row["candidate_type"] == "explicit_translation_heading":
                self.assertTrue(row["evidence_marker"])

    def test_ocr_status_outputs_stay_outside_committed_working_dirs(self) -> None:
        for row in self.status_rows:
            self.assertFalse(row["output_path_stub"].startswith("data/working/"))
            self.assertFalse(ABSOLUTE_PATH_PATTERN.search(row["output_path_stub"]))
            self.assertFalse(ABSOLUTE_PATH_PATTERN.search(row["metadata_sidecar_stub"]))
            if row["metadata_sidecar_stub"]:
                self.assertTrue(row["metadata_sidecar_stub"].startswith("data_local/ocr/jbrs/manifest/"))

    def test_readme_guardrails_and_validator(self) -> None:
        self.assertIn("Berkeley IOB catalogue record is not a verified local witness", self.readme_text)
        self.assertIn("IOB plate portfolios are not the missing companion text witness", self.readme_text)
        self.assertIn("SIP does not satisfy the separate UEM witness gap", self.readme_text)
        self.assertEqual(validate_jbrs_workflow(), [])


if __name__ == "__main__":
    unittest.main()
