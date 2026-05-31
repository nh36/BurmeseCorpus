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
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows, runtime_path_cache = build_local_manifest_rows(
        roots=args.root,
        existing_source_library_path=args.source_library_manifest,
        existing_local_manifest_path=args.local_file_manifest,
        existing_ocr_manifest_path=args.ocr_manifest,
    )
    write_tsv(args.output, rows, LOCAL_FILE_MANIFEST_FIELDS)
    if runtime_path_cache:
        write_runtime_path_cache(args.runtime_path_cache, runtime_path_cache)
        print(f"Wrote {len(runtime_path_cache)} runtime path mappings to {args.runtime_path_cache}")
    print(f"Wrote {len(rows)} JBRS local-manifest rows to {args.output}")


if __name__ == "__main__":
    main()
