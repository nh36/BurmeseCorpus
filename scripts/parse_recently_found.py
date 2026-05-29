from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from corpus_common import REPO_ROOT, first_int, normalize_match_text, normalize_whitespace, write_jsonl, write_tsv


ENTRY_PATTERN = re.compile(r"^\s*([၀-၉]+)။\s*([^\t]+?)\s*$")
FACE_MARKER_PATTERN = re.compile(r"^\((မျက်နှာဘက်|ကျောဘက်)\)\s*$")
PAGE_PATTERN = re.compile(r"^\s*([၀-၉]+)\s*$")


def strip_trailing_footnote_digits(title: str) -> str:
    return normalize_whitespace(re.sub(r"[0-9]+$", "", title))


def parse_recently_found_entries(text: str) -> list[dict]:
    lines = text.splitlines()
    entries: list[dict] = []
    current_page: int | None = None
    current_entry: dict | None = None

    def flush() -> None:
        nonlocal current_entry
        if current_entry is None:
            return
        content_lines = [line for line in current_entry.pop("content_lines") if line.strip()]
        face_markers = [normalize_whitespace(line.strip("()")) for line in content_lines if FACE_MARKER_PATTERN.match(line.strip())]
        current_entry["face_markers"] = face_markers
        current_entry["page_span"] = sorted(set(current_entry["page_span"]))
        current_entry["excerpt"] = normalize_whitespace(" ".join(content_lines[:4])) or None
        entries.append(current_entry)
        current_entry = None

    for raw_line in lines:
        stripped = raw_line.strip()
        page_match = PAGE_PATTERN.match(stripped)
        if page_match:
            current_page = first_int(page_match.group(1))
            if current_entry is not None and current_page is not None:
                current_entry["page_span"].append(current_page)
            continue

        entry_match = ENTRY_PATTERN.match(stripped)
        if entry_match:
            flush()
            entry_number_original = entry_match.group(1)
            cleaned_title = strip_trailing_footnote_digits(entry_match.group(2))
            current_entry = {
                "source_entry_number_original": entry_number_original,
                "source_entry_number": first_int(entry_number_original),
                "source_title": cleaned_title,
                "source_title_normalized": normalize_match_text(cleaned_title),
                "source_page": current_page,
                "page_span": [current_page] if current_page is not None else [],
                "content_lines": [],
            }
            continue

        if current_entry is not None:
            current_entry["content_lines"].append(raw_line)

    flush()
    return entries


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
                "source_entry_number": entry["source_entry_number"],
                "source_title": entry["source_title"],
                "source_page": entry["source_page"],
                "page_span": ",".join("" if page is None else str(page) for page in entry["page_span"]),
                "face_markers": ",".join(entry["face_markers"]),
                "source_title_normalized": entry["source_title_normalized"],
                "excerpt": entry["excerpt"],
            }
            for entry in entries
        ),
        [
            "source_entry_number",
            "source_title",
            "source_page",
            "page_span",
            "face_markers",
            "source_title_normalized",
            "excerpt",
        ],
    )

    summary = {
        "entry_count": len(entries),
        "start_pages": sorted({entry["source_page"] for entry in entries if entry["source_page"] is not None})[:10],
    }
    (args.output_dir / "source_entries_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Parsed {len(entries)} Recently Found source entries")


if __name__ == "__main__":
    main()
