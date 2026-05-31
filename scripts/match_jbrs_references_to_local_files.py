from __future__ import annotations

import argparse
from pathlib import Path

from corpus_common import read_tsv, write_tsv
from jbrs_workflow_common import (
    JBRS_ARTICLE_REFERENCE_TARGETS_PATH,
    JBRS_ARTICLE_REFERENCE_TARGETS_REVIEW_PATH,
    JBRS_LOCAL_FILE_MANIFEST_PATH,
    JBRS_REFERENCE_FILE_MATCH_PATH,
    REFERENCE_FILE_MATCH_FIELDS,
    apply_article_target_reviews,
    build_reference_file_match_rows,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Match JBRS reference-hunt rows to local-file manifest rows.")
    parser.add_argument("--article-targets", type=Path, default=JBRS_ARTICLE_REFERENCE_TARGETS_PATH)
    parser.add_argument("--target-review", type=Path, default=JBRS_ARTICLE_REFERENCE_TARGETS_REVIEW_PATH)
    parser.add_argument("--local-manifest", type=Path, default=JBRS_LOCAL_FILE_MANIFEST_PATH)
    parser.add_argument("--output", type=Path, default=JBRS_REFERENCE_FILE_MATCH_PATH)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    reference_rows = read_tsv(args.article_targets)
    review_rows = read_tsv(args.target_review)
    manifest_rows = read_tsv(args.local_manifest)
    reviewed_reference_rows = apply_article_target_reviews(reference_rows, review_rows)
    rows = build_reference_file_match_rows(reviewed_reference_rows, manifest_rows)
    write_tsv(args.output, rows, REFERENCE_FILE_MATCH_FIELDS)
    print(f"Wrote {len(rows)} JBRS reference-file match rows to {args.output}")


if __name__ == "__main__":
    main()
