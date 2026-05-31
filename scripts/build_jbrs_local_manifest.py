from __future__ import annotations

import argparse
from pathlib import Path

from corpus_common import write_tsv
from jbrs_workflow_common import (
    DEFAULT_RUNTIME_PATH_CACHE,
    JBRS_LOCAL_FILE_MANIFEST_PATH,
    LOCAL_FILE_MANIFEST_FIELDS,
    SOURCE_LIBRARY_MANIFEST_PATH,
    LOCAL_FILE_MANIFEST_PATH,
    OCR_MANIFEST_PATH,
    build_local_manifest_rows,
    write_runtime_path_cache,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the JBRS local-file manifest without committing absolute paths.")
    parser.add_argument("--output", type=Path, default=JBRS_LOCAL_FILE_MANIFEST_PATH)
    parser.add_argument("--root", action="append", type=Path, default=[], help="Optional external-drive root to scan.")
    parser.add_argument("--source-library-manifest", type=Path, default=SOURCE_LIBRARY_MANIFEST_PATH)
    parser.add_argument("--local-file-manifest", type=Path, default=LOCAL_FILE_MANIFEST_PATH)
    parser.add_argument("--ocr-manifest", type=Path, default=OCR_MANIFEST_PATH)
    parser.add_argument("--runtime-path-cache", type=Path, default=DEFAULT_RUNTIME_PATH_CACHE)
    parser.add_argument("--write-runtime-path-cache", action="store_true", help="Write local_file_id -> absolute runtime path map under data_local/.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows, runtime_path_cache = build_local_manifest_rows(
        roots=args.root,
        existing_source_library_path=args.source_library_manifest,
        existing_local_manifest_path=args.local_file_manifest,
        existing_ocr_manifest_path=args.ocr_manifest,
        mark_runtime_available=args.write_runtime_path_cache or args.runtime_path_cache.exists(),
    )
    write_tsv(args.output, rows, LOCAL_FILE_MANIFEST_FIELDS)
    if args.write_runtime_path_cache and runtime_path_cache:
        write_runtime_path_cache(args.runtime_path_cache, runtime_path_cache)
        print(f"Wrote {len(runtime_path_cache)} runtime path mappings to {args.runtime_path_cache}")
    elif args.write_runtime_path_cache:
        print(f"No live runtime paths were found to write to {args.runtime_path_cache}")
    print(f"Wrote {len(rows)} JBRS local-manifest rows to {args.output}")


if __name__ == "__main__":
    main()
