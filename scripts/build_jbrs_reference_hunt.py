from __future__ import annotations

import argparse

from corpus_common import write_tsv
from jbrs_workflow_common import (
    ARTICLE_REFERENCE_TARGET_FIELDS,
    JBRS_ARTICLE_REFERENCE_TARGETS_PATH,
    JBRS_REFERENCE_HUNT_PATH,
    JBRS_REFERENCE_HUNT_RAW_PATH,
    RAW_REFERENCE_HUNT_FIELDS,
    build_reference_hunt_rows,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the JBRS reference hunt from existing repository references.")
    parser.add_argument("--raw-output", default=JBRS_REFERENCE_HUNT_RAW_PATH)
    parser.add_argument("--legacy-output", default=JBRS_REFERENCE_HUNT_PATH)
    parser.add_argument("--target-output", default=JBRS_ARTICLE_REFERENCE_TARGETS_PATH)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    raw_rows, target_rows = build_reference_hunt_rows()
    write_tsv(args.raw_output, raw_rows, RAW_REFERENCE_HUNT_FIELDS)
    write_tsv(args.legacy_output, raw_rows, RAW_REFERENCE_HUNT_FIELDS)
    write_tsv(args.target_output, target_rows, ARTICLE_REFERENCE_TARGET_FIELDS)
    print(f"Wrote {len(raw_rows)} raw JBRS reference-hunt rows to {args.raw_output}")
    print(f"Wrote {len(target_rows)} clean JBRS article targets to {args.target_output}")


if __name__ == "__main__":
    main()
