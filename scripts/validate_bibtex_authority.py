from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

from build_bibtex_authority import (
    FINAL_SPRINT_ACRONYMS,
    REMAINING_ACRONYMS,
    RESOLUTION_LEVELS,
    RESOLUTION_STATUSES,
    looks_like_ocr_garbage,
    normalized_expansion_match,
    normalize_script_value,
)
from bibtex_common import duplicate_keys, parse_bibtex_text
from corpus_common import read_tsv
from extract_bibliography_acronyms import (
    GENERIC_BIBLIOGRAPHY_HEADINGS,
    MAX_STRONG_DEFINITION_QUOTE_LENGTH,
    PRIORITY_ACRONYMS,
    STRONG_DEFINITION_EVIDENCE_TYPES,
    line_has_definition_pattern,
)


ABSOLUTE_PATH_PATTERN = re.compile(r"(^/(?:Users|home|var|private|tmp|opt|Volumes)\b|^[A-Za-z]:\\\\)")
GENERIC_KEY_PATTERN = re.compile(r"^(?:work|sourceunresolved)\d+$", flags=re.IGNORECASE)
MAX_BIBTEX_FIELD_LENGTH = 280
MAX_MATCHED_LOCAL_REFERENCE_LENGTH = 140
PLACEHOLDER_EXPANSION_PATTERN = re.compile(
    r"\b(source family|catalogue family|publication family|series family|source family attested|unexpanded)\b",
    re.IGNORECASE,
)
VALID_AUTHORITY_LEVELS = {
    "series",
    "periodical",
    "source_work",
    "source_catalogue",
    "corpus_source",
    "locator_collection",
    "manuscript_collection",
    "archival_notebook",
    "article",
    "book",
    "candidate_work",
}


def has_absolute_path(value: str) -> bool:
    return bool(value and ABSOLUTE_PATH_PATTERN.search(value))


def has_list_date_false_positive(value: str) -> bool:
    compact = (value or "").strip().casefold()
    return "date" in compact and ("cs" in compact or bool(re.search(r"\b\d{3,4}\b", compact)))


def has_obi_remark_false_positive(value: str) -> bool:
    compact = (value or "").strip().casefold()
    return "spelling of inscription" in compact or compact.startswith("remark")


def has_lowercase_or_false_positive(value: str) -> bool:
    compact = (value or "").strip()
    return compact.casefold() == "or" or compact.startswith("or:")


def candidate_supports_strong_expansion(candidate_row: dict | None) -> bool:
    if not candidate_row:
        return False
    if candidate_row.get("definition_quality") == "manual_seed":
        return True
    if candidate_row.get("evidence_type") not in STRONG_DEFINITION_EVIDENCE_TYPES:
        return False
    return candidate_row.get("definition_quality") in {"explicit", "strong"}


def has_explicit_definition_pattern(text: str) -> bool:
    return any(line_has_definition_pattern((line or "").strip(), acronym) for line in text.splitlines() for acronym in PRIORITY_ACRONYMS)


def looks_like_irrelevant_tibetan_material(text: str) -> bool:
    lowered = (text or "").casefold()
    if not any(token in lowered for token in ("tibet", "tibetan", "richardson")):
        return False
    return not any(token in lowered for token in ("burma", "burmese", "bagan", "pagan", "obi"))


def validate_bibtex_authority(
    *,
    authority_bib_path: Path,
    candidates_bib_path: Path,
    authority_tsv_path: Path,
    crosswalk_path: Path,
    families_path: Path,
    external_entries_path: Path | None = None,
    seed_path: Path | None = None,
    high_frequency_path: Path | None = None,
    evidence_path: Path | None = None,
    resolution_plan_path: Path | None = None,
    source_family_path: Path | None = None,
    report_path: Path | None = None,
    frasch_references_path: Path | None = None,
    local_manifest_path: Path | None = None,
    acronym_status_path: Path | None = None,
    acronym_candidates_path: Path | None = None,
    acronym_report_path: Path | None = None,
    manual_acronym_seeds_path: Path | None = None,
    ocr_queue_path: Path | None = None,
    ocr_manifest_path: Path | None = None,
    ocr_index_path: Path | None = None,
    documentation_sections_path: Path | None = None,
    manual_review_packet_path: Path | None = None,
    remaining_acronym_worklist_path: Path | None = None,
    remaining_acronym_evidence_path: Path | None = None,
    source_work_locator_systems_path: Path | None = None,
    final_acronym_resolution_sprint_path: Path | None = None,
    final_acronym_local_file_hits_path: Path | None = None,
    final_acronym_web_searches_path: Path | None = None,
    frasch_abbreviation_list_review_path: Path | None = None,
    unresolved_acronym_dossier_path: Path | None = None,
    source_work_authority_path: Path | None = None,
    source_work_authority_audit_path: Path | None = None,
    source_work_to_bibtex_reconciliation_path: Path | None = None,
    bibtex_field_quality_audit_path: Path | None = None,
    authority_key_normalization_path: Path | None = None,
    raw_reference_crosswalk_audit_path: Path | None = None,
    candidate_stub_review_path: Path | None = None,
    ippa_occurrence_contexts_path: Path | None = None,
    ippa_ppa_comparison_path: Path | None = None,
    ippa_local_context_search_path: Path | None = None,
    ippa_frasch_abbrev_neighbourhood_path: Path | None = None,
    ippa_record_review_path: Path | None = None,
    ippa_targeted_ocr_notes_path: Path | None = None,
    ippa_resolution_decision_path: Path | None = None,
    reference_occurrences_path: Path | None = None,
) -> dict:
    errors: list[str] = []
    authority_entries, authority_warnings = parse_bibtex_text(authority_bib_path.read_text(encoding="utf-8"), source_label=authority_bib_path.name)
    candidate_entries, candidate_warnings = parse_bibtex_text(candidates_bib_path.read_text(encoding="utf-8"), source_label=candidates_bib_path.name)
    authority_rows = read_tsv(authority_tsv_path)
    crosswalk_rows = read_tsv(crosswalk_path)
    family_rows = read_tsv(families_path)
    external_rows = read_tsv(external_entries_path) if external_entries_path and external_entries_path.exists() else []
    seed_rows = read_tsv(seed_path) if seed_path and seed_path.exists() else []
    high_frequency_rows = read_tsv(high_frequency_path) if high_frequency_path and high_frequency_path.exists() else []
    evidence_rows = read_tsv(evidence_path) if evidence_path and evidence_path.exists() else []
    resolution_plan_rows = read_tsv(resolution_plan_path) if resolution_plan_path and resolution_plan_path.exists() else []
    source_family_rows = read_tsv(source_family_path) if source_family_path and source_family_path.exists() else []
    frasch_rows = read_tsv(frasch_references_path) if frasch_references_path and frasch_references_path.exists() else []
    manifest_rows = read_tsv(local_manifest_path) if local_manifest_path and local_manifest_path.exists() else []
    acronym_status_rows = read_tsv(acronym_status_path) if acronym_status_path and acronym_status_path.exists() else []
    acronym_candidate_rows = read_tsv(acronym_candidates_path) if acronym_candidates_path and acronym_candidates_path.exists() else []
    manual_seed_rows = read_tsv(manual_acronym_seeds_path) if manual_acronym_seeds_path and manual_acronym_seeds_path.exists() else []
    ocr_queue_rows = read_tsv(ocr_queue_path) if ocr_queue_path and ocr_queue_path.exists() else []
    ocr_manifest_rows = read_tsv(ocr_manifest_path) if ocr_manifest_path and ocr_manifest_path.exists() else []
    ocr_index_rows = read_tsv(ocr_index_path) if ocr_index_path and ocr_index_path.exists() else []
    documentation_section_rows = read_tsv(documentation_sections_path) if documentation_sections_path and documentation_sections_path.exists() else []
    manual_review_packet_rows = read_tsv(manual_review_packet_path) if manual_review_packet_path and manual_review_packet_path.exists() else []
    remaining_acronym_worklist_rows = read_tsv(remaining_acronym_worklist_path) if remaining_acronym_worklist_path and remaining_acronym_worklist_path.exists() else []
    remaining_acronym_evidence_rows = read_tsv(remaining_acronym_evidence_path) if remaining_acronym_evidence_path and remaining_acronym_evidence_path.exists() else []
    source_work_locator_rows = read_tsv(source_work_locator_systems_path) if source_work_locator_systems_path and source_work_locator_systems_path.exists() else []
    final_acronym_resolution_sprint_rows = read_tsv(final_acronym_resolution_sprint_path) if final_acronym_resolution_sprint_path and final_acronym_resolution_sprint_path.exists() else []
    final_acronym_local_file_hit_rows = read_tsv(final_acronym_local_file_hits_path) if final_acronym_local_file_hits_path and final_acronym_local_file_hits_path.exists() else []
    final_acronym_web_search_rows = read_tsv(final_acronym_web_searches_path) if final_acronym_web_searches_path and final_acronym_web_searches_path.exists() else []
    frasch_abbreviation_list_review_rows = read_tsv(frasch_abbreviation_list_review_path) if frasch_abbreviation_list_review_path and frasch_abbreviation_list_review_path.exists() else []
    unresolved_acronym_dossier_rows = read_tsv(unresolved_acronym_dossier_path) if unresolved_acronym_dossier_path and unresolved_acronym_dossier_path.exists() else []
    source_work_authority_rows = read_tsv(source_work_authority_path) if source_work_authority_path and source_work_authority_path.exists() else []
    source_work_authority_audit_rows = (
        read_tsv(source_work_authority_audit_path) if source_work_authority_audit_path and source_work_authority_audit_path.exists() else []
    )
    source_work_to_bibtex_reconciliation_rows = (
        read_tsv(source_work_to_bibtex_reconciliation_path)
        if source_work_to_bibtex_reconciliation_path and source_work_to_bibtex_reconciliation_path.exists()
        else []
    )
    bibtex_field_quality_audit_rows = (
        read_tsv(bibtex_field_quality_audit_path) if bibtex_field_quality_audit_path and bibtex_field_quality_audit_path.exists() else []
    )
    authority_key_normalization_rows = (
        read_tsv(authority_key_normalization_path) if authority_key_normalization_path and authority_key_normalization_path.exists() else []
    )
    raw_reference_crosswalk_audit_rows = read_tsv(raw_reference_crosswalk_audit_path) if raw_reference_crosswalk_audit_path and raw_reference_crosswalk_audit_path.exists() else []
    candidate_stub_review_rows = read_tsv(candidate_stub_review_path) if candidate_stub_review_path and candidate_stub_review_path.exists() else []
    ippa_occurrence_context_rows = read_tsv(ippa_occurrence_contexts_path) if ippa_occurrence_contexts_path and ippa_occurrence_contexts_path.exists() else []
    ippa_ppa_comparison_rows = read_tsv(ippa_ppa_comparison_path) if ippa_ppa_comparison_path and ippa_ppa_comparison_path.exists() else []
    ippa_local_context_search_rows = read_tsv(ippa_local_context_search_path) if ippa_local_context_search_path and ippa_local_context_search_path.exists() else []
    ippa_frasch_abbrev_neighbourhood_rows = (
        read_tsv(ippa_frasch_abbrev_neighbourhood_path)
        if ippa_frasch_abbrev_neighbourhood_path and ippa_frasch_abbrev_neighbourhood_path.exists()
        else []
    )
    ippa_record_review_rows = read_tsv(ippa_record_review_path) if ippa_record_review_path and ippa_record_review_path.exists() else []
    ippa_targeted_ocr_rows = read_tsv(ippa_targeted_ocr_notes_path) if ippa_targeted_ocr_notes_path and ippa_targeted_ocr_notes_path.exists() else []
    ippa_resolution_decision_rows = read_tsv(ippa_resolution_decision_path) if ippa_resolution_decision_path and ippa_resolution_decision_path.exists() else []
    reference_occurrence_rows = read_tsv(reference_occurrences_path) if reference_occurrences_path and reference_occurrences_path.exists() else []
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path and report_path.exists() else {}
    acronym_report = json.loads(acronym_report_path.read_text(encoding="utf-8")) if acronym_report_path and acronym_report_path.exists() else {}

    authority_keys = {entry["bibtex_key"] for entry in authority_entries}
    candidate_keys = {entry["bibtex_key"] for entry in candidate_entries}
    valid_keys = authority_keys | candidate_keys
    source_work_keys = {row.get("source_work_key", "") for row in source_work_authority_rows if row.get("source_work_key")}
    source_work_bibtex_by_key = {
        row.get("source_work_key", ""): row.get("bibtex_key", "")
        for row in source_work_authority_rows
        if row.get("source_work_key")
    }
    source_work_keys_with_bibtex = {row.get("bibtex_key", "") for row in source_work_authority_rows if row.get("bibtex_key")}
    reconciliation_by_work_key = {
        row.get("source_work_key", ""): row for row in source_work_to_bibtex_reconciliation_rows if row.get("source_work_key")
    }
    family_ids = {row["family_id"] for row in family_rows}
    source_family_ids = {row["source_family_id"] for row in source_family_rows if row.get("source_family_id")}
    external_keys = {row["bibtex_key"] for row in external_rows}
    frasch_ids = {row.get("frasch_ref_id", "") for row in frasch_rows if row.get("frasch_ref_id")}
    manifest_ids = {row.get("canonical_local_file_id", "") for row in manifest_rows if row.get("canonical_local_file_id")}
    evidence_by_key = {row.get("bibtex_key", ""): row for row in evidence_rows if row.get("bibtex_key")}
    evidence_by_source_family = {row.get("source_family_id", ""): row for row in evidence_rows if row.get("source_family_id")}
    acronym_status_by_acronym = {row.get("acronym", ""): row for row in acronym_status_rows if row.get("acronym")}
    acronym_candidate_by_id = {row.get("candidate_id", ""): row for row in acronym_candidate_rows if row.get("candidate_id")}
    manual_seed_by_acronym = {row.get("acronym", ""): row for row in manual_seed_rows if row.get("acronym")}
    remaining_evidence_by_acronym: dict[str, list[dict]] = {}
    for row in remaining_acronym_evidence_rows:
        remaining_evidence_by_acronym.setdefault(row.get("acronym", ""), []).append(row)
    final_sprint_by_acronym = {row.get("acronym", ""): row for row in final_acronym_resolution_sprint_rows if row.get("acronym")}
    ippa_decision_row = ippa_resolution_decision_rows[0] if ippa_resolution_decision_rows else {}

    duplicate_all = sorted(set(duplicate_keys(authority_entries) + duplicate_keys(candidate_entries) + list(authority_keys & candidate_keys)))
    if duplicate_all:
        errors.append(f"duplicate BibTeX keys detected: {', '.join(duplicate_all[:10])}")
    if authority_warnings:
        errors.append(f"authority BibTeX parse warnings: {authority_warnings[0]}")
    if candidate_warnings:
        errors.append(f"candidate BibTeX parse warnings: {candidate_warnings[0]}")
    for entry in authority_entries:
        if GENERIC_KEY_PATTERN.fullmatch(entry["bibtex_key"]):
            errors.append(f"authority BibTeX contains generic key {entry['bibtex_key']}")
        for field_name, value in entry["fields"].items():
            if len(value) > MAX_BIBTEX_FIELD_LENGTH:
                errors.append(f"authority BibTeX field {field_name} on {entry['bibtex_key']} exceeds {MAX_BIBTEX_FIELD_LENGTH} characters")
            if field_name == "matchedlocalreference" and len(value) > MAX_MATCHED_LOCAL_REFERENCE_LENGTH:
                errors.append(f"authority BibTeX matchedlocalreference on {entry['bibtex_key']} exceeds {MAX_MATCHED_LOCAL_REFERENCE_LENGTH} characters")
            if field_name in {"evidence", "matchedlocalreference"} and looks_like_ocr_garbage(value):
                errors.append(f"authority BibTeX field {field_name} on {entry['bibtex_key']} contains OCR-like garbage")
            if field_name == "script":
                normalized_script = normalize_script_value(value, fallback_title=entry["fields"].get("title", ""))
                if value != normalized_script:
                    errors.append(f"authority BibTeX script on {entry['bibtex_key']} must be normalized to {normalized_script}")

    for index, row in enumerate(crosswalk_rows, start=1):
        if (
            row["match_type"] != "no_match"
            and row["bibtex_key"]
            and row["bibtex_key"] not in valid_keys
            and row["bibtex_key"] not in source_work_keys_with_bibtex
        ):
            errors.append(f"raw_reference_to_bibtex[{index}] references missing bibtex_key {row['bibtex_key']}")
        if row["family_id"] not in family_ids:
            errors.append(f"raw_reference_to_bibtex[{index}] references unknown family_id {row['family_id']}")
        if source_family_rows and row.get("source_family_id") and row["source_family_id"] not in source_family_ids:
            errors.append(f"raw_reference_to_bibtex[{index}] references unknown source_family_id {row['source_family_id']}")
        if row.get("resolution_status") not in RESOLUTION_STATUSES:
            errors.append(f"raw_reference_to_bibtex[{index}] has invalid resolution_status {row.get('resolution_status')}")
        if row.get("resolution_level") not in RESOLUTION_LEVELS:
            errors.append(f"raw_reference_to_bibtex[{index}] has invalid resolution_level {row.get('resolution_level')}")
        if row.get("source_family_id") and row.get("bibtex_key") in candidate_keys:
            errors.append(f"raw_reference_to_bibtex[{index}] maps a resolved source family to machine-stub candidate {row['bibtex_key']}")
        if row.get("source_work_key") and row["source_work_key"] not in source_work_keys:
            errors.append(f"raw_reference_to_bibtex[{index}] references unknown source_work_key {row['source_work_key']}")
        if row.get("source_work_key") and source_work_bibtex_by_key.get(row["source_work_key"]) and row.get("bibtex_key") != source_work_bibtex_by_key[row["source_work_key"]]:
            errors.append(
                f"raw_reference_to_bibtex[{index}] should use bibtex_key {source_work_bibtex_by_key[row['source_work_key']]} for source_work_key {row['source_work_key']}"
            )
        if row.get("source_family_id") in {"sf-pl", "sf-iob", "sf-list", "sf-ppa", "sf-ippa", "sf-ub", "sf-mp", "sf-or", "sf-luce-d", "sf-luce-j"}:
            if not row.get("source_work_key"):
                errors.append(f"raw_reference_to_bibtex[{index}] is missing source_work_key for locator-aware source family {row['source_family_id']}")
            if not row.get("locator"):
                errors.append(f"raw_reference_to_bibtex[{index}] is missing locator for locator-aware source family {row['source_family_id']}")
        if row.get("source_family_id") == "sf-ippa":
            if not row.get("raw_reference_string", "").startswith("IPPA"):
                errors.append(f"raw_reference_to_bibtex[{index}] must preserve the raw IPPA string")
            if row.get("source_work_key") != "ppaCatalogue":
                errors.append(f"raw_reference_to_bibtex[{index}] must map IPPA rows to ppaCatalogue")
            if row.get("resolution_status") != "alias_or_variant_of_PPA":
                errors.append(f"raw_reference_to_bibtex[{index}] must classify IPPA rows as alias_or_variant_of_PPA")
        if row.get("source_family_id") in {"sf-mp", "sf-or", "sf-luce-d", "sf-luce-j"} and row.get("bibtex_key"):
            errors.append(f"raw_reference_to_bibtex[{index}] should not assign standalone bibtex_key to locator-only family {row['source_family_id']}")
        for value in row.values():
            if has_absolute_path(value):
                errors.append(f"raw_reference_to_bibtex[{index}] contains an absolute local path")
                break

    allowed_statuses = {
        "confirmed_external_bibtex",
        "confirmed_local_source",
        "provisional_local_source",
        "provisional_catalogue",
        "provisional_publication",
        "machine_stub",
        "needs_human_review",
    }
    for index, row in enumerate(authority_rows, start=1):
        if row["authority_status"] not in allowed_statuses:
            errors.append(f"bibtex_authority[{index}] has invalid authority_status {row['authority_status']}")
        if row["bibtex_key"] in authority_keys and GENERIC_KEY_PATTERN.fullmatch(row["bibtex_key"]):
            errors.append(f"bibtex_authority[{index}] uses generic authority key {row['bibtex_key']}")
        if row["matched_external_key"] and row["matched_external_key"] not in external_keys:
            errors.append(f"bibtex_authority[{index}] references missing matched_external_key {row['matched_external_key']}")
        if row["family_id"] and row["family_id"] not in family_ids:
            errors.append(f"bibtex_authority[{index}] references unknown family_id {row['family_id']}")
        if source_family_rows and row.get("source_family_id") and row["source_family_id"] not in source_family_ids:
            errors.append(f"bibtex_authority[{index}] references unknown source_family_id {row['source_family_id']}")
        if row.get("resolution_status") not in RESOLUTION_STATUSES:
            errors.append(f"bibtex_authority[{index}] has invalid resolution_status {row.get('resolution_status')}")
        if row.get("resolution_level") not in RESOLUTION_LEVELS:
            errors.append(f"bibtex_authority[{index}] has invalid resolution_level {row.get('resolution_level')}")
        if row["authority_status"] in {"machine_stub", "provisional_catalogue", "provisional_publication", "provisional_local_source", "needs_human_review"}:
            if not row["review_status"]:
                errors.append(f"bibtex_authority[{index}] is provisional but missing review_status")
            if not row["evidence"] and not row["notes"]:
                errors.append(f"bibtex_authority[{index}] is provisional but missing evidence or notes")
        if row["authority_status"] == "machine_stub" and row["bibtex_key"] in authority_keys:
            errors.append(f"bibtex_authority[{index}] contains machine_stub key {row['bibtex_key']} in authority bibliography")
        if row["authority_status"] == "confirmed_local_source":
            if not row.get("matched_local_source_id") or not row.get("matched_local_source_file"):
                errors.append(f"bibtex_authority[{index}] is confirmed_local_source but missing local evidence fields")
        if row["authority_status"] in {"confirmed_local_source", "provisional_local_source"}:
            if row["source_of_authority"] in {"frasch_bibliography", "frasch_word_document"} and not row.get("matched_local_source_id"):
                errors.append(f"bibtex_authority[{index}] is Frasch-derived but missing matched_local_source_id")
            if row.get("matched_local_source_id"):
                if row["matched_local_source_id"].startswith("frasch-ref-"):
                    if row["matched_local_source_id"] not in frasch_ids:
                        errors.append(f"bibtex_authority[{index}] references missing Frasch ref ID {row['matched_local_source_id']}")
                elif row["source_of_authority"] != "external_bibtex" and row["matched_local_source_id"] not in manifest_ids:
                    errors.append(f"bibtex_authority[{index}] references missing local manifest ID {row['matched_local_source_id']}")
            if row["bibtex_key"] not in evidence_by_key:
                errors.append(f"bibtex_authority[{index}] is evidence-backed but missing bibtex_authority_evidence.tsv row")
        if source_family_rows and row.get("source_family_id") and row["source_family_id"] not in evidence_by_source_family:
            errors.append(f"bibtex_authority[{index}] source family {row['source_family_id']} lacks evidence row")
        if len(row.get("matched_local_reference", "")) > MAX_MATCHED_LOCAL_REFERENCE_LENGTH:
            errors.append(f"bibtex_authority[{index}] has long matched_local_reference")
        normalized_script = normalize_script_value(row.get("script", ""), fallback_title=row.get("title", ""))
        if row.get("script", "") != normalized_script:
            errors.append(f"bibtex_authority[{index}] has non-normalized script value {row.get('script', '')}")
        for value in row.values():
            if has_absolute_path(value):
                errors.append(f"bibtex_authority[{index}] contains an absolute local path")
                break

    if high_frequency_path:
        if not high_frequency_path.exists():
            errors.append("high_frequency_unresolved.tsv is missing")
        else:
            counts = [int(row.get("occurrence_count", "0") or 0) for row in high_frequency_rows]
            if counts != sorted(counts, reverse=True):
                errors.append("high_frequency_unresolved.tsv is not sorted by descending occurrence_count")
    if evidence_path and not evidence_path.exists():
        errors.append("bibtex_authority_evidence.tsv is missing")
    if resolution_plan_path:
        if not resolution_plan_path.exists():
            errors.append("high_frequency_resolution_plan.tsv is missing")
        else:
            for index, row in enumerate(resolution_plan_rows, start=1):
                if row.get("resolution_status") not in RESOLUTION_STATUSES:
                    errors.append(f"high_frequency_resolution_plan[{index}] has invalid resolution_status {row.get('resolution_status')}")
                if row.get("resolution_level") not in RESOLUTION_LEVELS:
                    errors.append(f"high_frequency_resolution_plan[{index}] has invalid resolution_level {row.get('resolution_level')}")
                if row.get("resolution_status") != "unresolved" and not row.get("evidence_source"):
                    errors.append(f"high_frequency_resolution_plan[{index}] is resolved but missing evidence_source")

    if source_family_path:
        if not source_family_path.exists():
            errors.append("source_family_authority.tsv is missing")
        else:
            allowed_flags = {"true", "false"}
            for index, row in enumerate(source_family_rows, start=1):
                if row.get("resolution_status") not in RESOLUTION_STATUSES:
                    errors.append(f"source_family_authority[{index}] has invalid resolution_status {row.get('resolution_status')}")
                if row.get("resolution_level") not in RESOLUTION_LEVELS:
                    errors.append(f"source_family_authority[{index}] has invalid resolution_level {row.get('resolution_level')}")
                if row.get("needs_human_review") not in allowed_flags:
                    errors.append(f"source_family_authority[{index}] has invalid needs_human_review {row.get('needs_human_review')}")
                if row.get("family_id") and row["family_id"] not in family_ids:
                    errors.append(f"source_family_authority[{index}] references unknown family_id {row['family_id']}")
                if row.get("needs_human_review") == "true" and row.get("resolution_status") in {"source_family_resolved", "series_level_resolved"}:
                    has_inline_evidence = any(
                        row.get(field, "")
                        for field in ("best_definition_source", "best_definition_quote", "evidence_source", "evidence_id")
                    )
                    if row["source_family_id"] not in evidence_by_source_family and not has_inline_evidence:
                        errors.append(f"source_family_authority[{index}] provisional source family lacks evidence row")
                for value in row.values():
                    if has_absolute_path(value):
                        errors.append(f"source_family_authority[{index}] contains an absolute local path")
                        break

    if acronym_status_path:
        if not acronym_status_path.exists():
            errors.append("acronym_resolution_status.tsv is missing")
        else:
            allowed_acronym_statuses = {
                "alias_or_variant_of_PPA",
                "confirmed_expansion",
                "genuinely_unresolved_after_occurrence_level_review",
                "internal_locator_system",
                "probable_typo_for_PPA",
                "probable_expansion",
                "probable_locator_system",
                "probable_private_luce_locator_system",
                "source_family_only",
                "source_family_with_unknown_expansion_but_known_function",
                "contextual_usage_only",
                "unresolved",
                "unresolved_after_targeted_search",
                "unresolved_after_exhaustive_search",
                "not_an_acronym",
                "internal_locator",
            }
            strong_statuses = {"confirmed_expansion", "probable_expansion"}
            review_required = {
                "alias_or_variant_of_PPA",
                "genuinely_unresolved_after_occurrence_level_review",
                "internal_locator_system",
                "probable_typo_for_PPA",
                "probable_locator_system",
                "probable_private_luce_locator_system",
                "source_family_only",
                "source_family_with_unknown_expansion_but_known_function",
                "contextual_usage_only",
                "unresolved",
                "unresolved_after_targeted_search",
                "unresolved_after_exhaustive_search",
            }
            for acronym in PRIORITY_ACRONYMS:
                if acronym not in acronym_status_by_acronym:
                    errors.append(f"acronym_resolution_status.tsv is missing priority acronym {acronym}")
            for index, row in enumerate(acronym_status_rows, start=1):
                status = row.get("resolution_status", "")
                evidence_id = row.get("best_evidence_id", "")
                candidate_row = acronym_candidate_by_id.get(evidence_id)
                remaining_rows = remaining_evidence_by_acronym.get(row.get("acronym", ""), [])
                remaining_evidence_row = remaining_rows[0] if evidence_id.startswith("remaining-evidence:") and remaining_rows else None
                if status not in allowed_acronym_statuses:
                    errors.append(f"acronym_resolution_status[{index}] has invalid resolution_status {status}")
                if status in review_required and row.get("needs_human_review") != "true":
                    errors.append(f"acronym_resolution_status[{index}] should require human review for {status}")
                if status == "contextual_usage_only" and row.get("best_evidence_id"):
                    if candidate_row and candidate_row.get("evidence_type") in STRONG_DEFINITION_EVIDENCE_TYPES:
                        errors.append(f"acronym_resolution_status[{index}] marks strong evidence as contextual usage only")
                if status in strong_statuses:
                    if not candidate_row and not evidence_id.startswith(("manual-seed:", "remaining-evidence:")):
                        errors.append(f"acronym_resolution_status[{index}] requires strong evidence for {status}")
                    if candidate_row and candidate_row.get("evidence_type") not in STRONG_DEFINITION_EVIDENCE_TYPES and candidate_row.get("definition_quality") != "manual_seed":
                        errors.append(f"acronym_resolution_status[{index}] requires strong evidence for {status}")
                    if remaining_evidence_row and status == "confirmed_expansion" and remaining_evidence_row.get("evidence_strength") != "strong":
                        errors.append(f"acronym_resolution_status[{index}] remaining targeted evidence is not strong enough for {status}")
                    if remaining_evidence_row and status == "probable_expansion" and remaining_evidence_row.get("evidence_strength") not in {"strong", "medium"}:
                        errors.append(f"acronym_resolution_status[{index}] remaining targeted evidence is too weak for {status}")
                    if not candidate_supports_strong_expansion(candidate_row) and not evidence_id.startswith(("manual-seed:", "remaining-evidence:")):
                        errors.append(f"acronym_resolution_status[{index}] lacks explicit or strong definition evidence for {status}")
                    if len(row.get("best_evidence_quote", "")) > MAX_STRONG_DEFINITION_QUOTE_LENGTH:
                        errors.append(f"acronym_resolution_status[{index}] best_evidence_quote exceeds {MAX_STRONG_DEFINITION_QUOTE_LENGTH} characters")
                if status in {
                    "alias_or_variant_of_PPA",
                    "confirmed_expansion",
                    "internal_locator_system",
                    "probable_expansion",
                    "probable_locator_system",
                    "probable_private_luce_locator_system",
                    "probable_typo_for_PPA",
                    "source_family_with_unknown_expansion_but_known_function",
                } and not row.get("current_expansion"):
                    errors.append(f"acronym_resolution_status[{index}] {status} is missing current_expansion")
                if row.get("definition_quality") == "explicit" and row.get("acronym") in PRIORITY_ACRONYMS and not row.get("current_expansion"):
                    errors.append(f"acronym_resolution_status[{index}] explicit priority acronym is missing current_expansion")
                if row.get("definition_quality") == "manual_seed":
                    seed_row = manual_seed_by_acronym.get(row.get("acronym", ""))
                    if not seed_row:
                        errors.append(f"acronym_resolution_status[{index}] uses manual_seed without manual_acronym_seeds.tsv row")
                    elif not normalized_expansion_match(row.get("current_expansion", ""), seed_row.get("expansion", "")):
                        errors.append(f"acronym_resolution_status[{index}] manual_seed expansion does not match manual_acronym_seeds.tsv")
                    if row.get("confidence") != "high":
                        errors.append(f"acronym_resolution_status[{index}] manual_seed rows must keep confidence=high")
                if row.get("acronym") == "List" and (
                    has_list_date_false_positive(row.get("current_expansion", ""))
                    or has_list_date_false_positive(row.get("best_evidence_quote", ""))
                ):
                    errors.append("acronym_resolution_status contains the known List date-string false positive")
                if row.get("acronym") == "OBI" and (
                    has_obi_remark_false_positive(row.get("current_expansion", ""))
                    or has_obi_remark_false_positive(row.get("best_evidence_quote", ""))
                ):
                    errors.append("acronym_resolution_status contains the known OBI remark false positive")
                if row.get("acronym") == "OR" and (
                    has_lowercase_or_false_positive(row.get("current_expansion", ""))
                    or has_lowercase_or_false_positive(row.get("best_evidence_quote", ""))
                ):
                    errors.append("acronym_resolution_status contains the known lowercase 'or' false positive")
                if status in {"unresolved_after_targeted_search", "unresolved_after_exhaustive_search", "probable_locator_system", "probable_private_luce_locator_system"}:
                    if row.get("best_evidence_id") and not row.get("best_evidence_id").startswith("remaining-evidence:"):
                        errors.append(f"acronym_resolution_status[{index}] {status} must cite remaining targeted evidence")
                if status in {"alias_or_variant_of_PPA", "probable_typo_for_PPA", "source_family_with_unknown_expansion_but_known_function"}:
                    if row.get("best_evidence_id") and not row.get("best_evidence_id").startswith("remaining-evidence:"):
                        errors.append(f"acronym_resolution_status[{index}] {status} must cite targeted remaining evidence")
                if row.get("acronym") == "RDASB" and status == "unresolved_after_exhaustive_search":
                    errors.append("RDASB should not remain unresolved_after_exhaustive_search when publication-title evidence exists")

    if acronym_candidates_path and acronym_candidates_path.exists():
        for index, row in enumerate(acronym_candidate_rows, start=1):
            if row.get("definition_quality") == "explicit" and row.get("evidence_type") == "contextual_usage":
                errors.append(f"acronym_definition_candidates[{index}] cannot mark contextual usage as explicit")
            if row.get("acronym") == "OR" and has_lowercase_or_false_positive(row.get("raw_definition", "")):
                errors.append("acronym_definition_candidates.tsv still contains lowercase 'or' as a definition")
            if row.get("acronym") == "List" and has_list_date_false_positive(row.get("raw_definition", "")):
                errors.append("acronym_definition_candidates.tsv still contains the List date-string false positive")
            if row.get("acronym") == "OBI" and has_obi_remark_false_positive(row.get("raw_definition", "")):
                errors.append("acronym_definition_candidates.tsv still contains the OBI remark false positive")
            for value in row.values():
                if has_absolute_path(value):
                    errors.append(f"acronym_definition_candidates[{index}] contains an absolute local path")
                    break

    if manual_acronym_seeds_path:
        if not manual_acronym_seeds_path.exists():
            errors.append("manual_acronym_seeds.tsv is missing")
        else:
            for acronym, seed_row in manual_seed_by_acronym.items():
                status_row = acronym_status_by_acronym.get(acronym)
                if not status_row:
                    errors.append(f"manual seed {acronym} is missing from acronym_resolution_status.tsv")
                    continue
                if not status_row.get("current_expansion"):
                    errors.append(f"manual seed {acronym} was downgraded to a blank expansion")
                if status_row.get("resolution_status") == "source_family_only":
                    errors.append(f"manual seed {acronym} was downgraded to source_family_only")
                if status_row.get("confidence") != "high":
                    errors.append(f"manual seed {acronym} must keep confidence=high")
                if not normalized_expansion_match(status_row.get("current_expansion", ""), seed_row.get("expansion", "")):
                    errors.append(f"manual seed {acronym} expansion does not match the manual seed table")

    if ocr_queue_rows and ocr_manifest_path and not ocr_manifest_path.exists():
        errors.append("ocr_manifest.tsv is missing")
    if ocr_queue_rows and ocr_index_path and not ocr_index_path.exists():
        errors.append("ocr_text_index.tsv is missing")
    ocr_success_labels = {
        row.get("source_file_label", "")
        for row in ocr_manifest_rows
        if row.get("extraction_status") == "success" and row.get("source_file_label")
    }
    for index, row in enumerate(acronym_status_rows, start=1):
        if row.get("resolution_status") in {"confirmed_expansion", "probable_expansion"} and row.get("best_evidence_source", "") in ocr_success_labels:
            if not row.get("best_evidence_source") or not row.get("best_evidence_quote"):
                errors.append(f"acronym_resolution_status[{index}] OCR-backed expansion is missing evidence source or quote")
            if len(row.get("best_evidence_quote", "")) > MAX_STRONG_DEFINITION_QUOTE_LENGTH:
                errors.append(f"acronym_resolution_status[{index}] OCR-backed evidence quote exceeds {MAX_STRONG_DEFINITION_QUOTE_LENGTH} characters")
    if manual_review_packet_path:
        if not manual_review_packet_path.exists():
            errors.append("acronym_manual_review_packet.tsv is missing")
        else:
            packet_by_acronym = {row.get("acronym", ""): row for row in manual_review_packet_rows if row.get("acronym")}
            for acronym in PRIORITY_ACRONYMS:
                if acronym not in packet_by_acronym:
                    errors.append(f"acronym_manual_review_packet.tsv is missing priority acronym {acronym}")
    if remaining_acronym_worklist_path:
        if not remaining_acronym_worklist_path.exists():
            errors.append("remaining_acronym_worklist.tsv is missing")
        else:
            worklist_by_acronym = {row.get("acronym", ""): row for row in remaining_acronym_worklist_rows if row.get("acronym")}
            for acronym in REMAINING_ACRONYMS:
                if acronym not in worklist_by_acronym:
                    errors.append(f"remaining_acronym_worklist.tsv is missing {acronym}")
    if remaining_acronym_evidence_path:
        if not remaining_acronym_evidence_path.exists():
            errors.append("remaining_acronym_evidence.tsv is missing")
        else:
            for acronym in REMAINING_ACRONYMS:
                if not remaining_evidence_by_acronym.get(acronym):
                    errors.append(f"remaining_acronym_evidence.tsv is missing evidence rows for {acronym}")
            for acronym in REMAINING_ACRONYMS:
                status_row = acronym_status_by_acronym.get(acronym)
                if status_row and status_row.get("resolution_status") == "source_family_only":
                    errors.append(f"{acronym} cannot remain generic source_family_only after targeted search")
            for index, row in enumerate(remaining_acronym_evidence_rows, start=1):
                if row.get("evidence_strength") in {"strong", "medium"} and row.get("supports_expansion") == "true":
                    if not row.get("candidate_expansion") and row.get("evidence_type") != "manual_inference":
                        errors.append(f"remaining_acronym_evidence[{index}] supports an expansion but lacks candidate_expansion")
                for value in row.values():
                    if has_absolute_path(value):
                        errors.append(f"remaining_acronym_evidence[{index}] contains an absolute local path")
                        break
    if source_work_locator_systems_path:
        if not source_work_locator_systems_path.exists():
            errors.append("source_work_locator_systems.tsv is missing")
        else:
            source_family_by_id = {row.get("source_family_id", ""): row for row in source_family_rows if row.get("source_family_id")}
            for index, row in enumerate(source_work_locator_rows, start=1):
                if row.get("source_work_key") and row["source_work_key"] not in source_work_keys:
                    errors.append(f"source_work_locator_systems[{index}] references unknown source_work_key {row['source_work_key']}")
                for source_family_id in [item.strip() for item in row.get("source_family_ids", "").split(";") if item.strip()]:
                    if source_family_id not in source_family_by_id:
                        errors.append(f"source_work_locator_systems[{index}] references unknown source_family_id {source_family_id}")
                expected_bibtex_key = source_work_bibtex_by_key.get(row.get("source_work_key", ""), "")
                if expected_bibtex_key != row.get("bibtex_key", ""):
                    errors.append(f"source_work_locator_systems[{index}] has bibtex_key mismatch for {row.get('source_work_key', '')}")
            iob_pl_rows = [row for row in source_work_locator_rows if row.get("source_work_key") == "lucePeMaungTinInscriptionsOfBurma"]
            if not iob_pl_rows:
                errors.append("source_work_locator_systems.tsv must describe lucePeMaungTinInscriptionsOfBurma")
            if "sf-mp" in source_family_by_id and not any(row.get("source_work_key") == "mandalayPalaceStoneCollection" for row in source_work_locator_rows):
                errors.append("source_work_locator_systems.tsv must describe the MP Mandalay Palace locator system")
            if "sf-or" in source_family_by_id and not any(row.get("source_work_key") == "britishLibraryOrientalManuscripts" for row in source_work_locator_rows):
                errors.append("source_work_locator_systems.tsv must describe the OR shelfmark locator system")
            if "sf-luce-d" in source_family_by_id and not any(row.get("source_work_key") == "gHLuceNotebookD" for row in source_work_locator_rows):
                errors.append("source_work_locator_systems.tsv must describe the Luce D locator system")
            if "sf-luce-j" in source_family_by_id and not any(row.get("source_work_key") == "gHLuceNotebookJ" for row in source_work_locator_rows):
                errors.append("source_work_locator_systems.tsv must describe the Luce J locator system")
            if "sf-ippa" in source_family_by_id and not any(
                row.get("source_work_key") == "ppaCatalogue" and "sf-ippa" in row.get("source_family_ids", "") for row in source_work_locator_rows
            ):
                errors.append("source_work_locator_systems.tsv must describe IPPA as an alias/variant locator into ppaCatalogue")
            if "sf-sip" in source_family_by_id and not any(row.get("source_work_key") == "sipSelectionsPagan" for row in source_work_locator_rows):
                errors.append("source_work_locator_systems.tsv must describe SIP locator semantics")
            if "sf-uem" in source_family_by_id and not any(row.get("source_work_key") == "uemSelectionsPagan" for row in source_work_locator_rows):
                errors.append("source_work_locator_systems.tsv must describe UEM locator semantics")
            if "sf-tn" in source_family_by_id and not any(row.get("source_work_key") == "tnInscriptionsPaganPinyaAva" for row in source_work_locator_rows):
                errors.append("source_work_locator_systems.tsv must describe TN locator semantics")
    if source_work_authority_path:
        if not source_work_authority_path.exists():
            errors.append("source_work_authority.tsv is missing")
        else:
            if len(source_work_keys) != len(source_work_authority_rows):
                errors.append("source_work_authority.tsv must not contain duplicate source_work_key rows")
            for index, row in enumerate(source_work_authority_rows, start=1):
                if not row.get("canonical_title"):
                    errors.append(f"source_work_authority[{index}] is missing canonical_title")
                if row.get("authority_level") not in VALID_AUTHORITY_LEVELS:
                    errors.append(f"source_work_authority[{index}] has invalid authority_level {row.get('authority_level')}")
                if row.get("bibtex_key") and row["bibtex_key"] not in authority_keys:
                    errors.append(f"source_work_authority[{index}] references missing authority bibtex_key {row['bibtex_key']}")
                if row.get("authority_level") in {"locator_collection", "manuscript_collection", "archival_notebook"} and row.get("bibtex_key"):
                    errors.append(
                        f"source_work_authority[{index}] should not emit ordinary BibTeX publication key for locator or notebook authority {row['source_work_key']}"
                    )
                for source_family_id in [item.strip() for item in row.get("related_source_family_ids", "").split(";") if item.strip()]:
                    if source_family_rows and source_family_id not in {sf.get("source_family_id", "") for sf in source_family_rows}:
                        errors.append(f"source_work_authority[{index}] references unknown source_family_id {source_family_id}")
            for row in crosswalk_rows:
                if row.get("source_work_key") and row["source_work_key"] not in source_work_keys:
                    errors.append(f"crosswalk source_work_key {row['source_work_key']} is missing from source_work_authority.tsv")
    if source_work_authority_audit_path:
        if not source_work_authority_audit_path.exists():
            errors.append("source_work_authority_audit.tsv is missing")
        elif not source_work_authority_audit_rows:
            errors.append("source_work_authority_audit.tsv must review duplicate or overlapping source-work authorities")
    if source_work_to_bibtex_reconciliation_path:
        if not source_work_to_bibtex_reconciliation_path.exists():
            errors.append("source_work_to_bibtex_reconciliation.tsv is missing")
        else:
            if set(reconciliation_by_work_key) != source_work_keys:
                errors.append("source_work_to_bibtex_reconciliation.tsv must cover every source_work_key")
            for index, row in enumerate(source_work_to_bibtex_reconciliation_rows, start=1):
                if row.get("source_work_key") not in source_work_keys:
                    errors.append(f"source_work_to_bibtex_reconciliation[{index}] references unknown source_work_key {row.get('source_work_key')}")
                if row.get("current_bibtex_key") and row["current_bibtex_key"] not in valid_keys:
                    errors.append(f"source_work_to_bibtex_reconciliation[{index}] references missing BibTeX key {row['current_bibtex_key']}")
                if row.get("bibtex_status") == "suppressed_locator_system" and row.get("current_bibtex_key"):
                    errors.append(
                        f"source_work_to_bibtex_reconciliation[{index}] suppresses locator BibTeX emission but still points at {row['current_bibtex_key']}"
                    )
    if bibtex_field_quality_audit_path:
        if not bibtex_field_quality_audit_path.exists():
            errors.append("bibtex_field_quality_audit.tsv is missing")
    if authority_key_normalization_path:
        if not authority_key_normalization_path.exists():
            errors.append("authority_key_normalization.tsv is missing")
        elif not authority_key_normalization_rows:
            errors.append("authority_key_normalization.tsv must document reviewed key normalization decisions")
    if raw_reference_crosswalk_audit_path:
        if not raw_reference_crosswalk_audit_path.exists():
            errors.append("raw_reference_crosswalk_audit.tsv is missing")
        else:
            for index, row in enumerate(raw_reference_crosswalk_audit_rows, start=1):
                if row.get("severity") not in {"high", "medium", "low"}:
                    errors.append(f"raw_reference_crosswalk_audit[{index}] has invalid severity {row.get('severity')}")
                if row.get("auto_fixable") not in {"true", "false"}:
                    errors.append(f"raw_reference_crosswalk_audit[{index}] has invalid auto_fixable {row.get('auto_fixable')}")
                if row.get("human_review_required") not in {"true", "false"}:
                    errors.append(f"raw_reference_crosswalk_audit[{index}] has invalid human_review_required {row.get('human_review_required')}")
    if candidate_stub_review_path:
        if not candidate_stub_review_path.exists():
            errors.append("candidate_stub_review.tsv is missing")
        else:
            review_by_key = {row.get("candidate_key", ""): row for row in candidate_stub_review_rows if row.get("candidate_key")}
            reviewed_keys = set(review_by_key)
            current_candidate_keys = candidate_keys | {
                row.get("candidate_key", "") for row in candidate_stub_review_rows if row.get("review_decision") == "suppress"
            }
            if reviewed_keys != current_candidate_keys:
                errors.append("candidate_stub_review.tsv must review every retained or suppressed candidate stub")
            for row in candidate_stub_review_rows:
                if row.get("review_decision") == "retain" and not row.get("next_action"):
                    errors.append(f"candidate_stub_review.tsv must record next_action for retained candidate {row.get('candidate_key')}")
                if row.get("candidate_key") in authority_keys and row.get("review_decision") != "promote":
                    errors.append(f"candidate_stub_review.tsv silently promoted {row.get('candidate_key')} without review_decision=promote")
    if final_acronym_resolution_sprint_path:
        if not final_acronym_resolution_sprint_path.exists():
            errors.append("final_acronym_resolution_sprint.tsv is missing")
        else:
            for acronym in FINAL_SPRINT_ACRONYMS:
                if acronym not in final_sprint_by_acronym:
                    errors.append(f"final_acronym_resolution_sprint.tsv is missing {acronym}")
    if final_acronym_local_file_hits_path:
        if not final_acronym_local_file_hits_path.exists():
            errors.append("final_acronym_local_file_hits.tsv is missing")
        else:
            for acronym in FINAL_SPRINT_ACRONYMS:
                if not any(row.get("acronym") == acronym for row in final_acronym_local_file_hit_rows):
                    errors.append(f"final_acronym_local_file_hits.tsv is missing local search rows for {acronym}")
            for index, row in enumerate(final_acronym_local_file_hit_rows, start=1):
                for value in row.values():
                    if has_absolute_path(value):
                        errors.append(f"final_acronym_local_file_hits[{index}] contains an absolute local path")
                        break
    if final_acronym_web_searches_path:
        if not final_acronym_web_searches_path.exists():
            errors.append("final_acronym_web_searches.tsv is missing")
        else:
            for acronym in FINAL_SPRINT_ACRONYMS:
                if not any(row.get("acronym") == acronym for row in final_acronym_web_search_rows):
                    errors.append(f"final_acronym_web_searches.tsv is missing web-search rows for {acronym}")
    if frasch_abbreviation_list_review_path and not frasch_abbreviation_list_review_path.exists():
        errors.append("frasch_abbreviation_list_review.tsv is missing")
    elif frasch_abbreviation_list_review_rows and not any("IPPA" in row.get("possible_missing_acronyms", "") for row in frasch_abbreviation_list_review_rows):
        errors.append("frasch_abbreviation_list_review.tsv must record the missing final-sprint acronyms explicitly")
    if unresolved_acronym_dossier_path:
        if not unresolved_acronym_dossier_path.exists():
            errors.append("unresolved_acronym_dossier.tsv is missing")
        else:
            unresolved_status_acronyms = {
                row.get("acronym", "")
                for row in acronym_status_rows
                if row.get("acronym") in FINAL_SPRINT_ACRONYMS and row.get("resolution_status") == "unresolved_after_exhaustive_search"
            }
            dossier_acronyms = {row.get("acronym", "") for row in unresolved_acronym_dossier_rows if row.get("acronym")}
            if dossier_acronyms != unresolved_status_acronyms:
                errors.append("unresolved_acronym_dossier.tsv must contain exactly the unresolved_after_exhaustive_search final-sprint acronyms")
            if "IPPA" in dossier_acronyms:
                errors.append("unresolved_acronym_dossier.tsv should not include IPPA after alias/variant resolution")

    check_ippa_artifacts = any(
        path is not None
        for path in (
            ippa_occurrence_contexts_path,
            ippa_ppa_comparison_path,
            ippa_local_context_search_path,
            ippa_frasch_abbrev_neighbourhood_path,
            ippa_record_review_path,
            ippa_targeted_ocr_notes_path,
            ippa_resolution_decision_path,
            reference_occurrences_path,
        )
    )
    ippa_status_row = acronym_status_by_acronym.get("IPPA")
    if ippa_status_row and check_ippa_artifacts:
        if ippa_occurrence_contexts_path and not ippa_occurrence_contexts_path.exists():
            errors.append("ippa_occurrence_contexts.tsv is missing")
        if ippa_ppa_comparison_path and not ippa_ppa_comparison_path.exists():
            errors.append("ippa_ppa_comparison.tsv is missing")
        if ippa_local_context_search_path and not ippa_local_context_search_path.exists():
            errors.append("ippa_local_context_search.tsv is missing")
        if ippa_frasch_abbrev_neighbourhood_path and not ippa_frasch_abbrev_neighbourhood_path.exists():
            errors.append("ippa_frasch_abbrev_neighbourhood.tsv is missing")
        if ippa_record_review_path and not ippa_record_review_path.exists():
            errors.append("ippa_record_review.tsv is missing")
        if ippa_targeted_ocr_notes_path and not ippa_targeted_ocr_notes_path.exists():
            errors.append("ippa_targeted_ocr_notes.tsv is missing")
        if ippa_resolution_decision_path and not ippa_resolution_decision_path.exists():
            errors.append("ippa_resolution_decision.tsv is missing")
        if ippa_resolution_decision_rows and len(ippa_resolution_decision_rows) != 1:
            errors.append("ippa_resolution_decision.tsv must contain exactly one decision row")
        if ippa_occurrence_context_rows and reference_occurrence_rows:
            expected_ippa_occurrences = sum(
                1 for row in reference_occurrence_rows if (row.get("raw_reference_string", "") or "").strip().casefold().startswith("ippa")
            )
            if len(ippa_occurrence_context_rows) != expected_ippa_occurrences:
                errors.append("ippa_occurrence_contexts.tsv must list every IPPA occurrence from reference_occurrences.tsv")
        has_ippa_family_rows = any(row.get("source_family_id") == "sf-ippa" for row in source_family_rows) or any(
            row.get("source_family_id") == "sf-ippa" for row in crosswalk_rows
        )
        if ippa_status_row.get("resolution_status") == "alias_or_variant_of_PPA":
            if not ippa_decision_row or ippa_decision_row.get("decision") != "alias_or_variant_of_PPA":
                errors.append("IPPA alias/variant status requires matching ippa_resolution_decision.tsv evidence")
            if has_ippa_family_rows and not any(
                row.get("source_family_id") == "sf-ippa" and row.get("raw_reference_string", "").startswith("IPPA")
                for row in crosswalk_rows
            ):
                errors.append("raw_reference_to_bibtex.tsv must preserve raw IPPA strings when routing IPPA to PPA")
            if has_ippa_family_rows and not any(
                row.get("source_family_id") == "sf-ippa"
                and row.get("source_work_key") == "ppaCatalogue"
                and row.get("bibtex_key") == "ppaCatalogue"
                for row in crosswalk_rows
            ):
                errors.append("IPPA alias routing must map sf-ippa references to ppaCatalogue in raw_reference_to_bibtex.tsv")
        if ippa_status_row.get("resolution_status") == "genuinely_unresolved_after_occurrence_level_review":
            if not ippa_occurrence_context_rows or not ippa_resolution_decision_rows:
                errors.append("IPPA cannot remain unresolved without occurrence-level review artifacts")
        if ippa_decision_row:
            if not ippa_decision_row.get("evidence_summary"):
                errors.append("ippa_resolution_decision.tsv must include an evidence_summary")
            if ippa_decision_row.get("decision") in {"alias_or_variant_of_PPA", "probable_expansion"} and not ippa_decision_row.get("recommended_authority_update"):
                errors.append("ippa_resolution_decision.tsv must include a recommended_authority_update for resolved IPPA")

    unresolved_priority = [
        row.get("acronym", "")
        for row in acronym_status_rows
        if row.get("acronym") in PRIORITY_ACRONYMS
        and row.get("resolution_status") in {"unresolved", "unresolved_after_targeted_search", "unresolved_after_exhaustive_search", "genuinely_unresolved_after_occurrence_level_review"}
    ]
    if unresolved_priority:
        errors.append(f"priority acronyms remain unresolved: {', '.join(unresolved_priority)}")

    for index, row in enumerate(documentation_section_rows, start=1):
        heading = (row.get("section_heading", "") or "").casefold()
        excerpt = row.get("section_text_excerpt", "")
        if heading in GENERIC_BIBLIOGRAPHY_HEADINGS and row.get("contains_priority_acronyms") == "true" and not has_explicit_definition_pattern(excerpt):
            errors.append(f"documentation_abbreviation_sections[{index}] treats generic bibliography text as abbreviation evidence")
        if looks_like_irrelevant_tibetan_material(f"{row.get('source_file_label', '')} {excerpt}") and row.get("contains_priority_acronyms") == "true":
            errors.append(f"documentation_abbreviation_sections[{index}] treats irrelevant Tibetan material as Burmese acronym evidence")

    sip_explicit_candidates = [
        row
        for row in acronym_candidate_rows
        if row.get("acronym") == "SIP"
        and row.get("evidence_type") in STRONG_DEFINITION_EVIDENCE_TYPES
        and row.get("definition_quality") == "explicit"
    ]
    sip_status_row = acronym_status_by_acronym.get("SIP")
    if sip_explicit_candidates and sip_status_row and not sip_status_row.get("current_expansion"):
        errors.append("SIP has explicit definition evidence but remains blank in acronym_resolution_status.tsv")

    if source_family_rows:
        for index, row in enumerate(source_family_rows, start=1):
            acronym_status = row.get("acronym_resolution_status", "")
            expanded_label = row.get("expanded_label", "")
            if acronym_status in {"source_family_only", "contextual_usage_only", "unresolved"} and expanded_label and not PLACEHOLDER_EXPANSION_PATTERN.search(expanded_label):
                errors.append(f"source_family_authority[{index}] exposes an unverified expansion for {row.get('abbreviation')}")
            if acronym_status in {"unresolved_after_targeted_search", "unresolved_after_exhaustive_search"} and expanded_label and not PLACEHOLDER_EXPANSION_PATTERN.search(expanded_label):
                errors.append(f"source_family_authority[{index}] exposes an unverified expansion for {row.get('abbreviation')}")
            if acronym_status in {"confirmed_expansion", "probable_expansion"} and row.get("best_definition_evidence_id"):
                candidate_row = acronym_candidate_by_id.get(row["best_definition_evidence_id"])
                if row["best_definition_evidence_id"].startswith("manual-seed:"):
                    pass
                elif row["best_definition_evidence_id"].startswith("remaining-evidence:"):
                    matching_rows = remaining_evidence_by_acronym.get(row.get("abbreviation", ""), [])
                    if not matching_rows:
                        errors.append(f"source_family_authority[{index}] has non-strong definition evidence")
                    elif acronym_status == "confirmed_expansion" and matching_rows[0].get("evidence_strength") != "strong":
                        errors.append(f"source_family_authority[{index}] has non-strong definition evidence")
                    elif acronym_status == "probable_expansion" and matching_rows[0].get("evidence_strength") not in {"strong", "medium"}:
                        errors.append(f"source_family_authority[{index}] has non-strong definition evidence")
                elif not candidate_row or candidate_row.get("evidence_type") not in STRONG_DEFINITION_EVIDENCE_TYPES:
                    errors.append(f"source_family_authority[{index}] has non-strong definition evidence")
            if acronym_status in {
                "alias_or_variant_of_PPA",
                "internal_locator_system",
                "probable_typo_for_PPA",
                "probable_locator_system",
                "probable_private_luce_locator_system",
                "source_family_only",
                "source_family_with_unknown_expansion_but_known_function",
                "contextual_usage_only",
                "unresolved",
                "unresolved_after_targeted_search",
                "unresolved_after_exhaustive_search",
            } and row.get("needs_human_review") != "true":
                errors.append(f"source_family_authority[{index}] must keep needs_human_review=true for unresolved acronym state")
            if row.get("abbreviation") == "IPPA":
                if row.get("alias_of_source_family_id") != "sf-ppa":
                    errors.append("source_family_authority must link IPPA to sf-ppa as an alias family")
                if row.get("source_work_key") != "ppaCatalogue":
                    errors.append("source_family_authority must link IPPA to ppaCatalogue")
                if row.get("authority_key"):
                    errors.append("source_family_authority should not create a standalone BibTeX authority for IPPA")
            if row.get("abbreviation") == "Pl.":
                if row.get("locator_type") != "plate":
                    errors.append("source_family_authority must treat Pl. as locator_type=plate")
                if row.get("source_work_key") != "lucePeMaungTinInscriptionsOfBurma":
                    errors.append("source_family_authority must link Pl. to lucePeMaungTinInscriptionsOfBurma")
                if "plate reference into inscriptions of burma" not in row.get("expanded_label", "").casefold():
                    errors.append("source_family_authority must describe Pl. as a plate reference into Inscriptions of Burma")
            if row.get("abbreviation") in {"MP", "OR", "Luce D", "Luce J"} and row.get("authority_key") in valid_keys:
                errors.append(f"source_family_authority[{index}] should not force {row.get('abbreviation')} into a standalone BibTeX authority without publication evidence")

    if report:
        plan_family_ids = {row["family_id"] for row in resolution_plan_rows}
        unresolved_ids = {row["family_id"] for row in resolution_plan_rows if row.get("resolution_status") == "unresolved"}
        for row in report.get("top_unresolved_families", []):
            if row.get("family_id") in plan_family_ids and row.get("family_id") not in unresolved_ids:
                errors.append(f"report top_unresolved_families includes resolved family {row.get('family_id')}")
                break
        if report.get("priority_acronym_count") and report.get("priority_acronym_count") != len(PRIORITY_ACRONYMS):
            errors.append("report priority_acronym_count does not match configured priority acronym list")
        category_expectations = {
            "confirmed_acronym_expansions": sorted(
                row["acronym"] for row in acronym_status_rows if row.get("acronym") in PRIORITY_ACRONYMS and row.get("resolution_status") == "confirmed_expansion"
            ),
            "probable_acronym_expansions": sorted(
                row["acronym"] for row in acronym_status_rows if row.get("acronym") in PRIORITY_ACRONYMS and row.get("resolution_status") == "probable_expansion"
            ),
            "alias_or_variant_families": sorted(
                row["acronym"] for row in acronym_status_rows if row.get("acronym") in PRIORITY_ACRONYMS and row.get("resolution_status") == "alias_or_variant_of_PPA"
            ),
            "internal_locator_systems": sorted(
                row["acronym"]
                for row in acronym_status_rows
                if row.get("acronym") in PRIORITY_ACRONYMS and row.get("resolution_status") in {"internal_locator", "internal_locator_system"}
            ),
            "probable_locator_systems": sorted(
                row["acronym"] for row in acronym_status_rows if row.get("acronym") in PRIORITY_ACRONYMS and row.get("resolution_status") == "probable_locator_system"
            ),
            "probable_private_locator_systems": sorted(
                row["acronym"]
                for row in acronym_status_rows
                if row.get("acronym") in PRIORITY_ACRONYMS and row.get("resolution_status") == "probable_private_luce_locator_system"
            ),
            "not_acronyms": sorted(
                row["acronym"] for row in acronym_status_rows if row.get("acronym") in PRIORITY_ACRONYMS and row.get("resolution_status") == "not_an_acronym"
            ),
            "unresolved_after_exhaustive_search": sorted(
                row["acronym"]
                for row in acronym_status_rows
                if row.get("acronym") in PRIORITY_ACRONYMS
                and row.get("resolution_status") in {"genuinely_unresolved_after_occurrence_level_review", "unresolved_after_exhaustive_search"}
            ),
        }
        for key, expected in category_expectations.items():
            if sorted(report.get(key, [])) != expected:
                errors.append(f"report {key} does not match acronym_resolution_status.tsv")
        if any(acronym in report.get("confirmed_acronym_expansions", []) for acronym in ["IOB", "Pl.", "IPPA", "U Min Hswe"]):
            errors.append("report confirmed_acronym_expansions must not include locator, alias, or non-acronym families")
        if report.get("manual_acronym_seed_count") != len(manual_seed_rows):
            errors.append("report manual_acronym_seed_count does not match manual_acronym_seeds.tsv")
        if report.get("manual_review_packet_rows") != len(manual_review_packet_rows):
            errors.append("report manual_review_packet_rows does not match acronym_manual_review_packet.tsv")
        if report.get("remaining_acronym_count") != len(REMAINING_ACRONYMS):
            errors.append("report remaining_acronym_count does not match configured remaining acronym list")
        if report.get("remaining_acronyms_unresolved_after_targeted_search_count") != sum(
            1 for row in acronym_status_rows if row.get("acronym") in REMAINING_ACRONYMS and row.get("resolution_status") == "unresolved_after_targeted_search"
        ):
            errors.append("report remaining_acronyms_unresolved_after_targeted_search_count is inconsistent")
        if report.get("remaining_acronyms_unresolved_after_exhaustive_search_count") != sum(
            1 for row in acronym_status_rows if row.get("acronym") in REMAINING_ACRONYMS and row.get("resolution_status") == "unresolved_after_exhaustive_search"
        ):
            errors.append("report remaining_acronyms_unresolved_after_exhaustive_search_count is inconsistent")
        if report.get("source_work_authority_count") != len(source_work_authority_rows):
            errors.append("report source_work_authority_count does not match source_work_authority.tsv")
        if source_work_authority_audit_path and report.get("source_work_authority_audit_count") != len(source_work_authority_audit_rows):
            errors.append("report source_work_authority_audit_count does not match source_work_authority_audit.tsv")
        if source_work_authority_audit_path and report.get("source_work_duplicate_issue_count") != len(source_work_authority_audit_rows):
            errors.append("report source_work_duplicate_issue_count does not match source_work_authority_audit.tsv")
        if source_work_to_bibtex_reconciliation_path and report.get("source_work_to_bibtex_reconciliation_count") != len(source_work_to_bibtex_reconciliation_rows):
            errors.append("report source_work_to_bibtex_reconciliation_count does not match source_work_to_bibtex_reconciliation.tsv")
        if report.get("raw_reference_crosswalk_audit_count") != len(raw_reference_crosswalk_audit_rows):
            errors.append("report raw_reference_crosswalk_audit_count does not match raw_reference_crosswalk_audit.tsv")
        if report.get("high_severity_crosswalk_issue_count") != sum(1 for row in raw_reference_crosswalk_audit_rows if row.get("severity") == "high"):
            errors.append("report high_severity_crosswalk_issue_count does not match raw_reference_crosswalk_audit.tsv")
        if report.get("medium_severity_crosswalk_issue_count") != sum(1 for row in raw_reference_crosswalk_audit_rows if row.get("severity") == "medium"):
            errors.append("report medium_severity_crosswalk_issue_count does not match raw_reference_crosswalk_audit.tsv")
        if report.get("low_severity_crosswalk_issue_count") != sum(1 for row in raw_reference_crosswalk_audit_rows if row.get("severity") == "low"):
            errors.append("report low_severity_crosswalk_issue_count does not match raw_reference_crosswalk_audit.tsv")
        if bibtex_field_quality_audit_path and report.get("bibtex_field_quality_issue_count") != len(bibtex_field_quality_audit_rows):
            errors.append("report bibtex_field_quality_issue_count does not match bibtex_field_quality_audit.tsv")
        if bibtex_field_quality_audit_path and report.get("bad_ocr_bibtex_field_count") != sum(1 for row in bibtex_field_quality_audit_rows if row.get("issue_type") == "ocr_like_evidence_fragment"):
            errors.append("report bad_ocr_bibtex_field_count does not match bibtex_field_quality_audit.tsv")
        if authority_key_normalization_path and report.get("authority_key_normalization_count") != len(authority_key_normalization_rows):
            errors.append("report authority_key_normalization_count does not match authority_key_normalization.tsv")
        if report.get("bibtex_entries_emitted_count") != len(authority_entries):
            errors.append("report bibtex_entries_emitted_count does not match bibliography_authority.bib")
        if source_work_to_bibtex_reconciliation_path and report.get("bibtex_entries_suppressed_locator_count") != sum(
            1 for row in source_work_to_bibtex_reconciliation_rows if row.get("bibtex_status") == "suppressed_locator_system"
        ):
            errors.append("report bibtex_entries_suppressed_locator_count does not match source_work_to_bibtex_reconciliation.tsv")
        if source_work_to_bibtex_reconciliation_path and report.get("bibtex_entries_candidate_only_count") != sum(
            1 for row in source_work_to_bibtex_reconciliation_rows if row.get("bibtex_status") == "candidate_only"
        ):
            errors.append("report bibtex_entries_candidate_only_count does not match source_work_to_bibtex_reconciliation.tsv")
        if report.get("candidate_stub_review_count") != len(candidate_stub_review_rows):
            errors.append("report candidate_stub_review_count does not match candidate_stub_review.tsv")
        if report.get("candidate_stubs_promoted_count") != sum(1 for row in candidate_stub_review_rows if row.get("review_decision") == "promote"):
            errors.append("report candidate_stubs_promoted_count does not match candidate_stub_review.tsv")
        if report.get("candidate_stubs_suppressed_count") != sum(1 for row in candidate_stub_review_rows if row.get("review_decision") == "suppress"):
            errors.append("report candidate_stubs_suppressed_count does not match candidate_stub_review.tsv")
        if report.get("candidate_stubs_retained_count") != sum(1 for row in candidate_stub_review_rows if row.get("review_decision") == "retain"):
            errors.append("report candidate_stubs_retained_count does not match candidate_stub_review.tsv")

    if seed_rows:
        allowed_confidence = {"low", "medium", "high"}
        allowed_flags = {"true", "false"}
        for index, row in enumerate(seed_rows, start=1):
            if row.get("confidence") not in allowed_confidence:
                errors.append(f"source_abbreviation_seeds[{index}] has invalid confidence {row.get('confidence')}")
            if row.get("needs_human_review") not in allowed_flags:
                errors.append(f"source_abbreviation_seeds[{index}] has invalid needs_human_review {row.get('needs_human_review')}")
            for value in row.values():
                if has_absolute_path(value):
                    errors.append(f"source_abbreviation_seeds[{index}] contains an absolute local path")
                    break

    for index, row in enumerate(manifest_rows, start=1):
        copied_path = row.get("copied_path", "")
        if copied_path and not (copied_path.startswith("data/local/") or copied_path.startswith(".local/")):
            errors.append(f"local_file_manifest[{index}] copied_path is not under a gitignored local cache")
        if has_absolute_path(row.get("original_path", "")) or has_absolute_path(copied_path):
            errors.append(f"local_file_manifest[{index}] contains an absolute local path")

    try:
        tracked_local = subprocess.run(
            ["git", "ls-files", "data/local"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
    except (subprocess.CalledProcessError, FileNotFoundError):
        tracked_local = []
    for path in tracked_local:
        if path.casefold().endswith((".pdf", ".doc", ".docx", ".djvu", ".tif", ".tiff", ".png", ".jpg", ".jpeg")):
            errors.append(f"tracked local source binary found in git: {path}")
        if path.startswith("data/local/ocr_text/") and path.casefold().endswith(".txt"):
            errors.append(f"tracked OCR text found in git: {path}")
    try:
        tracked_ocr_outputs = subprocess.run(
            ["git", "ls-files", "data/working/bibliography/local_sources/ocr_outputs"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
    except (subprocess.CalledProcessError, FileNotFoundError):
        tracked_ocr_outputs = []
    for path in tracked_ocr_outputs:
        if path.casefold().endswith(".txt"):
            errors.append(f"tracked OCR output text file found in git: {path}")

    return {
        "ok": not errors,
        "errors": errors,
        "counts": {
            "authority_entries": len(authority_entries),
            "candidate_entries": len(candidate_entries),
            "crosswalk_rows": len(crosswalk_rows),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the BibTeX authority working layer.")
    parser.add_argument(
        "--authority-bib",
        type=Path,
        default=Path("data/working/bibliography/bibtex_authority/bibliography_authority.bib"),
    )
    parser.add_argument(
        "--candidate-bib",
        type=Path,
        default=Path("data/working/bibliography/bibtex_authority/bibliography_candidates.bib"),
    )
    parser.add_argument(
        "--authority-tsv",
        type=Path,
        default=Path("data/working/bibliography/bibtex_authority/bibtex_authority.tsv"),
    )
    parser.add_argument(
        "--crosswalk",
        type=Path,
        default=Path("data/working/bibliography/bibtex_authority/raw_reference_to_bibtex.tsv"),
    )
    parser.add_argument(
        "--families",
        type=Path,
        default=Path("data/working/bibliography/reference_families.tsv"),
    )
    parser.add_argument(
        "--external-entries",
        type=Path,
        default=Path("data/working/bibliography/external_bibtex/asia_2_entries.tsv"),
    )
    parser.add_argument(
        "--seed-path",
        type=Path,
        default=Path("data/working/bibliography/bibtex_authority/source_abbreviation_seeds.tsv"),
    )
    parser.add_argument(
        "--high-frequency",
        type=Path,
        default=Path("data/working/bibliography/bibtex_authority/high_frequency_unresolved.tsv"),
    )
    parser.add_argument(
        "--evidence-path",
        type=Path,
        default=Path("data/working/bibliography/bibtex_authority/bibtex_authority_evidence.tsv"),
    )
    parser.add_argument(
        "--resolution-plan",
        type=Path,
        default=Path("data/working/bibliography/bibtex_authority/high_frequency_resolution_plan.tsv"),
    )
    parser.add_argument(
        "--source-family-path",
        type=Path,
        default=Path("data/working/bibliography/bibtex_authority/source_family_authority.tsv"),
    )
    parser.add_argument(
        "--report-path",
        type=Path,
        default=Path("data/working/bibliography/bibtex_authority/bibtex_authority_report.json"),
    )
    parser.add_argument(
        "--frasch-references",
        type=Path,
        default=Path("data/working/bibliography/local_sources/frasch_reference_entries.tsv"),
    )
    parser.add_argument(
        "--local-manifest",
        type=Path,
        default=Path("data/working/bibliography/local_sources/local_file_manifest.tsv"),
    )
    parser.add_argument(
        "--acronym-status",
        type=Path,
        default=Path("data/working/bibliography/bibtex_authority/acronym_resolution_status.tsv"),
    )
    parser.add_argument(
        "--acronym-candidates",
        type=Path,
        default=Path("data/working/bibliography/local_sources/acronym_definition_candidates.tsv"),
    )
    parser.add_argument(
        "--acronym-report",
        type=Path,
        default=Path("data/working/bibliography/local_sources/acronym_definition_report.json"),
    )
    parser.add_argument(
        "--manual-acronym-seeds",
        type=Path,
        default=Path("data/working/bibliography/bibtex_authority/manual_acronym_seeds.tsv"),
    )
    parser.add_argument(
        "--ocr-queue",
        type=Path,
        default=Path("data/working/bibliography/local_sources/ocr_priority_queue.tsv"),
    )
    parser.add_argument(
        "--ocr-manifest",
        type=Path,
        default=Path("data/working/bibliography/local_sources/ocr_outputs/ocr_manifest.tsv"),
    )
    parser.add_argument(
        "--ocr-index",
        type=Path,
        default=Path("data/working/bibliography/local_sources/ocr_outputs/ocr_text_index.tsv"),
    )
    parser.add_argument(
        "--documentation-sections",
        type=Path,
        default=Path("data/working/bibliography/local_sources/documentation_abbreviation_sections.tsv"),
    )
    parser.add_argument(
        "--manual-review-packet",
        type=Path,
        default=Path("data/working/bibliography/bibtex_authority/acronym_manual_review_packet.tsv"),
    )
    parser.add_argument(
        "--remaining-acronym-worklist",
        type=Path,
        default=Path("data/working/bibliography/bibtex_authority/remaining_acronym_worklist.tsv"),
    )
    parser.add_argument(
        "--remaining-acronym-evidence",
        type=Path,
        default=Path("data/working/bibliography/bibtex_authority/remaining_acronym_evidence.tsv"),
    )
    parser.add_argument(
        "--source-work-locator-systems",
        type=Path,
        default=Path("data/working/bibliography/bibtex_authority/source_work_locator_systems.tsv"),
    )
    parser.add_argument(
        "--final-acronym-resolution-sprint",
        type=Path,
        default=Path("data/working/bibliography/bibtex_authority/final_acronym_resolution_sprint.tsv"),
    )
    parser.add_argument(
        "--final-acronym-local-file-hits",
        type=Path,
        default=Path("data/working/bibliography/bibtex_authority/final_acronym_local_file_hits.tsv"),
    )
    parser.add_argument(
        "--final-acronym-web-searches",
        type=Path,
        default=Path("data/working/bibliography/bibtex_authority/final_acronym_web_searches.tsv"),
    )
    parser.add_argument(
        "--frasch-abbreviation-list-review",
        type=Path,
        default=Path("data/working/bibliography/bibtex_authority/frasch_abbreviation_list_review.tsv"),
    )
    parser.add_argument(
        "--unresolved-acronym-dossier",
        type=Path,
        default=Path("data/working/bibliography/bibtex_authority/unresolved_acronym_dossier.tsv"),
    )
    parser.add_argument(
        "--source-work-authority",
        type=Path,
        default=Path("data/working/bibliography/bibtex_authority/source_work_authority.tsv"),
    )
    parser.add_argument(
        "--source-work-authority-audit",
        type=Path,
        default=Path("data/working/bibliography/bibtex_authority/source_work_authority_audit.tsv"),
    )
    parser.add_argument(
        "--source-work-to-bibtex-reconciliation",
        type=Path,
        default=Path("data/working/bibliography/bibtex_authority/source_work_to_bibtex_reconciliation.tsv"),
    )
    parser.add_argument(
        "--bibtex-field-quality-audit",
        type=Path,
        default=Path("data/working/bibliography/bibtex_authority/bibtex_field_quality_audit.tsv"),
    )
    parser.add_argument(
        "--authority-key-normalization",
        type=Path,
        default=Path("data/working/bibliography/bibtex_authority/authority_key_normalization.tsv"),
    )
    parser.add_argument(
        "--raw-reference-crosswalk-audit",
        type=Path,
        default=Path("data/working/bibliography/bibtex_authority/raw_reference_crosswalk_audit.tsv"),
    )
    parser.add_argument(
        "--candidate-stub-review",
        type=Path,
        default=Path("data/working/bibliography/bibtex_authority/candidate_stub_review.tsv"),
    )
    parser.add_argument(
        "--ippa-occurrence-contexts",
        type=Path,
        default=Path("data/working/bibliography/bibtex_authority/ippa_occurrence_contexts.tsv"),
    )
    parser.add_argument(
        "--ippa-ppa-comparison",
        type=Path,
        default=Path("data/working/bibliography/bibtex_authority/ippa_ppa_comparison.tsv"),
    )
    parser.add_argument(
        "--ippa-local-context-search",
        type=Path,
        default=Path("data/working/bibliography/bibtex_authority/ippa_local_context_search.tsv"),
    )
    parser.add_argument(
        "--ippa-frasch-abbrev-neighbourhood",
        type=Path,
        default=Path("data/working/bibliography/bibtex_authority/ippa_frasch_abbrev_neighbourhood.tsv"),
    )
    parser.add_argument(
        "--ippa-record-review",
        type=Path,
        default=Path("data/working/bibliography/bibtex_authority/ippa_record_review.tsv"),
    )
    parser.add_argument(
        "--ippa-targeted-ocr-notes",
        type=Path,
        default=Path("data/working/bibliography/bibtex_authority/ippa_targeted_ocr_notes.tsv"),
    )
    parser.add_argument(
        "--ippa-resolution-decision",
        type=Path,
        default=Path("data/working/bibliography/bibtex_authority/ippa_resolution_decision.tsv"),
    )
    parser.add_argument(
        "--reference-occurrences",
        type=Path,
        default=Path("data/working/bibliography/reference_occurrences.tsv"),
    )
    args = parser.parse_args()

    result = validate_bibtex_authority(
        authority_bib_path=args.authority_bib,
        candidates_bib_path=args.candidate_bib,
        authority_tsv_path=args.authority_tsv,
        crosswalk_path=args.crosswalk,
        families_path=args.families,
        external_entries_path=args.external_entries,
        seed_path=args.seed_path,
        high_frequency_path=args.high_frequency,
        evidence_path=args.evidence_path,
        resolution_plan_path=args.resolution_plan,
        source_family_path=args.source_family_path,
        report_path=args.report_path,
        frasch_references_path=args.frasch_references,
        local_manifest_path=args.local_manifest,
        acronym_status_path=args.acronym_status,
        acronym_candidates_path=args.acronym_candidates,
        acronym_report_path=args.acronym_report,
        manual_acronym_seeds_path=args.manual_acronym_seeds,
        ocr_queue_path=args.ocr_queue,
        ocr_manifest_path=args.ocr_manifest,
        ocr_index_path=args.ocr_index,
        documentation_sections_path=args.documentation_sections,
        manual_review_packet_path=args.manual_review_packet,
        remaining_acronym_worklist_path=args.remaining_acronym_worklist,
        remaining_acronym_evidence_path=args.remaining_acronym_evidence,
        source_work_locator_systems_path=args.source_work_locator_systems,
        final_acronym_resolution_sprint_path=args.final_acronym_resolution_sprint,
        final_acronym_local_file_hits_path=args.final_acronym_local_file_hits,
        final_acronym_web_searches_path=args.final_acronym_web_searches,
        frasch_abbreviation_list_review_path=args.frasch_abbreviation_list_review,
        unresolved_acronym_dossier_path=args.unresolved_acronym_dossier,
        source_work_authority_path=args.source_work_authority,
        source_work_authority_audit_path=args.source_work_authority_audit,
        source_work_to_bibtex_reconciliation_path=args.source_work_to_bibtex_reconciliation,
        bibtex_field_quality_audit_path=args.bibtex_field_quality_audit,
        authority_key_normalization_path=args.authority_key_normalization,
        raw_reference_crosswalk_audit_path=args.raw_reference_crosswalk_audit,
        candidate_stub_review_path=args.candidate_stub_review,
        ippa_occurrence_contexts_path=args.ippa_occurrence_contexts,
        ippa_ppa_comparison_path=args.ippa_ppa_comparison,
        ippa_local_context_search_path=args.ippa_local_context_search,
        ippa_frasch_abbrev_neighbourhood_path=args.ippa_frasch_abbrev_neighbourhood,
        ippa_record_review_path=args.ippa_record_review,
        ippa_targeted_ocr_notes_path=args.ippa_targeted_ocr_notes,
        ippa_resolution_decision_path=args.ippa_resolution_decision,
        reference_occurrences_path=args.reference_occurrences,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
