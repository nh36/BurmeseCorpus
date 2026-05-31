from __future__ import annotations

import argparse
import re
from pathlib import Path

from corpus_common import read_tsv, write_tsv
from jbrs_workflow_common import (
    JBRS_ARTICLE_REFERENCE_TARGETS_PATH,
    JBRS_LOCAL_FILE_MANIFEST_PATH,
    JBRS_OCR_BATCH_PLAN_PATH,
    JBRS_OCR_STATUS_LOG_PATH,
    JBRS_PILOT_SUMMARY_PATH,
    JBRS_REFERENCE_FILE_MATCH_PATH,
    JBRS_REFERENCE_HUNT_RAW_PATH,
    JBRS_TRANSLATION_CANDIDATE_LOG_PATH,
    JBRS_TRANSLATION_CANDIDATE_REVIEW_PATH,
    TRANSLATION_CANDIDATE_FIELDS,
    TRANSLATION_CANDIDATE_REVIEW_FIELDS,
    build_pilot_summary,
    build_translation_candidate_rows,
    build_translation_candidate_review_rows,
    load_review_rows,
    write_summary,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Detect JBRS translation candidates from existing text or OCR text.")
    parser.add_argument("--raw-reference-hunt", type=Path, default=JBRS_REFERENCE_HUNT_RAW_PATH)
    parser.add_argument("--article-targets", type=Path, default=JBRS_ARTICLE_REFERENCE_TARGETS_PATH)
    parser.add_argument("--local-manifest", type=Path, default=JBRS_LOCAL_FILE_MANIFEST_PATH)
    parser.add_argument("--reference-match", type=Path, default=JBRS_REFERENCE_FILE_MATCH_PATH)
    parser.add_argument("--ocr-batch-plan", type=Path, default=JBRS_OCR_BATCH_PLAN_PATH)
    parser.add_argument("--ocr-status-log", type=Path, default=JBRS_OCR_STATUS_LOG_PATH)
    parser.add_argument("--output", type=Path, default=JBRS_TRANSLATION_CANDIDATE_LOG_PATH)
    parser.add_argument("--review-output", type=Path, default=JBRS_TRANSLATION_CANDIDATE_REVIEW_PATH)
    parser.add_argument("--summary-output", type=Path, default=JBRS_PILOT_SUMMARY_PATH)
    parser.add_argument("--local-file-id", action="append", default=[], help="Optional local_file_id filter for a narrow candidate pass.")
    parser.add_argument("--batch-id", action="append", default=[], help="Optional OCR batch_id filter for a narrow candidate pass.")
    return parser.parse_args()


def resolve_selected_local_file_ids(
    manifest_rows: list[dict[str, str]],
    batch_rows: list[dict[str, str]],
    local_file_ids: list[str],
    batch_ids: list[str],
) -> set[str]:
    manifest_ids = {row.get("local_file_id", "") for row in manifest_rows if row.get("local_file_id")}
    selected = {local_file_id for local_file_id in local_file_ids if local_file_id in manifest_ids}
    batch_id_set = {batch_id for batch_id in batch_ids if batch_id}
    if batch_id_set:
        selected.update(
            row.get("local_file_id", "")
            for row in batch_rows
            if row.get("batch_id") in batch_id_set and row.get("local_file_id") in manifest_ids
        )
    return {local_file_id for local_file_id in selected if local_file_id}


def next_candidate_number(rows: list[dict[str, str]]) -> int:
    highest = 0
    for row in rows:
        match = re.fullmatch(r"jbrs-candidate-(\d+)", row.get("candidate_id", ""))
        if match:
            highest = max(highest, int(match.group(1)))
    return highest + 1


def merge_candidate_rows(
    existing_rows: list[dict[str, str]],
    replacement_rows: list[dict[str, str]],
    selected_local_file_ids: set[str],
) -> list[dict[str, str]]:
    existing_by_local_file = {row.get("local_file_id", ""): row for row in existing_rows if row.get("local_file_id")}
    next_number = next_candidate_number(existing_rows)
    merged_replacements: list[dict[str, str]] = []
    for row in replacement_rows:
        merged = dict(row)
        existing = existing_by_local_file.get(merged.get("local_file_id", ""))
        if existing:
            merged["candidate_id"] = existing["candidate_id"]
        else:
            merged["candidate_id"] = f"jbrs-candidate-{next_number:04d}"
            next_number += 1
        merged_replacements.append(merged)
    merged_rows = [row for row in existing_rows if row.get("local_file_id") not in selected_local_file_ids]
    merged_rows.extend(merged_replacements)
    return sorted(merged_rows, key=lambda row: row.get("candidate_id", ""))


def main() -> None:
    args = parse_args()
    raw_reference_rows = read_tsv(args.raw_reference_hunt)
    target_rows = read_tsv(args.article_targets)
    manifest_rows = read_tsv(args.local_manifest)
    match_rows = read_tsv(args.reference_match)
    batch_rows = read_tsv(args.ocr_batch_plan)
    status_rows = read_tsv(args.ocr_status_log)
    selected_local_file_ids = resolve_selected_local_file_ids(
        manifest_rows,
        batch_rows,
        args.local_file_id,
        args.batch_id,
    )
    existing_rows = read_tsv(args.output) if args.output.exists() else []
    filtered_manifest_rows = manifest_rows
    filtered_match_rows = match_rows
    if selected_local_file_ids:
        filtered_manifest_rows = [
            row for row in manifest_rows if row.get("local_file_id") in selected_local_file_ids
        ]
        filtered_match_rows = [
            row for row in match_rows if row.get("local_file_id") in selected_local_file_ids
        ]
    replacement_rows = build_translation_candidate_rows(target_rows, filtered_manifest_rows, filtered_match_rows, status_rows)
    rows = (
        merge_candidate_rows(existing_rows, replacement_rows, selected_local_file_ids)
        if selected_local_file_ids
        else replacement_rows
    )
    existing_review_rows = load_review_rows(args.review_output, "candidate_id")
    review_rows = build_translation_candidate_review_rows(rows, existing_review_rows)
    write_tsv(args.output, rows, TRANSLATION_CANDIDATE_FIELDS)
    write_tsv(args.review_output, review_rows, TRANSLATION_CANDIDATE_REVIEW_FIELDS)
    summary = build_pilot_summary(raw_reference_rows, target_rows, manifest_rows, match_rows, batch_rows, status_rows, rows)
    write_summary(args.summary_output, summary)
    print(f"Wrote {len(rows)} JBRS translation-candidate rows to {args.output}")
    print(f"Wrote {len(review_rows)} JBRS translation-candidate review rows to {args.review_output}")


if __name__ == "__main__":
    main()
