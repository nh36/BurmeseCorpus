from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from corpus_common import read_tsv, write_tsv
from local_bibliography_common import (
    FRASCH_TERMS,
    HIGH_PRIORITY_TERMS,
    configured_roots,
    copy_to_local_cache,
    discover_candidate_files,
    filename_metadata,
    missing_root_instructions,
    probable_relevance,
    safe_source_path,
    source_file_id,
)

BURMA_DOMAIN_TERMS = [
    "burma",
    "burmese",
    "myanmar",
    "pagan",
    "bagan",
    "luce",
    "duroiselle",
    "blagden",
    "than tun",
    "pe maung tin",
    "frasch",
    "jbrs",
    "bbhc",
    "jras",
    "rdasb",
]


FRASCH_FIELDS = [
    "candidate_id",
    "match_type",
    "name",
    "original_path",
    "file_type",
    "file_size",
    "modified_time",
    "sha256",
    "probable_relevance",
    "copy_status",
    "copied_path",
    "extraction_status",
    "notes",
]

HIGH_PRIORITY_FIELDS = [
    "candidate_id",
    "search_term",
    "name",
    "original_path",
    "file_type",
    "file_size",
    "sha256",
    "probable_work_label",
    "probable_author",
    "probable_year",
    "match_confidence",
    "copy_status",
    "copied_path",
    "notes",
]

MANIFEST_FIELDS = [
    "source_file_id",
    "original_path",
    "copied_path",
    "file_name",
    "file_type",
    "file_size",
    "sha256",
    "source_folder_hint",
    "copy_date",
    "copy_status",
    "notes",
]


def merge_manifest_rows(manifest_path: Path, new_rows: list[dict]) -> list[dict]:
    existing = read_tsv(manifest_path) if manifest_path.exists() else []
    by_key = {row["original_path"]: row for row in existing}
    for row in new_rows:
        by_key[row["original_path"]] = row
    merged = sorted(by_key.values(), key=lambda row: row["original_path"])
    write_tsv(manifest_path, merged, MANIFEST_FIELDS)
    return merged


def is_burma_relevant(path: Path) -> bool:
    haystack = f"{path.as_posix()} {path.parent.as_posix()}".casefold()
    return any(term in haystack for term in BURMA_DOMAIN_TERMS)


def run_harvest(mode: str, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    roots = configured_roots()
    manifest_path = output_dir / "local_file_manifest.tsv"
    report_path = output_dir / "local_source_harvest_report.json"

    if not roots:
        report = {
            "mode": mode,
            "available_roots": [],
            "candidate_count": 0,
            "copied_file_count": 0,
            "instructions": missing_root_instructions(),
        }
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        if not manifest_path.exists():
            write_tsv(manifest_path, [], MANIFEST_FIELDS)
        target_path = output_dir / ("frasch_source_candidates.tsv" if mode == "frasch" else "high_priority_local_candidates.tsv")
        if not target_path.exists():
            write_tsv(target_path, [], FRASCH_FIELDS if mode == "frasch" else HIGH_PRIORITY_FIELDS)
        return report

    search_terms = FRASCH_TERMS if mode == "frasch" else HIGH_PRIORITY_TERMS
    candidates = discover_candidate_files(roots, search_terms)
    if mode == "high-priority":
        candidates = [candidate for candidate in candidates if is_burma_relevant(candidate[1])]
    copied_rows: list[dict] = []
    candidate_rows: list[dict] = []
    target_path = output_dir / ("frasch_source_candidates.tsv" if mode == "frasch" else "high_priority_local_candidates.tsv")

    for root, path, match_type in candidates:
        metadata = filename_metadata(path)
        file_id = source_file_id(path, root)
        relevance = probable_relevance(path, search_terms)
        copied = copy_to_local_cache(path, root, source_folder_hint=path.parent.name)
        copied_rows.append(copied)
        if mode == "frasch":
            candidate_rows.append(
                {
                    "candidate_id": file_id,
                    "match_type": match_type,
                    "name": path.name,
                    "original_path": safe_source_path(path, root),
                    "file_type": path.suffix.casefold().lstrip("."),
                    "file_size": str(path.stat().st_size),
                    "modified_time": path.stat().st_mtime,
                    "sha256": copied["sha256"],
                    "probable_relevance": relevance,
                    "copy_status": copied["copy_status"],
                    "copied_path": copied["copied_path"],
                    "extraction_status": "pending",
                    "notes": "",
                }
            )
        else:
            matched_term = next((term for term in search_terms if term in path.name.casefold() or term in path.parent.name.casefold()), "")
            candidate_rows.append(
                {
                    "candidate_id": file_id,
                    "search_term": matched_term,
                    "name": path.name,
                    "original_path": safe_source_path(path, root),
                    "file_type": path.suffix.casefold().lstrip("."),
                    "file_size": str(path.stat().st_size),
                    "sha256": copied["sha256"],
                    "probable_work_label": metadata["probable_work_label"],
                    "probable_author": metadata["probable_author"],
                    "probable_year": metadata["probable_year"],
                    "match_confidence": "high" if relevance == "high" else "medium",
                    "copy_status": copied["copy_status"],
                    "copied_path": copied["copied_path"],
                    "notes": "",
                }
            )

    candidate_rows.sort(key=lambda row: (row.get("probable_relevance", ""), row["name"]), reverse=True)
    write_tsv(target_path, candidate_rows, FRASCH_FIELDS if mode == "frasch" else HIGH_PRIORITY_FIELDS)
    merged_manifest = merge_manifest_rows(manifest_path, copied_rows)

    report = {
        "mode": mode,
        "available_roots": [f"{root.label}:{root.path.name}" for root in roots],
        "candidate_count": len(candidate_rows),
        "copied_file_count": len(copied_rows),
        "file_type_counts": dict(Counter(row["file_type"] for row in candidate_rows)),
        "manifest_row_count": len(merged_manifest),
        "output_file": target_path.as_posix(),
    }
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Harvest local bibliography source candidates into a gitignored cache.")
    parser.add_argument("--mode", choices=["frasch", "high-priority"], required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("data/working/bibliography/local_sources"))
    args = parser.parse_args()
    result = run_harvest(args.mode, args.output_dir)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
