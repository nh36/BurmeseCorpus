from __future__ import annotations

import json
import hashlib
import re
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from corpus_common import ensure_parent, read_tsv

REPO_ROOT = Path(__file__).resolve().parents[1]
BIBLIOGRAPHY_DIRECTORY = REPO_ROOT / "data/working/bibliography"
JBRS_DIRECTORY = BIBLIOGRAPHY_DIRECTORY / "jbrs"

JBRS_REFERENCE_HUNT_PATH = JBRS_DIRECTORY / "jbrs_reference_hunt.tsv"
JBRS_REFERENCE_HUNT_RAW_PATH = JBRS_DIRECTORY / "jbrs_reference_hunt_raw.tsv"
JBRS_ARTICLE_REFERENCE_TARGETS_PATH = JBRS_DIRECTORY / "jbrs_article_reference_targets.tsv"
JBRS_ARTICLE_REFERENCE_TARGETS_REVIEW_PATH = JBRS_DIRECTORY / "jbrs_article_reference_targets_review.tsv"
JBRS_LOCAL_FILE_MANIFEST_PATH = JBRS_DIRECTORY / "jbrs_local_file_manifest.tsv"
JBRS_REFERENCE_FILE_MATCH_PATH = JBRS_DIRECTORY / "jbrs_reference_file_match.tsv"
JBRS_OCR_BATCH_PLAN_PATH = JBRS_DIRECTORY / "jbrs_ocr_batch_plan.tsv"
JBRS_OCR_STATUS_LOG_PATH = JBRS_DIRECTORY / "jbrs_ocr_status_log.tsv"
JBRS_TRANSLATION_CANDIDATE_LOG_PATH = JBRS_DIRECTORY / "jbrs_translation_candidate_log.tsv"
JBRS_TRANSLATION_CANDIDATE_REVIEW_PATH = JBRS_DIRECTORY / "jbrs_translation_candidate_review.tsv"
JBRS_OCR_QUALITY_REVIEW_PATH = JBRS_DIRECTORY / "jbrs_ocr_quality_review.tsv"
JBRS_EMBEDDED_TRANSLATION_EXCERPT_REVIEW_PATH = JBRS_DIRECTORY / "jbrs_embedded_translation_excerpt_review.tsv"
JBRS_FOLLOWUP_SOURCE_LEADS_PATH = JBRS_DIRECTORY / "jbrs_followup_source_leads.tsv"
JBRS_CORPUS_CITATION_PRIORITY_QUEUE_PATH = JBRS_DIRECTORY / "jbrs_corpus_citation_priority_queue.tsv"
JBRS_STRUCTURED_EXTRACTION_PLAN_PATH = JBRS_DIRECTORY / "jbrs_structured_extraction_plan.tsv"
JBRS_EXTRACTED_TRANSLATION_UNITS_PATH = JBRS_DIRECTORY / "jbrs_extracted_translation_units.tsv"
JBRS_EXTRACTED_SOURCE_TEXT_UNITS_PATH = JBRS_DIRECTORY / "jbrs_extracted_source_text_units.tsv"
JBRS_PILOT_SUMMARY_PATH = JBRS_DIRECTORY / "jbrs_pilot_summary.json"
JBRS_README_PATH = JBRS_DIRECTORY / "README.md"

SOURCE_LIBRARY_MANIFEST_PATH = REPO_ROOT / "data/working/bibliography/local_sources/source_library_manifest.tsv"
LOCAL_FILE_MANIFEST_PATH = REPO_ROOT / "data/working/bibliography/local_sources/local_file_manifest.tsv"
OCR_MANIFEST_PATH = REPO_ROOT / "data/working/bibliography/local_sources/ocr_outputs/ocr_manifest.tsv"
OCR_TEXT_INDEX_PATH = REPO_ROOT / "data/working/bibliography/local_sources/ocr_outputs/ocr_text_index.tsv"
GITIGNORE_PATH = REPO_ROOT / ".gitignore"

DEFAULT_LOCAL_OUTPUT_ROOT = REPO_ROOT / "data_local/ocr/jbrs"
DEFAULT_RUNTIME_PATH_CACHE = DEFAULT_LOCAL_OUTPUT_ROOT / "manifest/jbrs_runtime_path_map.json"
DEFAULT_PREFLIGHT_REPORT_PATH = DEFAULT_LOCAL_OUTPUT_ROOT / "logs/jbrs_ocr_preflight.json"
JBRS_WORKING_OCR_ROOT = REPO_ROOT / "data/working/ocr/jbrs"
JBRS_WORKING_OCR_TEXT_ROOT = JBRS_WORKING_OCR_ROOT / "text"
JBRS_WORKING_OCR_METADATA_ROOT = JBRS_WORKING_OCR_ROOT / "metadata"
JBRS_OCR_TEXT_INDEX_PATH = JBRS_WORKING_OCR_ROOT / "jbrs_ocr_text_index.tsv"
LOCAL_SOURCE_WORKING_OCR_ROOT = REPO_ROOT / "data/working/ocr/local_sources"
LOCAL_SOURCE_WORKING_OCR_TEXT_ROOT = LOCAL_SOURCE_WORKING_OCR_ROOT / "text"
LOCAL_SOURCE_WORKING_OCR_METADATA_ROOT = LOCAL_SOURCE_WORKING_OCR_ROOT / "metadata"
LOCAL_SOURCE_OCR_TEXT_INDEX_PATH = LOCAL_SOURCE_WORKING_OCR_ROOT / "local_source_ocr_text_index.tsv"
JBRS_OCR_PRODUCTION_RUN_LOG_PATH = JBRS_DIRECTORY / "jbrs_ocr_production_run_log.tsv"
JBRS_OCR_TRANSLATION_HIT_INDEX_PATH = JBRS_DIRECTORY / "jbrs_ocr_translation_hit_index.tsv"
JBRS_OCR_TOP_EXTRACTION_CANDIDATES_PATH = JBRS_DIRECTORY / "jbrs_ocr_top_extraction_candidates.tsv"
JBRS_OCR_TOP_INSCRIPTION_EXTRACTION_CANDIDATES_PATH = (
    JBRS_DIRECTORY / "jbrs_ocr_top_inscription_extraction_candidates.tsv"
)
JBRS_OCR_PRODUCTION_SUMMARY_PATH = JBRS_DIRECTORY / "jbrs_ocr_production_summary.json"
JBRS_FILE_RENAMING_PLAN_PATH = JBRS_DIRECTORY / "jbrs_file_renaming_plan.tsv"
JBRS_FILE_ALIAS_MAP_PATH = JBRS_DIRECTORY / "jbrs_file_alias_map.tsv"
CORPUS_CITATION_INVENTORY_PATH = BIBLIOGRAPHY_DIRECTORY / "corpus_citation_inventory.tsv"
CORPUS_CITATION_TARGETS_PATH = BIBLIOGRAPHY_DIRECTORY / "corpus_citation_targets.tsv"
CORPUS_CITATION_SOURCE_FILE_MATCH_PATH = BIBLIOGRAPHY_DIRECTORY / "corpus_citation_source_file_match.tsv"
CORPUS_CITATION_SOURCE_FILE_MATCH_REVIEW_PATH = (
    BIBLIOGRAPHY_DIRECTORY / "corpus_citation_source_file_match_review.tsv"
)
CORPUS_TRANSLATION_SOURCE_DASHBOARD_PATH = BIBLIOGRAPHY_DIRECTORY / "corpus_translation_source_dashboard.tsv"
CORPUS_OUT_OF_SCOPE_NON_BURMESE_AUDIT_PATH = (
    BIBLIOGRAPHY_DIRECTORY / "corpus_out_of_scope_non_burmese_audit.tsv"
)
CORPUS_CITED_SOURCE_OCR_QUEUE_PATH = BIBLIOGRAPHY_DIRECTORY / "corpus_cited_source_ocr_queue.tsv"
CORPUS_CITATION_WORKFLOW_SUMMARY_PATH = BIBLIOGRAPHY_DIRECTORY / "corpus_citation_workflow_summary.json"
INSCRIPTIONS_OF_BURMA_CROSS_REFERENCE_INDEX_PATH = (
    BIBLIOGRAPHY_DIRECTORY / "inscriptions_of_burma_cross_reference_index.tsv"
)
TN_SOURCE_HUNT_PATH = BIBLIOGRAPHY_DIRECTORY / "tn_source_hunt.tsv"
PPA_SOURCE_HUNT_PATH = BIBLIOGRAPHY_DIRECTORY / "ppa_source_hunt.tsv"
MAX_GITHUB_CONTENTS_SIZE = 1_000_000

RAW_REFERENCE_HUNT_FIELDS = [
    "reference_id",
    "target_reference_id",
    "source_file",
    "source_work_key_if_known",
    "reference_kind",
    "matched_reference_text_short",
    "normalized_journal_title",
    "normalized_reference_key",
    "volume",
    "issue",
    "year",
    "page_range",
    "author",
    "article_title",
    "inscription_or_topic_keywords",
    "reference_confidence",
    "needs_manual_bibliographic_cleanup",
    "notes",
]

REFERENCE_HUNT_FIELDS = RAW_REFERENCE_HUNT_FIELDS

ARTICLE_REFERENCE_TARGET_FIELDS = [
    "target_reference_id",
    "reference_kind",
    "normalized_reference_key",
    "source_file_examples",
    "raw_reference_ids",
    "raw_hit_count",
    "normalized_journal_title",
    "volume",
    "issue",
    "year",
    "page_range",
    "author",
    "article_title",
    "inscription_or_topic_keywords",
    "reference_confidence",
    "needs_manual_bibliographic_cleanup",
    "notes",
]

ARTICLE_REFERENCE_TARGET_REVIEW_FIELDS = [
    "target_reference_id",
    "current_author",
    "current_article_title",
    "current_volume",
    "current_issue",
    "current_year",
    "current_page_range",
    "review_status",
    "corrected_author",
    "corrected_article_title",
    "corrected_volume",
    "corrected_issue",
    "corrected_year",
    "corrected_page_range",
    "source_evidence_short",
    "notes",
]

LOCAL_FILE_MANIFEST_FIELDS = [
    "local_file_id",
    "path_stub_or_redacted_path",
    "file_name",
    "extension",
    "file_size_bytes",
    "modified_date",
    "probable_author_from_path",
    "probable_title_from_filename",
    "probable_year_from_filename",
    "probable_year_from_folder",
    "probable_volume_issue_from_filename",
    "probable_article_start_page_from_filename",
    "probable_article_end_page_from_filename",
    "folder_context",
    "is_probable_jbrs",
    "is_article_split_pdf",
    "is_whole_issue_or_volume",
    "runtime_path_available",
    "manifest_confidence",
    "ocr_priority_reason",
    "needs_manual_review",
    "notes",
]

REFERENCE_FILE_MATCH_FIELDS = [
    "reference_id",
    "target_review_status",
    "local_file_id",
    "match_status",
    "match_confidence",
    "match_basis",
    "author_match",
    "title_match",
    "year_match",
    "volume_issue_match",
    "path_context_match",
    "candidate_file_name",
    "candidate_path_stub",
    "next_action",
    "notes",
]

OCR_BATCH_PLAN_FIELDS = [
    "batch_id",
    "local_file_id",
    "file_name",
    "path_stub",
    "volume",
    "issue",
    "year",
    "page_count_estimate",
    "runtime_path_available",
    "ocr_priority",
    "ocr_priority_reason",
    "ocr_scope",
    "ocr_engine",
    "output_basename",
    "expected_output_format",
    "metadata_sidecar_path",
    "status",
    "blocked_by",
    "notes",
]

OCR_STATUS_LOG_FIELDS = [
    "ocr_job_id",
    "batch_id",
    "local_file_id",
    "file_name",
    "ocr_engine",
    "ocr_scope",
    "status",
    "pages_submitted",
    "pages_completed",
    "output_path_stub",
    "metadata_sidecar_stub",
    "error_type",
    "error_message_short",
    "created_at",
    "updated_at",
    "notes",
]

JBRS_OCR_PRODUCTION_RUN_LOG_FIELDS = [
    "run_id",
    "run_date",
    "selection_rule",
    "selected_count",
    "completed_count",
    "failed_count",
    "skipped_count",
    "output_text_root",
    "metadata_root",
    "notes",
]

JBRS_OCR_TEXT_INDEX_FIELDS = [
    "local_file_id",
    "batch_id",
    "file_name",
    "old_file_name",
    "canonical_file_name",
    "probable_article_title",
    "probable_author",
    "year",
    "path_stub",
    "old_path_stub",
    "new_path_stub_or_repo_path",
    "ocr_text_path",
    "metadata_path",
    "pages_completed",
    "ocr_status",
    "language_scope_guess",
    "contains_translation_marker",
    "contains_text_marker",
    "contains_inscription_marker",
    "contains_burmese_marker",
    "contains_pali_marker",
    "contains_mon_marker",
    "contains_pyu_marker",
    "notes",
]

JBRS_OCR_TRANSLATION_HIT_INDEX_FIELDS = [
    "hit_id",
    "local_file_id",
    "batch_id",
    "file_name",
    "old_file_name",
    "canonical_file_name",
    "probable_article_title",
    "probable_author",
    "old_path_stub",
    "new_path_stub_or_repo_path",
    "page_marker",
    "hit_type",
    "matched_marker",
    "short_context",
    "language_scope_guess",
    "burmese_relevance_guess",
    "priority",
    "next_action",
    "notes",
]

JBRS_OCR_TOP_EXTRACTION_CANDIDATES_FIELDS = [
    "candidate_rank",
    "local_file_id",
    "batch_id",
    "file_name",
    "old_file_name",
    "canonical_file_name",
    "probable_article_title",
    "probable_author",
    "year",
    "old_path_stub",
    "new_path_stub_or_repo_path",
    "ocr_text_path",
    "language_scope_guess",
    "burmese_relevance_guess",
    "inscriptional_relevance_class",
    "translation_hit_count",
    "text_hit_count",
    "inscription_hit_count",
    "strongest_markers",
    "sample_pages",
    "reason_for_priority",
    "recommended_next_action",
    "notes",
]

JBRS_OCR_TOP_INSCRIPTION_EXTRACTION_CANDIDATES_FIELDS = (
    JBRS_OCR_TOP_EXTRACTION_CANDIDATES_FIELDS
)

JBRS_FILE_RENAMING_PLAN_FIELDS = [
    "local_file_id",
    "batch_id",
    "old_file_name",
    "old_path_stub",
    "current_ocr_text_path",
    "current_metadata_path",
    "probable_article_title",
    "probable_author",
    "probable_year",
    "canonical_base_name",
    "proposed_pdf_file_name",
    "proposed_ocr_text_file_name",
    "proposed_metadata_file_name",
    "identity_confidence",
    "rename_status",
    "notes",
]

JBRS_FILE_ALIAS_MAP_FIELDS = [
    "local_file_id",
    "old_file_name",
    "old_path_stub",
    "canonical_file_name",
    "canonical_ocr_text_path",
    "canonical_metadata_path",
    "canonical_pdf_path_stub",
    "alias_status",
    "notes",
]

JBRS_OCR_LANGUAGE_SCOPE_VALUES = {
    "Burmese",
    "Pali",
    "Mixed Burmese/Pali",
    "Mon",
    "Pyu",
    "mixed_or_uncertain",
    "non_burmese_relevant_context",
}

JBRS_BURMESE_RELEVANCE_GUESS_VALUES = {
    "direct_burmese_relevance",
    "mixed_burmese_pali_relevance",
    "pali_only_not_burmese_corpus_material",
    "non_burmese_inscriptional_context",
    "contextual_only",
    "uncertain_needs_review",
}

JBRS_INSCRIPTIONAL_RELEVANCE_CLASS_VALUES = {
    "direct_inscription_translation",
    "direct_inscription_text",
    "inscription_commentary_or_citation",
    "language_history_or_epigraphy",
    "general_burmese_text_translation",
    "non_burmese_inscription_context",
    "uncertain",
}

TERMINAL_OCR_STATUS_VALUES = {"dry_run_ok", "submitted", "completed", "failed"}

OCR_QUALITY_REVIEW_FIELDS = [
    "review_id",
    "batch_id",
    "local_file_id",
    "file_name",
    "pages_expected",
    "pages_present",
    "page_markers_present",
    "english_ocr_quality",
    "burmese_or_pali_ocr_quality",
    "contains_inscription_text",
    "contains_translation_section",
    "contains_transliteration_or_edition",
    "contains_commentary_only",
    "manual_review_status",
    "short_safe_evidence_marker",
    "next_action",
    "notes",
]

EMBEDDED_TRANSLATION_EXCERPT_REVIEW_FIELDS = [
    "excerpt_review_id",
    "candidate_id",
    "candidate_key",
    "batch_id",
    "local_file_id",
    "file_name",
    "article_title",
    "author",
    "year",
    "page_marker_or_page_range",
    "excerpt_type",
    "source_reference_in_article",
    "inscription_or_text_identification",
    "is_actual_translation_excerpt",
    "is_standalone_translation_section",
    "is_citation_to_fuller_translation_elsewhere",
    "has_source_text_nearby",
    "has_transliteration_nearby",
    "short_safe_evidence_marker",
    "manual_review_status",
    "next_action",
    "notes",
]

FOLLOWUP_SOURCE_LEAD_FIELDS = [
    "lead_id",
    "trigger_candidate_id",
    "trigger_candidate_key",
    "trigger_file",
    "cited_source_description",
    "possible_local_file_id",
    "possible_file_name",
    "possible_path_stub",
    "match_confidence",
    "needs_bibliographic_cleanup",
    "is_same_work_as_cited_source",
    "recommended_action",
    "notes",
]

CORPUS_CITATION_PRIORITY_QUEUE_FIELDS = [
    "priority_id",
    "corpus_source_or_manifest",
    "corpus_citation_text_short",
    "normalized_source_reference",
    "candidate_local_file_id",
    "candidate_file_name",
    "candidate_batch_id",
    "matched_jbrs_candidate_key",
    "language_scope_expected",
    "burmese_relevance_status",
    "translation_evidence_type",
    "priority",
    "recommended_action",
    "notes",
]

TRANSLATION_CANDIDATE_FIELDS = [
    "candidate_id",
    "candidate_key",
    "local_file_id",
    "reference_id_if_any",
    "journal",
    "volume",
    "issue",
    "year",
    "article_title",
    "author",
    "page_range_or_page",
    "candidate_type",
    "evidence_marker",
    "short_evidence_snippet",
    "contains_translation_candidate",
    "contains_edition_or_transliteration_candidate",
    "contains_commentary_only",
    "confidence",
    "next_action",
    "notes",
]

TRANSLATION_CANDIDATE_REVIEW_FIELDS = [
    "candidate_id",
    "candidate_key",
    "local_file_id",
    "candidate_type",
    "review_status",
    "reviewed_by_or_method",
    "manual_assessment",
    "is_actual_translation_section",
    "is_inscription_translation",
    "is_general_discussion",
    "is_citation_to_external_translation",
    "next_action",
    "notes",
]

STRUCTURED_EXTRACTION_PLAN_FIELDS = [
    "extraction_plan_id",
    "source_local_file_id",
    "batch_id",
    "file_name",
    "article_title",
    "author",
    "year",
    "lead_type",
    "source_text_language_or_script",
    "translation_language",
    "contains_burmese_inscription",
    "contains_pali_inscription",
    "contains_other_language_inscription",
    "burmese_relevance_status",
    "page_range_or_markers",
    "source_identifier_in_article",
    "known_external_source_refs",
    "extraction_unit",
    "proposed_output_format",
    "needs_manual_source_linkage",
    "priority",
    "next_action",
    "notes",
]

EXTRACTED_TRANSLATION_UNIT_FIELDS = [
    "translation_unit_id",
    "source_local_file_id",
    "batch_id",
    "candidate_key",
    "extraction_plan_id",
    "excerpt_review_id",
    "corpus_record_id",
    "inscription_id",
    "citation_target_id",
    "normalized_source_key",
    "source_page_or_plate",
    "article_title",
    "page_marker",
    "unit_order",
    "inscription_or_text_id",
    "source_text_unit_id",
    "source_language",
    "translation_language",
    "is_burmese_relevant",
    "includes_pali",
    "includes_burmese",
    "includes_other_language",
    "translation_text",
    "translation_status",
    "review_status",
    "alignment_confidence",
    "notes",
]

EXTRACTED_SOURCE_TEXT_UNIT_FIELDS = [
    "source_text_unit_id",
    "source_local_file_id",
    "batch_id",
    "candidate_key",
    "extraction_plan_id",
    "excerpt_review_id",
    "corpus_record_id",
    "inscription_id",
    "citation_target_id",
    "normalized_source_key",
    "source_page_or_plate",
    "article_title",
    "page_marker",
    "unit_order",
    "inscription_or_text_id",
    "source_language",
    "translation_language",
    "script_or_transliteration",
    "is_burmese_relevant",
    "source_text",
    "source_text_status",
    "review_status",
    "alignment_confidence",
    "notes",
]

CORPUS_CITATION_INVENTORY_FIELDS = [
    "corpus_record_id",
    "inscription_id",
    "corpus_title_or_label",
    "corpus_date_or_period",
    "corpus_language_field",
    "citation_raw",
    "citation_type_if_given",
    "source_abbreviation",
    "source_author",
    "source_title",
    "source_year",
    "source_volume_issue",
    "source_page_or_plate",
    "mentions_translation",
    "mentions_text",
    "mentions_transcription",
    "mentions_edition",
    "mentions_rubbing_or_plate",
    "mentions_commentary_only",
    "corpus_language_scope",
    "source_work_language_scope",
    "citation_relevance_to_burmese_corpus",
    "citation_target_id",
    "notes",
]

CORPUS_CITATION_TARGET_FIELDS = [
    "citation_target_id",
    "normalized_source_key",
    "source_abbreviation",
    "normalized_author",
    "normalized_title",
    "normalized_year",
    "normalized_volume_issue",
    "normalized_page_or_plate",
    "source_type",
    "likely_contains_translation",
    "likely_contains_source_text",
    "likely_contains_edition_only",
    "likely_contains_commentary_only",
    "source_work_language_scope",
    "source_role",
    "target_priority",
    "notes",
]

CORPUS_CITATION_SOURCE_FILE_MATCH_FIELDS = [
    "citation_target_id",
    "normalized_source_key",
    "matched_local_file_id",
    "matched_batch_id",
    "matched_file_name",
    "matched_canonical_file_name",
    "matched_ocr_text_path",
    "matched_metadata_path",
    "match_status",
    "match_confidence",
    "match_basis",
    "ocr_status",
    "needs_ocr",
    "needs_manual_file_hunt",
    "notes",
]

CORPUS_CITATION_SOURCE_FILE_MATCH_REVIEW_FIELDS = [
    "citation_target_id",
    "normalized_source_key",
    "current_match_status",
    "current_matched_local_file_id",
    "current_matched_file_name",
    "review_status",
    "reviewed_match_status",
    "reviewed_matched_local_file_id",
    "reviewed_matched_file_name",
    "review_confidence",
    "review_basis",
    "queue_for_targeted_ocr",
    "notes",
]

CORPUS_TRANSLATION_SOURCE_DASHBOARD_FIELDS = [
    "dashboard_id",
    "inscription_id",
    "corpus_record_id",
    "corpus_title_or_label",
    "corpus_language_field",
    "corpus_language_scope",
    "citation_target_id",
    "citation_raw",
    "normalized_source_key",
    "source_role",
    "matched_local_file_id",
    "matched_ocr_text_path",
    "translation_status_from_citation",
    "source_text_status_from_citation",
    "source_work_language_scope",
    "citation_relevance_to_burmese_corpus",
    "is_burmese_relevant",
    "source_match_status",
    "ocr_status",
    "extraction_status",
    "next_action",
    "notes",
]

INSCRIPTIONS_OF_BURMA_CROSS_REFERENCE_INDEX_FIELDS = [
    "iob_plate",
    "iob_plate_normalized",
    "iob_page",
    "list_ref",
    "ppa_ref",
    "tn_ref",
    "sip_ref",
    "ub_ref",
    "jbrs_ref",
    "other_ref",
    "place_or_object_description",
    "linked_inscription_id",
    "linked_corpus_record_id",
    "link_confidence",
    "link_basis",
    "needs_manual_review",
    "notes",
]

SOURCE_HUNT_FIELDS = [
    "candidate_id",
    "candidate_file_id",
    "candidate_file_name",
    "candidate_path_stub_or_source",
    "candidate_title",
    "candidate_author",
    "candidate_year",
    "evidence_for_match",
    "evidence_against_match",
    "match_status",
    "needs_manual_review",
    "notes",
]

CORPUS_CITED_SOURCE_OCR_QUEUE_FIELDS = [
    "ocr_queue_id",
    "citation_target_id",
    "inscription_id_or_count",
    "matched_local_file_id",
    "batch_id",
    "file_name",
    "canonical_file_name",
    "reason_for_ocr",
    "priority",
    "ocr_status",
    "notes",
]

CORPUS_OUT_OF_SCOPE_NON_BURMESE_AUDIT_FIELDS = [
    "dashboard_id",
    "corpus_record_id",
    "inscription_id",
    "corpus_language_field",
    "corpus_language_scope",
    "source_work_language_scope",
    "citation_relevance_to_burmese_corpus",
    "citation_target_id",
    "normalized_source_key",
    "raw_citation",
    "extraction_status",
    "next_action",
    "audit_status",
    "audit_reason",
]

SHORT_SNIPPET_LIMIT = 220
ABSOLUTE_PATH_PATTERN = re.compile(r"(^/(?:Users|home|var|private|tmp|opt|Volumes)\b|^[A-Za-z]:\\\\)")
JOURNAL_TITLE = "Journal of the Burma Research Society"
ARTICLE_REFERENCE_KINDS = {"article_reference", "unclear"}
HIGH_PRIORITY_MATCH_STATUSES = {"exact_or_near_exact_match"}
ACCEPTED_TARGET_REVIEW_STATUSES = {"accepted", "corrected"}
SKIPPED_TARGET_REVIEW_STATUSES = {"parser_artifact", "duplicate_or_alias"}
MANUAL_TARGET_REVIEW_STATUSES = {"needs_manual_bibliographic_review"}
OCR_READY_STATUSES = {"ready_for_ocr"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp", ".bmp"}
SOURCE_FILE_EXTENSIONS = IMAGE_EXTENSIONS | {".pdf", ".djvu"}
CORPUS_CITATION_LANGUAGE_SCOPES = {
    "Burmese",
    "Old Burmese",
    "Pali",
    "Mon",
    "Pyu",
    "Mixed Burmese/Pali",
    "mixed_or_uncertain",
    "unknown",
}
CORPUS_CITATION_SOURCE_TYPES = {
    "article",
    "book",
    "corpus_volume",
    "catalogue",
    "plate_or_rubbing",
    "dissertation_or_thesis",
    "unclear",
}
CORPUS_CITATION_TARGET_PRIORITIES = {"high", "medium", "low"}
CORPUS_CITATION_SOURCE_ROLES = {
    "translation_witness",
    "source_text_witness",
    "edition_witness",
    "catalogue_or_list_witness",
    "cross_reference_witness",
    "commentary_witness",
    "internal_corpus_source",
    "mixed_or_uncertain",
}
NON_EXTRACTIVE_SOURCE_ROLES = {
    "catalogue_or_list_witness",
    "cross_reference_witness",
    "commentary_witness",
    "internal_corpus_source",
}
CORPUS_CITATION_MATCH_STATUSES = {
    "exact_or_near_exact_match",
    "plausible_match",
    "multiple_candidates",
    "no_local_candidate_found",
    "already_ocr_available",
    "needs_ocr",
    "needs_manual_review",
}
CORPUS_CITATION_MATCH_REVIEW_STATUSES = {
    "accepted_match",
    "corrected_match",
    "rejected_wrong_match",
    "needs_manual_file_hunt",
    "multiple_local_witnesses",
    "not_needed_internal_source",
}
CORPUS_CITATION_RELEVANCE_STATUSES = {
    "direct_burmese_relevance",
    "mixed_burmese_pali_relevance",
    "non_burmese_parallel_only",
    "supporting_context_only",
    "out_of_scope_non_burmese_record",
}
CORPUS_OUT_OF_SCOPE_AUDIT_STATUSES = {
    "correctly_out_of_scope_non_burmese_record",
    "wrongly_out_of_scope_burmese_record",
    "mixed_record_needs_review",
    "non_burmese_parallel_or_context",
    "unclear_needs_manual_review",
}
CORPUS_OUT_OF_SCOPE_AUDIT_REASONS = {
    "non_burmese_record_language_scope",
    "parallel_non_burmese_record",
    "non_burmese_context",
    "mixed_record_scope",
    "burmese_record_should_not_be_out_of_scope",
    "missing_corpus_language_scope",
    "unclear_corpus_language_scope",
}
CORPUS_CITATION_EXTRACTION_STATUSES = {
    "not_started",
    "ready_for_ocr",
    "ocr_available_needs_review",
    "ready_for_extraction",
    "extracted_needs_review",
    "extracted_verified",
    "citation_not_translation",
    "source_not_found",
    "out_of_scope_non_burmese",
    "unclear_needs_manual_review",
}


def corpus_citation_match_has_strong_evidence(row: dict[str, str]) -> bool:
    match_status = row.get("match_status", "")
    match_basis = row.get("match_basis", "")
    file_name = row.get("matched_file_name", "")
    target_key = row.get("normalized_source_key", "")
    if match_status not in {"needs_ocr", "already_ocr_available"}:
        return False
    if not row.get("matched_local_file_id", "") or not file_name:
        return False
    lowered_file_name = file_name.casefold()
    lowered_basis = match_basis.casefold()
    if "source_library:" in lowered_basis:
        title_tokens = {
            token
            for token in re.findall(r"[a-z0-9]+", target_key.casefold())
            if len(token) >= 4 and token not in {"source", "catalogue", "catalog"}
        }
        overlap = {token for token in title_tokens if token in lowered_file_name}
        return len(overlap) >= 2
    if "jbrs_ocr_index:" in lowered_basis:
        return "title:" in lowered_basis and "author:" in lowered_basis
    return False

JOURNAL_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"\bjournal of the burma research society\b",
        r"\bjournal of burma research society\b",
        r"\bj\.?\s*b\.?\s*r\.?\s*s\.?\b",
        r"\bj\.?\s*burma\s+res\.?\s+soc\.?\b",
        r"\bburma res\.?\s+soc\.?\b",
        r"\bburma research society\b",
    ]
]
VOLUME_PATTERN = re.compile(r"\b(?:vol(?:ume)?\.?|v\.)\s*([ivxlcdm0-9]+)\b", re.IGNORECASE)
JBRS_VOLUME_PATTERN = re.compile(
    r"\b(?:journal of the burma research society|j\.?\s*b\.?\s*r\.?\s*s\.?)\s*([ivxlcdm0-9]+)(?:\s*[\(\[]\s*([ivxlcdm0-9]+)\s*[\)\]])?",
    re.IGNORECASE,
)
PART_PATTERN = re.compile(r"\b(?:part|pt\.?|issue)\s*([ivxlcdm0-9]+)\b", re.IGNORECASE)
YEAR_PATTERN = re.compile(r"\b(18|19|20)\d{2}\b")
PAGE_RANGE_PATTERN = re.compile(r"\bpp?\.?\s*([0-9]+(?:\s*[-–]\s*[0-9]+)?)", re.IGNORECASE)
TRAILING_PAGE_PATTERN = re.compile(r"\b([0-9]{1,4})(?:\s*[-–]\s*([0-9]{1,4}))?\b")
QUOTED_TITLE_PATTERN = re.compile(r"[\"“']([^\"”']{4,160})[\"”']")
PAGE_MARKER_PATTERN = re.compile(r"\[\[page\s+([0-9]+)\]\]", re.IGNORECASE)

KNOWN_AUTHORS = [
    ("Charles Duroiselle", ["duroiselle", "charles duroiselle"]),
    ("Taw Sein Ko", ["taw sein ko", "tawseinko"]),
    ("Emil Forchhammer", ["forchhammer", "emil forchhammer"]),
    ("U Pe Maung Tin", ["pe maung tin", "pemaungtin", "u pe maung tin"]),
    ("G. H. Luce", ["g. h. luce", "g h luce", "luce"]),
    ("U Tun Nyein", ["tun nyein", "u tun nyein", "tunnyein"]),
    ("U E Maung", ["u e maung", "ue maung", "uemaung"]),
    ("C. O. Blagden", ["blagden", "c. o. blagden", "co blagden"]),
    ("Ba Shin", ["ba shin", "bashin"]),
    ("Than Tun", ["than tun", "thantun"]),
    ("Hla Pe", ["hla pe", "hlape"]),
    ("Htin Aung", ["htin aung", "htinaung"]),
    ("D. G. E. Hall", ["d. g. e. hall", "d g e hall", "hall"]),
    ("J. A. Stewart", ["j. a. stewart", "j a stewart", "stewart"]),
    ("May Oung", ["may oung"]),
]

KEYWORD_MARKERS = [
    "inscription",
    "pagan",
    "pinya",
    "ava",
    "mon",
    "talaing",
    "old burmese",
    "burmese",
    "pali",
    "translation",
    "transliteration",
    "plate",
    "pyu",
    "prome",
]

GENERIC_TITLE_WORDS = {
    "buddhism",
    "burma",
    "burmese",
    "buildings",
    "debt",
    "inscription",
    "inscriptions",
    "myanmar",
    "pagan",
    "plate",
    "prayers",
    "religious",
    "text",
    "translation",
}

LOCAL_FILE_REVIEW_HINTS = {
    "1920-shwegugyiinscription-luce1920-pdf": {"shwegugyi", "1141 a d", "pali text"},
    "1976-anandainscriptions-tinlwin1976-pdf": {"ananda", "translation of the text in p 1", "brick monastery"},
    "1932-burmadebttopagan-luce1932-pdf": {"burma s debt", "myanmar s debt", "lemyethna", "minnanthu"},
    "1917-pyuinscriptions-blagden1917-pdf": {"pyu inscriptions", "pyu", "translations in other languages"},
    "1948-centuryofprogress-luce1948-pdf": {"century of progress", "dhammaceti"},
}

HEADING_TRANSLATION_PATTERN = re.compile(
    r"^(translation(?:\s+of\b.*)?|text\s+and\s+translation|translation\s+and\s+notes|translated\s+text)\s*[:.]?$",
    re.IGNORECASE,
)
TEXT_AND_TRANSLATION_SECTION_PATTERN = re.compile(r"\btext\s+and\s+translation\b", re.IGNORECASE)
CITATION_TO_TRANSLATION_PATTERN = re.compile(
    r"\b(?:see|cf\.?|compare|quoted in)\b.*\btranslation\b.*\bby\b|\btranslation\b.*\bby\b",
    re.IGNORECASE,
)
GENERAL_TRANSLATION_DISCUSSION_PATTERN = re.compile(
    r"\b(?:to be|would be|were to be|planned|project|scheme|should be|for publication)\b.*\btranslation\b|\bfacsimile, notes, transcription and translation\b",
    re.IGNORECASE,
)
TRANSLATION_WORD_PATTERN = re.compile(r"\btranslation(?:s)?\b", re.IGNORECASE)
EDITION_PATTERN = re.compile(r"\b(?:transliteration|text|edition|edited by|edited|facsimile)\b", re.IGNORECASE)
BIBLIOGRAPHY_PATTERN = re.compile(r"\b(?:bibliography|references|shorttitle|journal =|title =|familyid =)\b", re.IGNORECASE)
METADATA_ASSIGNMENT_PATTERN = re.compile(r"^\s*[A-Za-z0-9_]+?\s*=\s*\{.*\}\s*,?\s*$")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_space(value: str | None) -> str:
    return " ".join((value or "").split())


def normalize_for_match(value: str | None) -> str:
    text = normalize_space(value).casefold()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return normalize_space(text)


def slugify(value: str) -> str:
    text = normalize_for_match(value)
    text = text.replace(" ", "-").strip("-")
    return text or "unknown"


def bool_string(value: bool) -> str:
    return "true" if value else "false"


def is_true(value: str) -> bool:
    return value.strip().casefold() == "true"


def normalized_language_scope(value: str) -> str:
    return value.strip().casefold()


def is_pali_only_language_scope(value: str) -> bool:
    normalized = normalized_language_scope(value)
    return "pali" in normalized and "burmese" not in normalized and "mixed" not in normalized


def truncate_short(value: str | None, limit: int = SHORT_SNIPPET_LIMIT) -> str:
    text = normalize_space(value)
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def candidate_lookup_key(row: dict[str, str]) -> str:
    return row.get("candidate_key", "") or row.get("candidate_id", "")


def infer_candidate_page_marker(text: str, evidence_marker: str) -> str:
    current_page_marker = ""
    normalized_marker = normalize_for_match(evidence_marker)
    marker_slug = slugify(evidence_marker)
    for line in text.splitlines():
        stripped = line.strip()
        page_match = PAGE_MARKER_PATTERN.fullmatch(stripped)
        if page_match:
            current_page_marker = f"[[page {page_match.group(1)}]]"
            continue
        if not stripped or not normalized_marker:
            continue
        normalized_line = normalize_for_match(stripped)
        if normalized_marker in normalized_line or normalized_line in normalized_marker:
            return current_page_marker
        if marker_slug and marker_slug in slugify(stripped):
            return current_page_marker
    return current_page_marker if normalized_marker else ""


def build_translation_candidate_key(
    local_file_id: str,
    candidate_type: str,
    evidence_marker: str,
    page_marker: str,
) -> str:
    anchor = page_marker or normalize_for_match(evidence_marker) or candidate_type
    anchor_slug = slugify(anchor)[:48] or "candidate"
    digest = hashlib.sha1(f"{local_file_id}|{candidate_type}|{anchor}".encode("utf-8")).hexdigest()[:12]
    return f"jbrs-candidate-key:{local_file_id}:{candidate_type}:{anchor_slug}:{digest}"


def manual_assessment_conflicts_with_local_file_id(manual_assessment: str, local_file_id: str) -> str:
    lowered = normalize_for_match(manual_assessment)
    if not lowered:
        return ""
    for expected_local_file_id, hints in LOCAL_FILE_REVIEW_HINTS.items():
        if expected_local_file_id == local_file_id:
            continue
        if any(hint in lowered for hint in hints):
            return expected_local_file_id
    return ""


def safe_path_stub(value: str | None, keep_parts: int = 4) -> str:
    raw = normalize_space(value)
    if not raw:
        return ""
    if ":" in raw and raw.split(":", 1)[0].isupper():
        raw = raw.split(":", 1)[1]
    path = raw.replace("\\", "/").strip("/")
    parts = [part for part in path.split("/") if part]
    if not parts:
        return ""
    return "/".join(parts[-keep_parts:])


def is_runtime_source_file(path: Path) -> bool:
    return path.is_file() and not path.name.startswith(".") and not path.name.startswith("._") and path.suffix.casefold() in SOURCE_FILE_EXTENSIONS


def contains_jbrs_marker(value: str | None) -> bool:
    text = value or ""
    return any(pattern.search(text) for pattern in JOURNAL_PATTERNS)


def detect_author(value: str | None) -> str:
    text = normalize_for_match(value)
    for canonical, variants in KNOWN_AUTHORS:
        for variant in variants:
            if normalize_for_match(variant) in text:
                return canonical
    return ""


def extract_keywords(value: str | None) -> str:
    text = normalize_for_match(value)
    found: list[str] = []
    for marker in KEYWORD_MARKERS:
        normalized_marker = normalize_for_match(marker)
        if normalized_marker in text and marker not in found:
            found.append(marker)
    return "; ".join(found[:5])


def parse_reference_bits(value: str | None) -> tuple[str, str, str, str]:
    text = normalize_space(value)
    volume = ""
    issue = ""
    year = ""
    page_range = ""
    jbrs_match = JBRS_VOLUME_PATTERN.search(text)
    if jbrs_match:
        volume = jbrs_match.group(1)
        issue = jbrs_match.group(2) or ""
    if not volume:
        volume_match = VOLUME_PATTERN.search(text)
        if volume_match:
            volume = volume_match.group(1)
    if not issue:
        part_match = PART_PATTERN.search(text)
        if part_match:
            issue = part_match.group(1)
    year_match = YEAR_PATTERN.search(text)
    if year_match:
        year = year_match.group(0)
    if volume and year and volume == year and len(volume) == 4:
        volume = ""
    page_match = PAGE_RANGE_PATTERN.search(text)
    if page_match:
        page_range = page_match.group(1).replace(" ", "").replace("–", "-")
    return volume, issue, year, page_range


def probable_title_from_descriptor(value: str | None) -> str:
    text = normalize_space(value)
    if not text or METADATA_ASSIGNMENT_PATTERN.match(text):
        return ""
    text = Path(text.split("/")[-1]).stem.replace("_", " ")
    text = re.sub(r"[-]+", " ", text)
    text = re.sub(r"\b(?:JBRS|Journal of the Burma Research Society)\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(18|19|20)\d{2}\b", "", text)
    text = re.sub(r"\b(vol(?:ume)?|part|issue|pp?)\b.*$", "", text, flags=re.IGNORECASE)
    text = normalize_space(text)
    if not text or text.casefold() in {"pdf", "djvu"}:
        return ""
    if re.fullmatch(r"[0-9A-Za-z]+", text) and text.upper() == text.upper() and len(text) <= 8:
        return ""
    return truncate_short(text, limit=120)


def detect_title(value: str | None) -> str:
    text = normalize_space(value)
    if not text or ".pdf" in text.casefold() or METADATA_ASSIGNMENT_PATTERN.match(text):
        return ""
    quoted = QUOTED_TITLE_PATTERN.search(text)
    if quoted:
        candidate = quoted.group(1).strip(" ,.;:-")
        if contains_jbrs_marker(candidate):
            return ""
        return truncate_short(candidate, limit=120)
    author = detect_author(text)
    volume, issue, year, page_range = parse_reference_bits(text)
    if author and contains_jbrs_marker(text):
        remainder = re.split(r"\b(?:JBRS|Journal of the Burma Research Society)\b", text, flags=re.IGNORECASE)[0]
        remainder = re.sub(re.escape(author), "", remainder, flags=re.IGNORECASE)
        remainder = re.sub(r"\b(18|19|20)\d{2}\b", "", remainder)
        remainder = re.sub(r"\bpp?\.?\s*[0-9]+(?:[-–][0-9]+)?\b", "", remainder, flags=re.IGNORECASE)
        remainder = remainder.strip(" ,.;:-")
        if remainder:
            return truncate_short(remainder, limit=120)
    if year and page_range and contains_jbrs_marker(text):
        leading = re.split(r"\b(?:JBRS|Journal of the Burma Research Society)\b", text, flags=re.IGNORECASE)[0]
        leading = leading.strip(" ,.;:-")
        if leading and not JOURNAL_PATTERNS[0].search(leading):
            return truncate_short(leading, limit=120)
    if volume or issue or year:
        maybe = probable_title_from_descriptor(text)
        if maybe and maybe.casefold() not in {JOURNAL_TITLE.casefold(), "jbrs"}:
            return maybe
    return ""


def looks_like_person_name(value: str | None) -> bool:
    text = normalize_space(value).strip(" ,.;:/")
    if not text or len(text) > 40 or re.search(r"\d", text):
        return False
    normalized = normalize_for_match(text)
    if not normalized:
        return False
    parts = normalized.split()
    if not 1 <= len(parts) <= 4:
        return False
    if any(part in GENERIC_TITLE_WORDS for part in parts):
        return False
    if parts == ["u"]:
        return False
    return all(part.isalpha() for part in parts)


def clean_article_title_fragment(author: str, title: str) -> str:
    cleaned = normalize_space(title).strip(" ,.;:")
    if not cleaned:
        return ""
    cleaned = re.sub(r"^\s*U\s*,\s*", "", cleaned, flags=re.IGNORECASE)
    if author:
        author_variants = {normalize_for_match(author)}
        surname = normalize_space(author).split()[-1].strip(" ,.;:/")
        if surname:
            author_variants.add(normalize_for_match(surname))
            cleaned = re.sub(rf"^\s*{re.escape(surname)}\s*[,/:-]?\s*", "", cleaned, flags=re.IGNORECASE)
        if normalize_for_match(cleaned) in author_variants:
            return ""
    cleaned = cleaned.strip(" ,.;:/")
    if cleaned.casefold() == "u":
        return ""
    if cleaned.endswith("/") and len(cleaned.rstrip("/").strip()) <= 4:
        return ""
    return truncate_short(cleaned, limit=120)


def normalize_reference_fields(author: str, article_title: str, volume: str, year: str) -> tuple[str, str, str, bool]:
    normalized_author = author
    normalized_title = article_title
    normalized_volume = volume
    changed = False

    if normalized_volume and year and normalized_volume == year and len(normalized_volume) == 4:
        normalized_volume = ""
        changed = True

    if not normalized_author and looks_like_person_name(normalized_title):
        normalized_author = normalized_title.strip(" ,.;:/")
        normalized_title = ""
        changed = True

    cleaned_title = clean_article_title_fragment(normalized_author, normalized_title)
    if cleaned_title != normalized_title:
        normalized_title = cleaned_title
        changed = True

    return normalized_author, normalized_title, normalized_volume, changed


def title_needs_review(value: str | None) -> bool:
    text = normalize_space(value)
    if not text:
        return True
    normalized = normalize_for_match(text)
    if not normalized:
        return True
    if text.endswith("/"):
        return True
    if re.match(r"^u\s*(,.*)?$", normalized):
        return True
    if looks_like_person_name(text):
        return True
    return False


def reference_confidence(author: str, article_title: str, year: str, volume: str, page_range: str) -> str:
    score = 0
    if author:
        score += 2
    if article_title:
        score += 2
    if year:
        score += 1
    if volume:
        score += 1
    if page_range:
        score += 1
    if score >= 5:
        return "high"
    if score >= 3:
        return "medium"
    return "low"


def normalized_reference_key(author: str, year: str, volume: str, issue: str, page_range: str, article_title: str) -> str:
    parts = [
        normalize_for_match(author),
        normalize_for_match(year),
        normalize_for_match(volume),
        normalize_for_match(issue),
        normalize_for_match(page_range),
        normalize_for_match(article_title),
    ]
    return " | ".join(parts)


def classify_reference_kind(source_file: str, raw_line: str) -> str:
    text = normalize_space(raw_line)
    normalized_source = source_file.casefold()
    lowered = text.casefold()
    author = detect_author(text)
    title = detect_title(text)
    volume, issue, year, page_range = parse_reference_bits(text)
    article_like = contains_jbrs_marker(text) and ((author or title) and (year or volume or page_range))
    if article_like:
        return "article_reference"
    if ".pdf" in lowered or "obi_library_root:" in lowered or "data/local/bibliography_sources/" in lowered:
        return "local_file_metadata"
    if "familyid" in lowered or "fam-jbrs" in lowered:
        return "bibliography_family_marker"
    if METADATA_ASSIGNMENT_PATTERN.match(text):
        if re.match(r"^\s*(title|journal|shorttitle)\s*=", text, flags=re.IGNORECASE):
            return "metadata_fragment"
        return "metadata_fragment"
    if "raw reference string" in lowered or "abbreviations such as" in lowered or "series- and periodical-level authorities" in lowered:
        return "metadata_fragment"
    if "periodical" in lowered or "series container" in lowered:
        return "periodical_authority_record"
    if "source_library_manifest" in normalized_source or "local_file_manifest" in normalized_source:
        return "local_file_metadata"
    if contains_jbrs_marker(text) and (author or title or page_range or year or volume):
        return "article_reference"
    if contains_jbrs_marker(text):
        return "unclear"
    return "metadata_fragment"


def iter_reference_source_files() -> list[Path]:
    candidates: list[Path] = []
    explicit_files = [
        REPO_ROOT / "data/working/bibliography/bibtex_authority/source_work_authority.tsv",
        REPO_ROOT / "data/working/bibliography/bibtex_authority/bibliography_authority.bib",
        REPO_ROOT / "data/working/bibliography/bibtex_authority/raw_reference_to_bibtex.tsv",
        REPO_ROOT / "data/working/bibliography/translation_source_discovery_plan.tsv",
        OCR_TEXT_INDEX_PATH,
        REPO_ROOT / "docs/phase2_bibtex_authority.md",
    ]
    for path in explicit_files:
        if path.exists():
            candidates.append(path)
    discovery_dir = REPO_ROOT / "data/working/bibliography/translation_source_discovery"
    if discovery_dir.exists():
        for path in sorted(discovery_dir.rglob("*")):
            if path.is_file() and path.suffix.casefold() in {".tsv", ".md", ".json"}:
                candidates.append(path)
    unique: list[Path] = []
    seen: set[Path] = set()
    for path in candidates:
        if path not in seen and JBRS_DIRECTORY not in path.parents:
            unique.append(path)
            seen.add(path)
    return unique


def is_clean_article_target_row(row: dict[str, str]) -> bool:
    if row.get("reference_kind") not in ARTICLE_REFERENCE_KINDS:
        return False
    source_file = row.get("source_file", "").casefold()
    matched_text = row.get("matched_reference_text_short", "").casefold()
    if source_file.startswith("docs/") or "raw reference string" in matched_text or "abbreviations such as" in matched_text:
        return False
    if ".pdf" in matched_text or "obi_library_root:" in matched_text or "data/local/bibliography_sources/" in matched_text:
        return False
    score = 0
    if row.get("author"):
        score += 1
    if row.get("article_title"):
        score += 2
    if row.get("year"):
        score += 1
    if row.get("volume"):
        score += 1
    if row.get("page_range"):
        score += 2
    return score >= 4 and bool(row.get("year") or row.get("page_range") or row.get("volume"))


def build_reference_hunt_rows() -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    raw_rows: list[dict[str, str]] = []
    raw_index = 0
    for path in iter_reference_source_files():
        relative = str(path.relative_to(REPO_ROOT))
        for line_number, raw_line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
            if not contains_jbrs_marker(raw_line):
                continue
            reference_kind = classify_reference_kind(relative, raw_line)
            volume, issue, year, page_range = parse_reference_bits(raw_line)
            author = detect_author(raw_line) if reference_kind in ARTICLE_REFERENCE_KINDS else ""
            article_title = detect_title(raw_line) if reference_kind in ARTICLE_REFERENCE_KINDS else ""
            raw_index += 1
            raw_rows.append(
                {
                    "reference_id": f"jbrs-ref-{raw_index:04d}",
                    "target_reference_id": "",
                    "source_file": f"{relative}:{line_number}",
                    "source_work_key_if_known": "",
                    "reference_kind": reference_kind,
                    "matched_reference_text_short": truncate_short(raw_line),
                    "normalized_journal_title": JOURNAL_TITLE,
                    "normalized_reference_key": normalized_reference_key(author, year, volume, issue, page_range, article_title),
                    "volume": volume,
                    "issue": issue,
                    "year": year,
                    "page_range": page_range,
                    "author": author,
                    "article_title": article_title,
                    "inscription_or_topic_keywords": extract_keywords(raw_line),
                    "reference_confidence": reference_confidence(author, article_title, year, volume, page_range),
                    "needs_manual_bibliographic_cleanup": bool_string(reference_kind in ARTICLE_REFERENCE_KINDS and not (author or article_title)),
                    "notes": "Raw JBRS repository hit retained for provenance.",
                }
            )

    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in raw_rows:
        if is_clean_article_target_row(row):
            key = row["normalized_reference_key"] or normalized_reference_key(
                row.get("author", ""),
                row.get("year", ""),
                row.get("volume", ""),
                row.get("issue", ""),
                row.get("page_range", ""),
                row.get("article_title", ""),
            )
            grouped[key].append(row)

    target_rows: list[dict[str, str]] = []
    for index, key in enumerate(sorted(grouped), start=1):
        group = grouped[key]
        preferred = max(
            group,
            key=lambda row: (
                row.get("reference_confidence", "") == "high",
                bool(row.get("author", "")),
                bool(row.get("article_title", "")),
                bool(row.get("page_range", "")),
                len(row.get("matched_reference_text_short", "")),
            ),
        )
        author, article_title, volume, auto_corrected = normalize_reference_fields(
            preferred.get("author", ""),
            preferred.get("article_title", ""),
            preferred.get("volume", ""),
            preferred.get("year", ""),
        )
        needs_review = (
            preferred.get("needs_manual_bibliographic_cleanup", "") == "true"
            or not article_title
            or title_needs_review(article_title)
            or auto_corrected
        )
        target_id = f"jbrs-target-{index:04d}"
        for raw_row in group:
            raw_row["target_reference_id"] = target_id
        target_rows.append(
            {
                "target_reference_id": target_id,
                "reference_kind": preferred["reference_kind"],
                "normalized_reference_key": key,
                "source_file_examples": " | ".join(row["source_file"] for row in group[:3]),
                "raw_reference_ids": "|".join(row["reference_id"] for row in group),
                "raw_hit_count": str(len(group)),
                "normalized_journal_title": JOURNAL_TITLE,
                "volume": volume,
                "issue": preferred["issue"],
                "year": preferred["year"],
                "page_range": preferred["page_range"],
                "author": author,
                "article_title": article_title,
                "inscription_or_topic_keywords": preferred["inscription_or_topic_keywords"],
                "reference_confidence": preferred["reference_confidence"],
                "needs_manual_bibliographic_cleanup": bool_string(needs_review),
                "notes": "Deduplicated clean article target built from raw JBRS repository hits."
                + (" Applied cautious parser cleanup before review." if auto_corrected else ""),
            }
        )
    return raw_rows, target_rows


def load_review_rows(path: Path, key_field: str) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    return {row[key_field]: row for row in read_tsv(path) if row.get(key_field)}


def build_article_target_review_rows(
    target_rows: list[dict[str, str]],
    raw_rows: list[dict[str, str]],
    existing_review_rows: dict[str, dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    existing_review_rows = existing_review_rows or {}
    raw_by_id = {row.get("reference_id", ""): row for row in raw_rows if row.get("reference_id")}
    review_rows: list[dict[str, str]] = []
    for row in target_rows:
        raw_ids = [part for part in row.get("raw_reference_ids", "").split("|") if part]
        evidence_row = raw_by_id.get(raw_ids[0], {}) if raw_ids else {}
        current_author = row.get("author", "")
        current_title = row.get("article_title", "")
        current_volume = row.get("volume", "")
        current_issue = row.get("issue", "")
        current_year = row.get("year", "")
        current_page_range = row.get("page_range", "")

        corrected_author, corrected_title, corrected_volume, auto_corrected = normalize_reference_fields(
            current_author,
            current_title,
            current_volume,
            current_year,
        )
        review_status = "accepted"
        notes: list[str] = []
        if auto_corrected:
            review_status = "corrected"
            notes.append("Applied cautious parser cleanup to author/title/volume fields.")
        if title_needs_review(corrected_title):
            review_status = "parser_artifact" if not corrected_title else "needs_manual_bibliographic_review"
            notes.append("Article title remains malformed or incomplete after cautious cleanup.")
        elif not (corrected_author and current_year and current_page_range):
            review_status = "needs_manual_bibliographic_review"
            notes.append("Target still lacks enough author/year/page evidence for automatic matching.")
        elif row.get("needs_manual_bibliographic_cleanup", "") == "true" and review_status == "accepted":
            review_status = "accepted"

        generated = {
            "target_reference_id": row.get("target_reference_id", ""),
            "current_author": current_author,
            "current_article_title": current_title,
            "current_volume": current_volume,
            "current_issue": current_issue,
            "current_year": current_year,
            "current_page_range": current_page_range,
            "review_status": review_status,
            "corrected_author": corrected_author,
            "corrected_article_title": corrected_title,
            "corrected_volume": corrected_volume,
            "corrected_issue": current_issue,
            "corrected_year": current_year,
            "corrected_page_range": current_page_range,
            "source_evidence_short": evidence_row.get("matched_reference_text_short", ""),
            "notes": " ".join(notes) or "Auto-generated review state for clean article targets.",
        }
        existing = existing_review_rows.get(generated["target_reference_id"], {})
        preserve_existing = bool(
            existing
            and (
                existing.get("review_status") in {"accepted", "corrected", "duplicate_or_alias"}
                or any(
                    existing.get(field) and existing.get(field) != generated.get(field, "")
                    for field in [
                        "corrected_author",
                        "corrected_article_title",
                        "corrected_volume",
                        "corrected_issue",
                        "corrected_year",
                        "corrected_page_range",
                    ]
                )
            )
        )
        if preserve_existing:
            for key in generated:
                if key.startswith("current_") or key == "source_evidence_short":
                    continue
                if existing.get(key):
                    generated[key] = existing[key]
        review_rows.append(generated)
    return review_rows


def apply_article_target_reviews(
    target_rows: list[dict[str, str]],
    review_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    review_by_id = {row.get("target_reference_id", ""): row for row in review_rows if row.get("target_reference_id")}
    reviewed_rows: list[dict[str, str]] = []
    for row in target_rows:
        reviewed = row.copy()
        review = review_by_id.get(row.get("target_reference_id", ""), {})
        reviewed["target_review_status"] = review.get("review_status", "accepted")
        if reviewed["target_review_status"] in ACCEPTED_TARGET_REVIEW_STATUSES:
            reviewed["author"] = review.get("corrected_author", reviewed.get("author", "")) or reviewed.get("author", "")
            reviewed["article_title"] = review.get("corrected_article_title", reviewed.get("article_title", ""))
            reviewed["volume"] = review.get("corrected_volume", reviewed.get("volume", ""))
            reviewed["issue"] = review.get("corrected_issue", reviewed.get("issue", ""))
            reviewed["year"] = review.get("corrected_year", reviewed.get("year", ""))
            reviewed["page_range"] = review.get("corrected_page_range", reviewed.get("page_range", ""))
        reviewed_rows.append(reviewed)
    return reviewed_rows


def build_translation_candidate_review_rows(
    candidate_rows: list[dict[str, str]],
    existing_review_rows: dict[str, dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    existing_review_rows = existing_review_rows or {}
    review_rows: list[dict[str, str]] = []
    for row in candidate_rows:
        candidate_type = row.get("candidate_type", "")
        generated = {
            "candidate_id": row.get("candidate_id", ""),
            "candidate_key": row.get("candidate_key", ""),
            "local_file_id": row.get("local_file_id", ""),
            "candidate_type": candidate_type,
            "review_status": "needs_manual_review",
            "reviewed_by_or_method": "auto_triage",
            "manual_assessment": "Heuristic lead only; inspect the source manually before promoting this as translation-bearing content.",
            "is_actual_translation_section": "",
            "is_inscription_translation": "",
            "is_general_discussion": "true" if candidate_type == "planned_or_general_translation_discussion" else "",
            "is_citation_to_external_translation": "true" if candidate_type == "citation_to_someone_else_translation" else "",
            "next_action": "Inspect the local source manually before treating this as an actual inscription translation.",
            "notes": "Auto-generated review row; no candidate is promoted to verified translation coverage without human review.",
        }
        existing = existing_review_rows.get(generated["candidate_key"], {})
        for key in generated:
            if key in {"candidate_id", "candidate_key", "local_file_id", "candidate_type"}:
                continue
            if existing.get(key):
                generated[key] = existing[key]
        review_rows.append(generated)
    return review_rows


def split_manifest_paths(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in str(value).split("|") if part.strip()]


def choose_best_descriptor(values: Iterable[str]) -> str:
    best = ""
    best_score = -1
    for value in values:
        text = normalize_space(value)
        if not text:
            continue
        score = len(re.findall(r"[A-Za-z]", text))
        if contains_jbrs_marker(text):
            score += 15
        if YEAR_PATTERN.search(text):
            score += 3
        if detect_author(text):
            score += 4
        if score > best_score:
            best = text
            best_score = score
    return best


def probable_volume_issue_from_text(value: str | None) -> str:
    volume, issue, _year, _pages = parse_reference_bits(value)
    parts = [part for part in [f"vol. {volume}" if volume else "", f"issue/part {issue}" if issue else ""] if part]
    return " | ".join(parts)


def infer_year_from_text(value: str | None) -> str:
    match = YEAR_PATTERN.search(value or "")
    return match.group(0) if match else ""


def infer_article_pages_from_filename(file_name: str) -> tuple[str, str]:
    stem = Path(file_name).stem
    numeric_match = re.fullmatch(r"([0-9]{5,6})([A-Za-z]?)", stem)
    if numeric_match:
        page = numeric_match.group(1)[-3:].lstrip("0") or "0"
        return page, ""
    range_match = re.search(r"([0-9]{1,4})[-_]+([0-9]{1,4})", stem)
    if range_match:
        return range_match.group(1).lstrip("0") or "0", range_match.group(2).lstrip("0") or "0"
    return "", ""


def is_whole_issue_or_volume_hint(text: str) -> bool:
    lowered = normalize_for_match(text)
    return any(token in lowered for token in ["whole volume", "whole issue", "journal of the burma research society", " volume ", " vol ", " part ", " issue ", " complete run"])


def resolve_existing_local_path(path_text: str | None) -> str:
    raw = normalize_space(path_text)
    if not raw:
        return ""
    if ":" in raw and raw.split(":", 1)[0].isupper():
        return ""
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = REPO_ROOT / raw
    if candidate.exists():
        return str(candidate.resolve())
    return ""


def _manifest_confidence_rank(value: str) -> int:
    return {"low": 0, "medium": 1, "high": 2}.get((value or "").casefold(), -1)


def merge_manifest_rows(existing: dict[str, str], incoming: dict[str, str]) -> dict[str, str]:
    merged = existing.copy()
    for key, value in incoming.items():
        if not value:
            continue
        current = merged.get(key, "")
        if not current:
            merged[key] = value
            continue
        if key == "manifest_confidence":
            if _manifest_confidence_rank(value) > _manifest_confidence_rank(current):
                merged[key] = value
        elif key in {"runtime_path_available", "is_article_split_pdf", "is_whole_issue_or_volume"}:
            if current == "false" and value == "true":
                merged[key] = value
        elif key == "needs_manual_review":
            if current == "true" and value == "false":
                merged[key] = value
        elif key in {"file_name", "probable_title_from_filename", "probable_author_from_path", "folder_context", "notes", "ocr_priority_reason"}:
            if len(value) > len(current):
                merged[key] = value
        elif key == "path_stub_or_redacted_path":
            if len(value.split("/")) > len(current.split("/")):
                merged[key] = value
    return merged


def upsert_manifest_row(manifest_by_id: dict[str, dict[str, str]], row: dict[str, str]) -> None:
    local_file_id = row.get("local_file_id", "")
    if not local_file_id:
        return
    existing = manifest_by_id.get(local_file_id)
    manifest_by_id[local_file_id] = merge_manifest_rows(existing, row) if existing else row


def build_manifest_row(
    *,
    local_file_id: str,
    descriptor: str,
    path_stub_source: str,
    file_name: str,
    file_size: str,
    folder_context: str,
    manifest_confidence: str,
    notes: str,
    runtime_available: bool,
) -> dict[str, str]:
    probable_year_filename = infer_year_from_text(file_name)
    probable_year_folder = infer_year_from_text(folder_context or descriptor)
    probable_start_page, probable_end_page = infer_article_pages_from_filename(file_name)
    probable_title = probable_title_from_descriptor(descriptor) or probable_title_from_descriptor(file_name)
    probable_author = detect_author(" ".join([descriptor, folder_context, file_name]))
    whole_issue_or_volume = is_whole_issue_or_volume_hint(" ".join([descriptor, folder_context, file_name]))
    is_article_split = bool(probable_start_page) and not whole_issue_or_volume
    priority_reason = "Generic probable JBRS file; OCR priority remains low until a target or author clue is confirmed."
    if probable_author:
        priority_reason = f"Known JBRS-related author hint in path metadata: {probable_author}."
    elif probable_title:
        priority_reason = "Descriptive title metadata exists and may support later article matching."
    return {
        "local_file_id": local_file_id,
        "path_stub_or_redacted_path": safe_path_stub(path_stub_source),
        "file_name": file_name,
        "extension": Path(file_name).suffix.casefold().lstrip("."),
        "file_size_bytes": file_size,
        "modified_date": "",
        "probable_author_from_path": probable_author,
        "probable_title_from_filename": probable_title,
        "probable_year_from_filename": probable_year_filename,
        "probable_year_from_folder": probable_year_folder,
        "probable_volume_issue_from_filename": probable_volume_issue_from_text(descriptor),
        "probable_article_start_page_from_filename": probable_start_page,
        "probable_article_end_page_from_filename": probable_end_page,
        "folder_context": truncate_short(folder_context, limit=120),
        "is_probable_jbrs": "true",
        "is_article_split_pdf": bool_string(is_article_split),
        "is_whole_issue_or_volume": bool_string(whole_issue_or_volume),
        "runtime_path_available": bool_string(runtime_available),
        "manifest_confidence": manifest_confidence,
        "ocr_priority_reason": priority_reason,
        "needs_manual_review": bool_string(not probable_title and not probable_author),
        "notes": notes,
    }


def build_local_manifest_rows(
    *,
    roots: list[Path] | None = None,
    existing_source_library_path: Path = SOURCE_LIBRARY_MANIFEST_PATH,
    existing_local_manifest_path: Path = LOCAL_FILE_MANIFEST_PATH,
    existing_ocr_manifest_path: Path = OCR_MANIFEST_PATH,
    mark_runtime_available: bool = False,
) -> tuple[list[dict[str, str]], dict[str, str]]:
    manifest_by_id: dict[str, dict[str, str]] = {}
    runtime_path_cache: dict[str, str] = {}
    seen_runtime_paths: set[str] = set()

    if existing_source_library_path.exists():
        for row in read_tsv(existing_source_library_path):
            descriptor_candidates = split_manifest_paths(row.get("all_original_paths", "")) + [row.get("original_path", ""), row.get("file_name", "")]
            descriptor = choose_best_descriptor(descriptor_candidates)
            path_text = " ".join(descriptor_candidates + [row.get("candidate_label", "")])
            if not contains_jbrs_marker(path_text):
                continue
            local_file_id = row.get("work_candidate_id", "") or slugify(descriptor or row.get("file_name", ""))
            runtime_path = resolve_existing_local_path(row.get("copied_path", ""))
            if runtime_path:
                runtime_path_cache[local_file_id] = runtime_path
                seen_runtime_paths.add(runtime_path)
            upsert_manifest_row(
                manifest_by_id,
                build_manifest_row(
                    local_file_id=local_file_id,
                    descriptor=descriptor or row.get("file_name", ""),
                    path_stub_source=row.get("original_path", "") or row.get("copied_path", ""),
                    file_name=row.get("file_name", ""),
                    file_size=row.get("file_size", ""),
                    folder_context=row.get("candidate_label", ""),
                    manifest_confidence="high",
                    notes="Derived from existing redacted source_library_manifest.tsv entry.",
                    runtime_available=mark_runtime_available and bool(runtime_path),
                ),
            )

    if existing_local_manifest_path.exists():
        for row in read_tsv(existing_local_manifest_path):
            source_text = " ".join([row.get("file_name", ""), row.get("primary_original_path", ""), row.get("all_original_paths", ""), row.get("copied_path", ""), row.get("source_folder_hints", "")])
            if not contains_jbrs_marker(source_text):
                continue
            local_file_id = row.get("canonical_local_file_id", "") or slugify(row.get("file_name", "") or row.get("copied_path", "") or row.get("primary_original_path", ""))
            runtime_path = resolve_existing_local_path(row.get("copied_path", ""))
            if runtime_path:
                runtime_path_cache[local_file_id] = runtime_path
                seen_runtime_paths.add(runtime_path)
            descriptor = choose_best_descriptor(
                [row.get("primary_original_path", ""), row.get("all_original_paths", ""), row.get("copied_path", ""), row.get("file_name", "")]
            )
            upsert_manifest_row(
                manifest_by_id,
                build_manifest_row(
                    local_file_id=local_file_id,
                    descriptor=descriptor,
                    path_stub_source=row.get("primary_original_path", "") or row.get("copied_path", ""),
                    file_name=row.get("file_name", ""),
                    file_size=row.get("file_size", ""),
                    folder_context=row.get("source_folder_hints", "") or "local_file_manifest supplement",
                    manifest_confidence="medium",
                    notes="Supplemented from existing redacted local_file_manifest.tsv entry.",
                    runtime_available=mark_runtime_available and bool(runtime_path),
                ),
            )

    if existing_ocr_manifest_path.exists():
        for row in read_tsv(existing_ocr_manifest_path):
            source_text = " ".join([row.get("source_file_label", ""), row.get("source_path", "")])
            if not contains_jbrs_marker(source_text):
                continue
            local_file_id = row.get("source_file_id", "") or slugify(row.get("source_file_label", "") or row.get("source_path", ""))
            runtime_path = resolve_existing_local_path(row.get("source_path", ""))
            if runtime_path:
                runtime_path_cache[local_file_id] = runtime_path
                seen_runtime_paths.add(runtime_path)
            descriptor = row.get("source_file_label", "") or row.get("source_path", "")
            upsert_manifest_row(
                manifest_by_id,
                build_manifest_row(
                    local_file_id=local_file_id,
                    descriptor=descriptor,
                    path_stub_source=row.get("source_path", ""),
                    file_name=Path(row.get("source_path", "")).name or row.get("source_file_label", ""),
                    file_size="",
                    folder_context="existing OCR manifest",
                    manifest_confidence="medium",
                    notes="Supplemented from existing OCR manifest metadata.",
                    runtime_available=mark_runtime_available and bool(runtime_path),
                ),
            )

    for root in roots or []:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if not is_runtime_source_file(path):
                continue
            resolved_path = str(path.resolve())
            if resolved_path in seen_runtime_paths:
                continue
            descriptor = str(path.relative_to(root))
            search_text = f"{root.name} {descriptor}"
            if not contains_jbrs_marker(search_text):
                continue
            local_file_id = slugify(str(path.relative_to(root)))
            runtime_path_cache[local_file_id] = resolved_path
            seen_runtime_paths.add(resolved_path)
            stat = path.stat()
            upsert_manifest_row(
                manifest_by_id,
                build_manifest_row(
                    local_file_id=local_file_id,
                    descriptor=descriptor,
                    path_stub_source=descriptor,
                    file_name=path.name,
                    file_size=str(stat.st_size),
                    folder_context=str(path.parent.relative_to(root)),
                    manifest_confidence="high",
                    notes="Scanned from an explicit JBRS root and written without storing the absolute path.",
                    runtime_available=mark_runtime_available,
                ),
            )

    rows = [manifest_by_id[key] for key in sorted(manifest_by_id)]
    return rows, {key: runtime_path_cache[key] for key in sorted(runtime_path_cache)}


def write_runtime_path_cache(path: Path, runtime_path_cache: dict[str, str]) -> None:
    ensure_parent(path)
    path.write_text(json.dumps(runtime_path_cache, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_runtime_path_cache(path: Path = DEFAULT_RUNTIME_PATH_CACHE) -> dict[str, str]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def match_row_for_reference(reference_row: dict[str, str], manifest_row: dict[str, str]) -> tuple[int, dict[str, str]]:
    score = 0
    author_match = "false"
    title_match = "false"
    year_match = "false"
    volume_issue_match = "false"
    path_context_match = "false"
    basis: list[str] = []

    ref_author = reference_row.get("author", "")
    manifest_author = manifest_row.get("probable_author_from_path", "")
    if ref_author and manifest_author and ref_author == manifest_author:
        score += 4
        author_match = "true"
        basis.append("author")

    ref_title = normalize_for_match(reference_row.get("article_title", ""))
    manifest_title = normalize_for_match(manifest_row.get("probable_title_from_filename", ""))
    if ref_title and manifest_title and (ref_title in manifest_title or manifest_title in ref_title):
        score += 5
        title_match = "true"
        basis.append("title")

    ref_year = reference_row.get("year", "")
    if ref_year and ref_year in {manifest_row.get("probable_year_from_filename", ""), manifest_row.get("probable_year_from_folder", "")}:
        score += 2
        year_match = "true"
        basis.append("year")

    ref_volume_issue = normalize_for_match(" ".join([reference_row.get("volume", ""), reference_row.get("issue", "")]))
    manifest_volume_issue = normalize_for_match(manifest_row.get("probable_volume_issue_from_filename", ""))
    if ref_volume_issue and manifest_volume_issue and ref_volume_issue in manifest_volume_issue:
        score += 2
        volume_issue_match = "true"
        basis.append("volume/issue")

    ref_page_range = reference_row.get("page_range", "")
    manifest_page_start = manifest_row.get("probable_article_start_page_from_filename", "")
    if ref_page_range and manifest_page_start:
        start_page = ref_page_range.split("-", 1)[0]
        if start_page == manifest_page_start:
            score += 2
            path_context_match = "true"
            basis.append("start-page")

    topic_keywords = normalize_for_match(reference_row.get("inscription_or_topic_keywords", ""))
    folder_context = normalize_for_match(manifest_row.get("folder_context", ""))
    if topic_keywords and any(keyword in folder_context for keyword in topic_keywords.split()):
        score += 1
        path_context_match = "true"
        basis.append("folder-context")

    detail = {
        "author_match": author_match,
        "title_match": title_match,
        "year_match": year_match,
        "volume_issue_match": volume_issue_match,
        "path_context_match": path_context_match,
        "match_basis": ", ".join(basis),
    }
    return score, detail


def build_reference_file_match_rows(reference_rows: list[dict[str, str]], manifest_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for reference_row in reference_rows:
        review_status = reference_row.get("target_review_status", "accepted")
        if review_status in SKIPPED_TARGET_REVIEW_STATUSES:
            rows.append(
                {
                    "reference_id": reference_row["target_reference_id"],
                    "target_review_status": review_status,
                    "local_file_id": "",
                    "match_status": "false_positive",
                    "match_confidence": "low",
                    "match_basis": "",
                    "author_match": "false",
                    "title_match": "false",
                    "year_match": "false",
                    "volume_issue_match": "false",
                    "path_context_match": "false",
                    "candidate_file_name": "",
                    "candidate_path_stub": "",
                    "next_action": "Exclude this parser artifact or alias from automatic JBRS matching.",
                    "notes": "Parser-artifact or alias targets are retained for review provenance but do not feed automatic matching.",
                }
            )
            continue
        scored: list[tuple[int, dict[str, str], dict[str, str]]] = []
        for manifest_row in manifest_rows:
            score, detail = match_row_for_reference(reference_row, manifest_row)
            if score > 0:
                scored.append((score, manifest_row, detail))
        scored.sort(key=lambda item: (-item[0], item[1].get("local_file_id", "")))
        if not scored or review_status in MANUAL_TARGET_REVIEW_STATUSES:
            best_manifest = scored[0][1] if scored else {}
            detail = scored[0][2] if scored else {
                "author_match": "false",
                "title_match": "false",
                "year_match": "false",
                "volume_issue_match": "false",
                "path_context_match": "false",
                "match_basis": "",
            }
            rows.append(
                {
                    "reference_id": reference_row["target_reference_id"],
                    "target_review_status": review_status,
                    "local_file_id": best_manifest.get("local_file_id", ""),
                    "match_status": "needs_manual_review" if review_status in MANUAL_TARGET_REVIEW_STATUSES else "no_local_candidate_found",
                    "match_confidence": "low",
                    "match_basis": detail["match_basis"],
                    "author_match": detail["author_match"],
                    "title_match": detail["title_match"],
                    "year_match": detail["year_match"],
                    "volume_issue_match": detail["volume_issue_match"],
                    "path_context_match": detail["path_context_match"],
                    "candidate_file_name": best_manifest.get("file_name", ""),
                    "candidate_path_stub": best_manifest.get("path_stub_or_redacted_path", ""),
                    "next_action": "Review and clean the bibliographic target manually before using any candidate file for OCR."
                    if review_status in MANUAL_TARGET_REVIEW_STATUSES
                    else "Search additional local JBRS roots or inspect author/year folders manually.",
                    "notes": "Unresolved targets are retained as low-confidence review leads only."
                    if review_status in MANUAL_TARGET_REVIEW_STATUSES
                    else "No local candidate met the article-target matching threshold.",
                }
            )
            continue
        best_score, best_manifest, detail = scored[0]
        if len(scored) > 1 and scored[1][0] == best_score:
            match_status = "multiple_candidates"
            match_confidence = "medium"
            next_action = "Review multiple candidate local files before OCR."
        elif best_score >= 8:
            match_status = "exact_or_near_exact_match"
            match_confidence = "high"
            next_action = "Use this file for OCR or manual content review."
        else:
            match_status = "plausible_match"
            match_confidence = "medium"
            next_action = "Confirm article/file alignment before OCR."
        rows.append(
            {
                "reference_id": reference_row["target_reference_id"],
                "target_review_status": review_status,
                "local_file_id": best_manifest["local_file_id"],
                "match_status": match_status,
                "match_confidence": match_confidence,
                "match_basis": detail["match_basis"],
                "author_match": detail["author_match"],
                "title_match": detail["title_match"],
                "year_match": detail["year_match"],
                "volume_issue_match": detail["volume_issue_match"],
                "path_context_match": detail["path_context_match"],
                "candidate_file_name": best_manifest.get("file_name", ""),
                "candidate_path_stub": best_manifest.get("path_stub_or_redacted_path", ""),
                "next_action": next_action,
                "notes": "Matches are computed only against clean article targets, not raw metadata fragments.",
            }
        )
    return rows


def output_basename_for_manifest_row(row: dict[str, str]) -> str:
    local_file_id = row.get("local_file_id", "")
    if local_file_id:
        return slugify(local_file_id)[:120]
    preferred = row.get("probable_title_from_filename", "") or Path(row.get("file_name", "")).stem
    return slugify(preferred)[:120]


def estimate_page_count(row: dict[str, str]) -> str:
    if row.get("probable_article_start_page_from_filename") and row.get("probable_article_end_page_from_filename"):
        start = int(row["probable_article_start_page_from_filename"])
        end = int(row["probable_article_end_page_from_filename"])
        if end >= start:
            return str(end - start + 1)
    return ""


def compact_ocr_priority_reason(value: str) -> str:
    mapping = {
        "Matched an accepted or corrected JBRS article target with exact or near-exact local evidence.": "accepted_target_match",
        "Linked to a reviewed or still-unresolved article target; confirm the file manually before OCR.": "reviewed_target_match",
        "Has author/title metadata that makes targeted OCR more useful than generic bulk OCR.": "metadata_clue",
        "Existing text evidence already suggests a translation-bearing section.": "existing_translation_signal",
        "Generic probable JBRS file; OCR priority remains low until a target or author clue is confirmed.": "generic_probable_jbrs",
    }
    return mapping.get(value, value)


def build_ocr_batch_plan_rows(
    manifest_rows: list[dict[str, str]],
    match_rows: list[dict[str, str]],
    runtime_path_cache: dict[str, str] | None = None,
    candidate_rows: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    runtime_path_cache = runtime_path_cache or {}
    candidate_rows = candidate_rows or []
    match_by_local_file: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in match_rows:
        if row.get("local_file_id"):
            match_by_local_file[row["local_file_id"]].append(row)
    candidate_by_local_file: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in candidate_rows:
        if row.get("local_file_id"):
            candidate_by_local_file[row["local_file_id"]].append(row)

    rows: list[dict[str, str]] = []
    for manifest_row in manifest_rows:
        local_file_id = manifest_row["local_file_id"]
        runtime_available = manifest_row.get("runtime_path_available", "false") == "true" or local_file_id in runtime_path_cache
        output_basename = output_basename_for_manifest_row(manifest_row)
        matches = match_by_local_file.get(local_file_id, [])
        candidates = candidate_by_local_file.get(local_file_id, [])
        existing_text = any(candidate.get("notes", "").startswith("Derived from existing OCR text") for candidate in candidates)
        match_statuses = {row.get("match_status", "") for row in matches}

        priority = "low"
        priority_reason = compact_ocr_priority_reason(manifest_row.get("ocr_priority_reason", "")) or "generic_probable_jbrs"
        if matches and match_statuses & HIGH_PRIORITY_MATCH_STATUSES:
            priority = "high"
            priority_reason = "accepted_target_match"
        elif matches:
            priority = "medium"
            priority_reason = "reviewed_target_match"
        elif manifest_row.get("probable_author_from_path", "") or manifest_row.get("probable_title_from_filename", ""):
            priority = "medium"
            priority_reason = "metadata_clue"
        if any(candidate.get("candidate_type") in {"explicit_translation_heading", "text_and_translation_section"} for candidate in candidates):
            priority = "high"
            priority_reason = "existing_translation_signal"

        if existing_text:
            status = "already_text_available"
            blocked_by = ""
            ocr_engine = "existing_pdf_text"
        elif not runtime_available:
            status = "needs_runtime_path_cache"
            blocked_by = "write_runtime_path_cache"
            ocr_engine = "google_vision"
        else:
            status = "ready_for_ocr"
            blocked_by = ""
            ocr_engine = "google_vision"

        ocr_scope = "whole_volume" if manifest_row.get("is_whole_issue_or_volume") == "true" else "article_pages_only"
        rows.append(
            {
                "batch_id": f"jbrs-ocr-{len(rows) + 1:04d}",
                "local_file_id": local_file_id,
                "file_name": manifest_row.get("file_name", ""),
                "path_stub": manifest_row.get("path_stub_or_redacted_path", ""),
                "volume": "",
                "issue": "",
                "year": manifest_row.get("probable_year_from_filename", "") or manifest_row.get("probable_year_from_folder", ""),
                "page_count_estimate": estimate_page_count(manifest_row),
                "runtime_path_available": bool_string(runtime_available),
                "ocr_priority": priority,
                "ocr_priority_reason": priority_reason,
                "ocr_scope": ocr_scope,
                "ocr_engine": ocr_engine,
                "output_basename": output_basename,
                "expected_output_format": "vision_json|page_text|article_text|sidecar",
                "metadata_sidecar_path": f"data_local/ocr/jbrs/manifest/{output_basename}.json",
                "status": status,
                "blocked_by": blocked_by,
                "notes": "",
            }
        )
    return rows


def effective_ocr_status(batch_row: dict[str, str], status_row: dict[str, str] | None = None) -> str:
    status_value = (status_row or {}).get("status", "").strip()
    if status_value:
        return status_value
    return batch_row.get("status", "").strip()


def ocr_selection_skip_reason(
    batch_row: dict[str, str],
    status_row: dict[str, str] | None = None,
    *,
    rerun_failed: bool = False,
    force_rerun_completed: bool = False,
) -> str:
    batch_id = batch_row.get("batch_id", "")
    batch_status = batch_row.get("status", "").strip()
    effective_status = effective_ocr_status(batch_row, status_row)
    if batch_status != "ready_for_ocr":
        return (
            f"Skipped {batch_id} because the batch plan status is {batch_status or 'blank'}, "
            "not ready_for_ocr."
        )
    if effective_status == "completed" and not force_rerun_completed:
        return (
            f"Skipped {batch_id} because the status log marks it completed; "
            "use --force-rerun-completed to override."
        )
    if effective_status == "failed" and not rerun_failed:
        return (
            f"Skipped {batch_id} because the status log marks it failed; "
            "use --rerun-failed to retry."
        )
    if effective_status == "submitted":
        return f"Skipped {batch_id} because the status log still marks it submitted."
    if effective_status not in {"ready_for_ocr", "dry_run_ok", "failed", "completed"}:
        return f"Skipped {batch_id} because the status log status {effective_status or 'blank'} is not selectable."
    return ""


def batch_is_selectable_for_ocr(
    batch_row: dict[str, str],
    status_row: dict[str, str] | None = None,
    *,
    rerun_failed: bool = False,
    force_rerun_completed: bool = False,
) -> bool:
    return not ocr_selection_skip_reason(
        batch_row,
        status_row,
        rerun_failed=rerun_failed,
        force_rerun_completed=force_rerun_completed,
    )


def build_ocr_status_log_rows(
    batch_rows: list[dict[str, str]],
    existing_rows: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    created_at = now_iso()
    existing_by_batch_id = {row.get("batch_id", ""): row for row in (existing_rows or [])}
    for batch_row in batch_rows:
        existing_row = existing_by_batch_id.get(batch_row["batch_id"])
        status = batch_row.get("status", "")
        pages_submitted = ""
        pages_completed = batch_row.get("page_count_estimate", "") if status == "already_text_available" else ""
        output_path_stub = ""
        metadata_sidecar_stub = ""
        error_type = ""
        error_message_short = ""
        notes = ""
        row_created_at = created_at
        row_updated_at = created_at
        if existing_row:
            row_created_at = existing_row.get("created_at", created_at)
            if existing_row.get("status", "") in TERMINAL_OCR_STATUS_VALUES:
                status = existing_row.get("status", status)
                pages_submitted = existing_row.get("pages_submitted", "")
                pages_completed = existing_row.get("pages_completed", "")
                output_path_stub = existing_row.get("output_path_stub", "")
                metadata_sidecar_stub = existing_row.get("metadata_sidecar_stub", "")
                error_type = existing_row.get("error_type", "")
                error_message_short = existing_row.get("error_message_short", "")
                notes = existing_row.get("notes", "")
                row_updated_at = existing_row.get("updated_at", created_at)
        rows.append(
            {
                "ocr_job_id": existing_row.get("ocr_job_id", f"{batch_row['batch_id']}-status") if existing_row else f"{batch_row['batch_id']}-status",
                "batch_id": batch_row["batch_id"],
                "local_file_id": batch_row["local_file_id"],
                "file_name": batch_row["file_name"],
                "ocr_engine": batch_row["ocr_engine"],
                "ocr_scope": batch_row["ocr_scope"],
                "status": status,
                "pages_submitted": pages_submitted,
                "pages_completed": pages_completed,
                "output_path_stub": output_path_stub,
                "metadata_sidecar_stub": metadata_sidecar_stub,
                "error_type": error_type,
                "error_message_short": error_message_short,
                "created_at": row_created_at,
                "updated_at": row_updated_at,
                "notes": notes,
            }
        )
    return rows


def best_text_source_for_file(local_file_id: str, status_rows: list[dict[str, str]]) -> Path | None:
    for row in status_rows:
        if row.get("local_file_id") != local_file_id:
            continue
        output_stub = row.get("output_path_stub", "")
        if not output_stub:
            continue
        path = REPO_ROOT / output_stub
        if path.exists():
            return path
    candidates = [
        REPO_ROOT / "data/local/ocr_text" / f"{local_file_id}.txt",
        DEFAULT_LOCAL_OUTPUT_ROOT / "article_text" / f"{local_file_id}.txt",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _extract_evidence(text: str, pattern: re.Pattern[str]) -> tuple[str, str]:
    for line in text.splitlines():
        stripped = line.strip()
        if pattern.search(stripped):
            return truncate_short(stripped, limit=80), truncate_short(stripped)
    return "", ""


def classify_translation_candidate(text: str) -> tuple[str, str, str, str, str, str, str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines:
        if HEADING_TRANSLATION_PATTERN.match(line) and len(line) <= 120:
            return (
                "explicit_translation_heading",
                truncate_short(line, limit=80),
                truncate_short(line),
                "true",
                "false",
                "false",
                "high",
            )
    for index, line in enumerate(lines):
        if TEXT_AND_TRANSLATION_SECTION_PATTERN.search(line):
            return (
                "text_and_translation_section",
                truncate_short(line, limit=80),
                truncate_short(line),
                "true",
                "true",
                "false",
                "medium",
            )
        if normalize_for_match(line) == "text" and index + 1 < len(lines) and normalize_for_match(lines[index + 1]).startswith("translation"):
            snippet = f"{line} / {lines[index + 1]}"
            return ("text_and_translation_section", truncate_short(snippet, limit=80), truncate_short(snippet), "true", "true", "false", "medium")

    marker, snippet = _extract_evidence(text, CITATION_TO_TRANSLATION_PATTERN)
    if marker:
        return ("citation_to_someone_else_translation", marker, snippet, "true", "false", "true", "low")

    marker, snippet = _extract_evidence(text, GENERAL_TRANSLATION_DISCUSSION_PATTERN)
    if marker:
        return ("planned_or_general_translation_discussion", marker, snippet, "false", "false", "true", "low")

    marker, snippet = _extract_evidence(text, TRANSLATION_WORD_PATTERN)
    if marker:
        return ("translation_word_hit", marker, snippet, "true", "false", "true", "low")

    marker, snippet = _extract_evidence(text, EDITION_PATTERN)
    if marker:
        return ("edition_or_transliteration_only", marker, snippet, "false", "true", "false", "low")

    marker, snippet = _extract_evidence(text, BIBLIOGRAPHY_PATTERN)
    if marker:
        return ("bibliography_only", marker, snippet, "false", "false", "true", "low")

    return ("unclear_needs_manual_review", "", "", "false", "false", "false", "low")


def build_translation_candidate_rows(
    reference_rows: list[dict[str, str]],
    manifest_rows: list[dict[str, str]],
    match_rows: list[dict[str, str]],
    status_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    match_by_local_file = {row.get("local_file_id", ""): row for row in match_rows if row.get("local_file_id")}
    reference_by_id = {row.get("target_reference_id", ""): row for row in reference_rows if row.get("target_reference_id")}
    rows: list[dict[str, str]] = []
    for manifest_row in manifest_rows:
        local_file_id = manifest_row["local_file_id"]
        text_path = best_text_source_for_file(local_file_id, status_rows)
        if not text_path:
            continue
        text = text_path.read_text(encoding="utf-8", errors="ignore")
        candidate_type, evidence_marker, snippet, contains_translation, contains_edition, contains_commentary, confidence = classify_translation_candidate(text)
        if candidate_type == "unclear_needs_manual_review":
            continue
        match_row = match_by_local_file.get(local_file_id, {})
        reference_id = match_row.get("reference_id", "")
        reference_row = reference_by_id.get(reference_id, {})
        page_marker = infer_candidate_page_marker(text, evidence_marker)
        candidate_key = build_translation_candidate_key(local_file_id, candidate_type, evidence_marker, page_marker)
        rows.append(
            {
                "candidate_id": f"jbrs-candidate-{len(rows) + 1:04d}",
                "candidate_key": candidate_key,
                "local_file_id": local_file_id,
                "reference_id_if_any": reference_id,
                "journal": JOURNAL_TITLE,
                "volume": reference_row.get("volume", ""),
                "issue": reference_row.get("issue", ""),
                "year": reference_row.get("year", "") or manifest_row.get("probable_year_from_filename", "") or manifest_row.get("probable_year_from_folder", ""),
                "article_title": reference_row.get("article_title", "") or manifest_row.get("probable_title_from_filename", ""),
                "author": reference_row.get("author", "") or manifest_row.get("probable_author_from_path", ""),
                "page_range_or_page": reference_row.get("page_range", "") or manifest_row.get("probable_article_start_page_from_filename", ""),
                "candidate_type": candidate_type,
                "evidence_marker": evidence_marker,
                "short_evidence_snippet": snippet,
                "contains_translation_candidate": contains_translation,
                "contains_edition_or_transliteration_candidate": contains_edition,
                "contains_commentary_only": contains_commentary,
                "confidence": confidence,
                "next_action": "Review the source manually before treating this as translation-bearing content.",
                "notes": "Derived from existing OCR text or local text-searchable content; this is a review lead, not verified translation coverage.",
            }
        )
    return rows


def build_pilot_summary(
    raw_reference_rows: list[dict[str, str]],
    target_rows: list[dict[str, str]],
    manifest_rows: list[dict[str, str]],
    match_rows: list[dict[str, str]],
    batch_rows: list[dict[str, str]],
    status_rows: list[dict[str, str]],
    candidate_rows: list[dict[str, str]],
    candidate_review_rows: list[dict[str, str]] | None = None,
    excerpt_review_rows: list[dict[str, str]] | None = None,
    followup_source_lead_rows: list[dict[str, str]] | None = None,
    ocr_quality_review_rows: list[dict[str, str]] | None = None,
    citation_priority_rows: list[dict[str, str]] | None = None,
    extraction_plan_rows: list[dict[str, str]] | None = None,
    extracted_translation_unit_rows: list[dict[str, str]] | None = None,
    extracted_source_text_unit_rows: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    candidate_review_rows = candidate_review_rows or []
    excerpt_review_rows = excerpt_review_rows or []
    followup_source_lead_rows = followup_source_lead_rows or []
    ocr_quality_review_rows = ocr_quality_review_rows or []
    citation_priority_rows = citation_priority_rows or []
    extraction_plan_rows = extraction_plan_rows or []
    extracted_translation_unit_rows = extracted_translation_unit_rows or []
    extracted_source_text_unit_rows = extracted_source_text_unit_rows or []
    matched_reference_ids = {
        row["reference_id"]
        for row in match_rows
        if row.get("match_status") in {"exact_or_near_exact_match", "plausible_match", "multiple_candidates"}
    }
    status_counts = defaultdict(int)
    for row in status_rows:
        status_counts[row.get("status", "")] += 1
    batch_status_counts = defaultdict(int)
    for row in batch_rows:
        batch_status_counts[row.get("status", "")] += 1
    status_by_batch_id = {row.get("batch_id", ""): row for row in status_rows}
    candidate_type_counts = defaultdict(int)
    for row in candidate_rows:
        candidate_type_counts[row.get("candidate_type", "")] += 1
    bibliography_only_translation_hit_count = sum(
        1
        for row in ocr_quality_review_rows
        if row.get("manual_review_status") == "reviewed_bibliography_only"
    )
    excerpt_review_candidate_keys = {candidate_lookup_key(row) for row in excerpt_review_rows if candidate_lookup_key(row)}
    embedded_translation_excerpt_candidate_count = len(excerpt_review_rows)
    embedded_translation_excerpt_reviewed_count = sum(
        1
        for row in excerpt_review_rows
        if row.get("manual_review_status", "") not in {"", "needs_manual_review"}
    )
    standalone_translation_section_count = sum(
        1
        for row in candidate_review_rows
        if row.get("is_actual_translation_section") == "true"
        and candidate_lookup_key(row) not in excerpt_review_candidate_keys
    )
    verified_translation_coverage_count = sum(
        1
        for row in candidate_review_rows
        if row.get("review_status", "") == "verified_translation_coverage"
        and row.get("is_actual_translation_section") == "true"
    )
    mixed_language_extraction_plan_count = sum(
        1
        for row in extraction_plan_rows
        if row.get("burmese_relevance_status", "") == "mixed_burmese_pali_relevance"
        or (
            "pali" in normalized_language_scope(row.get("source_text_language_or_script", ""))
            and "burmese" in normalized_language_scope(row.get("source_text_language_or_script", ""))
        )
    )
    burmese_relevant_extracted_unit_count = sum(
        1
        for row in extracted_translation_unit_rows + extracted_source_text_unit_rows
        if is_true(row.get("is_burmese_relevant", ""))
    )
    pali_only_extracted_unit_count = sum(
        1
        for row in extracted_translation_unit_rows
        if is_true(row.get("includes_pali", ""))
        and not is_true(row.get("includes_burmese", ""))
        and not is_true(row.get("includes_other_language", ""))
    ) + sum(
        1
        for row in extracted_source_text_unit_rows
        if is_pali_only_language_scope(row.get("source_language", ""))
    )
    return {
        "reference_hunt_count": len(raw_reference_rows),
        "article_reference_target_count": len(target_rows),
        "local_file_manifest_count": len(manifest_rows),
        "reference_file_match_count": len(match_rows),
        "matched_reference_count": len(matched_reference_ids),
        "unmatched_reference_count": len(target_rows) - len(matched_reference_ids),
        "ocr_batch_plan_count": len(batch_rows),
        "needs_runtime_path_cache_count": batch_status_counts["needs_runtime_path_cache"],
        "ready_for_ocr_count": batch_status_counts["ready_for_ocr"],
        "already_text_available_count": status_counts["already_text_available"],
        "ocr_completed_count": status_counts["completed"],
        "batch_plan_ready_for_ocr_count": batch_status_counts["ready_for_ocr"],
        "status_log_ready_for_ocr_count": status_counts["ready_for_ocr"],
        "status_log_completed_count": status_counts["completed"],
        "status_log_failed_count": status_counts["failed"],
        "selectable_for_ocr_count": sum(
            1
            for row in batch_rows
            if batch_is_selectable_for_ocr(row, status_by_batch_id.get(row.get("batch_id", "")))
        ),
        "translation_candidate_count": len(candidate_rows),
        "explicit_translation_candidate_count": candidate_type_counts["explicit_translation_heading"],
        "probable_translation_candidate_count": candidate_type_counts["text_and_translation_section"],
        "embedded_translation_excerpt_candidate_count": embedded_translation_excerpt_candidate_count,
        "embedded_translation_excerpt_reviewed_count": embedded_translation_excerpt_reviewed_count,
        "standalone_translation_section_count": standalone_translation_section_count,
        "fuller_source_followup_lead_count": len(followup_source_lead_rows),
        "citation_priority_queue_count": len(citation_priority_rows),
        "mixed_language_extraction_plan_count": mixed_language_extraction_plan_count,
        "extracted_source_text_unit_count": len(extracted_source_text_unit_rows),
        "extracted_translation_unit_count": len(extracted_translation_unit_rows),
        "burmese_relevant_extracted_unit_count": burmese_relevant_extracted_unit_count,
        "pali_only_extracted_unit_count": pali_only_extracted_unit_count,
        "bibliography_only_translation_hit_count": bibliography_only_translation_hit_count,
        "verified_translation_coverage_count": verified_translation_coverage_count,
        "edition_or_transliteration_only_count": candidate_type_counts["edition_or_transliteration_only"],
        "manual_review_needed_count": sum(
            1
            for row in candidate_rows
            if row.get("candidate_type") in {"translation_word_hit", "citation_to_someone_else_translation", "planned_or_general_translation_discussion", "commentary_or_citation_only", "bibliography_only", "unclear_needs_manual_review"}
        ),
        "notes": [
            "This summary records repository reference-hunt, local-manifest, matching, and OCR-preparation state only.",
            "ready_for_ocr_count and batch_plan_ready_for_ocr_count reflect the batch plan only; status_log_ready_for_ocr_count reflects rows still selectable after consulting the OCR status log.",
            "selectable_for_ocr_count excludes completed and failed rows unless the rerun flags are used explicitly.",
            "Translation candidates are heuristic review leads, not verified translation coverage.",
            "Embedded translation excerpts, bibliography-only hits, and fuller-source follow-up leads are tracked separately from verified translation coverage.",
            "Citation-priority rows count corpus-driven JBRS leads separately from reviewed mixed-language extraction dry runs.",
        ],
    }


def write_summary(path: Path, summary: dict[str, object]) -> None:
    ensure_parent(path)
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def validate_translation_candidate_alignment(
    candidate_rows: list[dict[str, str]],
    candidate_review_rows: list[dict[str, str]],
    ocr_quality_review_rows: list[dict[str, str]],
    excerpt_review_rows: list[dict[str, str]],
    followup_source_lead_rows: list[dict[str, str]],
) -> list[str]:
    errors: list[str] = []
    candidate_by_key = {candidate_lookup_key(row): row for row in candidate_rows if candidate_lookup_key(row)}
    candidate_by_id = {row.get("candidate_id", ""): row for row in candidate_rows if row.get("candidate_id")}
    quality_by_local_file = {row.get("local_file_id", ""): row for row in ocr_quality_review_rows if row.get("local_file_id")}
    excerpt_by_key = {candidate_lookup_key(row): row for row in excerpt_review_rows if candidate_lookup_key(row)}
    followup_by_key = {
        row.get("trigger_candidate_key", "") or row.get("trigger_candidate_id", ""): row
        for row in followup_source_lead_rows
        if row.get("trigger_candidate_key", "") or row.get("trigger_candidate_id", "")
    }

    if len(candidate_by_key) != len(candidate_rows):
        errors.append("Translation candidate log contains duplicate candidate_key values.")
    if len(candidate_by_id) != len(candidate_rows):
        errors.append("Translation candidate log contains duplicate candidate_id display values.")

    review_keys = set()
    for row in candidate_review_rows:
        review_key = candidate_lookup_key(row)
        if not review_key:
            errors.append("Translation candidate review row is missing candidate_key.")
            continue
        if review_key in review_keys:
            errors.append(f"Translation candidate review contains duplicate candidate_key values: {review_key}")
            continue
        review_keys.add(review_key)
        candidate_row = candidate_by_key.get(review_key)
        if not candidate_row:
            errors.append(f"Translation candidate review points to unknown candidate: {row.get('candidate_id', '')}")
            continue
        if row.get("candidate_id", "") and row.get("candidate_id", "") != candidate_row.get("candidate_id", ""):
            errors.append(f"Translation candidate review has stale display id for candidate_key {review_key}")
        if row.get("local_file_id", "") != candidate_row.get("local_file_id", ""):
            errors.append(f"Translation candidate review local_file_id does not match candidate log: {review_key}")
        if row.get("candidate_type", "") != candidate_row.get("candidate_type", ""):
            errors.append(f"Translation candidate review candidate_type does not match candidate log: {review_key}")
        conflicting_local_file_id = manual_assessment_conflicts_with_local_file_id(
            row.get("manual_assessment", ""),
            row.get("local_file_id", ""),
        )
        if conflicting_local_file_id:
            errors.append(
                f"Translation candidate review manual assessment conflicts with local_file_id {row.get('local_file_id', '')}: references {conflicting_local_file_id}"
            )
        if row.get("is_actual_translation_section") == "true" and row.get("review_status") == "needs_manual_review":
            errors.append(f"Candidate review marks actual translation content without a completed review status: {row.get('candidate_id', '')}")
        if row.get("is_actual_translation_section") == "true" and not row.get("manual_assessment", ""):
            errors.append(f"Candidate review marks actual translation content without manual assessment notes: {row.get('candidate_id', '')}")
        if row.get("review_status") == "verified_translation_coverage" and row.get("is_inscription_translation") != "true":
            errors.append(f"Bibliography-only or non-inscription hit was promoted to verified translation coverage: {row.get('candidate_id', '')}")
        if "embedded" in row.get("manual_assessment", "").casefold() and review_key not in excerpt_by_key:
            errors.append(f"Embedded translation review is missing an excerpt-review row: {row.get('candidate_id', '')}")
        if "fuller text and translation" in row.get("manual_assessment", "").casefold() and review_key not in followup_by_key:
            errors.append(f"External fuller-source citation is missing a follow-up lead row: {row.get('candidate_id', '')}")
        if row.get("is_actual_translation_section") == "true" and row.get("local_file_id", "") not in quality_by_local_file:
            errors.append(f"Standalone translation-section lead lacks OCR quality review: {row.get('local_file_id', '')}")

    for row in excerpt_review_rows:
        review_key = candidate_lookup_key(row)
        if not review_key:
            errors.append(f"Excerpt review row is missing candidate_key: {row.get('excerpt_review_id', '')}")
            continue
        candidate_row = candidate_by_key.get(review_key)
        if not candidate_row:
            errors.append(f"Excerpt review points to unknown translation candidate: {row.get('candidate_id', '')}")
            continue
        if row.get("candidate_id", "") and row.get("candidate_id", "") != candidate_row.get("candidate_id", ""):
            errors.append(f"Excerpt review has stale display id for candidate_key {review_key}")
        if row.get("local_file_id", "") != candidate_row.get("local_file_id", ""):
            errors.append(f"Excerpt review local_file_id does not match translation candidate: {row.get('excerpt_review_id', '')}")
        if row.get("is_standalone_translation_section") == "true" and row.get("is_actual_translation_excerpt") != "true":
            errors.append(f"Excerpt review marks a standalone translation section without confirming translation evidence: {row.get('excerpt_review_id', '')}")

    for row in followup_source_lead_rows:
        review_key = row.get("trigger_candidate_key", "") or row.get("trigger_candidate_id", "")
        if not review_key:
            errors.append(f"Follow-up source lead is missing trigger_candidate_key: {row.get('lead_id', '')}")
            continue
        candidate_row = candidate_by_key.get(review_key)
        if not candidate_row:
            errors.append(f"Follow-up source lead points to unknown translation candidate: {row.get('lead_id', '')}")
            continue
        if row.get("trigger_candidate_id", "") and row.get("trigger_candidate_id", "") != candidate_row.get("candidate_id", ""):
            errors.append(f"Follow-up source lead has stale display id for candidate_key {review_key}")
        if row.get("is_same_work_as_cited_source") == "true" and not row.get("possible_local_file_id"):
            errors.append(f"Follow-up source lead marks a same-work match without a local file id: {row.get('lead_id', '')}")

    return errors


def build_jbrs_ocr_production_summary(
    text_index_rows: list[dict[str, str]],
    translation_hit_rows: list[dict[str, str]],
    top_candidate_rows: list[dict[str, str]],
) -> dict[str, int]:
    translation_hit_local_ids = {
        row["local_file_id"]
        for row in translation_hit_rows
        if row.get("hit_type", "") == "translation_marker" and row.get("local_file_id", "")
    }
    inscription_hit_local_ids = {
        row["local_file_id"]
        for row in translation_hit_rows
        if row.get("hit_type", "") == "inscription_marker" and row.get("local_file_id", "")
    }
    text_hit_local_ids = {
        row["local_file_id"]
        for row in translation_hit_rows
        if row.get("hit_type", "") == "text_marker" and row.get("local_file_id", "")
    }
    scope_counts = defaultdict(int)
    for row in text_index_rows:
        scope_counts[row.get("language_scope_guess", "")] += 1
    return {
        "ocr_text_index_count": len(text_index_rows),
        "ocr_translation_hit_count": len(translation_hit_rows),
        "files_with_translation_hits": len(translation_hit_local_ids),
        "files_with_inscription_hits": len(inscription_hit_local_ids),
        "files_with_text_hits": len(text_hit_local_ids),
        "burmese_scope_file_count": scope_counts["Burmese"],
        "mixed_burmese_pali_scope_file_count": scope_counts["Mixed Burmese/Pali"],
        "pali_only_file_count": scope_counts["Pali"],
        "mon_file_count": scope_counts["Mon"],
        "pyu_file_count": scope_counts["Pyu"],
        "uncertain_scope_file_count": scope_counts["mixed_or_uncertain"],
        "non_burmese_context_file_count": scope_counts["non_burmese_relevant_context"],
        "top_extraction_candidate_count": len(top_candidate_rows),
    }


def validate_repo_ocr_artifacts() -> list[str]:
    errors: list[str] = []
    forbidden_suffixes = {
        ".pdf",
        ".png",
        ".jpg",
        ".jpeg",
        ".tif",
        ".tiff",
        ".webp",
        ".gif",
    }
    text_files = {
        path.relative_to(REPO_ROOT).as_posix(): path
        for path in JBRS_WORKING_OCR_TEXT_ROOT.glob("*.txt")
        if path.is_file()
    }
    metadata_entries: dict[str, dict[str, object]] = {}

    for path in JBRS_WORKING_OCR_ROOT.rglob("*"):
        if path.is_file() and path.suffix.casefold() in forbidden_suffixes:
            errors.append(
                f"Committed OCR working tree contains forbidden binary artifact {path.relative_to(REPO_ROOT)}."
            )

    for metadata_path in sorted(JBRS_WORKING_OCR_METADATA_ROOT.glob("*.json")):
        metadata_content = metadata_path.read_text(encoding="utf-8")
        if ABSOLUTE_PATH_PATTERN.search(metadata_content):
            errors.append(
                f"OCR metadata file {metadata_path.relative_to(REPO_ROOT)} contains an absolute path."
            )
        if "GOOGLE_APPLICATION_CREDENTIALS" in metadata_content or "-----BEGIN PRIVATE KEY-----" in metadata_content:
            errors.append(
                f"OCR metadata file {metadata_path.relative_to(REPO_ROOT)} contains a credential reference."
            )
        try:
            metadata = json.loads(metadata_content)
        except json.JSONDecodeError as exc:
            errors.append(
                f"OCR metadata file {metadata_path.relative_to(REPO_ROOT)} is not valid JSON: {exc}."
            )
            continue
        local_file_id = metadata.get("local_file_id", "") or metadata_path.stem
        if local_file_id in metadata_entries:
            errors.append(
                f"OCR metadata files {metadata_entries[local_file_id]['metadata_path']} and {metadata_path.relative_to(REPO_ROOT)} share local_file_id {local_file_id}."
            )
            continue
        text_rel = metadata.get("canonical_ocr_text_path", "") or relative_stub(
            JBRS_WORKING_OCR_TEXT_ROOT / f"{metadata_path.stem}.txt"
        )
        metadata_rel = metadata.get("canonical_metadata_path", "") or relative_stub(metadata_path)
        metadata_entries[local_file_id] = {
            "metadata_path": metadata_path.relative_to(REPO_ROOT).as_posix(),
            "text_path": text_rel,
            "metadata": metadata,
        }

    referenced_text_paths = {
        entry["text_path"]: REPO_ROOT / str(entry["text_path"])
        for entry in metadata_entries.values()
    }
    for text_rel, text_path in sorted(referenced_text_paths.items()):
        if not text_path.exists():
            errors.append(f"OCR metadata references missing OCR text file {text_rel}.")
            continue
        text_content = text_path.read_text(encoding="utf-8")
        if not re.search(r"^\[\[page \d+\]\]$", text_content, re.MULTILINE):
            errors.append(
                f"OCR text file {text_path.relative_to(REPO_ROOT)} lacks page markers."
            )
    for text_rel, text_path in sorted(text_files.items()):
        if text_rel not in referenced_text_paths:
            errors.append(
                f"OCR text file {text_path.relative_to(REPO_ROOT)} is missing a metadata sidecar reference."
            )

    text_index_rows = read_tsv(JBRS_OCR_TEXT_INDEX_PATH)
    text_index_by_local_id = {row["local_file_id"]: row for row in text_index_rows}
    for row in text_index_rows:
        local_file_id = row["local_file_id"]
        ocr_text_path = REPO_ROOT / row["ocr_text_path"]
        metadata_path = REPO_ROOT / row["metadata_path"]
        if row["language_scope_guess"] not in JBRS_OCR_LANGUAGE_SCOPE_VALUES:
            errors.append(
                f"OCR text index row {local_file_id} uses unsupported language_scope_guess '{row['language_scope_guess']}'."
            )
        if not ocr_text_path.exists():
            errors.append(
                f"OCR text index row {local_file_id} points to missing OCR text file {row['ocr_text_path']}."
            )
        if not metadata_path.exists():
            errors.append(
                f"OCR text index row {local_file_id} points to missing metadata file {row['metadata_path']}."
            )
        metadata_entry = metadata_entries.get(local_file_id)
        if not metadata_entry:
            errors.append(
                f"OCR text index row {local_file_id} has no matching committed OCR metadata entry."
            )
        else:
            if str(metadata_entry["text_path"]) != row["ocr_text_path"]:
                errors.append(
                    f"OCR text index row {local_file_id} points to {row['ocr_text_path']} but metadata references {metadata_entry['text_path']}."
                )
            if str(metadata_entry["metadata_path"]) != row["metadata_path"]:
                errors.append(
                    f"OCR text index row {local_file_id} points to metadata {row['metadata_path']} but the committed metadata file is {metadata_entry['metadata_path']}."
                )
        if row["ocr_status"] != "completed":
            errors.append(
                f"OCR text index row {local_file_id} must have ocr_status=completed."
            )
    for local_file_id in metadata_entries:
        if local_file_id not in text_index_by_local_id:
            errors.append(
                f"OCR metadata file {metadata_entries[local_file_id]['metadata_path']} has no matching OCR text index row."
            )

    production_run_rows = read_tsv(JBRS_OCR_PRODUCTION_RUN_LOG_PATH)
    for row in production_run_rows:
        run_id = row["run_id"]
        for field_name in ("selected_count", "completed_count", "failed_count", "skipped_count"):
            if not row[field_name].isdigit():
                errors.append(
                    f"Production run row {run_id} has a non-numeric {field_name} value '{row[field_name]}'."
                )
        for field_name in ("output_text_root", "metadata_root"):
            value = row[field_name]
            if not value:
                errors.append(f"Production run row {run_id} is missing {field_name}.")
                continue
            if ABSOLUTE_PATH_PATTERN.search(value):
                errors.append(
                    f"Production run row {run_id} stores absolute path '{value}' in {field_name}."
                )
            if not (REPO_ROOT / value).exists():
                errors.append(
                    f"Production run row {run_id} points to missing directory {value}."
                )

    translation_hit_rows = read_tsv(JBRS_OCR_TRANSLATION_HIT_INDEX_PATH)
    for row in translation_hit_rows:
        local_file_id = row["local_file_id"]
        if row["language_scope_guess"] not in JBRS_OCR_LANGUAGE_SCOPE_VALUES:
            errors.append(
                f"OCR hit row {row['hit_id']} uses unsupported language_scope_guess '{row['language_scope_guess']}'."
            )
        if row["burmese_relevance_guess"] not in JBRS_BURMESE_RELEVANCE_GUESS_VALUES:
            errors.append(
                f"OCR hit row {row['hit_id']} uses unsupported burmese_relevance_guess '{row['burmese_relevance_guess']}'."
            )
        if local_file_id not in text_index_by_local_id:
            errors.append(
                f"OCR hit row {row['hit_id']} references missing OCR text index row for {local_file_id}."
            )
        if local_file_id not in metadata_entries:
            errors.append(
                f"OCR hit row {row['hit_id']} references missing OCR metadata/text for {local_file_id}."
            )
        if (
            row["language_scope_guess"] == "Pali"
            and row["burmese_relevance_guess"]
            in {"direct_burmese_relevance", "mixed_burmese_pali_relevance"}
        ):
            errors.append(
                f"OCR hit row {row['hit_id']} marks Pali-only file {local_file_id} as Burmese-relevant."
            )
        if ABSOLUTE_PATH_PATTERN.search(row["notes"]):
            errors.append(
                f"OCR hit row {row['hit_id']} contains an absolute path in notes."
            )
    top_candidate_rows = read_tsv(JBRS_OCR_TOP_EXTRACTION_CANDIDATES_PATH)
    if len(top_candidate_rows) < 50:
        errors.append("OCR top extraction candidate report must list at least 50 rows.")
    top_twenty_marked = 0
    for row in top_candidate_rows:
        local_file_id = row["local_file_id"]
        if not row["candidate_rank"].isdigit():
            errors.append(
                f"OCR top extraction candidate row for {local_file_id} has non-numeric candidate_rank '{row['candidate_rank']}'."
            )
        if row["language_scope_guess"] not in JBRS_OCR_LANGUAGE_SCOPE_VALUES:
            errors.append(
                f"OCR top extraction candidate row for {local_file_id} uses unsupported language_scope_guess '{row['language_scope_guess']}'."
            )
        if row["burmese_relevance_guess"] not in JBRS_BURMESE_RELEVANCE_GUESS_VALUES:
            errors.append(
                f"OCR top extraction candidate row for {local_file_id} uses unsupported burmese_relevance_guess '{row['burmese_relevance_guess']}'."
            )
        if row["inscriptional_relevance_class"] not in JBRS_INSCRIPTIONAL_RELEVANCE_CLASS_VALUES:
            errors.append(
                f"OCR top extraction candidate row for {local_file_id} uses unsupported inscriptional_relevance_class '{row['inscriptional_relevance_class']}'."
            )
        if local_file_id not in text_index_by_local_id:
            errors.append(
                f"OCR top extraction candidate row for {local_file_id} references no OCR text index row."
            )
        ocr_text_path = REPO_ROOT / row["ocr_text_path"]
        if not ocr_text_path.exists():
            errors.append(
                f"OCR top extraction candidate row for {local_file_id} points to missing OCR text file {row['ocr_text_path']}."
            )
        if row["language_scope_guess"] == "Pali" and row["burmese_relevance_guess"] in {
            "direct_burmese_relevance",
            "mixed_burmese_pali_relevance",
        }:
            errors.append(
                f"OCR top extraction candidate row for {local_file_id} marks a Pali-only file as Burmese-relevant."
            )
        if "top_20_priority" in row["notes"]:
            top_twenty_marked += 1
        for field_name in ("reason_for_priority", "recommended_next_action", "notes"):
            if ABSOLUTE_PATH_PATTERN.search(row[field_name]):
                errors.append(
                    f"OCR top extraction candidate row for {local_file_id} contains an absolute path in {field_name}."
                )
    if top_twenty_marked < 20:
        errors.append("OCR top extraction candidate report must clearly mark the top 20 rows.")

    top_inscription_rows = read_tsv(JBRS_OCR_TOP_INSCRIPTION_EXTRACTION_CANDIDATES_PATH)
    if len(top_candidate_rows) >= 20 and len(top_inscription_rows) < 20:
        errors.append("OCR top inscription extraction candidate report must list 20 rows when enough candidates exist.")
    for row in top_inscription_rows:
        local_file_id = row["local_file_id"]
        if row["inscriptional_relevance_class"] not in JBRS_INSCRIPTIONAL_RELEVANCE_CLASS_VALUES:
            errors.append(
                f"OCR top inscription candidate row for {local_file_id} uses unsupported inscriptional_relevance_class '{row['inscriptional_relevance_class']}'."
            )
        if local_file_id not in text_index_by_local_id:
            errors.append(
                f"OCR top inscription candidate row for {local_file_id} references no OCR text index row."
            )
        ocr_text_path = REPO_ROOT / row["ocr_text_path"]
        if not ocr_text_path.exists():
            errors.append(
                f"OCR top inscription candidate row for {local_file_id} points to missing OCR text file {row['ocr_text_path']}."
            )
        for field_name in ("reason_for_priority", "recommended_next_action", "notes"):
            if ABSOLUTE_PATH_PATTERN.search(row[field_name]):
                errors.append(
                    f"OCR top inscription candidate row for {local_file_id} contains an absolute path in {field_name}."
                )

    renaming_plan_rows = read_tsv(JBRS_FILE_RENAMING_PLAN_PATH)
    alias_map_rows = read_tsv(JBRS_FILE_ALIAS_MAP_PATH)
    alias_by_local_file_id = {row["local_file_id"]: row for row in alias_map_rows}
    canonical_name_to_local_id: dict[str, str] = {}
    for row in renaming_plan_rows:
        canonical_base_name = row.get("canonical_base_name", "")
        if canonical_base_name:
            existing = canonical_name_to_local_id.get(canonical_base_name)
            if existing and existing != row["local_file_id"]:
                errors.append(
                    f"Canonical base name collision: {canonical_base_name} is assigned to both {existing} and {row['local_file_id']}."
                )
            canonical_name_to_local_id[canonical_base_name] = row["local_file_id"]
        if row.get("identity_confidence", "") == "low" and row.get("rename_status", "").startswith("renamed"):
            errors.append(
                f"Low-confidence renaming plan row {row['local_file_id']} must not be auto-renamed."
            )
        for field_name in ("current_ocr_text_path", "current_metadata_path"):
            value = row.get(field_name, "")
            if value and not (REPO_ROOT / value).exists():
                errors.append(
                    f"Renaming plan row {row['local_file_id']} points to missing file {value}."
                )
    numeric_name_pattern = re.compile(r"^\d+[A-Za-z]?\.pdf$", re.IGNORECASE)
    for row in text_index_rows:
        if row.get("old_file_name", "") and numeric_name_pattern.fullmatch(row["old_file_name"]):
            if row["local_file_id"] not in alias_by_local_file_id:
                errors.append(
                    f"Numeric OCR file {row['local_file_id']} is missing an alias-map row."
                )
    for row in alias_map_rows:
        local_file_id = row["local_file_id"]
        if local_file_id not in text_index_by_local_id:
            errors.append(
                f"Alias-map row for {local_file_id} has no matching OCR text index row."
            )
        if row["alias_status"] in {"renamed_in_repo", "already_canonical"}:
            for field_name in ("canonical_ocr_text_path", "canonical_metadata_path"):
                value = row.get(field_name, "")
                if value and not (REPO_ROOT / value).exists():
                    errors.append(
                        f"Alias-map row for {local_file_id} points to missing canonical file {value}."
                    )
    production_summary = json.loads(JBRS_OCR_PRODUCTION_SUMMARY_PATH.read_text(encoding="utf-8"))
    expected_summary = build_jbrs_ocr_production_summary(
        text_index_rows=text_index_rows,
        translation_hit_rows=translation_hit_rows,
        top_candidate_rows=top_candidate_rows,
    )
    if production_summary != expected_summary:
        errors.append("JBRS OCR production summary counts do not match the OCR text index, hit index, and top-candidate report.")
    return errors


def build_readme_text() -> str:
    return """# JBRS working metadata

This directory stores working metadata for the *Journal of the Burma Research Society* (JBRS) reference hunt, local-file matching, OCR planning, and translation-candidate triage. It does **not** store source PDFs, page images, Google Vision JSON, or raw `data_local/` OCR payloads.

## Core workflow
1. Build raw and clean article references: `python3 scripts/build_jbrs_reference_hunt.py`
2. Build or refresh the redacted manifest: `python3 scripts/build_jbrs_local_manifest.py`
3. Write a local runtime path cache when you have live roots available: `python3 scripts/build_jbrs_local_manifest.py --root "/path/to/jbrs/root" --write-runtime-path-cache`
4. Match clean article targets to local files: `python3 scripts/match_jbrs_references_to_local_files.py`
5. Build the OCR plan and status log: `python3 scripts/plan_jbrs_ocr_batches.py`
6. Run OCR preflight before live submission: `python3 scripts/preflight_jbrs_ocr.py --limit 5`
7. Dry-run the Google Vision workflow: `python3 scripts/ocr_jbrs_google_vision.py --dry-run --limit 5`
8. Run live Google Vision OCR only after preflight passes: `python3 scripts/ocr_jbrs_google_vision.py --execute --limit 5`
9. Refresh conservative translation-candidate leads: `python3 scripts/detect_jbrs_translation_candidates.py`
10. Review article-target cleanup in `jbrs_article_reference_targets_review.tsv` before trusting unresolved bibliographic rows.
11. Review candidate outcomes in `jbrs_translation_candidate_review.tsv` before treating any OCR hit as translation-bearing.

## Runtime path cache
- Local runtime cache path: `data_local/ocr/jbrs/manifest/jbrs_runtime_path_map.json`
- The committed TSV keeps redacted path stubs only.
- The runtime cache maps `local_file_id -> absolute local path` and must stay gitignored.

## Local OCR output location
- Preferred local output root: `data_local/ocr/jbrs/`
- Subdirectories used by the live OCR workflow:
  - `manifest/`
  - `google_vision_json/`
  - `page_text/`
  - `article_text/`
  - `logs/`

## Safe to commit
- TSV manifests and match logs in this directory
- JSON summaries
- README and scripts
- short evidence snippets only
- compact OCR-derived published source/translation units when they are clearly marked as OCR-derived extraction output and linked to source metadata

## Must not be committed
- source PDFs or page images
- raw `data_local/` OCR article_text/page_text dumps or Google Vision runtime payloads
- Google Vision JSON payloads
- Nathan's absolute external-drive paths
- Google credentials, API keys, or service-account secrets

## Guardrails
- The Berkeley IOB catalogue record is not a verified local witness.
- The IOB plate portfolios are not the missing companion text witness.
- SIP does not satisfy the separate UEM witness gap.
- Translation candidates are review leads only; do not treat OCR snippets or English prose as verified translation coverage.
"""


def build_gitignore_has_data_local() -> bool:
    if not GITIGNORE_PATH.exists():
        return False
    text = GITIGNORE_PATH.read_text(encoding="utf-8")
    return "data_local/" in text or "data_local/ocr/jbrs" in text


def tracked_files_under(prefix: str) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "--", prefix],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def tsv_header_and_row_count(path: Path, expected_fields: list[str]) -> tuple[str, int]:
    text = path.read_text(encoding="utf-8")
    nonempty_lines = [line.rstrip("\r") for line in text.splitlines() if line.strip()]
    if not nonempty_lines:
        return "", 0
    return nonempty_lines[0], max(len(nonempty_lines) - 1, 0)


def validate_corpus_citation_workflow(
    inventory_rows: list[dict[str, str]],
    target_rows: list[dict[str, str]],
    source_match_rows: list[dict[str, str]],
    source_match_review_rows: list[dict[str, str]],
    dashboard_rows: list[dict[str, str]],
    out_of_scope_audit_rows: list[dict[str, str]],
    ocr_queue_rows: list[dict[str, str]],
    extracted_translation_unit_rows: list[dict[str, str]],
    extracted_source_text_unit_rows: list[dict[str, str]],
    summary: dict[str, object],
) -> list[str]:
    errors: list[str] = []
    if not inventory_rows:
        return ["Corpus citation inventory is empty."]
    if not target_rows:
        return ["Corpus citation targets are empty."]

    target_ids = {row["citation_target_id"] for row in target_rows if row.get("citation_target_id")}
    inventory_counts_by_target: Counter[str] = Counter()
    for row in inventory_rows:
        if not row.get("corpus_record_id") and not row.get("inscription_id"):
            errors.append(
                f"Corpus citation inventory row {row.get('citation_raw', '<unknown>')} lacks corpus_record_id and inscription_id."
            )
        scope = row.get("corpus_language_scope", "")
        if scope and scope not in CORPUS_CITATION_LANGUAGE_SCOPES:
            errors.append(
                f"Corpus citation inventory row {row.get('citation_raw', '<unknown>')} has unsupported corpus_language_scope '{scope}'."
            )
        source_scope = row.get("source_work_language_scope", "")
        if source_scope and source_scope not in CORPUS_CITATION_LANGUAGE_SCOPES:
            errors.append(
                f"Corpus citation inventory row {row.get('citation_raw', '<unknown>')} has unsupported source_work_language_scope '{source_scope}'."
            )
        relevance = row.get("citation_relevance_to_burmese_corpus", "")
        if relevance and relevance not in CORPUS_CITATION_RELEVANCE_STATUSES:
            errors.append(
                f"Corpus citation inventory row {row.get('citation_raw', '<unknown>')} has unsupported citation_relevance_to_burmese_corpus '{relevance}'."
            )
        target_id = row.get("citation_target_id", "")
        if target_id not in target_ids:
            errors.append(
                f"Corpus citation inventory row {row.get('citation_raw', '<unknown>')} links to unknown citation_target_id '{target_id}'."
            )
        else:
            inventory_counts_by_target[target_id] += 1

    source_match_by_target_id = {row["citation_target_id"]: row for row in source_match_rows if row.get("citation_target_id")}
    review_by_target_id = {
        row["citation_target_id"]: row for row in source_match_review_rows if row.get("citation_target_id")
    }
    for row in target_rows:
        target_id = row.get("citation_target_id", "")
        if row.get("source_type") not in CORPUS_CITATION_SOURCE_TYPES:
            errors.append(f"Corpus citation target {target_id} has unsupported source_type '{row.get('source_type', '')}'.")
        if row.get("source_work_language_scope") not in CORPUS_CITATION_LANGUAGE_SCOPES:
            errors.append(
                f"Corpus citation target {target_id} has unsupported source_work_language_scope '{row.get('source_work_language_scope', '')}'."
            )
        if row.get("target_priority") not in CORPUS_CITATION_TARGET_PRIORITIES:
            errors.append(
                f"Corpus citation target {target_id} has unsupported target_priority '{row.get('target_priority', '')}'."
            )
        if row.get("source_role") not in CORPUS_CITATION_SOURCE_ROLES:
            errors.append(f"Corpus citation target {target_id} has unsupported source_role '{row.get('source_role', '')}'.")
        if inventory_counts_by_target[target_id] == 0:
            errors.append(f"Corpus citation target {target_id} does not link back to any corpus citation inventory row.")
        if target_id not in source_match_by_target_id:
            errors.append(f"Corpus citation target {target_id} has no source-file match row.")

    dashboard_target_ids: set[str] = set()
    for row in source_match_rows:
        target_id = row.get("citation_target_id", "")
        if target_id not in target_ids:
            errors.append(f"Corpus citation source-file match row links to unknown citation_target_id '{target_id}'.")
        if row.get("match_status") not in CORPUS_CITATION_MATCH_STATUSES:
            errors.append(
                f"Corpus citation source-file match row {target_id} has unsupported match_status '{row.get('match_status', '')}'."
            )
        if row.get("needs_ocr", "false") == "true" and not row.get("matched_local_file_id"):
            errors.append(f"Corpus citation source-file match row {target_id} requires OCR but has no matched_local_file_id.")
        if row.get("match_confidence") in {"medium", "high"}:
            review_row = review_by_target_id.get(target_id)
            if not review_row and not corpus_citation_match_has_strong_evidence(row):
                errors.append(
                    f"Corpus citation source-file match row {target_id} is {row.get('match_confidence')} confidence without review evidence."
                )

    for row in source_match_review_rows:
        target_id = row.get("citation_target_id", "")
        if target_id not in target_ids:
            errors.append(f"Corpus citation source-file review row links to unknown citation_target_id '{target_id}'.")
        if row.get("review_status") not in CORPUS_CITATION_MATCH_REVIEW_STATUSES:
            errors.append(
                f"Corpus citation source-file review row {target_id} has unsupported review_status '{row.get('review_status', '')}'."
            )
        reviewed_match_status = row.get("reviewed_match_status", "")
        if reviewed_match_status and reviewed_match_status not in CORPUS_CITATION_MATCH_STATUSES:
            errors.append(
                f"Corpus citation source-file review row {target_id} has unsupported reviewed_match_status '{reviewed_match_status}'."
            )

    for row in dashboard_rows:
        dashboard_id = row.get("dashboard_id", "<unknown>")
        target_id = row.get("citation_target_id", "")
        dashboard_target_ids.add(target_id)
        if not row.get("inscription_id") and not row.get("corpus_record_id"):
            errors.append(f"Corpus translation source dashboard row {dashboard_id} lacks inscription_id and corpus_record_id.")
        if target_id not in target_ids:
            errors.append(f"Corpus translation source dashboard row {dashboard_id} links to unknown citation_target_id '{target_id}'.")
        if row.get("corpus_language_scope") not in CORPUS_CITATION_LANGUAGE_SCOPES:
            errors.append(
                f"Corpus translation source dashboard row {dashboard_id} has unsupported corpus_language_scope '{row.get('corpus_language_scope', '')}'."
            )
        if row.get("source_work_language_scope") not in CORPUS_CITATION_LANGUAGE_SCOPES:
            errors.append(
                f"Corpus translation source dashboard row {dashboard_id} has unsupported source_work_language_scope '{row.get('source_work_language_scope', '')}'."
            )
        if row.get("citation_relevance_to_burmese_corpus") not in CORPUS_CITATION_RELEVANCE_STATUSES:
            errors.append(
                f"Corpus translation source dashboard row {dashboard_id} has unsupported citation_relevance_to_burmese_corpus '{row.get('citation_relevance_to_burmese_corpus', '')}'."
            )
        if row.get("source_role") not in CORPUS_CITATION_SOURCE_ROLES:
            errors.append(
                f"Corpus translation source dashboard row {dashboard_id} has unsupported source_role '{row.get('source_role', '')}'."
            )
        if row.get("source_match_status") not in CORPUS_CITATION_MATCH_STATUSES:
            errors.append(
                f"Corpus translation source dashboard row {dashboard_id} has unsupported source_match_status '{row.get('source_match_status', '')}'."
            )
        if row.get("extraction_status") not in CORPUS_CITATION_EXTRACTION_STATUSES:
            errors.append(
                f"Corpus translation source dashboard row {dashboard_id} has unsupported extraction_status '{row.get('extraction_status', '')}'."
            )
        if (
            row.get("corpus_language_scope") in {"Burmese", "Old Burmese", "Mixed Burmese/Pali"}
            and row.get("source_work_language_scope") == "mixed_or_uncertain"
            and row.get("extraction_status") == "out_of_scope_non_burmese"
        ):
            errors.append(
                f"Corpus translation source dashboard row {dashboard_id} marks a Burmese corpus citation out_of_scope_non_burmese only because the source work scope is mixed_or_uncertain."
            )
        if (
            row.get("source_role") in NON_EXTRACTIVE_SOURCE_ROLES
            and row.get("extraction_status") in {"ready_for_ocr", "ready_for_extraction"}
        ):
            errors.append(
                f"Corpus translation source dashboard row {dashboard_id} is {row.get('source_role', '')} but still marked {row.get('extraction_status', '')}."
            )

    out_of_scope_dashboard_rows = [
        row for row in dashboard_rows if row.get("extraction_status") == "out_of_scope_non_burmese"
    ]
    audit_by_dashboard_id = {
        row["dashboard_id"]: row for row in out_of_scope_audit_rows if row.get("dashboard_id")
    }
    for row in out_of_scope_audit_rows:
        dashboard_id = row.get("dashboard_id", "")
        if dashboard_id not in {item.get("dashboard_id", "") for item in out_of_scope_dashboard_rows}:
            errors.append(
                f"Corpus out-of-scope audit row {dashboard_id or '<unknown>'} does not correspond to an out_of_scope_non_burmese dashboard row."
            )
        if row.get("audit_status") not in CORPUS_OUT_OF_SCOPE_AUDIT_STATUSES:
            errors.append(
                f"Corpus out-of-scope audit row {dashboard_id or '<unknown>'} has unsupported audit_status '{row.get('audit_status', '')}'."
            )
        if row.get("audit_reason") not in CORPUS_OUT_OF_SCOPE_AUDIT_REASONS:
            errors.append(
                f"Corpus out-of-scope audit row {dashboard_id or '<unknown>'} has unsupported audit_reason '{row.get('audit_reason', '')}'."
            )
        if (
            row.get("corpus_language_scope") in {"Burmese", "Old Burmese"}
            and not (
                row.get("audit_status") == "non_burmese_parallel_or_context"
                and row.get("audit_reason") in {"parallel_non_burmese_record", "non_burmese_context"}
            )
        ):
            errors.append(
                f"Corpus out-of-scope audit row {dashboard_id or '<unknown>'} leaves a Burmese/Old Burmese record out_of_scope_non_burmese without an explicit parallel/context justification."
            )

    for row in out_of_scope_dashboard_rows:
        dashboard_id = row.get("dashboard_id", "")
        audit_row = audit_by_dashboard_id.get(dashboard_id)
        if not audit_row:
            errors.append(
                f"Corpus translation source dashboard row {dashboard_id} is out_of_scope_non_burmese but has no audit row."
            )

    for row in ocr_queue_rows:
        queue_id = row.get("ocr_queue_id", "<unknown>")
        target_id = row.get("citation_target_id", "")
        if target_id not in target_ids:
            errors.append(f"Corpus cited-source OCR queue row {queue_id} links to unknown citation_target_id '{target_id}'.")
            continue
        match_row = source_match_by_target_id.get(target_id)
        review_row = review_by_target_id.get(target_id)
        if not match_row or match_row.get("needs_ocr") != "true":
            errors.append(f"Corpus cited-source OCR queue row {queue_id} does not come from a cited source needing OCR.")
        if target_id not in dashboard_target_ids:
            errors.append(f"Corpus cited-source OCR queue row {queue_id} has no matching dashboard rows.")
        if not review_row or review_row.get("queue_for_targeted_ocr") != "true":
            errors.append(f"Corpus cited-source OCR queue row {queue_id} does not come from a reviewed plausible match.")
        target_row = next((item for item in target_rows if item.get("citation_target_id") == target_id), {})
        if target_row.get("source_role") in NON_EXTRACTIVE_SOURCE_ROLES:
            errors.append(
                f"Corpus cited-source OCR queue row {queue_id} points at non-extractive source_role '{target_row.get('source_role', '')}'."
            )

    target_ids_by_local_file_id: dict[str, set[str]] = defaultdict(set)
    for row in source_match_rows:
        local_file_id = row.get("matched_local_file_id", "")
        target_id = row.get("citation_target_id", "")
        if local_file_id and target_id:
            target_ids_by_local_file_id[local_file_id].add(target_id)

    for label, rows, id_field in (
        ("translation", extracted_translation_unit_rows, "translation_unit_id"),
        ("source-text", extracted_source_text_unit_rows, "source_text_unit_id"),
    ):
        for row in rows:
            row_id = row.get(id_field, "<unknown>")
            target_id = row.get("citation_target_id", "")
            if target_id and target_id not in target_ids:
                errors.append(f"Extracted {label} unit {row_id} links to unknown citation_target_id '{target_id}'.")
            local_file_id = row.get("source_local_file_id", "")
            candidate_target_ids = target_ids_by_local_file_id.get(local_file_id, set())
            if len(candidate_target_ids) == 1:
                expected_target_id = next(iter(candidate_target_ids))
                if target_id != expected_target_id:
                    errors.append(
                        f"Extracted {label} unit {row_id} should link to citation_target_id '{expected_target_id}' for local file {local_file_id}."
                    )

    expected_summary = {
        "citation_inventory_count": len(inventory_rows),
        "distinct_inscription_count": len(
            {
                row.get("inscription_id") or row.get("corpus_record_id")
                for row in inventory_rows
                if row.get("inscription_id") or row.get("corpus_record_id")
            }
        ),
        "citation_target_count": len(target_rows),
        "matched_target_count": sum(1 for row in source_match_rows if row.get("matched_local_file_id")),
        "ocr_queue_count": len(ocr_queue_rows),
        "manual_file_hunt_count": sum(1 for row in source_match_rows if row.get("needs_manual_file_hunt") == "true"),
        "likely_translation_target_count": sum(
            1 for row in target_rows if row.get("likely_contains_translation") == "true"
        ),
        "likely_source_text_target_count": sum(
            1 for row in target_rows if row.get("likely_contains_source_text") == "true"
        ),
        "extraction_ready_count": sum(
            1 for row in dashboard_rows if row.get("extraction_status") == "ready_for_extraction"
        ),
        "out_of_scope_non_burmese_total": len(out_of_scope_audit_rows),
        "out_of_scope_non_burmese_burmese_record_count": sum(
            1 for row in out_of_scope_audit_rows if row.get("corpus_language_scope") in {"Burmese", "Old Burmese"}
        ),
        "out_of_scope_non_burmese_non_burmese_record_count": sum(
            1 for row in out_of_scope_audit_rows if row.get("corpus_language_scope") in {"Pali", "Mon", "Pyu"}
        ),
        "wrongly_out_of_scope_burmese_record_count": sum(
            1 for row in out_of_scope_audit_rows if row.get("audit_status") == "wrongly_out_of_scope_burmese_record"
        ),
        "mixed_record_needs_review_count": sum(
            1 for row in out_of_scope_audit_rows if row.get("audit_status") == "mixed_record_needs_review"
        ),
        "non_burmese_parallel_or_context_count": sum(
            1 for row in out_of_scope_audit_rows if row.get("audit_status") == "non_burmese_parallel_or_context"
        ),
        "direct_burmese_record_citation_count": sum(
            1
            for row in dashboard_rows
            if row.get("corpus_language_scope") in {"Burmese", "Old Burmese"}
            and row.get("citation_relevance_to_burmese_corpus") == "direct_burmese_relevance"
        ),
        "mixed_source_for_burmese_record_count": sum(
            1
            for row in dashboard_rows
            if row.get("corpus_language_scope") in {"Burmese", "Old Burmese"}
            and row.get("source_work_language_scope") in {"mixed_or_uncertain", "Mixed Burmese/Pali"}
        ),
    }
    for key, expected_value in expected_summary.items():
        if summary.get(key) != expected_value:
            errors.append(
                f"Corpus citation workflow summary {key}={summary.get(key)!r} does not match expected value {expected_value!r}."
            )

    return errors


def validate_jbrs_workflow() -> list[str]:
    errors: list[str] = []
    required_paths = [
        JBRS_REFERENCE_HUNT_RAW_PATH,
        JBRS_ARTICLE_REFERENCE_TARGETS_PATH,
        JBRS_ARTICLE_REFERENCE_TARGETS_REVIEW_PATH,
        JBRS_LOCAL_FILE_MANIFEST_PATH,
        JBRS_REFERENCE_FILE_MATCH_PATH,
        JBRS_OCR_BATCH_PLAN_PATH,
        JBRS_OCR_STATUS_LOG_PATH,
        JBRS_TRANSLATION_CANDIDATE_LOG_PATH,
        JBRS_TRANSLATION_CANDIDATE_REVIEW_PATH,
        JBRS_OCR_QUALITY_REVIEW_PATH,
        JBRS_EMBEDDED_TRANSLATION_EXCERPT_REVIEW_PATH,
        JBRS_FOLLOWUP_SOURCE_LEADS_PATH,
        JBRS_CORPUS_CITATION_PRIORITY_QUEUE_PATH,
        JBRS_STRUCTURED_EXTRACTION_PLAN_PATH,
        JBRS_EXTRACTED_TRANSLATION_UNITS_PATH,
        JBRS_EXTRACTED_SOURCE_TEXT_UNITS_PATH,
        JBRS_OCR_PRODUCTION_RUN_LOG_PATH,
        JBRS_OCR_TEXT_INDEX_PATH,
        JBRS_OCR_TRANSLATION_HIT_INDEX_PATH,
        JBRS_OCR_TOP_EXTRACTION_CANDIDATES_PATH,
        JBRS_OCR_TOP_INSCRIPTION_EXTRACTION_CANDIDATES_PATH,
        JBRS_OCR_PRODUCTION_SUMMARY_PATH,
        JBRS_FILE_RENAMING_PLAN_PATH,
        JBRS_FILE_ALIAS_MAP_PATH,
        CORPUS_CITATION_INVENTORY_PATH,
        CORPUS_CITATION_TARGETS_PATH,
        CORPUS_CITATION_SOURCE_FILE_MATCH_PATH,
        CORPUS_CITATION_SOURCE_FILE_MATCH_REVIEW_PATH,
        CORPUS_TRANSLATION_SOURCE_DASHBOARD_PATH,
        CORPUS_OUT_OF_SCOPE_NON_BURMESE_AUDIT_PATH,
        CORPUS_CITED_SOURCE_OCR_QUEUE_PATH,
        CORPUS_CITATION_WORKFLOW_SUMMARY_PATH,
        JBRS_PILOT_SUMMARY_PATH,
        JBRS_README_PATH,
    ]
    for path in required_paths:
        if not path.exists():
            errors.append(f"Missing required JBRS artifact: {path.relative_to(REPO_ROOT)}")
    if errors:
        return errors

    batch_header, batch_row_count = tsv_header_and_row_count(JBRS_OCR_BATCH_PLAN_PATH, OCR_BATCH_PLAN_FIELDS)
    status_header, status_row_count = tsv_header_and_row_count(JBRS_OCR_STATUS_LOG_PATH, OCR_STATUS_LOG_FIELDS)
    expected_batch_header = "\t".join(OCR_BATCH_PLAN_FIELDS)
    expected_status_header = "\t".join(OCR_STATUS_LOG_FIELDS)
    if batch_header != expected_batch_header:
        errors.append("JBRS OCR batch plan TSV is blank or missing the expected header.")
    if status_header != expected_status_header:
        errors.append("JBRS OCR status log TSV is blank or missing the expected header.")
    if JBRS_OCR_BATCH_PLAN_PATH.stat().st_size > MAX_GITHUB_CONTENTS_SIZE:
        errors.append("JBRS OCR batch plan TSV exceeds the GitHub contents-view size threshold.")
    if JBRS_OCR_STATUS_LOG_PATH.stat().st_size > MAX_GITHUB_CONTENTS_SIZE:
        errors.append("JBRS OCR status log TSV exceeds the GitHub contents-view size threshold.")
    if errors:
        return errors

    raw_rows = read_tsv(JBRS_REFERENCE_HUNT_RAW_PATH)
    target_rows = read_tsv(JBRS_ARTICLE_REFERENCE_TARGETS_PATH)
    target_review_rows = read_tsv(JBRS_ARTICLE_REFERENCE_TARGETS_REVIEW_PATH)
    manifest_rows = read_tsv(JBRS_LOCAL_FILE_MANIFEST_PATH)
    match_rows = read_tsv(JBRS_REFERENCE_FILE_MATCH_PATH)
    batch_rows = read_tsv(JBRS_OCR_BATCH_PLAN_PATH)
    status_rows = read_tsv(JBRS_OCR_STATUS_LOG_PATH)
    candidate_rows = read_tsv(JBRS_TRANSLATION_CANDIDATE_LOG_PATH)
    candidate_review_rows = read_tsv(JBRS_TRANSLATION_CANDIDATE_REVIEW_PATH)
    ocr_quality_review_rows = read_tsv(JBRS_OCR_QUALITY_REVIEW_PATH)
    excerpt_review_rows = read_tsv(JBRS_EMBEDDED_TRANSLATION_EXCERPT_REVIEW_PATH)
    followup_source_lead_rows = read_tsv(JBRS_FOLLOWUP_SOURCE_LEADS_PATH)
    citation_priority_rows = read_tsv(JBRS_CORPUS_CITATION_PRIORITY_QUEUE_PATH)
    extraction_plan_rows = read_tsv(JBRS_STRUCTURED_EXTRACTION_PLAN_PATH)
    extracted_translation_unit_rows = read_tsv(JBRS_EXTRACTED_TRANSLATION_UNITS_PATH)
    extracted_source_text_unit_rows = read_tsv(JBRS_EXTRACTED_SOURCE_TEXT_UNITS_PATH)
    citation_inventory_rows = read_tsv(CORPUS_CITATION_INVENTORY_PATH)
    citation_target_rows = read_tsv(CORPUS_CITATION_TARGETS_PATH)
    citation_source_match_rows = read_tsv(CORPUS_CITATION_SOURCE_FILE_MATCH_PATH)
    citation_source_match_review_rows = read_tsv(CORPUS_CITATION_SOURCE_FILE_MATCH_REVIEW_PATH)
    citation_dashboard_rows = read_tsv(CORPUS_TRANSLATION_SOURCE_DASHBOARD_PATH)
    citation_out_of_scope_audit_rows = read_tsv(CORPUS_OUT_OF_SCOPE_NON_BURMESE_AUDIT_PATH)
    citation_ocr_queue_rows = read_tsv(CORPUS_CITED_SOURCE_OCR_QUEUE_PATH)
    citation_workflow_summary = json.loads(CORPUS_CITATION_WORKFLOW_SUMMARY_PATH.read_text(encoding="utf-8"))
    summary = json.loads(JBRS_PILOT_SUMMARY_PATH.read_text(encoding="utf-8"))
    readme_text = JBRS_README_PATH.read_text(encoding="utf-8")

    target_ids = {row["target_reference_id"] for row in target_rows}
    target_review_by_id = {row["target_reference_id"]: row for row in target_review_rows}
    manifest_by_id = {row["local_file_id"]: row for row in manifest_rows}
    batch_by_id = {row["batch_id"]: row for row in batch_rows}
    status_by_batch_id = {row["batch_id"]: row for row in status_rows}
    candidate_by_key = {candidate_lookup_key(row): row for row in candidate_rows if candidate_lookup_key(row)}
    excerpt_review_by_id = {
        row.get("excerpt_review_id", ""): row for row in excerpt_review_rows if row.get("excerpt_review_id", "")
    }

    if summary.get("ocr_batch_plan_count", 0) and not batch_rows:
        errors.append("JBRS pilot summary reports OCR batch rows, but jbrs_ocr_batch_plan.tsv has no rows.")
    if summary.get("ready_for_ocr_count", 0) and not any(row.get("status") == "ready_for_ocr" for row in batch_rows):
        errors.append("JBRS pilot summary reports ready_for_ocr rows, but the OCR batch plan has none.")
    if summary.get("already_text_available_count", 0) and not any(row.get("status") == "already_text_available" for row in status_rows):
        errors.append("JBRS pilot summary reports already_text_available rows, but the OCR status log has none.")
    if len(batch_rows) != batch_row_count:
        errors.append("JBRS OCR batch plan TSV row count does not match parsed batch rows.")
    if len(status_rows) != status_row_count:
        errors.append("JBRS OCR status log TSV row count does not match parsed status rows.")
    if len(batch_rows) != len(batch_by_id):
        errors.append("JBRS OCR batch plan contains duplicate batch_id values.")
    if len(status_rows) != len(status_by_batch_id):
        errors.append("JBRS OCR status log contains duplicate batch_id values.")
    if len(batch_rows) != len(status_rows) or set(batch_by_id) != set(status_by_batch_id):
        errors.append("JBRS OCR status rows do not correspond one-to-one with OCR batch rows.")

    for row in raw_rows:
        if len(row.get("matched_reference_text_short", "")) > SHORT_SNIPPET_LIMIT:
            errors.append(f"Raw JBRS reference snippet too long: {row.get('reference_id', '')}")
        if row.get("reference_kind") in {"metadata_fragment", "bibliography_family_marker", "periodical_authority_record"} and row.get("target_reference_id"):
            errors.append(f"Metadata or family-marker raw hit incorrectly linked to clean target: {row.get('reference_id', '')}")

    for row in target_rows:
        if row.get("reference_kind") not in ARTICLE_REFERENCE_KINDS:
            errors.append(f"Clean article target has invalid reference kind: {row.get('target_reference_id', '')}")
        review_row = target_review_by_id.get(row.get("target_reference_id", ""))
        if not review_row:
            errors.append(f"Clean article target lacks a review row: {row.get('target_reference_id', '')}")
            continue
        if title_needs_review(row.get("article_title", "")) and review_row.get("review_status") not in MANUAL_TARGET_REVIEW_STATUSES | SKIPPED_TARGET_REVIEW_STATUSES:
            errors.append(f"Malformed clean article target lacks manual-review status: {row.get('target_reference_id', '')}")

    for row in match_rows:
        if row.get("reference_id") not in target_ids:
            errors.append(f"Reference match points to unknown clean target: {row.get('reference_id', '')}")
        review_status = row.get("target_review_status", "")
        target_review = target_review_by_id.get(row.get("reference_id", ""), {})
        if review_status != target_review.get("review_status", ""):
            errors.append(f"Reference match row has stale or missing target_review_status: {row.get('reference_id', '')}")
        local_file_id = row.get("local_file_id", "")
        if local_file_id and local_file_id not in manifest_by_id:
            errors.append(f"Reference match points to unknown local file id: {local_file_id}")
        if review_status in SKIPPED_TARGET_REVIEW_STATUSES and row.get("match_status") != "false_positive":
            errors.append(f"Parser-artifact target fed automatic matching: {row.get('reference_id', '')}")
        if review_status in MANUAL_TARGET_REVIEW_STATUSES and row.get("match_status") in HIGH_PRIORITY_MATCH_STATUSES | {"plausible_match", "multiple_candidates"}:
            errors.append(f"Manual-review target produced an overconfident match: {row.get('reference_id', '')}")

    for row in batch_rows:
        local_file_id = row.get("local_file_id", "")
        manifest_row = manifest_by_id.get(local_file_id)
        if not manifest_row:
            errors.append(f"OCR batch row points to unknown local file id: {local_file_id}")
            continue
        status = row.get("status", "")
        blocked_by = row.get("blocked_by", "")
        runtime_available = row.get("runtime_path_available", "") == "true"
        if status == "ready_for_ocr" and blocked_by:
            errors.append(f"OCR batch row is ready_for_ocr but still blocked: {row.get('batch_id', '')}")
        if status == "ready_for_ocr" and not runtime_available:
            errors.append(f"OCR batch row is ready_for_ocr without runtime path availability: {row.get('batch_id', '')}")
        if status == "needs_runtime_path_cache" and runtime_available:
            errors.append(f"OCR batch row still waits on runtime cache despite runtime_path_available=true: {row.get('batch_id', '')}")
        if status == "needs_runtime_path_cache" and not blocked_by:
            errors.append(f"OCR batch row missing blocked_by reason for runtime-path wait: {row.get('batch_id', '')}")

    for row in status_rows:
        if row.get("batch_id") not in batch_by_id:
            errors.append(f"OCR status row points to unknown batch id: {row.get('batch_id', '')}")
        for key in ["output_path_stub", "metadata_sidecar_stub"]:
            value = row.get(key, "")
            if value and ABSOLUTE_PATH_PATTERN.search(value):
                errors.append(f"OCR status row commits an absolute path in {key}: {row.get('ocr_job_id', '')}")
        if row.get("output_path_stub", "").startswith("data/working/"):
            errors.append(f"OCR output path points inside committed working metadata: {row.get('ocr_job_id', '')}")

    for row in candidate_rows:
        if len(row.get("short_evidence_snippet", "")) > SHORT_SNIPPET_LIMIT:
            errors.append(f"Translation-candidate snippet too long: {row.get('candidate_id', '')}")
        if row.get("candidate_type") == "explicit_translation_heading" and not HEADING_TRANSLATION_PATTERN.search(row.get("short_evidence_snippet", "")):
            errors.append(f"Explicit translation candidate lacks heading-like evidence: {row.get('candidate_id', '')}")
        if not (row.get("local_file_id") or row.get("reference_id_if_any")):
            errors.append(f"Translation candidate lacks both local_file_id and reference_id_if_any: {row.get('candidate_id', '')}")
        if "review lead" not in row.get("notes", "").casefold():
            errors.append(f"Translation candidate note no longer marks the row as a review lead: {row.get('candidate_id', '')}")
        if not row.get("candidate_key", ""):
            errors.append(f"Translation candidate is missing candidate_key: {row.get('candidate_id', '')}")
        if not any(candidate_lookup_key(review_row) == candidate_lookup_key(row) for review_row in candidate_review_rows):
            errors.append(f"Translation candidate lacks a review row: {row.get('candidate_id', '')}")
    errors.extend(
        validate_translation_candidate_alignment(
            candidate_rows,
            candidate_review_rows,
            ocr_quality_review_rows,
            excerpt_review_rows,
            followup_source_lead_rows,
        )
    )

    extraction_plan_ids = set()
    extraction_plan_by_id: dict[str, dict[str, str]] = {}
    for row in extraction_plan_rows:
        extraction_plan_id = row.get("extraction_plan_id", "")
        if not extraction_plan_id:
            errors.append("Structured extraction plan row is missing extraction_plan_id.")
            continue
        if extraction_plan_id in extraction_plan_ids:
            errors.append(f"Structured extraction plan contains duplicate extraction_plan_id: {extraction_plan_id}")
        extraction_plan_ids.add(extraction_plan_id)
        extraction_plan_by_id[extraction_plan_id] = row
        if not row.get("source_text_language_or_script", "") or not row.get("translation_language", ""):
            errors.append(f"Structured extraction plan is missing language scope fields: {extraction_plan_id}")
        if row.get("burmese_relevance_status", "") not in {
            "direct_burmese_relevance",
            "mixed_burmese_pali_relevance",
            "related_non_burmese_pagan_source",
        }:
            errors.append(f"Structured extraction plan has invalid burmese_relevance_status: {extraction_plan_id}")
        if row.get("burmese_relevance_status", "") == "mixed_burmese_pali_relevance":
            language_scope = normalized_language_scope(row.get("source_text_language_or_script", ""))
            if "pali" not in language_scope or "burmese" not in language_scope:
                errors.append(f"Mixed-language extraction plan lacks explicit Pali/Burmese scope: {extraction_plan_id}")

    citation_priority_ids = set()
    for row in citation_priority_rows:
        priority_id = row.get("priority_id", "")
        if not priority_id:
            errors.append("Corpus citation priority row is missing priority_id.")
            continue
        if priority_id in citation_priority_ids:
            errors.append(f"Corpus citation priority queue contains duplicate priority_id: {priority_id}")
        citation_priority_ids.add(priority_id)
        local_file_id = row.get("candidate_local_file_id", "")
        if local_file_id and local_file_id not in manifest_by_id:
            errors.append(f"Corpus citation priority queue points to unknown local file id: {priority_id}")
        candidate_key = row.get("matched_jbrs_candidate_key", "")
        if candidate_key:
            candidate_row = candidate_by_key.get(candidate_key)
            if not candidate_row:
                errors.append(f"Corpus citation priority queue points to unknown candidate_key: {priority_id}")
            elif local_file_id and candidate_row.get("local_file_id", "") != local_file_id:
                errors.append(f"Corpus citation priority queue local_file_id does not match candidate log: {priority_id}")
        if row.get("burmese_relevance_status", "") not in {
            "direct_burmese_relevance",
            "mixed_burmese_pali_relevance",
            "related_non_burmese_pagan_source",
            "bibliography_only_lead",
        }:
            errors.append(f"Corpus citation priority queue has invalid burmese_relevance_status: {priority_id}")

    source_unit_ids = {
        row.get("source_text_unit_id", "")
        for row in extracted_source_text_unit_rows
        if row.get("source_text_unit_id", "")
    }

    for row in extracted_translation_unit_rows:
        if not row.get("translation_unit_id", ""):
            errors.append("Extracted translation unit row is missing translation_unit_id.")
        if not row.get("source_local_file_id", "") or not row.get("translation_text", ""):
            errors.append(f"Extracted translation unit is missing required content fields: {row.get('translation_unit_id', '')}")
        if not row.get("candidate_key", "") or row.get("candidate_key", "") not in candidate_by_key:
            errors.append(f"Extracted translation unit points to unknown candidate_key: {row.get('translation_unit_id', '')}")
        plan_row = extraction_plan_by_id.get(row.get("extraction_plan_id", ""))
        if not row.get("extraction_plan_id", "") or not plan_row:
            errors.append(f"Extracted translation unit points to unknown extraction_plan_id: {row.get('translation_unit_id', '')}")
        elif row.get("source_local_file_id", "") != plan_row.get("source_local_file_id", ""):
            errors.append(f"Extracted translation unit local_file_id disagrees with extraction plan: {row.get('translation_unit_id', '')}")
        if row.get("source_text_unit_id", "") and row.get("source_text_unit_id", "") not in source_unit_ids:
            errors.append(f"Extracted translation unit points to unknown source_text_unit_id: {row.get('translation_unit_id', '')}")
        if not row.get("source_language", "") or not row.get("translation_language", ""):
            errors.append(f"Extracted translation unit is missing language fields: {row.get('translation_unit_id', '')}")
        for field in ["is_burmese_relevant", "includes_pali", "includes_burmese", "includes_other_language"]:
            if row.get(field, "") not in {"true", "false"}:
                errors.append(f"Extracted translation unit has invalid boolean field {field}: {row.get('translation_unit_id', '')}")
        if row.get("excerpt_review_id", "") and row.get("excerpt_review_id", "") not in excerpt_review_by_id:
            errors.append(f"Extracted translation unit points to unknown excerpt_review_id: {row.get('translation_unit_id', '')}")
        if is_true(row.get("is_burmese_relevant", "")) and not (
            is_true(row.get("includes_burmese", "")) or (plan_row or {}).get("burmese_relevance_status", "") == "direct_burmese_relevance"
        ):
            errors.append(f"Extracted translation unit is marked Burmese-relevant without Burmese scope: {row.get('translation_unit_id', '')}")
        if (
            is_true(row.get("includes_pali", ""))
            and not is_true(row.get("includes_burmese", ""))
            and not is_true(row.get("includes_other_language", ""))
            and is_true(row.get("is_burmese_relevant", ""))
        ):
            errors.append(f"Pali-only extracted translation unit is incorrectly marked Burmese-relevant: {row.get('translation_unit_id', '')}")
        if (plan_row or {}).get("burmese_relevance_status", "") == "mixed_burmese_pali_relevance":
            if not is_true(row.get("includes_pali", "")) or not is_true(row.get("includes_burmese", "")):
                if "version-specific" not in row.get("notes", "").casefold():
                    errors.append(f"Mixed-language extraction plan lacks mixed or version-specific translation-unit scope: {row.get('translation_unit_id', '')}")
        if row.get("review_status", "") == "verified_translation_coverage":
            if not row.get("inscription_or_text_id", ""):
                errors.append(f"Verified extracted translation unit lacks inscription_or_text_id linkage: {row.get('translation_unit_id', '')}")
            if (plan_row or {}).get("needs_manual_source_linkage", "") == "true":
                errors.append(f"Verified extracted translation unit still points to a plan needing manual source linkage: {row.get('translation_unit_id', '')}")

    for row in extracted_source_text_unit_rows:
        if not row.get("source_text_unit_id", ""):
            errors.append("Extracted source-text unit row is missing source_text_unit_id.")
        if not row.get("source_local_file_id", "") or not row.get("source_text", ""):
            errors.append(f"Extracted source-text unit is missing required content fields: {row.get('source_text_unit_id', '')}")
        if not row.get("candidate_key", "") or row.get("candidate_key", "") not in candidate_by_key:
            errors.append(f"Extracted source-text unit points to unknown candidate_key: {row.get('source_text_unit_id', '')}")
        plan_row = extraction_plan_by_id.get(row.get("extraction_plan_id", ""))
        if not row.get("extraction_plan_id", "") or not plan_row:
            errors.append(f"Extracted source-text unit points to unknown extraction_plan_id: {row.get('source_text_unit_id', '')}")
        elif row.get("source_local_file_id", "") != plan_row.get("source_local_file_id", ""):
            errors.append(f"Extracted source-text unit local_file_id disagrees with extraction plan: {row.get('source_text_unit_id', '')}")
        if row.get("excerpt_review_id", "") and row.get("excerpt_review_id", "") not in excerpt_review_by_id:
            errors.append(f"Extracted source-text unit points to unknown excerpt_review_id: {row.get('source_text_unit_id', '')}")
        if not row.get("source_language", ""):
            errors.append(f"Extracted source-text unit is missing source_language: {row.get('source_text_unit_id', '')}")
        if is_true(row.get("is_burmese_relevant", "")) and not (
            "burmese" in normalized_language_scope(row.get("source_language", ""))
            or (plan_row or {}).get("burmese_relevance_status", "") == "direct_burmese_relevance"
        ):
            errors.append(f"Extracted source-text unit is marked Burmese-relevant without Burmese or direct-relevance scope: {row.get('source_text_unit_id', '')}")
        if is_pali_only_language_scope(row.get("source_language", "")) and is_true(row.get("is_burmese_relevant", "")):
            errors.append(f"Pali-only extracted source-text unit is incorrectly marked Burmese-relevant: {row.get('source_text_unit_id', '')}")
        if (plan_row or {}).get("burmese_relevance_status", "") == "mixed_burmese_pali_relevance":
            source_language = normalized_language_scope(row.get("source_language", ""))
            if "pali" not in source_language or "burmese" not in source_language:
                if "version-specific" not in row.get("notes", "").casefold():
                    errors.append(f"Mixed-language extraction plan lacks mixed or version-specific source-unit scope: {row.get('source_text_unit_id', '')}")
        if row.get("review_status", "") == "verified_translation_coverage":
            if not row.get("inscription_or_text_id", ""):
                errors.append(f"Verified extracted source-text unit lacks inscription_or_text_id linkage: {row.get('source_text_unit_id', '')}")
            if (plan_row or {}).get("needs_manual_source_linkage", "") == "true":
                errors.append(f"Verified extracted source-text unit still points to a plan needing manual source linkage: {row.get('source_text_unit_id', '')}")

    for row in manifest_rows:
        for key in ["path_stub_or_redacted_path"]:
            if ABSOLUTE_PATH_PATTERN.search(row.get(key, "")):
                errors.append(f"Committed manifest stores an absolute path: {row.get('local_file_id', '')}")

    errors.extend(
        validate_corpus_citation_workflow(
            inventory_rows=citation_inventory_rows,
            target_rows=citation_target_rows,
            source_match_rows=citation_source_match_rows,
            source_match_review_rows=citation_source_match_review_rows,
            dashboard_rows=citation_dashboard_rows,
            out_of_scope_audit_rows=citation_out_of_scope_audit_rows,
            ocr_queue_rows=citation_ocr_queue_rows,
            extracted_translation_unit_rows=extracted_translation_unit_rows,
            extracted_source_text_unit_rows=extracted_source_text_unit_rows,
            summary=citation_workflow_summary,
        )
    )

    if "Berkeley IOB catalogue record is not a verified local witness" not in readme_text:
        errors.append("JBRS README is missing the Berkeley/IOB non-promotion guardrail.")
    if "IOB plate portfolios are not the missing companion text witness" not in readme_text:
        errors.append("JBRS README is missing the IOB plates guardrail.")
    if "SIP does not satisfy the separate UEM witness gap" not in readme_text:
        errors.append("JBRS README is missing the SIP/UEM guardrail.")

    summary_expected = build_pilot_summary(
        raw_rows,
        target_rows,
        manifest_rows,
        match_rows,
        batch_rows,
        status_rows,
        candidate_rows,
        candidate_review_rows,
        excerpt_review_rows,
        followup_source_lead_rows,
        ocr_quality_review_rows,
        citation_priority_rows,
        extraction_plan_rows,
        extracted_translation_unit_rows,
        extracted_source_text_unit_rows,
    )
    if summary != summary_expected:
        errors.append("JBRS pilot summary counts do not match the generated artifacts.")
    errors.extend(validate_repo_ocr_artifacts())

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
        JBRS_OCR_QUALITY_REVIEW_PATH,
        JBRS_EMBEDDED_TRANSLATION_EXCERPT_REVIEW_PATH,
        JBRS_FOLLOWUP_SOURCE_LEADS_PATH,
        JBRS_CORPUS_CITATION_PRIORITY_QUEUE_PATH,
        JBRS_STRUCTURED_EXTRACTION_PLAN_PATH,
        JBRS_EXTRACTED_TRANSLATION_UNITS_PATH,
        JBRS_EXTRACTED_SOURCE_TEXT_UNITS_PATH,
        JBRS_OCR_PRODUCTION_RUN_LOG_PATH,
        JBRS_OCR_TEXT_INDEX_PATH,
        JBRS_OCR_TRANSLATION_HIT_INDEX_PATH,
        JBRS_OCR_TOP_EXTRACTION_CANDIDATES_PATH,
        JBRS_OCR_TOP_INSCRIPTION_EXTRACTION_CANDIDATES_PATH,
        JBRS_OCR_PRODUCTION_SUMMARY_PATH,
        JBRS_FILE_RENAMING_PLAN_PATH,
        JBRS_FILE_ALIAS_MAP_PATH,
        CORPUS_CITATION_INVENTORY_PATH,
        CORPUS_CITATION_TARGETS_PATH,
        CORPUS_CITATION_SOURCE_FILE_MATCH_PATH,
        CORPUS_TRANSLATION_SOURCE_DASHBOARD_PATH,
        CORPUS_CITED_SOURCE_OCR_QUEUE_PATH,
    ]:
        text = path.read_text(encoding="utf-8")
        if ABSOLUTE_PATH_PATTERN.search(text):
            errors.append(f"Committed JBRS artifact includes an absolute path: {path.relative_to(REPO_ROOT)}")
        if "GOOGLE_APPLICATION_CREDENTIALS" in text or "-----BEGIN PRIVATE KEY-----" in text:
            errors.append(f"Committed JBRS artifact includes Google credential material: {path.relative_to(REPO_ROOT)}")

    tracked_local_outputs = tracked_files_under("data_local/ocr/jbrs")
    if tracked_local_outputs:
        errors.append(f"Tracked local OCR outputs must not be committed: {', '.join(tracked_local_outputs[:5])}")
    if tracked_files_under("data_local/ocr/jbrs/manifest/jbrs_runtime_path_map.json"):
        errors.append("JBRS runtime path cache must not be committed.")

    if not build_gitignore_has_data_local():
        errors.append(".gitignore does not protect data_local/ OCR outputs.")

    return errors
