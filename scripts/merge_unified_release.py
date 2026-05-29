from __future__ import annotations

import argparse
import json
from pathlib import Path

from corpus_common import REPO_ROOT, TODAY, read_jsonl, write_jsonl


def rewrite_source_only_lines(source_lines: list[dict], source_record_id: str, canonical_record_id: str) -> list[dict]:
    rewritten: list[dict] = []
    for line in source_lines:
        if line["record_id"] != source_record_id:
            continue
        rewritten_line = dict(line)
        rewritten_line["record_id"] = canonical_record_id
        rewritten_line["line_id"] = line["line_id"].replace(source_record_id, canonical_record_id, 1)
        rewritten.append(rewritten_line)
    return rewritten


def merge_release(structured_inscriptions: list[dict], structured_lines: list[dict], source_inscriptions: list[dict], source_lines: list[dict]) -> tuple[list[dict], list[dict], dict]:
    structured_by_id = {record["record_id"]: dict(record) for record in structured_inscriptions}
    source_by_canonical = {record["canonical_record_id"]: record for record in source_inscriptions}
    source_lines_by_record: dict[str, list[dict]] = {}
    for line in source_lines:
        source_lines_by_record.setdefault(line["record_id"], []).append(line)

    merged_inscriptions: list[dict] = []
    merged_lines: list[dict] = []
    added_from_source_only = 0
    matched_with_source = 0
    title_variant_matches = 0

    for record in structured_inscriptions:
        merged_record = dict(record)
        if record["record_id"] in source_by_canonical:
            source_record = source_by_canonical[record["record_id"]]
            matched_with_source += 1
            merged_record["merge_status"] = "matched_with_source"
            merged_record["related_source_record_id"] = source_record["record_id"]
            merged_record["source_page_span"] = source_record["source_page_span"]
            merged_record["source_title_original"] = source_record["title_original"]
            merged_record["source_title_normalized"] = source_record["source_title_normalized"]
            if source_record["title_original"] != record.get("title_original"):
                merged_record["merge_status"] = "title_variant_match"
                merged_record["merge_notes"] = "Source title differs from structured volume 7 title"
                title_variant_matches += 1
            merged_record["provenance"] = {
                "created_from": "structured corpus txt + Recently Found source txt",
                "created_by_script": "merge_unified_release.py",
                "created_date": TODAY,
                "structured_record_id": record["record_id"],
                "source_record_id": source_record["record_id"],
            }
        else:
            merged_record["merge_status"] = "structured_only"
            merged_record["provenance"] = {
                "created_from": "structured corpus txt",
                "created_by_script": "merge_unified_release.py",
                "created_date": TODAY,
                "structured_record_id": record["record_id"],
            }
        merged_inscriptions.append(merged_record)

    merged_lines.extend(structured_lines)

    for source_record in source_inscriptions:
        canonical_id = source_record["canonical_record_id"]
        if canonical_id in structured_by_id:
            continue
        added_from_source_only += 1
        merged_record = dict(source_record)
        merged_record["record_id"] = canonical_id
        merged_record["merge_status"] = "added_from_source_only"
        merged_record["provenance"] = {
            "created_from": "Recently Found source txt",
            "created_by_script": "merge_unified_release.py",
            "created_date": TODAY,
            "source_record_id": source_record["record_id"],
        }
        merged_inscriptions.append(merged_record)
        merged_lines.extend(
            rewrite_source_only_lines(
                source_lines_by_record.get(source_record["record_id"], []),
                source_record["record_id"],
                canonical_id,
            )
        )

    merged_inscriptions.sort(key=lambda record: record["record_id"])
    merged_lines.sort(key=lambda line: (line["record_id"], line["line_number_arabic"], line["line_id"]))

    summary = {
        "structured_record_count": len(structured_inscriptions),
        "structured_line_count": len(structured_lines),
        "source_record_count": len(source_inscriptions),
        "source_line_count": len(source_lines),
        "matched_with_source": matched_with_source,
        "title_variant_matches": title_variant_matches,
        "added_from_source_only": added_from_source_only,
        "merged_record_count": len(merged_inscriptions),
        "merged_line_count": len(merged_lines),
    }
    return merged_inscriptions, merged_lines, summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--structured-dir",
        type=Path,
        default=REPO_ROOT / "data" / "extracted" / "structured_corpus_current",
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=REPO_ROOT / "data" / "extracted" / "supplementary_1302525",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "data" / "release" / "unified_release_v0_1",
    )
    args = parser.parse_args()

    structured_inscriptions = read_jsonl(args.structured_dir / "inscriptions.jsonl")
    structured_lines = read_jsonl(args.structured_dir / "lines.jsonl")
    source_inscriptions = read_jsonl(args.source_dir / "inscriptions.jsonl")
    source_lines = read_jsonl(args.source_dir / "lines.jsonl")

    merged_inscriptions, merged_lines, summary = merge_release(
        structured_inscriptions,
        structured_lines,
        source_inscriptions,
        source_lines,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.output_dir / "inscriptions.jsonl", merged_inscriptions)
    write_jsonl(args.output_dir / "lines.jsonl", merged_lines)
    (args.output_dir / "merge_report.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
