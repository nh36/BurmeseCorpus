from __future__ import annotations

import argparse
from pathlib import Path

from corpus_common import read_tsv, write_tsv
from jbrs_workflow_common import (
    DEFAULT_RUNTIME_PATH_CACHE,
    JBRS_LOCAL_FILE_MANIFEST_PATH,
    JBRS_OCR_BATCH_PLAN_PATH,
    JBRS_OCR_STATUS_LOG_PATH,
    JBRS_PILOT_SUMMARY_PATH,
    JBRS_REFERENCE_FILE_MATCH_PATH,
    JBRS_REFERENCE_HUNT_PATH,
    JBRS_TRANSLATION_CANDIDATE_LOG_PATH,
    OCR_BATCH_PLAN_FIELDS,
    OCR_STATUS_LOG_FIELDS,
    TRANSLATION_CANDIDATE_FIELDS,
    build_ocr_batch_plan_rows,
    build_ocr_status_log_rows,
    build_pilot_summary,
    write_summary,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the JBRS OCR batch plan, status log, and initial pilot summary.")
    parser.add_argument("--reference-hunt", type=Path, default=JBRS_REFERENCE_HUNT_PATH)
    parser.add_argument("--local-manifest", type=Path, default=JBRS_LOCAL_FILE_MANIFEST_PATH)
    parser.add_argument("--reference-match", type=Path, default=JBRS_REFERENCE_FILE_MATCH_PATH)
    parser.add_argument("--runtime-path-cache", type=Path, default=DEFAULT_RUNTIME_PATH_CACHE)
    parser.add_argument("--batch-output", type=Path, default=JBRS_OCR_BATCH_PLAN_PATH)
    parser.add_argument("--status-output", type=Path, default=JBRS_OCR_STATUS_LOG_PATH)
    parser.add_argument("--candidate-log", type=Path, default=JBRS_TRANSLATION_CANDIDATE_LOG_PATH)
    parser.add_argument("--summary-output", type=Path, default=JBRS_PILOT_SUMMARY_PATH)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    reference_rows = read_tsv(args.reference_hunt)
    manifest_rows = read_tsv(args.local_manifest)
    match_rows = read_tsv(args.reference_match)
    runtime_path_cache = {}
    if args.runtime_path_cache.exists():
        runtime_path_cache = __import__("json").loads(args.runtime_path_cache.read_text(encoding="utf-8"))
    batch_rows = build_ocr_batch_plan_rows(manifest_rows, match_rows, runtime_path_cache)
    status_rows = build_ocr_status_log_rows(batch_rows)
    write_tsv(args.batch_output, batch_rows, OCR_BATCH_PLAN_FIELDS)
    write_tsv(args.status_output, status_rows, OCR_STATUS_LOG_FIELDS)
    if not args.candidate_log.exists():
        write_tsv(args.candidate_log, [], TRANSLATION_CANDIDATE_FIELDS)
        candidate_rows = []
    else:
        candidate_rows = read_tsv(args.candidate_log)
    summary = build_pilot_summary(reference_rows, manifest_rows, match_rows, batch_rows, status_rows, candidate_rows)
    write_summary(args.summary_output, summary)
    print(f"Wrote {len(batch_rows)} JBRS OCR batch rows to {args.batch_output}")
    print(f"Wrote {len(status_rows)} JBRS OCR status rows to {args.status_output}")
    print(f"Wrote JBRS pilot summary to {args.summary_output}")


if __name__ == "__main__":
    main()
