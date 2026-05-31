from __future__ import annotations

import argparse

from jbrs_workflow_common import JBRS_REFERENCE_HUNT_PATH, REFERENCE_HUNT_FIELDS, build_reference_hunt_rows
from corpus_common import write_tsv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the JBRS reference hunt from existing repository references.")
    parser.add_argument("--output", default=JBRS_REFERENCE_HUNT_PATH)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = build_reference_hunt_rows()
    write_tsv(args.output, rows, REFERENCE_HUNT_FIELDS)
    print(f"Wrote {len(rows)} JBRS reference-hunt rows to {args.output}")


if __name__ == "__main__":
    main()
