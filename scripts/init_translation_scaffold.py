from __future__ import annotations

import argparse
from pathlib import Path

from corpus_common import REPO_ROOT, read_jsonl, write_jsonl, write_tsv


def touch_tsv(path: Path, fieldnames: list[str]) -> None:
    write_tsv(path, [], fieldnames)


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
        default=REPO_ROOT / "data" / "working" / "translations",
    )
    args = parser.parse_args()

    records = read_jsonl(args.input_jsonl)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    write_tsv(
        args.output_dir / "translation_targets.tsv",
        (
            {
                "record_id": record["record_id"],
                "title_original": record.get("title_original"),
                "source_deposit": record.get("source_deposit"),
                "translation_status": "not_started",
                "notes": "",
            }
            for record in records
        ),
        ["record_id", "title_original", "source_deposit", "translation_status", "notes"],
    )
    touch_tsv(
        args.output_dir / "published_translation_candidates.tsv",
        [
            "record_id",
            "source_bibliography_id",
            "source_page",
            "candidate_translation_text",
            "review_status",
            "notes",
        ],
    )
    touch_tsv(args.output_dir / "glossary_terms.tsv", ["term_id", "source_term", "normalized_gloss", "notes"])
    touch_tsv(args.output_dir / "formulae.tsv", ["formula_id", "record_id", "formula_text", "notes"])
    touch_tsv(args.output_dir / "names_places.tsv", ["entity_id", "entity_type", "label_original", "place_id", "notes"])
    touch_tsv(args.output_dir / "units_measures.tsv", ["unit_id", "source_form", "normalized_form", "notes"])
    touch_tsv(args.output_dir / "translation_memory.tsv", ["memory_id", "source_excerpt", "translation_text", "notes"])
    write_jsonl(args.output_dir / "translations.jsonl", [])
    print(f"Initialized translation scaffold for {len(records)} records")


if __name__ == "__main__":
    main()
