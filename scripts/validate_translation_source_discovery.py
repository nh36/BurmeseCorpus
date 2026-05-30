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


ABSOLUTE_PATH_PATTERN = re.compile(r"(^/(?:Users|home|var|private|tmp|opt|Volumes)\b|^[A-Za-z]:\\\\)")
SHORT_EVIDENCE_LIMIT = 280


def validate_translation_source_discovery(
    *,
    plan_path: Path = PLAN_PATH,
    source_work_authority_path: Path = SOURCE_WORK_AUTHORITY_PATH,
    witness_candidates_path: Path = DISCOVERY_DIRECTORY / "witness_candidates.tsv",
    witness_classification_path: Path = DISCOVERY_DIRECTORY / "witness_classification.tsv",
    periodical_article_plan_path: Path = DISCOVERY_DIRECTORY / "periodical_article_discovery_plan.tsv",
    report_path: Path = DISCOVERY_DIRECTORY / "translation_source_discovery_report.json",
) -> list[str]:
    errors: list[str] = []
    for path in [plan_path, source_work_authority_path, witness_candidates_path, witness_classification_path, periodical_article_plan_path, report_path]:
        if not path.exists():
            errors.append(f"Missing required discovery artifact: {path.relative_to(REPO_ROOT)}")
    if errors:
        return errors

    plan_rows = read_tsv(plan_path)
    source_rows = read_tsv(source_work_authority_path)
    candidate_rows = read_tsv(witness_candidates_path)
    classification_rows = read_tsv(witness_classification_path)
    periodical_plan_rows = read_tsv(periodical_article_plan_path)
    report = json.loads(report_path.read_text(encoding="utf-8"))

    source_by_key = {row["source_work_key"]: row for row in source_rows}
    candidate_by_id = {row["witness_id"]: row for row in candidate_rows}
    candidate_counts: dict[str, int] = {}
    classification_counts: dict[str, int] = {}
    confirmed_translation_counts: dict[str, int] = {}
    confirmed_edition_counts: dict[str, int] = {}
    confirmed_plate_counts: dict[str, int] = {}

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
            if source_row.get("authority_level") in {"series", "periodical"} and row.get("witness_type") in {
                "translation_source",
                "edition_and_translation",
                "source_edition",
            }:
                errors.append(
                    f"Witness classification {witness_id} promotes series/periodical {source_key} to a direct source witness without article-level handling"
                )

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

    planned_periodical_keys = {row.get("series_source_work_key", "") for row in periodical_plan_rows}
    for required_key in PERIODICAL_PLAN_KEYS:
        if required_key not in planned_periodical_keys:
            errors.append(f"Periodical article discovery plan is missing {required_key}")

    report_candidate_count = report.get("candidate_witness_count")
    report_classified_count = report.get("classified_witness_count")
    if report_candidate_count != len(candidate_rows):
        errors.append("translation_source_discovery_report.json has inconsistent candidate_witness_count")
    if report_classified_count != len(classification_rows):
        errors.append("translation_source_discovery_report.json has inconsistent classified_witness_count")
    if not isinstance(report.get("notes"), list):
        errors.append("translation_source_discovery_report.json notes must be a list")

    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate translation-source discovery artifacts.")
    parser.add_argument("--plan", type=Path, default=PLAN_PATH)
    parser.add_argument("--source-work-authority", type=Path, default=SOURCE_WORK_AUTHORITY_PATH)
    parser.add_argument("--witness-candidates", type=Path, default=DISCOVERY_DIRECTORY / "witness_candidates.tsv")
    parser.add_argument("--witness-classification", type=Path, default=DISCOVERY_DIRECTORY / "witness_classification.tsv")
    parser.add_argument("--periodical-article-plan", type=Path, default=DISCOVERY_DIRECTORY / "periodical_article_discovery_plan.tsv")
    parser.add_argument("--report", type=Path, default=DISCOVERY_DIRECTORY / "translation_source_discovery_report.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    errors = validate_translation_source_discovery(
        plan_path=args.plan,
        source_work_authority_path=args.source_work_authority,
        witness_candidates_path=args.witness_candidates,
        witness_classification_path=args.witness_classification,
        periodical_article_plan_path=args.periodical_article_plan,
        report_path=args.report,
    )
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)
    print("Translation-source discovery artifacts are valid.")


if __name__ == "__main__":
    main()
