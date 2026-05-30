from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

from build_bibtex_authority import RESOLUTION_LEVELS, RESOLUTION_STATUSES
from bibtex_common import duplicate_keys, parse_bibtex_text
from corpus_common import read_tsv
from extract_bibliography_acronyms import PRIORITY_ACRONYMS, STRONG_DEFINITION_EVIDENCE_TYPES


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
                if status not in allowed_acronym_statuses:
                    errors.append(f"acronym_resolution_status[{index}] has invalid resolution_status {status}")
                if status in review_required and row.get("needs_human_review") != "true":
                    errors.append(f"acronym_resolution_status[{index}] should require human review for {status}")
                if status == "contextual_usage_only" and row.get("best_evidence_id"):
                    candidate_row = acronym_candidate_by_id.get(row["best_evidence_id"])
                    if candidate_row and candidate_row.get("evidence_type") in STRONG_DEFINITION_EVIDENCE_TYPES:
                        errors.append(f"acronym_resolution_status[{index}] marks strong evidence as contextual usage only")
                if status in strong_statuses:
                    evidence_id = row.get("best_evidence_id", "")
                    candidate_row = acronym_candidate_by_id.get(evidence_id)
                    if not candidate_row or candidate_row.get("evidence_type") not in STRONG_DEFINITION_EVIDENCE_TYPES:
                        errors.append(f"acronym_resolution_status[{index}] requires strong evidence for {status}")
                if status == "confirmed_expansion" and not row.get("current_expansion"):
                    errors.append(f"acronym_resolution_status[{index}] confirmed expansion is missing current_expansion")

    if acronym_candidates_path and acronym_candidates_path.exists():
        for index, row in enumerate(acronym_candidate_rows, start=1):
            if row.get("definition_quality") == "explicit" and row.get("evidence_type") == "contextual_usage":
                errors.append(f"acronym_definition_candidates[{index}] cannot mark contextual usage as explicit")
            for value in row.values():
                if has_absolute_path(value):
                    errors.append(f"acronym_definition_candidates[{index}] contains an absolute local path")
                    break

    if source_family_rows:
        for index, row in enumerate(source_family_rows, start=1):
            acronym_status = row.get("acronym_resolution_status", "")
            expanded_label = row.get("expanded_label", "")
            if acronym_status in {"source_family_only", "contextual_usage_only", "unresolved"} and expanded_label and not PLACEHOLDER_EXPANSION_PATTERN.search(expanded_label):
                errors.append(f"source_family_authority[{index}] exposes an unverified expansion for {row.get('abbreviation')}")
            if acronym_status in {"confirmed_expansion", "probable_expansion"} and row.get("best_definition_evidence_id"):
                candidate_row = acronym_candidate_by_id.get(row["best_definition_evidence_id"])
                if not candidate_row or candidate_row.get("evidence_type") not in STRONG_DEFINITION_EVIDENCE_TYPES:
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
        if path.casefold().endswith((".pdf", ".doc", ".docx", ".djvu")):
            errors.append(f"tracked local source binary found in git: {path}")

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
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
