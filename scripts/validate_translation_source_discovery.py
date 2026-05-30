from __future__ import annotations

import argparse
import json
import re
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
    CORE_SOURCE_DIRECT_SEARCH_PATH,
    DIRECT_SEARCH_RESULT_STATUSES,
    DIRECTNESS_VALUES,
    EVIDENCE_QUALITY_VALUES,
    EPIGRAPHIA_BIRMANICA_FASCICLE_COVERAGE_PATH,
    EPIGRAPHIA_BIRMANICA_REVIEW_PATH,
    INSCRIPTIONS_OF_BURMA_TEXT_SEARCH_PATH,
    MISSING_DIRECT_SEARCH_PATH,
    RESCUE_CANDIDATE_REVIEW_PATH,
    SIP_WITNESS_ID,
    SIP_WITNESS_INSPECTION_PATH,
    SOURCE_WORK_GAPS_PATH,
    UEM_DIRECT_SEARCH_PATH,
    VERIFICATION_STATUSES,
    WITNESS_SNIPPETS_PATH,
    WITNESS_VERIFICATION_PATH,
    WITNESS_VERIFICATION_REPORT_PATH,
)


ABSOLUTE_PATH_PATTERN = re.compile(r"(^/(?:Users|home|var|private|tmp|opt|Volumes)\b|^[A-Za-z]:\\\\)")
SHORT_EVIDENCE_LIMIT = 280
DIRECT_VERIFICATION_STATUSES = {"verified_direct_witness", "verified_catalogue_witness"}


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
    uem_direct_search_path: Path = UEM_DIRECT_SEARCH_PATH,
    core_source_direct_search_path: Path = CORE_SOURCE_DIRECT_SEARCH_PATH,
    inscriptions_of_burma_text_search_path: Path = INSCRIPTIONS_OF_BURMA_TEXT_SEARCH_PATH,
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
        uem_direct_search_path,
        core_source_direct_search_path,
        inscriptions_of_burma_text_search_path,
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
    uem_search_rows = read_tsv(uem_direct_search_path)
    core_search_rows = read_tsv(core_source_direct_search_path)
    iob_text_search_rows = read_tsv(inscriptions_of_burma_text_search_path)
    rescue_review_rows = read_tsv(rescue_candidate_review_path)
    epigraphia_review_rows = read_tsv(epigraphia_birmanica_review_path)
    epigraphia_fascicle_coverage_rows = read_tsv(epigraphia_birmanica_fascicle_coverage_path)
    periodical_plan_rows = read_tsv(periodical_article_plan_path)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    verification_report = json.loads(witness_verification_report_path.read_text(encoding="utf-8"))

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
        supporting_sip_rows = [row for row in sip_inspection_rows if row.get("witness_id") == SIP_WITNESS_ID and row.get("contains_edition_or_transliteration") == "true" and row.get("evidence_snippet")]
        if not supporting_sip_rows:
            errors.append("SIP edition confirmation lacks supporting sip_witness_inspection evidence")
    if sip_verification and sip_verification.get("contains_translation_verified") == "confirmed":
        supporting_translation_rows = [row for row in sip_inspection_rows if row.get("witness_id") == SIP_WITNESS_ID and row.get("contains_translation") == "true" and row.get("evidence_snippet")]
        if not supporting_translation_rows:
            errors.append("SIP translation confirmation lacks supporting sip_witness_inspection evidence")

    for row in sip_inspection_rows:
        if row.get("witness_id") not in candidate_by_id:
            errors.append(f"SIP inspection row {row.get('witness_id')} has no matching witness candidate row")
        if len(row.get("evidence_snippet", "")) > SHORT_EVIDENCE_LIMIT or "\n" in row.get("evidence_snippet", ""):
            errors.append(f"SIP inspection row {row.get('witness_id')} stores more than a short evidence snippet")
    if sip_inspection_rows and not any(
        row.get("inspection_area") in {"contents", "preface", "sample_entry", "headings", "notes_or_commentary"}
        for row in sip_inspection_rows
    ):
        errors.append("SIP inspection remains title-page only; sample-entry or other follow-on inspection rows are required")

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
    ]:
        for row in rows:
            for field in ["searched_sources", "search_scope", "search_date_or_run_id", "search_result_status"]:
                if not row.get(field):
                    errors.append(f"{collection_name} row for {row.get('query', '') or row.get('source_work_key', '')} is missing {field}")
            if row.get("search_result_status") not in DIRECT_SEARCH_RESULT_STATUSES:
                errors.append(f"{collection_name} row uses invalid search_result_status {row.get('search_result_status')}")

    for collection_name, rows in [
        ("source-work witness gaps", gap_rows),
        ("UEM direct search", uem_search_rows),
        ("core direct search", core_search_rows),
        ("Inscriptions of Burma text search", iob_text_search_rows),
        ("rescue candidate review", rescue_review_rows),
        ("epigraphia birmanica review", epigraphia_review_rows),
        ("epigraphia birmanica fascicle coverage", epigraphia_fascicle_coverage_rows),
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
    if report.get("sip_inspection_completed") != bool(sip_inspection_rows):
        errors.append("translation_source_discovery_report.json has inconsistent sip_inspection_completed")
    if report.get("uem_direct_search_count") != sum(bool(row.get("matched_file_label")) for row in uem_search_rows):
        errors.append("translation_source_discovery_report.json has inconsistent uem_direct_search_count")
    if report.get("core_source_direct_search_count") != sum(bool(row.get("matched_file_label")) for row in core_search_rows):
        errors.append("translation_source_discovery_report.json has inconsistent core_source_direct_search_count")
    if report.get("inscriptions_of_burma_text_witness_search_count") != len(iob_text_search_rows):
        errors.append("translation_source_discovery_report.json has inconsistent inscriptions_of_burma_text_witness_search_count")
    if report.get("inscriptions_of_burma_text_witness_found") != sum(row.get("search_result_status") == "direct_witness_found" for row in iob_text_search_rows):
        errors.append("translation_source_discovery_report.json has inconsistent inscriptions_of_burma_text_witness_found")
    if report.get("rescue_candidate_review_count") != len(rescue_review_rows):
        errors.append("translation_source_discovery_report.json has inconsistent rescue_candidate_review_count")
    if report.get("epigraphia_birmanica_review_count") != len(epigraphia_review_rows):
        errors.append("translation_source_discovery_report.json has inconsistent epigraphia_birmanica_review_count")
    if report.get("eb_verified_fascicle_count") != len(epigraphia_fascicle_coverage_rows):
        errors.append("translation_source_discovery_report.json has inconsistent eb_verified_fascicle_count")
    if report.get("eb_fascicle_coverage_count") != len(epigraphia_fascicle_coverage_rows):
        errors.append("translation_source_discovery_report.json has inconsistent eb_fascicle_coverage_count")
    if report.get("sip_sample_entry_inspected") != any(row.get("inspection_area") == "sample_entry" for row in sip_inspection_rows):
        errors.append("translation_source_discovery_report.json has inconsistent sip_sample_entry_inspected")
    expected_sip_translation_status = next(
        (row.get("contains_translation") for row in sip_inspection_rows if row.get("inspection_area") == "sample_entry"),
        "unknown",
    )
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
    if verification_report.get("inscriptions_of_burma_text_witness_search_count") != len(iob_text_search_rows):
        errors.append("witness_verification_report.json has inconsistent inscriptions_of_burma_text_witness_search_count")
    if verification_report.get("eb_fascicle_coverage_count") != len(epigraphia_fascicle_coverage_rows):
        errors.append("witness_verification_report.json has inconsistent eb_fascicle_coverage_count")
    if verification_report.get("direct_witness_search_result_counts") != expected_search_result_counts:
        errors.append("witness_verification_report.json has inconsistent direct_witness_search_result_counts")
    if not isinstance(verification_report.get("notes"), list):
        errors.append("witness_verification_report.json notes must be a list")

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
    parser.add_argument("--uem-direct-search", type=Path, default=UEM_DIRECT_SEARCH_PATH)
    parser.add_argument("--core-source-direct-search", type=Path, default=CORE_SOURCE_DIRECT_SEARCH_PATH)
    parser.add_argument("--inscriptions-of-burma-text-search", type=Path, default=INSCRIPTIONS_OF_BURMA_TEXT_SEARCH_PATH)
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
        uem_direct_search_path=args.uem_direct_search,
        core_source_direct_search_path=args.core_source_direct_search,
        inscriptions_of_burma_text_search_path=args.inscriptions_of_burma_text_search,
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
