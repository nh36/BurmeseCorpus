from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

from corpus_common import REPO_ROOT, TODAY, read_jsonl, write_jsonl


def repo_relative_path(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def load_release_policy(path: Path | None) -> dict[str, dict]:
    if path is None or not path.exists():
        return {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        return {row["source_entry_key"]: row for row in csv.DictReader(handle, delimiter="\t")}


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


def relation_id_for(source_record: dict, policy_row: dict) -> str:
    key = source_record.get("source_entry_key") or source_record.get("source_inscription_number") or source_record["record_id"]
    relation_type = policy_row["editorial_status"]
    slug = re.sub(r"[^0-9a-z]+", "-", f"{key}-{relation_type}".casefold()).strip("-")
    return f"edrel-rfi-{slug or 'relation'}"


def annotate_target_record(target_record: dict, relation: dict) -> None:
    relation_ids = target_record.setdefault("editorial_relation_ids", [])
    if relation["relation_id"] not in relation_ids:
        relation_ids.append(relation["relation_id"])
        relation_ids.sort()
    if relation["relation_type"] == "title_variant_same_record" and relation.get("source_title_original"):
        variants = target_record.setdefault("editorial_title_variants", [])
        source_title = relation["source_title_original"]
        if source_title != target_record.get("title_original") and source_title not in variants:
            variants.append(source_title)
            variants.sort()


def build_editorial_relation(source_record: dict, policy_row: dict, target_record: dict) -> dict:
    return {
        "relation_id": relation_id_for(source_record, policy_row),
        "relation_type": policy_row["editorial_status"],
        "source_entry_number": policy_row["source_entry_number"],
        "source_entry_key": policy_row["source_entry_key"],
        "source_record_id": source_record["record_id"],
        "source_title_original": source_record.get("title_original"),
        "source_page": source_record.get("source_page"),
        "source_page_span": source_record.get("source_page_span"),
        "target_record_id": target_record["record_id"],
        "target_title_original": target_record.get("title_original"),
        "release_action": policy_row["release_action"],
        "line_action": policy_row["line_action"],
        "confidence": policy_row["confidence"],
        "rationale": policy_row["rationale"],
        "evidence_source": policy_row["evidence_source"],
        "notes": policy_row["notes"],
    }


def merge_release(
    structured_inscriptions: list[dict],
    structured_lines: list[dict],
    source_inscriptions: list[dict],
    source_lines: list[dict],
    *,
    release_policy: dict[str, dict] | None = None,
    release_policy_file: Path | None = None,
) -> tuple[list[dict], list[dict], list[dict], dict]:
    structured_by_id = {record["record_id"]: dict(record) for record in structured_inscriptions}
    source_by_canonical = {record["canonical_record_id"]: record for record in source_inscriptions}
    source_lines_by_record: dict[str, list[dict]] = {}
    for line in source_lines:
        source_lines_by_record.setdefault(line["record_id"], []).append(line)

    release_policy = release_policy or {}
    source_by_entry_key = {record.get("source_entry_key"): record for record in source_inscriptions if record.get("source_entry_key")}
    warnings: list[str] = []
    suppressed_source_record_ids: set[str] = set()
    annotated_target_ids: set[str] = set()
    relation_ids: set[str] = set()
    editorial_relations: list[dict] = []

    merged_records_by_id: dict[str, dict] = {}
    merged_lines: list[dict] = []
    added_from_source_only = 0
    matched_with_source = 0
    title_variant_matches = 0
    suppressed_source_only_by_policy = 0

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
        merged_records_by_id[record["record_id"]] = merged_record

    merged_lines.extend(structured_lines)

    for source_record in source_inscriptions:
        policy_row = release_policy.get(source_record.get("source_entry_key"))
        if not policy_row:
            continue
        target_record = merged_records_by_id.get(policy_row["target_record_id"])
        if target_record is None:
            warnings.append(
                "Release policy target missing from structured corpus for source entry "
                f"{policy_row['source_entry_key']}: {policy_row['target_record_id']}"
            )
            continue
        relation = build_editorial_relation(source_record, policy_row, target_record)
        if relation["relation_id"] in relation_ids:
            warnings.append(f"Duplicate editorial relation id {relation['relation_id']} for source entry {policy_row['source_entry_key']}")
            continue
        relation_ids.add(relation["relation_id"])
        editorial_relations.append(relation)
        annotate_target_record(target_record, relation)
        annotated_target_ids.add(target_record["record_id"])
        if policy_row["release_action"] == "annotate_target_only":
            suppressed_source_record_ids.add(source_record["record_id"])
            suppressed_source_only_by_policy += 1

    unused_policy_entries = sorted(set(release_policy) - set(source_by_entry_key))
    if unused_policy_entries:
        warnings.append(
            "Release-policy rows were not applied because the corresponding source entries were not present: "
            + ", ".join(unused_policy_entries)
        )

    for source_record in source_inscriptions:
        canonical_id = source_record["canonical_record_id"]
        if canonical_id in structured_by_id:
            continue
        if source_record["record_id"] in suppressed_source_record_ids:
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
        merged_records_by_id[canonical_id] = merged_record
        merged_lines.extend(
            rewrite_source_only_lines(
                source_lines_by_record.get(source_record["record_id"], []),
                source_record["record_id"],
                canonical_id,
            )
        )
    merged_inscriptions = sorted(merged_records_by_id.values(), key=lambda record: record["record_id"])
    editorial_relations.sort(key=lambda relation: relation["relation_id"])
    editorial_relations.sort(key=lambda relation: relation["relation_id"])
    merged_lines.sort(key=lambda line: (line["record_id"], line["line_number_arabic"], line["line_id"]))

    summary = {
        "structured_record_count": len(structured_inscriptions),
        "structured_line_count": len(structured_lines),
        "source_record_count": len(source_inscriptions),
        "source_line_count": len(source_lines),
        "matched_with_source": matched_with_source,
        "title_variant_matches": title_variant_matches,
        "added_from_source_only": added_from_source_only,
        "suppressed_source_only_by_policy": suppressed_source_only_by_policy,
        "editorial_relation_count": len(editorial_relations),
        "target_records_annotated": len(annotated_target_ids),
        "merged_record_count": len(merged_inscriptions),
        "merged_line_count": len(merged_lines),
        "release_policy_file": repo_relative_path(release_policy_file),
        "warnings": warnings,
    }
    return merged_inscriptions, merged_lines, editorial_relations, summary


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
        default=REPO_ROOT / "data" / "release" / "unified_release_v0_2",
    )
    parser.add_argument(
        "--release-policy",
        type=Path,
        default=REPO_ROOT / "data" / "working" / "inventory" / "recently_found_release_policy.tsv",
    )
    args = parser.parse_args()

    structured_inscriptions = read_jsonl(args.structured_dir / "inscriptions.jsonl")
    structured_lines = read_jsonl(args.structured_dir / "lines.jsonl")
    source_inscriptions = read_jsonl(args.source_dir / "inscriptions.jsonl")
    source_lines = read_jsonl(args.source_dir / "lines.jsonl")
    release_policy = load_release_policy(args.release_policy)

    merged_inscriptions, merged_lines, editorial_relations, summary = merge_release(
        structured_inscriptions,
        structured_lines,
        source_inscriptions,
        source_lines,
        release_policy=release_policy,
        release_policy_file=args.release_policy,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.output_dir / "inscriptions.jsonl", merged_inscriptions)
    write_jsonl(args.output_dir / "lines.jsonl", merged_lines)
    write_jsonl(args.output_dir / "editorial_relations.jsonl", editorial_relations)
    (args.output_dir / "merge_report.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
