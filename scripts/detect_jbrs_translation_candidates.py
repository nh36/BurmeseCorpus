from __future__ import annotations

import argparse
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
    TRANSLATION_CANDIDATE_FIELDS,
    build_pilot_summary,
    build_translation_candidate_rows,
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
    parser.add_argument("--summary-output", type=Path, default=JBRS_PILOT_SUMMARY_PATH)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    raw_reference_rows = read_tsv(args.raw_reference_hunt)
    target_rows = read_tsv(args.article_targets)
    manifest_rows = read_tsv(args.local_manifest)
    match_rows = read_tsv(args.reference_match)
    batch_rows = read_tsv(args.ocr_batch_plan)
    status_rows = read_tsv(args.ocr_status_log)
    rows = build_translation_candidate_rows(target_rows, manifest_rows, match_rows, status_rows)
    write_tsv(args.output, rows, TRANSLATION_CANDIDATE_FIELDS)
    summary = build_pilot_summary(raw_reference_rows, target_rows, manifest_rows, match_rows, batch_rows, status_rows, rows)
    write_summary(args.summary_output, summary)
    print(f"Wrote {len(rows)} JBRS translation-candidate rows to {args.output}")


if __name__ == "__main__":
    main()
