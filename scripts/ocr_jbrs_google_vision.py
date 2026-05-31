from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from corpus_common import ensure_parent, read_tsv, write_tsv
from jbrs_workflow_common import (
    DEFAULT_LOCAL_OUTPUT_ROOT,
    DEFAULT_RUNTIME_PATH_CACHE,
    JBRS_OCR_BATCH_PLAN_PATH,
    JBRS_OCR_STATUS_LOG_PATH,
    OCR_STATUS_LOG_FIELDS,
    now_iso,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dry-run or stage the JBRS Google Vision OCR workflow.")
    parser.add_argument("--batch-plan", type=Path, default=JBRS_OCR_BATCH_PLAN_PATH)
    parser.add_argument("--status-log", type=Path, default=JBRS_OCR_STATUS_LOG_PATH)
    parser.add_argument("--runtime-path-cache", type=Path, default=DEFAULT_RUNTIME_PATH_CACHE)
    parser.add_argument("--local-output-root", type=Path, default=DEFAULT_LOCAL_OUTPUT_ROOT)
    parser.add_argument("--batch-id", action="append", default=[], help="Optional batch_id filter.")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true", help="Validate staged OCR work without submitting anything.")
    parser.add_argument("--execute", action="store_true", help="Attempt a live OCR run. This scaffold currently validates inputs and writes sidecars only.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.dry_run and not args.execute:
        args.dry_run = True
    batch_rows = read_tsv(args.batch_plan)
    status_rows = {row.get("batch_id", ""): row for row in read_tsv(args.status_log)} if args.status_log.exists() else {}
    runtime_path_cache = json.loads(args.runtime_path_cache.read_text(encoding="utf-8")) if args.runtime_path_cache.exists() else {}
    selected_rows = [
        row
        for row in batch_rows
        if row.get("status") == "ready_for_ocr" and (not args.batch_id or row.get("batch_id") in set(args.batch_id))
    ]
    if args.limit > 0:
        selected_rows = selected_rows[: args.limit]

    for subdir in ["manifest", "google_vision_json", "page_text", "article_text", "logs"]:
        ensure_parent(args.local_output_root / subdir / ".keep")

    for row in selected_rows:
        batch_id = row.get("batch_id", "")
        local_file_id = row.get("local_file_id", "")
        status = status_rows.get(batch_id, {}).copy()
        status.update(
            {
                "ocr_job_id": f"{batch_id}-run",
                "batch_id": batch_id,
                "local_file_id": local_file_id,
                "file_name": row.get("file_name", ""),
                "ocr_engine": row.get("ocr_engine", ""),
                "ocr_scope": row.get("ocr_scope", ""),
                "pages_submitted": row.get("page_count_estimate", ""),
                "pages_completed": "",
                "output_path_stub": f"data_local/ocr/jbrs/page_text/{row.get('output_basename', '')}.txt",
                "metadata_sidecar_stub": row.get("metadata_sidecar_path", ""),
                "error_type": "",
                "error_message_short": "",
                "created_at": status.get("created_at", now_iso()),
                "updated_at": now_iso(),
                "notes": "JBRS OCR script updates committed status metadata only; OCR output stays outside git.",
            }
        )
        if args.dry_run:
            status["status"] = "dry_run_ok"
            status["notes"] = "Dry run succeeded; no OCR submission was attempted."
        else:
            source_path = runtime_path_cache.get(local_file_id, "")
            if not source_path:
                status["status"] = "failed"
                status["error_type"] = "missing_runtime_path"
                status["error_message_short"] = "Run build_jbrs_local_manifest.py with --root to write a local runtime path cache."
            elif not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
                status["status"] = "failed"
                status["error_type"] = "missing_google_credentials"
                status["error_message_short"] = "Set GOOGLE_APPLICATION_CREDENTIALS before live OCR."
            else:
                sidecar_path = args.local_output_root / "manifest" / f"{row.get('output_basename', '')}.json"
                ensure_parent(sidecar_path)
                sidecar_path.write_text(
                    json.dumps(
                        {
                            "local_file_id": local_file_id,
                            "source_file_name": row.get("file_name", ""),
                            "path_stub": row.get("path_stub", ""),
                            "journal": "Journal of the Burma Research Society",
                            "volume": row.get("volume", ""),
                            "issue": row.get("issue", ""),
                            "year": row.get("year", ""),
                            "ocr_engine": row.get("ocr_engine", ""),
                            "ocr_date": now_iso(),
                            "page_count": row.get("page_count_estimate", ""),
                            "language_hints": ["en", "my"],
                            "image_preprocessing_used": "",
                            "google_vision_batch_id_if_any": "",
                            "checksum_or_file_fingerprint": "",
                            "notes": "Live Google Vision submission is intentionally not automated in this repository-only scaffold.",
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                    + "\n",
                    encoding="utf-8",
                )
                status["status"] = "failed"
                status["error_type"] = "live_submission_not_implemented"
                status["error_message_short"] = "This scaffold stops after writing a metadata sidecar; submit to Google Vision manually or extend the script locally."
        status_rows[batch_id] = status

    write_tsv(args.status_log, [status_rows[key] for key in sorted(status_rows)], OCR_STATUS_LOG_FIELDS)
    print(f"Updated {len(selected_rows)} JBRS OCR status rows in {args.status_log}")


if __name__ == "__main__":
    main()
