from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
import re

from corpus_common import REPO_ROOT, read_jsonl, write_jsonl, write_tsv


SPLIT_PATTERN = re.compile(r"\s*;\s*")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-jsonl",
        type=Path,
        default=REPO_ROOT / "data" / "release" / "unified_release_v0_2" / "inscriptions.jsonl",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "data" / "working" / "bibliography",
    )
    args = parser.parse_args()

    records = read_jsonl(args.input_jsonl)
    occurrence_rows: list[dict] = []
    candidates: dict[str, dict] = {}
    raw_reference_counts: dict[str, int] = defaultdict(int)

    for record in records:
        reference_field = record.get("references_original")
        if not reference_field:
            continue
        raw_reference_counts[reference_field] += 1
        for fragment in [part.strip() for part in SPLIT_PATTERN.split(reference_field) if part.strip()]:
            occurrence_rows.append(
                {
                    "record_id": record["record_id"],
                    "source_deposit": record["source_deposit"],
                    "raw_reference_string": fragment,
                }
            )
            bibliography_id = re.sub(r"[^a-z0-9]+", "-", fragment.casefold()).strip("-")[:60] or "reference"
            bibliography_id = f"bib-{bibliography_id}"
            candidates.setdefault(
                bibliography_id,
                {
                    "bibliography_id": bibliography_id,
                    "short_label": fragment[:80],
                    "raw_reference_strings": [],
                    "author": None,
                    "year": None,
                    "title": None,
                    "publication": None,
                    "local_library_candidates": [],
                    "local_file_path": None,
                    "ocr_status": "not_started",
                    "translation_relevance": "unknown",
                    "notes": None,
                },
            )
            if fragment not in candidates[bibliography_id]["raw_reference_strings"]:
                candidates[bibliography_id]["raw_reference_strings"].append(fragment)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_tsv(
        args.output_dir / "raw_references.tsv",
        (
            {
                "raw_reference_string": raw_reference,
                "occurrence_count": count,
            }
            for raw_reference, count in sorted(raw_reference_counts.items(), key=lambda item: (-item[1], item[0]))
        ),
        ["raw_reference_string", "occurrence_count"],
    )
    write_tsv(
        args.output_dir / "reference_occurrences.tsv",
        occurrence_rows,
        ["record_id", "source_deposit", "raw_reference_string"],
    )
    write_tsv(
        args.output_dir / "bibliography_candidates.tsv",
        (
            {
                "bibliography_id": record["bibliography_id"],
                "short_label": record["short_label"],
                "raw_reference_strings": " | ".join(record["raw_reference_strings"]),
                "ocr_status": record["ocr_status"],
                "translation_relevance": record["translation_relevance"],
            }
            for record in sorted(candidates.values(), key=lambda item: item["bibliography_id"])
        ),
        [
            "bibliography_id",
            "short_label",
            "raw_reference_strings",
            "ocr_status",
            "translation_relevance",
        ],
    )
    write_jsonl(args.output_dir / "bibliography.jsonl", sorted(candidates.values(), key=lambda item: item["bibliography_id"]))
    (args.output_dir / "bibliography_summary.json").write_text(
        json.dumps(
            {
                "raw_reference_count": len(raw_reference_counts),
                "occurrence_count": len(occurrence_rows),
                "candidate_count": len(candidates),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Extracted {len(candidates)} bibliography candidates")


if __name__ == "__main__":
    main()
