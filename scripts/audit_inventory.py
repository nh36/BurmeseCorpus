from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from corpus_common import REPO_ROOT, normalize_match_text, read_jsonl, write_tsv


def base_inscription_number(value: str | None) -> str:
    if not value:
        return ""
    match = re.match(r"([0-9]+)", value)
    return match.group(1) if match else value


def audit_recently_found_vs_vol7(source_entries: list[dict], vol7_entries: list[dict]) -> tuple[list[dict], dict]:
    vol7_by_base_number: dict[str, list[dict]] = defaultdict(list)
    vol7_by_title: dict[str, list[dict]] = defaultdict(list)

    for record in vol7_entries:
        base_number = base_inscription_number(record.get("source_inscription_number"))
        vol7_by_base_number[base_number].append(record)
        vol7_by_title[normalize_match_text(record.get("title_original"))].append(record)

    crosswalk_rows: list[dict] = []
    matched_record_ids: set[str] = set()
    status_counter: Counter[str] = Counter()

    for source in source_entries:
        source_number = str(source["source_entry_number"])
        title_key = source["source_title_normalized"]
        number_candidates = vol7_by_base_number.get(source_number, [])
        exact_candidates = [record for record in number_candidates if normalize_match_text(record.get("title_original")) == title_key]
        title_only_candidates = [
            record
            for record in vol7_by_title.get(title_key, [])
            if record not in exact_candidates
        ]

        candidates = exact_candidates or number_candidates or title_only_candidates
        if not candidates:
            row = {
                "source_entry_number": source["source_entry_number"],
                "source_title": source["source_title"],
                "source_page": source["source_page"],
                "vol7_record_id": "",
                "vol7_inscription_number": "",
                "vol7_title": "",
                "match_status": "missing_from_vol7",
                "match_confidence": "low",
                "notes": "No title or number match in OBI volume 7",
            }
            crosswalk_rows.append(row)
            status_counter[row["match_status"]] += 1
            continue

        faces = {record.get("face") for record in candidates}
        if exact_candidates and len(candidates) > 1 and {"obverse", "reverse"} & faces:
            match_status = "matched_split_face"
            match_confidence = "high"
            notes = "Matched by source entry number and title; multiple face records in volume 7"
        elif exact_candidates and len(candidates) == 1:
            match_status = "matched"
            match_confidence = "high"
            notes = "Matched by source entry number and title"
        elif len(candidates) > 1:
            match_status = "possible_match"
            match_confidence = "medium"
            notes = "Multiple candidate matches found; review title and page span manually"
        else:
            match_status = "possible_match"
            match_confidence = "medium"
            notes = "Matched by source entry number or normalized title only"

        for candidate in candidates:
            matched_record_ids.add(candidate["record_id"])
            row = {
                "source_entry_number": source["source_entry_number"],
                "source_title": source["source_title"],
                "source_page": source["source_page"],
                "vol7_record_id": candidate["record_id"],
                "vol7_inscription_number": candidate["source_inscription_number"],
                "vol7_title": candidate["title_original"],
                "match_status": match_status,
                "match_confidence": match_confidence,
                "notes": notes,
            }
            crosswalk_rows.append(row)
            status_counter[match_status] += 1

    duplicate_rows = [
        {
            "source_entry_number": "",
            "source_title": "",
            "source_page": "",
            "vol7_record_id": candidate["record_id"],
            "vol7_inscription_number": candidate["source_inscription_number"],
            "vol7_title": candidate["title_original"],
            "match_status": "extra_in_vol7",
            "match_confidence": "low",
            "notes": "No source entry matched this volume 7 record",
        }
        for candidate in vol7_entries
        if candidate["record_id"] not in matched_record_ids
    ]
    for row in duplicate_rows:
        status_counter[row["match_status"]] += 1
    crosswalk_rows.extend(duplicate_rows)

    source_duplicate_titles = {
        title: count
        for title, count in Counter(source["source_title_normalized"] for source in source_entries if source["source_title_normalized"]).items()
        if count > 1
    }
    vol7_duplicate_titles = {
        title: count
        for title, count in Counter(normalize_match_text(record.get("title_original")) for record in vol7_entries if record.get("title_original")).items()
        if count > 1
    }

    summary = {
        "source_entry_count": len(source_entries),
        "vol7_record_count": len(vol7_entries),
        "status_counts": dict(status_counter),
        "source_duplicate_title_keys": source_duplicate_titles,
        "vol7_duplicate_title_keys": vol7_duplicate_titles,
        "recommendation": (
            "Volume 7 needs review before it is treated as authoritative."
            if status_counter["missing_from_vol7"] or status_counter["possible_match"] or status_counter["extra_in_vol7"]
            else "Volume 7 coverage looks aligned with the source inventory."
        ),
    }
    return crosswalk_rows, summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source-jsonl",
        type=Path,
        default=REPO_ROOT / "data" / "extracted" / "supplementary_1302525" / "source_entries.jsonl",
    )
    parser.add_argument(
        "--structured-jsonl",
        type=Path,
        default=REPO_ROOT / "data" / "extracted" / "structured_corpus_current" / "inscriptions.jsonl",
    )
    parser.add_argument(
        "--inventory-dir",
        type=Path,
        default=REPO_ROOT / "data" / "working" / "inventory",
    )
    args = parser.parse_args()

    source_entries = read_jsonl(args.source_jsonl)
    vol7_entries = [
        record
        for record in read_jsonl(args.structured_jsonl)
        if record.get("source_volume") == "7"
    ]

    crosswalk_rows, summary = audit_recently_found_vs_vol7(source_entries, vol7_entries)

    args.inventory_dir.mkdir(parents=True, exist_ok=True)
    write_tsv(
        args.inventory_dir / "vol7_structured_entries.tsv",
        (
            {
                "record_id": record["record_id"],
                "source_inscription_number": record["source_inscription_number"],
                "source_page": record["source_page"],
                "face": record["face"],
                "title_original": record["title_original"],
                "source_file": record["source_file"],
            }
            for record in vol7_entries
        ),
        [
            "record_id",
            "source_inscription_number",
            "source_page",
            "face",
            "title_original",
            "source_file",
        ],
    )
    write_tsv(
        args.inventory_dir / "recently_found_to_vol7_crosswalk.tsv",
        crosswalk_rows,
        [
            "source_entry_number",
            "source_title",
            "source_page",
            "vol7_record_id",
            "vol7_inscription_number",
            "vol7_title",
            "match_status",
            "match_confidence",
            "notes",
        ],
    )
    (args.inventory_dir / "recently_found_to_vol7_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
