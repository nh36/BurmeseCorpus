from __future__ import annotations

import argparse
import json
from pathlib import Path

from corpus_common import REPO_ROOT, write_jsonl, write_tsv
from recently_found_common import build_source_entries


def parse_recently_found_entries(text: str) -> list[dict]:
    entries = build_source_entries(text)
    return [
        {
            key: value
            for key, value in entry.items()
            if key not in {"page_blocks", "content_lines"}
        }
        | {
            "excerpt": entry["excerpt"],
            "face_markers": entry["face_markers"],
            "page_span": entry["page_span"],
        }
        for entry in entries
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-file",
        type=Path,
        default=REPO_ROOT / "1302525" / "Recently Found Burmese Inscriptiosn text.txt",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "data" / "extracted" / "supplementary_1302525",
    )
    parser.add_argument(
        "--inventory-dir",
        type=Path,
        default=REPO_ROOT / "data" / "working" / "inventory",
    )
    args = parser.parse_args()

    text = args.input_file.read_text(encoding="utf-8")
    entries = parse_recently_found_entries(text)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.inventory_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.output_dir / "source_entries.jsonl", entries)
    write_tsv(
        args.inventory_dir / "recently_found_source_entries.tsv",
        (
            {
                "source_entry_key": entry["source_entry_key"],
                "source_entry_number": entry["source_entry_number"],
                "source_title": entry["source_title"],
                "source_page": entry["source_page"],
                "page_span": entry["page_span_label"],
                "face_markers": ",".join(entry["face_markers"]),
                "source_title_normalized": entry["source_title_normalized"],
                "inferred_heading": entry["inferred_heading"],
                "excerpt": entry["excerpt"],
            }
            for entry in entries
        ),
        [
            "source_entry_key",
            "source_entry_number",
            "source_title",
            "source_page",
            "page_span",
            "face_markers",
            "source_title_normalized",
            "inferred_heading",
            "excerpt",
        ],
    )

    summary = {
        "entry_count": len(entries),
        "inferred_heading_count": sum(1 for entry in entries if entry["inferred_heading"]),
        "source_keys": [entry["source_entry_key"] for entry in entries[:10]],
    }
    (args.output_dir / "source_entries_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Parsed {len(entries)} Recently Found source entries")


if __name__ == "__main__":
    main()
