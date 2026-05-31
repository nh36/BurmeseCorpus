from __future__ import annotations

from ocr_jbrs_google_vision import parse_args, preflight_report, select_batch_rows, write_preflight_report
from corpus_common import read_tsv
from jbrs_workflow_common import DEFAULT_RUNTIME_PATH_CACHE


def main() -> None:
    args = parse_args()
    batch_rows = read_tsv(args.batch_plan)
    runtime_path_cache = {}
    if args.runtime_path_cache.exists():
        import json

        runtime_path_cache = json.loads(args.runtime_path_cache.read_text(encoding="utf-8"))
    selected_rows = select_batch_rows(batch_rows, args.batch_id, args.limit)
    report = preflight_report(
        selected_rows=selected_rows,
        runtime_path_cache=runtime_path_cache,
        local_output_root=args.local_output_root,
        live_mode=args.execute and not args.dry_run,
    )
    write_preflight_report(args.preflight_report, report)
    if report["errors"]:
        for error in report["errors"]:
            print(f"ERROR: {error}")
        raise SystemExit(1)
    print(f"JBRS OCR preflight passed for {len(selected_rows)} batch row(s). Report written to {args.preflight_report}")


if __name__ == "__main__":
    main()
