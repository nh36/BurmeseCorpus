from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

from bibtex_common import duplicate_keys, parse_bibtex_text
from corpus_common import read_tsv


ABSOLUTE_PATH_PATTERN = re.compile(r"(^/(?:Users|home|var|private|tmp|opt|Volumes)\b|^[A-Za-z]:\\\\)")
GENERIC_KEY_PATTERN = re.compile(r"^(?:work|sourceunresolved)\d+$", flags=re.IGNORECASE)
MAX_BIBTEX_FIELD_LENGTH = 280
MAX_MATCHED_LOCAL_REFERENCE_LENGTH = 140


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
    frasch_references_path: Path | None = None,
    local_manifest_path: Path | None = None,
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
    frasch_rows = read_tsv(frasch_references_path) if frasch_references_path and frasch_references_path.exists() else []
    manifest_rows = read_tsv(local_manifest_path) if local_manifest_path and local_manifest_path.exists() else []

    authority_keys = {entry["bibtex_key"] for entry in authority_entries}
    candidate_keys = {entry["bibtex_key"] for entry in candidate_entries}
    valid_keys = authority_keys | candidate_keys
    family_ids = {row["family_id"] for row in family_rows}
    external_keys = {row["bibtex_key"] for row in external_rows}
    frasch_ids = {row.get("frasch_ref_id", "") for row in frasch_rows if row.get("frasch_ref_id")}
    manifest_ids = {row.get("canonical_local_file_id", "") for row in manifest_rows if row.get("canonical_local_file_id")}
    evidence_by_key = {row.get("bibtex_key", ""): row for row in evidence_rows if row.get("bibtex_key")}

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
        if row["match_type"] != "no_match" and row["bibtex_key"] not in valid_keys:
            errors.append(f"raw_reference_to_bibtex[{index}] references missing bibtex_key {row['bibtex_key']}")
        if row["family_id"] not in family_ids:
            errors.append(f"raw_reference_to_bibtex[{index}] references unknown family_id {row['family_id']}")
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
        if row["authority_status"] in {"machine_stub", "provisional_catalogue", "provisional_publication", "provisional_local_source", "needs_human_review"}:
            if not row["review_status"]:
                errors.append(f"bibtex_authority[{index}] is provisional but missing review_status")
            if not row["evidence"] and not row["notes"]:
                errors.append(f"bibtex_authority[{index}] is provisional but missing evidence or notes")
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
                if row.get("current_status", "").startswith("resolved:") and (not row.get("evidence_source") or not row.get("notes")):
                    errors.append(f"high_frequency_resolution_plan[{index}] is resolved but missing evidence_source or notes")

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
        "--frasch-references",
        type=Path,
        default=Path("data/working/bibliography/local_sources/frasch_reference_entries.tsv"),
    )
    parser.add_argument(
        "--local-manifest",
        type=Path,
        default=Path("data/working/bibliography/local_sources/local_file_manifest.tsv"),
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
        frasch_references_path=args.frasch_references,
        local_manifest_path=args.local_manifest,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
