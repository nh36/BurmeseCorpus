from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from corpus_common import REPO_ROOT

DEFAULT_INPUT_PATH = (
    REPO_ROOT
    / "data"
    / "working"
    / "corpus_enrichment"
    / "release_candidate_v0_4"
    / "inscriptions_enriched_with_lines_v0_4_candidate.jsonl"
)


def find_record(path: Path, record_id: str) -> dict | None:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get("record_id") == record_id:
                return row
    return None


def summarize_record(record: dict) -> str:
    translations = record.get("translations", [])
    lines = record.get("lines", [])
    translation_sources = sorted(
        {
            translation.get("source_key", "")
            for translation in translations
            if translation.get("source_key", "")
        }
    )
    translation_coverages = sorted(
        {
            translation.get("translation_coverage", "")
            for translation in translations
            if translation.get("translation_coverage", "")
        }
    )
    return "\n".join(
        [
            f"record_id: {record.get('record_id', '')}",
            f"title_original: {record.get('title_original', '')}",
            f"language_original: {record.get('language_original', '')}",
            f"translation_count: {len(translations)}",
            f"line_count: {len(lines)}",
            f"line_join_status: {record.get('line_join_status', '')}",
            f"translation_sources: {', '.join(translation_sources) if translation_sources else '(none)'}",
            f"translation_coverages: {', '.join(translation_coverages) if translation_coverages else '(none)'}",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("record_id")
    parser.add_argument(
        "--input-jsonl",
        type=Path,
        default=DEFAULT_INPUT_PATH,
        help="Path to inscriptions_enriched_with_lines_v0_4_candidate.jsonl",
    )
    parser.add_argument(
        "--format",
        choices=["json", "summary"],
        default="json",
    )
    args = parser.parse_args()

    record = find_record(args.input_jsonl, args.record_id)
    if record is None:
        print(
            f"Record not found: {args.record_id} in {args.input_jsonl}",
            file=sys.stderr,
        )
        return 1

    if args.format == "summary":
        print(summarize_record(record))
    else:
        print(json.dumps(record, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
