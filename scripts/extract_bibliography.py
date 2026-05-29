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
        default=REPO_ROOT / "data" / "release" / "corpus_release_v0_3" / "inscriptions.jsonl",
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
    coverage_rows: dict[tuple[str, str], dict] = {}

    for record in records:
        source_deposit = record.get("source_deposit")
        source_layer = record.get("source_layer") or "unknown"
        coverage_key = (source_deposit, source_layer)
        coverage_rows.setdefault(
            coverage_key,
            {
                "source_deposit": source_deposit,
                "source_layer": source_layer,
                "inscription_count": 0,
                "records_with_references": 0,
                "records_without_references": 0,
                "distinct_raw_reference_strings": set(),
                "notes": "",
            },
        )
        coverage_rows[coverage_key]["inscription_count"] += 1
        reference_field = record.get("references_original")
        if not reference_field:
            coverage_rows[coverage_key]["records_without_references"] += 1
            continue
        coverage_rows[coverage_key]["records_with_references"] += 1
        coverage_rows[coverage_key]["distinct_raw_reference_strings"].add(reference_field)
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
        args.output_dir / "reference_coverage_by_source.tsv",
        (
            {
                "source_deposit": row["source_deposit"],
                "source_layer": row["source_layer"],
                "inscription_count": row["inscription_count"],
                "records_with_references": row["records_with_references"],
                "records_without_references": row["records_without_references"],
                "distinct_raw_reference_strings": len(row["distinct_raw_reference_strings"]),
                "notes": (
                    "No raw references present in current release input."
                    if row["records_with_references"] == 0
                    else ""
                ),
            }
            for row in sorted(coverage_rows.values(), key=lambda item: (item["source_deposit"], item["source_layer"]))
        ),
        [
            "source_deposit",
            "source_layer",
            "inscription_count",
            "records_with_references",
            "records_without_references",
            "distinct_raw_reference_strings",
            "notes",
        ],
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
                "coverage_group_count": len(coverage_rows),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Extracted {len(candidates)} bibliography candidates")


if __name__ == "__main__":
    main()
