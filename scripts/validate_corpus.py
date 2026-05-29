from __future__ import annotations

import argparse
import json
from pathlib import Path

from corpus_common import REPO_ROOT, read_jsonl


def validate_inscriptions(records: list[dict]) -> list[str]:
    errors: list[str] = []
    seen_ids: set[str] = set()
    required_fields = {
        "record_id": str,
        "source_deposit": str,
        "title_original": (str, type(None)),
        "source_file": str,
        "provenance": dict,
    }

    for index, record in enumerate(records, start=1):
        for field, expected_type in required_fields.items():
            if field not in record:
                errors.append(f"inscriptions[{index}] missing field {field}")
                continue
            if not isinstance(record[field], expected_type):
                errors.append(f"inscriptions[{index}] field {field} has wrong type")
        record_id = record.get("record_id")
        if record_id in seen_ids:
            errors.append(f"duplicate inscription record_id {record_id}")
        else:
            seen_ids.add(record_id)
    return errors


def validate_lines(records: list[dict], inscription_ids: set[str]) -> list[str]:
    errors: list[str] = []
    seen_ids: set[str] = set()
    required_fields = {
        "record_id": str,
        "line_id": str,
        "line_number_arabic": int,
        "text_original": str,
    }

    for index, record in enumerate(records, start=1):
        for field, expected_type in required_fields.items():
            if field not in record:
                errors.append(f"lines[{index}] missing field {field}")
                continue
            if not isinstance(record[field], expected_type):
                errors.append(f"lines[{index}] field {field} has wrong type")
        if record.get("record_id") not in inscription_ids:
            errors.append(f"line {record.get('line_id')} references unknown record_id {record.get('record_id')}")
        if record.get("line_id") in seen_ids:
            errors.append(f"duplicate line_id {record.get('line_id')}")
        else:
            seen_ids.add(record.get("line_id"))
    return errors


def validate_dataset(dataset_dir: Path) -> dict:
    result = {"dataset": str(dataset_dir), "errors": [], "record_counts": {}}
    inscriptions_path = dataset_dir / "inscriptions.jsonl"
    lines_path = dataset_dir / "lines.jsonl"
    if not inscriptions_path.exists() or not lines_path.exists():
        result["errors"].append("missing inscriptions.jsonl or lines.jsonl")
        return result

    inscriptions = read_jsonl(inscriptions_path)
    lines = read_jsonl(lines_path)
    inscription_ids = {record["record_id"] for record in inscriptions if "record_id" in record}

    result["errors"].extend(validate_inscriptions(inscriptions))
    result["errors"].extend(validate_lines(lines, inscription_ids))
    result["record_counts"] = {"inscriptions": len(inscriptions), "lines": len(lines)}
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset",
        action="append",
        type=Path,
        help="Dataset directory with inscriptions.jsonl and lines.jsonl",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=REPO_ROOT / "data" / "working" / "qa" / "validation_report.json",
    )
    args = parser.parse_args()

    datasets = args.dataset or [
        REPO_ROOT / "data" / "extracted" / "structured_corpus_current",
        REPO_ROOT / "data" / "extracted" / "supplementary_1302525",
        REPO_ROOT / "data" / "extracted" / "supplementary_1203709",
        REPO_ROOT / "data" / "release" / "sagaing_v0_1",
        REPO_ROOT / "data" / "release" / "unified_release_v0_1",
    ]

    report = {"datasets": [validate_dataset(dataset) for dataset in datasets]}
    report["ok"] = all(not dataset["errors"] for dataset in report["datasets"])

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))

    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
