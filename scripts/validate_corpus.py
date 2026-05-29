from __future__ import annotations

import argparse
import json
import re
import sqlite3
from pathlib import Path

from corpus_common import REPO_ROOT, read_jsonl


CORPUS_RELEASE_REQUIRED_FILES = [
    "README.md",
    "inscriptions.jsonl",
    "lines.jsonl",
    "editorial_relations.jsonl",
    "sources.jsonl",
    "release_manifest.json",
    "release_notes.md",
    "corpus_release.sqlite",
    "validation_report.json",
]

ABSOLUTE_PATH_PATTERN = re.compile(r"(^/|^[A-Za-z]:\\\\|/Users/|/home/)")
REQUIRED_RELEASE_DOCS = [
    "docs/release_workflow.md",
    "docs/field_dictionary.md",
    "docs/phase1_closeout.md",
]


def repo_relative_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


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


def scan_for_absolute_paths(value: object, *, context: str) -> list[str]:
    errors: list[str] = []
    if isinstance(value, dict):
        for key, nested_value in value.items():
            errors.extend(scan_for_absolute_paths(nested_value, context=f"{context}.{key}"))
    elif isinstance(value, list):
        for index, nested_value in enumerate(value, start=1):
            errors.extend(scan_for_absolute_paths(nested_value, context=f"{context}[{index}]"))
    elif isinstance(value, str) and ABSOLUTE_PATH_PATTERN.search(value):
        errors.append(f"{context} contains an absolute local path: {value}")
    return errors


def validate_editorial_relations(records: list[dict], inscription_ids: set[str]) -> list[str]:
    errors: list[str] = []
    seen_ids: set[str] = set()
    required_fields = {
        "relation_id": str,
        "relation_type": str,
        "source_entry_number": str,
        "target_record_id": str,
        "confidence": str,
        "release_action": str,
        "rationale": str,
    }

    for index, record in enumerate(records, start=1):
        for field, expected_type in required_fields.items():
            if field not in record:
                errors.append(f"editorial_relations[{index}] missing field {field}")
                continue
            if not isinstance(record[field], expected_type):
                errors.append(f"editorial_relations[{index}] field {field} has wrong type")
        relation_id = record.get("relation_id")
        if relation_id in seen_ids:
            errors.append(f"duplicate editorial relation_id {relation_id}")
        else:
            seen_ids.add(relation_id)
        if record.get("target_record_id") not in inscription_ids:
            errors.append(
                "editorial relation "
                f"{record.get('relation_id')} references unknown target_record_id {record.get('target_record_id')}"
            )
    return errors


def validate_sources(records: list[dict]) -> list[str]:
    errors: list[str] = []
    seen_ids: set[str] = set()
    required_fields = {
        "source_id": str,
        "source_type": str,
        "title_original": str,
        "title_english": str,
        "zenodo_doi": str,
        "local_source_path": str,
        "release_role": str,
        "inscription_record_count": int,
        "line_record_count": int,
        "editorial_relation_count": int,
        "record_count": int,
        "line_count": int,
        "parser_script": str,
        "source_status": str,
        "notes": str,
    }
    for index, record in enumerate(records, start=1):
        for field, expected_type in required_fields.items():
            if field not in record:
                errors.append(f"sources[{index}] missing field {field}")
                continue
            if not isinstance(record[field], expected_type):
                errors.append(f"sources[{index}] field {field} has wrong type")
        source_id = record.get("source_id")
        if source_id in seen_ids:
            errors.append(f"duplicate source_id {source_id}")
        else:
            seen_ids.add(source_id)
        if (
            isinstance(record.get("record_count"), int)
            and isinstance(record.get("inscription_record_count"), int)
            and record["record_count"] != record["inscription_record_count"]
        ):
            errors.append(f"sources[{index}] record_count does not match inscription_record_count")
        if (
            isinstance(record.get("line_count"), int)
            and isinstance(record.get("line_record_count"), int)
            and record["line_count"] != record["line_record_count"]
        ):
            errors.append(f"sources[{index}] line_count does not match line_record_count")
        errors.extend(scan_for_absolute_paths(record, context=f"sources[{index}]"))
    return errors


def validate_required_docs(repo_root: Path) -> list[str]:
    errors: list[str] = []
    for relative_path in REQUIRED_RELEASE_DOCS:
        if not (repo_root / relative_path).exists():
            errors.append(f"missing required documentation file {relative_path}")
    return errors


def validate_manifest(
    manifest: dict,
    *,
    inscriptions: list[dict],
    lines: list[dict],
    editorial_relations: list[dict],
    sources: list[dict],
) -> list[str]:
    errors: list[str] = []
    required_fields = {
        "release_id": str,
        "release_date": str,
        "created_by_script": str,
        "input_releases": list,
        "input_working_files": list,
        "record_counts_by_source": dict,
        "line_counts_by_source": dict,
        "source_contribution_counts": dict,
        "total_inscription_count": int,
        "total_line_count": int,
        "editorial_relation_count": int,
        "source_count": int,
        "validation_status": str,
        "known_limitations": list,
        "recommended_next_steps": list,
    }
    for field, expected_type in required_fields.items():
        if field not in manifest:
            errors.append(f"release_manifest missing field {field}")
            continue
        if not isinstance(manifest[field], expected_type):
            errors.append(f"release_manifest field {field} has wrong type")

    expected_record_counts = {record["source_id"]: record["record_count"] for record in sources}
    expected_line_counts = {record["source_id"]: record["line_count"] for record in sources}
    expected_source_contribution_counts = {
        record["source_id"]: {
            "inscription_records": record["inscription_record_count"],
            "line_records": record["line_record_count"],
            "editorial_relations": record["editorial_relation_count"],
        }
        for record in sources
    }
    if manifest.get("record_counts_by_source") != expected_record_counts:
        errors.append("release_manifest record_counts_by_source does not match sources.jsonl")
    if manifest.get("line_counts_by_source") != expected_line_counts:
        errors.append("release_manifest line_counts_by_source does not match sources.jsonl")
    if manifest.get("source_contribution_counts") != expected_source_contribution_counts:
        errors.append("release_manifest source_contribution_counts does not match sources.jsonl")
    if manifest.get("total_inscription_count") != len(inscriptions):
        errors.append("release_manifest total_inscription_count does not match inscriptions.jsonl")
    if manifest.get("total_line_count") != len(lines):
        errors.append("release_manifest total_line_count does not match lines.jsonl")
    if manifest.get("editorial_relation_count") != len(editorial_relations):
        errors.append("release_manifest editorial_relation_count does not match editorial_relations.jsonl")
    if manifest.get("source_count") != len(sources):
        errors.append("release_manifest source_count does not match sources.jsonl")
    errors.extend(scan_for_absolute_paths(manifest, context="release_manifest"))
    return errors


def validate_sqlite_export(
    sqlite_path: Path,
    *,
    inscriptions: list[dict],
    lines: list[dict],
    editorial_relations: list[dict],
    sources: list[dict],
) -> list[str]:
    errors: list[str] = []
    if not sqlite_path.exists():
        return [f"missing SQLite export {repo_relative_path(sqlite_path)}"]
    with sqlite3.connect(sqlite_path) as conn:
        expected_counts = {
            "inscriptions": len(inscriptions),
            "lines": len(lines),
            "editorial_relations": len(editorial_relations),
            "sources": len(sources),
        }
        for table_name, expected_count in expected_counts.items():
            cursor = conn.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name = ?",
                (table_name,),
            )
            if cursor.fetchone()[0] == 0:
                errors.append(f"SQLite export missing table {table_name}")
                continue
            actual_count = conn.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()[0]
            if actual_count != expected_count:
                errors.append(f"SQLite export table {table_name} count mismatch: expected {expected_count}, found {actual_count}")
    return errors


def validate_dataset(
    dataset_dir: Path,
    *,
    allow_missing_dataset_validation_report: bool = False,
    docs_root: Path = REPO_ROOT,
) -> dict:
    result = {"dataset": repo_relative_path(dataset_dir), "errors": [], "record_counts": {}}
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

    editorial_relations_path = dataset_dir / "editorial_relations.jsonl"
    if dataset_dir.name == "unified_release_v0_2":
        if not editorial_relations_path.exists():
            result["errors"].append("missing editorial_relations.jsonl")
            return result
        editorial_relations = read_jsonl(editorial_relations_path)
        result["errors"].extend(validate_editorial_relations(editorial_relations, inscription_ids))
        result["record_counts"]["editorial_relations"] = len(editorial_relations)
    elif dataset_dir.name == "corpus_release_v0_3":
        required_files = set(CORPUS_RELEASE_REQUIRED_FILES)
        if allow_missing_dataset_validation_report:
            required_files.remove("validation_report.json")
        missing_files = [name for name in sorted(required_files) if not (dataset_dir / name).exists()]
        if missing_files:
            result["errors"].append("missing required corpus release files: " + ", ".join(missing_files))
            return result
        if not editorial_relations_path.exists():
            result["errors"].append("missing editorial_relations.jsonl")
            return result
        editorial_relations = read_jsonl(editorial_relations_path)
        result["errors"].extend(validate_editorial_relations(editorial_relations, inscription_ids))
        result["record_counts"]["editorial_relations"] = len(editorial_relations)

        sources = read_jsonl(dataset_dir / "sources.jsonl")
        result["errors"].extend(validate_sources(sources))
        result["record_counts"]["sources"] = len(sources)
        result["errors"].extend(validate_required_docs(docs_root))
        source_ids = {record["source_id"] for record in sources if "source_id" in record}
        for record in inscriptions:
            if record.get("source_deposit") not in source_ids:
                result["errors"].append(
                    f"inscription {record.get('record_id')} uses unknown source_deposit {record.get('source_deposit')}"
                )

        manifest = json.loads((dataset_dir / "release_manifest.json").read_text(encoding="utf-8"))
        result["errors"].extend(
            validate_manifest(
                manifest,
                inscriptions=inscriptions,
                lines=lines,
                editorial_relations=editorial_relations,
                sources=sources,
            )
        )
        for record in inscriptions:
            if record.get("source_layer") is None:
                result["errors"].append(f"inscription {record.get('record_id')} missing source_layer")
            if record.get("release_status") is None:
                result["errors"].append(f"inscription {record.get('record_id')} missing release_status")
        validation_report_path = dataset_dir / "validation_report.json"
        if validation_report_path.exists():
            result["errors"].extend(
                scan_for_absolute_paths(
                    json.loads(validation_report_path.read_text(encoding="utf-8")),
                    context="validation_report",
                )
            )
        result["errors"].extend(
            scan_for_absolute_paths(
                (dataset_dir / "README.md").read_text(encoding="utf-8"),
                context="release_readme",
            )
        )
        result["errors"].extend(
            scan_for_absolute_paths(
                (dataset_dir / "release_notes.md").read_text(encoding="utf-8"),
                context="release_notes",
            )
        )
        result["errors"].extend(
            validate_sqlite_export(
                dataset_dir / "corpus_release.sqlite",
                inscriptions=inscriptions,
                lines=lines,
                editorial_relations=editorial_relations,
                sources=sources,
            )
        )
    elif editorial_relations_path.exists():
        editorial_relations = read_jsonl(editorial_relations_path)
        result["errors"].extend(validate_editorial_relations(editorial_relations, inscription_ids))
        result["record_counts"]["editorial_relations"] = len(editorial_relations)
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
        REPO_ROOT / "data" / "release" / "unified_release_v0_2",
        REPO_ROOT / "data" / "release" / "corpus_release_v0_3",
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
