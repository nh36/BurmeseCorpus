from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from corpus_common import REPO_ROOT, normalize_match_text, read_jsonl, write_tsv


def repo_relative_path(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def base_inscription_number(value: str | None) -> str:
    if not value:
        return ""
    match = re.match(r"([0-9]+)", value)
    return match.group(1) if match else value


def load_editorial_overrides(path: Path | None) -> dict[str, dict]:
    if path is None or not path.exists():
        return {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        return {row["source_entry_number"]: row for row in csv.DictReader(handle, delimiter="\t")}


def build_crosswalk_row(
    source: dict,
    vol7_record: dict | None,
    *,
    match_status: str,
    match_confidence: str,
    review_decision: str,
    evidence: str,
    notes: str,
    target_record_id: str | None = None,
) -> dict:
    return {
        "source_entry_key": source.get("source_entry_key", source["source_entry_number"]),
        "source_entry_number": source["source_entry_number"],
        "source_title": source["source_title"],
        "source_page": source["source_page"],
        "vol7_record_id": target_record_id or (vol7_record["record_id"] if vol7_record is not None else ""),
        "vol7_inscription_number": vol7_record["source_inscription_number"] if vol7_record is not None else "",
        "vol7_title": vol7_record["title_original"] if vol7_record is not None else "",
        "match_status": match_status,
        "match_confidence": match_confidence,
        "review_decision": review_decision,
        "evidence": evidence,
        "notes": notes,
    }


def build_override_row(source: dict, override: dict, vol7_record: dict | None) -> tuple[dict, str | None]:
    evidence = override["rationale"]
    notes = override["notes"]
    warning = None
    match_status = override["match_status"]
    match_confidence = override["match_confidence"]

    if vol7_record is None:
        match_status = "target_missing"
        match_confidence = "low"
        warning = (
            f"Editorial override for source entry {source['source_entry_number']} points to missing target "
            f"{override['target_record_id']}."
        )
        evidence = f"{evidence} Override target {override['target_record_id']} was not found in volume 7 structured records."
        notes = f"{notes} Override target record not found in volume 7 structured records."

    return (
        build_crosswalk_row(
            source,
            vol7_record,
            match_status=match_status,
            match_confidence=match_confidence,
            review_decision=override["editorial_status"],
            evidence=evidence,
            notes=notes,
            target_record_id=override["target_record_id"],
        ),
        warning,
    )


def audit_recently_found_vs_vol7(
    source_entries: list[dict],
    vol7_entries: list[dict],
    editorial_overrides: dict[str, dict] | None = None,
    override_file: Path | None = None,
) -> tuple[list[dict], dict]:
    vol7_by_base_number: dict[str, list[dict]] = defaultdict(list)
    vol7_by_title: dict[str, list[dict]] = defaultdict(list)
    vol7_by_record_id: dict[str, dict] = {}
    editorial_overrides = editorial_overrides or {}

    for record in vol7_entries:
        base_number = base_inscription_number(record.get("source_inscription_number"))
        vol7_by_base_number[base_number].append(record)
        vol7_by_title[normalize_match_text(record.get("title_original"))].append(record)
        vol7_by_record_id[record["record_id"]] = record

    crosswalk_rows: list[dict] = []
    matched_record_ids: set[str] = set()
    status_counter: Counter[str] = Counter()
    decision_counter: Counter[str] = Counter()
    applied_override_count = 0
    missing_target_count = 0
    warnings: list[str] = []
    seen_override_numbers: set[str] = set()

    for source in source_entries:
        source_number = str(source["source_entry_number"])
        override = editorial_overrides.get(source_number)
        if override is not None:
            seen_override_numbers.add(source_number)
            applied_override_count += 1
            target_record = vol7_by_record_id.get(override["target_record_id"])
            row, warning = build_override_row(source, override, target_record)
            crosswalk_rows.append(row)
            status_counter[row["match_status"]] += 1
            decision_counter[row["review_decision"]] += 1
            if target_record is not None:
                matched_record_ids.add(target_record["record_id"])
            else:
                missing_target_count += 1
            if warning is not None:
                warnings.append(warning)
            continue

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
            row = build_crosswalk_row(
                source,
                None,
                match_status="missing_from_vol7",
                match_confidence="low",
                review_decision="omission_in_volume7",
                evidence="No volume 7 record with matching number or normalized title",
                notes="No title or number match in OBI volume 7",
            )
            crosswalk_rows.append(row)
            status_counter[row["match_status"]] += 1
            decision_counter[row["review_decision"]] += 1
            continue

        faces = {record.get("face") for record in candidates}
        if exact_candidates and len(candidates) > 1 and {"obverse", "reverse"} & faces:
            match_status = "matched_split_face"
            match_confidence = "high"
            review_decision = "matched_split_face"
            evidence = "Matched by source entry number; multiple face records in volume 7"
            notes = "Matched by source entry number and title; multiple face records in volume 7"
        elif exact_candidates and len(candidates) == 1:
            match_status = "matched"
            match_confidence = "high"
            review_decision = "matched"
            evidence = "Matched by source entry number and normalized title"
            notes = "Matched by source entry number and title"
        elif number_candidates:
            match_status = "matched"
            match_confidence = "medium"
            review_decision = "title_mismatch"
            evidence = "Matched by source entry number, but source and volume 7 titles differ"
            notes = "Matched by source entry number; title differs between source and volume 7"
        elif len(candidates) > 1:
            match_status = "possible_match"
            match_confidence = "medium"
            review_decision = "needs_manual_review"
            evidence = "Multiple candidate matches found"
            notes = "Multiple candidate matches found; review title and page span manually"
        else:
            match_status = "possible_match"
            match_confidence = "medium"
            review_decision = "needs_manual_review"
            evidence = "Only a title-based candidate was found"
            notes = "Matched by source entry number or normalized title only"

        for candidate in candidates:
            matched_record_ids.add(candidate["record_id"])
            row = build_crosswalk_row(
                source,
                candidate,
                match_status=match_status,
                match_confidence=match_confidence,
                review_decision=review_decision,
                evidence=evidence,
                notes=notes,
            )
            crosswalk_rows.append(row)
            status_counter[match_status] += 1
            decision_counter[review_decision] += 1

    duplicate_rows = [
        {
            "source_entry_key": "",
            "source_entry_number": "",
            "source_title": "",
            "source_page": "",
            "vol7_record_id": candidate["record_id"],
            "vol7_inscription_number": candidate["source_inscription_number"],
            "vol7_title": candidate["title_original"],
            "match_status": "extra_in_vol7",
            "match_confidence": "low",
            "review_decision": "unexplained_extra_in_volume7",
            "evidence": "No source entry matched this volume 7 record",
            "notes": "No source entry matched this volume 7 record",
        }
        for candidate in vol7_entries
        if candidate["record_id"] not in matched_record_ids
    ]
    for row in duplicate_rows:
        status_counter[row["match_status"]] += 1
        decision_counter[row["review_decision"]] += 1
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
    unused_override_numbers = sorted(set(editorial_overrides) - seen_override_numbers)
    if unused_override_numbers:
        warnings.append(
            "Editorial overrides were not applied because the corresponding source entries were not present: "
            + ", ".join(unused_override_numbers)
        )

    summary = {
        "source_entry_count": len(source_entries),
        "vol7_record_count": len(vol7_entries),
        "status_counts": dict(status_counter),
        "review_decisions": dict(decision_counter),
        "editorial_overrides": {
            "override_file": repo_relative_path(override_file),
            "override_count": len(editorial_overrides),
            "applied_override_count": applied_override_count,
            "missing_target_count": missing_target_count,
            "status_counts_after_overrides": dict(status_counter),
            "warnings": warnings,
        },
        "source_duplicate_title_keys": source_duplicate_titles,
        "vol7_duplicate_title_keys": vol7_duplicate_titles,
        "recommendation": (
            "Volume 7 needs review before it is treated as authoritative."
            if (
                status_counter["missing_from_vol7"]
                or status_counter["possible_match"]
                or status_counter["extra_in_vol7"]
                or status_counter["editorial_override"]
                or status_counter["target_missing"]
            )
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
    parser.add_argument(
        "--editorial-overrides",
        type=Path,
        default=REPO_ROOT / "data" / "working" / "inventory" / "recently_found_editorial_overrides.tsv",
    )
    args = parser.parse_args()

    source_entries = read_jsonl(args.source_jsonl)
    vol7_entries = [
        record
        for record in read_jsonl(args.structured_jsonl)
        if record.get("source_volume") == "7"
    ]
    editorial_overrides = load_editorial_overrides(args.editorial_overrides)

    crosswalk_rows, summary = audit_recently_found_vs_vol7(
        source_entries,
        vol7_entries,
        editorial_overrides=editorial_overrides,
        override_file=args.editorial_overrides,
    )

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
            "source_entry_key",
            "source_entry_number",
            "source_title",
            "source_page",
            "vol7_record_id",
            "vol7_inscription_number",
            "vol7_title",
            "match_status",
            "match_confidence",
            "review_decision",
            "evidence",
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
