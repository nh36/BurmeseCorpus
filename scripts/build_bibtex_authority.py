from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

from bibtex_common import (
    make_bibtex_key,
    normalize_for_match,
    surname_token,
    title_keyword_tokens,
    write_bibtex,
)
from corpus_common import read_tsv, write_tsv
from extract_bibliography_acronyms import (
    MAX_STRONG_DEFINITION_QUOTE_LENGTH,
    PRIORITY_ACRONYMS,
    STRONG_DEFINITION_EVIDENCE_TYPES,
)


AUTHORITY_FIELDS = [
    "bibtex_key",
    "entry_type",
    "authority_status",
    "source_of_authority",
    "matched_external_key",
    "matched_local_source_id",
    "matched_local_source_file",
    "matched_local_reference",
    "match_confidence",
    "match_reason",
    "evidence_id",
    "short_evidence_note",
    "human_review_flag",
    "resolution_status",
    "resolution_level",
    "source_family_id",
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
]

CROSSWALK_FIELDS = [
    "raw_reference_string",
    "family_id",
    "source_family_id",
    "source_work_key",
    "work_candidate_id",
    "bibtex_key",
    "locator",
    "locator_type",
    "resolution_status",
    "resolution_level",
    "match_type",
    "match_confidence",
    "evidence",
    "needs_human_review",
    "notes",
]

HIGH_FREQUENCY_FIELDS = [
    "family_id",
    "family_label",
    "family_type",
    "member_count",
    "occurrence_count",
    "sample_raw_references",
    "current_bibtex_key",
    "current_status",
    "suggested_local_search_terms",
    "notes",
]

EVIDENCE_FIELDS = [
    "source_family_id",
    "bibtex_key",
    "evidence_id",
    "evidence_type",
    "source_file_id",
    "source_file_label",
    "source_ref_id",
    "short_evidence",
    "full_evidence_hash",
    "confidence",
    "notes",
]

RESOLUTION_PLAN_FIELDS = [
    "family_id",
    "family_label",
    "family_type",
    "occurrence_count",
    "sample_raw_references",
    "resolution_status",
    "resolution_level",
    "authority_key",
    "needs_human_review",
    "evidence_id",
    "evidence_source",
    "evidence_confidence",
    "next_action",
    "notes",
]

SOURCE_FAMILY_FIELDS = [
    "source_family_id",
    "abbreviation",
    "family_id",
    "authority_key",
    "alias_of_source_family_id",
    "source_work_key",
    "related_source_work_key",
    "source_family_type",
    "resolution_status",
    "resolution_level",
    "canonical_label",
    "expanded_label",
    "acronym_resolution_status",
    "definition_quality",
    "best_definition_evidence_id",
    "best_definition_source",
    "best_definition_quote",
    "related_bibtex_key",
    "locator_pattern",
    "locator_type",
    "example_raw_references",
    "evidence_id",
    "evidence_source",
    "confidence",
    "needs_human_review",
    "notes",
]

ACRONYM_STATUS_FIELDS = [
    "acronym",
    "current_expansion",
    "current_authority_key",
    "source_family_id",
    "resolution_status",
    "definition_quality",
    "best_evidence_source",
    "best_evidence_id",
    "best_evidence_quote",
    "confidence",
    "needs_human_review",
    "next_action",
    "notes",
]

SEED_FIELDS = [
    "abbreviation",
    "family_id",
    "family_type",
    "provisional_label",
    "probable_bibtex_key",
    "source_type",
    "evidence_source_file",
    "evidence_ref_id",
    "evidence_quote_short",
    "confidence",
    "needs_human_review",
    "notes",
]
MANUAL_ACRONYM_SEED_FIELDS = [
    "acronym",
    "expansion",
    "authority_key",
    "source_family_id",
    "confidence",
    "supplied_by",
    "date_added",
    "needs_documentary_confirmation",
    "notes",
]
MANUAL_REVIEW_PACKET_FIELDS = [
    "acronym",
    "current_status",
    "current_expansion",
    "best_evidence_source",
    "best_evidence_quote",
    "manual_seed",
    "ocr_sources_checked",
    "new_ocr_hits",
    "candidate_expansions",
    "recommended_resolution",
    "confidence",
    "needs_human_review",
    "notes",
]
REMAINING_ACRONYM_WORKLIST_FIELDS = [
    "acronym",
    "current_status",
    "current_expansion",
    "source_family_id",
    "occurrence_count",
    "top_example_references",
    "likely_source_type",
    "best_current_evidence",
    "specific_files_to_check",
    "specific_search_terms",
    "recommended_action",
    "notes",
]
REMAINING_ACRONYM_EVIDENCE_FIELDS = [
    "acronym",
    "candidate_expansion",
    "evidence_type",
    "source_file_id",
    "source_file_label",
    "source_location_hint",
    "short_quote",
    "evidence_strength",
    "supports_expansion",
    "contradicts_expansion",
    "needs_human_review",
    "notes",
]
SOURCE_WORK_LOCATOR_SYSTEM_FIELDS = [
    "source_work_key",
    "source_work_title",
    "source_family_ids",
    "locator_system",
    "locator_prefixes",
    "locator_type",
    "example_references",
    "bibtex_key",
    "authority_status",
    "needs_human_review",
    "alias_or_variant_notes",
    "notes",
]
SOURCE_WORK_AUTHORITY_FIELDS = [
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
RAW_REFERENCE_CROSSWALK_AUDIT_FIELDS = [
    "raw_reference_string",
    "family_id",
    "source_family_id",
    "source_work_key",
    "bibtex_key",
    "locator",
    "locator_type",
    "issue_type",
    "issue_category",
    "status",
    "severity",
    "auto_fixable",
    "human_review_required",
    "recommended_fix",
    "notes",
]
SOURCE_WORK_AUTHORITY_AUDIT_FIELDS = [
    "source_work_key",
    "canonical_title",
    "related_source_family_ids",
    "issue_type",
    "status",
    "open_issue",
    "resolved_by_key_normalization",
    "severity",
    "recommended_action",
    "merge_target_key",
    "notes",
]
SOURCE_WORK_TO_BIBTEX_RECONCILIATION_FIELDS = [
    "source_work_key",
    "canonical_title",
    "authority_level",
    "should_have_bibtex",
    "current_bibtex_key",
    "bibtex_status",
    "reason",
    "recommended_action",
    "notes",
]
BIBTEX_FIELD_QUALITY_AUDIT_FIELDS = [
    "bibtex_key",
    "field_name",
    "field_value_short",
    "issue_type",
    "severity",
    "recommended_fix",
    "notes",
]
BIBTEX_FIELD_QUALITY_AUDIT_HISTORY_FIELDS = [
    "bibtex_key",
    "field_name",
    "field_value_short",
    "issue_type",
    "severity",
    "status",
    "resolved_in_commit",
    "remaining_issue",
    "recommended_fix",
    "notes",
]
AUTHORITY_KEY_NORMALIZATION_FIELDS = [
    "old_key",
    "new_key",
    "object_type",
    "reason",
    "migration_action",
    "notes",
]
CANDIDATE_STUB_REVIEW_FIELDS = [
    "candidate_key",
    "candidate_label",
    "occurrence_count",
    "current_status",
    "review_decision",
    "reason",
    "next_action",
    "notes",
]
FINAL_ACRONYM_RESOLUTION_SPRINT_FIELDS = [
    "acronym",
    "current_status",
    "current_examples",
    "working_hypothesis",
    "hypothesis_source",
    "search_strategy",
    "local_files_searched",
    "internet_queries_run",
    "best_evidence_found",
    "candidate_expansion",
    "recommended_status",
    "confidence",
    "needs_human_review",
    "notes",
]
FINAL_ACRONYM_LOCAL_FILE_HITS_FIELDS = [
    "acronym",
    "search_term",
    "file_or_folder_name",
    "path_or_redacted_path",
    "file_type",
    "sha256_if_available",
    "match_reason",
    "copied_or_existing_cache_path",
    "extraction_status",
    "notes",
]
FINAL_ACRONYM_WEB_SEARCHES_FIELDS = [
    "acronym",
    "query",
    "result_title",
    "result_url_or_domain",
    "short_result_summary",
    "supports_candidate_expansion",
    "confidence",
    "notes",
]
FRASCH_ABBREVIATION_LIST_REVIEW_FIELDS = [
    "line_range",
    "acronyms_found",
    "raw_excerpt_short",
    "possible_missing_acronyms",
    "notes",
]
UNRESOLVED_ACRONYM_DOSSIER_FIELDS = [
    "acronym",
    "final_status",
    "best_hypothesis",
    "hypothesis_confidence",
    "evidence_summary",
    "files_checked",
    "web_queries_checked",
    "why_not_confirmed",
    "recommended_human_action",
    "notes",
]
IPPA_OCCURRENCE_CONTEXT_FIELDS = [
    "occurrence_id",
    "record_id",
    "source_deposit",
    "source_layer",
    "source_volume",
    "source_inscription_number",
    "title_original",
    "raw_reference_string",
    "full_references_original",
    "neighboring_reference_before",
    "neighboring_reference_after",
    "parsed_locator",
    "line_or_record_context",
    "notes",
]
IPPA_PPA_COMPARISON_FIELDS = [
    "ippa_reference",
    "ppa_like_reference",
    "shared_record_id",
    "same_or_neighboring_reference_field",
    "locator_pattern",
    "source_context",
    "looks_like_alias",
    "looks_like_typo",
    "looks_like_distinct_source",
    "confidence",
    "notes",
]
IPPA_LOCAL_CONTEXT_SEARCH_FIELDS = [
    "query",
    "matched_file_id",
    "matched_file_label",
    "match_location",
    "short_context_before",
    "match_text",
    "short_context_after",
    "evidence_type",
    "supports_alias_of_ppa",
    "supports_distinct_expansion",
    "supports_typo",
    "confidence",
    "notes",
]
IPPA_FRASCH_ABBREV_NEIGHBOURHOOD_FIELDS = [
    "source_file",
    "line_range",
    "excerpt_short",
    "contains_ppa",
    "contains_ippa",
    "contains_related_abbreviations",
    "interpretation",
    "notes",
]
IPPA_RECORD_REVIEW_FIELDS = [
    "record_id",
    "title_original",
    "references_original",
    "other_sources_cited",
    "IPPA_locator",
    "parallel_OBI_or_List_or_PPA_reference",
    "likely_source_relationship",
    "review_decision",
    "confidence",
    "notes",
]
IPPA_TARGETED_OCR_NOTES_FIELDS = [
    "source_file_id",
    "source_file_label",
    "reason_for_targeting",
    "page_or_region",
    "ocr_attempted",
    "ocr_success",
    "short_result",
    "supports_resolution",
    "notes",
]
IPPA_RESOLUTION_DECISION_FIELDS = [
    "decision",
    "expansion_or_classification",
    "confidence",
    "evidence_summary",
    "occurrences_reviewed",
    "local_contexts_reviewed",
    "frasch_neighbourhood_reviewed",
    "record_contexts_reviewed",
    "web_queries_reviewed",
    "remaining_uncertainty",
    "recommended_authority_update",
    "notes",
]

STATUS_RANK = {
    "confirmed_external_bibtex": 5,
    "confirmed_local_source": 4,
    "provisional_local_source": 3,
    "provisional_catalogue": 2,
    "provisional_publication": 2,
    "needs_human_review": 1,
}

TOP_FAMILY_REVIEW_COUNT = 25
MAX_BIBTEX_EVIDENCE_LENGTH = 180
MAX_MATCHED_REFERENCE_LENGTH = 140
DEFAULT_CORPUS_RELEASE_INSCRIPTIONS_PATH = Path("data/release/corpus_release_v0_3/inscriptions.jsonl")
DEFAULT_REFERENCE_OCCURRENCES_PATH = Path("data/working/bibliography/reference_occurrences.tsv")
DEFAULT_RAW_REFERENCES_PATH = Path("data/working/bibliography/raw_references.tsv")
DEFAULT_FRASCH_EXTRACTED_TEXT_PATH = Path("data/working/bibliography/local_sources/frasch_extracted_text.txt")
REMAINING_ACRONYMS = ["IOB", "TN", "UEM", "RDASB", "MP", "OR", "Luce J", "Luce D", "IPPA"]
FINAL_SPRINT_ACRONYMS = ["RDASB", "MP", "OR", "Luce J", "Luce D", "IPPA"]
PLACEHOLDER_EXPANSION_PATTERN = re.compile(
    r"\b(source family|catalogue family|publication family|series family|source family attested|unexpanded)\b",
    re.IGNORECASE,
)

RESOLUTION_STATUSES = {
    "unresolved",
    "alias_resolved",
    "alias_or_variant_of_PPA",
    "source_family_resolved",
    "series_level_resolved",
    "work_level_resolved",
    "confirmed_work",
    "provisional_work",
    "needs_human_review",
}

RESOLUTION_LEVELS = {
    "raw_locator",
    "abbreviation",
    "source_family",
    "series",
    "work",
    "article",
    "book",
    "internal_reference",
    "unknown",
}

GENERIC_MATCH_TOKENS = {
    "burma",
    "burmese",
    "myanmar",
    "pagan",
    "bagan",
    "inscription",
    "inscriptions",
    "history",
    "article",
    "study",
    "old",
    "first",
    "report",
    "references",
}

SOURCE_FAMILY_LIBRARY = {
    "list": {
        "author": "Charles Duroiselle",
        "year": "1921",
        "title": "List of Inscriptions Found in Burma",
        "shorttitle": "List",
        "entry_type": "book",
        "preferred_key": "duroiselle1921list",
        "local_search_terms": ["list of inscriptions"],
        "frasch_search_terms": ["list"],
    },
    "iob": {
        "author": "G. H. Luce and U Pe Maung Tin",
        "year": "",
        "title": "Inscriptions of Burma",
        "shorttitle": "IOB",
        "entry_type": "book",
        "preferred_key": "lucePeMaungTinInscriptionsOfBurma",
        "local_search_terms": ["inscriptions of burma"],
        "frasch_search_terms": ["iob"],
    },
    "obi": {
        "author": "Tilman Frasch",
        "year": "",
        "title": "Old Burmese Inscriptions structured corpus",
        "shorttitle": "OBI",
        "entry_type": "misc",
        "preferred_key": "obiCorpusSource",
        "local_search_terms": ["old burmese inscriptions", "bagan epig database"],
        "frasch_search_terms": ["obi", "old burmese inscriptions"],
    },
    "bed b": {
        "author": "Tilman Frasch",
        "year": "",
        "title": "Bagan Epigraphic Database, Part B",
        "shorttitle": "BED B",
        "entry_type": "misc",
        "preferred_key": "fraschBaganEpigraphicDatabasePartB",
        "local_search_terms": ["bagan epig database", "bagan epigraphic database"],
        "frasch_search_terms": ["bed b", "bagan epig database"],
    },
    "a": {
        "author": "Tilman Frasch",
        "year": "",
        "title": "Bagan Epigraphic Database, Part A",
        "shorttitle": "A",
        "entry_type": "misc",
        "preferred_key": "fraschBaganEpigraphicDatabasePartA",
        "local_search_terms": ["bagan epig database", "bagan epigraphic database"],
        "frasch_search_terms": [" a, p.", "bagan epig database"],
    },
    "b": {
        "author": "Tilman Frasch",
        "year": "",
        "title": "Bagan Epigraphic Database, Part B",
        "shorttitle": "B",
        "entry_type": "misc",
        "preferred_key": "fraschBaganEpigraphicDatabasePartBShort",
        "local_search_terms": ["bagan epig database", "bagan epigraphic database"],
        "frasch_search_terms": [" b 1", " b 2", "bagan epig database"],
    },
    "mp": {
        "author": "",
        "year": "",
        "title": "Mandalay Palace stone collection locator system",
        "shorttitle": "MP",
        "entry_type": "misc",
        "preferred_key": "mpSourceFamily",
        "local_search_terms": [],
        "frasch_search_terms": ["mp"],
    },
    "ub": {
        "author": "",
        "year": "",
        "title": "Inscriptions Collected in Upper Burma",
        "shorttitle": "UB",
        "entry_type": "misc",
        "preferred_key": "ubSourceFamily",
        "local_search_terms": [],
        "frasch_search_terms": ["ub"],
    },
    "uem": {
        "author": "U E Maung",
        "year": "1958",
        "title": "Selections from the Inscriptions of Pagan",
        "shorttitle": "UEM",
        "entry_type": "book",
        "preferred_key": "uEMaung1958selectionsInscriptionsPagan",
        "local_search_terms": [],
        "frasch_search_terms": ["uem"],
    },
    "ppa": {
        "author": "",
        "year": "",
        "title": "Inscriptions of Pagan, Pinya and Ava",
        "shorttitle": "PPA",
        "entry_type": "misc",
        "preferred_key": "ppaCatalogue",
        "local_search_terms": [],
        "frasch_search_terms": ["ppa"],
    },
    "tn": {
        "author": "U Tun Nyein",
        "year": "1897",
        "title": "Inscriptions of Pagan, Pinya and Ava",
        "shorttitle": "TN",
        "entry_type": "book",
        "preferred_key": "uTunNyein1897inscriptionsPaganPinyaAva",
        "local_search_terms": ["u tun nyein", "inscriptions of pagan pinya and ava"],
        "frasch_search_terms": ["tn", "u tun nyein"],
    },
    "jbrs": {
        "author": "",
        "year": "",
        "title": "Journal of the Burma Research Society",
        "shorttitle": "JBRS",
        "entry_type": "periodical",
        "preferred_key": "journalBurmaResearchSociety",
        "local_search_terms": ["jbrs", "burma jbrs"],
        "frasch_search_terms": ["jbrs"],
    },
    "bbhc": {
        "author": "",
        "year": "",
        "title": "Bulletin of the Burma Historical Commission",
        "shorttitle": "BBHC",
        "entry_type": "periodical",
        "preferred_key": "burmaHistoricalCommissionBulletin",
        "local_search_terms": [],
        "frasch_search_terms": ["bbhc"],
    },
    "jras": {
        "author": "",
        "year": "",
        "title": "Journal of the Royal Asiatic Society",
        "shorttitle": "JRAS",
        "entry_type": "periodical",
        "preferred_key": "journalRoyalAsiaticSociety",
        "local_search_terms": ["jras"],
        "frasch_search_terms": ["jras"],
    },
    "rdasb": {
        "author": "",
        "year": "",
        "title": "Report of the Director, Archaeological Survey of Burma",
        "shorttitle": "RDASB",
        "entry_type": "misc",
        "preferred_key": "rdasbSourceFamily",
        "local_search_terms": [],
        "frasch_search_terms": ["rdasb"],
    },
    "eb": {
        "author": "",
        "year": "",
        "title": "Epigraphia Birmanica",
        "shorttitle": "EB",
        "entry_type": "periodical",
        "preferred_key": "epigraphiaBirmanica",
        "local_search_terms": ["epigraphia birmanica"],
        "frasch_search_terms": ["eb", "epigraphia birmanica"],
    },
    "pl": {
        "author": "",
        "year": "",
        "title": "Plate reference into Inscriptions of Burma",
        "shorttitle": "Pl.",
        "entry_type": "misc",
        "preferred_key": "obiPlateReferenceSystem",
        "local_search_terms": [],
        "frasch_search_terms": ["pl."],
    },
    "u min hswe": {
        "author": "U Min Hswe",
        "year": "",
        "title": "U Min Hswe source family",
        "shorttitle": "U Min Hswe",
        "entry_type": "misc",
        "preferred_key": "uMinHsweSourceFamily",
        "local_search_terms": ["u min hswe"],
        "frasch_search_terms": ["u min hswe"],
    },
    "ippa": {
        "author": "",
        "year": "",
        "title": "IPPA variant locator family into Inscriptions of Pagan, Pinya and Ava",
        "shorttitle": "IPPA",
        "entry_type": "misc",
        "preferred_key": "ippaSourceFamily",
        "local_search_terms": [],
        "frasch_search_terms": ["ippa"],
    },
    "sip": {
        "author": "",
        "year": "",
        "title": "SIP source family",
        "shorttitle": "SIP",
        "entry_type": "misc",
        "preferred_key": "sipSourceFamily",
        "local_search_terms": [],
        "frasch_search_terms": ["sip"],
    },
    "mm": {
        "author": "",
        "year": "",
        "title": "MM source family",
        "shorttitle": "MM",
        "entry_type": "misc",
        "preferred_key": "mmSourceFamily",
        "local_search_terms": [],
        "frasch_search_terms": ["mm"],
    },
    "or": {
        "author": "",
        "year": "",
        "title": "British Library Oriental manuscript shelfmark system",
        "shorttitle": "OR",
        "entry_type": "misc",
        "preferred_key": "orSourceFamily",
        "local_search_terms": [],
        "frasch_search_terms": ["or"],
    },
    "arasi": {
        "author": "",
        "year": "",
        "title": "Annual Report of the Archaeological Survey of India",
        "shorttitle": "ARASI",
        "entry_type": "periodical",
        "preferred_key": "annualReportArchaeologicalSurveyIndia",
        "local_search_terms": ["archaeological survey of india"],
        "frasch_search_terms": ["arasi"],
    },
    "luce d": {
        "author": "G. H. Luce",
        "year": "",
        "title": "G. H. Luce Notebook D locator system",
        "shorttitle": "Luce D",
        "entry_type": "misc",
        "preferred_key": "luceDictionarySourceFamily",
        "local_search_terms": ["luce"],
        "frasch_search_terms": ["luce d"],
    },
    "luce j": {
        "author": "G. H. Luce",
        "year": "",
        "title": "G. H. Luce Notebook J locator system",
        "shorttitle": "Luce J",
        "entry_type": "misc",
        "preferred_key": "luceJournalSourceFamily",
        "local_search_terms": ["luce"],
        "frasch_search_terms": ["luce j"],
    },
}

SOURCE_FAMILY_SEMANTICS = {
    "list": {
        "source_family_id": "sf-list",
        "abbreviation": "List",
        "canonical_family_id": "fam-list-catalogue",
        "family_prefixes": ["fam-raw-list-"],
        "source_family_type": "catalogue",
        "resolution_status": "confirmed_work",
        "resolution_level": "book",
        "locator_pattern": "catalogue_number",
        "confidence": "high",
        "needs_human_review": "false",
        "notes": "List references resolve directly to Duroiselle 1921 plus a catalogue-number locator.",
    },
    "iob": {
        "source_family_id": "sf-iob",
        "abbreviation": "IOB",
        "canonical_family_id": "fam-iob-catalogue",
        "family_prefixes": ["fam-raw-iob"],
        "source_family_type": "catalogue",
        "resolution_status": "confirmed_work",
        "resolution_level": "book",
        "locator_pattern": "catalogue_number",
        "confidence": "medium",
        "needs_human_review": "true",
        "notes": "IOB behaves as a known work family with number-based locators.",
    },
    "obi": {
        "source_family_id": "sf-obi",
        "abbreviation": "OBI",
        "canonical_family_id": "fam-obi-internal",
        "source_family_type": "corpus_internal",
        "resolution_status": "source_family_resolved",
        "resolution_level": "internal_reference",
        "locator_pattern": "volume_page",
        "confidence": "high",
        "needs_human_review": "false",
        "notes": "OBI is an internal corpus citation system, not an external bibliographic work.",
    },
    "bed b": {
        "source_family_id": "sf-bed-b",
        "abbreviation": "BED B",
        "canonical_family_id": "fam-bed-b-catalogue",
        "source_family_type": "catalogue",
        "resolution_status": "source_family_resolved",
        "resolution_level": "source_family",
        "locator_pattern": "volume_page",
        "confidence": "medium",
        "needs_human_review": "true",
        "notes": "Bagan Epigraphic Database part B references are stable source-family citations pending fuller work-level normalization.",
    },
    "a": {
        "source_family_id": "sf-a",
        "abbreviation": "A",
        "canonical_family_id": "fam-raw-a",
        "family_prefixes": ["fam-raw-a-"],
        "source_family_type": "catalogue",
        "resolution_status": "source_family_resolved",
        "resolution_level": "abbreviation",
        "locator_pattern": "page",
        "confidence": "medium",
        "needs_human_review": "true",
        "notes": "A is a stable abbreviation family for Bagan Epigraphic Database part A style references.",
    },
    "b": {
        "source_family_id": "sf-b",
        "abbreviation": "B",
        "canonical_family_id": "fam-raw-b",
        "family_prefixes": ["fam-raw-b-"],
        "source_family_type": "catalogue",
        "resolution_status": "source_family_resolved",
        "resolution_level": "abbreviation",
        "locator_pattern": "volume_page",
        "confidence": "medium",
        "needs_human_review": "true",
        "notes": "B is kept as a stable abbreviation family rather than an ordinary work-level citation.",
    },
    "mp": {
        "source_family_id": "sf-mp",
        "abbreviation": "MP",
        "canonical_family_id": "fam-raw-mp",
        "family_prefixes": ["fam-raw-mp-"],
        "source_family_type": "catalogue",
        "resolution_status": "source_family_resolved",
        "resolution_level": "abbreviation",
        "locator_pattern": "volume_page",
        "confidence": "medium",
        "needs_human_review": "true",
        "notes": "MP references are stable enough to keep as a source-family abbreviation with locators.",
    },
    "ub": {
        "source_family_id": "sf-ub",
        "abbreviation": "UB",
        "canonical_family_id": "fam-raw-ub",
        "family_prefixes": ["fam-raw-ub-"],
        "source_family_type": "catalogue",
        "resolution_status": "source_family_resolved",
        "resolution_level": "abbreviation",
        "locator_pattern": "volume_page",
        "confidence": "medium",
        "needs_human_review": "true",
        "notes": "UB references are preserved as a stable source-family abbreviation with locators.",
    },
    "uem": {
        "source_family_id": "sf-uem",
        "abbreviation": "UEM",
        "canonical_family_id": "fam-uem-catalogue",
        "source_family_type": "catalogue",
        "resolution_status": "source_family_resolved",
        "resolution_level": "source_family",
        "locator_pattern": "page",
        "confidence": "medium",
        "needs_human_review": "true",
        "notes": "UEM is stable enough to model as a source family even though the full expansion remains provisional.",
    },
    "ppa": {
        "source_family_id": "sf-ppa",
        "abbreviation": "PPA",
        "canonical_family_id": "fam-ppa-catalogue",
        "source_family_type": "catalogue",
        "resolution_status": "source_family_resolved",
        "resolution_level": "source_family",
        "locator_pattern": "page",
        "confidence": "medium",
        "needs_human_review": "true",
        "notes": "Stable abbreviation family with page locators; exact work expansion remains provisional.",
    },
    "tn": {
        "source_family_id": "sf-tn",
        "abbreviation": "TN",
        "canonical_family_id": "fam-tn-catalogue",
        "source_family_type": "catalogue",
        "resolution_status": "source_family_resolved",
        "resolution_level": "source_family",
        "locator_pattern": "page",
        "confidence": "medium",
        "needs_human_review": "true",
        "notes": "TN behaves as a stable catalogue/source-family shorthand with locators.",
    },
    "u min hswe": {
        "source_family_id": "sf-u-min-hswe",
        "abbreviation": "U Min Hswe",
        "canonical_family_id": "fam-u-min-hswe-catalogue",
        "source_family_type": "catalogue",
        "resolution_status": "source_family_resolved",
        "resolution_level": "source_family",
        "locator_pattern": "page",
        "confidence": "medium",
        "needs_human_review": "true",
        "notes": "References identify a stable U Min Hswe source family, but the exact work boundary still needs confirmation.",
    },
    "jbrs": {
        "source_family_id": "sf-jbrs",
        "abbreviation": "JBRS",
        "canonical_family_id": "fam-jbrs-publication",
        "source_family_type": "periodical",
        "resolution_status": "series_level_resolved",
        "resolution_level": "series",
        "locator_pattern": "series_year_page",
        "confidence": "high",
        "needs_human_review": "false",
        "notes": "Journal of the Burma Research Society is resolved at the series level; article-level normalization is deferred.",
    },
    "bbhc": {
        "source_family_id": "sf-bbhc",
        "abbreviation": "BBHC",
        "canonical_family_id": "fam-bbhc-publication",
        "source_family_type": "periodical",
        "resolution_status": "series_level_resolved",
        "resolution_level": "series",
        "locator_pattern": "series_year_page",
        "confidence": "medium",
        "needs_human_review": "true",
        "notes": "Treat BBHC as a series-level source family until article-level normalization is added.",
    },
    "jras": {
        "source_family_id": "sf-jras",
        "abbreviation": "JRAS",
        "canonical_family_id": "fam-jras-publication",
        "source_family_type": "periodical",
        "resolution_status": "series_level_resolved",
        "resolution_level": "series",
        "locator_pattern": "series_year_page",
        "confidence": "high",
        "needs_human_review": "false",
        "notes": "Journal of the Royal Asiatic Society is resolved at the series level; article-level normalization is deferred.",
    },
    "rdasb": {
        "source_family_id": "sf-rdasb",
        "abbreviation": "RDASB",
        "canonical_family_id": "fam-rdasb-publication",
        "source_family_type": "periodical",
        "resolution_status": "series_level_resolved",
        "resolution_level": "series",
        "locator_pattern": "year",
        "confidence": "high",
        "needs_human_review": "false",
        "notes": "RDASB references are resolved to the report/journal series; issue-year article normalization remains future work.",
    },
    "eb": {
        "source_family_id": "sf-eb",
        "abbreviation": "EB",
        "canonical_family_id": "fam-eb-publication",
        "source_family_type": "periodical",
        "resolution_status": "series_level_resolved",
        "resolution_level": "series",
        "locator_pattern": "series_year_page",
        "confidence": "medium",
        "needs_human_review": "true",
        "notes": "EB is treated as a publication/series family rather than a standalone work.",
    },
    "pl": {
        "source_family_id": "sf-pl",
        "abbreviation": "Pl.",
        "canonical_family_id": "fam-plate-references",
        "source_family_type": "internal_reference",
        "resolution_status": "source_family_resolved",
        "resolution_level": "internal_reference",
        "locator_pattern": "plate",
        "confidence": "high",
        "needs_human_review": "false",
        "notes": "Plate references are internal locators and should stay separate from bibliographic works.",
    },
    "ippa": {
        "source_family_id": "sf-ippa",
        "abbreviation": "IPPA",
        "canonical_family_id": "fam-ippa-catalogue",
        "source_family_type": "catalogue",
        "resolution_status": "alias_resolved",
        "resolution_level": "source_family",
        "locator_pattern": "number",
        "confidence": "medium",
        "needs_human_review": "true",
        "notes": "IPPA behaves as a PPA-linked variant locator family in the structured OBI references rather than as a separate bibliographic work.",
    },
    "sip": {
        "source_family_id": "sf-sip",
        "abbreviation": "SIP",
        "canonical_family_id": "fam-sip-catalogue",
        "source_family_type": "catalogue",
        "resolution_status": "source_family_resolved",
        "resolution_level": "source_family",
        "locator_pattern": "page",
        "confidence": "medium",
        "needs_human_review": "true",
        "notes": "SIP is retained as a provisional source-family placeholder with locators.",
    },
    "mm": {
        "source_family_id": "sf-mm",
        "abbreviation": "MM",
        "canonical_family_id": "fam-mm-catalogue",
        "family_prefixes": ["fam-raw-another-mm-", "fam-raw-and-mm-"],
        "source_family_type": "catalogue",
        "resolution_status": "source_family_resolved",
        "resolution_level": "source_family",
        "locator_pattern": "page",
        "confidence": "medium",
        "needs_human_review": "true",
        "notes": "MM behaves as a source-family abbreviation with page-style locators.",
    },
    "or": {
        "source_family_id": "sf-or",
        "abbreviation": "OR",
        "canonical_family_id": "fam-or-catalogue",
        "source_family_type": "catalogue",
        "resolution_status": "source_family_resolved",
        "resolution_level": "source_family",
        "locator_pattern": "folio",
        "confidence": "medium",
        "needs_human_review": "true",
        "notes": "OR citations are modeled as a source family with folio-like locators.",
    },
    "arasi": {
        "source_family_id": "sf-arasi",
        "abbreviation": "ARASI",
        "canonical_family_id": "",
        "family_prefixes": ["fam-raw-arasi-"],
        "source_family_type": "periodical",
        "resolution_status": "series_level_resolved",
        "resolution_level": "series",
        "locator_pattern": "year",
        "confidence": "medium",
        "needs_human_review": "true",
        "notes": "ARASI references are stable series citations with year-style locators.",
    },
    "luce d": {
        "source_family_id": "sf-luce-d",
        "abbreviation": "Luce D",
        "canonical_family_id": "",
        "family_prefixes": ["fam-raw-luce-d-"],
        "source_family_type": "catalogue",
        "resolution_status": "source_family_resolved",
        "resolution_level": "source_family",
        "locator_pattern": "page",
        "confidence": "low",
        "needs_human_review": "true",
        "notes": "Luce D is kept as a provisional Luce source-family shorthand pending exact work confirmation.",
    },
    "luce j": {
        "source_family_id": "sf-luce-j",
        "abbreviation": "Luce J",
        "canonical_family_id": "",
        "family_prefixes": ["fam-raw-luce-j-"],
        "source_family_type": "catalogue",
        "resolution_status": "source_family_resolved",
        "resolution_level": "source_family",
        "locator_pattern": "page",
        "confidence": "low",
        "needs_human_review": "true",
        "notes": "Luce J is kept as a provisional Luce source-family shorthand pending exact work confirmation.",
    },
}

MANUAL_LOCAL_MATCHES = {
    "fam-raw-luce-u-tin-htway-15th-century-library": {
        "filename_terms": ["15th century inscription and library at pagan"],
        "confidence": "high",
    },
    "fam-raw-u-tin-htway-first-burmese-royal-inscription": {
        "filename_terms": ["oldest burmese inscription"],
        "confidence": "high",
    },
    "fam-raw-u-tha-myat-the-pali-version-of-the-myazedi-inscription-rangoon-1958": {
        "filename_terms": ["tha myat 1958 myazedi"],
        "confidence": "high",
    },
    "fam-raw-u-pe-maung-tin-the-myazedi-inscription-in-nava-rat-kui-svay-rangoon-1966": {
        "filename_terms": ["pemaungtin 1974 myazediinscription", "myazediinscription"],
        "confidence": "medium",
    },
}

CURATED_FAMILY_LIBRARY = {
    "fam-harvey-history": {
        "author": "G. E. Harvey",
        "year": "1925",
        "title": "History of Burma",
        "shorttitle": "History of Burma",
        "entry_type": "book",
        "preferred_key": "harvey1925historyBurma",
        "frasch_search_terms": ["harvey, history of burma", "history of burma"],
        "status": "provisional_local_source",
        "source_of_authority": "frasch_bibliography",
        "review_status": "needs_human_review",
        "notes": "Promoted from repeated Frasch shorthand citations; precise edition details still need confirmation.",
    },
    "fam-ray-theravada-buddhism": {
        "author": "Ray",
        "year": "",
        "title": "Theravada Buddhism",
        "shorttitle": "Theravada Buddhism",
        "entry_type": "book",
        "preferred_key": "rayTheravadaBuddhism",
        "frasch_search_terms": ["ray, theravada buddhism", "theravada buddhism"],
        "status": "provisional_local_source",
        "source_of_authority": "frasch_bibliography",
        "review_status": "needs_human_review",
        "notes": "Shorthand Frasch citations identify the work, but fuller publication metadata still needs local confirmation.",
    },
    "fam-raw-u-kyaw-bagan-minsa": {
        "author": "U Kyaw",
        "year": "",
        "title": "Bagan Minsa",
        "shorttitle": "Bagan Minsa",
        "entry_type": "article",
        "preferred_key": "uKyawBaganMinsa",
        "frasch_search_terms": ["u kyaw, bagan minsa", "bagan minsa"],
        "status": "provisional_local_source",
        "source_of_authority": "frasch_bibliography",
        "review_status": "needs_human_review",
        "notes": "Promoted from repeated Frasch shorthand citations pending fuller publication details.",
    },
    "fam-raw-u-tha-myat-the-pali-version-of-the-myazedi-inscription-rangoon-1958": {
        "author": "U Tha Myat",
        "year": "1958",
        "title": "The Pali Version of the Myazedi Inscription",
        "shorttitle": "Myazedi Inscription",
        "entry_type": "book",
        "preferred_key": "uThaMyat1958paliVersionMyazedi",
        "frasch_search_terms": ["u tha myat", "pali version of the myazedi inscription"],
        "status": "provisional_local_source",
        "source_of_authority": "frasch_bibliography",
        "review_status": "needs_human_review",
        "notes": "Attested as a full citation in Frasch bibliography evidence; local file confirmation is still pending.",
    },
    "fam-raw-u-pe-maung-tin-the-myazedi-inscription-in-nava-rat-kui-svay-rangoon-1966": {
        "author": "U Pe Maung Tin",
        "year": "1966",
        "title": "The Myazedi Inscription",
        "shorttitle": "Myazedi Inscription",
        "entry_type": "article",
        "preferred_key": "uPeMaungTin1966myazediInscription",
        "local_search_terms": ["pemaungtin 1974 myazediinscription", "myazediinscription"],
        "status": "provisional_local_source",
        "source_of_authority": "local_burma_folder",
        "review_status": "needs_human_review",
        "notes": "Matched to a likely local witness; edition details still need confirmation.",
    },
}

SUPPLEMENTAL_AUTHORITIES = {
    "annualReportArchaeologicalSurveyIndia": {
        "author": "",
        "year": "",
        "title": "Annual Report of the Archaeological Survey of India",
        "shorttitle": "ARASI",
        "entry_type": "periodical",
        "source_of_authority": "frasch_bibliography",
        "authority_status": "provisional_local_source",
        "review_status": "needs_human_review",
        "match_confidence": "medium",
        "match_reason": "Explicitly defined as ARASI in the extracted Bagan Epig Database abbreviations.",
        "evidence_terms": ["arasi"],
        "notes": "Used as the shared authority target for year-specific ARASI citation families.",
    },
    "luceDSourceFamily": {
        "author": "G. H. Luce",
        "year": "",
        "title": "Luce D source family",
        "shorttitle": "Luce D",
        "entry_type": "misc",
        "source_of_authority": "frasch_bibliography",
        "authority_status": "provisional_local_source",
        "review_status": "needs_human_review",
        "match_confidence": "low",
        "match_reason": "Abbreviation family attested in Frasch citations but not yet fully expanded.",
        "evidence_terms": ["luce d"],
        "notes": "Shared holding entry for Luce D shorthand references pending fuller identification.",
    },
    "luceJSourceFamily": {
        "author": "G. H. Luce",
        "year": "",
        "title": "Luce J source family",
        "shorttitle": "Luce J",
        "entry_type": "misc",
        "source_of_authority": "frasch_bibliography",
        "authority_status": "provisional_local_source",
        "review_status": "needs_human_review",
        "match_confidence": "low",
        "match_reason": "Abbreviation family attested in Frasch citations but not yet fully expanded.",
        "evidence_terms": ["luce j"],
        "notes": "Shared holding entry for Luce J shorthand references pending fuller identification.",
    },
}

SOURCE_WORK_RELATIONSHIPS = {
    "list": {
        "source_work_key": "duroiselle1921list",
        "source_work_title": "A List of Inscriptions Found in Burma",
        "locator_system": "catalogue number",
        "locator_prefixes": "List",
        "locator_type": "catalogue_number",
        "default_examples": "List 90 | List 302",
        "notes": "Duroiselle's List is a source work with catalogue-number locators.",
    },
    "a": {
        "source_work_key": "fraschBaganEpigraphicDatabasePartA",
        "source_work_title": "Bagan Epigraphic Database, Part A",
        "locator_system": "page",
        "locator_prefixes": "A",
        "locator_type": "page",
        "default_examples": "A, p. 79",
        "notes": "A references point to the Part A witness set of Frasch's Bagan Epigraphic Database.",
    },
    "b": {
        "source_work_key": "fraschBaganEpigraphicDatabasePartB",
        "source_work_title": "Bagan Epigraphic Database, Part B",
        "locator_system": "volume/page",
        "locator_prefixes": "B; BED B",
        "locator_type": "volume_page",
        "default_examples": "B 2, p. 815 | BED B 645-2",
        "notes": "B and BED B are treated as shorthand variants for the same Part B source work rather than separate works.",
    },
    "bed b": {
        "source_work_key": "fraschBaganEpigraphicDatabasePartB",
        "source_work_title": "Bagan Epigraphic Database, Part B",
        "locator_system": "volume/page",
        "locator_prefixes": "B; BED B",
        "locator_type": "volume_page",
        "default_examples": "B 2, p. 815 | BED B 645-2",
        "notes": "BED B is kept as the explicit Part B family label, but it shares the same source work as shorthand B references.",
    },
    "iob": {
        "source_work_key": "lucePeMaungTinInscriptionsOfBurma",
        "source_work_title": "Inscriptions of Burma",
        "locator_system": "IOB/plate references",
        "locator_prefixes": "IOB; Pl.",
        "locator_type": "catalogue_number; plate",
        "default_examples": "IOB--278 BED B 622-4 | Pl. II 198",
        "notes": "IOB references and Pl. references are treated as distinct locator systems into the same Luce and Pe Maung Tin work.",
    },
    "pl": {
        "source_work_key": "lucePeMaungTinInscriptionsOfBurma",
        "source_work_title": "Inscriptions of Burma",
        "locator_system": "IOB/plate references",
        "locator_prefixes": "IOB; Pl.",
        "locator_type": "catalogue_number; plate",
        "default_examples": "IOB--278 BED B 622-4 | Pl. II 198",
        "notes": "Plate references point into the Luce and Pe Maung Tin Inscriptions of Burma plates rather than naming a separate bibliographic work.",
    },
    "obi": {
        "source_work_key": "oldBurmeseInscriptions",
        "source_work_title": "Old Burmese Inscriptions",
        "locator_system": "volume/page reference",
        "locator_prefixes": "OBI",
        "locator_type": "volume_page",
        "default_examples": "OBI 3, p. 2",
        "notes": "OBI references point into the structured Old Burmese Inscriptions corpus rather than a separate printed bibliography item.",
    },
    "ppa": {
        "source_work_key": "ppaCatalogue",
        "source_work_title": "Inscriptions of Pagan, Pinya and Ava",
        "locator_system": "page and IPPA-variant references",
        "locator_prefixes": "PPA; IPPA",
        "locator_type": "page; number",
        "default_examples": "PPA, p. 55 | IPPA-159",
        "notes": "PPA references use page locators into the Pagan, Pinya and Ava source work, while IPPA preserves a related variant locator family in the structured OBI source.",
        "alias_or_variant_notes": "IPPA is preserved as a raw variant locator family into the same underlying PPA source work.",
    },
    "ippa": {
        "source_work_key": "ppaCatalogue",
        "source_work_title": "Inscriptions of Pagan, Pinya and Ava",
        "locator_system": "page and IPPA-variant references",
        "locator_prefixes": "PPA; IPPA",
        "locator_type": "page; number",
        "default_examples": "IPPA-159 | PPA, p. 159",
        "notes": "IPPA is retained as a distinct raw reference family, but it routes to the same underlying Pagan, Pinya and Ava source work as PPA.",
        "alias_of_source_family_id": "sf-ppa",
        "alias_or_variant_notes": "Raw IPPA strings are preserved in the crosswalk while the family routes to ppaCatalogue.",
    },
    "ub": {
        "source_work_key": "ubSourceFamily",
        "source_work_title": "Inscriptions Collected in Upper Burma",
        "locator_system": "volume/page",
        "locator_prefixes": "UB",
        "locator_type": "volume_page",
        "default_examples": "UB 1, p. 297",
        "notes": "UB references carry volume/page locators into the Arch. Survey of Burma edition.",
    },
    "sip": {
        "source_work_key": "sipSelectionsPagan",
        "source_work_title": "Selections from the Inscriptions of Pagan",
        "locator_system": "inscription number/page",
        "locator_prefixes": "SIP",
        "locator_type": "catalogue_number; page",
        "default_examples": "SIP no. 26, p. 55",
        "notes": "SIP references point to Pe Maung Tin and G. H. Luce's Selections from the Inscriptions of Pagan with inscription-number and page locators.",
    },
    "uem": {
        "source_work_key": "uemSelectionsPagan",
        "source_work_title": "Selections from the Inscriptions of Pagan",
        "locator_system": "inscription number/page",
        "locator_prefixes": "UEM",
        "locator_type": "catalogue_number; page",
        "default_examples": "UEM no. 44, p. 117",
        "notes": "UEM references point to U E Maung's Selections from the Inscriptions of Pagan with inscription-number and page locators.",
    },
    "tn": {
        "source_work_key": "tnInscriptionsPaganPinyaAva",
        "source_work_title": "Inscriptions of Pagan, Pinya and Ava",
        "locator_system": "page",
        "locator_prefixes": "TN",
        "locator_type": "page",
        "default_examples": "TN, p. 91",
        "notes": "TN references point to U Tun Nyein's Inscriptions of Pagan, Pinya and Ava with page locators.",
    },
    "mp": {
        "source_work_key": "mandalayPalaceStoneCollection",
        "source_work_title": "Mandalay Palace stone collection",
        "locator_system": "stone/page references",
        "locator_prefixes": "MP",
        "locator_type": "volume_page; number",
        "default_examples": "MP 1, p. 21 | MP stone 507",
        "notes": "MP behaves as a Mandalay Palace stone-collection locator family rather than as a standalone bibliographic work.",
    },
    "or": {
        "source_work_key": "britishLibraryOrientalManuscripts",
        "source_work_title": "British Library Oriental Manuscripts",
        "locator_system": "shelfmark/folio",
        "locator_prefixes": "OR",
        "locator_type": "folio",
        "default_examples": "OR 3475, no. 18 | OR 3434, fol. gha verso",
        "notes": "OR references are treated as British Library Oriental manuscript shelfmarks rather than as a published title.",
    },
    "luce d": {
        "source_work_key": "gHLuceNotebookD",
        "source_work_title": "G. H. Luce Notebook D",
        "locator_system": "notebook entry/page",
        "locator_prefixes": "Luce D",
        "locator_type": "number",
        "default_examples": "Luce D 825 | Luce D 835",
        "notes": "Archive descriptions support treating Luce D citations as references into an unpublished Luce notebook sequence.",
    },
    "luce j": {
        "source_work_key": "gHLuceNotebookJ",
        "source_work_title": "G. H. Luce Notebook J",
        "locator_system": "notebook entry/page",
        "locator_prefixes": "Luce J",
        "locator_type": "number",
        "default_examples": "Luce J 2507 | Luce J 2689",
        "notes": "Archive descriptions support treating Luce J citations as references into an unpublished Luce notebook sequence.",
    },
    "jbrs": {
        "source_work_key": "journalBurmaResearchSociety",
        "source_work_title": "Journal of the Burma Research Society",
        "locator_system": "series/year/page",
        "locator_prefixes": "JBRS",
        "locator_type": "series_year_page",
        "default_examples": "JBRS 48 (2), 1965, p. 67",
        "notes": "JBRS references point to the journal series rather than to a single pre-resolved article.",
    },
    "jras": {
        "source_work_key": "journalRoyalAsiaticSociety",
        "source_work_title": "Journal of the Royal Asiatic Society",
        "locator_system": "series/year/page",
        "locator_prefixes": "JRAS",
        "locator_type": "series_year_page",
        "default_examples": "JRAS 1909, p. 10",
        "notes": "JRAS references point to the journal series unless an article-level match is known.",
    },
    "bbhc": {
        "source_work_key": "bulletinBurmaHistoricalCommission",
        "source_work_title": "Bulletin of the Burma Historical Commission",
        "locator_system": "series/year/page",
        "locator_prefixes": "BBHC",
        "locator_type": "series_year_page",
        "default_examples": "BBHC 3, 1963, p. 96",
        "notes": "BBHC references point to the bulletin series rather than to a distinct standalone work.",
    },
    "arasi": {
        "source_work_key": "annualReportsArchaeologicalSurveyIndia",
        "source_work_title": "Annual Reports of the Archaeological Survey of India",
        "locator_system": "year/page",
        "locator_prefixes": "ARASI",
        "locator_type": "year; series_year_page",
        "default_examples": "ARASI 1936-37, p. 114",
        "notes": "ARASI references point to the Archaeological Survey of India annual-report series.",
    },
    "eb": {
        "source_work_key": "epigraphiaBirmanica",
        "source_work_title": "Epigraphia Birmanica",
        "locator_system": "series/year/page",
        "locator_prefixes": "EB",
        "locator_type": "series_year_page",
        "default_examples": "EB 1 (1), 1919, p. 1",
        "notes": "EB references point to the Epigraphia Birmanica series rather than a single resolved volume.",
    },
}

SOURCE_WORK_AUTHORITY_LIBRARY = {
    "lucePeMaungTinInscriptionsOfBurma": {
        "canonical_title": "Inscriptions of Burma",
        "short_title": "Inscriptions of Burma",
        "authority_level": "book",
        "work_type": "book",
        "authors_editors": "G. H. Luce and U Pe Maung Tin",
        "date_or_date_range": "1933-1956",
        "publisher_or_institution": "",
        "place": "",
        "authority_status": "confirmed_source_work",
        "primary_source_family_id": "sf-iob",
        "bibtex_key": "lucePeMaungTinInscriptionsOfBurma",
        "needs_human_review": "false",
        "notes": "Shared source work for IOB catalogue locators and Pl. plate locators.",
    },
    "duroiselle1921list": {
        "canonical_title": "List of Inscriptions Found in Burma",
        "short_title": "List",
        "authority_level": "book",
        "work_type": "book",
        "authors_editors": "Charles Duroiselle",
        "date_or_date_range": "1921",
        "publisher_or_institution": "",
        "place": "",
        "authority_status": "confirmed_source_work",
        "primary_source_family_id": "sf-list",
        "bibtex_key": "duroiselle1921list",
        "needs_human_review": "false",
        "notes": "Stable catalogue-style source work used for List locators.",
    },
    "fraschBaganEpigraphicDatabasePartA": {
        "canonical_title": "Bagan Epigraphic Database, Part A",
        "short_title": "A",
        "authority_level": "source_catalogue",
        "work_type": "source_catalogue",
        "authors_editors": "Tilman Frasch",
        "date_or_date_range": "",
        "publisher_or_institution": "",
        "place": "",
        "authority_status": "provisional_source_work",
        "primary_source_family_id": "sf-a",
        "bibtex_key": "fraschBaganEpigraphicDatabasePartA",
        "needs_human_review": "true",
        "notes": "Part A source-work authority for the Bagan Epigraphic Database abbreviations.",
    },
    "fraschBaganEpigraphicDatabasePartB": {
        "canonical_title": "Bagan Epigraphic Database, Part B",
        "short_title": "BED B",
        "authority_level": "source_catalogue",
        "work_type": "source_catalogue",
        "authors_editors": "Tilman Frasch",
        "date_or_date_range": "",
        "publisher_or_institution": "",
        "place": "",
        "authority_status": "provisional_source_work",
        "primary_source_family_id": "sf-bed-b",
        "bibtex_key": "fraschBaganEpigraphicDatabasePartB",
        "needs_human_review": "true",
        "notes": "Canonical Part B source-work authority shared by BED B and shorthand B references.",
    },
    "ppaCatalogue": {
        "canonical_title": "Inscriptions of Pagan, Pinya and Ava",
        "short_title": "PPA",
        "authority_level": "source_catalogue",
        "work_type": "source_catalogue",
        "authors_editors": "Archaeological Survey of Burma (ed.)",
        "date_or_date_range": "",
        "publisher_or_institution": "Archaeological Survey of Burma",
        "place": "Rangoon",
        "authority_status": "provisional_source_work",
        "primary_source_family_id": "sf-ppa",
        "bibtex_key": "ppaCatalogue",
        "needs_human_review": "true",
        "notes": "Canonical PPA work; IPPA is treated only as an alias/variant locator family into this source work.",
    },
    "ubSourceFamily": {
        "canonical_title": "Inscriptions Collected in Upper Burma",
        "short_title": "UB",
        "authority_level": "source_catalogue",
        "work_type": "source_catalogue",
        "authors_editors": "",
        "date_or_date_range": "",
        "publisher_or_institution": "Archaeological Survey of Burma",
        "place": "",
        "authority_status": "provisional_source_work",
        "primary_source_family_id": "sf-ub",
        "bibtex_key": "ubSourceFamily",
        "needs_human_review": "true",
        "notes": "Stable source-work layer for UB volume/page locators.",
    },
    "sipSelectionsPagan": {
        "canonical_title": "Selections from the Inscriptions of Pagan",
        "short_title": "SIP",
        "authority_level": "book",
        "work_type": "book",
        "authors_editors": "Pe Maung Tin and G. H. Luce",
        "date_or_date_range": "",
        "publisher_or_institution": "",
        "place": "",
        "authority_status": "provisional_source_work",
        "primary_source_family_id": "sf-sip",
        "bibtex_key": "sipSourceFamily",
        "needs_human_review": "true",
        "notes": "SIP is a named source work with locator semantics rather than a standalone raw-string expansion target.",
    },
    "uemSelectionsPagan": {
        "canonical_title": "Selections from the Inscriptions of Pagan",
        "short_title": "UEM",
        "authority_level": "book",
        "work_type": "book",
        "authors_editors": "U E Maung (ed.)",
        "date_or_date_range": "1958",
        "publisher_or_institution": "",
        "place": "Rangoon",
        "authority_status": "provisional_source_work",
        "primary_source_family_id": "sf-uem",
        "bibtex_key": "uEMaung1958selectionsInscriptionsPagan",
        "needs_human_review": "true",
        "notes": "UEM is modeled as a source work with inscription-number and page locators.",
    },
    "tnInscriptionsPaganPinyaAva": {
        "canonical_title": "Inscriptions of Pagan, Pinya and Ava",
        "short_title": "TN",
        "authority_level": "book",
        "work_type": "book",
        "authors_editors": "U Tun Nyein (tr.)",
        "date_or_date_range": "1897",
        "publisher_or_institution": "",
        "place": "Rangoon",
        "authority_status": "provisional_source_work",
        "primary_source_family_id": "sf-tn",
        "bibtex_key": "uTunNyein1897inscriptionsPaganPinyaAva",
        "needs_human_review": "true",
        "notes": "TN is modeled as a source work with page locators.",
    },
    "epigraphiaBirmanica": {
        "canonical_title": "Epigraphia Birmanica",
        "short_title": "EB",
        "authority_level": "series",
        "work_type": "series",
        "authors_editors": "",
        "date_or_date_range": "1919-1936",
        "publisher_or_institution": "",
        "place": "",
        "authority_status": "series_authority",
        "primary_source_family_id": "sf-eb",
        "bibtex_key": "epigraphiaBirmanica",
        "needs_human_review": "true",
        "notes": "Series-level authority only unless a specific EB fascicle/article is identified.",
    },
    "journalBurmaResearchSociety": {
        "canonical_title": "Journal of the Burma Research Society",
        "short_title": "JBRS",
        "authority_level": "periodical",
        "work_type": "periodical",
        "authors_editors": "",
        "date_or_date_range": "",
        "publisher_or_institution": "",
        "place": "",
        "authority_status": "series_authority",
        "primary_source_family_id": "sf-jbrs",
        "bibtex_key": "journalBurmaResearchSociety",
        "needs_human_review": "false",
        "notes": "Series-level authority only unless article-level evidence is available.",
    },
    "journalRoyalAsiaticSociety": {
        "canonical_title": "Journal of the Royal Asiatic Society",
        "short_title": "JRAS",
        "authority_level": "periodical",
        "work_type": "periodical",
        "authors_editors": "",
        "date_or_date_range": "",
        "publisher_or_institution": "",
        "place": "",
        "authority_status": "series_authority",
        "primary_source_family_id": "sf-jras",
        "bibtex_key": "journalRoyalAsiaticSociety",
        "needs_human_review": "false",
        "notes": "Series-level authority only unless article-level evidence is available.",
    },
    "bulletinBurmaHistoricalCommission": {
        "canonical_title": "Bulletin of the Burma Historical Commission",
        "short_title": "BBHC",
        "authority_level": "periodical",
        "work_type": "periodical",
        "authors_editors": "",
        "date_or_date_range": "",
        "publisher_or_institution": "Burma Historical Commission",
        "place": "",
        "authority_status": "series_authority",
        "primary_source_family_id": "sf-bbhc",
        "bibtex_key": "burmaHistoricalCommissionBulletin",
        "needs_human_review": "true",
        "notes": "Series-level authority for BBHC citations.",
    },
    "annualReportsArchaeologicalSurveyIndia": {
        "canonical_title": "Annual Reports of the Archaeological Survey of India",
        "short_title": "ARASI",
        "authority_level": "series",
        "work_type": "periodical",
        "authors_editors": "",
        "date_or_date_range": "",
        "publisher_or_institution": "Archaeological Survey of India",
        "place": "",
        "authority_status": "series_authority",
        "primary_source_family_id": "sf-arasi",
        "bibtex_key": "annualReportArchaeologicalSurveyIndia",
        "needs_human_review": "true",
        "notes": "Series-level authority for ARASI citations.",
    },
    "oldBurmeseInscriptions": {
        "canonical_title": "Old Burmese Inscriptions",
        "short_title": "OBI",
        "authority_level": "corpus_source",
        "work_type": "corpus_source",
        "authors_editors": "Tilman Frasch",
        "date_or_date_range": "",
        "publisher_or_institution": "",
        "place": "",
        "authority_status": "internal_corpus_source",
        "primary_source_family_id": "sf-obi",
        "bibtex_key": "obiCorpusSource",
        "needs_human_review": "false",
        "notes": "Structured corpus authority for OBI internal references.",
    },
    "rdasbSourceFamily": {
        "canonical_title": "Report of the Director, Archaeological Survey of Burma",
        "short_title": "RDASB",
        "authority_level": "series",
        "work_type": "series",
        "authors_editors": "",
        "date_or_date_range": "",
        "publisher_or_institution": "Archaeological Survey of Burma",
        "place": "",
        "authority_status": "provisional_source_work",
        "primary_source_family_id": "sf-rdasb",
        "bibtex_key": "rdasbSourceFamily",
        "needs_human_review": "true",
        "notes": "Series-level authority pending issue-level confirmation.",
    },
    "uMinHsweSourceFamily": {
        "canonical_title": "U Min Hswe",
        "short_title": "U Min Hswe",
        "authority_level": "source_catalogue",
        "work_type": "source_catalogue",
        "authors_editors": "U Min Hswe",
        "date_or_date_range": "",
        "publisher_or_institution": "",
        "place": "",
        "authority_status": "provisional_source_work",
        "primary_source_family_id": "sf-u-min-hswe",
        "bibtex_key": "uMinHsweSourceFamily",
        "needs_human_review": "true",
        "notes": "Named source authority retained for bibliography normalization even though the exact title boundary remains uncertain.",
    },
    "mandalayPalaceStoneCollection": {
        "canonical_title": "Mandalay Palace stone collection",
        "short_title": "MP",
        "authority_level": "locator_collection",
        "work_type": "locator_collection",
        "authors_editors": "",
        "date_or_date_range": "",
        "publisher_or_institution": "",
        "place": "Mandalay",
        "authority_status": "locator_system",
        "primary_source_family_id": "sf-mp",
        "bibtex_key": "",
        "needs_human_review": "true",
        "notes": "Locator collection authority only; do not emit a standalone BibTeX publication.",
    },
    "britishLibraryOrientalManuscripts": {
        "canonical_title": "British Library Oriental manuscripts",
        "short_title": "OR",
        "authority_level": "manuscript_collection",
        "work_type": "manuscript_collection",
        "authors_editors": "",
        "date_or_date_range": "",
        "publisher_or_institution": "British Library",
        "place": "London",
        "authority_status": "locator_system",
        "primary_source_family_id": "sf-or",
        "bibtex_key": "",
        "needs_human_review": "true",
        "notes": "Shelfmark/folio holding authority only; do not emit a standalone BibTeX publication.",
    },
    "gHLuceNotebookD": {
        "canonical_title": "G. H. Luce Notebook D",
        "short_title": "Luce D",
        "authority_level": "archival_notebook",
        "work_type": "archival_notebook",
        "authors_editors": "G. H. Luce",
        "date_or_date_range": "",
        "publisher_or_institution": "",
        "place": "",
        "authority_status": "probable_private_locator_system",
        "primary_source_family_id": "sf-luce-d",
        "bibtex_key": "",
        "needs_human_review": "true",
        "notes": "Probable private Luce notebook authority only; do not emit a standalone BibTeX publication.",
    },
    "gHLuceNotebookJ": {
        "canonical_title": "G. H. Luce Notebook J",
        "short_title": "Luce J",
        "authority_level": "archival_notebook",
        "work_type": "archival_notebook",
        "authors_editors": "G. H. Luce",
        "date_or_date_range": "",
        "publisher_or_institution": "",
        "place": "",
        "authority_status": "probable_private_locator_system",
        "primary_source_family_id": "sf-luce-j",
        "bibtex_key": "",
        "needs_human_review": "true",
        "notes": "Probable private Luce notebook authority only; do not emit a standalone BibTeX publication.",
    },
}

AUTHORITY_KEY_NORMALIZATION_ROWS = [
    {
        "old_key": "annualReportArchaeologicalSurveyIndia",
        "new_key": "annualReportsArchaeologicalSurveyIndia",
        "object_type": "source_work",
        "reason": "Prefer the pluralized series title for the ARASI source-work authority.",
        "migration_action": "Map source_work_key references to annualReportsArchaeologicalSurveyIndia while keeping the legacy BibTeX key only where already emitted.",
        "notes": "The singular form survives only as a BibTeX key; the source-work layer should use the series title.",
    },
    {
        "old_key": "burmaHistoricalCommissionBulletin",
        "new_key": "bulletinBurmaHistoricalCommission",
        "object_type": "source_work",
        "reason": "Prefer the title-forward source-work key for BBHC.",
        "migration_action": "Map source_work_key references to bulletinBurmaHistoricalCommission and keep the older BibTeX key only if needed for continuity.",
        "notes": "This avoids carrying both key orders through the source-work layer.",
    },
    {
        "old_key": "obiCorpusSource",
        "new_key": "oldBurmeseInscriptions",
        "object_type": "source_work",
        "reason": "Use the title of the corpus/source authority rather than a mixed corpus/object label.",
        "migration_action": "Normalize source_work_key references to oldBurmeseInscriptions.",
        "notes": "The corpus-facing source-work layer should be keyed by the work/corpus title rather than the legacy BibTeX key.",
    },
    {
        "old_key": "fraschBaganEpigraphicDatabasePartBShort",
        "new_key": "fraschBaganEpigraphicDatabasePartB",
        "object_type": "source_work",
        "reason": "Shorthand B references and explicit BED B references point to the same Part B source work.",
        "migration_action": "Map shorthand B rows to fraschBaganEpigraphicDatabasePartB and suppress the duplicate short-form source-work key.",
        "notes": "The distinction belongs in source-family semantics, not in duplicate source-work rows.",
    },
    {
        "old_key": "sipSourceFamily",
        "new_key": "sipSelectionsPagan",
        "object_type": "source_work",
        "reason": "Use the named source-work title rather than the older source-family-style key.",
        "migration_action": "Normalize crosswalk source_work_key values to sipSelectionsPagan.",
        "notes": "The BibTeX key may stay stable while the source-work key uses the publication-like title.",
    },
    {
        "old_key": "uEMaung1958selectionsInscriptionsPagan",
        "new_key": "uemSelectionsPagan",
        "object_type": "source_work",
        "reason": "Use the canonical source-work key for UEM rather than the legacy BibTeX key.",
        "migration_action": "Normalize crosswalk source_work_key values to uemSelectionsPagan.",
        "notes": "This keeps source-work identifiers independent from emitted BibTeX keys.",
    },
    {
        "old_key": "uTunNyein1897inscriptionsPaganPinyaAva",
        "new_key": "tnInscriptionsPaganPinyaAva",
        "object_type": "source_work",
        "reason": "Use the TN source-work key rather than the longer legacy BibTeX key in the authority layer.",
        "migration_action": "Normalize crosswalk source_work_key values to tnInscriptionsPaganPinyaAva.",
        "notes": "Source-work keys should reflect the authority object, not the exact emitted BibTeX label.",
    },
]
SOURCE_WORK_KEY_NORMALIZATION_MAP = {
    row["old_key"]: row["new_key"] for row in AUTHORITY_KEY_NORMALIZATION_ROWS
}
SOURCE_WORK_KEY_BY_BIBTEX_KEY = {
    metadata.get("bibtex_key", ""): source_work_key
    for source_work_key, metadata in SOURCE_WORK_AUTHORITY_LIBRARY.items()
    if metadata.get("bibtex_key")
}
SCRIPT_NORMALIZATION_MAP = {
    "latin": "Latn",
    "latn": "Latn",
}

CANDIDATE_STUB_REVIEW_DECISIONS = {
    "anthology": {
        "review_decision": "retain",
        "reason": "The citation family is generic, but repeated anthology-style locators suggest a real source rather than a pure parsing artifact.",
        "next_action": "Search local bibliography caches and Frasch-derived text for anthology, selections, collected inscriptions, or edited-volume language tied to the same raw references.",
        "notes": "Check data/working/bibliography/local_sources/, data/local/bibliography_sources/, and Frasch extracted text for anthology-like titles or editors before promoting.",
    },
    "lwin1989rajakumars": {
        "review_decision": "retain",
        "reason": "The title and year identify a plausible real work, but the current evidence is still corpus-triage level rather than a confirmed bibliographic witness.",
        "next_action": "Search local files for U Tin Lwin, Rajakumar's Inscription in Pali, Takkasuil, Yangon 1989, Myazedi, and Rajakumar before promoting.",
        "notes": "Retain until a stronger local bibliographic witness is found; do not promote from the corpus citation string alone.",
    },
    "work": {
        "review_decision": "suppress",
        "reason": "This row is a malformed residue about an incomplete plate witness, not a standalone bibliography item.",
        "next_action": "Suppress the stub and rely on source-family and locator handling instead.",
        "notes": "The generic key comes from a note-like fragment rather than a real work title.",
    },
}

REMAINING_ACRONYM_EVIDENCE_CONFIG = {
    "IOB": {
        "likely_source_type": "locator system into source work",
        "specific_files_to_check": [
            "data/working/bibliography/local_sources/frasch_extracted_text.txt",
            "data/working/bibliography/local_sources/acronym_definition_candidates.tsv",
        ],
        "specific_search_terms": ["IOB", "IB", "Inscriptions of Burma", "Pl."],
        "recommended_action": "treat as internal_locator tied to Inscriptions of Burma",
        "evidence_rows": [
            {
                "candidate_expansion": "Inscriptions of Burma",
                "evidence_type": "manual_inference",
                "source_file_id": "frasch-extracted-text",
                "source_file_label": "frasch_extracted_text.txt",
                "source_location_hint": "L8417-L8453",
                "short_quote": "IB  Inscriptions of Burma (Luce & Pe Maung Tin 1933–1956) ... Pl.  Inscriptions of Burma (Luce & Pe Maung Tin 1933–1956)",
                "evidence_strength": "medium",
                "supports_expansion": "true",
                "contradicts_expansion": "false",
                "needs_human_review": "true",
                "notes": "Frasch explicitly defines IB and Pl., not IOB; IOB is therefore kept as a locator-family relation to the same underlying work rather than as a standalone title expansion.",
            }
        ],
        "status_override": {
            "resolution_status": "internal_locator",
            "definition_quality": "documented_locator_relation",
            "current_expansion": "Locator reference into Inscriptions of Burma",
            "confidence": "medium",
            "needs_human_review": "true",
        },
    },
    "IPPA": {
        "likely_source_type": "PPA-linked variant locator family",
        "specific_files_to_check": [
            "data/release/corpus_release_v0_3/inscriptions.jsonl",
            "data/working/bibliography/reference_occurrences.tsv",
            "data/working/bibliography/local_sources/frasch_extracted_text.txt",
        ],
        "specific_search_terms": ["IPPA", "IPPA-159", "IPPA-209", "PPA, p. 159", "PPA, p. 209", "Inscriptions of Pagan, Pinya and Ava"],
        "recommended_action": "preserve raw IPPA strings while mapping the family to the underlying PPA work",
        "evidence_rows": [
            {
                "candidate_expansion": "IPPA variant locator family into Inscriptions of Pagan, Pinya and Ava",
                "evidence_type": "contextual_usage",
                "source_file_id": "obi-v01-no4-ob-p11",
                "source_file_label": "OBI_Corpus_Vol1/OBI_Vol1_No4__ob_p11.txt",
                "source_location_hint": "REFERENCES line in the structured OBI source",
                "short_quote": "IPPA-159; ... PPA, p. 159",
                "evidence_strength": "medium",
                "supports_expansion": "true",
                "contradicts_expansion": "false",
                "needs_human_review": "true",
                "notes": "Representative same-record pairing shows IPPA and PPA routed together in the raw corpus references.",
            },
            {
                "candidate_expansion": "Inscriptions of Pagan, Pinya and Ava",
                "evidence_type": "abbreviation_list",
                "source_file_id": "frasch-abbreviation-review",
                "source_file_label": "frasch_abbreviation_list_review.tsv",
                "source_location_hint": "L7859-L7884",
                "short_quote": "PPA Arch. Survey of Burma (ed.), Inscriptions of Pagan, Pinya and Ava",
                "evidence_strength": "medium",
                "supports_expansion": "true",
                "contradicts_expansion": "false",
                "needs_human_review": "true",
                "notes": "Frasch defines the underlying PPA source work explicitly, but does not define a separate IPPA work.",
            }
        ],
        "status_override": {
            "resolution_status": "alias_or_variant_of_PPA",
            "definition_quality": "occurrence_level_alias_relation",
            "current_expansion": "IPPA variant locator family into Inscriptions of Pagan, Pinya and Ava",
            "confidence": "medium",
            "needs_human_review": "true",
        },
    },
    "Luce D": {
        "likely_source_type": "private Luce notebook locator family",
        "specific_files_to_check": [
            "data/working/bibliography/local_sources/frasch_extracted_text.txt",
            "data/local/bibliography_sources/luce_collection-b951e346a053/Luce_collection.doc",
            "https://archive.org/details/bdrc-W2KG200022",
        ],
        "specific_search_terms": ['"Luce D"', '"Luce D 825"', '"Luce D 835"', '"Notebook D"', '"G. H. Luce"'],
        "recommended_action": "treat as probable_private_luce_locator_system; do not turn into a BibTeX work",
        "evidence_rows": [
            {
                "candidate_expansion": "G. H. Luce Notebook D archival locator system",
                "evidence_type": "contextual_usage",
                "source_file_id": "frasch-extracted-text",
                "source_file_label": "frasch_extracted_text.txt",
                "source_location_hint": "L488-L579",
                "short_quote": "References: Pl. V 581a = List 1406 = Luce D 825 ... Pl. V 599a-b = List 1445-1446 = A, p. 591-2 = Luce D 835",
                "evidence_strength": "medium",
                "supports_expansion": "true",
                "contradicts_expansion": "false",
                "needs_human_review": "true",
                "notes": "The corpus treats Luce D as a numbered Luce-only locator family rather than as a published work citation.",
            },
            {
                "candidate_expansion": "G. H. Luce Notebook D archival locator system",
                "evidence_type": "manual_inference",
                "source_file_id": "archive-bdrc-W2KG200022",
                "source_file_label": "Archive.org BDRC notebook listing",
                "source_location_hint": "Notebook D entry",
                "short_quote": "016-080: Epigraphical notes. 081-147: Listed inscriptions. 148-156: Unlisted inscriptions. 157a-161b: Miscellaneous notes.",
                "evidence_strength": "medium",
                "supports_expansion": "true",
                "contradicts_expansion": "false",
                "needs_human_review": "true",
                "notes": "Archive.org explicitly describes Notebook D as an unpublished Luce notebook with epigraphical notes and inscription listings.",
            }
        ],
        "status_override": {
            "resolution_status": "probable_private_luce_locator_system",
            "definition_quality": "archival_notebook_inferred_from_archive_catalogue",
            "current_expansion": "G. H. Luce Notebook D archival locator system",
            "confidence": "medium",
            "needs_human_review": "true",
        },
    },
    "Luce J": {
        "likely_source_type": "private Luce notebook locator family",
        "specific_files_to_check": [
            "data/working/bibliography/local_sources/frasch_extracted_text.txt",
            "data/local/bibliography_sources/luce_collection-b951e346a053/Luce_collection.doc",
            "https://archive.org/details/bdrc-W2KG200024",
        ],
        "specific_search_terms": ['"Luce J"', '"Luce J 2507"', '"Luce J2509"', '"Luce J 2689"', '"Notebook J"', '"G. H. Luce"'],
        "recommended_action": "treat as probable_private_luce_locator_system; do not turn into a BibTeX work",
        "evidence_rows": [
            {
                "candidate_expansion": "G. H. Luce Notebook J archival locator system",
                "evidence_type": "contextual_usage",
                "source_file_id": "frasch-extracted-text",
                "source_file_label": "frasch_extracted_text.txt",
                "source_location_hint": "L470-L804",
                "short_quote": "References: Pl. V 567b = Luce J2509 ... References: Luce J 2507 ... References: Luce J 2689",
                "evidence_strength": "medium",
                "supports_expansion": "true",
                "contradicts_expansion": "false",
                "needs_human_review": "true",
                "notes": "The corpus preserves Luce J as a numbered Luce-only locator family, which fits notebook-style references better than a published title.",
            },
            {
                "candidate_expansion": "G. H. Luce Notebook J archival locator system",
                "evidence_type": "manual_inference",
                "source_file_id": "archive-bdrc-W2KG200024",
                "source_file_label": "Archive.org BDRC notebook listing",
                "source_location_hint": "Notebook J entry",
                "short_quote": "001a-001b: Notes on inscriptions from Prome ... 081-147: Listed inscriptions ... 148-160: Miscellaneous notes and transcription.",
                "evidence_strength": "medium",
                "supports_expansion": "true",
                "contradicts_expansion": "false",
                "needs_human_review": "true",
                "notes": "Archive.org explicitly describes Notebook J as an unpublished Luce notebook containing inscription notes and transcriptions.",
            }
        ],
        "status_override": {
            "resolution_status": "probable_private_luce_locator_system",
            "definition_quality": "archival_notebook_inferred_from_archive_catalogue",
            "current_expansion": "G. H. Luce Notebook J archival locator system",
            "confidence": "medium",
            "needs_human_review": "true",
        },
    },
    "MP": {
        "likely_source_type": "collection locator system",
        "specific_files_to_check": [
            "data/working/bibliography/local_sources/frasch_extracted_text.txt",
            "data/local/bibliography_sources/bagan_epig_database-c4cfc990741f/Bagan Epig Database.doc",
        ],
        "specific_search_terms": ["MP", "MP 1, p.", "Mandalay Palace", "Mandalay Palace stone", "MP stone 507"],
        "recommended_action": "treat as probable_locator_system tied to the Mandalay Palace stone collection",
        "evidence_rows": [
            {
                "candidate_expansion": "Mandalay Palace stone collection locator system",
                "evidence_type": "contextual_usage",
                "source_file_id": "frasch-extracted-text",
                "source_file_label": "frasch_extracted_text.txt",
                "source_location_hint": "L10-L740",
                "short_quote": "Location: ?; Mandalay Palace stone 291 ... Dhammayan temple, Bagan; MP stone 507",
                "evidence_strength": "medium",
                "supports_expansion": "true",
                "contradicts_expansion": "false",
                "needs_human_review": "true",
                "notes": "The Frasch text repeatedly equates MP references with Mandalay Palace stone labels, supporting a collection-locator reading.",
            },
            {
                "candidate_expansion": "Mandalay Palace stone collection locator system",
                "evidence_type": "contextual_usage",
                "source_file_id": "bagan-epig-database-doc",
                "source_file_label": "Bagan Epig Database.doc",
                "source_location_hint": "targeted local text search",
                "short_quote": "Mandalay Palace stone 291 ... Mandalay Palace (unnumbered) ... MP stone 507",
                "evidence_strength": "medium",
                "supports_expansion": "true",
                "contradicts_expansion": "false",
                "needs_human_review": "true",
                "notes": "The local Bagan Epigraphic Database witness preserves both the full Mandalay Palace wording and the MP shorthand.",
            }
        ],
        "status_override": {
            "resolution_status": "probable_locator_system",
            "definition_quality": "collection_locator_inferred_from_local_context",
            "current_expansion": "Mandalay Palace stone collection locator system",
            "confidence": "medium",
            "needs_human_review": "true",
        },
    },
    "OR": {
        "likely_source_type": "holding or shelfmark system",
        "specific_files_to_check": [
            "data/working/bibliography/local_sources/frasch_extracted_text.txt",
            "https://searcharchives.bl.uk/",
        ],
        "specific_search_terms": ["OR 6452", "OR 3434", "OR 3475", "British Library Oriental Mss", "Or. shelfmark"],
        "recommended_action": "treat as probable_locator_system tied to British Library Oriental manuscript shelfmarks",
        "evidence_rows": [
            {
                "candidate_expansion": "British Library Oriental manuscript shelfmark system",
                "evidence_type": "contextual_usage",
                "source_file_id": "frasch-extracted-text",
                "source_file_label": "frasch_extracted_text.txt",
                "source_location_hint": "L5647-L5650; L3314",
                "short_quote": "British Library Oriental Mss Sect-ion OR 3434, fol. gha verso ... OR 3475, no. 18",
                "evidence_strength": "medium",
                "supports_expansion": "true",
                "contradicts_expansion": "false",
                "needs_human_review": "true",
                "notes": "The Frasch witness explicitly links OR citations to British Library Oriental manuscript shelfmarks and folio references.",
            }
        ],
        "status_override": {
            "resolution_status": "probable_locator_system",
            "definition_quality": "holding_system_inferred_from_local_and_web_evidence",
            "current_expansion": "British Library Oriental manuscript shelfmark system",
            "confidence": "medium",
            "needs_human_review": "true",
        },
    },
    "RDASB": {
        "likely_source_type": "year-based report series",
        "specific_files_to_check": [
            "data/working/bibliography/local_sources/frasch_extracted_text.txt",
            "data/working/bibliography/local_sources/frasch_bagan_epig_database_abbreviations.tsv",
            "https://catalog.hathitrust.org/Record/002444321",
        ],
        "specific_search_terms": ["RDASB", "Report of the Director, Archaeological Survey of Burma", "Director of Archaeology"],
        "recommended_action": "promote to probable_expansion while keeping abbreviation confirmation open",
        "evidence_rows": [
            {
                "candidate_expansion": "Report of the Director, Archaeological Survey of Burma",
                "evidence_type": "source_list_entry",
                "source_file_id": "frasch-bagan-epig-abbreviations",
                "source_file_label": "frasch_bagan_epig_database_abbreviations.tsv",
                "source_location_hint": "RDASB row",
                "short_quote": "RDASB | Report of Director Arch. Survey Burma",
                "evidence_strength": "medium",
                "supports_expansion": "true",
                "contradicts_expansion": "false",
                "needs_human_review": "true",
                "notes": "The Frasch abbreviation witness gives a directly aligned publication-title candidate, albeit not as a formal printed abbreviation list.",
            },
            {
                "candidate_expansion": "Report of the Director, Archaeological Survey of Burma",
                "evidence_type": "contextual_usage",
                "source_file_id": "frasch-extracted-text",
                "source_file_label": "frasch_extracted_text.txt",
                "source_location_hint": "L353-L362",
                "short_quote": "References: Pl. V 557c; RDASB 1938, p. xi, and app. H, no. 5 ... RDASB 1938, p. xii, and app. H, no. 19",
                "evidence_strength": "medium",
                "supports_expansion": "true",
                "contradicts_expansion": "false",
                "needs_human_review": "true",
                "notes": "The corpus uses RDASB as a year-based report series with page and appendix locators, matching the Director report pattern.",
            }
        ],
        "status_override": {
            "resolution_status": "probable_expansion",
            "definition_quality": "source_title_inferred_from_publication_series",
            "current_expansion": "Report of the Director, Archaeological Survey of Burma",
            "confidence": "medium",
            "needs_human_review": "true",
        },
    },
    "TN": {
        "likely_source_type": "book/work shorthand",
        "specific_files_to_check": [
            "data/working/bibliography/local_sources/frasch_extracted_text.txt",
        ],
        "specific_search_terms": ["TN", "U Tun Nyein", "Inscriptions of Pagan, Pinya and Ava"],
        "recommended_action": "promote to confirmed_expansion",
        "evidence_rows": [
            {
                "candidate_expansion": "U Tun Nyein (tr.), Inscriptions of Pagan, Pinya and Ava",
                "evidence_type": "explicit_definition",
                "source_file_id": "frasch-extracted-text",
                "source_file_label": "frasch_extracted_text.txt",
                "source_location_hint": "L7880",
                "short_quote": "TN U Tun Nyein (tr.), Inscriptions of Pagan, Pinya and Ava, Rangoon 1897",
                "evidence_strength": "strong",
                "supports_expansion": "true",
                "contradicts_expansion": "false",
                "needs_human_review": "false",
                "notes": "Explicit abbreviation-list definition in Frasch's extracted text.",
            }
        ],
        "status_override": {
            "resolution_status": "confirmed_expansion",
            "definition_quality": "explicit",
            "current_expansion": "U Tun Nyein (tr.), Inscriptions of Pagan, Pinya and Ava",
            "confidence": "high",
            "needs_human_review": "false",
        },
    },
    "UEM": {
        "likely_source_type": "book/work shorthand",
        "specific_files_to_check": [
            "data/working/bibliography/local_sources/frasch_extracted_text.txt",
        ],
        "specific_search_terms": ["UEM", "U E Maung", "Selections from the Inscriptions of Pagan"],
        "recommended_action": "promote to confirmed_expansion",
        "evidence_rows": [
            {
                "candidate_expansion": "U E Maung (ed.), Selections from the Inscriptions of Pagan",
                "evidence_type": "explicit_definition",
                "source_file_id": "frasch-extracted-text",
                "source_file_label": "frasch_extracted_text.txt",
                "source_location_hint": "L7883-L7884",
                "short_quote": "UEM U E Maung (ed.), Selections from the Inscriptions of Pagan, Rangoon 1958",
                "evidence_strength": "strong",
                "supports_expansion": "true",
                "contradicts_expansion": "false",
                "needs_human_review": "false",
                "notes": "Explicit abbreviation-list definition in Frasch's extracted text.",
            }
        ],
        "status_override": {
            "resolution_status": "confirmed_expansion",
            "definition_quality": "explicit",
            "current_expansion": "U E Maung (ed.), Selections from the Inscriptions of Pagan",
            "confidence": "high",
            "needs_human_review": "false",
        },
    },
}

FINAL_SPRINT_CONFIG = {
    "RDASB": {
        "working_hypothesis": "publication-series shorthand for the Director reports of the Archaeological Survey of Burma",
        "hypothesis_source": "Frasch abbreviation witness plus year-based report citations",
        "search_strategy": "Check cached Frasch abbreviation/context files first, then confirm the publication title with targeted public catalogue searches.",
        "best_evidence_found": "The Frasch abbreviation witness gives 'Report of Director Arch. Survey Burma', and public catalogues confirm the recurring Director/Superintendent report series.",
        "notes": "Publication title is well supported, but the exact abbreviation line still remains inferred rather than directly printed in a recovered list.",
        "local_hits": [
            {
                "search_term": "RDASB",
                "file_or_folder_name": "frasch_bagan_epig_database_abbreviations.tsv",
                "path_or_redacted_path": "data/working/bibliography/local_sources/frasch_bagan_epig_database_abbreviations.tsv",
                "file_type": "tsv",
                "sha256_if_available": "",
                "match_reason": "Contains the candidate expansion 'Report of Director Arch. Survey Burma'.",
                "copied_or_existing_cache_path": "data/working/bibliography/local_sources/frasch_bagan_epig_database_abbreviations.tsv",
                "extraction_status": "existing_cache",
                "notes": "Used because the live OBI local roots were unavailable in this shell.",
            },
            {
                "search_term": "RDASB 1938",
                "file_or_folder_name": "frasch_extracted_text.txt",
                "path_or_redacted_path": "data/working/bibliography/local_sources/frasch_extracted_text.txt",
                "file_type": "txt",
                "sha256_if_available": "",
                "match_reason": "Preserves year/page/appendix references such as 'RDASB 1938, p. xi, app. H'.",
                "copied_or_existing_cache_path": "data/working/bibliography/local_sources/frasch_extracted_text.txt",
                "extraction_status": "existing_cache",
                "notes": "Supports a report-series interpretation rather than a one-off article.",
            },
        ],
        "web_searches": [
            {
                "query": "\"Report of the Director, Archaeological Survey of Burma\"",
                "result_title": "Report of the Director, Archaeological Survey, Burma. 1955: September ...",
                "result_url_or_domain": "https://www.asiabookroom.com/pages/books/165200/archaeological-survey-burma/report-of-the-director-archaeological-survey-burma-1955-september-1965-september",
                "short_result_summary": "Confirms that 'Report of the Director, Archaeological Survey, Burma' is a real recurring publication title.",
                "supports_candidate_expansion": "true",
                "confidence": "medium",
                "notes": "Supports the publication title even though the exact RDASB abbreviation line remains inferred.",
            }
        ],
    },
    "MP": {
        "working_hypothesis": "locator family for the Mandalay Palace stone collection rather than a published work",
        "hypothesis_source": "Frasch extracted text plus Bagan Epig Database local witness",
        "search_strategy": "Search cached Frasch text and Bagan Epig Database text for 'Mandalay Palace' and MP citation forms, then check targeted web results for collection-style usage.",
        "best_evidence_found": "The local evidence uses both 'Mandalay Palace stone ...' and 'MP stone ...', which points to a collection locator system rather than a title abbreviation.",
        "notes": "No reliable published title corresponding to MP was found; the strongest evidence is collection/location usage.",
        "local_hits": [
            {
                "search_term": "Mandalay Palace",
                "file_or_folder_name": "Bagan Epig Database.doc",
                "path_or_redacted_path": "data/local/bibliography_sources/bagan_epig_database-c4cfc990741f/Bagan Epig Database.doc",
                "file_type": "doc",
                "sha256_if_available": "c4cfc990741f133430be72befe492e0dfff950a0eb72e3fd641420fa48cb0187",
                "match_reason": "Targeted extraction found 'Mandalay Palace stone 291' and 'MP stone 507'.",
                "copied_or_existing_cache_path": "data/local/bibliography_sources/bagan_epig_database-c4cfc990741f/Bagan Epig Database.doc",
                "extraction_status": "reused_existing",
                "notes": "Strongest local witness tying the shorthand to Mandalay Palace stone identifiers.",
            },
            {
                "search_term": "MP 1, p.",
                "file_or_folder_name": "frasch_extracted_text.txt",
                "path_or_redacted_path": "data/working/bibliography/local_sources/frasch_extracted_text.txt",
                "file_type": "txt",
                "sha256_if_available": "",
                "match_reason": "Preserves page-style MP citations alongside Mandalay Palace stone references.",
                "copied_or_existing_cache_path": "data/working/bibliography/local_sources/frasch_extracted_text.txt",
                "extraction_status": "existing_cache",
                "notes": "Suggests a local card/list or notebook locator layered over the same collection.",
            },
        ],
        "web_searches": [
            {
                "query": "\"MP\" \"Mandalay Palace\" inscriptions Burma",
                "result_title": "New Documents from Mingun and the Pyu Area",
                "result_url_or_domain": "https://zenodo.org/records/7701258",
                "short_result_summary": "Web results cluster around Mandalay Palace stones and inscriptions rather than around a standalone publication titled MP.",
                "supports_candidate_expansion": "true",
                "confidence": "low",
                "notes": "Used only as supporting context; the local Mandalay Palace stone evidence is stronger.",
            }
        ],
    },
    "OR": {
        "working_hypothesis": "British Library Oriental manuscript shelfmark system",
        "hypothesis_source": "Frasch extracted text plus British Library shelfmark conventions",
        "search_strategy": "Check local Frasch references for explicit 'British Library Oriental Mss' wording, then confirm the shelfmark convention via targeted web searches.",
        "best_evidence_found": "The local Frasch witness explicitly says 'British Library Oriental Mss Section OR 3434', which anchors OR as a holdings shelfmark family.",
        "notes": "This is a holdings/locator authority, not a bibliographic title.",
        "local_hits": [
            {
                "search_term": "British Library Oriental Mss Sect",
                "file_or_folder_name": "frasch_extracted_text.txt",
                "path_or_redacted_path": "data/working/bibliography/local_sources/frasch_extracted_text.txt",
                "file_type": "txt",
                "sha256_if_available": "",
                "match_reason": "Contains 'British Library Oriental Mss Sect-ion OR 3434' and nearby Or. shelfmark references.",
                "copied_or_existing_cache_path": "data/working/bibliography/local_sources/frasch_extracted_text.txt",
                "extraction_status": "existing_cache",
                "notes": "Best local evidence for OR as a manuscript shelfmark system.",
            }
        ],
        "web_searches": [
            {
                "query": "\"British Library\" \"Or. 3475\" Burma",
                "result_title": "British Library Archives and Manuscripts Catalogue",
                "result_url_or_domain": "https://searcharchives.bl.uk/",
                "short_result_summary": "Confirms that Or./OR identifiers are British Library Oriental manuscript shelfmarks used for individual items.",
                "supports_candidate_expansion": "true",
                "confidence": "medium",
                "notes": "Web evidence confirms the shelfmark system while the local Frasch witness ties it directly to Burma-inscription references.",
            }
        ],
    },
    "Luce D": {
        "working_hypothesis": "unpublished Luce notebook locator family, specifically Notebook D",
        "hypothesis_source": "Frasch citation pattern plus Archive.org notebook description and Luce collection notes",
        "search_strategy": "Review local Luce cache files for notebook/card-index language, then confirm Notebook D via targeted archive searches.",
        "best_evidence_found": "Archive.org explicitly describes Notebook D as epigraphical notes with listed and unlisted inscriptions, matching the numbered Luce D citations.",
        "notes": "Treat as an archival locator family unless a publication using the same numbering system is found later.",
        "local_hits": [
            {
                "search_term": "Luce notes",
                "file_or_folder_name": "Luce_collection.doc",
                "path_or_redacted_path": "data/local/bibliography_sources/luce_collection-b951e346a053/Luce_collection.doc",
                "file_type": "doc",
                "sha256_if_available": "b951e346a053548d39ee01a07962e9a6259247fe69dcda4cca5a0ddc4406dc7b",
                "match_reason": "Local Luce collection witness describes postwar notebooks and rebuilt card indexing.",
                "copied_or_existing_cache_path": "data/local/bibliography_sources/luce_collection-b951e346a053/Luce_collection.doc",
                "extraction_status": "reused_existing",
                "notes": "General local support for private Luce note/index systems.",
            },
            {
                "search_term": "Luce D 825",
                "file_or_folder_name": "frasch_extracted_text.txt",
                "path_or_redacted_path": "data/working/bibliography/local_sources/frasch_extracted_text.txt",
                "file_type": "txt",
                "sha256_if_available": "",
                "match_reason": "Preserves numbered Luce D citations such as 'Luce D 825' and 'Luce D 835'.",
                "copied_or_existing_cache_path": "data/working/bibliography/local_sources/frasch_extracted_text.txt",
                "extraction_status": "existing_cache",
                "notes": "Matches a notebook-entry interpretation better than a published title.",
            },
        ],
        "web_searches": [
            {
                "query": "\"G. H. Luce\" \"Notebook D\"",
                "result_title": "Notebook D : BDRC: W2KG200022",
                "result_url_or_domain": "https://archive.org/details/bdrc-W2KG200022",
                "short_result_summary": "Archive.org explicitly lists Notebook D with epigraphical notes and inscription sections, supporting a private notebook locator reading.",
                "supports_candidate_expansion": "true",
                "confidence": "medium",
                "notes": "This is archive evidence, not evidence of a published work.",
            }
        ],
    },
    "Luce J": {
        "working_hypothesis": "unpublished Luce notebook locator family, specifically Notebook J",
        "hypothesis_source": "Frasch citation pattern plus Archive.org notebook description and Luce collection notes",
        "search_strategy": "Review local Luce cache files for notebook/card-index language, then confirm Notebook J via targeted archive searches.",
        "best_evidence_found": "Archive.org explicitly describes Notebook J as notes on inscriptions and transcription material, matching the numbered Luce J citations.",
        "notes": "Treat as an archival locator family unless later evidence links the J numbers to a publication.",
        "local_hits": [
            {
                "search_term": "Luce notes",
                "file_or_folder_name": "Luce_collection.doc",
                "path_or_redacted_path": "data/local/bibliography_sources/luce_collection-b951e346a053/Luce_collection.doc",
                "file_type": "doc",
                "sha256_if_available": "b951e346a053548d39ee01a07962e9a6259247fe69dcda4cca5a0ddc4406dc7b",
                "match_reason": "Local Luce collection witness describes Luce notebook and card-index material.",
                "copied_or_existing_cache_path": "data/local/bibliography_sources/luce_collection-b951e346a053/Luce_collection.doc",
                "extraction_status": "reused_existing",
                "notes": "General local support for private Luce note/index systems.",
            },
            {
                "search_term": "Luce J 2507",
                "file_or_folder_name": "frasch_extracted_text.txt",
                "path_or_redacted_path": "data/working/bibliography/local_sources/frasch_extracted_text.txt",
                "file_type": "txt",
                "sha256_if_available": "",
                "match_reason": "Preserves numbered Luce J citations such as 'Luce J 2507', 'Luce J2509', and 'Luce J 2689'.",
                "copied_or_existing_cache_path": "data/working/bibliography/local_sources/frasch_extracted_text.txt",
                "extraction_status": "existing_cache",
                "notes": "The citation pattern fits a notebook or card-index system, not a journal title.",
            },
        ],
        "web_searches": [
            {
                "query": "\"G. H. Luce\" \"Notebook J\"",
                "result_title": "Notebook J : BDRC: W2KG200024",
                "result_url_or_domain": "https://archive.org/details/bdrc-W2KG200024",
                "short_result_summary": "Archive.org explicitly lists Notebook J and describes inscription notes and transcription content that fit Luce J citations.",
                "supports_candidate_expansion": "true",
                "confidence": "medium",
                "notes": "This is archival notebook evidence rather than evidence for a published journal or article.",
            }
        ],
    },
    "IPPA": {
        "working_hypothesis": "IPPA is a structured-OBI variant locator family into the same work cited elsewhere as PPA",
        "hypothesis_source": "occurrence-level corpus review plus Frasch abbreviation-list control evidence",
        "search_strategy": "Inspect every corpus IPPA occurrence first, then test exact-context local and web searches against the PPA hypothesis.",
        "best_evidence_found": "The raw OBI source repeatedly uses IPPA beside or near explicit PPA citations, while Frasch defines only PPA = Inscriptions of Pagan, Pinya and Ava.",
        "notes": "IPPA no longer sits in the unresolved dossier because the corpus occurrence pattern is strong enough to classify it as a PPA-linked variant family.",
        "local_hits": [
            {
                "search_term": "IPPA-159",
                "file_or_folder_name": "OBI_Vol1_No4__ob_p11.txt",
                "path_or_redacted_path": "4321314/OBI_Corpus_Vol1.zip::OBI_Corpus_Vol1/OBI_Vol1_No4__ob_p11.txt",
                "file_type": "structured_txt_in_zip",
                "sha256_if_available": "",
                "match_reason": "Representative raw-source reference line contains both IPPA-159 and PPA, p. 159.",
                "copied_or_existing_cache_path": "data/release/corpus_release_v0_3/inscriptions.jsonl",
                "extraction_status": "existing_cache",
                "notes": "Direct corpus evidence that IPPA and PPA are linked within the same source record.",
            },
            {
                "search_term": "Inscriptions of Pagan, Pinya and Ava",
                "file_or_folder_name": "frasch_extracted_text.txt",
                "path_or_redacted_path": "data/working/bibliography/local_sources/frasch_extracted_text.txt",
                "file_type": "txt",
                "sha256_if_available": "",
                "match_reason": "Frasch abbreviation list explicitly defines PPA as Inscriptions of Pagan, Pinya and Ava, but omits IPPA.",
                "copied_or_existing_cache_path": "data/working/bibliography/local_sources/frasch_extracted_text.txt",
                "extraction_status": "existing_cache",
                "notes": "Supports routing IPPA to the same underlying PPA work without inventing a separate expansion.",
            },
        ],
        "web_searches": [
            {
                "query": "\"IPPA 101\" Burma",
                "result_title": "No useful exact-context web result for IPPA 101",
                "result_url_or_domain": "web_search",
                "short_result_summary": "Exact-context web searching did not surface an external source that defines IPPA; useful evidence still points back to PPA-focused materials.",
                "supports_candidate_expansion": "false",
                "confidence": "low",
                "notes": "Negative web evidence only; the actual classification comes from corpus occurrences and local source context.",
            },
            {
                "query": "\"IPPA 137-138\" Burma",
                "result_title": "No useful exact-context web result for IPPA 137-138",
                "result_url_or_domain": "web_search",
                "short_result_summary": "The exact 137-138 query likewise failed to identify a distinct IPPA source family outside the corpus itself.",
                "supports_candidate_expansion": "false",
                "confidence": "low",
                "notes": "Negative web evidence that reinforces the need to classify IPPA from corpus context rather than the open web.",
            },
            {
                "query": "\"IPPA\" \"Inscriptions of Pagan, Pinya and Ava\" Burma",
                "result_title": "Digital Library of Myanmar Literature — Inscriptions of Pagan, Pinya, and Ava",
                "result_url_or_domain": "eresource.nlm.gov.mm",
                "short_result_summary": "Web-visible sources continue to expose the standard PPA title and do not provide an explicit independent IPPA expansion.",
                "supports_candidate_expansion": "true",
                "confidence": "low",
                "notes": "Useful only as control evidence that the standard published title is PPA-related rather than a separate IPPA work.",
            }
        ],
    },
}

FRASCH_ABBREVIATION_LIST_REVIEW_ROWS = [
    {
        "line_range": "L7778-L7896",
        "acronyms_found": "SIP; TN; UB; UEM",
        "raw_excerpt_short": "SIP ... TN U Tun Nyein (tr.), Inscriptions of Pagan, Pinya and Ava ... UB ... UEM U E Maung (ed.), Selections from the Inscriptions of Pagan",
        "possible_missing_acronyms": "IPPA; Luce D; Luce J; MP; OR; RDASB",
        "notes": "Final sprint review of the main TN/UEM abbreviation-list region found none of the six final-sprint acronyms.",
    },
    {
        "line_range": "L8317-L8453",
        "acronyms_found": "IB; JBRS; JRAS; List; MM; OBI; Pl.",
        "raw_excerpt_short": "IB Inscriptions of Burma ... JBRS ... JRAS ... List ... MM Middle Mon ... OBI ... Pl. Inscriptions of Burma",
        "possible_missing_acronyms": "IPPA; Luce D; Luce J; MP; OR; RDASB",
        "notes": "The later Frasch abbreviation slice confirms several other source works and locators but still omits the six final-sprint acronyms.",
    },
]


def parse_locator(raw_reference: str, family_id: str, family_label: str) -> tuple[str, str]:
    text = raw_reference.strip()
    if not text:
        return "", "unclear"

    if family_id == "fam-list-catalogue":
        locator = re.sub(r"^List\b[\s,:-]*", "", text, flags=re.IGNORECASE).strip()
        if locator:
            return locator, "catalogue_number"

    if family_id == "fam-ippa-catalogue":
        locator = re.sub(r"^IPPA\b[\s,:-]*", "", text, flags=re.IGNORECASE).strip()
        if locator:
            return locator, "number"

    if family_id == "fam-or-catalogue":
        locator = re.sub(r"^OR\b[\s,:-]*", "", text, flags=re.IGNORECASE).strip()
        if locator:
            return locator, "folio" if "verso" in locator.casefold() or "folio" in locator.casefold() else "number"

    if family_label.startswith("Pl"):
        locator = re.sub(r"^Pl\.?\s*", "", text, flags=re.IGNORECASE).strip(" ,")
        return locator or text, "plate"

    if family_label and text.casefold().startswith(family_label.casefold()):
        locator = text[len(family_label) :].strip(" ,")
        locator = re.sub(r"^[-–—:]+", "", locator).strip()
        if locator:
            lowered_locator = locator.casefold()
            if re.search(r"\bfol\.?\b", lowered_locator):
                return locator, "folio"
            if re.fullmatch(r"p+\.\s*[0-9-]+", locator, flags=re.IGNORECASE):
                return locator, "page"
            if family_id == "fam-ippa-catalogue":
                ippa_match = re.match(r"([0-9][0-9,\- ]*[0-9])", locator)
                if ippa_match:
                    return ippa_match.group(1).strip(), "number"
                if re.fullmatch(r"[0-9,\- ]+", locator):
                    return locator, "number"
            if family_id == "fam-iob-catalogue":
                iob_match = re.match(r"([0-9A-Za-z.-]+)", locator)
                if iob_match:
                    return iob_match.group(1).strip(), "catalogue_number"
            if "catalogue" in family_id and re.fullmatch(r"[0-9A-Za-z.-]+", locator):
                return locator, "catalogue_number"
            if family_id in {"fam-list-catalogue", "fam-iob-catalogue"} and re.fullmatch(r"[0-9A-Za-z.-]+", locator):
                return locator, "catalogue_number"
            if re.fullmatch(r"(?:vol\.?\s*)?[IVXLC0-9]+[, ]+p+\.\s*[0-9-]+", locator, flags=re.IGNORECASE):
                return locator, "volume_page"
            if re.fullmatch(r"[IVXLC0-9]+\s*,?\s*p+\.\s*[0-9-]+", locator, flags=re.IGNORECASE):
                return locator, "volume_page"
            if re.fullmatch(r"(?:19|20)\d{2}(?:\s*[,;]\s*p+\.\s*[0-9-]+)?", locator, flags=re.IGNORECASE):
                if "p." in lowered_locator:
                    return locator, "series_year_page"
                return locator, "year"
            if re.fullmatch(r"[0-9A-Za-z.-]+", locator):
                return locator, "number"
            if any(char.isdigit() for char in locator):
                return locator, "volume_page"
            return locator, "unclear"

    folio_match = re.search(r"\bfol\.?\s*([0-9A-Za-zĀāĪīŪūṅñṭḍṇśṣḥṃ\- ]+)", text, flags=re.IGNORECASE)
    if folio_match:
        return folio_match.group(1).strip(), "folio"
    plate_match = re.search(r"\bpl\.?\s*([IVXLC0-9A-Za-z.-]+(?:\s+[0-9A-Za-z.-]+)?)", text, flags=re.IGNORECASE)
    if plate_match:
        return plate_match.group(1).strip(), "plate"
    volume_page_match = re.search(r"\b([IVXLC0-9]+)\s*,?\s*p+\.\s*([0-9-]+)", text, flags=re.IGNORECASE)
    if volume_page_match:
        return f"{volume_page_match.group(1)}, p. {volume_page_match.group(2)}", "volume_page"
    series_year_page_match = re.search(r"\b((?:19|20)\d{2}[^,;]*[,;]\s*p+\.\s*[0-9-]+)\b", text, flags=re.IGNORECASE)
    if series_year_page_match:
        return series_year_page_match.group(1).strip(), "series_year_page"
    page_match = re.search(r"\bp+\.\s*([0-9-]+)", text, flags=re.IGNORECASE)
    if page_match:
        return page_match.group(1), "page"
    number_match = re.search(r"\b(?:no\.?|nr\.?)\s*([0-9A-Za-z.-]+)", text, flags=re.IGNORECASE)
    if number_match:
        return number_match.group(1), "catalogue_number"
    year_match = re.search(r"\b(1[0-9]{3}|20[0-9]{2})\b", text)
    if year_match:
        return year_match.group(1), "year"
    standalone_number_match = re.fullmatch(r"[0-9A-Za-z.-]+", text)
    if standalone_number_match:
        return text, "number"
    return text, "unclear"


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def split_reference_field(text: str) -> list[str]:
    return [part.strip() for part in (text or "").split(";") if part.strip()]


def normalize_reference_token(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip()).casefold()


def find_reference_index(parts: list[str], raw_reference: str) -> int:
    normalized_raw = normalize_reference_token(raw_reference)
    for index, part in enumerate(parts):
        if normalize_reference_token(part) == normalized_raw:
            return index
    for index, part in enumerate(parts):
        if normalized_raw and normalized_raw in normalize_reference_token(part):
            return index
    return -1


def parse_numeric_tokens(text: str) -> list[int]:
    return [int(token) for token in re.findall(r"\d+", text or "")]


def classify_ippa_ppa_relation(ippa_locator: str, ppa_reference: str) -> tuple[str, str]:
    if not ppa_reference:
        return "IPPA-only numeric locator in reviewed record/cluster", "low"
    ippa_numbers = parse_numeric_tokens(ippa_locator)
    ppa_numbers = parse_numeric_tokens(ppa_reference)
    if ippa_numbers and ppa_numbers and set(ippa_numbers) == set(ppa_numbers):
        return "exact numeric match to PPA page citation", "high"
    if ippa_numbers and ppa_numbers and set(ippa_numbers).intersection(ppa_numbers):
        return "partial numeric overlap with PPA page citation", "medium"
    return "paired with PPA source but using a different numeric locator", "medium"


def relative_display_path(path: Path) -> str:
    try:
        return path.relative_to(Path.cwd()).as_posix()
    except ValueError:
        return path.as_posix()


def collect_searchable_text_files() -> list[Path]:
    roots = [
        Path("data/working/bibliography/local_sources"),
        Path("data/local/ocr_text"),
        Path("data/local/bibliography_sources"),
    ]
    allowed_suffixes = {".txt", ".tsv", ".csv", ".json", ".jsonl", ".bib", ".md"}
    files: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix.casefold() not in allowed_suffixes:
                continue
            try:
                if path.stat().st_size > 1_500_000:
                    continue
            except OSError:
                continue
            files.append(path)
    return files


def find_query_in_files(query: str, files: list[Path]) -> dict | None:
    lowered_query = query.casefold()
    if not lowered_query:
        return None
    for path in files:
        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        for line_number, line in enumerate(lines, start=1):
            lowered_line = line.casefold()
            if lowered_query not in lowered_line:
                continue
            start = lowered_line.index(lowered_query)
            end = start + len(query)
            return {
                "matched_file_id": hashlib.sha256(relative_display_path(path).encode("utf-8")).hexdigest()[:12],
                "matched_file_label": path.name,
                "match_location": f"{relative_display_path(path)}:L{line_number}",
                "short_context_before": line[max(0, start - 60) : start].strip(),
                "match_text": line[start:end].strip() or query,
                "short_context_after": line[end : end + 60].strip(),
            }
    return None


def build_ippa_review_artifacts(
    *,
    corpus_inscriptions_path: Path,
    reference_occurrences_path: Path,
    frasch_extracted_text_path: Path,
) -> dict:
    records = read_jsonl(corpus_inscriptions_path)
    record_by_id = {row.get("record_id", ""): row for row in records if row.get("record_id")}
    cluster_to_records: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in records:
        cluster_to_records[(row.get("source_volume", ""), row.get("source_inscription_number", ""))].append(row)

    occurrence_rows = [
        row
        for row in read_tsv(reference_occurrences_path)
        if normalize_reference_token(row.get("raw_reference_string", "")).startswith("ippa")
    ]
    if not occurrence_rows:
        for row in records:
            for raw_reference in split_reference_field(row.get("references_original", "")):
                if normalize_reference_token(raw_reference).startswith("ippa"):
                    occurrence_rows.append({"record_id": row.get("record_id", ""), "raw_reference_string": raw_reference})

    ippa_occurrence_rows: list[dict] = []
    ippa_comparison_rows: list[dict] = []
    ippa_record_review_by_id: dict[str, dict] = {}
    unique_queries: list[str] = []
    seen_queries: set[str] = set()

    for index, occurrence in enumerate(occurrence_rows, start=1):
        record_id = occurrence.get("record_id", "")
        raw_reference = occurrence.get("raw_reference_string", "").strip()
        record = record_by_id.get(record_id, {})
        references_original = record.get("references_original", "") or ""
        parts = split_reference_field(references_original)
        reference_index = find_reference_index(parts, raw_reference)
        previous_reference = parts[reference_index - 1] if reference_index > 0 else ""
        next_reference = parts[reference_index + 1] if 0 <= reference_index < len(parts) - 1 else ""
        parsed_locator, locator_type = parse_locator(raw_reference, "fam-ippa-catalogue", "IPPA")
        cluster = (record.get("source_volume", ""), record.get("source_inscription_number", ""))
        cluster_records = cluster_to_records.get(cluster, [])
        same_record_ppa = [part for part in parts if part.casefold().startswith("ppa")]
        cluster_ppa = [
            part
            for cluster_record in cluster_records
            if cluster_record.get("record_id") != record_id
            for part in split_reference_field(cluster_record.get("references_original", ""))
            if part.casefold().startswith("ppa")
        ]
        if same_record_ppa:
            note = f"Same record also cites {same_record_ppa[0]}."
        elif cluster_ppa:
            note = f"Companion face/page in the same inscription cluster cites {cluster_ppa[0]}."
        else:
            note = "No explicit PPA citation survives on this record or its sibling records; classification relies on the wider IPPA/PPA occurrence pattern."
        ippa_occurrence_rows.append(
            {
                "occurrence_id": f"ippa-occ-{index:04d}",
                "record_id": record_id,
                "source_deposit": record.get("source_deposit", ""),
                "source_layer": record.get("source_layer", ""),
                "source_volume": record.get("source_volume", ""),
                "source_inscription_number": record.get("source_inscription_number", ""),
                "title_original": record.get("title_original", ""),
                "raw_reference_string": raw_reference,
                "full_references_original": references_original,
                "neighboring_reference_before": previous_reference,
                "neighboring_reference_after": next_reference,
                "parsed_locator": parsed_locator,
                "line_or_record_context": f"references_original on {record.get('face', '') or 'text'} face/page {record.get('source_page', '')}; locator_type={locator_type}",
                "notes": note,
            }
        )
        comparison_reference = same_record_ppa[0] if same_record_ppa else (cluster_ppa[0] if cluster_ppa else "")
        relation_label, relation_confidence = classify_ippa_ppa_relation(parsed_locator, comparison_reference)
        ippa_comparison_rows.append(
            {
                "ippa_reference": raw_reference,
                "ppa_like_reference": comparison_reference,
                "shared_record_id": record_id,
                "same_or_neighboring_reference_field": (
                    "same record"
                    if same_record_ppa
                    else "same inscription cluster"
                    if cluster_ppa
                    else "no explicit PPA neighbour"
                ),
                "locator_pattern": relation_label,
                "source_context": f"{record.get('record_id', '')} | vol. {record.get('source_volume', '')} no. {record.get('source_inscription_number', '')}",
                "looks_like_alias": "true" if same_record_ppa or cluster_ppa else "false",
                "looks_like_typo": "false",
                "looks_like_distinct_source": "false" if same_record_ppa or cluster_ppa else "false",
                "confidence": relation_confidence,
                "notes": note,
            }
        )
        if raw_reference not in seen_queries:
            seen_queries.add(raw_reference)
            unique_queries.append(raw_reference)

    for record in records:
        references_original = record.get("references_original", "") or ""
        if "IPPA" not in references_original:
            continue
        parts = split_reference_field(references_original)
        ippa_parts = [part for part in parts if part.casefold().startswith("ippa")]
        other_parts = [part for part in parts if not part.casefold().startswith("ippa")]
        cluster = (record.get("source_volume", ""), record.get("source_inscription_number", ""))
        cluster_ppa = [
            part
            for cluster_record in cluster_to_records.get(cluster, [])
            if cluster_record.get("record_id") != record.get("record_id")
            for part in split_reference_field(cluster_record.get("references_original", ""))
            if part.casefold().startswith("ppa")
        ]
        parallel_sources = [part for part in other_parts if part.startswith(("PPA", "OBI", "List", "Pl.", "A", "B", "UB", "UEM", "TN", "MP", "RDASB"))]
        if any(part.casefold().startswith("ppa") for part in other_parts):
            relationship = "IPPA is paired with explicit PPA on the same record."
            confidence = "high"
        elif cluster_ppa:
            relationship = "IPPA is paired with explicit PPA on a companion face/page in the same inscription cluster."
            confidence = "medium"
        else:
            relationship = "IPPA behaves like the PPA family but survives here without an explicit PPA companion citation."
            confidence = "medium"
        ippa_record_review_by_id[record["record_id"]] = {
            "record_id": record.get("record_id", ""),
            "title_original": record.get("title_original", ""),
            "references_original": references_original,
            "other_sources_cited": " | ".join(other_parts[:8]),
            "IPPA_locator": " | ".join(parse_locator(part, "fam-ippa-catalogue", "IPPA")[0] for part in ippa_parts),
            "parallel_OBI_or_List_or_PPA_reference": " | ".join((parallel_sources or cluster_ppa)[:6]),
            "likely_source_relationship": relationship,
            "review_decision": "alias_or_variant_of_PPA",
            "confidence": confidence,
            "notes": "Raw IPPA strings are preserved, but the underlying source work is treated as the PPA family.",
        }

    local_queries = unique_queries + [
        query
        for query in [
            "IPPA",
            "I PPA",
            "I.P.P.A.",
            "I.P.A.",
            "IPPA 101",
            "IPPA 102",
            "IPPA 137",
            "IPPA 138",
            "PPA 101",
            "PPA 102",
            "PPA 137",
            "PPA 138",
            "Pagan Pinya Ava 101",
            "Pagan Pinya Ava 137",
            "Inscriptions of Pagan, Pinya and Ava",
        ]
        if query not in seen_queries
    ]
    searchable_files = collect_searchable_text_files()
    local_context_rows: list[dict] = []
    for query in local_queries:
        match = find_query_in_files(query, searchable_files)
        if match:
            local_context_rows.append(
                {
                    "query": query,
                    "matched_file_id": match["matched_file_id"],
                    "matched_file_label": match["matched_file_label"],
                    "match_location": match["match_location"],
                    "short_context_before": match["short_context_before"],
                    "match_text": match["match_text"],
                    "short_context_after": match["short_context_after"],
                    "evidence_type": "abbreviation_list" if "pagan, pinya and ava" in query.casefold() else "contextual_usage",
                    "supports_alias_of_ppa": "true" if "pagan, pinya and ava" in query.casefold() else "false",
                    "supports_distinct_expansion": "false",
                    "supports_typo": "false",
                    "confidence": "medium" if "pagan, pinya and ava" in query.casefold() else "low",
                    "notes": (
                        "Positive local control hit for the underlying PPA source title."
                        if "pagan, pinya and ava" in query.casefold()
                        else "Exact query was found in the local extracted-text cache."
                    ),
                }
            )
        else:
            local_context_rows.append(
                {
                    "query": query,
                    "matched_file_id": "",
                    "matched_file_label": "",
                    "match_location": "",
                    "short_context_before": "",
                    "match_text": "",
                    "short_context_after": "",
                    "evidence_type": "negative_search",
                    "supports_alias_of_ppa": "false",
                    "supports_distinct_expansion": "false",
                    "supports_typo": "false",
                    "confidence": "low",
                    "notes": "No exact hit in the searched local extracted-text cache under data/local/ocr_text, data/local/bibliography_sources, or data/working/bibliography/local_sources.",
                }
            )

    frasch_neighbourhood_rows = [
        {
            "source_file": relative_display_path(frasch_extracted_text_path),
            "line_range": "L7859-L7884",
            "excerpt_short": "ABBREVIATIONS ... Pl. ... PPA Arch. Survey of Burma (ed.), Inscriptions of Pagan, Pinya and Ava ... TN ... UEM ...",
            "contains_ppa": "true",
            "contains_ippa": "false",
            "contains_related_abbreviations": "Pl.; PPA; TN; UEM",
            "interpretation": "Frasch explicitly defines PPA in the abbreviation list but does not define IPPA there.",
            "notes": "This is the key positive local definition for the underlying PPA source work.",
        },
        {
            "source_file": relative_display_path(frasch_extracted_text_path),
            "line_range": "L8391-L8453",
            "excerpt_short": "Abbreviations ... IB Inscriptions of Burma ... List ... MM ... OBI ... Pl. Inscriptions of Burma ...",
            "contains_ppa": "false",
            "contains_ippa": "false",
            "contains_related_abbreviations": "IB; List; MM; OBI; Pl.",
            "interpretation": "The later abbreviation slice again omits IPPA while confirming other established source works and locator systems.",
            "notes": "Negative evidence against a standard Frasch-defined IPPA acronym.",
        },
    ]

    targeted_ocr_rows = [
        {
            "source_file_id": "obi-vol1-no4-ob-p11",
            "source_file_label": "OBI_Corpus_Vol1/OBI_Vol1_No4__ob_p11.txt",
            "reason_for_targeting": "Representative same-record IPPA/PPA pairing in the raw structured source.",
            "page_or_region": "REFERENCES line",
            "ocr_attempted": "false",
            "ocr_success": "false",
            "short_result": "Skipped: the raw structured TXT already preserves the reference line clearly.",
            "supports_resolution": "true",
            "notes": "Targeted OCR was unnecessary because the structured OBI source is already machine-readable here.",
        },
        {
            "source_file_id": "obi-vol4-no36-re-p59",
            "source_file_label": "OBI_Corpus_Vol4/OBI_Vol4_No36__re_p59.txt",
            "reason_for_targeting": "Representative IPPA-only record chosen to test whether OCR would add anything beyond the existing structured source.",
            "page_or_region": "REFERENCES line",
            "ocr_attempted": "false",
            "ocr_success": "false",
            "short_result": "Skipped: the structured source already gives the exact IPPA token and surrounding citations.",
            "supports_resolution": "true",
            "notes": "Occurrence-level review was sufficient without broad or page-level OCR.",
        },
    ]

    same_record_or_cluster_support = sum(
        1 for row in ippa_comparison_rows if row["same_or_neighboring_reference_field"] != "no explicit PPA neighbour"
    )
    decision_rows = [
        {
            "decision": "alias_or_variant_of_PPA",
            "expansion_or_classification": "IPPA variant locator family into Inscriptions of Pagan, Pinya and Ava",
            "confidence": "medium",
            "evidence_summary": (
                f"Reviewed {len(ippa_occurrence_rows)} IPPA occurrences across {len(ippa_record_review_by_id)} records; "
                f"{same_record_or_cluster_support} occurrences have explicit PPA support in the same record or inscription cluster, "
                "and Frasch defines PPA but never IPPA."
            ),
            "occurrences_reviewed": str(len(ippa_occurrence_rows)),
            "local_contexts_reviewed": str(len(local_context_rows)),
            "frasch_neighbourhood_reviewed": str(len(frasch_neighbourhood_rows)),
            "record_contexts_reviewed": str(len(ippa_record_review_by_id)),
            "web_queries_reviewed": "3",
            "remaining_uncertainty": "The long form behind the initial I remains undocumented, and some IPPA locators do not equal the printed PPA page numbers.",
            "recommended_authority_update": "Keep sf-ippa as an alias/variant family linked to sf-ppa and ppaCatalogue; preserve raw IPPA strings in the crosswalk.",
            "notes": "The corpus evidence supports a PPA-related variant family rather than a distinct bibliographic work.",
        }
    ]

    return {
        "occurrence_rows": ippa_occurrence_rows,
        "comparison_rows": ippa_comparison_rows,
        "local_context_rows": local_context_rows,
        "frasch_neighbourhood_rows": frasch_neighbourhood_rows,
        "record_review_rows": sorted(ippa_record_review_by_id.values(), key=lambda row: row["record_id"]),
        "targeted_ocr_rows": targeted_ocr_rows,
        "decision_row": decision_rows[0],
        "decision_rows": decision_rows,
        "summary": {
            "decision": decision_rows[0]["decision"],
            "classification": decision_rows[0]["expansion_or_classification"],
            "confidence": decision_rows[0]["confidence"],
            "occurrence_count": len(ippa_occurrence_rows),
            "record_count": len(ippa_record_review_by_id),
            "same_record_or_cluster_support": same_record_or_cluster_support,
        },
    }


def normalize_title(value: str) -> str:
    return normalize_for_match(value)


def local_source_kind(row: dict) -> str:
    original = row.get("original_path", "").casefold()
    if "frasch" in original or "bagan epig" in original:
        return "frasch_word_document"
    if "luce" in original:
        return "local_luce_folder"
    return "local_burma_folder"


def shorten_text(value: str, max_length: int = MAX_BIBTEX_EVIDENCE_LENGTH) -> str:
    text = re.sub(r"\s+", " ", (value or "").strip())
    if len(text) <= max_length:
        return text
    return text[: max_length - 1].rstrip() + "…"


def evidence_excerpt(value: str) -> str:
    return shorten_text(value, MAX_BIBTEX_EVIDENCE_LENGTH)


def short_reference(value: str) -> str:
    return shorten_text(value, MAX_MATCHED_REFERENCE_LENGTH)


def text_hash(*parts: str) -> str:
    blob = " || ".join(part for part in parts if part)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest() if blob else ""


def needs_human_review(status: str, review_status: str) -> str:
    if review_status.startswith("reviewed_") and status in {"confirmed_external_bibtex", "confirmed_local_source"}:
        return "false"
    return "true"


def normalize_source_family_key(value: str) -> str:
    normalized = re.sub(r"[.\s]+", " ", (value or "").strip().casefold())
    return normalized.strip()


def infer_source_family_key(family_id: str, family_label: str, sample_raw_references: str = "") -> str | None:
    normalized_label = normalize_source_family_key(family_label)
    for key, metadata in SOURCE_FAMILY_SEMANTICS.items():
        if family_id == metadata.get("canonical_family_id"):
            return key
        if any(family_id.startswith(prefix) for prefix in metadata.get("family_prefixes", [])):
            return key
        abbreviation = normalize_source_family_key(metadata.get("abbreviation", key))
        if normalized_label == abbreviation:
            return key
    return None


def resolution_from_authority_row(row: dict) -> tuple[str, str]:
    authority_status = row.get("authority_status", "")
    entry_type = row.get("entry_type", "")
    if authority_status in {"confirmed_external_bibtex", "confirmed_local_source"}:
        if entry_type == "article":
            return "confirmed_work", "article"
        if entry_type == "book":
            return "confirmed_work", "book"
        return "confirmed_work", "work"
    if authority_status in {"provisional_local_source", "provisional_catalogue", "provisional_publication"}:
        if entry_type == "article":
            return "provisional_work", "article"
        if entry_type == "book":
            return "provisional_work", "book"
        return "provisional_work", "work"
    return "needs_human_review", "unknown"


def source_family_match_type(resolution_status: str, resolution_level: str) -> str:
    if resolution_status == "alias_resolved":
        return "alias_source_family_match"
    if resolution_status == "series_level_resolved":
        return "series_level_match"
    if resolution_status in {"source_family_resolved", "confirmed_work"} and resolution_level == "internal_reference":
        return "internal_reference_match"
    if resolution_status in {"source_family_resolved", "confirmed_work"}:
        return "source_family_match"
    return "source_family_match"


def build_source_family_lookup(family_rows: list[dict]) -> tuple[dict[str, dict], dict[str, dict]]:
    families_by_id = {row["family_id"]: row for row in family_rows}
    matched_family_ids: dict[str, list[str]] = defaultdict(list)
    family_to_source_family: dict[str, str] = {}

    for row in family_rows:
        key = infer_source_family_key(row["family_id"], row.get("family_label", ""), row.get("sample_raw_references", ""))
        if not key:
            continue
        family_to_source_family[row["family_id"]] = key
        matched_family_ids[key].append(row["family_id"])

    source_family_rows: dict[str, dict] = {}
    for key, family_ids in matched_family_ids.items():
        metadata = SOURCE_FAMILY_SEMANTICS[key]
        primary_family_id = metadata.get("canonical_family_id")
        if not primary_family_id or primary_family_id not in families_by_id:
            primary_family_id = max(
                family_ids,
                key=lambda family_id: int(families_by_id[family_id].get("occurrence_count", "0") or "0"),
            )
        primary_row = families_by_id[primary_family_id]
        matched_rows = [families_by_id[family_id] for family_id in family_ids]
        source_family_rows[metadata["source_family_id"]] = {
            "source_family_id": metadata["source_family_id"],
            "source_family_key": key,
            "abbreviation": metadata["abbreviation"],
            "family_id": primary_family_id,
            "source_family_type": metadata["source_family_type"],
            "resolution_status": metadata["resolution_status"],
            "resolution_level": metadata["resolution_level"],
            "canonical_label": SOURCE_FAMILY_LIBRARY.get(key, {}).get("title", metadata["abbreviation"]),
            "expanded_label": SOURCE_FAMILY_LIBRARY.get(key, {}).get("title", metadata["abbreviation"]),
            "locator_pattern": metadata["locator_pattern"],
            "confidence": metadata["confidence"],
            "needs_human_review": metadata["needs_human_review"],
            "notes": metadata["notes"],
            "matched_family_ids": family_ids,
            "matched_rows": matched_rows,
            "occurrence_count": sum(int(row.get("occurrence_count", "0") or "0") for row in matched_rows),
            "example_raw_references": " | ".join(
                row.get("sample_raw_references", "")
                for row in matched_rows[:3]
                if row.get("sample_raw_references")
            ),
        }
    return source_family_rows, family_to_source_family


def truthy(value: str) -> bool:
    return (value or "").strip().casefold() in {"1", "true", "yes", "y"}


def canonical_source_work_key(source_work_key: str) -> str:
    return SOURCE_WORK_KEY_NORMALIZATION_MAP.get(source_work_key, source_work_key)


def normalize_script_value(value: str, *, fallback_title: str = "") -> str:
    normalized = SCRIPT_NORMALIZATION_MAP.get((value or "").strip().casefold(), value or "")
    if normalized:
        return normalized
    if fallback_title and re.search(r"[A-Za-z]", fallback_title):
        return "Latn"
    return value or ""


def clean_bibtex_summary_text(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", (text or "").strip())
    cleaned = cleaned.replace(" ... ", "; ")
    if len(cleaned) > 180:
        cleaned = evidence_excerpt(cleaned)
    return cleaned


def looks_like_ocr_garbage(text: str) -> bool:
    cleaned = (text or "").strip()
    if not cleaned:
        return False
    if re.search(r"[\u1000-\u109F]", cleaned):
        return True
    return len(re.findall(r"\b[A-Za-z]\b", cleaned)) >= 6


def authority_level_requires_bibtex(authority_level: str) -> bool:
    return authority_level in {
        "series",
        "periodical",
        "source_work",
        "source_catalogue",
        "corpus_source",
        "article",
        "book",
    }


def is_placeholder_expansion(value: str) -> bool:
    text = (value or "").strip()
    return not text or bool(PLACEHOLDER_EXPANSION_PATTERN.search(text))


def acronym_quality_rank(value: str) -> int:
    return {
        "manual_seed": 6,
        "explicit": 5,
        "strong": 4,
        "medium": 3,
        "weak": 2,
        "context_only": 1,
        "not_found": 0,
    }.get(value or "", 0)


def choose_best_acronym_candidate(rows: list[dict]) -> dict | None:
    if not rows:
        return None
    return max(
        rows,
        key=lambda row: (
            1 if row.get("evidence_type", "") in STRONG_DEFINITION_EVIDENCE_TYPES else 0,
            acronym_quality_rank(row.get("definition_quality", "")),
            1 if not truthy(row.get("needs_human_review", "")) else 0,
            row.get("confidence", ""),
            -(len((row.get("raw_definition", "") or "").strip()) or 999),
        ),
    )


def load_acronym_candidates(path: Path) -> dict[str, list[dict]]:
    if not path.exists():
        return {}
    rows_by_acronym: dict[str, list[dict]] = defaultdict(list)
    for row in read_tsv(path):
        rows_by_acronym[row.get("acronym", "")].append(row)
    return rows_by_acronym


def load_json_report(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_manual_acronym_seeds(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    return {
        row.get("acronym", ""): row
        for row in read_tsv(path)
        if row.get("acronym")
    }


def normalized_expansion_match(left: str, right: str) -> bool:
    return normalize_source_family_key(left) == normalize_source_family_key(right)


def normalized_seed_match(seed_expansion: str, documentary_expansion: str) -> bool:
    def simplify(value: str) -> str:
        without_parens = re.sub(r"\([^)]*\)", "", value or "")
        without_years = re.sub(r"\b[12][0-9]{3}(?:[–-][12][0-9]{3})?\b", "", without_parens)
        return normalize_source_family_key(without_years)

    seed_simple = simplify(seed_expansion)
    documentary_simple = simplify(documentary_expansion)
    return bool(seed_simple and documentary_simple and (seed_simple == documentary_simple or seed_simple in documentary_simple or documentary_simple in seed_simple))


def manual_seed_candidate(seed_row: dict) -> dict:
    acronym = seed_row.get("acronym", "")
    expansion = seed_row.get("expansion", "")
    return {
        "candidate_id": f"manual-seed:{normalize_source_family_key(acronym).replace(' ', '-')}",
        "acronym": acronym,
        "candidate_expansion": expansion,
        "raw_definition": expansion,
        "definition_context": expansion,
        "source_file_id": "",
        "source_file_label": seed_row.get("supplied_by", "Nathan Hill"),
        "source_location_hint": "manual acronym seed",
        "evidence_type": "manual_scholarly_identification",
        "confidence": seed_row.get("confidence", "high") or "high",
        "definition_quality": "manual_seed",
        "needs_human_review": "false",
        "notes": seed_row.get("notes", ""),
    }


ACRONYM_STATUS_DEFAULTS = {
    "PPA": {"resolution_status": "confirmed_expansion"},
    "IPPA": {"resolution_status": "alias_or_variant_of_PPA"},
    "IOB": {"resolution_status": "internal_locator", "current_expansion": "Locator reference into Inscriptions of Burma"},
    "UEM": {"resolution_status": "confirmed_expansion"},
    "SIP": {"resolution_status": "confirmed_expansion"},
    "MP": {"resolution_status": "probable_locator_system"},
    "UB": {"resolution_status": "confirmed_expansion"},
    "MM": {"resolution_status": "confirmed_expansion", "current_expansion": "Middle Mon"},
    "OR": {"resolution_status": "probable_locator_system"},
    "TN": {"resolution_status": "confirmed_expansion"},
    "U Min Hswe": {"resolution_status": "not_an_acronym", "current_expansion": "U Min Hswe"},
    "Luce D": {"resolution_status": "probable_private_luce_locator_system"},
    "Luce J": {"resolution_status": "probable_private_luce_locator_system"},
    "Pl.": {"resolution_status": "internal_locator", "current_expansion": "Plate reference into Inscriptions of Burma"},
    "A": {"resolution_status": "probable_expansion", "current_expansion": "Bagan Epigraphic Database, Part A"},
    "B": {"resolution_status": "probable_expansion", "current_expansion": "Bagan Epigraphic Database, Part B"},
    "BED B": {"resolution_status": "probable_expansion", "current_expansion": "Bagan Epigraphic Database, Part B"},
    "ARASI": {"resolution_status": "confirmed_expansion"},
    "RDASB": {"resolution_status": "probable_expansion"},
    "BBHC": {"resolution_status": "confirmed_expansion"},
}

NON_BIBTEX_LOCATOR_ACRONYM_STATUSES = {
    "alias_or_variant_of_PPA",
    "probable_typo_for_PPA",
    "internal_locator_system",
    "internal_locator",
    "probable_locator_system",
    "probable_private_luce_locator_system",
    "source_family_with_unknown_expansion_but_known_function",
}


def next_acronym_action(status: str) -> str:
    if status == "confirmed_expansion":
        return "keep current definition evidence"
    if status == "probable_expansion":
        return "confirm with corpus documentation or abbreviation list"
    if status == "alias_or_variant_of_PPA":
        return "preserve raw IPPA strings while routing the family to the underlying PPA source work"
    if status == "probable_typo_for_PPA":
        return "preserve raw typo strings but normalize the authority target to PPA"
    if status == "internal_locator_system":
        return "treat as a locator system rather than a standalone bibliographic work"
    if status == "probable_locator_system":
        return "preserve locator semantics and avoid creating a standalone bibliographic work"
    if status == "probable_private_luce_locator_system":
        return "treat as unpublished Luce locator family unless stronger publication evidence appears"
    if status == "internal_locator":
        return "preserve locator semantics; no bibliographic expansion needed"
    if status == "not_an_acronym":
        return "treat as named person/source family"
    if status == "unresolved_after_targeted_search":
        return "keep unresolved and document searched files and terms"
    if status == "unresolved_after_exhaustive_search":
        return "retain only the documented search trail and defer to human review"
    if status == "genuinely_unresolved_after_occurrence_level_review":
        return "retain the full occurrence-level review trail and defer any stronger claim"
    if status == "contextual_usage_only":
        return "search explicit abbreviation list or bibliography heading"
    if status == "source_family_only":
        return "retain source-family mapping and keep acronym visibly unexpanded"
    if status == "source_family_with_unknown_expansion_but_known_function":
        return "keep the family distinct, document its known function, and avoid inventing an expansion"
    return "search corpus documentation and Frasch materials again"


def inferred_acronym_status(best_candidate: dict | None) -> str:
    if not best_candidate:
        return "unresolved"
    if best_candidate.get("evidence_type", "") not in STRONG_DEFINITION_EVIDENCE_TYPES:
        return "contextual_usage_only"
    if (
        best_candidate.get("definition_quality") == "explicit"
        and best_candidate.get("confidence") == "high"
    ):
        return "confirmed_expansion"
    return "probable_expansion"


def short_acronym_evidence_quote(best_candidate: dict | None) -> str:
    if not best_candidate:
        return ""
    quote = (best_candidate.get("raw_definition", "") or "").strip()
    if len(quote) <= MAX_STRONG_DEFINITION_QUOTE_LENGTH:
        return quote
    return quote[: MAX_STRONG_DEFINITION_QUOTE_LENGTH - 1].rstrip() + "…"


def strongest_remaining_evidence(rows: list[dict]) -> dict | None:
    if not rows:
        return None
    strength_rank = {"strong": 4, "medium": 3, "weak": 2, "negative": 1}
    return max(rows, key=lambda row: (strength_rank.get(row.get("evidence_strength", ""), 0), 1 if row.get("supports_expansion") == "true" else 0))


def build_remaining_acronym_evidence_rows() -> list[dict]:
    rows: list[dict] = []
    for acronym in REMAINING_ACRONYMS:
        config = REMAINING_ACRONYM_EVIDENCE_CONFIG[acronym]
        rows.extend({"acronym": acronym, **evidence_row} for evidence_row in config.get("evidence_rows", []))
    return rows


def build_remaining_acronym_worklist(
    *,
    source_family_rows: dict[str, dict],
    acronym_status_rows: list[dict],
    remaining_evidence_rows: list[dict],
) -> list[dict]:
    source_family_by_abbreviation = {row["abbreviation"]: row for row in source_family_rows.values()}
    status_by_acronym = {row["acronym"]: row for row in acronym_status_rows if row.get("acronym")}
    evidence_by_acronym: dict[str, list[dict]] = defaultdict(list)
    for row in remaining_evidence_rows:
        evidence_by_acronym[row["acronym"]].append(row)
    worklist_rows: list[dict] = []
    for acronym in REMAINING_ACRONYMS:
        config = REMAINING_ACRONYM_EVIDENCE_CONFIG[acronym]
        family_row = source_family_by_abbreviation.get(acronym, {})
        status_row = status_by_acronym.get(acronym, {})
        best_evidence = strongest_remaining_evidence(evidence_by_acronym.get(acronym, []))
        worklist_rows.append(
            {
                "acronym": acronym,
                "current_status": status_row.get("resolution_status", "unresolved"),
                "current_expansion": status_row.get("current_expansion", ""),
                "source_family_id": family_row.get("source_family_id", ""),
                "occurrence_count": family_row.get("occurrence_count", "0"),
                "top_example_references": family_row.get("example_raw_references", ""),
                "likely_source_type": config.get("likely_source_type", ""),
                "best_current_evidence": (
                    f'{best_evidence.get("source_file_label", "")}: {best_evidence.get("short_quote", "")}'
                    if best_evidence
                    else ""
                ),
                "specific_files_to_check": " | ".join(config.get("specific_files_to_check", [])),
                "specific_search_terms": " | ".join(config.get("specific_search_terms", [])),
                "recommended_action": config.get("recommended_action", ""),
                "notes": best_evidence.get("notes", "") if best_evidence else "",
            }
        )
    return sorted(worklist_rows, key=lambda row: int(row.get("occurrence_count", "0") or 0), reverse=True)


def build_final_acronym_resolution_sprint(
    *,
    acronym_status_rows: list[dict],
    remaining_worklist_rows: list[dict],
) -> list[dict]:
    status_by_acronym = {row["acronym"]: row for row in acronym_status_rows if row.get("acronym")}
    worklist_by_acronym = {row["acronym"]: row for row in remaining_worklist_rows if row.get("acronym")}
    rows = []
    for acronym in FINAL_SPRINT_ACRONYMS:
        config = FINAL_SPRINT_CONFIG[acronym]
        status_row = status_by_acronym.get(acronym, {})
        worklist_row = worklist_by_acronym.get(acronym, {})
        rows.append(
            {
                "acronym": acronym,
                "current_status": status_row.get("resolution_status", ""),
                "current_examples": worklist_row.get("top_example_references", ""),
                "working_hypothesis": config["working_hypothesis"],
                "hypothesis_source": config["hypothesis_source"],
                "search_strategy": config["search_strategy"],
                "local_files_searched": " | ".join(hit["path_or_redacted_path"] for hit in config["local_hits"]),
                "internet_queries_run": " | ".join(row["query"] for row in config["web_searches"]),
                "best_evidence_found": config["best_evidence_found"],
                "candidate_expansion": status_row.get("current_expansion", ""),
                "recommended_status": status_row.get("resolution_status", ""),
                "confidence": status_row.get("confidence", ""),
                "needs_human_review": status_row.get("needs_human_review", "true"),
                "notes": config["notes"],
            }
        )
    return rows


def build_final_acronym_local_file_hits() -> list[dict]:
    rows = []
    for acronym in FINAL_SPRINT_ACRONYMS:
        for hit in FINAL_SPRINT_CONFIG[acronym]["local_hits"]:
            rows.append({"acronym": acronym, **hit})
    return rows


def build_final_acronym_web_searches() -> list[dict]:
    rows = []
    for acronym in FINAL_SPRINT_ACRONYMS:
        for row in FINAL_SPRINT_CONFIG[acronym]["web_searches"]:
            rows.append({"acronym": acronym, **row})
    return rows


def build_unresolved_acronym_dossier(acronym_status_rows: list[dict]) -> list[dict]:
    status_by_acronym = {row["acronym"]: row for row in acronym_status_rows if row.get("acronym")}
    rows = []
    for acronym in FINAL_SPRINT_ACRONYMS:
        status_row = status_by_acronym.get(acronym, {})
        if status_row.get("resolution_status") != "unresolved_after_exhaustive_search":
            continue
        config = FINAL_SPRINT_CONFIG[acronym]
        rows.append(
            {
                "acronym": acronym,
                "final_status": status_row.get("resolution_status", ""),
                "best_hypothesis": config["working_hypothesis"],
                "hypothesis_confidence": status_row.get("confidence", ""),
                "evidence_summary": config["best_evidence_found"],
                "files_checked": " | ".join(hit["path_or_redacted_path"] for hit in config["local_hits"]),
                "web_queries_checked": " | ".join(row["query"] for row in config["web_searches"]),
                "why_not_confirmed": "Targeted local and web searches did not recover a reliable distinct documentary definition.",
                "recommended_human_action": "Check the underlying printed source or any uncached local bibliography files for an explicit abbreviation line before promoting it.",
                "notes": config["notes"],
            }
        )
    return rows


def build_source_work_authority_rows(
    *,
    authority_rows: list[dict],
    source_family_rows: list[dict],
    crosswalk_rows: list[dict],
) -> list[dict]:
    authority_by_key = {row.get("bibtex_key", ""): row for row in authority_rows if row.get("bibtex_key")}
    related_families_by_work: dict[str, list[dict]] = defaultdict(list)
    for row in source_family_rows:
        source_work_key = canonical_source_work_key(row.get("source_work_key", ""))
        if source_work_key:
            related_families_by_work[source_work_key].append({**row, "source_work_key": source_work_key})

    keys: set[str] = {
        canonical_source_work_key(row.get("source_work_key", ""))
        for row in source_family_rows + crosswalk_rows
        if row.get("source_work_key")
    }
    keys.update(
        canonical_source_work_key(SOURCE_WORK_KEY_BY_BIBTEX_KEY.get(row.get("bibtex_key", ""), row.get("bibtex_key", "")))
        for row in authority_rows
        if row.get("bibtex_key") and row.get("resolution_level") in {"series", "work", "book", "article", "internal_reference"}
    )
    keys.update(SOURCE_WORK_AUTHORITY_LIBRARY)

    def fallback_work_type(authority_row: dict | None, related_rows: list[dict]) -> str:
        if authority_row:
            entry_type = authority_row.get("entry_type", "")
            if entry_type == "book":
                return "book"
            if entry_type == "article":
                return "article"
            if related_rows and related_rows[0].get("source_family_type") == "periodical":
                return "periodical"
        if related_rows:
            source_family_type = related_rows[0].get("source_family_type", "")
            return {
                "periodical": "periodical",
                "catalogue": "source_catalogue",
                "corpus_internal": "corpus_source",
            }.get(source_family_type, "source_work")
        return "source_work"

    rows = []
    for source_work_key in sorted(keys):
        if not source_work_key:
            continue
        library = SOURCE_WORK_AUTHORITY_LIBRARY.get(source_work_key, {})
        preferred_bibtex_key = library.get("bibtex_key", "")
        authority_row = authority_by_key.get(preferred_bibtex_key) or authority_by_key.get(source_work_key)
        bibtex_key = authority_row.get("bibtex_key", "") if authority_row else ""
        related_rows = sorted(
            related_families_by_work.get(source_work_key, []),
            key=lambda row: (
                0 if row.get("source_family_id") == library.get("primary_source_family_id") else 1,
                row.get("abbreviation", ""),
            ),
        )
        primary_row = related_rows[0] if related_rows else None
        related_source_family_ids = "; ".join(row["source_family_id"] for row in related_rows)
        related_acronyms = "; ".join(row["abbreviation"] for row in related_rows)
        evidence_source = (
            library.get("evidence_source")
            or (primary_row.get("best_definition_source", "") if primary_row else "")
            or (authority_row.get("source_of_authority", "") if authority_row else "")
        )
        evidence_quote = (
            library.get("evidence_quote")
            or (primary_row.get("best_definition_quote", "") if primary_row else "")
            or (authority_row.get("matched_local_reference", "") if authority_row else "")
            or (authority_row.get("evidence", "") if authority_row else "")
        )
        notes = " ".join(
            part
            for part in (
                library.get("notes", ""),
                authority_row.get("notes", "") if authority_row else "",
            )
            if part
        )
        rows.append(
            {
                "source_work_key": source_work_key,
                "canonical_title": (
                    library.get("canonical_title")
                    or (authority_row.get("title", "") if authority_row else "")
                    or (primary_row.get("expanded_label", "") if primary_row else source_work_key)
                ),
                "short_title": (
                    library.get("short_title")
                    or (authority_row.get("shorttitle", "") if authority_row else "")
                    or (primary_row.get("abbreviation", "") if primary_row else source_work_key)
                ),
                "authority_level": library.get("authority_level") or library.get("work_type") or fallback_work_type(authority_row, related_rows),
                "work_type": library.get("work_type") or fallback_work_type(authority_row, related_rows),
                "authors_editors": library.get("authors_editors") or (authority_row.get("author", "") if authority_row else ""),
                "date_or_date_range": library.get("date_or_date_range") or (authority_row.get("year", "") if authority_row else ""),
                "publisher_or_institution": library.get("publisher_or_institution") or (authority_row.get("publisher", "") if authority_row else ""),
                "place": library.get("place") or (authority_row.get("address", "") if authority_row else ""),
                "related_source_family_ids": related_source_family_ids,
                "related_acronyms": related_acronyms,
                "authority_status": library.get("authority_status") or (authority_row.get("authority_status", "") if authority_row else "documented_source_work"),
                "evidence_source": evidence_source,
                "evidence_quote": evidence_quote,
                "bibtex_key": bibtex_key,
                "needs_human_review": (
                    library.get("needs_human_review")
                    or (authority_row.get("human_review_flag", "") if authority_row else "")
                    or ("true" if any(truthy(row.get("needs_human_review", "")) for row in related_rows) else "false")
                ),
                "notes": notes,
            }
        )
    return rows


def build_source_work_authority_audit_rows(source_work_authority_rows: list[dict]) -> list[dict]:
    source_work_by_key = {
        row.get("source_work_key", ""): row for row in source_work_authority_rows if row.get("source_work_key")
    }
    rows = []
    for normalization_row in AUTHORITY_KEY_NORMALIZATION_ROWS:
        merge_target = source_work_by_key.get(normalization_row["new_key"])
        if merge_target is None:
            continue
        rows.append(
            {
                "source_work_key": merge_target["source_work_key"],
                "canonical_title": merge_target.get("canonical_title", ""),
                "related_source_family_ids": merge_target.get("related_source_family_ids", ""),
                "issue_type": "normalized_overlap_review",
                "status": "reviewed_normalized",
                "open_issue": "false",
                "resolved_by_key_normalization": "true",
                "severity": "high" if normalization_row["old_key"] in {"obiCorpusSource", "fraschBaganEpigraphicDatabasePartBShort"} else "medium",
                "recommended_action": normalization_row["migration_action"],
                "merge_target_key": normalization_row["new_key"],
                "notes": normalization_row["notes"],
            }
        )
    return rows


def build_source_work_to_bibtex_reconciliation_rows(
    *,
    source_work_authority_rows: list[dict],
    authority_rows: list[dict],
    candidate_rows: list[dict],
) -> list[dict]:
    authority_by_key = {row.get("bibtex_key", ""): row for row in authority_rows if row.get("bibtex_key")}
    candidate_keys = {row.get("bibtex_key", "") for row in candidate_rows if row.get("bibtex_key")}
    rows = []
    for row in sorted(source_work_authority_rows, key=lambda item: item.get("source_work_key", "")):
        authority_level = row.get("authority_level", "") or row.get("work_type", "")
        current_bibtex_key = row.get("bibtex_key", "")
        should_have_bibtex = "true" if authority_level_requires_bibtex(authority_level) else "false"
        if current_bibtex_key in candidate_keys:
            bibtex_status = "candidate_only"
        elif authority_level in {"locator_collection", "manuscript_collection", "archival_notebook"}:
            bibtex_status = "suppressed_locator_system" if not current_bibtex_key else "present"
        elif should_have_bibtex == "true" and current_bibtex_key in authority_by_key:
            bibtex_status = "present"
        elif should_have_bibtex == "true":
            bibtex_status = "missing_expected"
        elif row.get("needs_human_review") == "true":
            bibtex_status = "needs_human_review"
        else:
            bibtex_status = "intentionally_no_bibtex"
        reason = {
            "present": "Publication-like source authority is represented in bibliography_authority.bib.",
            "missing_expected": "Publication-like source authority lacks an emitted BibTeX row.",
            "candidate_only": "Only a candidate stub exists, so the work should not be treated as resolved authority yet.",
            "suppressed_locator_system": "Locator, manuscript, or notebook authority should not be emitted as an ordinary publication.",
            "needs_human_review": "Authority remains too weak for publication-style emission.",
            "intentionally_no_bibtex": "This authority object is tracked structurally but should not emit a normal BibTeX publication.",
        }[bibtex_status]
        recommended_action = {
            "present": "Keep the BibTeX row aligned with the curated source-work metadata.",
            "missing_expected": "Emit or restore a bibliography_authority.bib row from source_work_authority.tsv.",
            "candidate_only": "Keep the work in bibliography_candidates.bib until stronger evidence is found.",
            "suppressed_locator_system": "Keep the source-work row but suppress ordinary publication-style BibTeX emission.",
            "needs_human_review": "Retain the source-work row and revisit emission only after stronger bibliographic witnesses are found.",
            "intentionally_no_bibtex": "Keep it in source_work_authority.tsv without emitting bibliography_authority.bib.",
        }[bibtex_status]
        rows.append(
            {
                "source_work_key": row.get("source_work_key", ""),
                "canonical_title": row.get("canonical_title", ""),
                "authority_level": authority_level,
                "should_have_bibtex": should_have_bibtex,
                "current_bibtex_key": current_bibtex_key,
                "bibtex_status": bibtex_status,
                "reason": reason,
                "recommended_action": recommended_action,
                "notes": row.get("notes", ""),
            }
        )
    return rows


def looks_like_series_definition_evidence(value: str) -> bool:
    compact = re.sub(r"\s+", " ", (value or "").strip())
    if not compact or compact.count("=") != 1:
        return False
    if re.search(r"\bp\.\s*\d|\bpp\.\s*\d|\bvol\.?\s*\d|\bno\.?\s*\d", compact, flags=re.IGNORECASE):
        return False
    left, right = [part.strip() for part in compact.split("=", 1)]
    if not left or not right:
        return False
    if len(left) > 24 or len(right) > 160:
        return False
    if not re.fullmatch(r"[A-Z][A-Z0-9 .&/-]{1,23}", left):
        return False
    if not re.match(r"[A-Z]", right):
        return False
    return True


def build_bibtex_field_quality_audit_rows(
    *,
    authority_rows: list[dict],
    source_work_authority_rows: list[dict],
) -> list[dict]:
    source_work_by_bibtex = {
        row.get("bibtex_key", ""): row for row in source_work_authority_rows if row.get("bibtex_key")
    }
    audit_rows: list[dict] = []

    def append_issue(row: dict, field_name: str, issue_type: str, severity: str, recommended_fix: str, notes: str) -> None:
        audit_rows.append(
            {
                "bibtex_key": row.get("bibtex_key", ""),
                "field_name": field_name,
                "field_value_short": short_reference(row.get(field_name, "")),
                "issue_type": issue_type,
                "severity": severity,
                "recommended_fix": recommended_fix,
                "notes": notes,
            }
        )

    for row in authority_rows:
        source_work_row = source_work_by_bibtex.get(row.get("bibtex_key", ""))
        authority_level = source_work_row.get("authority_level", "") if source_work_row else ""
        if looks_like_ocr_garbage(row.get("evidence", "")) or looks_like_ocr_garbage(row.get("matched_local_reference", "")):
            append_issue(
                row,
                "evidence",
                "ocr_like_evidence_fragment",
                "high",
                "Replace the BibTeX evidence field with a concise authority quote and keep raw OCR evidence only in bibtex_authority_evidence.tsv.",
                "BibTeX authority rows should not expose noisy OCR fragments.",
            )
        evidence = row.get("evidence", "")
        if authority_level in {"periodical", "series"} and not looks_like_series_definition_evidence(evidence) and re.search(
            r"\bp\.\s*\d|\bpp\.\s*\d|\bvol\.?\s*\d|\bno\.?\s*\d|\b\d{4}\b|\bJBRS\b.*[,;]|\bJRAS\b.*[,;]",
            evidence,
            flags=re.IGNORECASE,
        ):
            append_issue(
                row,
                "evidence",
                "article_like_series_evidence",
                "medium",
                "Use a concise series-definition quote rather than an article-specific citation fragment.",
                "Series-level BibTeX authorities should cite the series definition, not a sample article reference.",
            )
        normalized_script = normalize_script_value(row.get("script", ""), fallback_title=row.get("title", ""))
        if row.get("script", "") and row.get("script", "") != normalized_script:
            append_issue(
                row,
                "script",
                "non_normalized_script_value",
                "low",
                "Normalize Latin-script bibliographic rows to Latn.",
                "Script values should be normalized across the authority layer.",
            )
    audit_rows.sort(key=lambda item: ({"high": 0, "medium": 1, "low": 2}.get(item["severity"], 3), item["bibtex_key"], item["field_name"]))
    return audit_rows


def build_bibtex_field_quality_audit_history_rows(
    *,
    raw_audit_rows: list[dict],
    active_audit_rows: list[dict],
) -> list[dict]:
    active_issue_keys = {
        (row.get("bibtex_key", ""), row.get("field_name", ""), row.get("issue_type", "")) for row in active_audit_rows
    }
    history_rows: list[dict] = []
    for row in raw_audit_rows:
        issue_key = (row.get("bibtex_key", ""), row.get("field_name", ""), row.get("issue_type", ""))
        status = "open" if issue_key in active_issue_keys else "resolved"
        history_rows.append(
            {
                "bibtex_key": row.get("bibtex_key", ""),
                "field_name": row.get("field_name", ""),
                "field_value_short": row.get("field_value_short", ""),
                "issue_type": row.get("issue_type", ""),
                "severity": row.get("severity", ""),
                "status": status,
                "resolved_in_commit": "" if status == "open" else "current_worktree",
                "remaining_issue": row.get("issue_type", "") if status == "open" else "",
                "recommended_fix": row.get("recommended_fix", ""),
                "notes": row.get("notes", ""),
            }
        )
    history_rows.sort(
        key=lambda item: (
            {"open": 0, "needs_human_review": 1, "suppressed": 2, "resolved": 3}.get(item["status"], 4),
            {"high": 0, "medium": 1, "low": 2}.get(item["severity"], 3),
            item["bibtex_key"],
            item["field_name"],
        )
    )
    return history_rows


def build_bibtex_consistency_report(
    *,
    authority_rows: list[dict],
    active_audit_rows: list[dict],
    audit_history_rows: list[dict],
    reconciliation_rows: list[dict],
) -> dict:
    emitted_keys = {row.get("bibtex_key", "") for row in authority_rows if row.get("bibtex_key")}
    reconciliation_by_key = {
        row.get("current_bibtex_key", ""): row
        for row in reconciliation_rows
        if row.get("current_bibtex_key")
    }
    non_normalized_script_count = sum(
        1
        for row in authority_rows
        if row.get("script", "") != normalize_script_value(row.get("script", ""), fallback_title=row.get("title", ""))
    )
    ocr_like_evidence_count = sum(
        1
        for row in authority_rows
        if looks_like_ocr_garbage(row.get("evidence", "")) or looks_like_ocr_garbage(row.get("matched_local_reference", ""))
    )
    locator_publication_leak_count = sum(
        1
        for row in reconciliation_rows
        if row.get("authority_level") in {"locator_collection", "manuscript_collection", "archival_notebook"}
        and row.get("current_bibtex_key")
        and row.get("bibtex_status") != "suppressed_locator_system"
    )
    ippa_duplicate_bibtex_count = sum(1 for key in emitted_keys if "ippa" in key.casefold())
    intentional_emitted_keys = {
        row.get("current_bibtex_key", "")
        for row in reconciliation_rows
        if row.get("current_bibtex_key") and row.get("bibtex_status") in {"present", "needs_human_review"}
    }
    return {
        "bibtex_entry_count": len(authority_rows),
        "open_field_quality_issue_count": len(active_audit_rows),
        "resolved_field_quality_issue_count": sum(1 for row in audit_history_rows if row.get("status") == "resolved"),
        "non_normalized_script_count": non_normalized_script_count,
        "ocr_like_evidence_count": ocr_like_evidence_count,
        "locator_publication_leak_count": locator_publication_leak_count,
        "ippa_duplicate_bibtex_count": ippa_duplicate_bibtex_count,
        "unexpected_emitted_bibtex_key_count": len(emitted_keys - intentional_emitted_keys),
    }


def curate_authority_rows_for_emission(
    *,
    authority_rows: list[dict],
    source_work_authority_rows: list[dict],
    reconciliation_rows: list[dict],
) -> list[dict]:
    allowed_bibtex_keys = {
        row.get("current_bibtex_key", "")
        for row in reconciliation_rows
        if row.get("current_bibtex_key") and row.get("bibtex_status") in {"present", "needs_human_review"}
    }
    source_work_by_bibtex = {
        row.get("bibtex_key", ""): row for row in source_work_authority_rows if row.get("bibtex_key")
    }
    curated_rows: list[dict] = []
    for row in authority_rows:
        if row.get("bibtex_key", "") not in allowed_bibtex_keys:
            continue
        curated_row = dict(row)
        source_work_row = source_work_by_bibtex.get(curated_row.get("bibtex_key", ""))
        if source_work_row:
            authority_level = source_work_row.get("authority_level", "")
            curated_row["title"] = source_work_row.get("canonical_title", "") or curated_row.get("title", "")
            curated_row["shorttitle"] = source_work_row.get("short_title", "") or curated_row.get("shorttitle", "")
            curated_row["source_of_authority"] = source_work_row.get("evidence_source", "") or curated_row.get("source_of_authority", "")
            if source_work_row.get("evidence_quote"):
                clean_quote = clean_bibtex_summary_text(source_work_row["evidence_quote"])
                curated_row["short_evidence_note"] = clean_quote
                curated_row["evidence"] = clean_quote
                curated_row["matched_local_reference"] = ""
            if authority_level in {"periodical", "series"}:
                curated_row["entry_type"] = "periodical"
            elif authority_level == "book":
                curated_row["entry_type"] = "book"
            elif authority_level == "article":
                curated_row["entry_type"] = "article"
            elif authority_level in {"source_catalogue", "source_work", "corpus_source"} and curated_row.get("entry_type") not in {"book", "article", "periodical"}:
                curated_row["entry_type"] = "misc"
        curated_row["script"] = normalize_script_value(curated_row.get("script", ""), fallback_title=curated_row.get("title", ""))
        curated_rows.append(curated_row)
    curated_rows.sort(key=lambda row: (row.get("family_label", ""), row.get("bibtex_key", "")))
    return curated_rows


def build_candidate_stub_review_rows(candidate_rows: list[dict], family_by_id: dict[str, dict]) -> list[dict]:
    rows = []
    for row in candidate_rows:
        decision = CANDIDATE_STUB_REVIEW_DECISIONS.get(
            row.get("bibtex_key", ""),
            {
                "review_decision": "retain",
                "reason": "No automatic consolidation rule suppressed or promoted this candidate stub.",
                "next_action": "Retain for human review.",
                "notes": "",
            },
        )
        family_row = family_by_id.get(row.get("family_id", ""), {})
        rows.append(
            {
                "candidate_key": row.get("bibtex_key", ""),
                "candidate_label": row.get("title", "") or row.get("family_label", ""),
                "occurrence_count": family_row.get("occurrence_count", row.get("occurrence_count", "")),
                "current_status": row.get("authority_status", ""),
                "review_decision": decision["review_decision"],
                "reason": decision["reason"],
                "next_action": decision["next_action"],
                "notes": decision.get("notes", ""),
            }
        )
    rows.sort(key=lambda row: row["candidate_key"])
    return rows


def build_source_work_locator_rows(
    crosswalk_rows: list[dict],
    source_work_authority_rows: list[dict],
) -> list[dict]:
    examples_by_family: dict[str, list[str]] = defaultdict(list)
    for row in crosswalk_rows:
        if row.get("source_family_id") and row.get("raw_reference_string"):
            examples_by_family[row["source_family_id"]].append(row["raw_reference_string"])
    source_work_authority_by_key = {
        row.get("source_work_key", ""): row for row in source_work_authority_rows if row.get("source_work_key")
    }
    rows = []

    def append_row(*, family_ids: list[str], relationship_key: str, example_limit: int = 2, notes: str | None = None) -> None:
        if not any(examples_by_family.get(family_id) for family_id in family_ids):
            return
        defaults = SOURCE_WORK_RELATIONSHIPS[relationship_key]
        authority_row = source_work_authority_by_key.get(defaults["source_work_key"], {})
        collected_examples: list[str] = []
        for family_id in family_ids:
            collected_examples.extend(examples_by_family.get(family_id, [])[:1 if len(family_ids) > 1 else example_limit])
        rows.append(
            {
                "source_work_key": defaults["source_work_key"],
                "source_work_title": defaults["source_work_title"],
                "source_family_ids": "; ".join(family_id for family_id in family_ids if examples_by_family.get(family_id)),
                "locator_system": defaults["locator_system"],
                "locator_prefixes": defaults["locator_prefixes"],
                "locator_type": defaults.get("locator_type", ""),
                "example_references": " | ".join(collected_examples[:example_limit] or [defaults["default_examples"]]),
                "bibtex_key": authority_row.get("bibtex_key", ""),
                "authority_status": authority_row.get("authority_status", ""),
                "needs_human_review": authority_row.get("needs_human_review", "true"),
                "alias_or_variant_notes": defaults.get("alias_or_variant_notes", ""),
                "notes": notes or defaults["notes"],
            }
        )

    append_row(
        family_ids=["sf-iob", "sf-pl"],
        relationship_key="iob",
        notes="Clarifies that IOB and Pl. are separate locator systems into the same Luce and Pe Maung Tin source work.",
    )
    append_row(family_ids=["sf-list"], relationship_key="list")
    append_row(
        family_ids=["sf-ppa", "sf-ippa"],
        relationship_key="ppa",
        notes="Clarifies that PPA page citations and IPPA variant locators point into the same Pagan, Pinya and Ava source work.",
    )
    append_row(family_ids=["sf-ub"], relationship_key="ub")
    append_row(family_ids=["sf-sip"], relationship_key="sip")
    append_row(family_ids=["sf-uem"], relationship_key="uem")
    append_row(family_ids=["sf-tn"], relationship_key="tn")
    append_row(family_ids=["sf-mp"], relationship_key="mp")
    append_row(family_ids=["sf-or"], relationship_key="or")
    append_row(family_ids=["sf-luce-d"], relationship_key="luce d")
    append_row(family_ids=["sf-luce-j"], relationship_key="luce j")
    return rows


def build_raw_reference_crosswalk_audit_rows(
    *,
    crosswalk_rows: list[dict],
    source_work_authority_rows: list[dict],
    family_by_id: dict[str, dict],
) -> list[dict]:
    source_work_authority_by_key = {
        row.get("source_work_key", ""): row for row in source_work_authority_rows if row.get("source_work_key")
    }
    locator_expected_families = {"sf-iob", "sf-pl", "sf-ippa", "sf-ppa", "sf-list", "sf-ub", "sf-sip", "sf-uem", "sf-tn", "sf-mp", "sf-or", "sf-luce-d", "sf-luce-j"}
    audit_rows: list[dict] = []

    def append_issue(
        row: dict,
        issue_type: str,
        severity: str,
        recommended_fix: str,
        notes: str,
        *,
        issue_category: str,
        status: str,
        auto_fixable: str,
        human_review_required: str,
    ) -> None:
        audit_rows.append(
            {
                "raw_reference_string": row.get("raw_reference_string", ""),
                "family_id": row.get("family_id", ""),
                "source_family_id": row.get("source_family_id", ""),
                "source_work_key": row.get("source_work_key", ""),
                "bibtex_key": row.get("bibtex_key", ""),
                "locator": row.get("locator", ""),
                "locator_type": row.get("locator_type", ""),
                "issue_type": issue_type,
                "issue_category": issue_category,
                "status": status,
                "severity": severity,
                "auto_fixable": auto_fixable,
                "human_review_required": human_review_required,
                "recommended_fix": recommended_fix,
                "notes": notes,
            }
        )

    for row in crosswalk_rows:
        family_id = row.get("family_id", "")
        family_occurrence_count = int(family_by_id.get(family_id, {}).get("occurrence_count", "0") or "0")
        source_work_row = source_work_authority_by_key.get(row.get("source_work_key", ""), {})
        if row.get("source_family_id") in locator_expected_families and not row.get("source_work_key"):
            append_issue(row, "missing_source_work_key", "high", "Add the expected source_work_key for this locator-aware family.", "Locator-aware family is missing a source work target.", issue_category="authority_linkage", status="open", auto_fixable="true", human_review_required="false")
        if row.get("source_work_key") and row["source_work_key"] not in source_work_authority_by_key:
            append_issue(row, "invalid_source_work_key", "high", "Map the row to a documented source_work_authority entry.", "Crosswalk points to a source_work_key that is not present in source_work_authority.tsv.", issue_category="authority_linkage", status="open", auto_fixable="true", human_review_required="false")
        if source_work_row.get("bibtex_key") and not row.get("bibtex_key"):
            append_issue(row, "missing_bibtex_key", "medium", "Populate bibtex_key from source_work_authority.tsv.", "This source work already has a BibTeX authority key.", issue_category="bibtex_linkage", status="open", auto_fixable="true", human_review_required="false")
        if row.get("source_family_id") == "sf-tn" and re.fullmatch(r"TN,?\s*p\.\s*", row.get("raw_reference_string", ""), flags=re.IGNORECASE):
            append_issue(
                row,
                "incomplete_raw_reference",
                "low",
                "check source record manually if this record becomes important",
                "The structured corpus record preserves a truncated TN page citation with no recoverable page number.",
                issue_category="incomplete_reference",
                status="documented_residue",
                auto_fixable="false",
                human_review_required="true",
            )
            continue
        if row.get("source_family_id") in locator_expected_families and (not row.get("locator") or row.get("locator_type") == "unclear") and family_occurrence_count >= 10:
            append_issue(
                row,
                "unparsed_locator",
                "medium" if family_occurrence_count >= 25 else "low",
                "Improve locator parsing or document the irregular locator form.",
                "High-occurrence locator family still has an unclear locator parse.",
                issue_category="locator_parse",
                status="open",
                auto_fixable="true" if row.get("source_family_id") in {"sf-list", "sf-ippa", "sf-or"} else "false",
                human_review_required="true" if row.get("source_family_id") not in {"sf-list", "sf-ippa", "sf-or"} else "false",
            )
        if row.get("source_family_id") == "sf-ippa":
            if not row.get("raw_reference_string", "").startswith("IPPA"):
                append_issue(row, "ippa_raw_string_not_preserved", "high", "Preserve the raw IPPA string in raw_reference_to_bibtex.tsv.", "IPPA alias rows should keep the original IPPA spelling.", issue_category="ippa_alias_integrity", status="open", auto_fixable="true", human_review_required="false")
            if row.get("source_work_key") != "ppaCatalogue":
                append_issue(row, "ippa_wrong_source_work", "high", "Map IPPA rows to ppaCatalogue while preserving the raw string.", "IPPA should route to the PPA source work.", issue_category="ippa_alias_integrity", status="open", auto_fixable="true", human_review_required="false")
            if row.get("resolution_status") != "alias_or_variant_of_PPA":
                append_issue(row, "ippa_wrong_resolution_status", "high", "Mark IPPA crosswalk rows as alias_or_variant_of_PPA.", "IPPA should not look unresolved or generically alias_resolved in the crosswalk audit layer.", issue_category="ippa_alias_integrity", status="open", auto_fixable="true", human_review_required="false")
        if row.get("source_family_id") in {"sf-mp", "sf-or", "sf-luce-d", "sf-luce-j"} and row.get("bibtex_key"):
            append_issue(row, "locator_system_mapped_as_bibtex_work", "high", "Leave bibtex_key blank for locator systems that have no standalone BibTeX work.", "Locator-only source works should not masquerade as standalone bibliography entries.", issue_category="locator_emission", status="open", auto_fixable="true", human_review_required="false")

    audit_rows = list({
        (row["raw_reference_string"], row["issue_type"]): row
        for row in sorted(
            audit_rows,
            key=lambda row: (
                {"high": 0, "medium": 1, "low": 2}.get(row["severity"], 3),
                -int(family_by_id.get(row["family_id"], {}).get("occurrence_count", "0") or "0"),
                row["raw_reference_string"],
                row["issue_type"],
            ),
        )
    }.values())
    audit_rows.sort(
        key=lambda row: (
            {"high": 0, "medium": 1, "low": 2}.get(row["severity"], 3),
            -int(family_by_id.get(row["family_id"], {}).get("occurrence_count", "0") or "0"),
            row["raw_reference_string"],
            row["issue_type"],
        )
    )
    return audit_rows


def build_acronym_status_rows(
    source_family_rows: dict[str, dict],
    acronym_candidates_by_acronym: dict[str, list[dict]],
    manual_acronym_seeds: dict[str, dict],
    remaining_evidence_rows: list[dict],
) -> list[dict]:
    abbreviation_to_source_family = {
        row.get("abbreviation", ""): row for row in source_family_rows.values() if row.get("abbreviation")
    }
    acronyms = list(dict.fromkeys(PRIORITY_ACRONYMS + sorted(abbreviation_to_source_family) + sorted(manual_acronym_seeds)))
    status_rows: list[dict] = []
    remaining_evidence_by_acronym: dict[str, list[dict]] = defaultdict(list)
    for row in remaining_evidence_rows:
        remaining_evidence_by_acronym[row["acronym"]].append(row)
    for acronym in acronyms:
        source_family_row = abbreviation_to_source_family.get(acronym)
        documentary_candidate = choose_best_acronym_candidate(acronym_candidates_by_acronym.get(acronym, []))
        best_candidate = documentary_candidate
        manual_seed = manual_acronym_seeds.get(acronym)
        manual_candidate = manual_seed_candidate(manual_seed) if manual_seed else None
        default = ACRONYM_STATUS_DEFAULTS.get(acronym, {})
        override = REMAINING_ACRONYM_EVIDENCE_CONFIG.get(acronym, {}).get("status_override")
        best_remaining_evidence = strongest_remaining_evidence(remaining_evidence_by_acronym.get(acronym, []))
        strong_candidate = bool(
            documentary_candidate and documentary_candidate.get("evidence_type", "") in STRONG_DEFINITION_EVIDENCE_TYPES
        )
        contextual_candidate = bool(documentary_candidate and documentary_candidate.get("evidence_type") == "contextual_usage")
        documentary_confirms_manual = bool(
            manual_seed
            and documentary_candidate
            and strong_candidate
            and normalized_seed_match(manual_seed.get("expansion", ""), documentary_candidate.get("candidate_expansion", ""))
        )
        documentary_conflicts_manual = bool(manual_seed and documentary_candidate and strong_candidate and not documentary_confirms_manual)
        status = default.get("resolution_status", "")
        if not status:
            if documentary_confirms_manual:
                status = inferred_acronym_status(documentary_candidate)
                best_candidate = documentary_candidate
            elif manual_candidate:
                status = "confirmed_expansion"
                best_candidate = manual_candidate
            elif strong_candidate:
                status = inferred_acronym_status(documentary_candidate)
            elif contextual_candidate:
                status = "contextual_usage_only"
            elif source_family_row:
                status = "source_family_only"
            else:
                status = "unresolved"
        elif documentary_confirms_manual and status in {"source_family_only", "contextual_usage_only", "unresolved", "confirmed_expansion"}:
            status = inferred_acronym_status(documentary_candidate)
        elif manual_candidate and status in {"source_family_only", "contextual_usage_only", "unresolved", "confirmed_expansion"}:
            status = "confirmed_expansion"
            best_candidate = manual_candidate
        elif strong_candidate and status in {"source_family_only", "contextual_usage_only", "unresolved"}:
            status = inferred_acronym_status(documentary_candidate)
        if status in {"confirmed_expansion", "probable_expansion"} and not documentary_confirms_manual and not manual_candidate and not strong_candidate:
            status = "source_family_only" if source_family_row else "unresolved"
        current_expansion = default.get("current_expansion", "")
        if documentary_confirms_manual and manual_seed:
            current_expansion = manual_seed.get("expansion", "") or current_expansion
            best_candidate = documentary_candidate
        elif strong_candidate:
            current_expansion = documentary_candidate.get("candidate_expansion", "") or current_expansion
            best_candidate = documentary_candidate
        elif manual_candidate:
            current_expansion = manual_candidate.get("candidate_expansion", "") or current_expansion
            best_candidate = manual_candidate
        if status in {"internal_locator", "internal_locator_system"} and default.get("current_expansion"):
            current_expansion = default["current_expansion"]
        if status in {"source_family_only", "contextual_usage_only", "unresolved"}:
            current_expansion = ""
        if source_family_row and not current_expansion and not is_placeholder_expansion(source_family_row.get("expanded_label", "")):
            if status in {
                "alias_or_variant_of_PPA",
                "confirmed_expansion",
                "probable_expansion",
                "probable_typo_for_PPA",
                "not_an_acronym",
                "internal_locator",
                "internal_locator_system",
                "source_family_with_unknown_expansion_but_known_function",
            }:
                current_expansion = source_family_row.get("expanded_label", "")
        definition_quality = (
            best_candidate.get("definition_quality", "")
            if best_candidate
            else ("context_only" if contextual_candidate else "not_found")
        )
        if status in {"internal_locator", "internal_locator_system"} and not definition_quality:
            definition_quality = "strong"
        note_parts = [best_candidate.get("notes", "")] if best_candidate else []
        if best_remaining_evidence:
            note_parts.append(best_remaining_evidence.get("notes", ""))
        if manual_seed:
            if documentary_confirms_manual:
                note_parts.append("Manual identification supplied by Nathan; documentary source agrees.")
            elif documentary_conflicts_manual:
                note_parts.append("Manual identification supplied by Nathan; documentary wording differs, so the manual seed remains canonical.")
            else:
                note_parts.append("Manual identification supplied by Nathan; seek documentary corroboration.")
        needs_review = "true" if status in {
            "alias_or_variant_of_PPA",
            "probable_expansion",
            "probable_locator_system",
            "probable_private_luce_locator_system",
            "probable_typo_for_PPA",
            "source_family_only",
            "contextual_usage_only",
            "source_family_with_unknown_expansion_but_known_function",
            "unresolved",
            "unresolved_after_targeted_search",
            "unresolved_after_exhaustive_search",
            "genuinely_unresolved_after_occurrence_level_review",
        } else "false"
        if status in {"confirmed_expansion", "not_an_acronym"} and definition_quality == "manual_seed":
            needs_review = "false"
        if status == "not_an_acronym":
            needs_review = "false"
        next_action = next_acronym_action(status)
        if manual_seed and not strong_candidate and definition_quality == "manual_seed":
            next_action = "seek documentary corroboration for manual seed"
        if override and not manual_seed:
            status = override["resolution_status"]
            definition_quality = override["definition_quality"]
            current_expansion = override.get("current_expansion", "")
            best_source = best_remaining_evidence.get("source_file_label", "") if best_remaining_evidence else ""
            best_id = (
                f"remaining-evidence:{acronym.casefold().replace(' ', '').replace('.', '')}"
                if best_remaining_evidence
                else ""
            )
            best_quote = best_remaining_evidence.get("short_quote", "") if best_remaining_evidence else ""
            confidence = override.get("confidence", "low")
            needs_review = override.get("needs_human_review", "true")
            next_action = config_action = REMAINING_ACRONYM_EVIDENCE_CONFIG.get(acronym, {}).get("recommended_action", next_action)
        else:
            best_source = best_candidate.get("source_file_label", "") if best_candidate else ""
            best_id = best_candidate.get("candidate_id", "") if best_candidate else ""
            best_quote = short_acronym_evidence_quote(best_candidate)
            confidence = best_candidate.get("confidence", "low") if best_candidate else "low"
            config_action = next_action
        status_rows.append(
            {
                "acronym": acronym,
                "current_expansion": current_expansion,
                "current_authority_key": source_family_row.get("authority_key", "") if source_family_row else "",
                "source_family_id": source_family_row.get("source_family_id", "") if source_family_row else "",
                "resolution_status": status,
                "definition_quality": definition_quality or "not_found",
                "best_evidence_source": best_source,
                "best_evidence_id": best_id,
                "best_evidence_quote": best_quote,
                "confidence": confidence,
                "needs_human_review": needs_review,
                "next_action": config_action,
                "notes": " ".join(part for part in note_parts if part),
            }
        )
    return sorted(status_rows, key=lambda row: row["acronym"].casefold())


def candidate_is_plausible_standalone(family_row: dict, candidate: dict | None) -> bool:
    family_type = family_row.get("family_type", "")
    if family_type in {"book", "article"}:
        return True
    if family_type in {"source_catalogue", "publication", "internal_reference"}:
        return False
    if not candidate:
        return False
    author = (candidate.get("author", "") or "").strip()
    title = (candidate.get("title", "") or "").strip()
    raw_text = f"{author} {title}".strip()
    if not raw_text or len(raw_text) < 8:
        return False
    if title and title.casefold() == family_row.get("family_label", "").casefold():
        return False
    return bool(author or len(title.split()) >= 3)


def usable_frasch_rows(rows: list[dict]) -> list[dict]:
    return [
        row
        for row in rows
        if row.get("detected_entry_type") == "bibliographic_reference"
        and row.get("recommended_action") in {"use_for_bibliography", "manual_review"}
    ]


def find_frasch_match(rows: list[dict], search_terms: list[str]) -> dict | None:
    normalized_terms = [normalize_title(term) for term in search_terms if term]
    matches = [
        row
        for row in rows
        if any(
            term and term in normalize_title(
                f"{row.get('raw_reference', '')} {row.get('publication', '')} {row.get('title', '')} {row.get('author', '')}"
            )
            for term in normalized_terms
        )
    ]
    if not matches:
        return None
    matches.sort(key=lambda row: (0 if row.get("recommended_action") == "use_for_bibliography" else 1, len(row.get("raw_reference", ""))))
    return matches[0]


def find_local_match(rows: list[dict], search_terms: list[str]) -> dict | None:
    normalized_terms = [normalize_title(term) for term in search_terms if term]
    matches = [
        row
        for row in rows
        if any(
            term and term in normalize_title(
                f"{row.get('probable_work_label', '')} {row.get('name', '')} {row.get('original_path', '')}"
            )
            for term in normalized_terms
        )
    ]
    return matches[0] if matches else None


def resolve_alias_target(family_id: str) -> tuple[str, str, str] | None:
    if family_id.startswith("fam-raw-b-"):
        return ("family", "fam-raw-b", "Bagan Epigraphic Database, Part B")
    if family_id.startswith("fam-raw-ub-"):
        return ("family", "fam-raw-ub", "UB source family")
    if family_id.startswith("fam-raw-mp-"):
        return ("family", "fam-raw-mp", "MP source family")
    if family_id.startswith("fam-raw-arasi-"):
        return ("key", "annualReportArchaeologicalSurveyIndia", "Annual Report of the Archaeological Survey of India")
    if family_id.startswith("fam-raw-luce-d-"):
        return ("key", "luceDSourceFamily", "Luce D source family")
    if family_id.startswith("fam-raw-luce-j-"):
        return ("key", "luceJSourceFamily", "Luce J source family")
    return None


def row_to_bibtex_entry(row: dict) -> dict:
    fields = {
        "author": row.get("author", ""),
        "editor": row.get("editor", ""),
        "title": row.get("title", ""),
        "shorttitle": row.get("shorttitle", ""),
        "journal": row.get("journal", ""),
        "booktitle": row.get("booktitle", ""),
        "publisher": row.get("publisher", ""),
        "address": row.get("address", ""),
        "year": row.get("year", ""),
        "volume": row.get("volume", ""),
        "number": row.get("number", ""),
        "pages": row.get("pages", ""),
        "doi": row.get("doi", ""),
        "url": row.get("url", ""),
        "isbn": row.get("isbn", ""),
        "language": row.get("language", ""),
        "script": row.get("script", ""),
        "reviewstatus": row.get("review_status", ""),
        "translationrelevance": row.get("translation_relevance", ""),
        "evidence": evidence_excerpt(row.get("short_evidence_note", "") or row.get("evidence", "")),
        "evidenceid": row.get("evidence_id", ""),
        "sourceofauthority": row.get("source_of_authority", ""),
        "matchedexternalkey": row.get("matched_external_key", ""),
        "sourcefamilyid": row.get("source_family_id", ""),
        "resolutionstatus": row.get("resolution_status", ""),
        "resolutionlevel": row.get("resolution_level", ""),
        "familyid": row.get("family_id", ""),
        "note": row.get("notes", ""),
        "matchedlocalsourceid": row.get("matched_local_source_id", ""),
        "matchedlocalsourcefile": row.get("matched_local_source_file", ""),
        "matchedlocalreference": short_reference(row.get("matched_local_reference", "")),
    }
    return {
        "entry_type": row["entry_type"],
        "bibtex_key": row["bibtex_key"],
        "fields": {name: value for name, value in fields.items() if value},
    }


def dedupe_local_candidates(rows: list[dict]) -> list[dict]:
    by_candidate: dict[str, dict] = {}
    for row in rows:
        candidate_id = row.get("candidate_id") or row.get("sha256") or row.get("name")
        existing = by_candidate.get(candidate_id)
        if existing is None or ("OBI_AUTHOR_ALPHA_ROOT" in row.get("original_path", "") and "OBI_AUTHOR_ALPHA_ROOT" not in existing.get("original_path", "")):
            by_candidate[candidate_id] = row
    return list(by_candidate.values())


def build_external_index(external_rows: list[dict]) -> list[dict]:
    indexed = []
    for row in external_rows:
        indexed.append(
            {
                **row,
                "_title": normalize_title(row.get("title", "")),
                "_author": surname_token(row.get("author", "")),
                "_year": row.get("year", ""),
            }
        )
    return indexed


def find_external_match(candidate: dict, external_index: list[dict]) -> dict | None:
    title = normalize_title(candidate.get("title_original", ""))
    author = surname_token(candidate.get("author_original", ""))
    year = candidate.get("year", "")
    if not title:
        return None
    for row in external_index:
        if row["_title"] != title:
            continue
        if year and row["_year"] and row["_year"] != year:
            continue
        if author and row["_author"] and author != row["_author"]:
            continue
        return row
    return None


def candidate_search_blob(candidate: dict, family: dict, members: list[dict]) -> str:
    parts = [
        family.get("family_label", ""),
        family.get("sample_raw_references", ""),
        candidate.get("title_original", ""),
        candidate.get("author_original", ""),
        candidate.get("provisional_short_label", ""),
        candidate.get("evidence_raw_references", ""),
    ]
    parts.extend(member.get("raw_reference_string", "") for member in members[:5])
    return normalize_title(" ".join(part for part in parts if part))


def score_local_candidate(local_row: dict, candidate: dict, family: dict, members: list[dict]) -> tuple[int, str]:
    search_blob = candidate_search_blob(candidate, family, members)
    local_title = normalize_title(local_row.get("probable_work_label", "") or local_row.get("name", ""))
    local_author = surname_token(local_row.get("probable_author", "") or local_row.get("name", ""))
    local_year = local_row.get("probable_year", "")
    title_overlap = {
        token
        for token in set(title_keyword_tokens(local_title)) & set(title_keyword_tokens(search_blob))
        if token not in GENERIC_MATCH_TOKENS
    }
    score = 0
    reasons: list[str] = []
    if len(title_overlap) >= 2:
        score += min(len(title_overlap) * 2, 6)
        reasons.append(f"title-token overlap: {', '.join(sorted(title_overlap))}")
    if local_title and len(title_keyword_tokens(local_title)) >= 3 and (local_title in search_blob or search_blob in local_title):
        score += 4
        reasons.append("title substring match")
    if local_author and local_author in search_blob:
        score += 2
        reasons.append(f"author surname match: {local_author}")
    if local_year and (local_year == candidate.get("year") or local_year in family.get("sample_raw_references", "")):
        score += 1
        reasons.append(f"year match: {local_year}")
    if local_row.get("search_term") and normalize_title(local_row["search_term"]) not in GENERIC_MATCH_TOKENS and normalize_title(local_row["search_term"]) in search_blob:
        score += 1
        reasons.append(f"search term match: {local_row['search_term']}")
    if score and not (local_author or len(title_overlap) >= 2 or "title substring match" in reasons):
        return 0, ""
    return score, "; ".join(reasons)


def build_seed_authority(
    seed_row: dict,
    family_row: dict,
    frasch_rows: list[dict],
    local_candidate_rows: list[dict],
    existing_keys: set[str],
) -> dict:
    abbreviation = seed_row.get("abbreviation", "")
    normalized_abbreviation = normalize_source_family_key(abbreviation)
    defaults = SOURCE_FAMILY_LIBRARY.get(normalized_abbreviation, {})
    frasch_search_terms = defaults.get("frasch_search_terms", [abbreviation.casefold(), seed_row.get("provisional_label", "").casefold()])
    local_search_terms = defaults.get("local_search_terms", frasch_search_terms)
    frasch_match = find_frasch_match(frasch_rows, frasch_search_terms)
    local_match = find_local_match(local_candidate_rows, local_search_terms)
    source_of_authority = ""
    matched_local_source_id = ""
    matched_local_source_file = ""
    matched_local_reference = ""
    match_reason = ""
    match_confidence = "low"
    evidence_id = ""
    short_evidence_note = ""

    if local_match:
        match = local_match
        source_of_authority = local_source_kind(match)
        matched_local_source_id = match.get("canonical_local_file_id", "") or match.get("candidate_id", "")
        matched_local_source_file = match.get("file_name", "") or match.get("name", "")
        matched_local_reference = short_reference(match.get("probable_work_label", "") or match.get("name", ""))
        match_reason = f"Matched harvested local file for {abbreviation or family_row['family_label']}."
        match_confidence = "high"
        authority_status = "confirmed_local_source"
        evidence_id = matched_local_source_id or matched_local_source_file or abbreviation
        short_evidence_note = evidence_excerpt(match.get("probable_work_label", "") or match.get("name", ""))
    elif frasch_match:
        match = frasch_match
        source_of_authority = "frasch_bibliography"
        matched_local_source_id = match.get("frasch_ref_id", "")
        matched_local_source_file = match.get("extraction_source_file", "")
        matched_local_reference = short_reference(match.get("raw_reference", ""))
        match_reason = f"Attested in extracted Frasch bibliography evidence for {abbreviation or family_row['family_label']}."
        match_confidence = "medium"
        authority_status = "provisional_local_source"
        evidence_id = matched_local_source_id or abbreviation
        short_evidence_note = evidence_excerpt(match.get("raw_reference", ""))
    else:
        source_of_authority = "corpus_reference"
        authority_status = "provisional_catalogue" if family_row.get("family_type") == "source_catalogue" else "provisional_publication"
        match_reason = "Seeded from bibliography abbreviation table; local evidence not yet confirmed."
        evidence_id = family_row["family_id"]
        short_evidence_note = evidence_excerpt(seed_row.get("evidence_quote_short", "") or seed_row.get("evidence", "") or family_row.get("sample_raw_references", ""))

    title = defaults.get("title") or seed_row.get("provisional_label") or family_row.get("family_label")
    shorttitle = defaults.get("shorttitle") or abbreviation or family_row.get("family_label")
    author = defaults.get("author", "")
    year = defaults.get("year", "")
    preferred_key = defaults.get("preferred_key") or seed_row.get("probable_bibtex_key") or None
    bibtex_key = make_bibtex_key(
        author=author,
        year=year,
        title=title,
        preferred=preferred_key,
        fallback_prefix="sourceUnresolved",
        existing_keys=existing_keys,
    )
    return {
        "bibtex_key": bibtex_key,
        "entry_type": defaults.get("entry_type", "misc"),
        "authority_status": authority_status,
        "source_of_authority": source_of_authority,
        "matched_external_key": "",
        "matched_local_source_id": matched_local_source_id,
        "matched_local_source_file": matched_local_source_file,
        "matched_local_reference": matched_local_reference,
        "match_confidence": match_confidence,
        "match_reason": match_reason,
        "evidence_id": evidence_id,
        "short_evidence_note": short_evidence_note or evidence_excerpt(match_reason),
        "human_review_flag": needs_human_review(
            authority_status,
            "reviewed_provisional" if authority_status == "confirmed_local_source" else "needs_human_review",
        ),
        "family_id": family_row["family_id"],
        "family_label": family_row["family_label"],
        "family_type": family_row["family_type"],
        "author": author,
        "editor": "",
        "year": year,
        "title": title,
        "shorttitle": shorttitle,
        "journal": title if defaults.get("entry_type") == "periodical" else "",
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
        "script": "Latn",
        "translation_relevance": "unknown",
        "review_status": "reviewed_provisional" if authority_status == "confirmed_local_source" else "needs_human_review",
        "evidence": evidence_excerpt(seed_row.get("evidence_quote_short", "") or seed_row.get("evidence", "")),
        "notes": seed_row.get("notes", ""),
    }


def choose_better_row(existing: dict | None, candidate: dict) -> dict:
    if existing is None:
        return candidate
    existing_rank = STATUS_RANK.get(existing["authority_status"], 0)
    candidate_rank = STATUS_RANK.get(candidate["authority_status"], 0)
    if candidate_rank > existing_rank:
        return candidate
    return existing


def build_curated_authority(
    *,
    metadata: dict,
    family_row: dict | None,
    candidate_row: dict | None,
    frasch_row: dict | None,
    local_row: dict | None,
    existing_keys: set[str],
    bibtex_key_override: str | None = None,
) -> dict:
    title = metadata.get("title") or (candidate_row or {}).get("title_original", "") or (family_row or {}).get("family_label", "")
    author = metadata.get("author", "") or (candidate_row or {}).get("author_original", "")
    year = metadata.get("year", "") or (candidate_row or {}).get("year", "")
    bibtex_key = bibtex_key_override or make_bibtex_key(
        author=author,
        year=year,
        title=title,
        preferred=metadata.get("preferred_key"),
        fallback_prefix="authorityResolved",
        existing_keys=existing_keys,
    )
    matched_local_source_id = ""
    matched_local_source_file = ""
    matched_local_reference = ""
    evidence_id = family_row["family_id"] if family_row else bibtex_key
    short_note = metadata.get("notes", "")
    if local_row is not None:
        matched_local_source_id = local_row.get("canonical_local_file_id", "") or local_row.get("candidate_id", "")
        matched_local_source_file = local_row.get("file_name", "") or local_row.get("name", "")
        matched_local_reference = short_reference(local_row.get("probable_work_label", "") or local_row.get("name", ""))
        evidence_id = matched_local_source_id or evidence_id
        short_note = local_row.get("probable_work_label", "") or local_row.get("name", "") or short_note
    elif frasch_row is not None:
        matched_local_source_id = frasch_row.get("frasch_ref_id", "")
        matched_local_source_file = frasch_row.get("extraction_source_file", "")
        matched_local_reference = short_reference(frasch_row.get("raw_reference", ""))
        evidence_id = matched_local_source_id or evidence_id
        short_note = frasch_row.get("raw_reference", "") or short_note

    authority_status = metadata.get("status") or metadata.get("authority_status", "provisional_local_source")
    review_status = metadata.get("review_status", "needs_human_review")
    source_of_authority = metadata.get("source_of_authority", "corpus_reference")
    match_reason = local_row.get("_match_reason", metadata.get("match_reason", metadata.get("notes", ""))) if local_row is not None else metadata.get("match_reason", metadata.get("notes", ""))
    match_confidence = local_row.get("_match_confidence", metadata.get("match_confidence", "medium")) if local_row is not None else metadata.get("match_confidence", "medium")
    if local_row is None and frasch_row is None and authority_status in {"confirmed_local_source", "provisional_local_source"}:
        authority_status = "provisional_publication"
        source_of_authority = "corpus_reference"
        review_status = "needs_human_review"
        match_reason = "Named during high-frequency family review; local evidence still needs confirmation."
        match_confidence = "low"
    return {
        "bibtex_key": bibtex_key,
        "entry_type": metadata.get("entry_type", "misc"),
        "authority_status": authority_status,
        "source_of_authority": source_of_authority,
        "matched_external_key": "",
        "matched_local_source_id": matched_local_source_id,
        "matched_local_source_file": matched_local_source_file,
        "matched_local_reference": matched_local_reference,
        "match_confidence": match_confidence,
        "match_reason": match_reason,
        "evidence_id": evidence_id,
        "short_evidence_note": evidence_excerpt(short_note),
        "human_review_flag": metadata.get("human_review_flag", needs_human_review(authority_status, review_status)),
        "family_id": family_row.get("family_id", "") if family_row else "",
        "family_label": family_row.get("family_label", "") if family_row else metadata.get("shorttitle", title),
        "family_type": family_row.get("family_type", "") if family_row else metadata.get("family_type", ""),
        "author": author,
        "editor": metadata.get("editor", ""),
        "year": year,
        "title": title,
        "shorttitle": metadata.get("shorttitle", title),
        "journal": metadata.get("journal", title if metadata.get("entry_type") == "periodical" else ""),
        "booktitle": metadata.get("booktitle", ""),
        "publisher": metadata.get("publisher", ""),
        "address": metadata.get("address", ""),
        "volume": metadata.get("volume", ""),
        "number": metadata.get("number", ""),
        "pages": metadata.get("pages", ""),
        "doi": metadata.get("doi", ""),
        "url": metadata.get("url", ""),
        "isbn": metadata.get("isbn", ""),
        "language": metadata.get("language", (candidate_row or {}).get("language", "")),
        "script": metadata.get("script", (candidate_row or {}).get("script", "Latn")),
        "translation_relevance": metadata.get("translation_relevance", (candidate_row or {}).get("translation_relevance", "unknown")),
        "review_status": review_status,
        "evidence": evidence_excerpt(short_note),
        "notes": metadata.get("notes", ""),
    }


def build_specific_authority(
    candidate_row: dict,
    family_row: dict,
    local_row: dict | None,
    external_row: dict | None,
    existing_keys: set[str],
) -> dict:
    if external_row is not None:
        bibtex_key = make_bibtex_key(
            author=external_row.get("author", ""),
            year=external_row.get("year", ""),
            title=external_row.get("title", ""),
            preferred=None,
            fallback_prefix="authorityResolved",
            existing_keys=existing_keys,
        )
        return {
            "bibtex_key": bibtex_key,
            "entry_type": external_row.get("entry_type", "book"),
            "authority_status": "confirmed_external_bibtex",
            "source_of_authority": "external_bibtex",
            "matched_external_key": external_row.get("bibtex_key", ""),
            "matched_local_source_id": "",
            "matched_local_source_file": "",
            "matched_local_reference": "",
            "match_confidence": "high",
            "match_reason": "Matched imported external BibTeX metadata by normalized title, author, and year.",
            "evidence_id": external_row.get("bibtex_key", ""),
            "short_evidence_note": evidence_excerpt(candidate_row.get("evidence_raw_references", "") or external_row.get("title", "")),
            "human_review_flag": "false",
            "family_id": family_row["family_id"],
            "family_label": family_row["family_label"],
            "family_type": family_row["family_type"],
            "author": external_row.get("author", ""),
            "editor": external_row.get("editor", ""),
            "year": external_row.get("year", ""),
            "title": external_row.get("title", ""),
            "shorttitle": candidate_row.get("provisional_short_label", "") or family_row["family_label"],
            "journal": external_row.get("journal", ""),
            "booktitle": external_row.get("booktitle", ""),
            "publisher": external_row.get("publisher", ""),
            "address": external_row.get("address", ""),
            "volume": external_row.get("volume", ""),
            "number": external_row.get("number", ""),
            "pages": external_row.get("pages", ""),
            "doi": external_row.get("doi", ""),
            "url": external_row.get("url", ""),
            "isbn": external_row.get("isbn", ""),
            "language": candidate_row.get("language", ""),
            "script": candidate_row.get("script", ""),
            "translation_relevance": candidate_row.get("translation_relevance", "unknown"),
            "review_status": "reviewed_confirmed",
            "evidence": evidence_excerpt(candidate_row.get("evidence_raw_references", "")),
            "notes": candidate_row.get("notes", ""),
        }

    local_title = local_row.get("probable_work_label", "") if local_row else candidate_row.get("title_original", "")
    local_author = local_row.get("probable_author", "") if local_row else candidate_row.get("author_original", "")
    local_year = local_row.get("probable_year", "") if local_row else candidate_row.get("year", "")
    bibtex_key = make_bibtex_key(
        author=local_author or candidate_row.get("author_original", ""),
        year=local_year or candidate_row.get("year", ""),
        title=local_title or candidate_row.get("title_original", "") or family_row["family_label"],
        preferred=None,
        fallback_prefix="authorityResolved",
        existing_keys=existing_keys,
    )
    if local_row:
        confidence = local_row.get("_match_confidence", "medium")
        authority_status = "confirmed_local_source" if confidence == "high" else "provisional_local_source"
        source_of_authority = local_source_kind(local_row)
        match_reason = local_row.get("_match_reason", "Matched harvested local bibliography file.")
    else:
        authority_status = "provisional_publication"
        source_of_authority = "corpus_reference"
        confidence = "low"
        match_reason = "Built from corpus reference candidate only."
    return {
        "bibtex_key": bibtex_key,
        "entry_type": "book" if family_row.get("family_type") in {"book", "source_catalogue"} else "article",
        "authority_status": authority_status,
        "source_of_authority": source_of_authority,
        "matched_external_key": "",
        "matched_local_source_id": (local_row.get("canonical_local_file_id", "") or local_row.get("candidate_id", "")) if local_row else "",
        "matched_local_source_file": (local_row.get("file_name", "") or local_row.get("name", "")) if local_row else "",
        "matched_local_reference": short_reference(local_row.get("probable_work_label", "") if local_row else ""),
        "match_confidence": confidence,
        "match_reason": match_reason,
        "evidence_id": (
            (local_row.get("canonical_local_file_id", "") or local_row.get("candidate_id", "")) if local_row else family_row["family_id"]
        ),
        "short_evidence_note": evidence_excerpt(
            local_row.get("probable_work_label", "") if local_row else candidate_row.get("evidence_raw_references", "")
        ),
        "human_review_flag": needs_human_review(
            authority_status,
            "reviewed_confirmed" if authority_status == "confirmed_local_source" else "needs_human_review",
        ),
        "family_id": family_row["family_id"],
        "family_label": family_row["family_label"],
        "family_type": family_row["family_type"],
        "author": local_author or candidate_row.get("author_original", ""),
        "editor": "",
        "year": local_year or candidate_row.get("year", ""),
        "title": local_title or candidate_row.get("title_original", "") or family_row["family_label"],
        "shorttitle": candidate_row.get("provisional_short_label", "") or family_row["family_label"],
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
        "language": candidate_row.get("language", ""),
        "script": candidate_row.get("script", ""),
        "translation_relevance": candidate_row.get("translation_relevance", "unknown"),
        "review_status": "reviewed_confirmed" if authority_status == "confirmed_local_source" else "needs_human_review",
        "evidence": evidence_excerpt(candidate_row.get("evidence_raw_references", "")),
        "notes": candidate_row.get("notes", ""),
    }


def build_machine_stub(family_row: dict, candidate_row: dict | None, existing_keys: set[str]) -> dict:
    title = candidate_row.get("title_original", "") if candidate_row else family_row["family_label"]
    bibtex_key = make_bibtex_key(
        author=candidate_row.get("author_original", "") if candidate_row else "",
        year=candidate_row.get("year", "") if candidate_row else "",
        title=title,
        preferred=None,
        fallback_prefix="workUnresolved",
        existing_keys=existing_keys,
    )
    return {
        "bibtex_key": bibtex_key,
        "entry_type": "misc",
        "authority_status": "machine_stub",
        "source_of_authority": "corpus_reference",
        "matched_external_key": "",
        "matched_local_source_id": "",
        "matched_local_source_file": "",
        "matched_local_reference": "",
        "match_confidence": "low",
        "match_reason": "Machine-generated fallback stub from bibliography triage.",
        "evidence_id": family_row["family_id"],
        "short_evidence_note": evidence_excerpt(candidate_row.get("evidence_raw_references", "") if candidate_row else family_row.get("sample_raw_references", "")),
        "human_review_flag": "true",
        "family_id": family_row["family_id"],
        "family_label": family_row["family_label"],
        "family_type": family_row["family_type"],
        "author": candidate_row.get("author_original", "") if candidate_row else "",
        "editor": "",
        "year": candidate_row.get("year", "") if candidate_row else "",
        "title": title,
        "shorttitle": candidate_row.get("provisional_short_label", "") if candidate_row else family_row["family_label"],
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
        "language": candidate_row.get("language", "") if candidate_row else "",
        "script": candidate_row.get("script", "") if candidate_row else "",
        "translation_relevance": candidate_row.get("translation_relevance", "unknown") if candidate_row else "unknown",
        "review_status": candidate_row.get("review_status", "unreviewed") if candidate_row else family_row.get("review_status", "unreviewed"),
        "evidence": evidence_excerpt(candidate_row.get("evidence_raw_references", "") if candidate_row else family_row.get("sample_raw_references", "")),
        "notes": "Provisional entry generated from corpus reference triage; requires human review.",
    }


def build_evidence_rows(authority_rows: list[dict], manifest_by_id: dict[str, dict], manifest_by_name: dict[str, dict]) -> list[dict]:
    evidence_rows = []
    for row in authority_rows:
        if not row.get("source_family_id") and row["authority_status"] not in {
            "confirmed_external_bibtex",
            "confirmed_local_source",
            "provisional_local_source",
        }:
            continue
        source_file_id = ""
        source_file_label = ""
        source_ref_id = ""
        evidence_type = row["source_of_authority"] or ("source_family_authority" if row.get("source_family_id") else "authority")
        if row["source_of_authority"] == "external_bibtex":
            source_file_id = "external_bibtex"
            source_file_label = "Imported external BibTeX"
            source_ref_id = row.get("matched_external_key", "")
        elif row.get("matched_local_source_id"):
            manifest_row = manifest_by_id.get(row["matched_local_source_id"]) or manifest_by_name.get(row.get("matched_local_source_file", ""))
            if manifest_row:
                source_file_id = manifest_row.get("canonical_local_file_id", "")
                source_file_label = manifest_row.get("file_name", "")
            else:
                source_file_id = row.get("matched_local_source_id", "")
                source_file_label = row.get("matched_local_source_file", "")
            source_ref_id = row.get("matched_local_source_id", "")
        evidence_rows.append(
            {
                "source_family_id": row.get("source_family_id", ""),
                "bibtex_key": row["bibtex_key"],
                "evidence_id": row.get("evidence_id", "") or row["bibtex_key"],
                "evidence_type": evidence_type,
                "source_file_id": source_file_id,
                "source_file_label": source_file_label,
                "source_ref_id": source_ref_id,
                "short_evidence": evidence_excerpt(row.get("short_evidence_note", "") or row.get("match_reason", "")),
                "full_evidence_hash": text_hash(
                    row.get("matched_local_reference", ""),
                    row.get("matched_local_source_id", ""),
                    row.get("match_reason", ""),
                    row.get("notes", ""),
                ),
                "confidence": row.get("match_confidence", "low"),
                "notes": row.get("notes", ""),
            }
        )
    evidence_rows.sort(key=lambda item: (item["source_family_id"], item["bibtex_key"], item["evidence_id"]))
    return evidence_rows


def build_seed_output_rows(seed_rows: list[dict], authority_rows: list[dict]) -> list[dict]:
    seed_output = {}
    for row in seed_rows:
        seed_output[row["abbreviation"]] = {
            "abbreviation": row.get("abbreviation", ""),
            "family_id": row.get("family_id", ""),
            "family_type": row.get("family_type", ""),
            "provisional_label": row.get("provisional_label", ""),
            "probable_bibtex_key": row.get("probable_bibtex_key", ""),
            "source_type": row.get("source_type", ""),
            "evidence_source_file": row.get("evidence_source_file", ""),
            "evidence_ref_id": row.get("evidence_ref_id", ""),
            "evidence_quote_short": short_reference(row.get("evidence_quote_short", "") or row.get("evidence", "")),
            "confidence": row.get("confidence", ""),
            "needs_human_review": row.get("needs_human_review", "true"),
            "notes": row.get("notes", ""),
        }
    supplemental_seed_rows = [
        {"abbreviation": "ARASI", "provisional_label": "Annual Report of the Archaeological Survey of India", "probable_bibtex_key": "annualReportArchaeologicalSurveyIndia", "source_type": "periodical"},
        {"abbreviation": "Luce D", "provisional_label": "Luce D source family", "probable_bibtex_key": "luceDSourceFamily", "source_type": "misc"},
        {"abbreviation": "Luce J", "provisional_label": "Luce J source family", "probable_bibtex_key": "luceJSourceFamily", "source_type": "misc"},
    ]
    for row in supplemental_seed_rows:
        seed_output.setdefault(
            row["abbreviation"],
            {
                "abbreviation": row["abbreviation"],
                "family_id": "",
                "family_type": "",
                "provisional_label": row["provisional_label"],
                "probable_bibtex_key": row["probable_bibtex_key"],
                "source_type": row["source_type"],
                "evidence_source_file": "",
                "evidence_ref_id": "",
                "evidence_quote_short": "",
                "confidence": "low",
                "needs_human_review": "true",
                "notes": "",
            },
        )
    for authority in authority_rows:
        shorttitle = authority.get("shorttitle", "")
        if shorttitle not in seed_output:
            continue
        row = seed_output[shorttitle]
        row["probable_bibtex_key"] = authority["bibtex_key"]
        row["evidence_source_file"] = authority.get("matched_local_source_file", "")
        row["evidence_ref_id"] = authority.get("matched_local_source_id", "") or authority.get("matched_external_key", "")
        row["evidence_quote_short"] = short_reference(authority.get("short_evidence_note", "") or authority.get("matched_local_reference", ""))
        row["confidence"] = authority.get("match_confidence", "")
        row["needs_human_review"] = authority.get("human_review_flag", "true")
        if authority.get("notes"):
            row["notes"] = authority["notes"]
    return sorted(seed_output.values(), key=lambda row: row["abbreviation"])


def build_resolution_plan_rows(
    family_rows: list[dict],
    family_resolution: dict[str, dict],
    members_by_family: dict[str, list[dict]],
) -> list[dict]:
    ranked = sorted(family_rows, key=lambda row: int(row.get("occurrence_count") or 0), reverse=True)[:TOP_FAMILY_REVIEW_COUNT]
    plan_rows = []
    for family_row in ranked:
        family_id = family_row["family_id"]
        resolution = family_resolution[family_id]
        resolution_status = resolution["resolution_status"]
        resolution_level = resolution["resolution_level"]
        evidence_source = resolution.get("evidence_source", "")
        evidence_confidence = resolution.get("match_confidence", "")
        notes = resolution.get("notes", "")
        if resolution_status in {"source_family_resolved", "alias_resolved", "series_level_resolved"}:
            next_action = "Retain the source-family or series mapping and defer issue/article normalization."
        elif resolution_status in {"confirmed_work", "provisional_work"}:
            next_action = "Confirm work-level publication details and keep the authority key stable."
        elif resolution_status == "needs_human_review":
            next_action = "Review local or Frasch evidence before promoting the provisional work/source-family mapping."
        else:
            next_action = "Resolve the raw family before promoting any work-level authority."
            if not evidence_source:
                evidence_source = members_by_family.get(family_id, [{}])[0].get("raw_reference_string", "")
        authority_key = resolution.get("bibtex_key", "")
        plan_rows.append(
            {
                "family_id": family_id,
                "family_label": family_row.get("family_label", ""),
                "family_type": family_row.get("family_type", ""),
                "occurrence_count": family_row.get("occurrence_count", "0"),
                "sample_raw_references": family_row.get("sample_raw_references", ""),
                "resolution_status": resolution_status,
                "resolution_level": resolution_level,
                "authority_key": authority_key,
                "needs_human_review": resolution.get("needs_human_review", "true"),
                "evidence_id": resolution.get("evidence_id", ""),
                "evidence_source": evidence_source,
                "evidence_confidence": evidence_confidence,
                "next_action": next_action,
                "notes": notes,
            }
        )
    return plan_rows


def build_source_family_output_rows(
    source_family_rows: dict[str, dict],
    authority_by_key: dict[str, dict],
    authority_by_family: dict[str, dict],
    acronym_status_rows: list[dict],
) -> list[dict]:
    output_rows = []
    acronym_by_source_family = {
        row["source_family_id"]: row for row in acronym_status_rows if row.get("source_family_id")
    }
    acronym_by_abbreviation = {row["acronym"]: row for row in acronym_status_rows if row.get("acronym")}
    for row in source_family_rows.values():
        family_key = row["source_family_key"]
        library_defaults = SOURCE_FAMILY_LIBRARY.get(family_key, {})
        source_work_defaults = SOURCE_WORK_RELATIONSHIPS.get(family_key, {})
        acronym_row = acronym_by_source_family.get(row["source_family_id"]) or acronym_by_abbreviation.get(row["abbreviation"])
        locator_only_status = bool(
            acronym_row and acronym_row.get("resolution_status") in NON_BIBTEX_LOCATOR_ACRONYM_STATUSES
        )
        authority_key = ""
        preferred_key = library_defaults.get("preferred_key", "")
        authority_row = authority_by_key.get(preferred_key)
        if authority_row is None and preferred_key.lower() != preferred_key:
            authority_row = authority_by_key.get(preferred_key.lower())
        if authority_row is None:
            authority_row = authority_by_family.get(row["family_id"])
        if locator_only_status:
            authority_row = None
        if authority_row is not None:
            authority_key = authority_row["bibtex_key"]
        elif preferred_key and not locator_only_status:
            authority_key = preferred_key
        expanded_label = row["expanded_label"]
        if acronym_row:
            if acronym_row["resolution_status"] in {
                "alias_or_variant_of_PPA",
                "confirmed_expansion",
                "internal_locator_system",
                "probable_typo_for_PPA",
                "probable_expansion",
                "probable_locator_system",
                "probable_private_luce_locator_system",
                "source_family_with_unknown_expansion_but_known_function",
                "not_an_acronym",
                "internal_locator",
            }:
                expanded_label = acronym_row.get("current_expansion", "") or expanded_label
            else:
                expanded_label = f'{row["abbreviation"]} source family [unexpanded]'
        source_work_key = source_work_defaults.get("source_work_key", "")
        if not source_work_key and acronym_row and acronym_row.get("resolution_status") in {
            "alias_or_variant_of_PPA",
            "confirmed_expansion",
            "probable_expansion",
            "probable_typo_for_PPA",
            "not_an_acronym",
        }:
            source_work_key = authority_key
        related_source_work_key = source_work_key or authority_key
        source_work_bibtex_key = ""
        if source_work_key:
            preferred_source_work_key = SOURCE_WORK_AUTHORITY_LIBRARY.get(source_work_key, {}).get("bibtex_key", "")
            source_work_authority_row = authority_by_key.get(preferred_source_work_key) or authority_by_key.get(source_work_key)
            if source_work_authority_row is not None:
                source_work_bibtex_key = source_work_authority_row.get("bibtex_key", "")
        related_bibtex_key = authority_key or source_work_bibtex_key or ""
        output_rows.append(
            {
                "source_family_id": row["source_family_id"],
                "abbreviation": row["abbreviation"],
                "family_id": row["family_id"],
                "authority_key": authority_key,
                "alias_of_source_family_id": source_work_defaults.get("alias_of_source_family_id", ""),
                "source_work_key": source_work_key,
                "related_source_work_key": related_source_work_key,
                "source_family_type": row["source_family_type"],
                "resolution_status": row["resolution_status"],
                "resolution_level": row["resolution_level"],
                "canonical_label": row["canonical_label"],
                "expanded_label": expanded_label,
                "acronym_resolution_status": acronym_row.get("resolution_status", "") if acronym_row else "",
                "definition_quality": acronym_row.get("definition_quality", "") if acronym_row else "",
                "best_definition_evidence_id": acronym_row.get("best_evidence_id", "") if acronym_row else "",
                "best_definition_source": acronym_row.get("best_evidence_source", "") if acronym_row else "",
                "best_definition_quote": acronym_row.get("best_evidence_quote", "") if acronym_row else "",
                "related_bibtex_key": related_bibtex_key,
                "locator_pattern": row["locator_pattern"],
                "locator_type": row["locator_pattern"],
                "example_raw_references": row["example_raw_references"],
                "evidence_id": authority_row.get("evidence_id", row["family_id"]) if authority_row else row["family_id"],
                "evidence_source": authority_row.get("source_of_authority", "corpus_reference") if authority_row else "corpus_reference",
                "confidence": (
                    acronym_row.get("confidence", "")
                    if acronym_row and acronym_row.get("definition_quality") == "manual_seed"
                    else authority_row.get("match_confidence", row["confidence"]) if authority_row else row["confidence"]
                ),
                "needs_human_review": (
                    "true"
                    if acronym_row and truthy(acronym_row.get("needs_human_review", ""))
                    else authority_row.get("human_review_flag", row["needs_human_review"]) if authority_row else row["needs_human_review"]
                ),
                "notes": " ".join(
                    part
                    for part in (
                        authority_row.get("notes", row["notes"]) if authority_row else row["notes"],
                        acronym_row.get("notes", "") if acronym_row else "",
                    )
                    if part
                ),
            }
        )
    output_rows.sort(key=lambda item: item["abbreviation"])
    return output_rows


def build_manual_review_packet(
    *,
    acronym_status_rows: list[dict],
    manual_acronym_seeds: dict[str, dict],
    acronym_candidates_by_acronym: dict[str, list[dict]],
    ocr_queue_rows: list[dict],
    ocr_manifest_rows: list[dict],
    ocr_index_rows: list[dict],
    remaining_acronym_evidence_rows: list[dict],
    remaining_worklist_rows: list[dict],
) -> list[dict]:
    status_by_acronym = {row["acronym"]: row for row in acronym_status_rows}
    remaining_worklist_by_acronym = {row["acronym"]: row for row in remaining_worklist_rows}
    remaining_evidence_by_acronym: dict[str, list[dict]] = defaultdict(list)
    for row in remaining_acronym_evidence_rows:
        remaining_evidence_by_acronym[row["acronym"]].append(row)
    ocr_queue_by_acronym: dict[str, list[str]] = defaultdict(list)
    for row in ocr_queue_rows:
        for acronym in [item.strip() for item in row.get("target_acronyms", "").split(",") if item.strip()]:
            ocr_queue_by_acronym[acronym].append(row.get("source_file_label", ""))
    ocr_hits_by_acronym: dict[str, list[str]] = defaultdict(list)
    ocr_success_by_label = {
        row.get("source_file_label", "")
        for row in ocr_manifest_rows
        if row.get("extraction_status") == "success" and row.get("source_file_label")
    }
    for row in ocr_index_rows:
        acronyms = [item.strip() for item in row.get("acronyms_found", "").split(",") if item.strip()]
        for acronym in acronyms:
            ocr_hits_by_acronym[acronym].append(row.get("source_file_label", ""))

    packet_rows: list[dict] = []
    for acronym in PRIORITY_ACRONYMS:
        status_row = status_by_acronym.get(acronym, {})
        manual_seed = manual_acronym_seeds.get(acronym, {})
        remaining_evidence = remaining_evidence_by_acronym.get(acronym, [])
        candidate_expansions = sorted(
            {
                row.get("candidate_expansion", "")
                for row in acronym_candidates_by_acronym.get(acronym, [])
                if row.get("candidate_expansion")
            }
            | {
                row.get("candidate_expansion", "")
                for row in remaining_evidence
                if row.get("candidate_expansion")
            }
        )
        ocr_sources_checked = sorted(set(filter(None, ocr_queue_by_acronym.get(acronym, []))))
        ocr_successful_sources = [label for label in ocr_sources_checked if label in ocr_success_by_label]
        new_ocr_hits = sorted(set(filter(None, ocr_hits_by_acronym.get(acronym, []))))
        notes = status_row.get("notes", "")
        if acronym in remaining_worklist_by_acronym:
            worklist_row = remaining_worklist_by_acronym[acronym]
            notes = " ".join(
                part
                for part in (
                    notes,
                    f'Targeted files checked: {worklist_row.get("specific_files_to_check", "")}.',
                    f'Searched terms: {worklist_row.get("specific_search_terms", "")}.',
                )
                if part
            )
        if not new_ocr_hits and ocr_successful_sources:
            notes = " ".join(part for part in (notes, "Not found after targeted OCR review.") if part)
        elif ocr_sources_checked and not ocr_successful_sources:
            notes = " ".join(part for part in (notes, "Targeted OCR was attempted, but no queued source produced usable OCR text.") if part)
        packet_rows.append(
            {
                "acronym": acronym,
                "current_status": status_row.get("resolution_status", "unresolved"),
                "current_expansion": status_row.get("current_expansion", ""),
                "best_evidence_source": status_row.get("best_evidence_source", ""),
                "best_evidence_quote": status_row.get("best_evidence_quote", ""),
                "manual_seed": manual_seed.get("expansion", ""),
                "ocr_sources_checked": " | ".join(ocr_sources_checked),
                "new_ocr_hits": " | ".join(new_ocr_hits),
                "candidate_expansions": " | ".join(candidate_expansions),
                "recommended_resolution": status_row.get("resolution_status", "unresolved"),
                "confidence": status_row.get("confidence", "low"),
                "needs_human_review": status_row.get("needs_human_review", "true"),
                "notes": notes,
            }
        )
    return packet_rows


def build_family_resolution(
    *,
    family_rows: list[dict],
    source_family_rows: dict[str, dict],
    family_to_source_family: dict[str, str],
    authority_by_family: dict[str, dict],
    candidate_rows_by_family: dict[str, dict],
) -> dict[str, dict]:
    source_family_by_id = {row["source_family_id"]: row for row in source_family_rows.values()}
    family_resolution: dict[str, dict] = {}

    for family_row in family_rows:
        family_id = family_row["family_id"]
        source_family_key = family_to_source_family.get(family_id)
        if source_family_key:
            semantic = SOURCE_FAMILY_SEMANTICS[source_family_key]
            source_family_row = source_family_by_id[semantic["source_family_id"]]
            direct_family_id = semantic.get("canonical_family_id")
            is_direct = bool(direct_family_id and family_id == direct_family_id) or (
                not direct_family_id and family_id == source_family_row["family_id"]
            )
            resolution_status = source_family_row["resolution_status"] if is_direct else "alias_resolved"
            resolution_level = source_family_row["resolution_level"] if is_direct else "abbreviation"
            source_work_key = canonical_source_work_key(source_family_row.get("source_work_key", ""))
            bibtex_key = source_family_row.get("authority_key", "") or source_family_row.get("related_bibtex_key", "")
            if bibtex_key:
                canonical_bibtex_work_key = canonical_source_work_key(
                    SOURCE_WORK_KEY_BY_BIBTEX_KEY.get(bibtex_key, bibtex_key)
                )
                if canonical_bibtex_work_key in SOURCE_WORK_AUTHORITY_LIBRARY:
                    bibtex_key = SOURCE_WORK_AUTHORITY_LIBRARY[canonical_bibtex_work_key].get("bibtex_key", "") or bibtex_key
            family_resolution[family_id] = {
                "source_family_id": source_family_row["source_family_id"],
                "source_work_key": source_work_key,
                "bibtex_key": bibtex_key,
                "resolution_status": resolution_status,
                "resolution_level": resolution_level,
                "match_type": source_family_match_type(resolution_status, resolution_level),
                "match_confidence": source_family_row["confidence"],
                "needs_human_review": source_family_row["needs_human_review"],
                "evidence_id": source_family_row["evidence_id"],
                "evidence_source": source_family_row["evidence_source"],
                "notes": source_family_row["notes"],
                "authority_status": "",
            }
            continue

        authority_row = authority_by_family.get(family_id)
        if authority_row is not None:
            resolution_status, resolution_level = resolution_from_authority_row(authority_row)
            family_resolution[family_id] = {
                "source_family_id": authority_row.get("source_family_id", ""),
                "source_work_key": canonical_source_work_key(authority_row["bibtex_key"]) if resolution_level in {"work", "book", "article", "series"} else "",
                "bibtex_key": authority_row["bibtex_key"],
                "resolution_status": resolution_status,
                "resolution_level": resolution_level,
                "match_type": "confirmed_work_match" if resolution_status == "confirmed_work" else "provisional_work_match",
                "match_confidence": authority_row.get("match_confidence", "low"),
                "needs_human_review": authority_row.get("human_review_flag", "true"),
                "evidence_id": authority_row.get("evidence_id", ""),
                "evidence_source": authority_row.get("source_of_authority", ""),
                "notes": authority_row.get("notes", ""),
                "authority_status": authority_row.get("authority_status", ""),
            }
            continue

        candidate_row = candidate_rows_by_family.get(family_id)
        if candidate_row is not None:
            family_resolution[family_id] = {
                "source_family_id": "",
                "source_work_key": "",
                "bibtex_key": candidate_row["bibtex_key"],
                "resolution_status": "needs_human_review",
                "resolution_level": "unknown",
                "match_type": "machine_stub_match",
                "match_confidence": "low",
                "needs_human_review": "true",
                "evidence_id": candidate_row.get("evidence_id", family_id),
                "evidence_source": candidate_row.get("source_of_authority", "corpus_reference"),
                "notes": candidate_row.get("notes", ""),
                "authority_status": candidate_row.get("authority_status", ""),
            }
            continue

        family_resolution[family_id] = {
            "source_family_id": "",
            "source_work_key": "",
            "bibtex_key": "",
            "resolution_status": "unresolved",
            "resolution_level": "unknown",
            "match_type": "no_match",
            "match_confidence": "low",
            "needs_human_review": "true",
            "evidence_id": family_id,
            "evidence_source": "corpus_reference",
            "notes": "No stable source-family or plausible standalone work authority has been assigned.",
            "authority_status": "",
        }
    return family_resolution


def build_authority(
    *,
    reference_families_path: Path,
    reference_members_path: Path,
    work_candidates_path: Path,
    seed_path: Path,
    external_entries_path: Path | None = None,
    output_dir: Path,
    frasch_references_path: Path | None = None,
    local_candidates_path: Path | None = None,
    local_manifest_path: Path | None = None,
    acronym_candidates_path: Path | None = None,
    acronym_report_path: Path | None = None,
    manual_acronym_seeds_path: Path | None = None,
    ocr_queue_path: Path | None = None,
    ocr_manifest_path: Path | None = None,
    ocr_index_path: Path | None = None,
    ocr_report_path: Path | None = None,
    corpus_inscriptions_path: Path | None = None,
    reference_occurrences_path: Path | None = None,
    raw_references_path: Path | None = None,
    frasch_extracted_text_path: Path | None = None,
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    frasch_references_path = frasch_references_path or Path("data/working/bibliography/local_sources/frasch_reference_entries.tsv")
    local_candidates_path = local_candidates_path or Path("data/working/bibliography/local_sources/high_priority_local_candidates.tsv")
    local_manifest_path = local_manifest_path or Path("data/working/bibliography/local_sources/local_file_manifest.tsv")
    acronym_candidates_path = acronym_candidates_path or Path("data/working/bibliography/local_sources/acronym_definition_candidates.tsv")
    acronym_report_path = acronym_report_path or Path("data/working/bibliography/local_sources/acronym_definition_report.json")
    manual_acronym_seeds_path = manual_acronym_seeds_path or Path("data/working/bibliography/bibtex_authority/manual_acronym_seeds.tsv")
    ocr_queue_path = ocr_queue_path or Path("data/working/bibliography/local_sources/ocr_priority_queue.tsv")
    ocr_manifest_path = ocr_manifest_path or Path("data/working/bibliography/local_sources/ocr_outputs/ocr_manifest.tsv")
    ocr_index_path = ocr_index_path or Path("data/working/bibliography/local_sources/ocr_outputs/ocr_text_index.tsv")
    ocr_report_path = ocr_report_path or Path("data/working/bibliography/local_sources/ocr_outputs/ocr_report.json")
    corpus_inscriptions_path = corpus_inscriptions_path or DEFAULT_CORPUS_RELEASE_INSCRIPTIONS_PATH
    reference_occurrences_path = reference_occurrences_path or DEFAULT_REFERENCE_OCCURRENCES_PATH
    raw_references_path = raw_references_path or DEFAULT_RAW_REFERENCES_PATH
    frasch_extracted_text_path = frasch_extracted_text_path or DEFAULT_FRASCH_EXTRACTED_TEXT_PATH

    family_rows = read_tsv(reference_families_path)
    member_rows = read_tsv(reference_members_path)
    work_candidate_rows = read_tsv(work_candidates_path)
    seed_rows = read_tsv(seed_path)
    external_rows = read_tsv(external_entries_path) if external_entries_path and external_entries_path.exists() else []
    frasch_rows_all = read_tsv(frasch_references_path) if frasch_references_path.exists() else []
    frasch_rows = usable_frasch_rows(frasch_rows_all)
    local_candidate_rows = dedupe_local_candidates(read_tsv(local_candidates_path)) if local_candidates_path.exists() else []
    local_manifest_rows = read_tsv(local_manifest_path) if local_manifest_path.exists() else []
    acronym_candidates_by_acronym = load_acronym_candidates(acronym_candidates_path)
    acronym_report = load_json_report(acronym_report_path)
    manual_acronym_seeds = load_manual_acronym_seeds(manual_acronym_seeds_path)
    ocr_queue_rows = read_tsv(ocr_queue_path) if ocr_queue_path.exists() else []
    ocr_manifest_rows = read_tsv(ocr_manifest_path) if ocr_manifest_path.exists() else []
    ocr_index_rows = read_tsv(ocr_index_path) if ocr_index_path.exists() else []
    ocr_report = load_json_report(ocr_report_path)
    ippa_review = build_ippa_review_artifacts(
        corpus_inscriptions_path=corpus_inscriptions_path,
        reference_occurrences_path=reference_occurrences_path,
        frasch_extracted_text_path=frasch_extracted_text_path,
    )
    manifest_by_id = {row.get("canonical_local_file_id", ""): row for row in local_manifest_rows if row.get("canonical_local_file_id")}
    manifest_by_name = {row.get("file_name", ""): row for row in local_manifest_rows if row.get("file_name")}

    family_by_id = {row["family_id"]: row for row in family_rows}
    members_by_family: dict[str, list[dict]] = defaultdict(list)
    for row in member_rows:
        members_by_family[row["family_id"]].append(row)
    candidates_by_family: dict[str, list[dict]] = defaultdict(list)
    for row in work_candidate_rows:
        candidates_by_family[row["family_id"]].append(row)
    seed_by_family = {row["family_id"]: row for row in seed_rows if row.get("family_id")}
    external_index = build_external_index(external_rows)

    authority_by_family: dict[str, dict] = {}
    authority_by_key: dict[str, dict] = {}
    candidate_rows_by_family: dict[str, dict] = {}
    existing_keys: set[str] = set()
    source_family_rows_raw, family_to_source_family_key = build_source_family_lookup(family_rows)

    for family_id, seed_row in seed_by_family.items():
        family_row = family_by_id.get(family_id)
        if family_row is None:
            continue
        authority_row = build_seed_authority(seed_row, family_row, frasch_rows, local_candidate_rows, existing_keys)
        existing_keys.add(authority_row["bibtex_key"])
        chosen_row = choose_better_row(authority_by_family.get(family_id), authority_row)
        authority_by_family[family_id] = chosen_row
        authority_by_key[chosen_row["bibtex_key"]] = chosen_row

    needed_supplemental_keys = {
        SOURCE_FAMILY_LIBRARY.get(row["source_family_key"], {}).get("preferred_key", "")
        for row in source_family_rows_raw.values()
        if SOURCE_FAMILY_LIBRARY.get(row["source_family_key"], {}).get("preferred_key", "") in SUPPLEMENTAL_AUTHORITIES
    }
    for bibtex_key, metadata in SUPPLEMENTAL_AUTHORITIES.items():
        if bibtex_key not in needed_supplemental_keys:
            continue
        evidence_row = find_frasch_match(frasch_rows_all, metadata.get("evidence_terms", []))
        authority_row = build_curated_authority(
            metadata=metadata,
            family_row=None,
            candidate_row=None,
            frasch_row=evidence_row,
            local_row=None,
            existing_keys=existing_keys,
            bibtex_key_override=bibtex_key,
        )
        existing_keys.add(authority_row["bibtex_key"])
        authority_by_key[authority_row["bibtex_key"]] = authority_row

    for family_id, metadata in CURATED_FAMILY_LIBRARY.items():
        family_row = family_by_id.get(family_id)
        if family_row is None:
            continue
        candidate_row = candidates_by_family.get(family_id, [{}])[0]
        local_row = find_local_match(local_candidate_rows, metadata.get("local_search_terms", [])) if metadata.get("local_search_terms") else None
        manual_match = MANUAL_LOCAL_MATCHES.get(family_id)
        if local_row is None and manual_match:
            local_row = next(
                (
                    {
                        **row,
                        "_match_reason": "Matched explicit local file rule for a high-priority bibliography work.",
                        "_match_confidence": manual_match["confidence"],
                    }
                    for row in local_candidate_rows
                    if any(term in normalize_title(f"{row.get('probable_work_label', '')} {row.get('name', '')} {row.get('original_path', '')}") for term in manual_match["filename_terms"])
                ),
                None,
            )
        frasch_row = find_frasch_match(frasch_rows, metadata.get("frasch_search_terms", [])) if metadata.get("frasch_search_terms") else None
        authority_row = build_curated_authority(
            metadata=metadata,
            family_row=family_row,
            candidate_row=candidate_row,
            frasch_row=frasch_row,
            local_row=local_row,
            existing_keys=existing_keys,
        )
        existing_keys.add(authority_row["bibtex_key"])
        chosen_row = choose_better_row(authority_by_family.get(family_id), authority_row)
        authority_by_family[family_id] = chosen_row
        authority_by_key[chosen_row["bibtex_key"]] = chosen_row

    for source_family_row in source_family_rows_raw.values():
        family_key = source_family_row["source_family_key"]
        defaults = SOURCE_FAMILY_LIBRARY.get(family_key, {})
        preferred_key = defaults.get("preferred_key", "")
        if not preferred_key or preferred_key in authority_by_key:
            continue
        family_row = family_by_id.get(source_family_row["family_id"])
        frasch_row = find_frasch_match(frasch_rows, defaults.get("frasch_search_terms", [])) if defaults.get("frasch_search_terms") else None
        local_row = find_local_match(local_candidate_rows, defaults.get("local_search_terms", [])) if defaults.get("local_search_terms") else None
        authority_row = build_curated_authority(
            metadata={
                "author": defaults.get("author", ""),
                "year": defaults.get("year", ""),
                "title": defaults.get("title", source_family_row["expanded_label"]),
                "shorttitle": defaults.get("shorttitle", source_family_row["abbreviation"]),
                "entry_type": defaults.get("entry_type", "misc"),
                "preferred_key": preferred_key,
                "status": "provisional_publication"
                if source_family_row["source_family_type"] == "periodical"
                else "provisional_catalogue",
                "source_of_authority": "source_abbreviation_seed",
                "review_status": "needs_human_review",
                "match_confidence": source_family_row["confidence"],
                "match_reason": source_family_row["notes"],
                "notes": source_family_row["notes"],
            },
            family_row=family_row,
            candidate_row=candidates_by_family.get(source_family_row["family_id"], [{}])[0] if family_row else None,
            frasch_row=frasch_row,
            local_row=local_row,
            existing_keys=existing_keys,
            bibtex_key_override=preferred_key,
        )
        existing_keys.add(authority_row["bibtex_key"])
        authority_by_key[authority_row["bibtex_key"]] = authority_row
        if family_row is not None and family_row["family_id"] not in authority_by_family:
            authority_by_family[family_row["family_id"]] = authority_row

    for family_row in family_rows:
        family_id = family_row["family_id"]
        if family_id in seed_by_family or family_id in authority_by_family or family_id in family_to_source_family_key:
            continue
        best_candidate = candidates_by_family.get(family_id, [{}])[0]
        manual_match = MANUAL_LOCAL_MATCHES.get(family_id)
        if manual_match:
            manual_local = next(
                (
                    {
                        **row,
                        "_match_reason": "Matched explicit local file rule for a high-priority bibliography work.",
                        "_match_confidence": manual_match["confidence"],
                    }
                    for row in local_candidate_rows
                    if any(term in normalize_title(f"{row.get('probable_work_label', '')} {row.get('name', '')} {row.get('original_path', '')}") for term in manual_match["filename_terms"])
                ),
                None,
            )
            if manual_local is not None:
                authority_row = build_specific_authority(best_candidate, family_row, manual_local, None, existing_keys)
                existing_keys.add(authority_row["bibtex_key"])
                authority_by_family[family_id] = choose_better_row(
                    authority_by_family.get(family_id),
                    authority_row,
                )
                authority_by_key[authority_by_family[family_id]["bibtex_key"]] = authority_by_family[family_id]
                continue
        external_match = find_external_match(best_candidate, external_index) if best_candidate else None
        best_local: dict | None = None
        best_score = 0
        for local_row in local_candidate_rows:
            score, reason = score_local_candidate(local_row, best_candidate, family_row, members_by_family.get(family_id, []))
            if score > best_score:
                best_score = score
                best_local = {**local_row, "_match_reason": reason, "_match_confidence": "high" if score >= 6 else "medium"}
        if external_match is not None:
            authority_row = build_specific_authority(best_candidate, family_row, None, external_match, existing_keys)
            existing_keys.add(authority_row["bibtex_key"])
            authority_by_family[family_id] = choose_better_row(
                authority_by_family.get(family_id),
                authority_row,
            )
            authority_by_key[authority_by_family[family_id]["bibtex_key"]] = authority_by_family[family_id]
            continue
        if best_local is not None and best_score >= 6:
            authority_row = build_specific_authority(best_candidate, family_row, best_local, None, existing_keys)
            existing_keys.add(authority_row["bibtex_key"])
            authority_by_family[family_id] = choose_better_row(
                authority_by_family.get(family_id),
                authority_row,
            )
            authority_by_key[authority_by_family[family_id]["bibtex_key"]] = authority_by_family[family_id]

    remaining_acronym_evidence_rows = build_remaining_acronym_evidence_rows()
    acronym_status_rows = build_acronym_status_rows(
        source_family_rows_raw,
        acronym_candidates_by_acronym,
        manual_acronym_seeds,
        remaining_acronym_evidence_rows,
    )
    suppressed_locator_source_families = {
        row["source_family_id"]
        for row in acronym_status_rows
        if row.get("source_family_id") and row.get("resolution_status") in NON_BIBTEX_LOCATOR_ACRONYM_STATUSES
    }
    if suppressed_locator_source_families:
        suppressed_bibtex_keys = set()
        for source_family_id in suppressed_locator_source_families:
            source_family_row = source_family_rows_raw.get(source_family_id)
            if not source_family_row:
                continue
            family_key = source_family_row["source_family_key"]
            preferred_key = SOURCE_FAMILY_LIBRARY.get(family_key, {}).get("preferred_key", "")
            source_work_key = SOURCE_WORK_RELATIONSHIPS.get(family_key, {}).get("source_work_key", "")
            source_work_bibtex_key = SOURCE_WORK_AUTHORITY_LIBRARY.get(source_work_key, {}).get("bibtex_key", "") if source_work_key else ""
            if preferred_key and preferred_key != source_work_bibtex_key:
                suppressed_bibtex_keys.add(preferred_key)
        authority_by_family = {
            family_id: row
            for family_id, row in authority_by_family.items()
            if row.get("source_family_id") not in suppressed_locator_source_families
        }
        authority_by_key = {
            key: row
            for key, row in authority_by_key.items()
            if row.get("source_family_id") not in suppressed_locator_source_families and key not in suppressed_bibtex_keys
        }
    source_family_output_rows = build_source_family_output_rows(
        source_family_rows_raw,
        authority_by_key,
        authority_by_family,
        acronym_status_rows,
    )
    remaining_worklist_rows = build_remaining_acronym_worklist(
        source_family_rows=source_family_rows_raw,
        acronym_status_rows=acronym_status_rows,
        remaining_evidence_rows=remaining_acronym_evidence_rows,
    )
    final_acronym_resolution_sprint_rows = build_final_acronym_resolution_sprint(
        acronym_status_rows=acronym_status_rows,
        remaining_worklist_rows=remaining_worklist_rows,
    )
    final_acronym_local_file_hit_rows = build_final_acronym_local_file_hits()
    final_acronym_web_search_rows = build_final_acronym_web_searches()
    unresolved_acronym_dossier_rows = build_unresolved_acronym_dossier(acronym_status_rows)
    manual_review_packet_rows = build_manual_review_packet(
        acronym_status_rows=acronym_status_rows,
        manual_acronym_seeds=manual_acronym_seeds,
        acronym_candidates_by_acronym=acronym_candidates_by_acronym,
        ocr_queue_rows=ocr_queue_rows,
        ocr_manifest_rows=ocr_manifest_rows,
        ocr_index_rows=ocr_index_rows,
        remaining_acronym_evidence_rows=remaining_acronym_evidence_rows,
        remaining_worklist_rows=remaining_worklist_rows,
    )
    source_family_by_id = {row["source_family_id"]: row for row in source_family_output_rows}
    source_family_by_authority_key = {row["authority_key"]: row for row in source_family_output_rows if row.get("authority_key")}

    authority_rows = []
    for row in authority_by_key.values():
        authority_row = dict(row)
        source_family_row = None
        if authority_row.get("family_id") and authority_row["family_id"] in family_to_source_family_key:
            semantic_key = family_to_source_family_key[authority_row["family_id"]]
            source_family_row = source_family_by_id[SOURCE_FAMILY_SEMANTICS[semantic_key]["source_family_id"]]
        elif authority_row["bibtex_key"] in source_family_by_authority_key:
            source_family_row = source_family_by_authority_key[authority_row["bibtex_key"]]
        if source_family_row is not None:
            authority_row["source_family_id"] = source_family_row["source_family_id"]
            authority_row["resolution_status"] = source_family_row["resolution_status"]
            authority_row["resolution_level"] = source_family_row["resolution_level"]
        else:
            resolution_status, resolution_level = resolution_from_authority_row(authority_row)
            authority_row["source_family_id"] = ""
            authority_row["resolution_status"] = resolution_status
            authority_row["resolution_level"] = resolution_level
        authority_rows.append(authority_row)
    authority_rows.sort(key=lambda row: (row.get("family_label", ""), row["bibtex_key"]))
    authority_rows_raw = [dict(row) for row in authority_rows]

    for family_row in family_rows:
        family_id = family_row["family_id"]
        if family_id in authority_by_family or family_id in family_to_source_family_key:
            continue
        best_candidate = candidates_by_family.get(family_id, [{}])[0]
        if not candidate_is_plausible_standalone(family_row, best_candidate):
            continue
        candidate_row = build_machine_stub(family_row, best_candidate, existing_keys)
        candidate_row["resolution_status"] = "needs_human_review"
        candidate_row["resolution_level"] = "unknown"
        candidate_row["source_family_id"] = ""
        existing_keys.add(candidate_row["bibtex_key"])
        candidate_rows_by_family[family_id] = candidate_row

    candidate_rows = sorted(candidate_rows_by_family.values(), key=lambda row: (row["family_label"], row["bibtex_key"]))
    candidate_stub_review_rows = build_candidate_stub_review_rows(candidate_rows, family_by_id)
    retained_candidate_keys = {
        row["candidate_key"] for row in candidate_stub_review_rows if row["review_decision"] == "retain"
    }
    candidate_rows = [row for row in candidate_rows if row["bibtex_key"] in retained_candidate_keys]
    candidate_rows = [
        {
            **row,
            "script": normalize_script_value(row.get("script", ""), fallback_title=row.get("title", "")),
        }
        for row in candidate_rows
    ]
    candidate_rows_by_family = {
        family_id: row for family_id, row in candidate_rows_by_family.items() if row["bibtex_key"] in retained_candidate_keys
    }
    family_resolution = build_family_resolution(
        family_rows=family_rows,
        source_family_rows={row["source_family_id"]: row for row in source_family_output_rows},
        family_to_source_family=family_to_source_family_key,
        authority_by_family=authority_by_family,
        candidate_rows_by_family=candidate_rows_by_family,
    )

    evidence_rows = build_evidence_rows(authority_rows_raw, manifest_by_id, manifest_by_name)

    crosswalk_rows = []
    unresolved_rows = []
    for family_row in family_rows:
        family_id = family_row["family_id"]
        members = members_by_family.get(family_id, []) or [
            {
                "raw_reference_string": family_row.get("sample_raw_references", ""),
                "occurrence_count": family_row.get("occurrence_count", "0"),
                "notes": "",
            }
        ]
        for member in members:
            locator, locator_type = parse_locator(member.get("raw_reference_string", ""), family_id, family_row["family_label"])
            resolution = family_resolution[family_id]
            source_work_key = canonical_source_work_key(resolution.get("source_work_key", ""))
            bibtex_key = resolution.get("bibtex_key", "")
            if bibtex_key and source_work_key and source_work_key in SOURCE_WORK_AUTHORITY_LIBRARY:
                bibtex_key = SOURCE_WORK_AUTHORITY_LIBRARY[source_work_key].get("bibtex_key", "") or bibtex_key
            resolution_status = resolution["resolution_status"]
            notes = member.get("notes", "")
            if resolution.get("source_family_id") == "sf-ippa":
                resolution_status = "alias_or_variant_of_PPA"
                notes = " ".join(
                    part
                    for part in (
                        notes,
                        "raw IPPA preserved; mapped to PPA-related source work",
                    )
                    if part
                )
            crosswalk_rows.append(
                {
                    "raw_reference_string": member.get("raw_reference_string", ""),
                    "family_id": family_id,
                    "source_family_id": resolution.get("source_family_id", ""),
                    "source_work_key": source_work_key,
                    "work_candidate_id": candidates_by_family.get(family_id, [{}])[0].get("work_candidate_id", ""),
                    "bibtex_key": bibtex_key,
                    "locator": locator,
                    "locator_type": locator_type,
                    "resolution_status": resolution_status,
                    "resolution_level": resolution["resolution_level"],
                    "match_type": resolution["match_type"],
                    "match_confidence": resolution.get("match_confidence", "low"),
                    "evidence": evidence_excerpt(resolution.get("notes", "") or resolution.get("evidence_source", "")),
                    "needs_human_review": resolution.get("needs_human_review", "true"),
                    "notes": notes,
                }
            )
        resolution = family_resolution[family_id]
        if resolution["resolution_status"] == "unresolved":
            unresolved_rows.append(
                {
                    "family_id": family_id,
                    "family_label": family_row["family_label"],
                    "family_type": family_row["family_type"],
                    "member_count": family_row.get("member_count", ""),
                    "occurrence_count": family_row.get("occurrence_count", "0"),
                    "sample_raw_references": family_row.get("sample_raw_references", ""),
                    "current_bibtex_key": resolution.get("bibtex_key", ""),
                    "current_status": resolution["resolution_status"],
                    "suggested_local_search_terms": ", ".join(
                        token
                        for token in [
                            family_row["family_label"],
                            candidates_by_family.get(family_id, [{}])[0].get("author_original", ""),
                            candidates_by_family.get(family_id, [{}])[0].get("title_original", ""),
                        ]
                        if token
                    ),
                    "notes": "Prioritize local library or Frasch-preface evidence review.",
                }
            )

    crosswalk_rows.sort(key=lambda row: (row["family_id"], row["raw_reference_string"]))
    source_work_authority_rows = build_source_work_authority_rows(
        authority_rows=authority_rows_raw,
        source_family_rows=source_family_output_rows,
        crosswalk_rows=crosswalk_rows,
    )
    source_work_to_bibtex_reconciliation_rows = build_source_work_to_bibtex_reconciliation_rows(
        source_work_authority_rows=source_work_authority_rows,
        authority_rows=authority_rows_raw,
        candidate_rows=candidate_rows,
    )
    raw_bibtex_field_quality_audit_rows = build_bibtex_field_quality_audit_rows(
        authority_rows=authority_rows_raw,
        source_work_authority_rows=source_work_authority_rows,
    )
    authority_rows = curate_authority_rows_for_emission(
        authority_rows=authority_rows_raw,
        source_work_authority_rows=source_work_authority_rows,
        reconciliation_rows=source_work_to_bibtex_reconciliation_rows,
    )
    source_work_authority_rows = build_source_work_authority_rows(
        authority_rows=authority_rows,
        source_family_rows=source_family_output_rows,
        crosswalk_rows=crosswalk_rows,
    )
    source_work_authority_audit_rows = build_source_work_authority_audit_rows(source_work_authority_rows)
    source_work_to_bibtex_reconciliation_rows = build_source_work_to_bibtex_reconciliation_rows(
        source_work_authority_rows=source_work_authority_rows,
        authority_rows=authority_rows,
        candidate_rows=candidate_rows,
    )
    bibtex_field_quality_audit_rows = build_bibtex_field_quality_audit_rows(
        authority_rows=authority_rows,
        source_work_authority_rows=source_work_authority_rows,
    )
    bibtex_field_quality_audit_history_rows = build_bibtex_field_quality_audit_history_rows(
        raw_audit_rows=raw_bibtex_field_quality_audit_rows,
        active_audit_rows=bibtex_field_quality_audit_rows,
    )
    source_work_locator_rows = build_source_work_locator_rows(crosswalk_rows, source_work_authority_rows)
    raw_reference_crosswalk_audit_rows = build_raw_reference_crosswalk_audit_rows(
        crosswalk_rows=crosswalk_rows,
        source_work_authority_rows=source_work_authority_rows,
        family_by_id=family_by_id,
    )
    bibtex_consistency_report = build_bibtex_consistency_report(
        authority_rows=authority_rows,
        active_audit_rows=bibtex_field_quality_audit_rows,
        audit_history_rows=bibtex_field_quality_audit_history_rows,
        reconciliation_rows=source_work_to_bibtex_reconciliation_rows,
    )
    authority_bib_entries = [row_to_bibtex_entry(row) for row in authority_rows]
    candidate_bib_entries = [row_to_bibtex_entry(row) for row in candidate_rows]
    write_bibtex(output_dir / "bibliography_authority.bib", authority_bib_entries)
    write_bibtex(output_dir / "bibliography_candidates.bib", candidate_bib_entries)
    write_tsv(output_dir / "bibtex_authority.tsv", authority_rows + candidate_rows, AUTHORITY_FIELDS)
    write_tsv(seed_path, build_seed_output_rows(seed_rows, authority_rows), SEED_FIELDS)
    write_tsv(output_dir / "source_family_authority.tsv", source_family_output_rows, SOURCE_FAMILY_FIELDS)
    write_tsv(output_dir / "source_work_authority.tsv", source_work_authority_rows, SOURCE_WORK_AUTHORITY_FIELDS)
    write_tsv(output_dir / "source_work_authority_audit.tsv", source_work_authority_audit_rows, SOURCE_WORK_AUTHORITY_AUDIT_FIELDS)
    write_tsv(output_dir / "source_work_to_bibtex_reconciliation.tsv", source_work_to_bibtex_reconciliation_rows, SOURCE_WORK_TO_BIBTEX_RECONCILIATION_FIELDS)
    write_tsv(output_dir / "authority_key_normalization.tsv", AUTHORITY_KEY_NORMALIZATION_ROWS, AUTHORITY_KEY_NORMALIZATION_FIELDS)
    write_tsv(output_dir / "bibtex_field_quality_audit.tsv", bibtex_field_quality_audit_rows, BIBTEX_FIELD_QUALITY_AUDIT_FIELDS)
    write_tsv(
        output_dir / "bibtex_field_quality_audit_history.tsv",
        bibtex_field_quality_audit_history_rows,
        BIBTEX_FIELD_QUALITY_AUDIT_HISTORY_FIELDS,
    )
    write_tsv(output_dir / "source_work_locator_systems.tsv", source_work_locator_rows, SOURCE_WORK_LOCATOR_SYSTEM_FIELDS)
    write_tsv(output_dir / "raw_reference_to_bibtex.tsv", crosswalk_rows, CROSSWALK_FIELDS)
    write_tsv(output_dir / "raw_reference_crosswalk_audit.tsv", raw_reference_crosswalk_audit_rows, RAW_REFERENCE_CROSSWALK_AUDIT_FIELDS)
    write_tsv(output_dir / "acronym_resolution_status.tsv", acronym_status_rows, ACRONYM_STATUS_FIELDS)
    write_tsv(output_dir / "acronym_manual_review_packet.tsv", manual_review_packet_rows, MANUAL_REVIEW_PACKET_FIELDS)
    write_tsv(output_dir / "remaining_acronym_worklist.tsv", remaining_worklist_rows, REMAINING_ACRONYM_WORKLIST_FIELDS)
    write_tsv(output_dir / "remaining_acronym_evidence.tsv", remaining_acronym_evidence_rows, REMAINING_ACRONYM_EVIDENCE_FIELDS)
    write_tsv(output_dir / "final_acronym_resolution_sprint.tsv", final_acronym_resolution_sprint_rows, FINAL_ACRONYM_RESOLUTION_SPRINT_FIELDS)
    write_tsv(output_dir / "final_acronym_local_file_hits.tsv", final_acronym_local_file_hit_rows, FINAL_ACRONYM_LOCAL_FILE_HITS_FIELDS)
    write_tsv(output_dir / "final_acronym_web_searches.tsv", final_acronym_web_search_rows, FINAL_ACRONYM_WEB_SEARCHES_FIELDS)
    write_tsv(output_dir / "frasch_abbreviation_list_review.tsv", FRASCH_ABBREVIATION_LIST_REVIEW_ROWS, FRASCH_ABBREVIATION_LIST_REVIEW_FIELDS)
    write_tsv(output_dir / "bibtex_authority_evidence.tsv", evidence_rows, EVIDENCE_FIELDS)
    write_tsv(output_dir / "candidate_stub_review.tsv", candidate_stub_review_rows, CANDIDATE_STUB_REVIEW_FIELDS)
    write_tsv(output_dir / "ippa_occurrence_contexts.tsv", ippa_review["occurrence_rows"], IPPA_OCCURRENCE_CONTEXT_FIELDS)
    write_tsv(output_dir / "ippa_ppa_comparison.tsv", ippa_review["comparison_rows"], IPPA_PPA_COMPARISON_FIELDS)
    write_tsv(output_dir / "ippa_local_context_search.tsv", ippa_review["local_context_rows"], IPPA_LOCAL_CONTEXT_SEARCH_FIELDS)
    write_tsv(
        output_dir / "ippa_frasch_abbrev_neighbourhood.tsv",
        ippa_review["frasch_neighbourhood_rows"],
        IPPA_FRASCH_ABBREV_NEIGHBOURHOOD_FIELDS,
    )
    write_tsv(output_dir / "ippa_record_review.tsv", ippa_review["record_review_rows"], IPPA_RECORD_REVIEW_FIELDS)
    write_tsv(output_dir / "ippa_targeted_ocr_notes.tsv", ippa_review["targeted_ocr_rows"], IPPA_TARGETED_OCR_NOTES_FIELDS)
    write_tsv(output_dir / "ippa_resolution_decision.tsv", [ippa_review["decision_row"]], IPPA_RESOLUTION_DECISION_FIELDS)
    write_tsv(output_dir / "unresolved_acronym_dossier.tsv", unresolved_acronym_dossier_rows, UNRESOLVED_ACRONYM_DOSSIER_FIELDS)
    (output_dir / "bibtex_consistency_report.json").write_text(
        json.dumps(bibtex_consistency_report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    unresolved_rows.sort(key=lambda row: int(row["occurrence_count"] or 0), reverse=True)
    write_tsv(output_dir / "high_frequency_unresolved.tsv", unresolved_rows, HIGH_FREQUENCY_FIELDS)
    resolution_plan_rows = build_resolution_plan_rows(family_rows, family_resolution, members_by_family)
    write_tsv(output_dir / "high_frequency_resolution_plan.tsv", resolution_plan_rows, RESOLUTION_PLAN_FIELDS)

    duplicate_local_files_collapsed_count = sum(max(int(row.get("duplicate_count", "1") or 1) - 1, 0) for row in local_manifest_rows)
    long_bibtex_evidence_fields_count = sum(
        1
        for entry in authority_bib_entries
        for value in entry["fields"].values()
        if len(value) > MAX_BIBTEX_EVIDENCE_LENGTH and entry["entry_type"] != "misc"
    )
    high_frequency_reviewed_count = sum(1 for row in resolution_plan_rows if row["resolution_status"] != "unresolved")
    high_frequency_still_unresolved_count = sum(1 for row in resolution_plan_rows if row["resolution_status"] == "unresolved")
    sorted_resolutions = sorted(
        family_rows,
        key=lambda row: int(row.get("occurrence_count", "0") or "0"),
        reverse=True,
    )

    def top_families(statuses: set[str], *, provisional_only: bool = False) -> list[dict]:
        rows = []
        for family_row in sorted_resolutions:
            resolution = family_resolution[family_row["family_id"]]
            if resolution["resolution_status"] not in statuses:
                continue
            if provisional_only and resolution.get("needs_human_review") != "true":
                continue
            rows.append(
                {
                    "family_id": family_row["family_id"],
                    "family_label": family_row["family_label"],
                    "occurrence_count": int(family_row.get("occurrence_count", "0") or "0"),
                }
            )
            if len(rows) == 10:
                break
        return rows

    priority_acronym_rows = [row for row in acronym_status_rows if row["acronym"] in PRIORITY_ACRONYMS]
    ocr_success_labels = {
        row.get("source_file_label", "")
        for row in ocr_manifest_rows
        if row.get("extraction_status") == "success" and row.get("source_file_label")
    }
    confirmed_after_ocr = [
        row["acronym"]
        for row in priority_acronym_rows
        if row["resolution_status"] == "confirmed_expansion" and row.get("best_evidence_source", "") in ocr_success_labels
    ]
    still_source_family_only = [row["acronym"] for row in priority_acronym_rows if row["resolution_status"] == "source_family_only"]
    still_unresolved = [
        row["acronym"]
        for row in priority_acronym_rows
        if row["resolution_status"] in {"unresolved", "unresolved_after_targeted_search", "unresolved_after_exhaustive_search"}
    ]
    remaining_rows = [row for row in acronym_status_rows if row["acronym"] in REMAINING_ACRONYMS]
    confirmed_acronym_expansions = [
        row["acronym"] for row in priority_acronym_rows if row["resolution_status"] == "confirmed_expansion"
    ]
    probable_acronym_expansions = [
        row["acronym"] for row in priority_acronym_rows if row["resolution_status"] == "probable_expansion"
    ]
    alias_or_variant_families = [
        row["acronym"] for row in priority_acronym_rows if row["resolution_status"] == "alias_or_variant_of_PPA"
    ]
    internal_locator_systems = [
        row["acronym"] for row in priority_acronym_rows if row["resolution_status"] in {"internal_locator", "internal_locator_system"}
    ]
    probable_locator_systems = [
        row["acronym"] for row in priority_acronym_rows if row["resolution_status"] == "probable_locator_system"
    ]
    probable_private_locator_systems = [
        row["acronym"] for row in priority_acronym_rows if row["resolution_status"] == "probable_private_luce_locator_system"
    ]
    not_acronyms = [row["acronym"] for row in priority_acronym_rows if row["resolution_status"] == "not_an_acronym"]
    unresolved_after_exhaustive_search = [
        row["acronym"]
        for row in priority_acronym_rows
        if row["resolution_status"] in {"genuinely_unresolved_after_occurrence_level_review", "unresolved_after_exhaustive_search"}
    ]
    manual_seeds_confirmed_by_documentation_count = sum(
        1
        for acronym, seed_row in manual_acronym_seeds.items()
        if any(
            row["acronym"] == acronym
            and row["best_evidence_id"]
            and not row["best_evidence_id"].startswith("manual-seed:")
            and normalized_expansion_match(row.get("current_expansion", ""), seed_row.get("expansion", ""))
            for row in acronym_status_rows
        )
    )
    report = {
        "authority_entry_count": len(authority_rows),
        "candidate_entry_count": len(candidate_rows),
        "total_family_count": len(family_rows),
        "machine_stub_count": sum(1 for row in candidate_rows if row["authority_status"] == "machine_stub"),
        "suppressed_locator_stub_count": sum(
            1
            for resolution in family_resolution.values()
            if resolution["resolution_status"] in {"alias_resolved", "source_family_resolved", "series_level_resolved", "confirmed_work"}
        ),
        "unresolved_family_count": sum(1 for resolution in family_resolution.values() if resolution["resolution_status"] == "unresolved"),
        "alias_resolved_family_count": sum(1 for resolution in family_resolution.values() if resolution["resolution_status"] == "alias_resolved"),
        "source_family_resolved_count": sum(
            1 for resolution in family_resolution.values() if resolution["resolution_status"] == "source_family_resolved"
        ),
        "series_level_resolved_count": sum(
            1 for resolution in family_resolution.values() if resolution["resolution_status"] == "series_level_resolved"
        ),
        "work_level_resolved_count": sum(
            1 for resolution in family_resolution.values() if resolution["resolution_status"] in {"confirmed_work", "provisional_work"}
        ),
        "confirmed_work_count": sum(1 for resolution in family_resolution.values() if resolution["resolution_status"] == "confirmed_work"),
        "provisional_work_count": sum(
            1 for resolution in family_resolution.values() if resolution["resolution_status"] == "provisional_work"
        ),
        "needs_human_review_count": sum(
            1 for resolution in family_resolution.values() if resolution["resolution_status"] == "needs_human_review"
        ),
        "confirmed_external_bibtex_count": sum(1 for row in authority_rows if row["authority_status"] == "confirmed_external_bibtex"),
        "confirmed_local_source_count": sum(1 for row in authority_rows if row["authority_status"] == "confirmed_local_source"),
        "provisional_local_source_count": sum(1 for row in authority_rows if row["authority_status"] == "provisional_local_source"),
        "frasch_reference_count": len(frasch_rows_all),
        "frasch_usable_reference_count": len(frasch_rows),
        "frasch_excluded_body_text_count": sum(1 for row in frasch_rows_all if row.get("detected_entry_type") == "body_text"),
        "frasch_matched_count": sum(1 for row in authority_rows if row["source_of_authority"].startswith("frasch")),
        "luce_candidate_count": sum(1 for row in local_candidate_rows if "luce" in row.get("original_path", "").casefold()),
        "local_file_count": len({row.get("source_file_id", row.get("sha256", "")) for row in local_manifest_rows}),
        "duplicate_local_files_collapsed_count": duplicate_local_files_collapsed_count,
        "long_bibtex_evidence_fields_count": long_bibtex_evidence_fields_count,
        "high_frequency_reviewed_count": high_frequency_reviewed_count,
        "high_frequency_still_unresolved_count": high_frequency_still_unresolved_count,
        "priority_acronym_count": len(PRIORITY_ACRONYMS),
        "confirmed_acronym_expansion_count": len(confirmed_acronym_expansions),
        "confirmed_acronym_expansions": confirmed_acronym_expansions,
        "probable_acronym_expansion_count": len(probable_acronym_expansions),
        "probable_acronym_expansions": probable_acronym_expansions,
        "alias_or_variant_family_count": len(alias_or_variant_families),
        "alias_or_variant_families": alias_or_variant_families,
        "internal_locator_system_count": len(internal_locator_systems),
        "internal_locator_systems": internal_locator_systems,
        "probable_locator_system_count": len(probable_locator_systems),
        "probable_locator_systems": probable_locator_systems,
        "probable_private_locator_system_count": len(probable_private_locator_systems),
        "probable_private_locator_systems": probable_private_locator_systems,
        "not_acronym_count": len(not_acronyms),
        "not_acronyms": not_acronyms,
        "unresolved_after_exhaustive_search_count": len(unresolved_after_exhaustive_search),
        "unresolved_after_exhaustive_search": unresolved_after_exhaustive_search,
        "source_family_only_count": sum(1 for row in priority_acronym_rows if row["resolution_status"] == "source_family_only"),
        "contextual_usage_only_count": sum(1 for row in priority_acronym_rows if row["resolution_status"] == "contextual_usage_only"),
        "unresolved_acronym_count": sum(1 for row in priority_acronym_rows if row["resolution_status"] == "unresolved"),
        "internal_locator_count": sum(1 for row in priority_acronym_rows if row["resolution_status"] == "internal_locator"),
        "documentation_files_searched_count": acronym_report.get("documentation_files_searched_count", 0),
        "frasch_stadt_staat_files_searched_count": acronym_report.get("frasch_stadt_staat_files_searched_count", 0),
        "fratsch_stadt_staat_files_searched_count": acronym_report.get("fratsch_stadt_staat_files_searched_count", 0),
        "bagan_database_context_matches": acronym_report.get("bagan_database_context_matches", 0),
        "ocr_needed_count": acronym_report.get("ocr_needed_count", 0),
        "manual_acronym_seed_count": len(manual_acronym_seeds),
        "manual_seeds_confirmed_by_documentation_count": manual_seeds_confirmed_by_documentation_count,
        "ocr_files_attempted": ocr_report.get("files_attempted", len(ocr_manifest_rows)),
        "ocr_files_successful": ocr_report.get("files_successful", sum(1 for row in ocr_manifest_rows if row.get("extraction_status") == "success")),
        "ocr_files_failed": ocr_report.get("files_failed", sum(1 for row in ocr_manifest_rows if row.get("extraction_status") != "success")),
        "abbreviation_sections_from_ocr_count": acronym_report.get(
            "abbreviation_sections_from_ocr_count",
            sum(1 for row in ocr_index_rows if row.get("matched_heading")),
        ),
        "priority_acronyms_confirmed_after_ocr": len(confirmed_after_ocr),
        "priority_acronyms_confirmed_after_ocr_list": confirmed_after_ocr,
        "priority_acronyms_still_source_family_only": len(still_source_family_only),
        "priority_acronyms_still_source_family_only_list": still_source_family_only,
        "priority_acronyms_still_unresolved": len(still_unresolved),
        "priority_acronyms_still_unresolved_list": still_unresolved,
        "manual_review_packet_rows": len(manual_review_packet_rows),
        "remaining_acronym_count": len(REMAINING_ACRONYMS),
        "remaining_acronyms_confirmed_count": sum(1 for row in remaining_rows if row["resolution_status"] == "confirmed_expansion"),
        "remaining_acronyms_probable_count": sum(1 for row in remaining_rows if row["resolution_status"] == "probable_expansion"),
        "remaining_acronyms_probable_locator_system_count": sum(
            1 for row in remaining_rows if row["resolution_status"] == "probable_locator_system"
        ),
        "remaining_acronyms_probable_private_luce_locator_system_count": sum(
            1 for row in remaining_rows if row["resolution_status"] == "probable_private_luce_locator_system"
        ),
        "remaining_acronyms_unresolved_after_targeted_search_count": sum(
            1 for row in remaining_rows if row["resolution_status"] == "unresolved_after_targeted_search"
        ),
        "remaining_acronyms_unresolved_after_exhaustive_search_count": sum(
            1 for row in remaining_rows if row["resolution_status"] == "unresolved_after_exhaustive_search"
        ),
        "final_acronym_resolution_sprint_count": len(final_acronym_resolution_sprint_rows),
        "final_acronym_local_file_hit_count": len(final_acronym_local_file_hit_rows),
        "final_acronym_web_search_count": len(final_acronym_web_search_rows),
        "frasch_abbreviation_list_review_count": len(FRASCH_ABBREVIATION_LIST_REVIEW_ROWS),
        "final_unresolved_acronym_dossier_count": len(unresolved_acronym_dossier_rows),
        "ippa_occurrence_count": len(ippa_review["occurrence_rows"]),
        "ippa_record_review_count": len(ippa_review["record_review_rows"]),
        "ippa_local_context_search_count": len(ippa_review["local_context_rows"]),
        "ippa_web_query_count": int(ippa_review["decision_row"].get("web_queries_reviewed", "0") or "0"),
        "ippa_final_decision": ippa_review["decision_row"].get("decision", ""),
        "source_work_authority_count": len(source_work_authority_rows),
        "source_work_authority_audit_count": len(source_work_authority_audit_rows),
        "source_work_open_duplicate_issue_count": sum(1 for row in source_work_authority_audit_rows if row.get("open_issue") == "true"),
        "source_work_normalized_overlap_count": sum(1 for row in source_work_authority_audit_rows if row.get("status") == "reviewed_normalized"),
        "source_work_to_bibtex_reconciliation_count": len(source_work_to_bibtex_reconciliation_rows),
        "source_work_locator_system_count": len(source_work_locator_rows),
        "raw_reference_crosswalk_audit_count": len(raw_reference_crosswalk_audit_rows),
        "open_raw_crosswalk_issue_count": sum(1 for row in raw_reference_crosswalk_audit_rows if row.get("status", "open") == "open"),
        "high_severity_crosswalk_issue_count": sum(1 for row in raw_reference_crosswalk_audit_rows if row.get("severity") == "high"),
        "medium_severity_crosswalk_issue_count": sum(1 for row in raw_reference_crosswalk_audit_rows if row.get("severity") == "medium"),
        "low_severity_crosswalk_issue_count": sum(1 for row in raw_reference_crosswalk_audit_rows if row.get("severity") == "low"),
        "auto_fixable_crosswalk_issue_count": sum(1 for row in raw_reference_crosswalk_audit_rows if row.get("auto_fixable") == "true"),
        "human_review_crosswalk_issue_count": sum(1 for row in raw_reference_crosswalk_audit_rows if row.get("human_review_required") == "true"),
        "candidate_stub_review_count": len(candidate_stub_review_rows),
        "candidate_stubs_promoted_count": sum(1 for row in candidate_stub_review_rows if row["review_decision"] == "promote"),
        "candidate_stubs_suppressed_count": sum(1 for row in candidate_stub_review_rows if row["review_decision"] == "suppress"),
        "candidate_stubs_retained_count": sum(1 for row in candidate_stub_review_rows if row["review_decision"] == "retain"),
        "bibtex_field_quality_issue_count": len(bibtex_field_quality_audit_rows),
        "open_bibtex_field_quality_issue_count": len(bibtex_field_quality_audit_rows),
        "bad_ocr_bibtex_field_count": sum(1 for row in bibtex_field_quality_audit_rows if row.get("issue_type") == "ocr_like_evidence_fragment"),
        "authority_key_normalization_count": len(AUTHORITY_KEY_NORMALIZATION_ROWS),
        "bibtex_entries_emitted_count": len(authority_rows),
        "bibtex_entries_suppressed_locator_count": sum(
            1 for row in source_work_to_bibtex_reconciliation_rows if row.get("bibtex_status") == "suppressed_locator_system"
        ),
        "candidate_entries_promoted_to_authority_count": sum(
            1 for row in candidate_stub_review_rows if row.get("review_decision") == "promote"
        ),
        "pl_locator_semantics_checked": True,
        "iob_relationship_checked": True,
        "unresolved_priority_acronyms": unresolved_after_exhaustive_search,
        "top_unresolved_families": top_families({"unresolved"}),
        "top_provisional_source_families": top_families({"source_family_resolved", "series_level_resolved"}, provisional_only=True),
        "top_needs_human_review_families": top_families({"needs_human_review"}),
    }
    (output_dir / "bibtex_authority_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Build bibliography authority files from triage, external BibTeX, and local evidence.")
    parser.add_argument("--reference-families", type=Path, default=Path("data/working/bibliography/reference_families.tsv"))
    parser.add_argument("--reference-members", type=Path, default=Path("data/working/bibliography/reference_family_members.tsv"))
    parser.add_argument("--work-candidates", type=Path, default=Path("data/working/bibliography/bibliographic_work_candidates.tsv"))
    parser.add_argument("--seed-path", type=Path, default=Path("data/working/bibliography/bibtex_authority/source_abbreviation_seeds.tsv"))
    parser.add_argument("--external-entries", type=Path, default=Path("data/working/bibliography/external_bibtex/asia_2_entries.tsv"))
    parser.add_argument("--frasch-references", type=Path, default=Path("data/working/bibliography/local_sources/frasch_reference_entries.tsv"))
    parser.add_argument("--local-candidates", type=Path, default=Path("data/working/bibliography/local_sources/high_priority_local_candidates.tsv"))
    parser.add_argument("--local-manifest", type=Path, default=Path("data/working/bibliography/local_sources/local_file_manifest.tsv"))
    parser.add_argument("--acronym-candidates", type=Path, default=Path("data/working/bibliography/local_sources/acronym_definition_candidates.tsv"))
    parser.add_argument("--acronym-report", type=Path, default=Path("data/working/bibliography/local_sources/acronym_definition_report.json"))
    parser.add_argument("--manual-acronym-seeds", type=Path, default=Path("data/working/bibliography/bibtex_authority/manual_acronym_seeds.tsv"))
    parser.add_argument("--ocr-queue", type=Path, default=Path("data/working/bibliography/local_sources/ocr_priority_queue.tsv"))
    parser.add_argument("--ocr-manifest", type=Path, default=Path("data/working/bibliography/local_sources/ocr_outputs/ocr_manifest.tsv"))
    parser.add_argument("--ocr-index", type=Path, default=Path("data/working/bibliography/local_sources/ocr_outputs/ocr_text_index.tsv"))
    parser.add_argument("--ocr-report", type=Path, default=Path("data/working/bibliography/local_sources/ocr_outputs/ocr_report.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/working/bibliography/bibtex_authority"))
    args = parser.parse_args()

    report = build_authority(
        reference_families_path=args.reference_families,
        reference_members_path=args.reference_members,
        work_candidates_path=args.work_candidates,
        seed_path=args.seed_path,
        external_entries_path=args.external_entries,
        frasch_references_path=args.frasch_references,
        local_candidates_path=args.local_candidates,
        local_manifest_path=args.local_manifest,
        acronym_candidates_path=args.acronym_candidates,
        acronym_report_path=args.acronym_report,
        manual_acronym_seeds_path=args.manual_acronym_seeds,
        ocr_queue_path=args.ocr_queue,
        ocr_manifest_path=args.ocr_manifest,
        ocr_index_path=args.ocr_index,
        ocr_report_path=args.ocr_report,
        output_dir=args.output_dir,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
