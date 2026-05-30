from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

from build_bibtex_authority import RESOLUTION_LEVELS, RESOLUTION_STATUSES, normalized_expansion_match
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
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path and report_path.exists() else {}
    acronym_report = json.loads(acronym_report_path.read_text(encoding="utf-8")) if acronym_report_path and acronym_report_path.exists() else {}

    authority_keys = {entry["bibtex_key"] for entry in authority_entries}
    candidate_keys = {entry["bibtex_key"] for entry in candidate_entries}
    valid_keys = authority_keys | candidate_keys
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

    for index, row in enumerate(crosswalk_rows, start=1):
        if row["match_type"] != "no_match" and row["bibtex_key"] and row["bibtex_key"] not in valid_keys:
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
            if row["source_of_authority"] == "frasch_bibliography" and row.get("matched_local_source_id") and row["matched_local_source_id"] not in frasch_ids:
                errors.append(f"bibtex_authority[{index}] references missing Frasch ref ID {row['matched_local_source_id']}")
            if row["source_of_authority"] != "frasch_bibliography" and row.get("matched_local_source_id") and row["matched_local_source_id"] not in manifest_ids and row["source_of_authority"] != "external_bibtex":
                errors.append(f"bibtex_authority[{index}] references missing local manifest ID {row['matched_local_source_id']}")
            if row["bibtex_key"] not in evidence_by_key:
                errors.append(f"bibtex_authority[{index}] is evidence-backed but missing bibtex_authority_evidence.tsv row")
        if source_family_rows and row.get("source_family_id") and row["source_family_id"] not in evidence_by_source_family:
            errors.append(f"bibtex_authority[{index}] source family {row['source_family_id']} lacks evidence row")
        if len(row.get("matched_local_reference", "")) > MAX_MATCHED_LOCAL_REFERENCE_LENGTH:
            errors.append(f"bibtex_authority[{index}] has long matched_local_reference")
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
                    if row["source_family_id"] not in evidence_by_source_family:
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
                "confirmed_expansion",
                "probable_expansion",
                "source_family_only",
                "contextual_usage_only",
                "unresolved",
                "not_an_acronym",
                "internal_locator",
            }
            strong_statuses = {"confirmed_expansion", "probable_expansion"}
            review_required = {"source_family_only", "contextual_usage_only", "unresolved"}
            for acronym in PRIORITY_ACRONYMS:
                if acronym not in acronym_status_by_acronym:
                    errors.append(f"acronym_resolution_status.tsv is missing priority acronym {acronym}")
            for index, row in enumerate(acronym_status_rows, start=1):
                status = row.get("resolution_status", "")
                evidence_id = row.get("best_evidence_id", "")
                candidate_row = acronym_candidate_by_id.get(evidence_id)
                if status not in allowed_acronym_statuses:
                    errors.append(f"acronym_resolution_status[{index}] has invalid resolution_status {status}")
                if status in review_required and row.get("needs_human_review") != "true":
                    errors.append(f"acronym_resolution_status[{index}] should require human review for {status}")
                if status == "contextual_usage_only" and row.get("best_evidence_id"):
                    if candidate_row and candidate_row.get("evidence_type") in STRONG_DEFINITION_EVIDENCE_TYPES:
                        errors.append(f"acronym_resolution_status[{index}] marks strong evidence as contextual usage only")
                if status in strong_statuses:
                    if not candidate_row and not evidence_id.startswith("manual-seed:"):
                        errors.append(f"acronym_resolution_status[{index}] requires strong evidence for {status}")
                    if candidate_row and candidate_row.get("evidence_type") not in STRONG_DEFINITION_EVIDENCE_TYPES and candidate_row.get("definition_quality") != "manual_seed":
                        errors.append(f"acronym_resolution_status[{index}] requires strong evidence for {status}")
                    if not candidate_supports_strong_expansion(candidate_row) and not evidence_id.startswith("manual-seed:"):
                        errors.append(f"acronym_resolution_status[{index}] lacks explicit or strong definition evidence for {status}")
                    if len(row.get("best_evidence_quote", "")) > MAX_STRONG_DEFINITION_QUOTE_LENGTH:
                        errors.append(f"acronym_resolution_status[{index}] best_evidence_quote exceeds {MAX_STRONG_DEFINITION_QUOTE_LENGTH} characters")
                if status == "confirmed_expansion" and not row.get("current_expansion"):
                    errors.append(f"acronym_resolution_status[{index}] confirmed expansion is missing current_expansion")
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
            if acronym_status in {"confirmed_expansion", "probable_expansion"} and row.get("best_definition_evidence_id"):
                candidate_row = acronym_candidate_by_id.get(row["best_definition_evidence_id"])
                if row["best_definition_evidence_id"].startswith("manual-seed:"):
                    pass
                elif not candidate_row or candidate_row.get("evidence_type") not in STRONG_DEFINITION_EVIDENCE_TYPES:
                    errors.append(f"source_family_authority[{index}] has non-strong definition evidence")
            if acronym_status in {"source_family_only", "contextual_usage_only", "unresolved"} and row.get("needs_human_review") != "true":
                errors.append(f"source_family_authority[{index}] must keep needs_human_review=true for unresolved acronym state")

    if report:
        plan_family_ids = {row["family_id"] for row in resolution_plan_rows}
        unresolved_ids = {row["family_id"] for row in resolution_plan_rows if row.get("resolution_status") == "unresolved"}
        for row in report.get("top_unresolved_families", []):
            if row.get("family_id") in plan_family_ids and row.get("family_id") not in unresolved_ids:
                errors.append(f"report top_unresolved_families includes resolved family {row.get('family_id')}")
                break
        if report.get("priority_acronym_count") and report.get("priority_acronym_count") != len(PRIORITY_ACRONYMS):
            errors.append("report priority_acronym_count does not match configured priority acronym list")
        weak_statuses = {"probable_expansion", "source_family_only", "contextual_usage_only"}
        expected_weak = sorted(row["acronym"] for row in acronym_status_rows if row.get("acronym") in PRIORITY_ACRONYMS and row.get("resolution_status") in weak_statuses)
        if sorted(report.get("weakly_resolved_priority_acronyms", [])) != expected_weak:
            errors.append("report weakly_resolved_priority_acronyms does not match acronym_resolution_status.tsv")
        if report.get("manual_acronym_seed_count") != len(manual_seed_rows):
            errors.append("report manual_acronym_seed_count does not match manual_acronym_seeds.tsv")
        if report.get("manual_review_packet_rows") != len(manual_review_packet_rows):
            errors.append("report manual_review_packet_rows does not match acronym_manual_review_packet.tsv")

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
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
