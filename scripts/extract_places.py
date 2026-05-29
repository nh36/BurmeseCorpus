from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
import re

from corpus_common import REPO_ROOT, normalize_whitespace, read_jsonl, write_jsonl, write_tsv


def place_id_for(label: str) -> str:
    slug = re.sub(r"[^0-9a-z\u1000-\u109f]+", "-", label.casefold()).strip("-")
    return f"place-{slug or 'unknown'}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-jsonl",
        type=Path,
        default=REPO_ROOT / "data" / "release" / "unified_release_v0_1" / "inscriptions.jsonl",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "data" / "working" / "places",
    )
    args = parser.parse_args()

    records = read_jsonl(args.input_jsonl)
    occurrences: list[dict] = []
    candidates: dict[str, dict] = {}
    source_fields = ("place_of_origin_original", "current_location_original")

    for record in records:
        for field in source_fields:
            value = record.get(field)
            if not value:
                continue
            label = normalize_whitespace(value)
            place_id = place_id_for(label)
            occurrences.append(
                {
                    "record_id": record["record_id"],
                    "source_field": field,
                    "label_original": label,
                    "place_id": place_id,
                }
            )
            candidates.setdefault(
                place_id,
                {
                    "place_id": place_id,
                    "label_original": label,
                    "label_normalized": label,
                    "latitude": None,
                    "longitude": None,
                    "source_note": None,
                },
            )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_tsv(
        args.output_dir / "place_occurrences.tsv",
        occurrences,
        ["record_id", "source_field", "label_original", "place_id"],
    )
    write_jsonl(args.output_dir / "place_candidates.jsonl", sorted(candidates.values(), key=lambda item: item["place_id"]))
    (args.output_dir / "place_summary.json").write_text(
        json.dumps(
            {
                "occurrence_count": len(occurrences),
                "candidate_count": len(candidates),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Extracted {len(candidates)} place candidates")


if __name__ == "__main__":
    main()
