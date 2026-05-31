from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

from corpus_common import REPO_ROOT, read_tsv
from discover_translation_sources import (
    DISCOVERY_DIRECTORY,
    DISCOVERY_STATUSES,
    LIKELIHOOD_VALUES,
    PERIODICAL_PLAN_KEYS,
    PLAN_PATH,
    PLAN_DISCOVERY_FIELDS,
    SOURCE_WORK_AUTHORITY_PATH,
    WITNESS_TYPES,
)
from verify_translation_witnesses import (
    ACQUISITION_ACTION_QUEUE_PATH,
    ACQUISITION_STATUSES,
    ACQUISITION_REVIEW_GAP_TYPES,
    CATALOGUE_MATCH_ASSESSMENTS,
    CATALOGUE_RECORD_GAP_TYPES,
    CATALOGUE_RESULT_STATUSES,
    CONTENT_PROFILE_STATUSES,
    CORE_SOURCE_DIRECT_SEARCH_PATH,
    DIRECT_WITNESS_ACQUISITION_SOURCE_KEYS,
    DIRECT_WITNESS_ACQUISITION_PLAN_PATH,
    DIRECT_WITNESS_ACQUISITION_STATUS_PATH,
    DIRECT_SEARCH_RESULT_STATUSES,
    DIRECTNESS_VALUES,
    EB_FASCICLE_CONTENT_INSPECTION_PATH,
    EVIDENCE_QUALITY_VALUES,
    EPIGRAPHIA_BIRMANICA_FASCICLE_COVERAGE_PATH,
    EPIGRAPHIA_BIRMANICA_REVIEW_PATH,
    EXTERNAL_CATALOGUE_STATUSES,
    EXTERNAL_CATALOGUE_CANDIDATE_TRIAGE_PATH,
    EXTERNAL_CATALOGUE_SEARCH_LOG_PATH,
    EXTERNAL_CATALOGUE_TRIAGE_STATUSES,
    HUMAN_ACQUISITION_CHECKLIST_PATH,
    HUNT_CANDIDATE_TRIAGE_STATUSES,
    INSCRIPTIONS_OF_BURMA_TEXT_SEARCH_PATH,
    INSCRIPTIONS_OF_BURMA_TEXT_VOLUME_HUNT_PATH,
    LOCAL_DIRECT_WITNESS_STATUSES,
    MANUAL_REVIEW_QUEUE_PATH,
    MISSING_DIRECT_SEARCH_PATH,
    MISSING_CORE_WITNESS_HUNT_QUERIES,
    MISSING_CORE_WITNESS_HUNT_PATH,
    NON_PROMOTABLE_HUNT_TRIAGE_STATUSES,
    OPEN_DIRECT_WITNESS_GAP_TYPES,
    PLAUSIBLE_HUNT_TRIAGE_STATUSES,
    RESCUE_CANDIDATE_REVIEW_PATH,
    RULED_OUT_WITNESS_CANDIDATES_PATH,
    SIP_WITNESS_ID,
    SIP_WITNESS_INSPECTION_PATH,
    SOURCE_WITNESS_CONTENT_PROFILE_PATH,
    SOURCE_WORK_GAPS_PATH,
    TRANSLATION_SOURCE_DISCOVERY_PHASE_SUMMARY_PATH,
    TRANSLATION_COVERAGE_STATUSES,
    UEM_DIRECT_SEARCH_PATH,
    VERIFICATION_STATUSES,
    WITNESS_HUNT_CANDIDATE_TRIAGE_PATH,
    WITNESS_SNIPPETS_PATH,
    WITNESS_VERIFICATION_PATH,
    WITNESS_VERIFICATION_REPORT_PATH,
    has_plausible_iob_text_signal,
)


ABSOLUTE_PATH_PATTERN = re.compile(r"(^/(?:Users|home|var|private|tmp|opt|Volumes)\b|^[A-Za-z]:\\\\)")
SHORT_EVIDENCE_LIMIT = 280
DIRECT_VERIFICATION_STATUSES = {"verified_direct_witness", "verified_catalogue_witness"}
OPEN_DIRECT_WITNESS_GAP_SOURCE_KEYS = {
    "uemSelectionsPagan",
    "tnInscriptionsPaganPinyaAva",
    "ppaCatalogue",
    "ubSourceFamily",
    "lucePeMaungTinInscriptionsOfBurma",
}
FOLLOW_ON_PLAN_SOURCE_KEYS = {"sipSelectionsPagan", "epigraphiaBirmanica"}


def has_explicit_translation_signal(snippet: str, notes: str = "") -> bool:
    lowered = f"{snippet} {notes}".casefold()
    return any(keyword in lowered for keyword in ["translation", "translated", "parallel", "interlinear", "gloss"])


def hunt_row_key(hunt_table: str, row: dict, *, default_source_work_key: str = "") -> tuple[str, str, str, str, str]:
    return (
        hunt_table,
        row.get("source_work_key", default_source_work_key),
        row.get("query", ""),
        row.get("matched_file_id", ""),
        row.get("matched_file_label", ""),
    )


def ruled_out_candidate_key(source_work_key: str, candidate_id: str, candidate_label: str, category: str) -> tuple[str, str, str]:
    return (source_work_key, candidate_id or candidate_label, category)


def validate_translation_source_discovery(
    *,
    plan_path: Path = PLAN_PATH,
    source_work_authority_path: Path = SOURCE_WORK_AUTHORITY_PATH,
    witness_candidates_path: Path = DISCOVERY_DIRECTORY / "witness_candidates.tsv",
    witness_classification_path: Path = DISCOVERY_DIRECTORY / "witness_classification.tsv",
    witness_verification_path: Path = WITNESS_VERIFICATION_PATH,
    witness_snippets_path: Path = WITNESS_SNIPPETS_PATH,
    missing_direct_search_path: Path = MISSING_DIRECT_SEARCH_PATH,
    source_work_gaps_path: Path = SOURCE_WORK_GAPS_PATH,
    sip_witness_inspection_path: Path = SIP_WITNESS_INSPECTION_PATH,
    source_witness_content_profile_path: Path = SOURCE_WITNESS_CONTENT_PROFILE_PATH,
    eb_fascicle_content_inspection_path: Path = EB_FASCICLE_CONTENT_INSPECTION_PATH,
    uem_direct_search_path: Path = UEM_DIRECT_SEARCH_PATH,
    core_source_direct_search_path: Path = CORE_SOURCE_DIRECT_SEARCH_PATH,
    inscriptions_of_burma_text_search_path: Path = INSCRIPTIONS_OF_BURMA_TEXT_SEARCH_PATH,
    inscriptions_of_burma_text_volume_hunt_path: Path = INSCRIPTIONS_OF_BURMA_TEXT_VOLUME_HUNT_PATH,
    missing_core_witness_hunt_path: Path = MISSING_CORE_WITNESS_HUNT_PATH,
    witness_hunt_candidate_triage_path: Path = WITNESS_HUNT_CANDIDATE_TRIAGE_PATH,
    direct_witness_acquisition_plan_path: Path = DIRECT_WITNESS_ACQUISITION_PLAN_PATH,
    direct_witness_acquisition_status_path: Path = DIRECT_WITNESS_ACQUISITION_STATUS_PATH,
    manual_review_queue_path: Path = MANUAL_REVIEW_QUEUE_PATH,
    acquisition_action_queue_path: Path = ACQUISITION_ACTION_QUEUE_PATH,
    translation_source_discovery_phase_summary_path: Path = TRANSLATION_SOURCE_DISCOVERY_PHASE_SUMMARY_PATH,
    human_acquisition_checklist_path: Path = HUMAN_ACQUISITION_CHECKLIST_PATH,
    ruled_out_witness_candidates_path: Path = RULED_OUT_WITNESS_CANDIDATES_PATH,
    external_catalogue_search_log_path: Path = EXTERNAL_CATALOGUE_SEARCH_LOG_PATH,
    external_catalogue_candidate_triage_path: Path = EXTERNAL_CATALOGUE_CANDIDATE_TRIAGE_PATH,
    rescue_candidate_review_path: Path = RESCUE_CANDIDATE_REVIEW_PATH,
    epigraphia_birmanica_review_path: Path = EPIGRAPHIA_BIRMANICA_REVIEW_PATH,
    epigraphia_birmanica_fascicle_coverage_path: Path = EPIGRAPHIA_BIRMANICA_FASCICLE_COVERAGE_PATH,
    periodical_article_plan_path: Path = DISCOVERY_DIRECTORY / "periodical_article_discovery_plan.tsv",
    report_path: Path = DISCOVERY_DIRECTORY / "translation_source_discovery_report.json",
    witness_verification_report_path: Path = WITNESS_VERIFICATION_REPORT_PATH,
) -> list[str]:
    errors: list[str] = []
    for path in [
        plan_path,
        source_work_authority_path,
        witness_candidates_path,
        witness_classification_path,
        witness_verification_path,
        witness_snippets_path,
        missing_direct_search_path,
        source_work_gaps_path,
        sip_witness_inspection_path,
        source_witness_content_profile_path,
        eb_fascicle_content_inspection_path,
        uem_direct_search_path,
        core_source_direct_search_path,
        inscriptions_of_burma_text_search_path,
        inscriptions_of_burma_text_volume_hunt_path,
        missing_core_witness_hunt_path,
        witness_hunt_candidate_triage_path,
        direct_witness_acquisition_plan_path,
        direct_witness_acquisition_status_path,
        manual_review_queue_path,
        acquisition_action_queue_path,
        translation_source_discovery_phase_summary_path,
        human_acquisition_checklist_path,
        ruled_out_witness_candidates_path,
        external_catalogue_search_log_path,
        external_catalogue_candidate_triage_path,
        rescue_candidate_review_path,
        epigraphia_birmanica_review_path,
        epigraphia_birmanica_fascicle_coverage_path,
        periodical_article_plan_path,
        report_path,
        witness_verification_report_path,
    ]:
        if not path.exists():
            errors.append(f"Missing required discovery artifact: {path.relative_to(REPO_ROOT)}")
    if errors:
        return errors

    plan_rows = read_tsv(plan_path)
    source_rows = read_tsv(source_work_authority_path)
    candidate_rows = read_tsv(witness_candidates_path)
    classification_rows = read_tsv(witness_classification_path)
    verification_rows = read_tsv(witness_verification_path)
    snippet_rows = read_tsv(witness_snippets_path)
    missing_search_rows = read_tsv(missing_direct_search_path)
    gap_rows = read_tsv(source_work_gaps_path)
    sip_inspection_rows = read_tsv(sip_witness_inspection_path)
    source_witness_content_profile_rows = read_tsv(source_witness_content_profile_path)
    eb_fascicle_content_inspection_rows = read_tsv(eb_fascicle_content_inspection_path)
    uem_search_rows = read_tsv(uem_direct_search_path)
    core_search_rows = read_tsv(core_source_direct_search_path)
    iob_text_search_rows = read_tsv(inscriptions_of_burma_text_search_path)
    iob_text_volume_hunt_rows = read_tsv(inscriptions_of_burma_text_volume_hunt_path)
    missing_core_witness_hunt_rows = read_tsv(missing_core_witness_hunt_path)
    witness_hunt_candidate_triage_rows = read_tsv(witness_hunt_candidate_triage_path)
    direct_witness_acquisition_plan_rows = read_tsv(direct_witness_acquisition_plan_path)
    direct_witness_acquisition_status_rows = read_tsv(direct_witness_acquisition_status_path)
    manual_review_queue_rows = read_tsv(manual_review_queue_path)
    acquisition_action_queue_rows = read_tsv(acquisition_action_queue_path)
    human_acquisition_checklist_rows = read_tsv(human_acquisition_checklist_path)
    ruled_out_witness_candidate_rows = read_tsv(ruled_out_witness_candidates_path)
    external_catalogue_search_log_rows = read_tsv(external_catalogue_search_log_path)
    external_catalogue_candidate_triage_rows = read_tsv(external_catalogue_candidate_triage_path)
    rescue_review_rows = read_tsv(rescue_candidate_review_path)
    epigraphia_review_rows = read_tsv(epigraphia_birmanica_review_path)
    epigraphia_fascicle_coverage_rows = read_tsv(epigraphia_birmanica_fascicle_coverage_path)
    periodical_plan_rows = read_tsv(periodical_article_plan_path)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    verification_report = json.loads(witness_verification_report_path.read_text(encoding="utf-8"))
    phase_summary_text = translation_source_discovery_phase_summary_path.read_text(encoding="utf-8")

    source_by_key = {row["source_work_key"]: row for row in source_rows}
    candidate_by_id = {row["witness_id"]: row for row in candidate_rows}
    verification_by_id = {row["witness_id"]: row for row in verification_rows}
    gap_by_source = {row["source_work_key"]: row for row in gap_rows}
    candidate_counts: dict[str, int] = {}
    classification_counts: dict[str, int] = {}
    confirmed_translation_counts: dict[str, int] = {}
    confirmed_edition_counts: dict[str, int] = {}
    confirmed_plate_counts: dict[str, int] = {}
    verified_direct_counts: dict[str, int] = {}
    verified_translation_counts: dict[str, int] = {}
    verified_edition_counts: dict[str, int] = {}
    verified_plate_counts: dict[str, int] = {}
    weak_false_positive_counts: dict[str, int] = {}

    for row in candidate_rows:
        source_key = row.get("source_work_key", "")
        candidate_counts[source_key] = candidate_counts.get(source_key, 0) + 1
        if source_key not in source_by_key:
            errors.append(f"Witness candidate {row['witness_id']} references unknown source_work_key {source_key}")
        if ABSOLUTE_PATH_PATTERN.search(row.get("candidate_path_or_redacted_path", "")):
            errors.append(f"Witness candidate {row['witness_id']} stores an absolute path")

    for row in classification_rows:
        witness_id = row.get("witness_id", "")
        source_key = row.get("source_work_key", "")
        classification_counts[source_key] = classification_counts.get(source_key, 0) + 1
        if witness_id not in candidate_by_id:
            errors.append(f"Witness classification {witness_id} has no matching witness candidate row")
        if source_key not in source_by_key:
            errors.append(f"Witness classification {witness_id} references unknown source_work_key {source_key}")
        if row.get("witness_type") not in WITNESS_TYPES:
            errors.append(f"Witness classification {witness_id} uses invalid witness_type {row.get('witness_type')}")
        for field in [
            "contains_translation",
            "contains_edition_or_transliteration",
            "contains_plate_or_image",
            "contains_catalogue_metadata",
            "contains_secondary_discussion",
        ]:
            if row.get(field) not in LIKELIHOOD_VALUES:
                errors.append(f"Witness classification {witness_id} uses invalid {field} value {row.get(field)}")
        evidence_snippet = row.get("evidence_snippet", "")
        if len(evidence_snippet) > SHORT_EVIDENCE_LIMIT or "\n" in evidence_snippet:
            errors.append(f"Witness classification {witness_id} stores more than a short evidence snippet")
        if row.get("verification_status") and row.get("verification_status") not in VERIFICATION_STATUSES:
            errors.append(f"Witness classification {witness_id} uses invalid verification_status {row.get('verification_status')}")
        if row.get("directness") and row.get("directness") not in DIRECTNESS_VALUES:
            errors.append(f"Witness classification {witness_id} uses invalid directness {row.get('directness')}")
        if row.get("contains_translation") == "confirmed":
            if not row.get("evidence_source") or not evidence_snippet:
                errors.append(f"Witness classification {witness_id} marks confirmed translation without evidence")
            if row.get("witness_type") == "periodical_container":
                errors.append(f"Witness classification {witness_id} marks a periodical container as a direct translation witness")
            confirmed_translation_counts[source_key] = confirmed_translation_counts.get(source_key, 0) + 1
        if row.get("contains_edition_or_transliteration") == "confirmed":
            confirmed_edition_counts[source_key] = confirmed_edition_counts.get(source_key, 0) + 1
        if row.get("contains_plate_or_image") == "confirmed":
            confirmed_plate_counts[source_key] = confirmed_plate_counts.get(source_key, 0) + 1
        if row.get("witness_type") == "periodical_container" and row.get("contains_translation") in {"possible", "confirmed"}:
            errors.append(f"Witness classification {witness_id} gives direct translation status to a periodical container")
        if source_key in source_by_key:
            source_row = source_by_key[source_key]
            if source_key != "epigraphiaBirmanica" and source_row.get("authority_level") in {"series", "periodical"} and row.get("witness_type") in {
                "translation_source",
                "edition_and_translation",
                "source_edition",
            }:
                errors.append(
                    f"Witness classification {witness_id} promotes series/periodical {source_key} to a direct source witness without article-level handling"
                )

    snippet_count_by_witness: dict[str, int] = {}
    for row in snippet_rows:
        witness_id = row.get("witness_id", "")
        snippet_count_by_witness[witness_id] = snippet_count_by_witness.get(witness_id, 0) + 1
        if witness_id not in candidate_by_id:
            errors.append(f"Witness snippet {witness_id} has no matching witness candidate row")
        if len(row.get("snippet", "")) > SHORT_EVIDENCE_LIMIT or "\n" in row.get("snippet", ""):
            errors.append(f"Witness snippet {witness_id} stores more than a short OCR/title-page snippet")

    for row in verification_rows:
        witness_id = row.get("witness_id", "")
        source_key = row.get("source_work_key", "")
        if witness_id not in candidate_by_id:
            errors.append(f"Witness verification {witness_id} has no matching witness candidate row")
        if source_key not in source_by_key:
            errors.append(f"Witness verification {witness_id} references unknown source_work_key {source_key}")
        if row.get("verification_status") not in VERIFICATION_STATUSES:
            errors.append(f"Witness verification {witness_id} uses invalid verification_status {row.get('verification_status')}")
        if row.get("directness") not in DIRECTNESS_VALUES:
            errors.append(f"Witness verification {witness_id} uses invalid directness {row.get('directness')}")
        if row.get("verified_witness_type") not in WITNESS_TYPES and row.get("verified_witness_type") != "periodical_container":
            errors.append(f"Witness verification {witness_id} uses invalid verified_witness_type {row.get('verified_witness_type')}")
        if row.get("evidence_quality") not in EVIDENCE_QUALITY_VALUES:
            errors.append(f"Witness verification {witness_id} uses invalid evidence_quality {row.get('evidence_quality')}")
        for field in [
            "contains_translation_verified",
            "contains_edition_verified",
            "contains_plate_or_image_verified",
            "contains_catalogue_metadata_verified",
            "contains_secondary_discussion_verified",
        ]:
            if row.get(field) not in LIKELIHOOD_VALUES:
                errors.append(f"Witness verification {witness_id} uses invalid {field} value {row.get(field)}")
        for field in ["title_page_evidence", "toc_evidence", "ocr_or_text_snippet"]:
            if len(row.get(field, "")) > SHORT_EVIDENCE_LIMIT or "\n" in row.get(field, ""):
                errors.append(f"Witness verification {witness_id} stores more than a short evidence field in {field}")
        if row.get("contains_translation_verified") == "confirmed":
            if row.get("evidence_quality") not in {"explicit", "strong"}:
                errors.append(f"Witness verification {witness_id} confirms translation without strong or explicit evidence")
            if not (row.get("title_page_evidence") or row.get("toc_evidence")):
                errors.append(f"Witness verification {witness_id} confirms translation without title-page or contents evidence")
            verified_translation_counts[source_key] = verified_translation_counts.get(source_key, 0) + 1
        if row.get("contains_edition_verified") == "confirmed":
            if row.get("evidence_quality") in {"none", "weak"} and not row.get("title_page_evidence") and not row.get("toc_evidence"):
                errors.append(f"Witness verification {witness_id} confirms edition using filename-only evidence")
            verified_edition_counts[source_key] = verified_edition_counts.get(source_key, 0) + 1
        if row.get("verification_status") == "verified_plate_witness":
            verified_plate_counts[source_key] = verified_plate_counts.get(source_key, 0) + 1
        if row.get("verification_status") in DIRECT_VERIFICATION_STATUSES:
            verified_direct_counts[source_key] = verified_direct_counts.get(source_key, 0) + 1
        if row.get("verification_status") == "weak_false_positive":
            weak_false_positive_counts[source_key] = weak_false_positive_counts.get(source_key, 0) + 1
        if row.get("verification_status") == "weak_false_positive" and row.get("directness") != "weak_related_match":
            errors.append(f"Witness verification {witness_id} should use weak_related_match directness for weak false positives")
        if row.get("verification_status") == "verified_plate_witness" and row.get("contains_plate_or_image_verified") != "confirmed":
            errors.append(f"Witness verification {witness_id} marks a plate witness without confirmed plate evidence")
        if source_key in PERIODICAL_PLAN_KEYS and source_key != "epigraphiaBirmanica" and row.get("verification_status") in DIRECT_VERIFICATION_STATUSES:
            errors.append(f"Witness verification {witness_id} promotes periodical container {source_key} to a direct witness")
        if row.get("verification_status") == "verified_article_candidate" and row.get("directness") not in {"article_about_source", "series_container"}:
            errors.append(f"Witness verification {witness_id} uses invalid directness for an article candidate")
        if row.get("verification_status") in {"verified_direct_witness", "verified_catalogue_witness", "verified_plate_witness"} and snippet_count_by_witness.get(witness_id, 0) == 0 and row.get("evidence_quality") not in {"moderate", "strong", "explicit"}:
            errors.append(f"Witness verification {witness_id} lacks supporting snippet or adequate evidence quality")
        if (
            source_key == "lucePeMaungTinInscriptionsOfBurma"
            and "plate" in row.get("candidate_file_label", "").casefold()
            and row.get("verification_status") in DIRECT_VERIFICATION_STATUSES
        ):
            errors.append(f"Witness verification {witness_id} incorrectly counts an Inscriptions of Burma plate file as a direct text witness")

    sip_verification = verification_by_id.get(SIP_WITNESS_ID)
    if sip_verification and sip_verification.get("contains_edition_verified") == "confirmed":
        supporting_sip_rows = [
            row
            for row in sip_inspection_rows
            if row.get("witness_id") == SIP_WITNESS_ID
            and row.get("contains_edition_or_transliteration") == "confirmed"
            and row.get("evidence_snippet")
        ]
        if not supporting_sip_rows:
            errors.append("SIP edition confirmation lacks supporting sip_witness_inspection evidence")
    if sip_verification and sip_verification.get("contains_translation_verified") == "confirmed":
        supporting_translation_rows = [
            row
            for row in sip_inspection_rows
            if row.get("witness_id") == SIP_WITNESS_ID and row.get("contains_translation") == "confirmed" and row.get("evidence_snippet")
        ]
        if not supporting_translation_rows:
            errors.append("SIP translation confirmation lacks supporting sip_witness_inspection evidence")

    for row in sip_inspection_rows:
        if row.get("witness_id") not in candidate_by_id:
            errors.append(f"SIP inspection row {row.get('witness_id')} has no matching witness candidate row")
        if len(row.get("evidence_snippet", "")) > SHORT_EVIDENCE_LIMIT or "\n" in row.get("evidence_snippet", ""):
            errors.append(f"SIP inspection row {row.get('witness_id')} stores more than a short evidence snippet")
        if row.get("inspection_status") not in {"confirmed", "attempted_no_recoverable_text"}:
            errors.append(f"SIP inspection row {row.get('inspection_area')} uses invalid inspection_status {row.get('inspection_status')!r}")
        for field in ["contains_translation", "contains_edition_or_transliteration", "contains_notes_or_commentary"]:
            if row.get(field) not in CONTENT_PROFILE_STATUSES:
                errors.append(f"SIP inspection row {row.get('inspection_area')} uses invalid {field} value {row.get(field)!r}")
        if row.get("inspection_status") == "attempted_no_recoverable_text" and row.get("contains_translation") in {"false", "not_present"}:
            errors.append("failed OCR should not imply translation absence for SIP inspection rows")
    if sip_inspection_rows and not any(
        row.get("inspection_area") in {"contents", "preface", "sample_entry", "headings", "notes_or_commentary"}
        for row in sip_inspection_rows
    ):
        errors.append("SIP inspection remains title-page only; sample-entry or other follow-on inspection rows are required")
    sip_sample_entry_row = next((row for row in sip_inspection_rows if row.get("inspection_area") == "sample_entry"), None)
    if sip_sample_entry_row and sip_sample_entry_row.get("inspection_status") == "attempted_no_recoverable_text":
        if report.get("sip_sample_entry_inspected") is True:
            errors.append("sip_sample_entry_inspected cannot be true when sample-entry OCR was unrecoverable")
        if report.get("sip_translation_status") == "confirmed":
            errors.append("failed sample-entry OCR cannot confirm SIP translation coverage")

    if not source_witness_content_profile_rows:
        errors.append("source_witness_content_profile.tsv should exist")
    if not eb_fascicle_content_inspection_rows:
        errors.append("eb_fascicle_content_inspection.tsv should exist")
    if not iob_text_volume_hunt_rows:
        errors.append("inscriptions_of_burma_text_volume_hunt.tsv should exist")
    if not missing_core_witness_hunt_rows:
        errors.append("missing_core_witness_hunt.tsv should exist")

    eb_verified_direct_ids = {
        row.get("witness_id", "")
        for row in verification_rows
        if row.get("source_work_key") == "epigraphiaBirmanica" and row.get("verification_status") in DIRECT_VERIFICATION_STATUSES
    }
    content_profile_by_id = {row.get("witness_id", ""): row for row in source_witness_content_profile_rows}
    missing_profile_ids = sorted(witness_id for witness_id in eb_verified_direct_ids if witness_id not in content_profile_by_id)
    if missing_profile_ids:
        errors.append(f"EB direct witnesses missing content-profile rows: {', '.join(missing_profile_ids)}")
    for row in source_witness_content_profile_rows:
        for field in [
            "content_profile_status",
            "title_page_status",
            "contents_status",
            "sample_entry_status",
            "translation_status",
            "edition_status",
            "notes_commentary_status",
            "plate_image_status",
            "catalogue_metadata_status",
        ]:
            if row.get(field) not in CONTENT_PROFILE_STATUSES:
                errors.append(f"Source witness content profile {row.get('witness_id')} uses invalid {field} value {row.get(field)!r}")
        if row.get("source_work_key") == "lucePeMaungTinInscriptionsOfBurma" and "plate" in row.get("verified_witness_type", ""):
            if row.get("sample_entry_status") != "not_applicable":
                errors.append(f"IOB plate content profile {row.get('witness_id')} must use sample_entry_status=not_applicable")
            if row.get("translation_status") != "not_applicable" or row.get("edition_status") != "not_applicable":
                errors.append(f"IOB plate content profile {row.get('witness_id')} must keep translation and edition statuses not_applicable")
            if row.get("next_action") != "Retain as a plate/facsimile witness and continue hunting the companion text volume.":
                errors.append(f"IOB plate content profile {row.get('witness_id')} has the wrong next_action")
    for row in eb_fascicle_content_inspection_rows:
        if row.get("inspection_status") not in {"confirmed", "attempted_no_recoverable_text"}:
            errors.append(
                f"EB fascicle content inspection row {row.get('witness_id')}:{row.get('inspection_area')} uses invalid inspection_status"
            )
        for field in [
            "contains_translation",
            "contains_edition_or_transliteration",
            "contains_notes_or_commentary",
            "contains_plate_or_image",
        ]:
            if row.get(field) not in CONTENT_PROFILE_STATUSES:
                errors.append(
                    f"EB fascicle content inspection row {row.get('witness_id')}:{row.get('inspection_area')} uses invalid {field}"
                )
    confirmed_translation_profile_ids = {
        row.get("witness_id", "") for row in source_witness_content_profile_rows if row.get("translation_status") == "confirmed"
    }
    explicit_translation_evidence_ids = {
        row.get("witness_id", "")
        for row in sip_inspection_rows + eb_fascicle_content_inspection_rows
        if row.get("contains_translation") == "confirmed"
        and (row.get("evidence_snippet") or row.get("short_snippet"))
        and has_explicit_translation_signal(row.get("evidence_snippet", "") or row.get("short_snippet", ""), row.get("notes", ""))
    }
    unsupported_translation_ids = sorted(witness_id for witness_id in confirmed_translation_profile_ids if witness_id not in explicit_translation_evidence_ids)
    if unsupported_translation_ids:
        errors.append(
            "translation confirmed content profiles require explicit snippet evidence: "
            + ", ".join(unsupported_translation_ids)
        )

    for row in missing_search_rows:
        source_key = row.get("source_work_key", "")
        if source_key not in source_by_key:
            errors.append(f"Missing-direct search row references unknown source_work_key {source_key}")
        if row.get("matched_file_label") and ABSOLUTE_PATH_PATTERN.search(row.get("notes", "")):
            errors.append(f"Missing-direct search row for {source_key} stores an absolute path")

    for collection_name, rows in [
        ("UEM direct search", uem_search_rows),
        ("core direct search", core_search_rows),
        ("Inscriptions of Burma text search", iob_text_search_rows),
        ("Inscriptions of Burma text volume hunt", iob_text_volume_hunt_rows),
    ]:
        for row in rows:
            for field in ["searched_sources", "search_scope", "search_date_or_run_id", "search_result_status"]:
                if not row.get(field):
                    errors.append(f"{collection_name} row for {row.get('query', '') or row.get('source_work_key', '')} is missing {field}")
            if row.get("search_result_status") not in DIRECT_SEARCH_RESULT_STATUSES:
                errors.append(f"{collection_name} row uses invalid search_result_status {row.get('search_result_status')}")
    for row in missing_core_witness_hunt_rows:
        for field in ["searched_sources", "search_scope", "search_date_or_run_id", "search_result_status"]:
            if not row.get(field):
                errors.append(f"missing core witness hunt row for {row.get('source_work_key')}:{row.get('query')} is missing {field}")
        if row.get("search_result_status") not in DIRECT_SEARCH_RESULT_STATUSES:
            errors.append(f"missing core witness hunt row for {row.get('source_work_key')}:{row.get('query')} uses invalid search_result_status")
    expected_hunt_queries = {
        source_key: {query for query, _variant_type in query_rows}
        for source_key, query_rows in MISSING_CORE_WITNESS_HUNT_QUERIES.items()
    }
    observed_hunt_queries: dict[str, set[str]] = {}
    for row in missing_core_witness_hunt_rows:
        observed_hunt_queries.setdefault(row.get("source_work_key", ""), set()).add(row.get("query", ""))
        if row.get("search_result_status") == "not_found":
            if row.get("match_type") != "not_found" or row.get("match_confidence") != "low":
                errors.append(f"missing core witness hunt no-hit row {row.get('source_work_key')}:{row.get('query')} must use match_type=not_found and match_confidence=low")
            if row.get("matched_file_label") or row.get("matched_file_id"):
                errors.append(f"missing core witness hunt no-hit row {row.get('source_work_key')}:{row.get('query')} must keep matched fields empty")
    for source_key, expected_queries in expected_hunt_queries.items():
        missing_queries = sorted(expected_queries - observed_hunt_queries.get(source_key, set()))
        if missing_queries:
            errors.append(f"missing core witness hunt is missing expected queries for {source_key}: {', '.join(missing_queries)}")

    triage_by_key = {
        hunt_row_key(row.get("hunt_table", ""), row): row
        for row in witness_hunt_candidate_triage_rows
    }
    for row in witness_hunt_candidate_triage_rows:
        if row.get("triage_status") not in HUNT_CANDIDATE_TRIAGE_STATUSES:
            errors.append(
                f"witness_hunt_candidate_triage row {row.get('hunt_table')}:{row.get('source_work_key')}:{row.get('query')} uses invalid triage_status"
            )
    candidate_hunt_rows = [
        ("missing_core_witness_hunt", row, "")
        for row in missing_core_witness_hunt_rows
        if row.get("search_result_status") == "candidate_found" and row.get("matched_file_label")
    ] + [
        ("inscriptions_of_burma_text_volume_hunt", row, "lucePeMaungTinInscriptionsOfBurma")
        for row in iob_text_volume_hunt_rows
        if row.get("search_result_status") == "candidate_found" and row.get("matched_file_label")
    ]
    for hunt_table, row, default_source_key in candidate_hunt_rows:
        key = hunt_row_key(hunt_table, row, default_source_work_key=default_source_key)
        if key not in triage_by_key:
            errors.append(
                f"witness_hunt_candidate_triage.tsv is missing coverage for {hunt_table}:{row.get('source_work_key', default_source_key)}:{row.get('query')}"
            )

    for row in iob_text_volume_hunt_rows:
        label = row.get("matched_file_label", "")
        triage_row = triage_by_key.get(hunt_row_key("inscriptions_of_burma_text_volume_hunt", row, default_source_work_key="lucePeMaungTinInscriptionsOfBurma"))
        if row.get("search_result_status") == "candidate_found" and label and not triage_row:
            continue
        if row.get("is_text_witness_candidate") == "true":
            if not triage_row or triage_row.get("triage_status") not in PLAUSIBLE_HUNT_TRIAGE_STATUSES:
                errors.append(f"Inscriptions of Burma text-volume hunt row {label or row.get('query')} cannot remain a text candidate without plausible triage")
            elif not has_plausible_iob_text_signal(row):
                errors.append(f"Inscriptions of Burma text-volume hunt row {label or row.get('query')} lacks a plausible IOB-specific title/path signal")
        if label == "a_list_of_inscriptions_found_in_burma_part_i.pdf":
            if row.get("is_text_witness_candidate") != "false":
                errors.append("a_list_of_inscriptions_found_in_burma_part_i.pdf cannot count as an IOB text witness candidate")
            if not triage_row or triage_row.get("triage_status") != "cross_source_witness":
                errors.append("a_list_of_inscriptions_found_in_burma_part_i.pdf must be triaged as a cross-source witness")
        if label == "111029.pdf":
            if row.get("is_text_witness_candidate") != "false":
                errors.append("111029.pdf cannot count as an IOB text witness candidate")
            if not triage_row or triage_row.get("triage_status") != "secondary_or_unrelated":
                errors.append("111029.pdf must be triaged as a reviewed secondary/cross-source lead")

    for row in missing_core_witness_hunt_rows:
        if row.get("search_result_status") != "candidate_found" or not row.get("matched_file_label"):
            continue
        triage_row = triage_by_key.get(hunt_row_key("missing_core_witness_hunt", row))
        if not triage_row:
            continue
        normalized = f"{row.get('matched_file_label', '')} {row.get('short_evidence', '')} {row.get('notes', '')}".casefold()
        if row.get("source_work_key") == "uemSelectionsPagan" and (
            "pemaungtin" in normalized or "maunggyi" in normalized or "jbrs" in normalized
        ):
            if triage_row.get("triage_status") not in NON_PROMOTABLE_HUNT_TRIAGE_STATUSES:
                errors.append(f"Broad UEM hunt row {row.get('query')}:{row.get('matched_file_label')} must be triaged as non-promotable")
            if "do not promote" not in row.get("recommended_action", "").casefold():
                errors.append(f"Broad UEM hunt row {row.get('query')}:{row.get('matched_file_label')} cannot keep a promotable recommended_action")

    acquisition_plan_by_source = {
        row.get("source_work_key", ""): row
        for row in direct_witness_acquisition_plan_rows
    }
    acquisition_status_by_source = {
        row.get("source_work_key", ""): row
        for row in direct_witness_acquisition_status_rows
    }
    acquisition_actions_by_source = defaultdict(list)
    for row in direct_witness_acquisition_plan_rows:
        source_key = row.get("source_work_key", "")
        if source_key not in source_by_key:
            errors.append(f"direct_witness_acquisition_plan.tsv references unknown source_work_key {source_key}")
        if not row.get("recommended_next_action"):
            errors.append(f"direct_witness_acquisition_plan.tsv row {source_key} is missing recommended_next_action")
        if not row.get("priority"):
            errors.append(f"direct_witness_acquisition_plan.tsv row {source_key} is missing priority")
        if source_key == "uemSelectionsPagan" and row.get("known_or_expected_year") != "1958":
            errors.append("UEM acquisition-plan row should keep 1958 in known_or_expected_year")
        if source_key == "tnInscriptionsPaganPinyaAva":
            if row.get("known_or_expected_year") != "1897":
                errors.append("TN acquisition-plan row should keep 1897 in known_or_expected_year")
            if "government printing" not in row.get("known_or_expected_publisher_or_series", "").casefold():
                errors.append("TN acquisition-plan row should surface Government Printing in known_or_expected_publisher_or_series")
        if source_key in {"ppaCatalogue", "ubSourceFamily"}:
            if not row.get("known_or_expected_year"):
                errors.append(f"{source_key} acquisition-plan row should use 'unknown' instead of a blank known_or_expected_year")
            if not row.get("known_or_expected_publisher_or_series"):
                errors.append(f"{source_key} acquisition-plan row should use 'unknown' or a cautious publisher clue instead of a blank publisher field")
    for row in direct_witness_acquisition_status_rows:
        source_key = row.get("source_work_key", "")
        if source_key not in source_by_key:
            errors.append(f"direct_witness_acquisition_status.tsv references unknown source_work_key {source_key}")
        if source_key not in acquisition_plan_by_source:
            errors.append(f"direct_witness_acquisition_status.tsv row {source_key} has no matching direct_witness_acquisition_plan.tsv row")
        if row.get("local_direct_witness_status") not in LOCAL_DIRECT_WITNESS_STATUSES:
            errors.append(f"direct_witness_acquisition_status.tsv row {source_key} uses invalid local_direct_witness_status")
        if row.get("external_catalogue_status") not in EXTERNAL_CATALOGUE_STATUSES:
            errors.append(f"direct_witness_acquisition_status.tsv row {source_key} uses invalid external_catalogue_status")
        if row.get("acquisition_status") not in ACQUISITION_STATUSES:
            errors.append(f"direct_witness_acquisition_status.tsv row {source_key} uses invalid acquisition_status")
        if row.get("translation_coverage_status") not in TRANSLATION_COVERAGE_STATUSES:
            errors.append(f"direct_witness_acquisition_status.tsv row {source_key} uses invalid translation_coverage_status")
        if not row.get("priority"):
            errors.append(f"direct_witness_acquisition_status.tsv row {source_key} is missing priority")
        for field in ["current_blocker", "next_action", "notes"]:
            if len(row.get(field, "")) > SHORT_EVIDENCE_LIMIT or "\n" in row.get(field, ""):
                errors.append(f"direct_witness_acquisition_status.tsv row {source_key} stores more than a short field in {field}")
    for source_key in acquisition_plan_by_source:
        if source_key not in acquisition_status_by_source:
            errors.append(f"direct_witness_acquisition_plan.tsv row {source_key} is missing a direct_witness_acquisition_status.tsv row")
    for row in acquisition_action_queue_rows:
        source_key = row.get("source_work_key", "")
        acquisition_actions_by_source[source_key].append(row)
        if source_key not in source_by_key:
            errors.append(f"acquisition_action_queue.tsv references unknown source_work_key {source_key}")
        if len(row.get("authority_evidence", "")) > SHORT_EVIDENCE_LIMIT or "\n" in row.get("authority_evidence", ""):
            errors.append(f"acquisition_action_queue.tsv row {row.get('action_id', source_key)} stores more than a short authority_evidence snippet")

    external_log_by_source = defaultdict(list)
    external_triage_by_source = defaultdict(list)
    external_triage_by_log_id = {}
    for row in external_catalogue_search_log_rows:
        source_key = row.get("source_work_key", "")
        log_id = row.get("catalogue_log_row_id", "")
        external_log_by_source[source_key].append(row)
        if source_key not in source_by_key:
            errors.append(f"external_catalogue_search_log.tsv references unknown source_work_key {source_key}")
        if row.get("result_status") not in CATALOGUE_RESULT_STATUSES:
            errors.append(f"external_catalogue_search_log.tsv row {log_id or row.get('query')} uses invalid result_status {row.get('result_status')}")
        if row.get("match_assessment", "") not in CATALOGUE_MATCH_ASSESSMENTS:
            errors.append(f"external_catalogue_search_log.tsv row {log_id or row.get('query')} uses invalid match_assessment {row.get('match_assessment')}")
        if not row.get("catalogue_or_repository"):
            errors.append(f"external_catalogue_search_log.tsv row {log_id or row.get('query')} is missing catalogue_or_repository")
        if not row.get("query"):
            errors.append(f"external_catalogue_search_log.tsv row {log_id or source_key} is missing query")
        if row.get("result_status") != "no_match" and not (row.get("candidate_title") or row.get("evidence_snippet")):
            errors.append(f"external_catalogue_search_log.tsv row {log_id or row.get('query')} needs candidate or evidence detail")

    for row in external_catalogue_candidate_triage_rows:
        source_key = row.get("source_work_key", "")
        triage_key = row.get("catalogue_log_row_id_or_query", "")
        external_triage_by_source[source_key].append(row)
        external_triage_by_log_id[(source_key, triage_key)] = row
        if source_key not in source_by_key:
            errors.append(f"external_catalogue_candidate_triage.tsv references unknown source_work_key {source_key}")
        if row.get("triage_status") not in EXTERNAL_CATALOGUE_TRIAGE_STATUSES:
            errors.append(f"external_catalogue_candidate_triage.tsv row {triage_key or source_key} uses invalid triage_status {row.get('triage_status')}")

    for source_key in DIRECT_WITNESS_ACQUISITION_SOURCE_KEYS:
        if source_key not in acquisition_plan_by_source:
            continue
        if not external_log_by_source.get(source_key):
            errors.append(f"Acquisition-plan row {source_key} is missing external catalogue search-log coverage")

    for row in external_catalogue_search_log_rows:
        if row.get("result_status") in {"no_match", "blocked_or_unavailable"} and not row.get("candidate_title"):
            continue
        log_key = (row.get("source_work_key", ""), row.get("catalogue_log_row_id", "") or row.get("query", ""))
        if log_key not in external_triage_by_log_id:
            errors.append(f"Catalogue search row {log_key[1]} is missing external_catalogue_candidate_triage.tsv coverage")

    open_gap_rows = [
        row
        for row in gap_rows
        if row.get("source_work_key") in OPEN_DIRECT_WITNESS_GAP_SOURCE_KEYS
        and row.get("gap_type") in OPEN_DIRECT_WITNESS_GAP_TYPES
    ]
    acquisition_follow_up_gap_rows = [
        row
        for row in gap_rows
        if row.get("source_work_key") in OPEN_DIRECT_WITNESS_GAP_SOURCE_KEYS
        and row.get("gap_type") in ACQUISITION_REVIEW_GAP_TYPES
    ]
    for row in open_gap_rows:
        if row.get("source_work_key") not in acquisition_plan_by_source:
            errors.append(f"Open source-work gap {row.get('source_work_key')} is missing a direct_witness_acquisition_plan.tsv row")

    for source_key in FOLLOW_ON_PLAN_SOURCE_KEYS:
        if source_key in source_by_key and source_key not in acquisition_plan_by_source:
            errors.append(f"direct_witness_acquisition_plan.tsv is missing required follow-on row for {source_key}")
    for source_key, status_row in acquisition_status_by_source.items():
        if source_key in DIRECT_WITNESS_ACQUISITION_SOURCE_KEYS and status_row.get("acquisition_status") in {
            "needs_authoritative_catalogue_record",
            "needs_local_copy_or_scan",
        } and not acquisition_actions_by_source.get(source_key):
            errors.append(f"Acquisition status {source_key} requires a matching acquisition_action_queue.tsv row")

    manual_review_lookup = {
        (row.get("source_work_key", ""), row.get("target_file_or_work", ""), row.get("review_type", "")): row
        for row in manual_review_queue_rows
    }
    manual_review_by_source = defaultdict(list)
    for row in manual_review_queue_rows:
        source_key = row.get("source_work_key", "")
        if source_key not in source_by_key:
            errors.append(f"manual_review_queue.tsv references unknown source_work_key {source_key}")
        manual_review_by_source[source_key].append(row)

    for row in source_witness_content_profile_rows:
        source_key = row.get("source_work_key", "")
        if source_key not in {"sipSelectionsPagan", "epigraphiaBirmanica"}:
            continue
        if row.get("translation_status") == "confirmed":
            continue
        target_key = (source_key, row.get("file_label", ""), "")
        if not any(key[:2] == target_key[:2] for key in manual_review_lookup):
            errors.append(
                f"Verified direct witness {source_key}:{row.get('file_label')} needs a matching manual_review_queue.tsv row while translation remains unconfirmed"
            )

    iob_plate_profile_rows = [
        row
        for row in source_witness_content_profile_rows
        if row.get("source_work_key") == "lucePeMaungTinInscriptionsOfBurma" and row.get("plate_image_status") == "confirmed"
    ]
    for row in iob_plate_profile_rows:
        if ("lucePeMaungTinInscriptionsOfBurma", row.get("file_label", ""), "plate_guardrail") not in manual_review_lookup:
            errors.append(f"IOB plate witness {row.get('file_label')} needs a plate_guardrail manual review row")

    for row in acquisition_follow_up_gap_rows:
        if (
            row.get("source_work_key", ""),
            row.get("canonical_title", ""),
            "external_acquisition",
        ) not in manual_review_lookup:
            errors.append(f"Open source-work gap {row.get('source_work_key')} is missing an external acquisition manual-review row")

    authoritative_catalogue_sources = {
        row.get("source_work_key", "")
        for row in external_catalogue_candidate_triage_rows
        if row.get("is_authoritative_record") == "true"
    }
    for source_key, status_row in acquisition_status_by_source.items():
        local_status = status_row.get("local_direct_witness_status")
        external_status = status_row.get("external_catalogue_status")
        acquisition_status = status_row.get("acquisition_status")
        translation_status = status_row.get("translation_coverage_status")
        if translation_status == "confirmed":
            supporting_profiles = [
                row
                for row in source_witness_content_profile_rows
                if row.get("source_work_key") == source_key and row.get("translation_status") == "confirmed"
            ]
            if not supporting_profiles:
                errors.append(f"Acquisition status row {source_key} cannot mark translation_coverage_status=confirmed without explicit content-profile evidence")
        if external_status == "authoritative_catalogue_record_found":
            if source_key not in authoritative_catalogue_sources:
                errors.append(f"Acquisition status row {source_key} claims authoritative catalogue status without external triage support")
            if local_status not in {"local_direct_witness_verified", "local_direct_witness_needs_content_review"} and acquisition_status != "needs_local_copy_or_scan":
                errors.append(f"Acquisition status row {source_key} should use needs_local_copy_or_scan until a local direct witness is acquired")
        if local_status == "local_plate_witness_only" and source_key != "lucePeMaungTinInscriptionsOfBurma":
            errors.append(f"Only Inscriptions of Burma should use local_plate_witness_only in direct_witness_acquisition_status.tsv ({source_key})")

    iob_status_row = acquisition_status_by_source.get("lucePeMaungTinInscriptionsOfBurma", {})
    if iob_status_row:
        if iob_status_row.get("local_direct_witness_status") != "local_plate_witness_only":
            errors.append("Inscriptions of Burma acquisition status must keep local_direct_witness_status=local_plate_witness_only")
        if iob_status_row.get("external_catalogue_status") != "authoritative_catalogue_record_found":
            errors.append("Inscriptions of Burma acquisition status must keep external_catalogue_status=authoritative_catalogue_record_found")
        if iob_status_row.get("acquisition_status") != "needs_local_copy_or_scan":
            errors.append("Inscriptions of Burma acquisition status must keep acquisition_status=needs_local_copy_or_scan")
        if iob_status_row.get("translation_coverage_status") not in {"unconfirmed", "not_applicable_for_plate_only"}:
            errors.append("Inscriptions of Burma acquisition status must keep translation_coverage_status unconfirmed until a text witness is acquired")
        iob_actions = acquisition_actions_by_source.get("lucePeMaungTinInscriptionsOfBurma", [])
        if not any(
            row.get("action_type") == "acquire_local_copy_or_scan"
            and "berkeley" in row.get("target_record_or_work", "").casefold()
            for row in iob_actions
        ):
            errors.append("Inscriptions of Burma requires a Berkeley-specific acquire_local_copy_or_scan action row")
    for source_key in {"uemSelectionsPagan", "tnInscriptionsPaganPinyaAva", "ppaCatalogue", "ubSourceFamily"}:
        status_row = acquisition_status_by_source.get(source_key, {})
        if status_row and status_row.get("local_direct_witness_status") != "no_local_direct_witness":
            errors.append(f"{source_key} should remain no_local_direct_witness until a real direct witness is found")
        if status_row and status_row.get("acquisition_status") != "needs_authoritative_catalogue_record":
            errors.append(f"{source_key} should remain in needs_authoritative_catalogue_record until an authoritative record appears")

    checklist_by_source = defaultdict(list)
    for row in human_acquisition_checklist_rows:
        source_key = row.get("source_work_key", "")
        checklist_by_source[source_key].append(row)
        if source_key not in source_by_key:
            errors.append(f"human_acquisition_checklist.tsv references unknown source_work_key {source_key}")
        if not row.get("task_type"):
            errors.append(f"human_acquisition_checklist.tsv row {row.get('checklist_id', source_key)} is missing task_type")
        if not row.get("task"):
            errors.append(f"human_acquisition_checklist.tsv row {row.get('checklist_id', source_key)} is missing task")
        if not row.get("success_condition"):
            errors.append(f"human_acquisition_checklist.tsv row {row.get('checklist_id', source_key)} is missing success_condition")
        if not row.get("failure_condition"):
            errors.append(f"human_acquisition_checklist.tsv row {row.get('checklist_id', source_key)} is missing failure_condition")
        if not row.get("priority"):
            errors.append(f"human_acquisition_checklist.tsv row {row.get('checklist_id', source_key)} is missing priority")
    for source_key in acquisition_status_by_source:
        if not checklist_by_source.get(source_key):
            errors.append(f"Acquisition status {source_key} requires at least one human_acquisition_checklist.tsv row")

    iob_checklist_rows = checklist_by_source.get("lucePeMaungTinInscriptionsOfBurma", [])
    if not any(
        row.get("task_type") == "acquire_local_copy_or_scan"
        and "berkeley" in f"{row.get('task', '')} {row.get('notes', '')} {row.get('evidence_to_use', '')}".casefold()
        and "local copy" in f"{row.get('task', '')} {row.get('failure_condition', '')}".casefold()
        for row in iob_checklist_rows
    ):
        errors.append("Inscriptions of Burma human acquisition checklist must preserve the Berkeley acquisition lead and local-copy distinction")

    for source_key in {"sipSelectionsPagan", "epigraphiaBirmanica"}:
        for row in checklist_by_source.get(source_key, []):
            if row.get("task_type") != "manual_content_review":
                errors.append(f"{source_key} checklist rows must be manual content-review tasks")
    for source_key in {"uemSelectionsPagan", "ubSourceFamily"}:
        if not any(row.get("task_type") == "locate_authoritative_catalogue_record" for row in checklist_by_source.get(source_key, [])):
            errors.append(f"{source_key} checklist rows must require catalogue-acquisition work")
    for source_key in {"tnInscriptionsPaganPinyaAva", "ppaCatalogue"}:
        if not any(row.get("task_type") == "resolve_source_identity" for row in checklist_by_source.get(source_key, [])):
            errors.append(f"{source_key} checklist rows must require source-identity resolution")

    summary_casefold = phase_summary_text.casefold()
    for required_phrase in [
        "berkeley",
        "plate portfolios",
        "not a verified local witness",
        "sip/uem",
        "false positive",
    ]:
        if required_phrase not in summary_casefold:
            errors.append(f"translation_source_discovery_phase_summary.md is missing required guardrail language: {required_phrase}")

    ruled_out_by_key = {
        ruled_out_candidate_key(
            row.get("source_work_key", ""),
            row.get("candidate_id", ""),
            row.get("candidate_label", ""),
            row.get("ruled_out_category", ""),
        ): row
        for row in ruled_out_witness_candidate_rows
    }
    for row in witness_hunt_candidate_triage_rows:
        if row.get("triage_status") not in NON_PROMOTABLE_HUNT_TRIAGE_STATUSES:
            continue
        key = ruled_out_candidate_key(
            row.get("source_work_key", ""),
            row.get("matched_file_id", ""),
            row.get("matched_file_label", ""),
            row.get("triage_status", ""),
        )
        if key not in ruled_out_by_key:
            errors.append(
                f"Non-promotable hunt triage row {row.get('source_work_key')}:{row.get('query')} is missing from ruled_out_witness_candidates.tsv"
            )
    for row in rescue_review_rows:
        if row.get("classification") != "secondary_article":
            continue
        key = ruled_out_candidate_key(
            row.get("possible_source_work_keys", ""),
            row.get("candidate_file_id", ""),
            row.get("candidate_file_label", ""),
            row.get("classification", ""),
        )
        if key not in ruled_out_by_key:
            errors.append(f"Rescue secondary-article row {row.get('candidate_file_label')} is missing from ruled_out_witness_candidates.tsv")
    for row in verification_rows:
        if row.get("verification_status") != "weak_false_positive":
            continue
        key = ruled_out_candidate_key(
            row.get("source_work_key", ""),
            row.get("witness_id", ""),
            row.get("candidate_file_label", ""),
            row.get("verification_status", ""),
        )
        if key not in ruled_out_by_key:
            errors.append(f"Weak false-positive verification row {row.get('witness_id')} is missing from ruled_out_witness_candidates.tsv")
    for row in iob_text_search_rows + iob_text_volume_hunt_rows:
        if row.get("false_positive_for_text") != "true":
            continue
        key = ruled_out_candidate_key(
            row.get("source_work_key", "lucePeMaungTinInscriptionsOfBurma"),
            row.get("matched_file_id", ""),
            row.get("matched_file_label", ""),
            "known_false_positive",
        )
        if key not in ruled_out_by_key:
            errors.append(f"IOB plate false-positive row {row.get('matched_file_label')} is missing from ruled_out_witness_candidates.tsv")

    for collection_name, rows in [
        ("source-work witness gaps", gap_rows),
        ("UEM direct search", uem_search_rows),
        ("core direct search", core_search_rows),
        ("Inscriptions of Burma text search", iob_text_search_rows),
        ("Inscriptions of Burma text volume hunt", iob_text_volume_hunt_rows),
        ("missing core witness hunt", missing_core_witness_hunt_rows),
        ("direct witness acquisition plan", direct_witness_acquisition_plan_rows),
        ("direct witness acquisition status", direct_witness_acquisition_status_rows),
        ("manual review queue", manual_review_queue_rows),
        ("acquisition action queue", acquisition_action_queue_rows),
        ("human acquisition checklist", human_acquisition_checklist_rows),
        ("ruled out witness candidates", ruled_out_witness_candidate_rows),
        ("external catalogue search log", external_catalogue_search_log_rows),
        ("external catalogue candidate triage", external_catalogue_candidate_triage_rows),
        ("rescue candidate review", rescue_review_rows),
        ("epigraphia birmanica review", epigraphia_review_rows),
        ("epigraphia birmanica fascicle coverage", epigraphia_fascicle_coverage_rows),
        ("source witness content profile", source_witness_content_profile_rows),
        ("eb fascicle content inspection", eb_fascicle_content_inspection_rows),
    ]:
        for row in rows:
            for key, value in row.items():
                if isinstance(value, str) and (len(value) > SHORT_EVIDENCE_LIMIT or "\n" in value) and key not in {"notes", "recommended_action", "next_action"}:
                    errors.append(f"{collection_name} row stores more than a short value in {key}")

    uem_direct_rows = [row for row in verification_rows if row.get("source_work_key") == "uemSelectionsPagan" and row.get("verification_status") in DIRECT_VERIFICATION_STATUSES]
    if uem_direct_rows:
        errors.append("UEM incorrectly has a verified direct witness; the SIP witness must stay excluded")
    sip_candidate_label = candidate_by_id.get(SIP_WITNESS_ID, {}).get("candidate_file_label", "")
    uem_sip_false_positive = [
        row
        for row in verification_rows
        if row.get("source_work_key") == "uemSelectionsPagan"
        and row.get("candidate_file_label") == sip_candidate_label
        and row.get("verification_status") == "weak_false_positive"
    ]
    if not uem_sip_false_positive:
        errors.append("UEM does not retain the reviewed SIP false-positive row")
    sip_false_positive_hunt_rows = [
        row
        for row in missing_core_witness_hunt_rows
        if row.get("source_work_key") == "uemSelectionsPagan" and row.get("matched_file_label") == sip_candidate_label
    ]
    if sip_false_positive_hunt_rows:
        for row in sip_false_positive_hunt_rows:
            if row.get("is_known_false_positive") != "true":
                errors.append("UEM/SIP false-positive hunt rows must be marked as known false positives")
            if "do not promote" not in row.get("recommended_action", "").casefold():
                errors.append("UEM/SIP false-positive hunt rows cannot be surfaced as promotable direct-witness candidates")

    for row in iob_text_search_rows:
        label = row.get("matched_file_label", "")
        if "plates" in label.casefold():
            if row.get("is_plate_witness_candidate") != "true":
                errors.append(f"Inscriptions of Burma plate row {label} must be marked as a plate witness candidate")
            if row.get("is_text_witness_candidate") != "false":
                errors.append(f"Inscriptions of Burma plate row {label} must not be marked as a text witness candidate")
            if row.get("false_positive_for_text") != "true":
                errors.append(f"Inscriptions of Burma plate row {label} must be marked as a false positive for the text witness hunt")
            if "plate" not in row.get("reason_not_text_witness", "").casefold():
                errors.append(f"Inscriptions of Burma plate row {label} must explain why it is not a text witness")
    for row in iob_text_volume_hunt_rows:
        label = row.get("matched_file_label", "")
        if "plates" in label.casefold():
            if row.get("is_plate_witness_candidate") != "true" or row.get("is_text_witness_candidate") != "false" or row.get("false_positive_for_text") != "true":
                errors.append(f"Inscriptions of Burma text-volume hunt plate row {label} must be a false positive for text")
            if row.get("recommended_action") == "Inspect title page before promoting this as a direct witness.":
                errors.append(f"Inscriptions of Burma text-volume hunt plate row {label} still uses a promotable direct-witness action")

    direct_eb_review_rows = [row for row in epigraphia_review_rows if row.get("classification") == "actual_eb_fascicle"]
    direct_eb_verifications = {
        row.get("candidate_file_label", "")
        for row in verification_rows
        if row.get("source_work_key") == "epigraphiaBirmanica" and row.get("verification_status") in DIRECT_VERIFICATION_STATUSES
    }
    for row in direct_eb_review_rows:
        if row.get("confidence") == "high" and row.get("file_label", "") not in direct_eb_verifications:
            errors.append(f"Direct-looking EB fascicle {row.get('file_label')} is not promoted or explicitly blocked")
    if direct_eb_review_rows and not epigraphia_fascicle_coverage_rows:
        errors.append("Epigraphia Birmanica fascicle coverage is missing despite direct-looking EB fascicles")
    if epigraphia_fascicle_coverage_rows:
        coverage_ids = {row.get("witness_id", "") for row in epigraphia_fascicle_coverage_rows}
        promoted_ids = {row.get("witness_id", "") for row in direct_eb_review_rows if row.get("confidence") == "high"}
        if not promoted_ids.issubset(coverage_ids):
            errors.append("Epigraphia Birmanica fascicle coverage is missing promoted EB fascicle rows")

    for row in plan_rows:
        source_key = row.get("source_work_key", "")
        if row.get("discovery_status") == "verified_direct_witness_found" and verified_direct_counts.get(source_key, 0) == 0:
            errors.append(f"Discovery plan row {source_key} is marked verified_direct_witness_found without a verified direct witness")
        if row.get("discovery_status") == "needs_direct_witness_search" and source_key in {
            "sipSelectionsPagan",
            "uemSelectionsPagan",
            "tnInscriptionsPaganPinyaAva",
            "ppaCatalogue",
            "ubSourceFamily",
            "epigraphiaBirmanica",
            "lucePeMaungTinInscriptionsOfBurma",
        } and source_key not in gap_by_source:
            errors.append(f"Discovery plan row {source_key} needs a matching source_work_witness_gaps.tsv row")

    rescue_required_by_search = {
        row.get("matched_file_id", "") or row.get("matched_file_label", "")
        for row in missing_search_rows
        if row.get("matched_file_id") in {"111029.pdf", "Taw Sein Ko 1899 Inscriptions of Pagan.pdf"}
        or row.get("matched_file_label") in {"111029.pdf", "Taw Sein Ko 1899 Inscriptions of Pagan.pdf"}
    }
    required_rescue_labels = rescue_required_by_search or {"111029.pdf", "Taw Sein Ko 1899 Inscriptions of Pagan.pdf"}
    rescue_labels = {
        value
        for row in rescue_review_rows
        for value in (row.get("candidate_file_label", ""), row.get("candidate_file_id", ""))
        if value
    }
    if required_rescue_labels - rescue_labels:
        errors.append("Rescue candidate review is missing required 111029/Taw Sein Ko review rows")

    numbered_epigraphia_rows = [row for row in epigraphia_review_rows if re.fullmatch(r"\d+\.pdf", row.get("file_label", ""), flags=re.IGNORECASE)]
    if not numbered_epigraphia_rows:
        errors.append("Epigraphia Birmanica review is missing the numbered-PDF review rows")

    if any(field not in plan_rows[0] for field in PLAN_DISCOVERY_FIELDS):
        missing = [field for field in PLAN_DISCOVERY_FIELDS if field not in plan_rows[0]]
        errors.append(f"Discovery plan is missing required fields: {', '.join(missing)}")

    for row in plan_rows:
        source_key = row.get("source_work_key", "")
        if source_key not in source_by_key:
            errors.append(f"Discovery plan references unknown source_work_key {source_key}")
        if row.get("discovery_status") not in DISCOVERY_STATUSES:
            errors.append(f"Discovery plan row {source_key} uses invalid discovery_status {row.get('discovery_status')}")
        expected_candidate_count = candidate_counts.get(source_key, 0)
        expected_classified_count = classification_counts.get(source_key, 0)
        expected_translation_count = confirmed_translation_counts.get(source_key, 0)
        expected_edition_count = confirmed_edition_counts.get(source_key, 0)
        expected_plate_count = confirmed_plate_counts.get(source_key, 0)
        expected_verified_direct_count = verified_direct_counts.get(source_key, 0)
        expected_verified_translation_count = verified_translation_counts.get(source_key, 0)
        expected_verified_edition_count = verified_edition_counts.get(source_key, 0)
        expected_verified_plate_count = verified_plate_counts.get(source_key, 0)
        expected_weak_false_positive_count = weak_false_positive_counts.get(source_key, 0)
        if int(row.get("candidate_witness_count", "0")) != expected_candidate_count:
            errors.append(f"Discovery plan row {source_key} has inconsistent candidate_witness_count")
        if int(row.get("classified_witness_count", "0")) != expected_classified_count:
            errors.append(f"Discovery plan row {source_key} has inconsistent classified_witness_count")
        if int(row.get("confirmed_translation_witness_count", "0")) != expected_translation_count:
            errors.append(f"Discovery plan row {source_key} has inconsistent confirmed_translation_witness_count")
        if int(row.get("confirmed_edition_witness_count", "0")) != expected_edition_count:
            errors.append(f"Discovery plan row {source_key} has inconsistent confirmed_edition_witness_count")
        if int(row.get("confirmed_plate_witness_count", "0")) != expected_plate_count:
            errors.append(f"Discovery plan row {source_key} has inconsistent confirmed_plate_witness_count")
        if int(row.get("verified_direct_witness_count", "0")) != expected_verified_direct_count:
            errors.append(f"Discovery plan row {source_key} has inconsistent verified_direct_witness_count")
        if int(row.get("verified_translation_witness_count", "0")) != expected_verified_translation_count:
            errors.append(f"Discovery plan row {source_key} has inconsistent verified_translation_witness_count")
        if int(row.get("verified_edition_witness_count", "0")) != expected_verified_edition_count:
            errors.append(f"Discovery plan row {source_key} has inconsistent verified_edition_witness_count")
        if int(row.get("verified_plate_witness_count", "0")) != expected_verified_plate_count:
            errors.append(f"Discovery plan row {source_key} has inconsistent verified_plate_witness_count")
        if int(row.get("weak_false_positive_count", "0")) != expected_weak_false_positive_count:
            errors.append(f"Discovery plan row {source_key} has inconsistent weak_false_positive_count")

    planned_periodical_keys = {row.get("series_source_work_key", "") for row in periodical_plan_rows}
    for required_key in PERIODICAL_PLAN_KEYS:
        if required_key not in planned_periodical_keys:
            errors.append(f"Periodical article discovery plan is missing {required_key}")
    for row in periodical_plan_rows:
        if row.get("series_source_work_key") in PERIODICAL_PLAN_KEYS:
            for field in [
                "article_candidate_count",
                "high_priority_article_count",
                "needs_article_title_normalization",
                "needs_local_file_search",
            ]:
                if field not in row:
                    errors.append(f"Periodical article discovery plan row {row.get('series_source_work_key')} is missing {field}")

    report_candidate_count = report.get("candidate_witness_count")
    report_classified_count = report.get("classified_witness_count")
    if report_candidate_count != len(candidate_rows):
        errors.append("translation_source_discovery_report.json has inconsistent candidate_witness_count")
    if report_classified_count != len(classification_rows):
        errors.append("translation_source_discovery_report.json has inconsistent classified_witness_count")
    if report.get("verified_witness_count") != len(verification_rows):
        errors.append("translation_source_discovery_report.json has inconsistent verified_witness_count")
    if report.get("verified_direct_witness_count") != sum(verified_direct_counts.values()):
        errors.append("translation_source_discovery_report.json has inconsistent verified_direct_witness_count")
    if report.get("verified_translation_witness_count") != sum(verified_translation_counts.values()):
        errors.append("translation_source_discovery_report.json has inconsistent verified_translation_witness_count")
    if report.get("verified_edition_witness_count") != sum(verified_edition_counts.values()):
        errors.append("translation_source_discovery_report.json has inconsistent verified_edition_witness_count")
    if report.get("verified_plate_witness_count") != sum(verified_plate_counts.values()):
        errors.append("translation_source_discovery_report.json has inconsistent verified_plate_witness_count")
    if report.get("weak_false_positive_count") != sum(weak_false_positive_counts.values()):
        errors.append("translation_source_discovery_report.json has inconsistent weak_false_positive_count")
    if report.get("missing_direct_witness_search_count") != sum(bool(row.get("matched_file_label")) for row in missing_search_rows):
        errors.append("translation_source_discovery_report.json has inconsistent missing_direct_witness_search_count")
    if report.get("titlepage_toc_snippet_count") != len(snippet_rows):
        errors.append("translation_source_discovery_report.json has inconsistent titlepage_toc_snippet_count")
    if report.get("source_work_witness_gap_count") != len(gap_rows):
        errors.append("translation_source_discovery_report.json has inconsistent source_work_witness_gap_count")
    expected_open_gap_count = sum(
        row.get("local_direct_witness_status") == "no_local_direct_witness"
        for row in direct_witness_acquisition_status_rows
    )
    expected_acquisition_status_count = len(direct_witness_acquisition_status_rows)
    expected_acquisition_action_queue_count = len(acquisition_action_queue_rows)
    expected_needing_authoritative_catalogue_record_count = sum(
        row.get("acquisition_status") == "needs_authoritative_catalogue_record"
        for row in direct_witness_acquisition_status_rows
    )
    expected_with_authoritative_catalogue_record_needing_local_copy_count = sum(
        row.get("acquisition_status") == "needs_local_copy_or_scan"
        for row in direct_witness_acquisition_status_rows
    )
    expected_needing_manual_content_review_count = sum(
        row.get("acquisition_status") == "needs_manual_content_review"
        for row in direct_witness_acquisition_status_rows
    )
    expected_local_direct_witness_but_translation_unconfirmed_count = sum(
        row.get("local_direct_witness_status") in {"local_direct_witness_verified", "local_direct_witness_needs_content_review"}
        and row.get("translation_coverage_status") in {"unconfirmed", "needs_manual_review"}
        for row in direct_witness_acquisition_status_rows
    )
    if report.get("source_works_still_needing_direct_witness") != expected_open_gap_count:
        errors.append("translation_source_discovery_report.json has inconsistent source_works_still_needing_direct_witness")
    if report.get("sip_inspection_completed") != bool(sip_inspection_rows):
        errors.append("translation_source_discovery_report.json has inconsistent sip_inspection_completed")
    if report.get("uem_direct_search_count") != sum(bool(row.get("matched_file_label")) for row in uem_search_rows):
        errors.append("translation_source_discovery_report.json has inconsistent uem_direct_search_count")
    if report.get("core_source_direct_search_count") != sum(bool(row.get("matched_file_label")) for row in core_search_rows):
        errors.append("translation_source_discovery_report.json has inconsistent core_source_direct_search_count")
    if report.get("inscriptions_of_burma_text_witness_search_count") != len(iob_text_search_rows):
        errors.append("translation_source_discovery_report.json has inconsistent inscriptions_of_burma_text_witness_search_count")
    expected_iob_text_witness_found = sum(
        row.get("is_text_witness_candidate") == "true" and row.get("search_result_status") == "direct_witness_found"
        for row in iob_text_search_rows
    )
    if report.get("inscriptions_of_burma_text_witness_found") != expected_iob_text_witness_found:
        errors.append("translation_source_discovery_report.json has inconsistent inscriptions_of_burma_text_witness_found")
    expected_iob_plate_false_positive_count = len(
        {
            row.get("matched_file_id", "") or row.get("matched_file_label", "")
            for row in (iob_text_search_rows + iob_text_volume_hunt_rows)
            if row.get("false_positive_for_text") == "true"
        }
    )
    if report.get("inscriptions_of_burma_plate_false_positive_count") != expected_iob_plate_false_positive_count:
        errors.append("translation_source_discovery_report.json has inconsistent inscriptions_of_burma_plate_false_positive_count")
    if report.get("inscriptions_of_burma_text_volume_hunt_count") != len(iob_text_volume_hunt_rows):
        errors.append("translation_source_discovery_report.json has inconsistent inscriptions_of_burma_text_volume_hunt_count")
    if report.get("missing_core_witness_hunt_count") != len(missing_core_witness_hunt_rows):
        errors.append("translation_source_discovery_report.json has inconsistent missing_core_witness_hunt_count")
    expected_triage_count = len(witness_hunt_candidate_triage_rows)
    expected_plausible_triage_count = sum(row.get("triage_status") in PLAUSIBLE_HUNT_TRIAGE_STATUSES for row in witness_hunt_candidate_triage_rows)
    expected_known_false_positive_hunt_count = sum(row.get("triage_status") == "known_false_positive" for row in witness_hunt_candidate_triage_rows)
    expected_cross_source_or_secondary_hunt_count = sum(
        row.get("triage_status") in {"cross_source_witness", "secondary_or_unrelated", "too_broad_query_noise"}
        for row in witness_hunt_candidate_triage_rows
    )
    if report.get("witness_hunt_candidate_triage_count") != expected_triage_count:
        errors.append("translation_source_discovery_report.json has inconsistent witness_hunt_candidate_triage_count")
    if report.get("direct_witness_acquisition_plan_count") != len(direct_witness_acquisition_plan_rows):
        errors.append("translation_source_discovery_report.json has inconsistent direct_witness_acquisition_plan_count")
    if report.get("manual_review_queue_count") != len(manual_review_queue_rows):
        errors.append("translation_source_discovery_report.json has inconsistent manual_review_queue_count")
    if report.get("ruled_out_witness_candidate_count") != len(ruled_out_witness_candidate_rows):
        errors.append("translation_source_discovery_report.json has inconsistent ruled_out_witness_candidate_count")
    if report.get("external_catalogue_search_log_count") != len(external_catalogue_search_log_rows):
        errors.append("translation_source_discovery_report.json has inconsistent external_catalogue_search_log_count")
    if report.get("external_catalogue_candidate_triage_count") != len(external_catalogue_candidate_triage_rows):
        errors.append("translation_source_discovery_report.json has inconsistent external_catalogue_candidate_triage_count")
    if report.get("acquisition_status_count") != expected_acquisition_status_count:
        errors.append("translation_source_discovery_report.json has inconsistent acquisition_status_count")
    if report.get("acquisition_action_queue_count") != expected_acquisition_action_queue_count:
        errors.append("translation_source_discovery_report.json has inconsistent acquisition_action_queue_count")
    if report.get("authoritative_catalogue_record_count") != sum(row.get("is_authoritative_record") == "true" for row in external_catalogue_candidate_triage_rows):
        errors.append("translation_source_discovery_report.json has inconsistent authoritative_catalogue_record_count")
    if report.get("source_works_needing_authoritative_catalogue_record_count") != expected_needing_authoritative_catalogue_record_count:
        errors.append("translation_source_discovery_report.json has inconsistent source_works_needing_authoritative_catalogue_record_count")
    if report.get("source_works_with_authoritative_catalogue_record_needing_local_copy_count") != expected_with_authoritative_catalogue_record_needing_local_copy_count:
        errors.append("translation_source_discovery_report.json has inconsistent source_works_with_authoritative_catalogue_record_needing_local_copy_count")
    if report.get("source_works_needing_manual_content_review_count") != expected_needing_manual_content_review_count:
        errors.append("translation_source_discovery_report.json has inconsistent source_works_needing_manual_content_review_count")
    if report.get("source_works_with_local_direct_witness_but_translation_unconfirmed_count") != expected_local_direct_witness_but_translation_unconfirmed_count:
        errors.append("translation_source_discovery_report.json has inconsistent source_works_with_local_direct_witness_but_translation_unconfirmed_count")
    if report.get("plausible_direct_candidate_count") != expected_plausible_triage_count:
        errors.append("translation_source_discovery_report.json has inconsistent plausible_direct_candidate_count")
    if report.get("known_false_positive_hunt_count") != expected_known_false_positive_hunt_count:
        errors.append("translation_source_discovery_report.json has inconsistent known_false_positive_hunt_count")
    if report.get("cross_source_or_secondary_hunt_count") != expected_cross_source_or_secondary_hunt_count:
        errors.append("translation_source_discovery_report.json has inconsistent cross_source_or_secondary_hunt_count")
    if report.get("rescue_candidate_review_count") != len(rescue_review_rows):
        errors.append("translation_source_discovery_report.json has inconsistent rescue_candidate_review_count")
    if report.get("epigraphia_birmanica_review_count") != len(epigraphia_review_rows):
        errors.append("translation_source_discovery_report.json has inconsistent epigraphia_birmanica_review_count")
    if report.get("eb_verified_fascicle_count") != len(epigraphia_fascicle_coverage_rows):
        errors.append("translation_source_discovery_report.json has inconsistent eb_verified_fascicle_count")
    if report.get("eb_fascicle_coverage_count") != len(epigraphia_fascicle_coverage_rows):
        errors.append("translation_source_discovery_report.json has inconsistent eb_fascicle_coverage_count")
    eb_profile_rows = [row for row in source_witness_content_profile_rows if row.get("source_work_key") == "epigraphiaBirmanica"]
    if report.get("eb_content_profile_count") != len(eb_profile_rows):
        errors.append("translation_source_discovery_report.json has inconsistent eb_content_profile_count")
    if report.get("eb_translation_confirmed_count") != sum(row.get("translation_status") == "confirmed" for row in eb_profile_rows):
        errors.append("translation_source_discovery_report.json has inconsistent eb_translation_confirmed_count")
    if report.get("eb_translation_unconfirmed_count") != sum(row.get("translation_status") != "confirmed" for row in eb_profile_rows):
        errors.append("translation_source_discovery_report.json has inconsistent eb_translation_unconfirmed_count")
    if report.get("eb_fascicle_content_inspection_count") != len(eb_fascicle_content_inspection_rows):
        errors.append("translation_source_discovery_report.json has inconsistent eb_fascicle_content_inspection_count")
    if report.get("sip_title_page_inspected") != any(
        row.get("inspection_area") == "title_page" and row.get("inspection_status") == "confirmed" for row in sip_inspection_rows
    ):
        errors.append("translation_source_discovery_report.json has inconsistent sip_title_page_inspected")
    if report.get("sip_contents_inspected") != any(
        row.get("inspection_area") == "contents" and row.get("inspection_status") == "confirmed" for row in sip_inspection_rows
    ):
        errors.append("translation_source_discovery_report.json has inconsistent sip_contents_inspected")
    if report.get("sip_sample_entry_ocr_attempted") != any(row.get("inspection_area") == "sample_entry" for row in sip_inspection_rows):
        errors.append("translation_source_discovery_report.json has inconsistent sip_sample_entry_ocr_attempted")
    if report.get("sip_sample_entry_inspected") != any(
        row.get("inspection_area") == "sample_entry" and row.get("inspection_status") == "confirmed" for row in sip_inspection_rows
    ):
        errors.append("translation_source_discovery_report.json has inconsistent sip_sample_entry_inspected")
    sip_profile = next((row for row in source_witness_content_profile_rows if row.get("witness_id") == SIP_WITNESS_ID), None)
    expected_sip_translation_status = "confirmed" if sip_profile and sip_profile.get("translation_status") == "confirmed" else "unconfirmed"
    expected_sip_edition_status = "confirmed" if sip_profile and sip_profile.get("edition_status") == "confirmed" else "unconfirmed"
    if report.get("sip_translation_status") != expected_sip_translation_status:
        errors.append("translation_source_discovery_report.json has inconsistent sip_translation_status")
    if report.get("sip_edition_status") != expected_sip_edition_status:
        errors.append("translation_source_discovery_report.json has inconsistent sip_edition_status")
    if report.get("sip_contains_translation_status") != expected_sip_translation_status:
        errors.append("translation_source_discovery_report.json has inconsistent sip_contains_translation_status")
    expected_search_result_counts = {
        status: sum(row.get("search_result_status") == status for row in (uem_search_rows + core_search_rows + iob_text_search_rows))
        for status in DIRECT_SEARCH_RESULT_STATUSES
    }
    if report.get("direct_witness_search_result_counts") != expected_search_result_counts:
        errors.append("translation_source_discovery_report.json has inconsistent direct_witness_search_result_counts")
    if not isinstance(report.get("notes"), list):
        errors.append("translation_source_discovery_report.json notes must be a list")
    if verification_report.get("verified_witness_count") != len(verification_rows):
        errors.append("witness_verification_report.json has inconsistent verified_witness_count")
    if verification_report.get("verified_direct_witness_count") != sum(verified_direct_counts.values()):
        errors.append("witness_verification_report.json has inconsistent verified_direct_witness_count")
    if verification_report.get("titlepage_toc_snippet_count") != len(snippet_rows):
        errors.append("witness_verification_report.json has inconsistent titlepage_toc_snippet_count")
    if verification_report.get("source_work_witness_gap_count") != len(gap_rows):
        errors.append("witness_verification_report.json has inconsistent source_work_witness_gap_count")
    if verification_report.get("source_works_still_needing_direct_witness") != expected_open_gap_count:
        errors.append("witness_verification_report.json has inconsistent source_works_still_needing_direct_witness")
    if verification_report.get("inscriptions_of_burma_text_witness_search_count") != len(iob_text_search_rows):
        errors.append("witness_verification_report.json has inconsistent inscriptions_of_burma_text_witness_search_count")
    if verification_report.get("eb_fascicle_coverage_count") != len(epigraphia_fascicle_coverage_rows):
        errors.append("witness_verification_report.json has inconsistent eb_fascicle_coverage_count")
    if verification_report.get("missing_core_witness_hunt_count") != len(missing_core_witness_hunt_rows):
        errors.append("witness_verification_report.json has inconsistent missing_core_witness_hunt_count")
    if verification_report.get("witness_hunt_candidate_triage_count") != expected_triage_count:
        errors.append("witness_verification_report.json has inconsistent witness_hunt_candidate_triage_count")
    if verification_report.get("direct_witness_acquisition_plan_count") != len(direct_witness_acquisition_plan_rows):
        errors.append("witness_verification_report.json has inconsistent direct_witness_acquisition_plan_count")
    if verification_report.get("manual_review_queue_count") != len(manual_review_queue_rows):
        errors.append("witness_verification_report.json has inconsistent manual_review_queue_count")
    if verification_report.get("ruled_out_witness_candidate_count") != len(ruled_out_witness_candidate_rows):
        errors.append("witness_verification_report.json has inconsistent ruled_out_witness_candidate_count")
    if verification_report.get("external_catalogue_search_log_count") != len(external_catalogue_search_log_rows):
        errors.append("witness_verification_report.json has inconsistent external_catalogue_search_log_count")
    if verification_report.get("external_catalogue_candidate_triage_count") != len(external_catalogue_candidate_triage_rows):
        errors.append("witness_verification_report.json has inconsistent external_catalogue_candidate_triage_count")
    if verification_report.get("acquisition_status_count") != expected_acquisition_status_count:
        errors.append("witness_verification_report.json has inconsistent acquisition_status_count")
    if verification_report.get("acquisition_action_queue_count") != expected_acquisition_action_queue_count:
        errors.append("witness_verification_report.json has inconsistent acquisition_action_queue_count")
    if verification_report.get("authoritative_catalogue_record_count") != sum(row.get("is_authoritative_record") == "true" for row in external_catalogue_candidate_triage_rows):
        errors.append("witness_verification_report.json has inconsistent authoritative_catalogue_record_count")
    if verification_report.get("source_works_needing_authoritative_catalogue_record_count") != expected_needing_authoritative_catalogue_record_count:
        errors.append("witness_verification_report.json has inconsistent source_works_needing_authoritative_catalogue_record_count")
    if verification_report.get("source_works_with_authoritative_catalogue_record_needing_local_copy_count") != expected_with_authoritative_catalogue_record_needing_local_copy_count:
        errors.append("witness_verification_report.json has inconsistent source_works_with_authoritative_catalogue_record_needing_local_copy_count")
    if verification_report.get("source_works_needing_manual_content_review_count") != expected_needing_manual_content_review_count:
        errors.append("witness_verification_report.json has inconsistent source_works_needing_manual_content_review_count")
    if verification_report.get("source_works_with_local_direct_witness_but_translation_unconfirmed_count") != expected_local_direct_witness_but_translation_unconfirmed_count:
        errors.append("witness_verification_report.json has inconsistent source_works_with_local_direct_witness_but_translation_unconfirmed_count")
    if verification_report.get("plausible_direct_candidate_count") != expected_plausible_triage_count:
        errors.append("witness_verification_report.json has inconsistent plausible_direct_candidate_count")
    if verification_report.get("known_false_positive_hunt_count") != expected_known_false_positive_hunt_count:
        errors.append("witness_verification_report.json has inconsistent known_false_positive_hunt_count")
    if verification_report.get("cross_source_or_secondary_hunt_count") != expected_cross_source_or_secondary_hunt_count:
        errors.append("witness_verification_report.json has inconsistent cross_source_or_secondary_hunt_count")
    if verification_report.get("direct_witness_search_result_counts") != expected_search_result_counts:
        errors.append("witness_verification_report.json has inconsistent direct_witness_search_result_counts")
    if not isinstance(verification_report.get("notes"), list):
        errors.append("witness_verification_report.json notes must be a list")

    authoritative_catalogue_sources = {
        row.get("source_work_key", "")
        for row in external_catalogue_candidate_triage_rows
        if row.get("is_authoritative_record") == "true"
    }
    for row in gap_rows:
        source_key = row.get("source_work_key", "")
        if source_key not in OPEN_DIRECT_WITNESS_GAP_SOURCE_KEYS:
            continue
        if row.get("gap_type") in CATALOGUE_RECORD_GAP_TYPES:
            if source_key not in authoritative_catalogue_sources and verified_direct_counts.get(source_key, 0) == 0:
                errors.append(f"Gap row {source_key} cannot close from catalogue evidence without an authoritative or direct-candidate triage row")
        elif row.get("gap_type") not in ACQUISITION_REVIEW_GAP_TYPES and verified_direct_counts.get(source_key, 0) == 0:
            errors.append(f"Gap row {source_key} cannot leave acquisition review states without a verified local witness or authoritative catalogue record")

    iob_gap_row = gap_by_source.get("lucePeMaungTinInscriptionsOfBurma", {})
    if iob_gap_row.get("verified_plate_witness_count") != str(verified_plate_counts.get("lucePeMaungTinInscriptionsOfBurma", 0)):
        errors.append("Inscriptions of Burma gap row has inconsistent verified_plate_witness_count")
    if iob_gap_row.get("gap_type") == "has_authoritative_catalogue_record_needs_acquisition":
        if iob_gap_row.get("current_status") != "authoritative_catalogue_record_found":
            errors.append("Inscriptions of Burma gap row should use authoritative_catalogue_record_found when a catalogue record identifies the text volume")
        if "local corpus still lacks" not in iob_gap_row.get("notes", "").casefold():
            errors.append("Inscriptions of Burma authoritative catalogue gap row should explain that the local text witness is still missing")
    else:
        if iob_gap_row.get("current_status") and iob_gap_row.get("current_status") != "verification_in_progress":
            errors.append("Inscriptions of Burma gap row should remain verification_in_progress while the text volume is still missing")
        if "cross-source" not in iob_gap_row.get("notes", "").casefold() and "false positive" not in iob_gap_row.get("notes", "").casefold():
            errors.append("Inscriptions of Burma gap row should explain that current text-volume hunt leads are cross-source/secondary/false positives")

    uem_gap_row = gap_by_source.get("uemSelectionsPagan", {})
    if uem_gap_row.get("current_status") and uem_gap_row.get("current_status") != "needs_direct_witness":
        errors.append("UEM gap row should remain open until a real U E Maung direct witness is found")
    if "no direct u e maung witness" not in uem_gap_row.get("notes", "").casefold():
        errors.append("UEM gap row should state that no direct U E Maung witness has been found yet")

    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate translation-source discovery artifacts.")
    parser.add_argument("--plan", type=Path, default=PLAN_PATH)
    parser.add_argument("--source-work-authority", type=Path, default=SOURCE_WORK_AUTHORITY_PATH)
    parser.add_argument("--witness-candidates", type=Path, default=DISCOVERY_DIRECTORY / "witness_candidates.tsv")
    parser.add_argument("--witness-classification", type=Path, default=DISCOVERY_DIRECTORY / "witness_classification.tsv")
    parser.add_argument("--witness-verification", type=Path, default=WITNESS_VERIFICATION_PATH)
    parser.add_argument("--witness-snippets", type=Path, default=WITNESS_SNIPPETS_PATH)
    parser.add_argument("--missing-direct-search", type=Path, default=MISSING_DIRECT_SEARCH_PATH)
    parser.add_argument("--source-work-gaps", type=Path, default=SOURCE_WORK_GAPS_PATH)
    parser.add_argument("--sip-witness-inspection", type=Path, default=SIP_WITNESS_INSPECTION_PATH)
    parser.add_argument("--source-witness-content-profile", type=Path, default=SOURCE_WITNESS_CONTENT_PROFILE_PATH)
    parser.add_argument("--eb-fascicle-content-inspection", type=Path, default=EB_FASCICLE_CONTENT_INSPECTION_PATH)
    parser.add_argument("--uem-direct-search", type=Path, default=UEM_DIRECT_SEARCH_PATH)
    parser.add_argument("--core-source-direct-search", type=Path, default=CORE_SOURCE_DIRECT_SEARCH_PATH)
    parser.add_argument("--inscriptions-of-burma-text-search", type=Path, default=INSCRIPTIONS_OF_BURMA_TEXT_SEARCH_PATH)
    parser.add_argument("--inscriptions-of-burma-text-volume-hunt", type=Path, default=INSCRIPTIONS_OF_BURMA_TEXT_VOLUME_HUNT_PATH)
    parser.add_argument("--missing-core-witness-hunt", type=Path, default=MISSING_CORE_WITNESS_HUNT_PATH)
    parser.add_argument("--witness-hunt-candidate-triage", type=Path, default=WITNESS_HUNT_CANDIDATE_TRIAGE_PATH)
    parser.add_argument("--direct-witness-acquisition-plan", type=Path, default=DIRECT_WITNESS_ACQUISITION_PLAN_PATH)
    parser.add_argument("--direct-witness-acquisition-status", type=Path, default=DIRECT_WITNESS_ACQUISITION_STATUS_PATH)
    parser.add_argument("--manual-review-queue", type=Path, default=MANUAL_REVIEW_QUEUE_PATH)
    parser.add_argument("--acquisition-action-queue", type=Path, default=ACQUISITION_ACTION_QUEUE_PATH)
    parser.add_argument("--translation-source-discovery-phase-summary", type=Path, default=TRANSLATION_SOURCE_DISCOVERY_PHASE_SUMMARY_PATH)
    parser.add_argument("--human-acquisition-checklist", type=Path, default=HUMAN_ACQUISITION_CHECKLIST_PATH)
    parser.add_argument("--ruled-out-witness-candidates", type=Path, default=RULED_OUT_WITNESS_CANDIDATES_PATH)
    parser.add_argument("--external-catalogue-search-log", type=Path, default=EXTERNAL_CATALOGUE_SEARCH_LOG_PATH)
    parser.add_argument("--external-catalogue-candidate-triage", type=Path, default=EXTERNAL_CATALOGUE_CANDIDATE_TRIAGE_PATH)
    parser.add_argument("--rescue-candidate-review", type=Path, default=RESCUE_CANDIDATE_REVIEW_PATH)
    parser.add_argument("--epigraphia-birmanica-review", type=Path, default=EPIGRAPHIA_BIRMANICA_REVIEW_PATH)
    parser.add_argument("--epigraphia-birmanica-fascicle-coverage", type=Path, default=EPIGRAPHIA_BIRMANICA_FASCICLE_COVERAGE_PATH)
    parser.add_argument("--periodical-article-plan", type=Path, default=DISCOVERY_DIRECTORY / "periodical_article_discovery_plan.tsv")
    parser.add_argument("--report", type=Path, default=DISCOVERY_DIRECTORY / "translation_source_discovery_report.json")
    parser.add_argument("--witness-verification-report", type=Path, default=WITNESS_VERIFICATION_REPORT_PATH)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    errors = validate_translation_source_discovery(
        plan_path=args.plan,
        source_work_authority_path=args.source_work_authority,
        witness_candidates_path=args.witness_candidates,
        witness_classification_path=args.witness_classification,
        witness_verification_path=args.witness_verification,
        witness_snippets_path=args.witness_snippets,
        missing_direct_search_path=args.missing_direct_search,
        source_work_gaps_path=args.source_work_gaps,
        sip_witness_inspection_path=args.sip_witness_inspection,
        source_witness_content_profile_path=args.source_witness_content_profile,
        eb_fascicle_content_inspection_path=args.eb_fascicle_content_inspection,
        uem_direct_search_path=args.uem_direct_search,
        core_source_direct_search_path=args.core_source_direct_search,
        inscriptions_of_burma_text_search_path=args.inscriptions_of_burma_text_search,
        inscriptions_of_burma_text_volume_hunt_path=args.inscriptions_of_burma_text_volume_hunt,
        missing_core_witness_hunt_path=args.missing_core_witness_hunt,
        witness_hunt_candidate_triage_path=args.witness_hunt_candidate_triage,
        direct_witness_acquisition_plan_path=args.direct_witness_acquisition_plan,
        direct_witness_acquisition_status_path=args.direct_witness_acquisition_status,
        manual_review_queue_path=args.manual_review_queue,
        acquisition_action_queue_path=args.acquisition_action_queue,
        translation_source_discovery_phase_summary_path=args.translation_source_discovery_phase_summary,
        human_acquisition_checklist_path=args.human_acquisition_checklist,
        ruled_out_witness_candidates_path=args.ruled_out_witness_candidates,
        external_catalogue_search_log_path=args.external_catalogue_search_log,
        external_catalogue_candidate_triage_path=args.external_catalogue_candidate_triage,
        rescue_candidate_review_path=args.rescue_candidate_review,
        epigraphia_birmanica_review_path=args.epigraphia_birmanica_review,
        epigraphia_birmanica_fascicle_coverage_path=args.epigraphia_birmanica_fascicle_coverage,
        periodical_article_plan_path=args.periodical_article_plan,
        report_path=args.report,
        witness_verification_report_path=args.witness_verification_report,
    )
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)
    print("Translation-source discovery artifacts are valid.")


if __name__ == "__main__":
    main()
