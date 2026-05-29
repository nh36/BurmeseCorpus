from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from bibtex_common import duplicate_keys, parse_bibtex_text
from corpus_common import read_tsv


ABSOLUTE_PATH_PATTERN = re.compile(r"(^/(?:Users|home|var|private|tmp|opt|Volumes)\b|^[A-Za-z]:\\\\)")


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
) -> dict:
    errors: list[str] = []
    authority_entries, authority_warnings = parse_bibtex_text(authority_bib_path.read_text(encoding="utf-8"), source_label=authority_bib_path.name)
    candidate_entries, candidate_warnings = parse_bibtex_text(candidates_bib_path.read_text(encoding="utf-8"), source_label=candidates_bib_path.name)
    authority_rows = read_tsv(authority_tsv_path)
    crosswalk_rows = read_tsv(crosswalk_path)
    family_rows = read_tsv(families_path)
    external_rows = read_tsv(external_entries_path) if external_entries_path and external_entries_path.exists() else []

    authority_keys = {entry["bibtex_key"] for entry in authority_entries}
    candidate_keys = {entry["bibtex_key"] for entry in candidate_entries}
    valid_keys = authority_keys | candidate_keys
    family_ids = {row["family_id"] for row in family_rows}
    external_keys = {row["bibtex_key"] for row in external_rows}

    duplicate_all = sorted(set(duplicate_keys(authority_entries) + duplicate_keys(candidate_entries) + list(authority_keys & candidate_keys)))
    if duplicate_all:
        errors.append(f"duplicate BibTeX keys detected: {', '.join(duplicate_all[:10])}")
    if authority_warnings:
        errors.append(f"authority BibTeX parse warnings: {authority_warnings[0]}")
    if candidate_warnings:
        errors.append(f"candidate BibTeX parse warnings: {candidate_warnings[0]}")

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
        "provisional_catalogue",
        "provisional_publication",
        "machine_stub",
        "needs_human_review",
    }
    for index, row in enumerate(authority_rows, start=1):
        if row["authority_status"] not in allowed_statuses:
            errors.append(f"bibtex_authority[{index}] has invalid authority_status {row['authority_status']}")
        if row["matched_external_key"] and row["matched_external_key"] not in external_keys:
            errors.append(f"bibtex_authority[{index}] references missing matched_external_key {row['matched_external_key']}")
        if row["family_id"] and row["family_id"] not in family_ids:
            errors.append(f"bibtex_authority[{index}] references unknown family_id {row['family_id']}")
        if row["authority_status"] in {"machine_stub", "provisional_catalogue", "provisional_publication", "needs_human_review"}:
            if not row["review_status"]:
                errors.append(f"bibtex_authority[{index}] is provisional but missing review_status")
            if not row["evidence"] and not row["notes"]:
                errors.append(f"bibtex_authority[{index}] is provisional but missing evidence or notes")
        for value in row.values():
            if has_absolute_path(value):
                errors.append(f"bibtex_authority[{index}] contains an absolute local path")
                break

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
    args = parser.parse_args()

    result = validate_bibtex_authority(
        authority_bib_path=args.authority_bib,
        candidates_bib_path=args.candidate_bib,
        authority_tsv_path=args.authority_tsv,
        crosswalk_path=args.crosswalk,
        families_path=args.families,
        external_entries_path=args.external_entries,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
